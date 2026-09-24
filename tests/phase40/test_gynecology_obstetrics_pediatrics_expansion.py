#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 40: GYNECOLOGY, OBSTETRICS & PEDIATRICS EXPANSION TESTS
====================================================================================================
Comprehensive verification suite for Phase 40 clinical specialty depth:
1. FIGO PALM-COEIN AUB Classification & Postmenopausal Biopsy Trigger.
2. Rotterdam ESHRE/ASRM PCOS Phenotype Mapping & Metabolic Risk Stratification.
3. rASRM Endometriosis Staging & Deep Infiltrating Endometriosis Management.
4. ASCCP 2020 Cervical Screening & Oncogenic HPV Triage.
5. Combined Oral Contraceptive (COC) Thromboembolism Firewall.
6. Hypertensive Disorders of Pregnancy, Pre-eclampsia & HELLP Syndrome Stratifier.
7. FIGO Electronic Fetal Monitoring (CTG) Waveform Classification & Category 1 C-Section Trigger.
8. Inviolable Gestational Teratogenicity Safety Firewall.
9. Precision Dubois/Mosteller BSA & Holliday-Segar 4-2-1 Pediatric Maintenance Fluid Engine.
10. WHO Plan C Severe Dehydration Rehydration Protocol.
11. Broselow Pediatric Emergency Resuscitation Tape Calculator.
12. Pediatric Glasgow Coma Scale (pGCS) & Intubation Threshold.
13. AAP 2022 Neonatal Hyperbilirubinemia Phototherapy & Exchange Transfusion Nomogram.
14. Disease Knowledge Registry & STG Prescription Catalog Synchronization (52 Diseases).
====================================================================================================
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from gynecology_oncology_engine import (
    global_gynecology_oncology_engine,
    AUBStructuralCategory,
    AUBNonStructuralCategory,
    PCOSPhenotype,
    EndometriosisStage,
    CervicalCytology,
    ASCCPTriageAction
)
from obstetrics_labor_engine import (
    global_obstetrics_labor_engine,
    PartographActionLineBreachError
)
from pediatric_clinical_engine import (
    global_pediatric_clinical_engine,
    BroselowColorZone,
    WHODehydrationGrade
)
from disease_knowledge_registry import global_disease_registry_engine, DISEASE_REGISTRY
from prescription_protocol_engine import global_prescription_protocol_engine, STG_PROTOCOL_CATALOG


class TestPhase40GynecologyObstetricsPediatricsExpansion(unittest.TestCase):

    def setUp(self):
        self.gyn_engine = global_gynecology_oncology_engine
        self.obs_engine = global_obstetrics_labor_engine
        self.ped_engine = global_pediatric_clinical_engine
        self.disease_engine = global_disease_registry_engine
        self.stg_engine = global_prescription_protocol_engine

    # ----------------------------------------------------------------------------------------------
    # 1. GYNECOLOGY: FIGO PALM-COEIN AUB
    # ----------------------------------------------------------------------------------------------

    def test_01_figo_aub_classification_and_postmenopausal_rule(self):
        """Verifies FIGO PALM-COEIN categorization and postmenopausal endometrial thickness safety threshold."""
        # Case A: Reproductive age with submucosal fibroid
        res_a = self.gyn_engine.evaluate_aub_figo(
            patient_id="PAT-GYN-001",
            patient_age=32,
            has_leiomyoma=True,
            leiomyoma_submucosal=True
        )
        self.assertTrue(res_a.is_structural)
        self.assertIn(AUBStructuralCategory.LEIOMYOMA, res_a.structural_types)
        self.assertEqual(res_a.leiomyoma_subclassification, "SUBMUCOSAL (FIGO Type 0-2)")
        self.assertFalse(res_a.is_red_flag_malignancy)

        # Case B: Postmenopausal bleeding with ET = 7.5mm (> 4mm cutoff)
        res_b = self.gyn_engine.evaluate_aub_figo(
            patient_id="PAT-GYN-002",
            patient_age=58,
            endometrial_thickness_mm=7.5
        )
        self.assertTrue(res_b.is_red_flag_malignancy)
        self.assertTrue(any("Biopsy" in eval_item for eval_item in res_b.mandatory_evaluations))

    # ----------------------------------------------------------------------------------------------
    # 2. GYNECOLOGY: ROTTERDAM PCOS PHENOTYPING
    # ----------------------------------------------------------------------------------------------

    def test_02_rotterdam_pcos_phenotypes(self):
        """Verifies Rotterdam PCOS 4-phenotype classification and metabolic screening directives."""
        # Classic Phenotype A: Anovulation + Hyperandrogenism + PCOM
        res_a = self.gyn_engine.evaluate_pcos_rotterdam(
            patient_id="PAT-PCOS-01",
            cycle_length_days_avg=45.0,
            cycles_per_year=6,
            clinical_hirsutism_fg_score=12,
            biochemical_free_testosterone_elevated=True,
            antral_follicle_count_per_ovary=24,
            ovarian_volume_ml=12.5,
            bmi=31.2,
            has_acanthosis_nigricans=True
        )
        self.assertEqual(res_a.phenotype, PCOSPhenotype.PHENOTYPE_A_CLASSIC)
        self.assertEqual(res_a.metabolic_risk_level, "HIGH")
        self.assertTrue(any("OGTT" in s for s in res_a.indicated_metabolic_screens))
        self.assertTrue(any("Metformin" in t for t in res_a.therapeutic_strategy))

        # Non-PCOS Case: Only 1 criterion present (isolated acne/androgen with normal cycles and ovaries)
        res_none = self.gyn_engine.evaluate_pcos_rotterdam(
            patient_id="PAT-PCOS-02",
            cycle_length_days_avg=28.0,
            cycles_per_year=12,
            clinical_hirsutism_fg_score=9,
            biochemical_free_testosterone_elevated=False,
            antral_follicle_count_per_ovary=8,
            ovarian_volume_ml=6.0
        )
        self.assertEqual(res_none.phenotype, PCOSPhenotype.NON_PCOS)

    # ----------------------------------------------------------------------------------------------
    # 3. GYNECOLOGY: rASRM ENDOMETRIOSIS STAGING
    # ----------------------------------------------------------------------------------------------

    def test_03_rasrm_endometriosis_staging(self):
        """Verifies revised ASRM endometriosis staging and deep infiltrating surgical triggers."""
        res_stage4 = self.gyn_engine.evaluate_endometriosis_rasrm(
            patient_id="PAT-ENDO-01",
            peritoneal_superficial_score=4,
            ovarian_endometrioma_score=20,
            cul_de_sac_obliteration_score=40,
            tubal_adhesion_score=10,
            deep_infiltrating_nodules_present=True,
            ca125_u_per_ml=65.0
        )
        self.assertEqual(res_stage4.stage, EndometriosisStage.STAGE_IV_SEVERE)
        self.assertEqual(res_stage4.rASRM_score, 74)
        self.assertTrue(res_stage4.deep_infiltrating_endometriosis_present)
        self.assertTrue(res_stage4.ca125_elevated)
        self.assertTrue(res_stage4.fertility_preservation_indicated)
        self.assertIn("Multidisciplinary", res_stage4.recommended_pathway)

    # ----------------------------------------------------------------------------------------------
    # 4. GYNECOLOGY: ASCCP 2020 CERVICAL SCREENING TRIAGE
    # ----------------------------------------------------------------------------------------------

    def test_04_asccp_cervical_screening_triage(self):
        """Verifies ASCCP 2020 cervical cancer screening and oncogenic HPV management."""
        # HSIL cytology -> Immediate Colposcopy
        res_hsil = self.gyn_engine.evaluate_cervical_screening_asccp(
            patient_id="PAT-CX-01",
            patient_age=34,
            cytology=CervicalCytology.HSIL,
            hpv_16_18_positive=False,
            hpv_other_high_risk_positive=True
        )
        self.assertEqual(res_hsil["action"], ASCCPTriageAction.COLPOSCOPY_OR_EXCISION_IMMEDIATE.value)

        # Normal cytology + HPV 16 positive -> Colposcopy mandatory
        res_hpv16 = self.gyn_engine.evaluate_cervical_screening_asccp(
            patient_id="PAT-CX-02",
            patient_age=42,
            cytology=CervicalCytology.NILM,
            hpv_16_18_positive=True,
            hpv_other_high_risk_positive=False
        )
        self.assertEqual(res_hpv16["action"], ASCCPTriageAction.COLPOSCOPY_MANDATORY.value)

        # Co-negative screen -> 3-5 year routine
        res_neg = self.gyn_engine.evaluate_cervical_screening_asccp(
            patient_id="PAT-CX-03",
            patient_age=30,
            cytology=CervicalCytology.NILM,
            hpv_16_18_positive=False,
            hpv_other_high_risk_positive=False
        )
        self.assertEqual(res_neg["action"], ASCCPTriageAction.ROUTINE_SCREENING_3_YEARS.value)

    # ----------------------------------------------------------------------------------------------
    # 5. GYNECOLOGY: CONTRACEPTIVE THROMBOEMBOLISM FIREWALL
    # ----------------------------------------------------------------------------------------------

    def test_05_coc_thromboembolism_firewall(self):
        """Verifies WHO/CDC Category 4 absolute contraindications to Combined Oral Contraceptives."""
        # Smoker >= 35
        res_smoke = self.gyn_engine.screen_coc_contraindications(
            patient_id="PAT-CONTRA-01",
            patient_age=36,
            cigarettes_per_day=15
        )
        self.assertFalse(res_smoke.is_prescribing_safe)
        self.assertEqual(res_smoke.contraindication_severity, "ABSOLUTE_CONTRAINDICATION")
        self.assertTrue(len(res_smoke.safe_alternative_contraceptives) > 0)

        # Migraine with aura
        res_aura = self.gyn_engine.screen_coc_contraindications(
            patient_id="PAT-CONTRA-02",
            patient_age=26,
            has_migraine_with_aura=True
        )
        self.assertFalse(res_aura.is_prescribing_safe)

        # Young healthy patient -> Safe
        res_safe = self.gyn_engine.screen_coc_contraindications(
            patient_id="PAT-CONTRA-03",
            patient_age=24,
            cigarettes_per_day=0,
            systolic_bp=115,
            diastolic_bp=75
        )
        self.assertTrue(res_safe.is_prescribing_safe)
        self.assertEqual(res_safe.contraindication_severity, "SAFE")

    # ----------------------------------------------------------------------------------------------
    # 6. OBSTETRICS: PRE-ECLAMPSIA & HELLP SYNDROME
    # ----------------------------------------------------------------------------------------------

    def test_06_preeclampsia_and_hellp_stratification(self):
        """Verifies detection of severe pre-eclampsia, HELLP syndrome, and MgSO4 therapy triggers."""
        # HELLP Syndrome case
        res_hellp = self.obs_engine.evaluate_preeclampsia_hellp(
            patient_id="PAT-OBS-01",
            gestational_age_weeks=33.5,
            systolic_bp=165.0,
            diastolic_bp=112.0,
            proteinuria_dipstick="3+",
            platelet_count=72000.0,
            ast_u_per_l=115.0,
            alt_u_per_l=98.0,
            ldh_u_per_l=750.0,
            has_epigastric_or_ruq_pain=True
        )
        self.assertEqual(res_hellp["classification"], "HELLP_SYNDROME")
        self.assertTrue(res_hellp["is_hellp_syndrome"])
        self.assertTrue(res_hellp["magnesium_sulfate_indicated"])
        self.assertEqual(res_hellp["urgency"], "STAT_CRITICAL_EMERGENCY")

        # Gestational Hypertension case (no severe features, no proteinuria)
        res_gh = self.obs_engine.evaluate_preeclampsia_hellp(
            patient_id="PAT-OBS-02",
            gestational_age_weeks=28.0,
            systolic_bp=145.0,
            diastolic_bp=92.0,
            proteinuria_dipstick="NIL"
        )
        self.assertEqual(res_gh["classification"], "GESTATIONAL_HYPERTENSION")
        self.assertFalse(res_gh["is_severe"])

    # ----------------------------------------------------------------------------------------------
    # 7. OBSTETRICS: FIGO EFM/CTG WAVEFORM CLASSIFICATION
    # ----------------------------------------------------------------------------------------------

    def test_07_ctg_fetal_monitoring_and_emergency_csection_trigger(self):
        """Verifies FIGO CTG classification and Category 1 Emergency C-section trigger."""
        # Sustained severe bradycardia (< 80 bpm for > 3 minutes)
        res_brady = self.obs_engine.evaluate_fetal_ctg_trace(
            patient_id="PAT-CTG-01",
            baseline_fhr_bpm=75.0,
            variability_bpm=2.0,
            deceleration_type="PROLONGED",
            deceleration_duration_seconds=200.0
        )
        self.assertEqual(res_brady["category"], "PATHOLOGICAL_CATEGORY_III")
        self.assertTrue(res_brady["is_critical_life_threat"])
        self.assertIn("CATEGORY 1", res_brady["recommended_action"])

        # Sinusoidal trace
        res_sinus = self.obs_engine.evaluate_fetal_ctg_trace(
            patient_id="PAT-CTG-02",
            baseline_fhr_bpm=135.0,
            variability_bpm=5.0,
            deceleration_type="SINUSOIDAL"
        )
        self.assertEqual(res_sinus["category"], "PATHOLOGICAL_CATEGORY_III")
        self.assertIn("SINUSOIDAL", res_sinus["critical_alert"])

    # ----------------------------------------------------------------------------------------------
    # 8. OBSTETRICS: GESTATIONAL TERATOGENICITY FIREWALL
    # ----------------------------------------------------------------------------------------------

    def test_08_gestational_teratogenicity_firewall(self):
        """Verifies hard interception of Category X and D teratogenic drugs during pregnancy."""
        # Valproate in pregnant patient -> BLOCKED
        res_valp = self.obs_engine.screen_gestational_teratogenicity(
            patient_id="PAT-TERATO-01",
            drug_name="Sodium Valproate 500mg",
            is_pregnant=True
        )
        self.assertFalse(res_valp["is_safe"])
        self.assertTrue(res_valp["prescribing_blocked"])
        self.assertIn("VALPROATE", res_valp["danger_description"])

        # ACE Inhibitor Ramipril in pregnant patient -> BLOCKED
        res_ace = self.obs_engine.screen_gestational_teratogenicity(
            patient_id="PAT-TERATO-02",
            drug_name="Ramipril 5mg",
            is_pregnant=True
        )
        self.assertFalse(res_ace["is_safe"])
        self.assertTrue(res_ace["prescribing_blocked"])

        # Safe drug (Amoxicillin) -> APPROVED
        res_safe = self.obs_engine.screen_gestational_teratogenicity(
            patient_id="PAT-TERATO-03",
            drug_name="Amoxicillin 500mg",
            is_pregnant=True
        )
        self.assertTrue(res_safe["is_safe"])
        self.assertFalse(res_safe["prescribing_blocked"])

    # ----------------------------------------------------------------------------------------------
    # 9. PEDIATRICS: BSA & HOLLIDAY-SEGAR FLUID ENGINE
    # ----------------------------------------------------------------------------------------------

    def test_09_pediatric_bsa_and_fluid_calculations(self):
        """Verifies Mosteller BSA and Holliday-Segar 4-2-1 maintenance fluid arithmetic."""
        # 14 kg child
        bsa = self.ped_engine.calculate_body_surface_area(height_cm=95.0, weight_kg=14.0)
        self.assertGreater(bsa["bsa_mosteller_m2"], 0.5)
        self.assertLess(bsa["bsa_mosteller_m2"], 0.7)

        fluid = self.ped_engine.calculate_holliday_segar_maintenance(weight_kg=14.0)
        # Expected: 1000 + (4 * 50) = 1200 mL/day -> 50 mL/hr
        self.assertEqual(fluid.daily_maintenance_ml, 1200.0)
        self.assertEqual(fluid.hourly_rate_ml_per_hour, 50.0)
        self.assertGreater(fluid.electrolyte_sodium_meq_day, 0)

    # ----------------------------------------------------------------------------------------------
    # 10. PEDIATRICS: WHO PLAN C SEVERE DEHYDRATION RESUSCITATION
    # ----------------------------------------------------------------------------------------------

    def test_10_who_plan_c_dehydration_protocol(self):
        """Verifies WHO Plan C fluid resuscitation calculations for infant vs older child."""
        # 8 kg infant (age 8 months < 1 year)
        # 100 mL/kg = 800 mL total; Step 1: 30 mL/kg (240 mL in 1h); Step 2: 70 mL/kg (560 mL in 5h)
        res_infant = self.ped_engine.calculate_who_dehydration_plan_c(weight_kg=8.0, age_months=8)
        self.assertEqual(res_infant["total_fluid_ml"], 800.0)
        self.assertEqual(res_infant["step_1_bolus"]["volume_ml"], 240.0)
        self.assertEqual(res_infant["step_1_bolus"]["duration"], "1 hour")
        self.assertEqual(res_infant["step_2_maintenance"]["volume_ml"], 560.0)

        # 15 kg child (age 36 months >= 1 year)
        # Step 1 in 30 minutes, Step 2 in 2.5 hours
        res_child = self.ped_engine.calculate_who_dehydration_plan_c(weight_kg=15.0, age_months=36)
        self.assertEqual(res_child["step_1_bolus"]["duration"], "30 minutes")
        self.assertEqual(res_child["step_2_maintenance"]["duration"], "2.5 hours")

    # ----------------------------------------------------------------------------------------------
    # 11. PEDIATRICS: BROSELOW RESUSCITATION TAPE
    # ----------------------------------------------------------------------------------------------

    def test_11_broselow_resuscitation_tape(self):
        """Verifies Broselow color zone assignment, ET tube sizing, and defib/epinephrine dosing."""
        # Child length 72 cm -> RED zone (approx 8.5 kg)
        res_red = self.ped_engine.evaluate_broselow_resuscitation(length_cm=72.0)
        self.assertEqual(res_red.color_zone, BroselowColorZone.RED)
        self.assertEqual(res_red.estimated_weight_kg, 8.5)
        self.assertEqual(res_red.et_tube_size_cuffed_mm, 3.5)
        self.assertEqual(res_red.defibrillation_initial_joules, 17.0)  # 2 J/kg * 8.5
        self.assertEqual(res_red.fluid_bolus_volume_ml, 170.0)        # 20 mL/kg * 8.5

    # ----------------------------------------------------------------------------------------------
    # 12. PEDIATRICS: PEDIATRIC GLASGOW COMA SCALE (pGCS)
    # ----------------------------------------------------------------------------------------------

    def test_12_pediatric_gcs_scoring(self):
        """Verifies pre-verbal and child pGCS scoring with intubation threshold alert."""
        # Severe coma: Eyes 1, Verbal 2 (grunts), Motor 3 (abnormal flexion) -> Total 6 (<= 8)
        res_coma = self.ped_engine.evaluate_pediatric_gcs(
            eye_opening=1,
            verbal_response=2,
            motor_response=3,
            is_preverbal=True
        )
        self.assertEqual(res_coma["total_pgcs"], 6)
        self.assertEqual(res_coma["clinical_severity"], "SEVERE_HEAD_INJURY_OR_COMA")
        self.assertTrue(res_coma["is_intubation_indicated"])

    # ----------------------------------------------------------------------------------------------
    # 13. NEONATOLOGY: AAP HYPERBILIRUBINEMIA NOMOGRAM
    # ----------------------------------------------------------------------------------------------

    def test_13_aap_hyperbilirubinemia_nomogram(self):
        """Verifies AAP 2022 hour-specific phototherapy and exchange transfusion cutoffs."""
        # 36 hours old, TSB = 16.5 mg/dL, Term 39w -> Phototherapy indicated
        res_photo = self.ped_engine.evaluate_aap_hyperbilirubinemia(
            postnatal_age_hours=36.0,
            tsb_mg_per_dl=16.5,
            gestational_age_weeks=39.0
        )
        self.assertTrue(res_photo.phototherapy_indicated)
        self.assertFalse(res_photo.exchange_transfusion_indicated)
        self.assertIn("PHOTOTHERAPY", res_photo.urgency_recommendation)

        # Extreme hyperbilirubinemia: 48 hours old, TSB = 25.0 mg/dL -> Exchange transfusion indicated
        res_exchange = self.ped_engine.evaluate_aap_hyperbilirubinemia(
            postnatal_age_hours=48.0,
            tsb_mg_per_dl=25.0,
            gestational_age_weeks=39.0
        )
        self.assertTrue(res_exchange.exchange_transfusion_indicated)
        self.assertIn("EXCHANGE TRANSFUSION", res_exchange.urgency_recommendation)

    # ----------------------------------------------------------------------------------------------
    # 14. REGISTRY & STG SYNCHRONIZATION (52 CONDITIONS)
    # ----------------------------------------------------------------------------------------------

    def test_14_registry_and_stg_synchronization(self):
        """Verifies that DISEASE_REGISTRY and STG_PROTOCOL_CATALOG contain 52 synchronized conditions."""
        self.assertEqual(len(DISEASE_REGISTRY), 52)
        self.assertEqual(len(STG_PROTOCOL_CATALOG), 52)

        # Verify all new conditions exist in both
        new_keys = [
            "PRE_ECLAMPSIA_WITH_SEVERE_FEATURES",
            "POLYCYSTIC_OVARY_SYNDROME",
            "PEDIATRIC_STATUS_ASTHMATICUS",
            "PEDIATRIC_DIARRHEA_SEVERE_DEHYDRATION"
        ]
        for key in new_keys:
            self.assertIn(key, DISEASE_REGISTRY, f"Missing {key} in DISEASE_REGISTRY")
            self.assertIn(key, STG_PROTOCOL_CATALOG, f"Missing {key} in STG_PROTOCOL_CATALOG")

            entity = DISEASE_REGISTRY[key]
            self.assertTrue(entity.snomed_id)
            self.assertTrue(entity.icd11_id)

            protocol = STG_PROTOCOL_CATALOG[key]
            self.assertTrue(len(protocol.first_line_regimen) > 0)
            self.assertTrue(len(protocol.mandatory_baseline_labs) > 0)

    # ----------------------------------------------------------------------------------------------
    # 15. BATTLE-TESTED REAL-WORLD EDGE CASES: SAM MALNUTRITION & UNMEASURED AUB
    # ----------------------------------------------------------------------------------------------

    def test_15_sam_malnutrition_fluid_contraindication_and_unmeasured_postmenopausal_aub(self):
        """Verifies fatal SAM fluid overload prevention and postmenopausal AUB pre-TVS malignancy vigilance."""
        # Case A: Child with Severe Acute Malnutrition (SAM) presenting with severe dehydration
        res_sam = self.ped_engine.calculate_who_dehydration_plan_c(
            weight_kg=9.0,
            age_months=18,
            has_severe_acute_malnutrition=True
        )
        self.assertTrue(res_sam["is_standard_plan_c_contraindicated"])
        self.assertEqual(res_sam["protocol"], "WHO_SAM_DEHYDRATION_CONTRAINDICATION")
        self.assertEqual(res_sam["total_fluid_ml"], 0.0)
        self.assertIn("ReSoMal", res_sam["recommended_resuscitation"])

        # Case B: 55-year-old postmenopausal woman with bleeding but TVS not yet performed (ET is None)
        res_aub = self.gyn_engine.evaluate_aub_figo(
            patient_id="PAT-PMB-001",
            patient_age=55,
            endometrial_thickness_mm=None
        )
        self.assertTrue(res_aub.is_red_flag_malignancy)
        self.assertTrue(any("Immediate Transvaginal Ultrasound" in e for e in res_aub.mandatory_evaluations))

    # ----------------------------------------------------------------------------------------------
    # 16. REST API & APPSHIM PHASE 40 ENDPOINT PARITY VERIFICATION
    # ----------------------------------------------------------------------------------------------

    def test_16_fastapi_and_appshim_phase40_endpoints(self):
        """Verifies that main.py and AppShim provide full REST/shim coverage for Phase 40."""
        import main

        # Test AppShim methods
        shim = main.AppShim()

        # 1. AUB Evaluation
        aub = shim.evaluate_aub_figo("PAT-SHIM-01", 52, endometrial_thickness_mm=6.0)
        self.assertTrue(aub["is_red_flag_malignancy"])

        # 2. COC Safety
        coc = shim.screen_coc_safety("PAT-SHIM-02", 36, cigarettes_per_day=20)
        self.assertFalse(coc["is_prescribing_safe"])

        # 3. Obstetric CTG
        ctg = shim.evaluate_obstetric_ctg("PAT-SHIM-03", baseline_fhr_bpm=70.0, variability_bpm=2.0, deceleration_type="PROLONGED", deceleration_duration_seconds=200.0)
        self.assertEqual(ctg["category"], "PATHOLOGICAL_CATEGORY_III")

        # 4. Teratogenicity Screen
        terato = shim.screen_gestational_drug_safety("PAT-SHIM-04", "Methotrexate 15mg", is_pregnant=True)
        self.assertTrue(terato["prescribing_blocked"])

        # 5. Pediatric Maintenance Fluids
        fluids = shim.calculate_pediatric_fluids(weight_kg=12.0)
        self.assertEqual(fluids["daily_maintenance_ml"], 1100.0)

        # 6. Broselow Tape
        broselow = shim.calculate_broselow_emergency_profile(length_cm=65.0)
        self.assertIn("PINK", broselow["color_zone"])

        # 7. Neonatal Hyperbilirubinemia
        bili = shim.evaluate_neonatal_hyperbilirubinemia(postnatal_age_hours=48.0, tsb_mg_per_dl=18.0, gestational_age_weeks=39.0)
        self.assertTrue(bili["phototherapy_indicated"])


if __name__ == "__main__":
    unittest.main()

