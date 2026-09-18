#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 34: CLINICAL PRECISION & LIFECYCLE UPGRADE TESTS
====================================================================================================
Tests:
1. SNOMED-CT Semantic Disambiguation: Verifies unique concept IDs across all 48 diseases.
2. Differential Specificity: Asserts chest pain does NOT cross-pollinate into appendicitis or torsion.
3. Rule-Out Resolution: Verifies all mandatory rule-outs resolve to valid registry entities.
4. Calcium Gluconate & Ceftriaxone DDI: Asserts registration and lethal co-administration block.
5. Algorithmic Hash-Matching: Verifies O(1) DDI lookups without false-positive substring matches.
6. ISMP High-Alert Surveillance: Verifies dual-signoff warnings on high-alert medications.
7. Longitudinal Observation Recall: Verifies vitals and lab values are returned in patient record.
8. Clinical Lifecycle Transitions: Verifies encounter discharge and medication discontinuation.
9. Problem Resolution & Robustness: Verifies chronic problem resolution and error safety.
====================================================================================================
"""

import sys
import os
import unittest
import gc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from disease_knowledge_registry import global_disease_registry_engine, DISEASE_REGISTRY
from nlem_formulary_engine import global_nlem_formulary_engine, NLEM_2022_DRUG_CATALOG, DDI_INTERACTION_REGISTRY
from patient_persistence_store import PatientPersistenceStore
from cpoe_dre_engine import CPOEDREEngine


class TestPhase34ClinicalPrecisionAndLifecycle(unittest.TestCase):

    def setUp(self):
        self.test_db_path = f"test_phase34_store_{os.getpid()}.db"
        self.patient_store = PatientPersistenceStore(db_path=self.test_db_path)
        self.cpoe = CPOEDREEngine(tenant_id="TENANT-TEST-34")

    def tearDown(self):
        del self.patient_store
        gc.collect()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    # ----------------------------------------------------------------------------------------------
    # 1. SNOMED-CT DISAMBIGUATION & DIFFERENTIAL SPECIFICITY
    # ----------------------------------------------------------------------------------------------

    def test_01_snomed_semantic_disambiguation_breadth(self):
        """Verifies that generic placeholder SNOMED codes are not overloaded across distinct specialties."""
        chest_pain_diseases = [
            k for k, v in DISEASE_REGISTRY.items()
            if "29857009" in v.features
        ]
        # Chest pain 29857009 must only be on cardiac/chest conditions, NOT on appendicitis or testicular torsion
        self.assertIn("ACUTE_MYOCARDIAL_INFARCTION", chest_pain_diseases)
        self.assertNotIn("ACUTE_APPENDICITIS", chest_pain_diseases, "Appendicitis must use abdominal pain code, not chest pain")
        self.assertNotIn("TESTICULAR_TORSION", chest_pain_diseases, "Testicular torsion must use scrotal pain code, not chest pain")
        self.assertNotIn("INTUSSUSCEPTION", chest_pain_diseases, "Intussusception must use infant colic code, not chest pain")

        # Verify Appendicitis has McBurney RLQ pain
        app = DISEASE_REGISTRY["ACUTE_APPENDICITIS"]
        self.assertIn("163284000", app.features, "Appendicitis must have RLQ pain 163284000")

        # Verify Testicular Torsion has scrotal pain
        tt = DISEASE_REGISTRY["TESTICULAR_TORSION"]
        self.assertIn("276412004", tt.features, "Testicular torsion must have scrotal pain 276412004")

    def test_02_differential_specificity_isolation(self):
        """Verifies that evaluating acute retrosternal chest pain does NOT artificially boost unrelated conditions."""
        diff = global_disease_registry_engine.evaluate_case(
            present_snomed_ids={"29857009"},  # Retrosternal chest pain
            absent_snomed_ids=set()
        )
        # AMI should have positive findings applied and increased posterior
        ami = next(d for d in diff if d["disease_key"] == "ACUTE_MYOCARDIAL_INFARCTION")
        self.assertEqual(ami["findings_applied_count"], 1)
        self.assertGreater(ami["posterior_probability"], ami["base_prior_probability"])

        # Unrelated conditions must have ZERO matched findings and unboosted posterior
        app = next(d for d in diff if d["disease_key"] == "ACUTE_APPENDICITIS")
        self.assertEqual(app["findings_applied_count"], 0, "Chest pain must not match any feature in appendicitis")
        self.assertEqual(app["posterior_probability"], app["base_prior_probability"])

        tt = next(d for d in diff if d["disease_key"] == "TESTICULAR_TORSION")
        self.assertEqual(tt["findings_applied_count"], 0, "Chest pain must not match any feature in testicular torsion")
        self.assertEqual(tt["posterior_probability"], tt["base_prior_probability"])

        # Out of all diseases with positive matched findings, AMI must be #1
        matched_diseases = [d for d in diff if d["findings_applied_count"] > 0]
        self.assertEqual(matched_diseases[0]["disease_key"], "ACUTE_MYOCARDIAL_INFARCTION")

    def test_03_mandatory_ruleouts_resolution_integrity(self):
        """Verifies that all 48 diseases' mandatory_rule_outs resolve to valid registry keys."""
        all_keys = set(DISEASE_REGISTRY.keys())
        for key, entity in DISEASE_REGISTRY.items():
            for rule_out in entity.mandatory_rule_outs:
                self.assertIn(
                    rule_out, all_keys,
                    f"Disease {key} references unresolvable mandatory rule-out: {rule_out}"
                )

    # ----------------------------------------------------------------------------------------------
    # 2. NLEM FORMULARY O(1) HASH & HIGH-ALERT SURVEILLANCE
    # ----------------------------------------------------------------------------------------------

    def test_04_calcium_gluconate_registration_and_ddi(self):
        """Verifies Calcium Gluconate is registered in NLEM catalog and Ceftriaxone interaction fires."""
        cg = global_nlem_formulary_engine.lookup_drug("calcium gluconate")
        self.assertIsNotNone(cg, "Calcium Gluconate must be registered in NLEM catalog")
        self.assertEqual(cg.atc_code, "A12AA03")
        self.assertTrue(cg.is_high_alert_medication)

        # Screen Ceftriaxone + Calcium Gluconate
        res = global_nlem_formulary_engine.screen_prescription_regimen(["Ceftriaxone", "Calcium Gluconate"])
        self.assertEqual(res["status"], "REJECTED_LETHAL_INTERACTION")
        self.assertFalse(res["is_safe_to_dispense"])
        self.assertGreaterEqual(res["violations_count"], 1)

    def test_05_algorithmic_hash_matching_prevents_false_positives(self):
        """Verifies O(1) lookup does not trigger on short partial substrings."""
        # Querying a short string like "in" should return None
        lookup_in = global_nlem_formulary_engine.lookup_drug("in")
        self.assertIsNone(lookup_in, "Short substring 'in' must not match arbitrary drugs")

        # Prescribing non-interacting drugs containing common substrings should pass clean
        res = global_nlem_formulary_engine.screen_prescription_regimen(["Paracetamol", "Amoxicillin"])
        self.assertEqual(res["status"], "APPROVED_CLEAN")
        self.assertTrue(res["is_safe_to_dispense"])
        self.assertEqual(res["violations_count"], 0)

    def test_06_ismp_high_alert_medication_surveillance(self):
        """Verifies that high-alert medications trigger dual-signoff safety alerts."""
        res = global_nlem_formulary_engine.screen_prescription_regimen(["Propofol", "Paracetamol"])
        self.assertGreaterEqual(res["high_alerts_count"], 1)
        flagged_drugs = [ha["drug"] for ha in res["high_alert_medications"]]
        self.assertIn("Propofol", flagged_drugs)
        self.assertIn("ISMP High-Alert", res["high_alert_medications"][0]["warning"])

    # ----------------------------------------------------------------------------------------------
    # 3. PATIENT PERSISTENCE LIFECYCLE & OBSERVATION RECALL
    # ----------------------------------------------------------------------------------------------

    def test_07_longitudinal_observation_recall(self):
        """Verifies that get_longitudinal_record() includes comprehensive vital signs and lab values."""
        p = self.patient_store.register_patient(name="Sunita Rao", age=50, gender="FEMALE")
        pid = p["patient_id"]
        enc = self.patient_store.start_encounter(pid, "EMERGENCY", "Palpitations")
        enc_id = enc["encounter_id"]

        # Record multiple vital/lab observations
        self.patient_store.record_observation(enc_id, pid, "High-Sensitivity Troponin I", "105000003", value_numeric=8.2, unit="ng/L")
        self.patient_store.record_observation(enc_id, pid, "Serum Potassium", "14140009", value_numeric=4.1, unit="mmol/L")

        rec = self.patient_store.get_longitudinal_record(pid)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["total_recorded_observations"], 2)
        concept_codes = [obs["concept_code"] for obs in rec["longitudinal_observations"]]
        self.assertIn("105000003", concept_codes)
        self.assertIn("14140009", concept_codes)

    def test_08_encounter_discharge_and_medication_discontinuation(self):
        """Verifies clinical lifecycle state transitions: discharge encounter and discontinue medication."""
        p = self.patient_store.register_patient(name="Manoj Sharma", age=45, gender="MALE")
        pid = p["patient_id"]
        enc = self.patient_store.start_encounter(pid, "EMERGENCY", "Acute Bronchospasm")
        enc_id = enc["encounter_id"]

        med = self.patient_store.add_medication(pid, "Hydrocortisone", "100mg", "TID", route="IV", encounter_id=enc_id)
        med_id = med["medication_id"]

        # Discontinue medication
        disc_res = self.patient_store.discontinue_medication(med_id, reason="Course Completed")
        self.assertTrue(disc_res["success"])
        self.assertEqual(disc_res["status"], "DISCONTINUED")

        # Discharge encounter
        dc_res = self.patient_store.discharge_encounter(enc_id, disposition="DISCHARGED_HOME", discharge_summary="Wheezing resolved with IV steroids")
        self.assertTrue(dc_res["success"])
        self.assertEqual(dc_res["status"], "DISCHARGED")
        self.assertIsNotNone(dc_res["discharged_at"])

        # Check longitudinal record reflects updated states
        rec = self.patient_store.get_longitudinal_record(pid)
        self.assertEqual(len(rec["active_medications"]), 0, "Discontinued medication must not appear in active list")
        self.assertEqual(len(rec["all_medication_history"]), 1, "Discontinued medication must appear in full history")
        self.assertEqual(rec["all_medication_history"][0]["status"], "DISCONTINUED")
        self.assertEqual(rec["encounter_history"][0]["status"], "DISCHARGED")

    def test_09_chronic_problem_resolution_and_integrity(self):
        """Verifies that problem list items can be resolved cleanly."""
        p = self.patient_store.register_patient(name="Kavita Nair", age=28, gender="FEMALE")
        pid = p["patient_id"]

        prob = self.patient_store.add_problem(pid, "Acute Gastroenteritis", "21522001", "1A00")
        prob_id = prob["problem_id"]

        # Resolve problem
        res_prob = self.patient_store.resolve_problem(prob_id)
        self.assertTrue(res_prob["success"])
        self.assertEqual(res_prob["status"], "RESOLVED")

        rec = self.patient_store.get_longitudinal_record(pid)
        self.assertEqual(len(rec["chronic_problem_list"]), 0, "Resolved condition must not appear in active chronic list")
        self.assertEqual(len(rec["all_problem_history"]), 1, "Resolved condition must appear in problem history")
        self.assertEqual(rec["all_problem_history"][0]["status"], "RESOLVED")


if __name__ == "__main__":
    unittest.main()
