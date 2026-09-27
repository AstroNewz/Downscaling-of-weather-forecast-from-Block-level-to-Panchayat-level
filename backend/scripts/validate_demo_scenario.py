"""
SIH Demonstration Scenario Validation Script (Phase 13)
SIH Problem Statement 26074 (Agro-Meteorological Advisory Platform)

Validates that the complete 10-link canonical demonstration pipeline exists, is populated,
and maintains data integrity in the database:
1. Block Ingestion ('DEMO_BLOCK_01')
2. Panchayat GIS Boundary ('DEMO_PANCHAYAT_01')
3. Land-Use Cropland Mask (Eligible)
4. Localized Soil Profile (Hydrological Capacity)
5. Multi-Crop Diversity (Rice + Maize)
6. Crop Phenology Stage & DAS Context
7. Coarse Block Weather Forecast (Baseline)
8. Area-Weighted Downscaled Panchayat Weather
9. Detected Agronomic Multi-Hazards (Heat Stress + Wind Stress)
10. Actionable Agro-Meteorological Advisories & Complete Provenance
"""
import sys
import os
import argparse
from datetime import datetime

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, and_
from app.db.session import SessionLocal
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import BlockWeatherForecast, PanchayatWeather
from app.db.models.agriculture import Crop, CropPhenologyStage, SoilProfile, PanchayatCropContext
from app.db.models.advisory import AgriculturalRiskLog, AgroAdvisory


def validate_demo_scenario(date_str: str = "2026-07-15") -> bool:
    print("=" * 70)
    print("🔍 SIH 26074 DEMONSTRATION PIPELINE VALIDATOR (PHASE 13)")
    print("=" * 70)
    print(f"Target Evaluation Date: {date_str}")
    print("-" * 70)

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    forecast_time = datetime.combine(target_date, datetime.min.time())
    db = SessionLocal()

    errors = []
    checks = []

    try:
        # 1. Block Check
        demo_block = db.scalar(select(Block).where(Block.lgd_code == "DEMO_BLOCK_01"))
        if demo_block:
            checks.append(f"✓ Link 1: Block '{demo_block.name}' (ID: {demo_block.id}) verified.")
        else:
            errors.append("✗ Link 1: Block 'DEMO_BLOCK_01' not found.")

        # 2. Panchayat Check
        demo_panchayat = None
        if demo_block:
            demo_panchayat = db.scalar(select(Panchayat).where(Panchayat.lgd_code == "DEMO_PANCHAYAT_01"))
            if demo_panchayat:
                checks.append(f"✓ Link 2: Panchayat '{demo_panchayat.name}' (ID: {demo_panchayat.id}) verified.")
            else:
                errors.append("✗ Link 2: Panchayat 'DEMO_PANCHAYAT_01' not found.")

        # 3. Cropland Mask Check
        if demo_panchayat:
            mask = db.scalar(select(LandUseMask).where(LandUseMask.panchayat_id == demo_panchayat.id))
            if mask and mask.is_agricultural_eligible:
                checks.append(f"✓ Link 3: Cropland mask verified ({mask.cropland_area_hectares:.0f} ha eligible).")
            else:
                errors.append("✗ Link 3: Valid cropland eligibility mask not found.")

        # 4. Soil Profile Check
        if demo_panchayat:
            soil = db.scalar(select(SoilProfile).where(SoilProfile.panchayat_id == demo_panchayat.id))
            if soil and soil.water_holding_capacity_pct:
                checks.append(f"✓ Link 4: Soil profile verified ({soil.soil_type}, AWC: {soil.water_holding_capacity_pct}%).")
            else:
                errors.append("✗ Link 4: Soil hydrological profile missing.")

        # 5. Multi-Crop Check
        crops = db.scalars(select(Crop).where(Crop.name.like("%[DEMO]%"))).all()
        if len(crops) >= 2:
            crop_names = [c.name for c in crops]
            checks.append(f"✓ Link 5: Multi-crop separation verified ({len(crops)} crops: {', '.join(crop_names)}).")
        else:
            errors.append(f"✗ Link 5: Expected >= 2 demo crops, found {len(crops)}.")

        # 6. Crop Context Check
        if demo_panchayat:
            contexts = db.scalars(select(PanchayatCropContext).where(PanchayatCropContext.panchayat_id == demo_panchayat.id)).all()
            if len(contexts) >= 2:
                stages = [f"{c.crop.name if c.crop else c.crop_id}: {c.stage_name}" for c in contexts]
                checks.append(f"✓ Link 6: Phenological contexts resolved ({', '.join(stages)}).")
            else:
                errors.append("✗ Link 6: Phenology crop contexts missing.")

        # 7. Block Forecast Check
        if demo_block:
            block_f = db.scalar(
                select(BlockWeatherForecast).where(
                    and_(
                        BlockWeatherForecast.block_id == demo_block.id,
                        BlockWeatherForecast.forecast_valid_time == forecast_time,
                    )
                )
            )
            if block_f:
                checks.append(f"✓ Link 7: Coarse Block Forecast verified (Base Tmax: {block_f.tmax_c:.1f}°C, Wind: {block_f.wind_speed_kmh:.1f} km/h).")
            else:
                errors.append(f"✗ Link 7: Block weather forecast not found for {date_str}.")

        # 8. Panchayat Downscaled Weather Check
        if demo_panchayat:
            p_weather = db.scalar(
                select(PanchayatWeather).where(
                    and_(
                        PanchayatWeather.panchayat_id == demo_panchayat.id,
                        PanchayatWeather.forecast_valid_time == forecast_time,
                    )
                )
            )
            if p_weather:
                checks.append(f"✓ Link 8: 1-km Downscaled Panchayat Weather verified (Tmax: {p_weather.tmax_c:.1f}°C, ΔT: +{p_weather.predicted_residual_delta_c:.1f}°C).")
            else:
                errors.append(f"✗ Link 8: Downscaled Panchayat weather record missing.")

        # 9. Multi-Hazard Risks Check
        if demo_panchayat:
            risks = db.scalars(
                select(AgriculturalRiskLog).where(
                    and_(
                        AgriculturalRiskLog.panchayat_id == demo_panchayat.id,
                        AgriculturalRiskLog.evaluation_date == target_date,
                    )
                )
            ).all()
            if len(risks) >= 2:
                risk_summary = [f"{r.risk_type} ({r.severity})" for r in risks]
                checks.append(f"✓ Link 9: Multi-hazard risks evaluated ({', '.join(risk_summary)}).")
            else:
                errors.append(f"✗ Link 9: Expected >= 2 evaluated risks, found {len(risks)}.")

        # 10. Actionable Advisories & Provenance Check
        if demo_panchayat:
            advisories = db.scalars(
                select(AgroAdvisory).where(
                    and_(
                        AgroAdvisory.panchayat_id == demo_panchayat.id,
                        AgroAdvisory.forecast_date == target_date,
                    )
                )
            ).all()
            if len(advisories) >= 2:
                adv_titles = [f"{a.crop_name if hasattr(a, 'crop_name') else 'Crop'}: {a.title[:35]}..." for a in advisories]
                checks.append(f"✓ Link 10: Actionable Advisories verified ({len(advisories)} active advisories).")
            else:
                errors.append(f"✗ Link 10: Expected >= 2 generated advisories, found {len(advisories)}.")

        # Print Checks
        for c in checks:
            print(c)

        print("-" * 70)
        if len(errors) == 0:
            print("🎉 DEMO SCENARIO: PASS (All 10 pipeline stages validated)")
            print("=" * 70)
            return True
        else:
            print("❌ DEMO SCENARIO: FAIL")
            for e in errors:
                print(f"  {e}")
            print("=" * 70)
            return False

    except Exception as ex:
        print(f"❌ Exception validating demo scenario: {ex}")
        return False
    finally:
        db.close()


validate_canonical_demo = validate_demo_scenario


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Canonical SIH Demonstration Scenario")
    parser.add_argument("--date", type=str, default="2026-07-15", help="Target demo date (YYYY-MM-DD)")
    args = parser.parse_args()
    success = validate_demo_scenario(args.date)
    sys.exit(0 if success else 1)
