"""003_spatial_grid_downscaling

Phase 7 spatial grid downscaling updates:
- Makes panchayat_id nullable in downscaled_weather_grids (for pre-aggregation 1-km block grid inference)
- Adds block_id (ForeignKey to blocks.id) to downscaled_weather_grids
- Adds issue_time, source_model, latitude, longitude to downscaled_weather_grids
- Adds coarse_temp_c, predicted_residual_c, downscaled_temp_c to downscaled_weather_grids
- Adds model_version, feature_schema_version, quality_flag, and prediction_metadata (JSON)
- Creates indexes on block_id, forecast_date, grid_cell_id

Revision ID: 003_spatial_grid_downscaling
Revises: 002_weather_ingestion
Create Date: 2026-09-14 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "003_spatial_grid_downscaling"
down_revision: Union[str, None] = "002_weather_ingestion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter downscaled_weather_grids: make panchayat_id nullable
    op.alter_column("downscaled_weather_grids", "panchayat_id", existing_type=sa.Integer(), nullable=True)
    
    # 2. Add block_id and spatial reference fields
    op.add_column("downscaled_weather_grids", sa.Column("block_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_downscaled_weather_grids_block_id",
        "downscaled_weather_grids",
        "blocks",
        ["block_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_index(op.f("ix_downscaled_weather_grids_block_id"), "downscaled_weather_grids", ["block_id"], unique=False)

    # 3. Add coordinates and forecast run metadata
    op.add_column("downscaled_weather_grids", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("downscaled_weather_grids", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("downscaled_weather_grids", sa.Column("issue_time", sa.DateTime(), nullable=True))
    op.add_column("downscaled_weather_grids", sa.Column("source_model", sa.String(length=64), server_default="IMD-GFS", nullable=False))

    # 4. Add downscaled temperature components
    op.add_column("downscaled_weather_grids", sa.Column("coarse_temp_c", sa.Float(), nullable=True))
    op.add_column("downscaled_weather_grids", sa.Column("predicted_residual_c", sa.Float(), nullable=True))
    op.add_column("downscaled_weather_grids", sa.Column("downscaled_temp_c", sa.Float(), nullable=True))

    # 5. Add model provenance and quality control
    op.add_column("downscaled_weather_grids", sa.Column("model_version", sa.String(length=32), server_default="v1.0.0", nullable=False))
    op.add_column("downscaled_weather_grids", sa.Column("feature_schema_version", sa.String(length=32), server_default="v1.1.0", nullable=False))
    op.add_column("downscaled_weather_grids", sa.Column("quality_flag", sa.String(length=32), server_default="VALID", nullable=False))
    op.add_column("downscaled_weather_grids", sa.Column("prediction_metadata", sa.JSON(), nullable=True))

    # 6. Make existing fields nullable if they were required in Phase 2 for panchayat records
    op.alter_column("downscaled_weather_grids", "temp_min", existing_type=sa.Float(), nullable=True)
    op.alter_column("downscaled_weather_grids", "temp_max", existing_type=sa.Float(), nullable=True)
    op.alter_column("downscaled_weather_grids", "rainfall_mm", existing_type=sa.Float(), nullable=True)
    op.alter_column("downscaled_weather_grids", "relative_humidity_pct", existing_type=sa.Float(), nullable=True)
    op.alter_column("downscaled_weather_grids", "wind_speed_kmh", existing_type=sa.Float(), nullable=True)

    # 7. Add composite index for spatial query performance
    op.create_index("idx_block_grid_forecast_date", "downscaled_weather_grids", ["block_id", "forecast_date"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_block_grid_forecast_date", table_name="downscaled_weather_grids")
    op.drop_column("downscaled_weather_grids", "prediction_metadata")
    op.drop_column("downscaled_weather_grids", "quality_flag")
    op.drop_column("downscaled_weather_grids", "feature_schema_version")
    op.drop_column("downscaled_weather_grids", "model_version")
    op.drop_column("downscaled_weather_grids", "downscaled_temp_c")
    op.drop_column("downscaled_weather_grids", "predicted_residual_c")
    op.drop_column("downscaled_weather_grids", "coarse_temp_c")
    op.drop_column("downscaled_weather_grids", "source_model")
    op.drop_column("downscaled_weather_grids", "issue_time")
    op.drop_column("downscaled_weather_grids", "longitude")
    op.drop_column("downscaled_weather_grids", "latitude")
    op.drop_constraint("fk_downscaled_weather_grids_block_id", "downscaled_weather_grids", type_="foreignkey")
    op.drop_index(op.f("ix_downscaled_weather_grids_block_id"), table_name="downscaled_weather_grids")
    op.drop_column("downscaled_weather_grids", "block_id")
    op.alter_column("downscaled_weather_grids", "panchayat_id", existing_type=sa.Integer(), nullable=False)
