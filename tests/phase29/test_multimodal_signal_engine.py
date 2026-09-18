#!/usr/bin/env python3
"""
PROJECT 'HOSPITAL' — PHASE 29: MULTI-MODAL BEDSIDE DIAGNOSTIC SIGNAL TEST SUITE
Module: tests/phase29/test_multimodal_signal_engine.py
Validates:
  1. Bazett and Fridericia QTc calculations across bradycardia and tachycardia.
  2. Anterior STEMI detection with LAD culprit identification.
  3. Inferior STEMI detection with RV preload nitrate contraindication hard-stop.
  4. Automatic Cath Lab activation and 90-minute Door-to-Balloon target.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../services/core-api')))
from multimodal_signal_engine import (
    MultiModalSignalEngine,
    LeadVoltageData,
    CardiacRhythmType,
    STEMIAnatomy
)


class TestMultiModalSignalEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MultiModalSignalEngine()

    def test_qtc_calculation_formulas(self):
        """Verify Bazett and Fridericia mathematical QTc calculations."""
        # HR = 60 bpm -> RR = 1.0s. At RR=1.0s, QTc == QT
        baz, frid = self.engine.calculate_qtc(qt_ms=400.0, heart_rate_bpm=60)
        self.assertEqual(baz, 400.0)
        self.assertEqual(frid, 400.0)

        # HR = 100 bpm -> RR = 0.60s. sqrt(0.60) = 0.7746 -> QTc Bazett = 400 / 0.7746 = 516.4 ms
        baz100, frid100 = self.engine.calculate_qtc(qt_ms=400.0, heart_rate_bpm=100)
        self.assertAlmostEqual(baz100, 516.4, delta=0.5)
        self.assertTrue(frid100 < baz100)  # Bazett known to over-correct in tachycardia

    def test_anterior_stemi_detection_and_cath_lab_activation(self):
        """Verify anterior STEMI triggers LAD culprit, Cath Lab activation, and 90-min timer."""
        leads = {
            "I": LeadVoltageData("I", st_elevation_mm=0.2),
            "II": LeadVoltageData("II", st_elevation_mm=0.0),
            "III": LeadVoltageData("III", st_elevation_mm=0.0),
            "aVL": LeadVoltageData("aVL", st_elevation_mm=0.5),
            "aVF": LeadVoltageData("aVF", st_elevation_mm=0.0),
            "V1": LeadVoltageData("V1", st_elevation_mm=2.5),
            "V2": LeadVoltageData("V2", st_elevation_mm=3.2),
            "V3": LeadVoltageData("V3", st_elevation_mm=2.8),
            "V4": LeadVoltageData("V4", st_elevation_mm=1.0),
            "V5": LeadVoltageData("V5", st_elevation_mm=0.2),
            "V6": LeadVoltageData("V6", st_elevation_mm=0.0),
        }
        res = self.engine.analyze_12_lead_ecg(
            patient_id="PAT-STEMI-ANT-01",
            heart_rate_bpm=88,
            pr_ms=160.0,
            qrs_ms=92.0,
            qt_ms=380.0,
            leads=leads,
            patient_gender="MALE",
            patient_age=52
        )
        self.assertTrue(res.stemi_present)
        self.assertEqual(res.stemi_anatomy, STEMIAnatomy.ANTERIOR_WALL)
        self.assertIn("LAD", res.culprit_vessel_presumed)
        self.assertTrue(res.cath_lab_activation_required)
        self.assertEqual(res.door_to_balloon_target_minutes, 90)
        self.assertFalse(res.nitrate_contraindicated)

    def test_inferior_stemi_triggers_nitrate_contraindication(self):
        """Verify inferior STEMI triggers nitrate contraindication due to RV infarction risk."""
        leads = {
            "I": LeadVoltageData("I", st_elevation_mm=0.0, st_depression_mm=1.2),
            "II": LeadVoltageData("II", st_elevation_mm=2.2),
            "III": LeadVoltageData("III", st_elevation_mm=3.0),
            "aVL": LeadVoltageData("aVL", st_elevation_mm=0.0, st_depression_mm=1.5),
            "aVF": LeadVoltageData("aVF", st_elevation_mm=2.5),
            "V1": LeadVoltageData("V1", st_elevation_mm=0.0),
            "V2": LeadVoltageData("V2", st_elevation_mm=0.0),
            "V3": LeadVoltageData("V3", st_elevation_mm=0.0),
            "V4": LeadVoltageData("V4", st_elevation_mm=0.0),
            "V5": LeadVoltageData("V5", st_elevation_mm=0.0),
            "V6": LeadVoltageData("V6", st_elevation_mm=0.0),
        }
        res = self.engine.analyze_12_lead_ecg(
            patient_id="PAT-STEMI-INF-01",
            heart_rate_bpm=64,
            pr_ms=180.0,
            qrs_ms=88.0,
            qt_ms=410.0,
            leads=leads,
            patient_gender="FEMALE",
            patient_age=61
        )
        self.assertTrue(res.stemi_present)
        self.assertEqual(res.stemi_anatomy, STEMIAnatomy.INFERIOR_WALL)
        self.assertIn("RCA", res.culprit_vessel_presumed)
        self.assertTrue(res.cath_lab_activation_required)
        self.assertTrue(res.nitrate_contraindicated)


if __name__ == '__main__':
    unittest.main()
