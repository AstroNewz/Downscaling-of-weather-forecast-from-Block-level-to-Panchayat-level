"""
Real-Data Training Target Constructor
SIH Problem Statement 26074 — Agroweather-Downscaling

Constructs the Phase 6 downscaling target:
  temperature_residual_c = reference_temperature_c - coarse_temperature_c

Leakage Prevention Rules (Requirement 6, 7, 12):
  1. reference_source_id MUST differ from coarse_source_id
  2. If no genuine independent reference is available, target is NOT manufactured
  3. ERA5 cannot simultaneously be coarse input AND reference
  4. All three columns are preserved for auditability:
       reference_temperature_c
       coarse_temperature_c
       target_temperature_residual_c
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


VALID_SOURCE_TYPES = {"OBSERVATION", "REANALYSIS", "NWP_FORECAST", "REMOTE_SENSING", "DERIVED"}


@dataclass
class TargetRecord:
    """
    Auditable record containing both source temperatures and the derived target.
    All three values are stored together to allow verification.
    """
    reference_temperature_c: float          # Y_reference (observed or ERA5-Land)
    coarse_temperature_c: float             # X_coarse (ERA5 or NWP)
    target_temperature_residual_c: float    # Y_target = reference - coarse

    reference_source_id: str               # e.g., "AWS_BHU_001" or "ERA5_LAND"
    reference_source_type: str             # OBSERVATION or REANALYSIS
    coarse_source_id: str                  # e.g., "ERA5"
    coarse_source_type: str               # REANALYSIS or NWP_FORECAST

    is_station_validated: bool             # True only if reference is OBSERVATION
    leakage_safe: bool                     # True if sources differ


class TargetBuilder:
    """
    Constructs the temperature residual target from real data.

    Enforces all leakage-prevention rules from the project specification.
    """

    @staticmethod
    def build_target(
        reference_temp_c: Optional[float],
        coarse_temp_c: Optional[float],
        reference_source_id: str,
        reference_source_type: str,
        coarse_source_id: str,
        coarse_source_type: str,
    ) -> Optional[TargetRecord]:
        """
        Constructs the training target if and only if all conditions are met.

        Returns None (do NOT manufacture target) if:
          - reference_temp_c is None
          - coarse_temp_c is None
          - reference_source_id == coarse_source_id (leakage detected)
          - source types are invalid

        Args:
            reference_temp_c: Independent reference temperature in °C.
                              Should be OBSERVATION (IMD AWS) if available,
                              or REANALYSIS (ERA5-Land) as labelled fallback.
            coarse_temp_c: Coarse NWP/reanalysis temperature in °C.
                          Should be REANALYSIS (ERA5) or NWP_FORECAST.
            reference_source_id: Dataset identifier for the reference.
            reference_source_type: Source type for the reference.
            coarse_source_id: Dataset identifier for the coarse input.
            coarse_source_type: Source type for the coarse input.

        Returns:
            TargetRecord with all auditable fields, or None.
        """
        # Rule 1: Both values must be present — never manufacture target
        if reference_temp_c is None:
            return None
        if coarse_temp_c is None:
            return None

        # Rule 2: Sources must differ — prevent leakage
        if reference_source_id == coarse_source_id:
            raise ValueError(
                f"TARGET LEAKAGE VIOLATION: reference_source_id '{reference_source_id}' "
                f"is the same as coarse_source_id '{coarse_source_id}'. "
                f"This would give target = {reference_temp_c - coarse_temp_c:.3f}°C "
                f"based on internal model differences only — NOT true downscaling. "
                f"Use different datasets for reference and coarse inputs."
            )

        # Rule 3: Validate source types
        for st in [reference_source_type, coarse_source_type]:
            if st not in VALID_SOURCE_TYPES:
                raise ValueError(f"Invalid source_type '{st}'. Must be one of {VALID_SOURCE_TYPES}")

        # Rule 4: Compute target
        residual = round(reference_temp_c - coarse_temp_c, 4)

        # Determine if this is station-validated or reanalysis-to-reanalysis
        is_station = reference_source_type == "OBSERVATION"

        return TargetRecord(
            reference_temperature_c=round(reference_temp_c, 4),
            coarse_temperature_c=round(coarse_temp_c, 4),
            target_temperature_residual_c=residual,
            reference_source_id=reference_source_id,
            reference_source_type=reference_source_type,
            coarse_source_id=coarse_source_id,
            coarse_source_type=coarse_source_type,
            is_station_validated=is_station,
            leakage_safe=True,
        )

    @staticmethod
    def validate_target_integrity(target: TargetRecord) -> list[str]:
        """
        Post-construction integrity checks.
        Returns list of warning strings (empty = all good).
        """
        warnings = []

        # Physical plausibility: residual > 20°C or < -20°C is unusual
        if abs(target.target_temperature_residual_c) > 20.0:
            warnings.append(
                f"Temperature residual {target.target_temperature_residual_c:.2f}°C is very large. "
                f"Verify source data. reference={target.reference_temperature_c}°C, "
                f"coarse={target.coarse_temperature_c}°C."
            )

        # Both ERA5 types — valid but must be labelled
        if (target.reference_source_type == "REANALYSIS"
                and target.coarse_source_type == "REANALYSIS"):
            warnings.append(
                f"REANALYSIS-to-REANALYSIS target: "
                f"reference={target.reference_source_id}, coarse={target.coarse_source_id}. "
                f"This is valid but must be labelled as reanalysis comparison in reports. "
                f"Not station-observed validation."
            )

        return warnings
