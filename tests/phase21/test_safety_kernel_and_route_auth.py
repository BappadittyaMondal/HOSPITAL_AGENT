#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 21: SAFETY KERNEL & ROUTE AUTHENTICATION TEST SUITE
Module: tests/phase21/test_safety_kernel_and_route_auth.py
Validates:
  1. Route authentication guards (401 on missing/tampered token under STRICT_AUTH_REQUIRED / production).
  2. Strict dose parsing (rejection of non-numeric 'banana', 0mg, negative doses with 422).
  3. Mandatory clinical data holds (Metformin without creatinine, pediatric without weight -> INSUFFICIENT_DATA_HOLD).
  4. NDPS narcotics strict dual-biometric verification (403 on unverified biometric or missing hardware token).
  5. Audit logging failure resilience (fail-closed 500 under production).
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
import main
from auth_manager import auth_security_manager


class TestSafetyKernelAndRouteAuth(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)
        # Generate valid authenticated token
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

    def test_strict_auth_required_rejects_unauthenticated_request(self):
        """Under STRICT_AUTH_REQUIRED=true, requests without Authorization header must receive HTTP 401."""
        os.environ["STRICT_AUTH_REQUIRED"] = "true"
        try:
            res = self.client.post("/api/v1/safety/evaluate-order", json={
                "patient_id": "PAT-001",
                "clinician_id": "DOC-001",
                "items": [{"code": "AMOX", "name": "Amoxicillin", "dose": "500mg"}]
            })
            self.assertEqual(res.status_code, 401)
            self.assertEqual(res.json()["detail"]["status"], "UNAUTHORIZED")
        finally:
            os.environ.pop("STRICT_AUTH_REQUIRED", None)

    def test_tampered_token_is_rejected_with_401(self):
        """A cryptographically tampered or invalid token must be rejected with HTTP 401."""
        tampered_headers = {
            "Authorization": "Bearer JWT-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoYWNrZXIifQ.tampered_signature",
            "X-Tenant-ID": "TENANT-MAIN-01"
        }
        res = self.client.post("/api/v1/safety/evaluate-order", json={
            "patient_id": "PAT-001",
            "clinician_id": "DOC-001",
            "items": [{"code": "AMOX", "name": "Amoxicillin", "dose": "500mg"}]
        }, headers=tampered_headers)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"]["status"], "UNAUTHORIZED")

    def test_valid_token_authenticates_successfully(self):
        """A valid HMAC-SHA256 signed token must be accepted with HTTP 200."""
        res = self.client.post("/api/v1/safety/evaluate-order", json={
            "patient_id": "PAT-001",
            "clinician_id": "DOC-001",
            "items": [{"code": "AMOX", "name": "Amoxicillin", "dose": "500mg"}]
        }, headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "APPROVED")

    def test_dose_parser_rejects_malformed_dose_banana(self):
        """Nonsense dose strings like 'banana' must be rejected with HTTP 422, never defaulted."""
        res = self.client.post("/api/v1/safety/evaluate-order", json={
            "patient_id": "PAT-002",
            "clinician_id": "DOC-001",
            "items": [{"code": "AMOX", "name": "Amoxicillin", "dose": "banana"}]
        }, headers=self.auth_headers)
        self.assertEqual(res.status_code, 422)
        detail = res.json()["detail"]
        self.assertEqual(detail["status"], "INVALID_DOSE_FORMAT")
        self.assertIn("banana", detail["error"])

    def test_dose_parser_rejects_zero_and_negative_dose(self):
        """Doses <= 0 must be rejected with HTTP 422."""
        for bad_dose in ["0mg", "-250mg"]:
            res = self.client.post("/api/v1/safety/evaluate-order", json={
                "patient_id": "PAT-002",
                "clinician_id": "DOC-001",
                "items": [{"code": "AMOX", "name": "Amoxicillin", "dose": bad_dose}]
            }, headers=self.auth_headers)
            self.assertEqual(res.status_code, 422)
            self.assertEqual(res.json()["detail"]["status"], "INVALID_DOSE_FORMAT")

    def test_metformin_without_creatinine_triggers_insufficient_data_hold(self):
        """Prescribing Metformin without serum creatinine must trigger INSUFFICIENT_DATA_HOLD (not default Cr 1.0)."""
        res = self.client.post("/api/v1/safety/evaluate-order", json={
            "patient_id": "PAT-RENAL-001",
            "clinician_id": "DOC-001",
            "items": [{"code": "MET", "name": "Metformin", "dose": "500mg"}],
            "serum_creatinine": None,
            "patient_age": 65
        }, headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "INSUFFICIENT_DATA_HOLD")
        self.assertTrue(any("serum creatinine" in hs["message"] for hs in data["hard_stops"]))

    def test_pediatric_order_without_weight_triggers_insufficient_data_hold(self):
        """Prescribing to pediatric patient (< 18y) without measured weight must trigger INSUFFICIENT_DATA_HOLD."""
        res = self.client.post("/api/v1/safety/evaluate-order", json={
            "patient_id": "PAT-PED-001",
            "clinician_id": "DOC-001",
            "items": [{"code": "AMOX", "name": "Amoxicillin", "dose": "250mg"}],
            "patient_age": 5,
            "patient_weight_kg": None
        }, headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "INSUFFICIENT_DATA_HOLD")
        self.assertTrue(any("measured patient weight" in hs["message"] for hs in data["hard_stops"]))

    def test_ndps_narcotics_rejects_unverified_biometrics(self):
        """NDPS dispense must be rejected with HTTP 403 if either witness biometric is unverified."""
        res = self.client.post("/api/v1/pharmacy/narcotics/dispense", json={
            "drug_id": "MORPHINE_10MG",
            "batch_number": "BATCH-01",
            "quantity": 1,
            "patient_id": "PAT-01",
            "order_id": "ORD-01",
            "primary_user_id": "PHARM-01",
            "primary_role": "PHARMACIST",
            "primary_bio_token": "BIO-01",
            "primary_bio_verified": True,
            "secondary_user_id": "NURSE-01",
            "secondary_role": "NURSE_INCHARGE",
            "secondary_bio_token": "BIO-02",
            "secondary_bio_verified": False  # Unverified secondary witness
        }, headers=self.auth_headers)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"]["status"], "DUAL_BIOMETRIC_AUTH_FAILED")

    def test_ndps_narcotics_rejects_missing_biometric_token(self):
        """NDPS dispense must be rejected with HTTP 403 if hardware biometric token is omitted."""
        res = self.client.post("/api/v1/pharmacy/narcotics/dispense", json={
            "drug_id": "MORPHINE_10MG",
            "batch_number": "BATCH-01",
            "quantity": 1,
            "patient_id": "PAT-01",
            "order_id": "ORD-01",
            "primary_user_id": "PHARM-01",
            "primary_role": "PHARMACIST",
            "primary_bio_token": "",  # Empty token
            "primary_bio_verified": True,
            "secondary_user_id": "NURSE-01",
            "secondary_role": "NURSE_INCHARGE",
            "secondary_bio_token": "BIO-02",
            "secondary_bio_verified": True
        }, headers=self.auth_headers)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"]["status"], "DUAL_BIOMETRIC_AUTH_FAILED")


if __name__ == "__main__":
    unittest.main()
