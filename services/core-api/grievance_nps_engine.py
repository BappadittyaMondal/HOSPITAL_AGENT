"""
PROJECT "HOSPITAL" — PHASE 13: PATIENT EXPERIENCE
Module: grievance_nps_engine.py
Operational Scope:
  - Sub-task 13.5: Multi-Channel Patient Grievance Redressal & Ombudsman System (Gap 13)
  - Quality Gate 2: Strict SLA Escalation Hierarchy (Level 1 4h → Level 2 HOD 24h → Level 3 MS 48h → Level 4 Ombudsman 7d)
  - Closed-Loop Resolution Tracking with Mandatory Patient Verification
  - Sub-task 13.6: Multilingual Patient Experience & Net Promoter Score (NPS) Engine (Gap 34)
  - Sentiment Analysis & Mandatory 24-Hour Concierge Callback for Ratings < 3/5 Stars
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any


class GrievanceError(Exception):
    """Base exception for grievance management operations."""
    pass


class GrievanceChannel(str, Enum):
    WHATSAPP = "WHATSAPP"
    KIOSK = "KIOSK"
    PORTAL = "PORTAL"
    PHYSICAL_DESK = "PHYSICAL_DESK"


class GrievanceCategory(str, Enum):
    CLINICAL_CARE = "CLINICAL_CARE"
    NURSING_CARE = "NURSING_CARE"
    BILLING_DISPUTE = "BILLING_DISPUTE"
    SANITATION = "SANITATION"
    PHARMACY_DELAY = "PHARMACY_DELAY"
    STAFF_BEHAVIOR = "STAFF_BEHAVIOR"


class EscalationLevel(str, Enum):
    LEVEL_1_DUTY_OFFICER = "LEVEL_1_DUTY_OFFICER"    # 4h SLA
    LEVEL_2_DEPT_HEAD = "LEVEL_2_DEPT_HEAD"          # 24h SLA
    LEVEL_3_MEDICAL_SUPERINTENDENT = "LEVEL_3_MS"    # 48h SLA
    LEVEL_4_OMBUDSMAN = "LEVEL_4_OMBUDSMAN"          # 7 days SLA


class GrievanceStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    IN_INVESTIGATION = "IN_INVESTIGATION"
    ESCALATED_L2 = "ESCALATED_L2"
    ESCALATED_L3 = "ESCALATED_L3"
    ESCALATED_L4 = "ESCALATED_L4"
    RESOLVED_PENDING_VERIFICATION = "RESOLVED_PENDING_VERIFICATION"
    CLOSED_VERIFIED = "CLOSED_VERIFIED"


@dataclass
class GrievanceTicket:
    ticket_id: str
    patient_id: str
    patient_name: str
    phone_number: str
    channel: GrievanceChannel
    category: GrievanceCategory
    complaint_text: str
    submitted_at: datetime
    current_level: EscalationLevel = EscalationLevel.LEVEL_1_DUTY_OFFICER
    status: GrievanceStatus = GrievanceStatus.SUBMITTED
    assigned_officer_id: str = "OFFICER-DUTY-1"
    resolution_notes: str = ""
    patient_verification_otp: str = "7492"
    is_patient_satisfied: Optional[bool] = None
    resolved_at: Optional[datetime] = None


@dataclass
class PatientSurveyFeedback:
    feedback_id: str
    patient_id: str
    overall_rating_1_to_5: int
    nps_score_0_to_10: int          # 9-10 Promoter, 7-8 Passive, 0-6 Detractor
    free_text_comment: str
    sentiment_score: float          # -1.0 (Negative) to +1.0 (Positive)
    submitted_at: datetime
    requires_concierge_callback: bool = False
    concierge_task_id: Optional[str] = None


class GrievanceNPSEngine:
    """
    Patient Grievance Redressal and Net Promoter Score (NPS) Experience Engine.
    Enforces statutory NABH/MoHFW SLA escalations and closed-loop resolution verification.
    """

    # SLA Windows in Hours
    SLA_L1_HOURS = 4
    SLA_L2_HOURS = 24
    SLA_L3_HOURS = 48
    SLA_L4_HOURS = 168  # 7 days

    def __init__(self):
        self._grievances: Dict[str, GrievanceTicket] = {}
        self._surveys: Dict[str, PatientSurveyFeedback] = {}
        self._concierge_callback_tasks: List[Dict[str, Any]] = []

    def lodge_grievance(
        self,
        ticket_id: str,
        patient_id: str,
        patient_name: str,
        phone_number: str,
        channel: GrievanceChannel,
        category: GrievanceCategory,
        complaint_text: str,
        submitted_at: Optional[datetime] = None,
    ) -> GrievanceTicket:
        """Lodges patient complaint across WhatsApp, Kiosk, Portal, or Desk."""
        if ticket_id in self._grievances:
            raise GrievanceError(f"Duplicate grievance ticket {ticket_id}")

        ticket = GrievanceTicket(
            ticket_id=ticket_id,
            patient_id=patient_id,
            patient_name=patient_name,
            phone_number=phone_number,
            channel=channel,
            category=category,
            complaint_text=complaint_text,
            submitted_at=submitted_at or datetime.now(timezone.utc),
            current_level=EscalationLevel.LEVEL_1_DUTY_OFFICER,
            status=GrievanceStatus.SUBMITTED,
        )
        self._grievances[ticket_id] = ticket
        return ticket

    def evaluate_sla_escalations(self, current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Quality Gate 2: Evaluates pending grievances against SLA thresholds.
        If unresolved after 4 hours -> Auto-escalates to Department Head (Level 2).
        If unresolved after 24 hours -> Auto-escalates to Medical Superintendent (Level 3).
        If unresolved after 48 hours -> Auto-escalates to Ombudsman (Level 4).
        """
        now = current_time or datetime.now(timezone.utc)
        escalation_events: List[Dict[str, Any]] = []

        for ticket in self._grievances.values():
            if ticket.status in (GrievanceStatus.CLOSED_VERIFIED, GrievanceStatus.RESOLVED_PENDING_VERIFICATION):
                continue

            elapsed_hours = (now - ticket.submitted_at).total_seconds() / 3600.0

            if elapsed_hours >= self.SLA_L3_HOURS and ticket.current_level != EscalationLevel.LEVEL_4_OMBUDSMAN:
                ticket.current_level = EscalationLevel.LEVEL_4_OMBUDSMAN
                ticket.status = GrievanceStatus.ESCALATED_L4
                ticket.assigned_officer_id = "OMBUDSMAN_BOARD"
                escalation_events.append({
                    "ticket_id": ticket.ticket_id,
                    "new_level": EscalationLevel.LEVEL_4_OMBUDSMAN.value,
                    "elapsed_hours": round(elapsed_hours, 1),
                    "target_authority": "Hospital Ombudsman Board",
                })

            elif elapsed_hours >= self.SLA_L2_HOURS and ticket.current_level in (EscalationLevel.LEVEL_1_DUTY_OFFICER, EscalationLevel.LEVEL_2_DEPT_HEAD):
                ticket.current_level = EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT
                ticket.status = GrievanceStatus.ESCALATED_L3
                ticket.assigned_officer_id = "MEDICAL_SUPERINTENDENT"
                escalation_events.append({
                    "ticket_id": ticket.ticket_id,
                    "new_level": EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT.value,
                    "elapsed_hours": round(elapsed_hours, 1),
                    "target_authority": "Medical Superintendent",
                })

            elif elapsed_hours >= self.SLA_L1_HOURS and ticket.current_level == EscalationLevel.LEVEL_1_DUTY_OFFICER:
                ticket.current_level = EscalationLevel.LEVEL_2_DEPT_HEAD
                ticket.status = GrievanceStatus.ESCALATED_L2
                ticket.assigned_officer_id = "HEAD_OF_DEPARTMENT"
                escalation_events.append({
                    "ticket_id": ticket.ticket_id,
                    "new_level": EscalationLevel.LEVEL_2_DEPT_HEAD.value,
                    "elapsed_hours": round(elapsed_hours, 1),
                    "target_authority": "Head of Department (HOD)",
                })

        return escalation_events

    def resolve_grievance(self, ticket_id: str, resolution_notes: str, officer_id: str) -> Dict[str, Any]:
        """Marks complaint resolved, awaiting patient sign-off/OTP confirmation."""
        if ticket_id not in self._grievances:
            raise GrievanceError(f"Ticket {ticket_id} not found.")

        ticket = self._grievances[ticket_id]
        ticket.status = GrievanceStatus.RESOLVED_PENDING_VERIFICATION
        ticket.resolution_notes = resolution_notes
        ticket.resolved_at = datetime.now(timezone.utc)

        return {
            "ticket_id": ticket_id,
            "status": ticket.status.value,
            "resolution_notes": resolution_notes,
            "patient_verification_required": True,
        }

    def verify_patient_resolution_satisfaction(
        self,
        ticket_id: str,
        verification_otp: str,
        is_satisfied: bool,
    ) -> Dict[str, Any]:
        """Closed-loop verification: patient enters OTP to confirm resolution."""
        if ticket_id not in self._grievances:
            raise GrievanceError(f"Ticket {ticket_id} not found.")

        ticket = self._grievances[ticket_id]
        if verification_otp != ticket.patient_verification_otp:
            raise GrievanceError("Invalid verification OTP.")

        ticket.is_patient_satisfied = is_satisfied
        if is_satisfied:
            ticket.status = GrievanceStatus.CLOSED_VERIFIED
        else:
            # If patient is unsatisfied, escalate to Medical Superintendent
            ticket.current_level = EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT
            ticket.status = GrievanceStatus.ESCALATED_L3
            ticket.assigned_officer_id = "MEDICAL_SUPERINTENDENT"

        return {
            "ticket_id": ticket_id,
            "status": ticket.status.value,
            "is_patient_satisfied": is_satisfied,
        }

    # =========================================================================
    # 13.6 PATIENT FEEDBACK & NPS ENGINE
    # =========================================================================

    def _analyze_sentiment(self, text: str) -> float:
        """Simple deterministic NLP sentiment scoring (-1.0 to +1.0)."""
        lower = text.lower()
        positive_words = ["excellent", "great", "caring", "wonderful", "compassionate", "helpful", "good", "ভালো", "ধন্যবাদ", "उत्कृष्ट"]
        negative_words = ["bad", "horrible", "rude", "delayed", "dirty", "unhelpful", "painful", "খারাপ", "দেরি", "गंदा", "खराब"]

        pos_count = sum(1 for w in positive_words if w in lower)
        neg_count = sum(1 for w in negative_words if w in lower)

        if pos_count == 0 and neg_count == 0:
            return 0.0
        return round((pos_count - neg_count) / max(1, pos_count + neg_count), 2)

    def submit_patient_feedback(
        self,
        feedback_id: str,
        patient_id: str,
        overall_rating_1_to_5: int,
        nps_score_0_to_10: int,
        free_text_comment: str,
    ) -> PatientSurveyFeedback:
        """
        Submits patient experience survey.
        Mandatory Concierge Callback: Any rating < 3/5 stars triggers an automatic
        24-hour callback task for the Patient Relations team.
        """
        if overall_rating_1_to_5 < 1 or overall_rating_1_to_5 > 5:
            raise GrievanceError("Overall rating must be between 1 and 5.")
        if nps_score_0_to_10 < 0 or nps_score_0_to_10 > 10:
            raise GrievanceError("NPS score must be between 0 and 10.")

        sentiment = self._analyze_sentiment(free_text_comment)
        requires_callback = overall_rating_1_to_5 < 3 or nps_score_0_to_10 <= 6

        concierge_id = None
        if requires_callback:
            concierge_id = f"CONCIERGE-TASK-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}"
            self._concierge_callback_tasks.append({
                "task_id": concierge_id,
                "patient_id": patient_id,
                "rating": overall_rating_1_to_5,
                "nps": nps_score_0_to_10,
                "comment": free_text_comment,
                "sla_hours": 24,
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
            })

        feedback = PatientSurveyFeedback(
            feedback_id=feedback_id,
            patient_id=patient_id,
            overall_rating_1_to_5=overall_rating_1_to_5,
            nps_score_0_to_10=nps_score_0_to_10,
            free_text_comment=free_text_comment,
            sentiment_score=sentiment,
            submitted_at=datetime.now(timezone.utc),
            requires_concierge_callback=requires_callback,
            concierge_task_id=concierge_id,
        )
        self._surveys[feedback_id] = feedback
        return feedback

    def get_pending_concierge_callbacks(self) -> List[Dict[str, Any]]:
        return list(self._concierge_callback_tasks)
