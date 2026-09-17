#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18: SYNDROMIC PROTOCOL ENGINE TEST SUITE
====================================================================================================
Tests:
1. 8 Universal Syndromic Archetype Care Plan Generation.
2. 5-10 Hour Supportive Holding Plan Formulation.
3. DRE Safety Firewall Integration (blocking unsafe supportive medications).
4. Geriatric fracture protocol: Paracetamol approved, NSAID blacklisted.
5. Trilingual caregiver guidance validation (English, Bengali, Hindi).
"""
import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from syndromic_protocol_engine import (
    SyndromicProtocolEngine,
    SyndromicArchetype
)


class TestSyndromicProtocolEngine(unittest.TestCase):

    def setUp(self):
        self.tenant_id = "00000000-0000-0000-0000-000000000001"
        self.engine = SyndromicProtocolEngine(tenant_id=self.tenant_id)

    def test_acs_care_plan_and_aspirin_order(self):
        """Verifies ACS archetype generates chewable Aspirin and sublingual Nitroglycerin with SBP >= 100."""
        plan = self.engine.generate_holding_plan(
            patient_id="PAT-ACS-01",
            syndrome=SyndromicArchetype.ACUTE_CORONARY_SYNDROME,
            patient_age=55,
            is_female=False,
            patient_weight_kg=72.0,
            vitals={"systolic_bp": 130.0, "spo2": 97.0, "heart_rate": 88.0},
            current_medications=[],
            known_allergies=[],
            estimated_transit_hours=5.0
        )
        self.assertEqual(plan.urgency_tier, "RESUSCITATION")
        self.assertTrue(any("Aspirin chewable" in m.drug_name for m in plan.supportive_medications))
        self.assertTrue(any("Nitroglycerin" in m.drug_name for m in plan.supportive_medications))
        self.assertTrue(len(plan.vernacular_caregiver_guidance["bn"]) > 0)
        self.assertTrue(len(plan.vernacular_caregiver_guidance["hi"]) > 0)

    def test_acs_blocks_nitrates_when_sbp_under_100(self):
        """Verifies that Nitroglycerin is omitted from orders and added to blacklist when SBP < 100."""
        plan = self.engine.generate_holding_plan(
            patient_id="PAT-ACS-HYPO-02",
            syndrome=SyndromicArchetype.ACUTE_CORONARY_SYNDROME,
            patient_age=60,
            is_female=True,
            patient_weight_kg=60.0,
            vitals={"systolic_bp": 85.0, "spo2": 95.0}, # Hypotensive
            current_medications=[],
            known_allergies=[]
        )
        self.assertFalse(any("Nitroglycerin" in m.drug_name for m in plan.supportive_medications))
        self.assertTrue(any("DO NOT ADMINISTER NITROGLYCERIN" in b for b in plan.inviolable_blacklists))

    def test_geriatric_trauma_fracture_analgesia_and_nsaid_block(self):
        """Verifies 86yo female hip fracture patient receives Paracetamol while NSAIDs are strictly blacklisted."""
        plan = self.engine.generate_holding_plan(
            patient_id="PAT-HIP-86F",
            syndrome=SyndromicArchetype.SEVERE_TRAUMA_FRACTURE,
            patient_age=86,
            is_female=True,
            patient_weight_kg=60.0,
            vitals={"systolic_bp": 130.0, "diastolic_bp": 90.0, "spo2": 97.0, "vomiting_active": True},
            current_medications=[],
            known_allergies=[]
        )
        # Paracetamol IV ordered for severe pain
        self.assertTrue(any("Paracetamol" in m.drug_name for m in plan.supportive_medications))
        # NSAIDs explicitly blacklisted for geriatric patient
        self.assertTrue(any("DO NOT ADMINISTER NSAIDs" in b for b in plan.inviolable_blacklists))
        # Bengali guidance contains immobilize and splint instructions
        self.assertTrue(any("আহত পা একদম নাড়াচাড়া করবেন না" in msg for msg in plan.vernacular_caregiver_guidance["bn"]))

    def test_dre_safety_firewall_filters_contraindicated_supportive_med(self):
        """Verifies that if a patient has documented allergy to an empiric supportive drug, DRE intercepts it."""
        plan = self.engine.generate_holding_plan(
            patient_id="PAT-SEPSIS-ALLERGY",
            syndrome=SyndromicArchetype.SEPTIC_SHOCK_FEBRILE,
            patient_age=50,
            is_female=False,
            patient_weight_kg=70.0,
            vitals={"systolic_bp": 80.0, "spo2": 92.0},
            current_medications=[],
            known_allergies=["penicillin", "cephalosporin", "ceftriaxone"] # Documented allergy
        )
        # Ceftriaxone should be blocked by DRE and moved to blacklist
        self.assertFalse(any("Ceftriaxone" in m.drug_name for m in plan.supportive_medications))
        self.assertTrue(any("BLOCKED BY SAFETY FIREWALL" in b for b in plan.inviolable_blacklists))

    def test_toxicology_snakebite_blacklists_tourniquets(self):
        """Verifies snakebite care plan explicitly blacklists arterial tourniquets, cutting, and sucking."""
        plan = self.engine.generate_holding_plan(
            patient_id="PAT-SNAKE-01",
            syndrome=SyndromicArchetype.TOXICOLOGY_SNAKEBITE,
            patient_age=25,
            is_female=False,
            patient_weight_kg=65.0,
            vitals={"systolic_bp": 110.0, "spo2": 98.0},
            current_medications=[],
            known_allergies=[]
        )
        self.assertTrue(any("DO NOT APPLY ARTERIAL TOURNIQUETS" in b for b in plan.inviolable_blacklists))
        self.assertTrue(any("DO NOT CUT, INCISE, OR SUCK" in b for b in plan.inviolable_blacklists))


if __name__ == "__main__":
    unittest.main()
