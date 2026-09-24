"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Module: obstetrics_labor_engine.py
Operational Scope:
  - Antenatal Care (ANC) Serial Visit Tracker & High-Risk Pregnancy Stratification
  - Digital WHO Partograph with Alert & Action Line Real-Time Tracking
  - Quality Gate 1: Cervical Dilatation Crossing Action Line Triggers High-Priority Obstetric Alert
  - Category 1 Emergency C-Section Decision-to-Delivery Interval (DDI) Countdown (< 30 min)
  - Postpartum Hemorrhage (PPH) Rapid Escalation (Tone, Tissue, Trauma, Thrombin) (Gap 2)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any


class ObstetricSafetyError(Exception):
    """Base exception for obstetric safety alerts."""
    pass


class PartographActionLineBreachError(ObstetricSafetyError):
    """Raised when labor progression crosses the WHO Partograph Action Line."""
    pass


@dataclass
class PartographEntry:
    entry_id: str
    patient_id: str
    hours_in_active_labor: float
    cervical_dilatation_cm: float  # 4 to 10 cm
    fetal_heart_rate_bpm: float    # Normal: 110-160 bpm
    contractions_per_10min: int
    amniotic_fluid_state: str      # INTACT, CLEAR, MECONIUM_STAINED, BLOOD_STAINED
    recorded_at: str
    alert_line_dilatation_cm: float
    action_line_dilatation_cm: float
    action_line_breached: bool
    alert_line_breached: bool


@dataclass
class EmergencyCSectionDDI:
    case_id: str
    patient_id: str
    category: int                  # 1 = Immediate life threat (DDI < 30 min), 2 = Maternal/fetal compromise, 3 = No compromise
    decision_time: datetime
    target_delivery_time: datetime
    actual_delivery_time: Optional[datetime] = None
    target_ddi_minutes: float = 30.0
    actual_ddi_minutes: Optional[float] = None
    indication: str = ""
    is_breached: bool = False


class ObstetricsLaborEngine:
    """
    Labor ward and obstetrics clinical safety engine managing digital partographs,
    prolonged labor alerts, and emergency C-section DDI countdowns.
    """

    def __init__(self):
        # patient_id -> list of PartographEntry
        self.partographs: Dict[str, List[PartographEntry]] = {}
        self.csection_cases: Dict[str, EmergencyCSectionDDI] = {}

    def log_partograph_progress(
        self,
        patient_id: str,
        hours_in_active_labor: float,
        cervical_dilatation_cm: float,
        fetal_heart_rate_bpm: float,
        contractions_per_10min: int,
        amniotic_fluid_state: str = "CLEAR",
        recorded_at: Optional[datetime] = None
    ) -> PartographEntry:
        """
        Quality Gate 1:
        Partograph triggers high-priority alert when cervical dilatation crosses the action line.
        WHO Partograph Standard:
        - Active labor begins at 4 cm.
        - Alert line slope: 1 cm/hour dilatation starting at 4 cm at hour 0.
          dilatation_expected = 4.0 + (1.0 * hours_in_active_labor)
        - Action line is parallel to the alert line, shifted 4 hours to the right.
          action_line_threshold = 4.0 + 1.0 * (hours_in_active_labor - 4.0) if hours >= 4 else 4.0
        If measured dilatation is to the right of (below) the action line, it represents prolonged / obstructed labor.
        Specifically, for a given duration T, if cervical dilatation < (Alert - 4cm of expected progress), Action line is breached.
        Equivalently: At hour T, Alert Line expected = 4 + T. Action Line expected = 4 + (T - 4).
        If measured dilatation <= Action Line expected dilatation, labor is severely arrested/obstructed.
        """
        if recorded_at is None:
            recorded_at = datetime.now(timezone.utc)

        # Alert line: 1 cm/hour from 4 cm (e.g., at 0h = 4cm, 4h = 8cm, 6h = 10cm)
        alert_line_expected = min(10.0, 4.0 + hours_in_active_labor)
        # Action line: 4 hours lag behind alert line (starts after 4h)
        # At hour 4, action line is 4cm; at hour 6, action line is 6cm; at hour 8, action line is 8cm
        action_line_expected = min(10.0, max(4.0, 4.0 + (hours_in_active_labor - 4.0))) if hours_in_active_labor >= 4.0 else 0.0

        alert_breached = cervical_dilatation_cm < alert_line_expected
        action_breached = (hours_in_active_labor >= 4.0) and (cervical_dilatation_cm <= action_line_expected)

        entry = PartographEntry(
            entry_id=f"PARTO-{patient_id}-{int(hours_in_active_labor*10)}",
            patient_id=patient_id,
            hours_in_active_labor=hours_in_active_labor,
            cervical_dilatation_cm=cervical_dilatation_cm,
            fetal_heart_rate_bpm=fetal_heart_rate_bpm,
            contractions_per_10min=contractions_per_10min,
            amniotic_fluid_state=amniotic_fluid_state,
            recorded_at=recorded_at.isoformat(),
            alert_line_dilatation_cm=alert_line_expected,
            action_line_dilatation_cm=action_line_expected,
            action_line_breached=action_breached,
            alert_line_breached=alert_breached
        )
        self.partographs.setdefault(patient_id, []).append(entry)

        # Quality Gate 1: Action line breach triggers critical high-priority alert
        if action_breached:
            raise PartographActionLineBreachError(
                f"HIGH-PRIORITY OBSTETRIC ALERT: Cervical dilatation ({cervical_dilatation_cm} cm at {hours_in_active_labor}h) "
                f"has CROSSED THE WHO PARTOGRAPH ACTION LINE (Expected minimum {action_line_expected} cm). "
                f"Arrest of labor / Cephalopelvic Disproportion suspected. Immediate senior obstetrician review & intervention required."
            )

        return entry

    def trigger_category_1_emergency_csection(
        self,
        case_id: str,
        patient_id: str,
        indication: str,
        decision_time: Optional[datetime] = None
    ) -> EmergencyCSectionDDI:
        """
        Triggers statutory Category 1 Emergency C-Section countdown timer (DDI < 30 minutes).
        RCOG / NICE / National health guidelines standard.
        """
        if decision_time is None:
            decision_time = datetime.now(timezone.utc)

        target_time = decision_time + timedelta(minutes=30)
        csec = EmergencyCSectionDDI(
            case_id=case_id,
            patient_id=patient_id,
            category=1,
            decision_time=decision_time,
            target_delivery_time=target_time,
            target_ddi_minutes=30.0,
            indication=indication
        )
        self.csection_cases[case_id] = csec
        return csec

    def record_delivery_time(self, case_id: str, actual_delivery_time: datetime) -> EmergencyCSectionDDI:
        """Records infant delivery time and calculates actual Decision-to-Delivery Interval (DDI)."""
        csec = self.csection_cases.get(case_id)
        if not csec:
            raise ObstetricSafetyError(f"C-Section case {case_id} not found.")

        csec.actual_delivery_time = actual_delivery_time
        ddi_min = (actual_delivery_time - csec.decision_time).total_seconds() / 60.0
        csec.actual_ddi_minutes = round(ddi_min, 1)
        csec.is_breached = ddi_min > csec.target_ddi_minutes
        return csec

    # ----------------------------------------------------------------------------------------------
    # ADVANCED OBSTETRICS: PRE-ECLAMPSIA, HELLP, EFM/CTG & TERATOGENICITY FIREWALL (PHASE 40)
    # ----------------------------------------------------------------------------------------------

    def evaluate_preeclampsia_hellp(
        self,
        patient_id: str,
        gestational_age_weeks: float,
        systolic_bp: float,
        diastolic_bp: float,
        proteinuria_dipstick: str = "NIL",  # NIL, 1+, 2+, 3+, 4+
        protein_creatinine_ratio: Optional[float] = None,
        platelet_count: float = 250000.0,
        serum_creatinine: float = 0.7,
        ast_u_per_l: float = 25.0,
        alt_u_per_l: float = 25.0,
        ldh_u_per_l: float = 200.0,
        has_persistent_headache: bool = False,
        has_visual_scotomata: bool = False,
        has_epigastric_or_ruq_pain: bool = False,
        has_pulmonary_edema: bool = False,
        has_seizures: bool = False
    ) -> Dict[str, Any]:
        """
        Diagnoses & Stratifies Hypertensive Disorders of Pregnancy (ACOG 2020 / ISSHP 2021).
        Detects Eclampsia, Impending Eclampsia, and HELLP Syndrome.
        """
        is_hypertensive = (systolic_bp >= 140.0 or diastolic_bp >= 90.0)
        is_severe_bp = (systolic_bp >= 160.0 or diastolic_bp >= 110.0)
        is_proteinuria = (
            proteinuria_dipstick in ("1+", "2+", "3+", "4+") or
            (protein_creatinine_ratio is not None and protein_creatinine_ratio >= 0.3)
        )

        severe_features = []
        if is_severe_bp:
            severe_features.append(f"Severe blood pressure elevation ({systolic_bp}/{diastolic_bp} mmHg)")
        if platelet_count < 100000.0:
            severe_features.append(f"Thrombocytopenia (Platelets: {platelet_count}/uL < 100,000)")
        if serum_creatinine > 1.1:
            severe_features.append(f"Renal insufficiency (Creatinine: {serum_creatinine} mg/dL > 1.1)")
        if ast_u_per_l >= 70.0 or alt_u_per_l >= 70.0:
            severe_features.append(f"Impaired liver function (AST: {ast_u_per_l}, ALT: {alt_u_per_l} >= 2x normal)")
        if has_persistent_headache or has_visual_scotomata:
            severe_features.append("Cerebral / Visual disturbance (Persistent headache, scotomata)")
        if has_epigastric_or_ruq_pain:
            severe_features.append("Severe persistent epigastric or right upper quadrant pain (hepatic stretch)")
        if has_pulmonary_edema:
            severe_features.append("Pulmonary edema")

        # HELLP Syndrome (Hemolysis, Elevated Liver enzymes, Low Platelets)
        is_hellp = (
            platelet_count < 100000.0 and
            (ast_u_per_l >= 70.0 or alt_u_per_l >= 70.0) and
            ldh_u_per_l >= 600.0
        )

        if has_seizures:
            classification = "ECLAMPSIA"
            urgency = "STAT_CRITICAL_EMERGENCY"
        elif is_hellp:
            classification = "HELLP_SYNDROME"
            urgency = "STAT_CRITICAL_EMERGENCY"
        elif is_hypertensive and len(severe_features) > 0:
            classification = "PRE_ECLAMPSIA_WITH_SEVERE_FEATURES"
            urgency = "URGENT_INPATIENT_DELIVERY_EVALUATION"
        elif is_hypertensive and is_proteinuria:
            classification = "PRE_ECLAMPSIA_WITHOUT_SEVERE_FEATURES"
            urgency = "INPATIENT_SURVEILLANCE"
        elif is_hypertensive and gestational_age_weeks >= 20.0:
            classification = "GESTATIONAL_HYPERTENSION"
            urgency = "CLOSE_OUTPATIENT_ANC_MONITORING"
        else:
            classification = "NORMOTENSIVE_OR_CHRONIC_HYPERTENSION"
            urgency = "ROUTINE_ANC"

        # Protocol recommendations
        actions = []
        if classification in ("ECLAMPSIA", "HELLP_SYNDROME", "PRE_ECLAMPSIA_WITH_SEVERE_FEATURES"):
            actions.append("Initiate Magnesium Sulfate (MgSO4) Pritchard or Zuspan regimen for eclampsia neuro-prophylaxis")
            if is_severe_bp:
                actions.append("Administer IV Labetalol (20mg bolus) or Oral Nifedipine (10mg) for acute BP control (Target SBP 140-150, DBP 90-100)")
            actions.append("Insert Foley catheter with urometer for strict hourly urine output monitoring (>= 30 mL/hr mandatory)")
            if gestational_age_weeks >= 34.0 or classification in ("ECLAMPSIA", "HELLP_SYNDROME"):
                actions.append(f"Expedite definitive delivery: Gestational age {gestational_age_weeks}w (Maternal stabilization followed by delivery)")
            else:
                actions.append("Administer antenatal corticosteroids (Betamethasone 12mg IM q24h x 2 doses) for fetal lung maturity under close tertiary ICU surveillance")

        return {
            "patient_id": patient_id,
            "gestational_age_weeks": gestational_age_weeks,
            "classification": classification,
            "urgency": urgency,
            "is_severe": len(severe_features) > 0 or has_seizures or is_hellp,
            "severe_features": severe_features,
            "is_hellp_syndrome": is_hellp,
            "magnesium_sulfate_indicated": classification in ("ECLAMPSIA", "HELLP_SYNDROME", "PRE_ECLAMPSIA_WITH_SEVERE_FEATURES"),
            "urgent_interventions": actions
        }

    def evaluate_fetal_ctg_trace(
        self,
        patient_id: str,
        baseline_fhr_bpm: float,
        variability_bpm: float,
        deceleration_type: str = "NONE",  # NONE, EARLY, VARIABLE, LATE, PROLONGED, SINUSOIDAL
        deceleration_duration_seconds: float = 0.0,
        accelerations_present: bool = True
    ) -> Dict[str, Any]:
        """
        FIGO 2015 Electronic Fetal Monitoring (EFM/CTG) Waveform Classifier.
        Normal: Baseline 110-160, Variability 5-25, no late/variable decels.
        Suspicious: Lacks 1 normal feature without pathological signs.
        Pathological: Baseline < 100, variability < 5 for > 50 min, recurrent late/prolonged decels, or sinusoidal.
        """
        is_pathological = False
        is_suspicious = False
        critical_alert = None
        recommended_action = "Continue standard intrapartum CTG monitoring"

        if deceleration_type == "SINUSOIDAL":
            is_pathological = True
            critical_alert = "SINUSOIDAL FETAL TRACE DETECTED: Indicates severe fetal anemia, fetomaternal hemorrhage, or acute twin-twin transfusion"
            recommended_action = "IMMEDIATE EMERGENCY CESAREAN DELIVERY (Category 1 DDI < 30 min) + Prepare urgent neonatal O-neg blood for resuscitation"
        elif baseline_fhr_bpm < 80.0 and deceleration_duration_seconds >= 180.0:
            is_pathological = True
            critical_alert = f"SUSTAINED SEVERE FETAL BRADYCARDIA ({baseline_fhr_bpm} bpm for > 3 minutes): Imminent fetal demise"
            recommended_action = "ACTIVATE STAT CATEGORY 1 EMERGENCY C-SECTION (< 30 min) + Stop oxytocin + Maternal left lateral position + IV fluid bolus"
        elif deceleration_type == "LATE":
            is_pathological = True
            critical_alert = "RECURRENT LATE DECELERATIONS: Uteroplacental insufficiency and progressive fetal hypoxemia"
            recommended_action = "Intrauterine resuscitation: Stop uterotonics, administer oxygen, maternal left lateral tilt. If uncorrected within 15 min -> Urgent delivery"
        elif deceleration_type == "VARIABLE" and deceleration_duration_seconds >= 60.0:
            is_suspicious = True
            critical_alert = "ATYPICAL / SEVERE VARIABLE DECELERATIONS: Umbilical cord compression"
            recommended_action = "Maternal repositioning, assess for cord prolapse, consider amnioinfusion or expedited delivery"
        elif baseline_fhr_bpm < 110.0 or baseline_fhr_bpm > 160.0 or variability_bpm < 5.0:
            is_suspicious = True
            recommended_action = "Suspicious CTG: Re-evaluate maternal vitals (fever/dehydration/medications), maternal hydration, continue continuous tracing"

        category = "PATHOLOGICAL_CATEGORY_III" if is_pathological else ("SUSPICIOUS_CATEGORY_II" if is_suspicious else "NORMAL_CATEGORY_I")

        return {
            "patient_id": patient_id,
            "category": category,
            "baseline_fhr_bpm": baseline_fhr_bpm,
            "variability_bpm": variability_bpm,
            "deceleration_type": deceleration_type,
            "is_critical_life_threat": is_pathological,
            "critical_alert": critical_alert,
            "recommended_action": recommended_action
        }

    def screen_gestational_teratogenicity(
        self,
        patient_id: str,
        drug_name: str,
        is_pregnant: bool,
        trimester: int = 1
    ) -> Dict[str, Any]:
        """
        Inviolable Gestational Teratogenicity Barrier.
        Screening against absolute FDA/TGA Category X/D fetotoxic agents.
        """
        if not is_pregnant:
            return {"is_safe": True, "alert_level": "SAFE", "drug_name": drug_name}

        drug_upper = drug_name.upper().strip()
        teratogenic_catalog = {
            "VALPROATE": ("FETAL VALPROATE SYNDROME (Neural tube defects, microcephaly, facial dysmorphism, cognitive deficit)", "FDA_CATEGORY_X_TERATOGEN", "Switch to Levetiracetam or Lamotrigine with high-dose Folic Acid 5mg"),
            "SODIUM VALPROATE": ("FETAL VALPROATE SYNDROME", "FDA_CATEGORY_X_TERATOGEN", "Switch to Levetiracetam or Lamotrigine"),
            "METHOTREXATE": ("METHOTREXATE EMBRYOPATHY (Cranial dysostosis, cleft palate, limb reduction, fetal demise)", "FDA_CATEGORY_X_TERATOGEN", "Absolute contraindication; stop immediately"),
            "ISOTRETINOIN": ("RETINOIC ACID EMBRYOPATHY (Severe craniofacial, cardiac, thymic, and CNS malformations)", "FDA_CATEGORY_X_TERATOGEN", "Absolute contraindication; mandatory pregnancy test before use"),
            "WARFARIN": ("FETAL WARFARIN SYNDROME (Nasal hypoplasia, stippled epiphyses, CNS hemorrhage)", "FDA_CATEGORY_X_TERATOGEN", "Switch to Low-Molecular-Weight Heparin (Enoxaparin)"),
            "RAMIPRIL": ("FETAL RENAL DYSGENESIS & OLIGOHYDRAMNIOS (Neonatal anuria, pulmonary hypoplasia, skull hypoplasia)", "FDA_CATEGORY_D_FETOTOXIC", "Switch to Labetalol, Methyldopa, or Nifedipine"),
            "ENALAPRIL": ("FETAL RENAL DYSGENESIS", "FDA_CATEGORY_D_FETOTOXIC", "Switch to Labetalol or Nifedipine"),
            "LOSARTAN": ("FETAL ANGIOTENSIN RECEPTOR BLOCKER FETOPATHY", "FDA_CATEGORY_D_FETOTOXIC", "Switch to Labetalol or Nifedipine"),
            "TELMISARTAN": ("FETAL ARB FETOPATHY", "FDA_CATEGORY_D_FETOTOXIC", "Switch to Labetalol or Nifedipine"),
            "ATORVASTATIN": ("CHOLESTEROL SYNTHESIS DISRUPTION (Congenital anomalies, VACTERL association)", "FDA_CATEGORY_X_TERATOGEN", "Discontinue statin therapy during pregnancy"),
            "DOXYCYCLINE": ("PERMANENT DENTAL DISCOLORATION & ENAMEL HYPOPLASIA, BONE GROWTH SUPPRESSION", "FDA_CATEGORY_D_FETOTOXIC", "Switch to Amoxicillin or Azithromycin"),
            "CIPROFLOXACIN": ("ARTHROPATHY & CARTILAGE TOXICITY IN GROWING WEIGHT-BEARING JOINTS", "FDA_CATEGORY_C_CAUTION", "Switch to Ceftriaxone or Amoxicillin-Clavulanate")
        }

        for token, (danger, category, alt) in teratogenic_catalog.items():
            if token in drug_upper:
                return {
                    "is_safe": False,
                    "alert_level": category,
                    "drug_name": drug_name,
                    "danger_description": danger,
                    "trimester": trimester,
                    "mandatory_safe_alternative": alt,
                    "prescribing_blocked": True
                }

        return {
            "is_safe": True,
            "alert_level": "NO_ABSOLUTE_TERATOGENIC_CONTRAINDICATION",
            "drug_name": drug_name,
            "prescribing_blocked": False
        }


# Global Obstetric Engine Singleton
global_obstetrics_labor_engine = ObstetricsLaborEngine()

