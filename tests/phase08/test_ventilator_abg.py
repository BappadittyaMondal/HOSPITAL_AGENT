"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Test Suite: test_ventilator_abg.py
Validates:
  - Rapid Shallow Breathing Index (RSBI) weaning evaluator
  - Arterial Blood Gas (ABG) automated interpretation
  - Winter's formula compensation & Berlin ARDS P/F classification
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from ventilator_abg_engine import VentilatorABGEngine


class TestVentilatorABGEngine(unittest.TestCase):

    def setUp(self):
        self.engine = VentilatorABGEngine()

    def test_rsbi_weaning_readiness(self):
        """Verify RSBI calculation and weaning readiness threshold (< 105)."""
        # Patient A: RR 18 breaths/min, VT 450 mL (0.45 L) -> RSBI = 18 / 0.45 = 40.0 (< 105 -> Ready)
        res_a = self.engine.calculate_rsbi("PAT-VENT-01", respiratory_rate=18.0, tidal_volume_ml=450.0)
        self.assertEqual(res_a.rsbi_score, 40.0)
        self.assertTrue(res_a.weaning_ready)
        self.assertIn("Weaning readiness criteria MET", res_a.interpretation)

        # Patient B: RR 32 breaths/min, VT 250 mL (0.25 L) -> RSBI = 32 / 0.25 = 128.0 (>= 105 -> Failure risk)
        res_b = self.engine.calculate_rsbi("PAT-VENT-02", respiratory_rate=32.0, tidal_volume_ml=250.0)
        self.assertEqual(res_b.rsbi_score, 128.0)
        self.assertFalse(res_b.weaning_ready)
        self.assertIn("weaning failure", res_b.interpretation)

    def test_abg_high_anion_gap_metabolic_acidosis_with_winters_formula(self):
        """Verify ABG interpretation of DKA / lactic acidosis with Winter's formula compensation."""
        # Patient with DKA:
        # pH = 7.18 (Acidemia), HCO3 = 10 mEq/L, PaCO2 = 23 mmHg
        # Na = 138, Cl = 100 -> Anion Gap = 138 - (100 + 10) = 28 mEq/L (HIGH ANION GAP)
        # Winter's formula: Expected PaCO2 = 1.5 * 10 + 8 = 23 mmHg (+/- 2, so 21 - 25)
        # Measured PaCO2 is 23 mmHg -> ADEQUATELY COMPENSATED!
        # PaO2 = 90 on FiO2 21% -> P/F ratio = 90 / 0.21 = 428.6 (NONE)
        abg = self.engine.interpret_abg(
            ph=7.18,
            paco2=23.0,
            pao2=90.0,
            hco3=10.0,
            fio2=0.21,
            sodium_na=138.0,
            chloride_cl=100.0
        )
        self.assertEqual(abg.anion_gap, 28.0)
        self.assertEqual(abg.primary_disorder, "HIGH ANION GAP METABOLIC ACIDOSIS")
        self.assertIn("ADEQUATELY COMPENSATED", abg.compensation_status)
        self.assertEqual(abg.ards_severity, "NONE")

    def test_abg_ards_hypoxemia_berlin_classification(self):
        """Verify Berlin definition ARDS P/F ratio severity."""
        # PaO2 65 mmHg on 80% FiO2 (0.80) -> P/F = 65 / 0.8 = 81.25 (< 100 -> SEVERE ARDS)
        abg = self.engine.interpret_abg(
            ph=7.32,
            paco2=48.0,
            pao2=65.0,
            hco3=24.0,
            fio2=0.80
        )
        self.assertEqual(abg.pf_ratio, 81.2)
        self.assertEqual(abg.ards_severity, "SEVERE_ARDS")


if __name__ == "__main__":
    unittest.main()
