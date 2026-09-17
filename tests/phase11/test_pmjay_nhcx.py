"""
PROJECT "HOSPITAL" — PHASE 11: REVENUE CYCLE
Test Suite: test_pmjay_nhcx.py
Validates:
  - Quality Gate 2: System blocks attempt to add individual syringe/nursing charges to PM-JAY package
  - Inviolable statutory anti-breakage barrier
  - NHCX claim denial pre-screening scanner
"""

import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from pmjay_nhcx_engine import (
    PMJAYNHCXEngine, PMJAYPackageBreakageError
)


class TestPMJAYNHCXEngine(unittest.TestCase):

    def setUp(self):
        self.engine = PMJAYNHCXEngine()

        # Register encounter under Laparoscopic Cholecystectomy (SG001A - ₹28,000 all-inclusive)
        self.enc = self.engine.register_pmjay_encounter(
            encounter_id="ENC-PMJAY-1001",
            patient_id="PAT-PMJAY-01",
            pmjay_card_id="ABHA-PMJAY-9921",
            package_code="SG001A",
            preauth_number="PREAUTH-NHA-4412"
        )

    def test_quality_gate_package_breakage_blocked(self):
        """
        Phase 11 Quality Gate 2:
        System blocks attempt to add individual syringe or nursing charges to a cashless PM-JAY bundled package.
        """
        encounter_id = "ENC-PMJAY-1001"

        # 1. Attempting to add 10ml Syringe -> BLOCKED BY STATUTORY BARRIER!
        with self.assertRaises(PMJAYPackageBreakageError) as ctx1:
            self.engine.add_billing_item(
                encounter_id=encounter_id,
                item_name="Disposable Syringe 10 mL with Needle",
                category="SYRINGE",
                amount_inr=35.0
            )

        self.assertIn("STATUTORY PM-JAY VIOLATION", str(ctx1.exception))
        self.assertIn("is ALL-INCLUSIVE", str(ctx1.exception))
        self.assertIn("Billing separate consumables, nursing, or physician fees is strictly illegal", str(ctx1.exception))

        # 2. Attempting to add Nursing Charges -> BLOCKED!
        with self.assertRaises(PMJAYPackageBreakageError) as ctx2:
            self.engine.add_billing_item(
                encounter_id=encounter_id,
                item_name="Daily Nursing Care Fee",
                category="NURSING_CHARGES",
                amount_inr=500.0
            )

        self.assertIn("STATUTORY PM-JAY VIOLATION", str(ctx2.exception))

        # 3. Attempting to add Surgical Gloves -> BLOCKED!
        with self.assertRaises(PMJAYPackageBreakageError) as ctx3:
            self.engine.add_billing_item(
                encounter_id=encounter_id,
                item_name="Sterile Surgical Latex Gloves",
                category="CONSUMABLES",
                amount_inr=150.0
            )

        self.assertIn("STATUTORY PM-JAY VIOLATION", str(ctx3.exception))

    def test_nhcx_claim_denial_risk_scanner(self):
        """Verify NHCX pre-submission scanner detects missing ICD-10 or lack of clinical justification."""
        # Incomplete claim (missing ICD-10 and missing lab reports) -> HIGH RISK OF REJECTION
        scan = self.engine.scan_nhcx_claim_denial_risk(
            encounter_id="ENC-PMJAY-1001",
            primary_icd10_code="",  # Missing!
            preauth_approval_id="PREAUTH-NHA-4412",
            attached_diagnostic_reports=[]  # Missing!
        )
        self.assertFalse(scan["claim_dispatch_eligible"])
        self.assertEqual(scan["denial_risk_level"], "HIGH")
        self.assertEqual(len(scan["rejection_reasons"]), 2)

        # Complete claim -> APPROVED FOR DISPATCH
        clean_scan = self.engine.scan_nhcx_claim_denial_risk(
            encounter_id="ENC-PMJAY-1001",
            primary_icd10_code="K80.20",  # Calculus of gallbladder
            preauth_approval_id="PREAUTH-NHA-4412",
            attached_diagnostic_reports=["USG-ABDOMEN-REPORT-01", "LFT-LAB-REPORT-02"]
        )
        self.assertTrue(clean_scan["claim_dispatch_eligible"])
        self.assertEqual(clean_scan["denial_risk_level"], "LOW")


if __name__ == "__main__":
    unittest.main()
