#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18.1: STRUCTURED CLINICAL HISTORY-TAKING ENGINE
====================================================================================================
Module: services/core-api/structured_history_engine.py
Purpose: Algorithmic branching history-taking engine for rural community health workers (CHWs),
         paramedics, and triage nurses. Elicits structured symptom attributes (PQRST, onset,
         radiation, aggravating/relieving factors), pertinent positives and negatives, and acute
         red flags across 7 primary emergency presentation archetypes.
Deterministic Invariant: 100% deterministic decision-tree branching; zero ungrounded LLM hallucination.
====================================================================================================
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone


class ChiefComplaintCategory(str, Enum):
    CHEST_PAIN = "CHEST_PAIN"
    ABDOMINAL_PAIN = "ABDOMINAL_PAIN"
    BREATHLESSNESS = "BREATHLESSNESS"
    ALTERED_SENSORIUM_OR_WEAKNESS = "ALTERED_SENSORIUM_OR_WEAKNESS"
    TRAUMA_OR_FALL = "TRAUMA_OR_FALL"
    FEVER_OR_INFECTION = "FEVER_OR_INFECTION"
    OBSTETRIC_EMERGENCY = "OBSTETRIC_EMERGENCY"
    TOXIC_OR_SNAKEBITE = "TOXIC_OR_SNAKEBITE"


class FindingPolarity(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class StructuredFinding:
    concept_name: str
    snomed_id: str
    polarity: FindingPolarity
    severity_1_to_10: Optional[int] = None
    duration_hours: Optional[float] = None
    is_red_flag: bool = False
    clinical_note: str = ""


@dataclass
class HistoryIntakeSession:
    session_id: str
    patient_id: str
    chief_complaint: ChiefComplaintCategory
    patient_age: int
    is_female: bool
    is_pregnant: bool = False
    findings: List[StructuredFinding] = field(default_factory=list)
    active_red_flags: List[str] = field(default_factory=list)
    recommended_immediate_actions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StructuredHistoryEngine:
    """
    Branching clinical questionnaire engine that maps non-physician caregiver observations
    into rigorous, structured, SNOMED-annotated clinical findings with red-flag detection.
    """

    def __init__(self):
        pass

    def initiate_session(
        self,
        session_id: str,
        patient_id: str,
        chief_complaint: ChiefComplaintCategory,
        patient_age: int,
        is_female: bool,
        is_pregnant: bool = False
    ) -> HistoryIntakeSession:
        return HistoryIntakeSession(
            session_id=session_id,
            patient_id=patient_id,
            chief_complaint=chief_complaint,
            patient_age=patient_age,
            is_female=is_female,
            is_pregnant=is_pregnant
        )

    def process_responses(
        self,
        session: HistoryIntakeSession,
        answers: Dict[str, Any]
    ) -> HistoryIntakeSession:
        """
        Ingests answered branch questionnaire, extracts structured findings,
        detects immediate life-threatening red flags, and prescribes triage actions.
        """
        category = session.chief_complaint

        if category == ChiefComplaintCategory.CHEST_PAIN:
            self._process_chest_pain(session, answers)
        elif category == ChiefComplaintCategory.ABDOMINAL_PAIN:
            self._process_abdominal_pain(session, answers)
        elif category == ChiefComplaintCategory.BREATHLESSNESS:
            self._process_breathlessness(session, answers)
        elif category == ChiefComplaintCategory.ALTERED_SENSORIUM_OR_WEAKNESS:
            self._process_neurological(session, answers)
        elif category == ChiefComplaintCategory.TRAUMA_OR_FALL:
            self._process_trauma(session, answers)
        elif category == ChiefComplaintCategory.FEVER_OR_INFECTION:
            self._process_fever_sepsis(session, answers)
        elif category == ChiefComplaintCategory.OBSTETRIC_EMERGENCY:
            self._process_obstetric(session, answers)
        elif category == ChiefComplaintCategory.TOXIC_OR_SNAKEBITE:
            self._process_toxicology(session, answers)

        return session

    # ----------------------------------------------------------------------------------------------
    # Archetype Processors
    # ----------------------------------------------------------------------------------------------

    def _process_chest_pain(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        severity = ans.get("pain_severity_1_to_10", 5)
        duration_h = ans.get("duration_hours", 1.0)
        radiates_left_arm = ans.get("radiates_to_left_arm_or_jaw", False)
        diaphoresis = ans.get("has_cold_sweating", False)
        vomiting = ans.get("has_vomiting", False)
        breathlessness = ans.get("has_shortness_of_breath", False)
        pleuritic = ans.get("worse_with_deep_breath", False)

        session.findings.append(StructuredFinding(
            concept_name="Chest pain",
            snomed_id="29857009",
            polarity=FindingPolarity.PRESENT,
            severity_1_to_10=severity,
            duration_hours=duration_h,
            is_red_flag=(severity >= 7 or duration_h > 0.5)
        ))

        if radiates_left_arm:
            session.findings.append(StructuredFinding(
                concept_name="Radiation to arm/jaw",
                snomed_id="29857009",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=True,
                clinical_note="Classic ischemic radiation"
            ))

        session.findings.append(StructuredFinding(
            concept_name="Diaphoresis",
            snomed_id="247441003",
            polarity=FindingPolarity.PRESENT if diaphoresis else FindingPolarity.ABSENT,
            is_red_flag=diaphoresis
        ))

        session.findings.append(StructuredFinding(
            concept_name="Dyspnea",
            snomed_id="267036007",
            polarity=FindingPolarity.PRESENT if breathlessness else FindingPolarity.ABSENT
        ))

        session.findings.append(StructuredFinding(
            concept_name="Vomiting",
            snomed_id="422587007",
            polarity=FindingPolarity.PRESENT if vomiting else FindingPolarity.ABSENT
        ))

        # Red flags
        if diaphoresis and (radiates_left_arm or severity >= 7):
            session.active_red_flags.append("HIGH_PROBABILITY_ACUTE_CORONARY_SYNDROME")
            session.recommended_immediate_actions.extend([
                "Administer chewable Aspirin 300mg immediately (if no documented active bleeding or true allergy)",
                "Keep patient resting in semi-upright position; avoid physical exertion",
                "Prepare urgent 12-lead ECG and rush transfer to tertiary PCI-capable hospital"
            ])

        if pleuritic and not radiates_left_arm:
            session.findings.append(StructuredFinding(
                concept_name="Pleuritic chest pain",
                snomed_id="29857009",
                polarity=FindingPolarity.PRESENT,
                clinical_note="Worse with breathing; suspect PE, pleurisy, or pericarditis"
            ))

    def _process_abdominal_pain(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        severity = ans.get("pain_severity_1_to_10", 5)
        duration_h = ans.get("duration_hours", 6.0)
        rigidity = ans.get("is_abdomen_rigid_or_board_like", False)
        distension = ans.get("has_abdominal_distension", False)
        fever = ans.get("has_fever", False)
        vomiting = ans.get("has_persistent_vomiting", False)
        no_stool_flatus = ans.get("no_stool_or_flatus_in_24h", False)

        session.findings.append(StructuredFinding(
            concept_name="Abdominal pain",
            snomed_id="21522000",
            polarity=FindingPolarity.PRESENT,
            severity_1_to_10=severity,
            duration_hours=duration_h
        ))

        session.findings.append(StructuredFinding(
            concept_name="Abdominal rigidity",
            snomed_id="163428003",
            polarity=FindingPolarity.PRESENT if rigidity else FindingPolarity.ABSENT,
            is_red_flag=rigidity
        ))

        if rigidity or (distension and no_stool_flatus):
            session.active_red_flags.append("SURGICAL_ACUTE_ABDOMEN_PERITONITIS")
            session.recommended_immediate_actions.extend([
                "STRICT NPO (Nothing by Mouth): Do NOT give food, water, or oral painkillers",
                "Insert IV cannula and begin Ringer's Lactate / Normal Saline maintenance if trained personnel available",
                "RUSH transfer to surgical center for acute exploratory laparotomy / laparoscopy evaluation"
            ])

        if session.is_female and session.patient_age >= 14 and session.patient_age <= 50 and ans.get("missed_period", False):
            session.active_red_flags.append("SUSPECT_RUPTURED_ECTOPIC_PREGNANCY")
            session.recommended_immediate_actions.append(
                "Immediate urine pregnancy test (UPT) and urgent ultrasound for ectopic pregnancy rule-out"
            )

    def _process_breathlessness(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        onset = ans.get("onset_sudden", False)
        stridor = ans.get("has_stridor_or_throat_swelling", False)
        wheezing = ans.get("has_wheezing_or_asthma_history", False)
        spo2 = ans.get("measured_spo2", 98)
        cyanosis = ans.get("has_blue_lips_or_cyanosis", False)

        session.findings.append(StructuredFinding(
            concept_name="Dyspnea",
            snomed_id="267036007",
            polarity=FindingPolarity.PRESENT,
            is_red_flag=(spo2 < 90 or cyanosis or stridor)
        ))

        if stridor or ans.get("throat_swelling_after_sting_or_food", False):
            session.active_red_flags.append("ACUTE_AIRWAY_OBSTRUCTION_ANAPHYLAXIS")
            session.recommended_immediate_actions.extend([
                "IMMEDIATE INTRAMUSCULAR ADRENALINE (1:1000) 0.5mg IM mid-anterolateral thigh",
                "High-flow oxygen and upright sitting posture; prepare for emergency cricothyroidotomy"
            ])
        elif spo2 < 90 or cyanosis:
            session.active_red_flags.append("HYPOXIC_RESPIRATORY_FAILURE")
            session.recommended_immediate_actions.extend([
                "Administer high-flow oxygen via non-rebreather mask (10-15 L/min)",
                "Keep patient sitting upright 90 degrees",
                "If history of asthma/COPD, deliver inhaled Salbutamol nebulization"
            ])

    def _process_neurological(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        facial_droop = ans.get("facial_droop", False)
        arm_drift = ans.get("one_arm_weakness", False)
        speech_slurred = ans.get("speech_difficulty", False)
        onset_time_known = ans.get("onset_within_4_5_hours", False)
        gcs_motor_abnormal = ans.get("unresponsive_or_coma", False)
        neck_stiffness = ans.get("neck_stiffness_and_fever", False)

        if facial_droop or arm_drift or speech_slurred:
            session.findings.append(StructuredFinding(
                concept_name="Hemiparesis / Limb weakness",
                snomed_id="68569003",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=True
            ))
            session.active_red_flags.append("ACUTE_ISCHEMIC_STROKE_FAST_POSITIVE")
            session.recommended_immediate_actions.extend([
                "DOCUMENT EXACT TIME LAST SEEN NORMAL (Window for IV thrombolysis is < 4.5 hours)",
                "Keep patient in lateral recovery position; STRICT NPO (high aspiration risk)",
                "DO NOT lower blood pressure precipitously with sublingual or oral antihypertensives",
                "Urgent direct transport to CT-capable stroke center"
            ])

        if neck_stiffness:
            session.active_red_flags.append("ACUTE_MENINGITIS_MENINGISM")
            session.recommended_immediate_actions.extend([
                "Suspect bacterial meningitis: Administer empiric Ceftriaxone 2g IV/IM STAT",
                "Check blood glucose immediately to rule out acute hypoglycemia"
            ])

    def _process_trauma(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        deformity = ans.get("visible_bone_deformity", False)
        active_hemorrhage = ans.get("spurting_or_heavy_bleeding", False)
        head_injury = ans.get("struck_head_with_loss_of_consciousness", False)
        elderly_hip_fall = (session.patient_age >= 65 and ans.get("fall_with_inability_to_bear_weight", False))

        if deformity or elderly_hip_fall:
            session.findings.append(StructuredFinding(
                concept_name="Bone fracture / Limb deformity",
                snomed_id="125605004",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=True,
                clinical_note="High suspicion of femur neck or major bone fracture"
            ))

        if active_hemorrhage:
            session.active_red_flags.append("EXSANGUINATING_EXTERNAL_HEMORRHAGE")
            session.recommended_immediate_actions.extend([
                "Apply FIRM DIRECT PRESSURE over bleeding wound using sterile gauze or clean cloth",
                "If life-threatening limb arterial bleed uncontrolled by direct pressure, apply arterial tourniquet 5cm above wound and record timestamp"
            ])

        if elderly_hip_fall:
            session.active_red_flags.append("GERIATRIC_HIP_FRACTURE_RISK")
            session.recommended_immediate_actions.extend([
                "Immobilize affected lower limb with padded splint or gently bandaged to opposite uninjured leg",
                "Check distal pulses (dorsalis pedis) and skin warmth to ensure blood circulation",
                "Administer Paracetamol for pain. AVOID NSAIDs (Ibuprofen, Diclofenac) due to high AKI and bleeding risk in elderly",
                "Keep patient warm and well-hydrated during transit"
            ])

    def _process_fever_sepsis(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        fever_duration_days = ans.get("fever_duration_days", 2)
        sbp = ans.get("systolic_bp", 120)
        rr = ans.get("respiratory_rate", 18)
        altered_sensorium = ans.get("is_confused_or_lethargic", False)

        qsofa = 0
        if sbp <= 100:
            qsofa += 1
        if rr >= 22:
            qsofa += 1
        if altered_sensorium:
            qsofa += 1

        session.findings.append(StructuredFinding(
            concept_name="Fever",
            snomed_id="386661006",
            polarity=FindingPolarity.PRESENT,
            duration_hours=fever_duration_days * 24.0
        ))

        if qsofa >= 2:
            session.active_red_flags.append("qSOFA_POSITIVE_SEPTIC_SHOCK_RISK")
            session.recommended_immediate_actions.extend([
                "qSOFA >= 2: High in-hospital mortality risk from severe sepsis",
                "Initiate rapid IV fluid resuscitation (Normal Saline or Ringer's Lactate 30 mL/kg)",
                "Administer broad-spectrum empiric antibiotic (Ceftriaxone 2g IV/IM) within 1 hour",
                "Expedite urgent emergency admission to ICU-capable center"
            ])

    def _process_obstetric(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        heavy_vaginal_bleeding = ans.get("heavy_vaginal_bleeding", False)
        severe_headache_blurry_vision = ans.get("headache_with_high_bp_or_blurry_vision", False)
        seizures = ans.get("seizures_during_pregnancy", False)
        cord_prolapse = ans.get("umbilical_cord_protruding", False)

        if heavy_vaginal_bleeding:
            session.active_red_flags.append("OBSTETRIC_HEMORRHAGE_PPH_OR_APH")
            session.recommended_immediate_actions.extend([
                "Immediate left-lateral tilt position to relieve inferior vena cava compression",
                "Insert two large-bore IV lines (16G or 18G) and initiate crystalloid infusion",
                "If postpartum: Perform vigorous bimanual uterine massage and administer Misoprostol 800mcg sublingually",
                "STAT emergency transfer to comprehensive emergency obstetric care (CEmONC) facility"
            ])

        if seizures or severe_headache_blurry_vision:
            session.active_red_flags.append("SEVERE_PREECLAMPSIA_OR_ECLAMPSIA")
            session.recommended_immediate_actions.extend([
                "Administer Magnesium Sulfate loading dose (4g IV over 10-15 min + 10g IM, 5g in each buttock)",
                "Protect airway, place in left lateral position, pad bed rails to prevent trauma",
                "Avoid sudden loud noises or bright lights which trigger convulsions"
            ])

    def _process_toxicology(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        snakebite = ans.get("snakebite_confirmed_or_suspected", False)
        organophosphate = ans.get("pesticide_or_chemical_exposure", False)
        fang_marks = ans.get("fang_marks_visible", False)
        ptosis_or_difficulty_swallowing = ans.get("drooping_eyelids_or_difficulty_breathing", False)
        frothing_salivation = ans.get("excessive_salivation_pinpoint_pupils", False)

        if snakebite or fang_marks:
            session.findings.append(StructuredFinding(
                concept_name="Snakebite wound",
                snomed_id="283680004",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=True
            ))
            session.active_red_flags.append("SNAKEBITE_ENVENOMATION_RISK")
            session.recommended_immediate_actions.extend([
                "STRICT IMMOBILIZATION: Splint the bitten limb like a broken bone; keep at heart level",
                "DO NOT APPLY ARTERIAL TOURNIQUETS, DO NOT CUT, DO NOT SUCK WOUND, DO NOT APPLY ICE",
                "Perform 20-minute Whole Blood Clotting Test (20WBCT) in clean dry glass tube",
                "Prepare for Polyvalent Anti-Snake Venom (ASV) infusion if systemic envenomation signs occur (neurotoxicity, bleeding, coagulopathy)"
            ])
            if ptosis_or_difficulty_swallowing:
                session.active_red_flags.append("ELAPID_NEUROTOXIC_RESPIRATORY_FAILURE")
                session.recommended_immediate_actions.append(
                    "Neurotoxic envenomation: Support ventilation with bag-valve-mask; Neostigmine with Atropine trial if indicated"
                )

        if organophosphate or frothing_salivation:
            session.active_red_flags.append("ORGANOPHOSPHATE_CHOLINERGIC_CRISIS")
            session.recommended_immediate_actions.extend([
                "Decontaminate: Remove all poisoned clothing and wash skin thoroughly with soap and water",
                "Administer ATROPINE 2mg IV bolus every 5 minutes until atropinization achieved (lungs clear, HR > 80, pupils dilated)",
                "Secure airway; excessive bronchial secretions are the leading cause of death"
            ])
