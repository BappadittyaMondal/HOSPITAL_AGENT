"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Test Suite: test_anesthesia_pacu.py
Validates:
  - Pre-anesthetic checkup (Mallampati Class, difficult airway prediction)
  - PACU Aldrete recovery scoring
  - Hard rule blocking ward discharge when Aldrete score < 9
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from anesthesia_pacu_engine import (
    AnesthesiaPACUEngine, PACUDischargeBlockError
)


class TestAnesthesiaPACUEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AnesthesiaPACUEngine()

    def test_pac_difficult_airway_prediction(self):
        """Verify Mallampati Class 4 or narrow thyromental distance flags difficult airway."""
        pac = self.engine.conduct_pac_assessment(
            patient_id="PAT-ANES-01",
            asa_class="ASA_II",
            is_emergency=False,
            mallampati_class=4,  # Class IV
            mouth_opening_cm=2.5,
            thyromental_distance_cm=5.0,
            anesthetist_id="DOC-ANES-01"
        )
        self.assertTrue(pac.difficult_airway_predicted)

    def test_pacu_aldrete_discharge_gate(self):
        """Verify PACU discharge to ward is blocked when Aldrete score < 9."""
        patient_id = "PAT-POSTOP-02"

        # Record depressed post-op recovery:
        # Activity: 1 (moves 2 ext), Respiration: 1 (shallow), Circulation: 2 (BP normal),
        # Consciousness: 1 (arousable), O2: 1 (requires O2 mask) -> Total = 6 / 10
        self.engine.evaluate_aldrete_score(
            patient_id=patient_id,
            pacu_bay_id="PACU-BAY-03",
            activity=1,
            respiration=1,
            circulation=2,
            consciousness=1,
            o2_saturation=1,
            nurse_id="NURSE-PACU-01"
        )

        # Attempt discharge -> BLOCKED
        with self.assertRaises(PACUDischargeBlockError) as ctx:
            self.engine.authorize_pacu_discharge_to_ward(patient_id, "DOC-ANES-01")
        self.assertIn("Aldrete Score of 6/10 (Minimum 9 required)", str(ctx.exception))

        # Re-evaluate 45 minutes later:
        # Activity: 2, Respiration: 2, Circulation: 2, Consciousness: 2, O2: 2 -> Total = 10 / 10
        self.engine.evaluate_aldrete_score(
            patient_id=patient_id,
            pacu_bay_id="PACU-BAY-03",
            activity=2,
            respiration=2,
            circulation=2,
            consciousness=2,
            o2_saturation=2,
            nurse_id="NURSE-PACU-01"
        )

        # Now discharge succeeds
        res = self.engine.authorize_pacu_discharge_to_ward(patient_id, "DOC-ANES-01")
        self.assertTrue(res["discharged_to_ward"])
        self.assertEqual(res["aldrete_score"], 10)


if __name__ == "__main__":
    unittest.main()
