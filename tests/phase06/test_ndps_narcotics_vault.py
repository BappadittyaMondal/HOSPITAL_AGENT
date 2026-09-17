"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Test Suite: test_ndps_narcotics_vault.py
Validates:
  - Quality Gate 2: Controlled narcotic dispensing is impossible without two distinct authenticated biometric logins
  - Perpetual ledger balance updating
  - Hash chain cryptographic integrity validation
  - Partial dose wastage with witness co-signature
"""

import unittest
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
from ndps_narcotics_vault import (
    NDPSNarcoticsVaultEngine, BiometricCredential,
    DualBiometricAuthenticationError, NarcoticVaultError, NarcoticLedgerTamperError
)


class TestNDPSNarcoticsVaultEngine(unittest.TestCase):

    def setUp(self):
        self.engine = NDPSNarcoticsVaultEngine()
        self.now = datetime.now(timezone.utc)

        self.pharmacist_bio = BiometricCredential(
            user_id="PHARM-01",
            role="PHARMACIST",
            biometric_token="TOKEN-BIO-PHARM-01",
            biometric_verified=True,
            verified_at=self.now
        )
        self.nurse_ic_bio = BiometricCredential(
            user_id="NURSE-IC-01",
            role="NURSE_INCHARGE",
            biometric_token="TOKEN-BIO-NURSE-01",
            biometric_verified=True,
            verified_at=self.now
        )
        self.unverified_bio = BiometricCredential(
            user_id="RESIDENT-01",
            role="RESIDENT_DOCTOR",
            biometric_token="TOKEN-BIO-RES-01",
            biometric_verified=False,  # Unverified!
            verified_at=self.now
        )

        # Initialize vault with 100 ampoules of Fentanyl 50 mcg/mL
        self.drug_id = "DRUG-FENTANYL-50MCG"
        self.engine.initialize_drug_vault(
            drug_id=self.drug_id,
            initial_stock=100,
            admin_auth=self.pharmacist_bio,
            witness_auth=self.nurse_ic_bio
        )

    def test_quality_gate_dual_biometric_login_enforcement(self):
        """
        Phase 06 Quality Gate 2:
        Controlled narcotic dispensing is impossible without two distinct authenticated biometric logins.
        """
        # 1. Single user attempting to sign both roles -> FAILS
        with self.assertRaises(DualBiometricAuthenticationError) as ctx1:
            self.engine.dispense_narcotic(
                drug_id=self.drug_id,
                batch_number="BATCH-FENT-01",
                quantity=5,
                patient_id="PAT-ICU-09",
                prescription_order_id="RX-FENT-101",
                primary_auth=self.pharmacist_bio,
                secondary_auth=self.pharmacist_bio  # Same user!
            )
        self.assertIn("cannot be the same user", str(ctx1.exception))

        # 2. Secondary user with biometric_verified=False -> FAILS
        with self.assertRaises(DualBiometricAuthenticationError) as ctx2:
            self.engine.dispense_narcotic(
                drug_id=self.drug_id,
                batch_number="BATCH-FENT-01",
                quantity=5,
                patient_id="PAT-ICU-09",
                prescription_order_id="RX-FENT-101",
                primary_auth=self.pharmacist_bio,
                secondary_auth=self.unverified_bio  # Unverified!
            )
        self.assertIn("Both signers must present valid, active biometric verification", str(ctx2.exception))

        # 3. Two distinct verified biometrics -> SUCCEEDS
        entry = self.engine.dispense_narcotic(
            drug_id=self.drug_id,
            batch_number="BATCH-FENT-01",
            quantity=5,
            patient_id="PAT-ICU-09",
            prescription_order_id="RX-FENT-101",
            primary_auth=self.pharmacist_bio,
            secondary_auth=self.nurse_ic_bio
        )
        self.assertEqual(entry.running_balance, 95)
        self.assertEqual(self.engine.balances[self.drug_id], 95)

    def test_narcotic_wastage_with_witness(self):
        """Verify partial dose wastage recording with witness co-signature."""
        waste_entry = self.engine.record_narcotic_wastage(
            drug_id=self.drug_id,
            batch_number="BATCH-FENT-01",
            wasted_quantity=2,
            reason="Residual volume in ampoule after partial administration",
            disposal_method="Denatured in chemical drain with witnessed disposal",
            administering_nurse_auth=self.nurse_ic_bio,
            witness_nurse_auth=self.pharmacist_bio
        )
        self.assertEqual(waste_entry.transaction_type, "WASTE")
        self.assertEqual(waste_entry.quantity_change, -2)
        self.assertEqual(self.engine.balances[self.drug_id], 98)

    def test_cryptographic_hash_chain_integrity(self):
        """Verify immutable hash chain detects tampering in the NDPS ledger."""
        # Add a dispense transaction
        self.engine.dispense_narcotic(
            drug_id=self.drug_id,
            batch_number="BATCH-FENT-01",
            quantity=10,
            patient_id="PAT-ICU-10",
            prescription_order_id="RX-FENT-102",
            primary_auth=self.pharmacist_bio,
            secondary_auth=self.nurse_ic_bio
        )
        # Verify valid ledger
        self.assertTrue(self.engine.verify_ledger_integrity(self.drug_id))

        # Intentionally tamper with the recorded quantity in an earlier ledger entry
        self.engine.ledger[self.drug_id][1].running_balance = 999  # Tampering!

        with self.assertRaises(NarcoticLedgerTamperError) as ctx:
            self.engine.verify_ledger_integrity(self.drug_id)
        self.assertIn("Hash mismatch", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
