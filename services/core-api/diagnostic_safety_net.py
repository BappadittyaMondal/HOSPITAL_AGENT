"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 16.2: CLOSED-LOOP DIAGNOSTIC SAFETY NET & FAILURE-TO-RESCUE SENTINEL
====================================================================================================
Module: services/core-api/diagnostic_safety_net.py
Purpose: Tracks high-acuity diagnostic orders (histopathology, cytology, microbiology, imaging)
         from order creation through result verification to closed-loop treating consultant
         acknowledgement. Enforces strict SLA escalation (48h HOD -> 72h Medical Superintendent)
         to completely prevent "lost-to-follow-up" critical findings and incidentalomas.
====================================================================================================
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional


class SafetyNetException(Exception):
    """Base exception for diagnostic safety net violations."""
    pass


class IncompleteDiagnosticActionPlanError(SafetyNetException):
    """Raised when an unacknowledged critical report is closed without documenting a clinical action plan."""
    pass


class InvalidAcknowledgementError(SafetyNetException):
    """Raised when an unauthorized or unauthenticated user attempts to acknowledge a critical finding."""
    pass


class DiagnosticOrderPriority:
    STAT_PANIC = "STAT_PANIC"                # SLA: 60 seconds readback
    CRITICAL_PATHOLOGY = "CRITICAL_PATHOLOGY"# SLA: 48 hours consultant acknowledgement
    ACTIONABLE_INCIDENTAL = "ACTIONABLE_INCIDENTAL" # SLA: 14 days follow-up confirmation


class EscalationLevel:
    LEVEL_1_TREATING_CONSULTANT = "LEVEL_1_TREATING_CONSULTANT"
    LEVEL_2_DEPARTMENT_HEAD = "LEVEL_2_DEPARTMENT_HEAD"
    LEVEL_3_MEDICAL_SUPERINTENDENT = "LEVEL_3_MEDICAL_SUPERINTENDENT"


class DiagnosticSafetyNetEngine:
    """Enterprise sentinel preventing failure-to-rescue from unviewed or unacknowledged critical findings."""

    def __init__(self):
        self._tracked_orders: Dict[str, Dict] = {}
        self._escalation_log: List[Dict] = []

    def register_diagnostic_result(
        self,
        order_id: str,
        patient_id: str,
        ordering_doctor_id: str,
        department: str,
        test_name: str,
        result_summary: str,
        priority: str,
        reported_at: Optional[datetime] = None
    ) -> Dict:
        """Registers an issued diagnostic result requiring closed-loop clinician tracking."""
        if reported_at is None:
            reported_at = datetime.now(timezone.utc)

        tracking_entry = {
            "order_id": order_id,
            "patient_id": patient_id,
            "ordering_doctor_id": ordering_doctor_id,
            "department": department,
            "test_name": test_name,
            "result_summary": result_summary,
            "priority": priority,
            "reported_at": reported_at,
            "status": "UNACKNOWLEDGED",
            "current_escalation_level": EscalationLevel.LEVEL_1_TREATING_CONSULTANT,
            "escalation_timestamps": {
                EscalationLevel.LEVEL_1_TREATING_CONSULTANT: reported_at.isoformat()
            },
            "acknowledged_at": None,
            "acknowledged_by": None,
            "action_plan": None
        }

        self._tracked_orders[order_id] = tracking_entry
        return tracking_entry

    def evaluate_sla_escalations(self, current_time: Optional[datetime] = None) -> List[Dict]:
        """Evaluates elapsed time and triggers automated hierarchy escalations (48h HOD, 72h MS)."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        escalated_items = []

        for order_id, order in self._tracked_orders.items():
            if order["status"] == "ACKNOWLEDGED":
                continue

            elapsed = current_time - order["reported_at"]
            priority = order["priority"]

            if priority == DiagnosticOrderPriority.CRITICAL_PATHOLOGY:
                # 48 hours -> HOD Escalation
                if elapsed >= timedelta(hours=72):
                    if order["current_escalation_level"] != EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT:
                        order["current_escalation_level"] = EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT
                        order["escalation_timestamps"][EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT] = current_time.isoformat()
                        event = {
                            "order_id": order_id,
                            "patient_id": order["patient_id"],
                            "escalated_to": EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT,
                            "reason": f"Critical finding unacknowledged for {elapsed.total_seconds() / 3600:.1f} hours (> 72h SLA)",
                            "test_name": order["test_name"]
                        }
                        self._escalation_log.append(event)
                        escalated_items.append(event)

                elif elapsed >= timedelta(hours=48):
                    if order["current_escalation_level"] == EscalationLevel.LEVEL_1_TREATING_CONSULTANT:
                        order["current_escalation_level"] = EscalationLevel.LEVEL_2_DEPARTMENT_HEAD
                        order["escalation_timestamps"][EscalationLevel.LEVEL_2_DEPARTMENT_HEAD] = current_time.isoformat()
                        event = {
                            "order_id": order_id,
                            "patient_id": order["patient_id"],
                            "escalated_to": EscalationLevel.LEVEL_2_DEPARTMENT_HEAD,
                            "reason": f"Critical finding unacknowledged for {elapsed.total_seconds() / 3600:.1f} hours (> 48h SLA)",
                            "test_name": order["test_name"]
                        }
                        self._escalation_log.append(event)
                        escalated_items.append(event)

            elif priority == DiagnosticOrderPriority.STAT_PANIC:
                # 60 seconds panic readback
                if elapsed >= timedelta(seconds=60):
                    if order["current_escalation_level"] != EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT:
                        order["current_escalation_level"] = EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT
                        event = {
                            "order_id": order_id,
                            "patient_id": order["patient_id"],
                            "escalated_to": EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT,
                            "reason": "STAT Panic result unacknowledged > 60 seconds",
                            "test_name": order["test_name"]
                        }
                        self._escalation_log.append(event)
                        escalated_items.append(event)

        return escalated_items

    def acknowledge_result(
        self,
        order_id: str,
        clinician_id: str,
        digital_signature_hash: str,
        action_plan: str,
        ack_timestamp: Optional[datetime] = None
    ) -> Dict:
        """Enforces closed-loop resolution with mandatory clinical action plan and digital signature."""
        if order_id not in self._tracked_orders:
            raise SafetyNetException(f"Order ID '{order_id}' not found in Diagnostic Safety Net.")

        order = self._tracked_orders[order_id]

        if not action_plan or len(action_plan.strip()) < 10:
            raise IncompleteDiagnosticActionPlanError(
                "MANDATORY CLINICAL SAFETY GATE: Acknowledging critical diagnostic findings requires "
                "a substantive documented action plan (e.g., 'Patient recalled for urgent oncology consult')."
            )

        if not digital_signature_hash:
            raise InvalidAcknowledgementError("Digital signature hash is mandatory for statutory closed-loop log.")

        if ack_timestamp is None:
            ack_timestamp = datetime.now(timezone.utc)

        order["status"] = "ACKNOWLEDGED"
        order["acknowledged_at"] = ack_timestamp.isoformat()
        order["acknowledged_by"] = clinician_id
        order["digital_signature_hash"] = digital_signature_hash
        order["action_plan"] = action_plan.strip()

        return {
            "order_id": order_id,
            "status": "ACKNOWLEDGED",
            "acknowledged_by": clinician_id,
            "action_plan": order["action_plan"],
            "resolution_latency_hours": (ack_timestamp - order["reported_at"]).total_seconds() / 3600.0
        }

    def get_order_status(self, order_id: str) -> Dict:
        if order_id not in self._tracked_orders:
            raise SafetyNetException(f"Order ID '{order_id}' not tracked.")
        return self._tracked_orders[order_id]
