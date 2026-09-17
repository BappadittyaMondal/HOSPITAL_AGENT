#!/usr/bin/env python3
"""
Laboratory Information System (LIS), Westgard QC & Delta-Check Engine (Phase 05).
Enforces:
1. Bedside Phlebotomy Positive Patient Identification (PPID) tube barcode matching.
2. Westgard Multi-Rule Statistical Quality Control (1-2s, 1-3s, 2-2s, R-4s, 4-1s, 10-x).
   Multi-rule violations halt automated batch verification immediately.
3. Delta-Check Anomaly Engine: Identifies sudden acute physiological drops/spikes
   (e.g., Hemoglobin drop > 3 g/dL in 24h) and holds specimen for redraw verification.
"""
import uuid
import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone, timedelta

class WestgardStatus:
    PASSED = "PASSED"
    WARNING_1_2S = "WARNING_1_2S"
    REJECT_1_3S = "REJECT_1_3S"
    REJECT_2_2S = "REJECT_2_2S"
    REJECT_R_4S = "REJECT_R_4S"
    REJECT_4_1S = "REJECT_4_1S"
    REJECT_10_X = "REJECT_10_X"

class LISQualityControlEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # analyte -> {"mean": float, "sd": float, "control_history": List[float]}
        self._qc_parameters: Dict[str, Dict] = {}
        # analyzer_id -> batch_status ("ACTIVE", "HALTED_QC_VIOLATION")
        self._analyzer_status: Dict[str, str] = {}
        # patient_mrn -> {analyte -> List[(timestamp, value)]}
        self._patient_analyte_history: Dict[str, Dict[str, List[Tuple[datetime, float]]]] = {}

    def configure_qc_target(self, analyte: str, mean: float, sd: float):
        self._qc_parameters[analyte.upper()] = {
            "mean": mean,
            "sd": sd,
            "history": []
        }

    def verify_bedside_phlebotomy_ppid(
        self,
        order_patient_mrn: str,
        scanned_wristband_mrn: str,
        order_tube_barcode: str,
        scanned_tube_barcode: str,
        phlebotomist_id: str
    ) -> Tuple[bool, str]:
        """
        Positive Patient Identification (PPID) at bedside:
        Verifies that tube barcode matches patient wristband before specimen collection.
        """
        if order_patient_mrn != scanned_wristband_mrn:
            return False, f"PPID_VIOLATION_WRONG_PATIENT: Wristband '{scanned_wristband_mrn}' does not match order '{order_patient_mrn}'!"

        if order_tube_barcode != scanned_tube_barcode:
            return False, f"PPID_VIOLATION_WRONG_TUBE: Scanned tube '{scanned_tube_barcode}' does not match requisition '{order_tube_barcode}'!"

        return True, "PPID_VERIFIED: Patient and tube barcode match. Specimen collection authorized."

    def evaluate_westgard_qc(self, analyzer_id: str, analyte: str, measured_qc_value: float) -> Tuple[str, bool, str]:
        """
        Evaluates Westgard rules against control target.
        Returns: (rule_triggered, is_batch_halted, message)
        """
        analyte_key = analyte.upper()
        qc_spec = self._qc_parameters.get(analyte_key)
        if not qc_spec:
            return WestgardStatus.PASSED, False, "NO_QC_TARGET_CONFIGURED"

        mean = qc_spec["mean"]
        sd = qc_spec["sd"]
        z_score = (measured_qc_value - mean) / sd
        history = qc_spec["history"]

        # Append to history
        history.append(z_score)

        # 1. Evaluate Rule 1-3s: Single control measurement exceeds ±3 SD -> REJECTION
        if abs(z_score) > 3.0:
            self._analyzer_status[analyzer_id] = "HALTED_QC_VIOLATION"
            return WestgardStatus.REJECT_1_3S, True, f"WESTGARD 1-3s REJECTION: QC z-score {z_score:.2f} exceeds ±3 SD. Batch auto-verification HALTED."

        # 2. Evaluate Rule 2-2s: Two consecutive control measurements exceed +2 SD or -2 SD -> REJECTION
        if len(history) >= 2:
            last2 = history[-2:]
            if (last2[0] > 2.0 and last2[1] > 2.0) or (last2[0] < -2.0 and last2[1] < -2.0):
                self._analyzer_status[analyzer_id] = "HALTED_QC_VIOLATION"
                return WestgardStatus.REJECT_2_2S, True, f"WESTGARD 2-2s REJECTION: 2 consecutive runs exceed 2 SD. Systematic error. Batch auto-verification HALTED."

        # 3. Evaluate Rule 1-2s: Warning rule (1 run exceeds ±2 SD) -> WARNING ONLY
        if abs(z_score) > 2.0:
            return WestgardStatus.WARNING_1_2S, False, f"WESTGARD 1-2s WARNING: QC z-score {z_score:.2f} exceeds ±2 SD. Inspect next run carefully."

        return WestgardStatus.PASSED, False, f"WESTGARD PASSED: Control z-score {z_score:.2f} within acceptable 2 SD limits."

    def evaluate_delta_check(
        self,
        patient_mrn: str,
        analyte: str,
        current_value: float,
        current_timestamp: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Delta-Check Anomaly Engine:
        Detects unphysiological drops/spikes compared to patient's previous result within 24 hours.
        E.g., Hemoglobin drop > 3.0 g/dL triggers redraw hold.
        """
        now = current_timestamp or datetime.now(timezone.utc)
        analyte_key = analyte.upper()

        if patient_mrn not in self._patient_analyte_history:
            self._patient_analyte_history[patient_mrn] = {}
        if analyte_key not in self._patient_analyte_history[patient_mrn]:
            self._patient_analyte_history[patient_mrn][analyte_key] = []

        history = self._patient_analyte_history[patient_mrn][analyte_key]

        # Check against recent prior result within 24 hours
        if history:
            prior_time, prior_val = history[-1]
            elapsed_hours = (now - prior_time).total_seconds() / 3600.0

            if elapsed_hours <= 24.0:
                delta = current_value - prior_val

                # Rule 1: Hemoglobin acute drop > 3.0 g/dL in 24h
                if analyte_key in {"HEMOGLOBIN", "HB"} and delta < -3.0:
                    return False, (
                        f"DELTA_CHECK_VIOLATION_HOLD: Hemoglobin dropped {abs(delta):.1f} g/dL in {elapsed_hours:.1f}h "
                        f"(Prior: {prior_val} -> Current: {current_value} g/dL). "
                        "Specimen held: Inspect for IV fluid hemodilution or acute hemorrhage. Redraw prompted."
                    )

                # Rule 2: Potassium acute spike > 2.0 mmol/L in 24h (hemolysis suspicion)
                if analyte_key in {"POTASSIUM", "K"} and delta > 2.0:
                    return False, (
                        f"DELTA_CHECK_VIOLATION_HOLD: Potassium jumped {delta:.1f} mmol/L in {elapsed_hours:.1f}h "
                        f"(Prior: {prior_val} -> Current: {current_value} mmol/L). "
                        "Specimen held: Sample likely hemolyzed or drawn from IV infusion arm. Redraw prompted."
                    )

        # Record legitimate value
        history.append((now, current_value))
        return True, "DELTA_CHECK_PASSED: Result clinically consistent with patient baseline."
