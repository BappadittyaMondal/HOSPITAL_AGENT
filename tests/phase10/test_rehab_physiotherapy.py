"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Test Suite: test_rehab_physiotherapy.py
Validates:
  - Barthel Index (0-100) functional independence scoring
  - Goniometric Range of Motion (ROM) & VAS pain rating
  - Structured Cardiac Rehabilitation phase enrollment
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from rehab_physiotherapy_engine import RehabPhysiotherapyEngine


class TestRehabPhysiotherapyEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RehabPhysiotherapyEngine()

    def test_barthel_index_calculation(self):
        """Verify Barthel index calculates total score and dependency stratification."""
        # Patient with acute stroke:
        # Feeding: 5, Bathing: 0, Grooming: 0, Dressing: 5, Bowels: 5,
        # Bladder: 5, Toilet: 5, Transfers: 10, Mobility: 10, Stairs: 0
        # Total = 45 / 100 (Severe Dependency)
        assessment = self.engine.calculate_barthel_index(
            patient_id="PAT-STROKE-01",
            feeding=5, bathing=0, grooming=0, dressing=5,
            bowels=5, bladder=5, toilet_use=5,
            transfers=10, mobility=10, stairs=0,
            therapist_id="PT-NEURO-01"
        )
        self.assertEqual(assessment.total_score, 45)
        self.assertEqual(assessment.dependency_level, "SEVERE_DEPENDENCY")

    def test_range_of_motion_and_cardiac_rehab(self):
        """Verify ROM logging and cardiac rehabilitation enrollment."""
        rom = self.engine.record_range_of_motion(
            patient_id="PAT-ORTHO-09",
            joint_name="Right Knee",
            movement="Flexion",
            active_deg=85.0,
            passive_deg=95.0,
            normal_deg=135.0,
            vas_pain=4,
            therapist_id="PT-ORTHO-01"
        )
        self.assertEqual(rom.active_rom_degrees, 85.0)
        self.assertEqual(rom.vas_pain_score, 4)

        cardiac = self.engine.enroll_cardiac_rehab(
            patient_id="PAT-POST-CABG-01",
            phase=2,
            ejection_fraction_pct=45.0,
            met_target=5.0,
            cardiologist_id="DOC-CARDIO-01"
        )
        self.assertEqual(cardiac["phase"], 2)
        self.assertTrue(cardiac["ecg_telemetry_required"])


if __name__ == "__main__":
    unittest.main()
