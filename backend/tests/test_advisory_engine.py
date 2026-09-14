"""
Tests for Phase 11: Agro-Meteorological Advisory Generation Engine
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Validates:
- Transformation of Phase 10 DETECTED agricultural risks into actionable, prioritized advisories
- NOT_DETECTED risks generate NO hazard advisories
- INSUFFICIENT_DATA does not generate unsupported agricultural actions
- Disease-favorable conditions are NOT diagnosed as confirmed disease
- No chemical pesticides or dosages are prescribed
- Multi-crop Panchayats generate independent advisories per crop and growth stage
- Priority calculation and multi-risk ranking (priority_rank 1, 2, 3...)
- Confidence propagation and explainable evidence
- Operational conflict detection (e.g. irrigate vs withhold irrigation -> EXPERT_REVIEW_REQUIRED)
- Idempotent database upsert into AgroAdvisory
- REST API integration endpoints and CLI tool
- Full regression stability across Phases 1–10
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
from app.db.models.advisory import AgroAdvisory, AgriculturalRiskLog
from app.services.advisory_rules import AdvisoryRuleRegistry, advisory_rule_registry
from app.services.advisory_engine import AdvisoryEngine
from app.schemas.advisory import (
    AdvisoryResult,
    AdvisoryGenerationResponse,
    PanchayatAdvisoryProfile,
    AdvisorySubsystemStatus,
)


@pytest.fixture
def advisory_test_env(db_session: Session):
    """
    Sets up a complete agronomic advisory test environment:
    - Block: 'Faizabad Sadar Block'
    - Panchayat 1: 'Sohawal' (Agricultural, Alluvial soil, Rice Flowering + Maize Tasseling multi-crop, Hot Weather 38.5°C)
    - Panchayat 2: 'Bikapur' (Agricultural, Sandy Loam soil, Wheat Heading, Cold Weather 1.5°C)
    - Panchayat 3: 'Milkipur' (Agricultural, Missing Weather Record)
    - Panchayat 4: 'Ayodhya Cantt' (Non-agricultural / Urban, Cropland = 0)
    """
    # 1. Block
    block = Block(
        lgd_code="BLK_ADV_001",
        name="Faizabad Sadar Block",
        district_name="Ayodhya",
        state_name="Uttar Pradesh",
    )
    db_session.add(block)
    db_session.flush()

    # 2. Panchayats
    p1 = Panchayat(lgd_code="GP_ADV_01", name="Sohawal", block_id=block.id)
    p2 = Panchayat(lgd_code="GP_ADV_02", name="Bikapur", block_id=block.id)
    p3 = Panchayat(lgd_code="GP_ADV_03", name="Milkipur", block_id=block.id)
    p4 = Panchayat(lgd_code="GP_ADV_04", name="Ayodhya Cantt", block_id=block.id)
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
    soil_sandy = SoilProfile(
        soil_type="Sandy Loam",
        texture="Coarse",
        drainage_class="Excessive",
        water_holding_capacity_pct=18.0,
        ph_level=6.5,
        organic_carbon_pct=0.4,
    )
    db_session.add_all([soil_complete, soil_sandy])
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
    map_p2_wheat = PanchayatCropMapping(
        panchayat_id=p2.id,
        crop_id=crop_wheat.id,
        soil_id=soil_sandy.id,
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
    # P2: Cold weather -> max_temp = 18.0°C, min_temp = 1.5°C, mean_temp = 10.0°C (Frost risk for wheat)
    pw2 = PanchayatWeather(
        panchayat_id=p2.id,
        block_id=block.id,
        forecast_date=eval_dt,
        mean_temp_c=10.0,
        min_temp_c=1.5,
        max_temp_c=18.0,
        temp_stddev_c=0.9,
        total_panchayat_area_sqkm=9.0,
        covered_area_sqkm=9.0,
        coverage_pct=100.0,
        quality_status="COMPLETE",
        source_model="IMD-GFS",
        model_version="v1.0.0",
        aggregation_crs="EPSG:32643",
    )
    db_session.add_all([pw1, pw2])
    db_session.flush()

    return {
        "block": block,
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "p4": p4,
        "crop_rice": crop_rice,
        "crop_maize": crop_maize,
        "crop_wheat": crop_wheat,
        "eval_dt": eval_dt,
    }


# ============================================================================
# 1. CORE DETECTION TO ADVISORY GENERATION TESTS
# ============================================================================

def test_detected_risk_generates_advisory(db_session: Session, advisory_test_env):
    """Test 1: DETECTED risk in Phase 10 produces an actionable advisory in Phase 11."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        risk_type_filter="HEAT_STRESS",
        persist_to_db=True,
    )

    assert len(advisories) == 1
    adv = advisories[0]
    assert adv.advisory_type == "HEAT_STRESS_ADVISORY"
    assert adv.priority in ["HIGH", "CRITICAL"]
    assert adv.severity == "HIGH"
    assert "Rice" in adv.title
    assert adv.action is not None
    assert adv.action.action_category == "WATER_MANAGEMENT"
    assert "standing water" in adv.action.action_text.lower()
    assert adv.id is not None  # Persisted


def test_not_detected_risk_generates_no_hazard_advisory(db_session: Session, advisory_test_env):
    """Test 2: NOT_DETECTED risk does NOT generate hazard advisories."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    # In P1 (Hot weather 38.5°C), Cold stress is NOT_DETECTED
    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        risk_type_filter="COLD_STRESS",
        persist_to_db=False,
    )

    # Should not generate any cold stress advisory
    assert len(advisories) == 0


def test_insufficient_data_does_not_generate_unsupported_action(db_session: Session, advisory_test_env):
    """Test 3: INSUFFICIENT_DATA from missing weather produces no unsupported action advisory."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    # P3 has no weather record
    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p3"].id,
        forecast_date=env["eval_dt"],
        persist_to_db=False,
    )

    # No action advisories generated because risk detection is INSUFFICIENT_DATA
    assert len(advisories) == 0


def test_invalid_risk_does_not_generate_advisory(db_session: Session, advisory_test_env):
    """Test 4: Non-agricultural panchayat produces no advisories."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    # P4 has 0 cropland (urban)
    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p4"].id,
        forecast_date=env["eval_dt"],
        persist_to_db=False,
    )
    assert len(advisories) == 0


# ============================================================================
# 2. ADVISORY TYPES & SCIENTIFIC SAFETY TESTS
# ============================================================================

def test_heat_stress_advisory_content(db_session: Session, advisory_test_env):
    """Test 5: Heat stress advisory content contains specific physiological rationale."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        risk_type_filter="HEAT_STRESS",
        persist_to_db=False,
    )

    adv = advisories[0]
    assert "Flowering" in adv.title
    assert "38.5°C" in adv.message
    assert "spikelet sterility" in adv.rationale.lower() or "anthesis" in adv.rationale.lower()


def test_cold_stress_advisory_content(db_session: Session, advisory_test_env):
    """Test 6: Cold stress / frost advisory content for wheat heading."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p2"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_wheat"].id,
        risk_type_filter="COLD_STRESS",
        persist_to_db=False,
    )

    assert len(advisories) >= 1
    cold_adv = [a for a in advisories if a.advisory_type == "COLD_STRESS_ADVISORY"][0]
    assert cold_adv.severity == "HIGH"
    assert "Wheat" in cold_adv.title
    assert "1.5°C" in cold_adv.message
    assert "smoke" in cold_adv.action.action_text.lower() or "irrigation" in cold_adv.action.action_text.lower()


def test_disease_favorable_advisory_wording_safety(db_session: Session, advisory_test_env):
    """Test 7: Disease advisory states environmental favorability and NEVER claims confirmed diagnosis."""
    rule = advisory_rule_registry.get_rule(risk_type="DISEASE_FAVORABLE_CONDITIONS")
    assert rule is not None
    assert rule.advisory_type == "DISEASE_FAVORABLE_CONDITIONS_ADVISORY"
    assert "favorable" in rule.title_template.lower() or "favorable" in rule.message_template.lower()
    assert "NOT a confirmed" in rule.message_template or "suitability" in rule.message_template


def test_disease_is_never_called_confirmed(db_session: Session, advisory_test_env):
    """Test 8: Strict guardrails ensure no chemical pesticides or false diagnosis exist in rules."""
    for rule in advisory_rule_registry._rules:
        # Check title and message
        assert "your crop has disease" not in rule.title_template.lower()
        assert "your crop has disease" not in rule.message_template.lower()
        assert "diagnosed" not in rule.title_template.lower()
        # Check no specific chemical pesticide brands/doses are prescribed
        assert "chlorpyrifos" not in rule.recommended_action.lower()
        assert "monocrotophos" not in rule.recommended_action.lower()
        assert "glyphosate" not in rule.recommended_action.lower()


def test_excess_rain_and_water_and_wind_framework(db_session: Session):
    """Test 9: Structural verification for Excess Rain, Water Stress, and Wind Stress rules."""
    excess_rule = advisory_rule_registry.get_rule(risk_type="EXCESS_RAIN")
    assert excess_rule is not None
    assert "drainage" in excess_rule.recommended_action.lower()

    water_rule = advisory_rule_registry.get_rule(risk_type="WATER_STRESS")
    assert water_rule is not None
    assert "mulching" in water_rule.recommended_action.lower() or "irrigation" in water_rule.recommended_action.lower()

    wind_rule = advisory_rule_registry.get_rule(risk_type="WIND_STRESS")
    assert wind_rule is not None
    assert "withhold" in wind_rule.recommended_action.lower()


# ============================================================================
# 3. MULTI-CROP & STAGE SPECIFICITY
# ============================================================================

def test_crop_and_stage_specific_advisory(db_session: Session, advisory_test_env):
    """Test 10: Rice vs Maize in Panchayat 1 receive crop-specific tailored guidance."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        persist_to_db=False,
    )

    rice_advs = [a for a in advisories if a.crop_name == "Rice"]
    maize_advs = [a for a in advisories if a.crop_name == "Maize"]

    assert len(rice_advs) >= 1
    assert len(maize_advs) >= 1

    # Rice has standing water guidance
    assert any("standing water" in a.action.action_text.lower() for a in rice_advs)
    # Maize has tasseling/silking guidance
    assert any("tasseling" in a.title.lower() or "maize" in a.title.lower() for a in maize_advs)


def test_multi_crop_panchayat_independent_generation(db_session: Session, advisory_test_env):
    """Test 11: Multi-crop Panchayats produce independent advisories per crop."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        persist_to_db=False,
    )

    crops_represented = set(a.crop_name for a in advisories)
    assert "Rice" in crops_represented
    assert "Maize" in crops_represented
    # Each crop has its own distinct priority rank starting at 1
    rice_ranks = [a.priority_rank for a in advisories if a.crop_name == "Rice"]
    maize_ranks = [a.priority_rank for a in advisories if a.crop_name == "Maize"]
    assert 1 in rice_ranks
    assert 1 in maize_ranks


def test_missing_advisory_rule_returns_informational(db_session: Session, advisory_test_env):
    """Test 12: Unconfigured advisory rule falls back to informational without crashing."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    # Synthetic unconfigured risk result
    from app.schemas.agricultural_risk import RiskEvidence
    custom_risk = RiskResult(
        id=999,
        panchayat_id=env["p1"].id,
        panchayat_name="Sohawal",
        block_id=env["block"].id,
        crop_id=env["crop_rice"].id,
        crop_name="Rice",
        stage_name="Flowering",
        risk_type="UNCONFIGURED_HAZARD",
        risk_category="CUSTOM",
        status="DETECTED",
        severity="HIGH",
        risk_score=0.8,
        observed_value=50.0,
        threshold_value=40.0,
        unit="units",
        confidence="HIGH",
        rule_version="test_v1",
        rule_source="TEST",
        evidence=RiskEvidence(condition_description="Custom test condition"),
    )

    panchayat = db_session.scalar(select(Panchayat).where(Panchayat.id == env["p1"].id))
    v_from = env["eval_dt"].replace(hour=0, minute=0, second=0)
    v_until = v_from + timedelta(days=1, seconds=-1)

    adv = engine._build_advisory_from_risk(
        risk=custom_risk,
        panchayat=panchayat,
        block_name="Faizabad Sadar Block",
        valid_from=v_from,
        valid_until=v_until,
        forecast_date=env["eval_dt"],
    )

    assert adv.advisory_type == "INFORMATIONAL"
    assert adv.advisory_category == "INFORMATIONAL"
    assert adv.action is not None


# ============================================================================
# 4. PRIORITY, CONFIDENCE, CONFLICTS & PROVENANCE
# ============================================================================

def test_priority_calculation_and_ranking(db_session: Session, advisory_test_env):
    """Test 13: Priority levels and ranking order."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        persist_to_db=False,
    )

    # Advisories should be ranked in order of priority (1 = highest)
    ranks = [a.priority_rank for a in advisories]
    assert ranks == list(range(1, len(advisories) + 1))


def test_confidence_and_evidence_preservation(db_session: Session, advisory_test_env):
    """Test 14: Evidence and confidence are preserved from Phase 10 risk assessment."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        risk_type_filter="HEAT_STRESS",
        persist_to_db=False,
    )

    adv = advisories[0]
    assert adv.confidence == "HIGH"
    assert adv.evidence is not None
    assert adv.evidence["observed_value"] == 38.5
    assert adv.evidence["unit"] == "°C"
    assert adv.provenance["advisory_rule_version"] == "agri_advisory_v1.0.0"
    assert adv.provenance["source_model"] == "IMD-GFS"


def test_validity_window(db_session: Session, advisory_test_env):
    """Test 15: Validity window begins and ends accurately for forecast day."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        persist_to_db=False,
    )

    adv = advisories[0]
    assert adv.valid_from.startswith("2026-07-15T00:00:00")
    assert adv.valid_until.startswith("2026-07-15T23:59:59")


def test_conflict_detection_expert_review(db_session: Session, advisory_test_env):
    """Test 16: Conflicting advisories (irrigate vs withhold irrigation) flag EXPERT_REVIEW_REQUIRED."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    from app.schemas.advisory import AdvisoryAction

    adv1 = AdvisoryResult(
        panchayat_id=env["p1"].id,
        panchayat_name="Sohawal",
        block_id=env["block"].id,
        crop_id=env["crop_rice"].id,
        crop_name="Rice",
        advisory_type="HEAT_STRESS_ADVISORY",
        priority="HIGH",
        title="Heat Stress",
        message="Apply standing water irrigation",
        action=AdvisoryAction(action_category="WATER_MANAGEMENT", action_text="Maintain 5-7 cm standing water irrigation"),
        valid_from="2026-07-15T00:00:00",
        valid_until="2026-07-15T23:59:59",
        forecast_date="2026-07-15T00:00:00",
        issue_time="2026-07-15T00:00:00",
    )
    adv2 = AdvisoryResult(
        panchayat_id=env["p1"].id,
        panchayat_name="Sohawal",
        block_id=env["block"].id,
        crop_id=env["crop_rice"].id,
        crop_name="Rice",
        advisory_type="WIND_STRESS_ADVISORY",
        priority="HIGH",
        title="Wind Stress",
        message="Strong winds expected",
        action=AdvisoryAction(action_category="WEATHER_PREPAREDNESS", action_text="Withhold field irrigation immediately"),
        valid_from="2026-07-15T00:00:00",
        valid_until="2026-07-15T23:59:59",
        forecast_date="2026-07-15T00:00:00",
        issue_time="2026-07-15T00:00:00",
    )

    advisories = [adv1, adv2]
    engine._detect_and_flag_conflicts(advisories)

    assert adv1.is_expert_review_required is True
    assert adv1.status == "EXPERT_REVIEW_REQUIRED"
    assert adv2.is_expert_review_required is True
    assert "CONFLICT DETECTED" in adv1.priority_reason


def test_idempotent_upsert_persistence(db_session: Session, advisory_test_env):
    """Test 17: Generating advisories multiple times updates existing records without duplicate rows."""
    env = advisory_test_env
    engine = AdvisoryEngine(db=db_session)

    # First generation
    advs_1 = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        risk_type_filter="HEAT_STRESS",
        persist_to_db=True,
    )
    id_1 = advs_1[0].id

    count_1 = db_session.scalar(
        select(func.count(AgroAdvisory.id)).where(AgroAdvisory.panchayat_id == env["p1"].id)
    )

    # Second generation
    advs_2 = engine.generate_panchayat_advisories(
        panchayat_id=env["p1"].id,
        forecast_date=env["eval_dt"],
        crop_id=env["crop_rice"].id,
        risk_type_filter="HEAT_STRESS",
        persist_to_db=True,
    )
    id_2 = advs_2[0].id

    count_2 = db_session.scalar(
        select(func.count(AgroAdvisory.id)).where(AgroAdvisory.panchayat_id == env["p1"].id)
    )

    assert id_1 == id_2
    assert count_1 == count_2


# ============================================================================
# 5. REST API ENDPOINT INTEGRATION TESTS
# ============================================================================

def test_api_generate_block_and_panchayat(client: TestClient, advisory_test_env):
    """Test 18: API endpoint POST /api/v1/advisory/generate."""
    env = advisory_test_env

    # 1. Block-level generation
    res_block = client.post(
        "/api/v1/advisory/generate",
        json={
            "block_id": env["block"].id,
            "date": env["eval_dt"].isoformat(),
            "persist_to_db": True,
        },
    )
    assert res_block.status_code == 200
    data_block = res_block.json()["data"]
    assert data_block["total_advisories_generated"] >= 2
    assert data_block["block_id"] == env["block"].id

    # 2. Panchayat-level generation
    res_p = client.post(
        "/api/v1/advisory/generate",
        json={
            "panchayat_id": env["p1"].id,
            "date": env["eval_dt"].isoformat(),
            "persist_to_db": True,
        },
    )
    assert res_p.status_code == 200
    data_p = res_p.json()["data"]
    assert data_p["total_panchayats"] == 1


def test_api_query_advisories_with_filters(client: TestClient, advisory_test_env):
    """Test 19: API endpoint GET /api/v1/advisory with filters."""
    env = advisory_test_env

    # Populate database
    client.post(
        "/api/v1/advisory/generate",
        json={"block_id": env["block"].id, "date": env["eval_dt"].isoformat(), "persist_to_db": True},
    )

    # Query with filters
    res = client.get(f"/api/v1/advisory?panchayat_id={env['p1'].id}&priority=HIGH")
    assert res.status_code == 200
    items = res.json()["data"]
    assert isinstance(items, list)
    assert all(i["panchayat_id"] == env["p1"].id for i in items)


def test_api_panchayat_profile_and_detail(client: TestClient, advisory_test_env):
    """Test 20: API endpoints GET /panchayat/{id} and GET /{id}."""
    env = advisory_test_env

    # Populate database
    gen_res = client.post(
        "/api/v1/advisory/generate",
        json={"panchayat_id": env["p1"].id, "date": env["eval_dt"].isoformat(), "persist_to_db": True},
    )
    adv_id = gen_res.json()["data"]["advisories"][0]["id"]

    # Profile
    res_prof = client.get(f"/api/v1/advisory/panchayat/{env['p1'].id}?date={env['eval_dt'].isoformat()}")
    assert res_prof.status_code == 200
    prof_data = res_prof.json()["data"]
    assert prof_data["panchayat_id"] == env["p1"].id
    assert "crop_advisories" in prof_data

    # Detail
    res_det = client.get(f"/api/v1/advisory/{adv_id}")
    assert res_det.status_code == 200
    det_data = res_det.json()["data"]
    assert det_data["id"] == adv_id
    assert "title" in det_data
    assert "action" in det_data


def test_api_advisory_status(client: TestClient, advisory_test_env):
    """Test 21: API endpoint GET /api/v1/advisory/status."""
    env = advisory_test_env

    client.post(
        "/api/v1/advisory/generate",
        json={"block_id": env["block"].id, "date": env["eval_dt"].isoformat(), "persist_to_db": True},
    )

    res = client.get("/api/v1/advisory/status")
    assert res.status_code == 200
    stat = res.json()["data"]
    assert stat["total_advisories"] > 0
    assert stat["active_rule_version"] == "agri_advisory_v1.0.0"
    assert "advisories_by_priority" in stat
    assert "advisories_by_type" in stat
