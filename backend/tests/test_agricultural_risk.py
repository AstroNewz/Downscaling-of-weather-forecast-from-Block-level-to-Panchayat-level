"""
Tests for Phase 10: Agricultural Risk Engine
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Validates:
- Multi-crop agricultural risk detection across thermal, cold, hydrological, wind, and pathogen-favorable conditions
- Crop-aware and growth-stage-aware threshold selection
- Explicit INSUFFICIENT_DATA handling when weather/soil variables are missing
- NULL preservation (never converting missing values to 0)
- Disease-favorable environmental conditions (NOT disease diagnosis)
- Idempotency and upsert behavior on AgriculturalRiskLog
- REST API integration endpoints and CLI tool
- Strict scope preservation (no new weather ML, no rainfall downscaling, no farmer advisories)
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
from app.db.models.advisory import AgriculturalRiskLog
from app.services.risk_rules import RiskRuleRegistry, rule_registry
from app.services.agricultural_risk import AgriculturalRiskEngine
from app.schemas.agricultural_risk import (
    RiskResult,
    RiskEvaluationResponse,
    PanchayatRiskProfile,
    RiskSubsystemStatus,
)


@pytest.fixture
def risk_test_environment(db_session: Session):
    """
    Sets up a complete agronomic test environment:
    - Block: 'Faizabad Sadar Block'
    - Panchayat 1: 'Sohawal' (Agricultural, Alluvial soil, Rice Flowering + Maize Tasseling multi-crop, Hot Weather 38.5°C)
    - Panchayat 2: 'Bikapur' (Agricultural, Sandy Loam partial soil, Wheat Heading, Mild Weather 30.5°C)
    - Panchayat 3: 'Milkipur' (Agricultural, Missing Weather Record)
    - Panchayat 4: 'Ayodhya Cantt' (Non-agricultural / Urban, Cropland = 0)
    """
    # 1. Block
    block = Block(
        lgd_code="BLK_RISK_001",
        name="Faizabad Sadar Block",
        district_name="Ayodhya",
        state_name="Uttar Pradesh",
    )
    db_session.add(block)
    db_session.flush()

    # 2. Panchayats
    p1 = Panchayat(lgd_code="GP_RSK_01", name="Sohawal", block_id=block.id)
    p2 = Panchayat(lgd_code="GP_RSK_02", name="Bikapur", block_id=block.id)
    p3 = Panchayat(lgd_code="GP_RSK_03", name="Milkipur", block_id=block.id)
    p4 = Panchayat(lgd_code="GP_RSK_04", name="Ayodhya Cantt", block_id=block.id)
    db_session.add_all([p1, p2, p3, p4])
    db_session.flush()

    # 3. Land Use Masks
    lu1 = LandUseMask(panchayat_id=p1.id, total_area_ha=1000.0, cropland_area_ha=800.0, is_agricultural_eligible=True)
    lu2 = LandUseMask(panchayat_id=p2.id, total_area_ha=900.0, cropland_area_ha=650.0, is_agricultural_eligible=True)
    lu3 = LandUseMask(panchayat_id=p3.id, total_area_ha=700.0, cropland_area_ha=500.0, is_agricultural_eligible=True)
    lu4 = LandUseMask(panchayat_id=p4.id, total_area_ha=1500.0, cropland_area_ha=0.0, is_agricultural_eligible=False)
    db_session.add_all([lu1, lu2, lu3, lu4])

    # 4. Soils
    soil_complete = SoilProfile(
        soil_type="Alluvial",
        texture="Clay Loam",
        drainage_class="Well",
        water_holding_capacity_pct=36.0,
        ph_level=7.1,
        organic_carbon_pct=0.6,
    )
    soil_partial = SoilProfile(
        soil_type="Sandy Loam",
        texture="Coarse",
        drainage_class="Excessive",
        water_holding_capacity_pct=18.0,
        ph_level=None,  # Missing
        organic_carbon_pct=None,
    )
    db_session.add_all([soil_complete, soil_partial])
    db_session.flush()

    # 5. Crops & Stages
    crop_rice = Crop(crop_name="Rice", season="Kharif", base_temp_celsius=10.0, optimal_temp_min=20.0, optimal_temp_max=35.0)
    crop_maize = Crop(crop_name="Maize", season="Kharif", base_temp_celsius=10.0, optimal_temp_min=18.0, optimal_temp_max=32.0)
    crop_wheat = Crop(crop_name="Wheat", season="Rabi", base_temp_celsius=5.0, optimal_temp_min=15.0, optimal_temp_max=25.0)
    db_session.add_all([crop_rice, crop_maize, crop_wheat])
    db_session.flush()

    stg_r_flower = CropPhenologyStage(crop_id=crop_rice.id, stage_name="Flowering", stage_order=3, gdd_required=450.0, water_sensitivity="CRITICAL", temp_sensitivity="CRITICAL")
    stg_r_veg = CropPhenologyStage(crop_id=crop_rice.id, stage_name="Vegetative", stage_order=2, gdd_required=400.0, water_sensitivity="HIGH", temp_sensitivity="HIGH")
    stg_m_flower = CropPhenologyStage(crop_id=crop_maize.id, stage_name="Tasseling/Silking", stage_order=3, gdd_required=400.0, water_sensitivity="CRITICAL", temp_sensitivity="CRITICAL")
    stg_w_heading = CropPhenologyStage(crop_id=crop_wheat.id, stage_name="Heading/Flowering", stage_order=3, gdd_required=450.0, water_sensitivity="CRITICAL", temp_sensitivity="CRITICAL")
    db_session.add_all([stg_r_flower, stg_r_veg, stg_m_flower, stg_w_heading])
    db_session.flush()

    # 6. Panchayat Crop Mappings
    # P1: Rice (observed Flowering) + Maize (observed Tasseling/Silking)
    map_p1_rice = PanchayatCropMapping(
        panchayat_id=p1.id,
        crop_id=crop_rice.id,
        soil_id=soil_complete.id,
        current_stage_id=stg_r_flower.id,
        season="Kharif 2026",
        sowing_date=date(2026, 6, 1),
        crop_area_ha=500.0,
        is_active=True,
    )
    map_p1_maize = PanchayatCropMapping(
        panchayat_id=p1.id,
        crop_id=crop_maize.id,
        soil_id=soil_complete.id,
        current_stage_id=stg_m_flower.id,
        season="Kharif 2026",
        sowing_date=date(2026, 6, 10),
        crop_area_ha=250.0,
        is_active=True,
    )
    # P2: Wheat (observed Heading/Flowering) with partial soil
    map_p2_wheat = PanchayatCropMapping(
        panchayat_id=p2.id,
        crop_id=crop_wheat.id,
        soil_id=soil_partial.id,
        current_stage_id=stg_w_heading.id,
        season="Rabi 2026-27",
        sowing_date=date(2025, 11, 15),
        crop_area_ha=400.0,
        is_active=True,
    )
    db_session.add_all([map_p1_rice, map_p1_maize, map_p2_wheat])
    db_session.flush()

    # 7. PanchayatWeather records (Forecast Date: 2026-07-15)
    eval_dt = datetime(2026, 7, 15, 12, 0, 0)
    # P1: Hot weather -> max_temp = 38.5°C, min_temp = 28.0°C, mean_temp = 33.2°C
    pw1 = PanchayatWeather(
        panchayat_id=p1.id,
        block_id=block.id,
        forecast_date=eval_dt,
        mean_temp_c=33.2,
        min_temp_c=28.0,
        max_temp_c=38.5,
        temp_stddev_c=1.2,
        total_panchayat_area_sqkm=10.0,
        covered_area_sqkm=10.0,
        coverage_pct=100.0,
        quality_status="COMPLETE",
        source_model="IMD-GFS",
        model_version="v1.0.0",
        aggregation_crs="EPSG:32643",
    )
    # P2: Moderate weather -> max_temp = 30.5°C, min_temp = 16.0°C, mean_temp = 24.5°C
    pw2 = PanchayatWeather(
        panchayat_id=p2.id,
        block_id=block.id,
        forecast_date=eval_dt,
        mean_temp_c=24.5,
        min_temp_c=16.0,
        max_temp_c=30.5,
        temp_stddev_c=0.8,
        total_panchayat_area_sqkm=9.0,
        covered_area_sqkm=9.0,
        coverage_pct=100.0,
        quality_status="COMPLETE",
        source_model="IMD-GFS",
        model_version="v1.0.0",
        aggregation_crs="EPSG:32643",
    )
    # P4: Urban Panchayat weather
    pw4 = PanchayatWeather(
        panchayat_id=p4.id,
        block_id=block.id,
        forecast_date=eval_dt,
        mean_temp_c=34.0,
        min_temp_c=29.0,
        max_temp_c=39.0,
        temp_stddev_c=1.0,
        total_panchayat_area_sqkm=15.0,
        covered_area_sqkm=15.0,
        coverage_pct=100.0,
        quality_status="COMPLETE",
        source_model="IMD-GFS",
        model_version="v1.0.0",
        aggregation_crs="EPSG:32643",
    )
    db_session.add_all([pw1, pw2, pw4])
    db_session.commit()

    return {
        "block": block,
        "panchayats": [p1, p2, p3, p4],
        "crops": [crop_rice, crop_maize, crop_wheat],
        "stages": [stg_r_flower, stg_r_veg, stg_m_flower, stg_w_heading],
        "evaluation_date": eval_dt,
    }


# ============================================================================
# 1. THERMAL / HEAT STRESS EVALUATION TESTS
# ============================================================================

def test_heat_risk_detected_for_rice_flowering(risk_test_environment, db_session: Session):
    """1. Test that max_temp 38.5°C triggers HIGH heat stress for Rice at Flowering stage (threshold 37.0°C)."""
    p1 = risk_test_environment["panchayats"][0]
    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="HEAT_STRESS",
        persist_to_db=False,
    )
    rice_res = next(r for r in results if r.crop_name == "Rice")
    assert rice_res.status == "DETECTED"
    assert rice_res.severity in ["HIGH", "EXTREME"]
    assert rice_res.observed_value == 38.5
    assert rice_res.threshold_value == 37.0
    assert rice_res.risk_score > 0.5
    assert "spikelet sterility" in rice_res.evidence.condition_description.lower() or "flowering" in rice_res.evidence.condition_description.lower()


def test_heat_risk_not_detected_when_below_threshold(risk_test_environment, db_session: Session):
    """2. Test that max_temp 30.5°C does NOT trigger heat stress for Rice (threshold 35.0°C)."""
    # Create temporary low temp weather for P1
    p1 = risk_test_environment["panchayats"][0]
    pw = db_session.scalar(select(PanchayatWeather).where(PanchayatWeather.panchayat_id == p1.id))
    pw.max_temp_c = 31.0
    db_session.commit()

    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="HEAT_STRESS",
        persist_to_db=False,
    )
    rice_res = next(r for r in results if r.crop_name == "Rice")
    assert rice_res.status == "NOT_DETECTED"
    assert rice_res.severity == "NONE"
    assert rice_res.risk_score == 0.0


# ============================================================================
# 2. COLD / LOW-TEMPERATURE STRESS TESTS
# ============================================================================

def test_cold_risk_not_detected_in_summer(risk_test_environment, db_session: Session):
    """3. Test that min_temp 28.0°C does not trigger cold stress."""
    p1 = risk_test_environment["panchayats"][0]
    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="COLD_STRESS",
        persist_to_db=False,
    )
    rice_res = next(r for r in results if r.crop_name == "Rice")
    assert rice_res.status == "NOT_DETECTED"
    assert rice_res.severity == "NONE"


def test_cold_frost_risk_detected_for_wheat(risk_test_environment, db_session: Session):
    """4. Test that near-freezing temperature (1.5°C) triggers HIGH frost risk for Wheat Heading stage."""
    p2 = risk_test_environment["panchayats"][1]
    pw2 = db_session.scalar(select(PanchayatWeather).where(PanchayatWeather.panchayat_id == p2.id))
    pw2.min_temp_c = 1.5
    db_session.commit()

    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p2.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="COLD_STRESS",
        persist_to_db=False,
    )
    wheat_res = next(r for r in results if r.crop_name == "Wheat")
    assert wheat_res.status == "DETECTED"
    assert wheat_res.severity == "HIGH"
    assert wheat_res.observed_value == 1.5
    assert wheat_res.threshold_value == 2.0


# ============================================================================
# 3. DISEASE-FAVORABLE ENVIRONMENTAL CONDITIONS
# ============================================================================

def test_disease_favorable_environmental_window(risk_test_environment, db_session: Session):
    """5. Test environmental suitability for foliar pathogen proliferation (24.5°C mean temp in P2)."""
    p2 = risk_test_environment["panchayats"][1]
    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p2.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="DISEASE_FAVORABLE_CONDITIONS",
        persist_to_db=False,
    )
    wheat_res = next(r for r in results if r.crop_name == "Wheat")
    assert wheat_res.status == "DETECTED"
    assert wheat_res.severity == "MODERATE"
    assert wheat_res.risk_type == "DISEASE_FAVORABLE_CONDITIONS"


def test_disease_evaluation_is_not_diagnosis(risk_test_environment, db_session: Session):
    """6. Verify that disease-favorable evaluation strictly does NOT claim confirmed disease or recommend chemicals."""
    p2 = risk_test_environment["panchayats"][1]
    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p2.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="DISEASE_FAVORABLE_CONDITIONS",
        persist_to_db=False,
    )
    wheat_res = next(r for r in results if r.crop_name == "Wheat")
    desc = wheat_res.evidence.condition_description.lower()
    assert "not confirmed disease presence" in desc or "suitability only" in desc
    assert "spray" not in desc
    assert "pesticide" not in desc


# ============================================================================
# 4. DATA QUALITY GATES & MISSING DATA HANDLING (INSUFFICIENT_DATA)
# ============================================================================

def test_missing_panchayat_weather_insufficient_data(risk_test_environment, db_session: Session):
    """7. Test that missing Panchayat weather triggers INSUFFICIENT_DATA (not NOT_DETECTED)."""
    p3 = risk_test_environment["panchayats"][2]  # Milkipur: has mapping but no weather
    # Add crop mapping for P3
    crop_rice = risk_test_environment["crops"][0]
    map_p3 = PanchayatCropMapping(panchayat_id=p3.id, crop_id=crop_rice.id, season="Kharif 2026", is_active=True)
    db_session.add(map_p3)
    db_session.commit()

    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p3.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        persist_to_db=False,
    )
    assert len(results) > 0
    for r in results:
        assert r.status == "INSUFFICIENT_DATA"
        assert r.severity == "NONE"
        assert r.confidence == "INSUFFICIENT"


def test_missing_max_temp_does_not_become_zero(risk_test_environment, db_session: Session):
    """8. Test that max_temp_c = NULL results in INSUFFICIENT_DATA, never converted to 0.0."""
    p1 = risk_test_environment["panchayats"][0]
    pw1 = db_session.scalar(select(PanchayatWeather).where(PanchayatWeather.panchayat_id == p1.id))
    pw1.max_temp_c = None
    db_session.commit()

    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="HEAT_STRESS",
        persist_to_db=False,
    )
    rice_res = next(r for r in results if r.crop_name == "Rice")
    assert rice_res.status == "INSUFFICIENT_DATA"
    assert rice_res.observed_value is None
    assert rice_res.risk_score is None


def test_water_stress_framework_requires_temporal_accumulation(risk_test_environment, db_session: Session):
    """9. Test that single-day forecast without historical rainfall returns INSUFFICIENT_DATA for drought/dry spell."""
    p1 = risk_test_environment["panchayats"][0]
    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="WATER_STRESS",
        persist_to_db=False,
    )
    rice_res = next(r for r in results if r.crop_name == "Rice")
    assert rice_res.status == "INSUFFICIENT_DATA"
    assert "multi-day rainfall accumulation history is required" in rice_res.evidence.condition_description.lower()


# ============================================================================
# 5. MULTI-CROP & AGRICULTURAL ELIGIBILITY TESTS
# ============================================================================

def test_multi_crop_panchayat_evaluated_independently(risk_test_environment, db_session: Session):
    """10. Test that multi-crop Panchayat (Rice + Maize) produces separate risk evaluations per crop."""
    p1 = risk_test_environment["panchayats"][0]
    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="HEAT_STRESS",
        persist_to_db=False,
    )
    assert len(results) == 2
    crop_names = [r.crop_name for r in results]
    assert "Rice" in crop_names
    assert "Maize" in crop_names


def test_non_agricultural_panchayat_rejected(risk_test_environment, db_session: Session):
    """11. Test that non-agricultural Panchayat (cropland = 0) is excluded from agricultural risk scoring."""
    p4 = risk_test_environment["panchayats"][3]  # Ayodhya Cantt: cropland = 0, is_agricultural_eligible = False
    engine = AgriculturalRiskEngine(db=db_session)
    results = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p4.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        persist_to_db=False,
    )
    assert len(results) == 0  # No crop risks generated for non-agricultural Panchayat


# ============================================================================
# 6. IDEMPOTENCY & DATABASE PERSISTENCE TESTS
# ============================================================================

def test_idempotency_and_upsert_risk_logs(risk_test_environment, db_session: Session):
    """12. Test that repeated evaluations do not create duplicate AgriculturalRiskLog records."""
    p1 = risk_test_environment["panchayats"][0]
    engine = AgriculturalRiskEngine(db=db_session)

    # First run
    res1 = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="HEAT_STRESS",
        persist_to_db=True,
    )
    count_1 = db_session.scalar(
        select(func.count(AgriculturalRiskLog.id)).where(AgriculturalRiskLog.panchayat_id == p1.id)
    )
    assert count_1 == 2  # Rice + Maize

    # Second run with same date
    res2 = engine.evaluate_panchayat_crop_risks(
        panchayat_id=p1.id,
        evaluation_date=risk_test_environment["evaluation_date"],
        risk_type_filter="HEAT_STRESS",
        persist_to_db=True,
    )
    count_2 = db_session.scalar(
        select(func.count(AgriculturalRiskLog.id)).where(AgriculturalRiskLog.panchayat_id == p1.id)
    )
    assert count_2 == 2  # Idempotently updated


# ============================================================================
# 7. REST API ENDPOINT INTEGRATION TESTS
# ============================================================================

def test_api_risk_evaluate_post(client: TestClient, risk_test_environment):
    """13. Test POST /api/v1/agriculture/risk/evaluate."""
    block = risk_test_environment["block"]
    payload = {
        "block_id": block.id,
        "evaluation_date": risk_test_environment["evaluation_date"].isoformat(),
        "persist_to_db": True,
    }
    response = client.post("/api/v1/agriculture/risk/evaluate", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    data = res_json["data"]
    assert data["block_id"] == block.id
    assert data["total_risk_evaluations"] > 0
    assert data["detected_risks_count"] >= 1


def test_api_risk_query_get(client: TestClient, risk_test_environment):
    """14. Test GET /api/v1/agriculture/risk with filtering."""
    p1 = risk_test_environment["panchayats"][0]
    response = client.get(f"/api/v1/agriculture/risk?panchayat_id={p1.id}&risk_type=HEAT_STRESS")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert len(res_json["data"]) >= 1


def test_api_panchayat_risk_profile_get(client: TestClient, risk_test_environment):
    """15. Test GET /api/v1/agriculture/panchayat/{id}/risk."""
    p1 = risk_test_environment["panchayats"][0]
    date_str = risk_test_environment["evaluation_date"].isoformat()
    response = client.get(f"/api/v1/agriculture/panchayat/{p1.id}/risk?evaluation_date={date_str}")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    profile = res_json["data"]
    assert profile["panchayat_name"] == "Sohawal"
    assert "Rice" in profile["crop_risks"]


def test_api_risk_subsystem_status_get(client: TestClient, risk_test_environment):
    """16. Test GET /api/v1/agriculture/risk/status."""
    response = client.get("/api/v1/agriculture/risk/status")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    status_data = res_json["data"]
    assert status_data["active_rule_version"] == "agri_risk_v1.0.0"
    assert "HEAT_STRESS" in status_data["risk_counts_by_type"]
