"""004_panchayat_weather_aggregation

Phase 8 Panchayat weather aggregation updates:
- Creates panchayat_weather_records table for area-weighted spatial weather aggregation
- Adds indexes on panchayat_id, block_id, forecast_date
- Adds unique constraint uq_panchayat_weather_run on (panchayat_id, forecast_date, issue_time, source_model, model_version)

Revision ID: 004_panchayat_weather_aggregation
Revises: 003_spatial_grid_downscaling
Create Date: 2026-09-14 01:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_panchayat_weather_aggregation"
down_revision: Union[str, None] = "003_spatial_grid_downscaling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create panchayat_weather_records table
    op.create_table(
        "panchayat_weather_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("panchayat_id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("forecast_date", sa.DateTime(), nullable=False),
        sa.Column("issue_time", sa.DateTime(), nullable=False),
        sa.Column("source_model", sa.String(length=64), server_default="IMD-GFS", nullable=False),
        sa.Column("model_version", sa.String(length=32), server_default="v1.0.0", nullable=False),
        sa.Column("feature_schema_version", sa.String(length=32), server_default="v1.1.0", nullable=False),
        sa.Column("grid_resolution_km", sa.Float(), server_default="1.0", nullable=False),
        
        # Temperature Statistics
        sa.Column("mean_temp_c", sa.Float(), nullable=False),
        sa.Column("min_temp_c", sa.Float(), nullable=False),
        sa.Column("max_temp_c", sa.Float(), nullable=False),
        sa.Column("median_temp_c", sa.Float(), nullable=True),
        sa.Column("temp_stddev_c", sa.Float(), nullable=True),
        sa.Column("temp_p10_c", sa.Float(), nullable=True),
        sa.Column("temp_p90_c", sa.Float(), nullable=True),
        sa.Column("mean_residual_c", sa.Float(), nullable=True),

        # Spatial Coverage & Diagnostics
        sa.Column("total_panchayat_area_sqkm", sa.Float(), nullable=False),
        sa.Column("covered_area_sqkm", sa.Float(), nullable=False),
        sa.Column("coverage_pct", sa.Float(), nullable=False),
        sa.Column("contributing_grid_cells", sa.Integer(), nullable=False),
        sa.Column("valid_grid_cells", sa.Integer(), nullable=False),
        sa.Column("quality_status", sa.String(length=32), server_default="COMPLETE", nullable=False),
        sa.Column("quality_flags", sa.JSON(), nullable=True),

        # Aggregation Metadata
        sa.Column("aggregation_method", sa.String(length=64), server_default="AREA_WEIGHTED", nullable=False),
        sa.Column("aggregation_crs", sa.String(length=32), nullable=False),
        sa.Column("cropland_weighted_mean_temp_c", sa.Float(), nullable=True),
        sa.Column("aggregation_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(["panchayat_id"], ["panchayats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "panchayat_id",
            "forecast_date",
            "issue_time",
            "source_model",
            "model_version",
            name="uq_panchayat_weather_run"
        ),
    )
    op.create_index(op.f("ix_panchayat_weather_records_panchayat_id"), "panchayat_weather_records", ["panchayat_id"], unique=False)
    op.create_index(op.f("ix_panchayat_weather_records_block_id"), "panchayat_weather_records", ["block_id"], unique=False)
    op.create_index(op.f("ix_panchayat_weather_records_forecast_date"), "panchayat_weather_records", ["forecast_date"], unique=False)
    op.create_index(op.f("ix_panchayat_weather_records_quality_status"), "panchayat_weather_records", ["quality_status"], unique=False)
    op.create_index("idx_panchayat_weather_date", "panchayat_weather_records", ["panchayat_id", "forecast_date"], unique=False)
    op.create_index("idx_block_panchayat_weather_date", "panchayat_weather_records", ["block_id", "forecast_date"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_block_panchayat_weather_date", table_name="panchayat_weather_records")
    op.drop_index("idx_panchayat_weather_date", table_name="panchayat_weather_records")
    op.drop_index(op.f("ix_panchayat_weather_records_quality_status"), table_name="panchayat_weather_records")
    op.drop_index(op.f("ix_panchayat_weather_records_forecast_date"), table_name="panchayat_weather_records")
    op.drop_index(op.f("ix_panchayat_weather_records_block_id"), table_name="panchayat_weather_records")
    op.drop_index(op.f("ix_panchayat_weather_records_panchayat_id"), table_name="panchayat_weather_records")
    op.drop_table("panchayat_weather_records")
