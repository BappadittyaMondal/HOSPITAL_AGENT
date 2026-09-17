"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Module: organ_transplant_engine.py
Operational Scope:
  - Bedside Dual-Nurse Blood Transfusion Barcode Verification
  - Quality Gate 2: Blood Transfusion Barcode Mismatch Sounds Immediate Emergency Siren & Halts Administration
  - Statutory THOTA Brain Death 4-Member Board Certification (Mandated 6-Hour Interval) (Gap 26)
  - Cold Ischemic Time (CIT) Real-Time Countdown & Expiry Surveillance
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any


class TransfusionSafetyError(Exception):
    """Base exception for blood transfusion safety violations."""
    pass


class TransfusionBarcodeMismatchError(TransfusionSafetyError):
    """Raised when blood unit barcode or patient wristband mismatch occurs at bedside."""
    pass


class BrainDeathCertificationError(Exception):
    """Raised when statutory brain death protocol is incomplete or interval is violated."""
    pass


@dataclass
class BloodUnitTag:
    unit_barcode: str
    blood_group: str        # e.g., "A_POS", "O_NEG"
    component: str          # PRBC, FFP, PLATELETS, CRYO
    donor_id: str
    assigned_patient_id: str
    expiry_date: datetime


@dataclass
class OrganRetrievalRecord:
    organ_id: str
    donor_patient_id: str
    organ_type: str         # HEART, LUNG, LIVER, KIDNEY
    crossmatch_status: str
    cross_clamp_time: datetime
    max_safe_cit_hours: float
    current_status: str = "IN_TRANSIT"  # IN_TRANSIT, IMPLANTED, EXPIRED_VIABILITY


class OrganTransplantTransfusionEngine:
    """
    Manages bedside transfusion barcode verification, statutory THOTA brain death certification,
    and organ transplant cold ischemic timing.
    """

    # Maximum Cold Ischemic Times (hours)
    CIT_LIMITS_HOURS = {
        "HEART": 4.0,
        "LUNG": 6.0,
        "LIVER": 12.0,
        "KIDNEY": 24.0,
        "PANCREAS": 12.0
    }

    def __init__(self):
        self.transfusion_records: List[Dict[str, Any]] = []
        self.brain_death_certifications: Dict[str, Dict[str, Any]] = {}
        self.retrieved_organs: Dict[str, OrganRetrievalRecord] = {}

    def verify_bedside_transfusion_barcodes(
        self,
        patient_chart_id: str,
        scanned_patient_wristband: str,
        expected_blood_unit_barcode: str,
        scanned_blood_bag_barcode: str,
        nurse_1_id: str,
        nurse_2_id: str,
        as_of_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Quality Gate 2:
        Blood transfusion unit barcode mismatch sounds immediate emergency siren on nurse tablet
        and halts administration.
        Requires dual-nurse bedside scan verification.
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        now_str = as_of_time.isoformat()

        if nurse_1_id == nurse_2_id:
            raise TransfusionSafetyError("Dual-nurse verification mandates two distinct clinicians.")

        # Check 1: Patient Wristband Barcode Mismatch
        if scanned_patient_wristband != patient_chart_id:
            incident = {
                "patient_id": patient_chart_id,
                "scanned_wristband": scanned_patient_wristband,
                "status": "HALTED_WRISTBAND_MISMATCH",
                "emergency_siren_triggered": True,
                "timestamp": now_str,
                "error": f"EMERGENCY ALARM: Scanned wristband '{scanned_patient_wristband}' does not match patient '{patient_chart_id}'!"
            }
            self.transfusion_records.append(incident)
            raise TransfusionBarcodeMismatchError(incident["error"])

        # Check 2: Blood Bag Barcode Mismatch
        if scanned_blood_bag_barcode != expected_blood_unit_barcode:
            incident = {
                "patient_id": patient_chart_id,
                "expected_unit": expected_blood_unit_barcode,
                "scanned_unit": scanned_blood_bag_barcode,
                "status": "HALTED_UNIT_MISMATCH",
                "emergency_siren_triggered": True,
                "timestamp": now_str,
                "error": f"EMERGENCY ALARM: Scanned blood unit '{scanned_blood_bag_barcode}' does not match prescribed unit '{expected_blood_unit_barcode}'!"
            }
            self.transfusion_records.append(incident)
            raise TransfusionBarcodeMismatchError(incident["error"])

        # Success
        record = {
            "transfusion_id": f"TX-{patient_chart_id}-{int(as_of_time.timestamp())}",
            "patient_id": patient_chart_id,
            "unit_barcode": scanned_blood_bag_barcode,
            "verified_by_nurses": [nurse_1_id, nurse_2_id],
            "status": "APPROVED_ADMINISTERING",
            "emergency_siren_triggered": False,
            "timestamp": now_str
        }
        self.transfusion_records.append(record)
        return record

    def record_brain_death_assessment(
        self,
        patient_id: str,
        exam_number: int,  # 1 or 2
        apnea_test_positive: bool,
        brainstem_reflexes_absent: bool,
        medical_superintendent_id: str,
        treating_physician_id: str,
        independent_specialist_id: str,
        neurologist_id: str,
        exam_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Statutory THOTA Brain Death Certification:
        Requires 4 distinct designated board members and 2 serial examinations
        separated by at least 6 hours.
        """
        if exam_time is None:
            exam_time = datetime.now(timezone.utc)

        # Validate 4 distinct board members
        board = {medical_superintendent_id, treating_physician_id, independent_specialist_id, neurologist_id}
        if len(board) < 4:
            raise BrainDeathCertificationError(
                "THOTA VIOLATION: Brain Death Medical Board must consist of 4 distinct qualified medical practitioners."
            )

        if not (apnea_test_positive and brainstem_reflexes_absent):
            raise BrainDeathCertificationError(
                "CLINICAL PROTOCOL FAILURE: Apnea test must be positive (absence of spontaneous respiration with PaCO2 >= 60 mmHg) "
                "and all brainstem reflexes must be confirmed absent."
            )

        cert_record = self.brain_death_certifications.setdefault(patient_id, {
            "exam_1": None,
            "exam_2": None,
            "board_members": list(board),
            "status": "IN_PROGRESS"
        })

        if exam_number == 1:
            cert_record["exam_1"] = {
                "timestamp": exam_time,
                "apnea_test_positive": apnea_test_positive,
                "brainstem_reflexes_absent": brainstem_reflexes_absent
            }
            return {"patient_id": patient_id, "stage": "EXAM_1_COMPLETED", "next_exam_earliest": (exam_time + timedelta(hours=6)).isoformat()}

        elif exam_number == 2:
            if not cert_record["exam_1"]:
                raise BrainDeathCertificationError("Exam 1 must be completed prior to Exam 2.")

            exam_1_time = cert_record["exam_1"]["timestamp"]
            interval_hours = (exam_time - exam_1_time).total_seconds() / 3600.0

            # Mandated 6-Hour Observation Interval
            if interval_hours < 6.0:
                shortfall_min = round((6.0 - interval_hours) * 60.0)
                raise BrainDeathCertificationError(
                    f"STATUTORY 6-HOUR WINDOW BREACH: Only {round(interval_hours, 2)} hours elapsed since Exam 1. "
                    f"THOTA statutory guidelines mandate minimum 6.0 hours observation interval (Shortfall: {shortfall_min} minutes)."
                )

            cert_record["exam_2"] = {
                "timestamp": exam_time,
                "apnea_test_positive": apnea_test_positive,
                "brainstem_reflexes_absent": brainstem_reflexes_absent
            }
            cert_record["status"] = "BRAIN_DEATH_CERTIFIED_FORM_10"
            return {
                "patient_id": patient_id,
                "stage": "BRAIN_DEATH_CERTIFIED_FORM_10",
                "interval_hours": round(interval_hours, 2),
                "certified_at": exam_time.isoformat()
            }

        else:
            raise ValueError("Invalid exam number (must be 1 or 2).")

    def register_retrieved_organ(
        self,
        organ_id: str,
        donor_patient_id: str,
        organ_type: str,
        cross_clamp_time: datetime
    ) -> OrganRetrievalRecord:
        """Registers a retrieved donor organ and tracks Cold Ischemic Time (CIT)."""
        limit = self.CIT_LIMITS_HOURS.get(organ_type.upper(), 12.0)
        rec = OrganRetrievalRecord(
            organ_id=organ_id,
            donor_patient_id=donor_patient_id,
            organ_type=organ_type.upper(),
            crossmatch_status="NEGATIVE_COMPATIBLE",
            cross_clamp_time=cross_clamp_time,
            max_safe_cit_hours=limit
        )
        self.retrieved_organs[organ_id] = rec
        return rec

    def evaluate_cold_ischemic_time(self, organ_id: str, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Monitors Cold Ischemic Time against safe viability thresholds."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        organ = self.retrieved_organs.get(organ_id)
        if not organ:
            raise ValueError(f"Organ {organ_id} not found.")

        elapsed_hours = (current_time - organ.cross_clamp_time).total_seconds() / 3600.0
        remaining_hours = organ.max_safe_cit_hours - elapsed_hours

        is_viable = remaining_hours > 0.0
        if not is_viable:
            organ.current_status = "EXPIRED_VIABILITY"

        return {
            "organ_id": organ_id,
            "organ_type": organ.organ_type,
            "elapsed_cit_hours": round(elapsed_hours, 2),
            "max_safe_cit_hours": organ.max_safe_cit_hours,
            "remaining_cit_hours": round(max(0.0, remaining_hours), 2),
            "is_viable": is_viable,
            "warning": "CRITICAL CIT WINDOW: < 1 hour remaining!" if (0 < remaining_hours <= 1.0) else None
        }
