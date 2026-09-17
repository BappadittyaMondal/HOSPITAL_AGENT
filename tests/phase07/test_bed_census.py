"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Test Suite: test_bed_census.py
Validates:
  - Quality Gate 1: Bed status switches to CLEANING_REQUIRED on checkout; allocation blocked until sanitization
  - State machine lifecycle transitions
  - Contact precaution isolation disinfection protocols
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from bed_census_engine import (
    BedCensusEngine, TerminalCleaningSignOff,
    BedStateError, BedSanitizationBlockError
)


class TestBedCensusEngine(unittest.TestCase):

    def setUp(self):
        self.engine = TestBedCensusEngine_helper()

    def test_quality_gate_checkout_to_cleaning_and_allocation_block(self):
        """
        Phase 07 Quality Gate 1:
        Bed status switches to Cleaning-Required the instant patient checkout completes;
        bed allocation is blocked until housekeeping submits sanitization sign-off.
        """
        engine = BedCensusEngine()
        bed = engine.register_bed("BED-ICU-01", "WARD-ICU-A", "ICU")
        self.assertEqual(bed.state, "AVAILABLE")

        # Admit patient
        engine.admit_patient_to_bed("BED-ICU-01", "PAT-101", "NURSE-01")
        self.assertEqual(bed.state, "OCCUPIED")
        self.assertEqual(bed.current_patient_id, "PAT-101")

        # 1. Patient Checkout Completes -> Immediately switches to CLEANING_REQUIRED
        engine.complete_patient_checkout("BED-ICU-01", "ADMIN-01")
        self.assertEqual(bed.state, "CLEANING_REQUIRED")
        self.assertIsNone(bed.current_patient_id)

        # 2. Attempting to allocate/reserve bed while CLEANING_REQUIRED is mechanically blocked
        with self.assertRaises(BedSanitizationBlockError) as ctx1:
            engine.reserve_bed("BED-ICU-01", "PAT-102", "NURSE-02")
        self.assertIn("allocation strictly blocked until terminal sanitization", str(ctx1.exception).lower())

        with self.assertRaises(BedSanitizationBlockError) as ctx2:
            engine.admit_patient_to_bed("BED-ICU-01", "PAT-102", "NURSE-02")
        self.assertIn("terminal sanitization required", str(ctx2.exception).lower())

        # 3. Housekeeping submits sanitization sign-off -> Transitions to SANITIZED then AVAILABLE
        sign_off = TerminalCleaningSignOff(
            housekeeper_id="HK-01",
            supervisor_id="HK-SUP-01",
            checklist_completed=True,
            uv_decontamination_used=True,
            chemical_disinfectant="Virex II 256 Quaternary",
            completed_at="2026-09-17T17:00:00Z"
        )
        engine.submit_housekeeping_sanitization("BED-ICU-01", sign_off)
        self.assertEqual(bed.state, "AVAILABLE")

        # 4. Now reservation and admission succeed
        engine.reserve_bed("BED-ICU-01", "PAT-102", "NURSE-02")
        self.assertEqual(bed.state, "RESERVED")

    def test_isolation_room_mandates_uv_or_sporicidal_protocol(self):
        """Verify C. diff / MRSA isolation room requires specialized decontamination."""
        engine = BedCensusEngine()
        bed = engine.register_bed("BED-ISO-01", "WARD-MED-B", "ISOLATION")

        # Admit patient with C_DIFF isolation
        engine.admit_patient_to_bed("BED-ISO-01", "PAT-CDIFF-01", "NURSE-01", isolation_precaution="C_DIFF")
        engine.complete_patient_checkout("BED-ISO-01", "ADMIN-01")

        # Incomplete isolation cleaning (no UV and regular disinfectant) -> Rejected
        invalid_sign_off = TerminalCleaningSignOff(
            housekeeper_id="HK-02",
            supervisor_id="HK-SUP-01",
            checklist_completed=True,
            uv_decontamination_used=False,
            chemical_disinfectant="Standard Alcohol Wipe",
            completed_at="2026-09-17T17:05:00Z"
        )
        with self.assertRaises(BedStateError) as ctx:
            engine.submit_housekeeping_sanitization("BED-ISO-01", invalid_sign_off)
        self.assertIn("mandates UV decontamination or sporicidal disinfectant", str(ctx.exception))

        # Valid isolation cleaning with Sporicidal disinfectant
        valid_sign_off = TerminalCleaningSignOff(
            housekeeper_id="HK-02",
            supervisor_id="HK-SUP-01",
            checklist_completed=True,
            uv_decontamination_used=True,
            chemical_disinfectant="Sporicidal Sodium Hypochlorite 1:10 Bleach",
            completed_at="2026-09-17T17:10:00Z"
        )
        engine.submit_housekeeping_sanitization("BED-ISO-01", valid_sign_off)
        self.assertEqual(bed.state, "AVAILABLE")
        self.assertIsNone(bed.isolation_precaution)


def TestBedCensusEngine_helper():
    return None


if __name__ == "__main__":
    unittest.main()
