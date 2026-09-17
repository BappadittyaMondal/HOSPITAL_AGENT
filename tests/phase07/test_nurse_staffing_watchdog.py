"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Test Suite: test_nurse_staffing_watchdog.py
Validates:
  - Acuity-based nurse-to-patient staffing ratio evaluation (ICU 1:1, HDU 1:2, General 1:5)
  - Understaffing deficit detection and CNO automated alerting (Gap 6)
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from nurse_staffing_watchdog import NurseStaffingWatchdogEngine


class TestNurseStaffingWatchdogEngine(unittest.TestCase):

    def setUp(self):
        self.engine = NurseStaffingWatchdogEngine()

    def test_icu_staffing_evaluation_and_deficit_alert(self):
        """Verify ICU 1:1 staffing ratio triggers critical alert when breached."""
        # ICU with 10 occupied beds but only 6 active nurses -> ratio 1.67:1 (Breach!)
        # Required nurses = 10 -> Deficit = 4
        snapshot = self.engine.evaluate_ward_staffing(
            ward_id="ICU-MAIN",
            ward_type="ICU",
            active_nurse_count=6,
            occupied_bed_count=10
        )

        self.assertTrue(snapshot.is_breached)
        self.assertEqual(snapshot.current_patient_per_nurse_ratio, 1.67)
        self.assertEqual(snapshot.deficit_nurses, 4)
        self.assertEqual(snapshot.alert_level, "CRITICAL_DEFICIT")

        # Verify CNO alert was recorded
        self.assertEqual(len(self.engine.cno_alerts), 1)
        alert = self.engine.cno_alerts[0]
        self.assertEqual(alert["ward_id"], "ICU-MAIN")
        self.assertEqual(alert["recipient"], "CHIEF_NURSING_OFFICER")
        self.assertIn("Staff deficit: 4 nurse(s) urgently required", alert["message"])

    def test_general_ward_normal_staffing(self):
        """Verify compliant General Ward staffing (1:5 standard) reports normal status."""
        # General Ward with 20 beds and 5 nurses -> ratio 4.0:1 (< 5.0 -> Compliant)
        snapshot = self.engine.evaluate_ward_staffing(
            ward_id="WARD-MED-4",
            ward_type="GENERAL",
            active_nurse_count=5,
            occupied_bed_count=20
        )
        self.assertFalse(snapshot.is_breached)
        self.assertEqual(snapshot.current_patient_per_nurse_ratio, 4.0)
        self.assertEqual(snapshot.deficit_nurses, 0)
        self.assertEqual(snapshot.alert_level, "NORMAL")
        self.assertEqual(len(self.engine.cno_alerts), 0)


if __name__ == "__main__":
    unittest.main()
