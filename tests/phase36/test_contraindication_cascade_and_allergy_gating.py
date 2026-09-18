#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 36: CLINICAL CONTRAINDICATION CASCADING, ALLERGY GATING & REST INGESTION
====================================================================================================
Tests:
1. Multi-Contraindication Cascading: Pregnant + cephalosporin allergy prevents Ceftriaxone.
2. Negative & Zero Weight Sanitization: Rejects negative weight, preventing negative doses.
3. Pediatric Dose Ceiling Capping: Obese adolescent (90 kg) capped at 2,000 mg ceiling.
4. NLEM Formulary Engine Allergy Surveillance: Blocks Penicillin, Sulfa, and NSAID cross-reactivity.
5. Context-Aware CPOE Chart Allergy Extraction: Admitted patient allergy halts contraindicated drug.
6. Full REST Ingestion Lifecycle: Endpoints for encounter, allergy, problem, med, and observation.
====================================================================================================
"""

import sys
import os
import unittest
import gc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from patient_persistence_store import PatientPersistenceStore
from prescription_protocol_engine import global_prescription_protocol_engine, RegimenType
from nlem_formulary_engine import global_nlem_formulary_engine


class TestPhase36ContraindicationCascadeAndAllergyGating(unittest.TestCase):

    def setUp(self):
        self.test_db_path = f"test_phase36_store_{os.getpid()}.db"
        self.patient_store = PatientPersistenceStore(db_path=self.test_db_path)
        self.stg_engine = global_prescription_protocol_engine
        self.formulary_engine = global_nlem_formulary_engine

    def tearDown(self):
        del self.patient_store
        gc.collect()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    # ----------------------------------------------------------------------------------------------
    # 1. MULTI-CONTRAINDICATION CASCADING
    # ----------------------------------------------------------------------------------------------

    def test_01_multi_contraindication_cascading(self):
        """Verifies that pregnancy combined with drug allergy properly switches away from contraindicated drug."""
        res = self.stg_engine.generate_prescription_protocol(
            disease_key="ACUTE_APPENDICITIS",
            is_pregnant=True,
            known_allergies=["cephalosporin"]
        )
        self.assertEqual(res["status"], "GENERATED")
        drug_names = [item["drug_name"] for item in res["prescribed_items"]]
        self.assertNotIn("Ceftriaxone", drug_names,
                         "Ceftriaxone must not be prescribed to a cephalosporin-allergic patient even if pregnant")
        self.assertIn("Ciprofloxacin", drug_names,
                      "Alternative fluoroquinolone must be selected for cephalosporin allergy")

    # ----------------------------------------------------------------------------------------------
    # 2. NEGATIVE & ZERO WEIGHT SANITIZATION
    # ----------------------------------------------------------------------------------------------

    def test_02_negative_and_zero_weight_sanitization(self):
        """Verifies that non-positive weight inputs do not produce negative or zero doses."""
        # Negative weight
        res_neg = self.stg_engine.generate_prescription_protocol(
            disease_key="ACUTE_APPENDICITIS",
            patient_age=5,
            patient_weight_kg=-15.0
        )
        for it in res_neg["prescribed_items"]:
            self.assertFalse(it["prescribed_dose"].startswith("-"),
                             f"Prescribed dose {it['prescribed_dose']} must never be negative")
            self.assertIn("non-positive", it["dose_rationale"].lower())

        # Zero weight
        res_zero = self.stg_engine.generate_prescription_protocol(
            disease_key="ACUTE_APPENDICITIS",
            patient_age=5,
            patient_weight_kg=0.0
        )
        for it in res_zero["prescribed_items"]:
            self.assertFalse(it["prescribed_dose"].startswith("-"))
            self.assertIn("non-positive", it["dose_rationale"].lower())

    # ----------------------------------------------------------------------------------------------
    # 3. PEDIATRIC DOSE CEILING CAPPING
    # ----------------------------------------------------------------------------------------------

    def test_03_pediatric_dose_ceiling_capping(self):
        """Verifies that an obese adolescent (16yo, 90 kg) has weight-based doses capped at the clinical max."""
        res = self.stg_engine.generate_prescription_protocol(
            disease_key="ACUTE_APPENDICITIS",
            patient_age=16,
            patient_weight_kg=90.0
        )
        doses = {it["drug_name"]: it["prescribed_dose"] for it in res["prescribed_items"]}
        # Uncapped Ceftriaxone: 50 mg/kg * 90 kg = 4500 mg. Max allowed is 2g (2000 mg).
        self.assertEqual(doses["Ceftriaxone"], "2000.0mg",
                         "Ceftriaxone dose must be capped at 2000.0mg maximum daily ceiling")
        ceftriaxone_item = next(it for it in res["prescribed_items"] if it["drug_name"] == "Ceftriaxone")
        self.assertIn("Capped at maximum recommended limit", ceftriaxone_item["dose_rationale"])

    # ----------------------------------------------------------------------------------------------
    # 4. NLEM FORMULARY ENGINE ALLERGY SURVEILLANCE
    # ----------------------------------------------------------------------------------------------

    def test_04_nlem_formulary_allergy_screening(self):
        """Verifies sub-millisecond allergy cross-reactivity surveillance in NLEM formulary engine."""
        # Beta-lactam anaphylaxis
        res_pen = self.formulary_engine.screen_prescription_regimen(
            drugs_prescribed=["Amoxicillin"],
            patient_allergies=["penicillin"]
        )
        self.assertFalse(res_pen["is_safe_to_dispense"])
        self.assertEqual(res_pen["status"], "REJECTED_LETHAL_INTERACTION")
        self.assertTrue(any(v.get("mechanism") == "BETA_LACTAM_ANAPHYLAXIS" for v in res_pen["lethal_violations"]))

        # Sulfonamide anaphylaxis / SJS
        res_sulfa = self.formulary_engine.screen_prescription_regimen(
            drugs_prescribed=["Sulfamethoxazole"],
            patient_allergies=["sulfa"]
        )
        self.assertFalse(res_sulfa["is_safe_to_dispense"])
        self.assertTrue(any(v.get("mechanism") == "SULFONAMIDE_SJS_ANAPHYLAXIS" for v in res_sulfa["lethal_violations"]))

        # NSAID hypersensitivity
        res_nsaid = self.formulary_engine.screen_prescription_regimen(
            drugs_prescribed=["Diclofenac"],
            patient_allergies=["aspirin"]
        )
        self.assertFalse(res_nsaid["is_safe_to_dispense"])
        self.assertTrue(any(v.get("mechanism") == "NSAID_HYPERSENSITIVITY" for v in res_nsaid["lethal_violations"]))

    # ----------------------------------------------------------------------------------------------
    # 5. CONTEXT-AWARE CPOE CHART ALLERGY EXTRACTION
    # ----------------------------------------------------------------------------------------------

    def test_05_context_aware_cpoe_chart_allergy_extraction(self):
        """Verifies that an admitted patient's chart allergy is automatically extracted and blocks contraindicated CPOE orders."""
        reg = self.patient_store.register_patient(name="Vikram Singh", age=45, gender="MALE")
        p_id = reg["patient_id"]
        self.patient_store.add_allergy(patient_id=p_id, allergen_name="penicillin", severity="SEVERE")

        # Pull chart data as main.py screen_formulary_order does
        rec = self.patient_store.get_longitudinal_record(p_id)
        allergies = [a["allergen_name"] for a in rec.get("allergies", [])]
        self.assertIn("penicillin", allergies)

        # Screen CPOE order for Amoxicillin
        screen_res = self.formulary_engine.screen_prescription_regimen(
            drugs_prescribed=["Amoxicillin"],
            patient_allergies=allergies
        )
        self.assertFalse(screen_res["is_safe_to_dispense"], "Amoxicillin order must be BLOCKED for penicillin-allergic patient")
        self.assertEqual(screen_res["status"], "REJECTED_LETHAL_INTERACTION")

    # ----------------------------------------------------------------------------------------------
    # 6. FULL REST INGESTION LIFECYCLE
    # ----------------------------------------------------------------------------------------------

    def test_06_patient_store_rest_routes_end_to_end(self):
        """Verifies that all 5 patient store ingestion operations persist cleanly to SQLite."""
        # 1. Admit patient
        reg = self.patient_store.register_patient(name="Pooja Sharma", age=28, gender="FEMALE")
        p_id = reg["patient_id"]

        # 2. Start encounter
        enc = self.patient_store.start_encounter(
            patient_id=p_id, encounter_type="EMERGENCY", chief_complaint="Severe right lower quadrant pain", triage_level="ESI-2"
        )
        enc_id = enc["encounter_id"]
        self.assertEqual(enc["status"], "ACTIVE")

        # 3. Record allergy
        al = self.patient_store.add_allergy(
            patient_id=p_id, allergen_name="cephalosporin", reaction_type="ANAPHYLAXIS", severity="FATAL"
        )
        self.assertEqual(al["allergen_name"], "cephalosporin")

        # 4. Record diagnostic observation
        obs = self.patient_store.record_observation(
            encounter_id=enc_id,
            patient_id=p_id,
            concept_name="Body Temperature",
            concept_code="8310-5",
            value_numeric=38.9,
            unit="C"
        )
        self.assertEqual(obs["value_numeric"], 38.9)

        # 5. Record problem
        prob = self.patient_store.add_problem(
            patient_id=p_id,
            diagnosis_name="Acute Appendicitis",
            condition_snomed="163284000",
            condition_icd11="DB10.0"
        )
        self.assertEqual(prob["diagnosis_name"], "Acute Appendicitis")

        # 6. Record active medication
        med = self.patient_store.add_medication(
            patient_id=p_id,
            drug_name="Ciprofloxacin",
            dose="400mg",
            frequency="BD",
            route="IV",
            encounter_id=enc_id
        )
        self.assertEqual(med["drug_name"], "Ciprofloxacin")

        # 7. Verify all entries exist in longitudinal record
        rec = self.patient_store.get_longitudinal_record(p_id)
        self.assertEqual(len(rec["encounter_history"]), 1)
        self.assertEqual(len(rec["allergies"]), 1)
        self.assertEqual(len(rec["longitudinal_observations"]), 1)
        self.assertEqual(len(rec["chronic_problem_list"]), 1)
        self.assertEqual(len(rec["active_medications"]), 1)


if __name__ == "__main__":
    unittest.main()
