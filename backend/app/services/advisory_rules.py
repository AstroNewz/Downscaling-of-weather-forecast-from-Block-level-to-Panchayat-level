"""
Agro-Meteorological Advisory Rule Registry & Template Configuration
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Defines versioned, crop-aware, growth-stage-aware, and risk-aware advisory rules
based on ICAR / IMD Agrometeorological Advisory Guidelines.

Strict Agronomic Guardrails:
- Disease-favorable conditions are NOT diagnosed as disease presence.
- No chemical pesticide names or dosages are prescribed.
- No arbitrary fertilizer or irrigation quantities are fabricated.
- Clear distinction between ACTION_ADVISORY and INFORMATIONAL.
- Prototype / test rules are clearly identified.
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AdvisoryRuleDefinition:
    """Specification of an individual crop/stage/risk advisory rule template."""
    rule_id: str
    risk_type: str  # HEAT_STRESS, COLD_STRESS, WATER_STRESS, EXCESS_RAIN, DISEASE_FAVORABLE_CONDITIONS, WIND_STRESS
    advisory_type: str  # HEAT_STRESS_ADVISORY, COLD_STRESS_ADVISORY, etc.
    crop_name: Optional[str]  # e.g. "Rice", "Maize", "Wheat", or None for crop-wide default
    stage_name: Optional[str]  # e.g. "Flowering", "Vegetative", or None for stage-wide default
    severity: str  # LOW, MODERATE, HIGH, EXTREME
    
    title_template: str
    message_template: str
    action_category: str  # MONITOR, WATER_MANAGEMENT, CROP_PROTECTION, FIELD_OPERATIONS, WEATHER_PREPAREDNESS, DISEASE_MONITORING
    recommended_action: str
    timing: str
    urgency: str  # IMMEDIATE, UPCOMING, ROUTINE
    rationale_template: str
    
    base_priority: str  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    advisory_category: str = "ACTION_ADVISORY"  # ACTION_ADVISORY, INFORMATIONAL
    advisory_rule_version: str = "agri_advisory_v1.0.0"
    rule_source: str = "ICAR_IMD_AGROMET_GUIDELINES"
    last_reviewed: str = "2026-06-01"
    is_expert_review_required: bool = False


class AdvisoryRuleRegistry:
    """
    Central repository of versioned agronomic advisory generation rules.
    """

    ADVISORY_RULE_VERSION: str = "agri_advisory_v1.0.0"
    RULE_SOURCE: str = "ICAR_IMD_AGROMET_GUIDELINES"

    def __init__(self):
        self._rules: List[AdvisoryRuleDefinition] = []
        self._init_rules()

    def _init_rules(self) -> None:
        """Initializes standard agrometeorological advisory templates."""

        # ====================================================================
        # 1. HEAT STRESS ADVISORIES (Thermal Stress Mitigation)
        # ====================================================================
        # Rice Flowering - HIGH / EXTREME
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_RICE_FLOWERING_HIGH",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Rice",
                stage_name="Flowering",
                severity="HIGH",
                title_template="High Heat Stress Advisory for Rice during Flowering",
                message_template="Forecast maximum temperature of {observed:.1f}°C indicates high heat stress risk for rice during the flowering stage, which may impair pollination and increase spikelet sterility.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Maintain 5-7 cm standing water layer in paddy fields to moderate canopy micro-temperature during peak sunshine hours. Consider light foliar spray of potassium chloride (1%) or ascorbic acid to alleviate canopy thermal stress, subject to local agromet guidance.",
                timing="Early morning or late afternoon before peak heat",
                urgency="IMMEDIATE",
                rationale_template="Elevated daytime temperatures (≥ {threshold:.1f}°C) during anthesis inhibit anther dehiscence and pollen viability.",
                base_priority="HIGH",
            )
        )
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_RICE_FLOWERING_EXTREME",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Rice",
                stage_name="Flowering",
                severity="EXTREME",
                title_template="Critical Heat Stress Warning for Rice during Flowering",
                message_template="Forecast extreme temperature of {observed:.1f}°C poses severe floret sterility and yield reduction risks for flowering paddy crops.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Ensure continuous shallow standing water in paddy fields. Avoid nitrogen top-dressing during the heatwave period. Inspect bunds to prevent drainage loss.",
                timing="Immediate morning action",
                urgency="IMMEDIATE",
                rationale_template="Extreme daytime temperature ({observed:.1f}°C) exceeds critical tolerance boundary ({threshold:.1f}°C) inducing irreversible spikelet sterility.",
                base_priority="CRITICAL",
            )
        )
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_RICE_FLOWERING_MODERATE",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Rice",
                stage_name="Flowering",
                severity="MODERATE",
                title_template="Moderate Heat Stress Alert for Rice during Flowering",
                message_template="Forecast temperature of {observed:.1f}°C indicates moderate thermal stress during rice flowering.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Apply light and frequent irrigation to keep field moisture adequate and prevent canopy overheating.",
                timing="Morning hours",
                urgency="UPCOMING",
                rationale_template="Maximum temperature ({observed:.1f}°C) approaching critical floret sensitivity boundary ({threshold:.1f}°C).",
                base_priority="MEDIUM",
            )
        )

        # Rice Vegetative
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_RICE_VEGETATIVE_HIGH",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Rice",
                stage_name="Vegetative",
                severity="HIGH",
                title_template="Heat Stress Advisory for Rice at Vegetative Stage",
                message_template="Forecast temperature of {observed:.1f}°C may reduce tillering and accelerate evaporative water loss in vegetative rice.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Maintain adequate moisture in the field to support active tillering. Avoid spraying operations during midday heat.",
                timing="Late afternoon",
                urgency="UPCOMING",
                rationale_template="Canopy temperature ({observed:.1f}°C) exceeds optimal vegetative growth window ({threshold:.1f}°C).",
                base_priority="MEDIUM",
            )
        )

        # Rice Default / Generic Stage
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_RICE_DEFAULT",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Rice",
                stage_name=None,
                severity="HIGH",
                title_template="Heat Stress Alert for Rice Crop",
                message_template="Forecast maximum temperature of {observed:.1f}°C exceeds standard thermal tolerance for rice.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Ensure adequate soil moisture through timely irrigation to mitigate heat stress.",
                timing="Early morning or evening",
                urgency="UPCOMING",
                rationale_template="Forecast temperature ({observed:.1f}°C) exceeds general crop threshold ({threshold:.1f}°C).",
                base_priority="MEDIUM",
            )
        )

        # Maize Silking/Tasseling
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_MAIZE_FLOWERING_HIGH",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Maize",
                stage_name="Tasseling/Silking",
                severity="HIGH",
                title_template="Heat Stress Advisory for Maize during Tasseling/Silking",
                message_template="Forecast maximum temperature of {observed:.1f}°C during maize tasseling/silking may cause tassel blasting and poor grain setting.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Apply irrigation at tasseling and silking stages to maintain root-zone moisture and protect silk receptivity.",
                timing="Morning or late evening",
                urgency="IMMEDIATE",
                rationale_template="High thermal regime ({observed:.1f}°C) during pollination impairs pollen viability and silk hydration.",
                base_priority="HIGH",
            )
        )
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_MAIZE_DEFAULT",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Maize",
                stage_name=None,
                severity="HIGH",
                title_template="Heat Stress Alert for Maize Crop",
                message_template="Forecast maximum temperature of {observed:.1f}°C indicates thermal stress risk for maize.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Provide light irrigation to prevent moisture stress during elevated temperatures.",
                timing="Evening hours",
                urgency="UPCOMING",
                rationale_template="Maximum temperature ({observed:.1f}°C) exceeds maize thermal threshold ({threshold:.1f}°C).",
                base_priority="MEDIUM",
            )
        )

        # Wheat Heading / Grain Fill - Terminal Heat
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_WHEAT_HEADING_HIGH",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Wheat",
                stage_name="Heading/Flowering",
                severity="HIGH",
                title_template="Terminal Heat Stress Advisory for Wheat during Heading/Flowering",
                message_template="Forecast maximum temperature of {observed:.1f}°C indicates elevated terminal heat stress for wheat during heading/flowering, which can cause premature senescence and shrivelled grains.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Provide light and frequent irrigation during calm weather (avoid windy days to prevent lodging). Consider foliar spray of 0.2% potassium nitrate (KNO3) or 2% urea at boot/anthesis stage if approved by local agricultural extension.",
                timing="Late evening when winds are calm",
                urgency="IMMEDIATE",
                rationale_template="Elevated temperature ({observed:.1f}°C) during grain filling restricts starch accumulation and shortens the grain-filling duration.",
                base_priority="HIGH",
            )
        )
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_WHEAT_DEFAULT",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name="Wheat",
                stage_name=None,
                severity="HIGH",
                title_template="Thermal Stress Alert for Wheat Crop",
                message_template="Forecast maximum temperature of {observed:.1f}°C exceeds optimal temperature range for wheat.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Maintain adequate soil moisture in the root zone with light evening irrigation.",
                timing="Evening hours",
                urgency="UPCOMING",
                rationale_template="Temperature ({observed:.1f}°C) exceeds general wheat threshold ({threshold:.1f}°C).",
                base_priority="MEDIUM",
            )
        )

        # Generic Thermal Fallback
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_HEAT_GENERIC_DEFAULT",
                risk_type="HEAT_STRESS",
                advisory_type="HEAT_STRESS_ADVISORY",
                crop_name=None,
                stage_name=None,
                severity="HIGH",
                title_template="Elevated Temperature Advisory for Standing Crops",
                message_template="Forecast maximum temperature of {observed:.1f}°C indicates elevated thermal stress for standing agricultural crops.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Ensure adequate crop hydration through timely irrigation. Avoid applying chemical fertilizers during high-temperature daytime windows.",
                timing="Early morning or late afternoon",
                urgency="UPCOMING",
                rationale_template="Maximum temperature ({observed:.1f}°C) exceeds standard agronomic baseline ({threshold:.1f}°C).",
                base_priority="MEDIUM",
            )
        )

        # ====================================================================
        # 2. COLD STRESS ADVISORIES (Chilling & Frost Protection)
        # ====================================================================
        # Wheat Heading - Frost Risk
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_COLD_WHEAT_HEADING_HIGH",
                risk_type="COLD_STRESS",
                advisory_type="COLD_STRESS_ADVISORY",
                crop_name="Wheat",
                stage_name="Heading/Flowering",
                severity="HIGH",
                title_template="Frost and Cold Injury Advisory for Wheat during Heading",
                message_template="Forecast minimum temperature of {observed:.1f}°C indicates severe chilling and potential frost injury for wheat at heading/flowering.",
                action_category="FIELD_OPERATIONS",
                recommended_action="Apply light irrigation in the evening to elevate field soil and air temperature. Create light smoke screens (by burning agricultural waste/straw around field boundaries) during pre-dawn hours to prevent radiation frost.",
                timing="Evening before cold night / pre-dawn",
                urgency="IMMEDIATE",
                rationale_template="Sub-zero or near-freezing temperatures (≤ {threshold:.1f}°C) cause ice crystal formation in reproductive organs, leading to floret sterility.",
                base_priority="CRITICAL",
            )
        )
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_COLD_WHEAT_DEFAULT",
                risk_type="COLD_STRESS",
                advisory_type="COLD_STRESS_ADVISORY",
                crop_name="Wheat",
                stage_name=None,
                severity="MODERATE",
                title_template="Low Temperature Alert for Wheat Crop",
                message_template="Forecast minimum temperature of {observed:.1f}°C indicates cold weather conditions for wheat.",
                action_category="FIELD_OPERATIONS",
                recommended_action="Monitor field conditions and ensure light irrigation if cold wave conditions persist.",
                timing="Evening",
                urgency="ROUTINE",
                rationale_template="Minimum temperature ({observed:.1f}°C) fell to chilling threshold ({threshold:.1f}°C).",
                base_priority="LOW",
            )
        )

        # Rice Chilling
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_COLD_RICE_DEFAULT",
                risk_type="COLD_STRESS",
                advisory_type="COLD_STRESS_ADVISORY",
                crop_name="Rice",
                stage_name=None,
                severity="HIGH",
                title_template="Chilling Injury Advisory for Rice Crop",
                message_template="Forecast minimum temperature of {observed:.1f}°C indicates chilling stress for rice, which can retard growth and prolong vegetative duration.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Maintain standing water layer in paddy fields overnight to retain heat and buffer root zones against low temperature drops.",
                timing="Late afternoon before sunset",
                urgency="IMMEDIATE",
                rationale_template="Minimum temperature ({observed:.1f}°C) below base growth threshold ({threshold:.1f}°C).",
                base_priority="HIGH",
            )
        )

        # Generic Cold Fallback
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_COLD_GENERIC_DEFAULT",
                risk_type="COLD_STRESS",
                advisory_type="COLD_STRESS_ADVISORY",
                crop_name=None,
                stage_name=None,
                severity="HIGH",
                title_template="Cold Wave Advisory for Standing Crops",
                message_template="Forecast minimum temperature of {observed:.1f}°C indicates cold wave and chilling stress for standing crops.",
                action_category="FIELD_OPERATIONS",
                recommended_action="Provide light evening irrigation to moderate micro-climate. Cover sensitive nursery beds with polythene or straw mulch.",
                timing="Evening hours",
                urgency="IMMEDIATE",
                rationale_template="Minimum temperature ({observed:.1f}°C) fell below baseline thermal threshold ({threshold:.1f}°C).",
                base_priority="MEDIUM",
            )
        )

        # ====================================================================
        # 3. DISEASE-FAVORABLE ENVIRONMENTAL CONDITIONS
        # ====================================================================
        # Generic & Crop Disease Favorable
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_DISEASE_FAVORABLE_GENERIC",
                risk_type="DISEASE_FAVORABLE_CONDITIONS",
                advisory_type="DISEASE_FAVORABLE_CONDITIONS_ADVISORY",
                crop_name=None,
                stage_name=None,
                severity="MODERATE",
                title_template="Environmental Alert: Favorable Conditions for Foliar Pathogens",
                message_template="Forecast micro-climatic conditions (mean temperature around {observed:.1f}°C with high relative humidity) are favorable for foliar fungal and bacterial pathogen proliferation. Note: This indicates environmental suitability, NOT a confirmed crop disease diagnosis.",
                action_category="DISEASE_MONITORING",
                recommended_action="Inspect standing crops regularly for early symptom development (e.g. leaf spots, blights, or rusts). Follow recommended cultural sanitation practices and consult local agricultural extension officers for approved crop-protection measures if symptoms appear.",
                timing="During regular morning crop scouting",
                urgency="UPCOMING",
                rationale_template="Environmental temperature ({observed:.1f}°C) within favorable pathogen window (22-32°C).",
                base_priority="MEDIUM",
            )
        )

        # ====================================================================
        # 4. EXCESS RAINFALL / WATERLOGGING ADVISORY
        # ====================================================================
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_EXCESS_RAIN_GENERIC",
                risk_type="EXCESS_RAIN",
                advisory_type="EXCESS_RAIN_ADVISORY",
                crop_name=None,
                stage_name=None,
                severity="HIGH",
                title_template="Heavy Rainfall and Drainage Advisory for Agricultural Fields",
                message_template="Forecast heavy precipitation indicates risk of surface runoff and waterlogging in low-lying agricultural fields.",
                action_category="FIELD_OPERATIONS",
                recommended_action="Clear drainage channels, culverts, and field outlets immediately to prevent prolonged water stagnation. Postpone fertilizer top-dressing and field spraying operations until rain subsides.",
                timing="Before anticipated rainfall event",
                urgency="IMMEDIATE",
                rationale_template="Heavy rainfall forecast exceeds field surface drainage capacity.",
                base_priority="HIGH",
            )
        )

        # ====================================================================
        # 5. WATER STRESS / DRY SPELL ADVISORY
        # ====================================================================
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_WATER_STRESS_GENERIC",
                risk_type="WATER_STRESS",
                advisory_type="WATER_STRESS_ADVISORY",
                crop_name=None,
                stage_name=None,
                severity="MODERATE",
                title_template="Soil Moisture Deficit and Water Conservation Advisory",
                message_template="Soil characteristics and prevailing weather indicate rising moisture deficit in the crop root zone.",
                action_category="WATER_MANAGEMENT",
                recommended_action="Apply protective irrigation at critical growth stages if water resources permit. Employ organic mulching in crop rows to conserve soil moisture and reduce evaporative loss.",
                timing="Early morning or evening",
                urgency="UPCOMING",
                rationale_template="Available soil water retention capacity is low under prevailing dry weather regime.",
                base_priority="MEDIUM",
            )
        )

        # ====================================================================
        # 6. WIND STRESS (LODGING RISK)
        # ====================================================================
        self._rules.append(
            AdvisoryRuleDefinition(
                rule_id="ADV_WIND_STRESS_GENERIC",
                risk_type="WIND_STRESS",
                advisory_type="WIND_STRESS_ADVISORY",
                crop_name=None,
                stage_name=None,
                severity="HIGH",
                title_template="High Wind and Crop Lodging Preparedness Advisory",
                message_template="Forecast high wind speeds create mechanical stress and lodging hazard for tall, mature, and reproductive standing crops.",
                action_category="WEATHER_PREPAREDNESS",
                recommended_action="Withhold field irrigation immediately prior to high wind events, as saturated soil softens root anchoring and drastically increases lodging. Provide mechanical propping / staking for tall crops and fruit trees where feasible.",
                timing="Immediately before forecast wind event",
                urgency="IMMEDIATE",
                rationale_template="Sustained high wind speeds increase drag force and bending moment on tall crop canopies.",
                base_priority="HIGH",
            )
        )

    def get_rule(
        self,
        risk_type: str,
        crop_name: Optional[str] = None,
        stage_name: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> Optional[AdvisoryRuleDefinition]:
        """
        Retrieves the most specific matching advisory rule definition.
        Priority Hierarchy:
        1. Exact match (risk_type, crop_name, stage_name, severity)
        2. Crop & stage match (risk_type, crop_name, stage_name, any severity)
        3. Crop default match (risk_type, crop_name, None, severity)
        4. Crop default match (risk_type, crop_name, None, any severity)
        5. Universal default match (risk_type, None, None, severity)
        6. Universal default match (risk_type, None, None, any severity)
        """
        norm_crop = crop_name.lower() if crop_name else None
        norm_stage = stage_name.lower() if stage_name else None
        norm_sev = severity.upper() if severity else None

        # 1. Exact match
        if norm_crop and norm_stage and norm_sev:
            for r in self._rules:
                if (
                    r.risk_type == risk_type
                    and r.crop_name and r.crop_name.lower() == norm_crop
                    and r.stage_name and r.stage_name.lower() == norm_stage
                    and r.severity.upper() == norm_sev
                ):
                    return r

        # 2. Crop & Stage match (any severity)
        if norm_crop and norm_stage:
            for r in self._rules:
                if (
                    r.risk_type == risk_type
                    and r.crop_name and r.crop_name.lower() == norm_crop
                    and r.stage_name and r.stage_name.lower() == norm_stage
                ):
                    return r

        # 3. Crop default match with severity
        if norm_crop and norm_sev:
            for r in self._rules:
                if (
                    r.risk_type == risk_type
                    and r.crop_name and r.crop_name.lower() == norm_crop
                    and r.stage_name is None
                    and r.severity.upper() == norm_sev
                ):
                    return r

        # 4. Crop default match (any severity)
        if norm_crop:
            for r in self._rules:
                if (
                    r.risk_type == risk_type
                    and r.crop_name and r.crop_name.lower() == norm_crop
                    and r.stage_name is None
                ):
                    return r

        # 5. Universal default match with severity
        if norm_sev:
            for r in self._rules:
                if (
                    r.risk_type == risk_type
                    and r.crop_name is None
                    and r.stage_name is None
                    and r.severity.upper() == norm_sev
                ):
                    return r

        # 6. Universal default match (any severity)
        for r in self._rules:
            if (
                r.risk_type == risk_type
                and r.crop_name is None
                and r.stage_name is None
            ):
                return r

        return None

    def get_supported_advisory_types(self) -> List[str]:
        """Returns unique list of supported advisory types in the registry."""
        types = set(r.advisory_type for r in self._rules)
        return sorted(list(types))


# Global singleton instance
advisory_rule_registry = AdvisoryRuleRegistry()
