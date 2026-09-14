"""
SIH Demonstration Scenario Reset Script (Phase 13)
SIH Problem Statement 26074 (Agro-Meteorological Advisory Platform)

Safely wipes ONLY synthetic/demo entities (prefixed with 'DEMO_' or '[DEMO]')
without modifying or deleting any operational or production database records:
- Deletes DEMO AgroAdvisories
- Deletes DEMO AgriculturalRiskLogs
- Deletes DEMO PanchayatCropContexts
- Deletes DEMO PanchayatWeather records
- Deletes DEMO BlockWeatherForecast records
- Deletes DEMO PanchayatCropMappings
- Deletes DEMO CropPhenologyStages & Crops
- Deletes DEMO SoilProfiles
- Deletes DEMO LandUseMasks
- Deletes DEMO Panchayats & Blocks
"""
import sys
import os
import argparse

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, delete
from app.db.session import SessionLocal
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import BlockWeatherForecast, PanchayatWeather
from app.db.models.agriculture import Crop, CropPhenologyStage, SoilProfile, PanchayatCropMapping, PanchayatCropContext
from app.db.models.advisory import AgriculturalRiskLog, AgroAdvisory


def reset_demo_scenario(force: bool = False) -> bool:
    print("=" * 70)
    print("🧹 SIH 26074 DEMONSTRATION SCENARIO RESETTER (PHASE 13)")
    print("=" * 70)

    db = SessionLocal()
    try:
        # Find demo block and panchayat
        demo_blocks = db.scalars(select(Block).where(Block.lgd_code.like("DEMO_%"))).all()
        demo_panchayats = db.scalars(select(Panchayat).where(Panchayat.lgd_code.like("DEMO_%"))).all()
        demo_crops = db.scalars(select(Crop).where(Crop.name.like("%[DEMO]%"))).all()

        p_ids = [p.id for p in demo_panchayats]
        b_ids = [b.id for b in demo_blocks]
        c_ids = [c.id for c in demo_crops]

        print(f"[DEMO RESET] Identified Demo Entities:")
        print(f"  - Demo Blocks: {len(b_ids)} ({[b.name for b in demo_blocks]})")
        print(f"  - Demo Panchayats: {len(p_ids)} ({[p.name for p in demo_panchayats]})")
        print(f"  - Demo Crops: {len(c_ids)} ({[c.name for c in demo_crops]})")

        if len(b_ids) == 0 and len(p_ids) == 0 and len(c_ids) == 0:
            print("[DEMO RESET] No demo entities found. Database is already clean.")
            return True

        # 1. Delete Advisories
        if p_ids:
            adv_count = db.query(AgroAdvisory).filter(AgroAdvisory.panchayat_id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {adv_count} demo agro-advisory records.")

        # 2. Delete Risk Logs
        if p_ids:
            risk_count = db.query(AgriculturalRiskLog).filter(AgriculturalRiskLog.panchayat_id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {risk_count} demo agricultural risk log records.")

        # 3. Delete Crop Contexts
        if p_ids:
            ctx_count = db.query(PanchayatCropContext).filter(PanchayatCropContext.panchayat_id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {ctx_count} demo crop context records.")

        # 4. Delete Panchayat Weather
        if p_ids:
            pw_count = db.query(PanchayatWeather).filter(PanchayatWeather.panchayat_id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {pw_count} demo panchayat weather records.")

        # 5. Delete Block Weather
        if b_ids:
            bw_count = db.query(BlockWeatherForecast).filter(BlockWeatherForecast.block_id.in_(b_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {bw_count} demo block weather records.")

        # 6. Delete Panchayat Crop Mappings
        if p_ids:
            map_count = db.query(PanchayatCropMapping).filter(PanchayatCropMapping.panchayat_id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {map_count} demo crop mapping records.")

        # 7. Delete Soil Profiles
        if p_ids:
            soil_count = db.query(SoilProfile).filter(SoilProfile.panchayat_id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {soil_count} demo soil profile records.")

        # 8. Delete Land Use Masks
        if p_ids:
            mask_count = db.query(LandUseMask).filter(LandUseMask.panchayat_id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {mask_count} demo land use mask records.")

        # 9. Delete Panchayats
        if p_ids:
            p_count = db.query(Panchayat).filter(Panchayat.id.in_(p_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {p_count} demo panchayat records.")

        # 10. Delete Blocks
        if b_ids:
            b_count = db.query(Block).filter(Block.id.in_(b_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {b_count} demo block records.")

        # 11. Delete Demo Crops & Stages
        if c_ids:
            db.query(CropPhenologyStage).filter(CropPhenologyStage.crop_id.in_(c_ids)).delete(synchronize_session=False)
            c_count = db.query(Crop).filter(Crop.id.in_(c_ids)).delete(synchronize_session=False)
            print(f"[DEMO RESET] Deleted {c_count} demo crop records.")

        db.commit()
        print("=" * 70)
        print("✅ DEMO RESET COMPLETE: All synthetic/demo records safely removed.")
        print("Operational/Production data remained strictly untouched.")
        print("=" * 70)
        return True

    except Exception as ex:
        db.rollback()
        print(f"❌ Error resetting demo scenario: {ex}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely Reset SIH Demonstration Scenario Entities")
    parser.add_argument("--force", action="store_true", help="Force deletion without confirmation prompt")
    args = parser.parse_args()
    success = reset_demo_scenario(args.force)
    sys.exit(0 if success else 1)
