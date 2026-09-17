"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Test Suite: test_pharmacy_inventory.py
Validates:
  - Drug master formulary registration & LASA Tall Man warnings
  - FEFO (First-Expiry-First-Out) batch allocation
  - Vaccine cold-chain monitoring & excursion quarantine
  - AEFI adverse event reporting
  - Automated reorder point (ROP) calculation (Gap 9, 19)
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from pharmacy_inventory_engine import (
    PharmacyInventoryEngine, DrugMasterItem, InventoryBatch
)


class TestPharmacyInventoryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = PharmacyInventoryEngine()
        self.now = datetime.now(timezone.utc)

    def test_formulary_registration_and_lasa_conflict(self):
        """Verify drug master registration and LASA warning detection."""
        dopamine = DrugMasterItem(
            drug_id="DRUG-DOPAMINE",
            generic_name="Dopamine Hydrochloride",
            brand_names=["Intropin"],
            dosage_form="INJECTION",
            strength="40 mg/mL",
            route="IV",
            schedule="SCHEDULE_H",
            atc_code="C01CA04",
            tall_man_name="DOPamine"
        )
        self.engine.register_drug(dopamine)
        self.assertIn("DRUG-DOPAMINE", self.engine.drug_catalog)

        # Check LASA warning when prescribed alongside Dobutamine
        alerts = self.engine.check_lasa_conflict("DRUG-DOPAMINE", ["DRUG-DOBUTAMINE"])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "CRITICAL")
        self.assertTrue(alerts[0]["co_prescribed"])
        self.assertIn("DOPamine", alerts[0]["tall_man_a"])

    def test_fefo_stock_allocation_prefers_earliest_expiry(self):
        """Verify FEFO picks earliest expiring batch and skips expired batches."""
        drug_id = "DRUG-CEFTRIAXONE"
        self.engine.register_drug(DrugMasterItem(
            drug_id=drug_id,
            generic_name="Ceftriaxone Sodium",
            brand_names=["Rocephin", "Monocef"],
            dosage_form="INJECTION",
            strength="1 g",
            route="IV",
            schedule="SCHEDULE_H1",
            atc_code="J01DD04"
        ))

        # Add batch 1: expires in 30 days, qty = 10
        b1 = InventoryBatch(
            batch_number="BATCH-EARLY-30D",
            drug_id=drug_id,
            quantity_on_hand=10,
            expiry_date=self.now + timedelta(days=30),
            received_date=self.now - timedelta(days=10),
            cost_per_unit=50.0
        )
        # Add batch 2: expires in 180 days, qty = 50
        b2 = InventoryBatch(
            batch_number="BATCH-LATE-180D",
            drug_id=drug_id,
            quantity_on_hand=50,
            expiry_date=self.now + timedelta(days=180),
            received_date=self.now - timedelta(days=5),
            cost_per_unit=48.0
        )
        # Add batch 3: already expired 5 days ago, qty = 20
        b3 = InventoryBatch(
            batch_number="BATCH-EXPIRED",
            drug_id=drug_id,
            quantity_on_hand=20,
            expiry_date=self.now - timedelta(days=5),
            received_date=self.now - timedelta(days=400),
            cost_per_unit=45.0
        )

        self.engine.add_batch(b1)
        self.engine.add_batch(b2)
        self.engine.add_batch(b3)

        # Request 15 units. Should consume all 10 from b1, and 5 from b2. Never b3.
        allocation = self.engine.allocate_fefo_stock(drug_id, requested_qty=15, as_of_time=self.now)

        self.assertTrue(allocation["success"])
        self.assertEqual(allocation["allocated_qty"], 15)
        self.assertEqual(allocation["shortfall"], 0)
        self.assertEqual(len(allocation["allocations"]), 2)

        # First allocation must be BATCH-EARLY-30D
        self.assertEqual(allocation["allocations"][0]["batch_number"], "BATCH-EARLY-30D")
        self.assertEqual(allocation["allocations"][0]["allocated_qty"], 10)

        # Second allocation must be BATCH-LATE-180D
        self.assertEqual(allocation["allocations"][1]["batch_number"], "BATCH-LATE-180D")
        self.assertEqual(allocation["allocations"][1]["allocated_qty"], 5)

        # Expired batch untouched
        self.assertEqual(b3.quantity_on_hand, 20)

    def test_vaccine_cold_chain_excursion_quarantine(self):
        """Verify cold-chain temperature excursion triggers automated batch quarantine."""
        vaccine_id = "DRUG-COVAXIN"
        self.engine.register_drug(DrugMasterItem(
            drug_id=vaccine_id,
            generic_name="Whole Virion Inactivated Corona Vaccine",
            brand_names=["Covaxin"],
            dosage_form="INJECTION",
            strength="0.5 mL",
            route="IM",
            schedule="GENERAL",
            atc_code="J07BX03",
            storage_temp_range=(2.0, 8.0)
        ))

        batch = InventoryBatch(
            batch_number="VAX-LOT-991",
            drug_id=vaccine_id,
            quantity_on_hand=100,
            expiry_date=self.now + timedelta(days=120),
            received_date=self.now - timedelta(days=1),
            cost_per_unit=250.0
        )
        self.engine.add_batch(batch)

        # Log safe temperature 4.5°C
        res1 = self.engine.record_cold_chain_temperature(vaccine_id, "VAX-LOT-991", 4.5)
        self.assertEqual(res1["status"], "ACTIVE")
        self.assertIsNone(res1["alert"])

        # Log temperature spike 12.8°C (Refrigeration failure)
        res2 = self.engine.record_cold_chain_temperature(vaccine_id, "VAX-LOT-991", 12.8)
        self.assertEqual(res2["status"], "QUARANTINED_EXCURSION")
        self.assertIn("CRITICAL COLD-CHAIN EXCURSION", res2["alert"])

        # Attempt to allocate from quarantined batch should fail / return out of stock
        alloc = self.engine.allocate_fefo_stock(vaccine_id, requested_qty=10, as_of_time=self.now)
        self.assertFalse(alloc["success"])
        self.assertEqual(alloc["allocated_qty"], 0)

    def test_aefi_report_logging(self):
        """Verify AEFI reporting flags serious adverse reactions for regulatory escalation."""
        report = self.engine.log_aefi_report(
            patient_id="PAT-99182",
            vaccine_drug_id="DRUG-COVAXIN",
            batch_number="VAX-LOT-991",
            symptom_category="SERIOUS_HOSPITALIZATION",
            description="Severe anaphylaxis requiring immediate resuscitation within 15 min of injection",
            reporter_id="NURSE-IC-04"
        )
        self.assertTrue(report["regulatory_escalation"])
        self.assertEqual(report["symptom_category"], "SERIOUS_HOSPITALIZATION")
        self.assertEqual(len(self.engine.aefi_reports), 1)

    def test_reorder_point_calculation(self):
        """Verify automated reorder point calculation formula (Gap 9)."""
        # Daily velocity = 50 units, lead time = 5 days, std_dev = 5, Z = 1.645 (95%)
        # Lead time demand = 250
        # Safety stock = ceil(1.645 * 5 * sqrt(5)) = ceil(1.645 * 11.18) = ceil(18.39) = 19
        # ROP = 250 + 19 = 269
        rop_res = self.engine.calculate_reorder_point(
            daily_consumption_velocity=50.0,
            lead_time_days=5,
            daily_velocity_std_dev=5.0
        )
        self.assertEqual(rop_res["safety_stock"], 19)
        self.assertEqual(rop_res["reorder_point"], 269)


if __name__ == "__main__":
    unittest.main()
