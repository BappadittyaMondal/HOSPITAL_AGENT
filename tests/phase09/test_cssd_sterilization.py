"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Test Suite: test_cssd_sterilization.py
Validates:
  - Quality Gate 3: Failed autoclave spore test automatically locks all surgical trays in that batch
  - Mechanical block preventing issuance of unsterile or recalled trays to OT
  - Successful biological indicator test releases trays to sterile storage
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from cssd_sterilization_engine import (
    CSSDSterilizationEngine, SterilizationFailureError, TrayUnsterileIssueError
)


class TestCSSDSterilizationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CSSDSterilizationEngine()

        # Register trays
        self.engine.register_tray("TRAY-ORTHO-01", "Total Hip Set A", 45)
        self.engine.register_tray("TRAY-LAP-02", "Major Laparotomy Set B", 60)
        self.engine.register_tray("TRAY-ENT-03", "Microlaryngeal Set C", 25)

    def test_quality_gate_failed_spore_test_locks_all_batch_trays(self):
        """
        Phase 09 Quality Gate 3:
        Failed autoclave spore test automatically locks all surgical trays processed in that sterilization run.
        """
        batch_id = "AUTOCLAVE-BATCH-88"
        trays_in_batch = ["TRAY-ORTHO-01", "TRAY-LAP-02"]

        # 1. Run autoclave cycle
        self.engine.record_autoclave_run(
            batch_id=batch_id,
            autoclave_id="AUTOCLAVE-01",
            temperature_c=134.0,
            pressure_psi=30.2,
            exposure_time_min=4.0,
            bowie_dick_passed=True,
            operator_id="TECH-CSSD-01",
            tray_barcodes=trays_in_batch
        )

        for code in trays_in_batch:
            self.assertEqual(self.engine.trays[code].current_status, "AUTOCLAVING")

        # 2. Microbiology incubation result: Biological Spore Test FAILED (growth detected)
        with self.assertRaises(SterilizationFailureError) as ctx:
            self.engine.record_biological_indicator_result(
                batch_id=batch_id,
                spore_growth_detected=True,  # FAILED!
                microbiologist_id="DOC-MICRO-01"
            )

        self.assertIn("CRITICAL CSSD INFECTION HAZARD", str(ctx.exception))
        self.assertIn("failed biological spore indicator", str(ctx.exception))

        # Trays in batch must be in RECALLED_LOCKED status
        for code in trays_in_batch:
            self.assertEqual(self.engine.trays[code].current_status, "RECALLED_LOCKED")

        # 3. Attempting to issue a RECALLED_LOCKED tray to OT is mechanically blocked
        with self.assertRaises(TrayUnsterileIssueError) as ctx2:
            self.engine.issue_tray_to_operating_room("TRAY-ORTHO-01", "OT-2", "TECH-CSSD-02")
        self.assertIn("RECALLED_LOCKED", str(ctx2.exception))
        self.assertIn("Issuance strictly barred", str(ctx2.exception))

    def test_successful_spore_test_releases_trays(self):
        """Verify negative spore test approves trays to STERILE_STORAGE and allows OT issuance."""
        batch_id = "AUTOCLAVE-BATCH-89"
        self.engine.record_autoclave_run(
            batch_id=batch_id,
            autoclave_id="AUTOCLAVE-02",
            temperature_c=134.0,
            pressure_psi=30.5,
            exposure_time_min=4.0,
            bowie_dick_passed=True,
            operator_id="TECH-CSSD-01",
            tray_barcodes=["TRAY-ENT-03"]
        )

        # Spore test negative (sterile)
        res = self.engine.record_biological_indicator_result(
            batch_id=batch_id,
            spore_growth_detected=False,  # PASS
            microbiologist_id="DOC-MICRO-01"
        )
        self.assertEqual(res["status"], "APPROVED_STERILE")
        self.assertEqual(self.engine.trays["TRAY-ENT-03"].current_status, "STERILE_STORAGE")

        # Issuing to OT succeeds
        issue = self.engine.issue_tray_to_operating_room("TRAY-ENT-03", "OT-4", "TECH-CSSD-02")
        self.assertEqual(issue["status"], "ISSUED_TO_OT")
        self.assertEqual(self.engine.trays["TRAY-ENT-03"].current_status, "ISSUED_TO_OT")


if __name__ == "__main__":
    unittest.main()
