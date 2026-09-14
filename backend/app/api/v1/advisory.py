"""
Agro-Meteorological Advisory Generation API Endpoints
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Provides REST endpoints to:
- Generate crop-specific, stage-aware, and explainable agro-meteorological advisories
- Query active advisories with spatial, crop, priority, and validity filters
- Retrieve Panchayat advisory profiles grouped by crop
- Inspect individual advisory evidence and provenance
- Query advisory subsystem statistics and metrics
"""
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.db.session import get_db
from app.db.models.spatial import Block, Panchayat
from app.db.models.agriculture import Crop
from app.db.models.advisory import AgroAdvisory
from app.schemas.common import APIResponse
from app.schemas.advisory import (
    AdvisoryType,
    AdvisoryPriority,
    AdvisoryStatus,
    AdvisoryActionCategory,
    AdvisoryAction,
    AdvisoryResult,
    AdvisoryGenerationRequest,
    AdvisoryGenerationResponse,
    PanchayatAdvisoryProfile,
    AdvisorySubsystemStatus,
)
from app.services.advisory_engine import AdvisoryEngine

router = APIRouter(prefix="/advisory", tags=["Agro-Meteorological Advisory"])


@router.post(
    "/generate",
    response_model=APIResponse[AdvisoryGenerationResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate Agro-Meteorological Advisories",
    description="Translates Phase 10 detected agricultural risks into explainable, prioritized advisories for a Panchayat or Block."
)
def generate_advisories(
    payload: AdvisoryGenerationRequest,
    db: Session = Depends(get_db),
) -> APIResponse[AdvisoryGenerationResponse]:
    """
    Executes Phase 11 Advisory Generation Engine for a Block or individual Panchayat.
    """
    engine = AdvisoryEngine(db=db)

    if payload.block_id is not None:
        response = engine.generate_block_advisories(
            block_id=payload.block_id,
            forecast_date=payload.date,
            panchayat_id=payload.panchayat_id,
            crop_id=payload.crop_id,
            risk_type=payload.risk_type,
            persist_to_db=payload.persist_to_db,
            language=payload.language,
        )
        return APIResponse(
            success=True,
            message=f"Generated {response.total_advisories_generated} agro-meteorological advisories across {response.total_panchayats} Panchayats.",
            data=response,
        )

    elif payload.panchayat_id is not None:
        panchayat = db.scalar(select(Panchayat).where(Panchayat.id == payload.panchayat_id))
        if not panchayat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Panchayat with ID {payload.panchayat_id} not found."
            )

        results = engine.generate_panchayat_advisories(
            panchayat_id=payload.panchayat_id,
            forecast_date=payload.date,
            crop_id=payload.crop_id,
            risk_type_filter=payload.risk_type,
            persist_to_db=payload.persist_to_db,
            language=payload.language,
        )

        critical_count = sum(1 for a in results if a.priority == "CRITICAL")
        high_count = sum(1 for a in results if a.priority == "HIGH")
        med_count = sum(1 for a in results if a.priority == "MEDIUM")
        low_count = sum(1 for a in results if a.priority == "LOW")
        info_count = sum(1 for a in results if a.priority == "INFORMATIONAL")
        crops_set = set(a.crop_id for a in results)

        response = AdvisoryGenerationResponse(
            generation_run_id=datetime.utcnow().isoformat(),
            block_id=panchayat.block_id,
            block_name=panchayat.block.name if panchayat.block else None,
            forecast_date=payload.date.isoformat(),
            total_panchayats=1,
            total_crops_evaluated=len(crops_set),
            total_advisories_generated=len(results),
            critical_advisories_count=critical_count,
            high_advisories_count=high_count,
            medium_advisories_count=med_count,
            low_advisories_count=low_count,
            informational_count=info_count,
            advisories=results,
            execution_timestamp=datetime.utcnow().isoformat(),
        )

        return APIResponse(
            success=True,
            message=f"Generated {len(results)} agro-meteorological advisories for Panchayat '{panchayat.name}'.",
            data=response,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'block_id' or 'panchayat_id' must be specified in the generation request."
        )


@router.get(
    "",
    response_model=APIResponse[List[AdvisoryResult]],
    status_code=status.HTTP_200_OK,
    summary="Query Logged Agro-Meteorological Advisories",
    description="Queries persisted advisory records with optional spatial, crop, advisory type, priority, and validity filters."
)
def query_advisories(
    block_id: Optional[int] = Query(None, description="Filter by Block ID"),
    panchayat_id: Optional[int] = Query(None, description="Filter by Panchayat ID"),
    crop_id: Optional[int] = Query(None, description="Filter by Crop ID"),
    advisory_type: Optional[str] = Query(None, description="Filter by advisory type"),
    priority: Optional[str] = Query(None, description="Filter by priority (CRITICAL, HIGH, MEDIUM, LOW)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ACTIVE, DRAFT, EXPIRED, SUPPRESSED, etc.)"),
    valid_from: Optional[datetime] = Query(None, description="Filter valid from date"),
    valid_until: Optional[datetime] = Query(None, description="Filter valid until date"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> APIResponse[List[AdvisoryResult]]:
    """
    Retrieves logged agro-meteorological advisories.
    """
    stmt = select(AgroAdvisory).order_by(desc(AgroAdvisory.valid_from), AgroAdvisory.priority_rank)

    if block_id is not None:
        stmt = stmt.where(AgroAdvisory.block_id == block_id)
    if panchayat_id is not None:
        stmt = stmt.where(AgroAdvisory.panchayat_id == panchayat_id)
    if crop_id is not None:
        stmt = stmt.where(AgroAdvisory.crop_id == crop_id)
    if advisory_type is not None:
        stmt = stmt.where(AgroAdvisory.advisory_type == advisory_type)
    if priority is not None:
        stmt = stmt.where(AgroAdvisory.priority == priority)
    if status_filter is not None:
        stmt = stmt.where(AgroAdvisory.status == status_filter)
    if valid_from is not None:
        stmt = stmt.where(AgroAdvisory.valid_from >= valid_from)
    if valid_until is not None:
        stmt = stmt.where(AgroAdvisory.valid_until <= valid_until)

    records = db.scalars(stmt.offset(offset).limit(limit)).all()

    results: List[AdvisoryResult] = []
    for r in records:
        action = None
        if r.recommended_action or r.action_category:
            action = AdvisoryAction(
                action_category=r.action_category,
                action_text=r.recommended_action,
                timing=r.timing,
                urgency=r.urgency,
                conditions={},
            )

        results.append(
            AdvisoryResult(
                id=r.id,
                panchayat_id=r.panchayat_id,
                panchayat_name=r.panchayat.name if r.panchayat else f"Panchayat-{r.panchayat_id}",
                block_id=r.block_id,
                block_name=r.block.name if r.block else None,
                crop_id=r.crop_id,
                crop_name=r.crop.crop_name if r.crop else f"Crop-{r.crop_id}",
                stage_name=r.evidence.get("stage_name") if r.evidence else None,
                risk_log_id=r.risk_log_id,
                crop_context_id=r.crop_context_id,
                panchayat_weather_id=r.panchayat_weather_id,
                advisory_type=r.advisory_type,
                advisory_category=r.advisory_category,
                priority=r.priority,
                priority_rank=r.priority_rank,
                priority_reason=r.priority_reason,
                title=r.title,
                message=r.message,
                action=action,
                rationale=r.rationale,
                severity=r.severity,
                confidence=r.confidence,
                confidence_reason=r.confidence_reason,
                valid_from=r.valid_from.isoformat(),
                valid_until=r.valid_until.isoformat(),
                forecast_date=r.forecast_date.isoformat(),
                issue_time=r.issue_time.isoformat(),
                source_model=r.source_model,
                weather_model_version=r.weather_model_version,
                rule_version=r.rule_version,
                advisory_rule_version=r.advisory_rule_version,
                rule_source=r.rule_source,
                language=r.language,
                status=r.status,
                is_expert_review_required=r.is_expert_review_required,
                is_cropland_eligible=r.is_cropland_eligible,
                evidence=r.evidence,
                provenance=r.provenance,
                created_at=r.created_at.isoformat(),
            )
        )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(results)} agro-meteorological advisories.",
        data=results,
    )


@router.get(
    "/status",
    response_model=APIResponse[AdvisorySubsystemStatus],
    status_code=status.HTTP_200_OK,
    summary="Advisory Engine Status & Analytics",
    description="Returns aggregate metrics on generated advisories, priority distributions, and active rule version."
)
def get_advisory_status(
    db: Session = Depends(get_db),
) -> APIResponse[AdvisorySubsystemStatus]:
    """
    Returns operational metrics for the Phase 11 Advisory Generation subsystem.
    """
    engine = AdvisoryEngine(db=db)
    status_data = engine.get_subsystem_status()
    return APIResponse(
        success=True,
        message="Agro-meteorological advisory subsystem status retrieved successfully.",
        data=status_data,
    )


@router.get(
    "/panchayat/{panchayat_id}",
    response_model=APIResponse[PanchayatAdvisoryProfile],
    status_code=status.HTTP_200_OK,
    summary="Panchayat Active Advisory Profile",
    description="Retrieves active agro-meteorological advisories grouped by crop for a specific Gram Panchayat."
)
def get_panchayat_advisory_profile(
    panchayat_id: int = Path(..., description="Gram Panchayat ID"),
    evaluation_date: Optional[datetime] = Query(None, alias="date", description="Forecast evaluation date (default current date)"),
    db: Session = Depends(get_db),
) -> APIResponse[PanchayatAdvisoryProfile]:
    """
    Returns dashboard-ready active advisories grouped by crop for a single Panchayat.
    """
    eval_dt = evaluation_date or datetime.utcnow()
    engine = AdvisoryEngine(db=db)

    try:
        profile = engine.get_panchayat_advisory_profile(panchayat_id=panchayat_id, forecast_date=eval_dt)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return APIResponse(
        success=True,
        message=f"Retrieved active advisory profile for Panchayat ID {panchayat_id}.",
        data=profile,
    )


@router.get(
    "/{advisory_id}",
    response_model=APIResponse[AdvisoryResult],
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Advisory by ID",
    description="Retrieves complete advisory details including action, scientific rationale, evidence, and provenance."
)
def get_advisory_by_id(
    advisory_id: int = Path(..., description="Advisory Record ID"),
    db: Session = Depends(get_db),
) -> APIResponse[AdvisoryResult]:
    """
    Returns a single agro-meteorological advisory record by ID.
    """
    r = db.scalar(select(AgroAdvisory).where(AgroAdvisory.id == advisory_id))
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory record with ID {advisory_id} not found."
        )

    action = None
    if r.recommended_action or r.action_category:
        action = AdvisoryAction(
            action_category=r.action_category,
            action_text=r.recommended_action,
            timing=r.timing,
            urgency=r.urgency,
            conditions={},
        )

    res = AdvisoryResult(
        id=r.id,
        panchayat_id=r.panchayat_id,
        panchayat_name=r.panchayat.name if r.panchayat else f"Panchayat-{r.panchayat_id}",
        block_id=r.block_id,
        block_name=r.block.name if r.block else None,
        crop_id=r.crop_id,
        crop_name=r.crop.crop_name if r.crop else f"Crop-{r.crop_id}",
        stage_name=r.evidence.get("stage_name") if r.evidence else None,
        risk_log_id=r.risk_log_id,
        crop_context_id=r.crop_context_id,
        panchayat_weather_id=r.panchayat_weather_id,
        advisory_type=r.advisory_type,
        advisory_category=r.advisory_category,
        priority=r.priority,
        priority_rank=r.priority_rank,
        priority_reason=r.priority_reason,
        title=r.title,
        message=r.message,
        action=action,
        rationale=r.rationale,
        severity=r.severity,
        confidence=r.confidence,
        confidence_reason=r.confidence_reason,
        valid_from=r.valid_from.isoformat(),
        valid_until=r.valid_until.isoformat(),
        forecast_date=r.forecast_date.isoformat(),
        issue_time=r.issue_time.isoformat(),
        source_model=r.source_model,
        weather_model_version=r.weather_model_version,
        rule_version=r.rule_version,
        advisory_rule_version=r.advisory_rule_version,
        rule_source=r.rule_source,
        language=r.language,
        status=r.status,
        is_expert_review_required=r.is_expert_review_required,
        is_cropland_eligible=r.is_cropland_eligible,
        evidence=r.evidence,
        provenance=r.provenance,
        created_at=r.created_at.isoformat(),
    )

    return APIResponse(
        success=True,
        message=f"Retrieved advisory record ID {advisory_id}.",
        data=res,
    )
