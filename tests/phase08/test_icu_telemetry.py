"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Test Suite: test_icu_telemetry.py
Validates:
  - Quality Gate 1: Acute hemodynamic collapse triggers ICU bedside audible/visual STAT alert in < 5s
  - High-frequency 1Hz vitals ingestion & MAP calculation
  - qSOFA and SIRS early warning sepsis assessment
"""

import unittest
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from icu_telemetry_sepsis_engine import ICUTelemetrySepsisEngine


class TestICUTelemetrySepsisEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ICUTelemetrySepsisEngine()

    def test_quality_gate_hemodynamic_collapse_triggers_bedside_alert_in_sub_5_seconds(self):
        """
        Phase 08 Quality Gate 1:
        Simulated acute hemodynamic collapse (sudden MAP drop + tachycardia) triggers
        ICU bedside audible and visual alert in < 5 seconds.
        """
        patient_id = "PAT-ICU-8821"
        bed_id = "BED-ICU-04"

        # Baseline vitals: SBP 120, DBP 80 (MAP 93.3), HR 75
        base_res = self.engine.ingest_telemetry_sample(
            patient_id=patient_id,
            bed_id=bed_id,
            hr=75.0,
            spo2=99.0,
            sbp=120.0,
            dbp=80.0
        )
        self.assertFalse(base_res["hemodynamic_collapse"])
        self.assertIsNone(base_res["alert"])

        # Inject Acute Hemodynamic Collapse: SBP 75, DBP 45 -> MAP = (75 + 90)/3 = 55.0 mmHg (< 65)
        # Combined with severe sinus tachycardia HR 135 bpm
        start_time = time.time()
        collapse_res = self.engine.ingest_telemetry_sample(
            patient_id=patient_id,
            bed_id=bed_id,
            hr=135.0,
            spo2=88.0,
            sbp=75.0,
            dbp=45.0
        )
        elapsed_sec = time.time() - start_time

        # Must execute in < 5 seconds (SLA requirement)
        self.assertLess(elapsed_sec, 5.0)
        self.assertTrue(collapse_res["hemodynamic_collapse"])
        self.assertEqual(collapse_res["map"], 55.0)

        # Bedside audible/visual STAT alert verified
        alert = collapse_res["alert"]
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "STAT_CRITICAL")
        self.assertTrue(alert["bedside_alarm_sounded"])
        self.assertTrue(alert["intensivist_notified"])
        self.assertIn("ACUTE HEMODYNAMIC COLLAPSE", alert["trigger_reason"])

    def test_qsofa_sepsis_evaluation(self):
        """Verify qSOFA criteria and high-risk threshold (score >= 2)."""
        # GCS altered (1), RR 24 (1), SBP 95 (1) -> Score = 3 (High risk)
        assessment = self.engine.evaluate_qsofa_score(
            patient_id="PAT-SEPSIS-01",
            altered_mental_status=True,
            respiratory_rate=24.0,
            systolic_bp=95.0
        )
        self.assertEqual(assessment.qsofa_score, 3)
        self.assertTrue(assessment.high_risk_sepsis)

        # Normal: Alert mental status, RR 16, SBP 125 -> Score = 0 (Low risk)
        normal = self.engine.evaluate_qsofa_score(
            patient_id="PAT-STABLE-02",
            altered_mental_status=False,
            respiratory_rate=16.0,
            systolic_bp=125.0
        )
        self.assertEqual(normal.qsofa_score, 0)
        self.assertFalse(normal.high_risk_sepsis)

    def test_sirs_criteria_evaluation(self):
        """Verify SIRS criteria calculation."""
        # Fever 39.1°C, HR 105 bpm, RR 22, WBC 14,500 -> 4 criteria met (SIRS Positive)
        res = self.engine.evaluate_sirs_criteria(
            temperature_c=39.1,
            heart_rate=105.0,
            respiratory_rate=22.0,
            wbc_count_per_ul=14500.0
        )
        self.assertEqual(res["sirs_score"], 4)
        self.assertTrue(res["sirs_positive"])


if __name__ == "__main__":
    unittest.main()
