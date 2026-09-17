"""
Test Suite: test_grievance_nps.py
Phase 13: Patient Experience — Grievance Redressal & Net Promoter Score (NPS) Engine
Mandate / Quality Gate 2:
  - Multi-channel grievance lodging (WhatsApp, Kiosk, Portal, Desk).
  - Inviolable Quality Gate 2: Patient grievance filed via WhatsApp escalates
    automatically to Department Head (Level 2) if unresolved after 4 hours,
    and subsequently to Medical Superintendent (24h) and Ombudsman (48h).
  - Closed-loop resolution verification via patient OTP sign-off.
  - Multilingual patient satisfaction survey and NPS sentiment scoring.
  - Automatic 24-hour concierge callback task creation for ratings < 3/5 stars.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from grievance_nps_engine import (
    GrievanceNPSEngine,
    GrievanceChannel,
    GrievanceCategory,
    EscalationLevel,
    GrievanceStatus,
    GrievanceError,
)


class TestGrievanceNPSEngine(unittest.TestCase):

    def setUp(self):
        self.engine = GrievanceNPSEngine()

    def test_quality_gate_2_whatsapp_grievance_auto_escalation_after_4_hours(self):
        """
        Quality Gate 2:
        Patient grievance filed via WhatsApp escalates automatically to Department Head
        if unresolved after 4 hours.
        """
        initial_time = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)

        ticket = self.engine.lodge_grievance(
            ticket_id="TKT-WA-2026-001",
            patient_id="PAT-WA-771",
            patient_name="Pooja Mukherjee",
            phone_number="+91-9831122445",
            channel=GrievanceChannel.WHATSAPP,
            category=GrievanceCategory.NURSING_CARE,
            complaint_text="Night shift bell unanswered for 45 minutes when IV drip finished.",
            submitted_at=initial_time,
        )

        self.assertEqual(ticket.current_level, EscalationLevel.LEVEL_1_DUTY_OFFICER)
        self.assertEqual(ticket.status, GrievanceStatus.SUBMITTED)

        # 1. Evaluate after 2 hours (Within 4h SLA) -> No escalation
        events_2h = self.engine.evaluate_sla_escalations(current_time=initial_time + timedelta(hours=2))
        self.assertEqual(len(events_2h), 0)
        self.assertEqual(ticket.current_level, EscalationLevel.LEVEL_1_DUTY_OFFICER)

        # 2. Evaluate after 4.5 hours (> 4h SLA) -> Auto-escalate to Level 2: Department Head
        events_4h = self.engine.evaluate_sla_escalations(current_time=initial_time + timedelta(hours=4.5))
        self.assertEqual(len(events_4h), 1)
        self.assertEqual(events_4h[0]["new_level"], EscalationLevel.LEVEL_2_DEPT_HEAD.value)
        self.assertEqual(events_4h[0]["target_authority"], "Head of Department (HOD)")
        self.assertEqual(ticket.current_level, EscalationLevel.LEVEL_2_DEPT_HEAD)
        self.assertEqual(ticket.status, GrievanceStatus.ESCALATED_L2)
        self.assertEqual(ticket.assigned_officer_id, "HEAD_OF_DEPARTMENT")

        # 3. Evaluate after 25 hours (> 24h SLA) -> Auto-escalate to Level 3: Medical Superintendent
        events_25h = self.engine.evaluate_sla_escalations(current_time=initial_time + timedelta(hours=25))
        self.assertEqual(len(events_25h), 1)
        self.assertEqual(events_25h[0]["new_level"], EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT.value)
        self.assertEqual(ticket.current_level, EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT)
        self.assertEqual(ticket.status, GrievanceStatus.ESCALATED_L3)

    def test_closed_loop_resolution_verification(self):
        """Tests resolution flow with mandatory patient OTP confirmation."""
        ticket = self.engine.lodge_grievance(
            ticket_id="TKT-PORTAL-002",
            patient_id="PAT-PORT-99",
            patient_name="Rahul Varma",
            phone_number="+91-9988776655",
            channel=GrievanceChannel.PORTAL,
            category=GrievanceCategory.BILLING_DISPUTE,
            complaint_text="Duplicate pharmacy charge on final bill.",
        )

        # Officer marks resolved
        self.engine.resolve_grievance(
            ticket_id=ticket.ticket_id,
            resolution_notes="Duplicate item reversed; revised discharge bill issued.",
            officer_id="BILLING-MGR-1",
        )
        self.assertEqual(ticket.status, GrievanceStatus.RESOLVED_PENDING_VERIFICATION)

        # Patient confirms resolution with OTP
        verif = self.engine.verify_patient_resolution_satisfaction(
            ticket_id=ticket.ticket_id,
            verification_otp="7492",
            is_satisfied=True,
        )
        self.assertEqual(verif["status"], GrievanceStatus.CLOSED_VERIFIED.value)
        self.assertEqual(ticket.status, GrievanceStatus.CLOSED_VERIFIED)

    def test_nps_survey_and_negative_rating_concierge_callback(self):
        """Tests NPS survey feedback; rating < 3/5 stars triggers mandatory 24-hour concierge callback."""
        # 1. High rating feedback (5 stars, NPS 10)
        fb_pos = self.engine.submit_patient_feedback(
            feedback_id="FB-POS-01",
            patient_id="PAT-POS-1",
            overall_rating_1_to_5=5,
            nps_score_0_to_10=10,
            free_text_comment="Excellent nursing care and compassionate doctors, thank you!",
        )
        self.assertFalse(fb_pos.requires_concierge_callback)
        self.assertGreater(fb_pos.sentiment_score, 0.0)

        # 2. Negative rating feedback (2 stars, NPS 3)
        fb_neg = self.engine.submit_patient_feedback(
            feedback_id="FB-NEG-02",
            patient_id="PAT-NEG-2",
            overall_rating_1_to_5=2,
            nps_score_0_to_10=3,
            free_text_comment="Delayed discharge process and rude billing staff.",
        )
        self.assertTrue(fb_neg.requires_concierge_callback)
        self.assertLess(fb_neg.sentiment_score, 0.0)

        # Confirm concierge callback task created
        tasks = self.engine.get_pending_concierge_callbacks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["patient_id"], "PAT-NEG-2")
        self.assertEqual(tasks[0]["sla_hours"], 24)


if __name__ == "__main__":
    unittest.main()
