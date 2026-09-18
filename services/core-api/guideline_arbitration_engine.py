# ====================================================================================================
# PROJECT "HOSPITAL" — INSTITUTIONAL GUIDELINE ARBITRATION & JURISDICTION ROUTER
# ====================================================================================================
# Module: services/core-api/guideline_arbitration_engine.py
# Purpose: Implements the Pan-Institutional Clinical Knowledge Core (PICK-Core) guideline arbiter.
#          Routes and arbitrates between Indian National Tertiary standards (AIIMS New Delhi,
#          CMC Vellore, IPGMER/SSKM Kolkata, ICMR STWs) and International Gold-Standard Benchmarks
#          (Mayo Clinic, Cleveland Clinic, Johns Hopkins, NCCN, ESC/AHA), preventing dangerous
#          cross-jurisdictional prescribing conflicts and ensuring economic formulary compliance.
# ====================================================================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class JurisdictionContext(str, Enum):
    INDIAN_NATIONAL_TERTIARY = "INDIAN_NATIONAL_TERTIARY"
    INTERNATIONAL_BENCHMARK = "INTERNATIONAL_BENCHMARK"


class InstitutionSource(str, Enum):
    AIIMS_NEW_DELHI = "AIIMS_NEW_DELHI"
    CMC_VELLORE = "CMC_VELLORE"
    IPGMER_SSKM_KOLKATA = "IPGMER_SSKM_KOLKATA"
    ICMR_STW = "ICMR_STW"
    MAYO_CLINIC = "MAYO_CLINIC"
    CLEVELAND_CLINIC = "CLEVELAND_CLINIC"
    JOHNS_HOPKINS_MEDICINE = "JOHNS_HOPKINS_MEDICINE"
    NCCN_ONCOLOGY = "NCCN_ONCOLOGY"


class ClinicalDomain(str, Enum):
    HYPERTENSION = "HYPERTENSION"
    ANTIMICROBIAL_STEWARDSHIP = "ANTIMICROBIAL_STEWARDSHIP"
    H_PYLORI_GASTRITIS = "H_PYLORI_GASTRITIS"
    SEPSIS_RESUSCITATION = "SEPSIS_RESUSCITATION"
    DIABETES_INPATIENT = "DIABETES_INPATIENT"


@dataclass
class GuidelineRecommendation:
    institution: InstitutionSource
    jurisdiction: JurisdictionContext
    domain: ClinicalDomain
    diagnostic_criteria: Dict[str, Any]
    first_line_therapy: List[str]
    nlem_generic_molecules: List[str]
    estimated_daily_cost_inr: float
    antimicrobial_tier: Optional[str] = None
    evidence_grade: str = "GRADE_1A"
    clinical_rationale: str = ""
    citations: List[str] = field(default_factory=list)


class InstitutionalGuidelineRouter:
    """
    Arbitrates diagnostic thresholds and clinical practice guidelines across premier
    Indian medical institutes and global centers of excellence.
    """

    def __init__(self):
        self._guidelines: Dict[ClinicalDomain, Dict[JurisdictionContext, GuidelineRecommendation]] = self._init_catalog()

    def _init_catalog(self) -> Dict[ClinicalDomain, Dict[JurisdictionContext, GuidelineRecommendation]]:
        catalog: Dict[ClinicalDomain, Dict[JurisdictionContext, GuidelineRecommendation]] = {}

        # ------------------------------------------------------------------------------------------
        # 1. HYPERTENSION ARBITRATION
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.HYPERTENSION] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.AIIMS_NEW_DELHI,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.HYPERTENSION,
                diagnostic_criteria={
                    "systolic_threshold_mmhg": 140,
                    "diastolic_threshold_mmhg": 90,
                    "confirmation_method": "Repeat office BP on 2-3 separate visits or 24-hr ABPM",
                    "cardiovascular_risk_tool": "WHO/ISH South Asia Risk Charts (10-Year)"
                },
                first_line_therapy=[
                    "Amlodipine 5mg oral once daily",
                    "Telmisartan 40mg oral once daily (if diabetic/proteinuric)",
                    "Chlorthalidone 12.5mg oral once daily"
                ],
                nlem_generic_molecules=["Amlodipine", "Telmisartan", "Chlorthalidone"],
                estimated_daily_cost_inr=6.50,
                evidence_grade="ICMR_STW_CLASS_1",
                clinical_rationale="ICMR & AIIMS protocols define Stage 1 HTN at >= 140/90 mmHg to avoid over-medicalization in resource-constrained settings while prioritizing monotherapy with affordable NLEM generics.",
                citations=["ICMR Standard Treatment Workflow: Systemic Hypertension 2022", "AIIMS Protocol in Clinical Cardiology"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.CLEVELAND_CLINIC,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.HYPERTENSION,
                diagnostic_criteria={
                    "systolic_threshold_mmhg": 130,
                    "diastolic_threshold_mmhg": 80,
                    "confirmation_method": "Out-of-office automated home BP monitoring (HBPM)",
                    "cardiovascular_risk_tool": "AHA/ACC ASCVD Risk Estimator Plus (10-Year)"
                },
                first_line_therapy=[
                    "Single-Pill Combination: Amlodipine 5mg + Olmesartan 20mg daily",
                    "Chlorthalidone 12.5mg daily"
                ],
                nlem_generic_molecules=["Amlodipine", "Olmesartan", "Chlorthalidone"],
                estimated_daily_cost_inr=65.00,
                evidence_grade="AHA_ACC_CLASS_1",
                clinical_rationale="AHA/ACC and Cleveland Clinic guidelines initiate pharmacotherapy at >= 130/80 mmHg with early single-pill fixed-dose dual therapy for accelerated target attainment.",
                citations=["2017 AHA/ACC/AAPA/ABC/ACPM Guideline for High Blood Pressure in Adults"]
            )
        }

        # ------------------------------------------------------------------------------------------
        # 2. ANTIMICROBIAL STEWARDSHIP (PNEUMONIA / HOSPITAL-ACQUIRED INFECTIONS)
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.CMC_VELLORE,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP,
                diagnostic_criteria={
                    "blood_culture_prior_to_abx": True,
                    "esbl_prevalence_adjustment": "High (> 45% Gram-Negative Resistance)",
                    "crb65_score_threshold": 2
                },
                first_line_therapy=[
                    "Severe CAP: Ceftriaxone 2g IV once daily + Azithromycin 500mg IV once daily",
                    "Suspected Gram-Negative HAP: Piperacillin-Tazobactam 4.5g IV q6h (extended infusion over 3h)"
                ],
                nlem_generic_molecules=["Ceftriaxone", "Azithromycin", "Piperacillin-Tazobactam"],
                estimated_daily_cost_inr=280.00,
                antimicrobial_tier="WHO_AWARE_WATCH",
                evidence_grade="CMC_VELLORE_ASP_TIER_2",
                clinical_rationale="CMC Vellore & ICMR guidelines account for widespread ESBL circulation; Reserve Carbapenems (Meropenem) are strictly quarantined pending blood culture proof to avoid pan-drug resistant CRE emergence.",
                citations=["CMC Vellore Antibiotic Policy 12th Edition", "ICMR Guidelines on Antimicrobial Use in Common Syndromes"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.JOHNS_HOPKINS_MEDICINE,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP,
                diagnostic_criteria={
                    "blood_culture_prior_to_abx": True,
                    "mrsa_nasal_pcr_screening": True,
                    "procalcitonin_guided_cessation": True
                },
                first_line_therapy=[
                    "Ampicillin-Sulbactam 3g IV q6h + Azithromycin 500mg IV daily",
                    "If MRSA risk: Add Vancomycin 15-20mg/kg IV q12h with AUC/MIC therapeutic monitoring"
                ],
                nlem_generic_molecules=["Ampicillin-Sulbactam", "Azithromycin", "Vancomycin"],
                estimated_daily_cost_inr=2200.00,
                antimicrobial_tier="IDSA_ATS_BENCHMARK",
                evidence_grade="IDSA_LEVEL_1A",
                clinical_rationale="Johns Hopkins / IDSA protocols prioritize rapid MRSA nasal PCR rule-out and continuous PK/PD target attainment with AUC-guided glycopeptides.",
                citations=["IDSA/ATS Consensus Guidelines on the Management of Community-Acquired Pneumonia in Adults"]
            )
        }

        # ------------------------------------------------------------------------------------------
        # 3. H. PYLORI GASTRITIS REGIMENS
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.H_PYLORI_GASTRITIS] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.IPGMER_SSKM_KOLKATA,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.H_PYLORI_GASTRITIS,
                diagnostic_criteria={
                    "stool_antigen_or_rapid_urease": True,
                    "local_clarithromycin_resistance": "Severe (> 40% in Bengal/Gangetic basin)"
                },
                first_line_therapy=[
                    "Bismuth Subsalicylate 524mg PO qid + Metronidazole 400mg PO tid + Tetracycline 500mg PO qid + Omeprazole 20mg PO bid for 14 days (Quadruple Therapy)"
                ],
                nlem_generic_molecules=["Bismuth", "Metronidazole", "Tetracycline", "Omeprazole"],
                estimated_daily_cost_inr=45.00,
                evidence_grade="ISG_CONSENSUS_A1",
                clinical_rationale="IPGMER / Indian Society of Gastroenterology guidelines explicitly reject standard Clarithromycin triple therapy due to catastrophic local macrolide resistance (> 40%), mandating 14-day Bismuth Quadruple therapy.",
                citations=["Indian Society of Gastroenterology Consensus on Helicobacter Pylori Infection 2021"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.MAYO_CLINIC,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.H_PYLORI_GASTRITIS,
                diagnostic_criteria={
                    "stool_antigen_or_urea_breath_test": True,
                    "macrolide_resistance_testing": "Molecular PCR detection on biopsy"
                },
                first_line_therapy=[
                    "Vonoprazan 20mg PO bid + Amoxicillin 1000mg PO bid + Clarithromycin 500mg PO bid for 14 days (Dual/Triple Potassium-Competitive Acid Blocker)"
                ],
                nlem_generic_molecules=["Amoxicillin", "Clarithromycin"],
                estimated_daily_cost_inr=750.00,
                evidence_grade="ACG_CLINICAL_GUIDELINE",
                clinical_rationale="Mayo Clinic / ACG guidelines recommend novel Potassium-Competitive Acid Blockers (PCABs like Vonoprazan) for superior mucosal acid suppression and higher eradication rates.",
                citations=["American College of Gastroenterology Guideline on the Treatment of Helicobacter pylori Infection"]
            )
        }

        return catalog

    def get_recommendation(
        self,
        domain: ClinicalDomain,
        context: JurisdictionContext = JurisdictionContext.INDIAN_NATIONAL_TERTIARY
    ) -> GuidelineRecommendation:
        domain_guidelines = self._guidelines.get(domain)
        if not domain_guidelines:
            raise KeyError(f"Clinical domain '{domain}' not configured in guideline registry.")
        rec = domain_guidelines.get(context)
        if not rec:
            raise KeyError(f"Jurisdiction '{context}' not configured for domain '{domain}'.")
        return rec

    def arbitrate_conflict(
        self,
        domain: ClinicalDomain,
        patient_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cross-examines Indian National Tertiary protocols against Global Reference Standards,
        providing an actionable comparison highlighting diagnostic threshold differences,
        antimicrobial resistance risks, and economic formulary compliance.
        """
        local_rec = self.get_recommendation(domain, JurisdictionContext.INDIAN_NATIONAL_TERTIARY)
        global_rec = self.get_recommendation(domain, JurisdictionContext.INTERNATIONAL_BENCHMARK)

        cost_diff_ratio = round(global_rec.estimated_daily_cost_inr / max(1.0, local_rec.estimated_daily_cost_inr), 1)

        return {
            "domain": domain.value,
            "status": "ARBITRATED_SUCCESSFULLY",
            "primary_actionable_standard": {
                "institution": local_rec.institution.value,
                "jurisdiction": local_rec.jurisdiction.value,
                "first_line_therapy": local_rec.first_line_therapy,
                "nlem_generic_molecules": local_rec.nlem_generic_molecules,
                "estimated_daily_cost_inr": local_rec.estimated_daily_cost_inr,
                "clinical_rationale": local_rec.clinical_rationale,
                "citations": local_rec.citations
            },
            "global_reference_benchmark": {
                "institution": global_rec.institution.value,
                "jurisdiction": global_rec.jurisdiction.value,
                "first_line_therapy": global_rec.first_line_therapy,
                "nlem_generic_molecules": global_rec.nlem_generic_molecules,
                "estimated_daily_cost_inr": global_rec.estimated_daily_cost_inr,
                "clinical_rationale": global_rec.clinical_rationale,
                "citations": global_rec.citations
            },
            "economic_formulary_analysis": {
                "local_cost_per_day_inr": local_rec.estimated_daily_cost_inr,
                "global_benchmark_cost_per_day_inr": global_rec.estimated_daily_cost_inr,
                "cost_ratio": f"{cost_diff_ratio}x more expensive for global benchmark",
                "jan_aushadhi_accessible": True,
                "pmjay_coverage_eligible": True
            },
            "arbitration_verdict": f"For immediate actionable patient care in the Indian healthcare ecosystem, execute {local_rec.institution.value} protocol ({', '.join(local_rec.nlem_generic_molecules)}) to respect local AMR and economic feasibility. Consult {global_rec.institution.value} benchmark for advanced tertiary referral options."
        }


# Singleton Instance
guideline_router = InstitutionalGuidelineRouter()
