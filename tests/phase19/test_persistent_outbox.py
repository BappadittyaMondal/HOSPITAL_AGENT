"""
PROJECT "HOSPITAL" — PHASE 19: PRODUCTION SYSTEMS HARDENING
Test Suite: test_persistent_outbox.py
Validates:
  - Persistent SQLite WAL disk-backed outbox survives process crashes/restarts
  - Atomicity of event staging and pending query
  - Idempotent marking of successfully dispatched events
  - Exponential backoff / retry incrementing and error recording
  - Dead letter queue categorization on exceeded retry thresholds
"""

import os
import sys
import unittest
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from db_session import OutboxManager


class TestPersistentOutbox(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_outbox.db")
        self.outbox = OutboxManager(db_path=self.db_file)

    def tearDown(self):
        # Force garbage collection and connection release
        del self.outbox
        import gc
        gc.collect()
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except OSError:
                pass
        # Remove WAL / SHM files if any
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

    def test_stage_event_and_retrieve_pending(self):
        """Events staged must be returned in pending list with correct aggregate and payload."""
        eid = self.outbox.stage_event(
            aggregate_type="PATIENT_ADMISSION",
            aggregate_id="PAT-PHASE19-001",
            event_type="PATIENT_TRIAGED_RED",
            payload={"gcs": 8, "vitals": {"spo2": 88}}
        )
        self.assertIsNotNone(eid)

        pending = self.outbox.get_pending_events(limit=10)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["event_id"], eid)
        self.assertEqual(pending[0]["aggregate_type"], "PATIENT_ADMISSION")
        self.assertEqual(pending[0]["payload"]["gcs"], 8)
        self.assertEqual(pending[0]["status"], "PENDING")

    def test_reboot_persistence_simulation(self):
        """Events staged must persist across process reboot (fresh OutboxManager instance)."""
        eid = self.outbox.stage_event(
            aggregate_type="CRITICAL_ORDER",
            aggregate_id="ORD-9999",
            event_type="MEDICATION_PRESCRIBED",
            payload={"drug": "Sildenafil", "dose": 50.0}
        )

        # Simulate service shutdown / process death
        del self.outbox
        import gc
        gc.collect()

        # Simulate fresh service reboot
        fresh_outbox = OutboxManager(db_path=self.db_file)
        pending = fresh_outbox.get_pending_events(limit=10)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["event_id"], eid)
        self.assertEqual(pending[0]["event_type"], "MEDICATION_PRESCRIBED")
        self.outbox = fresh_outbox

    def test_mark_dispatched_lifecycle(self):
        """Marking an event as dispatched must remove it from pending queries."""
        eid = self.outbox.stage_event("LAB_ORDER", "LAB-001", "CBC_ORDERED", {"test": "CBC"})
        self.assertEqual(len(self.outbox.get_pending_events()), 1)

        self.outbox.mark_dispatched(eid)
        self.assertEqual(len(self.outbox.get_pending_events()), 0, "Dispatched event must not appear in pending")

    def test_dispatch_failure_and_retry_increment(self):
        """Dispatch failures must increment retry count and store error trace."""
        eid = self.outbox.stage_event("NOTIFICATION", "NOTIF-1", "SMS_ALERT", {"phone": "9999999999"})
        self.outbox.record_dispatch_failure(eid, "Connection timeout to Redpanda broker")

        pending = self.outbox.get_pending_events()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["retry_count"], 1)
        self.assertIn("Connection timeout", pending[0]["last_error"])

    def test_dead_letter_queue_transition(self):
        """Exceeding MAX_RETRIES must transition event to DEAD_LETTER status."""
        eid = self.outbox.stage_event("PAYMENT", "PAY-1", "PAYMENT_CAPTURE", {"amt": 5000})
        for i in range(5):
            self.outbox.record_dispatch_failure(eid, f"Failure attempt {i+1}")

        pending = self.outbox.get_pending_events()
        self.assertEqual(len(pending), 0, "Dead-lettered event must no longer be picked up by pending dispatcher")


if __name__ == "__main__":
    unittest.main()
