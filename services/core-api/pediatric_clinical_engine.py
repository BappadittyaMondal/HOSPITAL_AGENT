"""
PROJECT "HOSPITAL" — PHASE 40: CLINICAL SPECIALTY EXPANSION
Module: services/core-api/pediatric_clinical_engine.py
Purpose: Precision Pediatric Medicine, Emergency Resuscitation, Fluid Dynamics & Neonatal Bilirubin Nomograms.
Clinical Governance:
  - WHO Integrated Management of Childhood Illness (IMNCI) Guidelines
  - American Academy of Pediatrics (AAP) Hyperbilirubinemia Management (2022 Revision)
  - Broselow Pediatric Emergency Resuscitation System (PALS Standard)
  - Holliday-Segar Maintenance Fluid Requirements & WHO Severe Dehydration Plan C
  - Pediatric Glasgow Coma Scale (pGCS) for Pre-Verbal Children
Deterministic Invariants:
  - Zero adult-floor dose leakage.
  - Sub-millisecond calculation speed.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class BroselowColorZone(str, Enum):
    GREY = "GREY"       # 3-5 kg (approx 4 kg) Length < 60 cm
    PINK = "PINK"       # 6-7 kg (approx 6.5 kg) Length 60-67 cm
    RED = "RED"         # 8-9 kg (approx 8.5 kg) Length 68-74 cm
    PURPLE = "PURPLE"   # 10-11 kg (approx 10.5 kg) Length 75-84 cm
    YELLOW = "YELLOW"   # 12-14 kg (approx 13 kg) Length 85-95 cm
    WHITE = "WHITE"     # 15-18 kg (approx 16.5 kg) Length 96-107 cm
    BLUE = "BLUE"       # 19-23 kg (approx 21 kg) Length 108-119 cm
    ORANGE = "ORANGE"   # 24-29 kg (approx 26.5 kg) Length 120-132 cm
    GREEN = "GREEN"     # 30-36 kg (approx 33 kg) Length 133-146 cm


class WHODehydrationGrade(str, Enum):
    NO_DEHYDRATION = "NO_DEHYDRATION"            # Plan A (Home therapy)
    SOME_DEHYDRATION = "SOME_DEHYDRATION"        # Plan B (Oral Rehydration Solution 75 mL/kg over 4h)
    SEVERE_DEHYDRATION = "SEVERE_DEHYDRATION"    # Plan C (Urgent IV Rehydration 100 mL/kg Ringer's Lactate)


@dataclass
class BroselowResuscitationProfile:
    color_zone: BroselowColorZone
    length_cm: float
    estimated_weight_kg: float
    et_tube_size_uncuffed_mm: float
    et_tube_size_cuffed_mm: float
    et_tube_depth_at_lip_cm: float
    laryngoscope_blade: str
    defibrillation_initial_joules: float    # 2 J/kg
    defibrillation_subsequent_joules: float # 4 J/kg
    epinephrine_cardiac_arrest_mg: float    # 0.01 mg/kg (0.1 mL/kg of 1:10,000)
    epinephrine_cardiac_arrest_ml_1_in_10k: float
    amiodarone_cardiac_arrest_mg: float     # 5 mg/kg
    fluid_bolus_volume_ml: float            # 20 mL/kg Ringer's or Normal Saline
    ceftriaxone_sepsis_dose_mg: float       # 75 mg/kg max 2g
    paracetamol_antipyretic_dose_mg: float  # 15 mg/kg


@dataclass
class HollidaySegarFluidResult:
    weight_kg: float
    daily_maintenance_ml: float
    hourly_rate_ml_per_hour: float
    calculation_breakdown: str
    electrolyte_sodium_meq_day: float  # 3 mEq/100 mL maintenance
    electrolyte_potassium_meq_day: float  # 2 mEq/100 mL maintenance


@dataclass
class BilirubinRiskEvaluation:
    postnatal_age_hours: float
    total_serum_bilirubin_mg_per_dl: float
    gestational_age_weeks: float
    has_neurotoxicity_risk_factors: bool  # Hemolytic disease, G6PD, asphyxia, lethargy, sepsis
    phototherapy_threshold_mg_per_dl: float
    exchange_transfusion_threshold_mg_per_dl: float
    phototherapy_indicated: bool
    exchange_transfusion_indicated: bool
    urgency_recommendation: str


class PediatricClinicalEngine:
    """
    Precision pediatric drug, fluid, and emergency resuscitation decision support engine.
    """

    # Broselow Length to Zone Lookup
    BROSELOW_ZONES = [
        (60.0, BroselowColorZone.GREY, 4.0, 3.5, 3.0, 10.0, "Miller 0 or 1"),
        (68.0, BroselowColorZone.PINK, 6.5, 3.5, 3.0, 11.0, "Miller 1"),
        (75.0, BroselowColorZone.RED, 8.5, 4.0, 3.5, 12.0, "Miller 1"),
        (85.0, BroselowColorZone.PURPLE, 10.5, 4.0, 3.5, 13.0, "Miller 1 or 2"),
        (96.0, BroselowColorZone.YELLOW, 13.0, 4.5, 4.0, 14.0, "Mac 2 or Miller 2"),
        (108.0, BroselowColorZone.WHITE, 16.5, 5.0, 4.5, 15.0, "Mac 2 or Miller 2"),
        (120.0, BroselowColorZone.BLUE, 21.0, 5.5, 5.0, 16.5, "Mac 2 or 3"),
        (133.0, BroselowColorZone.ORANGE, 26.5, 6.0, 5.5, 18.0, "Mac 3"),
        (147.0, BroselowColorZone.GREEN, 33.0, 6.5, 6.0, 19.5, "Mac 3")
    ]

    def calculate_body_surface_area(self, height_cm: float, weight_kg: float) -> Dict[str, float]:
        """
        Calculates BSA via Mosteller and DuBois formulas.
        Mosteller: sqrt( (height_cm * weight_kg) / 3600 )
        DuBois: 0.007184 * (height_cm ^ 0.725) * (weight_kg ^ 0.425)
        """
        if height_cm <= 0 or weight_kg <= 0:
            raise ValueError("Height and weight must be positive non-zero numbers.")

        mosteller_bsa = round(math.sqrt((height_cm * weight_kg) / 3600.0), 4)
        dubois_bsa = round(0.007184 * (height_cm ** 0.725) * (weight_kg ** 0.425), 4)

        return {
            "bsa_mosteller_m2": mosteller_bsa,
            "bsa_dubois_m2": dubois_bsa,
            "recommended_clinical_bsa_m2": mosteller_bsa
        }

    def calculate_holliday_segar_maintenance(self, weight_kg: float) -> HollidaySegarFluidResult:
        """
        Standard Holliday-Segar 4-2-1 Maintenance Fluid Calculation.
        - First 10 kg: 100 mL/kg/day (4 mL/kg/hr)
        - Second 10 kg (10-20 kg): + 50 mL/kg/day (+ 2 mL/kg/hr)
        - Each kg > 20 kg: + 20 mL/kg/day (+ 1 mL/kg/hr)
        """
        if weight_kg <= 0:
            raise ValueError("Weight must be positive.")

        if weight_kg <= 10.0:
            daily_ml = weight_kg * 100.0
            hourly_ml = weight_kg * 4.0
            breakdown = f"{weight_kg}kg x 100 mL/kg = {daily_ml} mL/day"
        elif weight_kg <= 20.0:
            daily_ml = 1000.0 + (weight_kg - 10.0) * 50.0
            hourly_ml = 40.0 + (weight_kg - 10.0) * 2.0
            breakdown = f"1000 mL + ({weight_kg - 10.0}kg x 50 mL/kg) = {daily_ml} mL/day"
        else:
            daily_ml = 1500.0 + (weight_kg - 20.0) * 20.0
            hourly_ml = 60.0 + (weight_kg - 20.0) * 1.0
            breakdown = f"1500 mL + ({weight_kg - 20.0}kg x 20 mL/kg) = {daily_ml} mL/day"

        # Cap daily maintenance at standard adult maximum (2400-2500 mL)
        daily_ml = min(2500.0, daily_ml)
        hourly_ml = round(daily_ml / 24.0, 1)

        # Electrolyte maintenance: Na ~ 3 mEq/100mL, K ~ 2 mEq/100mL
        na_meq = round(daily_ml * 0.03, 1)
        k_meq = round(daily_ml * 0.02, 1)

        return HollidaySegarFluidResult(
            weight_kg=weight_kg,
            daily_maintenance_ml=round(daily_ml, 1),
            hourly_rate_ml_per_hour=hourly_ml,
            calculation_breakdown=breakdown,
            electrolyte_sodium_meq_day=na_meq,
            electrolyte_potassium_meq_day=k_meq
        )

    def calculate_who_dehydration_plan_c(
        self,
        weight_kg: float,
        age_months: int
    ) -> Dict[str, Any]:
        """
        WHO Plan C: Severe Dehydration Fluid Resuscitation Protocol.
        Total: 100 mL/kg IV Ringer's Lactate (or Normal Saline).
        If Age < 12 months:
          - Step 1: 30 mL/kg in 1 hour.
          - Step 2: 70 mL/kg in 5 hours.
        If Age >= 12 months:
          - Step 1: 30 mL/kg in 30 minutes.
          - Step 2: 70 mL/kg in 2.5 hours.
        """
        total_fluid_ml = round(weight_kg * 100.0, 1)
        bolus_step1_ml = round(weight_kg * 30.0, 1)
        subsequent_step2_ml = round(weight_kg * 70.0, 1)

        if age_months < 12:
            step1_duration = "1 hour"
            step2_duration = "5 hours"
            total_duration = "6 hours"
            reassess_interval = "every 15-30 minutes until strong radial pulse palpable"
        else:
            step1_duration = "30 minutes"
            step2_duration = "2.5 hours"
            total_duration = "3 hours"
            reassess_interval = "every 15 minutes"

        return {
            "weight_kg": weight_kg,
            "age_months": age_months,
            "protocol": "WHO_PLAN_C_SEVERE_DEHYDRATION",
            "fluid_type": "IV Ringer's Lactate (preferred) or Normal Saline 0.9%",
            "total_fluid_ml": total_fluid_ml,
            "step_1_bolus": {
                "volume_ml": bolus_step1_ml,
                "duration": step1_duration,
                "rate_ml_hr": round(bolus_step1_ml / (1.0 if age_months < 12 else 0.5), 1)
            },
            "step_2_maintenance": {
                "volume_ml": subsequent_step2_ml,
                "duration": step2_duration,
                "rate_ml_hr": round(subsequent_step2_ml / (5.0 if age_months < 12 else 2.5), 1)
            },
            "total_rehydration_time": total_duration,
            "monitoring_instructions": f"Reassess patient {reassess_interval}. As soon as child can drink, initiate Oral Rehydration Solution (ORS 5 mL/kg/hr)."
        }

    def evaluate_broselow_resuscitation(self, length_cm: float) -> BroselowResuscitationProfile:
        """
        Maps child length (cm) to Broselow Color Zone and calculates all PALS equipment & drug doses.
        """
        if length_cm < 45.0:
            length_cm = 45.0

        selected = self.BROSELOW_ZONES[-1]
        for limit, color, wt, ett_uncuff, ett_cuff, depth, blade in self.BROSELOW_ZONES:
            if length_cm <= limit:
                selected = (limit, color, wt, ett_uncuff, ett_cuff, depth, blade)
                break

        limit, color, wt, ett_uncuff, ett_cuff, depth, blade = selected

        # Calculate exact weight-based emergency medications
        epi_mg = round(0.01 * wt, 3)
        epi_ml = round(0.1 * wt, 2)  # 1:10,000 solution is 0.1 mg/mL
        amio_mg = round(5.0 * wt, 1)
        defib_initial = round(2.0 * wt, 1)
        defib_subsequent = round(4.0 * wt, 1)
        fluid_bolus = round(20.0 * wt, 1)
        ceftriaxone = min(2000.0, round(75.0 * wt, 1))
        pcm = min(1000.0, round(15.0 * wt, 1))

        return BroselowResuscitationProfile(
            color_zone=color,
            length_cm=length_cm,
            estimated_weight_kg=wt,
            et_tube_size_uncuffed_mm=ett_uncuff,
            et_tube_size_cuffed_mm=ett_cuff,
            et_tube_depth_at_lip_cm=depth,
            laryngoscope_blade=blade,
            defibrillation_initial_joules=defib_initial,
            defibrillation_subsequent_joules=defib_subsequent,
            epinephrine_cardiac_arrest_mg=epi_mg,
            epinephrine_cardiac_arrest_ml_1_in_10k=epi_ml,
            amiodarone_cardiac_arrest_mg=amio_mg,
            fluid_bolus_volume_ml=fluid_bolus,
            ceftriaxone_sepsis_dose_mg=ceftriaxone,
            paracetamol_antipyretic_dose_mg=pcm
        )

    def evaluate_pediatric_gcs(
        self,
        eye_opening: int,     # 1 to 4
        verbal_response: int, # 1 to 5
        motor_response: int,  # 1 to 6
        is_preverbal: bool = False
    ) -> Dict[str, Any]:
        """
        Pediatric Glasgow Coma Scale (pGCS) for Infants and Children.
        Pre-verbal verbal scoring:
          5: Coos, babbles / Smiles, interacts
          4: Irritable, cries consolable
          3: Cries persistently to pain, inconsolable
          2: Grunts, moans to pain
          1: No response
        Motor scoring:
          6: Spontaneous / purposeful movement
          5: Withdraws from touch / localizes pain
          4: Withdraws from pain
          3: Decorticate abnormal flexion
          2: Decerebrate abnormal extension
          1: No response (flaccid)
        """
        if not (1 <= eye_opening <= 4):
            raise ValueError("Eye opening must be between 1 and 4.")
        if not (1 <= verbal_response <= 5):
            raise ValueError("Verbal response must be between 1 and 5.")
        if not (1 <= motor_response <= 6):
            raise ValueError("Motor response must be between 1 and 6.")

        total_score = eye_opening + verbal_response + motor_response

        if total_score <= 8:
            severity = "SEVERE_HEAD_INJURY_OR_COMA"
            airway_action = "MANDATORY DEFENSIVE ENDOTRACHEAL INTUBATION (pGCS <= 8)"
        elif total_score <= 12:
            severity = "MODERATE_BRAIN_INJURY"
            airway_action = "Close neurological surveillance in Pediatric ICU; urgent non-contrast Head CT"
        else:
            severity = "MILD_OR_NORMAL"
            airway_action = "Observe for vomiting, lethargy, or pupillary asymmetry"

        return {
            "eye_score": eye_opening,
            "verbal_score": verbal_response,
            "motor_score": motor_response,
            "total_pgcs": total_score,
            "is_preverbal_criteria_used": is_preverbal,
            "clinical_severity": severity,
            "airway_and_triage_directive": airway_action,
            "is_intubation_indicated": total_score <= 8
        }

    def evaluate_aap_hyperbilirubinemia(
        self,
        postnatal_age_hours: float,
        tsb_mg_per_dl: float,
        gestational_age_weeks: float,
        has_neurotoxicity_risk: bool = False
    ) -> BilirubinRiskEvaluation:
        """
        AAP 2022 Clinical Practice Guideline for Neonatal Hyperbilirubinemia.
        Calculates hour-specific phototherapy and exchange transfusion cutoffs.
        Considers lower threshold for infants < 38 weeks and those with neurotoxicity risks.
        """
        # Base phototherapy threshold curves (simplified linear interpolation based on AAP 2022 hour curves)
        # For term infants >= 38 weeks with no risk factors:
        if postnatal_age_hours < 24.0:
            base_photo = 6.0 + (postnatal_age_hours / 24.0) * 6.0   # reaches 12 at 24h
            base_exchange = 10.0 + (postnatal_age_hours / 24.0) * 8.0 # reaches 18 at 24h
        elif postnatal_age_hours < 48.0:
            base_photo = 12.0 + ((postnatal_age_hours - 24.0) / 24.0) * 3.0 # reaches 15 at 48h
            base_exchange = 18.0 + ((postnatal_age_hours - 24.0) / 24.0) * 3.0 # reaches 21 at 48h
        elif postnatal_age_hours < 72.0:
            base_photo = 15.0 + ((postnatal_age_hours - 48.0) / 24.0) * 2.5 # reaches 17.5 at 72h
            base_exchange = 21.0 + ((postnatal_age_hours - 48.0) / 24.0) * 2.0 # reaches 23 at 72h
        else:
            base_photo = min(20.0, 17.5 + ((postnatal_age_hours - 72.0) / 48.0) * 1.5)
            base_exchange = min(25.0, 23.0 + ((postnatal_age_hours - 72.0) / 48.0) * 1.5)

        # Risk factor adjustment
        photo_cutoff = base_photo
        exchange_cutoff = base_exchange

        if gestational_age_weeks < 38.0 or has_neurotoxicity_risk:
            photo_cutoff -= 2.5
            exchange_cutoff -= 3.0

        if gestational_age_weeks < 36.0:
            photo_cutoff -= 1.5
            exchange_cutoff -= 2.0

        photo_cutoff = round(max(4.0, photo_cutoff), 1)
        exchange_cutoff = round(max(8.0, exchange_cutoff), 1)

        is_photo = tsb_mg_per_dl >= photo_cutoff
        is_exchange = tsb_mg_per_dl >= exchange_cutoff

        if is_exchange:
            rec = "IMMEDIATE NICU ADMISSION FOR DOUBLE-VOLUME EXCHANGE TRANSFUSION + Intensive Multi-Bank Phototherapy"
        elif is_photo:
            rec = "INITIATE INTENSIVE LED PHOTOTHERAPY (Irradiance >= 30 uW/cm2/nm). Repeat TSB in 4-6 hours."
        elif tsb_mg_per_dl >= (photo_cutoff - 2.0):
            rec = "High-Intermediate zone: Re-measure TSB in 8-12 hours; optimize breastfeeding/hydration."
        else:
            rec = "Low-risk zone: Routine clinical follow-up within 48 hours."

        return BilirubinRiskEvaluation(
            postnatal_age_hours=postnatal_age_hours,
            total_serum_bilirubin_mg_per_dl=tsb_mg_per_dl,
            gestational_age_weeks=gestational_age_weeks,
            has_neurotoxicity_risk_factors=has_neurotoxicity_risk,
            phototherapy_threshold_mg_per_dl=photo_cutoff,
            exchange_transfusion_threshold_mg_per_dl=exchange_cutoff,
            phototherapy_indicated=is_photo,
            exchange_transfusion_indicated=is_exchange,
            urgency_recommendation=rec
        )


# Global Pediatric Clinical Singleton
global_pediatric_clinical_engine = PediatricClinicalEngine()
