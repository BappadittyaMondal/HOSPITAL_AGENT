#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18.3: CLINICAL EMERGENCY SCORERS & SPECIALIZED PROTOCOLS
====================================================================================================
Module: services/core-api/clinical_emergency_scorers.py
Purpose: Evidence-based clinical assessment calculators for acute pre-hospital and triage care:
         1. Glasgow Coma Scale (GCS) with airway reflex compromise warnings (GCS <= 8).
         2. FAST Acute Stroke Screening with IV thrombolysis time-window tracking.
         3. Field-Portable Pediatric Emergency Dosing (Broselow/weight-based).
         4. Anaphylaxis Emergency Protocol (IM Adrenaline 1:1000 dosing & posture).
         5. Burns Total Body Surface Area (Rule of Nines) & Parkland Fluid Resuscitation Formula.
====================================================================================================
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class GCSAssessment:
    eye_score: int
    verbal_score: int
    motor_score: int
    total_gcs: int
    severity: str  # MILD, MODERATE, SEVERE
    airway_compromised: bool
    clinical_recommendation: str


def calculate_glasgow_coma_scale(
    eye_opening: int,
    verbal_response: int,
    motor_response: int
) -> GCSAssessment:
    """
    Computes adult and pediatric Glasgow Coma Scale (3 to 15).
    Eye: 1-4, Verbal: 1-5, Motor: 1-6.
    Inviolable Rule: GCS <= 8 signifies severe traumatic brain injury / loss of airway protective reflexes.
    """
    if not (1 <= eye_opening <= 4):
        raise ValueError(f"Invalid Eye score {eye_opening}. Must be between 1 and 4.")
    if not (1 <= verbal_response <= 5):
        raise ValueError(f"Invalid Verbal score {verbal_response}. Must be between 1 and 5.")
    if not (1 <= motor_response <= 6):
        raise ValueError(f"Invalid Motor score {motor_response}. Must be between 1 and 6.")

    total = eye_opening + verbal_response + motor_response

    if total <= 8:
        severity = "SEVERE"
        airway = True
        rec = "CRITICAL: GCS <= 8. Loss of airway protective reflexes. Immediate endotracheal intubation / definitive airway required."
    elif total <= 12:
        severity = "MODERATE"
        airway = False
        rec = "MODERATE IMPAIRMENT: Close serial neurological monitoring every 30 minutes; urgent non-contrast CT brain."
    else:
        severity = "MILD"
        airway = False
        rec = "MILD: Monitor for deterioration, vomiting, or progressive lethargy."

    return GCSAssessment(
        eye_score=eye_opening,
        verbal_score=verbal_response,
        motor_score=motor_response,
        total_gcs=total,
        severity=severity,
        airway_compromised=airway,
        clinical_recommendation=rec
    )


@dataclass
class FASTStrokeResult:
    is_fast_positive: bool
    eligible_for_thrombolysis_window: bool
    findings: List[str]
    action_plan: str


def evaluate_fast_stroke(
    facial_droop: bool,
    arm_weakness: bool,
    speech_difficulty: bool,
    onset_hours_ago: float
) -> FASTStrokeResult:
    """
    Cincinnati Prehospital Stroke Scale / FAST assessment.
    Window for intravenous Alteplase/Tenecteplase thrombolysis is < 4.5 hours.
    """
    findings = []
    if facial_droop:
        findings.append("Facial asymmetry / droop present")
    if arm_weakness:
        findings.append("Unilateral arm drift / weakness present")
    if speech_difficulty:
        findings.append("Slurred or abnormal speech present")

    is_positive = len(findings) > 0
    in_window = is_positive and (onset_hours_ago <= 4.5)

    if in_window:
        action = "CODE STROKE: Within 4.5h IV thrombolytic window! Pre-notify receiving tertiary CT stroke center immediately."
    elif is_positive:
        action = "ACUTE STROKE: Beyond 4.5h IV window. Transfer immediately for potential mechanical thrombectomy evaluation (up to 24h)."
    else:
        action = "FAST Negative: Stroke less likely; evaluate for metabolic, infectious, or peripheral causes."

    return FASTStrokeResult(
        is_fast_positive=is_positive,
        eligible_for_thrombolysis_window=in_window,
        findings=findings,
        action_plan=action
    )


@dataclass
class PediatricEmergencyDoses:
    weight_kg: float
    age_years_estimated: float
    paracetamol_single_dose_mg: float
    ceftriaxone_meningitis_sepsis_mg: float
    salbutamol_nebulization_mg: float
    ors_rehydration_first_4h_ml: float
    rectal_diazepam_mg: float
    weight_provenance: str = "MEASURED"


def calculate_pediatric_emergency_doses(
    weight_kg: Optional[float] = None,
    age_years: Optional[float] = None
) -> PediatricEmergencyDoses:
    """
    Field-portable pediatric emergency medication dosing based on weight or age estimation.
    Uses WHO/APLS formulas: Weight = (Age + 4) * 2 for ages 1-10 if weight unknown.
    """
    is_estimated = (weight_kg is None or weight_kg <= 0)
    if is_estimated:
        if age_years is not None and age_years > 0:
            if age_years < 1:
                weight_kg = 5.0 + (age_years * 5.0)
            else:
                weight_kg = (age_years + 4.0) * 2.0
        else:
            raise ValueError(
                "Mandatory pediatric clinical baseline required: both weight_kg and age_years are "
                "missing or non-positive. Cannot fabricate safe dosing baseline."
            )

    if age_years is None:
        age_years = max(0.5, (weight_kg / 2.0) - 4.0)

    # Paracetamol: 15 mg/kg single dose (max 1000 mg)
    paracetamol_mg = min(1000.0, round(weight_kg * 15.0, 1))

    # Ceftriaxone: 50-100 mg/kg for severe sepsis/meningitis (max 2000 mg)
    ceftriaxone_mg = min(2000.0, round(weight_kg * 75.0, 1))

    # Salbutamol nebulization: 2.5mg if < 5 years (or < 20kg), 5.0mg if >= 5 years
    salbutamol_mg = 2.5 if weight_kg < 20.0 else 5.0

    # WHO ORS plan B for dehydration: 75 mL/kg in first 4 hours
    ors_ml = round(weight_kg * 75.0, 1)

    # Rectal Diazepam for seizing child: 0.5 mg/kg (max 10 mg)
    diazepam_mg = min(10.0, round(weight_kg * 0.5, 1))

    provenance_tag = "APLS_AGE_ESTIMATED" if is_estimated else "MEASURED"

    return PediatricEmergencyDoses(
        weight_kg=weight_kg,
        age_years_estimated=round(age_years, 1),
        paracetamol_single_dose_mg=paracetamol_mg,
        ceftriaxone_meningitis_sepsis_mg=ceftriaxone_mg,
        salbutamol_nebulization_mg=salbutamol_mg,
        ors_rehydration_first_4h_ml=ors_ml,
        rectal_diazepam_mg=diazepam_mg,
        weight_provenance=provenance_tag
    )


@dataclass
class AnaphylaxisProtocol:
    weight_kg: float
    is_child: bool
    im_adrenaline_dose_mg: float
    im_adrenaline_volume_1_to_1000_ml: float
    recommended_site: str
    iv_crystalloid_bolus_ml: float
    second_line_hydrocortisone_mg: float
    inviolable_instructions: List[str]


def calculate_anaphylaxis_protocol(
    weight_kg: float,
    is_child: bool = False
) -> AnaphylaxisProtocol:
    """
    Computes emergency Anaphylaxis resuscitation protocol:
    First-line treatment is IMMEDIATE INTRAMUSCULAR ADRENALINE (Epinephrine) 1:1000 (1 mg/mL).
    Dose: 0.01 mg/kg IM, maximum 0.5 mg in adults (0.3 mg in children 6-12y, 0.15 mg in <6y).
    """
    if weight_kg is None or weight_kg <= 0:
        raise ValueError(f"Patient weight must be strictly positive (>0 kg), got: {weight_kg}")

    if is_child or weight_kg < 30.0:
        if weight_kg < 15.0:
            dose_mg = 0.15
        elif weight_kg < 30.0:
            dose_mg = 0.3
        else:
            dose_mg = 0.3
    else:
        dose_mg = 0.5

    volume_ml = dose_mg  # Since 1:1000 concentration is 1 mg / 1 mL

    fluid_bolus = 20.0 * weight_kg if (is_child or weight_kg < 50) else 1000.0
    hydrocortisone = 100.0 if (is_child or weight_kg < 30) else 200.0

    instructions = [
        "IMMEDIATE INTRAMUSCULAR INJECTION: Inject into the mid-anterolateral thigh (NOT buttock or arm; highest peak blood level).",
        "Repeat Adrenaline IM every 5 minutes if respiratory distress or shock persists (up to 3 doses).",
        "KEEP PATIENT FLAT WITH LEGS ELEVATED: DO NOT ALLOW PATIENT TO STAND OR SIT SUDDENLY (fatal empty-ventricle arrest risk).",
        "High-flow oxygen 10-15 L/min via non-rebreather mask.",
        "Second-line medications (Antihistamines, Steroids) do NOT treat acute laryngeal edema or shock; NEVER delay Adrenaline."
    ]

    return AnaphylaxisProtocol(
        weight_kg=weight_kg,
        is_child=is_child,
        im_adrenaline_dose_mg=dose_mg,
        im_adrenaline_volume_1_to_1000_ml=volume_ml,
        recommended_site="Mid-anterolateral thigh (Vastus Lateralis)",
        iv_crystalloid_bolus_ml=fluid_bolus,
        second_line_hydrocortisone_mg=hydrocortisone,
        inviolable_instructions=instructions
    )


@dataclass
class BurnsResuscitationPlan:
    tbsa_percentage: float
    patient_weight_kg: float
    total_24h_fluid_parkland_ml: float
    first_8h_fluid_ml: float
    first_8h_rate_ml_per_hour: float
    next_16h_fluid_ml: float
    next_16h_rate_ml_per_hour: float
    fluid_type: str
    target_urine_output_ml_per_kg_per_h: float
    safety_instructions: List[str]
    hours_since_burn: float = 0.0
    remaining_first_window_hours: float = 8.0
    adjusted_first_window_rate_ml_per_hour: float = 0.0
    is_delayed_presentation: bool = False


def calculate_parkland_burns_fluid(
    tbsa_percentage: float,
    patient_weight_kg: float,
    is_pediatric: bool = False,
    hours_since_burn: float = 0.0,
    fluids_already_given_ml: float = 0.0
) -> BurnsResuscitationPlan:
    """
    Computes Parkland fluid resuscitation for major thermal burns (> 15% TBSA in adults, > 10% in children).
    Formula: Total 24h Ringer's Lactate = 4 mL * Weight (kg) * % TBSA.
    50% given over the first 8 hours FROM THE TIME OF BURN INJURY (adjusted for elapsed time).
    50% given over the following 16 hours.
    """
    if tbsa_percentage < 0 or tbsa_percentage > 100:
        raise ValueError("TBSA percentage must be between 0 and 100.")

    # Parkland Formula: 4 mL * kg * %TBSA
    total_24h = 4.0 * patient_weight_kg * tbsa_percentage
    first_8h = total_24h * 0.5
    next_16h = total_24h * 0.5

    rate_first_8h = round(first_8h / 8.0, 1)
    rate_next_16h = round(next_16h / 16.0, 1)

    target_uo = 1.0 if is_pediatric else 0.5

    instructions = [
        "Use RINGER'S LACTATE (Hartmann's Solution) as the primary crystalloid.",
        "The first 8-hour clock starts at the TIME OF BURN INJURY, NOT the time of hospital arrival.",
        "TITRATE IV FLUID TO URINE OUTPUT: Target 0.5 mL/kg/h in adults (1.0 mL/kg/h in children). Adjust rate up or down hourly.",
        "Cover burn wounds with clean dry sheets or sterile plastic wrap. DO NOT APPLY ICE OR COLD WATER (hypothermia risk).",
        "DO NOT APPLY UNVERIFIED TOXIC HERBS, TOOTHPASTE, OR COW DUNG TO BURN WOUNDS."
    ]

    is_delayed = False
    if hours_since_burn <= 0.0:
        remaining_hours = 8.0
        adjusted_rate = rate_first_8h
    elif hours_since_burn < 8.0:
        remaining_hours = round(8.0 - hours_since_burn, 2)
        remaining_fluid = max(first_8h - fluids_already_given_ml, 0.0)
        adjusted_rate = round(remaining_fluid / remaining_hours, 1)
        instructions.insert(0, f"ELAPSED BURN TIME ADJUSTMENT: Patient presents {hours_since_burn:.1f}h post-burn. Deliver remaining first-half volume ({remaining_fluid:.0f} mL) over remaining {remaining_hours:.1f}h at {adjusted_rate} mL/h.")
    else:
        remaining_hours = 0.0
        is_delayed = True
        adjusted_rate = round(next_16h / 16.0, 1)
        instructions.insert(0, "DELAYED PRESENTATION WARNING: Patient arrived >= 8 hours after burn injury. First 8-hour window has elapsed. Aggressively titrate fluid resuscitation to target urine output immediately.")

    return BurnsResuscitationPlan(
        tbsa_percentage=tbsa_percentage,
        patient_weight_kg=patient_weight_kg,
        total_24h_fluid_parkland_ml=round(total_24h, 1),
        first_8h_fluid_ml=round(first_8h, 1),
        first_8h_rate_ml_per_hour=rate_first_8h,
        next_16h_fluid_ml=round(next_16h, 1),
        next_16h_rate_ml_per_hour=rate_next_16h,
        fluid_type="Ringer's Lactate (Hartmann's Solution)",
        target_urine_output_ml_per_kg_per_h=target_uo,
        safety_instructions=instructions,
        hours_since_burn=round(hours_since_burn, 2),
        remaining_first_window_hours=remaining_hours,
        adjusted_first_window_rate_ml_per_hour=adjusted_rate,
        is_delayed_presentation=is_delayed
    )
