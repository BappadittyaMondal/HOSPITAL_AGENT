"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Test Suite: test_med_reconciliation.py
Validates:
  - Quality Gate 3: Medication reconciliation module flags omissions and duplications across ward transfers
  - Clinician decisioning with mandatory clinical rationale
  - WHO Defined Daily Dose (DDD) per 1,000 patient-days calculation (Gap 17)
  - Microbiology antibiogram sensitivity calculation
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from med_reconciliation_engine import (
    MedicationReconciliationEngine, MedicationItem, ReconciliationDecision, DiscrepancyAlert
)


class TestMedicationReconciliationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MedicationReconciliationEngine()

    def test_quality_gate_detects_omissions_and_duplications_on_transfer(self):
        """
        Phase 06 Quality Gate 3:
        Medication reconciliation module flags omissions and duplications across ward transfers.
        """
        # Baseline: Home/Pre-admission medications
        baseline_meds = [
            MedicationItem(
                drug_id="DRUG-AMLODIPINE-5",
                drug_name="Amlodipine",
                dosage="5 mg",
                route="ORAL",
                frequency="OD",
                therapeutic_class="ANTIHYPERTENSIVE"
            ),
            MedicationItem(
                drug_id="DRUG-METFORMIN-500",
                drug_name="Metformin",
                dosage="500 mg",
                route="ORAL",
                frequency="BD",
                therapeutic_class="BIGUANIDE"
            )
        ]

        # Target: Inpatient orders upon ward transfer
        # Notice: Amlodipine is completely omitted! Metformin dose changed to 1000 mg.
        # Plus: Two ACE inhibitors ordered concurrently (Enalapril and Ramipril - duplication!)
        target_meds = [
            MedicationItem(
                drug_id="DRUG-METFORMIN-500",
                drug_name="Metformin",
                dosage="1000 mg",  # Dose altered
                route="ORAL",
                frequency="BD",
                therapeutic_class="BIGUANIDE"
            ),
            MedicationItem(
                drug_id="DRUG-ENALAPRIL-5",
                drug_name="Enalapril",
                dosage="5 mg",
                route="ORAL",
                frequency="OD",
                therapeutic_class="ACE_INHIBITOR"
            ),
            MedicationItem(
                drug_id="DRUG-RAMIPRIL-2.5",
                drug_name="Ramipril",
                dosage="2.5 mg",
                route="ORAL",
                frequency="OD",
                therapeutic_class="ACE_INHIBITOR"
            )
        ]

        alerts = self.engine.detect_discrepancies(baseline_meds, target_meds, transition_type="WARD_TRANSFER")

        # Must flag:
        # 1. UNINTENDED_OMISSION for Amlodipine (HIGH severity)
        # 2. DOSE_MISMATCH for Metformin
        # 3. THERAPEUTIC_DUPLICATION for ACE Inhibitors
        alert_types = [a.discrepancy_type for a in alerts]
        self.assertIn("UNINTENDED_OMISSION", alert_types)
        self.assertIn("DOSE_MISMATCH", alert_types)
        self.assertIn("THERAPEUTIC_DUPLICATION", alert_types)

        omission_alert = next(a for a in alerts if a.discrepancy_type == "UNINTENDED_OMISSION")
        self.assertEqual(omission_alert.drug_id, "DRUG-AMLODIPINE-5")
        self.assertEqual(omission_alert.severity, "HIGH")

        dup_alert = next(a for a in alerts if a.discrepancy_type == "THERAPEUTIC_DUPLICATION")
        self.assertIn("Enalapril", dup_alert.drug_name)
        self.assertIn("Ramipril", dup_alert.drug_name)

    def test_reconciliation_requires_rationale_for_modifications(self):
        """Verify clinician reconciliation demands clinical rationale for discontinued drugs."""
        decisions = [
            ReconciliationDecision(
                drug_id="DRUG-AMLODIPINE-5",
                action="DISCONTINUE",
                clinical_rationale=""  # Missing rationale!
            )
        ]
        with self.assertRaises(ValueError) as ctx:
            self.engine.complete_reconciliation(
                patient_id="PAT-5501",
                transition_type="WARD_TRANSFER",
                clinician_id="DOC-CARDIO-01",
                decisions=decisions,
                unresolved_alerts=[]
            )
        self.assertIn("Mandatory clinical rationale required", str(ctx.exception))

        # With rationale -> succeeds
        decisions[0].clinical_rationale = "Discontinued due to acute systolic hypotension and cardiogenic shock"
        record = self.engine.complete_reconciliation(
            patient_id="PAT-5501",
            transition_type="WARD_TRANSFER",
            clinician_id="DOC-CARDIO-01",
            decisions=decisions,
            unresolved_alerts=[]
        )
        self.assertEqual(record["status"], "COMPLETED")

    def test_who_defined_daily_dose_calculation(self):
        """Verify Defined Daily Dose per 1,000 patient-days (Gap 17)."""
        # Meropenem standard WHO DDD = 3.0 grams
        # 300 grams consumed across 1,000 patient bed-days
        # DDD units = 300 / 3 = 100
        # Rate per 1000 PD = (100 / 1000) * 1000 = 100.0 DDD / 1000 PD
        result = self.engine.calculate_defined_daily_dose_rate(
            antibiotic_name="MEROPENEM",
            total_grams_consumed=300.0,
            total_patient_bed_days=1000
        )
        self.assertEqual(result["who_standard_ddd_grams"], 3.0)
        self.assertEqual(result["ddd_units_consumed"], 100.0)
        self.assertEqual(result["ddd_per_1000_patient_days"], 100.0)

    def test_antibiogram_generation(self):
        """Verify microbiology antibiogram susceptibility percentage aggregation."""
        isolates = [
            {"organism": "KLEBSIELLA_PNEUMONIAE", "antibiotic": "MEROPENEM", "susceptibility": "S"},
            {"organism": "KLEBSIELLA_PNEUMONIAE", "antibiotic": "MEROPENEM", "susceptibility": "S"},
            {"organism": "KLEBSIELLA_PNEUMONIAE", "antibiotic": "MEROPENEM", "susceptibility": "R"},
            {"organism": "KLEBSIELLA_PNEUMONIAE", "antibiotic": "COLISTIN", "susceptibility": "S"},
            {"organism": "KLEBSIELLA_PNEUMONIAE", "antibiotic": "COLISTIN", "susceptibility": "S"},
        ]
        antibiogram = self.engine.generate_antibiogram(isolates)
        # Meropenem: 2 susceptible out of 3 = 66.7%
        # Colistin: 2 susceptible out of 2 = 100.0%
        self.assertAlmostEqual(antibiogram["KLEBSIELLA_PNEUMONIAE"]["MEROPENEM"], 66.7, places=1)
        self.assertEqual(antibiogram["KLEBSIELLA_PNEUMONIAE"]["COLISTIN"], 100.0)


if __name__ == "__main__":
    unittest.main()
