#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 23: DIAGNOSTIC ACCURACY & CONFORMAL CALIBRATION TEST SUITE
Module: tests/phase23/test_diagnostic_accuracy_and_conformal.py
Validates:
  1. Multi-assertion finding graph for atypical ACS in diabetic/geriatric patients.
  2. Structured InvestigationResult rule-out gate (status FINAL, numeric value, clinician sign-off).
  3. Split-conformal prediction calibration and dynamic uncertainty sizing.
  4. Time-elapsed Parkland burns fluid resuscitation calculation.
  5. Cryptographic HMAC-SHA256 Clinical Safety Board (CSB) model promotion authorization.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from structured_history_engine import (
    StructuredHistoryEngine,
    ChiefComplaintCategory,
    FindingPolarity
)
from diagnostic_graph_rag import (
    DiagnosticGraphRAGEngine,
    InvestigationResult,
    RedFlagRuleOutRequiredError
)
from sbccl_experience_engine import (
    SBCCLExperienceEngine,
    ConformalPredictionEngine,
    create_csb_authorization_token,
    UnauthorizedPromotionError
)
from clinical_emergency_scorers import calculate_parkland_burns_fluid


class TestDiagnosticAccuracyAndConformal(unittest.TestCase):

    def test_atypical_acs_history_intake_graph(self):
        """
        Diabetic/geriatric patient presenting with epigastric distress, cold sweats, and vomiting
        without chest pain must trigger ATYPICAL_ACUTE_CORONARY_SYNDROME_SILENT_MI red flag.
        """
        engine = StructuredHistoryEngine()
        sess = engine.initiate_session(
            session_id="SESS-GERIATRIC-01",
            patient_id="PAT-DIABETIC-70",
            chief_complaint=ChiefComplaintCategory.ABDOMINAL_PAIN,
            patient_age=68,
            is_female=True,
            is_pregnant=False
        )
        answers = {
            "has_diabetes": True,
            "pain_location": "EPIGASTRIC",
            "epigastric_burning": True,
            "has_cold_sweating": True,
            "has_vomiting": True,
            "chest_pain_present": False
        }
        sess = engine.process_responses(sess, answers)

        self.assertIn("ATYPICAL_ACUTE_CORONARY_SYNDROME_SILENT_MI", sess.active_red_flags)
        
        # Verify structured findings include Epigastric distress PRESENT and Chest pain ABSENT
        epigastric_finding = next((f for f in sess.findings if f.snomed_id == "249490001"), None)
        chest_pain_finding = next((f for f in sess.findings if f.snomed_id == "29857009"), None)

        self.assertIsNotNone(epigastric_finding)
        self.assertEqual(epigastric_finding.polarity, FindingPolarity.PRESENT)
        self.assertTrue(epigastric_finding.is_red_flag)

        self.assertIsNotNone(chest_pain_finding)
        self.assertEqual(chest_pain_finding.polarity, FindingPolarity.ABSENT)

        # Immediate actions must mandate 10-minute ECG and chewable Aspirin
        self.assertTrue(any("ECG WITHIN 10 MINUTES" in act for act in sess.recommended_immediate_actions))
        self.assertTrue(any("Aspirin 300mg" in act for act in sess.recommended_immediate_actions))

    def test_structured_investigation_result_rule_out_gate(self):
        """
        Clinician cannot confirm benign diagnosis (e.g. GERD) for acute chest pain
        if mandatory cardiac evaluations are PENDING, unsigned, or lack numeric values.
        """
        graph_rag = DiagnosticGraphRAGEngine()
        debiasing = graph_rag.debiasing
        present_snomed = {"29857009"}  # Chest pain

        # 1. Troponin is PENDING -> Must be BLOCKED
        pending_invs = [
            InvestigationResult(
                investigation_id="164868007",
                test_name="12-Lead ECG",
                status="FINAL",
                clinician_signed_off=True
            ),
            InvestigationResult(
                investigation_id="102685005",
                test_name="High-Sensitivity Troponin I",
                status="PENDING",  # Incomplete!
                numeric_value=None,
                clinician_signed_off=False
            ),
            InvestigationResult(
                investigation_id="274092004",
                test_name="Quantitative D-Dimer",
                status="FINAL",
                numeric_value=120.0,
                clinician_signed_off=True
            )
        ]
        with self.assertRaises(RedFlagRuleOutRequiredError) as ctx1:
            debiasing.verify_safe_discharge_or_benign_diagnosis(
                present_snomed_ids=present_snomed,
                completed_investigations=pending_invs,
                proposed_diagnosis_key="GASTROESOPHAGEAL_REFLUX"
            )
        self.assertIn("COGNITIVE DE-BIASING HARD-STOP", str(ctx1.exception))
        self.assertIn("REJECTED", str(ctx1.exception))

        # 2. Troponin is FINAL but unsigned -> Must be BLOCKED
        unsigned_invs = [
            InvestigationResult(
                investigation_id="164868007",
                test_name="12-Lead ECG",
                status="FINAL",
                clinician_signed_off=True
            ),
            InvestigationResult(
                investigation_id="102685005",
                test_name="High-Sensitivity Troponin I",
                status="FINAL",
                numeric_value=0.012,
                clinician_signed_off=False  # Missing sign-off!
            ),
            InvestigationResult(
                investigation_id="274092004",
                test_name="Quantitative D-Dimer",
                status="FINAL",
                numeric_value=120.0,
                clinician_signed_off=True
            )
        ]
        with self.assertRaises(RedFlagRuleOutRequiredError) as ctx2:
            debiasing.verify_safe_discharge_or_benign_diagnosis(
                present_snomed_ids=present_snomed,
                completed_investigations=unsigned_invs,
                proposed_diagnosis_key="GASTROESOPHAGEAL_REFLUX"
            )
        self.assertIn("lacks mandatory clinician sign-off", str(ctx2.exception))

        # 3. All investigations are FINAL, signed, and quantitative -> Must be APPROVED
        valid_invs = [
            InvestigationResult(
                investigation_id="164868007",
                test_name="12-Lead ECG",
                status="FINAL",
                clinician_signed_off=True
            ),
            InvestigationResult(
                investigation_id="102685005",
                test_name="High-Sensitivity Troponin I",
                status="FINAL",
                numeric_value=0.008,
                reference_high=0.014,
                units="ng/mL",
                clinician_signed_off=True,
                signed_by="DR-SHARMA"
            ),
            InvestigationResult(
                investigation_id="274092004",
                test_name="Quantitative D-Dimer",
                status="FINAL",
                numeric_value=150.0,
                reference_high=500.0,
                units="ng/mL FEU",
                clinician_signed_off=True,
                signed_by="DR-SHARMA"
            )
        ]
        res = debiasing.verify_safe_discharge_or_benign_diagnosis(
            present_snomed_ids=present_snomed,
            completed_investigations=valid_invs,
            proposed_diagnosis_key="GASTROESOPHAGEAL_REFLUX"
        )
        self.assertEqual(res["status"], "APPROVED")

    def test_split_conformal_calibration(self):
        """
        Split-conformal calibration adjusts quantile threshold using empirical non-conformity scores.
        """
        conformal = ConformalPredictionEngine(significance_level_alpha=0.05)
        # Holdout nonconformity scores
        calibration_scores = [0.85, 0.88, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
        conformal.calibrate(calibration_scores)
        self.assertIsNotNone(conformal._calibrated_quantile)

        probs = {
            "DISEASE_A": 0.70,
            "DISEASE_B": 0.20,
            "DISEASE_C": 0.08,
            "DISEASE_D": 0.02
        }
        pred = conformal.generate_prediction_set(probs, experience_cases=500)
        self.assertIn("DISEASE_A", pred["prediction_set"])
        self.assertIn("DISEASE_B", pred["prediction_set"])
        self.assertGreaterEqual(pred["accumulated_probability_mass"], 0.90)

    def test_time_aware_parkland_burn_formula(self):
        """
        70kg adult with 30% TBSA presenting 3 hours after burn injury:
        Remaining first 8-hour window is 5.0 hours.
        First-half fluid (4200 mL) must be infused over remaining 5 hours at 840 mL/h (not 525 mL/h).
        """
        # Baseline: 0 hours elapsed
        plan_0h = calculate_parkland_burns_fluid(tbsa_percentage=30.0, patient_weight_kg=70.0, hours_since_burn=0.0)
        self.assertEqual(plan_0h.first_8h_rate_ml_per_hour, 525.0)
        self.assertEqual(plan_0h.remaining_first_window_hours, 8.0)
        self.assertEqual(plan_0h.adjusted_first_window_rate_ml_per_hour, 525.0)
        self.assertFalse(plan_0h.is_delayed_presentation)

        # 3 hours elapsed: 5 hours remaining
        plan_3h = calculate_parkland_burns_fluid(tbsa_percentage=30.0, patient_weight_kg=70.0, hours_since_burn=3.0)
        self.assertEqual(plan_3h.remaining_first_window_hours, 5.0)
        self.assertEqual(plan_3h.adjusted_first_window_rate_ml_per_hour, 840.0)
        self.assertTrue(any("ELAPSED BURN TIME ADJUSTMENT" in inst for inst in plan_3h.safety_instructions))

        # 9 hours elapsed: Delayed presentation
        plan_9h = calculate_parkland_burns_fluid(tbsa_percentage=30.0, patient_weight_kg=70.0, hours_since_burn=9.0)
        self.assertEqual(plan_9h.remaining_first_window_hours, 0.0)
        self.assertTrue(plan_9h.is_delayed_presentation)
        self.assertTrue(any("DELAYED PRESENTATION WARNING" in inst for inst in plan_9h.safety_instructions))

    def test_cryptographic_csb_model_promotion(self):
        """
        Shadow model promotion requires authentic HMAC-SHA256 CSB signed token.
        Arbitrary string or invalid token must be rejected.
        """
        engine = SBCCLExperienceEngine()

        # 1. Trivial string length attempt must be rejected
        with self.assertRaises(UnauthorizedPromotionError):
            engine.promote_shadow_model_to_production(
                baseline_test_suite_passed=True,
                csb_signed_authorization="RandomStringOver16CharsBypassAttempt!"
            )

        # 2. Authentic HMAC-SHA256 token must succeed
        token = create_csb_authorization_token(
            board_member_id="CSB-CHAIR-AIIMS-01",
            target_version=engine.shadow_version
        )
        res = engine.promote_shadow_model_to_production(
            baseline_test_suite_passed=True,
            csb_signed_authorization=token
        )
        self.assertEqual(res["status"], "PROMOTED_TO_PRODUCTION")
        self.assertEqual(res["active_version"], "v1.1.0-SHADOW-CALIBRATED")


if __name__ == "__main__":
    unittest.main()
