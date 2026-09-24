"""
PROJECT "HOSPITAL" — PHASE 40: CLINICAL SPECIALTY EXPANSION
Module: services/core-api/gynecology_oncology_engine.py
Purpose: Comprehensive Gynecologic, Reproductive Endocrinology, and Gynecologic Oncology Engine.
Clinical Governance:
  - FIGO Abnormal Uterine Bleeding (AUB) PALM-COEIN Classification (2018)
  - Rotterdam ESHRE/ASRM Polycystic Ovary Syndrome (PCOS) Consensus Criteria (2004/2018)
  - Revised American Society for Reproductive Medicine (rASRM) Endometriosis Staging
  - 2020 ASCCP Risk-Based Management Consensus Guidelines for Abnormal Cervical Cancer Screening
  - WHO / CDC Medical Eligibility Criteria for Contraceptive Use (Thrombosis & Vascular Risk)
Deterministic Invariants:
  - Sub-millisecond execution; zero ungrounded generative hallucinations.
  - Fail-closed contraindicated prescribing (e.g. COCs in smokers >= 35, prior VTE, migraine with aura).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone


class AUBStructuralCategory(str, Enum):
    POLYP = "POLYP"
    ADENOMYOSIS = "ADENOMYOSIS"
    LEIOMYOMA = "LEIOMYOMA"
    MALIGNANCY_AND_HYPERPLASIA = "MALIGNANCY_AND_HYPERPLASIA"


class AUBNonStructuralCategory(str, Enum):
    COAGULOPATHY = "COAGULOPATHY"
    OVULATORY_DYSFUNCTION = "OVULATORY_DYSFUNCTION"
    ENDOMETRIAL = "ENDOMETRIAL"
    IATROGENIC = "IATROGENIC"
    NOT_OTHERWISE_CLASSIFIED = "NOT_OTHERWISE_CLASSIFIED"


class PCOSPhenotype(str, Enum):
    PHENOTYPE_A_CLASSIC = "PHENOTYPE_A_CLASSIC"       # Hyperandrogenism + Ovulatory Dysfunction + PCOM
    PHENOTYPE_B_HYPERANDROGENIC = "PHENOTYPE_B"        # Hyperandrogenism + Ovulatory Dysfunction (Normal Ovaries)
    PHENOTYPE_C_OVULATORY = "PHENOTYPE_C_OVULATORY"    # Hyperandrogenism + PCOM (Regular Cycles)
    PHENOTYPE_D_NON_HYPERANDROGENIC = "PHENOTYPE_D"    # Ovulatory Dysfunction + PCOM (Normal Androgens)
    NON_PCOS = "NON_PCOS"


class EndometriosisStage(str, Enum):
    STAGE_I_MINIMAL = "STAGE_I_MINIMAL"      # Score 1-5
    STAGE_II_MILD = "STAGE_II_MILD"          # Score 6-15
    STAGE_III_MODERATE = "STAGE_III_MODERATE"# Score 16-40
    STAGE_IV_SEVERE = "STAGE_IV_SEVERE"      # Score > 40


class CervicalCytology(str, Enum):
    NILM = "NILM"         # Negative for Intraepithelial Lesion or Malignancy
    ASC_US = "ASC_US"     # Atypical Squamous Cells of Undetermined Significance
    LSIL = "LSIL"         # Low-Grade Squamous Intraepithelial Lesion
    ASC_H = "ASC_H"       # Atypical Squamous Cells, Cannot Exclude HSIL
    HSIL = "HSIL"         # High-Grade Squamous Intraepithelial Lesion
    AGC = "AGC"           # Atypical Glandular Cells


class ASCCPTriageAction(str, Enum):
    ROUTINE_SCREENING_3_YEARS = "ROUTINE_SCREENING_3_YEARS"
    REPEAT_COTUSTING_1_YEAR = "REPEAT_COTUSTING_1_YEAR"
    COLPOSCOPY_MANDATORY = "COLPOSCOPY_MANDATORY"
    COLPOSCOPY_OR_EXCISION_IMMEDIATE = "COLPOSCOPY_OR_EXCISION_IMMEDIATE"


@dataclass
class FIGOAUBClassificationResult:
    patient_id: str
    is_structural: bool
    structural_types: List[AUBStructuralCategory] = field(default_factory=list)
    non_structural_types: List[AUBNonStructuralCategory] = field(default_factory=list)
    leiomyoma_subclassification: Optional[str] = None  # Submucosal (SM) vs Other (O)
    is_red_flag_malignancy: bool = False
    mandatory_evaluations: List[str] = field(default_factory=list)
    recommended_interventions: List[str] = field(default_factory=list)


@dataclass
class PCOSEvaluationResult:
    patient_id: str
    phenotype: PCOSPhenotype
    has_hyperandrogenism: bool
    has_ovulatory_dysfunction: bool
    has_polycystic_ovaries: bool
    ferriman_gallwey_score: int
    metabolic_risk_level: str  # LOW, MODERATE, HIGH
    indicated_metabolic_screens: List[str] = field(default_factory=list)
    therapeutic_strategy: List[str] = field(default_factory=list)


@dataclass
class EndometriosisStagingResult:
    patient_id: str
    stage: EndometriosisStage
    rASRM_score: int
    deep_infiltrating_endometriosis_present: bool
    endometrioma_present: bool
    ca125_elevated: bool
    recommended_pathway: str
    fertility_preservation_indicated: bool


@dataclass
class ContraceptiveSafetyResult:
    is_prescribing_safe: bool
    contraindication_severity: str  # "ABSOLUTE_CONTRAINDICATION", "RELATIVE_CAUTION", "SAFE"
    contraindications_detected: List[str] = field(default_factory=list)
    safe_alternative_contraceptives: List[str] = field(default_factory=list)


class GynecologyOncologyEngine:
    """
    Core Gynecologic Clinical Decision Support Engine enforcing FIGO, Rotterdam,
    rASRM, ASCCP 2020, and WHO Contraceptive Eligibility Standards.
    """

    def evaluate_aub_figo(
        self,
        patient_id: str,
        patient_age: int,
        has_polyp: bool = False,
        has_adenomyosis: bool = False,
        has_leiomyoma: bool = False,
        leiomyoma_submucosal: bool = False,
        has_malignancy_or_atypical_hyperplasia: bool = False,
        has_documented_coagulopathy: bool = False,
        has_ovulatory_irregularity: bool = False,
        has_endometrial_infection_or_endometritis: bool = False,
        is_on_anticoagulants_or_iud: bool = False,
        unclassified_findings: bool = False,
        endometrial_thickness_mm: Optional[float] = None
    ) -> FIGOAUBClassificationResult:
        """
        Classifies Abnormal Uterine Bleeding according to FIGO PALM-COEIN.
        Enforces post-menopausal endometrial thickness vigilance (> 4mm requires biopsy).
        """
        structs = []
        non_structs = []

        if has_polyp:
            structs.append(AUBStructuralCategory.POLYP)
        if has_adenomyosis:
            structs.append(AUBStructuralCategory.ADENOMYOSIS)
        if has_leiomyoma:
            structs.append(AUBStructuralCategory.LEIOMYOMA)
        if has_malignancy_or_atypical_hyperplasia:
            structs.append(AUBStructuralCategory.MALIGNANCY_AND_HYPERPLASIA)

        if has_documented_coagulopathy:
            non_structs.append(AUBNonStructuralCategory.COAGULOPATHY)
        if has_ovulatory_irregularity:
            non_structs.append(AUBNonStructuralCategory.OVULATORY_DYSFUNCTION)
        if has_endometrial_infection_or_endometritis:
            non_structs.append(AUBNonStructuralCategory.ENDOMETRIAL)
        if is_on_anticoagulants_or_iud:
            non_structs.append(AUBNonStructuralCategory.IATROGENIC)
        if unclassified_findings or (not structs and not non_structs):
            non_structs.append(AUBNonStructuralCategory.NOT_OTHERWISE_CLASSIFIED)

        is_structural = len(structs) > 0
        l_sub = None
        if has_leiomyoma:
            l_sub = "SUBMUCOSAL (FIGO Type 0-2)" if leiomyoma_submucosal else "OTHER (FIGO Type 3-8)"

        is_red_flag = has_malignancy_or_atypical_hyperplasia
        evals = []
        interventions = []

        # Postmenopausal Bleeding Safety Rule
        if patient_age >= 50:
            evals.append("Transvaginal Ultrasonography (TVS) for Endometrial Thickness measurement")
            if endometrial_thickness_mm is not None and endometrial_thickness_mm > 4.0:
                is_red_flag = True
                evals.append("URGENT: Pipelle Endometrial Aspiration Biopsy / Hysteroscopic D&C (ET > 4mm in postmenopausal patient)")
                interventions.append("Rule out Endometrial Carcinoma prior to any hormonal therapy")

        if AUBStructuralCategory.POLYP in structs:
            evals.append("Saline Infusion Sonohysterography (SIS) or Diagnostic Hysteroscopy")
            interventions.append("Hysteroscopic polypectomy with histopathological evaluation")

        if AUBStructuralCategory.LEIOMYOMA in structs and leiomyoma_submucosal:
            interventions.append("Consider Tranexamic acid or Levonorgestrel-releasing IUD (Mirena) for bleeding reduction; Hysteroscopic myomectomy evaluation")

        return FIGOAUBClassificationResult(
            patient_id=patient_id,
            is_structural=is_structural,
            structural_types=structs,
            non_structural_types=non_structs,
            leiomyoma_subclassification=l_sub,
            is_red_flag_malignancy=is_red_flag,
            mandatory_evaluations=evals,
            recommended_interventions=interventions
        )

    def evaluate_pcos_rotterdam(
        self,
        patient_id: str,
        cycle_length_days_avg: float,
        cycles_per_year: int,
        clinical_hirsutism_fg_score: int,
        biochemical_free_testosterone_elevated: bool,
        antral_follicle_count_per_ovary: int,
        ovarian_volume_ml: float,
        bmi: float = 24.0,
        has_acanthosis_nigricans: bool = False
    ) -> PCOSEvaluationResult:
        """
        Diagnoses PCOS based on the 2004/2018 Rotterdam criteria (at least 2 of 3 features):
        1. Oligo- or anovulation (cycles > 35 days or < 9 cycles/year).
        2. Clinical and/or biochemical hyperandrogenism (FG score >= 8, or elevated androgen).
        3. Polycystic ovarian morphology (>= 20 follicles per ovary and/or ovarian volume > 10 mL).
        """
        has_ovulatory = (cycle_length_days_avg > 35.0 or cycles_per_year < 9)
        has_hyperandrogenism = (clinical_hirsutism_fg_score >= 8 or biochemical_free_testosterone_elevated)
        has_pcom = (antral_follicle_count_per_ovary >= 20 or ovarian_volume_ml > 10.0)

        criteria_count = sum([has_ovulatory, has_hyperandrogenism, has_pcom])

        if criteria_count < 2:
            phenotype = PCOSPhenotype.NON_PCOS
        elif has_hyperandrogenism and has_ovulatory and has_pcom:
            phenotype = PCOSPhenotype.PHENOTYPE_A_CLASSIC
        elif has_hyperandrogenism and has_ovulatory and not has_pcom:
            phenotype = PCOSPhenotype.PHENOTYPE_B_HYPERANDROGENIC
        elif has_hyperandrogenism and not has_ovulatory and has_pcom:
            phenotype = PCOSPhenotype.PHENOTYPE_C_OVULATORY
        elif not has_hyperandrogenism and has_ovulatory and has_pcom:
            phenotype = PCOSPhenotype.PHENOTYPE_D_NON_HYPERANDROGENIC
        else:
            phenotype = PCOSPhenotype.NON_PCOS

        metabolic_risk = "LOW"
        if bmi >= 30.0 or has_acanthosis_nigricans:
            metabolic_risk = "HIGH"
        elif bmi >= 25.0:
            metabolic_risk = "MODERATE"

        screens = [
            "Baseline 75g 2-hour Oral Glucose Tolerance Test (OGTT)",
            "Fasting Lipid Profile (Total Cholesterol, HDL, LDL, Triglycerides)",
            "Serum TSH & Prolactin to rule out thyroid dysfunction and hyperprolactinemia",
            "17-Hydroxyprogesterone (17-OHP) to exclude Non-Classic Congenital Adrenal Hyperplasia"
        ]

        therapy = []
        if phenotype != PCOSPhenotype.NON_PCOS:
            therapy.append("Lifestyle modification: 5-10% weight reduction through caloric deficit and resistance training")
            if has_ovulatory:
                therapy.append("Endometrial protection: Cyclic oral progestins or Levonorgestrel-releasing IUD to prevent endometrial hyperplasia")
            if has_hyperandrogenism:
                therapy.append("Combined oral contraceptive with anti-androgenic progestin (Cyproterone/Drospirenone) or Spironolactone 50-100mg daily")
            if metabolic_risk in ("MODERATE", "HIGH"):
                therapy.append("Metformin 500-1500mg daily for insulin sensitization")

        return PCOSEvaluationResult(
            patient_id=patient_id,
            phenotype=phenotype,
            has_hyperandrogenism=has_hyperandrogenism,
            has_ovulatory_dysfunction=has_ovulatory,
            has_polycystic_ovaries=has_pcom,
            ferriman_gallwey_score=clinical_hirsutism_fg_score,
            metabolic_risk_level=metabolic_risk,
            indicated_metabolic_screens=screens,
            therapeutic_strategy=therapy
        )

    def evaluate_endometriosis_rasrm(
        self,
        patient_id: str,
        peritoneal_superficial_score: int,
        ovarian_endometrioma_score: int,
        cul_de_sac_obliteration_score: int,  # 0 = none, 40 = complete obliteration
        tubal_adhesion_score: int,
        deep_infiltrating_nodules_present: bool = False,
        ca125_u_per_ml: Optional[float] = None
    ) -> EndometriosisStagingResult:
        """
        Stages Endometriosis per the revised American Society for Reproductive Medicine (rASRM).
        Stage I: 1-5, Stage II: 6-15, Stage III: 16-40, Stage IV: > 40.
        """
        total_score = (
            peritoneal_superficial_score +
            ovarian_endometrioma_score +
            cul_de_sac_obliteration_score +
            tubal_adhesion_score
        )

        if total_score <= 5:
            stage = EndometriosisStage.STAGE_I_MINIMAL
        elif total_score <= 15:
            stage = EndometriosisStage.STAGE_II_MILD
        elif total_score <= 40:
            stage = EndometriosisStage.STAGE_III_MODERATE
        else:
            stage = EndometriosisStage.STAGE_IV_SEVERE

        has_endometrioma = ovarian_endometrioma_score > 0
        ca125_elevated = (ca125_u_per_ml is not None and ca125_u_per_ml > 35.0)

        pathway = "Medical Management: Continuous Progestins (Dienogest 2mg daily) or GnRH Antagonist/Agonist with add-back"
        if stage in (EndometriosisStage.STAGE_III_MODERATE, EndometriosisStage.STAGE_IV_SEVERE) or deep_infiltrating_nodules_present:
            pathway = "Surgical Multidisciplinary Excision: Laparoscopic excision with colorectal/urology standby if DIE present"

        fertility_preservation = (stage in (EndometriosisStage.STAGE_III_MODERATE, EndometriosisStage.STAGE_IV_SEVERE) or has_endometrioma)

        return EndometriosisStagingResult(
            patient_id=patient_id,
            stage=stage,
            rASRM_score=total_score,
            deep_infiltrating_endometriosis_present=deep_infiltrating_nodules_present,
            endometrioma_present=has_endometrioma,
            ca125_elevated=ca125_elevated,
            recommended_pathway=pathway,
            fertility_preservation_indicated=fertility_preservation
        )

    def evaluate_cervical_screening_asccp(
        self,
        patient_id: str,
        patient_age: int,
        cytology: CervicalCytology,
        hpv_16_18_positive: bool,
        hpv_other_high_risk_positive: bool,
        history_of_cin2_plus: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates cervical cancer screening results against ASCCP 2020 Risk-Based Consensus.
        Thresholds: Immediate Colposcopy / Excision threshold >= 4.0% immediate CIN 3+ risk.
        """
        is_hpv_positive = (hpv_16_18_positive or hpv_other_high_risk_positive)

        # High-Grade Cytology or HPV 16/18 High Risk
        if cytology == CervicalCytology.HSIL or cytology == CervicalCytology.ASC_H:
            action = ASCCPTriageAction.COLPOSCOPY_OR_EXCISION_IMMEDIATE
            rationale = "High-grade squamous intraepithelial lesion carries >= 25% immediate CIN 3+ risk"
            mandatory_next_step = "Immediate Diagnostic Colposcopy with directed cervical punch biopsy and endocervical curettage (ECC)"
        elif hpv_16_18_positive:
            action = ASCCPTriageAction.COLPOSCOPY_MANDATORY
            rationale = "HPV Genotypes 16 and/or 18 represent highest oncogenic virulence"
            mandatory_next_step = "Colposcopy mandatory regardless of cytology finding"
        elif cytology == CervicalCytology.LSIL and is_hpv_positive:
            action = ASCCPTriageAction.COLPOSCOPY_MANDATORY
            rationale = "LSIL with co-positive high-risk HPV exceeds 4% immediate CIN 3+ threshold"
            mandatory_next_step = "Colposcopic evaluation within 3 months"
        elif cytology == CervicalCytology.ASC_US and is_hpv_positive:
            action = ASCCPTriageAction.COLPOSCOPY_MANDATORY
            rationale = "ASC-US with positive high-risk HPV meets colposcopy threshold"
            mandatory_next_step = "Colposcopy"
        elif cytology == CervicalCytology.NILM and hpv_other_high_risk_positive:
            action = ASCCPTriageAction.REPEAT_COTUSTING_1_YEAR
            rationale = "Normal cytology with non-16/18 high-risk HPV: intermediate risk"
            mandatory_next_step = "Repeat co-testing (Cytology + HPV) in 12 months"
        elif cytology == CervicalCytology.NILM and not is_hpv_positive:
            action = ASCCPTriageAction.ROUTINE_SCREENING_3_YEARS
            rationale = "Co-negative screen carries < 0.15% 5-year CIN 3+ risk"
            mandatory_next_step = "Return to routine co-testing every 5 years or cytology every 3 years"
        else:
            action = ASCCPTriageAction.REPEAT_COTUSTING_1_YEAR
            rationale = "Equivocal or low-risk cytology in HPV-negative patient"
            mandatory_next_step = "Repeat cervical screening in 1 year"

        return {
            "patient_id": patient_id,
            "patient_age": patient_age,
            "cytology": cytology.value,
            "hpv_status": "HPV_16_18_POSITIVE" if hpv_16_18_positive else ("HPV_HR_POSITIVE" if hpv_other_high_risk_positive else "NEGATIVE"),
            "action": action.value,
            "clinical_rationale": rationale,
            "mandatory_next_step": mandatory_next_step
        }

    def screen_coc_contraindications(
        self,
        patient_id: str,
        patient_age: int,
        cigarettes_per_day: int = 0,
        systolic_bp: float = 120.0,
        diastolic_bp: float = 80.0,
        has_prior_dvt_or_pe: bool = False,
        has_migraine_with_aura: bool = False,
        has_active_liver_disease: bool = False,
        has_known_thrombophilia: bool = False,
        is_postpartum_under_21_days: bool = False
    ) -> ContraceptiveSafetyResult:
        """
        WHO / CDC Medical Eligibility Criteria Category 4 (Unacceptable Health Risk - ABSOLUTE CONTRAINDICATION)
        for Combined Oral Contraceptive (Estrogen-Progestin) therapy.
        """
        contraindications = []

        if patient_age >= 35 and cigarettes_per_day >= 15:
            contraindications.append("AGE >= 35 AND HEAVY SMOKER (>= 15 cigarettes/day): Extreme risk of myocardial infarction & stroke")
        elif patient_age >= 35 and cigarettes_per_day > 0:
            contraindications.append("AGE >= 35 AND SMOKER (< 15 cigarettes/day): Unacceptable cardiovascular risk (WHO Category 3/4)")

        if systolic_bp >= 160.0 or diastolic_bp >= 100.0:
            contraindications.append(f"UNCONTROLLED HYPERTENSION ({systolic_bp}/{diastolic_bp} mmHg): Severe risk of hemorrhagic stroke and aortic events")
        elif systolic_bp >= 140.0 or diastolic_bp >= 90.0:
            contraindications.append(f"STAGE 1 HYPERTENSION ({systolic_bp}/{diastolic_bp} mmHg): Relative caution (WHO Category 3)")

        if has_prior_dvt_or_pe or has_known_thrombophilia:
            contraindications.append("HISTORY OF VENOUS THROMBOEMBOLISM OR KNOWN THROMBOPHILIA (Factor V Leiden, Antithrombin III deficiency)")

        if has_migraine_with_aura:
            contraindications.append("MIGRAINE WITH FOCAL NEUROLOGIC AURA: Markedly elevated ischemic stroke risk with ethinyl estradiol")

        if has_active_liver_disease:
            contraindications.append("ACTIVE ACUTE VIRAL HEPATITIS, SEVERE DECOMPENSATED CIRRHOSIS, OR HEPATIC ADENOMA")

        if is_postpartum_under_21_days:
            contraindications.append("POSTPARTUM < 21 DAYS: Hypercoagulable puerperal window")

        is_safe = len(contraindications) == 0
        severity = "SAFE" if is_safe else "ABSOLUTE_CONTRAINDICATION"

        alternatives = [
            "Levonorgestrel-releasing Intrauterine System (Mirena / Kyleena)",
            "Copper Intrauterine Device (Cu-T 380A) (Non-hormonal)",
            "Progestin-Only Pill (POP / Minipill: Desogestrel 75mcg)",
            "Subdermal Etonogestrel Implant (Nexplanon)",
            "Barrier contraception (condoms)"
        ]

        return ContraceptiveSafetyResult(
            is_prescribing_safe=is_safe,
            contraindication_severity=severity,
            contraindications_detected=contraindications,
            safe_alternative_contraceptives=alternatives if not is_safe else []
        )


# Global Engine Singleton
global_gynecology_oncology_engine = GynecologyOncologyEngine()
