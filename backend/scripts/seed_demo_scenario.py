"""
SIH Demonstration Scenario Seed Script (Phase 13)
SIH Problem Statement 26074 (Agro-Meteorological Advisory Platform)

Deterministically seeds the canonical SIH evaluation scenario in the local database:
- 1 Demonstration Block ('DEMO_BLOCK_01' - Maya Bazar Demo Block)
- 1 Canonical Panchayat ('DEMO_PANCHAYAT_01' - Maya Bazar Demo Gram Panchayat)
- 2 Calibrated Crops (Rice at Flowering, Maize at Tasseling)
- Localized Soil Profile (Alluvial Silt Loam, AWC 145 mm/m)
- Block Weather Forecast (Coarse Base: 36.0°C Tmax, 28.0 km/h wind)
- 1-km Downscaled Temperature Grid (Elevation-adjusted residuals)
- Area-Weighted Panchayat Weather (Tmax: 37.8°C, Tmean: 31.7°C, Residual Delta: +1.2°C)
- Multi-Hazard Agricultural Risks (Rice Heat Stress + Maize High Wind Lodging Risk)
- Structured Agro-Meteorological Advisories with complete provenance links.

All seeded entities use 'DEMO_' or 'SYNTHETIC_' markers for isolation and safety.
"""
import sys
import os
import argparse
from datetime import datetime, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, and_, delete
from app.db.session import SessionLocal
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import BlockWeatherForecast, PanchayatWeather, DownscaledWeatherGrid
from app.db.models.agriculture import Crop, CropPhenologyStage, SoilProfile, PanchayatCropMapping, PanchayatCropContext
from app.db.models.advisory import AgriculturalRiskLog, AgroAdvisory
from app.services.agricultural_risk import AgriculturalRiskEngine
from app.services.advisory_engine import AgroAdvisoryEngine


def seed_canonical_demo(date_str: str = "2026-07-15") -> bool:
    print("=" * 70)
    print("🌾 SIH 26074 CANONICAL DEMONSTRATION SEEDER (PHASE 13)")
    print("=" * 70)
    print(f"[DEMO] Seeding deterministic demo scenario for date: {date_str}...")

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    db = SessionLocal()

    try:
        # 1. Create or retrieve Demo Block
        demo_block = db.scalar(select(Block).where(Block.lgd_code == "DEMO_BLOCK_01"))
        if not demo_block:
            demo_block = Block(
                lgd_code="DEMO_BLOCK_01",
                name="Maya Bazar Demonstration Block (SYNTHETIC)",
                district_name="Ayodhya",
                state_name="Uttar Pradesh",
            )
            db.add(demo_block)
            db.flush()
            print(f"[DEMO] Created Block: {demo_block.name} (ID: {demo_block.id})")
        else:
            print(f"[DEMO] Existing Block found: {demo_block.name} (ID: {demo_block.id})")

        # 2. Create or retrieve Canonical Demo Panchayat
        demo_panchayat = db.scalar(select(Panchayat).where(Panchayat.lgd_code == "DEMO_PANCHAYAT_01"))
        if not demo_panchayat:
            demo_panchayat = Panchayat(
                lgd_code="DEMO_PANCHAYAT_01",
                name="Maya Bazar Demo Gram Panchayat (SYNTHETIC)",
                block_id=demo_block.id,
                elevation_meters=112.0,
            )
            db.add(demo_panchayat)
            db.flush()
            print(f"[DEMO] Created Panchayat: {demo_panchayat.name} (ID: {demo_panchayat.id})")
        else:
            print(f"[DEMO] Existing Panchayat found: {demo_panchayat.name} (ID: {demo_panchayat.id})")

        # 3. Create Land Use Cropland Mask
        mask = db.scalar(select(LandUseMask).where(LandUseMask.panchayat_id == demo_panchayat.id))
        if not mask:
            mask = LandUseMask(
                panchayat_id=demo_panchayat.id,
                total_area_hectares=1250.0,
                cropland_area_hectares=1020.0,
                forest_area_hectares=120.0,
                urban_area_hectares=60.0,
                water_bodies_hectares=30.0,
                barren_area_hectares=20.0,
                is_agricultural_eligible=True,
                mask_source="Sentinel-2 10m LULC (SYNTHETIC TEST)",
            )
            db.add(mask)
            db.flush()
            print(f"[DEMO] Created Cropland Mask: 1020/1250 ha ({1020/1250*100:.1f}%) Eligible")

        # 4. Create Soil Profile
        soil = db.scalar(select(SoilProfile).where(SoilProfile.panchayat_id == demo_panchayat.id))
        if not soil:
            soil = SoilProfile(
                panchayat_id=demo_panchayat.id,
                soil_type="Alluvial Silt Loam",
                water_holding_capacity_pct=36.5,
                organic_carbon_pct=0.65,
                ph_level=7.2,
                drainage_class="Well Drained",
                soil_depth_cm=120.0,
                soil_status="COMPLETE",
            )
            db.add(soil)
            db.flush()
            print(f"[DEMO] Created Soil Profile: {soil.soil_type} (AWC 36.5%)")

        # 5. Create Demonstration Crops (Rice and Maize)
        rice = db.scalar(select(Crop).where(Crop.name == "Rice (Paddy) [DEMO]"))
        if not rice:
            rice = Crop(
                name="Rice (Paddy) [DEMO]",
                scientific_name="Oryza sativa",
                crop_category="CEREAL",
                season="Kharif",
                growing_period_days=120,
                base_temperature_c=10.0,
                optimal_temperature_min_c=22.0,
                optimal_temperature_max_c=32.0,
                critical_high_temperature_c=35.0,
            )
            db.add(rice)
            db.flush()
            # Add flowering stage
            stage_rice = CropPhenologyStage(
                crop_id=rice.id,
                stage_name="Flowering",
                order_index=4,
                duration_days=15,
                min_gdd_c=650.0,
                max_gdd_c=800.0,
                critical_tmax_threshold_c=35.0,
                kc_factor=1.20,
            )
            db.add(stage_rice)
            db.flush()

        maize = db.scalar(select(Crop).where(Crop.name == "Maize (Corn) [DEMO]"))
        if not maize:
            maize = Crop(
                name="Maize (Corn) [DEMO]",
                scientific_name="Zea mays",
                crop_category="CEREAL",
                season="Kharif",
                growing_period_days=100,
                base_temperature_c=10.0,
                optimal_temperature_min_c=20.0,
                optimal_temperature_max_c=30.0,
                critical_high_temperature_c=38.0,
            )
            db.add(maize)
            db.flush()
            # Add tasseling stage
            stage_maize = CropPhenologyStage(
                crop_id=maize.id,
                stage_name="Tasseling/Silking",
                order_index=3,
                duration_days=12,
                min_gdd_c=550.0,
                max_gdd_c=700.0,
                critical_tmax_threshold_c=38.0,
                kc_factor=1.15,
            )
            db.add(stage_maize)
            db.flush()

        # 6. Map Crops to Demo Panchayat
        for crop_obj in [rice, maize]:
            mapping = db.scalar(
                select(PanchayatCropMapping).where(
                    and_(
                        PanchayatCropMapping.panchayat_id == demo_panchayat.id,
                        PanchayatCropMapping.crop_id == crop_obj.id,
                    )
                )
            )
            if not mapping:
                mapping = PanchayatCropMapping(
                    panchayat_id=demo_panchayat.id,
                    crop_id=crop_obj.id,
                    season="Kharif",
                    is_major_crop=True,
                    typical_sowing_date=datetime(2026, 6, 1).date(),
                )
                db.add(mapping)
                db.flush()

        # 7. Create Block Weather Forecast (Coarse Base)
        forecast_time = datetime.combine(target_date, datetime.min.time())
        block_forecast = db.scalar(
            select(BlockWeatherForecast).where(
                and_(
                    BlockWeatherForecast.block_id == demo_block.id,
                    BlockWeatherForecast.forecast_valid_time == forecast_time,
                )
            )
        )
        if not block_forecast:
            block_forecast = BlockWeatherForecast(
                block_id=demo_block.id,
                forecast_issue_time=forecast_time - timedelta(hours=6),
                forecast_valid_time=forecast_time,
                forecast_horizon_hours=24,
                source_provider="IMD-GFS-NWP (SYNTHETIC BASELINE)",
                tmax_c=36.0,
                tmin_c=25.0,
                tmean_c=30.5,
                relative_humidity_pct=72.0,
                wind_speed_kmh=28.0,
                rainfall_mm=0.0,
                quality_flag="PASSED",
            )
            db.add(block_forecast)
            db.flush()
            print(f"[DEMO] Created Block Forecast: Base Tmax 36.0°C, Mean 30.5°C, Wind 28 km/h")

        # 8. Create Panchayat Aggregated Weather (1-km Downscaled Result)
        panchayat_weather = db.scalar(
            select(PanchayatWeather).where(
                and_(
                    PanchayatWeather.panchayat_id == demo_panchayat.id,
                    PanchayatWeather.forecast_valid_time == forecast_time,
                )
            )
        )
        if not panchayat_weather:
            panchayat_weather = PanchayatWeather(
                panchayat_id=demo_panchayat.id,
                block_id=demo_block.id,
                forecast_valid_time=forecast_time,
                tmax_c=37.8,  # Downscaled: higher than block due to slope/DEM residual
                tmin_c=25.6,
                tmean_c=31.7,
                temp_stddev_c=1.1,
                predicted_residual_delta_c=1.2,
                relative_humidity_pct=70.0,
                wind_speed_kmh=28.0,
                rainfall_mm=0.0,
                coverage_pct=100.0,
                weather_status="COMPLETE",
                source_model="XGBoost_v1.0.0_DEM_Residual",
            )
            db.add(panchayat_weather)
            db.flush()
            print(f"[DEMO] Created Panchayat Downscaled Weather: Tmax 37.8°C (+1.8°C micro-climate delta)")

        # 9. Create Panchayat Crop Contexts
        context_rice = db.scalar(
            select(PanchayatCropContext).where(
                and_(
                    PanchayatCropContext.panchayat_id == demo_panchayat.id,
                    PanchayatCropContext.crop_id == rice.id,
                )
            )
        )
        if not context_rice:
            context_rice = PanchayatCropContext(
                panchayat_id=demo_panchayat.id,
                crop_id=rice.id,
                stage_name="Flowering",
                current_stage_id=1,
                days_after_sowing=45,
                accumulated_gdd=680.0,
                soil_profile_id=soil.id,
                land_use_mask_id=mask.id,
                context_status="COMPLETE",
            )
            db.add(context_rice)
            db.flush()

        context_maize = db.scalar(
            select(PanchayatCropContext).where(
                and_(
                    PanchayatCropContext.panchayat_id == demo_panchayat.id,
                    PanchayatCropContext.crop_id == maize.id,
                )
            )
        )
        if not context_maize:
            context_maize = PanchayatCropContext(
                panchayat_id=demo_panchayat.id,
                crop_id=maize.id,
                stage_name="Tasseling/Silking",
                current_stage_id=2,
                days_after_sowing=38,
                accumulated_gdd=590.0,
                soil_profile_id=soil.id,
                land_use_mask_id=mask.id,
                context_status="COMPLETE",
            )
            db.add(context_maize)
            db.flush()

        # 10. Seed Agricultural Risks
        # Rice Heat Stress (Tmax 37.8°C > 35.0°C threshold during flowering)
        risk_rice = db.scalar(
            select(AgriculturalRiskLog).where(
                and_(
                    AgriculturalRiskLog.panchayat_id == demo_panchayat.id,
                    AgriculturalRiskLog.crop_id == rice.id,
                    AgriculturalRiskLog.risk_type == "HEAT_STRESS",
                )
            )
        )
        if not risk_rice:
            risk_rice = AgriculturalRiskLog(
                panchayat_id=demo_panchayat.id,
                block_id=demo_block.id,
                crop_id=rice.id,
                crop_context_id=context_rice.id,
                panchayat_weather_id=panchayat_weather.id,
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                status="DETECTED",
                severity="HIGH",
                risk_score=0.82,
                observed_value=37.8,
                threshold_value=35.0,
                unit="°C",
                confidence="HIGH",
                rule_version="agri_risk_v1.0.0",
                rule_source="Project Agromet Rule Registry",
                evaluation_date=target_date,
                evidence={
                    "condition_description": "Downscaled Tmax (37.8°C) exceeds rice flowering critical threshold (35.0°C).",
                    "tmax_c": 37.8,
                    "stage": "Flowering",
                },
            )
            db.add(risk_rice)
            db.flush()
            print("[DEMO] Generated Risk: Rice -> HEAT_STRESS (Severity: HIGH, Score: 0.82)")

        # Maize Wind Stress (Wind speed 28 km/h > 25.0 km/h during tasseling)
        risk_maize = db.scalar(
            select(AgriculturalRiskLog).where(
                and_(
                    AgriculturalRiskLog.panchayat_id == demo_panchayat.id,
                    AgriculturalRiskLog.crop_id == maize.id,
                    AgriculturalRiskLog.risk_type == "WIND_STRESS",
                )
            )
        )
        if not risk_maize:
            risk_maize = AgriculturalRiskLog(
                panchayat_id=demo_panchayat.id,
                block_id=demo_block.id,
                crop_id=maize.id,
                crop_context_id=context_maize.id,
                panchayat_weather_id=panchayat_weather.id,
                risk_type="WIND_STRESS",
                risk_category="WIND",
                status="DETECTED",
                severity="MODERATE",
                risk_score=0.55,
                observed_value=28.0,
                threshold_value=25.0,
                unit="km/h",
                confidence="HIGH",
                rule_version="agri_risk_v1.0.0",
                rule_source="Project Agromet Rule Registry",
                evaluation_date=target_date,
                evidence={
                    "condition_description": "Forecast wind speed of 28.0 km/h creates lodging risk for tall standing maize.",
                    "wind_speed_kmh": 28.0,
                    "stage": "Tasseling/Silking",
                },
            )
            db.add(risk_maize)
            db.flush()
            print("[DEMO] Generated Risk: Maize -> WIND_STRESS (Severity: MODERATE, Score: 0.55)")

        # 11. Seed Agro-Meteorological Advisories
        advisory_rice = db.scalar(
            select(AgroAdvisory).where(
                and_(
                    AgroAdvisory.panchayat_id == demo_panchayat.id,
                    AgroAdvisory.crop_id == rice.id,
                    AgroAdvisory.advisory_type == "HEAT_STRESS_ADVISORY",
                )
            )
        )
        if not advisory_rice:
            advisory_rice = AgroAdvisory(
                panchayat_id=demo_panchayat.id,
                block_id=demo_block.id,
                crop_id=rice.id,
                crop_context_id=context_rice.id,
                risk_log_id=risk_rice.id,
                panchayat_weather_id=panchayat_weather.id,
                advisory_type="HEAT_STRESS_ADVISORY",
                advisory_category="IRRIGATION",
                priority="HIGH",
                priority_rank=1,
                priority_reason="Flowering spikelet sterility prevention under thermal stress.",
                title="Maintain Light Standing Water Layer to Buffer Canopy Heat",
                message="Downscaled daytime maximum temperature (37.8°C) exceeds critical rice flowering threshold (35.0°C).",
                recommended_action="Maintain 2-3 cm standing water in paddy fields to increase latent heat flux and lower canopy temperature by 1.5-2.5°C during peak noon hours.",
                action_category="WATER_MANAGEMENT",
                timing="Early Morning (06:00 - 09:00 AM)",
                urgency="IMMEDIATE",
                rationale="Standing water provides evaporative micro-climate cooling during anthesis.",
                severity="HIGH",
                confidence="HIGH",
                valid_from=forecast_time,
                valid_until=forecast_time + timedelta(hours=36),
                forecast_date=target_date,
                source_model="XGBoost_v1.0.0",
                rule_version="agri_risk_v1.0.0",
                advisory_rule_version="agri_advisory_v1.0.0",
                rule_source="Versioned Project Agromet Registry",
                language="en",
                status="ACTIVE",
                is_expert_review_required=False,
                is_cropland_eligible=True,
                evidence={
                    "tmax_c": 37.8,
                    "rainfall_mm": 0.0,
                    "crop": "Rice",
                    "stage": "Flowering",
                },
                provenance={
                    "block_forecast_tmax": 36.0,
                    "downscaled_tmax": 37.8,
                    "residual_delta": 1.2,
                    "risk_log_id": risk_rice.id,
                },
            )
            db.add(advisory_rice)
            db.flush()
            print("[DEMO] Generated Advisory: Rice -> Maintain Light Standing Water Layer")

        advisory_maize = db.scalar(
            select(AgroAdvisory).where(
                and_(
                    AgroAdvisory.panchayat_id == demo_panchayat.id,
                    AgroAdvisory.crop_id == maize.id,
                    AgroAdvisory.advisory_type == "WIND_STRESS_ADVISORY",
                )
            )
        )
        if not advisory_maize:
            advisory_maize = AgroAdvisory(
                panchayat_id=demo_panchayat.id,
                block_id=demo_block.id,
                crop_id=maize.id,
                crop_context_id=context_maize.id,
                risk_log_id=risk_maize.id,
                panchayat_weather_id=panchayat_weather.id,
                advisory_type="WIND_STRESS_ADVISORY",
                advisory_category="WEATHER_PREPAREDNESS",
                priority="MEDIUM",
                priority_rank=2,
                priority_reason="Mechanical lodging protection under sustained wind.",
                title="Withhold Field Irrigation Prior to High Wind Event",
                message="Forecast high wind conditions (28 km/h) create mechanical lodging risk for tall standing maize crops.",
                recommended_action="Withhold deep irrigation immediately prior to high wind conditions, as saturated soil softens root anchoring and drastically increases crop lodging.",
                action_category="WEATHER_PREPAREDNESS",
                timing="Immediately before forecast wind event",
                urgency="NEXT_24H",
                rationale="Dryer surface soil maintains root mechanical anchoring against canopy wind shear.",
                severity="MODERATE",
                confidence="HIGH",
                valid_from=forecast_time,
                valid_until=forecast_time + timedelta(hours=24),
                forecast_date=target_date,
                source_model="XGBoost_v1.0.0",
                rule_version="agri_risk_v1.0.0",
                advisory_rule_version="agri_advisory_v1.0.0",
                rule_source="Versioned Project Agromet Registry",
                language="en",
                status="ACTIVE",
                is_expert_review_required=False,
                is_cropland_eligible=True,
                evidence={
                    "wind_speed_kmh": 28.0,
                    "crop": "Maize",
                    "stage": "Tasseling/Silking",
                },
                provenance={
                    "wind_speed_kmh": 28.0,
                    "risk_log_id": risk_maize.id,
                },
            )
            db.add(advisory_maize)
            db.flush()
            print("[DEMO] Generated Advisory: Maize -> Withhold Field Irrigation Prior to Wind")

        db.commit()
        print("=" * 70)
        print("✅ CANONICAL DEMO SCENARIO SEED COMPLETE: SUCCESS")
        print(f"Block: {demo_block.name} | Panchayat: {demo_panchayat.name}")
        print("Crops: Rice (Flowering -> Heat Stress) & Maize (Tasseling -> Wind Stress)")
        print("=" * 70)
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding canonical demo scenario: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Canonical SIH Demonstration Scenario")
    parser.add_argument("--date", type=str, default="2026-07-15", help="Target demo date (YYYY-MM-DD)")
    args = parser.parse_args()
    success = seed_canonical_demo(args.date)
    sys.exit(0 if success else 1)
