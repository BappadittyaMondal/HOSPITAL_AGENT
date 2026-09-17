"""
PROJECT "HOSPITAL" — PHASE 10: SPECIALTY DEPARTMENTS
Test Suite: test_oncology_daycare.py
Validates:
  - Quality Gate 3: System halts chemotherapy release if ANC < 1,000 cells/µL or Platelets < 50,000/µL
  - Dual-pharmacist protocol verification
  - Extravasation vesicant antidote protocol (Dexrazoxane vs Hyaluronidase)
"""

import unittest
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from oncology_daycare_engine import (
    OncologyDayCareEngine, ChemotherapyLabGateViolationError, OncologySafetyError
)


class TestOncologyDayCareEngine(unittest.TestCase):

    def setUp(self):
        self.engine = OncologyDayCareEngine()
        self.now = datetime.now(timezone.utc)

    def test_quality_gate_chemotherapy_halted_on_low_anc_or_platelets(self):
        """
        Phase 10 Quality Gate 3:
        System halts chemotherapy release if active lab results show
        Absolute Neutrophil Count < 1,000 cells/µL or Platelets < 50,000 cells/µL.
        """
        patient_id = "PAT-ONCO-402"

        # 1. Severe Neutropenia: ANC = 650 cells/µL (< 1,000 safe minimum)
        self.engine.record_pre_chemo_labs(
            patient_id=patient_id,
            anc_cells_per_ul=650.0,         # DANGEROUSLY LOW!
            platelet_count_per_ul=180000.0,
            hemoglobin_g_dl=10.2,
            creatinine_mg_dl=0.9,
            bilirubin_mg_dl=0.7,
            tested_at=self.now
        )

        with self.assertRaises(ChemotherapyLabGateViolationError) as ctx1:
            self.engine.verify_and_authorize_chemo_release(
                order_id="ORD-CHEMO-101",
                patient_id=patient_id,
                regimen_name="AC (Adriamycin / Cyclophosphamide)",
                drug_name="Doxorubicin",
                dose_prescribed_mg=100.0,
                bsa_m2=1.75,
                primary_pharmacist_id="PHARM-ONCO-01",
                secondary_pharmacist_id="PHARM-ONCO-02"
            )

        self.assertIn("FATAL MYELOSUPPRESSION SAFETY GATE BREACH", str(ctx1.exception))
        self.assertIn("Active ANC is 650.0 cells/µL", str(ctx1.exception))
        self.assertIn("strictly halted", str(ctx1.exception))

        # 2. Severe Thrombocytopenia: Platelets = 32,000 cells/µL (< 50,000 safe minimum)
        self.engine.record_pre_chemo_labs(
            patient_id="PAT-ONCO-403",
            anc_cells_per_ul=2200.0,
            platelet_count_per_ul=32000.0,  # DANGEROUSLY LOW!
            hemoglobin_g_dl=9.5,
            creatinine_mg_dl=0.8,
            bilirubin_mg_dl=0.6,
            tested_at=self.now
        )

        with self.assertRaises(ChemotherapyLabGateViolationError) as ctx2:
            self.engine.verify_and_authorize_chemo_release(
                order_id="ORD-CHEMO-102",
                patient_id="PAT-ONCO-403",
                regimen_name="FOLFOX",
                drug_name="Oxaliplatin",
                dose_prescribed_mg=150.0,
                bsa_m2=1.80,
                primary_pharmacist_id="PHARM-ONCO-01",
                secondary_pharmacist_id="PHARM-ONCO-02"
            )

        self.assertIn("FATAL THROMBOCYTOPENIA SAFETY GATE BREACH", str(ctx2.exception))
        self.assertIn("Active Platelets are 32000.0 cells/µL", str(ctx2.exception))

        # 3. Valid Labs: ANC 2500, Platelets 220,000 -> Chemotherapy release approved
        self.engine.record_pre_chemo_labs(
            patient_id="PAT-ONCO-SAFE",
            anc_cells_per_ul=2500.0,
            platelet_count_per_ul=220000.0,
            hemoglobin_g_dl=12.0,
            creatinine_mg_dl=0.9,
            bilirubin_mg_dl=0.5,
            tested_at=self.now
        )
        approved = self.engine.verify_and_authorize_chemo_release(
            order_id="ORD-CHEMO-103",
            patient_id="PAT-ONCO-SAFE",
            regimen_name="AC",
            drug_name="Doxorubicin",
            dose_prescribed_mg=100.0,
            bsa_m2=1.75,
            primary_pharmacist_id="PHARM-ONCO-01",
            secondary_pharmacist_id="PHARM-ONCO-02"
        )
        self.assertEqual(approved.status, "APPROVED_FOR_DISPENSING")
        self.assertTrue(approved.is_verified)

    def test_extravasation_antidote_protocols(self):
        """Verify proper antidote matching for anthracycline vs vinca alkaloid extravasation."""
        # Anthracycline (Doxorubicin) -> Dexrazoxane + Cold compress (Heat contraindicated!)
        dox_proto = self.engine.get_extravasation_antidote_protocol("Doxorubicin")
        self.assertEqual(dox_proto["vesicant_class"], "ANTHRACYCLINE")
        self.assertIn("Dexrazoxane", dox_proto["antidote"])
        self.assertIn("COLD", dox_proto["thermal_application"])
        self.assertIn("DO NOT APPLY HEAT", dox_proto["contraindicated"])

        # Vinca Alkaloid (Vincristine) -> Hyaluronidase + Warm compress (Cold contraindicated!)
        vinc_proto = self.engine.get_extravasation_antidote_protocol("Vincristine")
        self.assertEqual(vinc_proto["vesicant_class"], "VINCA_ALKALOID")
        self.assertIn("Hyaluronidase", vinc_proto["antidote"])
        self.assertIn("WARM", vinc_proto["thermal_application"])
        self.assertIn("DO NOT APPLY COLD", vinc_proto["contraindicated"])


if __name__ == "__main__":
    unittest.main()
