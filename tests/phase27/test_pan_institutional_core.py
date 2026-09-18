#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 27: PAN-INSTITUTIONAL CLINICAL KNOWLEDGE CORE (PICK-CORE)
Module: tests/phase27/test_pan_institutional_core.py
Validates:
  1. Multi-tenant jurisdictional routing (AIIMS/CMC/SSKM vs Mayo/Hopkins).
  2. Tropical fever syndromic scoring (Dengue warning signs & Scrub Typhus eschar).
  3. Hepatobiliary scoring (Child-Pugh Class & MELD-Na exact UNOS formula).
  4. AJCC 8th Edition TNM solid tumor staging.
  5. Rare disease phenotype matching (Wilson's disease & Punctate PPK via HPO).
  6. DualLensPresentationAgent local actionable vs global benchmark formatting.
  7. API route integration under zero-trust authentication.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
import main
from guideline_arbitration_engine import guideline_router, ClinicalDomain, JurisdictionContext, InstitutionSource
from tropical_syndromic_engine import tropical_syndromic_engine, TropicalInfectionType
from hepatobiliary_oncology_engine import hepatobiliary_oncology_engine, ChildPughClass, TumorResectability
from rare_disease_engine import rare_disease_engine
from dual_lens_presenter import dual_lens_presenter
from auth_manager import auth_security_manager
from cpoe_dre_engine import CPOEDREEngine


class TestPanInstitutionalCore(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)
        self.valid_token = auth_security_manager.create_access_token(
            username="dr_chatterjee",
            tenant_id="TENANT-MAIN-01",
            role="CONSULTANT_PHYSICIAN",
            permissions=["order_medications", "view_clinical_chart"]
        )
        self.auth_headers = {
            "Authorization": f"Bearer {self.valid_token}",
            "X-Tenant-ID": "TENANT-MAIN-01"
        }

    def test_hypertension_arbitration_aiims_vs_cleveland_clinic(self):
        """Verify hypertension arbitration identifies AIIMS 140/90 vs Cleveland Clinic 130/80."""
        res = guideline_router.arbitrate_conflict(ClinicalDomain.HYPERTENSION)
        self.assertEqual(res["status"], "ARBITRATED_SUCCESSFULLY")

        # Local standard (AIIMS New Delhi)
        local_std = res["primary_actionable_standard"]
        self.assertEqual(local_std["institution"], InstitutionSource.AIIMS_NEW_DELHI.value)
        self.assertIn("Amlodipine", local_std["nlem_generic_molecules"])
        self.assertIn("Telmisartan", local_std["nlem_generic_molecules"])
        self.assertLess(local_std["estimated_daily_cost_inr"], 20.0)

        # Global benchmark (Cleveland Clinic)
        global_bench = res["global_reference_benchmark"]
        self.assertEqual(global_bench["institution"], InstitutionSource.CLEVELAND_CLINIC.value)
        self.assertGreater(global_bench["estimated_daily_cost_inr"], local_std["estimated_daily_cost_inr"])

    def test_antimicrobial_stewardship_cmc_vellore_vs_johns_hopkins(self):
        """Verify antimicrobial stewardship balances CMC Vellore ESBL awareness with Hopkins MRSA."""
        res = guideline_router.arbitrate_conflict(ClinicalDomain.ANTIMICROBIAL_STEWARDSHIP)
        local_std = res["primary_actionable_standard"]
        self.assertEqual(local_std["institution"], InstitutionSource.CMC_VELLORE.value)
        self.assertIn("Piperacillin-Tazobactam", local_std["nlem_generic_molecules"])

        global_bench = res["global_reference_benchmark"]
        self.assertEqual(global_bench["institution"], InstitutionSource.JOHNS_HOPKINS_MEDICINE.value)
        self.assertIn("Vancomycin", global_bench["nlem_generic_molecules"])

    def test_tropical_fever_dengue_warning_signs_and_plasma_leak(self):
        """Verify Dengue evaluation triggers plasma leakage warning and fluid titration protocol."""
        assessment = tropical_syndromic_engine.evaluate_fever(
            patient_age=28,
            days_of_fever=4,
            platelet_count=35000,
            hematocrit_pct=48.0,
            baseline_hematocrit_pct=40.0,  # 20% hemoconcentration
            systolic_bp=95,
            pulse_rate=105,
            symptoms=["persistent vomiting", "severe abdominal pain", "retro-orbital headache"],
            physical_signs=["petechiae", "ascites"]
        )
        self.assertIn(assessment.primary_suspect, [TropicalInfectionType.DENGUE_WITH_WARNING_SIGNS, TropicalInfectionType.SEVERE_DENGUE_SHOCK])
        self.assertTrue(len(assessment.warning_signs_detected) >= 2)
        actions_str = " ".join(assessment.immediate_holding_protocol)
        self.assertIn("CRYSTALLOIDS", actions_str)
        self.assertIn("AVOID PROPHYLACTIC PLATELET", actions_str)

        contra_str = " ".join(assessment.contraindicated_interventions)
        self.assertIn("DO NOT ADMINISTER NSAIDs", contra_str)

    def test_tropical_fever_scrub_typhus_with_eschar(self):
        """Verify pathognomonic eschar triggers Scrub Typhus diagnosis with Doxycycline."""
        assessment = tropical_syndromic_engine.evaluate_fever(
            patient_age=35,
            days_of_fever=6,
            platelet_count=65000,
            symptoms=["breathlessness", "cough", "high fever"],
            physical_signs=["cigarette-burn eschar in left axilla", "lymphadenopathy"]
        )
        self.assertEqual(assessment.primary_suspect, TropicalInfectionType.SCRUB_TYPHUS_WITH_ARDS_RISK)
        actions_str = " ".join(assessment.immediate_holding_protocol)
        self.assertIn("DOXYCYCLINE", actions_str)

    def test_hepatobiliary_child_pugh_exact_class_c(self):
        """Verify Child-Pugh scoring correctly computes Class C decompensated cirrhosis."""
        # Bilirubin 3.5 (>3 -> 3pts), Albumin 2.5 (<2.8 -> 3pts), INR 2.4 (>2.3 -> 3pts), Ascites moderate (3pts), Encephalopathy Grade 2 (2pts)
        # Total = 3 + 3 + 3 + 3 + 2 = 14 points -> Class C
        res = hepatobiliary_oncology_engine.calculate_child_pugh(
            total_bilirubin_mg_dl=3.5,
            serum_albumin_g_dl=2.5,
            inr=2.4,
            ascites_severity="MODERATE_OR_SEVERE",
            encephalopathy_grade="GRADE_1_2"
        )
        self.assertEqual(res.total_score, 14)
        self.assertEqual(res.child_pugh_class, ChildPughClass.CLASS_C)
        self.assertGreater(res.perioperative_mortality_pct, 50.0)

    def test_hepatobiliary_meld_na_unos_formula_calculation(self):
        """Verify MELD-Na score matches official OPTN/UNOS double-precision mathematical bounds."""
        # Creatinine 2.5, Bilirubin 3.2, INR 1.9, Sodium 128 (hyponatremic cirrhosis)
        res = hepatobiliary_oncology_engine.calculate_meld_na(
            serum_creatinine_mg_dl=2.5,
            total_bilirubin_mg_dl=3.2,
            inr=1.9,
            serum_sodium_mEq_l=128.0,
            has_dialysis_past_week=False
        )
        self.assertGreater(res.initial_meld, 15.0)
        self.assertGreater(res.meld_na_score, int(res.initial_meld))  # Na < 137 increases score
        self.assertIn(res.transplant_urgency_tier, ["HIGH_PRIORITY_TRANSPLANT", "URGENT_CRITICAL_TRANSPLANT"])

    def test_ajcc_tnm_oncology_staging(self):
        """Verify AJCC 8th Edition staging separates localized resectable from metastatic."""
        # Stage I
        s1 = hepatobiliary_oncology_engine.stage_tnm_solid_tumor("Colorectal", "T1", "N0", "M0")
        self.assertEqual(s1.overall_stage, "Stage I")
        self.assertEqual(s1.resectability, TumorResectability.POTENTIALLY_RESECTABLE)

        # Stage IV
        s4 = hepatobiliary_oncology_engine.stage_tnm_solid_tumor("Pancreatic", "T3", "N1", "M1")
        self.assertEqual(s4.overall_stage, "Stage IV")
        self.assertEqual(s4.resectability, TumorResectability.UNRESECTABLE_METASTATIC)

    def test_rare_disease_hpo_phenotype_matching_wilson_and_ppk(self):
        """Verify rare disease engine matches HPO clusters to Wilson's disease and Punctate PPK."""
        # 1. Wilson's disease match
        w_res = rare_disease_engine.match_phenotypes(
            phenotype_hpo_terms=["HP:0001392", "HP:0001337", "HP:0001402"],
            clinical_keywords=["copper", "kayser-fleischer"]
        )
        self.assertTrue(len(w_res.top_candidate_diseases) > 0)
        self.assertEqual(w_res.top_candidate_diseases[0]["orpha_code"], "ORPHA:905")
        self.assertIn("Ceruloplasmin", " ".join(w_res.top_candidate_diseases[0]["mandatory_confirmatory_tests"]))

        # 2. Punctate PPK match
        p_res = rare_disease_engine.match_phenotypes(
            phenotype_hpo_terms=["HP:0000988", "HP:0001000"],
            clinical_keywords=["palmoplantar", "keratoderma", "corn-like"]
        )
        self.assertTrue(len(p_res.top_candidate_diseases) > 0)
        self.assertEqual(p_res.top_candidate_diseases[0]["orpha_code"], "ORPHA:49641")

    def test_pan_institutional_api_endpoints_via_fastapi(self):
        """Verify REST endpoints for PICK-Core engines execute cleanly with HTTP 200."""
        # 1. Arbitrate endpoint
        arb_res = self.client.post(
            "/api/v1/clinical/pan-institutional/arbitrate",
            json={"domain": "HYPERTENSION"},
            headers=self.auth_headers
        )
        self.assertEqual(arb_res.status_code, 200)
        arb_data = arb_res.json()
        self.assertIn("primary_actionable_standard", arb_data["arbitration_result"])
        self.assertIn("dual_lens_report", arb_data)

        # 2. Tropical fever endpoint
        trop_res = self.client.post(
            "/api/v1/clinical/tropical/score",
            json={
                "patient_age": 45,
                "days_of_fever": 5,
                "platelet_count": 42000,
                "hematocrit_pct": 42.0,
                "baseline_hematocrit_pct": 38.0,
                "symptoms": ["vomiting", "abdominal pain"],
                "physical_signs": ["petechiae"]
            },
            headers=self.auth_headers
        )
        self.assertEqual(trop_res.status_code, 200)
        self.assertEqual(trop_res.json()["severity_grade"], "MODERATE")

        # 3. Hepatobiliary endpoint
        hep_res = self.client.post(
            "/api/v1/clinical/hepatobiliary/score",
            json={
                "total_bilirubin_mg_dl": 2.2,
                "serum_albumin_g_dl": 3.1,
                "inr": 1.5,
                "serum_creatinine_mg_dl": 1.4,
                "serum_sodium_mEq_l": 132.0,
                "ascites_severity": "SLIGHT_OR_CONTROLLED",
                "encephalopathy_grade": "NONE"
            },
            headers=self.auth_headers
        )
        self.assertEqual(hep_res.status_code, 200)
        self.assertEqual(hep_res.json()["child_pugh"]["child_pugh_class"], "CLASS_B")

        # 4. Oncology TNM endpoint
        tnm_res = self.client.post(
            "/api/v1/clinical/oncology/tnm-stage",
            json={
                "tumor_site": "Gastric",
                "t_stage": "T3",
                "n_stage": "N1",
                "m_stage": "M0"
            },
            headers=self.auth_headers
        )
        self.assertEqual(tnm_res.status_code, 200)
        self.assertEqual(tnm_res.json()["overall_stage"], "Stage II")

        # 5. Rare disease endpoint
        rare_res = self.client.post(
            "/api/v1/clinical/rare-disease/match",
            json={
                "phenotype_hpo_terms": ["HP:0001392", "HP:0001337"],
                "clinical_keywords": ["tremor", "liver"]
            },
            headers=self.auth_headers
        )
        self.assertEqual(rare_res.status_code, 200)
        self.assertTrue(len(rare_res.json()["top_candidate_diseases"]) > 0)

        # 6. GET pan-institutional domains endpoint
        domains_res = self.client.get(
            "/api/v1/clinical/pan-institutional/domains",
            headers=self.auth_headers
        )
        self.assertEqual(domains_res.status_code, 200)
        self.assertIn("HYPERTENSION", domains_res.json()["supported_domains"])
        self.assertIn("SEPSIS_RESUSCITATION", domains_res.json()["supported_domains"])
        self.assertIn("CARDIOLOGY", domains_res.json()["department_domain_map"])

        # 7. GET department filtered domains endpoint
        dept_res = self.client.get(
            "/api/v1/clinical/pan-institutional/domains?department=CARDIOLOGY",
            headers=self.auth_headers
        )
        self.assertEqual(dept_res.status_code, 200)
        self.assertIn("HYPERTENSION", dept_res.json()["mapped_domains"])

        # 8. POST invalid domain returns clean HTTP 422 with supported_domains list
        bad_domain_res = self.client.post(
            "/api/v1/clinical/pan-institutional/arbitrate",
            json={"domain": "NON_EXISTENT_DISEASE_DOMAIN"},
            headers=self.auth_headers
        )
        self.assertEqual(bad_domain_res.status_code, 422)
        self.assertEqual(bad_domain_res.json()["detail"]["status"], "INVALID_DOMAIN")
        self.assertTrue(len(bad_domain_res.json()["detail"]["supported_domains"]) >= 8)

    def test_sepsis_resuscitation_arbitration_aiims_vs_johns_hopkins(self):
        """Verify Sepsis resuscitation arbitrates AIIMS crystalloid/norepi vs Hopkins multimodal VTI/vasopressin."""
        res = guideline_router.arbitrate_conflict(ClinicalDomain.SEPSIS_RESUSCITATION)
        local_std = res["primary_actionable_standard"]
        self.assertEqual(local_std["institution"], InstitutionSource.AIIMS_NEW_DELHI.value)
        self.assertIn("Norepinephrine", local_std["nlem_generic_molecules"])
        self.assertIn("Piperacillin-Tazobactam", local_std["nlem_generic_molecules"])

        global_bench = res["global_reference_benchmark"]
        self.assertEqual(global_bench["institution"], InstitutionSource.JOHNS_HOPKINS_MEDICINE.value)
        self.assertIn("Vasopressin", global_bench["nlem_generic_molecules"])

    def test_diabetes_inpatient_arbitration_aiims_vs_mayo_clinic(self):
        """Verify Inpatient Diabetes arbitrates AIIMS Human Insulin (low cost) vs Mayo Clinic analogs/CGM."""
        res = guideline_router.arbitrate_conflict(ClinicalDomain.DIABETES_INPATIENT)
        local_std = res["primary_actionable_standard"]
        self.assertEqual(local_std["institution"], InstitutionSource.AIIMS_NEW_DELHI.value)
        self.assertIn("Human Regular Insulin", local_std["nlem_generic_molecules"])
        self.assertLess(local_std["estimated_daily_cost_inr"], 50.0)

        global_bench = res["global_reference_benchmark"]
        self.assertEqual(global_bench["institution"], InstitutionSource.MAYO_CLINIC.value)
        self.assertIn("Insulin Glargine", global_bench["nlem_generic_molecules"])
        self.assertGreater(global_bench["estimated_daily_cost_inr"], 300.0)

    def test_nephrotic_syndrome_ckd_cmc_vellore_deworming(self):
        """Verify CMC Vellore Nephrology protocol mandates prophylactic Albendazole deworming prior to steroids."""
        res = guideline_router.arbitrate_conflict(ClinicalDomain.NEPHROTIC_SYNDROME_CKD)
        local_std = res["primary_actionable_standard"]
        self.assertEqual(local_std["institution"], InstitutionSource.CMC_VELLORE.value)
        self.assertIn("Albendazole", local_std["nlem_generic_molecules"])

    def test_department_to_domain_mapping_and_listing(self):
        """Verify 40-department mapping router links specialties to their correct clinical domains."""
        cardio_domains = guideline_router.get_domains_for_department("CARDIOLOGY")
        self.assertIn(ClinicalDomain.HYPERTENSION, cardio_domains)
        self.assertIn(ClinicalDomain.CORONARY_ARTERY_DISEASE_ACS, cardio_domains)

        critical_domains = guideline_router.get_domains_for_department("CRITICAL_CARE")
        self.assertIn(ClinicalDomain.SEPSIS_RESUSCITATION, critical_domains)

        all_domains = guideline_router.list_supported_domains()
        self.assertEqual(len(all_domains), 8)

    def test_pan_institutional_dre_deterministic_safety_gate_and_evaluate_endpoint(self):
        """Verify pan-institutional recommendations pass through CPOE DRE deterministic safety kernel."""
        # 1. Arbitrate via POST /evaluate alias
        eval_res = self.client.post(
            "/api/v1/clinical/pan-institutional/evaluate",
            json={"domain": "SEPSIS_RESUSCITATION"},
            headers=self.auth_headers
        )
        self.assertEqual(eval_res.status_code, 200)
        eval_data = eval_res.json()
        self.assertIn("Piperacillin-Tazobactam", eval_data["arbitration_result"]["primary_actionable_standard"]["nlem_generic_molecules"])

        # 2. Pipe recommendation into CPOE DRE safety kernel
        dre = CPOEDREEngine(tenant_id="TENANT-MAIN-01")
        
        # Test Case A: Patient with Penicillin anaphylaxis -> MUST BE HARD BLOCKED
        blocked_eval = dre.evaluate_order(
            patient_id="PT-SEPSIS-001",
            drug_name="Piperacillin-Tazobactam",
            prescribed_dose=4500.0,
            route="IV",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.8,
            serum_creatinine=1.0,
            patient_age=45,
            is_female=False,
            current_medications=[],
            known_allergies=["penicillin"]
        )
        self.assertEqual(blocked_eval["status"], "BLOCKED")
        self.assertTrue(any("LETHAL ALLERGY" in hs for hs in blocked_eval["hard_stops"]))

        # Test Case B: Patient with no penicillin allergy -> APPROVED
        approved_eval = dre.evaluate_order(
            patient_id="PT-SEPSIS-002",
            drug_name="Piperacillin-Tazobactam",
            prescribed_dose=4500.0,
            route="IV",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.8,
            serum_creatinine=1.0,
            patient_age=45,
            is_female=False,
            current_medications=[],
            known_allergies=[]
        )
        self.assertEqual(approved_eval["status"], "APPROVED")
        self.assertEqual(len(approved_eval["hard_stops"]), 0)


if __name__ == "__main__":
    unittest.main()

