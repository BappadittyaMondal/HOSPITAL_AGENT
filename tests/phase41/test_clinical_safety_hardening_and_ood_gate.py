#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 41: CLINICAL SAFETY HARDENING & OOD ABSTENTION GATE
====================================================================================================
Tests:
1. Out-of-Distribution (OOD) Abstention Gate: Prevents forced misdiagnosis of unindexed conditions.
2. In-Distribution Recognition: Preserves high-confidence Bayesian evaluation on recognized diseases.
3. Pertinent Negatives OOD Evaluation: Validates DAG graph RAG OOD thresholding.
4. Combinatorial Polypharmacy ("Triple Whammy"): Intercepts ACEi/ARB + Diuretic + NSAID acute renal shutdown.
5. Additive QTc Multi-Drug Surveillance: Detects synergistic Torsades de Pointes arrhythmia hazards.
6. Unspecified Allergy Safeguard: Eliminates silent defaults and mandates interview for high-risk drugs.
7. Longitudinal History Auto-Hydration: Ingests recorded chronic problems into diagnostic evaluations.
8. AppShim Parity & Multi-Drug Screening: Validates standalone and edge execution parity.
====================================================================================================
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from disease_knowledge_registry import global_disease_registry_engine
from diagnostic_graph_rag import PertinentNegativesEngine
from cpoe_dre_engine import CPOEDREEngine
from patient_persistence_store import PatientPersistenceStore
from main import AppShim


class TestPhase41ClinicalSafetyHardening(unittest.TestCase):

    def setUp(self):
        self.test_db_path = f"test_patient_store_{os.getpid()}_p41.db"
        self.patient_store = PatientPersistenceStore(db_path=self.test_db_path)
        self.cpoe = CPOEDREEngine(tenant_id="TENANT-TEST-41", persistence_store=self.patient_store)
        self.pertinent_engine = PertinentNegativesEngine()
        self.app_shim = AppShim()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    # ----------------------------------------------------------------------------------------------
    # 1. OUT-OF-DISTRIBUTION (OOD) ABSTENTION GATE TESTS
    # ----------------------------------------------------------------------------------------------

    def test_01_ood_abstention_gate_on_unindexed_complex_case(self):
        """Verifies OOD abstention gate withholds automated diagnosis when findings do not match registry."""
        # Unindexed rare presentation (e.g. Addisonian crisis / TTP with unindexed SNOMED codes)
        res = global_disease_registry_engine.evaluate_case_with_ood_gate(
            present_snomed_ids={"999999001", "999999002"},
            absent_snomed_ids=set()
        )
        self.assertTrue(res["ood_abstention_triggered"])
        self.assertEqual(res["diagnostic_status"], "OUT_OF_DISTRIBUTION_PATHOLOGY_UNRECOGNIZED_MANDATORY_SPECIALIST_REFERRAL")
        self.assertEqual(res["confidence_level"], "LOW_CONFIDENCE_UNINDEXED_PATHOLOGY")
        self.assertIsNone(res["top_match_disease_key"])
        self.assertIn("STATUTORY CLINICAL SAFETY ADVISORY", res["safety_advisory"])
        self.assertIn("Immediate senior multidisciplinary consultation", res["safety_advisory"])

    def test_02_in_distribution_case_passes_safely(self):
        """Verifies in-distribution classical presentation correctly identifies condition with high confidence."""
        # Classical STEMI: Chest pain (29857009) + Cold sweat (52613005) + ECG ST Elevation (164868007)
        res = global_disease_registry_engine.evaluate_case_with_ood_gate(
            present_snomed_ids={"29857009", "52613005", "164868007"},
            absent_snomed_ids=set()
        )
        self.assertFalse(res["ood_abstention_triggered"])
        self.assertEqual(res["diagnostic_status"], "IN_DISTRIBUTION_DIAGNOSTIC_CONSIDERATION")
        self.assertEqual(res["top_match_disease_key"], "ACUTE_MYOCARDIAL_INFARCTION")
        self.assertGreater(res["top_match_posterior_probability"], 0.70)
        self.assertIn(res["confidence_level"], ["HIGH_CONFIDENCE", "MODERATE_CONFIDENCE"])

    def test_03_pertinent_negatives_engine_ood_gate(self):
        """Verifies PertinentNegativesEngine in diagnostic_graph_rag supports OOD abstention."""
        # Empty / unindexed findings
        res_ood = self.pertinent_engine.evaluate_differential_with_ood_gate(
            present_snomed_ids={"999999099"},
            absent_snomed_ids=set()
        )
        self.assertTrue(res_ood["ood_abstention_triggered"])
        self.assertEqual(res_ood["diagnostic_status"], "OUT_OF_DISTRIBUTION_PATHOLOGY_UNRECOGNIZED_MANDATORY_SPECIALIST_REFERRAL")

        # In-distribution thunderclap headache
        res_indist = self.pertinent_engine.evaluate_differential_with_ood_gate(
            present_snomed_ids={"25064002", "423341008"},  # Headache + Thunderclap
            absent_snomed_ids=set()
        )
        self.assertFalse(res_indist["ood_abstention_triggered"])
        self.assertEqual(res_indist["diagnostic_status"], "IN_DISTRIBUTION_DIAGNOSTIC_CONSIDERATION")

    # ----------------------------------------------------------------------------------------------
    # 2. COMBINATORIAL POLYPHARMACY TESTS ("TRIPLE WHAMMY" & ADDITIVE QTC)
    # ----------------------------------------------------------------------------------------------

    def test_04_polypharmacy_triple_whammy_interception(self):
        """Verifies ACEi + Diuretic + NSAID combination is intercepted with critical hard-stop."""
        # Patient taking Ramipril (ACEi) and Furosemide (Diuretic) is prescribed Ibuprofen (NSAID)
        eval_res = self.cpoe.evaluate_order(
            patient_id="PAT-P41-01",
            drug_name="Ibuprofen",
            prescribed_dose=400.0,
            current_medications=["Ramipril 5mg", "Furosemide 40mg"]
        )
        self.assertEqual(eval_res["status"], "BLOCKED")
        whammy_stops = [hs for hs in eval_res["hard_stops"] if "COMBINATORIAL TRIPLE WHAMMY" in hs]
        self.assertGreaterEqual(len(whammy_stops), 1)
        self.assertIn("Acute Kidney Injury", whammy_stops[0])

    def test_05_polypharmacy_standalone_risk_screen(self):
        """Verifies check_combinatorial_polypharmacy_risks detects multi-drug interactions across regimen."""
        # Triple Whammy regimen: Losartan + Hydrochlorothiazide + Diclofenac
        res = self.cpoe.check_combinatorial_polypharmacy_risks(["Losartan", "Hydrochlorothiazide", "Diclofenac"])
        self.assertTrue(res["is_blocked"])
        self.assertGreaterEqual(res["detected_risks_count"], 1)
        whammy_risk = next(r for r in res["risks"] if r["risk_type"] == "COMBINATORIAL_TRIPLE_WHAMMY")
        self.assertEqual(whammy_risk["severity"], "CRITICAL_HARD_STOP")

    def test_06_additive_qtc_surveillance(self):
        """Verifies additive QTc surveillance flags multiple QT-prolonging drugs."""
        # Patient on Amiodarone is ordered Azithromycin and Ondansetron
        res = self.cpoe.check_combinatorial_polypharmacy_risks(["Amiodarone", "Azithromycin", "Ondansetron"])
        qt_risk = next((r for r in res["risks"] if r["risk_type"] == "POLYPHARMACY_ADDITIVE_QTC"), None)
        self.assertIsNotNone(qt_risk)
        self.assertEqual(qt_risk["severity"], "MAJOR_WARNING")
        self.assertIn("Torsades de Pointes", qt_risk["clinical_syndrome"])
        self.assertGreaterEqual(len(qt_risk["implicated_drugs"]), 2)

    # ----------------------------------------------------------------------------------------------
    # 3. ELIMINATING SILENT DEFAULTS & LONGITUDINAL AUTO-HYDRATION
    # ----------------------------------------------------------------------------------------------

    def test_07_unspecified_allergy_safeguard(self):
        """Verifies prescribing high-risk drug under unspecified allergy status triggers clinical warning."""
        eval_res = self.cpoe.evaluate_order(
            patient_id="PAT-P41-02",
            drug_name="Amoxicillin",
            prescribed_dose=500.0,
            known_allergies=["ALLERGY_STATUS_UNSPECIFIED"]
        )
        self.assertIn("WARNINGS_EXIST", eval_res["status"])
        unspecified_warns = [w for w in eval_res["warnings"] if "UNSPECIFIED_ALLERGY_HIGH_RISK_MEDICATION" in w]
        self.assertGreaterEqual(len(unspecified_warns), 1)
        self.assertIn("Active clinical allergy interview mandatory", unspecified_warns[0])

    def test_08_longitudinal_auto_hydration_via_appshim(self):
        """Verifies AppShim diagnostic evaluation auto-hydrates patient chronic problems from persistence store."""
        from patient_persistence_store import global_patient_persistence_store
        p_res = global_patient_persistence_store.register_patient(name="Subhashish Roy", age=68, gender="M")
        patient_id = p_res["patient_id"]
        global_patient_persistence_store.add_problem(patient_id=patient_id, diagnosis_name="Chronic Hypertension", condition_snomed="38341003", condition_icd11="BA00")
        global_patient_persistence_store.add_allergy(patient_id=patient_id, allergen_name="Sulfa", severity="SEVERE")

        # Diagnostic evaluation passing only acute chest pain ("29857009") with patient_id
        diff_res = self.app_shim.evaluate_clinical_differential(
            present_snomed_ids=["29857009"],
            patient_id=patient_id,
            enable_ood_gate=True
        )

        self.assertIn("hydrated_patient_context", diff_res)
        ctx = diff_res["hydrated_patient_context"]
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["patient_id"], patient_id)
        self.assertEqual(ctx["hydrated_allergies_count"], 1)
        self.assertIn("Chronic Hypertension", ctx["hydrated_chronic_problems"])

    def test_09_check_polypharmacy_route_via_appshim(self):
        """Verifies AppShim check_polypharmacy_risks provides seamless edge parity."""
        poly_res = self.app_shim.check_polypharmacy_risks(["Telmisartan", "Torsemide", "Naproxen"])
        self.assertTrue(poly_res["is_blocked"])
        self.assertEqual(poly_res["risks"][0]["risk_type"], "COMBINATORIAL_TRIPLE_WHAMMY")


if __name__ == "__main__":
    unittest.main()
