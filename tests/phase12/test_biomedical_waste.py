"""
Test Suite: test_biomedical_waste.py
Phase 12: Hospital Operations — Biomedical Waste Management (BMW Rules 2016) (Gap 11)
Mandate / Quality Gate 2:
  - Color-coded waste generation recording at source (Yellow, Red, White sharps, Blue).
  - Barcoded bag tracking from ward generation to central storage to CBWTF truck.
  - CBWTF manifest generation with truck scale reconciliation & weight discrepancy alarm (> 5%).
  - Inviolable Quality Gate 2: Complete SPCB annual Form IV statutory report generator
    matching barcoded pickup weights with zero unaccounted waste and SHA-256 seal.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from biomedical_waste_engine import (
    BiomedicalWasteEngine,
    BMWCategory,
    BagStatus,
    BMWError,
)


class TestBiomedicalWasteEngine(unittest.TestCase):

    def setUp(self):
        self.engine = BiomedicalWasteEngine(
            hospital_name="AIIMS Tertiary Health Center",
            spcb_reg_no="SPCB/BMW/2026/8941",
        )

    def test_waste_generation_and_cbwtf_manifest_workflow(self):
        """Tests end-to-end recording of BMW bags and CBWTF dispatch manifest."""
        # 1. Record generation at ward sources
        bag_yellow = self.engine.record_waste_generation(
            bag_barcode="BMW-YEL-OT1-001",
            category=BMWCategory.YELLOW,
            department_id="OPERATION_THEATRE",
            weight_kg=12.5,
            generator_staff_id="NURSE-OT-1",
        )
        bag_red = self.engine.record_waste_generation(
            bag_barcode="BMW-RED-ICU-002",
            category=BMWCategory.RED,
            department_id="INTENSIVE_CARE",
            weight_kg=8.4,
            generator_staff_id="NURSE-ICU-2",
        )
        bag_white = self.engine.record_waste_generation(
            bag_barcode="BMW-WHT-ED-003",
            category=BMWCategory.WHITE_SHARPS,
            department_id="EMERGENCY_DEPT",
            weight_kg=3.1,
            generator_staff_id="NURSE-ED-3",
        )
        bag_blue = self.engine.record_waste_generation(
            bag_barcode="BMW-BLU-LAB-004",
            category=BMWCategory.BLUE,
            department_id="CENTRAL_LAB",
            weight_kg=5.2,
            generator_staff_id="TECH-LAB-4",
        )

        total_source_weight = 12.5 + 8.4 + 3.1 + 5.2  # 29.2 kg

        # 2. Check in at central 48-hour storage
        for barcode in ["BMW-YEL-OT1-001", "BMW-RED-ICU-002", "BMW-WHT-ED-003", "BMW-BLU-LAB-004"]:
            self.engine.receive_at_central_waste_storage(barcode, receiver_staff_id="SANITATION-SUP-1")

        # 3. CBWTF vehicle pickup with scale weight 29.1 kg (variance 0.1 kg / 0.34% -> within 5% limit)
        manifest = self.engine.generate_cbwtf_dispatch_manifest(
            manifest_id="MNF-2026-0917-01",
            bag_barcodes=["BMW-YEL-OT1-001", "BMW-RED-ICU-002", "BMW-WHT-ED-003", "BMW-BLU-LAB-004"],
            cbwtf_agency_name="CleanGreen Bio-Waste Solutions Pvt Ltd",
            vehicle_number="DL-1GC-4488",
            driver_name="Ramesh Kumar",
            driver_license="DL-9920140023",
            actual_truck_scale_weight_kg=29.1,
        )

        self.assertEqual(manifest.total_manifest_weight_kg, 29.2)
        self.assertEqual(manifest.actual_truck_scale_weight_kg, 29.1)
        self.assertFalse(manifest.is_discrepancy_alert)
        self.assertTrue(len(manifest.manifest_sha256) == 64)

        # Confirm bags updated to handed over
        self.assertEqual(bag_yellow.status, BagStatus.HANDED_OVER_CBWTF)
        self.assertEqual(bag_yellow.cbwtf_manifest_id, "MNF-2026-0917-01")

    def test_cbwtf_weight_discrepancy_alarm(self):
        """Tests discrepancy alarm when truck weight deviates > 5% from source registered weight."""
        self.engine.record_waste_generation(
            bag_barcode="BMW-YEL-DISC-001",
            category=BMWCategory.YELLOW,
            department_id="ONCOLOGY",
            weight_kg=20.0,
            generator_staff_id="NURSE-ONCO-1",
        )

        # Handover where truck scale reports only 17.5 kg (2.5 kg / 12.5% loss -> exceeds 5% threshold)
        manifest = self.engine.generate_cbwtf_dispatch_manifest(
            manifest_id="MNF-DISCREPANCY-002",
            bag_barcodes=["BMW-YEL-DISC-001"],
            cbwtf_agency_name="CleanGreen Bio-Waste Solutions",
            vehicle_number="DL-1GC-4488",
            driver_name="Ramesh Kumar",
            driver_license="DL-9920140023",
            actual_truck_scale_weight_kg=17.5,
        )
        self.assertTrue(manifest.is_discrepancy_alert)
        self.assertEqual(manifest.weight_discrepancy_pct, 12.5)

    def test_quality_gate_2_spcb_annual_form_iv_report(self):
        """
        Quality Gate 2:
        Biomedical waste module generates complete SPCB annual Form IV report
        matching barcoded pickup weights with zero unaccounted waste and SHA-256 seal.
        """
        current_year = 2026

        # Register bags across categories
        self.engine.record_waste_generation("BMW-YEL-01", BMWCategory.YELLOW, "SURGERY", 50.0, "STAFF-1")
        self.engine.record_waste_generation("BMW-RED-02", BMWCategory.RED, "ICU", 35.0, "STAFF-2")
        self.engine.record_waste_generation("BMW-WHT-03", BMWCategory.WHITE_SHARPS, "EMERGENCY", 15.0, "STAFF-3")
        self.engine.record_waste_generation("BMW-BLU-04", BMWCategory.BLUE, "OPD", 20.0, "STAFF-4")

        # Hand over all 4 bags to CBWTF
        self.engine.generate_cbwtf_dispatch_manifest(
            manifest_id="MNF-ANNUAL-001",
            bag_barcodes=["BMW-YEL-01", "BMW-RED-02", "BMW-WHT-03", "BMW-BLU-04"],
            cbwtf_agency_name="CleanGreen CBWTF Facility",
            vehicle_number="DL-1GC-9911",
            driver_name="Suresh Singh",
            driver_license="DL-881920",
            actual_truck_scale_weight_kg=120.0,
        )

        # Generate Annual Form IV Report
        report = self.engine.generate_spcb_annual_form_iv_report(reporting_year=current_year)

        self.assertEqual(report["form_name"], "FORM_IV_ANNUAL_REPORT_BMWM_RULES_2016")
        self.assertEqual(report["reporting_year"], current_year)
        self.assertEqual(report["hospital_name"], "AIIMS Tertiary Health Center")
        self.assertEqual(report["total_bags_logged"], 4)
        self.assertEqual(report["total_waste_generated_kg"], 120.0)
        self.assertEqual(report["total_waste_dispatched_to_cbwtf_kg"], 120.0)

        # Category reconciliation
        self.assertEqual(report["category_summary_kg"][BMWCategory.YELLOW.value], 50.0)
        self.assertEqual(report["category_summary_kg"][BMWCategory.RED.value], 35.0)
        self.assertEqual(report["category_summary_kg"][BMWCategory.WHITE_SHARPS.value], 15.0)
        self.assertEqual(report["category_summary_kg"][BMWCategory.BLUE.value], 20.0)

        self.assertTrue(report["spcb_compliance_certified"])
        self.assertTrue(len(report["statutory_seal_sha256"]) == 64)


if __name__ == "__main__":
    unittest.main()
