"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Test Suite: test_transfusion_transplant.py
Validates:
  - Quality Gate 2: Blood transfusion barcode mismatch sounds emergency siren and halts administration
  - Statutory THOTA Brain Death 4-member board & mandated 6-hour interval enforcement
  - Cold Ischemic Time (CIT) monitoring and viability tracking
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from organ_transplant_engine import (
    OrganTransplantTransfusionEngine, TransfusionBarcodeMismatchError, BrainDeathCertificationError
)


class TestTransfusionTransplantEngine(unittest.TestCase):

    def setUp(self):
        self.engine = OrganTransplantTransfusionEngine()
        self.now = datetime.now(timezone.utc)

    def test_quality_gate_transfusion_barcode_mismatch_triggers_siren_and_halts(self):
        """
        Phase 09 Quality Gate 2:
        Blood transfusion unit barcode mismatch sounds immediate emergency siren on nurse tablet
        and halts administration.
        """
        patient_chart_id = "PAT-OT-902"
        prescribed_unit_barcode = "BLOOD-BAG-PRBC-1102"

        # 1. Nurse scans mismatched blood unit (e.g. adjacent patient's blood unit) -> HALT & SIREN!
        with self.assertRaises(TransfusionBarcodeMismatchError) as ctx1:
            self.engine.verify_bedside_transfusion_barcodes(
                patient_chart_id=patient_chart_id,
                scanned_patient_wristband=patient_chart_id,
                expected_blood_unit_barcode=prescribed_unit_barcode,
                scanned_blood_bag_barcode="BLOOD-BAG-PRBC-WRONG-88",  # Mismatch!
                nurse_1_id="NURSE-01",
                nurse_2_id="NURSE-02",
                as_of_time=self.now
            )

        self.assertIn("EMERGENCY ALARM", str(ctx1.exception))
        self.assertIn("does not match prescribed unit", str(ctx1.exception))

        # Check recorded event state
        last_event = self.engine.transfusion_records[-1]
        self.assertEqual(last_event["status"], "HALTED_UNIT_MISMATCH")
        self.assertTrue(last_event["emergency_siren_triggered"])

        # 2. Matching barcodes -> Transfusion approved
        admin = self.engine.verify_bedside_transfusion_barcodes(
            patient_chart_id=patient_chart_id,
            scanned_patient_wristband=patient_chart_id,
            expected_blood_unit_barcode=prescribed_unit_barcode,
            scanned_blood_bag_barcode=prescribed_unit_barcode,  # Match!
            nurse_1_id="NURSE-01",
            nurse_2_id="NURSE-02",
            as_of_time=self.now
        )
        self.assertEqual(admin["status"], "APPROVED_ADMINISTERING")
        self.assertFalse(admin["emergency_siren_triggered"])

    def test_thota_brain_death_certification_mandates_6_hour_interval(self):
        """Verify THOTA statutory 4-member board and minimum 6-hour interval between serial exams."""
        patient_id = "DONOR-ICU-09"

        # Exam 1 at time T
        exam_1_time = self.now - timedelta(hours=3)  # Only 3 hours ago!
        self.engine.record_brain_death_assessment(
            patient_id=patient_id,
            exam_number=1,
            apnea_test_positive=True,
            brainstem_reflexes_absent=True,
            medical_superintendent_id="DOC-MS-01",
            treating_physician_id="DOC-PYS-02",
            independent_specialist_id="DOC-SPEC-03",
            neurologist_id="DOC-NEURO-04",
            exam_time=exam_1_time
        )

        # Attempting Exam 2 after only 3 hours -> BLOCKED by THOTA statutory rule!
        with self.assertRaises(BrainDeathCertificationError) as ctx:
            self.engine.record_brain_death_assessment(
                patient_id=patient_id,
                exam_number=2,
                apnea_test_positive=True,
                brainstem_reflexes_absent=True,
                medical_superintendent_id="DOC-MS-01",
                treating_physician_id="DOC-PYS-02",
                independent_specialist_id="DOC-SPEC-03",
                neurologist_id="DOC-NEURO-04",
                exam_time=self.now  # Only 3 hours later!
            )
        self.assertIn("STATUTORY 6-HOUR WINDOW BREACH", str(ctx.exception))
        self.assertIn("mandate minimum 6.0 hours observation interval", str(ctx.exception))

        # Re-attempt Exam 2 after full 6.5 hours -> SUCCEEDS and certifies Form 10
        exam_2_time = exam_1_time + timedelta(hours=6, minutes=30)
        cert = self.engine.record_brain_death_assessment(
            patient_id=patient_id,
            exam_number=2,
            apnea_test_positive=True,
            brainstem_reflexes_absent=True,
            medical_superintendent_id="DOC-MS-01",
            treating_physician_id="DOC-PYS-02",
            independent_specialist_id="DOC-SPEC-03",
            neurologist_id="DOC-NEURO-04",
            exam_time=exam_2_time
        )
        self.assertEqual(cert["stage"], "BRAIN_DEATH_CERTIFIED_FORM_10")
        self.assertEqual(cert["interval_hours"], 6.5)

    def test_cold_ischemic_time_viability_tracking(self):
        """Verify Cold Ischemic Time (CIT) monitoring against organ limits."""
        # Donor Heart clamped 3 hours ago (Heart max CIT = 4.0 hours)
        clamp_time = self.now - timedelta(hours=3)
        self.engine.register_retrieved_organ(
            organ_id="ORGAN-HEART-01",
            donor_patient_id="DONOR-ICU-09",
            organ_type="HEART",
            cross_clamp_time=clamp_time
        )

        status = self.engine.evaluate_cold_ischemic_time("ORGAN-HEART-01", current_time=self.now)
        self.assertTrue(status["is_viable"])
        self.assertEqual(status["elapsed_cit_hours"], 3.0)
        self.assertEqual(status["remaining_cit_hours"], 1.0)
        self.assertIn("CRITICAL CIT WINDOW", status["warning"])


if __name__ == "__main__":
    unittest.main()
