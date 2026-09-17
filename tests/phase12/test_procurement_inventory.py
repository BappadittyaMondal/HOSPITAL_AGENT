"""
Test Suite: test_procurement_inventory.py
Phase 12: Hospital Operations — Vendor Procurement & Inventory Management (Gap 9)
Mandate:
  - Purchase Requisition → PO → Goods Receipt → QC Inspection → Stock Ledger pipeline.
  - Vendor rate contracts (VRC) and Government e-Marketplace (GeM) integration adapter.
  - Dual approval gate for high-value POs (> ₹100,000).
  - Inviolable Three-Way Match Engine (PO vs GRN vs Vendor Invoice) blocking payment discrepancies.
  - Vendor performance scoring (defect rate, composite vendor score).
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from procurement_inventory_engine import (
    ProcurementInventoryEngine,
    ProcurementMode,
    POStatus,
    QCStatus,
    ProcurementError,
    ThreeWayMatchError,
    GeMComplianceError,
)


class TestProcurementInventoryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ProcurementInventoryEngine()

        # Register an approved rate contract
        self.contract_gloves = self.engine.register_rate_contract(
            contract_id="RC-2026-GLV",
            vendor_id="VEND-MEDISAFE-01",
            vendor_name="MediSafe Surgical Supplies Ltd",
            item_code="GLV-NITRILE-M",
            item_name="Nitrile Examination Gloves (Medium, Box of 100)",
            unit_price_inr=350.0,
            lead_time_days=3,
            valid_until=datetime.now(timezone.utc) + timedelta(days=365),
        )

    def test_gem_adapter_validation(self):
        """Tests GeM procurement adapter requirement for GeM reference ID."""
        # Missing GeM contract ID raises GeMComplianceError
        with self.assertRaises(GeMComplianceError):
            self.engine.create_purchase_order(
                po_number="PO-GEM-ERR",
                vendor_id="VEND-GEM-99",
                procurement_mode=ProcurementMode.GEM_L1_BIDDING,
                items=[{"item_code": "STETH-LITTMANN", "ordered_qty": 10, "unit_price_inr": 8500.0}],
                gem_reference_id=None,
            )

    def test_high_value_dual_approval_gate(self):
        """Tests that PO >= ₹100,000 strictly requires MS / Financial Advisor co-signature."""
        # Order 500 boxes of gloves at ₹350 = ₹175,000 (Exceeds ₹100,000 threshold)
        po = self.engine.create_purchase_order(
            po_number="PO-2026-001",
            vendor_id="VEND-MEDISAFE-01",
            procurement_mode=ProcurementMode.RATE_CONTRACT,
            items=[{"item_code": "GLV-NITRILE-M", "ordered_qty": 500, "unit_price_inr": 350.0}],
        )
        self.assertEqual(po.total_po_amount_inr, 175000.0)
        self.assertEqual(po.status, POStatus.PENDING_APPROVAL)

        # Attempt to approve without MS signature raises ProcurementError
        with self.assertRaises(ProcurementError) as ctx:
            self.engine.approve_purchase_order(
                po_number="PO-2026-001",
                approver_id="HOD-CENTRAL-STORE",
                ms_approver_id=None,
            )
        self.assertIn("Medical Superintendent / Financial Advisor co-signature", str(ctx.exception))

        # Approve with dual sign-off
        approved_po = self.engine.approve_purchase_order(
            po_number="PO-2026-001",
            approver_id="HOD-CENTRAL-STORE",
            ms_approver_id="MS-AIIMS-01",
        )
        self.assertEqual(approved_po.status, POStatus.APPROVED)
        self.assertEqual(approved_po.ms_financial_approval, "MS-AIIMS-01")

    def test_three_way_match_success_and_stock_posting(self):
        """End-to-end test of PO -> GRN -> QC -> Stock Ledger -> 3-Way Match payment approval."""
        po = self.engine.create_purchase_order(
            po_number="PO-2026-002",
            vendor_id="VEND-MEDISAFE-01",
            procurement_mode=ProcurementMode.RATE_CONTRACT,
            items=[{"item_code": "GLV-NITRILE-M", "ordered_qty": 100, "unit_price_inr": 350.0}],
        )
        self.engine.approve_purchase_order("PO-2026-002", approver_id="STORE-MANAGER-1")

        # Warehouse receives 100 boxes
        grn = self.engine.record_goods_receipt(
            grn_number="GRN-2026-101",
            po_number="PO-2026-002",
            item_code="GLV-NITRILE-M",
            received_qty=100,
            batch_number="BATCH-GLV-8819",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=730),
            received_by="RECEIVER-1",
        )

        # QC inspection: 95 passed, 5 rejected due to packaging tear
        qc_res = self.engine.perform_qc_inspection(
            grn_number="GRN-2026-101",
            inspector_id="QC-OFFICER-1",
            passed_qty=95,
            rejected_qty=5,
            remarks="5 boxes packaging damp; quarantined for return.",
        )
        self.assertEqual(qc_res["passed_stock_added"], 95)
        self.assertEqual(self.engine.get_stock_balance("GLV-NITRILE-M"), 95)

        # 1. Vendor attempts to invoice for full 100 boxes (exceeds passed QC quantity of 95) -> 3-Way Match fails!
        with self.assertRaises(ThreeWayMatchError) as ctx:
            self.engine.execute_three_way_match(
                invoice_number="INV-ERR-001",
                po_number="PO-2026-002",
                grn_number="GRN-2026-101",
                invoiced_qty=100,  # 100 > 95 passed
                invoiced_unit_price_inr=350.0,
            )
        self.assertIn("Invoiced quantity (100) exceeds passed QC quantity (95)", str(ctx.exception))

        # 2. Vendor invoices for higher rate than PO agreed rate -> 3-Way Match fails!
        with self.assertRaises(ThreeWayMatchError) as ctx:
            self.engine.execute_three_way_match(
                invoice_number="INV-ERR-002",
                po_number="PO-2026-002",
                grn_number="GRN-2026-101",
                invoiced_qty=95,
                invoiced_unit_price_inr=380.0,  # ₹380 > contracted ₹350
            )
        self.assertIn("Invoiced unit rate (₹380.00) exceeds PO contracted rate (₹350.00)", str(ctx.exception))

        # 3. Vendor submits corrected invoice for exactly 95 passed boxes at ₹350 -> Approved
        match_res = self.engine.execute_three_way_match(
            invoice_number="INV-CORRECT-003",
            po_number="PO-2026-002",
            grn_number="GRN-2026-101",
            invoiced_qty=95,
            invoiced_unit_price_inr=350.0,
        )
        self.assertEqual(match_res["status"], "THREE_WAY_MATCH_VERIFIED")
        self.assertEqual(match_res["approved_amount_inr"], 33250.0)

        # 4. Check vendor performance score calculation
        score = self.engine.calculate_vendor_performance_score("VEND-MEDISAFE-01")
        self.assertEqual(score["total_units_delivered"], 100)
        self.assertEqual(score["total_units_rejected"], 5)
        self.assertEqual(score["defect_rate_pct"], 5.0)
        self.assertEqual(score["composite_vendor_score"], 85.0)  # (75 quality * 0.5) + (95 delivery * 0.5)
        self.assertEqual(score["rating"], "SATISFACTORY")


if __name__ == "__main__":
    unittest.main()
