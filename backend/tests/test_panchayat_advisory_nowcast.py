"""
Unit and Integration Tests for Panchayat-Level Precipitation Nowcast Advisory Integration.
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services - Task 5).

Verifies:
1. Baseline advisory preservation (when nowcast is None or INSUFFICIENT_DATA).
2. Explicit nowcast advisory-use states (NOT_AVAILABLE, INSUFFICIENT_DATA, LOW, MEDIUM, HIGH).
3. Conservative agronomic policy execution:
   - Spraying deferral when rain is imminent (30-60m) with high confidence.
   - Irrigation withholding when rain is likely (60-120m).
   - Clear window confirmation when dry with high confidence.
4. Cautious handling of low-confidence nowcasts (no false aggressive interventions).
5. Disagreement detection and conservative phrasing when NWP and satellite contradict.
6. Adjacent Panchayat A/B differentiation under identical Block NWP baselines.
7. Side-by-side baseline and nowcast context preservation (auditability).
8. Full backward compatibility of AdvisoryResult schema and Presentation Contract (Action/Why/Timing).
"""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from app.schemas.advisory import (
    AdvisoryResult,
    AdvisoryAction,
    NowcastAdvisoryState,
    LocalizedPrecipitationAdvisoryEvidence,
    NowcastAdvisoryExplanation,
    AdvisoryType,
    AdvisoryCategory,
    AdvisoryPriority,
    AdvisoryActionCategory,
    AdvisoryUrgency,
)
from app.schemas.precipitation_nowcast import (
    PanchayatPrecipitationNowcastResult,
    PrecipitationNowcastHorizonResult,
    BaselinePrecipitationExpectation,
    PrecipitationNowcastProvenance,
    NowcastConfidence,
    PrecipitationSourceState,
)
from app.services.advisory_nowcast_service import (
    PanchayatAdvisoryNowcastService,
    panchayat_advisory_nowcast_service,
)


def _make_dummy_baseline_advisory(
    panchayat_id: int = 101,
    panchayat_name: str = "Dholakpur West",
    crop_name: str = "Wheat",
    advisory_type: str = "WATER_STRESS_ADVISORY",
    action_text: str = "Apply light irrigation in late afternoon to maintain soil moisture.",
) -> AdvisoryResult:
    """Creates a sample Phase 11 baseline AdvisoryResult."""
    return AdvisoryResult(
        id=1,
        panchayat_id=panchayat_id,
        panchayat_name=panchayat_name,
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name=crop_name,
        stage_name="Crown Root Initiation",
        advisory_type=advisory_type,
        advisory_category="ACTION_ADVISORY",
        priority="HIGH",
        priority_rank=1,
        title=f"{crop_name} Moisture Management Advisory",
        message="Mild moisture deficit detected in root zone. Supplemental irrigation advised.",
        action=AdvisoryAction(
            action_category="WATER_MANAGEMENT",
            action_text=action_text,
            timing="Next 24 hours",
            urgency="UPCOMING",
            conditions={"stage": "Crown Root Initiation"},
        ),
        rationale="Soil moisture tension is approaching critical threshold during moisture-sensitive crown root stage.",
        valid_from="2026-09-27T00:00:00",
        valid_until="2026-09-27T23:59:59",
        forecast_date="2026-09-27T00:00:00",
        issue_time="2026-09-27T06:00:00",
        source_model="IMD-GFS",
        rule_version="agri_risk_v1.0.0",
        advisory_rule_version="agri_advisory_v1.0.0",
        rule_source="ICAR_IMD_AGROMET_GUIDELINES",
        language="en",
        status="ACTIVE",
    )


def _make_mock_nowcast(
    panchayat_id: str = "101",
    panchayat_name: str = "Dholakpur West",
    rain_prob_30: float = 0.85,
    rain_prob_60: float = 0.90,
    rain_prob_120: float = 0.75,
    expected_mm_60: float = 12.5,
    confidence: NowcastConfidence = NowcastConfidence.HIGH,
    source_state: PrecipitationSourceState = PrecipitationSourceState.NWP_SATELLITE,
    disagreement: bool = False,
    disagreement_reason: str = None,
    baseline_mm: float = 5.0,
    baseline_prob: float = 0.40,
) -> PanchayatPrecipitationNowcastResult:
    """Creates a mock PanchayatPrecipitationNowcastResult for testing."""
    now_iso = datetime.utcnow().isoformat()
    h30 = PrecipitationNowcastHorizonResult(
        horizon_minutes=30,
        valid_time=(datetime.utcnow() + timedelta(minutes=30)).isoformat(),
        rain_probability=rain_prob_30,
        is_rain_likely=rain_prob_30 >= 0.50,
        expected_amount_mm=round(expected_mm_60 * 0.4, 1),
        confidence=confidence,
        confidence_score=0.90 if confidence == NowcastConfidence.HIGH else 0.40,
        evidence_sources=["NWP", "SATELLITE"],
        source_state=source_state,
        evidence_disagreement=disagreement,
        disagreement_reason=disagreement_reason,
        observation_age_minutes=12.0,
        spatial_coverage=1.0,
        fusion_method="DETERMINISTIC_RESEARCH_HEURISTIC_V1",
    )
    h60 = PrecipitationNowcastHorizonResult(
        horizon_minutes=60,
        valid_time=(datetime.utcnow() + timedelta(minutes=60)).isoformat(),
        rain_probability=rain_prob_60,
        is_rain_likely=rain_prob_60 >= 0.50,
        expected_amount_mm=expected_mm_60,
        confidence=confidence,
        confidence_score=0.90 if confidence == NowcastConfidence.HIGH else 0.40,
        evidence_sources=["NWP", "SATELLITE"],
        source_state=source_state,
        evidence_disagreement=disagreement,
        disagreement_reason=disagreement_reason,
        observation_age_minutes=12.0,
        spatial_coverage=1.0,
        fusion_method="DETERMINISTIC_RESEARCH_HEURISTIC_V1",
    )
    h120 = PrecipitationNowcastHorizonResult(
        horizon_minutes=120,
        valid_time=(datetime.utcnow() + timedelta(minutes=120)).isoformat(),
        rain_probability=rain_prob_120,
        is_rain_likely=rain_prob_120 >= 0.50,
        expected_amount_mm=round(expected_mm_60 * 1.2, 1),
        confidence=confidence,
        confidence_score=0.85 if confidence == NowcastConfidence.HIGH else 0.35,
        evidence_sources=["NWP", "SATELLITE"],
        source_state=source_state,
        evidence_disagreement=disagreement,
        disagreement_reason=disagreement_reason,
        observation_age_minutes=12.0,
        spatial_coverage=1.0,
        fusion_method="DETERMINISTIC_RESEARCH_HEURISTIC_V1",
    )

    return PanchayatPrecipitationNowcastResult(
        panchayat_id=panchayat_id,
        panchayat_name=panchayat_name,
        block_id=1,
        block_name="Dholakpur",
        issue_time=now_iso,
        baseline_forecast=BaselinePrecipitationExpectation(
            source_model="IMD-GFS",
            forecast_valid_time=now_iso,
            baseline_precipitation_mm=baseline_mm,
            baseline_probability=baseline_prob,
            block_id=1,
            block_name="Dholakpur",
        ),
        horizons={
            "30m": h30,
            "60m": h60,
            "120m": h120,
        },
        primary_horizon=h60,
        source_state=source_state,
        overall_source_state=source_state,
        overall_confidence=confidence,
        evidence_disagreement=disagreement,
        disagreement_details=disagreement_reason,
        provenance=PrecipitationNowcastProvenance(
            nwp_source="IMD-GFS-0.25deg",
            satellite_source="INSAT-3D-HEM",
            evidence_weight_version="RESEARCH_HEURISTIC_V1",
            generated_at=now_iso,
        ),
    )


# ============================================================================
# TEST CASES
# ============================================================================

def test_advisory_state_derivation():
    """Verifies correct mapping of nowcast evidence to NowcastAdvisoryState enum."""
    svc = PanchayatAdvisoryNowcastService()

    # Case 1: None nowcast
    assert svc.determine_advisory_state(None) == NowcastAdvisoryState.NOWCAST_NOT_AVAILABLE

    # Case 2: Insufficient data
    nc_insufficient = _make_mock_nowcast(
        confidence=NowcastConfidence.INSUFFICIENT_DATA,
        source_state=PrecipitationSourceState.INSUFFICIENT_DATA,
    )
    assert svc.determine_advisory_state(nc_insufficient) == NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA

    # Case 3: Low confidence
    nc_low = _make_mock_nowcast(confidence=NowcastConfidence.LOW)
    assert svc.determine_advisory_state(nc_low) == NowcastAdvisoryState.NOWCAST_LOW_CONFIDENCE

    # Case 4: Medium confidence
    nc_med = _make_mock_nowcast(confidence=NowcastConfidence.MEDIUM)
    assert svc.determine_advisory_state(nc_med) == NowcastAdvisoryState.NOWCAST_MEDIUM_CONFIDENCE

    # Case 5: High confidence
    nc_high = _make_mock_nowcast(confidence=NowcastConfidence.HIGH)
    assert svc.determine_advisory_state(nc_high) == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE


def test_baseline_preservation_when_nowcast_is_none():
    """
    Verifies that when nowcast is None, baseline advisories are 100% unaltered.
    Action, Timing, and Rationale remain identical.
    """
    svc = PanchayatAdvisoryNowcastService()
    baseline = _make_dummy_baseline_advisory()
    original_action = baseline.action.action_text
    original_timing = baseline.action.timing
    original_rationale = baseline.rationale

    enriched = svc.enrich_advisories_with_nowcast([baseline], nowcast=None)

    assert len(enriched) == 1
    adv = enriched[0]
    assert adv.nowcast_advisory_state == NowcastAdvisoryState.NOWCAST_NOT_AVAILABLE
    assert adv.localized_nowcast_context is None
    assert adv.baseline_precipitation_context is None
    assert adv.action.action_text == original_action
    assert adv.action.timing == original_timing
    assert adv.rationale == original_rationale
    assert adv.nowcast_explanation.action_strength == "NO_ACTION"


def test_insufficient_data_never_treated_as_no_rain():
    """
    Critical guardrail: INSUFFICIENT_DATA must NEVER be treated as 'no rain' or used to cancel precautions.
    """
    svc = PanchayatAdvisoryNowcastService()
    baseline = _make_dummy_baseline_advisory()
    original_action = baseline.action.action_text

    nc_insufficient = _make_mock_nowcast(
        rain_prob_30=0.0,
        rain_prob_60=0.0,
        confidence=NowcastConfidence.INSUFFICIENT_DATA,
        source_state=PrecipitationSourceState.INSUFFICIENT_DATA,
    )

    enriched = svc.enrich_advisories_with_nowcast([baseline], nowcast=nc_insufficient)
    adv = enriched[0]

    assert adv.nowcast_advisory_state == NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA
    # Baseline action text must NOT say "Clear skies" or remove irrigation recommendation
    assert "clear window" not in adv.action.action_text.lower()
    assert adv.action.action_text == original_action
    assert adv.nowcast_explanation.action_strength == "NO_ACTION"


def test_high_confidence_imminent_rain_modifies_irrigation():
    """
    Verifies that HIGH confidence imminent rain modifies baseline irrigation guidance
    with a clear short-horizon deferral alert while preserving the original baseline context.
    """
    svc = PanchayatAdvisoryNowcastService()
    baseline = _make_dummy_baseline_advisory(
        advisory_type="WATER_STRESS_ADVISORY",
        action_text="Apply light irrigation in late afternoon.",
    )

    nc_rain = _make_mock_nowcast(
        rain_prob_30=0.85,
        rain_prob_60=0.90,
        expected_mm_60=14.0,
        confidence=NowcastConfidence.HIGH,
    )

    enriched = svc.enrich_advisories_with_nowcast([baseline], nowcast=nc_rain)
    adv = enriched[0]

    assert adv.nowcast_advisory_state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE
    assert "[Short-Horizon Alert: Defer Irrigation]" in adv.action.action_text
    assert "Apply light irrigation in late afternoon." in adv.action.action_text  # Original action preserved
    assert adv.action.urgency == AdvisoryUrgency.IMMEDIATE.value
    assert adv.localized_nowcast_context is not None
    assert adv.localized_nowcast_context.rain_probability >= 0.85
    assert adv.baseline_precipitation_context["baseline_precipitation_mm"] == 5.0
    assert adv.nowcast_explanation.action_strength == "STRONG"


def test_high_confidence_imminent_rain_spraying_advisory():
    """
    Verifies generation of dedicated short-horizon spraying window advisory
    when rain is imminent with HIGH confidence.
    """
    svc = PanchayatAdvisoryNowcastService()
    nc_rain = _make_mock_nowcast(
        rain_prob_30=0.90,
        rain_prob_60=0.85,
        expected_mm_60=10.0,
        confidence=NowcastConfidence.HIGH,
    )

    ops = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=101,
        panchayat_name="Dholakpur West",
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name="Wheat",
        forecast_date=datetime(2026, 9, 27, 6, 0),
        nowcast=nc_rain,
    )

    # Should produce spraying deferral and irrigation withholding
    assert len(ops) >= 1
    spray_adv = next((a for a in ops if a.action.action_category == "CROP_PROTECTION"), None)
    assert spray_adv is not None
    assert "Postpone chemical spraying" in spray_adv.action.action_text
    assert "washes active ingredients" in spray_adv.rationale
    assert "Next 30" in spray_adv.action.timing
    assert spray_adv.priority == AdvisoryPriority.HIGH.value
    assert spray_adv.action.urgency == AdvisoryUrgency.IMMEDIATE.value


def test_clear_window_spraying_confirmation():
    """
    Verifies that when nowcast detects clear skies with HIGH confidence,
    a favorable short-horizon operational spraying window is confirmed.
    """
    svc = PanchayatAdvisoryNowcastService()
    nc_dry = _make_mock_nowcast(
        rain_prob_30=0.05,
        rain_prob_60=0.08,
        rain_prob_120=0.10,
        expected_mm_60=0.0,
        confidence=NowcastConfidence.HIGH,
    )

    ops = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=101,
        panchayat_name="Dholakpur West",
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name="Wheat",
        forecast_date=datetime(2026, 9, 27, 6, 0),
        nowcast=nc_dry,
    )

    spray_adv = next((a for a in ops if a.action.action_category == "CROP_PROTECTION"), None)
    assert spray_adv is not None
    assert "Favorable window for necessary foliar spraying" in spray_adv.action.action_text
    assert "low rain probability" in spray_adv.rationale
    assert spray_adv.priority == AdvisoryPriority.LOW.value


def test_low_confidence_prevents_aggressive_intervention():
    """
    Verifies that LOW confidence nowcast does not create aggressive intervention
    or cancel existing operations.
    """
    svc = PanchayatAdvisoryNowcastService()
    baseline = _make_dummy_baseline_advisory()
    original_action = baseline.action.action_text

    nc_low = _make_mock_nowcast(
        rain_prob_30=0.75,
        rain_prob_60=0.70,
        confidence=NowcastConfidence.LOW,
    )

    # 1. Enriched baseline must keep original action
    enriched = svc.enrich_advisories_with_nowcast([baseline], nowcast=nc_low)
    adv = enriched[0]
    assert adv.nowcast_advisory_state == NowcastAdvisoryState.NOWCAST_LOW_CONFIDENCE
    assert adv.action.action_text == original_action  # Unadjusted
    assert adv.nowcast_explanation.action_strength == "CONTEXT_ONLY"

    # 2. Standalone ops should NOT generate high-urgency interventions
    ops = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=101,
        panchayat_name="Dholakpur West",
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name="Wheat",
        forecast_date=datetime(2026, 9, 27, 6, 0),
        nowcast=nc_low,
    )
    assert len(ops) == 0  # No aggressive advisory under LOW confidence


def test_disagreement_nwp_rain_vs_satellite_dry():
    """
    Verifies cautious advisory handling when NWP predicts rain but satellite detects clear skies.
    Disagreement must be explicitly stated and confidence capped at LOW.
    """
    svc = PanchayatAdvisoryNowcastService()
    nc_disagree = _make_mock_nowcast(
        rain_prob_30=0.10,
        rain_prob_60=0.12,
        expected_mm_60=0.0,
        baseline_mm=18.0,
        baseline_prob=0.85,
        confidence=NowcastConfidence.LOW,
        disagreement=True,
        disagreement_reason="NWP indicates widespread heavy rainfall, but georeferenced satellite IR shows clear skies over Panchayat.",
    )

    ops = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=101,
        panchayat_name="Dholakpur West",
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name="Mustard",
        forecast_date=datetime(2026, 9, 27, 6, 0),
        nowcast=nc_disagree,
    )

    disagree_adv = next((a for a in ops if "Divergence" in a.title), None)
    assert disagree_adv is not None
    assert "Forecast Signal Divergence" in disagree_adv.title
    assert "Exercise caution" in disagree_adv.action.action_text
    assert "Evidence divergence" in disagree_adv.rationale
    assert disagree_adv.confidence == "LOW"
    assert disagree_adv.nowcast_explanation.evidence_agreement is False


def test_adjacent_panchayat_ab_differentiation():
    """
    CRITICAL SIH REQUIREMENT:
    Adjacent Panchayats A and B in Dholakpur Block share the EXACT SAME Block NWP forecast.
    However, localized satellite nowcast detects imminent convective rain in Panchayat A,
    while Panchayat B remains completely clear.
    
    Verifies:
    - Panchayat A receives immediate spraying deferral & irrigation withholding.
    - Panchayat B receives clear operational window for foliar management.
    """
    svc = PanchayatAdvisoryNowcastService()
    forecast_dt = datetime(2026, 9, 27, 6, 0)

    # Common Block NWP: 6.0 mm rain expected across Dholakpur Block
    common_baseline_mm = 6.0
    common_baseline_prob = 0.55

    # Panchayat A (Convective Cloud Cell Centered Over A)
    nc_a = _make_mock_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        panchayat_name="Dholakpur West",
        rain_prob_30=0.92,
        rain_prob_60=0.95,
        expected_mm_60=16.5,
        confidence=NowcastConfidence.HIGH,
        baseline_mm=common_baseline_mm,
        baseline_prob=common_baseline_prob,
    )

    # Panchayat B (Outside Cloud Shield / Clear Over B)
    nc_b = _make_mock_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_B",
        panchayat_name="Dholakpur East",
        rain_prob_30=0.08,
        rain_prob_60=0.10,
        expected_mm_60=0.0,
        confidence=NowcastConfidence.HIGH,
        baseline_mm=common_baseline_mm,
        baseline_prob=common_baseline_prob,
    )

    # 1. Generate advisories for Panchayat A
    advisories_a = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=101,
        panchayat_name="Dholakpur West",
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name="Cotton",
        forecast_date=forecast_dt,
        nowcast=nc_a,
    )

    # 2. Generate advisories for Panchayat B
    advisories_b = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=102,
        panchayat_name="Dholakpur East",
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name="Cotton",
        forecast_date=forecast_dt,
        nowcast=nc_b,
    )

    # Verify Panchayat A guidance: Rain precaution, delay spraying
    spray_a = next(a for a in advisories_a if a.action.action_category == "CROP_PROTECTION")
    assert "Postpone chemical spraying" in spray_a.action.action_text
    assert spray_a.priority == AdvisoryPriority.HIGH.value
    assert spray_a.action.urgency == AdvisoryUrgency.IMMEDIATE.value

    # Verify Panchayat B guidance: Clear window, proceed with operations
    spray_b = next(a for a in advisories_b if a.action.action_category == "CROP_PROTECTION")
    assert "Favorable window for necessary foliar spraying" in spray_b.action.action_text
    assert spray_b.priority == AdvisoryPriority.LOW.value
    assert spray_b.action.urgency == AdvisoryUrgency.ROUTINE.value

    # Contrast check: Same crop, same block, opposite operational recommendations
    assert spray_a.action.action_text != spray_b.action.action_text
    assert spray_a.priority != spray_b.priority
    assert spray_a.localized_nowcast_context.rain_probability == 0.95
    assert spray_b.localized_nowcast_context.rain_probability == 0.10
    # Both preserve the exact same baseline
    assert spray_a.baseline_precipitation_context["baseline_precipitation_mm"] == 6.0
    assert spray_b.baseline_precipitation_context["baseline_precipitation_mm"] == 6.0


def test_presentation_contract_action_why_timing():
    """
    Verifies that all generated nowcast advisories adhere strictly to the presentation contract:
    - Action: non-empty action_text
    - Why: non-empty rationale
    - Timing: non-empty timing
    """
    svc = PanchayatAdvisoryNowcastService()
    nc = _make_mock_nowcast(rain_prob_30=0.88, rain_prob_60=0.85, confidence=NowcastConfidence.HIGH)

    ops = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=101,
        panchayat_name="Dholakpur West",
        block_id=1,
        block_name="Dholakpur",
        crop_id=1,
        crop_name="Paddy",
        forecast_date=datetime(2026, 9, 27, 6, 0),
        nowcast=nc,
    )

    assert len(ops) >= 2
    for adv in ops:
        assert adv.action is not None
        assert adv.action.action_text and len(adv.action.action_text.strip()) > 10, "Action must be substantial"
        assert adv.rationale and len(adv.rationale.strip()) > 10, "Why (rationale) must be substantial"
        assert adv.action.timing and len(adv.action.timing.strip()) > 3, "Timing must be specified"
        assert adv.title and len(adv.title.strip()) > 5
        assert adv.message and len(adv.message.strip()) > 5


def test_backward_compatibility_schema_serialization():
    """
    Verifies that AdvisoryResult with localized nowcast fields serializes cleanly
    to dictionary / JSON and can be parsed by standard Pydantic models.
    """
    svc = PanchayatAdvisoryNowcastService()
    nc = _make_mock_nowcast(rain_prob_30=0.75, rain_prob_60=0.80, confidence=NowcastConfidence.HIGH)
    baseline = _make_dummy_baseline_advisory()

    enriched = svc.enrich_advisories_with_nowcast([baseline], nowcast=nc)
    adv = enriched[0]

    dumped = adv.model_dump()
    assert "localized_nowcast_context" in dumped
    assert "baseline_precipitation_context" in dumped
    assert "nowcast_advisory_state" in dumped
    assert "nowcast_explanation" in dumped

    # Round-trip deserialization
    reconstructed = AdvisoryResult(**dumped)
    assert reconstructed.panchayat_name == "Dholakpur West"
    assert reconstructed.nowcast_advisory_state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE
    assert reconstructed.localized_nowcast_context.rain_probability == 0.75


def test_advisory_engine_integration_with_nowcast():
    """
    Verifies that AdvisoryEngine.generate_panchayat_advisories correctly accepts
    nowcast_result and executes end-to-end enrichment alongside risk evaluation.
    """
    from unittest.mock import MagicMock
    from app.services.advisory_engine import AdvisoryEngine
    from app.schemas.agricultural_risk import RiskResult, RiskEvidence

    mock_db = MagicMock()
    mock_panchayat = MagicMock()
    mock_panchayat.id = 101
    mock_panchayat.name = "Dholakpur West"
    mock_panchayat.block_id = 1
    mock_panchayat.block = MagicMock()
    mock_panchayat.block.id = 1
    mock_panchayat.block.name = "Dholakpur"

    mock_db.scalar.return_value = mock_panchayat

    engine = AdvisoryEngine(db=mock_db)

    # Mock risk_engine to return a detected water stress risk
    mock_risk = RiskResult(
        id=1,
        panchayat_id=101,
        panchayat_name="Dholakpur West",
        block_id=1,
        crop_id=1,
        crop_name="Wheat",
        stage_name="Crown Root Initiation",
        risk_type="WATER_STRESS",
        risk_category="MOISTURE",
        status="DETECTED",
        severity="MODERATE",
        confidence="HIGH",
        risk_score=0.75,
        observed_value=12.0,
        threshold_value=20.0,
        unit="mm",
        evaluation_date="2026-09-27T00:00:00",
        rule_version="agri_risk_v1.0.0",
        evidence=RiskEvidence(
            crop_name="Wheat",
            condition_description="Root zone moisture deficit detected.",
            metrics={"sm_index": 0.45},
            contributing_factors=["Low precipitation"],
        ),
    )
    engine.risk_engine.evaluate_panchayat_crop_risks = MagicMock(return_value=[mock_risk])

    nc = _make_mock_nowcast(rain_prob_30=0.88, rain_prob_60=0.90, expected_mm_60=15.0, confidence=NowcastConfidence.HIGH)

    advisories = engine.generate_panchayat_advisories(
        panchayat_id=101,
        forecast_date=datetime(2026, 9, 27, 6, 0),
        persist_to_db=False,
        nowcast_result=nc,
    )

    assert len(advisories) >= 2
    # Verify baseline advisory was enriched with nowcast
    baseline_adv = next(a for a in advisories if a.advisory_type == "WATER_STRESS_ADVISORY")
    assert baseline_adv.nowcast_advisory_state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE
    assert baseline_adv.localized_nowcast_context is not None
    assert baseline_adv.baseline_precipitation_context is not None
    assert "[Short-Horizon Alert: Defer Irrigation]" in baseline_adv.action.action_text

    # Verify short-horizon operational advisories were appended
    ops_adv = next(a for a in advisories if a.advisory_type == AdvisoryType.SHORT_HORIZON_OPERATIONS_ADVISORY.value)
    assert ops_adv.nowcast_advisory_state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE

