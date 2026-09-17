"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Test Suite: test_nicu_pediatric.py
Validates:
  - Quality Gate 3: Neonatal drug order validates against infant weight in grams, blocking 10x adult dose errors
  - Precision neonatal weight calculations
  - Incubator microenvironment telemetry alarms
  - Retinopathy of Prematurity (ROP) screening eligibility
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from nicu_pediatric_engine import (
    NICUPediatricEngine, NeonatalDoseToxicityError
)


class TestNICUPediatricEngine(unittest.TestCase):

    def setUp(self):
        self.engine = NICUPediatricEngine()
        self.now = datetime.now(timezone.utc)

        # Register preterm infant: 28 weeks GA, birth weight 1100g, current weight 1200g (1.2 kg)
        self.patient_id = "NEO-28W-1200G"
        self.engine.register_neonate(
            patient_id=self.patient_id,
            gestational_age_weeks=28.0,
            birth_weight_grams=1100.0,
            current_weight_grams=1200.0,
            dob=self.now - timedelta(days=14)
        )

    def test_quality_gate_neonatal_10x_adult_overdose_mechanically_blocked(self):
        """
        Phase 08 Quality Gate 3:
        Neonatal drug order validates against exact infant weight in grams,
        preventing 10x adult dose calculation errors.
        """
        # Ampicillin formulary limit: max 100 mg/kg/dose.
        # For a 1200g (1.2 kg) infant, maximum allowable dose is:
        # 100 mg/kg * 1.2 kg = 120 mg.
        # If an adult dose of 1000 mg (1 g) is erroneously ordered (an 8.3x overdose):
        with self.assertRaises(NeonatalDoseToxicityError) as ctx:
            self.engine.validate_and_calculate_dose(
                patient_id=self.patient_id,
                drug_id="DRUG-AMPICILLIN",
                prescribed_absolute_dose_mg=1000.0,  # Adult dose error!
                clinician_id="DOC-RESIDENT-01"
            )

        self.assertIn("FATAL NEONATAL OVERDOSE BLOCK", str(ctx.exception))
        self.assertIn("weighing 1200.0g", str(ctx.exception))
        self.assertIn("Maximum safe limit is 100.0 mg/kg (120.0 mg max)", str(ctx.exception))

    def test_safe_neonatal_weight_based_dosing_approved(self):
        """Verify compliant weight-based neonatal dose passes validation."""
        # Prescribing 60 mg Ampicillin (50 mg/kg for 1.2 kg infant) -> Safe!
        result = self.engine.validate_and_calculate_dose(
            patient_id=self.patient_id,
            drug_id="DRUG-AMPICILLIN",
            prescribed_absolute_dose_mg=60.0,
            clinician_id="DOC-NEONATOLOGIST-01"
        )
        self.assertEqual(result["status"], "APPROVED_SAFE_DOSE")
        self.assertEqual(result["effective_mg_per_kg"], 50.0)
        self.assertEqual(result["infant_weight_kg"], 1.2)

    def test_incubator_cold_stress_and_humidity_telemetry(self):
        """Verify incubator cold stress alarm triggers when skin temp < 36.5°C."""
        # Cold stress: skin temp 35.8°C, humidity 50%
        telemetry = self.engine.monitor_incubator_environment(
            incubator_id="INC-01",
            air_temp_c=34.0,
            skin_temp_c=35.8,
            relative_humidity_pct=50.0,
            is_elbw=True
        )
        self.assertFalse(telemetry["in_safe_range"])
        self.assertEqual(len(telemetry["alarms"]), 2)
        self.assertIn("COLD STRESS ALARM", telemetry["alarms"][0])
        self.assertIn("HUMIDITY DEFICIT", telemetry["alarms"][1])

    def test_rop_screening_eligibility(self):
        """Verify ROP screening eligibility for infant born <= 30 weeks GA."""
        rop_eval = self.engine.evaluate_rop_screening_eligibility(self.patient_id, as_of_time=self.now)
        self.assertTrue(rop_eval["is_eligible_for_rop"])
        self.assertEqual(rop_eval["gestational_age_weeks"], 28.0)
        self.assertIsNotNone(rop_eval["screening_due_date"])


if __name__ == "__main__":
    unittest.main()
