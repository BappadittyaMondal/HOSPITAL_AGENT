#!/usr/bin/env python3
"""
Phase 37 Test Suite: P0 Zero-Trust Security, DRE Fail-Closed Safety Gate & Allergy Invariance.
Validates:
1. DRE Fail-Closed Invariant (C-01): Internal exceptions result in hard BLOCKED state.
2. Symmetrical PDE5i + Nitrate blocking for Tadalafil / Isosorbide (C-02).
3. Semantic Allergy Invariance for PCN / Amoxycillin / Augmentin / NSAIDs (C-04).
4. Zero-Trust Auth Guard (S-01): Missing token under strict auth returns HTTP 401.
5. Production credential sanitization (S-02).
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add services/core-api to path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from cpoe_dre_engine import CPOEDREEngine
from auth_manager import AuthSecurityManager
import main
from fastapi.testclient import TestClient


class TestPhase37P0SecurityAndFailClosed(unittest.TestCase):

    def setUp(self):
        self.dre = CPOEDREEngine(tenant_id="TENANT-P37-TEST")
        self.auth_mgr = AuthSecurityManager(jwt_secret="phase37-test-secret-key-32chars-min!!")

    def test_pde5i_nitrate_bidirectional_symmetry(self):
        """Tadalafil prescribed with active Isosorbide Mononitrate must be blocked symmetrically."""
        # Tadalafil -> Nitrates
        res1 = self.dre.evaluate_order(
            patient_id="PT-DDI-01",
            drug_name="Tadalafil 20mg",
            prescribed_dose=20.0,
            route="ORAL",
            patient_weight_kg=72.0,
            patient_bsa_m2=1.8,
            serum_creatinine=1.0,
            patient_age=55,
            is_female=False,
            current_medications=["Isosorbide Mononitrate 30mg SR"],
            known_allergies=[]
        )
        self.assertEqual(res1["status"], "BLOCKED")
        self.assertTrue(any("PDE5" in hs or "Nitrate" in hs for hs in res1["hard_stops"]))

        # Nitrates -> Tadalafil
        res2 = self.dre.evaluate_order(
            patient_id="PT-DDI-02",
            drug_name="Isosorbide Dinitrate 10mg",
            prescribed_dose=10.0,
            route="SUBLINGUAL",
            patient_weight_kg=72.0,
            patient_bsa_m2=1.8,
            serum_creatinine=1.0,
            patient_age=55,
            is_female=False,
            current_medications=["Tadalafil 20mg"],
            known_allergies=[]
        )
        self.assertEqual(res2["status"], "BLOCKED")
        self.assertTrue(any("PDE5" in hs or "Nitrate" in hs for hs in res2["hard_stops"]))

    def test_semantic_allergy_invariance_pcn_and_amoxycillin(self):
        """Allergy documented as 'PCN' must block British/Indian spelling 'Amoxycillin' and 'Augmentin'."""
        # 1. PCN allergy -> Amoxycillin
        res1 = self.dre.evaluate_order(
            patient_id="PT-ALLERGY-01",
            drug_name="Amoxycillin 500mg",
            prescribed_dose=500.0,
            route="ORAL",
            patient_weight_kg=65.0,
            patient_bsa_m2=1.7,
            serum_creatinine=0.9,
            patient_age=40,
            is_female=False,
            current_medications=[],
            known_allergies=["PCN"]
        )
        self.assertEqual(res1["status"], "BLOCKED")
        self.assertTrue(any("LETHAL ALLERGY" in hs and ("penicillin" in hs.lower() or "beta-lactam" in hs.lower()) for hs in res1["hard_stops"]))

        # 2. Penicillin allergy -> Augmentin
        res2 = self.dre.evaluate_order(
            patient_id="PT-ALLERGY-02",
            drug_name="Augmentin 625mg",
            prescribed_dose=625.0,
            route="ORAL",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.8,
            serum_creatinine=1.0,
            patient_age=45,
            is_female=True,
            current_medications=[],
            known_allergies=["penicillin"]
        )
        self.assertEqual(res2["status"], "BLOCKED")
        self.assertTrue(any("LETHAL ALLERGY" in hs and ("penicillin" in hs.lower() or "beta-lactam" in hs.lower()) for hs in res2["hard_stops"]))

    def test_semantic_allergy_invariance_nsaid_cross_reactivity(self):
        """Documented allergy to 'NSAIDs' or 'Aspirin' must block Ibuprofen/Diclofenac."""
        res = self.dre.evaluate_order(
            patient_id="PT-ALLERGY-03",
            drug_name="Diclofenac 50mg",
            prescribed_dose=50.0,
            route="ORAL",
            patient_weight_kg=60.0,
            patient_bsa_m2=1.65,
            serum_creatinine=0.8,
            patient_age=35,
            is_female=True,
            current_medications=[],
            known_allergies=["NSAID allergy"]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("NSAID" in hs for hs in res["hard_stops"]))

    def test_dre_fail_closed_on_screening_exception(self):
        """If the underlying formulary screening engine encounters an unhandled exception, order is BLOCKED."""
        with patch("cpoe_dre_engine.global_nlem_formulary_engine") as mock_engine:
            mock_engine.screen_prescription_regimen.side_effect = RuntimeError("Simulated critical DB failure")
            res = self.dre.evaluate_order(
                patient_id="PT-ERR-01",
                drug_name="Atorvastatin 20mg",
                prescribed_dose=20.0,
                route="ORAL",
                patient_weight_kg=70.0,
                patient_bsa_m2=1.75,
                serum_creatinine=1.0,
                patient_age=50,
                is_female=False,
                current_medications=[],
                known_allergies=[]
            )
            self.assertEqual(res["status"], "BLOCKED")
            self.assertTrue(any("DRE_FAIL_CLOSED_HALT" in hs for hs in res["hard_stops"]))

    def test_zero_trust_strict_auth_rejection(self):
        """When STRICT_AUTH_REQUIRED is enabled, unauthenticated requests are strictly rejected with 401."""
        client = TestClient(main.app)
        with patch.dict(os.environ, {"STRICT_AUTH_REQUIRED": "true"}):
            res = client.post(
                "/api/v1/safety/evaluate-order",
                json={
                    "patient_id": "PT-AUTH-01",
                    "drug_name": "Paracetamol 500mg",
                    "prescribed_dose": 500.0,
                    "route": "ORAL",
                    "patient_weight_kg": 70.0,
                    "patient_bsa_m2": 1.73,
                    "serum_creatinine": 1.0,
                    "patient_age": 30,
                    "is_female": False,
                    "current_medications": [],
                    "known_allergies": []
                }
            )
            self.assertEqual(res.status_code, 401)
            self.assertIn("Missing mandatory Authorization", res.json()["detail"]["error"])

    def test_production_credential_sanitization(self):
        """In production environment, default hardcoded user accounts must not be seeded without explicit env."""
        with patch.dict(os.environ, {"HOSPITAL_ENV": "production"}):
            # If no prod password provided, dr_sharma is not seeded
            prod_auth = AuthSecurityManager(jwt_secret="prod-super-secure-secret-key-32chars!!")
            self.assertIsNone(prod_auth.verify_credentials("dr_sharma", "DoctorSecurePass@2026!"))
            self.assertIsNone(prod_auth.verify_credentials("test_user", "pwd"))


if __name__ == "__main__":
    unittest.main()
