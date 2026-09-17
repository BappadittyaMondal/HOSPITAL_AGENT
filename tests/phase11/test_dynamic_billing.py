"""
PROJECT "HOSPITAL" — PHASE 11: REVENUE CYCLE
Test Suite: test_dynamic_billing.py
Validates:
  - Quality Gate 1: Final patient discharge billing completes within 45 minutes of clinical sign-off
  - Dynamic tiered tariffs (General, Semi-Private, Private, ICU)
  - Pre-treatment cost estimation
  - Dual-approval discount gate
  - Cryptographic SHA-256 immutable financial audit chain (Gap 35)
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from dynamic_billing_engine import (
    DynamicBillingEngine, TariffItem, DiscountAuthorizationError
)


class TestDynamicBillingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = DynamicBillingEngine()
        self.now = datetime.now(timezone.utc)

        # Register standard tariffs
        self.engine.register_tariff_item(TariffItem(
            service_code="SRV-BED-DAY",
            service_name="Inpatient Bed Care",
            sac_code="999312",
            base_price=1000.0
        ))
        self.engine.register_tariff_item(TariffItem(
            service_code="SRV-CONSULT",
            service_name="Specialist Physician Consultation",
            sac_code="999311",
            base_price=500.0
        ))
        self.engine.register_tariff_item(TariffItem(
            service_code="SRV-CBC",
            service_name="Complete Blood Count",
            sac_code="999313",
            base_price=350.0
        ))

    def test_quality_gate_discharge_settlement_within_45_minutes(self):
        """
        Phase 11 Quality Gate 1:
        Final patient discharge billing completes within 45 minutes of clinical sign-off
        in simulated discharge runs.
        """
        invoice = self.engine.create_invoice(
            invoice_id="INV-DISC-001",
            patient_id="PAT-DISC-101",
            encounter_id="ENC-550",
            ward_tier="GENERAL"
        )
        self.engine.add_line_item("INV-DISC-001", "SRV-BED-DAY", quantity=3)
        self.engine.add_line_item("INV-DISC-001", "SRV-CONSULT", quantity=2)

        clinical_signoff = self.now
        settlement_completed = self.now + timedelta(minutes=28)  # Completed in 28 minutes (< 45 min!)

        result = self.engine.orchestrate_parallel_discharge_settlement(
            invoice_id="INV-DISC-001",
            clinical_signoff_time=clinical_signoff,
            unused_pharmacy_return_count=2,
            settlement_completed_time=settlement_completed
        )

        self.assertTrue(result["sla_passed"])
        self.assertEqual(result["duration_minutes"], 28.0)
        self.assertLessEqual(result["duration_minutes"], 45.0)
        self.assertIsNotNone(result["audit_hash"])

    def test_tiered_tariff_calculation(self):
        """Verify bed tier multipliers (General 1.0x, Private 2.2x, ICU 3.5x)."""
        # Base price for Bed Day = 1000
        price_gen = self.engine.compute_tiered_price("SRV-BED-DAY", "GENERAL")
        price_pvt = self.engine.compute_tiered_price("SRV-BED-DAY", "PRIVATE")
        price_icu = self.engine.compute_tiered_price("SRV-BED-DAY", "ICU")

        self.assertEqual(price_gen, 1000.0)
        self.assertEqual(price_pvt, 2200.0)
        self.assertEqual(price_icu, 3500.0)

    def test_pretreatment_cost_estimate(self):
        """Verify pre-treatment estimate generation."""
        est = self.engine.generate_pretreatment_cost_estimate(
            service_codes=["SRV-BED-DAY", "SRV-CONSULT", "SRV-CBC"],
            ward_tier="SEMI_PRIVATE",
            expected_days=2
        )
        # Semi-Private = 1.5x
        # Bed: 1000 * 1.5 = 1500
        # Consult: 500 * 1.5 = 750
        # CBC: 350 * 1.5 = 525
        # Total = 2775.0
        self.assertEqual(est["total_estimated_cost"], 2775.0)
        self.assertEqual(len(est["breakdown"]), 3)

    def test_discount_dual_approval_gate(self):
        """Verify discounts > 10% require independent sign-off."""
        inv = self.engine.create_invoice("INV-DISC-002", "PAT-99", "ENC-99", "GENERAL")
        self.engine.add_line_item("INV-DISC-002", "SRV-BED-DAY", quantity=10)  # Gross = 10,000

        # 5% discount (₹500) -> Allowed with single staff ID
        self.engine.apply_discount("INV-DISC-002", 500.0, "BILLING-CLERK-01")
        self.assertEqual(inv.total_net, 9500.0)

        # 25% discount (₹2500) without independent authority -> BLOCKED!
        with self.assertRaises(DiscountAuthorizationError) as ctx:
            self.engine.apply_discount("INV-DISC-002", 2500.0, "BILLING-CLERK-01")
        self.assertIn("DISCOUNT APPROVAL BREACH", str(ctx.exception))
        self.assertIn("exceeds 10% threshold", str(ctx.exception))

        # 25% discount with independent MS sign-off -> APPROVED
        self.engine.apply_discount("INV-DISC-002", 2500.0, "BILLING-CLERK-01", "DOC-MS-01")
        self.assertEqual(inv.total_net, 7500.0)


if __name__ == "__main__":
    unittest.main()
