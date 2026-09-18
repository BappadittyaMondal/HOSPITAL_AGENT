#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 26: ADAPTIVE SEQUENTIAL ELICITATION, PARTIAL-INTAKE FALLBACK & SOCKET HEALTH
Module: tests/phase26/test_sequential_elicitation_and_sockets.py
Validates:
  1. Cutaneous & Pigmentary archetype (Addison's vs B12 vs Arsenicosis discrimination).
  2. Interactive sequential turn-by-turn question generation.
  3. Graceful partial-intake fallback when patient drops off or disconnects (unexcluded red flags & conservative differential).
  4. PediatricEmergencyDoses self-describing weight_provenance (MEASURED vs APLS_AGE_ESTIMATED).
  5. Enhanced dynamic /ready probe including database ledger connectivity.
  6. Standardized HTTP 422 unprocessable content status without deprecation warnings.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
import main
from structured_history_engine import (
    StructuredHistoryEngine,
    ChiefComplaintCategory,
    FindingPolarity
)
from clinical_emergency_scorers import calculate_pediatric_emergency_doses
from auth_manager import auth_security_manager


class TestSequentialElicitationAndSockets(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)
        self.engine = StructuredHistoryEngine()
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

    def test_dermatologic_archetype_addisons_vs_b12_vs_arsenic(self):
        """Verify cutaneous archetype distinguishes Addison's, B12 deficiency, and Arsenicosis."""
        # 1. Addison's presentation: Palmar creases + orthostatic dizziness + mucosal hyperpigmentation
        sess1 = self.engine.initiate_session(
            session_id="SESS-DERM-01",
            patient_id="PAT-45M-01",
            chief_complaint=ChiefComplaintCategory.DERMATOLOGIC_PIGMENTARY_OR_RASH,
            patient_age=45,
            is_female=False
        )
        self.engine.process_responses(sess1, {
            "palmar_crease_darkening": True,
            "orthostatic_dizziness": True,
            "buccal_mucosa_darkening": True
        })
        self.assertIn("SUSPECTED_ADDISONS_ADRENAL_INSUFFICIENCY_CRISIS_RISK", sess1.active_red_flags)
        actions1 = " ".join(sess1.recommended_immediate_actions)
        self.assertIn("Serum Electrolytes", actions1)
        self.assertIn("Cortisol and Plasma ACTH", actions1)
        self.assertIn("Adrenal Tuberculosis", actions1)

        # 2. Vitamin B12 deficiency: Palmar creases + peripheral paresthesia
        sess2 = self.engine.initiate_session(
            session_id="SESS-DERM-02",
            patient_id="PAT-45M-02",
            chief_complaint=ChiefComplaintCategory.DERMATOLOGIC_PIGMENTARY_OR_RASH,
            patient_age=45,
            is_female=False
        )
        self.engine.process_responses(sess2, {
            "palmar_crease_darkening": True,
            "peripheral_tingling_numbness": True
        })
        self.assertIn("SUSPECTED_VITAMIN_B12_DEFICIENCY_NEUROPATHY", sess2.active_red_flags)
        actions2 = " ".join(sess2.recommended_immediate_actions)
        self.assertIn("Serum Vitamin B12", actions2)
        self.assertIn("NEVER administer Folic Acid alone", actions2)

        # 3. Arsenicosis: Palmar creases + untreated tube-well water
        sess3 = self.engine.initiate_session(
            session_id="SESS-DERM-03",
            patient_id="PAT-45M-03",
            chief_complaint=ChiefComplaintCategory.DERMATOLOGIC_PIGMENTARY_OR_RASH,
            patient_age=45,
            is_female=False
        )
        self.engine.process_responses(sess3, {
            "palmar_crease_darkening": True,
            "tube_well_drinking_water": True
        })
        self.assertIn("SUSPECTED_CHRONIC_ARSENICOSIS_MELANOSIS", sess3.active_red_flags)
        actions3 = " ".join(sess3.recommended_immediate_actions)
        self.assertIn("Arsenic", actions3)

    def test_sequential_interactive_intake_flow(self):
        """Verify turn-by-turn question generation advances through the clinical decision tree."""
        # Start sequential session
        start_res = self.client.post(
            "/api/v1/triage/history/sequential/start",
            json={
                "session_id": "SESS-SEQ-01",
                "patient_id": "PAT-45M-SEQ",
                "chief_complaint": "DERMATOLOGIC_PIGMENTARY_OR_RASH",
                "patient_age": 45,
                "is_female": False
            },
            headers=self.auth_headers
        )
        self.assertEqual(start_res.status_code, 200)
        data = start_res.json()
        self.assertEqual(data["intake_status"], "IN_PROGRESS")
        self.assertEqual(data["current_turn"], 1)
        self.assertEqual(data["pending_question"]["question_id"], "Q_PALMAR_CREASES")

        # Turn 1: Palmar creases = YES
        t1_res = self.client.post(
            "/api/v1/triage/history/sequential/turn",
            json={
                "session_id": "SESS-SEQ-01",
                "question_id": "Q_PALMAR_CREASES",
                "answer_value": "YES"
            },
            headers=self.auth_headers
        )
        self.assertEqual(t1_res.status_code, 200)
        t1_data = t1_res.json()
        self.assertEqual(t1_data["current_turn"], 1)
        self.assertEqual(t1_data["intake_status"], "IN_PROGRESS")
        self.assertEqual(t1_data["next_question"]["question_id"], "Q_BUCCAL_MUCOSA")

        # Turn 2: Buccal mucosa = NO
        t2_res = self.client.post(
            "/api/v1/triage/history/sequential/turn",
            json={
                "session_id": "SESS-SEQ-01",
                "question_id": "Q_BUCCAL_MUCOSA",
                "answer_value": "NO"
            },
            headers=self.auth_headers
        )
        self.assertEqual(t2_res.status_code, 200)
        self.assertEqual(t2_res.json()["next_question"]["question_id"], "Q_ORTHOSTATIC_DIZZINESS")

    def test_partial_intake_fallback_patient_drop_off(self):
        """Verify when patient drops off, fallback generates conservative differential & safety net."""
        # Start session
        self.client.post(
            "/api/v1/triage/history/sequential/start",
            json={
                "session_id": "SESS-DROPOFF-01",
                "patient_id": "PAT-DROPOFF",
                "chief_complaint": "DERMATOLOGIC_PIGMENTARY_OR_RASH",
                "patient_age": 45,
                "is_female": False
            },
            headers=self.auth_headers
        )

        # Answer only Turn 1 (palmar creases), then simulate patient disconnection
        self.client.post(
            "/api/v1/triage/history/sequential/turn",
            json={
                "session_id": "SESS-DROPOFF-01",
                "question_id": "Q_PALMAR_CREASES",
                "answer_value": "YES"
            },
            headers=self.auth_headers
        )

        # Trigger partial fallback
        fb_res = self.client.post(
            "/api/v1/triage/history/sequential/partial-fallback",
            json={"session_id": "SESS-DROPOFF-01"},
            headers=self.auth_headers
        )
        self.assertEqual(fb_res.status_code, 200)
        fb_data = fb_res.json()

        self.assertEqual(fb_data["intake_status"], "PARTIAL_FALLBACK")
        self.assertEqual(fb_data["data_quality"], "INCOMPLETE_INTAKE_FALLBACK")
        self.assertEqual(fb_data["turns_completed"], 1)

        # Verify unexcluded red flags
        unexcluded = fb_data["unexcluded_must_not_miss"]
        self.assertIn("PRIMARY_ADRENAL_INSUFFICIENCY_ADDISONS_CRISIS", unexcluded)
        self.assertIn("VITAMIN_B12_DEFICIENCY_NEUROPATHY", unexcluded)

        # Verify ranked provisional differential
        diff = fb_data["partial_differential"]
        diff_conditions = [d["condition"] for d in diff]
        self.assertTrue(any("Addison" in c for c in diff_conditions))
        self.assertTrue(any("Vitamin B12" in c for c in diff_conditions))

        # Verify safety net instructions
        actions_str = " ".join(fb_data["recommended_immediate_actions"])
        self.assertIn("PARTIAL CLINICAL INTAKE WARNING", actions_str)
        self.assertIn("EMERGENCY ROOM IMMEDIATELY", actions_str)

    def test_pediatric_emergency_doses_weight_provenance(self):
        """Verify PediatricEmergencyDoses self-describes weight provenance correctly."""
        # Estimated via age formula: (5+4)*2 = 18kg
        est_doses = calculate_pediatric_emergency_doses(age_years=5.0)
        self.assertEqual(est_doses.weight_kg, 18.0)
        self.assertEqual(est_doses.weight_provenance, "APLS_AGE_ESTIMATED")

        # Measured weight: 14kg
        meas_doses = calculate_pediatric_emergency_doses(weight_kg=14.0, age_years=3.5)
        self.assertEqual(meas_doses.weight_kg, 14.0)
        self.assertEqual(meas_doses.weight_provenance, "MEASURED")

    def test_readiness_probe_database_ledger(self):
        """Verify /ready probe actively checks database ledger readiness."""
        res = self.client.get("/ready")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ready"])
        self.assertEqual(data["subsystems"]["database_ledger"], "HEALTHY")
        self.assertEqual(data["subsystems"]["dre_engine"], "HEALTHY")
        self.assertEqual(data["subsystems"]["blood_bank"], "HEALTHY")

    def test_starlette_deprecation_free_dose_parser_422(self):
        """Verify malformed dose produces 422 without Starlette deprecation warnings."""
        res = self.client.post(
            "/api/v1/safety/evaluate-order",
            json={
                "patient_id": "PAT-422",
                "clinician_id": "DR-01",
                "items": [{"code": "PCM", "name": "Paracetamol", "dose": "banana"}]
            },
            headers=self.auth_headers
        )
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["detail"]["status"], "INVALID_DOSE_FORMAT")


if __name__ == "__main__":
    unittest.main()
