"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Test Suite: test_hai_device_surveillance.py
Validates:
  - Quality Gate 3: Central line removal automatically decrements device-day counter and logs duration
  - Device insertion, active tracking, and removal workflow
  - NHSN / NABH HAI rate calculations (CLABSI, CAUTI, VAP per 1,000 device-days)
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from hai_device_surveillance import (
    HAIDeviceSurveillanceEngine, InvasiveDeviceRecord
)


class TestHAIDeviceSurveillanceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = HAIDeviceSurveillanceEngine()
        self.now = datetime.now(timezone.utc)

    def test_quality_gate_central_line_removal_decrements_counter_and_logs_duration(self):
        """
        Phase 07 Quality Gate 3:
        Central line removal automatically decrements device-day counter and logs duration.
        """
        patient_id = "PAT-ICU-301"
        device_id = "CVC-LINE-001"
        inserted_time = self.now - timedelta(days=5, hours=6)  # 126 hours ago

        # 1. Insert central line
        self.engine.record_device_insertion(
            device_id=device_id,
            patient_id=patient_id,
            device_type="CENTRAL_LINE",
            insertion_site="Right Internal Jugular Vein",
            inserted_by="DOC-INTENSIVIST-01",
            inserted_at=inserted_time
        )

        self.assertEqual(self.engine.get_active_device_count("CENTRAL_LINE"), 1)
        self.assertIn(device_id, self.engine.patient_active_devices[patient_id])

        # 2. Removal event
        removed_record = self.engine.record_device_removal(
            device_id=device_id,
            removed_by="NURSE-ICU-05",
            removal_reason="Suspected line infection / catheter colonization",
            removed_at=self.now
        )

        # Active counter decremented to 0
        self.assertEqual(self.engine.get_active_device_count("CENTRAL_LINE"), 0)
        self.assertNotIn(device_id, self.engine.patient_active_devices[patient_id])

        # Duration logged
        self.assertFalse(removed_record.is_active)
        self.assertEqual(removed_record.removed_by, "NURSE-ICU-05")
        self.assertAlmostEqual(removed_record.total_device_hours, 126.0, delta=0.5)
        self.assertEqual(removed_record.total_device_days, 6)  # 126h = 5.25 days -> 6 calendar/24h intervals

    def test_hai_infection_rate_calculations(self):
        """Verify NHSN/NABH CLABSI, CAUTI, and VAP rate calculations per 1,000 device-days."""
        # Log 2 CLABSI incidents and 1 CAUTI incident
        self.engine.log_hai_infection(
            patient_id="PAT-ICU-01",
            infection_type="CLABSI",
            pathogen_isolated="Staphylococcus epidermidis",
            diagnosed_by="DOC-ID-01"
        )
        self.engine.log_hai_infection(
            patient_id="PAT-ICU-02",
            infection_type="CLABSI",
            pathogen_isolated="Klebsiella pneumoniae",
            diagnosed_by="DOC-ID-01",
            is_mdr=True
        )
        self.engine.log_hai_infection(
            patient_id="PAT-ICU-03",
            infection_type="CAUTI",
            pathogen_isolated="Pseudomonas aeruginosa",
            diagnosed_by="DOC-ID-01"
        )

        # Benchmarks: CLABSI (1.5), CAUTI (2.0), VAP (2.5)
        # Denominators: 1,000 Central Line days, 1,000 Catheter days, 500 Ventilator days
        rates = self.engine.calculate_hai_rates(
            total_central_line_days=1000,
            total_catheter_days=1000,
            total_ventilator_days=500
        )

        # CLABSI: 2 / 1000 * 1000 = 2.0 (Exceeds benchmark 1.5!)
        self.assertEqual(rates["CLABSI"].rate_per_1000_device_days, 2.0)
        self.assertTrue(rates["CLABSI"].is_exceeded)

        # CAUTI: 1 / 1000 * 1000 = 1.0 (Within benchmark 2.0)
        self.assertEqual(rates["CAUTI"].rate_per_1000_device_days, 1.0)
        self.assertFalse(rates["CAUTI"].is_exceeded)

        # VAP: 0 / 500 * 1000 = 0.0
        self.assertEqual(rates["VAP"].rate_per_1000_device_days, 0.0)
        self.assertFalse(rates["VAP"].is_exceeded)


if __name__ == "__main__":
    unittest.main()
