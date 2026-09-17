"""
Test Suite: test_vernacular_discharge.py
Phase 13: Patient Experience — Trilingual Vernacular Discharge Dossier & Audio Prescriptions
Mandate / Quality Gate 1:
  - Generation of discharge dossier in Bengali (বাংলা), Hindi (हिंदी), and English.
  - Visual pictogram medication timetables (Morning, Afternoon, Evening, Night, Meal relation).
  - Inviolable Quality Gate 1: Vernacular translated prescription matches doctor's signed orders
    with 100.00% pharmacological accuracy in automated back-translation tests;
    any deviation in dosage or frequency strictly raises VernacularTranslationMismatchError.
  - Conversational vernacular audio prescription script synthesis.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from vernacular_discharge_engine import (
    VernacularDischargeEngine,
    SupportedLanguage,
    MealRelation,
    PrescribedMedication,
    PictogramMedicationCard,
    PictogramTimeSlot,
    VernacularTranslationMismatchError,
    VernacularError,
)


class TestVernacularDischargeEngine(unittest.TestCase):

    def setUp(self):
        self.engine = VernacularDischargeEngine()

        self.med_metformin = PrescribedMedication(
            drug_name="Metformin",
            dosage_mg=500.0,
            morning_dose=1,
            afternoon_dose=0,
            evening_dose=0,
            night_dose=1,
            duration_days=30,
            meal_relation=MealRelation.AFTER_MEAL,
        )

        self.med_amlodipine = PrescribedMedication(
            drug_name="Amlodipine",
            dosage_mg=5.0,
            morning_dose=1,
            afternoon_dose=0,
            evening_dose=0,
            night_dose=0,
            duration_days=30,
            meal_relation=MealRelation.BEFORE_MEAL,
        )

    def test_bengali_pictogram_dossier_and_quality_gate_1_success(self):
        """
        Quality Gate 1:
        Validates 100.00% certified pharmacological accuracy for Bengali vernacular dossier.
        """
        dossier = self.engine.generate_vernacular_discharge_dossier(
            dossier_id="DOS-BN-2026-001",
            patient_id="PAT-BN-101",
            patient_name="সুভাষ বোস (Subhash Bose)",
            mrn="MRN-781920",
            language=SupportedLanguage.BENGALI,
            discharge_date=datetime.now(timezone.utc),
            primary_diagnosis="Type 2 Diabetes Mellitus & Essential Hypertension",
            medications=[self.med_metformin, self.med_amlodipine],
        )

        self.assertTrue(dossier.is_pharmacologically_verified)
        self.assertEqual(len(dossier.pictogram_medications), 2)

        # Verify Metformin card
        card_met = dossier.pictogram_medications[0]
        self.assertEqual(card_met.drug_name_english, "Metformin")
        self.assertIn("মেটফরমিন", card_met.drug_name_vernacular)
        self.assertIn("৫০০", card_met.dosage_display)  # Bengali numeral 500
        self.assertEqual(card_met.meal_instruction_icon, "🍽️")
        self.assertIn("খাওয়ার পরে", card_met.meal_instruction_vernacular)

        # Verify Amlodipine card
        card_aml = dossier.pictogram_medications[1]
        self.assertEqual(card_aml.drug_name_english, "Amlodipine")
        self.assertIn("৫", card_aml.dosage_display)  # Bengali numeral 5
        self.assertEqual(card_aml.meal_instruction_icon, "🚫🍽️")

        # Verify audio prescription script was synthesized
        self.assertIn("ওষুধ Metformin ৫০০ মিলিগ্রাম", dossier.audio_prescription_script)
        self.assertIn("সকালে ১টি", dossier.audio_prescription_script)
        self.assertIn("রাতে ১টি", dossier.audio_prescription_script)

    def test_hindi_pictogram_dossier_and_quality_gate_1_success(self):
        """Validates Hindi vernacular generation with 100% back-translation accuracy."""
        dossier = self.engine.generate_vernacular_discharge_dossier(
            dossier_id="DOS-HI-2026-002",
            patient_id="PAT-HI-202",
            patient_name="रामेश्वर शर्मा (Rameshwar Sharma)",
            mrn="MRN-664411",
            language=SupportedLanguage.HINDI,
            discharge_date=datetime.now(timezone.utc),
            primary_diagnosis="Essential Hypertension",
            medications=[self.med_amlodipine],
        )

        self.assertTrue(dossier.is_pharmacologically_verified)
        card = dossier.pictogram_medications[0]
        self.assertIn("५", card.dosage_display)  # Devanagari numeral 5
        self.assertIn("भोजन से पहले", card.meal_instruction_vernacular)
        self.assertIn("दवा Amlodipine ५ मिलीग्राम", dossier.audio_prescription_script)

    def test_quality_gate_1_catches_lethal_dosage_deviation(self):
        """
        Quality Gate 1:
        If translation creates a dosage deviation (e.g. 500 mg translated as 50 mg),
        back-translation verification strictly catches it and raises VernacularTranslationMismatchError.
        """
        corrupted_card = PictogramMedicationCard(
            drug_name_english="Metformin",
            drug_name_vernacular="মেটফরমিন (Metformin)",
            dosage_display="৫০ মিগ্রা (mg)",  # Corrupted to 50 mg instead of 500 mg!
            meal_instruction_icon="🍽️",
            meal_instruction_vernacular="খাওয়ার পরে",
            timetable=[
                PictogramTimeSlot("Morning", "🌅", "সকাল", 1),
                PictogramTimeSlot("Afternoon", "☀️", "দুপুর", 0),
                PictogramTimeSlot("Evening", "🌇", "সন্ধ্যা", 0),
                PictogramTimeSlot("Night", "🌙", "রাত", 1),
            ],
            duration_vernacular="৩০ দিনের জন্য",
        )

        with self.assertRaises(VernacularTranslationMismatchError) as ctx:
            self.engine.verify_pharmacological_back_translation(
                original_orders=[self.med_metformin],
                cards=[corrupted_card],
            )

        self.assertIn("LETHAL DOSAGE MISMATCH", str(ctx.exception))
        self.assertIn("ordered 500.0 mg", str(ctx.exception))
        self.assertIn("displays 50.0 mg", str(ctx.exception))

    def test_quality_gate_1_catches_schedule_frequency_deviation(self):
        """
        Quality Gate 1:
        If translation schedules drug 3 times a day (1-1-1) when doctor ordered 2 times (1-0-1),
        back-translation verification strictly catches it and raises VernacularTranslationMismatchError.
        """
        corrupted_schedule_card = PictogramMedicationCard(
            drug_name_english="Metformin",
            drug_name_vernacular="মেটফরমিন (Metformin)",
            dosage_display="৫০০ মিগ্রা (mg)",
            meal_instruction_icon="🍽️",
            meal_instruction_vernacular="খাওয়ার পরে",
            timetable=[
                PictogramTimeSlot("Morning", "🌅", "সকাল", 1),
                PictogramTimeSlot("Afternoon", "☀️", "দুপুর", 1),  # Overdose schedule: 1-1-0-1 instead of 1-0-0-1
                PictogramTimeSlot("Evening", "🌇", "সন্ধ্যা", 0),
                PictogramTimeSlot("Night", "🌙", "রাত", 1),
            ],
            duration_vernacular="৩০ দিনের জন্য",
        )

        with self.assertRaises(VernacularTranslationMismatchError) as ctx:
            self.engine.verify_pharmacological_back_translation(
                original_orders=[self.med_metformin],
                cards=[corrupted_schedule_card],
            )

        self.assertIn("FREQUENCY MISMATCH", str(ctx.exception))
        self.assertIn("Physician ordered schedule (1-0-0-1)", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
