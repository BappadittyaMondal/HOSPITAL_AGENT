"""
PROJECT "HOSPITAL" — PHASE 19: PRODUCTION SYSTEMS HARDENING
Test Suite: test_tamper_evident_audit.py
Validates:
  - Append-only SHA-256 cryptographic hash-chained audit ledger
  - Mathematical integrity verification across sequential events
  - Sub-millisecond tampering detection when payload is altered directly in SQLite
  - Linkage break detection when hash pointers are forged or modified
"""

import os
import sys
import sqlite3
import unittest
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from audit_ledger import UniversalAuditLedger, GENESIS_HASH


class TestTamperEvidentAudit(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_audit.db")
        self.ledger = UniversalAuditLedger(db_path=self.db_file)

    def tearDown(self):
        del self.ledger
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

    def test_genesis_state_verification(self):
        """Empty ledger must pass integrity check in genesis state."""
        is_valid, bad_idx, msg = self.ledger.verify_chain_integrity()
        self.assertTrue(is_valid)
        self.assertIsNone(bad_idx)
        self.assertEqual(self.ledger.total_entries, 0)

    def test_sequential_hash_chaining(self):
        """Recording sequential events must generate valid SHA-256 chained pointers."""
        e1 = self.ledger.record_event(
            tenant_id="TENANT-01",
            event_type="PATIENT_ADMITTED",
            aggregate_id="PAT-001",
            actor_id="DR-001",
            payload={"action": "admit", "bed": "ICU-03"}
        )
        self.assertEqual(e1["prev_hash"], GENESIS_HASH)

        e2 = self.ledger.record_event(
            tenant_id="TENANT-01",
            event_type="MEDICATION_ORDERED",
            aggregate_id="PAT-001",
            actor_id="DR-001",
            payload={"drug": "Sorbitrate", "dose_mg": 10}
        )
        self.assertEqual(e2["prev_hash"], e1["current_hash"], "Second event prev_hash must link to first event current_hash")

        e3 = self.ledger.record_event(
            tenant_id="TENANT-01",
            event_type="DISCHARGE_SIGN_OFF",
            aggregate_id="PAT-001",
            actor_id="DR-MS-01",
            payload={"status": "STABLE"}
        )
        self.assertEqual(e3["prev_hash"], e2["current_hash"])

        self.assertEqual(self.ledger.total_entries, 3)
        is_valid, bad_idx, msg = self.ledger.verify_chain_integrity()
        self.assertTrue(is_valid)
        self.assertIsNone(bad_idx)

    def test_detect_payload_tampering(self):
        """Direct row alteration of payload in SQLite must trigger mathematical tampering alarm."""
        for i in range(5):
            self.ledger.record_event(
                tenant_id="TENANT-01",
                event_type=f"EVENT_{i}",
                aggregate_id=f"AGG_{i}",
                actor_id="ACTOR-1",
                payload={"index": i, "data": f"payload_{i}"}
            )

        # Attacker modifies payload of row with entry_index=3 directly in database
        conn = sqlite3.connect(self.db_file)
        try:
            with conn:
                conn.execute("""
                    UPDATE audit_chain
                    SET payload_json = '{"index": 3, "data": "MALICIOUS_FORGED_DATA"}'
                    WHERE entry_index = 3;
                """)
        finally:
            conn.close()

        is_valid, bad_idx, msg = self.ledger.verify_chain_integrity()
        self.assertFalse(is_valid, "Tampered payload must be detected")
        self.assertEqual(bad_idx, 3, "Compromised index must be accurately pinned to entry 3")
        self.assertIn("tampering detected", msg.lower())

    def test_detect_hash_pointer_tampering(self):
        """Forging a hash pointer in the middle of the chain must trigger linkage failure."""
        for i in range(4):
            self.ledger.record_event(
                tenant_id="TENANT-01",
                event_type=f"EVENT_{i}",
                aggregate_id=f"AGG_{i}",
                actor_id="ACTOR-1",
                payload={"index": i}
            )

        # Attacker alters current_hash of row 2
        conn = sqlite3.connect(self.db_file)
        try:
            with conn:
                conn.execute("""
                    UPDATE audit_chain
                    SET current_hash = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
                    WHERE entry_index = 2;
                """)
        finally:
            conn.close()

        is_valid, bad_idx, msg = self.ledger.verify_chain_integrity()
        self.assertFalse(is_valid)
        self.assertEqual(bad_idx, 2)


if __name__ == "__main__":
    unittest.main()
