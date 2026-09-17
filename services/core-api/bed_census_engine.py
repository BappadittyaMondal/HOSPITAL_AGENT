"""
PROJECT "HOSPITAL" — PHASE 07: INPATIENT CORE
Module: bed_census_engine.py
Operational Scope:
  - Inpatient Bed Lifecycle State Machine: AVAILABLE -> RESERVED -> OCCUPIED -> DISCHARGE_PENDING -> CLEANING_REQUIRED -> SANITIZED -> AVAILABLE
  - INVIOLABLE HARD GATE: Mechanical Block Preventing Bed Allocation Until Terminal Sanitization Confirmed
  - Automatic Transition to CLEANING_REQUIRED Upon Checkout Completion
  - Isolation Contact Precaution Bed Management (MRSA, VRE, C. diff, MDR) & Enhanced Terminal Decontamination
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set


class BedStateError(Exception):
    """Base exception for invalid bed state operations."""
    pass


class BedSanitizationBlockError(BedStateError):
    """Raised when an attempt is made to allocate or occupy an unsanitized bed."""
    pass


@dataclass
class TerminalCleaningSignOff:
    housekeeper_id: str
    supervisor_id: str
    checklist_completed: bool
    uv_decontamination_used: bool
    chemical_disinfectant: str
    completed_at: str


@dataclass
class BedRecord:
    bed_id: str
    ward_id: str
    ward_type: str  # GENERAL, HDU, ICU, NICU, ISOLATION
    state: str = "AVAILABLE"  # AVAILABLE, RESERVED, OCCUPIED, DISCHARGE_PENDING, CLEANING_REQUIRED, SANITIZED
    current_patient_id: Optional[str] = None
    isolation_precaution: Optional[str] = None  # None, CONTACT, DROPLET, AIRBORNE (MRSA, VRE, C_DIFF)
    reserved_for_patient_id: Optional[str] = None
    last_state_change: str = ""
    last_cleaning_sign_off: Optional[TerminalCleaningSignOff] = None
    audit_history: List[Dict[str, Any]] = field(default_factory=list)


class BedCensusEngine:
    """
    Inpatient bed state machine engine enforcing sanitary gates,
    automatic checkout-to-cleaning transitions, and isolation protocols.
    """

    ALLOWED_TRANSITIONS = {
        "AVAILABLE": ["RESERVED", "OCCUPIED"],
        "RESERVED": ["OCCUPIED", "AVAILABLE"],
        "OCCUPIED": ["DISCHARGE_PENDING", "CLEANING_REQUIRED"],
        "DISCHARGE_PENDING": ["CLEANING_REQUIRED", "OCCUPIED"],
        "CLEANING_REQUIRED": ["SANITIZED"],
        "SANITIZED": ["AVAILABLE"]
    }

    def __init__(self):
        self.beds: Dict[str, BedRecord] = {}

    def register_bed(self, bed_id: str, ward_id: str, ward_type: str) -> BedRecord:
        now_str = datetime.now(timezone.utc).isoformat()
        bed = BedRecord(
            bed_id=bed_id,
            ward_id=ward_id,
            ward_type=ward_type,
            state="AVAILABLE",
            last_state_change=now_str
        )
        self.beds[bed_id] = bed
        return bed

    def _log_transition(self, bed: BedRecord, old_state: str, new_state: str, actor_id: str, reason: str):
        now_str = datetime.now(timezone.utc).isoformat()
        bed.state = new_state
        bed.last_state_change = now_str
        bed.audit_history.append({
            "from_state": old_state,
            "to_state": new_state,
            "actor_id": actor_id,
            "reason": reason,
            "timestamp": now_str
        })

    def reserve_bed(self, bed_id: str, patient_id: str, actor_id: str) -> BedRecord:
        """Reserve an available bed for an incoming admission or transfer."""
        bed = self.beds.get(bed_id)
        if not bed:
            raise BedStateError(f"Bed {bed_id} does not exist.")

        # INVIOLABLE SANITARY GATE
        if bed.state == "CLEANING_REQUIRED":
            raise BedSanitizationBlockError(
                f"SAFETY HARD STOP: Bed {bed_id} is in CLEANING_REQUIRED status. Allocation strictly blocked until terminal sanitization."
            )
        if bed.state != "AVAILABLE":
            raise BedStateError(f"Cannot reserve bed {bed_id} in state '{bed.state}'. Bed must be 'AVAILABLE'.")

        bed.reserved_for_patient_id = patient_id
        self._log_transition(bed, "AVAILABLE", "RESERVED", actor_id, f"Reserved for patient {patient_id}")
        return bed

    def admit_patient_to_bed(self, bed_id: str, patient_id: str, actor_id: str, isolation_precaution: Optional[str] = None) -> BedRecord:
        """Occupy bed with patient."""
        bed = self.beds.get(bed_id)
        if not bed:
            raise BedStateError(f"Bed {bed_id} does not exist.")

        # INVIOLABLE SANITARY GATE
        if bed.state == "CLEANING_REQUIRED":
            raise BedSanitizationBlockError(
                f"SAFETY HARD STOP: Cannot admit patient {patient_id} into bed {bed_id} while in CLEANING_REQUIRED status. Terminal sanitization required."
            )

        if bed.state not in ("AVAILABLE", "RESERVED"):
            raise BedStateError(f"Cannot admit to bed {bed_id} in state '{bed.state}'.")

        if bed.state == "RESERVED" and bed.reserved_for_patient_id != patient_id:
            raise BedStateError(f"Bed {bed_id} is reserved for patient {bed.reserved_for_patient_id}, not {patient_id}.")

        old_state = bed.state
        bed.current_patient_id = patient_id
        bed.reserved_for_patient_id = None
        bed.isolation_precaution = isolation_precaution
        self._log_transition(bed, old_state, "OCCUPIED", actor_id, f"Admitted patient {patient_id}")
        return bed

    def complete_patient_checkout(self, bed_id: str, actor_id: str) -> BedRecord:
        """
        Quality Gate 1:
        Bed status switches to CLEANING_REQUIRED the instant patient checkout completes.
        Bed allocation is blocked until housekeeping submits sanitization sign-off.
        """
        bed = self.beds.get(bed_id)
        if not bed:
            raise BedStateError(f"Bed {bed_id} does not exist.")

        if bed.state not in ("OCCUPIED", "DISCHARGE_PENDING"):
            raise BedStateError(f"Cannot checkout patient from bed {bed_id} in state '{bed.state}'.")

        departing_patient = bed.current_patient_id
        bed.current_patient_id = None
        old_state = bed.state

        # Automatically transition to CLEANING_REQUIRED
        self._log_transition(bed, old_state, "CLEANING_REQUIRED", actor_id, f"Patient {departing_patient} discharged/checked-out. Terminal cleaning triggered.")
        return bed

    def submit_housekeeping_sanitization(
        self,
        bed_id: str,
        sign_off: TerminalCleaningSignOff
    ) -> BedRecord:
        """
        Housekeeping submits terminal cleaning sign-off.
        Verifies checklist. If bed was an isolation room (e.g. C. diff, MRSA), enforces UV or sporicidal protocol.
        Transitions bed from CLEANING_REQUIRED -> SANITIZED -> AVAILABLE.
        """
        bed = self.beds.get(bed_id)
        if not bed:
            raise BedStateError(f"Bed {bed_id} does not exist.")

        if bed.state != "CLEANING_REQUIRED":
            raise BedStateError(f"Bed {bed_id} is not in CLEANING_REQUIRED state (currently '{bed.state}').")

        if not sign_off.checklist_completed:
            raise BedStateError("Housekeeping checklist must be 100% completed before submitting sign-off.")

        # Isolation precaution requirement
        if bed.isolation_precaution in ("CONTACT", "AIRBORNE", "C_DIFF", "MRSA", "VRE"):
            if not sign_off.uv_decontamination_used and "SPORICIDAL" not in sign_off.chemical_disinfectant.upper():
                raise BedStateError(
                    f"INFECTION CONTROL BREACH: Isolation bed {bed_id} ({bed.isolation_precaution}) mandates UV decontamination or sporicidal disinfectant."
                )

        bed.last_cleaning_sign_off = sign_off
        # Clean isolation flag
        bed.isolation_precaution = None

        # Transition to SANITIZED
        self._log_transition(bed, "CLEANING_REQUIRED", "SANITIZED", sign_off.housekeeper_id, "Terminal cleaning completed by housekeeping")
        # Immediately transition to AVAILABLE for next patient
        self._log_transition(bed, "SANITIZED", "AVAILABLE", sign_off.supervisor_id, "Supervisor validated terminal sanitization; bed released to pool")
        return bed
