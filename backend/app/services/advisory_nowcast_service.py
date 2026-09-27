"""
Panchayat-Level Precipitation Nowcast Advisory Service.
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services).

Integrates the Task 4 Panchayat-level observation-fused precipitation nowcast into the
agronomic advisory pipeline without breaking, replacing, or silently altering existing
baseline advisory logic.

Strict Scientific & Agronomic Governance:
- Source of truth for baseline seasonal/daily risk remains Phase 10 / Phase 11 Advisory Engine.
- Does NOT claim certified millimeter-level rainfall accuracy or replace validated rules.
- Strictly adheres to the two-stage representation: P(rain) and conditional E[rain].
- Explicit advisory-use states: NOWCAST_NOT_AVAILABLE, NOWCAST_INSUFFICIENT_DATA,
  NOWCAST_LOW_CONFIDENCE, NOWCAST_MEDIUM_CONFIDENCE, NOWCAST_HIGH_CONFIDENCE.
- Never treats INSUFFICIENT_DATA or LOW_CONFIDENCE as "no rain".
- If baseline and nowcast disagree, flags disagreement explicitly and caps confidence at LOW.
- Always preserves side-by-side baseline and nowcast contexts for complete auditability.
- Preserves the standard Presentation Contract: Action (action_text), Why (rationale), Timing (timing).
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.core.logging import logger
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
    NowcastConfidence,
    PrecipitationSourceState,
)


class PanchayatAdvisoryNowcastService:
    """
    Service responsible for fusing localized short-horizon precipitation nowcasts
    with agro-meteorological management guidance.
    """

    def __init__(self):
        self.version = "1.0.0"
        self.policy_version = "PANCHAYAT_NOWCAST_ADVISORY_POLICY_V1"

    def determine_advisory_state(
        self,
        nowcast: Optional[PanchayatPrecipitationNowcastResult],
    ) -> NowcastAdvisoryState:
        """
        Derives the explicit advisory-use operational state from a nowcast result.
        """
        if nowcast is None:
            return NowcastAdvisoryState.NOWCAST_NOT_AVAILABLE

        if not nowcast.horizons:
            return NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA

        # Inspect the 30m or 60m primary operational horizon
        primary_horizon = nowcast.horizons.get("30m") or nowcast.horizons.get("60m")
        if not primary_horizon:
            return NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA

        conf = primary_horizon.confidence
        source_state = primary_horizon.source_state

        if conf == NowcastConfidence.INSUFFICIENT_DATA or source_state == PrecipitationSourceState.INSUFFICIENT_DATA:
            return NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA
        elif conf == NowcastConfidence.LOW:
            return NowcastAdvisoryState.NOWCAST_LOW_CONFIDENCE
        elif conf == NowcastConfidence.MEDIUM:
            return NowcastAdvisoryState.NOWCAST_MEDIUM_CONFIDENCE
        elif conf == NowcastConfidence.HIGH:
            return NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE
        else:
            return NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA

    def build_evidence_context(
        self,
        nowcast: PanchayatPrecipitationNowcastResult,
        horizon_key: str = "60m",
    ) -> LocalizedPrecipitationAdvisoryEvidence:
        """
        Extracts structured localized precipitation nowcast evidence for advisory attachment.
        """
        horizon = nowcast.horizons.get(horizon_key) or list(nowcast.horizons.values())[0]

        return LocalizedPrecipitationAdvisoryEvidence(
            panchayat_id=str(nowcast.panchayat_id),
            valid_time=horizon.valid_time,
            horizon_minutes=horizon.horizon_minutes,
            rain_probability=round(horizon.rain_probability, 3),
            expected_amount_mm=round(horizon.expected_amount_mm, 2) if horizon.expected_amount_mm is not None else None,
            confidence=horizon.confidence.value,
            source_state=horizon.source_state.value,
            evidence_sources=horizon.evidence_sources,
            evidence_disagreement=horizon.evidence_disagreement,
            disagreement_reason=horizon.disagreement_reason,
            spatial_coverage=round(horizon.spatial_coverage, 3),
            observation_age_minutes=round(horizon.observation_age_minutes, 1),
            method_version=horizon.fusion_method,
            provenance=nowcast.provenance.model_dump() if nowcast.provenance else None,
        )

    def build_baseline_context(
        self,
        nowcast: PanchayatPrecipitationNowcastResult,
    ) -> Dict[str, Any]:
        """
        Builds serializable macroscale NWP baseline context for audit trail comparison.
        """
        bf = nowcast.baseline_forecast
        return {
            "source_model": bf.source_model,
            "forecast_valid_time": bf.forecast_valid_time,
            "forecast_issue_time": bf.forecast_issue_time,
            "baseline_precipitation_mm": round(bf.baseline_precipitation_mm, 2),
            "baseline_probability": round(bf.baseline_probability, 3),
            "block_id": bf.block_id,
            "block_name": bf.block_name,
        }

    def enrich_advisories_with_nowcast(
        self,
        advisories: List[AdvisoryResult],
        nowcast: Optional[PanchayatPrecipitationNowcastResult],
    ) -> List[AdvisoryResult]:
        """
        Enriches existing baseline advisory results in-place with nowcast context and
        conservative short-horizon operational refinements without replacing baseline logic.
        """
        state = self.determine_advisory_state(nowcast)

        if nowcast is None or state == NowcastAdvisoryState.NOWCAST_NOT_AVAILABLE:
            for adv in advisories:
                adv.nowcast_advisory_state = NowcastAdvisoryState.NOWCAST_NOT_AVAILABLE
                adv.localized_nowcast_context = None
                adv.baseline_precipitation_context = None
                adv.nowcast_explanation = NowcastAdvisoryExplanation(
                    primary_reason="No localized nowcast executed; relying 100% on baseline downscaled forecast.",
                    localized_precipitation_signal="NONE",
                    baseline_signal="STANDARD_NWP",
                    evidence_agreement=True,
                    confidence="NOT_AVAILABLE",
                    action_strength="NO_ACTION",
                    recommended_horizon_minutes=60,
                    short_horizon_recommendation="Follow standard day-scale agronomic advisory guidance.",
                )
            return advisories

        # Valid or evaluated nowcast exists
        baseline_ctx = self.build_baseline_context(nowcast)
        
        # Select primary operational horizon: 30m if rain is imminent, else 60m
        h30 = nowcast.horizons.get("30m")
        h60 = nowcast.horizons.get("60m")
        primary_horizon_key = "30m" if (h30 and h30.is_rain_likely) else "60m"
        primary_h = nowcast.horizons.get(primary_horizon_key) or (h60 or h30)
        
        if not primary_h:
            # Insufficient horizon data
            for adv in advisories:
                adv.nowcast_advisory_state = NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA
                adv.baseline_precipitation_context = baseline_ctx
            return advisories

        evidence_ctx = self.build_evidence_context(nowcast, horizon_key=primary_horizon_key)
        is_rain_likely = primary_h.is_rain_likely
        rain_prob = primary_h.rain_probability
        disagreement = primary_h.evidence_disagreement
        conf = primary_h.confidence

        for adv in advisories:
            adv.localized_nowcast_context = evidence_ctx
            adv.baseline_precipitation_context = baseline_ctx
            adv.nowcast_advisory_state = state

            # Determine explainability parameters
            localized_sig = f"P(rain)={rain_prob:.2f} at {primary_h.horizon_minutes}m (Conf: {conf.value})"
            baseline_sig = f"NWP expected={baseline_ctx['baseline_precipitation_mm']}mm (P={baseline_ctx['baseline_probability']:.2f})"
            agreement = not disagreement

            # Conservative policy enforcement on existing actions:
            if state == NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA:
                adv.nowcast_explanation = NowcastAdvisoryExplanation(
                    primary_reason="Localized nowcast data is missing or insufficient. Preserving baseline guidance.",
                    localized_precipitation_signal=localized_sig,
                    baseline_signal=baseline_sig,
                    evidence_agreement=True,
                    confidence=conf.value,
                    action_strength="NO_ACTION",
                    recommended_horizon_minutes=primary_h.horizon_minutes,
                    short_horizon_recommendation="Baseline advisory remains active; observational data is insufficient to refine short-horizon timing.",
                )
                continue

            if state == NowcastAdvisoryState.NOWCAST_LOW_CONFIDENCE:
                adv.nowcast_explanation = NowcastAdvisoryExplanation(
                    primary_reason="Localized nowcast confidence is LOW. Baseline advisory remains unadjusted to prevent false interventions.",
                    localized_precipitation_signal=localized_sig,
                    baseline_signal=baseline_sig,
                    evidence_agreement=agreement,
                    confidence=conf.value,
                    action_strength="CONTEXT_ONLY",
                    recommended_horizon_minutes=primary_h.horizon_minutes,
                    short_horizon_recommendation="Monitor local sky conditions before beginning sensitive field operations.",
                )
                continue

            # When MEDIUM or HIGH confidence:
            action_strength = "STRONG" if state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE else "CAUTIOUS"

            # Check if this advisory involves irrigation or chemical spraying
            adv_text = (adv.action.action_text if adv.action and adv.action.action_text else "").lower()
            adv_cat = adv.action.action_category if adv.action else ""

            if is_rain_likely:
                # Rain imminent within 30-60 min
                if adv_cat == AdvisoryActionCategory.WATER_MANAGEMENT.value or "irrigation" in adv_text or "irrigate" in adv_text:
                    if adv.action:
                        adv.action.action_text = (
                            f"[Short-Horizon Alert: Defer Irrigation] {adv.action.action_text} "
                            f"— NOTE: Local nowcast indicates measurable rainfall is likely within {primary_h.horizon_minutes} minutes "
                            f"(P={rain_prob*100:.0f}%). Withhold irrigation until actual rainfall accumulation is verified."
                        )
                        adv.action.urgency = AdvisoryUrgency.IMMEDIATE.value
                    adv.rationale = (adv.rationale or "") + (
                        f" Observation-fused nowcast indicates rain within {primary_h.horizon_minutes}m. "
                        f"Temporarily withholding irrigation avoids waterlogging and conserves resources."
                    )
                    adv.nowcast_explanation = NowcastAdvisoryExplanation(
                        primary_reason="Rain imminent in localized nowcast; advise temporary hold on scheduled irrigation.",
                        localized_precipitation_signal=localized_sig,
                        baseline_signal=baseline_sig,
                        evidence_agreement=agreement,
                        confidence=conf.value,
                        action_strength=action_strength,
                        recommended_horizon_minutes=primary_h.horizon_minutes,
                        short_horizon_recommendation=f"Withhold irrigation for next {primary_h.horizon_minutes} minutes.",
                    )
                elif adv_cat == AdvisoryActionCategory.CROP_PROTECTION.value or "spray" in adv_text or "fungicide" in adv_text or "pesticide" in adv_text:
                    if adv.action:
                        adv.action.action_text = (
                            f"[Short-Horizon Alert: Postpone Spraying] {adv.action.action_text} "
                            f"— NOTE: Immediate rainfall likely within {primary_h.horizon_minutes} min (P={rain_prob*100:.0f}%). "
                            f"Postpone chemical applications to prevent wash-off."
                        )
                        adv.action.urgency = AdvisoryUrgency.IMMEDIATE.value
                    adv.rationale = (adv.rationale or "") + (
                        f" Immediate precipitation will wash agrochemicals off foliage into runoff."
                    )
                    adv.nowcast_explanation = NowcastAdvisoryExplanation(
                        primary_reason="Imminent precipitation detected; postpone foliar spraying to prevent wash-off.",
                        localized_precipitation_signal=localized_sig,
                        baseline_signal=baseline_sig,
                        evidence_agreement=agreement,
                        confidence=conf.value,
                        action_strength=action_strength,
                        recommended_horizon_minutes=primary_h.horizon_minutes,
                        short_horizon_recommendation="Postpone spraying operations for next 30-60 minutes.",
                    )
                else:
                    # General advisory with rain imminent
                    adv.nowcast_explanation = NowcastAdvisoryExplanation(
                        primary_reason=f"Localized rainfall likely within {primary_h.horizon_minutes} minutes.",
                        localized_precipitation_signal=localized_sig,
                        baseline_signal=baseline_sig,
                        evidence_agreement=agreement,
                        confidence=conf.value,
                        action_strength=action_strength,
                        recommended_horizon_minutes=primary_h.horizon_minutes,
                        short_horizon_recommendation="Take precautions for short-horizon precipitation.",
                    )
            else:
                # Dry / No rain likely in nowcast horizon
                if disagreement and baseline_ctx["baseline_precipitation_mm"] >= 2.5:
                    # NWP predicted rain, but nowcast shows clear skies
                    adv.nowcast_explanation = NowcastAdvisoryExplanation(
                        primary_reason="Satellite/radar observations indicate clear conditions over Panchayat despite synoptic rain forecast.",
                        localized_precipitation_signal=localized_sig,
                        baseline_signal=baseline_sig,
                        evidence_agreement=False,
                        confidence=conf.value,
                        action_strength="CAUTIOUS",
                        recommended_horizon_minutes=primary_h.horizon_minutes,
                        short_horizon_recommendation="Satellite shows dry conditions in next 60m; maintain vigilance as diurnal convection may develop.",
                    )
                else:
                    adv.nowcast_explanation = NowcastAdvisoryExplanation(
                        primary_reason="Short-horizon nowcast confirms dry conditions, consistent with planned routine operations.",
                        localized_precipitation_signal=localized_sig,
                        baseline_signal=baseline_sig,
                        evidence_agreement=True,
                        confidence=conf.value,
                        action_strength=action_strength,
                        recommended_horizon_minutes=primary_h.horizon_minutes,
                        short_horizon_recommendation="Clear window available for routine field operations.",
                    )

        return advisories

    def generate_panchayat_nowcast_advisories(
        self,
        panchayat_id: int,
        panchayat_name: str,
        block_id: int,
        block_name: Optional[str],
        crop_id: int,
        crop_name: str,
        forecast_date: datetime,
        nowcast: Optional[PanchayatPrecipitationNowcastResult],
        stage_name: Optional[str] = None,
        language: str = "en",
    ) -> List[AdvisoryResult]:
        """
        Generates dedicated, standalone short-horizon operational advisories
        (Spraying Window, Irrigation Scheduling, Field Operations) derived strictly
        from the conservative policy table and nowcast evidence.
        """
        state = self.determine_advisory_state(nowcast)
        if nowcast is None or state in (
            NowcastAdvisoryState.NOWCAST_NOT_AVAILABLE,
            NowcastAdvisoryState.NOWCAST_INSUFFICIENT_DATA,
        ):
            return []

        h30 = nowcast.horizons.get("30m")
        h60 = nowcast.horizons.get("60m")
        h120 = nowcast.horizons.get("120m")

        if not h30 or not h60:
            return []

        evidence_ctx = self.build_evidence_context(nowcast, horizon_key="60m")
        baseline_ctx = self.build_baseline_context(nowcast)

        results: List[AdvisoryResult] = []
        valid_from = forecast_date
        valid_until = forecast_date + timedelta(hours=2)

        # ---------------------------------------------------------------------
        # Policy 1: Chemical Spraying & Foliar Application Window
        # ---------------------------------------------------------------------
        spray_advisory = self._build_spraying_advisory(
            panchayat_id=panchayat_id,
            panchayat_name=panchayat_name,
            block_id=block_id,
            block_name=block_name,
            crop_id=crop_id,
            crop_name=crop_name,
            stage_name=stage_name,
            h30=h30,
            h60=h60,
            h120=h120,
            state=state,
            valid_from=valid_from,
            valid_until=valid_until,
            forecast_date=forecast_date,
            evidence_ctx=evidence_ctx,
            baseline_ctx=baseline_ctx,
            language=language,
        )
        if spray_advisory:
            results.append(spray_advisory)

        # ---------------------------------------------------------------------
        # Policy 2: Irrigation Scheduling & Water Management
        # ---------------------------------------------------------------------
        irrigation_advisory = self._build_irrigation_advisory(
            panchayat_id=panchayat_id,
            panchayat_name=panchayat_name,
            block_id=block_id,
            block_name=block_name,
            crop_id=crop_id,
            crop_name=crop_name,
            stage_name=stage_name,
            h60=h60,
            h120=h120,
            state=state,
            valid_from=valid_from,
            valid_until=valid_until,
            forecast_date=forecast_date,
            evidence_ctx=evidence_ctx,
            baseline_ctx=baseline_ctx,
            language=language,
        )
        if irrigation_advisory:
            results.append(irrigation_advisory)

        # ---------------------------------------------------------------------
        # Policy 3: Disagreement Handling (NWP rain vs localized dry)
        # ---------------------------------------------------------------------
        if h60.evidence_disagreement:
            disagreement_advisory = self._build_disagreement_advisory(
                panchayat_id=panchayat_id,
                panchayat_name=panchayat_name,
                block_id=block_id,
                block_name=block_name,
                crop_id=crop_id,
                crop_name=crop_name,
                stage_name=stage_name,
                h60=h60,
                state=state,
                valid_from=valid_from,
                valid_until=valid_until,
                forecast_date=forecast_date,
                evidence_ctx=evidence_ctx,
                baseline_ctx=baseline_ctx,
                language=language,
            )
            if disagreement_advisory:
                results.append(disagreement_advisory)

        return results

    def _build_spraying_advisory(
        self,
        panchayat_id: int,
        panchayat_name: str,
        block_id: int,
        block_name: Optional[str],
        crop_id: int,
        crop_name: str,
        stage_name: Optional[str],
        h30: PrecipitationNowcastHorizonResult,
        h60: PrecipitationNowcastHorizonResult,
        h120: Optional[PrecipitationNowcastHorizonResult],
        state: NowcastAdvisoryState,
        valid_from: datetime,
        valid_until: datetime,
        forecast_date: datetime,
        evidence_ctx: LocalizedPrecipitationAdvisoryEvidence,
        baseline_ctx: Dict[str, Any],
        language: str,
    ) -> Optional[AdvisoryResult]:
        """Builds a spraying window advisory based on short-horizon rain risk."""
        is_rain_30 = h30.is_rain_likely
        is_rain_60 = h60.is_rain_likely

        if is_rain_30 or is_rain_60:
            horizon_mins = 30 if is_rain_30 else 60
            prob = h30.rain_probability if is_rain_30 else h60.rain_probability

            if state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE:
                action_text = (
                    f"Postpone chemical spraying, bio-pesticides, and foliar fertilizer applications "
                    f"for the next {horizon_mins}–60 minutes. Rain is imminent over the Panchayat."
                )
                rationale = (
                    f"High-confidence localized nowcast indicates rain is likely (P={prob*100:.0f}%) "
                    f"within {horizon_mins} minutes. Rainfall within 1–2 hours of spraying washes active "
                    f"ingredients off foliage, resulting in financial loss and ground contamination."
                )
                timing = f"Next {horizon_mins}–60 minutes (Recheck nowcast before spraying)"
                urgency = AdvisoryUrgency.IMMEDIATE.value
                priority = AdvisoryPriority.HIGH.value
                action_strength = "STRONG"
            elif state == NowcastAdvisoryState.NOWCAST_MEDIUM_CONFIDENCE:
                action_text = (
                    f"Hold planned spraying operations temporarily. Observe cloud development over the next "
                    f"{horizon_mins} minutes before commencing application."
                )
                rationale = (
                    f"Moderate-confidence satellite/radar nowcast indicates elevated rain probability "
                    f"(P={prob*100:.0f}%) within {horizon_mins} minutes."
                )
                timing = f"Next 30–60 minutes"
                urgency = AdvisoryUrgency.UPCOMING.value
                priority = AdvisoryPriority.MEDIUM.value
                action_strength = "CAUTIOUS"
            else:
                # LOW confidence - do not generate aggressive intervention
                return None

            title = f"{crop_name} Spraying Window: Imminent Rain Precaution"
            message = f"Precipitation expected within {horizon_mins} min (P={prob*100:.0f}%). Delay chemical/foliar spraying."
        else:
            # Clear window
            if state in (NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE, NowcastAdvisoryState.NOWCAST_MEDIUM_CONFIDENCE):
                title = f"{crop_name} Spraying Window: Clear Short-Horizon Opportunity"
                message = f"Clear sky conditions detected for {panchayat_name}. Favorable operational window for next 2 hours."
                action_text = (
                    f"Favorable window for necessary foliar spraying, nutrient application, or weeding in {crop_name}. "
                    f"Ensure wind speeds are below 15 km/h before spraying."
                )
                rationale = (
                    f"Observation-fused nowcast indicates very low rain probability (P={h60.rain_probability*100:.0f}%) "
                    f"over the next 60–120 minutes with high/medium observational confidence."
                )
                timing = "Next 1–2 hours"
                urgency = AdvisoryUrgency.ROUTINE.value
                priority = AdvisoryPriority.LOW.value
                action_strength = "STRONG" if state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE else "CAUTIOUS"
            else:
                return None

        explanation = NowcastAdvisoryExplanation(
            primary_reason=title,
            localized_precipitation_signal=f"P(rain)={h60.rain_probability:.2f} at 60m (Conf: {h60.confidence.value})",
            baseline_signal=f"NWP expected={baseline_ctx['baseline_precipitation_mm']}mm",
            evidence_agreement=not h60.evidence_disagreement,
            confidence=h60.confidence.value,
            action_strength=action_strength,
            recommended_horizon_minutes=60,
            short_horizon_recommendation=action_text,
        )

        return AdvisoryResult(
            id=None,
            panchayat_id=panchayat_id,
            panchayat_name=panchayat_name,
            block_id=block_id,
            block_name=block_name,
            crop_id=crop_id,
            crop_name=crop_name,
            stage_name=stage_name,
            risk_log_id=None,
            crop_context_id=None,
            panchayat_weather_id=None,
            advisory_type=AdvisoryType.SHORT_HORIZON_OPERATIONS_ADVISORY.value,
            advisory_category=AdvisoryCategory.ACTION_ADVISORY.value,
            priority=priority,
            priority_rank=1,
            priority_reason=f"Derived from {state.value} precipitation nowcast.",
            title=title,
            message=message,
            action=AdvisoryAction(
                action_category=AdvisoryActionCategory.CROP_PROTECTION.value,
                action_text=action_text,
                timing=timing,
                urgency=urgency,
                conditions={"stage": stage_name, "nowcast_state": state.value},
            ),
            rationale=rationale,
            severity="LOW",
            confidence=h60.confidence.value,
            confidence_reason=f"Observation fusion: {', '.join(h60.evidence_sources)}",
            valid_from=valid_from.isoformat(),
            valid_until=valid_until.isoformat(),
            forecast_date=forecast_date.isoformat(),
            issue_time=datetime.utcnow().isoformat(),
            source_model="FUSED_NOWCAST_V1",
            weather_model_version=None,
            rule_version=self.policy_version,
            advisory_rule_version=self.policy_version,
            rule_source="ICAR_IMD_NOWCAST_INTEGRATION_GUIDELINES",
            language=language,
            status="ACTIVE",
            is_expert_review_required=False,
            is_cropland_eligible=True,
            localized_nowcast_context=evidence_ctx,
            baseline_precipitation_context=baseline_ctx,
            nowcast_advisory_state=state,
            nowcast_explanation=explanation,
            created_at=datetime.utcnow().isoformat(),
        )

    def _build_irrigation_advisory(
        self,
        panchayat_id: int,
        panchayat_name: str,
        block_id: int,
        block_name: Optional[str],
        crop_id: int,
        crop_name: str,
        stage_name: Optional[str],
        h60: PrecipitationNowcastHorizonResult,
        h120: Optional[PrecipitationNowcastHorizonResult],
        state: NowcastAdvisoryState,
        valid_from: datetime,
        valid_until: datetime,
        forecast_date: datetime,
        evidence_ctx: LocalizedPrecipitationAdvisoryEvidence,
        baseline_ctx: Dict[str, Any],
        language: str,
    ) -> Optional[AdvisoryResult]:
        """Builds an irrigation scheduling advisory if rain is likely or expected amount is substantial."""
        ref_h = h120 if (h120 and h120.is_rain_likely) else h60
        if not ref_h.is_rain_likely:
            return None

        expected_mm = ref_h.expected_amount_mm or 0.0
        if state not in (NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE, NowcastAdvisoryState.NOWCAST_MEDIUM_CONFIDENCE):
            return None

        title = f"{crop_name} Irrigation Scheduling: Defer Surface Watering"
        message = (
            f"Precipitation likely within {ref_h.horizon_minutes} min (expected ~{expected_mm:.1f} mm). "
            f"Hold surface irrigation."
        )
        action_text = (
            f"Withhold planned surface, canal, and sprinkler irrigation in {crop_name} for the next "
            f"{ref_h.horizon_minutes} minutes. Allow expected natural rainfall to satisfy soil moisture requirements."
        )
        rationale = (
            f"Localized nowcast shows P(rain)={ref_h.rain_probability*100:.0f}% with expected accumulation "
            f"of ~{expected_mm:.1f} mm. Irrigating ahead of imminent rain induces root hypoxia, lodging risk, "
            f"and wastes pumped irrigation power."
        )
        timing = f"Next {ref_h.horizon_minutes} minutes"
        urgency = AdvisoryUrgency.IMMEDIATE.value
        priority = AdvisoryPriority.MEDIUM.value

        explanation = NowcastAdvisoryExplanation(
            primary_reason=title,
            localized_precipitation_signal=f"P(rain)={ref_h.rain_probability:.2f}, expected={expected_mm:.1f}mm",
            baseline_signal=f"NWP expected={baseline_ctx['baseline_precipitation_mm']}mm",
            evidence_agreement=not ref_h.evidence_disagreement,
            confidence=ref_h.confidence.value,
            action_strength="STRONG" if state == NowcastAdvisoryState.NOWCAST_HIGH_CONFIDENCE else "CAUTIOUS",
            recommended_horizon_minutes=ref_h.horizon_minutes,
            short_horizon_recommendation=action_text,
        )

        return AdvisoryResult(
            id=None,
            panchayat_id=panchayat_id,
            panchayat_name=panchayat_name,
            block_id=block_id,
            block_name=block_name,
            crop_id=crop_id,
            crop_name=crop_name,
            stage_name=stage_name,
            risk_log_id=None,
            crop_context_id=None,
            panchayat_weather_id=None,
            advisory_type=AdvisoryType.SHORT_HORIZON_OPERATIONS_ADVISORY.value,
            advisory_category=AdvisoryCategory.ACTION_ADVISORY.value,
            priority=priority,
            priority_rank=2,
            priority_reason=f"Derived from {state.value} precipitation nowcast.",
            title=title,
            message=message,
            action=AdvisoryAction(
                action_category=AdvisoryActionCategory.WATER_MANAGEMENT.value,
                action_text=action_text,
                timing=timing,
                urgency=urgency,
                conditions={"stage": stage_name, "expected_rain_mm": expected_mm},
            ),
            rationale=rationale,
            severity="LOW",
            confidence=ref_h.confidence.value,
            confidence_reason=f"Multi-horizon observation fusion: {', '.join(ref_h.evidence_sources)}",
            valid_from=valid_from.isoformat(),
            valid_until=valid_until.isoformat(),
            forecast_date=forecast_date.isoformat(),
            issue_time=datetime.utcnow().isoformat(),
            source_model="FUSED_NOWCAST_V1",
            weather_model_version=None,
            rule_version=self.policy_version,
            advisory_rule_version=self.policy_version,
            rule_source="ICAR_IMD_NOWCAST_INTEGRATION_GUIDELINES",
            language=language,
            status="ACTIVE",
            is_expert_review_required=False,
            is_cropland_eligible=True,
            localized_nowcast_context=evidence_ctx,
            baseline_precipitation_context=baseline_ctx,
            nowcast_advisory_state=state,
            nowcast_explanation=explanation,
            created_at=datetime.utcnow().isoformat(),
        )

    def _build_disagreement_advisory(
        self,
        panchayat_id: int,
        panchayat_name: str,
        block_id: int,
        block_name: Optional[str],
        crop_id: int,
        crop_name: str,
        stage_name: Optional[str],
        h60: PrecipitationNowcastHorizonResult,
        state: NowcastAdvisoryState,
        valid_from: datetime,
        valid_until: datetime,
        forecast_date: datetime,
        evidence_ctx: LocalizedPrecipitationAdvisoryEvidence,
        baseline_ctx: Dict[str, Any],
        language: str,
    ) -> Optional[AdvisoryResult]:
        """Generates explicit cautious advisory when NWP and satellite/radar contradict."""
        title = f"{crop_name}: Forecast Signal Divergence Caution"
        message = (
            f"Block NWP predicts rain ({baseline_ctx['baseline_precipitation_mm']:.1f} mm) but local satellite/radar "
            f"detects clear skies over {panchayat_name}. Proceed with operations cautiously."
        )
        action_text = (
            f"Exercise caution in {crop_name} field operations. Keep drainage channels unobstructed as precautionary "
            f"measure, but avoid hasty changes to field management until local sky conditions confirm precipitation."
        )
        rationale = (
            f"Evidence divergence: {h60.disagreement_reason or 'Model and observational platforms disagree'}. "
            f"Nowcast confidence is conservatively capped at LOW to avoid false positive alarms."
        )
        timing = "Next 60–120 minutes"

        explanation = NowcastAdvisoryExplanation(
            primary_reason="Disagreement between macroscale NWP baseline and localized satellite observations.",
            localized_precipitation_signal=f"P(rain)={h60.rain_probability:.2f} (Conf: {h60.confidence.value})",
            baseline_signal=f"NWP expected={baseline_ctx['baseline_precipitation_mm']}mm (P={baseline_ctx['baseline_probability']:.2f})",
            evidence_agreement=False,
            confidence=h60.confidence.value,
            action_strength="CAUTIOUS",
            recommended_horizon_minutes=60,
            short_horizon_recommendation=action_text,
        )

        return AdvisoryResult(
            id=None,
            panchayat_id=panchayat_id,
            panchayat_name=panchayat_name,
            block_id=block_id,
            block_name=block_name,
            crop_id=crop_id,
            crop_name=crop_name,
            stage_name=stage_name,
            risk_log_id=None,
            crop_context_id=None,
            panchayat_weather_id=None,
            advisory_type=AdvisoryType.INFORMATIONAL.value,
            advisory_category=AdvisoryCategory.INFORMATIONAL.value,
            priority=AdvisoryPriority.LOW.value,
            priority_rank=3,
            priority_reason="Forecast evidence disagreement advisory.",
            title=title,
            message=message,
            action=AdvisoryAction(
                action_category=AdvisoryActionCategory.MONITOR.value,
                action_text=action_text,
                timing=timing,
                urgency=AdvisoryUrgency.ROUTINE.value,
                conditions={"stage": stage_name, "evidence_disagreement": True},
            ),
            rationale=rationale,
            severity="LOW",
            confidence="LOW",
            confidence_reason=h60.disagreement_reason or "Evidence divergence between NWP and observations",
            valid_from=valid_from.isoformat(),
            valid_until=valid_until.isoformat(),
            forecast_date=forecast_date.isoformat(),
            issue_time=datetime.utcnow().isoformat(),
            source_model="FUSED_NOWCAST_V1",
            weather_model_version=None,
            rule_version=self.policy_version,
            advisory_rule_version=self.policy_version,
            rule_source="ICAR_IMD_NOWCAST_INTEGRATION_GUIDELINES",
            language=language,
            status="ACTIVE",
            is_expert_review_required=False,
            is_cropland_eligible=True,
            localized_nowcast_context=evidence_ctx,
            baseline_precipitation_context=baseline_ctx,
            nowcast_advisory_state=NowcastAdvisoryState.NOWCAST_LOW_CONFIDENCE,
            nowcast_explanation=explanation,
            created_at=datetime.utcnow().isoformat(),
        )


# Global singleton instance
panchayat_advisory_nowcast_service = PanchayatAdvisoryNowcastService()
