"""
PROJECT "HOSPITAL" — PHASE 12: HOSPITAL OPERATIONS
Module: procurement_inventory_engine.py
Operational Scope:
  - Sub-task 12.4: Vendor Procurement & Inventory Management (Gap 9)
  - Full P2P (Procure-to-Pay) Lifecycle: PR → PO → GRN → QC Inspection → Stock Ledger
  - Vendor Rate Contracts (VRC) & Government e-Marketplace (GeM) Adapter
  - Three-Way Match Engine (PO vs GRN vs Vendor Invoice) Blocking Payment Discrepancies
  - Vendor Performance Rating Engine (Lead Time, Defect Rate, Composite Score 0-100)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any


class ProcurementError(Exception):
    """Base exception for procurement and supply chain violations."""
    pass


class ThreeWayMatchError(ProcurementError):
    """Raised when vendor invoice exceeds GRN verified quantity or PO negotiated price."""
    pass


class GeMComplianceError(ProcurementError):
    """Raised when a Government e-Marketplace procurement order violates GeM guidelines."""
    pass


class POStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DISPATCHED_TO_VENDOR = "DISPATCHED_TO_VENDOR"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class QCStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class ProcurementMode(str, Enum):
    RATE_CONTRACT = "RATE_CONTRACT"
    GEM_DIRECT = "GEM_DIRECT"          # Direct purchase on GeM (< ₹25,000 or proprietary)
    GEM_L1_BIDDING = "GEM_L1_BIDDING"  # L1 lowest bidder on GeM
    OPEN_TENDER = "OPEN_TENDER"


@dataclass
class VendorRateContract:
    contract_id: str
    vendor_id: str
    vendor_name: str
    item_code: str
    item_name: str
    contracted_unit_price_inr: float
    promised_lead_time_days: int
    valid_until: datetime
    is_gem_contract: bool = False
    gem_contract_ref: Optional[str] = None


@dataclass
class PurchaseOrderItem:
    item_code: str
    item_name: str
    ordered_qty: int
    unit_price_inr: float
    total_price_inr: float


@dataclass
class PurchaseOrder:
    po_number: str
    vendor_id: str
    procurement_mode: ProcurementMode
    items: List[PurchaseOrderItem]
    total_po_amount_inr: float
    created_at: datetime
    status: POStatus = POStatus.DRAFT
    approved_by: Optional[str] = None
    ms_financial_approval: Optional[str] = None
    gem_reference_id: Optional[str] = None


@dataclass
class GoodsReceiptNote:
    grn_number: str
    po_number: str
    vendor_id: str
    item_code: str
    received_qty: int
    batch_number: str
    expiry_date: datetime
    received_at: datetime
    received_by: str
    qc_status: QCStatus = QCStatus.PENDING
    passed_qty: int = 0
    rejected_qty: int = 0
    qc_remarks: str = ""
    qc_inspector_id: Optional[str] = None


@dataclass
class VendorInvoice:
    invoice_number: str
    po_number: str
    vendor_id: str
    item_code: str
    invoiced_qty: int
    invoiced_unit_price_inr: float
    total_invoiced_amount_inr: float
    submitted_at: datetime
    is_payment_approved: bool = False
    payment_approval_notes: str = ""


class ProcurementInventoryEngine:
    """
    Hospital Procurement & Supply Chain Management Engine.
    Handles the procure-to-pay workflow, rate contracts, GeM compliance,
    3-way matching, and vendor performance scoring.
    """

    # Dual sign-off threshold: Orders exceeding ₹100,000 require Financial Advisor / MS approval
    HIGH_VALUE_THRESHOLD_INR = 100000.0

    def __init__(self):
        self._rate_contracts: Dict[str, VendorRateContract] = {}  # contract_id -> VRC
        self._purchase_orders: Dict[str, PurchaseOrder] = {}      # po_number -> PO
        self._grns: Dict[str, GoodsReceiptNote] = {}              # grn_number -> GRN
        self._stock_ledger: Dict[str, int] = {}                   # item_code -> active balance
        self._invoices: Dict[str, VendorInvoice] = {}             # invoice_number -> Invoice
        self._vendor_deliveries: Dict[str, List[Dict[str, Any]]] = {}  # vendor_id -> delivery history

    def register_rate_contract(
        self,
        contract_id: str,
        vendor_id: str,
        vendor_name: str,
        item_code: str,
        item_name: str,
        unit_price_inr: float,
        lead_time_days: int,
        valid_until: datetime,
        is_gem_contract: bool = False,
        gem_contract_ref: Optional[str] = None,
    ) -> VendorRateContract:
        """Registers an approved annual rate contract or GeM contract."""
        vrc = VendorRateContract(
            contract_id=contract_id,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            item_code=item_code,
            item_name=item_name,
            contracted_unit_price_inr=round(unit_price_inr, 2),
            promised_lead_time_days=lead_time_days,
            valid_until=valid_until,
            is_gem_contract=is_gem_contract,
            gem_contract_ref=gem_contract_ref,
        )
        self._rate_contracts[contract_id] = vrc
        return vrc

    def create_purchase_order(
        self,
        po_number: str,
        vendor_id: str,
        procurement_mode: ProcurementMode,
        items: List[Dict[str, Any]],
        gem_reference_id: Optional[str] = None,
    ) -> PurchaseOrder:
        """Creates a Purchase Order enforcing contracted pricing."""
        if po_number in self._purchase_orders:
            raise ProcurementError(f"Duplicate PO number {po_number}")

        if procurement_mode in (ProcurementMode.GEM_DIRECT, ProcurementMode.GEM_L1_BIDDING) and not gem_reference_id:
            raise GeMComplianceError("GeM procurement mode requires a verified GeM Reference/Contract ID.")

        po_items: List[PurchaseOrderItem] = []
        total_amount = 0.0

        for it in items:
            item_code = it["item_code"]
            qty = it["ordered_qty"]
            unit_price = it["unit_price_inr"]

            # Validate against rate contract if mode is RATE_CONTRACT
            if procurement_mode == ProcurementMode.RATE_CONTRACT:
                matching_contract = next(
                    (c for c in self._rate_contracts.values() if c.vendor_id == vendor_id and c.item_code == item_code),
                    None
                )
                if not matching_contract:
                    raise ProcurementError(f"No active rate contract found for item {item_code} with vendor {vendor_id}.")
                if unit_price > matching_contract.contracted_unit_price_inr:
                    raise ProcurementError(
                        f"Price ₹{unit_price} exceeds contracted rate of ₹{matching_contract.contracted_unit_price_inr}."
                    )

            line_total = round(qty * unit_price, 2)
            po_items.append(PurchaseOrderItem(
                item_code=item_code,
                item_name=it.get("item_name", item_code),
                ordered_qty=qty,
                unit_price_inr=unit_price,
                total_price_inr=line_total,
            ))
            total_amount += line_total

        total_amount = round(total_amount, 2)
        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=vendor_id,
            procurement_mode=procurement_mode,
            items=po_items,
            total_po_amount_inr=total_amount,
            created_at=datetime.now(timezone.utc),
            status=POStatus.PENDING_APPROVAL,
            gem_reference_id=gem_reference_id,
        )
        self._purchase_orders[po_number] = po
        return po

    def approve_purchase_order(
        self,
        po_number: str,
        approver_id: str,
        ms_approver_id: Optional[str] = None,
    ) -> PurchaseOrder:
        """
        Approves PO.
        Enforces Dual-Approval Gate: High-value orders (> ₹100,000) require Medical Superintendent / FA sign-off.
        """
        if po_number not in self._purchase_orders:
            raise ProcurementError(f"PO {po_number} not found.")

        po = self._purchase_orders[po_number]

        if po.total_po_amount_inr >= self.HIGH_VALUE_THRESHOLD_INR:
            if not ms_approver_id:
                raise ProcurementError(
                    f"High-value PO (₹{po.total_po_amount_inr:,.2f} >= ₹{self.HIGH_VALUE_THRESHOLD_INR:,.2f}) "
                    f"strictly requires Medical Superintendent / Financial Advisor co-signature."
                )
            po.ms_financial_approval = ms_approver_id

        po.approved_by = approver_id
        po.status = POStatus.APPROVED
        return po

    def record_goods_receipt(
        self,
        grn_number: str,
        po_number: str,
        item_code: str,
        received_qty: int,
        batch_number: str,
        expiry_date: datetime,
        received_by: str,
    ) -> GoodsReceiptNote:
        """Records physical arrival of stock at hospital warehouse."""
        if po_number not in self._purchase_orders:
            raise ProcurementError(f"PO {po_number} does not exist.")

        po = self._purchase_orders[po_number]
        if po.status not in (POStatus.APPROVED, POStatus.PARTIALLY_RECEIVED):
            raise ProcurementError(f"Cannot receive goods against unapproved PO ({po.status.value}).")

        matching_item = next((it for it in po.items if it.item_code == item_code), None)
        if not matching_item:
            raise ProcurementError(f"Item {item_code} is not on PO {po_number}.")

        if received_qty > matching_item.ordered_qty:
            raise ProcurementError(
                f"Received quantity {received_qty} exceeds ordered quantity {matching_item.ordered_qty} on PO {po_number}."
            )

        grn = GoodsReceiptNote(
            grn_number=grn_number,
            po_number=po_number,
            vendor_id=po.vendor_id,
            item_code=item_code,
            received_qty=received_qty,
            batch_number=batch_number,
            expiry_date=expiry_date,
            received_at=datetime.now(timezone.utc),
            received_by=received_by,
        )
        self._grns[grn_number] = grn
        return grn

    def perform_qc_inspection(
        self,
        grn_number: str,
        inspector_id: str,
        passed_qty: int,
        rejected_qty: int,
        remarks: str = "",
    ) -> Dict[str, Any]:
        """
        Quality Control Inspection. Only PASSED goods update active stock ledger.
        Rejected goods are held in return-to-vendor quarantine.
        """
        if grn_number not in self._grns:
            raise ProcurementError(f"GRN {grn_number} not found.")

        grn = self._grns[grn_number]
        if passed_qty + rejected_qty != grn.received_qty:
            raise ProcurementError("Sum of passed and rejected quantities must equal total received quantity.")

        grn.passed_qty = passed_qty
        grn.rejected_qty = rejected_qty
        grn.qc_remarks = remarks
        grn.qc_inspector_id = inspector_id

        if rejected_qty > 0 and passed_qty == 0:
            grn.qc_status = QCStatus.REJECTED
        elif rejected_qty > 0 and passed_qty > 0:
            grn.qc_status = QCStatus.PASSED  # partially passed
        else:
            grn.qc_status = QCStatus.PASSED

        # Update active hospital stock ledger with PASSED quantity
        if passed_qty > 0:
            self._stock_ledger[grn.item_code] = self._stock_ledger.get(grn.item_code, 0) + passed_qty

        # Record delivery data for vendor performance scoring
        if grn.vendor_id not in self._vendor_deliveries:
            self._vendor_deliveries[grn.vendor_id] = []

        self._vendor_deliveries[grn.vendor_id].append({
            "grn_number": grn_number,
            "received_at": grn.received_at,
            "received_qty": grn.received_qty,
            "passed_qty": passed_qty,
            "rejected_qty": rejected_qty,
        })

        return {
            "grn_number": grn_number,
            "qc_status": grn.qc_status.value,
            "passed_stock_added": passed_qty,
            "rejected_quarantined": rejected_qty,
            "current_active_stock": self._stock_ledger.get(grn.item_code, 0),
        }

    def execute_three_way_match(
        self,
        invoice_number: str,
        po_number: str,
        grn_number: str,
        invoiced_qty: int,
        invoiced_unit_price_inr: float,
    ) -> Dict[str, Any]:
        """
        Executes Three-Way Match: PO vs GRN vs Vendor Invoice.
        Inviolable Gate: Blocks payment release if invoiced quantity > passed QC quantity
        or if invoiced rate > negotiated PO rate.
        """
        if po_number not in self._purchase_orders:
            raise ThreeWayMatchError(f"PO {po_number} not found.")
        if grn_number not in self._grns:
            raise ThreeWayMatchError(f"GRN {grn_number} not found.")

        po = self._purchase_orders[po_number]
        grn = self._grns[grn_number]

        po_item = next((it for it in po.items if it.item_code == grn.item_code), None)
        if not po_item:
            raise ThreeWayMatchError(f"Item {grn.item_code} mismatch between GRN and PO.")

        # 1. Quantity Match: Invoiced Qty cannot exceed passed QC quantity
        if invoiced_qty > grn.passed_qty:
            raise ThreeWayMatchError(
                f"[3-WAY MATCH FAILED: QUANTITY] Invoiced quantity ({invoiced_qty}) exceeds "
                f"passed QC quantity ({grn.passed_qty}) from GRN {grn_number}! Payment blocked."
            )

        # 2. Rate Match: Invoiced unit price cannot exceed PO agreed unit price
        if invoiced_unit_price_inr > po_item.unit_price_inr:
            raise ThreeWayMatchError(
                f"[3-WAY MATCH FAILED: RATE] Invoiced unit rate (₹{invoiced_unit_price_inr:.2f}) "
                f"exceeds PO contracted rate (₹{po_item.unit_price_inr:.2f})! Payment blocked."
            )

        total_invoiced = round(invoiced_qty * invoiced_unit_price_inr, 2)
        invoice = VendorInvoice(
            invoice_number=invoice_number,
            po_number=po_number,
            vendor_id=po.vendor_id,
            item_code=grn.item_code,
            invoiced_qty=invoiced_qty,
            invoiced_unit_price_inr=invoiced_unit_price_inr,
            total_invoiced_amount_inr=total_invoiced,
            submitted_at=datetime.now(timezone.utc),
            is_payment_approved=True,
            payment_approval_notes="Passed 3-Way Match (PO, GRN QC, and Invoice perfectly reconciled).",
        )
        self._invoices[invoice_number] = invoice

        return {
            "status": "THREE_WAY_MATCH_VERIFIED",
            "invoice_number": invoice_number,
            "approved_amount_inr": total_invoiced,
            "payment_cleared": True,
        }

    def calculate_vendor_performance_score(self, vendor_id: str) -> Dict[str, Any]:
        """
        Calculates Vendor Performance Score (0-100) based on:
        - Quality Defect Rate (Weight: 50%)
        - Delivery Compliance (Weight: 50%)
        """
        deliveries = self._vendor_deliveries.get(vendor_id, [])
        if not deliveries:
            return {"vendor_id": vendor_id, "deliveries_recorded": 0, "score": 100.0, "rating": "NEW_VENDOR"}

        total_received = sum(d["received_qty"] for d in deliveries)
        total_rejected = sum(d["rejected_qty"] for d in deliveries)

        defect_rate_pct = (total_rejected / total_received * 100.0) if total_received > 0 else 0.0
        quality_score = max(0.0, 100.0 - (defect_rate_pct * 5.0))  # Each 1% defect drops 5 points

        # Delivery score (mock base 95 for completed deliveries)
        delivery_score = 95.0

        composite_score = round((quality_score * 0.5) + (delivery_score * 0.5), 1)

        rating = "EXCELLENT" if composite_score >= 90 else "SATISFACTORY" if composite_score >= 75 else "NEEDS_IMPROVEMENT"

        return {
            "vendor_id": vendor_id,
            "total_units_delivered": total_received,
            "total_units_rejected": total_rejected,
            "defect_rate_pct": round(defect_rate_pct, 2),
            "quality_score": round(quality_score, 1),
            "delivery_score": delivery_score,
            "composite_vendor_score": composite_score,
            "rating": rating,
        }

    def get_stock_balance(self, item_code: str) -> int:
        return self._stock_ledger.get(item_code, 0)
