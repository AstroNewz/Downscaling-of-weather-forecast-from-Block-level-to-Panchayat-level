import pytest
from datetime import datetime
from sqlalchemy import inspect
from app.db.base import Base
from app.db.models import (
    Block,
    Panchayat,
    LandUseMask,
    BlockWeatherForecast,
    DownscaledWeatherGrid,
    PanchayatWeather,
    Crop,
    CropPhenologyStage,
    SoilProfile,
    PanchayatCropMapping,
    PanchayatCropContext,
    AgroAdvisory,
    AgriculturalRiskLog,
)



def test_models_metadata_registered():
    """Verifies that all required tables are properly registered in Base metadata."""
    expected_tables = {
        "blocks",
        "panchayats",
        "land_use_masks",
        "block_weather_forecasts",
        "downscaled_weather_grids",
        "panchayat_weather_records",
        "crops",
        "crop_phenology_stages",
        "soil_profiles",
        "panchayat_crop_mappings",
        "panchayat_crop_contexts",
        "agro_advisories",
        "agricultural_risk_logs",
    }
    registered_tables = set(Base.metadata.tables.keys())
    for table_name in expected_tables:
        assert table_name in registered_tables, f"Table '{table_name}' is missing from metadata."



def test_spatial_geometry_columns():
    """Verifies that spatial models contain appropriate PostGIS geometry columns."""
    blocks_table = Base.metadata.tables["blocks"]
    assert "geometry" in blocks_table.columns
    assert "centroid" in blocks_table.columns

    panchayats_table = Base.metadata.tables["panchayats"]
    assert "geometry" in panchayats_table.columns
    assert "centroid" in panchayats_table.columns
    assert "block_id" in panchayats_table.columns

    land_use_table = Base.metadata.tables["land_use_masks"]
    assert "cropland_geometry" in land_use_table.columns
    assert "is_agricultural_eligible" in land_use_table.columns

    weather_grid_table = Base.metadata.tables["downscaled_weather_grids"]
    assert "location" in weather_grid_table.columns


def test_model_foreign_key_relationships():
    """Verifies foreign key constraints across models."""
    panchayats_table = Base.metadata.tables["panchayats"]
    block_fks = [fk.target_fullname for fk in panchayats_table.foreign_keys]
    assert "blocks.id" in block_fks

    land_use_table = Base.metadata.tables["land_use_masks"]
    lu_fks = [fk.target_fullname for fk in land_use_table.foreign_keys]
    assert "panchayats.id" in lu_fks

    advisory_table = Base.metadata.tables["agro_advisories"]
    adv_fks = [fk.target_fullname for fk in advisory_table.foreign_keys]
    assert "panchayats.id" in adv_fks
    assert "crops.id" in adv_fks

    risk_table = Base.metadata.tables["agricultural_risk_logs"]
    risk_fks = [fk.target_fullname for fk in risk_table.foreign_keys]
    assert "agro_advisories.id" in risk_fks
    assert "panchayats.id" in risk_fks
    assert "crops.id" in risk_fks


def test_model_instantiation():
    """Verifies model classes can be instantiated with valid attributes."""
    crop = Crop(
        crop_name="Paddy (Rice)",
        scientific_name="Oryza sativa",
        season="Kharif",
        base_temp_celsius=10.0,
        optimal_temp_min=20.0,
        optimal_temp_max=35.0,
        water_requirement_mm=1200.0,
    )
    assert crop.crop_name == "Paddy (Rice)"
    assert crop.season == "Kharif"

    stage = CropPhenologyStage(
        stage_name="Flowering",
        stage_order=3,
        gdd_required=350.0,
        water_sensitivity="CRITICAL",
        temp_sensitivity="HIGH",
    )
    assert stage.stage_name == "Flowering"
    assert stage.water_sensitivity == "CRITICAL"

    soil = SoilProfile(
        soil_type="Alluvial Loam",
        texture="Loamy",
        drainage_class="Well",
        water_holding_capacity_pct=35.0,
    )
    assert soil.soil_type == "Alluvial Loam"

    ctx = PanchayatCropContext(
        panchayat_id=1,
        block_id=1,
        crop_id=1,
        crop_name="Rice",
        context_date=datetime(2026, 7, 15),
        status="COMPLETE",
        source="AGRI_CONTEXT_ENGINE",
    )
    assert ctx.crop_name == "Rice"
    assert ctx.status == "COMPLETE"

    risk_log = AgriculturalRiskLog(
        panchayat_id=1,
        block_id=1,
        crop_id=1,
        crop_name="Rice",
        stage_name="Flowering",
        risk_type="HEAT_STRESS",
        risk_category="THERMAL",
        severity="HIGH",
        status="DETECTED",
        observed_value=38.5,
        threshold_value=37.0,
        unit="°C",
        rule_version="agri_risk_v1.0.0",
        rule_source="ICAR_IMD_AGROMET_CRITERIA",
        evaluation_date=datetime(2026, 7, 15),
        forecast_valid_time=datetime(2026, 7, 15),
        source_model="IMD-GFS",
    )
    assert risk_log.risk_type == "HEAT_STRESS"
    assert risk_log.status == "DETECTED"
    assert risk_log.observed_value == 38.5

    advisory = AgroAdvisory(
        panchayat_id=1,
        block_id=1,
        crop_id=1,
        advisory_type="HEAT_STRESS_ADVISORY",
        priority="HIGH",
        title="Rice Heat Stress Advisory",
        message="Maintain standing water layer in paddy fields.",
        summary_advisory="Maintain standing water layer in paddy fields.",
        valid_from=datetime(2026, 7, 15, 0, 0, 0),
        valid_until=datetime(2026, 7, 15, 23, 59, 59),
        forecast_date=datetime(2026, 7, 15),
        issue_time=datetime.utcnow(),
        rule_version="agri_risk_v1.0.0",
        advisory_rule_version="agri_advisory_v1.0.0",
        rule_source="ICAR_IMD_AGROMET_GUIDELINES",
    )
    assert advisory.advisory_type == "HEAT_STRESS_ADVISORY"
    assert advisory.priority == "HIGH"
    assert advisory.advisory_rule_version == "agri_advisory_v1.0.0"



