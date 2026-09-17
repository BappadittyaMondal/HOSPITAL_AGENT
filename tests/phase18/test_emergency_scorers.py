#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18: EMERGENCY SCORERS & SPECIALIZED PROTOCOLS TEST SUITE
====================================================================================================
Tests:
1. Glasgow Coma Scale (GCS) calculation & GCS <= 8 airway loss flag.
2. FAST acute stroke screening & IV thrombolytic time window.
3. Pediatric Broselow weight-based emergency dosing table.
4. Anaphylaxis emergency IM Adrenaline 1:1000 calculation & posture rule.
5. Burns Rule of Nines & Parkland Fluid Resuscitation formula.
"""
import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from clinical_emergency_scorers import (
    calculate_glasgow_coma_scale,
    evaluate_fast_stroke,
    calculate_pediatric_emergency_doses,
    calculate_anaphylaxis_protocol,
    calculate_parkland_burns_fluid
)


class TestEmergencyScorers(unittest.TestCase):

    def test_gcs_score_and_airway_compromise_alert(self):
        """Verifies GCS calculation: Eye=2, Verbal=2, Motor=4 -> Total GCS 8 triggers airway compromise alert."""
        gcs = calculate_glasgow_coma_scale(eye_opening=2, verbal_response=2, motor_response=4)
        self.assertEqual(gcs.total_gcs, 8)
        self.assertEqual(gcs.severity, "SEVERE")
        self.assertTrue(gcs.airway_compromised)
        self.assertTrue("Immediate endotracheal intubation" in gcs.clinical_recommendation)

        # Mild GCS (15)
        gcs_normal = calculate_glasgow_coma_scale(eye_opening=4, verbal_response=5, motor_response=6)
        self.assertEqual(gcs_normal.total_gcs, 15)
        self.assertEqual(gcs_normal.severity, "MILD")
        self.assertFalse(gcs_normal.airway_compromised)

    def test_fast_stroke_thrombolytic_window(self):
        """Verifies FAST positive within 3 hours triggers Code Stroke for IV thrombolysis."""
        res = evaluate_fast_stroke(
            facial_droop=True,
            arm_weakness=True,
            speech_difficulty=False,
            onset_hours_ago=2.5
        )
        self.assertTrue(res.is_fast_positive)
        self.assertTrue(res.eligible_for_thrombolysis_window)
        self.assertIn("CODE STROKE", res.action_plan)

    def test_pediatric_emergency_weight_based_dosing(self):
        """Verifies 10kg toddler emergency dosing: Paracetamol 150mg (15mg/kg), Ceftriaxone 750mg."""
        doses = calculate_pediatric_emergency_doses(weight_kg=10.0)
        self.assertEqual(doses.paracetamol_single_dose_mg, 150.0)
        self.assertEqual(doses.ceftriaxone_meningitis_sepsis_mg, 750.0)
        self.assertEqual(doses.salbutamol_nebulization_mg, 2.5)
        self.assertEqual(doses.ors_rehydration_first_4h_ml, 750.0)

    def test_anaphylaxis_adrenaline_protocol(self):
        """Verifies adult anaphylaxis generates 0.5mg IM Adrenaline into mid-anterolateral thigh."""
        protocol = calculate_anaphylaxis_protocol(weight_kg=70.0, is_child=False)
        self.assertEqual(protocol.im_adrenaline_dose_mg, 0.5)
        self.assertEqual(protocol.im_adrenaline_volume_1_to_1000_ml, 0.5)
        self.assertIn("Vastus Lateralis", protocol.recommended_site)
        self.assertTrue(any("KEEP PATIENT FLAT WITH LEGS ELEVATED" in inst for inst in protocol.inviolable_instructions))

    def test_burns_rule_of_nines_parkland_formula(self):
        """Verifies 70kg adult with 30% TBSA burn gets 8400 mL total Parkland fluid (4200 mL in first 8h)."""
        # Parkland formula: 4 mL * 70 kg * 30% TBSA = 8400 mL
        plan = calculate_parkland_burns_fluid(tbsa_percentage=30.0, patient_weight_kg=70.0)
        self.assertEqual(plan.total_24h_fluid_parkland_ml, 8400.0)
        self.assertEqual(plan.first_8h_fluid_ml, 4200.0)
        self.assertEqual(plan.first_8h_rate_ml_per_hour, 525.0)  # 4200 / 8 = 525 mL/h
        self.assertEqual(plan.next_16h_rate_ml_per_hour, 262.5) # 4200 / 16 = 262.5 mL/h
        self.assertIn("Ringer's Lactate", plan.fluid_type)


if __name__ == "__main__":
    unittest.main()
