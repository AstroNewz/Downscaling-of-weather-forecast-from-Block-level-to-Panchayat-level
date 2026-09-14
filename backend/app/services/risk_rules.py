"""
Agricultural Risk Rule Registry & Threshold Configuration
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Defines versioned, crop-aware, stage-aware, and explainable threshold criteria
based on ICAR / IMD agrometeorological advisory standards.
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass
class RiskRuleDefinition:
    """Specification of an individual crop/stage threshold rule."""
    rule_id: str
    risk_type: str  # HEAT_STRESS, COLD_STRESS, WATER_STRESS, EXCESS_RAIN, DISEASE_FAVORABLE_CONDITIONS, WIND_STRESS
    risk_category: str  # THERMAL, HYDROLOGICAL, PATHOLOGICAL_ENVIRONMENT, WIND
    crop_name: Optional[str]  # e.g. "Rice", "Maize", "Wheat", or None for universal
    stage_name: Optional[str]  # e.g. "Flowering", "Vegetative", or None for crop-wide default
    trigger_variable: str  # max_temp_c, min_temp_c, mean_temp_c, rainfall_mm, wind_speed_kmh
    comparison_operator: str  # "GE" (>=), "LE" (<=), "BETWEEN", "CUSTOM"
    unit: str  # "°C", "mm", "km/h", "%"
    thresholds: Dict[str, float]  # e.g. {"MODERATE": 35.0, "HIGH": 37.0, "EXTREME": 40.0}
    rule_version: str = "agri_risk_v1.0.0"
    rule_source: str = "ICAR_IMD_AGROMET_CRITERIA"
    description: str = ""
    evidence_template: str = ""


class RiskRuleRegistry:
    """
    Central repository of versioned agronomic risk evaluation rules.
    """

    RULE_VERSION: str = "agri_risk_v1.0.0"
    RULE_SOURCE: str = "ICAR_IMD_AGROMET_CRITERIA"

    def __init__(self):
        self._rules: List[RiskRuleDefinition] = []
        self._init_rules()

    def _init_rules(self) -> None:
        """Initializes standard agrometeorological risk threshold rules."""

        # ====================================================================
        # 1. HEAT STRESS RULES (High Temperature / Thermal Stress)
        # ====================================================================
        # Rice (Flowering is critically sensitive: spikelet sterility above 35°C)
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_RICE_FLOWERING",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name="Rice",
                stage_name="Flowering",
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 33.0, "MODERATE": 35.0, "HIGH": 37.0, "EXTREME": 40.0},
                description="High temperature during rice flowering induces spikelet sterility and floret desiccation.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded critical flowering threshold of {threshold:.1f}°C.",
            )
        )
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_RICE_VEGETATIVE",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name="Rice",
                stage_name="Vegetative",
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 36.0, "MODERATE": 38.0, "HIGH": 41.0, "EXTREME": 44.0},
                description="Elevated temperature during rice vegetative stage impairs tillering and biomass production.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded vegetative threshold of {threshold:.1f}°C.",
            )
        )
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_RICE_DEFAULT",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name="Rice",
                stage_name=None,
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 35.0, "MODERATE": 37.0, "HIGH": 40.0, "EXTREME": 43.0},
                description="Elevated maximum temperature exceeds general rice thermal tolerance.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded crop threshold of {threshold:.1f}°C.",
            )
        )

        # Maize (Tasseling/Silking/Flowering sensitivity)
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_MAIZE_FLOWERING",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name="Maize",
                stage_name="Tasseling/Silking",
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 33.0, "MODERATE": 35.0, "HIGH": 38.0, "EXTREME": 41.0},
                description="Thermal stress during maize silking causes poor pollination and kernel abortion.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded maize tasseling threshold of {threshold:.1f}°C.",
            )
        )
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_MAIZE_DEFAULT",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name="Maize",
                stage_name=None,
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 35.0, "MODERATE": 37.0, "HIGH": 40.0, "EXTREME": 43.0},
                description="General maize thermal stress threshold exceeded.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded maize threshold of {threshold:.1f}°C.",
            )
        )

        # Wheat (Terminal Heat Stress during heading/flowering/grain filling)
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_WHEAT_HEADING",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name="Wheat",
                stage_name="Heading/Flowering",
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 26.0, "MODERATE": 28.0, "HIGH": 32.0, "EXTREME": 35.0},
                description="Terminal heat stress during wheat flowering/grain fill forces premature ripening and shrivelled grain.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded critical wheat threshold of {threshold:.1f}°C.",
            )
        )
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_WHEAT_DEFAULT",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name="Wheat",
                stage_name=None,
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 27.0, "MODERATE": 30.0, "HIGH": 33.0, "EXTREME": 36.0},
                description="General wheat thermal stress threshold exceeded.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded wheat threshold of {threshold:.1f}°C.",
            )
        )

        # Generic Thermal Fallback
        self._rules.append(
            RiskRuleDefinition(
                rule_id="HEAT_GENERIC_DEFAULT",
                risk_type="HEAT_STRESS",
                risk_category="THERMAL",
                crop_name=None,
                stage_name=None,
                trigger_variable="max_temp_c",
                comparison_operator="GE",
                unit="°C",
                thresholds={"LOW": 36.0, "MODERATE": 38.0, "HIGH": 42.0, "EXTREME": 45.0},
                description="General thermal stress threshold exceeded for unclassified crops.",
                evidence_template="Max temperature of {observed:.1f}°C exceeded generic threshold of {threshold:.1f}°C.",
            )
        )

        # ====================================================================
        # 2. COLD STRESS RULES (Low Temperature / Chilling / Frost)
        # ====================================================================
        # Wheat (Frost susceptibility during heading)
        self._rules.append(
            RiskRuleDefinition(
                rule_id="COLD_WHEAT_HEADING",
                risk_type="COLD_STRESS",
                risk_category="THERMAL",
                crop_name="Wheat",
                stage_name="Heading/Flowering",
                trigger_variable="min_temp_c",
                comparison_operator="LE",
                unit="°C",
                thresholds={"LOW": 5.0, "MODERATE": 4.0, "HIGH": 2.0, "EXTREME": 0.0},
                description="Near-freezing temperatures induce severe reproductive frost injury in wheat heads.",
                evidence_template="Min temperature of {observed:.1f}°C fell below critical frost threshold of {threshold:.1f}°C.",
            )
        )
        self._rules.append(
            RiskRuleDefinition(
                rule_id="COLD_WHEAT_DEFAULT",
                risk_type="COLD_STRESS",
                risk_category="THERMAL",
                crop_name="Wheat",
                stage_name=None,
                trigger_variable="min_temp_c",
                comparison_operator="LE",
                unit="°C",
                thresholds={"LOW": 4.0, "MODERATE": 2.0, "HIGH": 0.0, "EXTREME": -2.0},
                description="Low minimum temperature chilling threshold exceeded for wheat.",
                evidence_template="Min temperature of {observed:.1f}°C fell below wheat minimum threshold of {threshold:.1f}°C.",
            )
        )

        # Rice (Chilling stress)
        self._rules.append(
            RiskRuleDefinition(
                rule_id="COLD_RICE_DEFAULT",
                risk_type="COLD_STRESS",
                risk_category="THERMAL",
                crop_name="Rice",
                stage_name=None,
                trigger_variable="min_temp_c",
                comparison_operator="LE",
                unit="°C",
                thresholds={"LOW": 18.0, "MODERATE": 15.0, "HIGH": 12.0, "EXTREME": 8.0},
                description="Chilling temperatures below base threshold retard rice development and cause floret degeneration.",
                evidence_template="Min temperature of {observed:.1f}°C fell below rice chilling threshold of {threshold:.1f}°C.",
            )
        )

        # Generic Cold Fallback
        self._rules.append(
            RiskRuleDefinition(
                rule_id="COLD_GENERIC_DEFAULT",
                risk_type="COLD_STRESS",
                risk_category="THERMAL",
                crop_name=None,
                stage_name=None,
                trigger_variable="min_temp_c",
                comparison_operator="LE",
                unit="°C",
                thresholds={"LOW": 12.0, "MODERATE": 8.0, "HIGH": 4.0, "EXTREME": 1.0},
                description="Low minimum temperature chilling threshold exceeded for general crops.",
                evidence_template="Min temperature of {observed:.1f}°C fell below generic threshold of {threshold:.1f}°C.",
            )
        )

        # ====================================================================
        # 3. DISEASE-FAVORABLE ENVIRONMENTAL CONDITIONS
        # ====================================================================
        self._rules.append(
            RiskRuleDefinition(
                rule_id="DISEASE_FAVORABLE_GENERIC",
                risk_type="DISEASE_FAVORABLE_CONDITIONS",
                risk_category="PATHOLOGICAL_ENVIRONMENT",
                crop_name=None,
                stage_name=None,
                trigger_variable="mean_temp_c",
                comparison_operator="BETWEEN",
                unit="°C",
                thresholds={"MODERATE": 22.0, "HIGH": 26.0, "EXTREME": 30.0},
                description="Warm, humid micro-climatic conditions are conducive to foliar fungal and bacterial proliferation.",
                evidence_template="Environmental temperature ({observed:.1f}°C) within favorable pathogen window (22-32°C).",
            )
        )

        # ====================================================================
        # 4. EXCESS RAIN / WATERLOGGING RISK
        # ====================================================================
        self._rules.append(
            RiskRuleDefinition(
                rule_id="EXCESS_RAIN_GENERIC",
                risk_type="EXCESS_RAIN",
                risk_category="HYDROLOGICAL",
                crop_name=None,
                stage_name=None,
                trigger_variable="rainfall_mm",
                comparison_operator="GE",
                unit="mm",
                thresholds={"LOW": 35.0, "MODERATE": 50.0, "HIGH": 100.0, "EXTREME": 150.0},
                description="Heavy precipitation forecast exceeds field surface drainage capacity.",
                evidence_template="Forecast precipitation of {observed:.1f} mm exceeds waterlogging threshold of {threshold:.1f} mm.",
            )
        )

        # ====================================================================
        # 5. WATER / DRY-SPELL STRESS
        # ====================================================================
        self._rules.append(
            RiskRuleDefinition(
                rule_id="WATER_STRESS_GENERIC",
                risk_type="WATER_STRESS",
                risk_category="HYDROLOGICAL",
                crop_name=None,
                stage_name=None,
                trigger_variable="water_holding_capacity_pct",
                comparison_operator="LE",
                unit="%",
                thresholds={"LOW": 25.0, "MODERATE": 20.0, "HIGH": 15.0, "EXTREME": 10.0},
                description="Low available soil water holding capacity predisposes crop to moisture deficit under dry conditions.",
                evidence_template="Soil available water capacity of {observed:.1f}% below moisture retention threshold of {threshold:.1f}%.",
            )
        )

        # ====================================================================
        # 6. WIND STRESS (High Wind Lodging Risk)
        # ====================================================================
        self._rules.append(
            RiskRuleDefinition(
                rule_id="WIND_STRESS_GENERIC",
                risk_type="WIND_STRESS",
                risk_category="WIND",
                crop_name=None,
                stage_name=None,
                trigger_variable="wind_speed_kmh",
                comparison_operator="GE",
                unit="km/h",
                thresholds={"LOW": 25.0, "MODERATE": 35.0, "HIGH": 50.0, "EXTREME": 70.0},
                description="Sustained high wind conditions create mechanical lodging and stem breakage hazard for standing crops.",
                evidence_template="Forecast wind speed of {observed:.1f} km/h exceeds crop lodging threshold of {threshold:.1f} km/h.",
            )
        )

    def get_rule(
        self,
        risk_type: str,
        crop_name: Optional[str] = None,
        stage_name: Optional[str] = None,
    ) -> Optional[RiskRuleDefinition]:
        """
        Retrieves the most specific matching rule definition.
        Priority:
        1. Exact match (risk_type, crop_name, stage_name)
        2. Crop default match (risk_type, crop_name, None)
        3. Universal default match (risk_type, None, None)
        """
        # 1. Exact match
        if crop_name and stage_name:
            for r in self._rules:
                if (
                    r.risk_type == risk_type
                    and r.crop_name
                    and r.crop_name.lower() == crop_name.lower()
                    and r.stage_name
                    and r.stage_name.lower() == stage_name.lower()
                ):
                    return r

        # 2. Crop default match
        if crop_name:
            for r in self._rules:
                if (
                    r.risk_type == risk_type
                    and r.crop_name
                    and r.crop_name.lower() == crop_name.lower()
                    and r.stage_name is None
                ):
                    return r

        # 3. Universal default match
        for r in self._rules:
            if (
                r.risk_type == risk_type
                and r.crop_name is None
                and r.stage_name is None
            ):
                return r

        return None

    def get_supported_risk_types(self) -> List[str]:
        """Returns unique list of supported risk types in the registry."""
        types = set(r.risk_type for r in self._rules)
        return sorted(list(types))


# Global singleton instance
rule_registry = RiskRuleRegistry()
