"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Module: nursing_cockpit_engine.py
Operational Scope:
  - Bedside 5-Rights eMAR Administration Enforcing Scanned Patient Wristband Match
  - Cumulative Fluid Intake/Output Balance & Oliguria (<0.5 mL/kg/h) Surveillance
  - Clinical Risk Calculators: Braden Scale (Pressure Ulcer) & Morse Fall Scale
  - Structured ISBAR Nursing Handover with Dual Outgoing/Incoming Signatures
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class WristbandBarcodeVerificationError(Exception):
    """Raised when medication administration is attempted without a valid wristband scan."""
    pass


class NursingHandoverError(Exception):
    """Raised when nursing handover requirements are incomplete."""
    pass


@dataclass
class BradenScoreAssessment:
    assessment_id: str
    patient_id: str
    nurse_id: str
    sensory_perception: int  # 1-4
    moisture: int            # 1-4
    activity: int            # 1-4
    mobility: int            # 1-4
    nutrition: int           # 1-4
    friction_shear: int      # 1-3
    total_score: int
    risk_level: str          # VERY_HIGH (<=9), HIGH (10-12), MODERATE (13-14), MILD (15-18), NO_RISK (19-23)
    air_mattress_indicated: bool
    assessed_at: str


@dataclass
class MorseFallAssessment:
    assessment_id: str
    patient_id: str
    nurse_id: str
    history_of_falls: int     # 0 or 25
    secondary_diagnosis: int  # 0 or 15
    ambulatory_aid: int       # 0, 15, or 30
    iv_or_saline_lock: int    # 0 or 20
    gait_transferring: int    # 0, 10, or 20
    mental_status: int        # 0 or 15
    total_score: int
    risk_level: str           # HIGH (>=45), MEDIUM (25-44), LOW (0-24)
    fall_precaution_flag: bool
    assessed_at: str


@dataclass
class ISBARHandoverRecord:
    handover_id: str
    ward_id: str
    outgoing_nurse_id: str
    incoming_nurse_id: str
    patients_reviewed: List[Dict[str, Any]]
    outgoing_signed_at: str
    incoming_signed_at: str
    shift_name: str  # MORNING, EVENING, NIGHT
    status: str = "COMPLETED"


class NursingCockpitEngine:
    """
    Nursing station operational engine managing bedside barcode verification,
    intake/output fluid balance, clinical risk calculators, and ISBAR handovers.
    """

    def __init__(self):
        self.administration_logs: List[Dict[str, Any]] = []
        self.fluid_records: Dict[str, List[Dict[str, Any]]] = {}  # patient_id -> list of entries
        self.braden_assessments: List[BradenScoreAssessment] = []
        self.fall_assessments: List[MorseFallAssessment] = []
        self.handover_records: List[ISBARHandoverRecord] = []

    def administer_medication_at_bedside(
        self,
        patient_id: str,
        scanned_wristband_barcode: Optional[str],
        medication_order_id: str,
        drug_name: str,
        dose: str,
        nurse_id: str,
        as_of_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Quality Gate 2:
        Inpatient medication administration without scanning the patient wristband barcode is blocked
        or logged as a safety exception. Mismatch strictly blocks administration.
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        now_str = as_of_time.isoformat()

        # Hard stop if wristband barcode is missing
        if not scanned_wristband_barcode or not scanned_wristband_barcode.strip():
            exception_record = {
                "patient_id": patient_id,
                "order_id": medication_order_id,
                "drug_name": drug_name,
                "nurse_id": nurse_id,
                "timestamp": now_str,
                "status": "BLOCKED_NO_WRISTBAND_SCAN",
                "error": "CRITICAL PATIENT SAFETY VIOLATION: Wristband barcode scan is mandatory prior to medication administration."
            }
            self.administration_logs.append(exception_record)
            raise WristbandBarcodeVerificationError(exception_record["error"])

        # Check barcode matches patient ID
        if scanned_wristband_barcode.strip() != patient_id.strip():
            exception_record = {
                "patient_id": patient_id,
                "scanned_wristband": scanned_wristband_barcode,
                "order_id": medication_order_id,
                "drug_name": drug_name,
                "nurse_id": nurse_id,
                "timestamp": now_str,
                "status": "BLOCKED_WRONG_PATIENT_WRISTBAND",
                "error": f"FATAL MISIDENTIFICATION RISK: Scanned wristband '{scanned_wristband_barcode}' does not match chart patient '{patient_id}'."
            }
            self.administration_logs.append(exception_record)
            raise WristbandBarcodeVerificationError(exception_record["error"])

        # Successful administration
        admin_record = {
            "administration_id": f"ADM-{patient_id}-{int(as_of_time.timestamp())}",
            "patient_id": patient_id,
            "wristband_verified": True,
            "order_id": medication_order_id,
            "drug_name": drug_name,
            "dose": dose,
            "nurse_id": nurse_id,
            "timestamp": now_str,
            "status": "ADMINISTERED"
        }
        self.administration_logs.append(admin_record)
        return admin_record

    def log_fluid_intake_output(
        self,
        patient_id: str,
        nurse_id: str,
        intake_ml: float,
        intake_type: str,    # IV_CRYSTALLOID, BLOOD_PRODUCT, ORAL, NG_FEED
        output_ml: float,
        output_type: str,   # URINE, DRAIN, CHEST_TUBE, VOMIT, STOMA
        patient_weight_kg: float = 70.0,
        observation_hours: float = 2.0
    ) -> Dict[str, Any]:
        """
        Logs fluid intake/output and surveils for acute oliguria (< 0.5 mL/kg/h).
        """
        now_str = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": now_str,
            "intake_ml": intake_ml,
            "intake_type": intake_type,
            "output_ml": output_ml,
            "output_type": output_type,
            "nurse_id": nurse_id
        }
        self.fluid_records.setdefault(patient_id, []).append(entry)

        # Calculate cumulative 24h totals
        total_intake = sum(e["intake_ml"] for e in self.fluid_records[patient_id])
        total_output = sum(e["output_ml"] for e in self.fluid_records[patient_id])
        net_balance = total_intake - total_output

        # Oliguria check (if output is urine)
        oliguria_alert = False
        urine_rate_ml_kg_hr = 0.0
        if output_type == "URINE" and observation_hours > 0 and patient_weight_kg > 0:
            urine_rate_ml_kg_hr = round(output_ml / (patient_weight_kg * observation_hours), 2)
            if urine_rate_ml_kg_hr < 0.5:
                oliguria_alert = True

        return {
            "patient_id": patient_id,
            "recorded_intake_ml": intake_ml,
            "recorded_output_ml": output_ml,
            "cumulative_intake_ml": total_intake,
            "cumulative_output_ml": total_output,
            "net_fluid_balance_ml": net_balance,
            "urine_rate_ml_kg_hr": urine_rate_ml_kg_hr,
            "oliguria_alert": oliguria_alert
        }

    def assess_braden_score(
        self,
        patient_id: str,
        nurse_id: str,
        sensory: int,
        moisture: int,
        activity: int,
        mobility: int,
        nutrition: int,
        friction_shear: int
    ) -> BradenScoreAssessment:
        """
        Braden Scale for Pressure Sore Risk (Score 6-23).
        Score <= 12 is HIGH RISK -> triggers alternating air pressure mattress.
        """
        total = sensory + moisture + activity + mobility + nutrition + friction_shear
        if total <= 9:
            risk = "VERY_HIGH"
        elif total <= 12:
            risk = "HIGH"
        elif total <= 14:
            risk = "MODERATE"
        elif total <= 18:
            risk = "MILD"
        else:
            risk = "NO_RISK"

        air_mattress = total <= 12

        assessment = BradenScoreAssessment(
            assessment_id=f"BRADEN-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            patient_id=patient_id,
            nurse_id=nurse_id,
            sensory_perception=sensory,
            moisture=moisture,
            activity=activity,
            mobility=mobility,
            nutrition=nutrition,
            friction_shear=friction_shear,
            total_score=total,
            risk_level=risk,
            air_mattress_indicated=air_mattress,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.braden_assessments.append(assessment)
        return assessment

    def assess_morse_fall_score(
        self,
        patient_id: str,
        nurse_id: str,
        history_falls: int,
        secondary_diag: int,
        ambulatory_aid: int,
        iv_lock: int,
        gait: int,
        mental: int
    ) -> MorseFallAssessment:
        """
        Morse Fall Scale (Score 0-125).
        Score >= 45 is HIGH FALL RISK -> yellow wristband + bed alarm flag.
        """
        total = history_falls + secondary_diag + ambulatory_aid + iv_lock + gait + mental
        if total >= 45:
            risk = "HIGH"
            fall_flag = True
        elif total >= 25:
            risk = "MEDIUM"
            fall_flag = False
        else:
            risk = "LOW"
            fall_flag = False

        assessment = MorseFallAssessment(
            assessment_id=f"FALL-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            patient_id=patient_id,
            nurse_id=nurse_id,
            history_of_falls=history_falls,
            secondary_diagnosis=secondary_diag,
            ambulatory_aid=ambulatory_aid,
            iv_or_saline_lock=iv_lock,
            gait_transferring=gait,
            mental_status=mental,
            total_score=total,
            risk_level=risk,
            fall_precaution_flag=fall_flag,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )
        self.fall_assessments.append(assessment)
        return assessment

    def execute_isbar_handover(
        self,
        ward_id: str,
        outgoing_nurse_id: str,
        incoming_nurse_id: str,
        patients_reviewed: List[Dict[str, Any]],
        shift_name: str,
        outgoing_signed: bool,
        incoming_signed: bool
    ) -> ISBARHandoverRecord:
        """
        Structured ISBAR shift handover requiring dual electronic signatures.
        """
        now_str = datetime.now(timezone.utc).isoformat()

        if not outgoing_signed or not incoming_signed:
            raise NursingHandoverError(
                "ISBAR HANDOVER VIOLATION: Shift transition mandates dual electronic sign-off from both outgoing and incoming nurses."
            )

        if outgoing_nurse_id == incoming_nurse_id:
            raise NursingHandoverError(
                "ISBAR HANDOVER VIOLATION: Outgoing and incoming nurses must be distinct clinicians."
            )

        handover = ISBARHandoverRecord(
            handover_id=f"ISBAR-{ward_id}-{int(datetime.now(timezone.utc).timestamp())}",
            ward_id=ward_id,
            outgoing_nurse_id=outgoing_nurse_id,
            incoming_nurse_id=incoming_nurse_id,
            patients_reviewed=patients_reviewed,
            outgoing_signed_at=now_str,
            incoming_signed_at=now_str,
            shift_name=shift_name,
            status="COMPLETED"
        )
        self.handover_records.append(handover)
        return handover
