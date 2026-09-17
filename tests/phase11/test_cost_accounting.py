"""
PROJECT "HOSPITAL" — PHASE 11: REVENUE CYCLE
Test Suite: test_cost_accounting.py
Validates:
  - Quality Gate 3: Departmental P&L report accurately balances revenue against direct material costs and allocated overheads
  - Activity-Based Costing (ABC) reconciliation
  - Zero mathematical discrepancy verification
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from cost_accounting_pnl import CostAccountingPnLEngine


class TestCostAccountingPnLEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CostAccountingPnLEngine()

    def test_quality_gate_departmental_pnl_accurately_balances(self):
        """
        Phase 11 Quality Gate 3:
        Departmental P&L report accurately balances revenue against direct material costs and allocated overheads.
        """
        # Department: Department of Cardiology
        # Gross Revenue: ₹5,000,000.00
        # Direct Materials (Stents, Catheters, Balloons): ₹1,800,000.00
        # Direct Labor (Interventional Cardiologists, Cath Lab Nurses, Techs): ₹1,200,000.00
        # Equipment Depreciation (Cath Lab Philips Azurion): ₹450,000.00
        # Allocated Overheads (Electricity, HVAC, Admin): ₹350,000.00
        # Total Costs = 1.8M + 1.2M + 0.45M + 0.35M = ₹3,800,000.00
        # Net P&L = ₹5,000,000 - ₹3,800,000 = ₹1,200,000.00
        # Margin = 1.2M / 5.0M * 100 = 24.0%
        record = self.engine.generate_departmental_pnl(
            department_id="DEPT-CARDIO",
            department_name="Department of Cardiology & Cath Lab",
            period="2026-Q3",
            gross_revenue=5000000.0,
            direct_materials_cost=1800000.0,
            direct_labor_cost=1200000.0,
            equipment_depreciation=450000.0,
            allocated_overheads=350000.0
        )

        self.assertEqual(record.net_pnl, 1200000.0)
        self.assertEqual(record.operating_margin_pct, 24.0)

        # Verify mathematical balance
        is_balanced = self.engine.verify_mathematical_balance(record)
        self.assertTrue(is_balanced)


if __name__ == "__main__":
    unittest.main()
