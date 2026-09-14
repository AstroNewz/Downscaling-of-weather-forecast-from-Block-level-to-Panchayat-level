"""005_agricultural_context

Phase 9 Agricultural Context migration:
- Adds optional nutrient fields (N, P, K) to soil_profiles table
- Adds crop_area_ha, expected_harvest_date, source to panchayat_crop_mappings table
- Creates panchayat_crop_contexts table for storing multi-crop, stage, soil, and weather context snapshots
- Adds indexes and unique constraints for idempotent context snapshots

Revision ID: 005_agricultural_context
Revises: 004_panchayat_weather_aggregation
Create Date: 2026-09-14 01:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_agricultural_context"
down_revision: Union[str, None] = "004_panchayat_weather_aggregation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nutrient columns to soil_profiles if missing
    op.add_column("soil_profiles", sa.Column("available_nitrogen_kg_ha", sa.Float(), nullable=True))
    op.add_column("soil_profiles", sa.Column("available_phosphorus_kg_ha", sa.Float(), nullable=True))
    op.add_column("soil_profiles", sa.Column("available_potassium_kg_ha", sa.Float(), nullable=True))

    # 2. Add crop area, expected harvest date, source to panchayat_crop_mappings
    op.add_column("panchayat_crop_mappings", sa.Column("crop_area_ha", sa.Float(), nullable=True))
    op.add_column("panchayat_crop_mappings", sa.Column("expected_harvest_date", sa.Date(), nullable=True))
    op.add_column("panchayat_crop_mappings", sa.Column("source", sa.String(length=64), server_default="AGRICULTURAL_DEPARTMENT", nullable=False))

    # 3. Create panchayat_crop_contexts table
    op.create_table(
        "panchayat_crop_contexts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("panchayat_id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("crop_id", sa.Integer(), nullable=False),
        sa.Column("crop_name", sa.String(length=64), nullable=False),

        # Phenology
        sa.Column("phenology_stage_id", sa.Integer(), nullable=True),
        sa.Column("stage_name", sa.String(length=64), nullable=True),
        sa.Column("stage_order", sa.Integer(), nullable=True),
        sa.Column("stage_derivation_method", sa.String(length=32), server_default="UNKNOWN", nullable=False),
        sa.Column("planting_date", sa.Date(), nullable=True),
        sa.Column("days_since_planting", sa.Integer(), nullable=True),
        sa.Column("expected_harvest_date", sa.Date(), nullable=True),

        # Soil
        sa.Column("soil_profile_id", sa.Integer(), nullable=True),
        sa.Column("soil_type", sa.String(length=64), nullable=True),
        sa.Column("soil_available", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("soil_status", sa.String(length=32), server_default="UNAVAILABLE", nullable=False),

        # Weather snapshot
        sa.Column("panchayat_weather_id", sa.Integer(), nullable=True),
        sa.Column("mean_temp_c", sa.Float(), nullable=True),
        sa.Column("min_temp_c", sa.Float(), nullable=True),
        sa.Column("max_temp_c", sa.Float(), nullable=True),
        sa.Column("temp_stddev_c", sa.Float(), nullable=True),
        sa.Column("weather_status", sa.String(length=32), server_default="UNAVAILABLE", nullable=False),

        # Agricultural area
        sa.Column("crop_area_ha", sa.Float(), nullable=True),
        sa.Column("agricultural_area_ha", sa.Float(), nullable=True),
        sa.Column("crop_fraction", sa.Float(), nullable=True),
        sa.Column("is_agricultural_eligible", sa.Boolean(), server_default=sa.text("true"), nullable=False),

        # Metadata & Evaluation
        sa.Column("context_date", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=64), server_default="AGRI_CONTEXT_ENGINE", nullable=False),
        sa.Column("source_version", sa.String(length=32), server_default="v1.0.0", nullable=True),
        sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="COMPLETE", nullable=False),
        sa.Column("quality_flags", sa.JSON(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(["panchayat_id"], ["panchayats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["phenology_stage_id"], ["crop_phenology_stages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["soil_profile_id"], ["soil_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["panchayat_weather_id"], ["panchayat_weather_records.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "panchayat_id",
            "crop_id",
            "context_date",
            "source",
            name="uq_panchayat_crop_context"
        ),
    )

    op.create_index(op.f("ix_panchayat_crop_contexts_panchayat_id"), "panchayat_crop_contexts", ["panchayat_id"], unique=False)
    op.create_index(op.f("ix_panchayat_crop_contexts_block_id"), "panchayat_crop_contexts", ["block_id"], unique=False)
    op.create_index(op.f("ix_panchayat_crop_contexts_crop_id"), "panchayat_crop_contexts", ["crop_id"], unique=False)
    op.create_index(op.f("ix_panchayat_crop_contexts_context_date"), "panchayat_crop_contexts", ["context_date"], unique=False)
    op.create_index(op.f("ix_panchayat_crop_contexts_status"), "panchayat_crop_contexts", ["status"], unique=False)
    op.create_index("idx_panchayat_crop_context_date", "panchayat_crop_contexts", ["panchayat_id", "crop_id", "context_date"], unique=False)
    op.create_index("idx_block_crop_context_date", "panchayat_crop_contexts", ["block_id", "context_date"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_block_crop_context_date", table_name="panchayat_crop_contexts")
    op.drop_index("idx_panchayat_crop_context_date", table_name="panchayat_crop_contexts")
    op.drop_index(op.f("ix_panchayat_crop_contexts_status"), table_name="panchayat_crop_contexts")
    op.drop_index(op.f("ix_panchayat_crop_contexts_context_date"), table_name="panchayat_crop_contexts")
    op.drop_index(op.f("ix_panchayat_crop_contexts_crop_id"), table_name="panchayat_crop_contexts")
    op.drop_index(op.f("ix_panchayat_crop_contexts_block_id"), table_name="panchayat_crop_contexts")
    op.drop_index(op.f("ix_panchayat_crop_contexts_panchayat_id"), table_name="panchayat_crop_contexts")
    op.drop_table("panchayat_crop_contexts")

    op.drop_column("panchayat_crop_mappings", "source")
    op.drop_column("panchayat_crop_mappings", "expected_harvest_date")
    op.drop_column("panchayat_crop_mappings", "crop_area_ha")

    op.drop_column("soil_profiles", "available_potassium_kg_ha")
    op.drop_column("soil_profiles", "available_phosphorus_kg_ha")
    op.drop_column("soil_profiles", "available_nitrogen_kg_ha")
