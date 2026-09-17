"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Test Suite: test_nursing_cockpit.py
Validates:
  - Quality Gate 2: Inpatient med administration without wristband scan is blocked
  - Fluid intake/output balance & oliguria alert (< 0.5 mL/kg/h)
  - Braden Scale & Morse Fall Scale clinical scoring
  - ISBAR shift handover dual signature verification
"""

import unittest
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from nursing_cockpit_engine import (
    NursingCockpitEngine, WristbandBarcodeVerificationError, NursingHandoverError
)


class TestNursingCockpitEngine(unittest.TestCase):

    def setUp(self):
        self.engine = NursingCockpitEngine()
        self.now = datetime.now(timezone.utc)

    def test_quality_gate_wristband_scan_mandatory_and_mismatch_blocked(self):
        """
        Phase 07 Quality Gate 2:
        Inpatient medication administration without scanning the patient wristband barcode
        is blocked or logged as a safety exception.
        """
        patient_id = "PAT-INP-7721"

        # 1. No wristband scan provided -> BLOCKED
        with self.assertRaises(WristbandBarcodeVerificationError) as ctx1:
            self.engine.administer_medication_at_bedside(
                patient_id=patient_id,
                scanned_wristband_barcode=None,  # Missing!
                medication_order_id="ORD-MED-99",
                drug_name="Ceftriaxone",
                dose="1 g IV",
                nurse_id="NURSE-01",
                as_of_time=self.now
            )
        self.assertIn("Wristband barcode scan is mandatory", str(ctx1.exception))
        self.assertEqual(self.engine.administration_logs[-1]["status"], "BLOCKED_NO_WRISTBAND_SCAN")

        # 2. Mismatched wristband scanned (e.g. adjacent bed patient) -> BLOCKED
        with self.assertRaises(WristbandBarcodeVerificationError) as ctx2:
            self.engine.administer_medication_at_bedside(
                patient_id=patient_id,
                scanned_wristband_barcode="PAT-INP-WRONG",  # Mismatch!
                medication_order_id="ORD-MED-99",
                drug_name="Ceftriaxone",
                dose="1 g IV",
                nurse_id="NURSE-01",
                as_of_time=self.now
            )
        self.assertIn("FATAL MISIDENTIFICATION RISK", str(ctx2.exception))
        self.assertEqual(self.engine.administration_logs[-1]["status"], "BLOCKED_WRONG_PATIENT_WRISTBAND")

        # 3. Valid matching wristband scanned -> ADMINISTERED
        admin = self.engine.administer_medication_at_bedside(
            patient_id=patient_id,
            scanned_wristband_barcode=patient_id,  # Match!
            medication_order_id="ORD-MED-99",
            drug_name="Ceftriaxone",
            dose="1 g IV",
            nurse_id="NURSE-01",
            as_of_time=self.now
        )
        self.assertEqual(admin["status"], "ADMINISTERED")
        self.assertTrue(admin["wristband_verified"])

    def test_fluid_intake_output_and_oliguria_detection(self):
        """Verify fluid balance calculation and oliguria detection."""
        patient_id = "PAT-SURG-01"
        # Weight 70kg, 2 hours observation, urine output 40 mL -> 40 / (70 * 2) = 0.29 mL/kg/h (< 0.5 -> OLIGURIA)
        res = self.engine.log_fluid_intake_output(
            patient_id=patient_id,
            nurse_id="NURSE-02",
            intake_ml=500.0,
            intake_type="IV_CRYSTALLOID",
            output_ml=40.0,
            output_type="URINE",
            patient_weight_kg=70.0,
            observation_hours=2.0
        )
        self.assertEqual(res["cumulative_intake_ml"], 500.0)
        self.assertEqual(res["cumulative_output_ml"], 40.0)
        self.assertEqual(res["net_fluid_balance_ml"], 460.0)
        self.assertEqual(res["urine_rate_ml_kg_hr"], 0.29)
        self.assertTrue(res["oliguria_alert"])

    def test_braden_score_and_air_mattress_indication(self):
        """Verify Braden score calculation triggers air mattress when score <= 12."""
        # Total = 2 + 2 + 1 + 2 + 2 + 1 = 10 (HIGH RISK)
        assessment = self.engine.assess_braden_score(
            patient_id="PAT-ICU-05",
            nurse_id="NURSE-03",
            sensory=2, moisture=2, activity=1, mobility=2, nutrition=2, friction_shear=1
        )
        self.assertEqual(assessment.total_score, 10)
        self.assertEqual(assessment.risk_level, "HIGH")
        self.assertTrue(assessment.air_mattress_indicated)

    def test_morse_fall_score_and_precaution_flag(self):
        """Verify Morse fall scale triggers fall precaution flag when score >= 45."""
        # History (25) + Secondary (15) + IV lock (20) = 60 (HIGH RISK)
        assessment = self.engine.assess_morse_fall_score(
            patient_id="PAT-GERI-01",
            nurse_id="NURSE-03",
            history_falls=25, secondary_diag=15, ambulatory_aid=0,
            iv_lock=20, gait=0, mental=0
        )
        self.assertEqual(assessment.total_score, 60)
        self.assertEqual(assessment.risk_level, "HIGH")
        self.assertTrue(assessment.fall_precaution_flag)

    def test_isbar_handover_mandates_dual_distinct_signatures(self):
        """Verify ISBAR handover requires distinct signatures from both nurses."""
        patients = [{"bed": "101", "name": "Patient A", "acuity": "STABLE"}]

        # Missing incoming signature -> FAILS
        with self.assertRaises(NursingHandoverError) as ctx1:
            self.engine.execute_isbar_handover(
                ward_id="WARD-SURG-A",
                outgoing_nurse_id="NURSE-OUT",
                incoming_nurse_id="NURSE-IN",
                patients_reviewed=patients,
                shift_name="MORNING",
                outgoing_signed=True,
                incoming_signed=False  # Missing!
            )
        self.assertIn("mandates dual electronic sign-off", str(ctx1.exception))

        # Same nurse attempting both roles -> FAILS
        with self.assertRaises(NursingHandoverError) as ctx2:
            self.engine.execute_isbar_handover(
                ward_id="WARD-SURG-A",
                outgoing_nurse_id="NURSE-OUT",
                incoming_nurse_id="NURSE-OUT",  # Same user!
                patients_reviewed=patients,
                shift_name="MORNING",
                outgoing_signed=True,
                incoming_signed=True
            )
        self.assertIn("must be distinct clinicians", str(ctx2.exception))

        # Distinct nurses signed -> SUCCEEDS
        handover = self.engine.execute_isbar_handover(
            ward_id="WARD-SURG-A",
            outgoing_nurse_id="NURSE-OUT",
            incoming_nurse_id="NURSE-IN",
            patients_reviewed=patients,
            shift_name="MORNING",
            outgoing_signed=True,
            incoming_signed=True
        )
        self.assertEqual(handover.status, "COMPLETED")


if __name__ == "__main__":
    unittest.main()
