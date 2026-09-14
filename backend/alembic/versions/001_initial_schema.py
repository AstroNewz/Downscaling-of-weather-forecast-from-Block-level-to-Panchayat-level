"""001_initial_schema

Initial baseline database migration for SIH 26074:
- Enables PostGIS spatial extension
- Creates spatial tables (blocks, panchayats, land_use_masks)
- Creates weather forecast and downscaled grid tables (block_weather_forecasts, downscaled_weather_grids)
- Creates agricultural profile tables (crops, crop_phenology_stages, soil_profiles, panchayat_crop_mappings)
- Creates advisory tables (agro_advisories, agricultural_risk_logs)

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS Extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Table: blocks
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lgd_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("district_name", sa.String(length=128), nullable=False),
        sa.Column("state_name", sa.String(length=128), nullable=False),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("centroid", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blocks_lgd_code"), "blocks", ["lgd_code"], unique=True)
    op.create_index(op.f("ix_blocks_name"), "blocks", ["name"], unique=False)
    op.create_index(op.f("ix_blocks_district_name"), "blocks", ["district_name"], unique=False)
    op.create_index(op.f("ix_blocks_state_name"), "blocks", ["state_name"], unique=False)

    # 3. Table: panchayats
    op.create_table(
        "panchayats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lgd_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("elevation_meters", sa.Float(), nullable=True),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("centroid", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_panchayats_lgd_code"), "panchayats", ["lgd_code"], unique=True)
    op.create_index(op.f("ix_panchayats_name"), "panchayats", ["name"], unique=False)
    op.create_index(op.f("ix_panchayats_block_id"), "panchayats", ["block_id"], unique=False)

    # 4. Table: land_use_masks
    op.create_table(
        "land_use_masks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("panchayat_id", sa.Integer(), nullable=False),
        sa.Column("total_area_ha", sa.Float(), nullable=False),
        sa.Column("cropland_area_ha", sa.Float(), nullable=False),
        sa.Column("forest_area_ha", sa.Float(), nullable=False),
        sa.Column("urban_area_ha", sa.Float(), nullable=False),
        sa.Column("water_area_ha", sa.Float(), nullable=False),
        sa.Column("barren_area_ha", sa.Float(), nullable=False),
        sa.Column("cropland_geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("is_agricultural_eligible", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["panchayat_id"], ["panchayats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_land_use_masks_panchayat_id"), "land_use_masks", ["panchayat_id"], unique=True)
    op.create_index(op.f("ix_land_use_masks_is_agricultural_eligible"), "land_use_masks", ["is_agricultural_eligible"], unique=False)

    # 5. Table: block_weather_forecasts
    op.create_table(
        "block_weather_forecasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("forecast_date", sa.DateTime(), nullable=False),
        sa.Column("issue_time", sa.DateTime(), nullable=False),
        sa.Column("temp_min", sa.Float(), nullable=False),
        sa.Column("temp_max", sa.Float(), nullable=False),
        sa.Column("rainfall_mm", sa.Float(), nullable=False),
        sa.Column("relative_humidity_pct", sa.Float(), nullable=False),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=False),
        sa.Column("wind_direction_deg", sa.Float(), nullable=True),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=True),
        sa.Column("source_model", sa.String(length=64), nullable=False),
        sa.Column("raw_resolution_km", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_block_weather_forecasts_block_id"), "block_weather_forecasts", ["block_id"], unique=False)
    op.create_index(op.f("ix_block_weather_forecasts_forecast_date"), "block_weather_forecasts", ["forecast_date"], unique=False)
    op.create_index("idx_block_forecast_date", "block_weather_forecasts", ["block_id", "forecast_date"], unique=False)

    # 6. Table: downscaled_weather_grids
    op.create_table(
        "downscaled_weather_grids",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("panchayat_id", sa.Integer(), nullable=False),
        sa.Column("forecast_date", sa.DateTime(), nullable=False),
        sa.Column("grid_cell_id", sa.String(length=64), nullable=True),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("temp_min", sa.Float(), nullable=False),
        sa.Column("temp_max", sa.Float(), nullable=False),
        sa.Column("rainfall_mm", sa.Float(), nullable=False),
        sa.Column("relative_humidity_pct", sa.Float(), nullable=False),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=False),
        sa.Column("wind_direction_deg", sa.Float(), nullable=True),
        sa.Column("downscaling_algorithm", sa.String(length=64), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("terrain_corrected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["panchayat_id"], ["panchayats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_downscaled_weather_grids_panchayat_id"), "downscaled_weather_grids", ["panchayat_id"], unique=False)
    op.create_index(op.f("ix_downscaled_weather_grids_forecast_date"), "downscaled_weather_grids", ["forecast_date"], unique=False)
    op.create_index("idx_panchayat_forecast_date", "downscaled_weather_grids", ["panchayat_id", "forecast_date"], unique=False)

    # 7. Table: crops
    op.create_table(
        "crops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("crop_name", sa.String(length=64), nullable=False),
        sa.Column("scientific_name", sa.String(length=128), nullable=True),
        sa.Column("season", sa.String(length=32), nullable=False),
        sa.Column("base_temp_celsius", sa.Float(), nullable=False),
        sa.Column("optimal_temp_min", sa.Float(), nullable=False),
        sa.Column("optimal_temp_max", sa.Float(), nullable=False),
        sa.Column("water_requirement_mm", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crops_crop_name"), "crops", ["crop_name"], unique=True)
    op.create_index(op.f("ix_crops_season"), "crops", ["season"], unique=False)

    # 8. Table: crop_phenology_stages
    op.create_table(
        "crop_phenology_stages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("crop_id", sa.Integer(), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("gdd_required", sa.Float(), nullable=False),
        sa.Column("water_sensitivity", sa.String(length=32), nullable=False),
        sa.Column("temp_sensitivity", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crop_phenology_stages_crop_id"), "crop_phenology_stages", ["crop_id"], unique=False)
    op.create_index("idx_crop_stage_order", "crop_phenology_stages", ["crop_id", "stage_order"], unique=False)

    # 9. Table: soil_profiles
    op.create_table(
        "soil_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("soil_type", sa.String(length=64), nullable=False),
        sa.Column("texture", sa.String(length=64), nullable=True),
        sa.Column("drainage_class", sa.String(length=32), nullable=False),
        sa.Column("water_holding_capacity_pct", sa.Float(), nullable=False),
        sa.Column("organic_carbon_pct", sa.Float(), nullable=True),
        sa.Column("ph_level", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_soil_profiles_soil_type"), "soil_profiles", ["soil_type"], unique=False)

    # 10. Table: panchayat_crop_mappings
    op.create_table(
        "panchayat_crop_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("panchayat_id", sa.Integer(), nullable=False),
        sa.Column("crop_id", sa.Integer(), nullable=False),
        sa.Column("soil_id", sa.Integer(), nullable=True),
        sa.Column("current_stage_id", sa.Integer(), nullable=True),
        sa.Column("season", sa.String(length=32), nullable=False),
        sa.Column("sowing_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_stage_id"], ["crop_phenology_stages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["panchayat_id"], ["panchayats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["soil_id"], ["soil_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_panchayat_crop_mappings_crop_id"), "panchayat_crop_mappings", ["crop_id"], unique=False)
    op.create_index(op.f("ix_panchayat_crop_mappings_panchayat_id"), "panchayat_crop_mappings", ["panchayat_id"], unique=False)
    op.create_index(op.f("ix_panchayat_crop_mappings_is_active"), "panchayat_crop_mappings", ["is_active"], unique=False)
    op.create_index("idx_panchayat_crop_season", "panchayat_crop_mappings", ["panchayat_id", "crop_id", "season"], unique=False)

    # 11. Table: agro_advisories
    op.create_table(
        "agro_advisories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("panchayat_id", sa.Integer(), nullable=False),
        sa.Column("crop_id", sa.Integer(), nullable=False),
        sa.Column("issue_date", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("is_cropland_eligible", sa.Boolean(), nullable=False),
        sa.Column("summary_advisory", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["panchayat_id"], ["panchayats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agro_advisories_crop_id"), "agro_advisories", ["crop_id"], unique=False)
    op.create_index(op.f("ix_agro_advisories_issue_date"), "agro_advisories", ["issue_date"], unique=False)
    op.create_index(op.f("ix_agro_advisories_panchayat_id"), "agro_advisories", ["panchayat_id"], unique=False)
    op.create_index("idx_advisory_panchayat_date", "agro_advisories", ["panchayat_id", "issue_date"], unique=False)

    # 12. Table: agricultural_risk_logs
    op.create_table(
        "agricultural_risk_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("advisory_id", sa.Integer(), nullable=False),
        sa.Column("risk_category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("triggering_factor", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["advisory_id"], ["agro_advisories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agricultural_risk_logs_advisory_id"), "agricultural_risk_logs", ["advisory_id"], unique=False)


def downgrade() -> None:
    op.drop_table("agricultural_risk_logs")
    op.drop_table("agro_advisories")
    op.drop_table("panchayat_crop_mappings")
    op.drop_table("soil_profiles")
    op.drop_table("crop_phenology_stages")
    op.drop_table("crops")
    op.drop_table("downscaled_weather_grids")
    op.drop_table("block_weather_forecasts")
    op.drop_table("land_use_masks")
    op.drop_table("panchayats")
    op.drop_table("blocks")
