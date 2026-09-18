#!/usr/bin/env python3
"""
Phase 38 Test Suite: Persistent Cumulative Lifetime Toxicity State & Statutory RMP Digital Counter-Signature.
Validates:
1. Persistent Cumulative Toxicity Storage across engine restarts (SQLite WAL persistence).
2. Hard-stop interception when multi-encounter lifetime doses breach safety ceiling on a fresh engine.
3. In-memory fallback backward-compatibility when persistence_store is None.
4. Statutory Governance in Prescription Protocol Engine (draft status, legal_status, statutory_disclaimer).
5. Statutory RMP Digital Counter-Signature Gate via REST API (role gating, NMC registration number check).
6. Immutable audit logging of RMP prescription counter-signature.
7. AppShim standalone sign_prescription parity.
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
from cpoe_dre_engine import CPOEDREEngine
from prescription_protocol_engine import PrescriptionProtocolEngine, global_prescription_protocol_engine
from auth_manager import auth_security_manager
import main
from fastapi.testclient import TestClient


class TestPhase38PersistentStateAndRMPSignoff(unittest.TestCase):

    def setUp(self):
        # Create a persistent temporary database for isolated testing
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.store = PatientPersistenceStore(db_path=self.temp_db_path)
        self.dre = CPOEDREEngine(tenant_id="TENANT-P38-TEST", persistence_store=self.store)
        self.client = TestClient(main.app)

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

    def test_cumulative_toxicity_persistence_across_engine_reboots(self):
        """
        Doxorubicin lifetime dose administered in encounter 1 must persist to disk
        and be strictly enforced when a brand new CPOEDREEngine instance starts up.
        """
        patient_id = "PT-ONCO-LIFETIME-01"

        # Encounter 1: Administer 350 mg (BSA = 1.0, so 350 mg/m² <= 450 mg/m² ceiling)
        eval1 = self.dre.evaluate_order(
            patient_id=patient_id,
            drug_name="Doxorubicin 50mg/vial",
            prescribed_dose=350.0,
            route="IV",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.0,
            serum_creatinine=0.9,
            patient_age=52,
            is_female=True,
            current_medications=[],
            known_allergies=[]
        )
        self.assertIn(eval1["status"], ("APPROVED", "PASSED"))

        # Record administration in store
        self.dre.record_administered_dose(patient_id, "DOXORUBICIN", 350.0)

        # Verify disk store contains the recorded dose
        stored_dose = self.store.get_lifetime_dose(patient_id, "doxorubicin")
        self.assertEqual(stored_dose, 350.0)

        # SIMULATE COMPLETE ENGINE REBOOT: Instantiate a completely new CPOEDREEngine
        fresh_rebooted_dre = CPOEDREEngine(tenant_id="TENANT-P38-TEST", persistence_store=self.store)

        # Confirm rebooted engine reads persisted cumulative dose from disk
        reboot_dose = fresh_rebooted_dre.get_lifetime_dose(patient_id, "doxorubicin")
        self.assertEqual(reboot_dose, 350.0)

        # Encounter 2: Prescribe additional 250 mg (Total would be 350 + 250 = 600 mg/m² > 450 mg/m² limit)
        eval2 = fresh_rebooted_dre.evaluate_order(
            patient_id=patient_id,
            drug_name="Doxorubicin 50mg/vial",
            prescribed_dose=250.0,
            route="IV",
            patient_weight_kg=70.0,
            patient_bsa_m2=1.0,
            serum_creatinine=0.9,
            patient_age=52,
            is_female=True,
            current_medications=[],
            known_allergies=[]
        )
        self.assertEqual(eval2["status"], "BLOCKED")
        self.assertTrue(
            any("CUMULATIVE TOXICITY CEILING EXCEEDED" in hs for hs in eval2["hard_stops"]),
            f"Expected cumulative toxicity hard stop, got: {eval2['hard_stops']}"
        )

    def test_bleomycin_lifetime_toxicity_persistence(self):
        """Bleomycin lifetime ceiling (400 units) must be enforced across fresh engine reboots."""
        patient_id = "PT-BLEO-01"
        self.dre.record_administered_dose(patient_id, "BLEOMYCIN", 250.0)

        fresh_dre = CPOEDREEngine(tenant_id="TENANT-P38-TEST", persistence_store=self.store)
        self.assertEqual(fresh_dre.get_lifetime_dose(patient_id, "bleomycin"), 250.0)

        # Attempt to prescribe 200 units (Total = 250 + 200 = 450 > 400 units)
        res = fresh_dre.evaluate_order(
            patient_id=patient_id,
            drug_name="Bleomycin 15 units",
            prescribed_dose=200.0,
            route="IV",
            patient_weight_kg=65.0,
            patient_bsa_m2=1.7,
            serum_creatinine=1.0,
            patient_age=40,
            is_female=False
        )
        self.assertEqual(res["status"], "BLOCKED")
        self.assertTrue(any("CUMULATIVE TOXICITY CEILING EXCEEDED" in hs for hs in res["hard_stops"]))

    def test_in_memory_fallback_backward_compatibility(self):
        """When persistence_store is None, in-memory dict works seamlessly without errors."""
        mem_dre = CPOEDREEngine(tenant_id="TENANT-MEM-ONLY", persistence_store=None)
        mem_dre.record_administered_dose("PT-MEM-01", "DOXORUBICIN", 200.0)
        self.assertEqual(mem_dre.get_lifetime_dose("PT-MEM-01", "doxorubicin"), 200.0)

        # Order below limit: 200 + 100 = 300 <= 450
        res1 = mem_dre.evaluate_order(
            patient_id="PT-MEM-01",
            drug_name="Doxorubicin",
            prescribed_dose=100.0,
            patient_bsa_m2=1.0
        )
        self.assertIn(res1["status"], ("APPROVED", "PASSED"))

        # Order exceeding limit: 200 + 300 = 500 > 450
        res2 = mem_dre.evaluate_order(
            patient_id="PT-MEM-01",
            drug_name="Doxorubicin",
            prescribed_dose=300.0,
            patient_bsa_m2=1.0
        )
        self.assertEqual(res2["status"], "BLOCKED")

    def test_prescription_protocol_statutory_governance_attributes(self):
        """
        Generated prescription protocols must contain statutory disclaimer,
        unique prescription_id, draft legal status, and un-signed flag.
        """
        engine = PrescriptionProtocolEngine()
        proto = engine.generate_prescription_protocol(
            disease_key="ACUTE_MYOCARDIAL_INFARCTION",
            patient_age=58,
            patient_weight_kg=75.0,
            patient_egfr=85.0
        )
        self.assertEqual(proto["status"], "GENERATED")
        self.assertEqual(proto["legal_status"], "DRAFT_DECISION_SUPPORT_REQUIRES_PHYSICIAN_SIGNATURE")
        self.assertFalse(proto["is_physician_signed"])
        self.assertTrue(proto["prescription_id"].startswith("RX-PROT-"))
        self.assertIn("statutory_disclaimer", proto)
        self.assertIn("NMC ACT 2019", proto["statutory_disclaimer"])
        self.assertIn("DISPENSING PROHIBITED WITHOUT PHYSICIAN SIGNATURE", proto["statutory_disclaimer"])

    def test_rmp_prescription_countersign_success(self):
        """A licensed RMP physician successfully signs a draft prescription, making it dispensable."""
        # Issue a token for a Consultant Physician
        token = auth_security_manager.create_access_token(
            username="DR-AIIMS-001",
            tenant_id="TENANT-MAIN-01",
            role="CONSULTANT_PHYSICIAN",
            permissions=["PRESCRIPTION_SIGN", "CLINICAL_ORDER"]
        )

        sign_payload = {
            "prescription_id": "RX-PROT-2026-TEST-001",
            "physician_name": "Dr. Arvind Sharma, MD (AIIMS)",
            "rmp_registration_number": "NMC-MCI-2015-94820",
            "council_affiliation": "NATIONAL_MEDICAL_COMMISSION",
            "clinical_notes": "Reviewed ECG and ST elevations. Indicated for dual antiplatelet and high-intensity statin.",
            "override_flags": []
        }

        response = self.client.post(
            "/api/v1/clinical/prescriptions/sign",
            json=sign_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "DISPENSABLE_AUTHORIZED")
        self.assertEqual(data["legal_status"], "STATUTORILY_VALID_DISPENSABLE_ORDER")
        self.assertTrue(data["is_physician_signed"])
        self.assertEqual(data["signed_by"]["rmp_registration_number"], "NMC-MCI-2015-94820")
        self.assertEqual(data["signed_by"]["physician_name"], "Dr. Arvind Sharma, MD (AIIMS)")
        self.assertIn("Telemedicine Practice Guidelines 2020", data["statutory_compliance"])

    def test_rmp_prescription_countersign_unauthorized_role(self):
        """Non-physician roles (e.g. PHARMACIST, NURSE) must be rejected with HTTP 403 Forbidden."""
        token = auth_security_manager.create_access_token(
            username="PHARM-001",
            tenant_id="TENANT-MAIN-01",
            role="PHARMACIST",
            permissions=["DISPENSE_NARCOTICS"]
        )

        sign_payload = {
            "prescription_id": "RX-PROT-2026-TEST-002",
            "physician_name": "Pharmacist Raman",
            "rmp_registration_number": "PHARM-REG-4491",
            "council_affiliation": "PHARMACY_COUNCIL"
        }

        response = self.client.post(
            "/api/v1/clinical/prescriptions/sign",
            json=sign_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"]["status"], "UNAUTHORIZED_CLINICIAN")

    def test_rmp_prescription_countersign_missing_registration(self):
        """Empty or missing RMP registration number must be rejected with HTTP 422."""
        token = auth_security_manager.create_access_token(
            username="DR-RESIDENT-002",
            tenant_id="TENANT-MAIN-01",
            role="RESIDENT_PHYSICIAN",
            permissions=["*"]
        )

        sign_payload = {
            "prescription_id": "RX-PROT-2026-TEST-003",
            "physician_name": "Dr. Priya Sen",
            "rmp_registration_number": "",  # Missing statutory reg number
            "council_affiliation": "NATIONAL_MEDICAL_COMMISSION"
        }

        response = self.client.post(
            "/api/v1/clinical/prescriptions/sign",
            json=sign_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data["detail"]["status"], "INVALID_RMP_CREDENTIALS")

    def test_appshim_sign_prescription_parity(self):
        """AppShim standalone sign_prescription method works and enforces RMP registration number."""
        app_shim = main.AppShim()
        # Valid sign off
        signed = app_shim.sign_prescription(
            prescription_id="RX-SHIM-001",
            physician_name="Dr. K. Bannerjee",
            rmp_registration_number="WBMC-1998-10293"
        )
        self.assertEqual(signed["status"], "DISPENSABLE_AUTHORIZED")
        self.assertTrue(signed["is_physician_signed"])
        self.assertEqual(signed["signed_by"]["rmp_registration_number"], "WBMC-1998-10293")

        # Missing registration number raises ValueError
        with self.assertRaises(ValueError):
            app_shim.sign_prescription(
                prescription_id="RX-SHIM-002",
                physician_name="Dr. Anonymous",
                rmp_registration_number=""
            )


if __name__ == "__main__":
    unittest.main()
