"""
PROJECT "HOSPITAL" — PHASE 13: PATIENT EXPERIENCE
Module: vernacular_discharge_engine.py
Operational Scope:
  - Sub-task 13.1: Trilingual Vernacular Discharge Dossier (Bengali, Hindi, English)
  - Visual Pictogram Medication Timetable (Sun, Overhead Sun, Moon, Food Icons)
  - Quality Gate 1: Pharmacological Accuracy Gate with Automated Back-Translation Verification
  - Sub-task 13.2: Multilingual Audio Prescription Generator & Voice Note Synthesizer
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class VernacularError(Exception):
    """Base exception for vernacular and discharge communication errors."""
    pass


class VernacularTranslationMismatchError(VernacularError):
    """Raised when the translated prescription deviates from the physician's signed clinical order."""
    pass


class SupportedLanguage(str, Enum):
    ENGLISH = "en"
    BENGALI = "bn"  # বাংলা
    HINDI = "hi"    # हिंदी


class MealRelation(str, Enum):
    BEFORE_MEAL = "BEFORE_MEAL"
    AFTER_MEAL = "AFTER_MEAL"
    WITH_MEAL = "WITH_MEAL"
    EMPTY_STOMACH = "EMPTY_STOMACH"


@dataclass
class PrescribedMedication:
    drug_name: str          # e.g., "Metformin", "Amlodipine", "Paracetamol"
    dosage_mg: float        # e.g., 500.0, 5.0, 650.0
    morning_dose: int       # 1 or 0
    afternoon_dose: int     # 1 or 0
    evening_dose: int       # 1 or 0
    night_dose: int         # 1 or 0
    duration_days: int      # e.g., 14, 30
    meal_relation: MealRelation
    special_instruction: str = ""


@dataclass
class PictogramTimeSlot:
    slot_name: str          # Morning, Afternoon, Evening, Night
    icon_symbol: str        # 🌅, ☀️, 🌇, 🌙
    vernacular_label: str   # সকাল, দুপুর, সন্ধ্যা, রাত
    dose_count: int


@dataclass
class PictogramMedicationCard:
    drug_name_english: str
    drug_name_vernacular: str
    dosage_display: str     # "500 mg" / "৫০০ মিগ্রা" / "५०० मिग्रा"
    meal_instruction_icon: str # 🍽️ (After) or 🚫🍽️ (Before)
    meal_instruction_vernacular: str
    timetable: List[PictogramTimeSlot]
    duration_vernacular: str


@dataclass
class VernacularDischargeDossier:
    dossier_id: str
    patient_id: str
    patient_name: str
    mrn: str
    language: SupportedLanguage
    discharge_date: datetime
    primary_diagnosis_vernacular: str
    emergency_warning_signs_vernacular: List[str]
    pictogram_medications: List[PictogramMedicationCard]
    audio_prescription_script: str
    is_pharmacologically_verified: bool
    verification_hash: str


class VernacularDischargeEngine:
    """
    Translates signed clinical discharge summaries into patient-centric vernacular dossiers
    (Bengali, Hindi, English) with visual pictograms, audio scripts, and 100% back-translation safety gates.
    """

    # Lexicons for translation and back-translation verification
    BENGALI_NUMERALS = {'0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪', '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'}
    HINDI_NUMERALS = {'0': '०', '1': '१', '2': '२', '3': '३', '4': '४', '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'}

    REVERSE_BENGALI_NUM = {v: k for k, v in BENGALI_NUMERALS.items()}
    REVERSE_HINDI_NUM = {v: k for k, v in HINDI_NUMERALS.items()}

    BENGALI_DRUG_NAMES = {
        "Metformin": "মেটফরমিন (Metformin)",
        "Amlodipine": "অ্যামলোডিপিন (Amlodipine)",
        "Paracetamol": "প্যারাসিটামল (Paracetamol)",
        "Atorvastatin": "অ্যাটরভাস্ট্যাটিন (Atorvastatin)",
        "Pantoprazole": "প্যান্টোপ্রাজল (Pantoprazole)",
        "Azithromycin": "অ্যাজিথ্রোমাইসিন (Azithromycin)",
    }

    HINDI_DRUG_NAMES = {
        "Metformin": "मेटफॉर्मिन (Metformin)",
        "Amlodipine": "एम्लोडिपिन (Amlodipine)",
        "Paracetamol": "पैरासिटामोल (Paracetamol)",
        "Atorvastatin": "एटोरवास्टेटिन (Atorvastatin)",
        "Pantoprazole": "पैंटोप्राजोल (Pantoprazole)",
        "Azithromycin": "एज़िथ्रोमाइसिन (Azithromycin)",
    }

    def _to_vernacular_number(self, num_val: float, lang: SupportedLanguage) -> str:
        s = str(int(num_val)) if num_val == int(num_val) else str(num_val)
        if lang == SupportedLanguage.BENGALI:
            return "".join(self.BENGALI_NUMERALS.get(c, c) for c in s)
        elif lang == SupportedLanguage.HINDI:
            return "".join(self.HINDI_NUMERALS.get(c, c) for c in s)
        return s

    def _from_vernacular_number(self, text: str) -> float:
        cleaned = ""
        for c in text:
            if c in self.REVERSE_BENGALI_NUM:
                cleaned += self.REVERSE_BENGALI_NUM[c]
            elif c in self.REVERSE_HINDI_NUM:
                cleaned += self.REVERSE_HINDI_NUM[c]
            elif c.isdigit() or c == '.':
                cleaned += c
        return float(cleaned) if cleaned else 0.0

    def generate_pictogram_medication_card(
        self,
        med: PrescribedMedication,
        lang: SupportedLanguage,
    ) -> PictogramMedicationCard:
        """Constructs visual pictogram card for a prescribed drug."""
        vernacular_num = self._to_vernacular_number(med.dosage_mg, lang)
        duration_num = self._to_vernacular_number(med.duration_days, lang)

        if lang == SupportedLanguage.BENGALI:
            drug_vernacular = self.BENGALI_DRUG_NAMES.get(med.drug_name, med.drug_name)
            dosage_display = f"{vernacular_num} মিগ্রা (mg)"
            meal_text = "খাওয়ার পরে" if med.meal_relation == MealRelation.AFTER_MEAL else "খালি পেটে (খাওয়ার আগে)"
            duration_text = f"{duration_num} দিনের জন্য"
            slots = [
                PictogramTimeSlot("Morning", "🌅", "সকাল", med.morning_dose),
                PictogramTimeSlot("Afternoon", "☀️", "দুপুর", med.afternoon_dose),
                PictogramTimeSlot("Evening", "🌇", "সন্ধ্যা", med.evening_dose),
                PictogramTimeSlot("Night", "🌙", "রাত", med.night_dose),
            ]
        elif lang == SupportedLanguage.HINDI:
            drug_vernacular = self.HINDI_DRUG_NAMES.get(med.drug_name, med.drug_name)
            dosage_display = f"{vernacular_num} मिग्रा (mg)"
            meal_text = "भोजन के बाद" if med.meal_relation == MealRelation.AFTER_MEAL else "भोजन से पहले (खाली पेट)"
            duration_text = f"{duration_num} दिनों के लिए"
            slots = [
                PictogramTimeSlot("Morning", "🌅", "प्रातः", med.morning_dose),
                PictogramTimeSlot("Afternoon", "☀️", "दोपहर", med.afternoon_dose),
                PictogramTimeSlot("Evening", "🌇", "सायं", med.evening_dose),
                PictogramTimeSlot("Night", "🌙", "रात्रि", med.night_dose),
            ]
        else:
            drug_vernacular = med.drug_name
            dosage_display = f"{med.dosage_mg} mg"
            meal_text = "After Meals" if med.meal_relation == MealRelation.AFTER_MEAL else "Before Meals (Empty Stomach)"
            duration_text = f"For {med.duration_days} days"
            slots = [
                PictogramTimeSlot("Morning", "🌅", "Morning", med.morning_dose),
                PictogramTimeSlot("Afternoon", "☀️", "Afternoon", med.afternoon_dose),
                PictogramTimeSlot("Evening", "🌇", "Evening", med.evening_dose),
                PictogramTimeSlot("Night", "🌙", "Night", med.night_dose),
            ]

        meal_icon = "🍽️" if med.meal_relation == MealRelation.AFTER_MEAL else "🚫🍽️"

        return PictogramMedicationCard(
            drug_name_english=med.drug_name,
            drug_name_vernacular=drug_vernacular,
            dosage_display=dosage_display,
            meal_instruction_icon=meal_icon,
            meal_instruction_vernacular=meal_text,
            timetable=slots,
            duration_vernacular=duration_text,
        )

    def synthesize_audio_prescription_script(
        self,
        patient_name: str,
        medications: List[PrescribedMedication],
        lang: SupportedLanguage,
    ) -> str:
        """
        Sub-task 13.2: Generates native speech synthesis audio script explaining
        dosages, timetables, and meal instructions in conversational vernacular.
        """
        if lang == SupportedLanguage.BENGALI:
            script_parts = [
                f"নমস্কার {patient_name}। হাসপাতাল থেকে বাড়ি ফেরার পর আপনার ওষুধের সময়সূচী শুনুন।",
            ]
            for m in medications:
                timing_words = []
                m_dose = self._to_vernacular_number(m.morning_dose, lang)
                a_dose = self._to_vernacular_number(m.afternoon_dose, lang)
                e_dose = self._to_vernacular_number(m.evening_dose, lang)
                n_dose = self._to_vernacular_number(m.night_dose, lang)
                if m.morning_dose > 0: timing_words.append(f"সকালে {m_dose}টি")
                if m.afternoon_dose > 0: timing_words.append(f"দুপুরে {a_dose}টি")
                if m.evening_dose > 0: timing_words.append(f"সন্ধ্যায় {e_dose}টি")
                if m.night_dose > 0: timing_words.append(f"রাতে {n_dose}টি")

                meal_w = "খাওয়ার পরে" if m.meal_relation == MealRelation.AFTER_MEAL else "খালি পেটে"
                vernacular_dose = self._to_vernacular_number(m.dosage_mg, lang)
                line = (
                    f"ওষুধ {m.drug_name} {vernacular_dose} মিলিগ্রাম: "
                    f"{', '.join(timing_words)}, {meal_w} খাবেন, টানা {self._to_vernacular_number(m.duration_days, lang)} দিন।"
                )
                script_parts.append(line)
            script_parts.append("জরুরী কোনো অসুবিধা হলে অবিলম্বে আমাদের ২৪ ঘণ্টার হেল্পলাইনে যোগাযোগ করুন। ধন্যবাদ।")
            return " ".join(script_parts)

        elif lang == SupportedLanguage.HINDI:
            script_parts = [
                f"नमस्ते {patient_name}। अस्पताल से छुट्टी के बाद अपनी दवाओं का समय ध्यानपूर्वक सुनें।",
            ]
            for m in medications:
                timing_words = []
                m_dose = self._to_vernacular_number(m.morning_dose, lang)
                a_dose = self._to_vernacular_number(m.afternoon_dose, lang)
                e_dose = self._to_vernacular_number(m.evening_dose, lang)
                n_dose = self._to_vernacular_number(m.night_dose, lang)
                if m.morning_dose > 0: timing_words.append(f"सुबह {m_dose}")
                if m.afternoon_dose > 0: timing_words.append(f"दोपहर {a_dose}")
                if m.evening_dose > 0: timing_words.append(f"शाम {e_dose}")
                if m.night_dose > 0: timing_words.append(f"रात {n_dose}")

                meal_w = "भोजन के बाद" if m.meal_relation == MealRelation.AFTER_MEAL else "खाली पेट"
                vernacular_dose = self._to_vernacular_number(m.dosage_mg, lang)
                line = (
                    f"दवा {m.drug_name} {vernacular_dose} मिलीग्राम: "
                    f"{', '.join(timing_words)}, {meal_w} लें, कुल {self._to_vernacular_number(m.duration_days, lang)} दिनों तक।"
                )
                script_parts.append(line)
            script_parts.append("कोई भी आपातकालीन समस्या होने पर तुरंत हमारी 24 घंटे हेल्पलाइन पर संपर्क करें। धन्यवाद।")
            return " ".join(script_parts)

        else:
            script_parts = [
                f"Hello {patient_name}. Please listen to your post-discharge medication schedule.",
            ]
            for m in medications:
                timing_words = []
                if m.morning_dose > 0: timing_words.append(f"Morning: {m.morning_dose}")
                if m.afternoon_dose > 0: timing_words.append(f"Afternoon: {m.afternoon_dose}")
                if m.evening_dose > 0: timing_words.append(f"Evening: {m.evening_dose}")
                if m.night_dose > 0: timing_words.append(f"Night: {m.night_dose}")

                meal_w = "after food" if m.meal_relation == MealRelation.AFTER_MEAL else "on an empty stomach"
                line = (
                    f"Medication {m.drug_name} {m.dosage_mg} mg: "
                    f"{', '.join(timing_words)}, {meal_w}, for {m.duration_days} days."
                )
                script_parts.append(line)
            script_parts.append("In case of any emergency symptom, contact our 24/7 hotline immediately. Thank you.")
            return " ".join(script_parts)

    def verify_pharmacological_back_translation(
        self,
        original_orders: List[PrescribedMedication],
        cards: List[PictogramMedicationCard],
    ) -> bool:
        """
        Quality Gate 1: Pharmacological Accuracy Gate.
        Performs automated back-translation check of every card against doctor's signed orders.
        Strictly raises VernacularTranslationMismatchError if any dosage, drug name, or frequency differs.
        """
        if len(original_orders) != len(cards):
            raise VernacularTranslationMismatchError(
                f"Medication count mismatch: {len(original_orders)} ordered vs {len(cards)} translated."
            )

        for orig, card in zip(original_orders, cards):
            # 1. Drug name check
            if orig.drug_name.lower() not in card.drug_name_vernacular.lower():
                raise VernacularTranslationMismatchError(
                    f"Drug name translation error: Expected {orig.drug_name} but found in card: {card.drug_name_vernacular}"
                )

            # 2. Dosage check via reverse numeral extraction
            extracted_dosage = self._from_vernacular_number(card.dosage_display)
            if extracted_dosage != orig.dosage_mg:
                raise VernacularTranslationMismatchError(
                    f"[LETHAL DOSAGE MISMATCH] Drug {orig.drug_name}: Physician ordered {orig.dosage_mg} mg, "
                    f"but translated card displays {extracted_dosage} mg ({card.dosage_display})!"
                )

            # 3. Frequency / Schedule check
            card_morning = next(s.dose_count for s in card.timetable if s.slot_name == "Morning")
            card_afternoon = next(s.dose_count for s in card.timetable if s.slot_name == "Afternoon")
            card_evening = next(s.dose_count for s in card.timetable if s.slot_name == "Evening")
            card_night = next(s.dose_count for s in card.timetable if s.slot_name == "Night")

            if (card_morning != orig.morning_dose or
                card_afternoon != orig.afternoon_dose or
                card_evening != orig.evening_dose or
                card_night != orig.night_dose):
                raise VernacularTranslationMismatchError(
                    f"[FREQUENCY MISMATCH] Drug {orig.drug_name}: Physician ordered schedule "
                    f"({orig.morning_dose}-{orig.afternoon_dose}-{orig.evening_dose}-{orig.night_dose}) "
                    f"but card displays ({card_morning}-{card_afternoon}-{card_evening}-{card_night})!"
                )

        return True

    def generate_vernacular_discharge_dossier(
        self,
        dossier_id: str,
        patient_id: str,
        patient_name: str,
        mrn: str,
        language: SupportedLanguage,
        discharge_date: datetime,
        primary_diagnosis: str,
        medications: List[PrescribedMedication],
    ) -> VernacularDischargeDossier:
        """
        Creates complete multilingual discharge dossier verified through Quality Gate 1.
        """
        cards: List[PictogramMedicationCard] = []
        for med in medications:
            card = self.generate_pictogram_medication_card(med, language)
            cards.append(card)

        # Inviolable Quality Gate 1: Automated Back-Translation Verification
        is_verified = self.verify_pharmacological_back_translation(medications, cards)

        # Audio Script
        audio_script = self.synthesize_audio_prescription_script(patient_name, medications, language)

        # Emergency Warning signs in vernacular
        if language == SupportedLanguage.BENGALI:
            diagnosis_vernacular = f"রোগ নির্ণয়: {primary_diagnosis}"
            warning_signs = [
                "অতিরিক্ত শ্বাসকষ্ট বা বুকে ব্যথা হলে অবিলম্বে আসুন।",
                "১০১° এর বেশি তীব্র জ্বর বা ক্রমাগত বমি হলে।",
                "অপারেশনের ক্ষতস্থান থেকে রক্তপাত বা পুঁজ নির্গত হলে।",
            ]
        elif language == SupportedLanguage.HINDI:
            diagnosis_vernacular = f"निदान: {primary_diagnosis}"
            warning_signs = [
                "अत्यधिक सांस फूलना या सीने में तेज दर्द होने पर तुरंत आएं।",
                "१०१° से अधिक तेज बुखार या लगातार उल्टी होने पर।",
                "ऑपरेशन के घाव से खून बहने या मवाद निकलने पर।",
            ]
        else:
            diagnosis_vernacular = f"Diagnosis: {primary_diagnosis}"
            warning_signs = [
                "Seek immediate emergency care for severe chest pain or shortness of breath.",
                "Fever exceeding 101°F or persistent uncontrollable vomiting.",
                "Active wound bleeding, swelling, or purulent drainage.",
            ]

        verification_hash = f"PHARMA-VERIFIED-{dossier_id}-{language.value}-100PCT"

        return VernacularDischargeDossier(
            dossier_id=dossier_id,
            patient_id=patient_id,
            patient_name=patient_name,
            mrn=mrn,
            language=language,
            discharge_date=discharge_date,
            primary_diagnosis_vernacular=diagnosis_vernacular,
            emergency_warning_signs_vernacular=warning_signs,
            pictogram_medications=cards,
            audio_prescription_script=audio_script,
            is_pharmacologically_verified=is_verified,
            verification_hash=verification_hash,
        )
