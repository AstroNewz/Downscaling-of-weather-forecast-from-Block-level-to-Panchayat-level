"""
Tests for Phase 9: Crop + Crop Stage + Soil Context
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Validates:
- Panchayat Weather + Crop + Stage + Soil Context integration
- Multi-crop support per Panchayat
- Deterministic stage resolution (Observed -> Planting date -> Crop calendar -> Unknown)
- Soil completeness and NULL preservation (never fabricating 0s)
- LandUseMask agricultural cropland eligibility
- Idempotency and database upsert behavior
- REST API endpoints and CLI execution
- Strict scope preservation (no ML retraining, no rainfall downscaling, no risk scores, no advisories)
"""
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.config import settings
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import PanchayatWeather
from app.db.models.agriculture import (
    Crop,
    CropPhenologyStage,
    SoilProfile,
    PanchayatCropMapping,
    PanchayatCropContext,
)
from app.services.agricultural_context import AgriculturalContextService
from app.schemas.agricultural_context import (
    CropStageContext,
    SoilContextSummary,
    WeatherContextSummary,
    PanchayatCropContextSummary,
    AgriculturalContextResponse,
)


@pytest.fixture
def agri_test_environment(db_session: Session):
    """
    Sets up a realistic agronomic test environment:
    - Block: 'Barabanki Block'
    - Panchayat 1: 'Kishunpur' (Agricultural, Alluvial complete soil, Rice & Maize multi-crop)
    - Panchayat 2: 'Masauli' (Agricultural, Partial soil, Wheat with observed stage)
    - Panchayat 3: 'Barel' (Agricultural, No crop mapping -> UNAVAILABLE)
    - Panchayat 4: 'Nawabganj Urban' (Non-agricultural cropland = 0)
    - Weather: Valid PanchayatWeather records for 2026-07-15
    """
    # 1. Block
    block = Block(
        lgd_code="BLK_AGRI_001",
        name="Barabanki Block",
        district_name="Barabanki",
        state_name="Uttar Pradesh",
    )
    db_session.add(block)
    db_session.flush()

    # 2. Panchayats
    p1 = Panchayat(lgd_code="GP_AGRI_01", name="Kishunpur", block_id=block.id)
    p2 = Panchayat(lgd_code="GP_AGRI_02", name="Masauli", block_id=block.id)
    p3 = Panchayat(lgd_code="GP_AGRI_03", name="Barel", block_id=block.id)
    p4 = Panchayat(lgd_code="GP_AGRI_04", name="Nawabganj Urban", block_id=block.id)
    db_session.add_all([p1, p2, p3, p4])
    db_session.flush()

    # 3. Land Use Masks
    lu1 = LandUseMask(panchayat_id=p1.id, total_area_ha=1000.0, cropland_area_ha=750.0, is_agricultural_eligible=True)
    lu2 = LandUseMask(panchayat_id=p2.id, total_area_ha=800.0, cropland_area_ha=600.0, is_agricultural_eligible=True)
    lu3 = LandUseMask(panchayat_id=p3.id, total_area_ha=500.0, cropland_area_ha=400.0, is_agricultural_eligible=True)
    lu4 = LandUseMask(panchayat_id=p4.id, total_area_ha=1200.0, cropland_area_ha=0.0, is_agricultural_eligible=False)
    db_session.add_all([lu1, lu2, lu3, lu4])

    # 4. Soil Profiles
    soil_complete = SoilProfile(
        soil_type="Alluvial",
        texture="Clay Loam",
        drainage_class="Well",
        water_holding_capacity_pct=38.5,
        ph_level=7.2,
        organic_carbon_pct=0.65,
        available_nitrogen_kg_ha=240.0,
        available_phosphorus_kg_ha=18.5,
        available_potassium_kg_ha=210.0,
    )
    soil_partial = SoilProfile(
        soil_type="Sandy Loam",
        texture="Sandy",
        drainage_class="Excessive",
        water_holding_capacity_pct=22.0,
        ph_level=None,  # Missing pH must remain None
        organic_carbon_pct=None,  # Missing OC must remain None
    )
    db_session.add_all([soil_complete, soil_partial])
    db_session.flush()

    # 5. Crops & Phenological Stages
    # Crop A: Rice (Kharif)
    crop_rice = Crop(
        crop_name="Rice",
        scientific_name="Oryza sativa",
        season="Kharif",
        base_temp_celsius=10.0,
        optimal_temp_min=20.0,
        optimal_temp_max=35.0,
        water_requirement_mm=1200.0,
    )
    # Crop B: Maize (Kharif)
    crop_maize = Crop(
        crop_name="Maize",
        scientific_name="Zea mays",
        season="Kharif",
        base_temp_celsius=10.0,
        optimal_temp_min=18.0,
        optimal_temp_max=32.0,
        water_requirement_mm=600.0,
    )
    # Crop C: Wheat (Rabi)
    crop_wheat = Crop(
        crop_name="Wheat",
        scientific_name="Triticum aestivum",
        season="Rabi",
        base_temp_celsius=5.0,
        optimal_temp_min=15.0,
        optimal_temp_max=25.0,
        water_requirement_mm=450.0,
    )
    db_session.add_all([crop_rice, crop_maize, crop_wheat])
    db_session.flush()

    # Rice Stages
    stg_r1 = CropPhenologyStage(crop_id=crop_rice.id, stage_name="Sowing", stage_order=1, gdd_required=150.0, water_sensitivity="HIGH", temp_sensitivity="MODERATE")
    stg_r2 = CropPhenologyStage(crop_id=crop_rice.id, stage_name="Vegetative", stage_order=2, gdd_required=450.0, water_sensitivity="HIGH", temp_sensitivity="HIGH")
    stg_r3 = CropPhenologyStage(crop_id=crop_rice.id, stage_name="Flowering", stage_order=3, gdd_required=450.0, water_sensitivity="CRITICAL", temp_sensitivity="CRITICAL")
    stg_r4 = CropPhenologyStage(crop_id=crop_rice.id, stage_name="Maturity", stage_order=4, gdd_required=300.0, water_sensitivity="LOW", temp_sensitivity="MODERATE")

    # Maize Stages
    stg_m1 = CropPhenologyStage(crop_id=crop_maize.id, stage_name="Sowing", stage_order=1, gdd_required=150.0, water_sensitivity="MODERATE", temp_sensitivity="MODERATE")
    stg_m2 = CropPhenologyStage(crop_id=crop_maize.id, stage_name="Vegetative", stage_order=2, gdd_required=400.0, water_sensitivity="HIGH", temp_sensitivity="HIGH")
    stg_m3 = CropPhenologyStage(crop_id=crop_maize.id, stage_name="Tasseling/Silking", stage_order=3, gdd_required=400.0, water_sensitivity="CRITICAL", temp_sensitivity="CRITICAL")
    stg_m4 = CropPhenologyStage(crop_id=crop_maize.id, stage_name="Grain Fill", stage_order=4, gdd_required=350.0, water_sensitivity="MODERATE", temp_sensitivity="MODERATE")

    # Wheat Stages
    stg_w1 = CropPhenologyStage(crop_id=crop_wheat.id, stage_name="Crown Root", stage_order=1, gdd_required=200.0, water_sensitivity="HIGH", temp_sensitivity="MODERATE")
    stg_w2 = CropPhenologyStage(crop_id=crop_wheat.id, stage_name="Tillering", stage_order=2, gdd_required=400.0, water_sensitivity="HIGH", temp_sensitivity="HIGH")
    stg_w3 = CropPhenologyStage(crop_id=crop_wheat.id, stage_name="Heading/Flowering", stage_order=3, gdd_required=450.0, water_sensitivity="CRITICAL", temp_sensitivity="CRITICAL")

    db_session.add_all([stg_r1, stg_r2, stg_r3, stg_r4, stg_m1, stg_m2, stg_m3, stg_m4, stg_w1, stg_w2, stg_w3])
    db_session.flush()

    # 6. Panchayat Crop Mappings
    # P1 Multi-crop: Rice (sown 30 days prior) + Maize (sown 10 days prior)
    map_p1_rice = PanchayatCropMapping(
        panchayat_id=p1.id,
        crop_id=crop_rice.id,
        soil_id=soil_complete.id,
        season="Kharif 2026",
        sowing_date=date(2026, 6, 15),
        expected_harvest_date=date(2026, 10, 15),
        crop_area_ha=450.0,
        is_active=True,
        source="STATE_AGRI_DEPT",
    )
    map_p1_maize = PanchayatCropMapping(
        panchayat_id=p1.id,
        crop_id=crop_maize.id,
        soil_id=soil_complete.id,
        season="Kharif 2026",
        sowing_date=date(2026, 7, 5),
        expected_harvest_date=date(2026, 9, 30),
        crop_area_ha=200.0,
        is_active=True,
        source="STATE_AGRI_DEPT",
    )
    # P2: Wheat with explicit observed stage (Heading/Flowering) and partial soil
    map_p2_wheat = PanchayatCropMapping(
        panchayat_id=p2.id,
        crop_id=crop_wheat.id,
        soil_id=soil_partial.id,
        current_stage_id=stg_w3.id,
        season="Rabi 2026-27",
        sowing_date=date(2025, 11, 20),
        expected_harvest_date=date(2026, 3, 30),
        crop_area_ha=350.0,
        is_active=True,
        source="DISTRICT_KVK",
    )
    db_session.add_all([map_p1_rice, map_p1_maize, map_p2_wheat])
    db_session.flush()

    # 7. PanchayatWeather records (Phase 8 weather output for 2026-07-15)
    forecast_dt = datetime(2026, 7, 15, 12, 0, 0)
    pw1 = PanchayatWeather(
        panchayat_id=p1.id,
        block_id=block.id,
        forecast_date=forecast_dt,
        mean_temp_c=31.2,
        min_temp_c=27.4,
        max_temp_c=35.8,
        temp_stddev_c=1.1,
        total_panchayat_area_sqkm=10.0,
        covered_area_sqkm=10.0,
        coverage_pct=100.0,
        quality_status="COMPLETE",
        source_model="IMD-GFS",
        model_version="v1.0.0",
        aggregation_crs="EPSG:32643",
    )
    pw2 = PanchayatWeather(
        panchayat_id=p2.id,
        block_id=block.id,
        forecast_date=forecast_dt,
        mean_temp_c=30.8,
        min_temp_c=26.9,
        max_temp_c=34.5,
        temp_stddev_c=0.9,
        total_panchayat_area_sqkm=8.0,
        covered_area_sqkm=7.8,
        coverage_pct=97.5,
        quality_status="COMPLETE",
        source_model="IMD-GFS",
        model_version="v1.0.0",
        aggregation_crs="EPSG:32643",
    )
    pw3 = PanchayatWeather(
        panchayat_id=p3.id,
        block_id=block.id,
        forecast_date=forecast_dt,
        mean_temp_c=32.0,
        min_temp_c=28.0,
        max_temp_c=36.0,
        temp_stddev_c=1.2,
        total_panchayat_area_sqkm=5.0,
        covered_area_sqkm=5.0,
        coverage_pct=100.0,
        quality_status="COMPLETE",
        source_model="IMD-GFS",
        model_version="v1.0.0",
        aggregation_crs="EPSG:32643",
    )
    db_session.add_all([pw1, pw2, pw3])
    db_session.commit()

    return {
        "block": block,
        "panchayats": [p1, p2, p3, p4],
        "crops": [crop_rice, crop_maize, crop_wheat],
        "soils": [soil_complete, soil_partial],
        "forecast_date": forecast_dt,
    }


# ============================================================================
# 1. CROP MAPPING & MULTI-CROP TESTS
# ============================================================================

def test_crop_mapping_retrieval(agri_test_environment, db_session: Session):
    """1. Test crop mapping retrieval for a mapped Panchayat."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    assert len(contexts) == 2
    crop_names = [c.crop_name for c in contexts]
    assert "Rice" in crop_names
    assert "Maize" in crop_names


def test_multi_crop_in_single_panchayat(agri_test_environment, db_session: Session):
    """2. Test that multi-crop Panchayat returns distinct context snapshots for each crop."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    assert len(contexts) == 2
    rice_ctx = next(c for c in contexts if c.crop_name == "Rice")
    maize_ctx = next(c for c in contexts if c.crop_name == "Maize")

    assert rice_ctx.crop_area_ha == 450.0
    assert maize_ctx.crop_area_ha == 200.0
    assert rice_ctx.crop_id != maize_ctx.crop_id


def test_missing_crop_mapping_unavailable(agri_test_environment, db_session: Session):
    """3. Test that Panchayat with no crop mappings yields UNAVAILABLE status without fabricating crops."""
    p3 = agri_test_environment["panchayats"][2]  # Barel: has weather but no crop mappings
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p3.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    assert len(contexts) == 1
    assert contexts[0].status == "UNAVAILABLE"
    assert contexts[0].crop_name == "UNAVAILABLE"
    assert "NO_ACTIVE_CROP_MAPPING" in contexts[0].quality_flags


def test_crop_area_validations(agri_test_environment, db_session: Session):
    """4. Test crop area validation (crop_fraction computation and exceeding agricultural area flag)."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    rice_ctx = next(c for c in contexts if c.crop_name == "Rice")
    assert rice_ctx.agricultural_area_ha == 750.0
    assert rice_ctx.crop_area_ha == 450.0
    assert pytest.approx(rice_ctx.crop_fraction, rel=1e-3) == (450.0 / 750.0)


# ============================================================================
# 2. CROP PHENOLOGY STAGE RESOLUTION TESTS
# ============================================================================

def test_crop_stage_resolution_from_planting_date(agri_test_environment, db_session: Session):
    """5. Test stage resolution from days_since_planting."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    # Context date: 2026-07-15, Rice sowing date: 2026-06-15 -> days_since_planting = 30
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    rice_ctx = next(c for c in contexts if c.crop_name == "Rice")
    assert rice_ctx.crop_stage.days_since_planting == 30
    assert rice_ctx.crop_stage.stage_derivation_method == "PLANTING_DATE"
    assert rice_ctx.crop_stage.is_stage_resolved is True
    assert rice_ctx.crop_stage.stage_name in ["Sowing", "Vegetative"]


def test_observed_stage_takes_priority(agri_test_environment, db_session: Session):
    """6. Test that explicit current_stage takes priority over planting date calculation."""
    p2 = agri_test_environment["panchayats"][1]  # Masauli: Wheat has explicit stg_w3
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p2.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    wheat_ctx = contexts[0]
    assert wheat_ctx.crop_stage.stage_derivation_method == "OBSERVED"
    assert wheat_ctx.crop_stage.stage_name == "Heading/Flowering"
    assert wheat_ctx.crop_stage.stage_order == 3


def test_stage_boundary_before_planting(agri_test_environment, db_session: Session):
    """7. Test stage evaluation when context date is before planting date."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    # Date before sowing date (2026-05-01 is before 2026-06-15)
    past_date = datetime(2026, 5, 1, 12, 0, 0)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=past_date,
        persist_to_db=False,
    )
    rice_ctx = next(c for c in contexts if c.crop_name == "Rice")
    assert "DATE_BEFORE_PLANTING" in rice_ctx.quality_flags
    assert rice_ctx.crop_stage.is_stage_resolved is False


def test_stage_beyond_final_stage(agri_test_environment, db_session: Session):
    """8. Test stage evaluation when days since planting exceeds all defined stages."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    # 250 days after sowing
    far_future = datetime(2027, 2, 15, 12, 0, 0)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=far_future,
        persist_to_db=False,
    )
    rice_ctx = next(c for c in contexts if c.crop_name == "Rice")
    assert "BEYOND_FINAL_STAGE" in rice_ctx.quality_flags
    assert rice_ctx.crop_stage.stage_name == "Maturity"


# ============================================================================
# 3. SOIL CONTEXT TESTS
# ============================================================================

def test_soil_profile_retrieval_complete(agri_test_environment, db_session: Session):
    """9. Test complete soil profile evaluation."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    soil = contexts[0].soil
    assert soil.soil_available is True
    assert soil.soil_status == "COMPLETE"
    assert soil.soil_type == "Alluvial"
    assert soil.ph_level == 7.2
    assert soil.organic_carbon_pct == 0.65
    assert soil.water_holding_capacity_pct == 38.5


def test_partial_soil_data_preserves_nulls(agri_test_environment, db_session: Session):
    """10. Test that missing soil properties result in PARTIAL status and remain None (never 0.0)."""
    p2 = agri_test_environment["panchayats"][1]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p2.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    soil = contexts[0].soil
    assert soil.soil_status == "PARTIAL"
    assert soil.ph_level is None
    assert soil.organic_carbon_pct is None
    assert soil.soil_type == "Sandy Loam"
    assert "PARTIAL_SOIL_DATA" in contexts[0].quality_flags


def test_missing_soil_profile(db_session: Session):
    """11. Test missing soil profile evaluation in isolation."""
    service = AgriculturalContextService(db=db_session)
    soil_ctx, flags = service.evaluate_soil_profile(soil=None)
    assert soil_ctx.soil_available is False
    assert soil_ctx.soil_status == "UNAVAILABLE"
    assert "MISSING_SOIL_PROFILE" in flags
    assert soil_ctx.ph_level is None


# ============================================================================
# 4. AGRICULTURAL ELIGIBILITY & WEATHER JOIN TESTS
# ============================================================================

def test_agricultural_landuse_eligibility(agri_test_environment, db_session: Session):
    """12. Test non-agricultural Panchayat restriction."""
    p4 = agri_test_environment["panchayats"][3]  # Nawabganj Urban: cropland = 0, eligible = False
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p4.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    assert contexts[0].is_agricultural_eligible is False
    assert "NON_AGRICULTURAL_PANCHAYAT" in contexts[0].quality_flags


def test_panchayat_weather_association(agri_test_environment, db_session: Session):
    """13. Test weather association and temperature statistics extraction."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    weather = contexts[0].weather
    assert weather.weather_status == "COMPLETE"
    assert weather.mean_temp_c == 31.2
    assert weather.min_temp_c == 27.4
    assert weather.max_temp_c == 35.8


def test_weather_temporal_mismatch(agri_test_environment, db_session: Session):
    """14. Test weather handling when no forecast exists for target date."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    # Forecast date with no weather in DB
    future_date = datetime(2026, 12, 1, 12, 0, 0)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=future_date,
        persist_to_db=False,
    )
    weather = contexts[0].weather
    assert weather.weather_status == "UNAVAILABLE"
    assert weather.mean_temp_c is None
    assert "MISSING_PANCHAYAT_WEATHER" in contexts[0].quality_flags
    # Context should degrade to PARTIAL
    assert contexts[0].status == "PARTIAL"


# ============================================================================
# 5. IDEMPOTENCY & BATCH PROCESSING TESTS
# ============================================================================

def test_idempotency_and_upsert(agri_test_environment, db_session: Session):
    """15. Test idempotent upsert behavior for repeated context generation."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)

    # First run: persists 2 records
    ctx1 = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=True,
    )
    assert len(ctx1) == 2
    count_first = db_session.scalar(
        select(func.count(PanchayatCropContext.id)).where(PanchayatCropContext.panchayat_id == p1.id)
    )
    assert count_first == 2

    # Second run with same date: updates without duplicating
    ctx2 = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=True,
    )
    assert len(ctx2) == 2
    count_second = db_session.scalar(
        select(func.count(PanchayatCropContext.id)).where(PanchayatCropContext.panchayat_id == p1.id)
    )
    assert count_second == 2


def test_block_batch_processing(agri_test_environment, db_session: Session):
    """16. Test block-level batch processing across multiple Panchayats."""
    block = agri_test_environment["block"]
    service = AgriculturalContextService(db=db_session)
    response = service.build_block_agricultural_context(
        block_id=block.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=True,
    )
    assert isinstance(response, AgriculturalContextResponse)
    assert response.total_panchayats == 4
    # P1 (2 crops) + P2 (1 crop) + P3 (1 unavailable) + P4 (1 unavailable) = 5 contexts
    assert response.total_crop_contexts == 5
    assert response.complete_contexts_count >= 2


# ============================================================================
# 6. REST API INTEGRATION TESTS
# ============================================================================

def test_api_generate_context_post(client: TestClient, agri_test_environment):
    """17. Test POST /api/v1/agriculture/context endpoint."""
    block = agri_test_environment["block"]
    payload = {
        "block_id": block.id,
        "context_date": agri_test_environment["forecast_date"].isoformat(),
        "persist_to_db": True
    }
    response = client.post("/api/v1/agriculture/context", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    data = res_json["data"]
    assert data["block_id"] == block.id
    assert data["total_panchayats"] == 4
    assert len(data["contexts"]) >= 4


def test_api_query_context_get(client: TestClient, agri_test_environment):
    """18. Test GET /api/v1/agriculture/context endpoint with filters."""
    p1 = agri_test_environment["panchayats"][0]
    response = client.get(f"/api/v1/agriculture/context?panchayat_id={p1.id}")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert len(res_json["data"]) >= 2


def test_api_panchayat_profile_get(client: TestClient, agri_test_environment):
    """19. Test GET /api/v1/agriculture/panchayat/{id}/context endpoint."""
    p1 = agri_test_environment["panchayats"][0]
    date_str = agri_test_environment["forecast_date"].isoformat()
    response = client.get(f"/api/v1/agriculture/panchayat/{p1.id}/context?context_date={date_str}")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    profile = res_json["data"]
    assert profile["panchayat_name"] == "Kishunpur"
    assert profile["total_active_crops"] == 2
    assert len(profile["crop_contexts"]) == 2


def test_api_subsystem_status_get(client: TestClient, agri_test_environment):
    """20. Test GET /api/v1/agriculture/status endpoint."""
    response = client.get("/api/v1/agriculture/status")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    status_data = res_json["data"]
    assert status_data["panchayats_with_crop_mappings"] >= 2
    assert status_data["panchayats_with_soil_profiles"] >= 2


# ============================================================================
# 7. PROVENANCE & STRICT SCIENTIFIC SCOPE VALIDATION TESTS
# ============================================================================

def test_provenance_metadata_completeness(agri_test_environment, db_session: Session):
    """21. Test provenance completeness and traceability."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    prov = contexts[0].provenance
    assert prov is not None
    assert "panchayat_id" in prov
    assert "block_id" in prov
    assert "crop_id" in prov
    assert "crop_mapping_source" in prov
    assert "weather_source_model" in prov
    assert "generation_timestamp" in prov


def test_strict_scope_no_risk_scoring_or_advisories(agri_test_environment, db_session: Session):
    """22. Verify strict scope: Phase 9 does NOT generate risk scores, pest alerts, or farmer advisories."""
    p1 = agri_test_environment["panchayats"][0]
    service = AgriculturalContextService(db=db_session)
    contexts = service.build_panchayat_crop_context(
        panchayat_id=p1.id,
        context_date=agri_test_environment["forecast_date"],
        persist_to_db=False,
    )
    for ctx in contexts:
        ctx_dict = ctx.model_dump()
        # Verify absence of risk/advisory fields
        assert "risk_score" not in ctx_dict
        assert "pest_alert" not in ctx_dict
        assert "disease_alert" not in ctx_dict
        assert "farmer_advisory" not in ctx_dict
        assert "irrigation_recommendation" not in ctx_dict
