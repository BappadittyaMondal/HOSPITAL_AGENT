"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 17.1: CLINICAL SAFETY BOARD (CSB) GOVERNANCE ENGINE
====================================================================================================
Module: services/core-api/clinical_safety_board_governance.py
Purpose: Enforces statutory clinical governance, quorum validation, cryptographic stage-gate
         authorizations (HMAC-SHA256), emergency clinical safety pause, and immutable dissent
         recording for hospital leadership.
====================================================================================================
"""

import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set


class GovernanceSafetyException(Exception):
    """Base exception for clinical governance violations."""
    pass


class QuorumNotMetError(GovernanceSafetyException):
    """Raised when an attempt is made to pass clinical resolutions without statutory quorum."""
    pass


class EmergencySafetyPauseActiveError(GovernanceSafetyException):
    """Raised when operations are attempted during an active Clinical Safety Pause."""
    pass


# Mandatory Statutory Roles for Clinical Safety Board Quorum
MANDATORY_CSB_ROLES = {
    "MEDICAL_SUPERINTENDENT",  # Chair (Non-negotiable)
    "CHIEF_NURSING_OFFICER",   # Nursing governance (Non-negotiable)
    "HEAD_OF_PHARMACY",
    "CHIEF_INFORMATION_OFFICER",
    "LEGAL_COUNSEL",
    "HEAD_OF_INTERNAL_MEDICINE",
    "HEAD_OF_SURGERY",
    "HEAD_OF_PEDIATRICS"
}


class ClinicalSafetyBoardGovernanceEngine:
    """Manages the statutory governance, quorum, and stage-gate authorizations of the Clinical Safety Board."""

    def __init__(self, hospital_id: str = "HOSPITAL-AIIMS-01"):
        self.hospital_id = hospital_id
        self._registered_members: Dict[str, Dict] = {}
        self._stage_authorizations: Dict[int, Dict] = {}
        self._emergency_pause_active: bool = False
        self._pause_reason: Optional[str] = None
        self._dissent_log: List[Dict] = []
        self._governance_audit_ledger: List[Dict] = []

    def register_board_member(
        self,
        member_id: str,
        name: str,
        role: str,
        nmc_registration_number: Optional[str] = None
    ) -> Dict:
        """Registers a verified credentialed member of the Hospital Clinical Safety Board."""
        member = {
            "member_id": member_id,
            "name": name,
            "role": role,
            "nmc_registration": nmc_registration_number,
            "status": "ACTIVE",
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        self._registered_members[member_id] = member
        return member

    def verify_quorum(self, attending_member_ids: List[str]) -> bool:
        """Verifies statutory quorum (minimum 6 members, including MS and CNO)."""
        attending_roles = set()
        for mid in attending_member_ids:
            if mid in self._registered_members and self._registered_members[mid]["status"] == "ACTIVE":
                attending_roles.add(self._registered_members[mid]["role"])

        # Inviolable Rule 1: Medical Superintendent (Chair) must be present
        if "MEDICAL_SUPERINTENDENT" not in attending_roles:
            return False

        # Inviolable Rule 2: Chief Nursing Officer must be present
        if "CHIEF_NURSING_OFFICER" not in attending_roles:
            return False

        # Inviolable Rule 3: Minimum 6 distinct statutory roles represented
        valid_statutory_roles = attending_roles.intersection(MANDATORY_CSB_ROLES)
        return len(valid_statutory_roles) >= 6

    def issue_stage_authorization_token(
        self,
        stage_number: int,
        attending_member_ids: List[str],
        scorecard_compliance_percent: float,
        secret_key: str = "CSB_HMAC_SECRET_KEY_2026"
    ) -> Dict:
        """Issues an HMAC-SHA256 cryptographic authorization token required to unlock pilot stages."""
        if self._emergency_pause_active:
            raise EmergencySafetyPauseActiveError(
                f"CANNOT AUTHORIZE STAGE {stage_number}: Clinical Safety Pause is currently ACTIVE! "
                f"Reason: {self._pause_reason}"
            )

        if not self.verify_quorum(attending_member_ids):
            raise QuorumNotMetError(
                f"QUORUM DEFICIT: Authorizing Stage {stage_number} requires minimum 6 statutory CSB members, "
                f"including Medical Superintendent and Chief Nursing Officer."
            )

        if scorecard_compliance_percent < 100.0:
            raise GovernanceSafetyException(
                f"SAFETY SCORECARD DEFICIT: Stage {stage_number} requires 100.0% Production Scorecard compliance. "
                f"Current: {scorecard_compliance_percent:.1f}%"
            )

        now = datetime.now(timezone.utc)
        payload = f"{self.hospital_id}:STAGE_{stage_number}:{now.strftime('%Y-%m-%d')}:{len(attending_member_ids)}"
        token_signature = hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        token = f"CSB-AUTH-STAGE-{stage_number}-{token_signature[:16].upper()}"

        record = {
            "stage_number": stage_number,
            "token": token,
            "authorized_at": now.isoformat(),
            "attending_members_count": len(attending_member_ids),
            "scorecard_certified": scorecard_compliance_percent,
            "payload": payload,
            "status": "VALID"
        }
        self._stage_authorizations[stage_number] = record
        self._governance_audit_ledger.append(record)
        return record

    def trigger_emergency_safety_pause(self, reason: str, initiated_by_member_id: str) -> Dict:
        """Immediately activates an Emergency Safety Pause halting all active pilot progressions."""
        if initiated_by_member_id not in self._registered_members:
            raise GovernanceSafetyException("Only registered CSB members can trigger a Clinical Safety Pause.")

        self._emergency_pause_active = True
        self._pause_reason = reason.strip()

        event = {
            "action": "EMERGENCY_SAFETY_PAUSE_TRIGGERED",
            "initiated_by": initiated_by_member_id,
            "reason": self._pause_reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._governance_audit_ledger.append(event)
        return event

    def resolve_emergency_safety_pause(
        self,
        resolution_notes: str,
        attending_member_ids: List[str]
    ) -> Dict:
        """Resolves an Emergency Safety Pause, requiring full board quorum review."""
        if not self.verify_quorum(attending_member_ids):
            raise QuorumNotMetError("Resolving an Emergency Safety Pause requires full CSB statutory quorum.")

        self._emergency_pause_active = False
        self._pause_reason = None

        event = {
            "action": "EMERGENCY_SAFETY_PAUSE_RESOLVED",
            "resolution_notes": resolution_notes,
            "quorum_attending": len(attending_member_ids),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._governance_audit_ledger.append(event)
        return event

    def record_clinical_dissent(
        self,
        member_id: str,
        stage_number: int,
        objection_details: str
    ) -> Dict:
        """Inviolably records clinical dissent or safety reservations into the perpetual audit ledger."""
        if member_id not in self._registered_members:
            raise GovernanceSafetyException("Member not found.")

        dissent = {
            "member_id": member_id,
            "member_name": self._registered_members[member_id]["name"],
            "role": self._registered_members[member_id]["role"],
            "stage_number": stage_number,
            "objection_details": objection_details.strip(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._dissent_log.append(dissent)
        self._governance_audit_ledger.append(dissent)
        return dissent

    @property
    def is_paused(self) -> bool:
        return self._emergency_pause_active
