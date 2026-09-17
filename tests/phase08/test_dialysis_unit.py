"""
PROJECT "HOSPITAL" — PHASE 08: CRITICAL CARE
Test Suite: test_dialysis_unit.py
Validates:
  - Quality Gate 2: System rejects assignment of a Hepatitis B-positive patient to a general dialysis machine
  - Seronegative cross-contamination prevention
  - Reverse osmosis (RO) water quality monitoring and contamination stops
  - CRRT effluent clearance dose calculation
"""

import unittest
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from dialysis_unit_engine import (
    DialysisUnitEngine, DialysisIsolationBreachError, ROWaterContaminationError
)


class TestDialysisUnitEngine(unittest.TestCase):

    def setUp(self):
        self.engine = DialysisUnitEngine()

        # Register machines: 1 general, 1 dedicated HepB, 1 dedicated HepC
        self.engine.register_machine("MACH-GEN-01", "BAY-01", "GENERAL")
        self.engine.register_machine("MACH-HEPB-01", "BAY-ISO-B", "DEDICATED_HEPB")
        self.engine.register_machine("MACH-HEPC-01", "BAY-ISO-C", "DEDICATED_HEPC")

    def test_quality_gate_hepatitis_b_assignment_to_general_machine_strictly_rejected(self):
        """
        Phase 08 Quality Gate 2:
        System rejects assignment of a Hepatitis B-positive patient to a general dialysis machine.
        """
        patient_id = "PAT-HEPB-9901"

        # 1. Attempting to allocate HBsAg+ patient to GENERAL machine -> Strictly Rejected!
        with self.assertRaises(DialysisIsolationBreachError) as ctx1:
            self.engine.allocate_dialysis_machine(
                patient_id=patient_id,
                machine_id="MACH-GEN-01",
                patient_hbsag_positive=True,  # HBsAg positive!
                patient_hcv_positive=False,
                technician_id="TECH-RENAL-01"
            )

        self.assertIn("CRITICAL ISOLATION BREACH", str(ctx1.exception))
        self.assertIn("Hepatitis B Surface Antigen (HBsAg) POSITIVE", str(ctx1.exception))
        self.assertIn("strictly rejected", str(ctx1.exception))

        # 2. Assigning HBsAg+ patient to DEDICATED_HEPB machine -> SUCCEEDS
        session = self.engine.allocate_dialysis_machine(
            patient_id=patient_id,
            machine_id="MACH-HEPB-01",
            patient_hbsag_positive=True,
            patient_hcv_positive=False,
            technician_id="TECH-RENAL-01"
        )
        self.assertEqual(session["status"], "ACTIVE_SESSION")
        self.assertEqual(session["machine_type"], "DEDICATED_HEPB")

    def test_seronegative_patient_blocked_from_dedicated_hepatitis_station(self):
        """Verify seronegative patient cannot be assigned to a HepB isolation machine."""
        with self.assertRaises(DialysisIsolationBreachError) as ctx:
            self.engine.allocate_dialysis_machine(
                patient_id="PAT-CLEAN-01",
                machine_id="MACH-HEPB-01",  # Dedicated HepB!
                patient_hbsag_positive=False,
                patient_hcv_positive=False,
                technician_id="TECH-RENAL-01"
            )
        self.assertIn("CROSS-CONTAMINATION HAZARD", str(ctx.exception))

    def test_ro_water_contamination_halts_dialysis(self):
        """Verify RO water chloramine or endotoxin breach blocks dialysis allocation."""
        # Log dangerous chloramine level (0.25 mg/L > max safe 0.10 mg/L)
        self.engine.log_ro_water_test(
            endotoxin_eu_per_ml=0.05,
            total_chloramine_mg_l=0.25,  # Contaminated!
            conductivity_us_cm=15.0,
            technician_id="TECH-WATER-01"
        )
        self.assertFalse(self.engine.is_water_supply_safe())

        with self.assertRaises(ROWaterContaminationError) as ctx:
            self.engine.allocate_dialysis_machine(
                patient_id="PAT-NORMAL-02",
                machine_id="MACH-GEN-01",
                patient_hbsag_positive=False,
                patient_hcv_positive=False,
                technician_id="TECH-RENAL-01"
            )
        self.assertIn("RO WATER SAFETY HAZARD", str(ctx.exception))

    def test_crrt_kdigo_effluent_dose_calculation(self):
        """Verify CRRT effluent dose calculation against KDIGO target (20-25 mL/kg/h)."""
        # Weight 70kg, Dialysate 1000 mL/h, Replacement 500 mL/h, UF 200 mL/h
        # Total effluent = 1700 mL/h -> 1700 / 70 = 24.3 mL/kg/h (Within target!)
        res = self.engine.calculate_crrt_effluent_dose(
            dialysate_flow_ml_hr=1000.0,
            replacement_flow_ml_hr=500.0,
            ultrafiltration_ml_hr=200.0,
            patient_weight_kg=70.0
        )
        self.assertEqual(res["effluent_dose_ml_kg_hr"], 24.3)
        self.assertTrue(res["is_within_kdigo_target"])


if __name__ == "__main__":
    unittest.main()
