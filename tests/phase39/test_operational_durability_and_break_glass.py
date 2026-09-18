#!/usr/bin/env python3
"""
Phase 39 Test Suite: Operational State Durability, NABH Emergency Break-Glass,
Jan Aushadhi Generic Equivalents, and Tri-Lingual Vernacular Patient Guidance.

Validates:
1. Blood Bank inventory durability across reboots (SQLite WAL persistence).
2. NDPS Narcotics Vault durability with 100% unbroken cryptographic SHA-256 hash chains across reboots.
3. Edge Pessimistic Leasing partition durability across reboots.
4. In-memory fallback backward-compatibility when persistence_store is None.
5. Jan Aushadhi (PMBJP) generic formulary matching and affordability metrics.
6. Tri-lingual (English, Hindi, Bengali) vernacular plain-language patient instructions and critical red flags.
7. NABH Code Red Emergency Break-Glass workflow via REST API with 24-hour statutory reconciliation deadline and audit trail.
8. AppShim standalone parity for emergency break-glass and standard RMP counter-signature.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

# Add services/core-api to path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "core-api"))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from patient_persistence_store import PatientPersistenceStore
from blood_bank_engine import BloodBankEngine
from ndps_narcotics_vault import (
    NDPSNarcoticsVaultEngine, BiometricCredential,
    DualBiometricAuthenticationError, NarcoticVaultError
)
from edge_resilience_engine import EdgeResilienceEngine, ResourceNotLeasedError
from prescription_protocol_engine import PrescriptionProtocolEngine, global_prescription_protocol_engine
from auth_manager import auth_security_manager
import main
from fastapi.testclient import TestClient


class TestPhase39OperationalDurabilityAndBreakGlass(unittest.TestCase):

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.store = PatientPersistenceStore(db_path=self.temp_db_path)
        self.client = TestClient(main.app)

        self.admin_cred = BiometricCredential(
            user_id="PHARM-01",
            role="PHARMACIST",
            biometric_token="BIO-ADMIN-P39",
            biometric_verified=True,
            verified_at=datetime.now(timezone.utc)
        )
        self.witness_cred = BiometricCredential(
            user_id="NURSE-01",
            role="NURSE_INCHARGE",
            biometric_token="BIO-WITNESS-P39",
            biometric_verified=True,
            verified_at=datetime.now(timezone.utc)
        )

    def tearDown(self):
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
            wal_path = f"{self.temp_db_path}-wal"
            if os.path.exists(wal_path):
                os.remove(wal_path)
            shm_path = f"{self.temp_db_path}-shm"
            if os.path.exists(shm_path):
                os.remove(shm_path)
        except Exception:
            pass

    # =========================================================================
    # 1. BLOOD BANK OPERATIONAL DURABILITY
    # =========================================================================

    def test_blood_bank_durability_across_reboots(self):
        """Blood bank units and crossmatch reservations must survive complete engine recreation."""
        bb1 = BloodBankEngine(tenant_id="TENANT-P39", persistence_store=self.store)
        bb1.register_blood_unit("UNIT-O-NEG-P39", "O_NEG", "PACKED_RED_BLOOD_CELLS")
        bb1.register_blood_unit("UNIT-AB-POS-P39", "AB_POS", "PACKED_RED_BLOOD_CELLS")

        # Reserve a unit for patient
        comp, msg = bb1.verify_and_crossmatch_unit("MRN-P39-100", "O_NEG", "UNIT-O-NEG-P39", "ORD-TX-P39-01")
        self.assertTrue(comp)
        self.assertIn("CROSSMATCH_COMPATIBLE", msg)

        # Destroy in-memory engine and instantiate a new one
        del bb1
        bb2 = BloodBankEngine(tenant_id="TENANT-P39", persistence_store=self.store)

        # Verify unit is still present and reserved
        restored_unit = bb2._inventory.get("UNIT-O-NEG-P39")
        self.assertIsNotNone(restored_unit)
        self.assertEqual(restored_unit["status"], "RESERVED_FOR_TRANSFUSION")
        self.assertEqual(restored_unit["reserved_for_mrn"], "MRN-P39-100")

        # Verify other unit available
        other_unit = bb2._inventory.get("UNIT-AB-POS-P39")
        self.assertIsNotNone(other_unit)
        self.assertEqual(other_unit["status"], "AVAILABLE_IN_INVENTORY")

    # =========================================================================
    # 2. NDPS NARCOTICS VAULT DURABILITY & CRYPTOGRAPHIC HASH CHAIN
    # =========================================================================

    def test_ndps_vault_durability_and_hash_chain_integrity(self):
        """
        Perpetual narcotic ledger transactions must persist across crashes
        and retain an unbroken SHA-256 cryptographic hash chain.
        """
        nv1 = NDPSNarcoticsVaultEngine(persistence_store=self.store)
        nv1.initialize_drug_vault("FENTANYL_100MCG", 50, self.admin_cred, self.witness_cred)

        # Dispense 5 ampoules to an ICU patient
        dispense_entry = nv1.dispense_narcotic(
            drug_id="FENTANYL_100MCG",
            batch_number="BATCH-FNT-001",
            quantity=5,
            patient_id="PT-ICU-P39",
            prescription_order_id="RX-FNT-999",
            primary_auth=self.admin_cred,
            secondary_auth=self.witness_cred
        )
        self.assertEqual(nv1.balances["FENTANYL_100MCG"], 45)

        # Record witnessed wastage of partial dose
        nv1.record_narcotic_wastage(
            drug_id="FENTANYL_100MCG",
            batch_number="BATCH-FNT-001",
            wasted_quantity=1,
            reason="Remaining 50mcg in opened ampoule destroyed",
            disposal_method="DRAIN_WITH_SALINE_FLUSH",
            administering_nurse_auth=self.witness_cred,
            witness_nurse_auth=self.admin_cred
        )
        self.assertEqual(nv1.balances["FENTANYL_100MCG"], 44)

        # Return 2 unused intact ampoules to vault
        nv1.return_narcotic(
            drug_id="FENTANYL_100MCG",
            batch_number="BATCH-FNT-001",
            quantity=2,
            reason="Procedure completed earlier than expected",
            returning_nurse_auth=self.witness_cred,
            receiving_pharmacist_auth=self.admin_cred
        )
        self.assertEqual(nv1.balances["FENTANYL_100MCG"], 46)

        # Validate hash chain integrity before reboot
        self.assertTrue(nv1.verify_ledger_integrity("FENTANYL_100MCG"))

        # Simulate complete system shutdown / server crash
        del nv1

        # Boot brand new engine reading from disk
        nv2 = NDPSNarcoticsVaultEngine(persistence_store=self.store)
        self.assertEqual(nv2.balances.get("FENTANYL_100MCG"), 46)
        self.assertEqual(len(nv2.ledger.get("FENTANYL_100MCG", [])), 4)

        # Verify that the cryptographic hash chain is completely unbroken on the fresh instance
        self.assertTrue(nv2.verify_ledger_integrity("FENTANYL_100MCG"))

    # =========================================================================
    # 3. EDGE RESOURCE LEASE DURABILITY
    # =========================================================================

    def test_edge_lease_durability_across_reboots(self):
        """Pessimistic edge partition leases must survive server reboots."""
        edge1 = EdgeResilienceEngine(persistence_store=self.store)
        edge1.grant_pessimistic_lease(
            node_id="EDGE_NODE_01",
            resource_id="ICU_BED_P39_01",
            resource_type="ICU_BED",
            duration_days=5
        )

        del edge1

        edge2 = EdgeResilienceEngine(persistence_store=self.store)
        # EDGE_NODE_01 should retain assigned lease
        self.assertIn("ICU_BED_P39_01", edge2._nodes["EDGE_NODE_01"].assigned_leases)

        # Disconnect WAN and verify EDGE_NODE_02 is blocked from allocating EDGE_NODE_01's bed
        edge2.disconnect_hospital_wan()
        with self.assertRaises(ResourceNotLeasedError):
            edge2.execute_local_emergency_bed_allocation(
                node_id="EDGE_NODE_02",
                patient_id="PT-EMERG-002",
                resource_id="ICU_BED_P39_01"
            )

        # EDGE_NODE_01 can successfully allocate it offline
        tx = edge2.execute_local_emergency_bed_allocation(
            node_id="EDGE_NODE_01",
            patient_id="PT-EMERG-001",
            resource_id="ICU_BED_P39_01"
        )
        self.assertEqual(tx.tx_type, "EMERGENCY_ADMISSION")

    # =========================================================================
    # 4. BACKWARD COMPATIBILITY
    # =========================================================================

    def test_in_memory_fallback_compatibility(self):
        """Passing persistence_store=None must preserve 100% in-memory functionality."""
        bb = BloodBankEngine(tenant_id="TENANT-P39", persistence_store=None)
        bb.register_blood_unit("UNIT-MEM-01", "B_POS")
        self.assertIn("UNIT-MEM-01", bb._inventory)

        nv = NDPSNarcoticsVaultEngine(persistence_store=None)
        nv.initialize_drug_vault("MORPHINE_10MG", 10, self.admin_cred, self.witness_cred)
        self.assertEqual(nv.balances["MORPHINE_10MG"], 10)

        edge = EdgeResilienceEngine(persistence_store=None)
        lease = edge.grant_pessimistic_lease("EDGE_NODE_01", "BED-MEM-01", "ICU_BED")
        self.assertIsNotNone(lease)

    # =========================================================================
    # 5. JAN AUSHADHI (PMBJP) GENERIC EQUIVALENTS & SAVINGS
    # =========================================================================

    def test_jan_aushadhi_generic_equivalents(self):
        """Prescription protocols must attach matching PMBJP generic equivalents with cost savings."""
        rx = global_prescription_protocol_engine.generate_prescription_protocol(
            disease_key="ACUTE_MYOCARDIAL_INFARCTION",
            patient_age=58,
            patient_weight_kg=72.0
        )
        self.assertEqual(rx["status"], "GENERATED")
        self.assertIn("jan_aushadhi_generic_equivalents", rx)
        jan_items = rx["jan_aushadhi_generic_equivalents"]
        self.assertTrue(len(jan_items) >= 2)

        aspirin_match = next((item for item in jan_items if "Aspirin" in item["prescribed_drug"]), None)
        self.assertIsNotNone(aspirin_match)
        self.assertEqual(aspirin_match["pmbjp_drug_code"], "PMBJP-0012")
        self.assertTrue(aspirin_match["estimated_savings_percent"] > 50.0)

        clopidogrel_match = next((item for item in jan_items if "Clopidogrel" in item["prescribed_drug"]), None)
        self.assertIsNotNone(clopidogrel_match)
        self.assertTrue(clopidogrel_match["estimated_savings_percent"] > 50.0)

    # =========================================================================
    # 6. TRI-LINGUAL VERNACULAR PATIENT GUIDANCE (EN / HI / BN)
    # =========================================================================

    def test_vernacular_patient_guidance_tri_lingual(self):
        """Prescription protocols must provide clear instructions in English, Hindi, and Bengali."""
        rx = global_prescription_protocol_engine.generate_prescription_protocol(
            disease_key="ACUTE_APPENDICITIS",
            patient_age=32,
            patient_weight_kg=65.0
        )
        self.assertIn("vernacular_patient_guidance", rx)
        guidance = rx["vernacular_patient_guidance"]

        self.assertIn("en", guidance)
        self.assertIn("hi", guidance)
        self.assertIn("bn", guidance)

        # English checks
        self.assertIn("Acute Appendicitis", guidance["en"]["plain_language_summary"])
        self.assertTrue(len(guidance["en"]["critical_red_flags"]) >= 1)

        # Hindi (हिन्दी) Devanagari checks
        self.assertIn("दवा", guidance["hi"]["plain_language_summary"])
        self.assertIn("आपातकालीन", guidance["hi"]["critical_red_flags"][0])
        self.assertIn("जन औषधि", guidance["hi"]["jan_aushadhi_affordability_note"])

        # Bengali (বাংলা) checks
        self.assertIn("ঔষধ", guidance["bn"]["plain_language_summary"])
        self.assertIn("জরুরি বিভাগে", guidance["bn"]["critical_red_flags"][0])
        self.assertIn("জনঔষধী", guidance["bn"]["jan_aushadhi_affordability_note"])

    # =========================================================================
    # 7. NABH CODE RED EMERGENCY BREAK-GLASS WORKFLOW VIA REST API
    # =========================================================================

    def test_emergency_break_glass_rest_api_workflow(self):
        """
        Under NABH Code Red emergency conditions, life-saving orders can be authorized
        with mandatory justification, creating a 24-hour statutory reconciliation deadline.
        """
        token = auth_security_manager.create_access_token(
            username="EMERGENCY_DOC_01",
            tenant_id="TENANT-MAIN-01",
            role="RESIDENT_PHYSICIAN",
            permissions=["PRESCRIPTION_SIGN", "CLINICAL_ORDER", "EMERGENCY_OVERRIDE"]
        )
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Missing reason must be rejected with 422
        bad_req = {
            "prescription_id": "RX-PROT-EMERG-01",
            "is_emergency_override": True,
            "emergency_override_reason": ""
        }
        res_bad = self.client.post("/api/v1/clinical/prescriptions/sign", json=bad_req, headers=headers)
        self.assertEqual(res_bad.status_code, 422)
        self.assertEqual(res_bad.json()["detail"]["status"], "MISSING_EMERGENCY_REASON")

        # 2. Valid emergency break-glass invocation
        valid_req = {
            "prescription_id": "RX-PROT-EMERG-01",
            "physician_name": "Dr. A. Sharma (EMO)",
            "is_emergency_override": True,
            "emergency_override_reason": "CODE RED RESUSCITATION: ACUTE ANAPHYLACTIC SHOCK AT TRIAGE BEDSIDE",
            "clinical_notes": "Stat epinephrine and hydrocortisone administered immediately."
        }
        res_ok = self.client.post("/api/v1/clinical/prescriptions/sign", json=valid_req, headers=headers)
        self.assertEqual(res_ok.status_code, 200)
        data = res_ok.json()

        self.assertEqual(data["status"], "EMERGENCY_BREAK_GLASS_AUTHORIZED")
        self.assertEqual(data["legal_status"], "EMERGENCY_PROVISIONAL_ORDER_NABH_BREAK_GLASS")
        self.assertFalse(data["is_physician_signed"])
        self.assertTrue(data["emergency_break_glass"]["is_emergency_override"])
        self.assertTrue(data["emergency_break_glass"]["requires_24h_reconciliation"])
        self.assertIn("CODE RED RESUSCITATION", data["emergency_break_glass"]["override_reason"])
        self.assertIsNotNone(data["emergency_break_glass"]["reconciliation_deadline_utc"])

    # =========================================================================
    # 8. APPSHIM STANDALONE PARITY
    # =========================================================================

    def test_appshim_sign_prescription_break_glass_parity(self):
        """AppShim sign_prescription must implement identical emergency break-glass rules."""
        shim = main.AppShim()

        # Without reason -> ValueError
        with self.assertRaises(ValueError):
            shim.sign_prescription(
                prescription_id="RX-SHIM-001",
                is_emergency_override=True,
                emergency_override_reason=""
            )

        # With reason -> EMERGENCY_BREAK_GLASS_AUTHORIZED
        resp = shim.sign_prescription(
            prescription_id="RX-SHIM-001",
            physician_name="Dr. Bedside EMO",
            is_emergency_override=True,
            emergency_override_reason="CODE RED CARDIAC ARREST"
        )
        self.assertEqual(resp["status"], "EMERGENCY_BREAK_GLASS_AUTHORIZED")
        self.assertTrue(resp["emergency_break_glass"]["requires_24h_reconciliation"])

        # Standard RMP sign-off
        resp_std = shim.sign_prescription(
            prescription_id="RX-SHIM-002",
            physician_name="Dr. Senior Consultant",
            rmp_registration_number="MCI-P39-998877"
        )
        self.assertEqual(resp_std["status"], "DISPENSABLE_AUTHORIZED")
        self.assertTrue(resp_std["is_physician_signed"])


if __name__ == "__main__":
    unittest.main()
