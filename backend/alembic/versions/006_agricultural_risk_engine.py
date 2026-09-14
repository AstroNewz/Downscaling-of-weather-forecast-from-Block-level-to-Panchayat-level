"""006_agricultural_risk_engine

Phase 10 Agricultural Risk Engine migration:
- Extends agricultural_risk_logs table with standalone risk evaluation fields
- Makes advisory_id optional (nullable)
- Adds foreign keys to panchayats, blocks, crops, panchayat_crop_contexts, panchayat_weather_records
- Adds indexes and unique constraint for idempotent risk evaluations

Revision ID: 006_agricultural_risk_engine
Revises: 005_agricultural_context
Create Date: 2026-09-14 01:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006_agricultural_risk_engine"
down_revision: Union[str, None] = "005_agricultural_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter advisory_id to be nullable
    op.alter_column("agricultural_risk_logs", "advisory_id", existing_type=sa.Integer(), nullable=True)

    # 2. Add spatial and agricultural context foreign keys and metadata
    op.add_column("agricultural_risk_logs", sa.Column("panchayat_id", sa.Integer(), nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("block_id", sa.Integer(), nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("crop_id", sa.Integer(), nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("crop_context_id", sa.Integer(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("panchayat_weather_id", sa.Integer(), nullable=True))

    op.add_column("agricultural_risk_logs", sa.Column("crop_name", sa.String(length=64), nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("stage_name", sa.String(length=64), nullable=True))

    # 3. Add risk classification and evaluation metrics
    op.add_column("agricultural_risk_logs", sa.Column("risk_type", sa.String(length=64), nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("status", sa.String(length=32), server_default="NOT_DETECTED", nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("risk_score", sa.Float(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("observed_value", sa.Float(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("threshold_value", sa.Float(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("unit", sa.String(length=32), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("duration_hours", sa.Float(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("confidence", sa.String(length=32), server_default="HIGH", nullable=False))

    # 4. Add rule versioning and provenance
    op.add_column("agricultural_risk_logs", sa.Column("rule_version", sa.String(length=64), server_default="agri_risk_v1.0.0", nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("rule_source", sa.String(length=64), server_default="ICAR_IMD_AGROMET_CRITERIA", nullable=False))

    op.add_column("agricultural_risk_logs", sa.Column("evaluation_date", sa.DateTime(), nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("forecast_valid_time", sa.DateTime(), nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("issue_time", sa.DateTime(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("source_model", sa.String(length=64), server_default="IMD-GFS", nullable=False))
    op.add_column("agricultural_risk_logs", sa.Column("weather_model_version", sa.String(length=32), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("feature_schema_version", sa.String(length=32), nullable=True))

    op.add_column("agricultural_risk_logs", sa.Column("evidence", sa.JSON(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("provenance", sa.JSON(), nullable=True))
    op.add_column("agricultural_risk_logs", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # 5. Make title, description, triggering_factor nullable
    op.alter_column("agricultural_risk_logs", "title", existing_type=sa.String(length=256), nullable=True)
    op.alter_column("agricultural_risk_logs", "description", existing_type=sa.Text(), nullable=True)
    op.alter_column("agricultural_risk_logs", "triggering_factor", existing_type=sa.String(length=256), nullable=True)

    # 6. Foreign key constraints
    op.create_foreign_key("fk_risk_logs_panchayat_id", "agricultural_risk_logs", "panchayats", ["panchayat_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_risk_logs_block_id", "agricultural_risk_logs", "blocks", ["block_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_risk_logs_crop_id", "agricultural_risk_logs", "crops", ["crop_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_risk_logs_crop_context_id", "agricultural_risk_logs", "panchayat_crop_contexts", ["crop_context_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_risk_logs_panchayat_weather_id", "agricultural_risk_logs", "panchayat_weather_records", ["panchayat_weather_id"], ["id"], ondelete="SET NULL")

    # 7. Indexes and unique constraint
    op.create_index(op.f("ix_agricultural_risk_logs_panchayat_id"), "agricultural_risk_logs", ["panchayat_id"], unique=False)
    op.create_index(op.f("ix_agricultural_risk_logs_block_id"), "agricultural_risk_logs", ["block_id"], unique=False)
    op.create_index(op.f("ix_agricultural_risk_logs_crop_id"), "agricultural_risk_logs", ["crop_id"], unique=False)
    op.create_index(op.f("ix_agricultural_risk_logs_risk_type"), "agricultural_risk_logs", ["risk_type"], unique=False)
    op.create_index(op.f("ix_agricultural_risk_logs_severity"), "agricultural_risk_logs", ["severity"], unique=False)
    op.create_index(op.f("ix_agricultural_risk_logs_status"), "agricultural_risk_logs", ["status"], unique=False)
    op.create_index(op.f("ix_agricultural_risk_logs_evaluation_date"), "agricultural_risk_logs", ["evaluation_date"], unique=False)
    op.create_index("idx_panchayat_risk_eval", "agricultural_risk_logs", ["panchayat_id", "crop_id", "risk_type", "evaluation_date"], unique=False)
    op.create_index("idx_block_risk_eval", "agricultural_risk_logs", ["block_id", "evaluation_date"], unique=False)
    op.create_unique_constraint(
        "uq_panchayat_crop_risk_run",
        "agricultural_risk_logs",
        ["panchayat_id", "crop_id", "risk_type", "evaluation_date", "rule_version", "source_model"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_panchayat_crop_risk_run", "agricultural_risk_logs", type_="unique")
    op.drop_index("idx_block_risk_eval", table_name="agricultural_risk_logs")
    op.drop_index("idx_panchayat_risk_eval", table_name="agricultural_risk_logs")
    op.drop_index(op.f("ix_agricultural_risk_logs_evaluation_date"), table_name="agricultural_risk_logs")
    op.drop_index(op.f("ix_agricultural_risk_logs_status"), table_name="agricultural_risk_logs")
    op.drop_index(op.f("ix_agricultural_risk_logs_severity"), table_name="agricultural_risk_logs")
    op.drop_index(op.f("ix_agricultural_risk_logs_risk_type"), table_name="agricultural_risk_logs")
    op.drop_index(op.f("ix_agricultural_risk_logs_crop_id"), table_name="agricultural_risk_logs")
    op.drop_index(op.f("ix_agricultural_risk_logs_block_id"), table_name="agricultural_risk_logs")
    op.drop_index(op.f("ix_agricultural_risk_logs_panchayat_id"), table_name="agricultural_risk_logs")

    op.drop_constraint("fk_risk_logs_panchayat_weather_id", "agricultural_risk_logs", type_="foreignkey")
    op.drop_constraint("fk_risk_logs_crop_context_id", "agricultural_risk_logs", type_="foreignkey")
    op.drop_constraint("fk_risk_logs_crop_id", "agricultural_risk_logs", type_="foreignkey")
    op.drop_constraint("fk_risk_logs_block_id", "agricultural_risk_logs", type_="foreignkey")
    op.drop_constraint("fk_risk_logs_panchayat_id", "agricultural_risk_logs", type_="foreignkey")

    op.drop_column("agricultural_risk_logs", "updated_at")
    op.drop_column("agricultural_risk_logs", "provenance")
    op.drop_column("agricultural_risk_logs", "evidence")
    op.drop_column("agricultural_risk_logs", "feature_schema_version")
    op.drop_column("agricultural_risk_logs", "weather_model_version")
    op.drop_column("agricultural_risk_logs", "source_model")
    op.drop_column("agricultural_risk_logs", "issue_time")
    op.drop_column("agricultural_risk_logs", "forecast_valid_time")
    op.drop_column("agricultural_risk_logs", "evaluation_date")
    op.drop_column("agricultural_risk_logs", "rule_source")
    op.drop_column("agricultural_risk_logs", "rule_version")
    op.drop_column("agricultural_risk_logs", "confidence")
    op.drop_column("agricultural_risk_logs", "duration_hours")
    op.drop_column("agricultural_risk_logs", "unit")
    op.drop_column("agricultural_risk_logs", "threshold_value")
    op.drop_column("agricultural_risk_logs", "observed_value")
    op.drop_column("agricultural_risk_logs", "risk_score")
    op.drop_column("agricultural_risk_logs", "status")
    op.drop_column("agricultural_risk_logs", "risk_type")
    op.drop_column("agricultural_risk_logs", "stage_name")
    op.drop_column("agricultural_risk_logs", "crop_name")
    op.drop_column("agricultural_risk_logs", "panchayat_weather_id")
    op.drop_column("agricultural_risk_logs", "crop_context_id")
    op.drop_column("agricultural_risk_logs", "crop_id")
    op.drop_column("agricultural_risk_logs", "block_id")
    op.drop_column("agricultural_risk_logs", "panchayat_id")
