"""
Test Suite: test_linen_laundry.py
Phase 12: Hospital Operations — Linen & Contaminated Laundry Management (Gap 31)
Mandate:
  - Departmental linen inventory and indent tracking.
  - Wash thermal parameter validation per CDC/NABH (> 71°C for 25 min).
  - Chemical disinfection validation (> 65°C for 10 min with > 100 ppm bleach).
  - Inviolable Quarantine Gate: Disinfection failure strictly blocks release to clean store.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from linen_laundry_engine import (
    LinenLaundryEngine,
    LinenType,
    LinenBiohazardGrade,
    WashCycleStatus,
    DisinfectionFailureError,
    LinenError,
)


class TestLinenLaundryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = LinenLaundryEngine()

    def test_thermal_disinfection_success_and_release(self):
        """Validates high-temp thermal wash achieving >= 71°C for >= 25 mins."""
        cycle = self.engine.initiate_wash_cycle(
            cycle_id="WASH-2026-001",
            machine_id="WASHER-EXTRACTOR-01",
            batch_barcode="BATCH-OT-DRAPES-901",
            biohazard_grade=LinenBiohazardGrade.ROUTINE_SOILED,
            item_counts={LinenType.BEDSHEET.value: 50, LinenType.PILLOW_COVER.value: 50},
            operator_id="OP-LAUNDRY-1",
        )
        self.assertEqual(cycle.status, WashCycleStatus.IN_PROGRESS)

        # Ingest compliant telemetry: 73.5°C sustained for 28 minutes
        telemetry = self.engine.record_wash_cycle_telemetry(
            cycle_id="WASH-2026-001",
            max_temperature_c=73.5,
            duration_at_or_above_target_mins=28.0,
        )
        self.assertEqual(telemetry.status, WashCycleStatus.DISINFECTED_PASSED)
        self.assertIn("Thermal disinfection satisfied", telemetry.validation_notes)

        # Release to clean store
        initial_bedsheets = self.engine.get_central_stock()[LinenType.BEDSHEET.value]
        release_res = self.engine.release_batch_to_clean_inventory(
            cycle_id="WASH-2026-001",
            supervisor_id="SUP-LINEN-1",
        )
        self.assertEqual(release_res["status"], "BATCH_RELEASED")
        self.assertEqual(
            self.engine.get_central_stock()[LinenType.BEDSHEET.value],
            initial_bedsheets + 50,
        )

    def test_thermal_disinfection_failure_and_quarantine_block(self):
        """Validates that substandard thermal wash is quarantined and blocked from clean storage."""
        cycle = self.engine.initiate_wash_cycle(
            cycle_id="WASH-2026-002",
            machine_id="WASHER-EXTRACTOR-02",
            batch_barcode="BATCH-ICU-INFECTIOUS-881",
            biohazard_grade=LinenBiohazardGrade.CONTAMINATED_INFECTIOUS,
            item_counts={LinenType.PATIENT_GOWN.value: 30},
            operator_id="OP-LAUNDRY-2",
        )

        # Substandard telemetry: reached only 62°C for 14 minutes (failed both thermal & chemical criteria)
        failed_telemetry = self.engine.record_wash_cycle_telemetry(
            cycle_id="WASH-2026-002",
            max_temperature_c=62.0,
            duration_at_or_above_target_mins=14.0,
            chemical_disinfectant_ppm=20.0,
        )
        self.assertEqual(failed_telemetry.status, WashCycleStatus.DISINFECTION_FAILED)
        self.assertIn("DISINFECTION DEFICIENCY", failed_telemetry.validation_notes)

        # Attempt to release failed batch must raise DisinfectionFailureError
        with self.assertRaises(DisinfectionFailureError) as ctx:
            self.engine.release_batch_to_clean_inventory(
                cycle_id="WASH-2026-002",
                supervisor_id="SUP-LINEN-1",
            )
        self.assertIn("INFECTION CONTROL VIOLATION", str(ctx.exception))
        self.assertEqual(failed_telemetry.status, WashCycleStatus.QUARANTINED_RE_WASH)

    def test_ward_indent_and_fulfillment(self):
        """Tests ward requisition and inventory issuance."""
        indent = self.engine.create_ward_indent(
            indent_id="IND-ICU-001",
            ward_id="ICU_EAST",
            requested_items={LinenType.BEDSHEET.value: 20, LinenType.PILLOW_COVER.value: 20},
            requested_by="NURSE-INCHARGE-ICU",
        )
        self.assertEqual(indent.status, "PENDING")

        fulfilled = self.engine.fulfill_ward_indent(indent.indent_id, issuer_id="STORE-KEEPER-1")
        self.assertEqual(fulfilled["status"], "INDENT_FULFILLED")

        ward_stock = self.engine.get_ward_stock("ICU_EAST")
        self.assertEqual(ward_stock[LinenType.BEDSHEET.value], 20)
        self.assertEqual(ward_stock[LinenType.PILLOW_COVER.value], 20)


if __name__ == "__main__":
    unittest.main()
