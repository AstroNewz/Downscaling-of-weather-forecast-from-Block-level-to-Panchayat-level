"""
Panchayat GIS Intelligence & Spatial Weather API Router
SIH Problem Statement 26074 (Weather Downscaling)

Exposes Panchayat boundary management, land-use masks, area-weighted spatial
weather aggregation from 1-km downscaled grids, and hyper-local weather queries.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.spatial import Panchayat, Block, LandUseMask
from app.db.models.weather import PanchayatWeather
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.panchayat import PanchayatResponse, LandUseComposition
from app.schemas.panchayat_weather import (
    PanchayatWeatherSummary,
    PanchayatWeatherAggregateRequest,
    PanchayatWeatherAggregateResponse,
)
from app.gis.landuse import LandUseExtractor
from app.gis.spatial_features import SpatialFeatureExtractor
from app.services.panchayat_aggregation import PanchayatWeatherAggregationService
from app.core.logging import logger

router = APIRouter(prefix="/panchayat", tags=["Panchayat GIS & Weather Aggregation"])


@router.get(
    "/status",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Panchayat GIS Service Status",
    description="Returns current status of Panchayat spatial mapping, LULC masks, and coordinate reference system (EPSG:4326)."
)
async def get_panchayat_service_status(db: Session = Depends(get_db)) -> APIResponse[dict]:
    total_panchayats = db.scalar(select(func.count(Panchayat.id))) or 0
    total_blocks = db.scalar(select(func.count(Block.id))) or 0
    total_masks = db.scalar(select(func.count(LandUseMask.id))) or 0
    total_weather_records = db.scalar(select(func.count(PanchayatWeather.id))) or 0

    return APIResponse(
        success=True,
        message="Panchayat GIS subsystem operational.",
        data={
            "module": "Panchayat GIS & Weather Aggregation Service",
            "phase": "Phase 8 Panchayat-Level Weather Aggregation Active",
            "spatial_srid": 4326,
            "aggregation_method": "AREA_WEIGHTED",
            "cropland_mask_filter": "Active - non-cropland excluded from crop advisories",
            "database_stats": {
                "total_blocks": total_blocks,
                "total_panchayats": total_panchayats,
                "total_land_use_masks": total_masks,
                "total_panchayat_weather_records": total_weather_records,
            }
        }
    )


@router.get(
    "/list",
    response_model=APIResponse[PaginatedResponse[PanchayatResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Gram Panchayats with Land-Use Masks",
    description="Queries paginated Panchayats with optional block filtering and land-use composition."
)
async def list_panchayats(
    block_id: Optional[int] = Query(None, description="Filter by Block ID"),
    name: Optional[str] = Query(None, description="Filter by Panchayat name keyword"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> APIResponse[PaginatedResponse[PanchayatResponse]]:
    stmt = select(Panchayat).join(Panchayat.block)
    conds = []
    if block_id:
        conds.append(Panchayat.block_id == block_id)
    if name:
        conds.append(func.lower(Panchayat.name).like(f"%{name.lower()}%"))

    if conds:
        stmt = stmt.where(and_(*conds))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    panchayats = db.scalars(stmt.offset(offset).limit(page_size)).all()

    items: List[PanchayatResponse] = []
    for p in panchayats:
        p_lat, p_lon = SpatialFeatureExtractor.extract_centroid_coordinates(p.centroid or p.geometry)
        lat = p_lat if p_lat is not None else 0.0
        lon = p_lon if p_lon is not None else 0.0

        land_use_comp = None
        if p.land_use:
            lu_feat = LandUseExtractor.extract_from_mask_record(p.land_use)
            land_use_comp = LandUseComposition(
                total_area_hectares=lu_feat.total_area_ha or 0.0,
                cropland_area_hectares=lu_feat.cropland_area_ha or 0.0,
                forest_area_hectares=round((lu_feat.forest_fraction or 0.0) * (lu_feat.total_area_ha or 0.0), 2),
                urban_area_hectares=round((lu_feat.urban_fraction or 0.0) * (lu_feat.total_area_ha or 0.0), 2),
                water_bodies_hectares=round((lu_feat.water_fraction or 0.0) * (lu_feat.total_area_ha or 0.0), 2),
                barren_area_hectares=round((lu_feat.barren_fraction or 0.0) * (lu_feat.total_area_ha or 0.0), 2),
                is_agricultural_eligible=lu_feat.is_agricultural_cropland,
            )

        item = PanchayatResponse(
            panchayat_id=p.lgd_code,
            name=p.name,
            block_id=str(p.block_id),
            district_name=p.block.district_name if p.block else "Unassigned",
            state_name=p.block.state_name if p.block else "Unassigned",
            latitude=lat,
            longitude=lon,
            elevation_meters=p.elevation_meters,
            land_use=land_use_comp,
        )
        items.append(item)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    paginated = PaginatedResponse[PanchayatResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} Panchayat records.",
        data=paginated
    )


# =========================================================================
# Phase 8: Panchayat-Level Weather Aggregation Endpoints
# =========================================================================

@router.post(
    "/weather/aggregate",
    response_model=APIResponse[PanchayatWeatherAggregateResponse],
    status_code=status.HTTP_200_OK,
    summary="Aggregate 1-km Weather Grid to Panchayat Level",
    description="Performs area-weighted spatial intersection of Phase 7 1-km grid cells across Gram Panchayats in a Block."
)
async def aggregate_panchayat_weather(
    payload: PanchayatWeatherAggregateRequest,
    db: Session = Depends(get_db)
) -> APIResponse[PanchayatWeatherAggregateResponse]:
    service = PanchayatWeatherAggregationService(db=db)
    try:
        response = service.aggregate_block_panchayats(
            block_id=payload.block_id,
            forecast_valid_time=payload.forecast_valid_time,
            forecast_issue_time=payload.forecast_issue_time,
            source_model=payload.source_model,
            model_version=payload.model_version,
            grid_resolution_km=payload.grid_resolution_km,
            panchayat_id=payload.panchayat_id,
            persist_to_db=payload.persist_to_db
        )
        return APIResponse(
            success=True,
            message=f"Panchayat weather aggregation completed for Block ID {payload.block_id} ({response.aggregated_panchayats_count} Panchayats).",
            data=response
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Panchayat weather aggregation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Aggregation execution failed: {e}"
        )


@router.get(
    "/weather",
    response_model=APIResponse[PaginatedResponse[PanchayatWeatherSummary]],
    status_code=status.HTTP_200_OK,
    summary="Query Aggregated Panchayat Weather Records",
    description="Queries stored area-weighted Panchayat weather statistics with filtering by block, date, and quality status."
)
async def query_panchayat_weather(
    block_id: Optional[int] = Query(None, description="Filter by Block ID"),
    panchayat_id: Optional[int] = Query(None, description="Filter by Panchayat database ID"),
    valid_time: Optional[datetime] = Query(None, description="Filter by forecast valid time (ISO UTC)"),
    quality_status: Optional[str] = Query(None, description="Filter by quality status (COMPLETE, PARTIAL, UNAVAILABLE)"),
    source_model: Optional[str] = Query(None, description="Filter by source model"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> APIResponse[PaginatedResponse[PanchayatWeatherSummary]]:
    stmt = select(PanchayatWeather).join(PanchayatWeather.panchayat).join(PanchayatWeather.block)
    conds = []

    if block_id:
        conds.append(PanchayatWeather.block_id == block_id)
    if panchayat_id:
        conds.append(PanchayatWeather.panchayat_id == panchayat_id)
    if valid_time:
        conds.append(PanchayatWeather.forecast_date == valid_time)
    if quality_status:
        conds.append(PanchayatWeather.quality_status == quality_status)
    if source_model:
        conds.append(PanchayatWeather.source_model == source_model)

    if conds:
        stmt = stmt.where(and_(*conds))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    records = db.scalars(stmt.offset(offset).limit(page_size).order_by(PanchayatWeather.forecast_date.desc())).all()

    items: List[PanchayatWeatherSummary] = []
    for r in records:
        summary = PanchayatWeatherSummary(
            panchayat_id=r.panchayat_id,
            panchayat_name=r.panchayat.name if r.panchayat else f"Panchayat_{r.panchayat_id}",
            lgd_code=r.panchayat.lgd_code if r.panchayat else "N/A",
            block_id=r.block_id,
            block_name=r.block.name if r.block else f"Block_{r.block_id}",
            forecast_valid_time=r.forecast_date.isoformat(),
            forecast_issue_time=r.issue_time.isoformat(),
            source_model=r.source_model,
            model_version=r.model_version,
            grid_resolution_km=r.grid_resolution_km,
            mean_temperature_c=r.mean_temp_c,
            min_temperature_c=r.min_temp_c,
            max_temperature_c=r.max_temp_c,
            median_temperature_c=r.median_temp_c,
            temperature_stddev_c=r.temp_stddev_c,
            temperature_p10_c=r.temp_p10_c,
            temperature_p90_c=r.temp_p90_c,
            mean_residual_c=r.mean_residual_c,
            total_panchayat_area_sqkm=r.total_panchayat_area_sqkm,
            covered_area_sqkm=r.covered_area_sqkm,
            coverage_percentage=r.coverage_pct,
            contributing_grid_cells=r.contributing_grid_cells,
            valid_grid_cells=r.valid_grid_cells,
            quality_status=r.quality_status,
            quality_flags=r.quality_flags or [],
            aggregation_method=r.aggregation_method,
            aggregation_crs=r.aggregation_crs,
            cropland_weighted_mean_temp_c=r.cropland_weighted_mean_temp_c,
            created_at=r.created_at.isoformat()
        )
        items.append(summary)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    paginated = PaginatedResponse[PanchayatWeatherSummary](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} Panchayat weather records.",
        data=paginated
    )


@router.get(
    "/{panchayat_id}/weather",
    response_model=APIResponse[List[PanchayatWeatherSummary]],
    status_code=status.HTTP_200_OK,
    summary="Get Weather Records for a Specific Panchayat",
    description="Retrieves latest and forecast horizon weather records for a single Gram Panchayat."
)
async def get_single_panchayat_weather(
    panchayat_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> APIResponse[List[PanchayatWeatherSummary]]:
    records = db.scalars(
        select(PanchayatWeather)
        .where(PanchayatWeather.panchayat_id == panchayat_id)
        .order_by(PanchayatWeather.forecast_date.desc())
        .limit(limit)
    ).all()

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No weather records found for Panchayat ID {panchayat_id}. Trigger aggregation first."
        )

    items: List[PanchayatWeatherSummary] = []
    for r in records:
        items.append(
            PanchayatWeatherSummary(
                panchayat_id=r.panchayat_id,
                panchayat_name=r.panchayat.name if r.panchayat else f"Panchayat_{r.panchayat_id}",
                lgd_code=r.panchayat.lgd_code if r.panchayat else "N/A",
                block_id=r.block_id,
                block_name=r.block.name if r.block else f"Block_{r.block_id}",
                forecast_valid_time=r.forecast_date.isoformat(),
                forecast_issue_time=r.issue_time.isoformat(),
                source_model=r.source_model,
                model_version=r.model_version,
                grid_resolution_km=r.grid_resolution_km,
                mean_temperature_c=r.mean_temp_c,
                min_temperature_c=r.min_temp_c,
                max_temperature_c=r.max_temp_c,
                median_temperature_c=r.median_temp_c,
                temperature_stddev_c=r.temp_stddev_c,
                temperature_p10_c=r.temp_p10_c,
                temperature_p90_c=r.temp_p90_c,
                mean_residual_c=r.mean_residual_c,
                total_panchayat_area_sqkm=r.total_panchayat_area_sqkm,
                covered_area_sqkm=r.covered_area_sqkm,
                coverage_percentage=r.coverage_pct,
                contributing_grid_cells=r.contributing_grid_cells,
                valid_grid_cells=r.valid_grid_cells,
                quality_status=r.quality_status,
                quality_flags=r.quality_flags or [],
                aggregation_method=r.aggregation_method,
                aggregation_crs=r.aggregation_crs,
                cropland_weighted_mean_temp_c=r.cropland_weighted_mean_temp_c,
                created_at=r.created_at.isoformat()
            )
        )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(items)} weather records for Panchayat ID {panchayat_id}.",
        data=items
    )


@router.get(
    "/weather/status",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Panchayat Weather Aggregation Status",
    description="Inspects aggregated Panchayat weather record counts, coverage rates, and operational parameters."
)
async def get_panchayat_weather_status(db: Session = Depends(get_db)) -> APIResponse[dict]:
    total_records = db.scalar(select(func.count(PanchayatWeather.id))) or 0
    complete_records = db.scalar(select(func.count(PanchayatWeather.id)).where(PanchayatWeather.quality_status == "COMPLETE")) or 0
    partial_records = db.scalar(select(func.count(PanchayatWeather.id)).where(PanchayatWeather.quality_status == "PARTIAL")) or 0
    distinct_panchayats = db.scalar(select(func.count(func.distinct(PanchayatWeather.panchayat_id)))) or 0

    return APIResponse(
        success=True,
        message="Panchayat weather aggregation status retrieved.",
        data={
            "module": "Panchayat Weather Spatial Aggregation Engine",
            "phase": "Phase 8 Panchayat Aggregation Active",
            "aggregation_method": "AREA_WEIGHTED",
            "complete_coverage_threshold_pct": 95.0,
            "total_weather_records": total_records,
            "distinct_panchayats_covered": distinct_panchayats,
            "complete_coverage_records": complete_records,
            "partial_coverage_records": partial_records,
        }
    )


@router.get(
    "/blocks",
    response_model=APIResponse[List[dict]],
    status_code=status.HTTP_200_OK,
    summary="List Administrative Blocks",
    description="Retrieves all administrative Blocks with child Panchayat count and district/state names."
)
async def list_blocks(db: Session = Depends(get_db)) -> APIResponse[List[dict]]:
    blocks = db.scalars(select(Block).order_by(Block.name.asc())).all()
    results = []
    for b in blocks:
        p_count = db.scalar(select(func.count(Panchayat.id)).where(Panchayat.block_id == b.id)) or 0
        results.append({
            "id": b.id,
            "lgd_code": b.lgd_code,
            "name": b.name,
            "district_name": b.district_name,
            "state_name": b.state_name,
            "panchayats_count": p_count,
        })
    return APIResponse(
        success=True,
        message=f"Retrieved {len(results)} blocks.",
        data=results,
    )


@router.get(
    "/geojson",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Panchayat GeoJSON FeatureCollection",
    description="Returns standard GeoJSON FeatureCollection of Gram Panchayats with spatial centroids, eligibility, weather, and risk properties."
)
async def get_panchayats_geojson(
    block_id: Optional[int] = Query(None, description="Optional block filter"),
    db: Session = Depends(get_db)
) -> APIResponse[dict]:
    stmt = select(Panchayat)
    if block_id is not None:
        stmt = stmt.where(Panchayat.block_id == block_id)
    panchayats = db.scalars(stmt).all()

    features = []
    for p in panchayats:
        p_lat, p_lon = SpatialFeatureExtractor.extract_centroid_coordinates(p.centroid or p.geometry)
        lat = p_lat if p_lat is not None else 26.78
        lon = p_lon if p_lon is not None else 82.15

        # Latest weather record if any
        pw = db.scalar(
            select(PanchayatWeather)
            .where(PanchayatWeather.panchayat_id == p.id)
            .order_by(PanchayatWeather.forecast_date.desc())
        )

        is_agri = p.land_use.is_agricultural_eligible if p.land_use else True
        cropland_ha = p.land_use.cropland_area_ha if p.land_use else 0.0

        # Risk count
        risk_count = db.scalar(
            select(func.count(AgriculturalRiskLog.id))
            .where(and_(AgriculturalRiskLog.panchayat_id == p.id, AgriculturalRiskLog.status == "DETECTED"))
        ) or 0

        # Top advisory
        top_adv = db.scalar(
            select(AgroAdvisory)
            .where(AgroAdvisory.panchayat_id == p.id)
            .order_by(AgroAdvisory.priority_rank.asc())
        )

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "id": p.id,
                "lgd_code": p.lgd_code,
                "name": p.name,
                "block_id": p.block_id,
                "block_name": p.block.name if p.block else None,
                "district_name": p.block.district_name if p.block else None,
                "elevation_m": p.elevation_meters,
                "is_agricultural_eligible": is_agri,
                "cropland_ha": cropland_ha,
                "mean_temp_c": pw.mean_temp_c if pw else None,
                "min_temp_c": pw.min_temp_c if pw else None,
                "max_temp_c": pw.max_temp_c if pw else None,
                "weather_status": pw.quality_status if pw else "UNAVAILABLE",
                "coverage_pct": pw.coverage_pct if pw else 0.0,
                "active_risks_count": risk_count,
                "top_advisory_priority": top_adv.priority if top_adv else "NONE",
                "top_advisory_title": top_adv.title if top_adv else None,
            }
        })

    geojson_data = {
        "type": "FeatureCollection",
        "features": features,
    }

    return APIResponse(
        success=True,
        message=f"Generated GeoJSON with {len(features)} Panchayat features.",
        data=geojson_data,
    )


@router.get(
    "/{panchayat_id}/detail",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Consolidated Panchayat Detail Profile",
    description="Delivers complete unified Panchayat profile combining metadata, land-use, latest downscaled weather, crop contexts, detected risks, and active advisories."
)
async def get_panchayat_full_detail(
    panchayat_id: int,
    date: Optional[datetime] = Query(None, description="Target forecast date (defaults to today)"),
    db: Session = Depends(get_db)
) -> APIResponse[dict]:
    eval_dt = date or datetime.utcnow()
    p = db.scalar(select(Panchayat).where(Panchayat.id == panchayat_id))
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panchayat with ID {panchayat_id} not found."
        )

    p_lat, p_lon = SpatialFeatureExtractor.extract_centroid_coordinates(p.centroid or p.geometry)

    # 1. Land Use
    lu_data = None
    if p.land_use:
        lu_data = {
            "total_area_ha": p.land_use.total_area_ha,
            "cropland_area_ha": p.land_use.cropland_area_ha,
            "forest_area_ha": p.land_use.forest_area_ha,
            "urban_area_ha": p.land_use.urban_area_ha,
            "water_area_ha": p.land_use.water_area_ha,
            "barren_area_ha": p.land_use.barren_area_ha,
            "is_agricultural_eligible": p.land_use.is_agricultural_eligible,
        }

    # 2. Latest Weather
    pw = db.scalar(
        select(PanchayatWeather)
        .where(PanchayatWeather.panchayat_id == panchayat_id)
        .order_by(PanchayatWeather.forecast_date.desc())
    )
    weather_data = None
    if pw:
        weather_data = {
            "mean_temp_c": pw.mean_temp_c,
            "min_temp_c": pw.min_temp_c,
            "max_temp_c": pw.max_temp_c,
            "temp_stddev_c": pw.temp_stddev_c,
            "mean_residual_c": pw.mean_residual_c,
            "coverage_pct": pw.coverage_pct,
            "quality_status": pw.quality_status,
            "contributing_grid_cells": pw.contributing_grid_cells,
            "valid_grid_cells": pw.valid_grid_cells,
            "forecast_valid_time": pw.forecast_date.isoformat(),
            "source_model": pw.source_model,
            "model_version": pw.model_version,
        }

    # 3. Agricultural Contexts
    from app.services.agricultural_context import AgriculturalContextService
    agri_svc = AgriculturalContextService(db=db)
    crop_contexts = agri_svc.build_panchayat_crop_context(panchayat_id=panchayat_id, context_date=eval_dt, persist_to_db=False)

    # 4. Agricultural Risks
    from app.services.agricultural_risk import AgriculturalRiskEngine
    risk_engine = AgriculturalRiskEngine(db=db)
    risks = risk_engine.evaluate_panchayat_crop_risks(panchayat_id=panchayat_id, evaluation_date=eval_dt, persist_to_db=False)

    # 5. Agro-Meteorological Advisories
    from app.services.advisory_engine import AdvisoryEngine
    adv_engine = AdvisoryEngine(db=db)
    advisories = adv_engine.generate_panchayat_advisories(panchayat_id=panchayat_id, forecast_date=eval_dt, persist_to_db=False)

    result_data = {
        "panchayat": {
            "id": p.id,
            "lgd_code": p.lgd_code,
            "name": p.name,
            "block_id": p.block_id,
            "block_name": p.block.name if p.block else None,
            "district_name": p.block.district_name if p.block else None,
            "state_name": p.block.state_name if p.block else None,
            "elevation_meters": p.elevation_meters,
            "latitude": p_lat,
            "longitude": p_lon,
        },
        "land_use": lu_data,
        "latest_weather": weather_data,
        "crop_contexts": [c.model_dump() for c in crop_contexts],
        "risks": [r.model_dump() for r in risks],
        "advisories": [a.model_dump() for a in advisories],
    }

    return APIResponse(
        success=True,
        message=f"Consolidated profile retrieved for Panchayat '{p.name}'.",
        data=result_data,
    )

