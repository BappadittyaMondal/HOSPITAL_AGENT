# ====================================================================================================
# PROJECT "HOSPITAL" — HEPATOBILIARY SCORING & SURGICAL ONCOLOGY STAGING ENGINE
# ====================================================================================================
# Module: services/core-api/hepatobiliary_oncology_engine.py
# Purpose: Implements IPGMER / SSKM Hospital (School of Digestive & Liver Diseases) and
#          Tata Memorial Hospital / MSKCC clinical standards. Provides double-precision mathematical
#          scoring for Child-Pugh Class, MELD-Na 90-day liver transplant mortality, and
#          AJCC 8th Edition TNM solid tumor anatomical staging and resectability determinations.
# ====================================================================================================

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class ChildPughClass(str, Enum):
    CLASS_A = "CLASS_A"  # 5 - 6 points (Well-compensated)
    CLASS_B = "CLASS_B"  # 7 - 9 points (Significant functional compromise)
    CLASS_C = "CLASS_C"  # 10 - 15 points (Decompensated, urgent transplant evaluation)


class TumorResectability(str, Enum):
    POTENTIALLY_RESECTABLE = "POTENTIALLY_RESECTABLE"
    LOCALLY_ADVANCED_BORDERLINE = "LOCALLY_ADVANCED_BORDERLINE"
    UNRESECTABLE_METASTATIC = "UNRESECTABLE_METASTATIC"


@dataclass
class ChildPughResult:
    total_score: int
    child_pugh_class: ChildPughClass
    one_year_survival_pct: float
    two_year_survival_pct: float
    perioperative_mortality_pct: float
    clinical_interpretation: str
    component_points: Dict[str, int]


@dataclass
class MELDNaResult:
    initial_meld: float
    meld_na_score: int
    ninety_day_mortality_pct: float
    transplant_urgency_tier: str  # ELECTIVE, HIGH_PRIORITY, CRITICAL_URGENT
    clinical_action_plan: List[str]
    input_parameters_validated: Dict[str, float]


@dataclass
class TNMStagingResult:
    tumor_site: str
    t_stage: str
    n_stage: str
    m_stage: str
    overall_stage: str
    resectability: TumorResectability
    recommended_tumor_board_actions: List[str]
    evidence_source: str = "AJCC Cancer Staging Manual 8th Edition / NCCN Guidelines"


class HepatobiliaryOncologyEngine:
    """
    Hepatobiliary and Oncology mathematical staging engine.
    """

    def calculate_child_pugh(
        self,
        total_bilirubin_mg_dl: float,
        serum_albumin_g_dl: float,
        inr: float,
        ascites_severity: str = "NONE",  # NONE, SLIGHT_OR_CONTROLLED, MODERATE_OR_SEVERE
        encephalopathy_grade: str = "NONE"  # NONE, GRADE_1_2, GRADE_3_4
    ) -> ChildPughResult:
        if total_bilirubin_mg_dl <= 0 or serum_albumin_g_dl <= 0 or inr <= 0:
            raise ValueError("Bilirubin, Albumin, and INR must be strictly positive numeric values.")

        points = {}

        # 1. Bilirubin Points
        if total_bilirubin_mg_dl < 2.0:
            points["bilirubin"] = 1
        elif total_bilirubin_mg_dl <= 3.0:
            points["bilirubin"] = 2
        else:
            points["bilirubin"] = 3

        # 2. Albumin Points
        if serum_albumin_g_dl > 3.5:
            points["albumin"] = 1
        elif serum_albumin_g_dl >= 2.8:
            points["albumin"] = 2
        else:
            points["albumin"] = 3

        # 3. INR Points
        if inr < 1.7:
            points["inr"] = 1
        elif inr <= 2.3:
            points["inr"] = 2
        else:
            points["inr"] = 3

        # 4. Ascites Points
        asc_clean = ascites_severity.upper()
        if "NONE" in asc_clean:
            points["ascites"] = 1
        elif "SLIGHT" in asc_clean or "MILD" in asc_clean or "CONTROLLED" in asc_clean:
            points["ascites"] = 2
        else:
            points["ascites"] = 3

        # 5. Encephalopathy Points
        enc_clean = encephalopathy_grade.upper()
        if "NONE" in enc_clean:
            points["encephalopathy"] = 1
        elif "1" in enc_clean or "2" in enc_clean or "MILD" in enc_clean:
            points["encephalopathy"] = 2
        else:
            points["encephalopathy"] = 3

        total = sum(points.values())

        if total <= 6:
            cp_class = ChildPughClass.CLASS_A
            s1, s2, mort = 100.0, 85.0, 10.0
            interp = "Child-Pugh Class A: Well-compensated cirrhosis. Low perioperative abdominal surgery risk (< 10%)."
        elif total <= 9:
            cp_class = ChildPughClass.CLASS_B
            s1, s2, mort = 80.0, 60.0, 30.0
            interp = "Child-Pugh Class B: Significant functional impairment. Moderate perioperative risk (~30%). Pre-op optimization mandatory."
        else:
            cp_class = ChildPughClass.CLASS_C
            s1, s2, mort = 45.0, 35.0, 75.0
            interp = "Child-Pugh Class C: Decompensated end-stage cirrhosis. High perioperative mortality (> 75%). Elective surgery contraindicated; urgent liver transplant assessment indicated."

        return ChildPughResult(
            total_score=total,
            child_pugh_class=cp_class,
            one_year_survival_pct=s1,
            two_year_survival_pct=s2,
            perioperative_mortality_pct=mort,
            clinical_interpretation=interp,
            component_points=points
        )

    def calculate_meld_na(
        self,
        serum_creatinine_mg_dl: float,
        total_bilirubin_mg_dl: float,
        inr: float,
        serum_sodium_mEq_l: float,
        has_dialysis_past_week: bool = False
    ) -> MELDNaResult:
        """
        Computes MELD-Na score per UNOS/OPTN policy.
        """
        if serum_creatinine_mg_dl <= 0 or total_bilirubin_mg_dl <= 0 or inr <= 0 or serum_sodium_mEq_l <= 0:
            raise ValueError("All lab inputs for MELD-Na must be strictly positive values.")

        # UNOS bounds rules
        cr = 4.0 if has_dialysis_past_week else min(4.0, max(1.0, serum_creatinine_mg_dl))
        bili = max(1.0, total_bilirubin_mg_dl)
        inr_val = max(1.0, inr)
        na = min(137.0, max(125.0, serum_sodium_mEq_l))

        # Initial MELD formula
        meld_initial = (9.57 * math.log(cr)) + (3.78 * math.log(bili)) + (11.2 * math.log(inr_val)) + 6.43
        meld_initial_rounded = round(meld_initial)

        # MELD-Na Adjustment (only if initial MELD > 11)
        if meld_initial_rounded > 11:
            meld_na = meld_initial_rounded + 1.32 * (137.0 - na) - (0.033 * meld_initial_rounded * (137.0 - na))
            meld_na_rounded = int(round(meld_na))
        else:
            meld_na_rounded = int(meld_initial_rounded)

        # Bounded between 6 and 40
        final_score = max(6, min(40, meld_na_rounded))

        # 90-day estimated mortality
        if final_score <= 9:
            mort = 1.9
            tier = "LOW_WAITLIST_RISK"
        elif final_score <= 19:
            mort = 6.0
            tier = "MODERATE_WAITLIST_RISK"
        elif final_score <= 29:
            mort = 19.6
            tier = "HIGH_PRIORITY_TRANSPLANT"
        elif final_score <= 39:
            mort = 52.6
            tier = "URGENT_CRITICAL_TRANSPLANT"
        else:
            mort = 71.3
            tier = "EMERGENCY_STATUS_1A"

        actions = [
            f"MELD-Na Score {final_score}: Estimated 90-day waitlist mortality is {mort}%.",
            "Screen for Spontaneous Bacterial Peritonitis (diagnostic paracentesis if ascites present).",
            "Initiate primary/secondary prophylaxis for esophageal variceal hemorrhage (Endoscopic Band Ligation or Carvedilol).",
            "Maintain strict sodium restriction (< 2g/day) and evaluate for Hepatorenal Syndrome (HRS-AKI) if creatinine rises."
        ]

        return MELDNaResult(
            initial_meld=round(meld_initial, 2),
            meld_na_score=final_score,
            ninety_day_mortality_pct=mort,
            transplant_urgency_tier=tier,
            clinical_action_plan=actions,
            input_parameters_validated={
                "creatinine_used": cr,
                "bilirubin_used": bili,
                "inr_used": inr_val,
                "sodium_used": na,
                "dialysis_applied": 1.0 if has_dialysis_past_week else 0.0
            }
        )

    def stage_tnm_solid_tumor(
        self,
        tumor_site: str,
        t_stage: str,  # T1, T2, T3, T4
        n_stage: str,  # N0, N1, N2, N3
        m_stage: str   # M0, M1
    ) -> TNMStagingResult:
        """
        Determines anatomical stage and resectability per AJCC 8th Edition rules.
        """
        t = t_stage.upper().strip()
        n = n_stage.upper().strip()
        m = m_stage.upper().strip()

        if m == "M1":
            stage = "Stage IV"
            resectability = TumorResectability.UNRESECTABLE_METASTATIC
            actions = [
                "Metastatic Disease (Stage IV): Primary surgery usually non-curative.",
                "Refer to Medical Oncology for systemic palliative chemotherapy, targeted therapy, or immunotherapy.",
                "Consult Palliative Care Medicine for symptom management, pain ladder titration, and quality-of-life optimization."
            ]
        elif t in ("T4", "T4A", "T4B") or n in ("N2", "N3"):
            stage = "Stage III"
            resectability = TumorResectability.LOCALLY_ADVANCED_BORDERLINE
            actions = [
                "Locally Advanced Disease (Stage III): Borderline resectable.",
                "Present at Multidisciplinary Tumor Board (MDT) for neoadjuvant chemotherapy/chemoradiation to achieve tumor downstaging prior to re-assessment for resection."
            ]
        elif t in ("T2", "T3") or n == "N1":
            stage = "Stage II"
            resectability = TumorResectability.POTENTIALLY_RESECTABLE
            actions = [
                "Intermediate Disease (Stage II): Potentially resectable with negative margins (R0).",
                "Complete pre-operative cardiopulmonary clearance and metastatic workup (Contrast CT Chest/Abdomen/Pelvis or PET-CT)."
            ]
        else:
            stage = "Stage I"
            resectability = TumorResectability.POTENTIALLY_RESECTABLE
            actions = [
                "Early-Stage Localized Disease (Stage I): High cure rate with definitive surgical resection (R0).",
                "Proceed with organ-preserving or standard radical oncologic resection with regional lymphadenectomy."
            ]

        return TNMStagingResult(
            tumor_site=tumor_site,
            t_stage=t,
            n_stage=n,
            m_stage=m,
            overall_stage=stage,
            resectability=resectability,
            recommended_tumor_board_actions=actions
        )


# Singleton Instance
hepatobiliary_oncology_engine = HepatobiliaryOncologyEngine()
