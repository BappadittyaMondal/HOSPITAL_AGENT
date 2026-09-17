"""
Test Suite: test_post_discharge_chronic.py
Phase 13: Patient Experience — Automated Post-Discharge Follow-Up & Chronic Care Pathways
Mandate / Quality Gate 3:
  - Day 2 and Day 5 post-discharge automated check-in questionnaires.
  - Inviolable Quality Gate 3: Patient indicating "worse fever" on post-discharge
    WhatsApp check-in generates an immediate nurse callback task on the ward dashboard.
  - Longitudinal monitoring programs (Type 2 Diabetes, Hypertension, Heart Failure).
  - Rapid heart failure decompensation detection (> 2.0 kg fluid retention).
"""

import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from post_discharge_chronic_care import (
    PostDischargeChronicCareEngine,
    TriageSeverity,
    ChronicPathwayType,
    FollowUpError,
)


class TestPostDischargeChronicCare(unittest.TestCase):

    def setUp(self):
        self.engine = PostDischargeChronicCareEngine()

        self.encounter = self.engine.register_discharge_encounter(
            encounter_id="ENC-DISCH-001",
            patient_id="PAT-SURG-881",
            patient_name="Ananya Sen",
            phone_number="+91-9830112233",
            discharging_ward="SURGICAL_WARD_4",
            primary_diagnosis="Post-laparoscopic Cholecystectomy",
        )

    def test_quality_gate_3_worse_fever_triggers_stat_nurse_callback(self):
        """
        Quality Gate 3:
        Patient indicating "worse fever" on post-discharge WhatsApp check-in
        generates an immediate nurse callback task on the ward dashboard with 15-minute SLA.
        """
        # Patient replies on Day 2: "I am feeling worse fever and shivering since morning"
        result = self.engine.process_whatsapp_checkin_response(
            encounter_id="ENC-DISCH-001",
            checkin_day=2,
            patient_response_text="I am feeling worse fever and shivering since morning",
            has_fever=True,
        )

        self.assertEqual(result["status"], "RED_FLAG_TRIGGERED")
        self.assertEqual(result["severity"], TriageSeverity.RED_FLAG_EMERGENCY.value)
        self.assertEqual(result["dispatched_to_ward"], "SURGICAL_WARD_4")
        self.assertEqual(result["sla_minutes"], 15)
        self.assertIn("A senior triage nurse from your ward has been alerted", result["bot_reply"])

        # Check ward dashboard callback tasks
        callbacks = self.engine.get_pending_nurse_callbacks(ward_id="SURGICAL_WARD_4")
        self.assertEqual(len(callbacks), 1)

        task = callbacks[0]
        self.assertEqual(task.patient_id, "PAT-SURG-881")
        self.assertEqual(task.ward_id, "SURGICAL_WARD_4")
        self.assertEqual(task.severity, TriageSeverity.RED_FLAG_EMERGENCY)
        self.assertIn("worse fever", task.reported_symptom)
        self.assertEqual(task.sla_response_minutes, 15)
        self.assertFalse(task.is_completed)

    def test_normal_checkin_recovery(self):
        """Patient reporting healthy recovery generates positive confirmation without nurse callback."""
        result = self.engine.process_whatsapp_checkin_response(
            encounter_id="ENC-DISCH-001",
            checkin_day=5,
            patient_response_text="Feeling much better today, walking and eating normally.",
            reported_pain_score_1_to_10=1,
            has_fever=False,
        )

        self.assertEqual(result["status"], "RECOVERING_WELL")
        self.assertEqual(result["severity"], TriageSeverity.NORMAL_RECOVERY.value)

        # Confirm no callback created
        callbacks = self.engine.get_pending_nurse_callbacks(ward_id="SURGICAL_WARD_4")
        self.assertEqual(len(callbacks), 0)

    def test_chronic_pathway_heart_failure_fluid_overload(self):
        """Tests heart failure patient telemetry detecting > 2.0 kg fluid overload."""
        enrollment = self.engine.enroll_in_chronic_pathway(
            enrollment_id="ENR-HF-01",
            patient_id="PAT-CARDIO-99",
            pathway=ChronicPathwayType.HEART_FAILURE,
            baseline_weight_kg=68.0,
        )

        # Telemetry: weight jumped to 70.5 kg (+2.5 kg fluid retention)
        res = self.engine.log_chronic_telemetry(
            enrollment_id="ENR-HF-01",
            weight_kg=70.5,
        )

        self.assertTrue(res["requires_clinical_intervention"])
        self.assertIn("HEART FAILURE DECOMPENSATION ALERT", res["alerts_triggered"][0])
        self.assertIn("fluid overload", res["alerts_triggered"][0])


if __name__ == "__main__":
    unittest.main()
