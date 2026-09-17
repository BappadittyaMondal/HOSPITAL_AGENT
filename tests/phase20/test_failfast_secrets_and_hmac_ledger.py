"""
PROJECT "HOSPITAL" — PHASE 20: PRODUCTION CORE SECURITY HARDENING
Test Suite: test_failfast_secrets_and_hmac_ledger.py
Validates:
  - Fail-fast RuntimeError in production mode when secrets are missing
  - Dynamic ephemeral random key generation in dev mode (no committed static strings)
  - Pure RFC 7519 JWT generation with standard formatting
  - Keyed HMAC-SHA256 audit ledger with external secret anchoring
  - Resistance against database rewrite attacks by privileged database operators
"""

import os
import sys
import hmac
import hashlib
import sqlite3
import unittest
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from auth_manager import AuthSecurityManager, auth_security_manager
from clinical_safety_board_governance import ClinicalSafetyBoardGovernanceEngine
from audit_ledger import UniversalAuditLedger, GENESIS_HASH


class TestFailFastSecretsAndHMACLedger(unittest.TestCase):

    def setUp(self):
        self.old_env = os.environ.get("HOSPITAL_ENV")
        self.old_jwt = os.environ.get("JWT_SECRET_KEY")
        self.old_csb = os.environ.get("CSB_HMAC_SECRET")
        self.old_audit = os.environ.get("AUDIT_LEDGER_HMAC_KEY")

        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "phase20_audit.db")

    def tearDown(self):
        # Restore environment variables
        if self.old_env is not None:
            os.environ["HOSPITAL_ENV"] = self.old_env
        else:
            os.environ.pop("HOSPITAL_ENV", None)

        if self.old_jwt is not None:
            os.environ["JWT_SECRET_KEY"] = self.old_jwt
        else:
            os.environ.pop("JWT_SECRET_KEY", None)

        if self.old_csb is not None:
            os.environ["CSB_HMAC_SECRET"] = self.old_csb
        else:
            os.environ.pop("CSB_HMAC_SECRET", None)

        if self.old_audit is not None:
            os.environ["AUDIT_LEDGER_HMAC_KEY"] = self.old_audit
        else:
            os.environ.pop("AUDIT_LEDGER_HMAC_KEY", None)

        import gc
        gc.collect()
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except OSError:
                pass
        for ext in ["-wal", "-shm"]:
            f = self.db_file + ext
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    def test_auth_manager_fail_fast_in_production(self):
        """AuthSecurityManager must raise RuntimeError if JWT_SECRET_KEY is unset in production."""
        os.environ["HOSPITAL_ENV"] = "production"
        os.environ.pop("JWT_SECRET_KEY", None)

        with self.assertRaises(RuntimeError) as ctx:
            AuthSecurityManager(jwt_secret=None)
        self.assertIn("FATAL SECURITY EXCEPTION", str(ctx.exception))
        self.assertIn("JWT_SECRET_KEY", str(ctx.exception))

    def test_csb_governance_fail_fast_in_production(self):
        """ClinicalSafetyBoardGovernanceEngine must raise RuntimeError if CSB_HMAC_SECRET is unset in production."""
        os.environ["HOSPITAL_ENV"] = "production"
        os.environ.pop("CSB_HMAC_SECRET", None)

        with self.assertRaises(RuntimeError) as ctx:
            ClinicalSafetyBoardGovernanceEngine()
        self.assertIn("FATAL SECURITY EXCEPTION", str(ctx.exception))
        self.assertIn("CSB_HMAC_SECRET", str(ctx.exception))

    def test_audit_ledger_fail_fast_in_production(self):
        """UniversalAuditLedger must raise RuntimeError if AUDIT_LEDGER_HMAC_KEY is unset in production."""
        os.environ["HOSPITAL_ENV"] = "production"
        os.environ.pop("AUDIT_LEDGER_HMAC_KEY", None)

        with self.assertRaises(RuntimeError) as ctx:
            UniversalAuditLedger(db_path=self.db_file, hmac_key=None)
        self.assertIn("FATAL SECURITY EXCEPTION", str(ctx.exception))
        self.assertIn("AUDIT_LEDGER_HMAC_KEY", str(ctx.exception))

    def test_dev_mode_ephemeral_random_keys(self):
        """In development mode, distinct instances generate unique random keys without static fallbacks."""
        os.environ["HOSPITAL_ENV"] = "development"
        os.environ.pop("JWT_SECRET_KEY", None)
        os.environ.pop("JWT_EPHEMERAL_DEV_SECRET", None)

        mgr1 = AuthSecurityManager(jwt_secret=None)
        mgr2 = AuthSecurityManager(jwt_secret=None)

        self.assertNotEqual(mgr1._jwt_secret, mgr2._jwt_secret, "Each dev instance must get unique random secret")
        self.assertNotEqual(mgr1._jwt_secret, b"HOSPITAL_PROD_JWT_SECURE_KEY_2026_CHANGE_IN_VAULT")

    def test_standard_rfc7519_jwt_generation(self):
        """When standard_format=True, token must be pure {hdr}.{pay}.{sig} without 'JWT-' prefix."""
        mgr = AuthSecurityManager(jwt_secret="PHASE-20-TEST-SECRET-KEY-FOR-RFC7519-TOKEN-VALIDATION")
        token = mgr.create_access_token(
            username="dr_sharma",
            tenant_id="TENANT-MAIN-01",
            role="CHIEF_SURGEON",
            permissions=["OT_BOOKING", "EMERGENCY_SIGN"],
            standard_format=True
        )
        self.assertFalse(token.startswith("JWT-"), "Standard token must not have JWT- prefix")
        self.assertEqual(len(token.split(".")), 3, "Must have exactly three base64url segments")

        is_valid, claims, err = mgr.decode_and_verify_token(token)
        self.assertTrue(is_valid)
        self.assertIsNotNone(claims)
        self.assertEqual(claims["sub"], "dr_sharma")
        self.assertEqual(claims["role"], "CHIEF_SURGEON")

    def test_keyed_hmac_audit_ledger_prevents_unkeyed_rewrite(self):
        """A malicious DBA rewriting ledger with unkeyed SHA-256 must be detected."""
        secret_key = "TOP-SECRET-VAULT-EXTERNAL-AUDIT-KEY-2026"
        ledger = UniversalAuditLedger(db_path=self.db_file, hmac_key=secret_key)

        for i in range(3):
            ledger.record_event(
                tenant_id="TENANT-01",
                event_type="CLINICAL_ORDER",
                aggregate_id=f"PAT-{i}",
                actor_id="DR-01",
                payload={"order": f"Drug_{i}", "dose": 100}
            )

        # Confirm ledger verifies valid
        is_valid, bad_idx, msg = ledger.verify_chain_integrity()
        self.assertTrue(is_valid)

        # Attacker attempts to rewrite row 2 with forged data and recalculates with standard SHA-256 (no HMAC key)
        conn = sqlite3.connect(self.db_file)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT prev_hash, timestamp, tenant_id, event_type, aggregate_id, actor_id FROM audit_chain WHERE entry_index=2;")
                prev_h, ts, tid, et, agg, act = cursor.fetchone()
                forged_payload = '{"order": "FORGED_NARCOTIC", "dose": 500}'
                forged_phash = hashlib.sha256(forged_payload.encode("utf-8")).hexdigest()
                unkeyed_hash = hashlib.sha256(f"{prev_h}|{ts}|{tid}|{et}|{agg}|{act}|{forged_phash}".encode("utf-8")).hexdigest()
                conn.execute("""
                    UPDATE audit_chain
                    SET payload_json = ?, payload_hash = ?, current_hash = ?
                    WHERE entry_index = 2;
                """, (forged_payload, forged_phash, unkeyed_hash))
        finally:
            conn.close()

        # Chain verification must catch the unkeyed forgery
        is_valid, bad_idx, msg = ledger.verify_chain_integrity()
        self.assertFalse(is_valid)
        self.assertEqual(bad_idx, 2)
        self.assertIn("signature mismatch", msg.lower())


if __name__ == "__main__":
    unittest.main()
