#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 35: END-TO-END PIPELINE & STG PRESCRIPTION TESTS
====================================================================================================
Tests:
1. Context-Aware CPOE Prescribing: Admitted patient with active Warfarin blocks new Diclofenac order.
2. STG Prescription Generation - Acute MI: Full evidence-based protocol with pre-screened safety.
3. STG Prescription Generation - Bacterial Meningitis: High-dose cephalosporin + vancomycin + steroid.
4. STG Pediatric Weight-Based Dosing: Precise mg/kg arithmetic for pediatric appendicitis.
5. STG Allergy-Driven Regimen Substitution: Beta-lactam anaphylaxis triggers ciprofloxacin/metronidazole.
6. STG Pregnancy Teratogen Substitution: Scrub typhus switches from Doxycycline to Azithromycin.
7. Patient Persistence Store Lifecycle - Discharge: Encounter discharge disposition persistence.
8. Patient Persistence Store Lifecycle - Discontinue & Resolve: Medication stop and problem resolution.
9. Diagnostic DAG Synchronization & Intake Semantics: Authoritative registry sync & diaphoresis SNOMED.
====================================================================================================
"""

import sys
import os
import unittest
import gc
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from patient_persistence_store import PatientPersistenceStore
from prescription_protocol_engine import global_prescription_protocol_engine, STG_PROTOCOL_CATALOG, RegimenType
from nlem_formulary_engine import global_nlem_formulary_engine
from structured_history_engine import StructuredHistoryEngine, FindingPolarity, ChiefComplaintCategory
from diagnostic_graph_rag import DISEASE_KNOWLEDGE_DAG
from disease_knowledge_registry import DISEASE_REGISTRY


class TestPhase35EndToEndPipelineAndSTG(unittest.TestCase):

    def setUp(self):
        self.test_db_path = f"test_phase35_store_{os.getpid()}.db"
        self.patient_store = PatientPersistenceStore(db_path=self.test_db_path)
        self.stg_engine = global_prescription_protocol_engine
        self.history_engine = StructuredHistoryEngine()

    def tearDown(self):
        del self.patient_store
        gc.collect()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    # ----------------------------------------------------------------------------------------------
    # 1. CONTEXT-AWARE CPOE ACTIVE MEDICATION GATING
    # ----------------------------------------------------------------------------------------------

    def test_01_context_aware_cpoe_active_medication_gating(self):
        """Verifies that an admitted patient's active medication (Warfarin) is pulled and blocks lethal NSAID co-prescription."""
        # 1. Register patient and admit with active Warfarin
        reg = self.patient_store.register_patient(
            name="Ramesh Kumar", age=62, gender="MALE", abha_id="ABHA-998877"
        )
        p_id = reg["patient_id"]
        enc = self.patient_store.start_encounter(
            patient_id=p_id, encounter_type="CARDIOLOGY", chief_complaint="Atrial Fibrillation follow-up"
        )
        self.patient_store.add_medication(
            patient_id=p_id, drug_name="Warfarin", dose="5mg", frequency="OD", route="ORAL", encounter_id=enc["encounter_id"]
        )

        # 2. Simulate context-aware CPOE screen for newly ordered Diclofenac
        rec = self.patient_store.get_longitudinal_record(p_id)
        active_med_names = [m["drug_name"] for m in rec["active_medications"]]
        self.assertIn("Warfarin", active_med_names)

        # Merge new order with chart active medications
        newly_ordered = ["Diclofenac"]
        combined_drugs = list(newly_ordered)
        for m_name in active_med_names:
            if m_name not in combined_drugs:
                combined_drugs.append(m_name)

        screen_res = global_nlem_formulary_engine.screen_prescription_regimen(
            drugs_prescribed=combined_drugs,
            patient_is_pregnant=False,
            patient_egfr=90.0
        )

        self.assertFalse(screen_res["is_safe_to_dispense"], "Co-prescription of Diclofenac with active Warfarin must be BLOCKED")
        self.assertTrue(any("warfarin" in v["drug_pair"] and "diclofenac" in v["drug_pair"] for v in screen_res["lethal_violations"]),
                        "Must detect fatal hemorrhagic risk between active Warfarin and newly ordered Diclofenac")

    # ----------------------------------------------------------------------------------------------
    # 2. STANDARD TREATMENT GUIDELINES PRESCRIPTION GENERATION (AMI)
    # ----------------------------------------------------------------------------------------------

    def test_02_stg_prescription_generation_ami(self):
        """Verifies evidence-based STG prescription generation for Acute Myocardial Infarction."""
        res = self.stg_engine.generate_prescription_protocol("ACUTE_MYOCARDIAL_INFARCTION")
        self.assertEqual(res["status"], "GENERATED")
        self.assertEqual(res["regimen_type"], RegimenType.FIRST_LINE.value)

        prescribed_drugs = [item["drug_name"] for item in res["prescribed_items"]]
        self.assertIn("Aspirin", prescribed_drugs)
        self.assertIn("Clopidogrel", prescribed_drugs)
        self.assertIn("Atorvastatin", prescribed_drugs)
        self.assertIn("Heparin", prescribed_drugs)
        self.assertIn("Nitroglycerin", prescribed_drugs)

        # Verify CPOE pre-screening safety
        self.assertTrue(res["formulary_safety_certification"]["safe_to_prescribe"])
        self.assertEqual(len(res["formulary_safety_certification"]["lethal_hard_stops"]), 0)

        # Verify mandatory baseline labs and interventions
        self.assertTrue(any("ECG" in lab for lab in res["mandatory_baseline_labs"]))
        self.assertTrue(any("Troponin" in lab for lab in res["mandatory_baseline_labs"]))
        self.assertTrue(any("Catheterization" in ui or "PCI" in ui for ui in res["urgent_interventions"]))

    # ----------------------------------------------------------------------------------------------
    # 3. STG PRESCRIPTION GENERATION (BACTERIAL MENINGITIS)
    # ----------------------------------------------------------------------------------------------

    def test_03_stg_prescription_generation_bacterial_meningitis(self):
        """Verifies evidence-based STG prescription for Bacterial Meningitis (high-dose Ceftriaxone + Vancomycin + Steroids)."""
        res = self.stg_engine.generate_prescription_protocol("BACTERIAL_MENINGITIS")
        self.assertEqual(res["status"], "GENERATED")

        prescribed = {it["drug_name"]: it["prescribed_dose"] for it in res["prescribed_items"]}
        self.assertIn("Ceftriaxone", prescribed)
        self.assertEqual(prescribed["Ceftriaxone"], "2g", "Bacterial meningitis requires 2g high meningeal dose")
        self.assertIn("Vancomycin", prescribed)
        self.assertIn("Dexamethasone", prescribed)

        # Verify Lumbar puncture and blood cultures in baseline labs
        self.assertTrue(any("Lumbar Puncture" in lab for lab in res["mandatory_baseline_labs"]))
        self.assertTrue(any("Blood cultures" in lab for lab in res["mandatory_baseline_labs"]))

    # ----------------------------------------------------------------------------------------------
    # 4. STG PEDIATRIC WEIGHT-BASED DOSING ARITHMETIC
    # ----------------------------------------------------------------------------------------------

    def test_04_stg_pediatric_weight_based_dosing(self):
        """Verifies exact mg/kg pediatric dose calculations for Acute Appendicitis in an 8-year-old (25 kg)."""
        res = self.stg_engine.generate_prescription_protocol(
            disease_key="ACUTE_APPENDICITIS",
            patient_age=8,
            patient_weight_kg=25.0
        )
        self.assertTrue(res["patient_context"]["is_pediatric"])

        doses = {it["drug_name"]: it["prescribed_dose"] for it in res["prescribed_items"]}
        # Ceftriaxone: 50 mg/kg * 25 kg = 1250.0mg
        self.assertEqual(doses["Ceftriaxone"], "1250.0mg")
        # Metronidazole: 7.5 mg/kg * 25 kg = 187.5mg
        self.assertEqual(doses["Metronidazole"], "187.5mg")
        # Paracetamol: 15.0 mg/kg * 25 kg = 375.0mg
        self.assertEqual(doses["Paracetamol"], "375.0mg")

    # ----------------------------------------------------------------------------------------------
    # 5. STG ALLERGY-DRIVEN REGIMEN SUBSTITUTION
    # ----------------------------------------------------------------------------------------------

    def test_05_stg_allergy_alternative_regimen_switch(self):
        """Verifies that documented beta-lactam allergy automatically substitutes first-line Ceftriaxone with Ciprofloxacin."""
        res = self.stg_engine.generate_prescription_protocol(
            disease_key="ACUTE_APPENDICITIS",
            known_allergies=["penicillin", "cephalosporin"]
        )
        self.assertEqual(res["regimen_type"], RegimenType.ALTERNATIVE_ALLERGY.value)
        drugs = [it["drug_name"] for it in res["prescribed_items"]]
        self.assertNotIn("Ceftriaxone", drugs, "Ceftriaxone must not be prescribed to cephalosporin-allergic patient")
        self.assertIn("Ciprofloxacin", drugs, "Alternative non-beta-lactam fluoroquinolone must be substituted")
        self.assertIn("Metronidazole", drugs)
        self.assertTrue(res["formulary_safety_certification"]["safe_to_prescribe"])

    # ----------------------------------------------------------------------------------------------
    # 6. STG PREGNANCY TERATOGEN SUBSTITUTION
    # ----------------------------------------------------------------------------------------------

    def test_06_stg_pregnancy_teratogen_switch(self):
        """Verifies that Scrub Typhus in pregnancy automatically substitutes teratogenic Doxycycline with Azithromycin."""
        res = self.stg_engine.generate_prescription_protocol(
            disease_key="SCRUB_TYPHUS",
            is_pregnant=True
        )
        self.assertEqual(res["regimen_type"], RegimenType.ALTERNATIVE_PREGNANCY.value)
        drugs = [it["drug_name"] for it in res["prescribed_items"]]
        self.assertNotIn("Doxycycline", drugs, "Doxycycline is teratogenic in pregnancy and must be avoided")
        self.assertIn("Azithromycin", drugs, "Azithromycin is the WHO drug of choice for Scrub Typhus in pregnancy")
        self.assertTrue(res["formulary_safety_certification"]["safe_to_prescribe"])

    # ----------------------------------------------------------------------------------------------
    # 7. PATIENT PERSISTENCE STORE ENCOUNTER DISCHARGE
    # ----------------------------------------------------------------------------------------------

    def test_07_patient_store_encounter_discharge(self):
        """Verifies encounter discharge lifecycle and disposition recording."""
        reg = self.patient_store.register_patient(name="Anita Devi", age=40, gender="FEMALE")
        p_id = reg["patient_id"]
        enc = self.patient_store.start_encounter(patient_id=p_id, encounter_type="EMERGENCY", chief_complaint="Chest pain")
        enc_id = enc["encounter_id"]

        # Discharge encounter
        dis_res = self.patient_store.discharge_encounter(
            encounter_id=enc_id, disposition="HOME_RECOVERED"
        )
        self.assertTrue(dis_res["success"])
        self.assertEqual(dis_res["status"], "DISCHARGED")

        # Verify longitudinal record shows encounter is discharged
        rec = self.patient_store.get_longitudinal_record(p_id)
        enc_found = next(e for e in rec["encounter_history"] if e["encounter_id"] == enc_id)
        self.assertEqual(enc_found["status"], "DISCHARGED")
        self.assertIsNotNone(enc_found["discharged_at"])

    # ----------------------------------------------------------------------------------------------
    # 8. PATIENT STORE LIFECYCLE: DISCONTINUE MEDICATION & RESOLVE PROBLEM
    # ----------------------------------------------------------------------------------------------

    def test_08_patient_store_medication_discontinue_and_problem_resolve(self):
        """Verifies active medication discontinuation and chronic problem resolution."""
        reg = self.patient_store.register_patient(name="Sunil Verma", age=55, gender="MALE")
        p_id = reg["patient_id"]
        enc = self.patient_store.start_encounter(patient_id=p_id, encounter_type="MEDICINE", chief_complaint="Cough")
        enc_id = enc["encounter_id"]

        # Record medication and problem
        med = self.patient_store.add_medication(
            patient_id=p_id, drug_name="Amoxicillin", dose="500mg", frequency="TDS", encounter_id=enc_id
        )
        med_id = med["medication_id"]

        prob = self.patient_store.add_problem(
            patient_id=p_id, diagnosis_name="Acute Bronchitis", condition_snomed="10509002", condition_icd11="CA20"
        )
        prob_id = prob["problem_id"]

        # Discontinue medication
        self.patient_store.discontinue_medication(med_id, reason="COURSE_COMPLETED")
        # Resolve problem
        self.patient_store.resolve_problem(prob_id)

        # Verify in longitudinal record
        rec = self.patient_store.get_longitudinal_record(p_id)
        self.assertEqual(len(rec["active_medications"]), 0, "Discontinued medication must not appear in active medications list")
        self.assertEqual(len(rec["chronic_problem_list"]), 0, "Resolved problem must not appear in active problem list")
        self.assertEqual(len(rec["all_problem_history"]), 1, "Resolved problem must appear in all problem history")
        self.assertEqual(rec["all_problem_history"][0]["status"], "RESOLVED")

    # ----------------------------------------------------------------------------------------------
    # 9. DIAGNOSTIC DAG SYNCHRONIZATION & INTAKE SEMANTICS
    # ----------------------------------------------------------------------------------------------

    def test_09_dag_synchronization_and_intake_semantics(self):
        """Verifies that DISEASE_KNOWLEDGE_DAG is fully synchronized with DISEASE_REGISTRY and intake uses correct SNOMEDs."""
        # 1. Verify DAG has updated mandatory rule outs from DISEASE_REGISTRY
        ami_dag = DISEASE_KNOWLEDGE_DAG["ACUTE_MYOCARDIAL_INFARCTION"]
        ami_reg = DISEASE_REGISTRY["ACUTE_MYOCARDIAL_INFARCTION"]
        self.assertEqual(ami_dag["mandatory_rule_outs"], ami_reg.mandatory_rule_outs,
                         "DAG must be synchronized with authoritative registry rule-outs")

        # 2. Verify StructuredHistoryEngine generates Diaphoresis with SNOMED ID 398602008 (Cold diaphoresis)
        init_res = self.history_engine.initiate_sequential_intake(
            session_id="sess-35-chest",
            patient_id="PAT-CHEST-01",
            chief_complaint=ChiefComplaintCategory.CHEST_PAIN,
            patient_age=58,
            is_female=False
        )
        turn_res = self.history_engine.process_sequential_turn(
            session_id="sess-35-chest",
            question_id="Q_CHEST_DIAPHORESIS",
            answer_value="YES"
        )

        session = self.history_engine._active_sessions["sess-35-chest"]
        diaphoresis_finding = next(
            (f for f in session.findings if f.concept_name == "Diaphoresis"), None
        )
        self.assertIsNotNone(diaphoresis_finding, "Diaphoresis finding must be generated")
        self.assertEqual(diaphoresis_finding.snomed_id, "398602008",
                         "Diaphoresis SNOMED must be 398602008 (Cold diaphoresis), not 247441003")
        self.assertEqual(diaphoresis_finding.polarity, FindingPolarity.PRESENT)


if __name__ == "__main__":
    unittest.main()
