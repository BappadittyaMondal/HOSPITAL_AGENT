"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Test Suite: test_obstetrics_labor.py
Validates:
  - Quality Gate 1: Partograph triggers high-priority alert when cervical dilatation crosses the action line
  - Normal progressive labor recording
  - Category 1 Emergency C-Section DDI countdown (< 30 min)
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from obstetrics_labor_engine import (
    ObstetricsLaborEngine, PartographActionLineBreachError
)


class TestObstetricsLaborEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ObstetricsLaborEngine()
        self.now = datetime.now(timezone.utc)

    def test_quality_gate_partograph_action_line_breach_triggers_critical_alert(self):
        """
        Phase 10 Quality Gate 1:
        Partograph triggers high-priority alert when cervical dilatation crosses the action line.
        """
        patient_id = "PAT-LABOR-01"

        # Record labor start at 4 cm at hour 0 (Alert line = 4cm)
        self.engine.log_partograph_progress(
            patient_id=patient_id,
            hours_in_active_labor=0.0,
            cervical_dilatation_cm=4.0,
            fetal_heart_rate_bpm=140.0,
            contractions_per_10min=3
        )

        # At hour 5, alert line expected = 9.0 cm. Action line expected = 5.0 cm (4h lag).
        # Patient's cervical dilatation has remained completely arrested at 4.5 cm (<= action line 5.0cm)!
        with self.assertRaises(PartographActionLineBreachError) as ctx:
            self.engine.log_partograph_progress(
                patient_id=patient_id,
                hours_in_active_labor=5.0,
                cervical_dilatation_cm=4.5,  # Arrested progress crossing action line!
                fetal_heart_rate_bpm=145.0,
                contractions_per_10min=2
            )

        self.assertIn("HIGH-PRIORITY OBSTETRIC ALERT", str(ctx.exception))
        self.assertIn("CROSSED THE WHO PARTOGRAPH ACTION LINE", str(ctx.exception))
        self.assertIn("Arrest of labor", str(ctx.exception))

    def test_normal_partograph_progression(self):
        """Verify normal labor progression along the alert line generates clean records."""
        patient_id = "PAT-LABOR-02"
        # 4 cm at hour 0 -> 6 cm at hour 2 -> 8 cm at hour 4 -> 10 cm at hour 6
        entry_0 = self.engine.log_partograph_progress(patient_id, 0.0, 4.0, 135.0, 3)
        self.assertFalse(entry_0.action_line_breached)

        entry_2 = self.engine.log_partograph_progress(patient_id, 2.0, 6.0, 138.0, 4)
        self.assertFalse(entry_2.action_line_breached)

        entry_4 = self.engine.log_partograph_progress(patient_id, 4.0, 8.0, 142.0, 4)
        self.assertFalse(entry_4.action_line_breached)

    def test_emergency_csection_ddi_tracking(self):
        """Verify Category 1 Emergency C-Section Decision-to-Delivery Interval countdown (< 30 min)."""
        case = self.engine.trigger_category_1_emergency_csection(
            case_id="CSEC-CASE-99",
            patient_id="PAT-LABOR-03",
            indication="Prolonged fetal bradycardia (FHR 70 bpm) and placental abruption",
            decision_time=self.now
        )
        self.assertEqual(case.category, 1)
        self.assertEqual(case.target_ddi_minutes, 30.0)

        # Delivery achieved in 22 minutes
        delivery_time = self.now + timedelta(minutes=22)
        completed_case = self.engine.record_delivery_time("CSEC-CASE-99", delivery_time)
        self.assertEqual(completed_case.actual_ddi_minutes, 22.0)
        self.assertFalse(completed_case.is_breached)


if __name__ == "__main__":
    unittest.main()
