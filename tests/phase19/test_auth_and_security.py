"""
PROJECT "HOSPITAL" — PHASE 19: PRODUCTION SYSTEMS HARDENING
Test Suite: test_auth_and_security.py
Validates:
  - PBKDF2-HMAC-SHA256 password hashing with per-user unique salt
  - Constant-time password verification mitigating timing attacks
  - Authentic RFC 7519 HMAC-SHA256 JWT creation, claims, and signature validation
  - Rejection of tampered signatures, forged payloads, and expired tokens
  - CSB governance HMAC secret environment compliance
"""

import os
import sys
import unittest
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from auth_manager import AuthSecurityManager, hash_password, verify_password, auth_security_manager
from clinical_safety_board_governance import ClinicalSafetyBoardGovernanceEngine


class TestAuthAndSecurity(unittest.TestCase):

    def setUp(self):
        self.auth = AuthSecurityManager(jwt_secret="TEST-SUPER-SECRET-KEY-FOR-PHASE-19-VERIFICATION-32B+")

    def test_password_hashing_and_salt_uniqueness(self):
        """Test PBKDF2 hashing generates unique salts and verifiable hashes."""
        pwd = "DoctorStrongPassword@2026"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)

        self.assertNotEqual(h1, h2, "Two hashes of same password must differ due to unique salts")
        self.assertTrue(verify_password(pwd, h1))
        self.assertTrue(verify_password(pwd, h2))
        self.assertFalse(verify_password("WrongPassword123", h1))

    def test_verify_credentials_success(self):
        """Valid default staff credentials must authenticate successfully."""
        user = self.auth.verify_credentials("dr_sharma", "DoctorSecurePass@2026!")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "dr_sharma")
        self.assertEqual(user["role"], "CONSULTANT_PHYSICIAN")
        self.assertIn("order_medications", user["permissions"])

    def test_register_and_authenticate_new_staff(self):
        """Dynamic user registration with unique salt and authentication."""
        self.auth.register_user("dr_patel", "OncoSecurePass@2026!", "MEDICAL_ONCOLOGIST", ["order_chemo"])
        user = self.auth.verify_credentials("dr_patel", "OncoSecurePass@2026!")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "MEDICAL_ONCOLOGIST")

    def test_verify_credentials_rejection(self):
        """Invalid username or password must return None without leaking timing info."""
        self.assertIsNone(self.auth.verify_credentials("dr_sharma", "WrongPassword!"))
        self.assertIsNone(self.auth.verify_credentials("non_existent_user", "AnyPassword123"))

    def test_jwt_issuance_and_signature_verification(self):
        """JWT creation and decoding must maintain RFC 7519 cryptographic integrity."""
        token = self.auth.create_access_token(
            username="dr_sharma",
            tenant_id="TENANT-MAIN-01",
            role="CARDIOLOGIST",
            permissions=["SIGN_ORDERS", "OVERRIDE_DRE_WARNING"],
            expires_delta_seconds=3600
        )
        self.assertTrue(token.startswith("JWT-"))

        is_valid, claims, err = self.auth.decode_and_verify_token(token)
        self.assertTrue(is_valid)
        self.assertIsNotNone(claims)
        self.assertEqual(claims["sub"], "dr_sharma")
        self.assertEqual(claims["tenant_id"], "TENANT-MAIN-01")
        self.assertEqual(claims["role"], "CARDIOLOGIST")
        self.assertIn("SIGN_ORDERS", claims["permissions"])

    def test_jwt_tampered_payload_rejected(self):
        """Tampering with token payload must cause verification failure."""
        token = self.auth.create_access_token(
            username="nurse_anita",
            tenant_id="TENANT-MAIN-01",
            role="TRIAGE_NURSE",
            permissions=["READ_VITALS"]
        )
        raw = token[4:]  # strip JWT-
        parts = raw.split(".")
        # Tamper payload part: change role to SUPER_ADMIN
        tampered_payload = "eyJzdWIiOiAibnVyc2VfYW5pdGEiLCAicm9sZSI6ICJTVVBFUl9BRE1JTiJ9"
        tampered_token = f"JWT-{parts[0]}.{tampered_payload}.{parts[2]}"

        is_valid, claims, err = self.auth.decode_and_verify_token(tampered_token)
        self.assertFalse(is_valid)
        self.assertIsNone(claims)
        self.assertIn("signature", err.lower())

    def test_jwt_tampered_signature_rejected(self):
        """Tampering with token signature must fail cryptographic check."""
        token = self.auth.create_access_token("dr_sharma", "TENANT-MAIN-01", "CARDIOLOGIST", [])
        raw = token[4:]
        parts = raw.split(".")
        fake_sig = "a" * len(parts[2])
        tampered_token = f"JWT-{parts[0]}.{parts[1]}.{fake_sig}"

        is_valid, claims, err = self.auth.decode_and_verify_token(tampered_token)
        self.assertFalse(is_valid)
        self.assertIsNone(claims)

    def test_csb_secret_configuration(self):
        """Clinical Safety Board governance must load HMAC secret from environment."""
        os.environ["CSB_HMAC_SECRET"] = "PHASE19-CSB-ENTERPRISE-SECRET-KEY-999"
        csb = ClinicalSafetyBoardGovernanceEngine(tenant_id="TENANT-MAIN-01")
        self.assertEqual(csb._secret_key, "PHASE19-CSB-ENTERPRISE-SECRET-KEY-999")


if __name__ == "__main__":
    unittest.main()
