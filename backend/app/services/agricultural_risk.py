"""
Agricultural Risk Engine Service
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Evaluates crop-specific, stage-aware, and soil-integrated agricultural stress conditions
using transparent, explainable rule criteria.

Strict Scientific Scope:
- Identifies risk conditions and stress severity (NOT a farmer advisory).
- Disease-favorable evaluations indicate environmental suitability (NOT a disease diagnosis).
- Missing inputs trigger explicit INSUFFICIENT_DATA (never converted to NOT_DETECTED or 0).
- Multi-crop Panchayats evaluated independently per crop/stage.
- Idempotent upsert persistence to AgriculturalRiskLog.
"""
import uuid
import math
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, or_

from app.core.config import settings
from app.core.logging import logger
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import PanchayatWeather
from app.db.models.agriculture import Crop, CropPhenologyStage, SoilProfile, PanchayatCropContext
from app.db.models.advisory import AgriculturalRiskLog
from app.schemas.agricultural_context import PanchayatCropContextSummary, WeatherContextSummary
from app.schemas.agricultural_risk import (
    RiskStatus,
    RiskSeverity,
    RiskType,
    RiskCategory,
    RiskEvidence,
    RiskResult,
    RiskEvaluationRequest,
    RiskEvaluationResponse,
    PanchayatRiskProfile,
    RiskSubsystemStatus,
)
from app.services.risk_rules import RiskRuleRegistry, RiskRuleDefinition, rule_registry
from app.services.agricultural_context import AgriculturalContextService


class BaseRiskEvaluator:
    """Base class for modular agricultural risk evaluators."""

    def __init__(self, registry: RiskRuleRegistry):
        self.registry = registry

    def evaluate(
        self,
        crop_context: PanchayatCropContextSummary,
        weather: WeatherContextSummary,
        evaluation_date: datetime,
    ) -> RiskResult:
        raise NotImplementedError


class HeatStressEvaluator(BaseRiskEvaluator):
    """Evaluates high-temperature / thermal stress against crop and stage thresholds."""

    def evaluate(
        self,
        crop_context: PanchayatCropContextSummary,
        weather: WeatherContextSummary,
        evaluation_date: datetime,
    ) -> RiskResult:
        crop_name = crop_context.crop_name
        stage_name = crop_context.crop_stage.stage_name
        rule = self.registry.get_rule(risk_type="HEAT_STRESS", crop_name=crop_name, stage_name=stage_name)
        rule_version = rule.rule_version if rule else self.registry.RULE_VERSION
        rule_source = rule.rule_source if rule else self.registry.RULE_SOURCE

        # Data quality check: observed max temperature
        obs_val = weather.max_temp_c
        if obs_val is None:
            evidence = RiskEvidence(
                observed_value=None,
                threshold_value=None,
                unit="°C",
                crop_name=crop_name,
                stage_name=stage_name,
                condition_description="Maximum temperature forecast data unavailable for evaluation.",
                metrics={"weather_status": weather.weather_status},
            )
            return self._build_result(
                crop_context=crop_context,
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                status="INSUFFICIENT_DATA",
                severity="NONE",
                risk_score=None,
                observed_val=None,
                threshold_val=None,
                unit="°C",
                confidence="INSUFFICIENT",
                rule_version=rule_version,
                rule_source=rule_source,
                evidence=evidence,
                evaluation_date=evaluation_date,
            )

        if not rule or not rule.thresholds:
            evidence = RiskEvidence(
                observed_value=obs_val,
                threshold_value=None,
                unit="°C",
                crop_name=crop_name,
                stage_name=stage_name,
                condition_description=f"No thermal stress rule configured for crop '{crop_name}'.",
                metrics={"max_temp_c": obs_val},
            )
            return self._build_result(
                crop_context=crop_context,
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                status="INSUFFICIENT_DATA",
                severity="NONE",
                risk_score=None,
                observed_val=obs_val,
                threshold_val=None,
                unit="°C",
                confidence="LOW",
                rule_version=rule_version,
                rule_source=rule_source,
                evidence=evidence,
                evaluation_date=evaluation_date,
            )

        # Threshold evaluation (Extreme > High > Moderate > Low)
        thresholds = rule.thresholds
        severity = "NONE"
        status = "NOT_DETECTED"
        matched_thresh = None

        if "EXTREME" in thresholds and obs_val >= thresholds["EXTREME"]:
            severity = "EXTREME"
            status = "DETECTED"
            matched_thresh = thresholds["EXTREME"]
        elif "HIGH" in thresholds and obs_val >= thresholds["HIGH"]:
            severity = "HIGH"
            status = "DETECTED"
            matched_thresh = thresholds["HIGH"]
        elif "MODERATE" in thresholds and obs_val >= thresholds["MODERATE"]:
            severity = "MODERATE"
            status = "DETECTED"
            matched_thresh = thresholds["MODERATE"]
        elif "LOW" in thresholds and obs_val >= thresholds["LOW"]:
            severity = "LOW"
            status = "DETECTED"
            matched_thresh = thresholds["LOW"]
        else:
            matched_thresh = thresholds.get("MODERATE") or thresholds.get("LOW")

        # Explainable normalized score calculation
        min_t = thresholds.get("LOW") or thresholds.get("MODERATE", 35.0)
        max_t = thresholds.get("EXTREME") or (thresholds.get("HIGH", 38.0) + 3.0)
        if status == "DETECTED" and max_t > min_t:
            risk_score = round(min(1.0, max(0.2, (obs_val - min_t) / (max_t - min_t))), 3)
        else:
            risk_score = 0.0

        if status == "DETECTED":
            desc = rule.evidence_template.format(observed=obs_val, threshold=matched_thresh)
        else:
            desc = f"Max temperature ({obs_val:.1f}°C) below thermal threshold ({matched_thresh:.1f}°C)."

        confidence = "HIGH" if crop_context.crop_stage.is_stage_resolved and weather.weather_status == "COMPLETE" else "MEDIUM"

        evidence = RiskEvidence(
            observed_value=obs_val,
            threshold_value=matched_thresh,
            unit="°C",
            crop_name=crop_name,
            stage_name=stage_name,
            condition_description=desc,
            metrics={"mean_temp_c": weather.mean_temp_c, "min_temp_c": weather.min_temp_c, "temp_stddev_c": weather.temp_stddev_c},
        )

        return self._build_result(
            crop_context=crop_context,
            risk_type="HEAT_STRESS",
            risk_category="THERMAL",
            status=status,
            severity=severity,
            risk_score=risk_score if status == "DETECTED" else 0.0,
            observed_val=obs_val,
            threshold_val=matched_thresh,
            unit="°C",
            confidence=confidence,
            rule_version=rule_version,
            rule_source=rule_source,
            evidence=evidence,
            evaluation_date=evaluation_date,
        )

    def _build_result(self, **kwargs) -> RiskResult:
        ctx: PanchayatCropContextSummary = kwargs["crop_context"]
        return RiskResult(
            id=None,
            panchayat_id=ctx.panchayat_id,
            panchayat_name=ctx.panchayat_name,
            block_id=ctx.block_id,
            block_name=ctx.block_name,
            crop_id=ctx.crop_id,
            crop_name=ctx.crop_name,
            stage_name=ctx.crop_stage.stage_name,
            risk_type=kwargs["risk_type"],
            risk_category=kwargs["risk_category"],
            status=kwargs["status"],
            severity=kwargs["severity"],
            risk_score=kwargs["risk_score"],
            observed_value=kwargs["observed_val"],
            threshold_value=kwargs["threshold_val"],
            unit=kwargs["unit"],
            duration_hours=24.0,
            confidence=kwargs["confidence"],
            rule_version=kwargs["rule_version"],
            rule_source=kwargs["rule_source"],
            evidence=kwargs["evidence"],
            provenance={
                "panchayat_id": ctx.panchayat_id,
                "crop_id": ctx.crop_id,
                "weather_id": ctx.weather.panchayat_weather_id,
                "rule_version": kwargs["rule_version"],
                "generation_timestamp": datetime.utcnow().isoformat(),
            },
            evaluation_date=kwargs["evaluation_date"].isoformat(),
            created_at=datetime.utcnow().isoformat(),
        )


class ColdStressEvaluator(BaseRiskEvaluator):
    """Evaluates low-temperature / chilling / frost stress against crop thresholds."""

    def evaluate(
        self,
        crop_context: PanchayatCropContextSummary,
        weather: WeatherContextSummary,
        evaluation_date: datetime,
    ) -> RiskResult:
        crop_name = crop_context.crop_name
        stage_name = crop_context.crop_stage.stage_name
        rule = self.registry.get_rule(risk_type="COLD_STRESS", crop_name=crop_name, stage_name=stage_name)
        rule_version = rule.rule_version if rule else self.registry.RULE_VERSION
        rule_source = rule.rule_source if rule else self.registry.RULE_SOURCE

        obs_val = weather.min_temp_c
        if obs_val is None:
            evidence = RiskEvidence(
                observed_value=None,
                threshold_value=None,
                unit="°C",
                crop_name=crop_name,
                stage_name=stage_name,
                condition_description="Minimum temperature forecast data unavailable for evaluation.",
                metrics={"weather_status": weather.weather_status},
            )
            return self._build_result(
                crop_context=crop_context,
                risk_type="COLD_STRESS",
                risk_category="THERMAL",
                status="INSUFFICIENT_DATA",
                severity="NONE",
                risk_score=None,
                observed_val=None,
                threshold_val=None,
                unit="°C",
                confidence="INSUFFICIENT",
                rule_version=rule_version,
                rule_source=rule_source,
                evidence=evidence,
                evaluation_date=evaluation_date,
            )

        if not rule or not rule.thresholds:
            evidence = RiskEvidence(
                observed_value=obs_val,
                threshold_value=None,
                unit="°C",
                crop_name=crop_name,
                stage_name=stage_name,
                condition_description=f"No cold stress rule configured for crop '{crop_name}'.",
                metrics={"min_temp_c": obs_val},
            )
            return self._build_result(
                crop_context=crop_context,
                risk_type="COLD_STRESS",
                risk_category="THERMAL",
                status="INSUFFICIENT_DATA",
                severity="NONE",
                risk_score=None,
                observed_val=obs_val,
                threshold_val=None,
                unit="°C",
                confidence="LOW",
                rule_version=rule_version,
                rule_source=rule_source,
                evidence=evidence,
                evaluation_date=evaluation_date,
            )

        # Threshold evaluation for LE comparison (Extreme <= High <= Moderate <= Low)
        thresholds = rule.thresholds
        severity = "NONE"
        status = "NOT_DETECTED"
        matched_thresh = None

        if "EXTREME" in thresholds and obs_val <= thresholds["EXTREME"]:
            severity = "EXTREME"
            status = "DETECTED"
            matched_thresh = thresholds["EXTREME"]
        elif "HIGH" in thresholds and obs_val <= thresholds["HIGH"]:
            severity = "HIGH"
            status = "DETECTED"
            matched_thresh = thresholds["HIGH"]
        elif "MODERATE" in thresholds and obs_val <= thresholds["MODERATE"]:
            severity = "MODERATE"
            status = "DETECTED"
            matched_thresh = thresholds["MODERATE"]
        elif "LOW" in thresholds and obs_val <= thresholds["LOW"]:
            severity = "LOW"
            status = "DETECTED"
            matched_thresh = thresholds["LOW"]
        else:
            matched_thresh = thresholds.get("MODERATE") or thresholds.get("LOW")

        max_t = thresholds.get("LOW") or thresholds.get("MODERATE", 10.0)
        min_t = thresholds.get("EXTREME") or (thresholds.get("HIGH", 2.0) - 2.0)
        if status == "DETECTED" and max_t > min_t:
            risk_score = round(min(1.0, max(0.2, (max_t - obs_val) / (max_t - min_t))), 3)
        else:
            risk_score = 0.0

        if status == "DETECTED":
            desc = rule.evidence_template.format(observed=obs_val, threshold=matched_thresh)
        else:
            desc = f"Min temperature ({obs_val:.1f}°C) above chilling threshold ({matched_thresh:.1f}°C)."

        confidence = "HIGH" if crop_context.crop_stage.is_stage_resolved and weather.weather_status == "COMPLETE" else "MEDIUM"

        evidence = RiskEvidence(
            observed_value=obs_val,
            threshold_value=matched_thresh,
            unit="°C",
            crop_name=crop_name,
            stage_name=stage_name,
            condition_description=desc,
            metrics={"mean_temp_c": weather.mean_temp_c, "min_temp_c": obs_val},
        )

        return self._build_result(
            crop_context=crop_context,
            risk_type="COLD_STRESS",
            risk_category="THERMAL",
            status=status,
            severity=severity,
            risk_score=risk_score if status == "DETECTED" else 0.0,
            observed_val=obs_val,
            threshold_val=matched_thresh,
            unit="°C",
            confidence=confidence,
            rule_version=rule_version,
            rule_source=rule_source,
            evidence=evidence,
            evaluation_date=evaluation_date,
        )

    def _build_result(self, **kwargs) -> RiskResult:
        ctx: PanchayatCropContextSummary = kwargs["crop_context"]
        return RiskResult(
            id=None,
            panchayat_id=ctx.panchayat_id,
            panchayat_name=ctx.panchayat_name,
            block_id=ctx.block_id,
            block_name=ctx.block_name,
            crop_id=ctx.crop_id,
            crop_name=ctx.crop_name,
            stage_name=ctx.crop_stage.stage_name,
            risk_type=kwargs["risk_type"],
            risk_category=kwargs["risk_category"],
            status=kwargs["status"],
            severity=kwargs["severity"],
            risk_score=kwargs["risk_score"],
            observed_value=kwargs["observed_val"],
            threshold_value=kwargs["threshold_val"],
            unit=kwargs["unit"],
            duration_hours=24.0,
            confidence=kwargs["confidence"],
            rule_version=kwargs["rule_version"],
            rule_source=kwargs["rule_source"],
            evidence=kwargs["evidence"],
            provenance={
                "panchayat_id": ctx.panchayat_id,
                "crop_id": ctx.crop_id,
                "weather_id": ctx.weather.panchayat_weather_id,
                "rule_version": kwargs["rule_version"],
                "generation_timestamp": datetime.utcnow().isoformat(),
            },
            evaluation_date=kwargs["evaluation_date"].isoformat(),
            created_at=datetime.utcnow().isoformat(),
        )


class DiseaseFavorableEvaluator(BaseRiskEvaluator):
    """
    Evaluates micro-climatic environmental suitability for fungal/bacterial foliar pathogen propagation.
    Strictly reports environmental favorability, NOT a disease diagnosis.
    """

    def evaluate(
        self,
        crop_context: PanchayatCropContextSummary,
        weather: WeatherContextSummary,
        evaluation_date: datetime,
    ) -> RiskResult:
        crop_name = crop_context.crop_name
        stage_name = crop_context.crop_stage.stage_name
        rule = self.registry.get_rule(risk_type="DISEASE_FAVORABLE_CONDITIONS", crop_name=crop_name, stage_name=stage_name)
        rule_version = rule.rule_version if rule else self.registry.RULE_VERSION
        rule_source = rule.rule_source if rule else self.registry.RULE_SOURCE

        mean_t = weather.mean_temp_c
        if mean_t is None:
            evidence = RiskEvidence(
                observed_value=None,
                threshold_value=None,
                unit="°C",
                crop_name=crop_name,
                stage_name=stage_name,
                condition_description="Mean temperature unavailable for pathogen environmental window analysis.",
                metrics={"weather_status": weather.weather_status},
            )
            return self._build_result(
                crop_context=crop_context,
                status="INSUFFICIENT_DATA",
                severity="NONE",
                risk_score=None,
                observed_val=None,
                threshold_val=None,
                evidence=evidence,
                confidence="INSUFFICIENT",
                rule_version=rule_version,
                rule_source=rule_source,
                evaluation_date=evaluation_date,
            )

        # Pathogen environmental window: 22.0°C <= mean_t <= 32.0°C
        is_favorable_temp = (22.0 <= mean_t <= 32.0)
        
        if is_favorable_temp:
            status = "DETECTED"
            severity = "MODERATE"
            risk_score = 0.65
            desc = (
                f"Environmental mean temperature ({mean_t:.1f}°C) is within the favorable pathogen proliferation range (22-32°C). "
                f"Note: Indicates environmental suitability only, NOT confirmed disease presence."
            )
        else:
            status = "NOT_DETECTED"
            severity = "NONE"
            risk_score = 0.0
            desc = f"Environmental temperature ({mean_t:.1f}°C) outside optimal foliar pathogen proliferation window."

        evidence = RiskEvidence(
            observed_value=mean_t,
            threshold_value=22.0,
            unit="°C",
            crop_name=crop_name,
            stage_name=stage_name,
            condition_description=desc,
            metrics={"mean_temp_c": mean_t, "min_temp_c": weather.min_temp_c, "max_temp_c": weather.max_temp_c},
        )

        return self._build_result(
            crop_context=crop_context,
            status=status,
            severity=severity,
            risk_score=risk_score,
            observed_val=mean_t,
            threshold_val=22.0,
            evidence=evidence,
            confidence="MEDIUM",
            rule_version=rule_version,
            rule_source=rule_source,
            evaluation_date=evaluation_date,
        )

    def _build_result(self, **kwargs) -> RiskResult:
        ctx: PanchayatCropContextSummary = kwargs["crop_context"]
        return RiskResult(
            id=None,
            panchayat_id=ctx.panchayat_id,
            panchayat_name=ctx.panchayat_name,
            block_id=ctx.block_id,
            block_name=ctx.block_name,
            crop_id=ctx.crop_id,
            crop_name=ctx.crop_name,
            stage_name=ctx.crop_stage.stage_name,
            risk_type="DISEASE_FAVORABLE_CONDITIONS",
            risk_category="PATHOLOGICAL_ENVIRONMENT",
            status=kwargs["status"],
            severity=kwargs["severity"],
            risk_score=kwargs["risk_score"],
            observed_value=kwargs["observed_val"],
            threshold_value=kwargs["threshold_val"],
            unit="°C",
            duration_hours=24.0,
            confidence=kwargs["confidence"],
            rule_version=kwargs["rule_version"],
            rule_source=kwargs["rule_source"],
            evidence=kwargs["evidence"],
            provenance={
                "panchayat_id": ctx.panchayat_id,
                "crop_id": ctx.crop_id,
                "rule_version": kwargs["rule_version"],
                "generation_timestamp": datetime.utcnow().isoformat(),
            },
            evaluation_date=kwargs["evaluation_date"].isoformat(),
            created_at=datetime.utcnow().isoformat(),
        )


class WaterStressEvaluator(BaseRiskEvaluator):
    """
    Evaluates soil water / dry-spell moisture deficit.
    Requires multi-day precipitation temporal window and soil water holding capacity.
    """

    def evaluate(
        self,
        crop_context: PanchayatCropContextSummary,
        weather: WeatherContextSummary,
        evaluation_date: datetime,
    ) -> RiskResult:
        crop_name = crop_context.crop_name
        stage_name = crop_context.crop_stage.stage_name
        rule = self.registry.get_rule(risk_type="WATER_STRESS", crop_name=crop_name, stage_name=stage_name)
        rule_version = rule.rule_version if rule else self.registry.RULE_VERSION
        rule_source = rule.rule_source if rule else self.registry.RULE_SOURCE

        # Check soil water holding capacity availability
        soil_whc = crop_context.soil.water_holding_capacity_pct
        if soil_whc is None or not crop_context.soil.soil_available:
            evidence = RiskEvidence(
                observed_value=None,
                threshold_value=None,
                unit="%",
                crop_name=crop_name,
                stage_name=stage_name,
                condition_description="Soil water-holding capacity data unavailable for water stress evaluation.",
                metrics={"soil_status": crop_context.soil.soil_status},
            )
            return self._build_result(
                crop_context=crop_context,
                status="INSUFFICIENT_DATA",
                severity="NONE",
                risk_score=None,
                observed_val=None,
                threshold_val=None,
                evidence=evidence,
                confidence="INSUFFICIENT",
                rule_version=rule_version,
                rule_source=rule_source,
                evaluation_date=evaluation_date,
            )

        # Single-day forecast limitation: multi-day precipitation history required
        evidence = RiskEvidence(
            observed_value=soil_whc,
            threshold_value=20.0,
            unit="%",
            crop_name=crop_name,
            stage_name=stage_name,
            condition_description=(
                f"Available soil water holding capacity is {soil_whc:.1f}%. "
                f"Multi-day rainfall accumulation history is required to determine dry-spell progression."
            ),
            metrics={"water_holding_capacity_pct": soil_whc, "soil_type": crop_context.soil.soil_type},
        )
        return self._build_result(
            crop_context=crop_context,
            status="INSUFFICIENT_DATA",
            severity="NONE",
            risk_score=None,
            observed_val=soil_whc,
            threshold_val=20.0,
            evidence=evidence,
            confidence="LOW",
            rule_version=rule_version,
            rule_source=rule_source,
            evaluation_date=evaluation_date,
        )

    def _build_result(self, **kwargs) -> RiskResult:
        ctx: PanchayatCropContextSummary = kwargs["crop_context"]
        return RiskResult(
            id=None,
            panchayat_id=ctx.panchayat_id,
            panchayat_name=ctx.panchayat_name,
            block_id=ctx.block_id,
            block_name=ctx.block_name,
            crop_id=ctx.crop_id,
            crop_name=ctx.crop_name,
            stage_name=ctx.crop_stage.stage_name,
            risk_type="WATER_STRESS",
            risk_category="HYDROLOGICAL",
            status=kwargs["status"],
            severity=kwargs["severity"],
            risk_score=kwargs["risk_score"],
            observed_value=kwargs["observed_val"],
            threshold_value=kwargs["threshold_val"],
            unit="%",
            duration_hours=24.0,
            confidence=kwargs["confidence"],
            rule_version=kwargs["rule_version"],
            rule_source=kwargs["rule_source"],
            evidence=kwargs["evidence"],
            provenance={
                "panchayat_id": ctx.panchayat_id,
                "crop_id": ctx.crop_id,
                "rule_version": kwargs["rule_version"],
                "generation_timestamp": datetime.utcnow().isoformat(),
            },
            evaluation_date=kwargs["evaluation_date"].isoformat(),
            created_at=datetime.utcnow().isoformat(),
        )


class ExcessRainEvaluator(BaseRiskEvaluator):
    """
    Evaluates excessive rainfall and waterlogging risk using available forecast precipitation.
    Does NOT perform rainfall spatial downscaling.
    """

    def evaluate(
        self,
        crop_context: PanchayatCropContextSummary,
        weather: WeatherContextSummary,
        evaluation_date: datetime,
    ) -> RiskResult:
        crop_name = crop_context.crop_name
        stage_name = crop_context.crop_stage.stage_name
        rule = self.registry.get_rule(risk_type="EXCESS_RAIN", crop_name=crop_name, stage_name=stage_name)
        rule_version = rule.rule_version if rule else self.registry.RULE_VERSION
        rule_source = rule.rule_source if rule else self.registry.RULE_SOURCE

        # Rainfall forecast data check
        evidence = RiskEvidence(
            observed_value=None,
            threshold_value=50.0,
            unit="mm",
            crop_name=crop_name,
            stage_name=stage_name,
            condition_description="Forecast precipitation data unavailable for heavy rainfall / waterlogging evaluation.",
            metrics={"soil_drainage": crop_context.soil.drainage_class},
        )
        return RiskResult(
            id=None,
            panchayat_id=crop_context.panchayat_id,
            panchayat_name=crop_context.panchayat_name,
            block_id=crop_context.block_id,
            block_name=crop_context.block_name,
            crop_id=crop_context.crop_id,
            crop_name=crop_context.crop_name,
            stage_name=crop_context.crop_stage.stage_name,
            risk_type="EXCESS_RAIN",
            risk_category="HYDROLOGICAL",
            status="INSUFFICIENT_DATA",
            severity="NONE",
            risk_score=None,
            observed_value=None,
            threshold_value=50.0,
            unit="mm",
            duration_hours=24.0,
            confidence="INSUFFICIENT",
            rule_version=rule_version,
            rule_source=rule_source,
            evidence=evidence,
            provenance={
                "panchayat_id": crop_context.panchayat_id,
                "crop_id": crop_context.crop_id,
                "rule_version": rule_version,
                "generation_timestamp": datetime.utcnow().isoformat(),
            },
            evaluation_date=evaluation_date.isoformat(),
            created_at=datetime.utcnow().isoformat(),
        )


class WindStressEvaluator(BaseRiskEvaluator):
    """Evaluates crop lodging risk from forecast sustained high wind conditions."""

    def evaluate(
        self,
        crop_context: PanchayatCropContextSummary,
        weather: WeatherContextSummary,
        evaluation_date: datetime,
    ) -> RiskResult:
        crop_name = crop_context.crop_name
        stage_name = crop_context.crop_stage.stage_name
        rule = self.registry.get_rule(risk_type="WIND_STRESS", crop_name=crop_name, stage_name=stage_name)
        rule_version = rule.rule_version if rule else self.registry.RULE_VERSION
        rule_source = rule.rule_source if rule else self.registry.RULE_SOURCE

        evidence = RiskEvidence(
            observed_value=None,
            threshold_value=35.0,
            unit="km/h",
            crop_name=crop_name,
            stage_name=stage_name,
            condition_description="Forecast wind speed unavailable for mechanical lodging evaluation.",
            metrics={},
        )
        return RiskResult(
            id=None,
            panchayat_id=crop_context.panchayat_id,
            panchayat_name=crop_context.panchayat_name,
            block_id=crop_context.block_id,
            block_name=crop_context.block_name,
            crop_id=crop_context.crop_id,
            crop_name=crop_context.crop_name,
            stage_name=crop_context.crop_stage.stage_name,
            risk_type="WIND_STRESS",
            risk_category="WIND",
            status="INSUFFICIENT_DATA",
            severity="NONE",
            risk_score=None,
            observed_value=None,
            threshold_value=35.0,
            unit="km/h",
            duration_hours=24.0,
            confidence="INSUFFICIENT",
            rule_version=rule_version,
            rule_source=rule_source,
            evidence=evidence,
            provenance={
                "panchayat_id": crop_context.panchayat_id,
                "crop_id": crop_context.crop_id,
                "rule_version": rule_version,
                "generation_timestamp": datetime.utcnow().isoformat(),
            },
            evaluation_date=evaluation_date.isoformat(),
            created_at=datetime.utcnow().isoformat(),
        )


# ============================================================================
# AGRICULTURAL RISK ENGINE ORCHESTRATOR
# ============================================================================

class AgriculturalRiskEngine:
    """
    Main orchestration engine for agricultural risk evaluation and database persistence.
    """

    def __init__(self, db: Session, registry: Optional[RiskRuleRegistry] = None):
        self.db = db
        self.registry = registry or rule_registry
        self.agri_context_service = AgriculturalContextService(db=db)

        # Register evaluators
        self.evaluators: Dict[str, BaseRiskEvaluator] = {
            "HEAT_STRESS": HeatStressEvaluator(registry=self.registry),
            "COLD_STRESS": ColdStressEvaluator(registry=self.registry),
            "DISEASE_FAVORABLE_CONDITIONS": DiseaseFavorableEvaluator(registry=self.registry),
            "WATER_STRESS": WaterStressEvaluator(registry=self.registry),
            "EXCESS_RAIN": ExcessRainEvaluator(registry=self.registry),
            "WIND_STRESS": WindStressEvaluator(registry=self.registry),
        }

    def evaluate_panchayat_crop_risks(
        self,
        panchayat_id: int,
        evaluation_date: datetime,
        crop_id: Optional[int] = None,
        risk_type_filter: Optional[str] = None,
        persist_to_db: bool = True,
    ) -> List[RiskResult]:
        """
        Evaluates agricultural risks for all (or single) crops in a Panchayat for a specific forecast date.
        """
        # 1. Retrieve Agricultural Contexts for this Panchayat
        contexts = self.agri_context_service.build_panchayat_crop_context(
            panchayat_id=panchayat_id,
            context_date=evaluation_date,
            persist_to_db=False,
        )

        if crop_id is not None:
            contexts = [c for c in contexts if c.crop_id == crop_id]

        all_results: List[RiskResult] = []

        for ctx in contexts:
            # Data Quality Gate: Check Agricultural Cropland Eligibility
            if not ctx.is_agricultural_eligible or ctx.crop_name == "UNAVAILABLE":
                # Non-agricultural Panchayat or unmapped crop: skip risk evaluation
                continue

            # Determine which risk evaluators to run
            evaluator_keys = [risk_type_filter] if risk_type_filter else list(self.evaluators.keys())

            for r_type in evaluator_keys:
                evaluator = self.evaluators.get(r_type)
                if not evaluator:
                    continue

                risk_res = evaluator.evaluate(
                    crop_context=ctx,
                    weather=ctx.weather,
                    evaluation_date=evaluation_date,
                )

                # Persist to database idempotently if requested
                if persist_to_db:
                    db_id = self._persist_risk_result(risk_res=risk_res, crop_context=ctx, evaluation_date=evaluation_date)
                    risk_res.id = db_id

                all_results.append(risk_res)

        return all_results

    def evaluate_block_risks(
        self,
        block_id: int,
        evaluation_date: datetime,
        panchayat_id: Optional[int] = None,
        crop_id: Optional[int] = None,
        risk_type: Optional[str] = None,
        persist_to_db: bool = True,
    ) -> RiskEvaluationResponse:
        """
        Batch risk evaluation across all Panchayats in a Block.
        """
        run_id = str(uuid.uuid4())
        block = self.db.scalar(select(Block).where(Block.id == block_id))
        if not block:
            raise ValueError(f"Block with ID {block_id} not found in database.")

        panchayat_stmt = select(Panchayat).where(Panchayat.block_id == block_id)
        if panchayat_id is not None:
            panchayat_stmt = panchayat_stmt.where(Panchayat.id == panchayat_id)

        panchayats = self.db.scalars(panchayat_stmt).all()
        if not panchayats:
            raise ValueError(f"No Panchayats found for Block '{block.name}' (ID: {block_id}).")

        logger.info(
            f"Executing Phase 10 Agricultural Risk Engine [Run ID: {run_id}] "
            f"for Block '{block.name}' ({len(panchayats)} Panchayats) at {evaluation_date.isoformat()}..."
        )

        all_results: List[RiskResult] = []
        detected_count = 0
        not_detected_count = 0
        insufficient_count = 0
        crops_evaluated_set = set()

        for p in panchayats:
            p_risks = self.evaluate_panchayat_crop_risks(
                panchayat_id=p.id,
                evaluation_date=evaluation_date,
                crop_id=crop_id,
                risk_type_filter=risk_type,
                persist_to_db=persist_to_db,
            )
            for r in p_risks:
                all_results.append(r)
                crops_evaluated_set.add((r.panchayat_id, r.crop_id))
                if r.status == "DETECTED":
                    detected_count += 1
                elif r.status == "NOT_DETECTED":
                    not_detected_count += 1
                else:
                    insufficient_count += 1

        return RiskEvaluationResponse(
            evaluation_run_id=run_id,
            block_id=block.id,
            block_name=block.name,
            evaluation_date=evaluation_date.isoformat(),
            total_panchayats=len(panchayats),
            total_crops_evaluated=len(crops_evaluated_set),
            total_risk_evaluations=len(all_results),
            detected_risks_count=detected_count,
            not_detected_count=not_detected_count,
            insufficient_data_count=insufficient_count,
            results=all_results,
            execution_timestamp=datetime.utcnow().isoformat(),
        )

    def get_panchayat_risk_profile(
        self,
        panchayat_id: int,
        evaluation_date: datetime,
    ) -> PanchayatRiskProfile:
        """
        Consolidates active risk assessment grouped by crop for a specific Panchayat.
        """
        panchayat = self.db.scalar(select(Panchayat).where(Panchayat.id == panchayat_id))
        if not panchayat:
            raise ValueError(f"Panchayat with ID {panchayat_id} not found in database.")

        block = panchayat.block or self.db.scalar(select(Block).where(Block.id == panchayat.block_id))
        block_name = block.name if block else None

        results = self.evaluate_panchayat_crop_risks(
            panchayat_id=panchayat_id,
            evaluation_date=evaluation_date,
            persist_to_db=False,
        )

        crop_risks: Dict[str, List[RiskResult]] = {}
        highest_severity = "NONE"
        detected_count = 0

        severity_rank = {"NONE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "EXTREME": 4}

        for r in results:
            if r.crop_name not in crop_risks:
                crop_risks[r.crop_name] = []
            crop_risks[r.crop_name].append(r)

            if r.status == "DETECTED":
                detected_count += 1
                if severity_rank.get(r.severity, 0) > severity_rank.get(highest_severity, 0):
                    highest_severity = r.severity

        return PanchayatRiskProfile(
            panchayat_id=panchayat.id,
            panchayat_name=panchayat.name,
            lgd_code=panchayat.lgd_code,
            block_id=panchayat.block_id,
            block_name=block_name,
            evaluation_date=evaluation_date.isoformat(),
            crop_risks=crop_risks,
            detected_risks_count=detected_count,
            highest_severity=highest_severity,
        )

    def get_subsystem_status(self) -> RiskSubsystemStatus:
        """
        Computes aggregate statistics of risk evaluations and logged records in the database.
        """
        total_records = self.db.scalar(select(func.count(AgriculturalRiskLog.id))) or 0
        detected = self.db.scalar(select(func.count(AgriculturalRiskLog.id)).where(AgriculturalRiskLog.status == "DETECTED")) or 0
        not_detected = self.db.scalar(select(func.count(AgriculturalRiskLog.id)).where(AgriculturalRiskLog.status == "NOT_DETECTED")) or 0
        insufficient = self.db.scalar(select(func.count(AgriculturalRiskLog.id)).where(AgriculturalRiskLog.status == "INSUFFICIENT_DATA")) or 0

        panchayats_count = self.db.scalar(select(func.count(func.distinct(AgriculturalRiskLog.panchayat_id)))) or 0
        crops_count = self.db.scalar(select(func.count(func.distinct(AgriculturalRiskLog.crop_id)))) or 0

        # Counts by risk type
        type_rows = self.db.execute(
            select(AgriculturalRiskLog.risk_type, func.count(AgriculturalRiskLog.id)).group_by(AgriculturalRiskLog.risk_type)
        ).all()
        risk_counts_by_type = {row[0]: row[1] for row in type_rows}

        # Counts by severity
        sev_rows = self.db.execute(
            select(AgriculturalRiskLog.severity, func.count(AgriculturalRiskLog.id)).group_by(AgriculturalRiskLog.severity)
        ).all()
        risk_counts_by_sev = {row[0]: row[1] for row in sev_rows}

        return RiskSubsystemStatus(
            total_risk_records=total_records,
            detected_risks=detected,
            not_detected_evaluations=not_detected,
            insufficient_data_evaluations=insufficient,
            risk_counts_by_type=risk_counts_by_type,
            risk_counts_by_severity=risk_counts_by_sev,
            panchayats_evaluated=panchayats_count,
            crops_evaluated=crops_count,
            active_rule_version=self.registry.RULE_VERSION,
        )

    def _persist_risk_result(
        self,
        risk_res: RiskResult,
        crop_context: PanchayatCropContextSummary,
        evaluation_date: datetime,
    ) -> int:
        """
        Idempotent upsert of risk evaluation into agricultural_risk_logs table.
        """
        source_model = "IMD-GFS"
        rule_version = risk_res.rule_version

        existing = self.db.scalar(
            select(AgriculturalRiskLog).where(
                and_(
                    AgriculturalRiskLog.panchayat_id == risk_res.panchayat_id,
                    AgriculturalRiskLog.crop_id == risk_res.crop_id,
                    AgriculturalRiskLog.risk_type == risk_res.risk_type,
                    AgriculturalRiskLog.evaluation_date == evaluation_date,
                    AgriculturalRiskLog.rule_version == rule_version,
                    AgriculturalRiskLog.source_model == source_model,
                )
            )
        )

        if existing:
            existing.crop_context_id = crop_context.id
            existing.panchayat_weather_id = crop_context.weather.panchayat_weather_id
            existing.stage_name = risk_res.stage_name
            existing.severity = risk_res.severity
            existing.status = risk_res.status
            existing.risk_score = risk_res.risk_score
            existing.observed_value = risk_res.observed_value
            existing.threshold_value = risk_res.threshold_value
            existing.unit = risk_res.unit
            existing.confidence = risk_res.confidence
            existing.evidence = risk_res.evidence.model_dump()
            existing.provenance = risk_res.provenance
            existing.updated_at = datetime.utcnow()
            self.db.flush()
            self.db.commit()
            return existing.id
        else:
            new_log = AgriculturalRiskLog(
                panchayat_id=risk_res.panchayat_id,
                block_id=risk_res.block_id,
                crop_id=risk_res.crop_id,
                crop_context_id=crop_context.id,
                panchayat_weather_id=crop_context.weather.panchayat_weather_id,
                advisory_id=None,
                crop_name=risk_res.crop_name,
                stage_name=risk_res.stage_name,
                risk_type=risk_res.risk_type,
                risk_category=risk_res.risk_category,
                severity=risk_res.severity,
                status=risk_res.status,
                risk_score=risk_res.risk_score,
                observed_value=risk_res.observed_value,
                threshold_value=risk_res.threshold_value,
                unit=risk_res.unit,
                duration_hours=risk_res.duration_hours,
                confidence=risk_res.confidence,
                rule_version=risk_res.rule_version,
                rule_source=risk_res.rule_source,
                title=f"{risk_res.crop_name} {risk_res.risk_type.replace('_', ' ').title()}",
                description=risk_res.evidence.condition_description,
                triggering_factor=f"{risk_res.observed_value} {risk_res.unit}" if risk_res.observed_value is not None else None,
                evaluation_date=evaluation_date,
                forecast_valid_time=evaluation_date,
                issue_time=datetime.utcnow(),
                source_model=source_model,
                evidence=risk_res.evidence.model_dump(),
                provenance=risk_res.provenance,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(new_log)
            self.db.flush()
            self.db.commit()
            return new_log.id
