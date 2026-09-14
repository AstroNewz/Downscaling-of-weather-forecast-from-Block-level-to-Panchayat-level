"""
Automated Test Suite for Phase 13 SIH Demonstration & Evaluation Package
SIH Problem Statement 26074 (Agro-Meteorological Advisory Platform)
"""
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from fastapi.testclient import TestClient

from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import BlockWeatherForecast, PanchayatWeather
from app.db.models.agriculture import Crop, CropPhenologyStage, SoilProfile, PanchayatCropContext
from app.db.models.advisory import AgriculturalRiskLog, AgroAdvisory
from scripts.seed_demo_scenario import seed_canonical_demo
from scripts.validate_demo_scenario import validate_demo_scenario
from scripts.reset_demo_scenario import reset_demo_scenario


def test_canonical_demo_seed_and_validate(db_session: Session):
    """
    Test 1: Verifies that seed_canonical_demo creates the complete 10-link pipeline
    and validate_demo_scenario returns True.
    """
    # 1. Seed demo scenario
    seed_success = seed_canonical_demo(date_str="2026-07-15")
    assert seed_success is True

    # 2. Validate demo scenario
    validate_success = validate_demo_scenario(date_str="2026-07-15")
    assert validate_success is True


def test_canonical_demo_multi_crop_separation(db_session: Session):
    """
    Test 2: Verifies that the demo Panchayat maintains independent crop contexts,
    independent risk evaluations, and independent advisories for Rice and Maize.
    """
    seed_canonical_demo(date_str="2026-07-15")

    demo_p = db_session.scalar(select(Panchayat).where(Panchayat.lgd_code == "DEMO_PANCHAYAT_01"))
    assert demo_p is not None

    # Verify 2 distinct crop contexts
    contexts = db_session.scalars(select(PanchayatCropContext).where(PanchayatCropContext.panchayat_id == demo_p.id)).all()
    assert len(contexts) >= 2

    # Verify Rice risk is HEAT_STRESS
    rice_crop = db_session.scalar(select(Crop).where(Crop.name == "Rice (Paddy) [DEMO]"))
    assert rice_crop is not None
    rice_risk = db_session.scalar(
        select(AgriculturalRiskLog).where(
            and_(
                AgriculturalRiskLog.panchayat_id == demo_p.id,
                AgriculturalRiskLog.crop_id == rice_crop.id,
            )
        )
    )
    assert rice_risk is not None
    assert rice_risk.risk_type == "HEAT_STRESS"
    assert rice_risk.severity == "HIGH"

    # Verify Maize risk is WIND_STRESS
    maize_crop = db_session.scalar(select(Crop).where(Crop.name == "Maize (Corn) [DEMO]"))
    assert maize_crop is not None
    maize_risk = db_session.scalar(
        select(AgriculturalRiskLog).where(
            and_(
                AgriculturalRiskLog.panchayat_id == demo_p.id,
                AgriculturalRiskLog.crop_id == maize_crop.id,
            )
        )
    )
    assert maize_risk is not None
    assert maize_risk.risk_type == "WIND_STRESS"
    assert maize_risk.severity == "MODERATE"


def test_canonical_demo_provenance_traceability(db_session: Session):
    """
    Test 3: Verifies that every demo advisory maintains complete provenance links
    (panchayat_id, risk_log_id, panchayat_weather_id, rule_version).
    """
    seed_canonical_demo(date_str="2026-07-15")

    demo_p = db_session.scalar(select(Panchayat).where(Panchayat.lgd_code == "DEMO_PANCHAYAT_01"))
    assert demo_p is not None

    advisories = db_session.scalars(select(AgroAdvisory).where(AgroAdvisory.panchayat_id == demo_p.id)).all()
    assert len(advisories) >= 2

    for adv in advisories:
        assert adv.panchayat_id == demo_p.id
        assert adv.risk_log_id is not None
        assert adv.panchayat_weather_id is not None
        assert adv.rule_version == "agri_risk_v1.0.0"
        assert adv.advisory_rule_version == "agri_advisory_v1.0.0"
        assert adv.status == "ACTIVE"
        assert adv.is_cropland_eligible is True


def test_canonical_demo_reset_safety(db_session: Session):
    """
    Test 4: Verifies that reset_demo_scenario deletes only DEMO entities
    and leaves the database in a clean state.
    """
    seed_canonical_demo(date_str="2026-07-15")

    # Run reset
    reset_success = reset_demo_scenario(force=True)
    assert reset_success is True

    # Verify demo panchayat and block are removed
    demo_b = db_session.scalar(select(Block).where(Block.lgd_code == "DEMO_BLOCK_01"))
    demo_p = db_session.scalar(select(Panchayat).where(Panchayat.lgd_code == "DEMO_PANCHAYAT_01"))
    assert demo_b is None
    assert demo_p is None
