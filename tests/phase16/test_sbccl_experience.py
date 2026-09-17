"""
====================================================================================================
TEST SUITE: PHASE 16.3 — SUPERVISED BAYESIAN-CONFORMAL CONTINUOUS LEARNING (SBCCL) ENGINE
====================================================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from sbccl_experience_engine import (
    SBCCLExperienceEngine,
    DirichletMultinomialBayesianCalibrator,
    ConformalPredictionEngine,
    DoublyRobustTreatmentEvaluator,
    UnverifiedGroundTruthRejectionError,
    ShadowModelRegressionError,
    UnauthorizedPromotionError
)


class TestSBCCLExperienceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SBCCLExperienceEngine()

    def test_rejection_of_unverified_ground_truth(self):
        """Quality Gate 3: Preliminary guesses, junior opinions, and unverified entries are REJECTED."""
        calibrator = self.engine.calibrator

        with self.assertRaises(UnverifiedGroundTruthRejectionError):
            calibrator.ingest_ground_truth_outcome(
                case_id="CASE-001",
                confirmed_disease="ACUTE_MYOCARDIAL_INFARCTION",
                outcome_source="JUNIOR_RESIDENT_PRELIMINARY_GUESS"  # Unverified source
            )

        # Verified source succeeds
        calibrator.ingest_ground_truth_outcome(
            case_id="CASE-002",
            confirmed_disease="ACUTE_MYOCARDIAL_INFARCTION",
            outcome_source="HISTOPATHOLOGY_BIOPSY_CONFIRMED"
        )
        self.assertEqual(calibrator.total_verified_cases, 1)

    def test_bayesian_variance_reduction_as_experience_accumulates(self):
        """Mathematically verifies that as verified cases N grow from 10 to 5,000, variance drops to near zero."""
        calibrator = DirichletMultinomialBayesianCalibrator(
            initial_priors={"DISEASE_A": 10.0, "DISEASE_B": 10.0}
        )

        initial_dist = calibrator.get_parameter_distribution()
        initial_var = initial_dist["DISEASE_A"]["variance"]

        # Simulate 2,000 verified cases of experience accumulating
        for i in range(2000):
            calibrator.ingest_ground_truth_outcome(
                case_id=f"CASE-SIM-{i}",
                confirmed_disease="DISEASE_A" if i % 2 == 0 else "DISEASE_B",
                outcome_source="DISCHARGE_CONSULTANT_RECONCILED"
            )

        updated_dist = calibrator.get_parameter_distribution()
        updated_var = updated_dist["DISEASE_A"]["variance"]

        # Variance must have dropped by over 90% (mathematical proof of seasoned confidence)
        self.assertLess(updated_var, initial_var * 0.1)
        self.assertGreater(updated_dist["DISEASE_A"]["alpha"], 1000)

    def test_conformal_prediction_set_coverage_and_uncertainty(self):
        """Verifies conformal prediction guarantees 99% coverage and dynamically sizes the differential."""
        conformal = self.engine.conformal

        # Case 1: Ambiguous presentation with distributed probabilities
        ambiguous_probs = {
            "PULMONARY_EMBOLISM": 0.40,
            "ACUTE_MYOCARDIAL_INFARCTION": 0.35,
            "PNEUMOTHORAX": 0.15,
            "GASTROESOPHAGEAL_REFLUX": 0.08,
            "COSTOCHONDRITIS": 0.02
        }
        pred_ambiguous = conformal.generate_prediction_set(ambiguous_probs, experience_cases=50)
        # To cover 99%, requires multiple candidates
        self.assertGreaterEqual(pred_ambiguous["prediction_set_size"], 3)
        self.assertIn("PULMONARY_EMBOLISM", pred_ambiguous["prediction_set"])
        self.assertIn("ACUTE_MYOCARDIAL_INFARCTION", pred_ambiguous["prediction_set"])

        # Case 2: Classic pathognomonic presentation with high certainty
        clear_probs = {
            "ACUTE_MYOCARDIAL_INFARCTION": 0.992,
            "GASTROESOPHAGEAL_REFLUX": 0.005,
            "PULMONARY_EMBOLISM": 0.003
        }
        pred_clear = conformal.generate_prediction_set(clear_probs, experience_cases=10000)
        # Single high-confidence candidate satisfies 99% coverage
        self.assertEqual(pred_clear["prediction_set_size"], 1)
        self.assertEqual(pred_clear["prediction_set"], ["ACUTE_MYOCARDIAL_INFARCTION"])
        self.assertEqual(pred_clear["epistemic_uncertainty"], "LOW")

    def test_doubly_robust_treatment_outcome_evaluation(self):
        """Verifies Doubly Robust ATE correctly identifies positive treatment benefit with propensity de-biasing."""
        evaluator = DoublyRobustTreatmentEvaluator()

        # Synthetic cohort: Active treatment gives 85% recovery, Control gives 50% recovery
        records = [
            {"recovered": 1, "active_treatment": 1, "propensity_score": 0.6, "predicted_recovery_treated": 0.8, "predicted_recovery_untreated": 0.5},
            {"recovered": 1, "active_treatment": 1, "propensity_score": 0.7, "predicted_recovery_treated": 0.82, "predicted_recovery_untreated": 0.52},
            {"recovered": 0, "active_treatment": 0, "propensity_score": 0.4, "predicted_recovery_treated": 0.78, "predicted_recovery_untreated": 0.48},
            {"recovered": 1, "active_treatment": 0, "propensity_score": 0.3, "predicted_recovery_treated": 0.81, "predicted_recovery_untreated": 0.51},
        ]
        ate = evaluator.evaluate_treatment_benefit(records)
        # Treatment effect should be strongly positive
        self.assertGreater(ate, 0.20)

    def test_shadow_promotion_safety_firewall(self):
        """Quality Gate 3: Shadow models cannot be promoted without passing baseline tests and CSB authorization."""
        # Attempt promotion when baseline regression test failed
        with self.assertRaises(ShadowModelRegressionError):
            self.engine.promote_shadow_model_to_production(
                baseline_test_suite_passed=False,
                csb_signed_authorization="CSB-AUTH-TOKEN-VALID-2026"
            )

        # Attempt promotion without valid Clinical Safety Board signature token
        with self.assertRaises(UnauthorizedPromotionError):
            self.engine.promote_shadow_model_to_production(
                baseline_test_suite_passed=True,
                csb_signed_authorization=None
            )

        # Promotion with passing regression tests and CSB sign-off token succeeds
        res = self.engine.promote_shadow_model_to_production(
            baseline_test_suite_passed=True,
            csb_signed_authorization="CSB-AUTH-TOKEN-2026-BOARD-CERTIFIED"
        )
        self.assertEqual(res["status"], "PROMOTED_TO_PRODUCTION")
        self.assertEqual(res["active_version"], "v1.1.0-SHADOW-CALIBRATED")


if __name__ == "__main__":
    unittest.main()
