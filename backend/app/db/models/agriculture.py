from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Index, JSON, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base


class Crop(Base):
    """
    Crop Entity and Master Agronomic Profile.
    """
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, doc="e.g. Paddy, Wheat, Mustard, Cotton")
    scientific_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    season: Mapped[str] = mapped_column(String(32), index=True, nullable=False, doc="Kharif, Rabi, Zaid, Perennial")

    base_temp_celsius: Mapped[float] = mapped_column(Float, default=10.0, nullable=False, doc="Base temperature for GDD calculations")
    optimal_temp_min: Mapped[float] = mapped_column(Float, default=18.0, nullable=False)
    optimal_temp_max: Mapped[float] = mapped_column(Float, default=32.0, nullable=False)
    water_requirement_mm: Mapped[float] = mapped_column(Float, default=500.0, nullable=False, doc="Total seasonal water requirement")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    stages: Mapped[List["CropPhenologyStage"]] = relationship("CropPhenologyStage", back_populates="crop", cascade="all, delete-orphan")
    panchayat_mappings: Mapped[List["PanchayatCropMapping"]] = relationship("PanchayatCropMapping", back_populates="crop", cascade="all, delete-orphan")
    crop_contexts: Mapped[List["PanchayatCropContext"]] = relationship("PanchayatCropContext", back_populates="crop", cascade="all, delete-orphan")
    advisories: Mapped[List["AgroAdvisory"]] = relationship("AgroAdvisory", back_populates="crop", cascade="all, delete-orphan")


class CropPhenologyStage(Base):
    """
    Phenological Growth Stages for a specific Crop.
    Advisories vary sharply by stage (e.g., flowering is critically sensitive to moisture stress).
    """
    __tablename__ = "crop_phenology_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_id: Mapped[int] = mapped_column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)

    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, doc="Sowing, Vegetative, Flowering, Grain Filling, Harvesting")
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False, doc="Sequential order (1, 2, 3...)")
    gdd_required: Mapped[float] = mapped_column(Float, default=200.0, nullable=False, doc="Growing Degree Days needed for this stage")

    # Sensitivity levels (LOW, MODERATE, HIGH, CRITICAL)
    water_sensitivity: Mapped[str] = mapped_column(String(32), default="MODERATE", nullable=False)
    temp_sensitivity: Mapped[str] = mapped_column(String(32), default="MODERATE", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    crop: Mapped["Crop"] = relationship("Crop", back_populates="stages")
    panchayat_mappings: Mapped[List["PanchayatCropMapping"]] = relationship("PanchayatCropMapping", back_populates="current_stage")

    __table_args__ = (
        Index("idx_crop_stage_order", "crop_id", "stage_order"),
    )


class SoilProfile(Base):
    """
    Soil Properties and Hydrological Characteristics for a Panchayat or Region.
    """
    __tablename__ = "soil_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    soil_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False, doc="Alluvial, Black Soil, Red Soil, Sandy Loam, Clay")
    texture: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    drainage_class: Mapped[str] = mapped_column(String(32), default="Moderate", nullable=False, doc="Excessive, Well, Moderate, Poor")
    water_holding_capacity_pct: Mapped[float] = mapped_column(Float, default=30.0, nullable=False, doc="Field capacity %")
    organic_carbon_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ph_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    available_nitrogen_kg_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    available_phosphorus_kg_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    available_potassium_kg_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    panchayat_mappings: Mapped[List["PanchayatCropMapping"]] = relationship("PanchayatCropMapping", back_populates="soil")


class PanchayatCropMapping(Base):
    """
    Active Crop Deployment per Panchayat for a given agricultural season.
    """
    __tablename__ = "panchayat_crop_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[int] = mapped_column(Integer, ForeignKey("panchayats.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_id: Mapped[int] = mapped_column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    soil_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("soil_profiles.id", ondelete="SET NULL"), nullable=True)
    current_stage_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crop_phenology_stages.id", ondelete="SET NULL"), nullable=True)

    season: Mapped[str] = mapped_column(String(32), nullable=False, doc="Kharif 2026, Rabi 2026-27")
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    crop_area_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Cultivated area in hectares")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), default="AGRICULTURAL_DEPARTMENT", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    panchayat: Mapped["Panchayat"] = relationship("Panchayat", back_populates="crop_mappings")
    crop: Mapped["Crop"] = relationship("Crop", back_populates="panchayat_mappings")
    soil: Mapped[Optional["SoilProfile"]] = relationship("SoilProfile", back_populates="panchayat_mappings")
    current_stage: Mapped[Optional["CropPhenologyStage"]] = relationship("CropPhenologyStage", back_populates="panchayat_mappings")

    __table_args__ = (
        Index("idx_panchayat_crop_season", "panchayat_id", "crop_id", "season"),
    )


class PanchayatCropContext(Base):
    """
    Gram Panchayat Agricultural Context Snapshot.
    Combines Panchayat Weather + Crop + Crop Phenology Stage + Soil Profile + Cropland Eligibility.
    Direct input to Phase 10 Agricultural Risk Engine.
    """
    __tablename__ = "panchayat_crop_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[int] = mapped_column(Integer, ForeignKey("panchayats.id", ondelete="CASCADE"), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_id: Mapped[int] = mapped_column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Phenological Stage Context
    phenology_stage_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crop_phenology_stages.id", ondelete="SET NULL"), nullable=True, index=True)
    stage_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    stage_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stage_derivation_method: Mapped[str] = mapped_column(String(32), default="UNKNOWN", nullable=False, doc="OBSERVED, PLANTING_DATE, CROP_CALENDAR, UNKNOWN")
    planting_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    days_since_planting: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Soil Context
    soil_profile_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("soil_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    soil_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    soil_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    soil_status: Mapped[str] = mapped_column(String(32), default="UNAVAILABLE", nullable=False, doc="COMPLETE, PARTIAL, UNAVAILABLE")

    # Associated Panchayat Weather Context
    panchayat_weather_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("panchayat_weather_records.id", ondelete="SET NULL"), nullable=True, index=True)
    mean_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_stddev_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weather_status: Mapped[str] = mapped_column(String(32), default="UNAVAILABLE", nullable=False, doc="COMPLETE, PARTIAL, UNAVAILABLE")

    # Agricultural Cropland Area Context
    crop_area_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    agricultural_area_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crop_fraction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_agricultural_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Temporal and Evaluation Scope
    context_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, doc="Target forecast / snapshot valid date")
    source: Mapped[str] = mapped_column(String(64), default="AGRI_CONTEXT_ENGINE", nullable=False)
    source_version: Mapped[Optional[str]] = mapped_column(String(32), default="v1.0.0", nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETE", nullable=False, index=True, doc="COMPLETE, PARTIAL, UNAVAILABLE")

    # Quality and Provenance
    quality_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    provenance: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    panchayat: Mapped["Panchayat"] = relationship("Panchayat", back_populates="crop_contexts")
    block: Mapped["Block"] = relationship("Block")
    crop: Mapped["Crop"] = relationship("Crop", back_populates="crop_contexts")
    stage: Mapped[Optional["CropPhenologyStage"]] = relationship("CropPhenologyStage")
    soil: Mapped[Optional["SoilProfile"]] = relationship("SoilProfile")
    weather: Mapped[Optional["PanchayatWeather"]] = relationship("PanchayatWeather")

    __table_args__ = (
        Index("idx_panchayat_crop_context_date", "panchayat_id", "crop_id", "context_date"),
        Index("idx_block_crop_context_date", "block_id", "context_date"),
        UniqueConstraint("panchayat_id", "crop_id", "context_date", "source", name="uq_panchayat_crop_context"),
    )

