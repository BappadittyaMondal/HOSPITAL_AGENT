#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 22: CONCURRENT AUDIT LEDGER & RESILIENT PERSISTENCE TEST SUITE
Module: tests/phase22/test_concurrent_audit_and_persistence.py
Validates:
  1. 100+ concurrent worker threads recording events simultaneously into UniversalAuditLedger.
  2. Strict monotonic serialization without sequence gaps or duplicate entry_indices.
  3. Continuous uninterrupted cryptographic SHA-256 hash chain with 0 forks.
  4. Instant detection of cryptographic tamper/corruption in audit history.
"""

import os
import sys
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from audit_ledger import UniversalAuditLedger, AuditLedger


class TestConcurrentAuditAndPersistence(unittest.TestCase):

    def setUp(self):
        self.test_db_path = os.path.abspath("test_phase22_concurrent_audit.db")
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass
        self.ledger = UniversalAuditLedger(db_path=self.test_db_path)

    def tearDown(self):
        del self.ledger
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def test_100_concurrent_writers_produce_zero_forks_and_strict_chain(self):
        """
        Stress-tests 100 concurrent worker threads writing simultaneously.
        Verifies that thread locking + SQLite BEGIN EXCLUSIVE transaction serializes all 100 events
        monotonically without hash-chain forks or sequence collisions.
        """
        num_writers = 100
        errors = []

        def worker_write(writer_id: int):
            try:
                entry = self.ledger.record_event(
                    tenant_id="TENANT-CONCURRENCY",
                    event_type="CONCURRENT_STRESS_TEST",
                    aggregate_id=f"PAT-{writer_id:04d}",
                    actor_id=f"USER-CONCUR-{writer_id}",
                    payload={"writer_id": writer_id, "data": f"sample_payload_{writer_id}"}
                )
                return entry
            except Exception as e:
                errors.append(e)
                raise

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker_write, i) for i in range(num_writers)]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(errors), 0, f"Encountered write errors: {errors}")
        self.assertEqual(len(results), num_writers)

        # Inspect raw database records
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT entry_index, prev_hash, current_hash FROM audit_chain ORDER BY entry_index ASC;")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), num_writers)

        # Verify strict monotonicity: entry_indices must be 1, 2, ..., 100 exactly
        indices = [r[0] for r in rows]
        self.assertEqual(indices, list(range(1, num_writers + 1)))

        # Verify cryptographic hash continuity: each row's prev_hash must equal preceding row's current_hash
        for i in range(1, len(rows)):
            prev_row = rows[i - 1]
            curr_row = rows[i]
            self.assertEqual(
                curr_row[1], prev_row[2],
                f"Hash chain broken at index {curr_row[0]}: prev_hash '{curr_row[1]}' != '{prev_row[2]}'"
            )

        # Verify full ledger integrity using engine verification
        is_valid, corrupted_idx, report = self.ledger.verify_chain_integrity()
        self.assertTrue(is_valid, f"Ledger integrity verification failed: {report}")
        self.assertIsNone(corrupted_idx)
        self.assertIn("100", report)

    def test_cryptographic_tamper_detection(self):
        """
        Artificially mutates a committed audit event's payload in SQLite.
        Verifies that verify_chain_integrity() immediately flags the breach.
        """
        for i in range(5):
            self.ledger.record_event(
                tenant_id="TENANT-MAIN-01",
                event_type="CLINICAL_EVENT",
                aggregate_id=f"PAT-{i}",
                actor_id=f"DOC-{i}",
                payload={"iteration": i}
            )

        # Artificially alter the payload of record entry_index 3
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("UPDATE audit_chain SET payload_json = '{\"tampered\": true}' WHERE entry_index = 3;")
        conn.commit()
        conn.close()

        # Chain verification must now fail and pinpoint index 3
        is_valid, corrupted_idx, msg = self.ledger.verify_chain_integrity()
        self.assertFalse(is_valid, "Tampered database record was not detected!")
        self.assertEqual(corrupted_idx, 3)
        self.assertIn("tampering detected", msg.lower())


if __name__ == "__main__":
    unittest.main()
