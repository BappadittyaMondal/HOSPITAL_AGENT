#!/usr/bin/env python3
"""
PROJECT 'HOSPITAL' — PHASE 31: VERNACULAR CLINICAL VOICE-TO-FHIR SCRIBE TEST SUITE
Module: tests/phase31/test_vernacular_voice_scribe.py
Validates:
  1. Bengali vernacular chest pain transcript parsing (crushing pain, cold sweat, left arm radiation).
  2. Hindi vernacular acute dyspnea and chest pressure extraction.
  3. Automatic red flag identification and emergency alert trigger.
  4. Compliant HL7 FHIR R4 Bundle serialization with Encounter and Observation entries.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../services/core-api')))
from vernacular_voice_scribe import VernacularVoiceScribeEngine, vernacular_voice_scribe


class TestVernacularVoiceScribe(unittest.TestCase):

    def setUp(self):
        self.scribe = vernacular_voice_scribe

    def test_bengali_atypical_acs_parsing(self):
        """Spoken Bengali input with chest pressure, sweat, and arm pain triggers red flag alert."""
        transcript = "daktar babu amar buke chap chap byatha hochhe sathe khub ghaam dichhe ar baam haate byatha jachhe"
        bundle = self.scribe.parse_vernacular_transcript(transcript, patient_id="PAT-BENG-01")

        self.assertEqual(bundle.language_detected, "BENGALI")
        self.assertTrue(bundle.red_flag_alert_triggered)
        concepts = [o.concept_name for o in bundle.observations]
        self.assertIn("Retrosternal crushing chest pain", concepts)
        self.assertIn("Diaphoresis / Cold sweat", concepts)
        self.assertIn("Pain radiating to left arm", concepts)

    def test_hindi_dyspnea_and_pressure_parsing(self):
        """Spoken Hindi input with chest pressure and breathlessness is extracted accurately."""
        transcript = "mujhe seene me dabav lag raha hai aur thoda saans phoolna shuru ho gaya hai"
        bundle = self.scribe.parse_vernacular_transcript(transcript, patient_id="PAT-HINDI-01")

        self.assertEqual(bundle.language_detected, "HINDI")
        self.assertTrue(bundle.red_flag_alert_triggered)
        concepts = [o.concept_name for o in bundle.observations]
        self.assertIn("Crushing chest pressure", concepts)
        self.assertIn("Dyspnea / Breathlessness", concepts)

    def test_fhir_r4_bundle_serialization_compliance(self):
        """Verified that generated bundle contains valid HL7 FHIR R4 Encounter and Observation resources."""
        transcript = "buke byatha hochhe"
        bundle = self.scribe.parse_vernacular_transcript(transcript, patient_id="PAT-FHIR-01")

        fhir = bundle.fhir_bundle_json
        self.assertEqual(fhir["resourceType"], "Bundle")
        self.assertEqual(fhir["type"], "collection")
        self.assertTrue(len(fhir["entry"]) >= 2)  # 1 Encounter + at least 1 Observation

        # Check Encounter
        enc_entry = fhir["entry"][0]["resource"]
        self.assertEqual(enc_entry["resourceType"], "Encounter")
        self.assertEqual(enc_entry["subject"]["reference"], "Patient/PAT-FHIR-01")

        # Check Observation
        obs_entry = fhir["entry"][1]["resource"]
        self.assertEqual(obs_entry["resourceType"], "Observation")
        self.assertEqual(obs_entry["status"], "preliminary")
        self.assertIn("snomed.info/sct", obs_entry["code"]["coding"][0]["system"])


if __name__ == '__main__':
    unittest.main()
