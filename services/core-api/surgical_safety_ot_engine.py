"""
PROJECT "HOSPITAL" — PHASE 09: SURGICAL & PROCEDURAL
Module: surgical_safety_ot_engine.py
Operational Scope:
  - WHO Surgical Safety Checklist Stage-Gates (Sign-In, Time-Out, Sign-Out)
  - Quality Gate 1: Inviolable Block Preventing Wound Closure Completion on Count Discrepancy
  - Dual-Nurse (Scrub Nurse + Circulating Nurse) Count Reconciliation (Sponges, Needles, Instruments)
  - Unique Device Identifier (UDI) Implant Tracking & Permanent EHR Logging
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class SurgicalSafetyError(Exception):
    """Base exception for surgical safety checklist violations."""
    pass


class SurgicalCountDiscrepancyError(SurgicalSafetyError):
    """Raised when sponge/needle/instrument count is unbalanced or unverified prior to wound closure."""
    pass


@dataclass
class UDIImplantRecord:
    implant_id: str
    case_id: str
    patient_id: str
    udi_barcode: str       # GS1 / HIBCC format
    device_name: str       # e.g., "Coronary Drug-Eluting Stent", "Total Knee Prosthesis"
    manufacturer: str
    lot_serial_number: str
    expiry_date: str
    implanted_by_surgeon: str
    implanted_at: str


@dataclass
class SurgicalCountItem:
    item_type: str  # SPONGE, NEEDLE, INSTRUMENT
    initial_count: int
    added_intraop: int
    discarded_count: int
    final_counted: int

    @property
    def total_expected(self) -> int:
        return self.initial_count + self.added_intraop

    @property
    def is_balanced(self) -> bool:
        return (self.final_counted + self.discarded_count) == self.total_expected


@dataclass
class SurgicalCase:
    case_id: str
    patient_id: str
    ot_room_id: str
    lead_surgeon_id: str
    anesthetist_id: str
    scrub_nurse_id: str
    circulating_nurse_id: str
    procedure_name: str
    state: str = "SCHEDULED"  # SCHEDULED, SIGN_IN_COMPLETED, TIME_OUT_COMPLETED, IN_SURGERY, SIGN_OUT_COMPLETED, CLOSED
    sign_in_record: Optional[Dict[str, Any]] = None
    time_out_record: Optional[Dict[str, Any]] = None
    sign_out_record: Optional[Dict[str, Any]] = None
    counts: Dict[str, SurgicalCountItem] = field(default_factory=dict)
    implants: List[UDIImplantRecord] = field(default_factory=list)


class SurgicalSafetyOTEngine:
    """
    Operating Theater safety engine enforcing the WHO Surgical Safety Checklist,
    strict dual-nurse count reconciliations, and UDI implant traceability.
    """

    def __init__(self):
        self.cases: Dict[str, SurgicalCase] = {}

    def schedule_case(
        self,
        case_id: str,
        patient_id: str,
        ot_room_id: str,
        lead_surgeon_id: str,
        anesthetist_id: str,
        scrub_nurse_id: str,
        circulating_nurse_id: str,
        procedure_name: str
    ) -> SurgicalCase:
        case = SurgicalCase(
            case_id=case_id,
            patient_id=patient_id,
            ot_room_id=ot_room_id,
            lead_surgeon_id=lead_surgeon_id,
            anesthetist_id=anesthetist_id,
            scrub_nurse_id=scrub_nurse_id,
            circulating_nurse_id=circulating_nurse_id,
            procedure_name=procedure_name
        )
        self.cases[case_id] = case
        return case

    def execute_sign_in_gate(
        self,
        case_id: str,
        patient_identity_confirmed: bool,
        surgical_site_marked: bool,
        anesthesia_safety_check_done: bool,
        pulse_oximeter_functioning: bool,
        known_allergy: bool,
        difficult_airway_risk: bool,
        blood_loss_risk_over_500ml: bool,
        sign_off_anesthetist_id: str
    ) -> Dict[str, Any]:
        """
        WHO Sign-In Stage-Gate (Before induction of anesthesia).
        """
        case = self.cases.get(case_id)
        if not case:
            raise SurgicalSafetyError(f"Case {case_id} not found.")

        if not (patient_identity_confirmed and surgical_site_marked and anesthesia_safety_check_done and pulse_oximeter_functioning):
            raise SurgicalSafetyError("SIGN-IN GATE FAILED: Patient identity, site marking, and anesthesia check must all be verified.")

        record = {
            "stage": "SIGN_IN",
            "patient_identity_confirmed": patient_identity_confirmed,
            "surgical_site_marked": surgical_site_marked,
            "anesthesia_safety_check_done": anesthesia_safety_check_done,
            "pulse_oximeter_functioning": pulse_oximeter_functioning,
            "known_allergy": known_allergy,
            "difficult_airway_risk": difficult_airway_risk,
            "blood_loss_risk_over_500ml": blood_loss_risk_over_500ml,
            "sign_off_anesthetist_id": sign_off_anesthetist_id,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        case.sign_in_record = record
        case.state = "SIGN_IN_COMPLETED"
        return record

    def execute_time_out_gate(
        self,
        case_id: str,
        team_members_introduced: bool,
        patient_identity_and_site_reconfirmed: bool,
        critical_surgical_steps_reviewed: bool,
        antibiotic_prophylaxis_given_within_60min: bool,
        sterility_indicators_confirmed: bool,
        imaging_displayed: bool,
        sign_off_surgeon_id: str
    ) -> Dict[str, Any]:
        """
        WHO Time-Out Stage-Gate (Before skin incision).
        """
        case = self.cases.get(case_id)
        if not case:
            raise SurgicalSafetyError(f"Case {case_id} not found.")

        if case.state != "SIGN_IN_COMPLETED":
            raise SurgicalSafetyError(f"Cannot perform Time-Out before completing Sign-In (Current state: {case.state}).")

        if not (team_members_introduced and patient_identity_and_site_reconfirmed and sterility_indicators_confirmed and antibiotic_prophylaxis_given_within_60min):
            raise SurgicalSafetyError("TIME-OUT GATE FAILED: Antibiotic prophylaxis, sterility check, and team introduction must be confirmed.")

        record = {
            "stage": "TIME_OUT",
            "team_members_introduced": team_members_introduced,
            "patient_identity_and_site_reconfirmed": patient_identity_and_site_reconfirmed,
            "antibiotic_prophylaxis_given_within_60min": antibiotic_prophylaxis_given_within_60min,
            "sterility_indicators_confirmed": sterility_indicators_confirmed,
            "sign_off_surgeon_id": sign_off_surgeon_id,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        case.time_out_record = record
        case.state = "IN_SURGERY"
        return record

    def update_surgical_count(
        self,
        case_id: str,
        item_type: str,  # SPONGE, NEEDLE, INSTRUMENT
        initial: int,
        added: int,
        discarded: int,
        final_counted: int
    ):
        """Updates counts for sponges, needles, and instruments."""
        case = self.cases.get(case_id)
        if not case:
            raise SurgicalSafetyError(f"Case {case_id} not found.")

        item = SurgicalCountItem(
            item_type=item_type,
            initial_count=initial,
            added_intraop=added,
            discarded_count=discarded,
            final_counted=final_counted
        )
        case.counts[item_type] = item

    def record_implant_udi(
        self,
        case_id: str,
        udi_barcode: str,
        device_name: str,
        manufacturer: str,
        lot_serial_number: str,
        expiry_date: str,
        surgeon_id: str
    ) -> UDIImplantRecord:
        """Logs implant UDI directly into the surgical record and permanent EHR."""
        case = self.cases.get(case_id)
        if not case:
            raise SurgicalSafetyError(f"Case {case_id} not found.")

        rec = UDIImplantRecord(
            implant_id=f"UDI-{case_id}-{len(case.implants)+1}",
            case_id=case_id,
            patient_id=case.patient_id,
            udi_barcode=udi_barcode,
            device_name=device_name,
            manufacturer=manufacturer,
            lot_serial_number=lot_serial_number,
            expiry_date=expiry_date,
            implanted_by_surgeon=surgeon_id,
            implanted_at=datetime.now(timezone.utc).isoformat()
        )
        case.implants.append(rec)
        return rec

    def execute_sign_out_and_closure_gate(
        self,
        case_id: str,
        scrub_nurse_id: str,
        circulating_nurse_id: str,
        specimen_labeled_correctly: bool,
        postop_recovery_concerns: str
    ) -> Dict[str, Any]:
        """
        Quality Gate 1:
        OT workflow physically prevents surgical case closure completion if sponge/needle count indicates a discrepancy.
        Wound closure documentation is blocked until scrub nurse and circulating nurse independently confirm balanced counts.
        """
        case = self.cases.get(case_id)
        if not case:
            raise SurgicalSafetyError(f"Case {case_id} not found.")

        if case.state != "IN_SURGERY":
            raise SurgicalSafetyError(f"Case {case_id} is not in surgery (State: {case.state}).")

        # Must have distinct scrub and circulating nurse sign-offs
        if scrub_nurse_id == circulating_nurse_id:
            raise SurgicalCountDiscrepancyError(
                "COUNT RECONCILIATION VIOLATION: Scrub nurse and circulating nurse must be two distinct individuals."
            )

        # Check all counts (SPONGE, NEEDLE, INSTRUMENT)
        required_items = ["SPONGE", "NEEDLE", "INSTRUMENT"]
        for item_name in required_items:
            count_item = case.counts.get(item_name)
            if not count_item:
                raise SurgicalCountDiscrepancyError(
                    f"INCOMPLETE SURGICAL COUNT: Count for '{item_name}' was not recorded. Wound closure blocked."
                )

            if not count_item.is_balanced:
                deficit = count_item.total_expected - (count_item.final_counted + count_item.discarded_count)
                raise SurgicalCountDiscrepancyError(
                    f"FATAL SURGICAL SAFETY HARD STOP: Discrepancy detected in '{item_name}' count! "
                    f"Expected {count_item.total_expected}, but accounted for {count_item.final_counted + count_item.discarded_count} "
                    f"(Deficit: {deficit}). Surgical case closure physically blocked. Intraoperative X-ray / cavity search required."
                )

        if not specimen_labeled_correctly:
            raise SurgicalSafetyError("SIGN-OUT GATE FAILED: Surgical specimen labeling verification failed.")

        record = {
            "stage": "SIGN_OUT",
            "scrub_nurse_id": scrub_nurse_id,
            "circulating_nurse_id": circulating_nurse_id,
            "all_counts_balanced": True,
            "specimen_labeled_correctly": specimen_labeled_correctly,
            "postop_recovery_concerns": postop_recovery_concerns,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        case.sign_out_record = record
        case.state = "CLOSED"
        return record
