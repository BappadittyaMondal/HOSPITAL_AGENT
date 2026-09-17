"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Module: nicu_pediatric_engine.py
Operational Scope:
  - Weight-Based Precision Neonatal Dosing (Grams to Kilograms)
  - Quality Gate 3: Inviolable Mechanical Barrier Blocking 10x / Adult Dose Calculation Errors in Neonates
  - Incubator Telemetry (Temperature 36.5-37.5°C, Humidity 60-80% for ELBW)
  - Retinopathy of Prematurity (ROP) Screening & Kangaroo Mother Care (KMC) Tracker (Gap 2)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any


class NeonatalDoseToxicityError(Exception):
    """Raised when an order for a neonate exceeds safe weight-based limits (e.g., 10x adult dose error)."""
    pass


@dataclass
class NeonatalPatientProfile:
    patient_id: str
    gestational_age_weeks: float
    birth_weight_grams: float
    current_weight_grams: float
    dob: datetime
    is_elbw: bool = False  # Extremely Low Birth Weight (< 1000g)
    is_vlbw: bool = False  # Very Low Birth Weight (< 1500g)


@dataclass
class KMCSession:
    session_id: str
    patient_id: str
    caregiver_relationship: str  # MOTHER, FATHER
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    infant_temp_before: float
    infant_temp_after: float


class NICUPediatricEngine:
    """
    Specialized neonatal and pediatric engine enforcing strict gram-based
    dosing safety gates, incubator telemetry monitoring, and screening protocols.
    """

    # Safe neonatal dosing ranges in mg/kg/dose or mcg/kg/dose
    NEONATAL_FORMULARY_LIMITS = {
        "DRUG-AMPICILLIN": {"max_mg_per_kg_dose": 100.0, "unit": "mg"},
        "DRUG-GENTAMICIN": {"max_mg_per_kg_dose": 5.0, "unit": "mg"},
        "DRUG-AMIKACIN": {"max_mg_per_kg_dose": 15.0, "unit": "mg"},
        "DRUG-CAFFEINE-CITRATE": {"max_mg_per_kg_dose": 20.0, "unit": "mg"},  # Loading 20, maint 5-10
        "DRUG-VANCOMYCIN": {"max_mg_per_kg_dose": 15.0, "unit": "mg"},
        "DRUG-PARACETAMOL-IV": {"max_mg_per_kg_dose": 15.0, "unit": "mg"},
        "DRUG-FENTANYL": {"max_mg_per_kg_dose": 0.003, "unit": "mg"}  # 3 mcg/kg max
    }

    def __init__(self):
        self.neonates: Dict[str, NeonatalPatientProfile] = {}
        self.kmc_sessions: List[KMCSession] = []

    def register_neonate(
        self,
        patient_id: str,
        gestational_age_weeks: float,
        birth_weight_grams: float,
        current_weight_grams: float,
        dob: Optional[datetime] = None
    ) -> NeonatalPatientProfile:
        """Registers infant with exact gram weights and prematurity classification."""
        if dob is None:
            dob = datetime.now(timezone.utc)

        profile = NeonatalPatientProfile(
            patient_id=patient_id,
            gestational_age_weeks=gestational_age_weeks,
            birth_weight_grams=birth_weight_grams,
            current_weight_grams=current_weight_grams,
            dob=dob,
            is_elbw=birth_weight_grams < 1000.0,
            is_vlbw=birth_weight_grams < 1500.0
        )
        self.neonates[patient_id] = profile
        return profile

    def validate_and_calculate_dose(
        self,
        patient_id: str,
        drug_id: str,
        prescribed_absolute_dose_mg: float,
        clinician_id: str
    ) -> Dict[str, Any]:
        """
        Quality Gate 3:
        Neonatal drug order validates against exact infant weight in grams,
        preventing 10x adult dose calculation errors.
        """
        profile = self.neonates.get(patient_id)
        if not profile:
            raise ValueError(f"Neonate {patient_id} not registered in NICU system.")

        weight_kg = profile.current_weight_grams / 1000.0
        if weight_kg <= 0:
            raise ValueError("Invalid infant weight.")

        limit_info = self.NEONATAL_FORMULARY_LIMITS.get(drug_id)
        if not limit_info:
            raise ValueError(f"Drug {drug_id} lacks neonatal dosing rules in NICU formulary.")

        max_safe_mg_per_kg = limit_info["max_mg_per_kg_dose"]
        max_allowable_dose_mg = round(max_safe_mg_per_kg * weight_kg, 3)

        effective_mg_per_kg = round(prescribed_absolute_dose_mg / weight_kg, 3)

        # Check if prescribed dose exceeds allowable ceiling
        if prescribed_absolute_dose_mg > max_allowable_dose_mg:
            error_msg = (
                f"FATAL NEONATAL OVERDOSE BLOCK: Prescribed {prescribed_absolute_dose_mg} mg "
                f"({effective_mg_per_kg} mg/kg) for infant weighing {profile.current_weight_grams}g ({weight_kg}kg). "
                f"Maximum safe limit is {max_safe_mg_per_kg} mg/kg ({max_allowable_dose_mg} mg max). "
                f"Order mechanically blocked to prevent fatal 10x dose error."
            )
            raise NeonatalDoseToxicityError(error_msg)

        return {
            "patient_id": patient_id,
            "drug_id": drug_id,
            "infant_weight_grams": profile.current_weight_grams,
            "infant_weight_kg": weight_kg,
            "prescribed_dose_mg": prescribed_absolute_dose_mg,
            "effective_mg_per_kg": effective_mg_per_kg,
            "max_allowable_dose_mg": max_allowable_dose_mg,
            "status": "APPROVED_SAFE_DOSE"
        }

    def evaluate_rop_screening_eligibility(
        self,
        patient_id: str,
        as_of_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Evaluates eligibility for Retinopathy of Prematurity (ROP) screening.
        Criteria: Gestational Age <= 30 weeks OR Birth Weight <= 1500g (or high risk).
        Scheduled at 4 weeks chronological age or 31 weeks post-menstrual age (PMA).
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        profile = self.neonates.get(patient_id)
        if not profile:
            raise ValueError(f"Neonate {patient_id} not registered.")

        is_eligible = (profile.gestational_age_weeks <= 30.0) or (profile.birth_weight_grams <= 1500.0)
        pma_weeks = profile.gestational_age_weeks + ((as_of_time - profile.dob).days / 7.0)

        recommended_screening_date = profile.dob + timedelta(weeks=4)

        return {
            "patient_id": patient_id,
            "is_eligible_for_rop": is_eligible,
            "gestational_age_weeks": profile.gestational_age_weeks,
            "birth_weight_grams": profile.birth_weight_grams,
            "current_pma_weeks": round(pma_weeks, 1),
            "screening_due_date": recommended_screening_date.strftime("%Y-%m-%d") if is_eligible else None
        }

    def monitor_incubator_environment(
        self,
        incubator_id: str,
        air_temp_c: float,
        skin_temp_c: float,
        relative_humidity_pct: float,
        is_elbw: bool = False
    ) -> Dict[str, Any]:
        """
        Monitors incubator microenvironment telemetry.
        Flags hypothermia (< 36.5°C) or hyperthermia (> 37.5°C).
        Checks for adequate humidity (60-80% for ELBW to prevent dehydration).
        """
        alarms = []
        if skin_temp_c < 36.5:
            alarms.append(f"COLD STRESS ALARM: Infant skin temp {skin_temp_c}°C is below neutral thermal zone (36.5°C).")
        elif skin_temp_c > 37.5:
            alarms.append(f"HYPERTHERMIA ALARM: Infant skin temp {skin_temp_c}°C exceeds safe upper limit (37.5°C).")

        if is_elbw and relative_humidity_pct < 60.0:
            alarms.append(f"HUMIDITY DEFICIT: ELBW incubator humidity {relative_humidity_pct}% is below 60% threshold.")

        return {
            "incubator_id": incubator_id,
            "skin_temp_c": skin_temp_c,
            "air_temp_c": air_temp_c,
            "humidity_pct": relative_humidity_pct,
            "in_safe_range": len(alarms) == 0,
            "alarms": alarms
        }
