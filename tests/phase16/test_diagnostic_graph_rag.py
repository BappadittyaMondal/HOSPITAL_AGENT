"""
====================================================================================================
TEST SUITE: PHASE 16.1 — ONTOLOGICAL GRAPH-RAG & PERTINENT NEGATIVES ENGINE
====================================================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from diagnostic_graph_rag import (
    ClinicalConceptMapper,
    PertinentNegativesEngine,
    CognitiveDeBiasingMatrix,
    DiagnosticGraphRAGEngine,
    RedFlagRuleOutRequiredError,
    UnmappedClinicalConceptError
)


class TestDiagnosticGraphRAG(unittest.TestCase):

    def setUp(self):
        self.engine = DiagnosticGraphRAGEngine()

    def test_vernacular_concept_resolution(self):
        """Verifies multi-lingual Bengali and Hindi terms map to exact SNOMED CT concepts."""
        mapper = self.engine.mapper

        # Bengali "বুক ধড়ফড়" -> Palpitations
        bengali_palp = mapper.resolve("বুক ধড়ফড়")
        self.assertEqual(bengali_palp["snomed_id"], "271594007")
        self.assertEqual(bengali_palp["preferred_term"], "Palpitations")

        # Bengali "বুকে চাপ" -> Chest pain
        bengali_chest = mapper.resolve("বুকে চাপ")
        self.assertEqual(bengali_chest["snomed_id"], "29857009")

        # Hindi "seene mein dard" -> Chest pain
        hindi_chest = mapper.resolve("seene mein dard")
        self.assertEqual(hindi_chest["snomed_id"], "29857009")

        # Bengali "পেটে গ্যাস" -> Dyspepsia
        gas_res = mapper.resolve("পেটে গ্যাস")
        self.assertEqual(gas_res["snomed_id"], "28539006")

    def test_unmapped_concept_raises_error(self):
        """Verifies completely nonsensical/hallucinated terms fail with strict exception."""
        mapper = self.engine.mapper
        with self.assertRaises(UnmappedClinicalConceptError):
            mapper.resolve("completely_unknown_medical_gibberish_xyz")

    def test_pertinent_negatives_likelihood_ratio_calculation(self):
        """Verifies that an absent finding with high sensitivity drastically reduces disease odds."""
        # Patient has Dyspnea, but D-Dimer is strictly NEGATIVE
        analysis = self.engine.analyze_presentation(
            present_terms=["Dyspnea"],
            absent_terms=["Elevated D-dimer"]
        )

        diffs = {d["disease_key"]: d for d in analysis["differentials"]}
        pe = diffs["PULMONARY_EMBOLISM"]

        # For PE, D-dimer sensitivity is 0.96. LR- = (1 - 0.96) / 0.50 = 0.08
        # The presence of negative D-dimer should apply a reducing LR of ~0.08
        d_dimer_neg_finding = next(f for f in pe["applied_findings"] if f["snomed_id"] == "274092004")
        self.assertEqual(d_dimer_neg_finding["status"], "PERTINENT_NEGATIVE")
        self.assertEqual(d_dimer_neg_finding["effect"], "DECREASED_PROBABILITY")
        self.assertLess(d_dimer_neg_finding["lr_applied"], 0.1)

        # Posterior probability of PE is suppressed despite dyspnea
        self.assertLess(pe["posterior_probability"], pe["prior_probability"])

    def test_cognitive_debiasing_blocks_benign_diagnosis_when_red_flags_unruled_out(self):
        """Quality Gate 1: Attempting to confirm 'GERD/Gas' for chest pain without ECG/Troponin is BLOCKED."""
        debiasing = self.engine.debiasing

        # Patient presented with chest pain (29857009)
        present_snomed = {"29857009"}
        # Clinician has NOT performed ECG (164868007) or Troponin (102685005)
        completed_investigations = set()

        # Doctor attempts to sign off on benign diagnosis GASTROESOPHAGEAL_REFLUX
        with self.assertRaises(RedFlagRuleOutRequiredError) as ctx:
            debiasing.verify_safe_discharge_or_benign_diagnosis(
                present_snomed_ids=present_snomed,
                completed_investigations=completed_investigations,
                proposed_diagnosis_key="GASTROESOPHAGEAL_REFLUX"
            )
        self.assertIn("COGNITIVE DE-BIASING HARD-STOP", str(ctx.exception))
        self.assertIn("Acute Coronary Syndrome", str(ctx.exception))

    def test_cognitive_debiasing_allows_benign_diagnosis_when_red_flags_are_cleared(self):
        """Verifies benign diagnosis is authorized once mandatory investigations are documented."""
        debiasing = self.engine.debiasing
        present_snomed = {"29857009", "28539006"}

        # Doctor completed ECG, Troponin, and D-dimer rule-outs
        completed_investigations = {"164868007", "102685005", "274092004"}

        result = debiasing.verify_safe_discharge_or_benign_diagnosis(
            present_snomed_ids=present_snomed,
            completed_investigations=completed_investigations,
            proposed_diagnosis_key="GASTROESOPHAGEAL_REFLUX"
        )
        self.assertEqual(result["status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
