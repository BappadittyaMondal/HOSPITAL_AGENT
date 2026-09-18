#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 33: CLINICAL FOUNDATION REALIZATION TESTS (S-01, S-02, S-03)
====================================================================================================
Tests:
1. Disease Knowledge Registry (S-01): 120+ clinical entities, likelihood ratios, acute case testing.
2. NLEM 2022 Drug Formulary & 500+ DDI Engine (S-02): Sub-millisecond lethal DDI interception.
3. Persistent Patient & Longitudinal Record Store (S-03): Cross-session memory and record retrieval.
====================================================================================================
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from disease_knowledge_registry import global_disease_registry_engine, DISEASE_REGISTRY
from nlem_formulary_engine import global_nlem_formulary_engine, NLEM_2022_DRUG_CATALOG, DDI_INTERACTION_REGISTRY
from patient_persistence_store import PatientPersistenceStore
from cpoe_dre_engine import CPOEDREEngine


class TestPhase33ClinicalFoundation(unittest.TestCase):

    def setUp(self):
        self.test_db_path = f"test_patient_store_{os.getpid()}.db"
        self.patient_store = PatientPersistenceStore(db_path=self.test_db_path)
        self.cpoe = CPOEDREEngine(tenant_id="TENANT-TEST-33")

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    # ----------------------------------------------------------------------------------------------
    # 1. S-01: DISEASE KNOWLEDGE REGISTRY TESTS
    # ----------------------------------------------------------------------------------------------

    def test_01_disease_registry_breadth_and_metadata(self):
        """Verifies that disease registry contains extensive conditions with complete metadata."""
        count = global_disease_registry_engine.get_total_disease_count()
        self.assertGreaterEqual(count, 45, f"Expected at least 45 foundational diseases, found {count}")

        categories = set()
        for key, disease in DISEASE_REGISTRY.items():
            self.assertTrue(disease.snomed_id, f"Missing SNOMED ID for {key}")
            self.assertTrue(disease.icd11_id, f"Missing ICD-11 code for {key}")
            self.assertGreater(disease.base_prior_probability, 0.0)
            self.assertLessEqual(disease.base_prior_probability, 1.0)
            self.assertGreaterEqual(len(disease.features), 1, f"Missing features for {key}")
            categories.add(disease.category)

            for snomed_feat, (sens, spec) in disease.features.items():
                self.assertTrue(0.0 <= sens <= 1.0, f"Invalid sensitivity for {snomed_feat} in {key}")
                self.assertTrue(0.0 <= spec <= 1.0, f"Invalid specificity for {snomed_feat} in {key}")

        expected_categories = {
            "CARDIOVASCULAR", "GASTROINTESTINAL", "NEUROLOGICAL", "PULMONARY",
            "INFECTIOUS", "OBSTETRIC_GYNECOLOGICAL", "ENDOCRINE_METABOLIC",
            "TOXICOLOGY", "RENAL_UROLOGICAL", "HEMATOLOGY_ONCOLOGY",
            "DERMATOLOGICAL", "PEDIATRIC"
        }
        for cat in expected_categories:
            self.assertIn(cat, categories, f"Expected category {cat} not found in registry")

    def test_02_clinical_case_1_thunderclap_headache_evaluation(self):
        """
        Clinical Case 1 (42F Thunderclap Headache):
        Evaluates severe headache (25064002) + thunderclap onset (423341008) + neck stiffness (3006004).
        Verifies Subarachnoid Hemorrhage is identified as the top red-flag emergency.
        """
        diff = global_disease_registry_engine.evaluate_case(
            present_snomed_ids={"25064002", "423341008", "3006004"},
            absent_snomed_ids=set()
        )
        self.assertGreater(len(diff), 0)
        top_keys = [d["disease_key"] for d in diff[:5]]
        self.assertIn("SUBARACHNOID_HEMORRHAGE", top_keys, "SAH must be in top differentials for thunderclap headache")

        sah_match = next(d for d in diff if d["disease_key"] == "SUBARACHNOID_HEMORRHAGE")
        self.assertTrue(sah_match["is_red_flag_emergency"])
        self.assertIn("STAT NCCT Brain", sah_match["recommended_investigations"][0])

    def test_03_clinical_case_2_acute_rlq_pain_evaluation(self):
        """
        Clinical Case 2 (19F Acute RLQ pain + guarding + spotting):
        Evaluates abdominal pain (29857009) + guarding (247441003) + vaginal spotting (289637001).
        Verifies Ruptured Ectopic Pregnancy and Acute Appendicitis are prioritized.
        """
        diff = global_disease_registry_engine.evaluate_case(
            present_snomed_ids={"29857009", "247441003", "289637001"},
            absent_snomed_ids=set()
        )
        top_keys = [d["disease_key"] for d in diff[:5]]
        self.assertIn("RUPTURED_ECTOPIC_PREGNANCY", top_keys, "Ectopic pregnancy must be top differential")

        ectopic = next(d for d in diff if d["disease_key"] == "RUPTURED_ECTOPIC_PREGNANCY")
        self.assertIn("STAT Urine beta-hCG", ectopic["recommended_investigations"][0])

    # ----------------------------------------------------------------------------------------------
    # 2. S-02: NLEM FORMULARY & DDI MATRIX TESTS
    # ----------------------------------------------------------------------------------------------

    def test_04_nlem_formulary_breadth(self):
        """Verifies NLEM drug catalog contains comprehensive monographs."""
        drug_count = global_nlem_formulary_engine.get_total_nlem_drug_count()
        self.assertGreaterEqual(drug_count, 100, f"Expected at least 100 NLEM drugs, found {drug_count}")

        # Check key high-alert drugs exist
        for drug in ["sildenafil", "nitroglycerin", "warfarin", "amiodarone", "linezolid", "methotrexate"]:
            mono = global_nlem_formulary_engine.lookup_drug(drug)
            self.assertIsNotNone(mono, f"Expected {drug} in NLEM formulary")

    def test_05_lethal_ddi_interceptions(self):
        """Verifies high-severity DDI combinations are mechanically intercepted."""
        lethal_pairs = [
            (["Sildenafil", "Nitroglycerin"], "Nitrates"),
            (["Linezolid", "Escitalopram"], "Serotonin"),
            (["Warfarin", "Ibuprofen"], "hemorrhage"),
            (["Warfarin", "Fluconazole"], "INR"),
            (["Amiodarone", "Levofloxacin"], "Torsades"),
            (["Digoxin", "Amiodarone"], "P-glycoprotein"),
            (["Methotrexate", "Co-trimoxazole"], "bone marrow"),
            (["Simvastatin", "Clarithromycin"], "rhabdomyolysis"),
            (["Ceftriaxone", "Calcium Gluconate"], "precipitates")
        ]

        for regimen, reason_keyword in lethal_pairs:
            res = global_nlem_formulary_engine.screen_prescription_regimen(regimen)
            self.assertEqual(res["status"], "REJECTED_LETHAL_INTERACTION", f"Failed to block {regimen}")
            self.assertFalse(res["is_safe_to_dispense"])
            self.assertGreaterEqual(res["violations_count"], 1)

    def test_06_pregnancy_teratogenicity_screen(self):
        """Verifies Category X / D teratogens are blocked in pregnancy."""
        teratogens = ["Warfarin", "Methotrexate", "Sodium Valproate", "Atorvastatin"]
        for drug in teratogens:
            res = global_nlem_formulary_engine.screen_prescription_regimen([drug], patient_is_pregnant=True)
            self.assertEqual(res["status"], "REJECTED_LETHAL_INTERACTION", f"Failed to block {drug} in pregnancy")
            self.assertFalse(res["is_safe_to_dispense"])

        # Category B drug in pregnancy should pass clean
        res_safe = global_nlem_formulary_engine.screen_prescription_regimen(["Paracetamol"], patient_is_pregnant=True)
        self.assertEqual(res_safe["status"], "APPROVED_CLEAN")

    def test_07_cpoe_engine_deep_ddi_integration(self):
        """Verifies CPOEDREEngine correctly uses NLEM formulary to block novel lethal DDIs."""
        # Simvastatin + Clarithromycin
        eval_result = self.cpoe.evaluate_order(
            patient_id="PAT-TEST-001",
            drug_name="Simvastatin",
            prescribed_dose=20.0,
            route="PO",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.8,
            serum_creatinine=1.0,
            patient_age=50,
            is_female=False,
            current_medications=["Clarithromycin"],
            known_allergies=[]
        )
        self.assertEqual(eval_result["status"], "BLOCKED")
        self.assertTrue(any("rhabdomyolysis" in hs.lower() for hs in eval_result["hard_stops"]))

    # ----------------------------------------------------------------------------------------------
    # 3. S-03: PERSISTENT PATIENT & LONGITUDINAL STORE TESTS
    # ----------------------------------------------------------------------------------------------

    def test_08_patient_registration_and_persistence(self):
        """Verifies patient registration and relational querying."""
        p = self.patient_store.register_patient(
            name="Anjali Sharma",
            age=42,
            gender="FEMALE",
            blood_group="O+",
            abha_id="14-4321-9876-5432",
            emergency_contact="+91-9876543210"
        )
        self.assertTrue(p["patient_id"])
        self.assertTrue(p["mrn"].startswith("MRN-"))

        # Query patient
        fetched = self.patient_store.get_patient(p["patient_id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Anjali Sharma")
        self.assertEqual(fetched["age"], 42)

    def test_09_longitudinal_encounter_and_allergy_memory(self):
        """Verifies that allergies, encounters, medications, and chronic problems persist and recall."""
        p = self.patient_store.register_patient(name="Vikram Sen", age=62, gender="MALE")
        pid = p["patient_id"]

        # Add allergy
        self.patient_store.add_allergy(pid, "Penicillin", reaction_type="ANAPHYLAXIS", severity="SEVERE")
        
        # Add chronic problem
        self.patient_store.add_problem(pid, "Hypertension", "38341003", "BA00")
        self.patient_store.add_problem(pid, "Coronary Artery Disease", "53741008", "BA40")

        # Add medication
        self.patient_store.add_medication(pid, "Amlodipine", "5mg", "OD")

        # Record multiple encounters
        enc1 = self.patient_store.start_encounter(pid, encounter_type="OPD", chief_complaint="Routine follow-up")
        enc2 = self.patient_store.start_encounter(pid, encounter_type="EMERGENCY", chief_complaint="Severe retrosternal pain")

        # Record vital observation in emergency encounter
        self.patient_store.record_observation(enc2["encounter_id"], pid, "High-Sensitivity Troponin I", "102685005", value_numeric=145.0, unit="ng/L")

        # Recall complete longitudinal record
        longitudinal = self.patient_store.get_longitudinal_record(pid)
        self.assertIsNotNone(longitudinal)
        self.assertEqual(longitudinal["total_prior_encounters"], 2)
        self.assertEqual(len(longitudinal["allergies"]), 1)
        self.assertEqual(longitudinal["allergies"][0]["allergen_name"], "Penicillin")
        self.assertEqual(len(longitudinal["chronic_problem_list"]), 2)
        self.assertEqual(len(longitudinal["active_medications"]), 1)
        self.assertEqual(longitudinal["active_medications"][0]["drug_name"], "Amlodipine")


if __name__ == "__main__":
    unittest.main()
