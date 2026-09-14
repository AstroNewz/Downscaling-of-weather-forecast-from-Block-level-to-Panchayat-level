from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, Index, JSON, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base


class AgroAdvisory(Base):
    """
    Generated Agro-Meteorological Advisory Record.
    Targeted to farmers and agricultural extension officers at the Gram Panchayat level.
    Downstream from Phase 10 Agricultural Risk Engine.
    """
    __tablename__ = "agro_advisories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[int] = mapped_column(Integer, ForeignKey("panchayats.id", ondelete="CASCADE"), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_id: Mapped[int] = mapped_column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_context_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("panchayat_crop_contexts.id", ondelete="SET NULL"), nullable=True, index=True)
    risk_log_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agricultural_risk_logs.id", ondelete="SET NULL"), nullable=True, index=True)
    panchayat_weather_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("panchayat_weather_records.id", ondelete="SET NULL"), nullable=True, index=True)

    advisory_type: Mapped[str] = mapped_column(
        String(64),
        default="INFORMATIONAL",
        nullable=False,
        index=True,
        doc="HEAT_STRESS_ADVISORY, COLD_STRESS_ADVISORY, WATER_STRESS_ADVISORY, EXCESS_RAIN_ADVISORY, WIND_STRESS_ADVISORY, DISEASE_FAVORABLE_CONDITIONS_ADVISORY, INFORMATIONAL"
    )
    advisory_category: Mapped[str] = mapped_column(
        String(32),
        default="ACTION_ADVISORY",
        nullable=False,
        doc="ACTION_ADVISORY, INFORMATIONAL"
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        default="MEDIUM",
        nullable=False,
        index=True,
        doc="CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL"
    )
    priority_rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    priority_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, doc="High-level advisory summary message")
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_category: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="MONITOR, WATER_MANAGEMENT, CROP_PROTECTION, FIELD_OPERATIONS, WEATHER_PREPAREDNESS, DISEASE_MONITORING"
    )
    timing: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, doc="IMMEDIATE, UPCOMING, ROUTINE")
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="NONE", nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False)
    confidence_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Validity & Dates
    issue_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    forecast_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    issue_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Cropland check
    is_cropland_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Legacy compatibility fields
    summary_advisory: Mapped[str] = mapped_column(Text, nullable=False, doc="High-level advisory narrative")
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, doc="Complete JSON advisory structure with actions")

    # Provenance & Versioning
    source_model: Mapped[str] = mapped_column(String(64), default="IMD-GFS", nullable=False)
    weather_model_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rule_version: Mapped[str] = mapped_column(String(64), default="agri_risk_v1.0.0", nullable=False)
    advisory_rule_version: Mapped[str] = mapped_column(String(64), default="agri_advisory_v1.0.0", nullable=False)
    rule_source: Mapped[str] = mapped_column(String(64), default="ICAR_IMD_AGROMET_GUIDELINES", nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)

    status: Mapped[str] = mapped_column(
        String(32),
        default="ACTIVE",
        nullable=False,
        index=True,
        doc="ACTIVE, DRAFT, EXPIRED, SUPPRESSED, INSUFFICIENT_DATA, EXPERT_REVIEW_REQUIRED"
    )
    is_expert_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    provenance: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    panchayat: Mapped["Panchayat"] = relationship("Panchayat", back_populates="advisories")
    block: Mapped["Block"] = relationship("Block")
    crop: Mapped["Crop"] = relationship("Crop", back_populates="advisories")
    crop_context: Mapped[Optional["PanchayatCropContext"]] = relationship("PanchayatCropContext")
    weather: Mapped[Optional["PanchayatWeather"]] = relationship("PanchayatWeather")
    risk_log: Mapped[Optional["AgriculturalRiskLog"]] = relationship("AgriculturalRiskLog", foreign_keys=[risk_log_id])
    risks: Mapped[List["AgriculturalRiskLog"]] = relationship(
        "AgriculturalRiskLog",
        back_populates="advisory",
        foreign_keys="[AgriculturalRiskLog.advisory_id]"
    )

    __table_args__ = (
        Index("idx_advisory_panchayat_date", "panchayat_id", "issue_date"),
        Index("idx_advisory_block_valid", "block_id", "valid_from", "valid_until"),
        Index("idx_advisory_type_priority", "advisory_type", "priority", "status"),
        UniqueConstraint(
            "panchayat_id",
            "crop_id",
            "risk_log_id",
            "advisory_rule_version",
            "valid_from",
            "source_model",
            name="uq_panchayat_crop_advisory_run"
        ),
    )


class AgriculturalRiskLog(Base):
    """
    Individual Agricultural Risk Flag detected by the risk engine.
    Correlates downscaled weather thresholds with crop growth stage sensitivities.
    """
    __tablename__ = "agricultural_risk_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[int] = mapped_column(Integer, ForeignKey("panchayats.id", ondelete="CASCADE"), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_id: Mapped[int] = mapped_column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_context_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("panchayat_crop_contexts.id", ondelete="SET NULL"), nullable=True, index=True)
    panchayat_weather_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("panchayat_weather_records.id", ondelete="SET NULL"), nullable=True, index=True)
    advisory_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agro_advisories.id", ondelete="SET NULL"), nullable=True, index=True)

    crop_name: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    risk_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False, doc="HEAT_STRESS, COLD_STRESS, WATER_STRESS, EXCESS_RAIN, DISEASE_FAVORABLE_CONDITIONS, WIND_STRESS")
    risk_category: Mapped[str] = mapped_column(String(64), nullable=False, doc="THERMAL, HYDROLOGICAL, PATHOLOGICAL_ENVIRONMENT, WIND")
    severity: Mapped[str] = mapped_column(String(32), default="NONE", nullable=False, index=True, doc="NONE, LOW, MODERATE, HIGH, EXTREME")
    status: Mapped[str] = mapped_column(String(32), default="NOT_DETECTED", nullable=False, index=True, doc="DETECTED, NOT_DETECTED, INSUFFICIENT_DATA, INVALID")

    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Normalized score 0.0-1.0")
    observed_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    duration_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False, doc="HIGH, MEDIUM, LOW, INSUFFICIENT")

    rule_version: Mapped[str] = mapped_column(String(64), default="agri_risk_v1.0.0", nullable=False)
    rule_source: Mapped[str] = mapped_column(String(64), default="ICAR_IMD_AGROMET_CRITERIA", nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggering_factor: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    evaluation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    forecast_valid_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    issue_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_model: Mapped[str] = mapped_column(String(64), default="IMD-GFS", nullable=False)
    weather_model_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    feature_schema_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    provenance: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    panchayat: Mapped["Panchayat"] = relationship("Panchayat")
    block: Mapped["Block"] = relationship("Block")
    crop: Mapped["Crop"] = relationship("Crop")
    crop_context: Mapped[Optional["PanchayatCropContext"]] = relationship("PanchayatCropContext")
    weather: Mapped[Optional["PanchayatWeather"]] = relationship("PanchayatWeather")
    advisory: Mapped[Optional["AgroAdvisory"]] = relationship(
        "AgroAdvisory",
        back_populates="risks",
        foreign_keys=[advisory_id]
    )

    __table_args__ = (
        Index("idx_panchayat_risk_eval", "panchayat_id", "crop_id", "risk_type", "evaluation_date"),
        Index("idx_block_risk_eval", "block_id", "evaluation_date"),
        UniqueConstraint("panchayat_id", "crop_id", "risk_type", "evaluation_date", "rule_version", "source_model", name="uq_panchayat_crop_risk_run"),
    )

