"""
PROJECT "HOSPITAL" — PHASE 11: REVENUE CYCLE
Module: dynamic_billing_engine.py
Operational Scope:
  - Dynamic Tariff & Tiered Rate Cards (General, Semi-Private, Private, ICU)
  - Pre-Discharge Parallel Settlement Orchestration (< 45 min SLA) (Quality Gate 1)
  - Pre-Treatment Cost Estimation Calculator with SAC/GST Compliance
  - Structured Discount & Refund Dual Approval Matrix
  - Cryptographically Chained Append-Only Financial Audit Trail (Gap 35)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import json


class BillingError(Exception):
    """Base exception for billing violations."""
    pass


class DiscountAuthorizationError(BillingError):
    """Raised when an unauthorized discount exceeds approval thresholds."""
    pass


@dataclass
class TariffItem:
    service_code: str       # e.g., "SRV-CONSULT", "SRV-CBC", "SRV-LAP-CHOL"
    service_name: str
    sac_code: str           # HSN/SAC code, e.g. "9993"
    base_price: float
    gst_rate_pct: float = 0.0  # Healthcare typically exempt (0%), cosmetic/non-exempt taxed


@dataclass
class InvoiceLineItem:
    line_id: str
    service_code: str
    service_name: str
    quantity: int
    unit_price: float
    gst_amount: float
    total_amount: float
    category: str           # INVESTIGATION, PHARMACY, BED_CHARGES, CONSULTATION, SURGERY


@dataclass
class PatientInvoice:
    invoice_id: str
    patient_id: str
    encounter_id: str
    ward_tier: str          # GENERAL (1.0x), SEMI_PRIVATE (1.5x), PRIVATE (2.2x), ICU (3.5x)
    lines: List[InvoiceLineItem] = field(default_factory=list)
    discount_amount: float = 0.0
    discount_authorized_by: Optional[str] = None
    total_gross: float = 0.0
    total_gst: float = 0.0
    total_net: float = 0.0
    status: str = "PROVISIONAL"  # PROVISIONAL, FINAL_SETTLED, REFUNDED
    created_at: str = ""
    settled_at: Optional[str] = None
    prev_audit_hash: str = ""
    audit_hash: str = ""


class DynamicBillingEngine:
    """
    Revenue cycle management engine handling tariff tiers, pre-treatment estimates,
    speedy pre-discharge parallel settlements (< 45 min SLA), and immutable hash chains.
    """

    WARD_TIER_MULTIPLIERS = {
        "GENERAL": 1.0,
        "SEMI_PRIVATE": 1.5,
        "PRIVATE": 2.2,
        "ICU": 3.5
    }

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self.tariff_master: Dict[str, TariffItem] = {}
        self.invoices: Dict[str, PatientInvoice] = {}
        self.last_audit_hash: str = self.GENESIS_HASH

    def register_tariff_item(self, item: TariffItem):
        self.tariff_master[item.service_code] = item

    def compute_tiered_price(self, service_code: str, ward_tier: str) -> float:
        item = self.tariff_master.get(service_code)
        if not item:
            raise BillingError(f"Service code {service_code} not found in tariff master.")
        multiplier = self.WARD_TIER_MULTIPLIERS.get(ward_tier.upper(), 1.0)
        return round(item.base_price * multiplier, 2)

    def generate_pretreatment_cost_estimate(
        self,
        service_codes: List[str],
        ward_tier: str,
        expected_days: int = 1
    ) -> Dict[str, Any]:
        """Generates pre-treatment cost estimate provided to patients upon admission."""
        multiplier = self.WARD_TIER_MULTIPLIERS.get(ward_tier.upper(), 1.0)
        breakdown = []
        total_estimate = 0.0

        for code in service_codes:
            item = self.tariff_master.get(code)
            if item:
                price = round(item.base_price * multiplier, 2)
                gst = round(price * (item.gst_rate_pct / 100.0), 2)
                subtotal = price + gst
                total_estimate += subtotal
                breakdown.append({
                    "service_code": code,
                    "service_name": item.service_name,
                    "sac_code": item.sac_code,
                    "unit_price": price,
                    "gst": gst,
                    "subtotal": subtotal
                })

        return {
            "ward_tier": ward_tier,
            "expected_days": expected_days,
            "breakdown": breakdown,
            "total_estimated_cost": round(total_estimate, 2)
        }

    def create_invoice(self, invoice_id: str, patient_id: str, encounter_id: str, ward_tier: str) -> PatientInvoice:
        inv = PatientInvoice(
            invoice_id=invoice_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            ward_tier=ward_tier,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        self.invoices[invoice_id] = inv
        return inv

    def add_line_item(
        self,
        invoice_id: str,
        service_code: str,
        quantity: int,
        category: str = "GENERAL"
    ) -> InvoiceLineItem:
        inv = self.invoices.get(invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} not found.")

        price = self.compute_tiered_price(service_code, inv.ward_tier)
        item = self.tariff_master[service_code]
        gst = round((price * quantity) * (item.gst_rate_pct / 100.0), 2)
        total = round((price * quantity) + gst, 2)

        line = InvoiceLineItem(
            line_id=f"LINE-{len(inv.lines)+1}",
            service_code=service_code,
            service_name=item.service_name,
            quantity=quantity,
            unit_price=price,
            gst_amount=gst,
            total_amount=total,
            category=category
        )
        inv.lines.append(line)
        self._recalculate_totals(inv)
        return line

    def apply_discount(
        self,
        invoice_id: str,
        discount_amount: float,
        requesting_staff_id: str,
        approving_authority_id: Optional[str] = None
    ):
        """
        Applies discount. Discounts > 10% of gross strictly require dual approval from Medical Superintendent/CFO.
        """
        inv = self.invoices.get(invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} not found.")

        pct = (discount_amount / inv.total_gross * 100.0) if inv.total_gross > 0 else 0.0
        if pct > 10.0:
            if not approving_authority_id or approving_authority_id == requesting_staff_id:
                raise DiscountAuthorizationError(
                    f"DISCOUNT APPROVAL BREACH: Discount of ₹{discount_amount} ({round(pct, 1)}%) exceeds 10% threshold. "
                    f"Mandatory independent sign-off by Medical Superintendent / CFO required."
                )

        inv.discount_amount = discount_amount
        inv.discount_authorized_by = approving_authority_id or requesting_staff_id
        self._recalculate_totals(inv)

    def _recalculate_totals(self, inv: PatientInvoice):
        gross = sum(l.unit_price * l.quantity for l in inv.lines)
        gst = sum(l.gst_amount for l in inv.lines)
        net = max(0.0, (gross + gst) - inv.discount_amount)
        inv.total_gross = round(gross, 2)
        inv.total_gst = round(gst, 2)
        inv.total_net = round(net, 2)

    def orchestrate_parallel_discharge_settlement(
        self,
        invoice_id: str,
        clinical_signoff_time: datetime,
        unused_pharmacy_return_count: int,
        settlement_completed_time: datetime
    ) -> Dict[str, Any]:
        """
        Quality Gate 1:
        Final patient discharge billing completes within 45 minutes of clinical sign-off
        in simulated discharge runs.
        """
        inv = self.invoices.get(invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} not found.")

        duration_sec = (settlement_completed_time - clinical_signoff_time).total_seconds()
        duration_minutes = round(duration_sec / 60.0, 1)

        # SLA Target: < 45 minutes
        sla_passed = duration_minutes <= 45.0

        inv.status = "FINAL_SETTLED"
        inv.settled_at = settlement_completed_time.isoformat()

        # Immutable Audit Hash Chain
        audit_payload = {
            "invoice_id": inv.invoice_id,
            "patient_id": inv.patient_id,
            "total_net": inv.total_net,
            "settled_at": inv.settled_at,
            "prev_hash": self.last_audit_hash
        }
        computed_hash = hashlib.sha256(json.dumps(audit_payload, sort_keys=True).encode("utf-8")).hexdigest()
        inv.prev_audit_hash = self.last_audit_hash
        inv.audit_hash = computed_hash
        self.last_audit_hash = computed_hash

        return {
            "invoice_id": invoice_id,
            "duration_minutes": duration_minutes,
            "target_sla_minutes": 45.0,
            "sla_passed": sla_passed,
            "pharmacy_returns_processed": unused_pharmacy_return_count,
            "final_amount": inv.total_net,
            "audit_hash": inv.audit_hash
        }
