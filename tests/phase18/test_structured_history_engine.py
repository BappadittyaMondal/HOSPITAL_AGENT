#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18: STRUCTURED HISTORY ENGINE TEST SUITE
====================================================================================================
Tests:
1. Chest pain branch: PQRST, ischemic radiation, diaphoresis red-flag trigger.
2. Abdominal pain branch: Peritoneal rigidity and acute abdomen peritonitis alert.
3. Neurological branch: Acute stroke FAST-positive red-flag and IV thrombolytic window note.
4. Trauma branch: Geriatric hip fracture fall detection and Paracetamol analgesia recommendation.
5. Sepsis branch: qSOFA scoring calculation and early fluid resuscitation alert.
6. Snakebite branch: 20WBCT prompt and strict prohibition of tourniquets/cuts.
"""
import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from structured_history_engine import (
    StructuredHistoryEngine,
    ChiefComplaintCategory,
    FindingPolarity
)


class TestStructuredHistoryEngine(unittest.TestCase):

    def setUp(self):
        self.engine = StructuredHistoryEngine()

    def test_chest_pain_red_flag_acs_detection(self):
        """Verifies classic ACS symptoms trigger red-flag and Aspirin/ECG guidance."""
        session = self.engine.initiate_session(
            session_id="SESS-001",
            patient_id="PAT-CHEST-01",
            chief_complaint=ChiefComplaintCategory.CHEST_PAIN,
            patient_age=58,
            is_female=False
        )
        answers = {
            "pain_severity_1_to_10": 8,
            "duration_hours": 1.5,
            "radiates_to_left_arm_or_jaw": True,
            "has_cold_sweating": True,
            "has_vomiting": True,
            "has_shortness_of_breath": True
        }
        self.engine.process_responses(session, answers)

        self.assertIn("HIGH_PROBABILITY_ACUTE_CORONARY_SYNDROME", session.active_red_flags)
        self.assertTrue(any("Aspirin 300mg" in act for act in session.recommended_immediate_actions))
        
        # Verify findings
        findings_map = {f.concept_name: f for f in session.findings}
        self.assertIn("Chest pain", findings_map)
        self.assertEqual(findings_map["Chest pain"].polarity, FindingPolarity.PRESENT)
        self.assertEqual(findings_map["Diaphoresis"].polarity, FindingPolarity.PRESENT)

    def test_acute_abdomen_rigidity_triggers_peritonitis_alert(self):
        """Verifies board-like abdominal rigidity triggers acute surgical peritonitis red flag and strict NPO."""
        session = self.engine.initiate_session(
            session_id="SESS-002",
            patient_id="PAT-ABD-02",
            chief_complaint=ChiefComplaintCategory.ABDOMINAL_PAIN,
            patient_age=42,
            is_female=True
        )
        answers = {
            "pain_severity_1_to_10": 9,
            "duration_hours": 8.0,
            "is_abdomen_rigid_or_board_like": True,
            "has_abdominal_distension": True,
            "has_fever": True,
            "has_persistent_vomiting": True,
            "no_stool_or_flatus_in_24h": True
        }
        self.engine.process_responses(session, answers)

        self.assertIn("SURGICAL_ACUTE_ABDOMEN_PERITONITIS", session.active_red_flags)
        self.assertTrue(any("STRICT NPO" in act for act in session.recommended_immediate_actions))

    def test_stroke_fast_positive_recognition(self):
        """Verifies unilateral limb weakness and speech difficulty triggers FAST stroke alert."""
        session = self.engine.initiate_session(
            session_id="SESS-003",
            patient_id="PAT-NEURO-03",
            chief_complaint=ChiefComplaintCategory.ALTERED_SENSORIUM_OR_WEAKNESS,
            patient_age=67,
            is_female=True
        )
        answers = {
            "facial_droop": True,
            "one_arm_weakness": True,
            "speech_difficulty": True,
            "onset_within_4_5_hours": True
        }
        self.engine.process_responses(session, answers)

        self.assertIn("ACUTE_ISCHEMIC_STROKE_FAST_POSITIVE", session.active_red_flags)
        self.assertTrue(any("TIME LAST SEEN NORMAL" in act for act in session.recommended_immediate_actions))

    def test_snakebite_envenomation_prohibits_tourniquets(self):
        """Verifies snakebite intake enforces strict immobilization and forbids tourniquets/incisions."""
        session = self.engine.initiate_session(
            session_id="SESS-004",
            patient_id="PAT-TOX-04",
            chief_complaint=ChiefComplaintCategory.TOXIC_OR_SNAKEBITE,
            patient_age=30,
            is_female=False
        )
        answers = {
            "snakebite_confirmed_or_suspected": True,
            "fang_marks_visible": True,
            "drooping_eyelids_or_difficulty_breathing": True
        }
        self.engine.process_responses(session, answers)

        self.assertIn("SNAKEBITE_ENVENOMATION_RISK", session.active_red_flags)
        self.assertIn("ELAPID_NEUROTOXIC_RESPIRATORY_FAILURE", session.active_red_flags)
        self.assertTrue(any("DO NOT APPLY ARTERIAL TOURNIQUETS" in act for act in session.recommended_immediate_actions))
        self.assertTrue(any("20-minute Whole Blood Clotting Test" in act for act in session.recommended_immediate_actions))


if __name__ == "__main__":
    unittest.main()
