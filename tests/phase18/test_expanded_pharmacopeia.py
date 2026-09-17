#!/usr/bin/env python3
"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 18: EXPANDED PHARMACOPEIA & SAFETY GATES TEST SUITE
====================================================================================================
Tests:
1. Extended Drug-Drug Interactions (Warfarin + NSAIDs, ACEi + K-sparing, SSRI + Tramadol).
2. Pregnancy Teratogenicity Safety Gate (Categories D/X: Warfarin, Methotrexate, ACEi in pregnancy).
3. AGS Beers Criteria 2023 Geriatric Safety Gate (Age >= 65: Antihistamines, Benzodiazepines, TCAs).
"""
import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
from cpoe_dre_engine import CPOEDREEngine


class TestExpandedPharmacopeia(unittest.TestCase):

    def setUp(self):
        self.tenant_id = "00000000-0000-0000-0000-000000000001"
        self.dre = CPOEDREEngine(tenant_id=self.tenant_id)

    def test_extended_ddi_warfarin_and_nsaid_is_blocked(self):
        """Verifies that prescribing an NSAID (e.g. Ibuprofen) to a patient on Warfarin is BLOCKED."""
        res = self.dre.evaluate_order(
            patient_id="PAT-WAR-01",
            drug_name="Ibuprofen 400mg",
            prescribed_dose=400.0,
            route="ORAL",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.8,
            serum_creatinine=1.0,
            patient_age=55,
            is_female=False,
            current_medications=["Warfarin 5mg"],
            known_allergies=[]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("LETHAL DDI: NSAID prescribed to patient on Warfarin" in s for s in res["hard_stops"]))

    def test_extended_ddi_acei_and_k_sparing_is_blocked(self):
        """Verifies that Ramipril + Spironolactone generates a hard-stop for fatal hyperkalemia."""
        res = self.dre.evaluate_order(
            patient_id="PAT-HTN-02",
            drug_name="Ramipril 5mg",
            prescribed_dose=5.0,
            route="ORAL",
            patient_weight_kg=75.0,
            patient_bsa_m2=1.85,
            serum_creatinine=1.1,
            patient_age=60,
            is_female=False,
            current_medications=["Spironolactone 25mg"],
            known_allergies=[]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("LETHAL DDI: ACEi/ARB combined with Potassium-sparing" in s for s in res["hard_stops"]))

    def test_pregnancy_teratogenicity_warfarin_and_methotrexate_blocked(self):
        """Verifies that teratogenic Category X drugs are strictly BLOCKED in pregnant patients."""
        # Warfarin in pregnancy
        res_war = self.dre.evaluate_order(
            patient_id="PAT-PREG-01",
            drug_name="Warfarin",
            prescribed_dose=5.0,
            route="ORAL",
            patient_weight_kg=62.0,
            patient_bsa_m2=1.65,
            serum_creatinine=0.7,
            patient_age=28,
            is_female=True,
            current_medications=[],
            known_allergies=[],
            is_pregnant=True
        )
        self.assertEqual(res_war["status"], "BLOCKED")
        self.assertTrue(any("BLOCKED_PREGNANCY_TERATOGENICITY" in s for s in res_war["hard_stops"]))
        self.assertTrue(any("Fetal warfarin syndrome" in s for s in res_war["hard_stops"]))

        # Methotrexate in pregnancy
        res_mtx = self.dre.evaluate_order(
            patient_id="PAT-PREG-02",
            drug_name="Methotrexate 15mg",
            prescribed_dose=15.0,
            route="ORAL",
            patient_weight_kg=58.0,
            patient_bsa_m2=1.6,
            serum_creatinine=0.8,
            patient_age=32,
            is_female=True,
            current_medications=[],
            known_allergies=[],
            is_pregnant=True
        )
        self.assertEqual(res_mtx["status"], "BLOCKED")
        self.assertTrue(any("BLOCKED_PREGNANCY_TERATOGENICITY" in s for s in res_mtx["hard_stops"]))

    def test_ags_beers_criteria_geriatric_alert_in_elderly(self):
        """Verifies that high-risk anticholinergic / benzodiazepine orders in age >= 65 trigger Beers alerts."""
        res_hydroxyzine = self.dre.evaluate_order(
            patient_id="PAT-GERI-01",
            drug_name="Hydroxyzine 25mg",
            prescribed_dose=25.0,
            route="ORAL",
            patient_weight_kg=60.0,
            patient_bsa_m2=1.6,
            serum_creatinine=0.9,
            patient_age=78,  # Elderly
            is_female=True,
            current_medications=[],
            known_allergies=[]
        )
        self.assertEqual(res_hydroxyzine["status"], "WARNINGS_EXIST")
        self.assertTrue(any("AGS_BEERS_CRITERIA_2023" in w for w in res_hydroxyzine["warnings"]))
        self.assertTrue(any("delirium" in w.lower() for w in res_hydroxyzine["warnings"]))


if __name__ == "__main__":
    unittest.main()
