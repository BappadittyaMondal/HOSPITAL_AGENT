"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Test Suite: test_closed_loop_dispensing.py
Validates:
  - Quality Gate 1: Attempting to dispense expired batch is 100% blocked with terminal error
  - Barcode verification matching prescription to physical product
  - ISMP High-Alert dual verification protocol
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from closed_loop_dispensing import (
    ClosedLoopDispensingEngine, PrescriptionItem,
    ExpiredMedicationBlockError, HighAlertVerificationError, BarcodeMismatchError
)


class TestClosedLoopDispensingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ClosedLoopDispensingEngine()
        self.now = datetime.now(timezone.utc)

    def test_quality_gate_expired_batch_strictly_blocked(self):
        """
        Phase 06 Quality Gate 1:
        Attempting to dispense an expired medication batch is 100% blocked by system logic with terminal error.
        """
        prescription = PrescriptionItem(
            prescription_id="RX-9001",
            patient_id="PAT-1002",
            drug_id="DRUG-PARACETAMOL-500",
            generic_name="Paracetamol",
            prescribed_dose="500 mg",
            route="ORAL",
            prescribed_qty=10
        )
        expired_date = self.now - timedelta(days=2)

        with self.assertRaises(ExpiredMedicationBlockError) as ctx:
            self.engine.verify_and_dispense(
                prescription=prescription,
                batch_number="BATCH-EXPIRED-77",
                batch_expiry_date=expired_date,
                scanned_barcode_drug_id="DRUG-PARACETAMOL-500",
                dispense_qty=10,
                primary_pharmacist_id="PHARM-01",
                as_of_time=self.now
            )

        self.assertIn("FATAL PHARMACY SAFETY HAZARD", str(ctx.exception))
        self.assertIn("expired on", str(ctx.exception))

        # Check recorded event state
        last_event = self.engine.dispense_history[-1]
        self.assertEqual(last_event.status, "BLOCKED_EXPIRED")
        self.assertTrue(last_event.terminal_alarm_sounded)
        self.assertEqual(last_event.quantity_dispensed, 0)

    def test_barcode_mismatch_blocked(self):
        """Verify scanning wrong medication barcode is rejected."""
        prescription = PrescriptionItem(
            prescription_id="RX-9002",
            patient_id="PAT-1002",
            drug_id="DRUG-AMLO-5",
            generic_name="Amlodipine",
            prescribed_dose="5 mg",
            route="ORAL",
            prescribed_qty=30
        )
        unexpired_date = self.now + timedelta(days=180)

        with self.assertRaises(BarcodeMismatchError) as ctx:
            self.engine.verify_and_dispense(
                prescription=prescription,
                batch_number="BATCH-ATEN-50",
                batch_expiry_date=unexpired_date,
                scanned_barcode_drug_id="DRUG-ATENOLOL-50",  # Mismatch!
                dispense_qty=30,
                primary_pharmacist_id="PHARM-01",
                as_of_time=self.now
            )

        self.assertIn("BARCODE MISMATCH", str(ctx.exception))
        last_event = self.engine.dispense_history[-1]
        self.assertEqual(last_event.status, "BLOCKED_MISMATCH")

    def test_ismp_high_alert_dual_verification_enforcement(self):
        """Verify high-alert medication requires independent secondary verification."""
        prescription = PrescriptionItem(
            prescription_id="RX-9003",
            patient_id="PAT-ICU-88",
            drug_id="DRUG-KCL-CONC",
            generic_name="Potassium Chloride 15% Concentrate",
            prescribed_dose="20 mEq IV Infusion",
            route="IV",
            prescribed_qty=1,
            is_high_alert=True
        )
        unexpired_date = self.now + timedelta(days=90)

        # 1. Missing secondary verifier -> FAILS
        with self.assertRaises(HighAlertVerificationError) as ctx1:
            self.engine.verify_and_dispense(
                prescription=prescription,
                batch_number="BATCH-KCL-001",
                batch_expiry_date=unexpired_date,
                scanned_barcode_drug_id="DRUG-KCL-CONC",
                dispense_qty=1,
                primary_pharmacist_id="PHARM-01",
                secondary_verifier_id=None,
                as_of_time=self.now
            )
        self.assertIn("ISMP HIGH-ALERT RULE VIOLATION", str(ctx1.exception))

        # 2. Same user attempting dual sign-off -> FAILS
        with self.assertRaises(HighAlertVerificationError) as ctx2:
            self.engine.verify_and_dispense(
                prescription=prescription,
                batch_number="BATCH-KCL-001",
                batch_expiry_date=unexpired_date,
                scanned_barcode_drug_id="DRUG-KCL-CONC",
                dispense_qty=1,
                primary_pharmacist_id="PHARM-01",
                secondary_verifier_id="PHARM-01",  # Same user!
                as_of_time=self.now
            )
        self.assertIn("requires an independent, distinct secondary verifier", str(ctx2.exception))

        # 3. Two distinct verifiers -> SUCCEEDS
        event = self.engine.verify_and_dispense(
            prescription=prescription,
            batch_number="BATCH-KCL-001",
            batch_expiry_date=unexpired_date,
            scanned_barcode_drug_id="DRUG-KCL-CONC",
            dispense_qty=1,
            primary_pharmacist_id="PHARM-01",
            secondary_verifier_id="PHARM-02",  # Distinct
            as_of_time=self.now
        )
        self.assertEqual(event.status, "DISPENSED")
        self.assertEqual(event.quantity_dispensed, 1)


if __name__ == "__main__":
    unittest.main()
