from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from geoalchemy2 import Geometry
from app.db.base import Base


class Block(Base):
    """
    Administrative Block (Tehsil/Mandal) Entity.
    Acts as the parent container for Gram Panchayats and the input level for coarse NWP forecasts.
    """
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lgd_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False, doc="Local Government Directory Code")
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    district_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    state_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    # Spatial Geometry: MultiPolygon boundary and Point centroid (SRID 4326: WGS84)
    geometry = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True)
    centroid = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    panchayats: Mapped[List["Panchayat"]] = relationship("Panchayat", back_populates="block", cascade="all, delete-orphan")
    weather_forecasts: Mapped[List["BlockWeatherForecast"]] = relationship("BlockWeatherForecast", back_populates="block", cascade="all, delete-orphan")


class Panchayat(Base):
    """
    Gram Panchayat Entity.
    Target administrative spatial unit for downscaled weather predictions and agro-meteorological advisories.
    """
    __tablename__ = "panchayats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lgd_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False, doc="Local Government Directory Code")
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    block_id: Mapped[int] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False, index=True)

    elevation_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Mean elevation in meters from DEM")
    
    # Spatial Geometry: MultiPolygon boundary and Point centroid (SRID 4326)
    geometry = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True)
    centroid = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    block: Mapped["Block"] = relationship("Block", back_populates="panchayats")
    land_use: Mapped[Optional["LandUseMask"]] = relationship("LandUseMask", back_populates="panchayat", uselist=False, cascade="all, delete-orphan")
    downscaled_weather_records: Mapped[List["DownscaledWeatherGrid"]] = relationship("DownscaledWeatherGrid", back_populates="panchayat", cascade="all, delete-orphan")
    weather_records: Mapped[List["PanchayatWeather"]] = relationship("PanchayatWeather", back_populates="panchayat", cascade="all, delete-orphan")
    crop_mappings: Mapped[List["PanchayatCropMapping"]] = relationship("PanchayatCropMapping", back_populates="panchayat", cascade="all, delete-orphan")
    crop_contexts: Mapped[List["PanchayatCropContext"]] = relationship("PanchayatCropContext", back_populates="panchayat", cascade="all, delete-orphan")
    advisories: Mapped[List["AgroAdvisory"]] = relationship("AgroAdvisory", back_populates="panchayat", cascade="all, delete-orphan")


class LandUseMask(Base):
    """
    Land-Use / Land-Cover (LULC) Classification & Cropland Mask for a Panchayat.
    Differentiates atmospheric weather modeling domain from crop-advisory applicable cropland.
    """
    __tablename__ = "land_use_masks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[int] = mapped_column(Integer, ForeignKey("panchayats.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    total_area_ha: Mapped[float] = mapped_column(Float, nullable=False, doc="Total geographical area in hectares")
    cropland_area_ha: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, doc="Net cultivated/agricultural area")
    forest_area_ha: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    urban_area_ha: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    water_area_ha: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    barren_area_ha: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Spatial mask of actual agricultural cropland parcels/zones within Panchayat
    cropland_geometry = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True)

    # Eligibility flag: True if cropland exceeds agricultural threshold
    is_agricultural_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    panchayat: Mapped["Panchayat"] = relationship("Panchayat", back_populates="land_use")
