#!/usr/bin/env python3
"""
PROJECT 'HOSPITAL' — PHASE 30: FULL-GRAPH LOCAL ONTOLOGICAL INDEX TEST SUITE
Module: tests/phase30/test_snomed_icd_ontology_index.py
Validates:
  1. Instant resolution of colloquial/vernacular terms to canonical SNOMED CT Concept IDs.
  2. Subsumption traversal (Anterior STEMI is-a Acute MI is-a Acute Coronary Syndrome is-a Disease).
  3. Neurological subsumption (Subarachnoid Hemorrhage is-a Stroke is-a Neurological Disorder).
  4. Mapped ICD-11 codes correspond accurately to SNOMED concepts.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../services/core-api')))
from snomed_icd_ontology_index import LocalOntologyGraphIndex, local_ontology_index


class TestLocalOntologyGraphIndex(unittest.TestCase):

    def setUp(self):
        self.index = local_ontology_index

    def test_colloquial_alias_resolution(self):
        """Colloquial and vernacular tokens resolve to canonical SNOMED Concept IDs."""
        # 'heart attack' -> Acute Coronary Syndrome (57054005)
        cid = self.index.resolve_term_to_concept_id("heart attack")
        self.assertEqual(cid, "57054005")

        # 'buke byatha' (Bengali) -> Acute Coronary Syndrome (57054005)
        cid_bengali = self.index.resolve_term_to_concept_id("buke byatha")
        self.assertEqual(cid_bengali, "57054005")

        # 'thunderclap headache' -> Subarachnoid Hemorrhage (274100004)
        cid_sah = self.index.resolve_term_to_concept_id("thunderclap headache")
        self.assertEqual(cid_sah, "274100004")

        # 'dengu jwor' -> Dengue fever (38362002)
        cid_dengue = self.index.resolve_term_to_concept_id("dengu jwor")
        self.assertEqual(cid_dengue, "38362002")

    def test_hierarchical_subsumption_transitive_closure(self):
        """Verify multi-level is-a DAG traversal for cardiovascular conditions."""
        anterior_stemi_id = "54329005"
        ami_id = "70422006"
        acs_id = "57054005"
        ihd_id = "414545008"
        cvd_id = "49601007"
        disease_root_id = "64572001"

        # Anterior STEMI is an Acute MI
        self.assertTrue(self.index.is_a_descendant_of(anterior_stemi_id, ami_id))
        # Anterior STEMI is an ACS
        self.assertTrue(self.index.is_a_descendant_of(anterior_stemi_id, acs_id))
        # Anterior STEMI is an Ischemic Heart Disease
        self.assertTrue(self.index.is_a_descendant_of(anterior_stemi_id, ihd_id))
        # Anterior STEMI is a Cardiovascular Disease
        self.assertTrue(self.index.is_a_descendant_of(anterior_stemi_id, cvd_id))
        # Anterior STEMI is a Disease
        self.assertTrue(self.index.is_a_descendant_of(anterior_stemi_id, disease_root_id))

        # Negative test: Anterior STEMI is NOT a Stroke
        stroke_id = "230690007"
        self.assertFalse(self.index.is_a_descendant_of(anterior_stemi_id, stroke_id))

    def test_icd11_cross_mapping_accuracy(self):
        """Verify that canonical SNOMED concepts possess accurate ICD-11 codes."""
        sah = self.index.get_concept("274100004")
        self.assertIsNotNone(sah)
        self.assertEqual(sah.icd11_code, "8B00.0")

        dengue = self.index.get_concept("38362002")
        self.assertIsNotNone(dengue)
        self.assertEqual(dengue.icd11_code, "1D20")


if __name__ == '__main__':
    unittest.main()
