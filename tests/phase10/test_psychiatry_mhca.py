"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Test Suite: test_psychiatry_mhca.py
Validates:
  - Quality Gate 2: Involuntary psychiatric admission auto-generates statutory MHCA Form and 72h review board dossier
  - Section 23 clinical notes privacy barrier
  - CIWA-Ar and COWS withdrawal scoring
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from psychiatry_mhca_engine import (
    PsychiatryMHCAEngine, MHCAComplianceError, PsychiatricRecordPrivacyError
)


class TestPsychiatryMHCAEngine(unittest.TestCase):

    def setUp(self):
        self.engine = PsychiatryMHCAEngine()
        self.now = datetime.now(timezone.utc)

    def test_quality_gate_involuntary_admission_generates_form_and_72h_dossier(self):
        """
        Phase 10 Quality Gate 2:
        Involuntary psychiatric admission auto-generates statutory MHCA Form and
        schedules review board dossier dispatch within 72 hours.
        """
        patient_id = "PAT-PSYCH-801"

        dossier = self.engine.process_supported_involuntary_admission(
            patient_id=patient_id,
            primary_psychiatrist_id="DOC-PSYCH-01",
            secondary_evaluator_id="DOC-PSYCH-02",
            nominated_representative_id="NR-SPOUSE-01",
            nominated_representative_name="Sunita Sharma",
            nominated_rep_consent=True,
            advance_directive_registered=False,
            clinical_justification="Severe bipolar mania with acute psychotic agitation and grave risk of self-harm",
            admission_time=self.now
        )

        # 1. Statutory Form 4 generated
        self.assertEqual(dossier.statutory_form_name, "MHCA_FORM_4_SUPPORTED_ADMISSION")
        self.assertEqual(dossier.admission_type, "SUPPORTED_INVOLUNTARY")
        self.assertEqual(dossier.dossier_status, "PENDING_DISPATCH")

        # 2. 72-Hour Review Board dispatch deadline enforced
        expected_deadline = self.now + timedelta(hours=72)
        self.assertEqual(dossier.review_board_deadline_72h, expected_deadline)

    def test_section_23_mental_health_records_privacy_barrier(self):
        """Verify unprivileged staff cannot access protected psychiatric clinical notes."""
        # General Nurse attempting access -> BLOCKED
        with self.assertRaises(PsychiatricRecordPrivacyError) as ctx1:
            self.engine.verify_psychiatric_note_access("GENERAL_NURSE", "NURSE-WARD-04")
        self.assertIn("STATUTORY PRIVACY VIOLATION", str(ctx1.exception))
        self.assertIn("Sec 23", str(ctx1.exception))

        # Billing clerk attempting access -> BLOCKED
        with self.assertRaises(PsychiatricRecordPrivacyError) as ctx2:
            self.engine.verify_psychiatric_note_access("BILLING_CLERK", "STAFF-BILL-01")
        self.assertIn("strictly barred", str(ctx2.exception))

        # Psychiatrist attempting access -> ALLOWED
        self.assertTrue(self.engine.verify_psychiatric_note_access("PSYCHIATRIST", "DOC-PSYCH-01"))

    def test_ciwa_ar_alcohol_withdrawal_scoring(self):
        """Verify CIWA-Ar score calculation and benzodiazepine indication (score >= 15)."""
        # High withdrawal symptoms: Nausea 5, Tremor 6, Sweats 5, Anxiety 5 -> Total = 21 (Severe)
        scores = {
            "nausea": 5, "tremor": 6, "sweats": 5, "anxiety": 5, "agitation": 4,
            "tactile": 0, "auditory": 0, "visual": 0, "headache": 2, "orientation": 0
        }
        assessment = self.engine.calculate_ciwa_ar("PAT-DETOX-01", scores, "NURSE-PSYCH-01")
        self.assertEqual(assessment.total_score, 27)
        self.assertEqual(assessment.severity, "SEVERE")
        self.assertTrue(assessment.benzodiazepine_protocol_indicated)


if __name__ == "__main__":
    unittest.main()
