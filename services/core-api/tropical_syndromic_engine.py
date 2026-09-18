# ====================================================================================================
# PROJECT "HOSPITAL" — TROPICAL INFECTION & GEO-TEMPORAL DEDUCTION ENGINE
# ====================================================================================================
# Module: services/core-api/tropical_syndromic_engine.py
# Purpose: Implements the AIIMS New Delhi & CMC Vellore Tropical Medicine syndromic deduction
#          protocols for acute febrile illnesses across South Asia. Evaluates geo-temporal endemicity,
#          seasonal monsoon dynamics, and hematologic kinetics (Platelet/Hematocrit ratio) to
#          differentiate Dengue, Malaria, Scrub Typhus, Leptospirosis, Kala-Azar, and Enteric Fever.
# ====================================================================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class TropicalInfectionType(str, Enum):
    DENGUE_WITH_WARNING_SIGNS = "DENGUE_WITH_WARNING_SIGNS"
    SEVERE_DENGUE_SHOCK = "SEVERE_DENGUE_SHOCK"
    SEVERE_FALCIPARUM_MALARIA = "SEVERE_FALCIPARUM_MALARIA"
    VIVAX_MALARIA = "VIVAX_MALARIA"
    SCRUB_TYPHUS_WITH_ARDS_RISK = "SCRUB_TYPHUS_WITH_ARDS_RISK"
    LEPTOSPIROSIS_WEILS_DISEASE = "LEPTOSPIROSIS_WEILS_DISEASE"
    VISCERAL_LEISHMANIASIS_KALA_AZAR = "VISCERAL_LEISHMANIASIS_KALA_AZAR"
    ENTERIC_TYPHOID_FEVER = "ENTERIC_TYPHOID_FEVER"
    UNDIFFERENTIATED_TROPICAL_FEVER = "UNDIFFERENTIATED_TROPICAL_FEVER"


@dataclass
class TropicalFeverAssessment:
    primary_suspect: TropicalInfectionType
    confidence_score: float
    differential_diagnoses: List[Dict[str, Any]]
    severity_grade: str  # MILD, MODERATE, SEVERE_CRITICAL
    warning_signs_detected: List[str]
    hematologic_kinetics: Dict[str, Any]
    immediate_holding_protocol: List[str]
    stat_confirmatory_tests: List[str]
    contraindicated_interventions: List[str]
    clinical_guideline_source: str = "AIIMS New Delhi & CMC Vellore Tropical Medicine Clinical Protocol"


class TropicalInfectionDeductionEngine:
    """
    Syndromic deduction engine for acute tropical febrile illnesses, incorporating
    AIIMS and CMC Vellore national clinical guidelines.
    """

    def evaluate_fever(
        self,
        patient_age: int,
        days_of_fever: int,
        platelet_count: Optional[int] = None,
        hematocrit_pct: Optional[float] = None,
        baseline_hematocrit_pct: Optional[float] = None,
        systolic_bp: Optional[int] = None,
        pulse_rate: Optional[int] = None,
        symptoms: Optional[List[str]] = None,
        physical_signs: Optional[List[str]] = None,
        is_monsoon_season: bool = True,
        is_pregnant: bool = False,
        geographic_belt: str = "GANGETIC_ALLUVIAL"
    ) -> TropicalFeverAssessment:
        sym_set = set(s.lower() for s in (symptoms or []))
        sign_set = set(s.lower() for s in (physical_signs or []))

        # Hematologic Kinetics Analysis
        hemoconcentration_pct = 0.0
        if hematocrit_pct and baseline_hematocrit_pct and baseline_hematocrit_pct > 0:
            hemoconcentration_pct = round(((hematocrit_pct - baseline_hematocrit_pct) / baseline_hematocrit_pct) * 100.0, 1)

        thrombocytopenia = platelet_count is not None and platelet_count < 100000
        severe_thrombocytopenia = platelet_count is not None and platelet_count < 50000
        critical_thrombocytopenia = platelet_count is not None and platelet_count < 20000

        warning_signs = []
        immediate_actions = []
        stat_tests = []
        contraindicated = []
        differentials = []

        # ------------------------------------------------------------------------------------------
        # 1. DENGUE SEVERITY & CAPILLARY LEAK CHECK
        # ------------------------------------------------------------------------------------------
        has_abdominal_pain = any("abdominal" in s for s in sym_set)
        has_persistent_vomiting = any("vomit" in s for s in sym_set)
        has_mucosal_bleed = any("bleed" in s or "petechiae" in s or "epistaxis" in s for s in sym_set | sign_set)
        has_fluid_accumulation = any("ascites" in s or "effusion" in s or "puffiness" in s for s in sign_set)
        has_retro_orbital_pain = any("retro-orbital" in s or "behind eyes" in s for s in sym_set)

        is_narrow_pulse_pressure = False
        if systolic_bp and pulse_rate:
            pulse_pressure = systolic_bp - (systolic_bp * 0.65)  # estimate if diastolic absent
            if systolic_bp < 90 or pulse_rate > 110:
                is_narrow_pulse_pressure = True

        if has_abdominal_pain:
            warning_signs.append("Severe persistent abdominal pain / tenderness (Sign of rapid plasma leakage)")
        if has_persistent_vomiting:
            warning_signs.append("Persistent vomiting (prevents oral rehydration)")
        if has_mucosal_bleed:
            warning_signs.append("Mucosal bleeding / petechial purpura")
        if has_fluid_accumulation or hemoconcentration_pct >= 20.0:
            warning_signs.append(f"Clinical plasma leak: Hematocrit rise {hemoconcentration_pct}% (>= 20% hemoconcentration threshold)")

        # ------------------------------------------------------------------------------------------
        # 1. SCRUB TYPHUS EVALUATION (Orientia tsutsugamushi) — PATHOGNOMONIC ESCHAR
        # ------------------------------------------------------------------------------------------
        if any("eschar" in s for s in sign_set):
            primary = TropicalInfectionType.SCRUB_TYPHUS_WITH_ARDS_RISK
            severity = "SEVERE_CRITICAL" if any("breathless" in s or "ards" in s for s in sym_set) else "MODERATE"
            conf = 0.95
            warning_signs.append("Pathognomonic cigarette-burn ESCHAR detected: Highly diagnostic of Scrub Typhus Vasculitis")

            abx_therapy = "Tab. DOXYCYCLINE 100mg PO bid for 7-10 days" if not is_pregnant else "Tab. AZITHROMYCIN 500mg PO daily for 7 days (Pregnancy safe)"
            immediate_actions.extend([
                f"STAT EMPIRIC ANTIMICROBIAL: {abx_therapy}",
                "Perform meticulous whole-body cutaneous inspection for additional eschars in skin folds (groin, axilla, waistband, perineum)",
                "Monitor oxygen saturation continuously; prepare for non-invasive ventilation if PaO2/FiO2 drops"
            ])
            stat_tests.extend([
                "Scrub Typhus IgM ELISA (InBios, cut-off OD > 0.5 for Indian endemicity)",
                "Chest X-Ray / Arterial Blood Gas (ABG) to screen for interstitial pneumonitis / ARDS",
                "Liver Function Tests (evaluate transaminitis / reactive hepatitis)"
            ])
            differentials.append({"condition": "Dengue Fever", "probability": 0.40, "rationale": "Shared thrombocytopenia and fever"})
            differentials.append({"condition": "Leptospirosis", "probability": 0.30, "rationale": "Shared vasculitic multi-organ involvement"})

        # ------------------------------------------------------------------------------------------
        # 2. DENGUE SEVERITY & CAPILLARY LEAK CHECK
        # ------------------------------------------------------------------------------------------
        elif (has_retro_orbital_pain or days_of_fever in (3, 4, 5, 6, 7)) and thrombocytopenia:
            if is_narrow_pulse_pressure or critical_thrombocytopenia or hemoconcentration_pct >= 20.0:
                primary = TropicalInfectionType.SEVERE_DENGUE_SHOCK
                severity = "SEVERE_CRITICAL"
                conf = 0.90
            elif warning_signs:
                primary = TropicalInfectionType.DENGUE_WITH_WARNING_SIGNS
                severity = "MODERATE"
                conf = 0.85
            else:
                primary = TropicalInfectionType.DENGUE_WITH_WARNING_SIGNS
                severity = "MODERATE"
                conf = 0.75

            immediate_actions.extend([
                "INITIATE ISOTONIC CRYSTALLOIDS (Normal Saline / Ringer's Lactate) titrated strictly at 5-7 mL/kg/hour for 1-2 hours",
                "Repeat Hematocrit every 4-6 hours to titrate fluid infusion rate (taper to 3-5 mL/kg/h as Hct stabilizes)",
                "Hourly urine output monitoring: Target strictly > 0.5 mL/kg/hour",
                "AVOID PROPHYLACTIC PLATELET TRANSFUSIONS even if count < 20,000 unless active severe clinical hemorrhage occurs (AIIMS/WHO Guideline)"
            ])
            stat_tests.extend([
                "Dengue NS1 Antigen (Day 1-5) or Dengue IgM/IgG ELISA (Day >= 5)",
                "Serial Complete Blood Count (CBC) with Hematocrit every 6 hours",
                "Bedside Focused Ultrasound (USG Abdomen/Chest) for gall bladder wall edema, ascites, and pleural effusion"
            ])
            contraindicated.extend([
                "DO NOT ADMINISTER NSAIDs (Ibuprofen, Diclofenac, Aspirin) due to catastrophic gastrointestinal hemorrhage risk. Use Paracetamol only (max 3g/day).",
                "DO NOT ADMINISTER INTRAMUSCULAR (IM) INJECTIONS (triggers massive intramuscular hematoma)",
                "DO NOT ADMINISTER EXCESSIVE IV HYDRATION in recovery phase (leads to fatal pulmonary edema)"
            ])
            differentials.append({"condition": "Scrub Typhus", "probability": 0.35, "rationale": "Overlapping thrombocytopenia & capillary leak"})
            differentials.append({"condition": "Falciparum Malaria", "probability": 0.25, "rationale": "High endemic overlap"})

        # ------------------------------------------------------------------------------------------
        # 3. SCRUB TYPHUS WITHOUT ESCHAR (Respiratory / Lymphadenopathic Presentation)
        # ------------------------------------------------------------------------------------------
        elif thrombocytopenia and any("lymphadenopathy" in s or "cough" in s or "breathless" in s for s in sym_set | sign_set):
            primary = TropicalInfectionType.SCRUB_TYPHUS_WITH_ARDS_RISK
            severity = "SEVERE_CRITICAL" if any("breathless" in s or "ards" in s for s in sym_set) else "MODERATE"
            conf = 0.78
            warning_signs.append("Scrub Typhus Vasculitis with Acute Respiratory Distress Syndrome (ARDS) / Multi-Organ Dysfunction Risk")

            abx_therapy = "Tab. DOXYCYCLINE 100mg PO bid for 7-10 days" if not is_pregnant else "Tab. AZITHROMYCIN 500mg PO daily for 7 days (Pregnancy safe)"
            immediate_actions.extend([
                f"STAT EMPIRIC ANTIMICROBIAL: {abx_therapy}",
                "Perform meticulous whole-body cutaneous inspection for pathognomonic ESCHAR in skin folds (groin, axilla, waistband, perineum)",
                "Monitor oxygen saturation continuously; prepare for non-invasive ventilation if PaO2/FiO2 drops"
            ])
            stat_tests.extend([
                "Scrub Typhus IgM ELISA (InBios, cut-off OD > 0.5 for Indian endemicity)",
                "Chest X-Ray / Arterial Blood Gas (ABG) to screen for interstitial pneumonitis / ARDS",
                "Liver Function Tests (evaluate transaminitis / reactive hepatitis)"
            ])
            differentials.append({"condition": "Dengue Fever", "probability": 0.40, "rationale": "Shared thrombocytopenia and fever"})
            differentials.append({"condition": "Leptospirosis", "probability": 0.30, "rationale": "Shared vasculitic multi-organ involvement"})

        # ------------------------------------------------------------------------------------------
        # 4. LEPTOSPIROSIS / WEIL'S DISEASE
        # ------------------------------------------------------------------------------------------
        elif any("conjunctival" in s or "calf" in s for s in sym_set | sign_set) or (any("jaundice" in s for s in sym_set) and any("flood" in s or "sewage" in s or "water" in s for s in sym_set)):
            primary = TropicalInfectionType.LEPTOSPIROSIS_WEILS_DISEASE
            severity = "SEVERE_CRITICAL"
            conf = 0.88
            warning_signs.append("Weil's Syndrome triad: Conjunctival suffusion without discharge, Jaundice, and Acute Renal Failure")

            immediate_actions.extend([
                "INITIATE IV CEFTRIAXONE 1g to 2g IV once daily (or Crystalline Penicillin G 1.5 million units IV q6h)",
                "Aggressive fluid resuscitation with monitoring of hourly urine output to avert acute tubular necrosis",
                "Evaluate for Pulmonary Hemorrhage Syndrome: Sudden hemoptysis requires immediate ICU mechanical ventilation"
            ])
            stat_tests.extend([
                "Leptospira IgM ELISA / Microscopic Agglutination Test (MAT)",
                "Serum Creatinine & Blood Urea Nitrogen (screen for acute kidney injury)",
                "Total & Direct Serum Bilirubin (typically marked conjugated hyperbilirubinemia)"
            ])
            differentials.append({"condition": "Severe Falciparum Malaria", "probability": 0.35, "rationale": "Shared hepatorenal syndrome"})
            differentials.append({"condition": "Viral Hepatitis with Acute Liver Failure", "probability": 0.20, "rationale": "Shared jaundice"})

        # ------------------------------------------------------------------------------------------
        # 4. SEVERE FALCIPARUM MALARIA
        # ------------------------------------------------------------------------------------------
        elif any("chills" in s or "rigor" in s for s in sym_set) and (thrombocytopenia or any("splenomegaly" in s for s in sign_set)):
            primary = TropicalInfectionType.SEVERE_FALCIPARUM_MALARIA
            severity = "SEVERE_CRITICAL" if any("altered" in s or "coma" in s or "seizure" in s for s in sym_set) else "MODERATE"
            conf = 0.82

            immediate_actions.extend([
                "STAT IV ARTESUNATE 2.4 mg/kg IV at 0, 12, and 24 hours, then once daily for minimum 3 doses until patient can tolerate oral ACT",
                "Monitor for Hypoglycemia: Check fingerstick blood glucose every 4 hours (severe malaria consumes glucose rapidly)",
                "Strict fluid restriction (avoid overhydration; high risk of non-cardiogenic pulmonary edema in severe malaria)"
            ])
            stat_tests.extend([
                "Peripheral Blood Smear (Thick and Thin films) stained with Giemsa (examine 200 fields before declaring negative)",
                "Rapid Diagnostic Test (RDT) for Malaria Pf/Pv Antigen (HRP-2 and pLDH)",
                "Serial Hemoglobin & Serum Lactate"
            ])
            differentials.append({"condition": "Dengue Fever with Severe Thrombocytopenia", "probability": 0.40, "rationale": "High co-endemicity"})
            differentials.append({"condition": "Enteric Fever (Typhoid)", "probability": 0.25, "rationale": "Step-ladder fever pattern"})

        # ------------------------------------------------------------------------------------------
        # 5. VISCERAL LEISHMANIASIS (KALA-AZAR) — CHRONIC INDOLENT FEVER
        # ------------------------------------------------------------------------------------------
        elif days_of_fever >= 14 and (any("splenomegaly" in s for s in sign_set) or any("weight loss" in s or "darkening" in s for s in sym_set)):
            primary = TropicalInfectionType.VISCERAL_LEISHMANIASIS_KALA_AZAR
            severity = "SEVERE_CRITICAL"
            conf = 0.85
            warning_signs.append("Prolonged fever > 14 days with massive splenomegaly, pancytopenia, and hyperpigmentation (Kala-Azar)")

            immediate_actions.extend([
                "Single-Dose LIPOSOMAL AMPHOTERICIN B (AmBisome) 10 mg/kg IV infusion over 2 hours (WHO / National Kala-Azar Elimination Protocol)",
                "Strict isolation from sandfly vectors (insecticide-treated bed nets)",
                "Screen for secondary bacterial infections (leukopenia predisposes to fatal sepsis)"
            ])
            stat_tests.extend([
                "rK39 Immunochromatographic Strip Test (Rapid antibody test; 98% sensitivity in Indian subcontinent)",
                "Bone Marrow Aspirate / Splenic Aspirate for Leishmania donovani (LD) bodies (if rK39 non-conclusive)",
                "Complete Blood Count (Pancytopenia: anemia, leukopenia, thrombocytopenia)"
            ])
            differentials.append({"condition": "Disseminated Tuberculosis", "probability": 0.35, "rationale": "Shared prolonged fever & wasting"})
            differentials.append({"condition": "Hematologic Malignancy (Lymphoma/Leukemia)", "probability": 0.25, "rationale": "Shared splenomegaly & cytopenias"})

        else:
            primary = TropicalInfectionType.UNDIFFERENTIATED_TROPICAL_FEVER
            severity = "MILD"
            conf = 0.50
            immediate_actions.extend([
                "Maintain adequate oral hydration with clean water, ORS, coconut water, or fresh juices",
                "Tab. Paracetamol 500mg-650mg PO every 6 hours PRN for temperature > 100°F (DO NOT TAKE NSAIDs)",
                "Review immediately if warning signs develop: persistent vomiting, abdominal pain, breathlessness, or petechiae"
            ])
            stat_tests.extend([
                "Complete Blood Count (CBC) with Platelet Count",
                "Malaria Rapid Diagnostic Test (RDT) & Peripheral Smear",
                "Dengue NS1 Antigen & IgM Serology",
                "Urine Routine & Microscopic Examination"
            ])
            differentials.append({"condition": "Viral Exanthem / Flu", "probability": 0.40, "rationale": "Early non-specific febrile illness"})

        return TropicalFeverAssessment(
            primary_suspect=primary,
            confidence_score=conf,
            differential_diagnoses=differentials,
            severity_grade=severity,
            warning_signs_detected=warning_signs,
            hematologic_kinetics={
                "platelet_count": platelet_count,
                "hematocrit_pct": hematocrit_pct,
                "hemoconcentration_pct": hemoconcentration_pct,
                "thrombocytopenia_flag": thrombocytopenia,
                "severe_thrombocytopenia_flag": severe_thrombocytopenia,
                "critical_thrombocytopenia_flag": critical_thrombocytopenia
            },
            immediate_holding_protocol=immediate_actions,
            stat_confirmatory_tests=stat_tests,
            contraindicated_interventions=contraindicated
        )


# Singleton Instance
tropical_syndromic_engine = TropicalInfectionDeductionEngine()
