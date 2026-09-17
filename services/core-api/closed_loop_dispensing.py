"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Module: closed_loop_dispensing.py
Operational Scope:
  - Barcode-Scanned Dispensing Verification (Prescription vs Medication Barcode)
  - INVIOLABLE HARD STOP: Mechanical Expiry Date Barrier Blocking Expired Batches
  - ISMP High-Alert Medication Dual-Verification Protocol (KCl, Insulin, Heparin)
  - Closed-Loop Traceable Dispense Log with Terminal Safety Alarms
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class ExpiredMedicationBlockError(Exception):
    """Raised when an attempt is made to dispense an expired medication batch."""
    pass


class HighAlertVerificationError(Exception):
    """Raised when high-alert medication lacks independent secondary sign-off."""
    pass


class BarcodeMismatchError(Exception):
    """Raised when scanned barcode does not match prescribed medication."""
    pass


@dataclass
class PrescriptionItem:
    prescription_id: str
    patient_id: str
    drug_id: str
    generic_name: str
    prescribed_dose: str
    route: str
    prescribed_qty: int
    is_high_alert: bool = False
    prescriber_id: str = "DOC-DEFAULT"


@dataclass
class DispenseEvent:
    dispense_id: str
    prescription_id: str
    patient_id: str
    drug_id: str
    batch_number: str
    quantity_dispensed: int
    pharmacist_id: str
    verifier_id: Optional[str]
    scanned_barcode: str
    dispense_time: datetime
    status: str  # DISPENSED, BLOCKED_EXPIRED, BLOCKED_MISMATCH, BLOCKED_UNVERIFIED
    terminal_alarm_sounded: bool = False
    block_reason: Optional[str] = None


class ClosedLoopDispensingEngine:
    """
    Closed-loop dispensing verification engine enforcing inviolable expiration blocks,
    barcode matching, and dual verification for high-alert drugs.
    """

    # High-alert drug identifiers requiring dual verification
    HIGH_ALERT_KEYWORDS = [
        "POTASSIUM CHLORIDE", "KCL", "INSULIN", "HEPARIN",
        "METHOTREXATE", "DOXORUBICIN", "CISPLATIN", "FENTANYL", "EPINEPHRINE"
    ]

    def __init__(self):
        self.dispense_history: List[DispenseEvent] = []

    def verify_and_dispense(
        self,
        prescription: PrescriptionItem,
        batch_number: str,
        batch_expiry_date: datetime,
        scanned_barcode_drug_id: str,
        dispense_qty: int,
        primary_pharmacist_id: str,
        secondary_verifier_id: Optional[str] = None,
        as_of_time: Optional[datetime] = None
    ) -> DispenseEvent:
        """
        Closed-loop verification workflow:
        1. Expiration check: If batch_expiry_date <= as_of_time, 100% HARD STOP.
        2. Barcode match: Scanned barcode drug ID must strictly match prescribed drug ID.
        3. ISMP High-Alert check: If drug is high-alert, require distinct secondary verifier.
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        dispense_id = f"DISP-{int(as_of_time.timestamp())}-{len(self.dispense_history)+1}"

        # 1. INVIOLABLE HARD STOP: Expiration check
        if batch_expiry_date <= as_of_time:
            event = DispenseEvent(
                dispense_id=dispense_id,
                prescription_id=prescription.prescription_id,
                patient_id=prescription.patient_id,
                drug_id=prescription.drug_id,
                batch_number=batch_number,
                quantity_dispensed=0,
                pharmacist_id=primary_pharmacist_id,
                verifier_id=secondary_verifier_id,
                scanned_barcode=scanned_barcode_drug_id,
                dispense_time=as_of_time,
                status="BLOCKED_EXPIRED",
                terminal_alarm_sounded=True,
                block_reason=f"FATAL PHARMACY SAFETY HAZARD: Batch {batch_number} expired on {batch_expiry_date.isoformat()}. System mechanically blocked dispensing."
            )
            self.dispense_history.append(event)
            raise ExpiredMedicationBlockError(event.block_reason)

        # 2. Barcode match verification
        if scanned_barcode_drug_id != prescription.drug_id:
            event = DispenseEvent(
                dispense_id=dispense_id,
                prescription_id=prescription.prescription_id,
                patient_id=prescription.patient_id,
                drug_id=prescription.drug_id,
                batch_number=batch_number,
                quantity_dispensed=0,
                pharmacist_id=primary_pharmacist_id,
                verifier_id=secondary_verifier_id,
                scanned_barcode=scanned_barcode_drug_id,
                dispense_time=as_of_time,
                status="BLOCKED_MISMATCH",
                terminal_alarm_sounded=True,
                block_reason=f"BARCODE MISMATCH: Prescribed {prescription.drug_id} does not match scanned barcode {scanned_barcode_drug_id}."
            )
            self.dispense_history.append(event)
            raise BarcodeMismatchError(event.block_reason)

        # 3. High-Alert ISMP verification
        is_high_alert = prescription.is_high_alert or any(
            kw in prescription.generic_name.upper() for kw in self.HIGH_ALERT_KEYWORDS
        )

        if is_high_alert:
            if not secondary_verifier_id or secondary_verifier_id == primary_pharmacist_id:
                event = DispenseEvent(
                    dispense_id=dispense_id,
                    prescription_id=prescription.prescription_id,
                    patient_id=prescription.patient_id,
                    drug_id=prescription.drug_id,
                    batch_number=batch_number,
                    quantity_dispensed=0,
                    pharmacist_id=primary_pharmacist_id,
                    verifier_id=secondary_verifier_id,
                    scanned_barcode=scanned_barcode_drug_id,
                    dispense_time=as_of_time,
                    status="BLOCKED_UNVERIFIED",
                    terminal_alarm_sounded=True,
                    block_reason=f"ISMP HIGH-ALERT RULE VIOLATION: {prescription.generic_name} requires an independent, distinct secondary verifier sign-off."
                )
                self.dispense_history.append(event)
                raise HighAlertVerificationError(event.block_reason)

        # 4. Successful Dispense
        event = DispenseEvent(
            dispense_id=dispense_id,
            prescription_id=prescription.prescription_id,
            patient_id=prescription.patient_id,
            drug_id=prescription.drug_id,
            batch_number=batch_number,
            quantity_dispensed=dispense_qty,
            pharmacist_id=primary_pharmacist_id,
            verifier_id=secondary_verifier_id,
            scanned_barcode=scanned_barcode_drug_id,
            dispense_time=as_of_time,
            status="DISPENSED",
            terminal_alarm_sounded=False,
            block_reason=None
        )
        self.dispense_history.append(event)
        return event
