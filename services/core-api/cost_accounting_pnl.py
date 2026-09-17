"""
PROJECT "HOSPITAL" — PHASE 11: REVENUE CYCLE
Module: cost_accounting_pnl.py
Operational Scope:
  - Departmental Cost Center Ledger & Procedure Activity-Based Costing (ABC) (Gap 29)
  - Quality Gate 3: Departmental P&L Report Accurately Balances Revenue Against Direct Costs & Overheads
  - Granular Margin Contribution & Operating Ratio Analytics
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


@dataclass
class DepartmentCostRecord:
    department_id: str
    department_name: str
    period: str                     # e.g., "2026-Q3", "2026-09"
    gross_revenue: float
    direct_materials_cost: float     # Pharmaceuticals, implants, reagents
    direct_labor_cost: float         # Surgeons, anesthesiologists, nurses
    equipment_depreciation: float    # MRI, CT, OT lights, ventilators
    allocated_overheads: float       # Power, HVAC, biomedical waste, admin
    net_pnl: float = 0.0
    operating_margin_pct: float = 0.0


class CostAccountingPnLEngine:
    """
    Hospital managerial accounting engine tracking cost centers,
    direct vs indirect expenses, and generating mathematically balanced P&L reports.
    """

    def __init__(self):
        # (department_id, period) -> DepartmentCostRecord
        self.department_records: Dict[tuple, DepartmentCostRecord] = {}

    def generate_departmental_pnl(
        self,
        department_id: str,
        department_name: str,
        period: str,
        gross_revenue: float,
        direct_materials_cost: float,
        direct_labor_cost: float,
        equipment_depreciation: float,
        allocated_overheads: float
    ) -> DepartmentCostRecord:
        """
        Quality Gate 3:
        Departmental P&L report accurately balances revenue against direct material costs and allocated overheads.
        Formula:
          Total Costs = Direct Materials + Direct Labor + Depreciation + Overheads
          Net PnL = Gross Revenue - Total Costs
          Operating Margin % = (Net PnL / Gross Revenue) * 100
        """
        if gross_revenue < 0:
            raise ValueError("Gross revenue cannot be negative.")

        total_costs = direct_materials_cost + direct_labor_cost + equipment_depreciation + allocated_overheads
        net_pnl = round(gross_revenue - total_costs, 2)
        operating_margin = round((net_pnl / gross_revenue * 100.0), 2) if gross_revenue > 0 else 0.0

        record = DepartmentCostRecord(
            department_id=department_id,
            department_name=department_name,
            period=period,
            gross_revenue=round(gross_revenue, 2),
            direct_materials_cost=round(direct_materials_cost, 2),
            direct_labor_cost=round(direct_labor_cost, 2),
            equipment_depreciation=round(equipment_depreciation, 2),
            allocated_overheads=round(allocated_overheads, 2),
            net_pnl=net_pnl,
            operating_margin_pct=operating_margin
        )
        self.department_records[(department_id, period)] = record
        return record

    def verify_mathematical_balance(self, record: DepartmentCostRecord) -> bool:
        """Verifies that PnL components balance with 100.00% precision (Zero discrepancies)."""
        recalculated_costs = (
            record.direct_materials_cost +
            record.direct_labor_cost +
            record.equipment_depreciation +
            record.allocated_overheads
        )
        recalculated_pnl = round(record.gross_revenue - recalculated_costs, 2)
        return recalculated_pnl == record.net_pnl
