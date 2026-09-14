"""
Panchayat Agricultural Context Service
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Assembles agricultural context snapshots:
Panchayat Weather + Crop Mapping + Crop Phenology Stage + Soil Profile + Cropland Eligibility.

Provides strict data integrity:
- Multi-crop Panchayat handling (separate context snapshots per crop)
- Deterministic stage resolution (Observed -> Planting Date -> Crop Calendar -> Unknown)
- Soil profile evaluation preserving NULLs (never substituting 0 for missing values)
- Cropland restriction via LandUseMask
- Idempotent upsert persistence
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
from app.db.models.agriculture import (
    Crop,
    CropPhenologyStage,
    SoilProfile,
    PanchayatCropMapping,
    PanchayatCropContext,
)
from app.schemas.agricultural_context import (
    CropStageContext,
    SoilContextSummary,
    WeatherContextSummary,
    PanchayatCropContextSummary,
    AgriculturalContextRequest,
    AgriculturalContextResponse,
    PanchayatAgriculturalProfile,
    AgricultureSubsystemStatus,
)


class AgriculturalContextService:
    """
    Service layer for constructing and querying Gram Panchayat Agricultural Context.
    """

    SERVICE_VERSION: str = "v1.0.0"
    DEFAULT_SOURCE: str = "AGRI_CONTEXT_ENGINE"

    def __init__(self, db: Session):
        self.db = db

    def resolve_crop_stage(
        self,
        crop: Crop,
        mapping: Optional[PanchayatCropMapping],
        context_date: datetime,
    ) -> Tuple[CropStageContext, List[str]]:
        """
        Resolves the phenological growth stage of a crop for a given context date.

        Hierarchy:
        1. Explicit observed stage in mapping.current_stage (OBSERVED).
        2. Sowing/Planting date calculation mapped against crop stage day ranges (PLANTING_DATE).
        3. Seasonal crop calendar defaults (CROP_CALENDAR).
        4. Fallback: UNKNOWN.
        """
        quality_flags: List[str] = []
        target_date = context_date.date() if isinstance(context_date, datetime) else context_date

        # Priority 1: Explicit observed stage
        if mapping and mapping.current_stage_id:
            stage = mapping.current_stage or self.db.scalar(
                select(CropPhenologyStage).where(CropPhenologyStage.id == mapping.current_stage_id)
            )
            if stage:
                days_since_planting = None
                if mapping.sowing_date:
                    days_since_planting = (target_date - mapping.sowing_date).days

                return (
                    CropStageContext(
                        phenology_stage_id=stage.id,
                        stage_name=stage.stage_name,
                        stage_order=stage.stage_order,
                        gdd_required=stage.gdd_required,
                        water_sensitivity=stage.water_sensitivity,
                        temp_sensitivity=stage.temp_sensitivity,
                        stage_derivation_method="OBSERVED",
                        planting_date=mapping.sowing_date.isoformat() if mapping.sowing_date else None,
                        days_since_planting=days_since_planting,
                        expected_harvest_date=mapping.expected_harvest_date.isoformat() if mapping.expected_harvest_date else None,
                        is_stage_resolved=True,
                    ),
                    quality_flags,
                )

        # Priority 2: Planting-date-based calculation
        if mapping and mapping.sowing_date:
            days_since_planting = (target_date - mapping.sowing_date).days

            # Validation: date before planting
            if days_since_planting < 0:
                quality_flags.append("DATE_BEFORE_PLANTING")
                return (
                    CropStageContext(
                        phenology_stage_id=None,
                        stage_name=None,
                        stage_order=None,
                        gdd_required=None,
                        water_sensitivity=None,
                        temp_sensitivity=None,
                        stage_derivation_method="UNKNOWN",
                        planting_date=mapping.sowing_date.isoformat(),
                        days_since_planting=days_since_planting,
                        expected_harvest_date=mapping.expected_harvest_date.isoformat() if mapping.expected_harvest_date else None,
                        is_stage_resolved=False,
                    ),
                    quality_flags,
                )

            # Retrieve stages ordered by stage_order
            stages = self.db.scalars(
                select(CropPhenologyStage)
                .where(CropPhenologyStage.crop_id == crop.id)
                .order_by(CropPhenologyStage.stage_order.asc())
            ).all()

            if stages:
                # Calculate cumulative day intervals
                # Base heuristic: stage days derived from GDD (approx. 15 GDD/day, min 10 days)
                cumulative_days = 0
                matched_stage: Optional[CropPhenologyStage] = None

                for stg in stages:
                    stage_duration = max(10, round(stg.gdd_required / 15.0))
                    start_day = cumulative_days
                    end_day = cumulative_days + stage_duration
                    cumulative_days = end_day

                    if start_day <= days_since_planting <= end_day:
                        matched_stage = stg
                        break

                if matched_stage:
                    return (
                        CropStageContext(
                            phenology_stage_id=matched_stage.id,
                            stage_name=matched_stage.stage_name,
                            stage_order=matched_stage.stage_order,
                            gdd_required=matched_stage.gdd_required,
                            water_sensitivity=matched_stage.water_sensitivity,
                            temp_sensitivity=matched_stage.temp_sensitivity,
                            stage_derivation_method="PLANTING_DATE",
                            planting_date=mapping.sowing_date.isoformat(),
                            days_since_planting=days_since_planting,
                            expected_harvest_date=mapping.expected_harvest_date.isoformat() if mapping.expected_harvest_date else None,
                            is_stage_resolved=True,
                        ),
                        quality_flags,
                    )
                else:
                    # Days beyond final stage
                    quality_flags.append("BEYOND_FINAL_STAGE")
                    last_stage = stages[-1]
                    return (
                        CropStageContext(
                            phenology_stage_id=last_stage.id,
                            stage_name=last_stage.stage_name,
                            stage_order=last_stage.stage_order,
                            gdd_required=last_stage.gdd_required,
                            water_sensitivity=last_stage.water_sensitivity,
                            temp_sensitivity=last_stage.temp_sensitivity,
                            stage_derivation_method="PLANTING_DATE",
                            planting_date=mapping.sowing_date.isoformat(),
                            days_since_planting=days_since_planting,
                            expected_harvest_date=mapping.expected_harvest_date.isoformat() if mapping.expected_harvest_date else None,
                            is_stage_resolved=True,
                        ),
                        quality_flags,
                    )

        # Priority 3: Crop calendar seasonal defaults
        season = (mapping.season if mapping and mapping.season else crop.season) or ""
        month = target_date.month

        stages = self.db.scalars(
            select(CropPhenologyStage)
            .where(CropPhenologyStage.crop_id == crop.id)
            .order_by(CropPhenologyStage.stage_order.asc())
        ).all()

        if stages and season:
            # Map month to approximate stage for standard Indian seasons
            # Kharif (June-Nov: 6-11): 6-7 Sowing/Veg, 8-9 Flowering, 10-11 Maturity/Harvest
            # Rabi (Oct-April: 10-4): 10-11 Sowing/Veg, 12-1 Flowering, 2-3 Maturity/Harvest
            stage_idx = 0
            if "kharif" in season.lower():
                if month in [6, 7]:
                    stage_idx = min(1, len(stages) - 1)
                elif month in [8, 9]:
                    stage_idx = min(2, len(stages) - 1)
                elif month in [10, 11]:
                    stage_idx = min(len(stages) - 1, max(3, len(stages) - 1))
                else:
                    stage_idx = 0
            elif "rabi" in season.lower():
                if month in [10, 11]:
                    stage_idx = min(1, len(stages) - 1)
                elif month in [12, 1]:
                    stage_idx = min(2, len(stages) - 1)
                elif month in [2, 3, 4]:
                    stage_idx = min(len(stages) - 1, max(3, len(stages) - 1))
                else:
                    stage_idx = 0

            cal_stage = stages[stage_idx]
            quality_flags.append("CALENDAR_INFERRED_STAGE")
            return (
                CropStageContext(
                    phenology_stage_id=cal_stage.id,
                    stage_name=cal_stage.stage_name,
                    stage_order=cal_stage.stage_order,
                    gdd_required=cal_stage.gdd_required,
                    water_sensitivity=cal_stage.water_sensitivity,
                    temp_sensitivity=cal_stage.temp_sensitivity,
                    stage_derivation_method="CROP_CALENDAR",
                    planting_date=mapping.sowing_date.isoformat() if mapping and mapping.sowing_date else None,
                    days_since_planting=None,
                    expected_harvest_date=mapping.expected_harvest_date.isoformat() if mapping and mapping.expected_harvest_date else None,
                    is_stage_resolved=True,
                ),
                quality_flags,
            )

        # Fallback: UNKNOWN
        quality_flags.append("UNRESOLVED_STAGE")
        return (
            CropStageContext(
                phenology_stage_id=None,
                stage_name=None,
                stage_order=None,
                gdd_required=None,
                water_sensitivity=None,
                temp_sensitivity=None,
                stage_derivation_method="UNKNOWN",
                planting_date=None,
                days_since_planting=None,
                expected_harvest_date=None,
                is_stage_resolved=False,
            ),
            quality_flags,
        )

    def evaluate_soil_profile(
        self,
        soil: Optional[SoilProfile]
    ) -> Tuple[SoilContextSummary, List[str]]:
        """
        Evaluates soil profile data completeness and quality without fabricating missing values.
        """
        quality_flags: List[str] = []
        if soil is None:
            return (
                SoilContextSummary(
                    soil_profile_id=None,
                    soil_type=None,
                    texture=None,
                    drainage_class=None,
                    water_holding_capacity_pct=None,
                    ph_level=None,
                    organic_carbon_pct=None,
                    available_nitrogen_kg_ha=None,
                    available_phosphorus_kg_ha=None,
                    available_potassium_kg_ha=None,
                    soil_available=False,
                    soil_status="UNAVAILABLE",
                ),
                ["MISSING_SOIL_PROFILE"],
            )

        # Quality validations
        if soil.ph_level is not None and not (0.0 <= soil.ph_level <= 14.0):
            quality_flags.append("SUSPICIOUS_SOIL_PH")
        if soil.water_holding_capacity_pct is not None and not (0.0 <= soil.water_holding_capacity_pct <= 100.0):
            quality_flags.append("SUSPICIOUS_SOIL_WATER_CAPACITY")
        if soil.organic_carbon_pct is not None and not (0.0 <= soil.organic_carbon_pct <= 100.0):
            quality_flags.append("SUSPICIOUS_SOIL_ORGANIC_CARBON")

        # Completeness evaluation
        core_fields = [
            soil.soil_type,
            soil.drainage_class,
            soil.water_holding_capacity_pct,
            soil.ph_level,
            soil.organic_carbon_pct,
        ]
        present_count = sum(1 for f in core_fields if f is not None)

        if present_count == len(core_fields):
            soil_status = "COMPLETE"
        elif present_count > 0:
            soil_status = "PARTIAL"
            quality_flags.append("PARTIAL_SOIL_DATA")
        else:
            soil_status = "UNAVAILABLE"
            quality_flags.append("UNAVAILABLE_SOIL_DATA")

        return (
            SoilContextSummary(
                soil_profile_id=soil.id,
                soil_type=soil.soil_type,
                texture=soil.texture,
                drainage_class=soil.drainage_class,
                water_holding_capacity_pct=soil.water_holding_capacity_pct,
                ph_level=soil.ph_level,
                organic_carbon_pct=soil.organic_carbon_pct,
                available_nitrogen_kg_ha=soil.available_nitrogen_kg_ha,
                available_phosphorus_kg_ha=soil.available_phosphorus_kg_ha,
                available_potassium_kg_ha=soil.available_potassium_kg_ha,
                soil_available=True,
                soil_status=soil_status,
            ),
            quality_flags,
        )

    def get_panchayat_weather_context(
        self,
        panchayat_id: int,
        context_date: datetime,
        source_model: str = "IMD-GFS",
        model_version: Optional[str] = None,
    ) -> Tuple[WeatherContextSummary, Optional[PanchayatWeather], List[str]]:
        """
        Retrieves Phase 8 PanchayatWeather record for target forecast date.
        """
        quality_flags: List[str] = []
        target_model_version = model_version or settings.TEMPERATURE_MODEL_VERSION

        # Date window query (same calendar day)
        target_day = context_date.date() if isinstance(context_date, datetime) else context_date

        stmt = select(PanchayatWeather).where(
            and_(
                PanchayatWeather.panchayat_id == panchayat_id,
                func.date(PanchayatWeather.forecast_date) == target_day,
                PanchayatWeather.source_model == source_model,
            )
        )
        if model_version:
            stmt = stmt.where(PanchayatWeather.model_version == model_version)

        weather_record = self.db.scalars(stmt.order_by(PanchayatWeather.forecast_date.desc())).first()

        if weather_record is None:
            quality_flags.append("MISSING_PANCHAYAT_WEATHER")
            return (
                WeatherContextSummary(
                    panchayat_weather_id=None,
                    forecast_valid_time=None,
                    mean_temp_c=None,
                    min_temp_c=None,
                    max_temp_c=None,
                    temp_stddev_c=None,
                    weather_status="UNAVAILABLE",
                ),
                None,
                quality_flags,
            )

        weather_status = weather_record.quality_status or "COMPLETE"
        if weather_status != "COMPLETE":
            quality_flags.append(f"WEATHER_{weather_status}")

        return (
            WeatherContextSummary(
                panchayat_weather_id=weather_record.id,
                forecast_valid_time=weather_record.forecast_date.isoformat(),
                mean_temp_c=weather_record.mean_temp_c,
                min_temp_c=weather_record.min_temp_c,
                max_temp_c=weather_record.max_temp_c,
                temp_stddev_c=weather_record.temp_stddev_c,
                weather_status=weather_status,
            ),
            weather_record,
            quality_flags,
        )

    def build_panchayat_crop_context(
        self,
        panchayat_id: int,
        context_date: datetime,
        source_model: str = "IMD-GFS",
        model_version: Optional[str] = None,
        persist_to_db: bool = True,
    ) -> List[PanchayatCropContextSummary]:
        """
        Builds normalized agricultural context snapshots for all active crops in a Panchayat.
        Supports multi-crop Panchayats with distinct context snapshots per crop.
        """
        # 1. Retrieve Panchayat and parent Block
        panchayat = self.db.scalar(select(Panchayat).where(Panchayat.id == panchayat_id))
        if not panchayat:
            raise ValueError(f"Panchayat with ID {panchayat_id} not found in database.")

        block = panchayat.block or self.db.scalar(select(Block).where(Block.id == panchayat.block_id))
        block_name = block.name if block else None

        # 2. Retrieve LandUseMask & Agricultural Eligibility
        land_use = self.db.scalar(select(LandUseMask).where(LandUseMask.panchayat_id == panchayat_id))
        is_agri_eligible = True
        agricultural_area_ha = None

        if land_use:
            is_agri_eligible = land_use.is_agricultural_eligible and (land_use.cropland_area_ha > 0)
            agricultural_area_ha = land_use.cropland_area_ha
        else:
            is_agri_eligible = True

        # 3. Retrieve Panchayat Weather Context
        weather_summary, weather_record, weather_flags = self.get_panchayat_weather_context(
            panchayat_id=panchayat_id,
            context_date=context_date,
            source_model=source_model,
            model_version=model_version,
        )

        # 4. Retrieve Active Crop Mappings for this Panchayat
        crop_mappings = self.db.scalars(
            select(PanchayatCropMapping)
            .where(
                and_(
                    PanchayatCropMapping.panchayat_id == panchayat_id,
                    PanchayatCropMapping.is_active == True,
                )
            )
        ).all()

        results: List[PanchayatCropContextSummary] = []

        # If NO active crop mappings exist: record UNAVAILABLE context without fabricating data
        if not crop_mappings:
            flags = list(weather_flags)
            flags.append("NO_ACTIVE_CROP_MAPPING")
            if not is_agri_eligible:
                flags.append("NON_AGRICULTURAL_PANCHAYAT")

            empty_stage = CropStageContext(
                phenology_stage_id=None,
                stage_name=None,
                stage_order=None,
                gdd_required=None,
                water_sensitivity=None,
                temp_sensitivity=None,
                stage_derivation_method="UNKNOWN",
                planting_date=None,
                days_since_planting=None,
                expected_harvest_date=None,
                is_stage_resolved=False,
            )
            empty_soil = SoilContextSummary(
                soil_profile_id=None,
                soil_type=None,
                texture=None,
                drainage_class=None,
                water_holding_capacity_pct=None,
                ph_level=None,
                organic_carbon_pct=None,
                available_nitrogen_kg_ha=None,
                available_phosphorus_kg_ha=None,
                available_potassium_kg_ha=None,
                soil_available=False,
                soil_status="UNAVAILABLE",
            )

            summary = PanchayatCropContextSummary(
                id=None,
                panchayat_id=panchayat.id,
                panchayat_name=panchayat.name,
                block_id=panchayat.block_id,
                block_name=block_name,
                crop_id=0,
                crop_name="UNAVAILABLE",
                scientific_name=None,
                season=None,
                crop_stage=empty_stage,
                soil=empty_soil,
                weather=weather_summary,
                crop_area_ha=None,
                agricultural_area_ha=agricultural_area_ha,
                crop_fraction=None,
                is_agricultural_eligible=is_agri_eligible,
                context_date=context_date.isoformat(),
                source=self.DEFAULT_SOURCE,
                source_version=self.SERVICE_VERSION,
                confidence_score=0.0,
                status="UNAVAILABLE",
                quality_flags=flags,
                provenance={
                    "panchayat_id": panchayat.id,
                    "block_id": panchayat.block_id,
                    "reason": "No active crop mapping found for Panchayat",
                    "generation_timestamp": datetime.utcnow().isoformat(),
                },
                created_at=datetime.utcnow().isoformat(),
            )
            return [summary]

        # Multi-Crop Processing: iterate over each mapped crop
        for mapping in crop_mappings:
            crop = mapping.crop or self.db.scalar(select(Crop).where(Crop.id == mapping.crop_id))
            if not crop:
                continue

            flags = list(weather_flags)

            # Crop stage resolution
            stage_ctx, stage_flags = self.resolve_crop_stage(crop=crop, mapping=mapping, context_date=context_date)
            flags.extend(stage_flags)

            # Soil profile evaluation
            soil_obj = mapping.soil
            if soil_obj is None and mapping.soil_id is not None:
                soil_obj = self.db.scalar(select(SoilProfile).where(SoilProfile.id == mapping.soil_id))
            soil_ctx, soil_flags = self.evaluate_soil_profile(soil=soil_obj)
            flags.extend(soil_flags)

            # Crop area validation
            crop_area_ha = mapping.crop_area_ha
            crop_fraction = None

            if crop_area_ha is not None:
                if crop_area_ha < 0:
                    flags.append("NEGATIVE_CROP_AREA")
                elif agricultural_area_ha is not None and agricultural_area_ha > 0:
                    crop_fraction = min(1.0, crop_area_ha / agricultural_area_ha)
                    if crop_area_ha > agricultural_area_ha:
                        flags.append("CROP_AREA_EXCEEDS_AGRICULTURAL_AREA")

            # Date validations
            if mapping.sowing_date and mapping.expected_harvest_date:
                if mapping.sowing_date > mapping.expected_harvest_date:
                    flags.append("PLANTING_AFTER_HARVEST_DATE")

            # Overall status determination
            # COMPLETE: crop mapped + stage resolved + soil complete + weather complete + agri eligible
            # PARTIAL: crop mapped, but some elements incomplete or partial
            # UNAVAILABLE: no valid mapping
            is_complete = (
                stage_ctx.is_stage_resolved
                and soil_ctx.soil_status == "COMPLETE"
                and weather_summary.weather_status == "COMPLETE"
                and is_agri_eligible
            )

            if is_complete:
                overall_status = "COMPLETE"
                confidence = 1.0
            else:
                overall_status = "PARTIAL"
                confidence = 0.75 if (stage_ctx.is_stage_resolved or soil_ctx.soil_available) else 0.5

            if not is_agri_eligible:
                flags.append("NON_AGRICULTURAL_PANCHAYAT")

            # Provenance metadata
            provenance = {
                "panchayat_id": panchayat.id,
                "block_id": panchayat.block_id,
                "crop_id": crop.id,
                "crop_mapping_source": mapping.source,
                "phenology_source": stage_ctx.stage_derivation_method,
                "planting_date_source": "PanchayatCropMapping" if mapping.sowing_date else None,
                "soil_profile_source": "SoilProfile" if soil_ctx.soil_available else None,
                "weather_forecast_date": weather_summary.forecast_valid_time,
                "weather_source_model": source_model,
                "weather_model_version": weather_record.model_version if weather_record else model_version,
                "feature_schema_version": weather_record.feature_schema_version if weather_record else None,
                "land_use_source": "LandUseMask" if land_use else None,
                "generation_timestamp": datetime.utcnow().isoformat(),
                "service_version": self.SERVICE_VERSION,
            }

            db_record_id = None

            # Persist to database if requested
            if persist_to_db:
                # Idempotent lookup
                existing = self.db.scalar(
                    select(PanchayatCropContext).where(
                        and_(
                            PanchayatCropContext.panchayat_id == panchayat.id,
                            PanchayatCropContext.crop_id == crop.id,
                            PanchayatCropContext.context_date == context_date,
                            PanchayatCropContext.source == self.DEFAULT_SOURCE,
                        )
                    )
                )

                sowing_d = mapping.sowing_date
                harvest_d = mapping.expected_harvest_date

                if existing:
                    existing.block_id = panchayat.block_id
                    existing.crop_name = crop.crop_name
                    existing.phenology_stage_id = stage_ctx.phenology_stage_id
                    existing.stage_name = stage_ctx.stage_name
                    existing.stage_order = stage_ctx.stage_order
                    existing.stage_derivation_method = stage_ctx.stage_derivation_method
                    existing.planting_date = sowing_d
                    existing.days_since_planting = stage_ctx.days_since_planting
                    existing.expected_harvest_date = harvest_d
                    existing.soil_profile_id = soil_ctx.soil_profile_id
                    existing.soil_type = soil_ctx.soil_type
                    existing.soil_available = soil_ctx.soil_available
                    existing.soil_status = soil_ctx.soil_status
                    existing.panchayat_weather_id = weather_summary.panchayat_weather_id
                    existing.mean_temp_c = weather_summary.mean_temp_c
                    existing.min_temp_c = weather_summary.min_temp_c
                    existing.max_temp_c = weather_summary.max_temp_c
                    existing.temp_stddev_c = weather_summary.temp_stddev_c
                    existing.weather_status = weather_summary.weather_status
                    existing.crop_area_ha = crop_area_ha
                    existing.agricultural_area_ha = agricultural_area_ha
                    existing.crop_fraction = crop_fraction
                    existing.is_agricultural_eligible = is_agri_eligible
                    existing.confidence_score = confidence
                    existing.status = overall_status
                    existing.quality_flags = flags
                    existing.provenance = provenance
                    existing.updated_at = datetime.utcnow()
                    self.db.flush()
                    db_record_id = existing.id
                else:
                    new_ctx = PanchayatCropContext(
                        panchayat_id=panchayat.id,
                        block_id=panchayat.block_id,
                        crop_id=crop.id,
                        crop_name=crop.crop_name,
                        phenology_stage_id=stage_ctx.phenology_stage_id,
                        stage_name=stage_ctx.stage_name,
                        stage_order=stage_ctx.stage_order,
                        stage_derivation_method=stage_ctx.stage_derivation_method,
                        planting_date=sowing_d,
                        days_since_planting=stage_ctx.days_since_planting,
                        expected_harvest_date=harvest_d,
                        soil_profile_id=soil_ctx.soil_profile_id,
                        soil_type=soil_ctx.soil_type,
                        soil_available=soil_ctx.soil_available,
                        soil_status=soil_ctx.soil_status,
                        panchayat_weather_id=weather_summary.panchayat_weather_id,
                        mean_temp_c=weather_summary.mean_temp_c,
                        min_temp_c=weather_summary.min_temp_c,
                        max_temp_c=weather_summary.max_temp_c,
                        temp_stddev_c=weather_summary.temp_stddev_c,
                        weather_status=weather_summary.weather_status,
                        crop_area_ha=crop_area_ha,
                        agricultural_area_ha=agricultural_area_ha,
                        crop_fraction=crop_fraction,
                        is_agricultural_eligible=is_agri_eligible,
                        context_date=context_date,
                        source=self.DEFAULT_SOURCE,
                        source_version=self.SERVICE_VERSION,
                        confidence_score=confidence,
                        status=overall_status,
                        quality_flags=flags,
                        provenance=provenance,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    self.db.add(new_ctx)
                    self.db.flush()
                    db_record_id = new_ctx.id

                self.db.commit()

            summary = PanchayatCropContextSummary(
                id=db_record_id,
                panchayat_id=panchayat.id,
                panchayat_name=panchayat.name,
                block_id=panchayat.block_id,
                block_name=block_name,
                crop_id=crop.id,
                crop_name=crop.crop_name,
                scientific_name=crop.scientific_name,
                season=crop.season,
                crop_stage=stage_ctx,
                soil=soil_ctx,
                weather=weather_summary,
                crop_area_ha=crop_area_ha,
                agricultural_area_ha=agricultural_area_ha,
                crop_fraction=crop_fraction,
                is_agricultural_eligible=is_agri_eligible,
                context_date=context_date.isoformat(),
                source=self.DEFAULT_SOURCE,
                source_version=self.SERVICE_VERSION,
                confidence_score=confidence,
                status=overall_status,
                quality_flags=flags,
                provenance=provenance,
                created_at=datetime.utcnow().isoformat(),
            )
            results.append(summary)

        return results

    def build_block_agricultural_context(
        self,
        block_id: int,
        context_date: datetime,
        source_model: str = "IMD-GFS",
        model_version: Optional[str] = None,
        panchayat_id: Optional[int] = None,
        persist_to_db: bool = True,
    ) -> AgriculturalContextResponse:
        """
        Processes and aggregates agricultural context for all (or single) Panchayats in a Block.
        """
        context_run_id = str(uuid.uuid4())

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
            f"Building Phase 9 Agricultural Context [Run ID: {context_run_id}] "
            f"for Block '{block.name}' ({len(panchayats)} Panchayats) at {context_date.isoformat()}..."
        )

        all_contexts: List[PanchayatCropContextSummary] = []
        complete_count = 0
        partial_count = 0
        unavailable_count = 0

        for p in panchayats:
            p_contexts = self.build_panchayat_crop_context(
                panchayat_id=p.id,
                context_date=context_date,
                source_model=source_model,
                model_version=model_version,
                persist_to_db=persist_to_db,
            )
            for ctx in p_contexts:
                all_contexts.append(ctx)
                if ctx.status == "COMPLETE":
                    complete_count += 1
                elif ctx.status == "PARTIAL":
                    partial_count += 1
                else:
                    unavailable_count += 1

        return AgriculturalContextResponse(
            context_run_id=context_run_id,
            block_id=block.id,
            block_name=block.name,
            context_date=context_date.isoformat(),
            total_panchayats=len(panchayats),
            total_crop_contexts=len(all_contexts),
            complete_contexts_count=complete_count,
            partial_contexts_count=partial_count,
            unavailable_contexts_count=unavailable_count,
            contexts=all_contexts,
            execution_timestamp=datetime.utcnow().isoformat(),
        )

    def get_panchayat_profile(
        self,
        panchayat_id: int,
        context_date: datetime,
    ) -> PanchayatAgriculturalProfile:
        """
        Retrieves active agricultural profile and multi-crop contexts for a single Panchayat.
        """
        panchayat = self.db.scalar(select(Panchayat).where(Panchayat.id == panchayat_id))
        if not panchayat:
            raise ValueError(f"Panchayat with ID {panchayat_id} not found in database.")

        block = panchayat.block or self.db.scalar(select(Block).where(Block.id == panchayat.block_id))
        block_name = block.name if block else None

        land_use = self.db.scalar(select(LandUseMask).where(LandUseMask.panchayat_id == panchayat_id))
        is_agri_eligible = True
        agri_area = None
        if land_use:
            is_agri_eligible = land_use.is_agricultural_eligible and (land_use.cropland_area_ha > 0)
            agri_area = land_use.cropland_area_ha

        contexts = self.build_panchayat_crop_context(
            panchayat_id=panchayat_id,
            context_date=context_date,
            persist_to_db=False,
        )

        overall_status = "COMPLETE" if any(c.status == "COMPLETE" for c in contexts) else "PARTIAL"
        if not contexts or all(c.status == "UNAVAILABLE" for c in contexts):
            overall_status = "UNAVAILABLE"

        return PanchayatAgriculturalProfile(
            panchayat_id=panchayat.id,
            panchayat_name=panchayat.name,
            lgd_code=panchayat.lgd_code,
            block_id=panchayat.block_id,
            block_name=block_name,
            context_date=context_date.isoformat(),
            is_agricultural_eligible=is_agri_eligible,
            agricultural_area_ha=agri_area,
            total_active_crops=len(contexts) if contexts and contexts[0].crop_name != "UNAVAILABLE" else 0,
            crop_contexts=contexts,
            overall_status=overall_status,
        )

    def get_subsystem_status(self) -> AgricultureSubsystemStatus:
        """
        Computes system-wide inventory counts of crop mappings, soil profiles, and context snapshots.
        """
        total_contexts = self.db.scalar(select(func.count(PanchayatCropContext.id))) or 0
        panchayats_with_mappings = self.db.scalar(
            select(func.count(func.distinct(PanchayatCropMapping.panchayat_id)))
            .where(PanchayatCropMapping.is_active == True)
        ) or 0
        panchayats_with_soil = self.db.scalar(
            select(func.count(func.distinct(PanchayatCropMapping.panchayat_id)))
            .where(
                and_(
                    PanchayatCropMapping.is_active == True,
                    PanchayatCropMapping.soil_id != None,
                )
            )
        ) or 0
        panchayats_with_stage = self.db.scalar(
            select(func.count(func.distinct(PanchayatCropMapping.panchayat_id)))
            .where(
                and_(
                    PanchayatCropMapping.is_active == True,
                    PanchayatCropMapping.current_stage_id != None,
                )
            )
        ) or 0

        complete_count = self.db.scalar(
            select(func.count(PanchayatCropContext.id)).where(PanchayatCropContext.status == "COMPLETE")
        ) or 0
        partial_count = self.db.scalar(
            select(func.count(PanchayatCropContext.id)).where(PanchayatCropContext.status == "PARTIAL")
        ) or 0
        unavailable_count = self.db.scalar(
            select(func.count(PanchayatCropContext.id)).where(PanchayatCropContext.status == "UNAVAILABLE")
        ) or 0

        last_date_rec = self.db.scalar(
            select(func.max(PanchayatCropContext.context_date))
        )
        last_date_str = last_date_rec.isoformat() if last_date_rec else None

        return AgricultureSubsystemStatus(
            total_context_records=total_contexts,
            panchayats_with_crop_mappings=panchayats_with_mappings,
            panchayats_with_soil_profiles=panchayats_with_soil,
            panchayats_with_resolved_stages=panchayats_with_stage,
            complete_status_count=complete_count,
            partial_status_count=partial_count,
            unavailable_status_count=unavailable_count,
            last_context_date=last_date_str,
        )
