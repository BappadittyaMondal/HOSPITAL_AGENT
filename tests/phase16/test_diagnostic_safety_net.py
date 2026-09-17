"""
====================================================================================================
TEST SUITE: PHASE 16.2 — CLOSED-LOOP DIAGNOSTIC SAFETY NET & FAILURE-TO-RESCUE SENTINEL
====================================================================================================
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from diagnostic_safety_net import (
    DiagnosticSafetyNetEngine,
    DiagnosticOrderPriority,
    EscalationLevel,
    IncompleteDiagnosticActionPlanError,
    InvalidAcknowledgementError,
    SafetyNetException
)


class TestDiagnosticSafetyNet(unittest.TestCase):

    def setUp(self):
        self.sentinel = DiagnosticSafetyNetEngine()

    def test_critical_pathology_registration_and_sla_escalation(self):
        """Quality Gate 2: Unacknowledged critical biopsy auto-escalates at 48h to HOD and 72h to MS."""
        t0 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Register critical histopathology biopsy positive for Invasive Ductal Carcinoma
        order = self.sentinel.register_diagnostic_result(
            order_id="BX-2026-9901",
            patient_id="P-8801",
            ordering_doctor_id="DR-SURG-01",
            department="SURGICAL_ONCOLOGY",
            test_name="Right Breast Tru-Cut Biopsy",
            result_summary="Positive for Invasive Ductal Carcinoma, Grade III",
            priority=DiagnosticOrderPriority.CRITICAL_PATHOLOGY,
            reported_at=t0
        )
        self.assertEqual(order["status"], "UNACKNOWLEDGED")
        self.assertEqual(order["current_escalation_level"], EscalationLevel.LEVEL_1_TREATING_CONSULTANT)

        # Simulate 24 hours elapsed: Still within consultant SLA
        t_24h = t0 + timedelta(hours=24)
        escalations_24 = self.sentinel.evaluate_sla_escalations(t_24h)
        self.assertEqual(len(escalations_24), 0)

        # Simulate 49 hours elapsed: Breaches 48h SLA -> Escalates to Department Head (Level 2)
        t_49h = t0 + timedelta(hours=49)
        escalations_49 = self.sentinel.evaluate_sla_escalations(t_49h)
        self.assertEqual(len(escalations_49), 1)
        self.assertEqual(escalations_49[0]["escalated_to"], EscalationLevel.LEVEL_2_DEPARTMENT_HEAD)

        # Simulate 73 hours elapsed: Breaches 72h SLA -> Escalates to Medical Superintendent (Level 3)
        t_73h = t0 + timedelta(hours=73)
        escalations_73 = self.sentinel.evaluate_sla_escalations(t_73h)
        self.assertEqual(len(escalations_73), 1)
        self.assertEqual(escalations_73[0]["escalated_to"], EscalationLevel.LEVEL_3_MEDICAL_SUPERINTENDENT)

    def test_acknowledgement_requires_substantive_action_plan(self):
        """Quality Gate 2: Closing an unacknowledged critical report without action plan is BLOCKED."""
        t0 = datetime.now(timezone.utc)
        self.sentinel.register_diagnostic_result(
            order_id="CULT-4402",
            patient_id="P-9912",
            ordering_doctor_id="DR-MED-04",
            department="INTERNAL_MEDICINE",
            test_name="Blood Culture",
            result_summary="Staphylococcus aureus (MRSA positive)",
            priority=DiagnosticOrderPriority.CRITICAL_PATHOLOGY,
            reported_at=t0
        )

        # Attempting acknowledgement with empty or trivial action plan raises error
        with self.assertRaises(IncompleteDiagnosticActionPlanError):
            self.sentinel.acknowledge_result(
                order_id="CULT-4402",
                clinician_id="DR-MED-04",
                digital_signature_hash="sha256_sig_abc123",
                action_plan="noted"  # < 10 characters / trivial
            )

        # Valid substantive action plan succeeds
        ack_res = self.sentinel.acknowledge_result(
            order_id="CULT-4402",
            clinician_id="DR-MED-04",
            digital_signature_hash="sha256_sig_valid_hash_999",
            action_plan="Patient recalled immediately; started IV Vancomycin target trough 15 mcg/mL; ID consult placed"
        )
        self.assertEqual(ack_res["status"], "ACKNOWLEDGED")

        # After acknowledgement, subsequent SLA evaluation produces no escalations
        future_time = t0 + timedelta(days=7)
        future_escalations = self.sentinel.evaluate_sla_escalations(future_time)
        self.assertEqual(len(future_escalations), 0)


if __name__ == "__main__":
    unittest.main()
