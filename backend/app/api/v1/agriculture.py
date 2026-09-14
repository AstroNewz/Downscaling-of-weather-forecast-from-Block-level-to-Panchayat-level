"""
Agricultural Context (Crops, Crop Stage, Soil Context) API Endpoints
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Exposes endpoints for:
- Building Panchayat Agricultural Context snapshots from Weather + Crop + Stage + Soil
- Querying multi-crop context snapshots with spatial/temporal filters
- Retrieving Panchayat agricultural profiles
- Monitoring agricultural subsystem inventory and health status
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.spatial import Panchayat, Block
from app.db.models.agriculture import (
    Crop,
    CropPhenologyStage,
    SoilProfile,
    PanchayatCropMapping,
    PanchayatCropContext,
)
from app.schemas.common import APIResponse, PaginatedResponse
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
from app.services.agricultural_context import AgriculturalContextService
from app.core.logging import logger

router = APIRouter(prefix="/agriculture", tags=["Agricultural Context"])


@router.post(
    "/context",
    response_model=APIResponse[AgriculturalContextResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate Agricultural Context",
    description=(
        "Executes Phase 9 Agricultural Context generation by joining Panchayat Weather, "
        "active Crop Mappings, resolved Crop Phenology Stages, Soil Profiles, and Land-Use eligibility."
    )
)
async def generate_agricultural_context(
    request: AgriculturalContextRequest,
    db: Session = Depends(get_db)
) -> APIResponse[AgriculturalContextResponse]:
    try:
        service = AgriculturalContextService(db=db)
        response_data = service.build_block_agricultural_context(
            block_id=request.block_id,
            context_date=request.context_date,
            source_model=request.source_model or "IMD-GFS",
            model_version=request.model_version,
            panchayat_id=request.panchayat_id,
            persist_to_db=request.persist_to_db,
        )
        return APIResponse(
            success=True,
            message=f"Agricultural context generated successfully for Block ID {request.block_id}.",
            data=response_data,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )
    except Exception as exc:
        logger.error(f"Error generating agricultural context: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate agricultural context: {str(exc)}",
        )


@router.get(
    "/context",
    response_model=APIResponse[List[PanchayatCropContextSummary]],
    status_code=status.HTTP_200_OK,
    summary="Query Agricultural Context Records",
    description="Queries persisted PanchayatCropContext records with optional filtering by block, panchayat, crop, date, or status."
)
async def query_agricultural_contexts(
    block_id: Optional[int] = Query(None, description="Filter by Block ID"),
    panchayat_id: Optional[int] = Query(None, description="Filter by Panchayat ID"),
    crop_id: Optional[int] = Query(None, description="Filter by Crop ID"),
    context_date: Optional[datetime] = Query(None, description="Filter by Target context date"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: COMPLETE, PARTIAL, UNAVAILABLE"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
) -> APIResponse[List[PanchayatCropContextSummary]]:
    stmt = select(PanchayatCropContext)

    if block_id is not None:
        stmt = stmt.where(PanchayatCropContext.block_id == block_id)
    if panchayat_id is not None:
        stmt = stmt.where(PanchayatCropContext.panchayat_id == panchayat_id)
    if crop_id is not None:
        stmt = stmt.where(PanchayatCropContext.crop_id == crop_id)
    if context_date is not None:
        target_day = context_date.date() if isinstance(context_date, datetime) else context_date
        stmt = stmt.where(func.date(PanchayatCropContext.context_date) == target_day)
    if status_filter is not None:
        stmt = stmt.where(PanchayatCropContext.status == status_filter)

    stmt = stmt.order_by(PanchayatCropContext.context_date.desc(), PanchayatCropContext.panchayat_id.asc()).limit(limit).offset(offset)
    records = db.scalars(stmt).all()

    summaries: List[PanchayatCropContextSummary] = []
    for rec in records:
        panchayat_name = rec.panchayat.name if rec.panchayat else f"Panchayat #{rec.panchayat_id}"
        block_name = rec.block.name if rec.block else None

        stage_ctx = CropStageContext(
            phenology_stage_id=rec.phenology_stage_id,
            stage_name=rec.stage_name,
            stage_order=rec.stage_order,
            gdd_required=rec.stage.gdd_required if rec.stage else None,
            water_sensitivity=rec.stage.water_sensitivity if rec.stage else None,
            temp_sensitivity=rec.stage.temp_sensitivity if rec.stage else None,
            stage_derivation_method=rec.stage_derivation_method,
            planting_date=rec.planting_date.isoformat() if rec.planting_date else None,
            days_since_planting=rec.days_since_planting,
            expected_harvest_date=rec.expected_harvest_date.isoformat() if rec.expected_harvest_date else None,
            is_stage_resolved=rec.stage_name is not None and rec.stage_name != "UNKNOWN",
        )

        soil_ctx = SoilContextSummary(
            soil_profile_id=rec.soil_profile_id,
            soil_type=rec.soil_type,
            texture=rec.soil.texture if rec.soil else None,
            drainage_class=rec.soil.drainage_class if rec.soil else None,
            water_holding_capacity_pct=rec.soil.water_holding_capacity_pct if rec.soil else None,
            ph_level=rec.soil.ph_level if rec.soil else None,
            organic_carbon_pct=rec.soil.organic_carbon_pct if rec.soil else None,
            available_nitrogen_kg_ha=rec.soil.available_nitrogen_kg_ha if rec.soil else None,
            available_phosphorus_kg_ha=rec.soil.available_phosphorus_kg_ha if rec.soil else None,
            available_potassium_kg_ha=rec.soil.available_potassium_kg_ha if rec.soil else None,
            soil_available=rec.soil_available,
            soil_status=rec.soil_status,
        )

        weather_ctx = WeatherContextSummary(
            panchayat_weather_id=rec.panchayat_weather_id,
            forecast_valid_time=rec.context_date.isoformat() if rec.context_date else None,
            mean_temp_c=rec.mean_temp_c,
            min_temp_c=rec.min_temp_c,
            max_temp_c=rec.max_temp_c,
            temp_stddev_c=rec.temp_stddev_c,
            weather_status=rec.weather_status,
        )

        summaries.append(
            PanchayatCropContextSummary(
                id=rec.id,
                panchayat_id=rec.panchayat_id,
                panchayat_name=panchayat_name,
                block_id=rec.block_id,
                block_name=block_name,
                crop_id=rec.crop_id,
                crop_name=rec.crop_name,
                scientific_name=rec.crop.scientific_name if rec.crop else None,
                season=rec.crop.season if rec.crop else None,
                crop_stage=stage_ctx,
                soil=soil_ctx,
                weather=weather_ctx,
                crop_area_ha=rec.crop_area_ha,
                agricultural_area_ha=rec.agricultural_area_ha,
                crop_fraction=rec.crop_fraction,
                is_agricultural_eligible=rec.is_agricultural_eligible,
                context_date=rec.context_date.isoformat(),
                source=rec.source,
                source_version=rec.source_version,
                confidence_score=rec.confidence_score,
                status=rec.status,
                quality_flags=rec.quality_flags or [],
                provenance=rec.provenance,
                created_at=rec.created_at.isoformat(),
            )
        )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(summaries)} agricultural context records.",
        data=summaries,
    )


@router.get(
    "/panchayat/{panchayat_id}/context",
    response_model=APIResponse[PanchayatAgriculturalProfile],
    status_code=status.HTTP_200_OK,
    summary="Get Panchayat Agricultural Profile",
    description="Retrieves active agricultural profile and all mapped crop/stage/soil contexts for a specific Panchayat."
)
async def get_panchayat_agricultural_context(
    panchayat_id: int,
    context_date: Optional[datetime] = Query(None, description="Target forecast date (defaults to today)"),
    db: Session = Depends(get_db)
) -> APIResponse[PanchayatAgriculturalProfile]:
    target_dt = context_date or datetime.utcnow()
    try:
        service = AgriculturalContextService(db=db)
        profile = service.get_panchayat_profile(panchayat_id=panchayat_id, context_date=target_dt)
        return APIResponse(
            success=True,
            message=f"Agricultural profile retrieved for Panchayat ID {panchayat_id}.",
            data=profile,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        logger.error(f"Error fetching Panchayat agricultural profile: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agricultural profile: {str(exc)}",
        )


@router.get(
    "/status",
    response_model=APIResponse[AgricultureSubsystemStatus],
    status_code=status.HTTP_200_OK,
    summary="Agriculture Service Status",
    description="Returns aggregate inventory of crop mappings, soil profiles, resolved stages, and context snapshot counts."
)
async def get_agriculture_service_status(db: Session = Depends(get_db)) -> APIResponse[AgricultureSubsystemStatus]:
    service = AgriculturalContextService(db=db)
    status_data = service.get_subsystem_status()
    return APIResponse(
        success=True,
        message="Agricultural context subsystem operational.",
        data=status_data,
    )


# ============================================================================
# PHASE 10: AGRICULTURAL RISK ENGINE ENDPOINTS
# ============================================================================

from app.db.models.advisory import AgriculturalRiskLog
from app.schemas.agricultural_risk import (
    RiskEvidence,
    RiskResult,
    RiskEvaluationRequest,
    RiskEvaluationResponse,
    PanchayatRiskProfile,
    RiskSubsystemStatus,
)
from app.services.agricultural_risk import AgriculturalRiskEngine


@router.post(
    "/risk/evaluate",
    response_model=APIResponse[RiskEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Evaluate Agricultural Risks",
    description=(
        "Executes Phase 10 Agricultural Risk Engine evaluation across downscaled weather, "
        "crop growth stages, and soil characteristics. Evaluates thermal, chilling, hydrological, "
        "and pathogen-favorable environmental conditions."
    )
)
async def evaluate_agricultural_risks(
    request: RiskEvaluationRequest,
    db: Session = Depends(get_db)
) -> APIResponse[RiskEvaluationResponse]:
    try:
        engine = AgriculturalRiskEngine(db=db)
        response_data = engine.evaluate_block_risks(
            block_id=request.block_id,
            evaluation_date=request.evaluation_date,
            panchayat_id=request.panchayat_id,
            crop_id=request.crop_id,
            risk_type=request.risk_type,
            persist_to_db=request.persist_to_db,
        )
        return APIResponse(
            success=True,
            message=f"Agricultural risk evaluation completed successfully for Block ID {request.block_id}.",
            data=response_data,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )
    except Exception as exc:
        logger.error(f"Error evaluating agricultural risks: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate agricultural risks: {str(exc)}",
        )


@router.get(
    "/risk",
    response_model=APIResponse[List[RiskResult]],
    status_code=status.HTTP_200_OK,
    summary="Query Logged Agricultural Risks",
    description="Queries persisted AgriculturalRiskLog records with spatial, temporal, risk type, and severity filtering."
)
async def query_agricultural_risks(
    block_id: Optional[int] = Query(None, description="Filter by Block ID"),
    panchayat_id: Optional[int] = Query(None, description="Filter by Panchayat ID"),
    crop_id: Optional[int] = Query(None, description="Filter by Crop ID"),
    risk_type: Optional[str] = Query(None, description="Filter by risk type (e.g. HEAT_STRESS, COLD_STRESS)"),
    severity: Optional[str] = Query(None, description="Filter by severity: NONE, LOW, MODERATE, HIGH, EXTREME"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: DETECTED, NOT_DETECTED, INSUFFICIENT_DATA"),
    evaluation_date: Optional[datetime] = Query(None, description="Filter by evaluation date"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
) -> APIResponse[List[RiskResult]]:
    stmt = select(AgriculturalRiskLog)

    if block_id is not None:
        stmt = stmt.where(AgriculturalRiskLog.block_id == block_id)
    if panchayat_id is not None:
        stmt = stmt.where(AgriculturalRiskLog.panchayat_id == panchayat_id)
    if crop_id is not None:
        stmt = stmt.where(AgriculturalRiskLog.crop_id == crop_id)
    if risk_type is not None:
        stmt = stmt.where(AgriculturalRiskLog.risk_type == risk_type)
    if severity is not None:
        stmt = stmt.where(AgriculturalRiskLog.severity == severity)
    if status_filter is not None:
        stmt = stmt.where(AgriculturalRiskLog.status == status_filter)
    if evaluation_date is not None:
        target_day = evaluation_date.date() if isinstance(evaluation_date, datetime) else evaluation_date
        stmt = stmt.where(func.date(AgriculturalRiskLog.evaluation_date) == target_day)

    stmt = stmt.order_by(AgriculturalRiskLog.evaluation_date.desc(), AgriculturalRiskLog.panchayat_id.asc()).limit(limit).offset(offset)
    records = db.scalars(stmt).all()

    results: List[RiskResult] = []
    for rec in records:
        panchayat_name = rec.panchayat.name if rec.panchayat else f"Panchayat #{rec.panchayat_id}"
        block_name = rec.block.name if rec.block else None

        evidence_obj = RiskEvidence(
            observed_value=rec.observed_value,
            threshold_value=rec.threshold_value,
            unit=rec.unit,
            crop_name=rec.crop_name,
            stage_name=rec.stage_name,
            condition_description=rec.description or f"{rec.risk_type} evaluation: {rec.status}",
            metrics=(rec.evidence or {}).get("metrics", {}),
        )

        results.append(
            RiskResult(
                id=rec.id,
                panchayat_id=rec.panchayat_id,
                panchayat_name=panchayat_name,
                block_id=rec.block_id,
                block_name=block_name,
                crop_id=rec.crop_id,
                crop_name=rec.crop_name,
                stage_name=rec.stage_name,
                risk_type=rec.risk_type,
                risk_category=rec.risk_category,
                severity=rec.severity,
                status=rec.status,
                risk_score=rec.risk_score,
                observed_value=rec.observed_value,
                threshold_value=rec.threshold_value,
                unit=rec.unit,
                duration_hours=rec.duration_hours,
                confidence=rec.confidence,
                rule_version=rec.rule_version,
                rule_source=rec.rule_source,
                evidence=evidence_obj,
                provenance=rec.provenance or {},
                evaluation_date=rec.evaluation_date.isoformat(),
                created_at=rec.created_at.isoformat(),
            )
        )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(results)} agricultural risk records.",
        data=results,
    )


@router.get(
    "/panchayat/{panchayat_id}/risk",
    response_model=APIResponse[PanchayatRiskProfile],
    status_code=status.HTTP_200_OK,
    summary="Get Panchayat Risk Profile",
    description="Retrieves multi-crop agricultural risk assessments grouped by crop for a specific Panchayat."
)
async def get_panchayat_risk_profile(
    panchayat_id: int,
    evaluation_date: Optional[datetime] = Query(None, description="Target forecast date (defaults to today)"),
    db: Session = Depends(get_db)
) -> APIResponse[PanchayatRiskProfile]:
    target_dt = evaluation_date or datetime.utcnow()
    try:
        engine = AgriculturalRiskEngine(db=db)
        profile = engine.get_panchayat_risk_profile(panchayat_id=panchayat_id, evaluation_date=target_dt)
        return APIResponse(
            success=True,
            message=f"Agricultural risk profile retrieved for Panchayat ID {panchayat_id}.",
            data=profile,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        logger.error(f"Error fetching Panchayat risk profile: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch risk profile: {str(exc)}",
        )


@router.get(
    "/risk/status",
    response_model=APIResponse[RiskSubsystemStatus],
    status_code=status.HTTP_200_OK,
    summary="Risk Engine Subsystem Status",
    description="Returns aggregate inventory of detected, not-detected, and insufficient-data evaluations across risk types and severities."
)
async def get_risk_subsystem_status(db: Session = Depends(get_db)) -> APIResponse[RiskSubsystemStatus]:
    engine = AgriculturalRiskEngine(db=db)
    status_data = engine.get_subsystem_status()
    return APIResponse(
        success=True,
        message="Agricultural risk subsystem operational.",
        data=status_data,
    )

