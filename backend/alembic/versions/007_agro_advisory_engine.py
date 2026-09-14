"""007_agro_advisory_engine

Phase 11 Agro-Meteorological Advisory Generation Engine migration:
- Extends agro_advisories table with structured actions, priority, validity, evidence, and provenance
- Adds foreign keys to blocks, panchayat_crop_contexts, agricultural_risk_logs, panchayat_weather_records
- Adds indexes and unique constraint for idempotent advisory generation

Revision ID: 007_agro_advisory_engine
Revises: 006_agricultural_risk_engine
Create Date: 2026-09-14 01:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007_agro_advisory_engine"
down_revision: Union[str, None] = "006_agricultural_risk_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add spatial and foreign key columns
    op.add_column("agro_advisories", sa.Column("block_id", sa.Integer(), nullable=False))
    op.add_column("agro_advisories", sa.Column("crop_context_id", sa.Integer(), nullable=True))
    op.add_column("agro_advisories", sa.Column("risk_log_id", sa.Integer(), nullable=True))
    op.add_column("agro_advisories", sa.Column("panchayat_weather_id", sa.Integer(), nullable=True))

    # 2. Add advisory classification, priority and action fields
    op.add_column("agro_advisories", sa.Column("advisory_type", sa.String(length=64), server_default="INFORMATIONAL", nullable=False))
    op.add_column("agro_advisories", sa.Column("advisory_category", sa.String(length=32), server_default="ACTION_ADVISORY", nullable=False))
    op.add_column("agro_advisories", sa.Column("priority", sa.String(length=32), server_default="MEDIUM", nullable=False))
    op.add_column("agro_advisories", sa.Column("priority_rank", sa.Integer(), server_default="1", nullable=False))
    op.add_column("agro_advisories", sa.Column("priority_reason", sa.Text(), nullable=True))

    op.add_column("agro_advisories", sa.Column("title", sa.String(length=256), server_default="", nullable=False))
    op.add_column("agro_advisories", sa.Column("message", sa.Text(), server_default="", nullable=False))
    op.add_column("agro_advisories", sa.Column("recommended_action", sa.Text(), nullable=True))
    op.add_column("agro_advisories", sa.Column("action_category", sa.String(length=64), nullable=True))
    op.add_column("agro_advisories", sa.Column("timing", sa.String(length=128), nullable=True))
    op.add_column("agro_advisories", sa.Column("urgency", sa.String(length=32), nullable=True))
    op.add_column("agro_advisories", sa.Column("rationale", sa.Text(), nullable=True))
    op.add_column("agro_advisories", sa.Column("severity", sa.String(length=32), server_default="NONE", nullable=False))
    op.add_column("agro_advisories", sa.Column("confidence", sa.String(length=32), server_default="HIGH", nullable=False))
    op.add_column("agro_advisories", sa.Column("confidence_reason", sa.Text(), nullable=True))

    # 3. Add validity and forecast temporal fields
    op.add_column("agro_advisories", sa.Column("valid_from", sa.DateTime(), nullable=False))
    op.add_column("agro_advisories", sa.Column("forecast_date", sa.DateTime(), nullable=False))
    op.add_column("agro_advisories", sa.Column("issue_time", sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # 4. Add provenance, versioning and localization
    op.add_column("agro_advisories", sa.Column("source_model", sa.String(length=64), server_default="IMD-GFS", nullable=False))
    op.add_column("agro_advisories", sa.Column("weather_model_version", sa.String(length=32), nullable=True))
    op.add_column("agro_advisories", sa.Column("rule_version", sa.String(length=64), server_default="agri_risk_v1.0.0", nullable=False))
    op.add_column("agro_advisories", sa.Column("advisory_rule_version", sa.String(length=64), server_default="agri_advisory_v1.0.0", nullable=False))
    op.add_column("agro_advisories", sa.Column("rule_source", sa.String(length=64), server_default="ICAR_IMD_AGROMET_GUIDELINES", nullable=False))
    op.add_column("agro_advisories", sa.Column("language", sa.String(length=16), server_default="en", nullable=False))

    op.add_column("agro_advisories", sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False))
    op.add_column("agro_advisories", sa.Column("is_expert_review_required", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    op.add_column("agro_advisories", sa.Column("provenance", sa.JSON(), nullable=True))
    op.add_column("agro_advisories", sa.Column("evidence", sa.JSON(), nullable=True))
    op.add_column("agro_advisories", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.add_column("agro_advisories", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # 5. Foreign key constraints
    op.create_foreign_key("fk_advisories_block_id", "agro_advisories", "blocks", ["block_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_advisories_crop_context_id", "agro_advisories", "panchayat_crop_contexts", ["crop_context_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_advisories_risk_log_id", "agro_advisories", "agricultural_risk_logs", ["risk_log_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_advisories_panchayat_weather_id", "agro_advisories", "panchayat_weather_records", ["panchayat_weather_id"], ["id"], ondelete="SET NULL")

    # 6. Indexes and unique constraint
    op.create_index(op.f("ix_agro_advisories_block_id"), "agro_advisories", ["block_id"], unique=False)
    op.create_index(op.f("ix_agro_advisories_crop_context_id"), "agro_advisories", ["crop_context_id"], unique=False)
    op.create_index(op.f("ix_agro_advisories_risk_log_id"), "agro_advisories", ["risk_log_id"], unique=False)
    op.create_index(op.f("ix_agro_advisories_panchayat_weather_id"), "agro_advisories", ["panchayat_weather_id"], unique=False)
    op.create_index(op.f("ix_agro_advisories_advisory_type"), "agro_advisories", ["advisory_type"], unique=False)
    op.create_index(op.f("ix_agro_advisories_priority"), "agro_advisories", ["priority"], unique=False)
    op.create_index(op.f("ix_agro_advisories_status"), "agro_advisories", ["status"], unique=False)
    op.create_index(op.f("ix_agro_advisories_valid_from"), "agro_advisories", ["valid_from"], unique=False)
    op.create_index(op.f("ix_agro_advisories_valid_until"), "agro_advisories", ["valid_until"], unique=False)
    op.create_index(op.f("ix_agro_advisories_forecast_date"), "agro_advisories", ["forecast_date"], unique=False)
    op.create_index("idx_advisory_block_valid", "agro_advisories", ["block_id", "valid_from", "valid_until"], unique=False)
    op.create_index("idx_advisory_type_priority", "agro_advisories", ["advisory_type", "priority", "status"], unique=False)
    op.create_unique_constraint(
        "uq_panchayat_crop_advisory_run",
        "agro_advisories",
        ["panchayat_id", "crop_id", "risk_log_id", "advisory_rule_version", "valid_from", "source_model"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_panchayat_crop_advisory_run", "agro_advisories", type_="unique")
    op.drop_index("idx_advisory_type_priority", table_name="agro_advisories")
    op.drop_index("idx_advisory_block_valid", table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_forecast_date"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_valid_until"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_valid_from"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_status"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_priority"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_advisory_type"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_panchayat_weather_id"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_risk_log_id"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_crop_context_id"), table_name="agro_advisories")
    op.drop_index(op.f("ix_agro_advisories_block_id"), table_name="agro_advisories")

    op.drop_constraint("fk_advisories_panchayat_weather_id", "agro_advisories", type_="foreignkey")
    op.drop_constraint("fk_advisories_risk_log_id", "agro_advisories", type_="foreignkey")
    op.drop_constraint("fk_advisories_crop_context_id", "agro_advisories", type_="foreignkey")
    op.drop_constraint("fk_advisories_block_id", "agro_advisories", type_="foreignkey")

    op.drop_column("agro_advisories", "updated_at")
    op.drop_column("agro_advisories", "metadata_json")
    op.drop_column("agro_advisories", "evidence")
    op.drop_column("agro_advisories", "provenance")
    op.drop_column("agro_advisories", "is_expert_review_required")
    op.drop_column("agro_advisories", "status")
    op.drop_column("agro_advisories", "language")
    op.drop_column("agro_advisories", "rule_source")
    op.drop_column("agro_advisories", "advisory_rule_version")
    op.drop_column("agro_advisories", "rule_version")
    op.drop_column("agro_advisories", "weather_model_version")
    op.drop_column("agro_advisories", "source_model")
    op.drop_column("agro_advisories", "issue_time")
    op.drop_column("agro_advisories", "forecast_date")
    op.drop_column("agro_advisories", "valid_from")
    op.drop_column("agro_advisories", "confidence_reason")
    op.drop_column("agro_advisories", "confidence")
    op.drop_column("agro_advisories", "severity")
    op.drop_column("agro_advisories", "rationale")
    op.drop_column("agro_advisories", "urgency")
    op.drop_column("agro_advisories", "timing")
    op.drop_column("agro_advisories", "action_category")
    op.drop_column("agro_advisories", "recommended_action")
    op.drop_column("agro_advisories", "message")
    op.drop_column("agro_advisories", "title")
    op.drop_column("agro_advisories", "priority_reason")
    op.drop_column("agro_advisories", "priority_rank")
    op.drop_column("agro_advisories", "priority")
    op.drop_column("agro_advisories", "advisory_category")
    op.drop_column("agro_advisories", "advisory_type")
    op.drop_column("agro_advisories", "panchayat_weather_id")
    op.drop_column("agro_advisories", "risk_log_id")
    op.drop_column("agro_advisories", "crop_context_id")
    op.drop_column("agro_advisories", "block_id")
