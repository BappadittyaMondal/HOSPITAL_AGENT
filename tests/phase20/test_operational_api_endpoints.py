"""
PROJECT "HOSPITAL" — PHASE 20: OPERATIONAL API ROUTING & SAFETY GATES
Test Suite: test_operational_api_endpoints.py
Validates live FastAPI endpoints for:
  - Blood Bank ABO/Rh Inviolable Crossmatch Gate (/api/v1/transfusion/crossmatch)
  - NDPS Schedule X Dual-Witness Narcotic Vault (/api/v1/pharmacy/narcotics/dispense)
  - PM-JAY Bundled Package Anti-Breakage Adjudication (/api/v1/billing/pmjay/adjudicate)
  - Pessimistic Edge Resource Leasing for 72h WAN Partition (/api/v1/edge/leases/request)
  - Digital WHO Partograph Action Line Alarm (/api/v1/clinical/partograph/record)
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
import main


class TestOperationalAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)

    def test_blood_bank_crossmatch_compatible(self):
        """Compatible blood unit must crossmatch cleanly with HTTP 200."""
        payload = {
            "recipient_mrn": "MRN-PT-001",
            "recipient_blood_group": "O_POS",
            "unit_barcode": "UNIT-O-NEG-001",
            "transfusion_order_id": "ORD-TX-001"
        }
        res = self.client.post("/api/v1/transfusion/crossmatch", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["compatible"])
        self.assertEqual(data["status"], "CROSSMATCH_VERIFIED_COMPATIBLE")

    def test_blood_bank_crossmatch_incompatible_blocked(self):
        """Incompatible unit (A+ to O- recipient) must be hard-blocked with HTTP 422."""
        payload = {
            "recipient_mrn": "MRN-PT-002",
            "recipient_blood_group": "O_NEG",
            "unit_barcode": "UNIT-A-POS-001",
            "transfusion_order_id": "ORD-TX-002"
        }
        res = self.client.post("/api/v1/transfusion/crossmatch", json=payload)
        self.assertEqual(res.status_code, 422)
        detail = res.json()["detail"]
        self.assertFalse(detail["compatible"])
        self.assertEqual(detail["status"], "TRANSFUSION_INCOMPATIBLE_BLOCKED")

    def test_ndps_narcotics_dispense_dual_witness_success(self):
        """Narcotic dispense with two distinct verified witnesses must succeed with HTTP 200."""
        payload = {
            "drug_id": "MORPHINE_10MG",
            "batch_number": "BATCH-MOR-2026-01",
            "quantity": 2,
            "patient_id": "PAT-ICU-001",
            "order_id": "ORD-MED-991",
            "primary_user_id": "PHARM-SHARMA",
            "primary_role": "PHARMACIST",
            "primary_bio_token": "BIO-PHARM-VALID",
            "primary_bio_verified": True,
            "secondary_user_id": "NURSE-PRIYA",
            "secondary_role": "NURSE_INCHARGE",
            "secondary_bio_token": "BIO-NURSE-VALID",
            "secondary_bio_verified": True
        }
        res = self.client.post("/api/v1/pharmacy/narcotics/dispense", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "NARCOTIC_DISPENSED_SUCCESS")
        self.assertEqual(data["dispensed_quantity"], 2)
        self.assertIn("remaining_balance", data)
        self.assertIn("current_hash", data)

    def test_ndps_narcotics_dispense_same_user_rejected(self):
        """Primary and secondary witness as the same user must be rejected with HTTP 403."""
        payload = {
            "drug_id": "MORPHINE_10MG",
            "batch_number": "BATCH-MOR-2026-01",
            "quantity": 1,
            "patient_id": "PAT-ICU-002",
            "order_id": "ORD-MED-992",
            "primary_user_id": "PHARM-SHARMA",
            "primary_role": "PHARMACIST",
            "primary_bio_verified": True,
            "secondary_user_id": "PHARM-SHARMA",
            "secondary_role": "PHARMACIST",
            "secondary_bio_verified": True
        }
        res = self.client.post("/api/v1/pharmacy/narcotics/dispense", json=payload)
        self.assertEqual(res.status_code, 403)
        detail = res.json()["detail"]
        self.assertEqual(detail["status"], "DUAL_BIOMETRIC_AUTH_FAILED")

    def test_pmjay_adjudicate_package_breakage_blocked(self):
        """Illegal billing of consumables under all-inclusive PM-JAY package must be blocked with HTTP 422."""
        payload = {
            "encounter_id": "ENC-PMJAY-101",
            "patient_id": "PAT-RURAL-001",
            "pmjay_card_id": "AB-PMJAY-998877",
            "package_code": "SG001A",
            "item_code": "CONS-001",
            "item_name": "Surgical Gloves Box",
            "category": "CONSUMABLES",
            "amount_inr": 450.0
        }
        res = self.client.post("/api/v1/billing/pmjay/adjudicate", json=payload)
        self.assertEqual(res.status_code, 422)
        detail = res.json()["detail"]
        self.assertIn("Illegal attempt to bill unbundled item", detail["error"])

    def test_pmjay_adjudicate_specialty_addon_approved(self):
        """Legitimate specialty addon outside bundled list must be approved with HTTP 200."""
        payload = {
            "encounter_id": "ENC-PMJAY-102",
            "patient_id": "PAT-RURAL-002",
            "pmjay_card_id": "AB-PMJAY-998878",
            "package_code": "SG001A",
            "item_code": "IMP-001",
            "item_name": "Specialized Titanium Mesh",
            "category": "SPECIALTY_IMPLANT",
            "amount_inr": 12500.0
        }
        res = self.client.post("/api/v1/billing/pmjay/adjudicate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "PMJAY_ADDON_APPROVED")
        self.assertEqual(data["adjudicated_amount_inr"], 12500.0)

    def test_edge_resource_lease_grant_and_conflict(self):
        """Class A ICU bed lease granted to Node 1 must conflict if requested by Node 2."""
        payload1 = {
            "node_id": "EDGE-NODE-01",
            "resource_id": "ICU-BED-09",
            "resource_type": "ICU_BED",
            "duration_hours": 72.0
        }
        res1 = self.client.post("/api/v1/edge/leases/request", json=payload1)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1["status"], "LEASE_GRANTED")
        self.assertTrue(data1["is_active"])

        # Conflicting request for same bed from another node
        payload2 = {
            "node_id": "EDGE-NODE-02",
            "resource_id": "ICU-BED-09",
            "resource_type": "ICU_BED",
            "duration_hours": 72.0
        }
        res2 = self.client.post("/api/v1/edge/leases/request", json=payload2)
        self.assertEqual(res2.status_code, 409)
        detail2 = res2.json()["detail"]
        self.assertEqual(detail2["status"], "LEASE_CONFLICT_REJECTED")

    def test_obstetrics_partograph_normal_and_action_line_breach(self):
        """Partograph must track normal labor and trigger emergency alert on action line breach."""
        # Normal labor progress: 5 cm dilatation at hour 1
        normal_payload = {
            "patient_id": "MOM-001",
            "hours_in_active_labor": 1.0,
            "cervical_dilatation_cm": 5.0,
            "fetal_heart_rate_bpm": 135.0,
            "contractions_per_10min": 3,
            "amniotic_fluid_state": "CLEAR"
        }
        res1 = self.client.post("/api/v1/clinical/partograph/record", json=normal_payload)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertFalse(data1["action_line_breached"])
        self.assertEqual(data1["urgency"], "NORMAL")

        # Obstructed labor: 4 cm dilatation at hour 8 (severe arrest)
        breached_payload = {
            "patient_id": "MOM-002",
            "hours_in_active_labor": 8.0,
            "cervical_dilatation_cm": 4.0,
            "fetal_heart_rate_bpm": 105.0,
            "contractions_per_10min": 1,
            "amniotic_fluid_state": "MECONIUM_STAINED"
        }
        res2 = self.client.post("/api/v1/clinical/partograph/record", json=breached_payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2["action_line_breached"])
        self.assertEqual(data2["urgency"], "EMERGENCY_OBSTETRIC_INTERVENTION")
        self.assertIn("ACTION LINE BREACHED", data2["recommended_action"])


if __name__ == "__main__":
    unittest.main()
