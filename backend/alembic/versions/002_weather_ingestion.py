"""002_weather_ingestion

Phase 3 weather ingestion updates:
- Creates raw_weather_records table for raw audit payloads
- Creates weather_observations table for station ground-truth observations
- Adds quality_flag, quality_notes, and wind_speed_mps to block_weather_forecasts
- Adds unique constraint uq_block_forecast_run on (block_id, forecast_date, issue_time, source_model)

Revision ID: 002_weather_ingestion
Revises: 001_initial_schema
Create Date: 2026-09-14 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "002_weather_ingestion"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create raw_weather_records table
    op.create_table(
        "raw_weather_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_file", sa.String(length=256), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("records_count", sa.Integer(), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_weather_records_source"), "raw_weather_records", ["source"], unique=False)
    op.create_index(op.f("ix_raw_weather_records_checksum"), "raw_weather_records", ["checksum"], unique=False)
    op.create_index(op.f("ix_raw_weather_records_processing_status"), "raw_weather_records", ["processing_status"], unique=False)

    # 2. Create weather_observations table
    op.create_table(
        "weather_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.String(length=64), nullable=False),
        sa.Column("station_name", sa.String(length=128), nullable=True),
        sa.Column("block_id", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("observation_time", sa.DateTime(), nullable=False),
        sa.Column("temp_celsius", sa.Float(), nullable=True),
        sa.Column("temp_min", sa.Float(), nullable=True),
        sa.Column("temp_max", sa.Float(), nullable=True),
        sa.Column("rainfall_mm", sa.Float(), nullable=True),
        sa.Column("relative_humidity_pct", sa.Float(), nullable=True),
        sa.Column("wind_speed_mps", sa.Float(), nullable=True),
        sa.Column("wind_direction_deg", sa.Float(), nullable=True),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=True),
        sa.Column("quality_flag", sa.String(length=32), nullable=False),
        sa.Column("quality_notes", sa.String(length=256), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("station_id", "observation_time", "source", name="uq_station_observation_time"),
    )
    op.create_index(op.f("ix_weather_observations_station_id"), "weather_observations", ["station_id"], unique=False)
    op.create_index(op.f("ix_weather_observations_block_id"), "weather_observations", ["block_id"], unique=False)
    op.create_index(op.f("ix_weather_observations_observation_time"), "weather_observations", ["observation_time"], unique=False)
    op.create_index(op.f("ix_weather_observations_quality_flag"), "weather_observations", ["quality_flag"], unique=False)
    op.create_index("idx_station_time", "weather_observations", ["station_id", "observation_time"], unique=False)

    # 3. Alter block_weather_forecasts: add columns and constraints
    op.add_column("block_weather_forecasts", sa.Column("wind_speed_mps", sa.Float(), nullable=True))
    op.add_column("block_weather_forecasts", sa.Column("quality_flag", sa.String(length=32), server_default="VALID", nullable=False))
    op.add_column("block_weather_forecasts", sa.Column("quality_notes", sa.String(length=256), nullable=True))
    op.create_index(op.f("ix_block_weather_forecasts_quality_flag"), "block_weather_forecasts", ["quality_flag"], unique=False)
    op.create_index("idx_block_run_date", "block_weather_forecasts", ["block_id", "forecast_date", "issue_time", "source_model"], unique=False)
    op.create_unique_constraint("uq_block_forecast_run", "block_weather_forecasts", ["block_id", "forecast_date", "issue_time", "source_model"])


def downgrade() -> None:
    op.drop_constraint("uq_block_forecast_run", "block_weather_forecasts", type_="unique")
    op.drop_index("idx_block_run_date", table_name="block_weather_forecasts")
    op.drop_index(op.f("ix_block_weather_forecasts_quality_flag"), table_name="block_weather_forecasts")
    op.drop_column("block_weather_forecasts", "quality_notes")
    op.drop_column("block_weather_forecasts", "quality_flag")
    op.drop_column("block_weather_forecasts", "wind_speed_mps")

    op.drop_table("weather_observations")
    op.drop_table("raw_weather_records")
