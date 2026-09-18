#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 24: CLINICAL SEMANTIC INTEGRITY & CONFORMAL MATH TEST SUITE
Module: tests/phase24/test_semantic_integrity_and_math.py
Validates:
  1. Pediatric emergency dosing weight integrity (strict rejection of zero/missing weights, zero silent defaults).
  2. Acute severe headache "Must-Not-Miss" syndrome (ruling out Subarachnoid Hemorrhage & Meningitis via structured investigations).
  3. Finite-sample split-conformal prediction mathematical calibration and marginal coverage guarantee.
  4. Cryptographic CSB authorization token validation (rejection of legacy strings under strict mode).
  5. CPOE teratogenic medication pregnancy safety hold (DRE-INSUFFICIENT-DATA) and clinical provenance integrity.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
import main
from clinical_emergency_scorers import (
    calculate_pediatric_emergency_doses,
    calculate_anaphylaxis_protocol
)
from diagnostic_graph_rag import (
    ClinicalConceptMapper,
    CognitiveDeBiasingMatrix,
    InvestigationResult,
    RedFlagRuleOutRequiredError
)
from sbccl_experience_engine import (
    SBCCLExperienceEngine,
    ConformalPredictionEngine,
    create_csb_authorization_token,
    verify_csb_authorization_token,
    UnauthorizedPromotionError
)
from auth_manager import auth_security_manager


class TestSemanticIntegrityAndMath(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)
        self.valid_token = auth_security_manager.create_access_token(
            username="dr_sharma",
            tenant_id="TENANT-MAIN-01",
            role="CONSULTANT_PHYSICIAN",
            permissions=["order_medications", "view_clinical_chart"]
        )
        self.auth_headers = {
            "Authorization": f"Bearer {self.valid_token}",
            "X-Tenant-ID": "TENANT-MAIN-01"
        }

    def test_pediatric_dosing_zero_silent_defaults(self):
        """Verify pediatric emergency dosing strictly rejects missing/zero/negative weight without age."""
        # 1. Neither weight nor age provided -> ValueError
        with self.assertRaises(ValueError) as ctx:
            calculate_pediatric_emergency_doses(weight_kg=None, age_years=None)
        self.assertIn("Mandatory pediatric clinical baseline required", str(ctx.exception))

        # 2. Zero weight -> ValueError
        with self.assertRaises(ValueError):
            calculate_pediatric_emergency_doses(weight_kg=0.0, age_years=None)

        # 3. Negative weight -> ValueError
        with self.assertRaises(ValueError):
            calculate_pediatric_emergency_doses(weight_kg=-4.5, age_years=None)

        # 4. Age provided without weight -> estimates weight from age: (5+4)*2 = 18.0
        calc = calculate_pediatric_emergency_doses(weight_kg=None, age_years=5.0)
        self.assertEqual(calc.weight_kg, 18.0)
        self.assertEqual(calc.age_years_estimated, 5.0)
        self.assertGreater(calc.paracetamol_single_dose_mg, 0.0)
        self.assertGreater(calc.ceftriaxone_meningitis_sepsis_mg, 0.0)

        # 5. Exact weight provided
        exact_calc = calculate_pediatric_emergency_doses(weight_kg=15.0, age_years=4.0)
        self.assertEqual(exact_calc.weight_kg, 15.0)
        self.assertEqual(exact_calc.age_years_estimated, 4.0)

    def test_anaphylaxis_protocol_weight_validation(self):
        """Verify anaphylaxis dosing rejects zero or negative weights."""
        with self.assertRaises(ValueError):
            calculate_anaphylaxis_protocol(weight_kg=0.0)

        with self.assertRaises(ValueError):
            calculate_anaphylaxis_protocol(weight_kg=-10.0)

        # Normal weights produce accurate dosing (18kg child is in 15-30kg bracket -> 0.3mg)
        peds_anaph = calculate_anaphylaxis_protocol(weight_kg=18.0, is_child=True)
        self.assertEqual(peds_anaph.im_adrenaline_dose_mg, 0.3)

        adult_anaph = calculate_anaphylaxis_protocol(weight_kg=70.0, is_child=False)
        self.assertEqual(adult_anaph.im_adrenaline_dose_mg, 0.5)

    def test_acute_severe_headache_rule_out_gate(self):
        """Verify Acute Severe Headache syndrome mandates CT/LP to rule out Subarachnoid Hemorrhage."""
        mapper = ClinicalConceptMapper()
        debiasing = CognitiveDeBiasingMatrix(mapper)
        headache_snomed = {"25064002"}  # Thunderclap headache trigger for ACUTE_SEVERE_HEADACHE

        # Attempt discharge without ruling out SAH -> must raise RedFlagRuleOutRequiredError
        with self.assertRaises(RedFlagRuleOutRequiredError) as ctx:
            debiasing.verify_safe_discharge_or_benign_diagnosis(
                present_snomed_ids=headache_snomed,
                completed_investigations=[],
                proposed_diagnosis_key="TENSION_HEADACHE",
                strict_validation=True
            )
        self.assertIn("Subarachnoid Hemorrhage", str(ctx.exception))

        # Attempt discharge with raw string IDs in strict mode -> rejected
        with self.assertRaises(RedFlagRuleOutRequiredError):
            debiasing.verify_safe_discharge_or_benign_diagnosis(
                present_snomed_ids=headache_snomed,
                completed_investigations=["168537006", "276575001"],
                proposed_diagnosis_key="TENSION_HEADACHE",
                strict_validation=True
            )

        # Provide structured, signed-off investigations ruling out SAH and Meningitis
        ct_result = InvestigationResult(
            investigation_id="168537006",
            test_name="Non-contrast CT Brain",
            status="FINAL",
            numeric_value=None,
            clinician_signed_off=True
        )
        lp_result = InvestigationResult(
            investigation_id="276575001",
            test_name="Lumbar Puncture CSF Analysis",
            status="FINAL",
            numeric_value=None,
            clinician_signed_off=True
        )

        verification = debiasing.verify_safe_discharge_or_benign_diagnosis(
            present_snomed_ids=headache_snomed,
            completed_investigations=[ct_result, lp_result],
            proposed_diagnosis_key="TENSION_HEADACHE",
            strict_validation=True
        )
        self.assertEqual(verification["status"], "APPROVED")
        self.assertEqual(verification["proposed_diagnosis"], "TENSION_HEADACHE")
        self.assertIn("Must-Not-Miss", verification["safety_advisory"])

    def test_finite_sample_conformal_prediction_calibration(self):
        """Verify conformal prediction applies finite sample correction and marginal coverage guarantee."""
        # Calibration with 100 non-conformity scores
        calibration_scores = [float(i) / 100.0 for i in range(100)]
        engine = ConformalPredictionEngine(significance_level_alpha=0.05)  # 95% nominal coverage
        engine.calibrate(calibration_scores)

        # Quantile index at level ceil((100+1)*0.95)/100 = 96/100 -> idx 95 -> score 0.95
        self.assertIsNotNone(engine._calibrated_quantile)
        self.assertAlmostEqual(engine._calibrated_quantile, 0.95, places=2)

        candidates = {
            "COMMUNITY_ACQUIRED_PNEUMONIA": 0.60,
            "VIRAL_BRONCHITIS": 0.35,
            "PULMONARY_EMBOLISM": 0.05
        }

        res = engine.generate_prediction_set(candidates, experience_cases=100)
        self.assertEqual(res["coverage_guarantee"], "95.0%")
        self.assertIn("COMMUNITY_ACQUIRED_PNEUMONIA", res["prediction_set"])
        self.assertIn("VIRAL_BRONCHITIS", res["prediction_set"])
        self.assertNotIn("PULMONARY_EMBOLISM", res["prediction_set"])
        self.assertEqual(res["prediction_set_size"], 2)

    def test_cryptographic_csb_authorization_token(self):
        """Verify legacy string tokens are rejected under strict mode and HMAC tokens are validated."""
        os.environ["STRICT_AUTH_REQUIRED"] = "true"
        try:
            # 1. Legacy string token must be rejected under strict mode
            is_valid_legacy = verify_csb_authorization_token(
                token_str="CSB-AUTH-TOKEN-2026-BOARD-CERTIFIED",
                target_version="v1.2.0-SHADOW-CALIBRATED"
            )
            self.assertFalse(is_valid_legacy)

            # 2. Authentic HMAC token must be validated
            valid_token = create_csb_authorization_token(
                board_member_id="AIIMS_CHAIR_MED_SUPERINTENDENT",
                target_version="v1.2.0-SHADOW-CALIBRATED"
            )
            self.assertTrue(verify_csb_authorization_token(
                token_str=valid_token,
                target_version="v1.2.0-SHADOW-CALIBRATED"
            ))

            # 3. Mismatched version fails verification
            self.assertFalse(verify_csb_authorization_token(
                token_str=valid_token,
                target_version="v9.9.9-UNAPPROVED"
            ))
        finally:
            os.environ.pop("STRICT_AUTH_REQUIRED", None)

    def test_cpoe_teratogenic_pregnancy_safety_gate(self):
        """Verify female of childbearing age without pregnancy status gets safety hold on teratogenic drug."""
        # Prescribe isotretinoin to female patient aged 24 with pregnancy status omitted
        teratogenic_order = {
            "patient_id": "PAT-FEMALE-24",
            "clinician_id": "DR-SHARMA-01",
            "order_type": "MEDICATION",
            "items": [{"code": "ISO-001", "name": "isotretinoin", "dose": "20mg", "route": "ORAL"}],
            "patient_age": 24,
            "is_female": True,
            "patient_weight_kg": 55.0,
            "serum_creatinine": 0.8
            # is_pregnant omitted
        }

        response = self.client.post(
            "/api/v1/safety/evaluate-order",
            json=teratogenic_order,
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "INSUFFICIENT_DATA_HOLD")
        self.assertTrue(any(hs["rule_id"] == "DRE-INSUFFICIENT-DATA" for hs in data["hard_stops"]))
        self.assertIn("Teratogenic medication 'isotretinoin'", data["hard_stops"][0]["message"])
        self.assertIn("data_quality", data)


if __name__ == "__main__":
    unittest.main()
