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
    DERMATOLOGIC_PIGMENTARY_OR_RASH = "DERMATOLOGIC_PIGMENTARY_OR_RASH"


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
    current_turn: int = 0
    planned_question_ids: List[str] = field(default_factory=list)
    pending_question: Optional[Dict[str, Any]] = None
    unanswered_question_ids: List[str] = field(default_factory=list)
    intake_status: str = "IN_PROGRESS"
    partial_differential: List[Dict[str, Any]] = field(default_factory=list)
    unexcluded_must_not_miss: List[str] = field(default_factory=list)


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
        elif category == ChiefComplaintCategory.DERMATOLOGIC_PIGMENTARY_OR_RASH:
            self._process_dermatologic_pigmentary(session, answers)

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

        # Check for atypical ACS presentation when chest pain is minimal/absent in high-risk patients
        is_high_risk_acs = session.patient_age >= 60 or ans.get("has_diabetes", False) or ans.get("is_diabetic", False)
        has_epigastric_cp = ans.get("epigastric_burning", False) or ans.get("epigastric_pain", False)
        if is_high_risk_acs and has_epigastric_cp and (diaphoresis or breathlessness or vomiting):
            if "ATYPICAL_ACUTE_CORONARY_SYNDROME_SILENT_MI" not in session.active_red_flags:
                session.active_red_flags.append("ATYPICAL_ACUTE_CORONARY_SYNDROME_SILENT_MI")
                session.recommended_immediate_actions.extend([
                    "URGENT 12-LEAD ECG WITHIN 10 MINUTES: Diabetic/geriatric atypical ACS presentation (epigastric discomfort with autonomic symptoms).",
                    "Administer chewable Aspirin 300mg immediately (if no active GI bleeding or documented allergy)."
                ])

    def _process_abdominal_pain(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        severity = ans.get("pain_severity_1_to_10", 5)
        duration_h = ans.get("duration_hours", 6.0)
        rigidity = ans.get("is_abdomen_rigid_or_board_like", False)
        distension = ans.get("has_abdominal_distension", False)
        fever = ans.get("has_fever", False)
        vomiting = ans.get("has_persistent_vomiting", False) or ans.get("has_vomiting", False)
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

        # Multi-assertion finding graph: Detect atypical ACS in diabetic or geriatric patients
        is_high_risk = session.patient_age >= 60 or ans.get("has_diabetes", False) or ans.get("is_diabetic", False)
        has_epigastric = (
            ans.get("epigastric_burning", False) or
            ans.get("epigastric_discomfort", False) or
            ans.get("epigastric_pain", False) or
            ans.get("pain_location") in ("EPIGASTRIC", "UPPER_ABDOMEN") or
            ans.get("is_epigastric", False)
        )
        has_autonomic = (
            ans.get("has_cold_sweating", False) or
            ans.get("has_vomiting", False) or
            ans.get("has_shortness_of_breath", False) or
            ans.get("has_diaphoresis", False)
        )

        if is_high_risk and has_epigastric and has_autonomic:
            session.findings.append(StructuredFinding(
                concept_name="Epigastric burning/discomfort",
                snomed_id="249490001",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=True,
                clinical_note="Atypical ACS presentation in high-risk demographic (geriatric/diabetic)"
            ))
            session.findings.append(StructuredFinding(
                concept_name="Chest pain",
                snomed_id="29857009",
                polarity=FindingPolarity.ABSENT,
                clinical_note="Pertinent negative: absence of chest pain due to diabetic neuropathy or atypical ACS presentation"
            ))
            if "ATYPICAL_ACUTE_CORONARY_SYNDROME_SILENT_MI" not in session.active_red_flags:
                session.active_red_flags.append("ATYPICAL_ACUTE_CORONARY_SYNDROME_SILENT_MI")
                session.recommended_immediate_actions.extend([
                    "URGENT 12-LEAD ECG WITHIN 10 MINUTES: Diabetic/geriatric patient with epigastric discomfort and autonomic symptoms must be evaluated for inferior wall / atypical myocardial infarction.",
                    "Administer chewable Aspirin 300mg immediately (if no active GI bleeding or documented true aspirin allergy).",
                    "Rule out inferior wall MI / acute coronary syndrome before treating as simple gastrointestinal dyspepsia."
                ])

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

    def _process_dermatologic_pigmentary(self, session: HistoryIntakeSession, ans: Dict[str, Any]):
        palmar_creases = ans.get("palmar_crease_darkening", False)
        buccal_mucosa = ans.get("buccal_mucosa_darkening", False)
        orthostatic = ans.get("orthostatic_dizziness", False)
        paresthesia = ans.get("peripheral_tingling_numbness", False)
        tube_well = ans.get("tube_well_drinking_water", False)
        weight_loss = ans.get("unexplained_weight_loss_fatigue", False)
        hair_dye = ans.get("chemical_hair_dye_contact", False)

        if palmar_creases:
            session.findings.append(StructuredFinding(
                concept_name="Palmar crease hyperpigmentation",
                snomed_id="247441003",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=False,
                clinical_note="Hyperpigmentation concentrated in palmar and interphalangeal flexion creases"
            ))

        if buccal_mucosa:
            session.findings.append(StructuredFinding(
                concept_name="Oral mucosal hyperpigmentation",
                snomed_id="247443000",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=True,
                clinical_note="Oral hyperpigmentation indicates elevated ACTH/POMC or severe cobalamin deficiency"
            ))

        if orthostatic:
            session.findings.append(StructuredFinding(
                concept_name="Postural orthostatic dizziness",
                snomed_id="28651003",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=True,
                clinical_note="Orthostatic instability suggests mineralocorticoid deficiency / hypovolemia"
            ))

        if paresthesia:
            session.findings.append(StructuredFinding(
                concept_name="Paresthesia of extremities",
                snomed_id="91019004",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=False,
                clinical_note="Distal symmetrical pins-and-needles sensation"
            ))

        if tube_well:
            session.findings.append(StructuredFinding(
                concept_name="Untreated groundwater exposure",
                snomed_id="425400000",
                polarity=FindingPolarity.PRESENT,
                is_red_flag=False,
                clinical_note="Chronic tube-well groundwater consumption in endemic arsenic belt"
            ))

        # Red Flag and Action Logic
        if palmar_creases and (orthostatic or buccal_mucosa or weight_loss):
            if "SUSPECTED_ADDISONS_ADRENAL_INSUFFICIENCY_CRISIS_RISK" not in session.active_red_flags:
                session.active_red_flags.append("SUSPECTED_ADDISONS_ADRENAL_INSUFFICIENCY_CRISIS_RISK")
            session.recommended_immediate_actions.extend([
                "STAT Serum Electrolytes (Sodium, Potassium, Chloride): Evaluate for life-threatening hyponatremia and hyperkalemia",
                "8:00 AM Fasting Serum Cortisol and Plasma ACTH before starting exogenous steroids",
                "Rule out Adrenal Tuberculosis (Chest X-ray, Mantoux/IGRA, Contrast CT Adrenals)",
                "If systolic BP < 90 mmHg or intractable vomiting: Initiate emergency Normal Saline IV bolus and hydrocortisone 100mg IV"
            ])

        if palmar_creases and paresthesia:
            if "SUSPECTED_VITAMIN_B12_DEFICIENCY_NEUROPATHY" not in session.active_red_flags:
                session.active_red_flags.append("SUSPECTED_VITAMIN_B12_DEFICIENCY_NEUROPATHY")
            session.recommended_immediate_actions.extend([
                "Order Serum Vitamin B12, Serum Folate, and Complete Blood Count with Peripheral Smear (MCV)",
                "NEVER administer Folic Acid alone without verifying Vitamin B12 (risk of precipitating Subacute Combined Degeneration)"
            ])

        if palmar_creases and tube_well:
            if "SUSPECTED_CHRONIC_ARSENICOSIS_MELANOSIS" not in session.active_red_flags:
                session.active_red_flags.append("SUSPECTED_CHRONIC_ARSENICOSIS_MELANOSIS")
            session.recommended_immediate_actions.extend([
                "Test primary drinking water source for Arsenic (> 10 mcg/L BIS limit)",
                "Conduct whole-body cutaneous exam for raindrop pigmentation on trunk and punctate palmar/plantar keratosis",
                "Provide immediate arsenic-safe drinking water alternative"
            ])

        if hair_dye and not (buccal_mucosa or orthostatic or paresthesia or tube_well):
            session.recommended_immediate_actions.append(
                "Likely exogenous staining (PPD / contact): Discontinue chemical contact; skin will gradually exfoliate over 3-6 weeks"
            )

    # ----------------------------------------------------------------------------------------------
    # Sequential Interactive Elicitation & Partial-Intake Fallback
    # ----------------------------------------------------------------------------------------------

    QUESTION_CATALOG: Dict[str, Dict[str, Any]] = {
        # Cutaneous & Pigmentary Questions
        "Q_PALMAR_CREASES": {
            "question_id": "Q_PALMAR_CREASES",
            "attribute_key": "palmar_crease_darkening",
            "question_text": "Are the skin creases on the palms of your hands noticeably darker than surrounding skin?",
            "clinical_purpose": "Identifies localized palmar crease hyperpigmentation (classic marker of ACTH/POMC excess or cobalamin deficiency)",
            "options": ["YES", "NO", "UNSURE"]
        },
        "Q_BUCCAL_MUCOSA": {
            "question_id": "Q_BUCCAL_MUCOSA",
            "attribute_key": "buccal_mucosa_darkening",
            "question_text": "Look inside your mouth with a light. Are there dark, brownish or bluish-black patches inside your cheeks, gums, or tongue?",
            "clinical_purpose": "Differentiates systemic mucosal hyperpigmentation (Addison's / ACTH excess) from isolated contact skin staining",
            "options": ["YES", "NO", "UNSURE"]
        },
        "Q_ORTHOSTATIC_DIZZINESS": {
            "question_id": "Q_ORTHOSTATIC_DIZZINESS",
            "attribute_key": "orthostatic_dizziness",
            "question_text": "Do you feel dizzy, lightheaded, or faint when standing up quickly, or crave salt?",
            "clinical_purpose": "Screens for orthostatic hypotension and impending Addisonian crisis / mineralocorticoid deficiency",
            "options": ["YES", "NO", "UNSURE"]
        },
        "Q_PERIPHERAL_PARESTHESIA": {
            "question_id": "Q_PERIPHERAL_PARESTHESIA",
            "attribute_key": "peripheral_tingling_numbness",
            "question_text": "Do you experience tingling, pins-and-needles, or burning numbness in your feet, toes, or hands?",
            "clinical_purpose": "Screens for Vitamin B12 deficiency peripheral neuropathy / Subacute Combined Degeneration",
            "options": ["YES", "NO", "UNSURE"]
        },
        "Q_TUBE_WELL_WATER": {
            "question_id": "Q_TUBE_WELL_WATER",
            "attribute_key": "tube_well_drinking_water",
            "question_text": "Is your primary daily drinking water from an untreated deep or shallow tube-well in an alluvial rural area?",
            "clinical_purpose": "Evaluates environmental exposure risk to chronic groundwater Arsenic toxicity (Arsenicosis)",
            "options": ["YES", "NO", "UNSURE"]
        },
        # Chest Pain Questions
        "Q_CHEST_RADIATION": {
            "question_id": "Q_CHEST_RADIATION",
            "attribute_key": "radiates_to_left_arm_or_jaw",
            "question_text": "Does your chest discomfort radiate to your left arm, shoulder, jaw, neck, or back?",
            "clinical_purpose": "Evaluates ischemic cardiac pain radiation",
            "options": ["YES", "NO", "UNSURE"]
        },
        "Q_CHEST_DIAPHORESIS": {
            "question_id": "Q_CHEST_DIAPHORESIS",
            "attribute_key": "has_cold_sweating",
            "question_text": "Are you experiencing profuse cold sweating (diaphoresis) or unexplained clamminess?",
            "clinical_purpose": "Autonomic sign of acute myocardial infarction / cardiogenic shock",
            "options": ["YES", "NO", "UNSURE"]
        },
        "Q_EPIGASTRIC_DISTRESS": {
            "question_id": "Q_EPIGASTRIC_DISTRESS",
            "attribute_key": "epigastric_burning",
            "question_text": "Is the discomfort primarily in the upper middle stomach (epigastrium) like severe indigestion?",
            "clinical_purpose": "Screens for atypical silent acute coronary syndrome in diabetics/elderly",
            "options": ["YES", "NO", "UNSURE"]
        }
    }

    CATEGORY_QUESTION_FLOW: Dict[ChiefComplaintCategory, List[str]] = {
        ChiefComplaintCategory.DERMATOLOGIC_PIGMENTARY_OR_RASH: [
            "Q_PALMAR_CREASES",
            "Q_BUCCAL_MUCOSA",
            "Q_ORTHOSTATIC_DIZZINESS",
            "Q_PERIPHERAL_PARESTHESIA",
            "Q_TUBE_WELL_WATER"
        ],
        ChiefComplaintCategory.CHEST_PAIN: [
            "Q_CHEST_RADIATION",
            "Q_CHEST_DIAPHORESIS",
            "Q_EPIGASTRIC_DISTRESS"
        ]
    }

    def initiate_sequential_intake(
        self,
        session_id: str,
        patient_id: str,
        chief_complaint: ChiefComplaintCategory,
        patient_age: int,
        is_female: bool,
        is_pregnant: bool = False
    ) -> Dict[str, Any]:
        session = self.initiate_session(
            session_id=session_id,
            patient_id=patient_id,
            chief_complaint=chief_complaint,
            patient_age=patient_age,
            is_female=is_female,
            is_pregnant=is_pregnant
        )
        flow = self.CATEGORY_QUESTION_FLOW.get(chief_complaint, [])
        session.planned_question_ids = list(flow)
        session.unanswered_question_ids = list(flow)
        session.current_turn = 0
        session.intake_status = "IN_PROGRESS"

        first_q = None
        if flow:
            q_id = flow[0]
            first_q = self.QUESTION_CATALOG.get(q_id)
            session.pending_question = first_q

        if not hasattr(self, "_active_sessions"):
            self._active_sessions = {}
        self._active_sessions[session_id] = session

        return {
            "session_id": session_id,
            "patient_id": patient_id,
            "intake_status": "IN_PROGRESS",
            "current_turn": 1,
            "total_turns_planned": len(flow),
            "pending_question": first_q
        }

    def process_sequential_turn(
        self,
        session_id: str,
        question_id: str,
        answer_value: Any
    ) -> Dict[str, Any]:
        if not hasattr(self, "_active_sessions") or session_id not in self._active_sessions:
            raise KeyError(f"Active clinical intake session '{session_id}' not found.")

        session = self._active_sessions[session_id]
        q_meta = self.QUESTION_CATALOG.get(question_id)
        if not q_meta:
            raise ValueError(f"Unknown clinical question ID '{question_id}'")

        attr_key = q_meta["attribute_key"]
        is_pos = (answer_value is True or str(answer_value).upper() in ("YES", "TRUE", "1"))

        ans_dict = {attr_key: is_pos}
        self.process_responses(session, ans_dict)

        if question_id in session.unanswered_question_ids:
            session.unanswered_question_ids.remove(question_id)
        session.current_turn += 1

        next_q = None
        if session.unanswered_question_ids:
            next_q_id = session.unanswered_question_ids[0]
            next_q = self.QUESTION_CATALOG.get(next_q_id)
            session.pending_question = next_q
            status = "IN_PROGRESS"
        else:
            session.pending_question = None
            session.intake_status = "COMPLETED"
            status = "COMPLETED"

        return {
            "session_id": session_id,
            "intake_status": status,
            "current_turn": session.current_turn,
            "remaining_questions": len(session.unanswered_question_ids),
            "next_question": next_q,
            "active_red_flags": session.active_red_flags,
            "findings_count": len(session.findings)
        }

    def evaluate_partial_session(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Graceful Partial-Intake Fallback:
        If patient drops off or disconnects mid-triage, computes a conservative provisional
        differential from available evidence, flags unexcluded critical red flags, and emits
        urgent clinical escalation guidance.
        """
        if not hasattr(self, "_active_sessions") or session_id not in self._active_sessions:
            raise KeyError(f"Active clinical intake session '{session_id}' not found.")

        session = self._active_sessions[session_id]
        session.intake_status = "PARTIAL_FALLBACK"

        unexcluded = []
        partial_diff = []
        unanswered_set = set(session.unanswered_question_ids)

        if session.chief_complaint == ChiefComplaintCategory.DERMATOLOGIC_PIGMENTARY_OR_RASH:
            has_palmar = any(f.snomed_id == "247441003" and f.polarity == FindingPolarity.PRESENT for f in session.findings)
            if has_palmar:
                if "Q_ORTHOSTATIC_DIZZINESS" in unanswered_set or "Q_BUCCAL_MUCOSA" in unanswered_set:
                    unexcluded.append("PRIMARY_ADRENAL_INSUFFICIENCY_ADDISONS_CRISIS")
                    partial_diff.append({
                        "condition": "Primary Adrenal Insufficiency (Addison's Disease)",
                        "priority": "MUST_NOT_MISS",
                        "status": "UNEXCLUDED_HIGH_RISK",
                        "reason": "Palmar crease hyperpigmentation present; orthostatic dizziness/mucosal involvement unanswered"
                    })
                if "Q_PERIPHERAL_PARESTHESIA" in unanswered_set:
                    unexcluded.append("VITAMIN_B12_DEFICIENCY_NEUROPATHY")
                    partial_diff.append({
                        "condition": "Severe Vitamin B12 (Cobalamin) Deficiency",
                        "priority": "HIGH",
                        "status": "UNEXCLUDED",
                        "reason": "Palmar hyperpigmentation present; peripheral tingling/neuropathy unanswered"
                    })
                if "Q_TUBE_WELL_WATER" in unanswered_set:
                    unexcluded.append("CHRONIC_ARSENICOSIS_MELANOSIS")
                    partial_diff.append({
                        "condition": "Chronic Arsenic Toxicity (Arsenicosis)",
                        "priority": "MODERATE",
                        "status": "UNEXCLUDED",
                        "reason": "Palmar hyperpigmentation present; tube-well groundwater source unverified"
                    })

        elif session.chief_complaint == ChiefComplaintCategory.CHEST_PAIN:
            if "Q_CHEST_DIAPHORESIS" in unanswered_set or "Q_CHEST_RADIATION" in unanswered_set:
                unexcluded.append("ACUTE_CORONARY_SYNDROME_MYOCARDIAL_INFARCTION")
                partial_diff.append({
                    "condition": "Acute Myocardial Infarction",
                    "priority": "MUST_NOT_MISS",
                    "status": "UNEXCLUDED_LETHAL",
                    "reason": "Chest pain intake incomplete; autonomic diaphoresis/radiation unverified"
                })

        session.unexcluded_must_not_miss = unexcluded
        session.partial_differential = partial_diff

        safety_net_instructions = [
            "PARTIAL CLINICAL INTAKE WARNING: Patient disconnected or timed out before evaluation completed.",
            "Conservative rule-out mode engaged: Do not assume unasked or unanswered questions are negative.",
            f"CRITICAL RULE-OUTS REMAINING UNEXCLUDED: {', '.join(unexcluded) if unexcluded else 'None'}",
            "If patient is experiencing severe weakness, postural dizziness, blackouts, or vomiting: REPORT TO EMERGENCY ROOM IMMEDIATELY."
        ]
        session.recommended_immediate_actions = safety_net_instructions + session.recommended_immediate_actions

        return {
            "session_id": session.session_id,
            "patient_id": session.patient_id,
            "intake_status": "PARTIAL_FALLBACK",
            "data_quality": "INCOMPLETE_INTAKE_FALLBACK",
            "turns_completed": session.current_turn,
            "unanswered_questions_count": len(session.unanswered_question_ids),
            "unexcluded_must_not_miss": unexcluded,
            "partial_differential": partial_diff,
            "active_red_flags": session.active_red_flags,
            "recommended_immediate_actions": session.recommended_immediate_actions
        }
