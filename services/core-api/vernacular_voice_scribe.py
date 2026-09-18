# ====================================================================================================
# PROJECT "HOSPITAL" — VERNACULAR CLINICAL VOICE-TO-FHIR SCRIBE INTERFACE
# ====================================================================================================
# Module: services/core-api/vernacular_voice_scribe.py
# Purpose: Translates rural vernacular audio transcripts (Hindi & Bengali) into structured clinical
#          PQRST attributes and serializes them into valid HL7 FHIR R4 Encounter & Observation bundles.
# ====================================================================================================

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set


@dataclass
class ExtractedClinicalObservation:
    concept_name: str
    snomed_id: str
    loinc_code: str
    polarity: str          # "PRESENT", "ABSENT", "UNCERTAIN"
    severity_1_to_10: Optional[int] = None
    duration_hours: Optional[float] = None
    is_red_flag: bool = False
    vernacular_raw_phrase: str = ""


@dataclass
class ScribeIntakeBundle:
    encounter_id: str
    patient_id: str
    language_detected: str       # "HINDI", "BENGALI", "ENGLISH"
    chief_complaint: str
    observations: List[ExtractedClinicalObservation] = field(default_factory=list)
    fhir_bundle_json: Dict[str, Any] = field(default_factory=dict)
    red_flag_alert_triggered: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VernacularVoiceScribeEngine:
    """
    Zero-hallucination semantic parser for Indian vernacular spoken clinical histories.
    """

    # Bengali clinical colloquial dictionary
    BENGALI_LEXICON = {
        "buke chap": ("Retrosternal crushing chest pain", "57054005", "75325-1", True),
        "buke byatha": ("Chest pain", "29857009", "75325-1", True),
        "ghaam": ("Diaphoresis / Cold sweat", "52613005", "75325-1", True),
        "baam haate": ("Pain radiating to left arm", "29857009", "75325-1", True),
        "saas nite koshto": ("Dyspnea / Shortness of breath", "267036007", "75325-1", True),
        "matha ghorano": ("Vertigo / Presyncope", "399153001", "75325-1", False),
        "jwor": ("Fever / Pyrexia", "386661006", "75325-1", False),
        "pet byatha": ("Abdominal pain", "21522001", "75325-1", False),
    }

    # Hindi clinical colloquial dictionary
    HINDI_LEXICON = {
        "seene me dard": ("Chest pain", "29857009", "75325-1", True),
        "seene me dabav": ("Crushing chest pressure", "57054005", "75325-1", True),
        "paseena": ("Diaphoresis / Sweating", "52613005", "75325-1", True),
        "baaye haath me dard": ("Pain radiating to left arm", "29857009", "75325-1", True),
        "saans phoolna": ("Dyspnea / Breathlessness", "267036007", "75325-1", True),
        "chakkar": ("Vertigo / Dizziness", "399153001", "75325-1", False),
        "bukhar": ("Fever / Pyrexia", "386661006", "75325-1", False),
        "pet me dard": ("Abdominal pain", "21522001", "75325-1", False),
    }

    def parse_vernacular_transcript(
        self,
        transcript_text: str,
        patient_id: str,
        language_hint: Optional[str] = None
    ) -> ScribeIntakeBundle:
        clean = transcript_text.lower().strip()
        lang = language_hint.upper() if language_hint else self._detect_language(clean)

        lexicon = self.BENGALI_LEXICON if lang == "BENGALI" else self.HINDI_LEXICON
        observations = []
        has_red_flag = False

        for phrase, (concept, snomed_id, loinc, is_rf) in lexicon.items():
            if phrase in clean:
                # Check for negation in vernacular (e.g. "nei", "nahi")
                negated = bool(re.search(rf"{re.escape(phrase)}\s+(nei|nai|hoche na|nahi hai)", clean))
                polarity = "ABSENT" if negated else "PRESENT"
                if polarity == "PRESENT" and is_rf:
                    has_red_flag = True

                observations.append(ExtractedClinicalObservation(
                    concept_name=concept,
                    snomed_id=snomed_id,
                    loinc_code=loinc,
                    polarity=polarity,
                    is_red_flag=is_rf if polarity == "PRESENT" else False,
                    vernacular_raw_phrase=phrase
                ))

        encounter_id = f"ENC-VOICE-{uuid.uuid4().hex[:8].upper()}"
        fhir_bundle = self._build_fhir_bundle(encounter_id, patient_id, observations)

        return ScribeIntakeBundle(
            encounter_id=encounter_id,
            patient_id=patient_id,
            language_detected=lang,
            chief_complaint=observations[0].concept_name if observations else "Undetermined Symptom",
            observations=observations,
            fhir_bundle_json=fhir_bundle,
            red_flag_alert_triggered=has_red_flag
        )

    def _detect_language(self, text: str) -> str:
        bengali_cues = ["buke", "byatha", "hoche", "saas", "pet", "matha", "nei", "hochhe"]
        hindi_cues = ["seene", "dard", "raha", "saans", "bukhar", "chakkar", "nahi", "hota"]
        b_score = sum(1 for c in bengali_cues if c in text)
        h_score = sum(1 for c in hindi_cues if c in text)
        return "BENGALI" if b_score >= h_score else "HINDI"

    def _build_fhir_bundle(
        self,
        encounter_id: str,
        patient_id: str,
        observations: List[ExtractedClinicalObservation]
    ) -> Dict[str, Any]:
        """Constructs an HL7 FHIR R4 Bundle containing Encounter and Observation entries."""
        now = datetime.now(timezone.utc).isoformat()
        entries = [
            {
                "fullUrl": f"urn:uuid:{encounter_id}",
                "resource": {
                    "resourceType": "Encounter",
                    "id": encounter_id,
                    "status": "in-progress",
                    "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "EMER"},
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "period": {"start": now}
                }
            }
        ]

        for obs in observations:
            obs_id = f"OBS-{uuid.uuid4().hex[:8].upper()}"
            entries.append({
                "fullUrl": f"urn:uuid:{obs_id}",
                "resource": {
                    "resourceType": "Observation",
                    "id": obs_id,
                    "status": "preliminary",
                    "category": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                    "code": "vital-signs" if "52613005" in obs.snomed_id else "exam"
                                }
                            ]
                        }
                    ],
                    "code": {
                        "coding": [
                            {"system": "http://snomed.info/sct", "code": obs.snomed_id, "display": obs.concept_name},
                            {"system": "http://loinc.org", "code": obs.loinc_code}
                        ],
                        "text": obs.vernacular_raw_phrase
                    },
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "encounter": {"reference": f"Encounter/{encounter_id}"},
                    "effectiveDateTime": now,
                    "valueString": obs.polarity
                }
            })

        return {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": now,
            "total": len(entries),
            "entry": entries
        }


vernacular_voice_scribe = VernacularVoiceScribeEngine()
