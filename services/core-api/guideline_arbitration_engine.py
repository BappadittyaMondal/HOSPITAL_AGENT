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
    NEPHROTIC_SYNDROME_CKD = "NEPHROTIC_SYNDROME_CKD"
    CORONARY_ARTERY_DISEASE_ACS = "CORONARY_ARTERY_DISEASE_ACS"
    SOLID_TUMOR_ONCOLOGY = "SOLID_TUMOR_ONCOLOGY"


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
    Indian medical institutes (AIIMS, CMC Vellore, SSKM) and global centers of excellence
    (Mayo, Cleveland Clinic, Johns Hopkins, NCCN) across 40+ hospital departments.
    """

    DEPARTMENT_DOMAIN_MAP: Dict[str, List[ClinicalDomain]] = {
        "CARDIOLOGY": [ClinicalDomain.HYPERTENSION, ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS],
        "INTERNAL_MEDICINE": [ClinicalDomain.HYPERTENSION, ClinicalDomain.DIABETES_INPATIENT, ClinicalDomain.SEPSIS_RESUSCITATION],
        "INFECTIOUS_DISEASES": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP, ClinicalDomain.SEPSIS_RESUSCITATION],
        "GASTROENTEROLOGY": [ClinicalDomain.H_PYLORI_GASTRITIS],
        "HEPATOLOGY": [ClinicalDomain.H_PYLORI_GASTRITIS],
        "ENDOCRINOLOGY": [ClinicalDomain.DIABETES_INPATIENT],
        "CRITICAL_CARE": [ClinicalDomain.SEPSIS_RESUSCITATION, ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "EMERGENCY_MEDICINE": [ClinicalDomain.SEPSIS_RESUSCITATION, ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS],
        "NEPHROLOGY": [ClinicalDomain.NEPHROTIC_SYNDROME_CKD, ClinicalDomain.HYPERTENSION],
        "MEDICAL_ONCOLOGY": [ClinicalDomain.SOLID_TUMOR_ONCOLOGY],
        "SURGICAL_ONCOLOGY": [ClinicalDomain.SOLID_TUMOR_ONCOLOGY],
        "RADIATION_ONCOLOGY": [ClinicalDomain.SOLID_TUMOR_ONCOLOGY],
        "HEMATOLOGY": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP, ClinicalDomain.SOLID_TUMOR_ONCOLOGY],
        "PEDIATRICS": [ClinicalDomain.NEPHROTIC_SYNDROME_CKD, ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "PEDIATRIC_SURGERY": [ClinicalDomain.SEPSIS_RESUSCITATION, ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "NEONATOLOGY": [ClinicalDomain.SEPSIS_RESUSCITATION, ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "PULMONOLOGY": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP, ClinicalDomain.SEPSIS_RESUSCITATION],
        "NEUROLOGY": [ClinicalDomain.HYPERTENSION],
        "NEUROSURGERY": [ClinicalDomain.SEPSIS_RESUSCITATION, ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "RHEUMATOLOGY": [ClinicalDomain.NEPHROTIC_SYNDROME_CKD],
        "DERMATOLOGY": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "PSYCHIATRY": [ClinicalDomain.DIABETES_INPATIENT, ClinicalDomain.HYPERTENSION],
        "OBSTETRICS": [ClinicalDomain.HYPERTENSION, ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "GYNECOLOGY": [ClinicalDomain.SOLID_TUMOR_ONCOLOGY, ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "GENERAL_SURGERY": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP, ClinicalDomain.SEPSIS_RESUSCITATION],
        "ORTHOPEDICS": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "UROLOGY": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP, ClinicalDomain.NEPHROTIC_SYNDROME_CKD],
        "ENT_OTORHINOLARYNGOLOGY": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "OPHTHALMOLOGY": [ClinicalDomain.DIABETES_INPATIENT, ClinicalDomain.HYPERTENSION],
        "ANESTHESIOLOGY": [ClinicalDomain.SEPSIS_RESUSCITATION],
        "PALLIATIVE_CARE": [ClinicalDomain.SOLID_TUMOR_ONCOLOGY],
        "PHYSICAL_MEDICINE_REHAB": [ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS],
        "GERIATRICS": [ClinicalDomain.HYPERTENSION, ClinicalDomain.DIABETES_INPATIENT],
        "TRANSFUSION_MEDICINE": [ClinicalDomain.SEPSIS_RESUSCITATION],
        "PATHOLOGY": [ClinicalDomain.SOLID_TUMOR_ONCOLOGY],
        "MICROBIOLOGY": [ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP],
        "BIOCHEMISTRY": [ClinicalDomain.DIABETES_INPATIENT, ClinicalDomain.NEPHROTIC_SYNDROME_CKD],
        "RADIO_DIAGNOSIS": [ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS, ClinicalDomain.SOLID_TUMOR_ONCOLOGY],
        "NUCLEAR_MEDICINE": [ClinicalDomain.SOLID_TUMOR_ONCOLOGY, ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS],
        "COMMUNITY_MEDICINE": [ClinicalDomain.HYPERTENSION, ClinicalDomain.DIABETES_INPATIENT]
    }

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

        # ------------------------------------------------------------------------------------------
        # 4. SEPSIS RESUSCITATION & CRITICAL CARE
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.SEPSIS_RESUSCITATION] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.AIIMS_NEW_DELHI,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.SEPSIS_RESUSCITATION,
                diagnostic_criteria={
                    "qsofa_screening": True,
                    "blood_lactate_stat": True,
                    "blood_cultures_x2_prior_to_abx": True
                },
                first_line_therapy=[
                    "Isotonic balanced crystalloid (Ringer's Lactate) titrated at 30 mL/kg within initial 3 hours",
                    "Norepinephrine infusion (0.05-0.5 mcg/kg/min) titrated to MAP >= 65 mmHg",
                    "Empiric Piperacillin-Tazobactam 4.5g IV q6h (or Cefoperazone-Sulbactam 3g IV q12h) within 1 hour of recognition"
                ],
                nlem_generic_molecules=["Ringer's Lactate", "Norepinephrine", "Piperacillin-Tazobactam", "Cefoperazone-Sulbactam"],
                estimated_daily_cost_inr=420.00,
                evidence_grade="AIIMS_CRITICAL_CARE_PROTOCOL",
                clinical_rationale="AIIMS New Delhi & ICMR STW sepsis protocols mandate rapid crystalloid resuscitation and early norepinephrine while guarding against aggressive over-resuscitation in ward settings with limited mechanical ventilators.",
                citations=["AIIMS Protocol in Emergency Medicine & Critical Care", "ICMR Standard Treatment Workflow: Sepsis & Septic Shock 2023"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.JOHNS_HOPKINS_MEDICINE,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.SEPSIS_RESUSCITATION,
                diagnostic_criteria={
                    "dynamic_measures_fluid_responsiveness": "Echocardiographic VTI / Passive Leg Raise",
                    "continuous_arterial_line_monitoring": True,
                    "serial_lactate_clearance_target_pct": 20.0
                },
                first_line_therapy=[
                    "Dynamic guided fluid titration with buffered crystalloids",
                    "Norepinephrine + Early low-dose Vasopressin (0.03 units/min fixed)",
                    "Vancomycin 15-20mg/kg IV q12h + Cefepime 2g IV q8h + Stress-dose IV Hydrocortisone 200mg/day"
                ],
                nlem_generic_molecules=["Norepinephrine", "Vasopressin", "Vancomycin", "Cefepime", "Hydrocortisone"],
                estimated_daily_cost_inr=3850.00,
                evidence_grade="SURVIVING_SEPSIS_CAMPAIGN_1A",
                clinical_rationale="Johns Hopkins Medicine & Surviving Sepsis Campaign emphasize multimodal advanced hemodynamic profiling, early vasopressin initiation, and empiric MRSA/pseudomonal dual coverage.",
                citations=["Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2021"]
            )
        }

        # ------------------------------------------------------------------------------------------
        # 5. INPATIENT DIABETES MELLITUS
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.DIABETES_INPATIENT] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.AIIMS_NEW_DELHI,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.DIABETES_INPATIENT,
                diagnostic_criteria={
                    "target_blood_glucose_mg_dl": "140 - 180 mg/dL (7.8 - 10.0 mmol/L)",
                    "sliding_scale_monotherapy_prohibited": True,
                    "oral_hypoglycemics_withheld": True
                },
                first_line_therapy=[
                    "Regular Human Insulin (Soluble) pre-meals + NPH/Isophane Human Insulin at bedtime (Basal-Bolus)",
                    "Withhold oral hypoglycemics (Metformin, SGLT2i, Sulfonylureas) during acute hospitalization",
                    "Correction scale: Regular Human Insulin for blood glucose > 180 mg/dL"
                ],
                nlem_generic_molecules=["Human Regular Insulin", "Human NPH Insulin"],
                estimated_daily_cost_inr=35.00,
                evidence_grade="RSSDI_AIIMS_CONSENSUS",
                clinical_rationale="AIIMS & RSSDI protocols prioritize cost-effective human insulins available under Jan Aushadhi / NLEM, avoiding high-cost proprietary analogs while maintaining excellent inpatient safety.",
                citations=["RSSDI Clinical Practice Recommendations for Management of Type 2 Diabetes Mellitus 2022", "AIIMS Endocrinology Inpatient Protocol"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.MAYO_CLINIC,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.DIABETES_INPATIENT,
                diagnostic_criteria={
                    "continuous_glucose_monitoring_cgm": True,
                    "target_blood_glucose_mg_dl": "140 - 180 mg/dL (general) or 110 - 140 mg/dL (selected ICU)",
                    "automated_insulin_titration_algorithm": True
                },
                first_line_therapy=[
                    "Long-acting insulin analog (Insulin Degludec or Glargine U-300) once daily",
                    "Rapid-acting insulin analog (Insulin Aspart or Lispro) pre-meals with automated dose calculator",
                    "Bedside telemetry via Continuous Glucose Monitoring sensor"
                ],
                nlem_generic_molecules=["Insulin Glargine", "Insulin Aspart"],
                estimated_daily_cost_inr=380.00,
                evidence_grade="ADA_STANDARDS_OF_CARE_LEVEL_A",
                clinical_rationale="Mayo Clinic & ADA Standards of Care recommend modern basal-bolus insulin analogs and continuous CGM monitoring to minimize glycemic variability and nocturnal hypoglycemia risk.",
                citations=["American Diabetes Association Standards of Care in Hospitalized Patients 2024"]
            )
        }

        # ------------------------------------------------------------------------------------------
        # 6. NEPHROTIC SYNDROME & CHRONIC KIDNEY DISEASE
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.NEPHROTIC_SYNDROME_CKD] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.CMC_VELLORE,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.NEPHROTIC_SYNDROME_CKD,
                diagnostic_criteria={
                    "proteinuria_threshold_g_day": 3.5,
                    "hypoalbuminemia_g_dl": 3.0,
                    "endemic_parasite_screening": "Mandatory prior to high-dose steroid therapy"
                },
                first_line_therapy=[
                    "Tab. Prednisolone 1 mg/kg/day (single morning dose, max 60mg)",
                    "Prophylactic Tab. Albendazole 400mg PO daily x 3 days (preempts fatal Strongyloides hyperinfection)",
                    "Dietary sodium restriction (< 2g/day) + Tab. Calcium Carbonate 500mg + Vit D3"
                ],
                nlem_generic_molecules=["Prednisolone", "Albendazole", "Calcium Carbonate", "Vitamin D3"],
                estimated_daily_cost_inr=16.50,
                evidence_grade="ISN_INDIAN_CONSENSUS",
                clinical_rationale="CMC Vellore Nephrology protocols mandate prophylactic tropical deworming with Albendazole prior to high-dose immunosuppression and utilize low-cost NLEM generic Prednisolone.",
                citations=["CMC Vellore Department of Nephrology Protocol", "Indian Society of Nephrology Guidelines on Glomerular Diseases"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.MAYO_CLINIC,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.NEPHROTIC_SYNDROME_CKD,
                diagnostic_criteria={
                    "anti_pla2r_biomarker_titration": True,
                    "renal_biopsy_electron_microscopy": True
                },
                first_line_therapy=[
                    "Anti-PLA2R biomarker-guided immunotherapy",
                    "IV Rituximab 375 mg/m2 weekly x 4 doses (or 1000mg x 2 doses) for B-cell depletion",
                    "SGLT2 inhibitor (Dapagliflozin 10mg daily) for chronic glomerular nephroprotection"
                ],
                nlem_generic_molecules=["Prednisolone", "Rituximab", "Dapagliflozin"],
                estimated_daily_cost_inr=1450.00,
                evidence_grade="KDIGO_LEVEL_1A",
                clinical_rationale="Mayo Clinic / KDIGO protocols prioritize targeted B-cell depletion with monoclonal antibody Rituximab to spare steroid toxicity and protect long-term eGFR.",
                citations=["KDIGO Clinical Practice Guideline for the Management of Glomerular Diseases 2021"]
            )
        }

        # ------------------------------------------------------------------------------------------
        # 7. CORONARY ARTERY DISEASE & ACUTE CORONARY SYNDROMES
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.AIIMS_NEW_DELHI,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS,
                diagnostic_criteria={
                    "ecg_door_to_eval_min": 10,
                    "troponin_i_t_stat": True,
                    "pharmaco_invasive_transit_threshold_min": 120
                },
                first_line_therapy=[
                    "STAT Loading: Tab. Aspirin 300mg + Tab. Clopidogrel 300mg + Tab. Atorvastatin 80mg",
                    "Primary PCI within 90 min (if available) or Thrombolysis with Tenecteplase if transit > 120 min",
                    "Maintenance: Aspirin 75mg daily + Clopidogrel 75mg daily + Atorvastatin 40mg daily"
                ],
                nlem_generic_molecules=["Aspirin", "Clopidogrel", "Atorvastatin", "Tenecteplase"],
                estimated_daily_cost_inr=18.00,
                evidence_grade="CSI_AIIMS_ACS_GUIDELINE",
                clinical_rationale="AIIMS Cardiology & Cardiological Society of India (CSI) protocols prioritize dual antiplatelet therapy with affordable Clopidogrel and pharmaco-invasive thrombolytic pathways for resource-constrained transit.",
                citations=["Cardiological Society of India Guidelines for Management of Acute Myocardial Infarction", "AIIMS Cardiology Protocol"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.CLEVELAND_CLINIC,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS,
                diagnostic_criteria={
                    "high_sensitivity_troponin_0_1h_algorithm": True,
                    "immediate_cath_lab_activation": True
                },
                first_line_therapy=[
                    "STAT Loading: Aspirin 324mg + Ticagrelor 180mg (or Prasugrel 60mg) + Rosuvastatin 40mg",
                    "Immediate primary PCI with drug-eluting stent (DES)",
                    "PCSK9 inhibitor (Evolocumab 140mg SC) within 24h if baseline LDL > 150 mg/dL"
                ],
                nlem_generic_molecules=["Aspirin", "Ticagrelor", "Rosuvastatin"],
                estimated_daily_cost_inr=520.00,
                evidence_grade="ACC_AHA_CLASS_1A",
                clinical_rationale="Cleveland Clinic & AHA/ACC guidelines prioritize potent P2Y12 receptor antagonists (Ticagrelor/Prasugrel) with rapid onset and early PCSK9 monoclonal antibody lipid lowering.",
                citations=["2023 AHA/ACC Guideline for the Management of Patients With Chronic Coronary Disease"]
            )
        }

        # ------------------------------------------------------------------------------------------
        # 8. SOLID TUMOR ONCOLOGY (GASTROINTESTINAL & BREAST)
        # ------------------------------------------------------------------------------------------
        catalog[ClinicalDomain.SOLID_TUMOR_ONCOLOGY] = {
            JurisdictionContext.INDIAN_NATIONAL_TERTIARY: GuidelineRecommendation(
                institution=InstitutionSource.IPGMER_SSKM_KOLKATA,
                jurisdiction=JurisdictionContext.INDIAN_NATIONAL_TERTIARY,
                domain=ClinicalDomain.SOLID_TUMOR_ONCOLOGY,
                diagnostic_criteria={
                    "histopathological_biopsy_confirmation": True,
                    "ihc_receptor_status": "ER, PR, HER2, Ki-67 for Breast; MMR/MSI for Colorectal",
                    "mdt_tumor_board_review": True
                },
                first_line_therapy=[
                    "Multidisciplinary Tumor Board curative-intent systemic chemotherapy",
                    "FOLFOX (5-FU + Leucovorin + Oxaliplatin) or AC-T (Doxorubicin + Cyclophosphamide + Paclitaxel)",
                    "Trastuzumab domestic biosimilar if HER2 3+ overexpression (subsidized via PM-JAY)"
                ],
                nlem_generic_molecules=["Fluorouracil", "Oxaliplatin", "Paclitaxel", "Doxorubicin", "Cyclophosphamide"],
                estimated_daily_cost_inr=750.00,
                evidence_grade="TATA_MEMORIAL_EVIDENCE_BASED_GUIDELINE",
                clinical_rationale="IPGMER / SSKM and Tata Memorial Centre protocols prioritize curative-intent NLEM generic chemotherapy backbones and domestic biosimilars within public PM-JAY package ceilings.",
                citations=["Tata Memorial Centre Evidence-Based Management Guidelines in Oncology", "IPGMER Oncology Protocols"]
            ),
            JurisdictionContext.INTERNATIONAL_BENCHMARK: GuidelineRecommendation(
                institution=InstitutionSource.NCCN_ONCOLOGY,
                jurisdiction=JurisdictionContext.INTERNATIONAL_BENCHMARK,
                domain=ClinicalDomain.SOLID_TUMOR_ONCOLOGY,
                diagnostic_criteria={
                    "next_generation_sequencing_ngs_panel": "Comprehensive 500+ gene tumor profiling",
                    "circulating_tumor_dna_ctdna_monitoring": True
                },
                first_line_therapy=[
                    "Comprehensive Genomic Profiling (CGP Next-Gen Sequencing)",
                    "Targeted Antibody-Drug Conjugate (e.g. Trastuzumab Deruxtecan) or Immune Checkpoint Inhibitor (Pembrolizumab 200mg IV q3w)",
                    "Precision molecular tumor board guided clinical trial enrollment"
                ],
                nlem_generic_molecules=["Fluorouracil", "Oxaliplatin"],
                estimated_daily_cost_inr=11200.00,
                evidence_grade="NCCN_CATEGORY_1",
                clinical_rationale="NCCN & MSKCC guidelines prioritize comprehensive genomic profiling, novel antibody-drug conjugates, and checkpoint immunotherapy for precision oncology care.",
                citations=["NCCN Clinical Practice Guidelines in Oncology (NCCN Guidelines)"]
            )
        }

        return catalog

    def get_domains_for_department(self, department: str) -> List[ClinicalDomain]:
        dept_clean = department.upper().replace(" ", "_").replace("-", "_")
        return self.DEPARTMENT_DOMAIN_MAP.get(dept_clean, [ClinicalDomain.HYPERTENSION])

    def list_supported_domains(self) -> List[str]:
        return [d.value for d in self._guidelines.keys()]

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
