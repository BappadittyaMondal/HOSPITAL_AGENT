"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Test Suite: test_surgical_safety_ot.py
Validates:
  - Quality Gate 1: OT workflow physically prevents surgical case closure completion if sponge/needle count has discrepancy
  - WHO Surgical Safety Checklist (Sign-In, Time-Out, Sign-Out)
  - UDI implant barcode logging
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from surgical_safety_ot_engine import (
    SurgicalSafetyOTEngine, SurgicalCountDiscrepancyError, SurgicalSafetyError
)


class TestSurgicalSafetyOTEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SurgicalSafetyOTEngine()
        self.case = self.engine.schedule_case(
            case_id="CASE-OT-101",
            patient_id="PAT-SURG-77",
            ot_room_id="OT-1",
            lead_surgeon_id="SURG-01",
            anesthetist_id="ANES-01",
            scrub_nurse_id="NURSE-SCRUB-01",
            circulating_nurse_id="NURSE-CIRC-02",
            procedure_name="Exploratory Laparotomy & Appendectomy"
        )

    def test_quality_gate_sponge_count_discrepancy_blocks_closure(self):
        """
        Phase 09 Quality Gate 1:
        OT workflow physically prevents surgical case closure completion
        if sponge/needle count indicates a discrepancy.
        """
        # Execute Sign-In
        self.engine.execute_sign_in_gate(
            case_id="CASE-OT-101",
            patient_identity_confirmed=True,
            surgical_site_marked=True,
            anesthesia_safety_check_done=True,
            pulse_oximeter_functioning=True,
            known_allergy=False,
            difficult_airway_risk=False,
            blood_loss_risk_over_500ml=False,
            sign_off_anesthetist_id="ANES-01"
        )

        # Execute Time-Out
        self.engine.execute_time_out_gate(
            case_id="CASE-OT-101",
            team_members_introduced=True,
            patient_identity_and_site_reconfirmed=True,
            critical_surgical_steps_reviewed=True,
            antibiotic_prophylaxis_given_within_60min=True,
            sterility_indicators_confirmed=True,
            imaging_displayed=True,
            sign_off_surgeon_id="SURG-01"
        )

        # Record Counts:
        # Needle: Initial 10, Added 0, Discarded 0, Final 10 -> Balanced (10 == 10)
        self.engine.update_surgical_count("CASE-OT-101", "NEEDLE", initial=10, added=0, discarded=0, final_counted=10)
        # Instrument: Initial 30, Added 5, Discarded 0, Final 35 -> Balanced (35 == 35)
        self.engine.update_surgical_count("CASE-OT-101", "INSTRUMENT", initial=30, added=5, discarded=0, final_counted=35)
        # SPONGE: Initial 20, Added 10 (Total 30). Discarded 5, Final counted 24 (Sum = 29 != 30, Missing 1 sponge!)
        self.engine.update_surgical_count("CASE-OT-101", "SPONGE", initial=20, added=10, discarded=5, final_counted=24)

        # Attempt to complete case closure with unbalanced sponge count -> MUST THROW FATAL HARD STOP ERROR!
        with self.assertRaises(SurgicalCountDiscrepancyError) as ctx:
            self.engine.execute_sign_out_and_closure_gate(
                case_id="CASE-OT-101",
                scrub_nurse_id="NURSE-SCRUB-01",
                circulating_nurse_id="NURSE-CIRC-02",
                specimen_labeled_correctly=True,
                postop_recovery_concerns="None"
            )

        self.assertIn("FATAL SURGICAL SAFETY HARD STOP", str(ctx.exception))
        self.assertIn("Discrepancy detected in 'SPONGE' count", str(ctx.exception))
        self.assertIn("Deficit: 1", str(ctx.exception))
        self.assertIn("physically blocked", str(ctx.exception))
        self.assertEqual(self.case.state, "IN_SURGERY")

        # Now locate the missing sponge in the discard bucket and update count: Discarded = 6, Final = 24 -> 30 == 30!
        self.engine.update_surgical_count("CASE-OT-101", "SPONGE", initial=20, added=10, discarded=6, final_counted=24)

        # Now Sign-Out and closure succeed
        sign_out = self.engine.execute_sign_out_and_closure_gate(
            case_id="CASE-OT-101",
            scrub_nurse_id="NURSE-SCRUB-01",
            circulating_nurse_id="NURSE-CIRC-02",
            specimen_labeled_correctly=True,
            postop_recovery_concerns="Patient stable, extubated"
        )
        self.assertEqual(sign_out["stage"], "SIGN_OUT")
        self.assertTrue(sign_out["all_counts_balanced"])
        self.assertEqual(self.case.state, "CLOSED")

    def test_udi_implant_barcode_recording(self):
        """Verify UDI implant scanning directly attaches to surgical record."""
        udi = self.engine.record_implant_udi(
            case_id="CASE-OT-101",
            udi_barcode="(01)00884838045678(17)281231(10)LOT-998(21)SN-4451",
            device_name="Cobalt-Chromium Femoral Knee Component",
            manufacturer="Zimmer Biomet",
            lot_serial_number="LOT-998-SN4451",
            expiry_date="2028-12-31",
            surgeon_id="SURG-01"
        )
        self.assertEqual(len(self.case.implants), 1)
        self.assertEqual(udi.udi_barcode, "(01)00884838045678(17)281231(10)LOT-998(21)SN-4451")
        self.assertEqual(udi.device_name, "Cobalt-Chromium Femoral Knee Component")


if __name__ == "__main__":
    unittest.main()
