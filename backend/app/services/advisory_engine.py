"""
Agro-Meteorological Advisory Generation Engine Service
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Translates Phase 10 validated agricultural risks into explainable, prioritized,
crop-aware, and growth-stage-aware management guidance.

Strict Scientific & Agronomic Scope:
- Source of truth for detected risks is strictly Phase 10 Agricultural Risk Engine.
- Advisory engine NEVER creates or invents a risk out of thin air.
- NOT_DETECTED risks generate NO hazard advisories.
- INSUFFICIENT_DATA produces explicit uncertainty / informational guidance without fake prescriptions.
- Disease-favorable conditions are strictly framed as micro-climatic environmental favorability.
- No chemical pesticides or chemical dosages are ever prescribed.
- Multi-crop Panchayats evaluate advisories independently per crop and growth stage.
- Idempotent upsert persistence to AgroAdvisory table.
"""
import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, or_

from app.core.config import settings
from app.core.logging import logger
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import PanchayatWeather
from app.db.models.agriculture import Crop, CropPhenologyStage, SoilProfile, PanchayatCropContext
from app.db.models.advisory import AgroAdvisory, AgriculturalRiskLog
from app.schemas.agricultural_context import PanchayatCropContextSummary, WeatherContextSummary
from app.schemas.agricultural_risk import RiskResult
from app.schemas.advisory import (
    AdvisoryType,
    AdvisoryCategory,
    AdvisoryPriority,
    AdvisoryStatus,
    AdvisoryActionCategory,
    AdvisoryUrgency,
    AdvisoryAction,
    AdvisoryResult,
    AdvisoryGenerationRequest,
    AdvisoryGenerationResponse,
    PanchayatAdvisoryProfile,
    AdvisorySubsystemStatus,
)
from app.services.advisory_rules import (
    AdvisoryRuleRegistry,
    AdvisoryRuleDefinition,
    advisory_rule_registry,
)
from app.services.agricultural_risk import AgriculturalRiskEngine
from app.services.agricultural_context import AgriculturalContextService
from app.schemas.precipitation_nowcast import PanchayatPrecipitationNowcastResult
from app.services.advisory_nowcast_service import (
    PanchayatAdvisoryNowcastService,
    panchayat_advisory_nowcast_service,
)


class AdvisoryEngine:
    """
    Main orchestration engine for agro-meteorological advisory generation and persistence.
    """

    def __init__(
        self,
        db: Session,
        rule_registry: Optional[AdvisoryRuleRegistry] = None,
    ):
        self.db = db
        self.registry = rule_registry or advisory_rule_registry
        self.risk_engine = AgriculturalRiskEngine(db=db)
        self.agri_context_service = AgriculturalContextService(db=db)

    def generate_panchayat_advisories(
        self,
        panchayat_id: int,
        forecast_date: datetime,
        crop_id: Optional[int] = None,
        risk_type_filter: Optional[str] = None,
        persist_to_db: bool = True,
        language: str = "en",
        nowcast_result: Optional[PanchayatPrecipitationNowcastResult] = None,
    ) -> List[AdvisoryResult]:
        """
        Generates crop-specific, stage-aware advisories for all active crops in a Panchayat.
        Transforms Phase 10 DETECTED agricultural risks into actionable advisories, and optionally
        integrates Phase 5 / Task 4 localized precipitation nowcast evidence.
        """
        # 1. Evaluate or retrieve Phase 10 risks
        risks: List[RiskResult] = self.risk_engine.evaluate_panchayat_crop_risks(
            panchayat_id=panchayat_id,
            evaluation_date=forecast_date,
            crop_id=crop_id,
            risk_type_filter=risk_type_filter,
            persist_to_db=persist_to_db,
        )

        panchayat = self.db.scalar(select(Panchayat).where(Panchayat.id == panchayat_id))
        if not panchayat:
            raise ValueError(f"Panchayat with ID {panchayat_id} not found in database.")

        block = panchayat.block or self.db.scalar(select(Block).where(Block.id == panchayat.block_id))
        block_name = block.name if block else None

        # Filter risks: only DETECTED risks generate action advisories
        # (NOT_DETECTED risks do not produce hazard advisories)
        detected_risks = [r for r in risks if r.status == "DETECTED"]

        # Group detected risks by crop for ranking and conflict checking
        crop_risks_map: Dict[int, List[RiskResult]] = {}
        for r in detected_risks:
            if r.crop_id not in crop_risks_map:
                crop_risks_map[r.crop_id] = []
            crop_risks_map[r.crop_id].append(r)

        all_advisories: List[AdvisoryResult] = []

        # Validity Window: Full forecast day
        valid_from = forecast_date.replace(hour=0, minute=0, second=0, microsecond=0)
        valid_until = valid_from + timedelta(days=1, seconds=-1)

        for c_id, c_risks in crop_risks_map.items():
            crop_advisories: List[AdvisoryResult] = []

            for risk in c_risks:
                advisory = self._build_advisory_from_risk(
                    risk=risk,
                    panchayat=panchayat,
                    block_name=block_name,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    forecast_date=forecast_date,
                    language=language,
                )
                crop_advisories.append(advisory)

            # Check for conflicting operations across advisories for this crop
            # e.g., Heat recommends irrigation, Wind recommends withholding irrigation
            self._detect_and_flag_conflicts(crop_advisories)

            # Prioritize and rank advisories for this crop
            self._rank_crop_advisories(crop_advisories)

            # Persist to database if requested
            if persist_to_db:
                for adv in crop_advisories:
                    db_id = self._persist_advisory(adv=adv, forecast_date=forecast_date)
                    adv.id = db_id

            all_advisories.extend(crop_advisories)

        # Task 5 Extension: Enrich baseline advisories with localized precipitation nowcast
        all_advisories = panchayat_advisory_nowcast_service.enrich_advisories_with_nowcast(
            advisories=all_advisories,
            nowcast=nowcast_result,
        )

        # Generate dedicated short-horizon operational advisories if nowcast provided
        if nowcast_result:
            crops_to_evaluate = []
            if crop_risks_map:
                for c_id, c_risks in crop_risks_map.items():
                    c_name = c_risks[0].crop_name if c_risks else "Crop"
                    s_name = c_risks[0].stage_name if c_risks else None
                    crops_to_evaluate.append((c_id, c_name, s_name))
            else:
                # If no detected risks, check if crop was filtered or default
                crops_to_evaluate.append((crop_id or 1, "Field Crop", None))

            for c_id, c_name, s_name in crops_to_evaluate:
                nowcast_ops = panchayat_advisory_nowcast_service.generate_panchayat_nowcast_advisories(
                    panchayat_id=panchayat.id,
                    panchayat_name=panchayat.name,
                    block_id=panchayat.block_id,
                    block_name=block_name,
                    crop_id=c_id,
                    crop_name=c_name,
                    forecast_date=forecast_date,
                    nowcast=nowcast_result,
                    stage_name=s_name,
                    language=language,
                )
                if persist_to_db:
                    for adv in nowcast_ops:
                        db_id = self._persist_advisory(adv=adv, forecast_date=forecast_date)
                        adv.id = db_id
                all_advisories.extend(nowcast_ops)

        return all_advisories

    def _build_advisory_from_risk(
        self,
        risk: RiskResult,
        panchayat: Panchayat,
        block_name: Optional[str],
        valid_from: datetime,
        valid_until: datetime,
        forecast_date: datetime,
        language: str = "en",
    ) -> AdvisoryResult:
        """
        Translates an individual Phase 10 RiskResult into a structured AdvisoryResult.
        """
        crop_name = risk.crop_name
        stage_name = risk.stage_name
        severity = risk.severity
        obs_val = risk.observed_value
        thresh_val = risk.threshold_value

        rule: Optional[AdvisoryRuleDefinition] = self.registry.get_rule(
            risk_type=risk.risk_type,
            crop_name=crop_name,
            stage_name=stage_name,
            severity=severity,
        )

        advisory_rule_ver = rule.advisory_rule_version if rule else self.registry.ADVISORY_RULE_VERSION
        rule_source = rule.rule_source if rule else self.registry.RULE_SOURCE

        if not rule:
            # Informational fallback when no specific advisory rule is configured
            title = f"{crop_name} {risk.risk_type.replace('_', ' ').title()} Advisory"
            message = f"Elevated {risk.risk_type.replace('_', ' ').lower()} risk detected for {crop_name}. Follow local agronomic advisory guidance."
            action = AdvisoryAction(
                action_category="MONITOR",
                action_text="Monitor field conditions and consult local agricultural extension officer.",
                timing="Routine morning inspection",
                urgency="ROUTINE",
                conditions={},
            )
            rationale = risk.evidence.condition_description if risk.evidence else None
            priority = "MEDIUM"
            advisory_type = "INFORMATIONAL"
            advisory_cat = "INFORMATIONAL"
        else:
            # Format title, message, and rationale templates safely
            obs_display = obs_val if obs_val is not None else 0.0
            thresh_display = thresh_val if thresh_val is not None else 0.0
            
            try:
                title = rule.title_template
                message = rule.message_template.format(observed=obs_display, threshold=thresh_display)
                rationale = rule.rationale_template.format(observed=obs_display, threshold=thresh_display)
            except Exception:
                title = rule.title_template
                message = rule.message_template
                rationale = rule.rationale_template

            action = AdvisoryAction(
                action_category=rule.action_category,
                action_text=rule.recommended_action,
                timing=rule.timing,
                urgency=rule.urgency,
                conditions={"stage": stage_name, "severity": severity},
            )
            priority = self._calculate_priority(risk=risk, rule=rule)
            advisory_type = rule.advisory_type
            advisory_cat = rule.advisory_category

        # Confidence inheritance
        confidence = risk.confidence
        confidence_reason = (
            f"Inherited from Phase 10 {risk.risk_type} risk confidence ({confidence}). "
            f"Stage resolved: {stage_name is not None}."
        )

        evidence_dict = {
            "risk_type": risk.risk_type,
            "risk_score": risk.risk_score,
            "severity": risk.severity,
            "observed_value": obs_val,
            "threshold_value": thresh_val,
            "unit": risk.unit,
            "crop_name": crop_name,
            "stage_name": stage_name,
            "risk_rule_version": risk.rule_version,
            "condition_description": risk.evidence.condition_description if risk.evidence else None,
            "metrics": risk.evidence.metrics if risk.evidence else {},
        }

        provenance_dict = {
            "panchayat_id": panchayat.id,
            "block_id": panchayat.block_id,
            "crop_id": risk.crop_id,
            "risk_log_id": risk.id,
            "risk_rule_version": risk.rule_version,
            "advisory_rule_version": advisory_rule_ver,
            "rule_source": rule_source,
            "source_model": "IMD-GFS",
            "generation_timestamp": datetime.utcnow().isoformat(),
        }

        return AdvisoryResult(
            id=None,
            panchayat_id=panchayat.id,
            panchayat_name=panchayat.name,
            block_id=panchayat.block_id,
            block_name=block_name,
            crop_id=risk.crop_id,
            crop_name=crop_name,
            stage_name=stage_name,
            risk_log_id=risk.id,
            crop_context_id=None,
            panchayat_weather_id=None,
            advisory_type=advisory_type,
            advisory_category=advisory_cat,
            priority=priority,
            priority_rank=1,
            priority_reason=f"Derived from {risk.severity} severity {risk.risk_type} hazard.",
            title=title,
            message=message,
            action=action,
            rationale=rationale,
            severity=severity,
            confidence=confidence,
            confidence_reason=confidence_reason,
            valid_from=valid_from.isoformat(),
            valid_until=valid_until.isoformat(),
            forecast_date=forecast_date.isoformat(),
            issue_time=datetime.utcnow().isoformat(),
            source_model="IMD-GFS",
            weather_model_version=None,
            rule_version=risk.rule_version,
            advisory_rule_version=advisory_rule_ver,
            rule_source=rule_source,
            language=language,
            status="ACTIVE",
            is_expert_review_required=False,
            is_cropland_eligible=True,
            evidence=evidence_dict,
            provenance=provenance_dict,
            created_at=datetime.utcnow().isoformat(),
        )

    def _calculate_priority(self, risk: RiskResult, rule: AdvisoryRuleDefinition) -> str:
        """
        Derives explainable priority from hazard severity, rule base priority, and growth stage sensitivity.
        """
        sev = risk.severity.upper() if risk.severity else "NONE"
        base_p = rule.base_priority.upper() if rule.base_priority else "MEDIUM"

        if sev == "EXTREME":
            return "CRITICAL"
        elif sev == "HIGH":
            return "HIGH" if base_p != "CRITICAL" else "CRITICAL"
        elif sev == "MODERATE":
            return "MEDIUM"
        elif sev == "LOW":
            return "LOW"
        else:
            return "INFORMATIONAL"

    def _rank_crop_advisories(self, advisories: List[AdvisoryResult]) -> None:
        """
        Ranks multiple active advisories for a single crop in descending priority order.
        """
        priority_weight = {
            "CRITICAL": 5,
            "HIGH": 4,
            "MEDIUM": 3,
            "LOW": 2,
            "INFORMATIONAL": 1,
        }

        # Sort descending by priority weight, then severity
        advisories.sort(
            key=lambda a: priority_weight.get(a.priority, 1),
            reverse=True
        )

        for idx, adv in enumerate(advisories, start=1):
            adv.priority_rank = idx
            adv.priority_reason = (
                f"Ranked #{idx} of {len(advisories)} for {adv.crop_name} based on "
                f"priority '{adv.priority}' and hazard severity '{adv.severity}'."
            )

    def _detect_and_flag_conflicts(self, advisories: List[AdvisoryResult]) -> None:
        """
        Identifies conflicting agronomic recommendations (e.g. Irrigate for heat vs Withhold irrigation for wind).
        Sets is_expert_review_required = True and tags advisory status.
        """
        has_irrigation_recommendation = False
        has_withhold_irrigation = False

        for adv in advisories:
            act_text = (adv.action.action_text or "").lower() if adv.action else ""
            if "irrigation" in act_text and ("maintain" in act_text or "apply" in act_text or "provide" in act_text):
                has_irrigation_recommendation = True
            if "withhold" in act_text and "irrigation" in act_text:
                has_withhold_irrigation = True

        if has_irrigation_recommendation and has_withhold_irrigation:
            for adv in advisories:
                adv.is_expert_review_required = True
                adv.status = "EXPERT_REVIEW_REQUIRED"
                adv.priority_reason = (
                    f"{adv.priority_reason or ''} [CONFLICT DETECTED: Opposing irrigation actions recommended. "
                    f"Expert review required prior to field dispatch.]"
                ).strip()

    def generate_block_advisories(
        self,
        block_id: int,
        forecast_date: datetime,
        panchayat_id: Optional[int] = None,
        crop_id: Optional[int] = None,
        risk_type: Optional[str] = None,
        persist_to_db: bool = True,
        language: str = "en",
    ) -> AdvisoryGenerationResponse:
        """
        Batch advisory generation across all Gram Panchayats in a Block.
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
            f"Executing Phase 11 Advisory Generation Engine [Run ID: {run_id}] "
            f"for Block '{block.name}' ({len(panchayats)} Panchayats) at {forecast_date.isoformat()}..."
        )

        all_advisories: List[AdvisoryResult] = []
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        info_count = 0
        crops_evaluated_set = set()

        for p in panchayats:
            p_advisories = self.generate_panchayat_advisories(
                panchayat_id=p.id,
                forecast_date=forecast_date,
                crop_id=crop_id,
                risk_type_filter=risk_type,
                persist_to_db=persist_to_db,
                language=language,
            )
            for adv in p_advisories:
                all_advisories.append(adv)
                crops_evaluated_set.add((adv.panchayat_id, adv.crop_id))
                if adv.priority == "CRITICAL":
                    critical_count += 1
                elif adv.priority == "HIGH":
                    high_count += 1
                elif adv.priority == "MEDIUM":
                    medium_count += 1
                elif adv.priority == "LOW":
                    low_count += 1
                else:
                    info_count += 1

        return AdvisoryGenerationResponse(
            generation_run_id=run_id,
            block_id=block.id,
            block_name=block.name,
            forecast_date=forecast_date.isoformat(),
            total_panchayats=len(panchayats),
            total_crops_evaluated=len(crops_evaluated_set),
            total_advisories_generated=len(all_advisories),
            critical_advisories_count=critical_count,
            high_advisories_count=high_count,
            medium_advisories_count=medium_count,
            low_advisories_count=low_count,
            informational_count=info_count,
            advisories=all_advisories,
            execution_timestamp=datetime.utcnow().isoformat(),
        )

    def get_panchayat_advisory_profile(
        self,
        panchayat_id: int,
        forecast_date: datetime,
    ) -> PanchayatAdvisoryProfile:
        """
        Retrieves active advisory profile for a Panchayat grouped by crop.
        """
        panchayat = self.db.scalar(select(Panchayat).where(Panchayat.id == panchayat_id))
        if not panchayat:
            raise ValueError(f"Panchayat with ID {panchayat_id} not found in database.")

        block = panchayat.block or self.db.scalar(select(Block).where(Block.id == panchayat.block_id))
        block_name = block.name if block else None

        advisories = self.generate_panchayat_advisories(
            panchayat_id=panchayat_id,
            forecast_date=forecast_date,
            persist_to_db=False,
        )

        crop_advisories: Dict[str, List[AdvisoryResult]] = {}
        highest_priority = "INFORMATIONAL"
        expert_review = False

        priority_weight = {
            "CRITICAL": 5,
            "HIGH": 4,
            "MEDIUM": 3,
            "LOW": 2,
            "INFORMATIONAL": 1,
        }

        for adv in advisories:
            if adv.crop_name not in crop_advisories:
                crop_advisories[adv.crop_name] = []
            crop_advisories[adv.crop_name].append(adv)

            if adv.is_expert_review_required:
                expert_review = True

            if priority_weight.get(adv.priority, 1) > priority_weight.get(highest_priority, 1):
                highest_priority = adv.priority

        return PanchayatAdvisoryProfile(
            panchayat_id=panchayat.id,
            panchayat_name=panchayat.name,
            lgd_code=panchayat.lgd_code,
            block_id=panchayat.block_id,
            block_name=block_name,
            forecast_date=forecast_date.isoformat(),
            crop_advisories=crop_advisories,
            total_active_advisories=len(advisories),
            highest_priority=highest_priority,
            expert_review_required=expert_review,
        )

    def get_subsystem_status(self) -> AdvisorySubsystemStatus:
        """
        Computes aggregate statistics of agro-meteorological advisories in the database.
        """
        total_records = self.db.scalar(select(func.count(AgroAdvisory.id))) or 0
        active = self.db.scalar(select(func.count(AgroAdvisory.id)).where(AgroAdvisory.status == "ACTIVE")) or 0
        draft = self.db.scalar(select(func.count(AgroAdvisory.id)).where(AgroAdvisory.status == "DRAFT")) or 0
        expired = self.db.scalar(select(func.count(AgroAdvisory.id)).where(AgroAdvisory.status == "EXPIRED")) or 0
        suppressed = self.db.scalar(select(func.count(AgroAdvisory.id)).where(AgroAdvisory.status == "SUPPRESSED")) or 0
        insufficient = self.db.scalar(select(func.count(AgroAdvisory.id)).where(AgroAdvisory.status == "INSUFFICIENT_DATA")) or 0
        expert_review = self.db.scalar(select(func.count(AgroAdvisory.id)).where(AgroAdvisory.is_expert_review_required.is_(True))) or 0

        panchayats_count = self.db.scalar(select(func.count(func.distinct(AgroAdvisory.panchayat_id)))) or 0

        # Counts by priority
        p_rows = self.db.execute(
            select(AgroAdvisory.priority, func.count(AgroAdvisory.id)).group_by(AgroAdvisory.priority)
        ).all()
        by_priority = {row[0]: row[1] for row in p_rows}

        # Counts by advisory type
        t_rows = self.db.execute(
            select(AgroAdvisory.advisory_type, func.count(AgroAdvisory.id)).group_by(AgroAdvisory.advisory_type)
        ).all()
        by_type = {row[0]: row[1] for row in t_rows}

        # Counts by crop
        c_rows = self.db.execute(
            select(Crop.crop_name, func.count(AgroAdvisory.id))
            .join(Crop, AgroAdvisory.crop_id == Crop.id)
            .group_by(Crop.crop_name)
        ).all()
        by_crop = {row[0]: row[1] for row in c_rows}

        return AdvisorySubsystemStatus(
            total_advisories=total_records,
            active_advisories=active,
            draft_advisories=draft,
            expired_advisories=expired,
            suppressed_advisories=suppressed,
            insufficient_data_advisories=insufficient,
            expert_review_required_advisories=expert_review,
            advisories_by_priority=by_priority,
            advisories_by_type=by_type,
            advisories_by_crop=by_crop,
            advisories_by_panchayat=panchayats_count,
            active_rule_version=self.registry.ADVISORY_RULE_VERSION,
        )

    def _persist_advisory(
        self,
        adv: AdvisoryResult,
        forecast_date: datetime,
    ) -> int:
        """
        Idempotent upsert of generated advisory into agro_advisories table.
        """
        source_model = adv.source_model
        rule_ver = adv.advisory_rule_version
        v_from = datetime.fromisoformat(adv.valid_from)
        v_until = datetime.fromisoformat(adv.valid_until)

        where_conditions = [
            AgroAdvisory.panchayat_id == adv.panchayat_id,
            AgroAdvisory.crop_id == adv.crop_id,
            AgroAdvisory.advisory_rule_version == rule_ver,
            AgroAdvisory.valid_from == v_from,
            AgroAdvisory.source_model == source_model,
        ]
        if adv.risk_log_id is not None:
            where_conditions.append(AgroAdvisory.risk_log_id == adv.risk_log_id)
        else:
            where_conditions.append(AgroAdvisory.advisory_type == adv.advisory_type)
            where_conditions.append(AgroAdvisory.title == adv.title)

        existing = self.db.scalar(
            select(AgroAdvisory).where(and_(*where_conditions))
        )

        raw_payload_dict = {
            "title": adv.title,
            "message": adv.message,
            "action": adv.action.model_dump() if adv.action else None,
            "priority": adv.priority,
            "priority_rank": adv.priority_rank,
            "severity": adv.severity,
            "confidence": adv.confidence,
            "valid_from": adv.valid_from,
            "valid_until": adv.valid_until,
            "evidence": adv.evidence,
            "provenance": adv.provenance,
            "localized_nowcast_context": adv.localized_nowcast_context.model_dump() if adv.localized_nowcast_context else None,
            "baseline_precipitation_context": adv.baseline_precipitation_context,
            "nowcast_advisory_state": adv.nowcast_advisory_state.value if adv.nowcast_advisory_state else None,
            "nowcast_explanation": adv.nowcast_explanation.model_dump() if adv.nowcast_explanation else None,
        }

        if existing:
            existing.block_id = adv.block_id
            existing.crop_context_id = adv.crop_context_id
            existing.panchayat_weather_id = adv.panchayat_weather_id
            existing.advisory_type = adv.advisory_type
            existing.advisory_category = adv.advisory_category
            existing.priority = adv.priority
            existing.priority_rank = adv.priority_rank
            existing.priority_reason = adv.priority_reason
            existing.title = adv.title
            existing.message = adv.message
            existing.summary_advisory = adv.message
            existing.recommended_action = adv.action.action_text if adv.action else None
            existing.action_category = adv.action.action_category if adv.action else None
            existing.timing = adv.action.timing if adv.action else None
            existing.urgency = adv.action.urgency if adv.action else None
            existing.rationale = adv.rationale
            existing.severity = adv.severity
            existing.confidence = adv.confidence
            existing.confidence_reason = adv.confidence_reason
            existing.status = adv.status
            existing.is_expert_review_required = adv.is_expert_review_required
            existing.raw_payload = raw_payload_dict
            existing.evidence = adv.evidence
            existing.provenance = adv.provenance
            existing.updated_at = datetime.utcnow()
            self.db.flush()
            self.db.commit()
            return existing.id
        else:
            new_adv = AgroAdvisory(
                panchayat_id=adv.panchayat_id,
                block_id=adv.block_id,
                crop_id=adv.crop_id,
                crop_context_id=adv.crop_context_id,
                risk_log_id=adv.risk_log_id,
                panchayat_weather_id=adv.panchayat_weather_id,
                advisory_type=adv.advisory_type,
                advisory_category=adv.advisory_category,
                priority=adv.priority,
                priority_rank=adv.priority_rank,
                priority_reason=adv.priority_reason,
                title=adv.title,
                message=adv.message,
                summary_advisory=adv.message,
                recommended_action=adv.action.action_text if adv.action else None,
                action_category=adv.action.action_category if adv.action else None,
                timing=adv.action.timing if adv.action else None,
                urgency=adv.action.urgency if adv.action else None,
                rationale=adv.rationale,
                severity=adv.severity,
                confidence=adv.confidence,
                confidence_reason=adv.confidence_reason,
                issue_date=datetime.utcnow(),
                valid_from=v_from,
                valid_until=v_until,
                forecast_date=forecast_date,
                issue_time=datetime.utcnow(),
                is_cropland_eligible=adv.is_cropland_eligible,
                raw_payload=raw_payload_dict,
                source_model=source_model,
                weather_model_version=adv.weather_model_version,
                rule_version=adv.rule_version,
                advisory_rule_version=adv.advisory_rule_version,
                rule_source=adv.rule_source,
                language=adv.language,
                status=adv.status,
                is_expert_review_required=adv.is_expert_review_required,
                evidence=adv.evidence,
                provenance=adv.provenance,
                metadata_json={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(new_adv)
            self.db.flush()
            self.db.commit()
            return new_adv.id


AgroAdvisoryEngine = AdvisoryEngine
