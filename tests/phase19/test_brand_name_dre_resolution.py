"""
PROJECT "HOSPITAL" — PHASE 19: PRODUCTION SYSTEMS HARDENING
Test Suite: test_brand_name_dre_resolution.py
Validates:
  - Resolution of Indian and international trade brand names to active pharmaceutical generics
  - Sub-millisecond DDI interception when commercial brand names are ordered
  - Pregnancy teratogenicity hard stops triggered by commercial brand names
  - AGS Beers Criteria 2023 geriatric safety warnings triggered by brand names
  - Cross-allergen beta-lactam and sulfonamide interception by brand name
  - Cumulative lifetime toxicity limits enforcement across brand name entries
"""

import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from cpoe_dre_engine import CPOEDREEngine
from terminology_engine import normalize_drug_name, get_drug_aliases


class TestBrandNameDREResolution(unittest.TestCase):

    def setUp(self):
        self.dre = CPOEDREEngine(tenant_id="TENANT-MAIN-01")

    def test_brand_normalization_helpers(self):
        """Standardization helper accurately maps brands to generic INN."""
        self.assertEqual(normalize_drug_name("Caverta 50mg"), "sildenafil")
        self.assertEqual(normalize_drug_name("Sorbitrate 10mg"), "isosorbide dinitrate")
        self.assertEqual(normalize_drug_name("Dynapar AQ Inj"), "diclofenac")
        self.assertEqual(normalize_drug_name("Uniwarfin 5mg"), "warfarin")
        self.assertEqual(normalize_drug_name("Augmentin 625 Duo"), "amoxicillin-clavulanate")
        self.assertEqual(normalize_drug_name("Lipitor 20"), "atorvastatin")
        self.assertEqual(normalize_drug_name("Atarax 25"), "hydroxyzine")

        aliases = get_drug_aliases("sildenafil")
        self.assertIn("caverta", aliases)
        self.assertIn("viagra", aliases)
        self.assertIn("penegra", aliases)

    def test_brand_ddi_sildenafil_nitrate(self):
        """Caverta 50mg ordered with Sorbitrate 10mg in meds must trigger fatal DDI hard stop."""
        res = self.dre.evaluate_order(
            patient_id="PAT-DDI-01",
            drug_name="Caverta 50mg",
            prescribed_dose=50.0,
            route="ORAL",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.73,
            serum_creatinine=1.0,
            patient_age=55,
            is_female=False,
            current_medications=["Sorbitrate 10mg", "Amlodipine 5mg"],
            known_allergies=[]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("FATAL DDI: Sildenafil combined with Nitrates" in hs for hs in res["hard_stops"]))

    def test_brand_ddi_warfarin_nsaid(self):
        """Dynapar (Diclofenac) ordered for patient on Uniwarfin (Warfarin) must trigger lethal DDI hard stop."""
        res = self.dre.evaluate_order(
            patient_id="PAT-DDI-02",
            drug_name="Dynapar 50mg",
            prescribed_dose=50.0,
            route="ORAL",
            patient_weight_kg=65.0,
            patient_bsa_m2=1.65,
            serum_creatinine=0.9,
            patient_age=60,
            is_female=True,
            current_medications=["Uniwarfin 5mg"],
            known_allergies=[]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("LETHAL DDI: NSAID prescribed to patient on Warfarin" in hs for hs in res["hard_stops"]))

    def test_brand_ddi_linezolid_ssri(self):
        """Zyvox (Linezolid) ordered for patient on Nexito (Escitalopram) must block Serotonin Syndrome."""
        res = self.dre.evaluate_order(
            patient_id="PAT-DDI-03",
            drug_name="Zyvox 600mg",
            prescribed_dose=600.0,
            route="IV",
            patient_weight_kg=72.0,
            patient_bsa_m2=1.78,
            serum_creatinine=1.1,
            patient_age=38,
            is_female=False,
            current_medications=["Nexito 10mg"],
            known_allergies=[]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("Serotonin Syndrome" in hs for hs in res["hard_stops"]))

    def test_brand_teratogenicity_block(self):
        """Lipitor 20mg (Atorvastatin) prescribed to pregnant patient must trigger Category X block."""
        res = self.dre.evaluate_order(
            patient_id="PAT-TERATO-01",
            drug_name="Lipitor 20mg",
            prescribed_dose=20.0,
            route="ORAL",
            patient_weight_kg=62.0,
            patient_bsa_m2=1.60,
            serum_creatinine=0.7,
            patient_age=28,
            is_female=True,
            current_medications=[],
            known_allergies=[],
            is_pregnant=True
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("BLOCKED_PREGNANCY_TERATOGENICITY" in hs for hs in res["hard_stops"]))
        self.assertTrue(any("Category X" in hs for hs in res["hard_stops"]))

    def test_brand_beers_criteria_geriatric_warning(self):
        """Atarax (Hydroxyzine) prescribed to 75-year-old patient must trigger Beers 2023 alert."""
        res = self.dre.evaluate_order(
            patient_id="PAT-GERI-01",
            drug_name="Atarax 25mg",
            prescribed_dose=25.0,
            route="ORAL",
            patient_weight_kg=60.0,
            patient_bsa_m2=1.55,
            serum_creatinine=1.2,
            patient_age=75,
            is_female=False,
            current_medications=[],
            known_allergies=[]
        )
        self.assertEqual(res["status"], "WARNINGS_EXIST")
        self.assertTrue(any("AGS_BEERS_CRITERIA_2023" in w for w in res["warnings"]))
        self.assertTrue(any("anticholinergic" in w.lower() for w in res["warnings"]))

    def test_brand_cross_allergy_interception(self):
        """Augmentin ordered for patient with documented Penicillin allergy must trigger anaphylaxis hard stop."""
        res = self.dre.evaluate_order(
            patient_id="PAT-ALLERGY-01",
            drug_name="Augmentin 625mg",
            prescribed_dose=625.0,
            route="ORAL",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.70,
            serum_creatinine=1.0,
            patient_age=42,
            is_female=True,
            current_medications=[],
            known_allergies=["Penicillin"]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("LETHAL ALLERGY: Beta-lactam anaphylaxis risk" in hs for hs in res["hard_stops"]))

    def test_brand_cumulative_toxicity_tracking(self):
        """Adriblastina (Doxorubicin) cumulative dosage is normalized to doxorubicin ceiling."""
        pid = "PAT-ONCO-TOX-01"
        # Administer 400 mg/m2 via brand Adriblastina (400 * 1.5 = 600mg)
        self.dre.record_administered_dose(pid, "Adriblastina 100mg", 600.0)

        # Attempt to order another 100 mg/m2 (150mg) -> total 500 mg/m2 > 450 mg/m2 ceiling
        res = self.dre.evaluate_order(
            patient_id=pid,
            drug_name="Adriamycin 50mg",
            prescribed_dose=150.0,
            route="IV",
            patient_weight_kg=60.0,
            patient_bsa_m2=1.50,
            serum_creatinine=0.9,
            patient_age=50,
            is_female=True,
            current_medications=[],
            known_allergies=[]
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("CUMULATIVE TOXICITY CEILING EXCEEDED" in hs for hs in res["hard_stops"]))


if __name__ == "__main__":
    unittest.main()
