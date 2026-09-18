#!/usr/bin/env python3
"""
PROJECT "HOSPITAL" — PHASE 25: SECURITY, EDGE MONOTONIC FENCING & ABDM AES-GCM SUITE
Module: tests/phase25/test_auth_edge_and_abdm.py
Validates:
  1. Zero-Trust Route Authorization & Anti-Tenant-Tampering Gate (403 on tenant header mismatch).
  2. Granular Route Role/Permission Enforcement (403 on missing mandatory permission).
  3. Dynamic Liveness & Subsystem Readiness Probes (/health & /ready).
  4. Monotonic Edge Fencing Tokens & Safe Unavailability on Expired Leases (StaleFencingTokenError).
  5. Genuine ABDM M3 AES-256-GCM Wire-Format Encryption with 128-bit Authentication Tag & Tamper Detection.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))
import main
from auth_manager import auth_security_manager
from edge_resilience_engine import (
    EdgeResilienceEngine,
    LocalEdgeTransaction,
    StaleFencingTokenError,
    ResourceNotLeasedError
)
from abdm_dpdp_gateway import (
    ABDMDPDPGateway,
    ABDMError
)


class TestAuthEdgeAndABDM(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(main.app)

        # Regular Doctor token for TENANT-MAIN-01 without billing permissions
        self.doctor_token = auth_security_manager.create_access_token(
            username="dr_sharma",
            tenant_id="TENANT-MAIN-01",
            role="CONSULTANT_PHYSICIAN",
            permissions=["order_medications", "view_clinical_chart"]
        )

        # Billing Clerk token for TENANT-MAIN-01 with BILLING_ADJUDICATE permission
        self.billing_token = auth_security_manager.create_access_token(
            username="clerk_patel",
            tenant_id="TENANT-MAIN-01",
            role="BILLING_EXECUTIVE",
            permissions=["BILLING_ADJUDICATE", "view_billing_reports"]
        )

        # Superadmin token
        self.admin_token = auth_security_manager.create_access_token(
            username="admin_singh",
            tenant_id="TENANT-MAIN-01",
            role="SUPERADMIN",
            permissions=["*"]
        )

    def test_anti_tenant_tampering_prohibits_cross_tenant_header(self):
        """A user authenticated for Tenant A cannot assert Tenant B via X-Tenant-ID header."""
        cross_tenant_headers = {
            "Authorization": f"Bearer {self.doctor_token}",
            "X-Tenant-ID": "TENANT-ROGUE-99"
        }
        res = self.client.post(
            "/api/v1/safety/evaluate-order",
            json={
                "patient_id": "PAT-001",
                "clinician_id": "DR-SHARMA-01",
                "items": [{"code": "PCM", "name": "Paracetamol", "dose": "500mg"}]
            },
            headers=cross_tenant_headers
        )
        self.assertEqual(res.status_code, 403)
        detail = res.json()["detail"]
        self.assertEqual(detail["status"], "FORBIDDEN")
        self.assertIn("Cross-tenant access prohibited", detail["error"])

    def test_superadmin_can_manage_cross_tenant(self):
        """Platform SUPERADMIN is permitted to access tenant contexts with valid authorization."""
        admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "X-Tenant-ID": "TENANT-BRANCH-02"
        }
        res = self.client.post(
            "/api/v1/safety/evaluate-order",
            json={
                "patient_id": "PAT-ADMIN-01",
                "clinician_id": "ADMIN-SINGH",
                "items": [{"code": "PCM", "name": "Paracetamol", "dose": "500mg"}]
            },
            headers=admin_headers
        )
        self.assertEqual(res.status_code, 200)

    def test_route_permission_enforcement_on_sensitive_routes(self):
        """Physician without BILLING_ADJUDICATE receives 403 when invoking claim adjudication."""
        physician_headers = {
            "Authorization": f"Bearer {self.doctor_token}",
            "X-Tenant-ID": "TENANT-MAIN-01"
        }
        claim_payload = {
            "encounter_id": "ENC-PMJAY-SEC-01",
            "patient_id": "PAT-001",
            "pmjay_card_id": "PMJAY-001",
            "package_code": "SG001A",
            "item_code": "IMP-001",
            "item_name": "Titanium Mesh",
            "category": "SPECIALTY_IMPLANT",
            "amount_inr": 12000.0
        }

        # 1. Doctor without billing permission is rejected
        res = self.client.post(
            "/api/v1/billing/pmjay/adjudicate",
            json=claim_payload,
            headers=physician_headers
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"]["status"], "FORBIDDEN")
        self.assertIn("BILLING_ADJUDICATE", res.json()["detail"]["error"])

        # 2. Billing executive with permission is authorized
        billing_headers = {
            "Authorization": f"Bearer {self.billing_token}",
            "X-Tenant-ID": "TENANT-MAIN-01"
        }
        res_ok = self.client.post(
            "/api/v1/billing/pmjay/adjudicate",
            json=claim_payload,
            headers=billing_headers
        )
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json()["status"], "PMJAY_ADDON_APPROVED")

    def test_dynamic_readiness_probe_healthy(self):
        """Readiness probe verifies core subsystem initialization dynamically."""
        res = self.client.get("/ready")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ready"])
        self.assertEqual(data["subsystems"]["dre_engine"], "HEALTHY")
        self.assertEqual(data["subsystems"]["blood_bank"], "HEALTHY")
        self.assertEqual(data["subsystems"]["narcotics_vault"], "HEALTHY")
        self.assertEqual(data["subsystems"]["edge_resilience"], "HEALTHY")

    def test_edge_monotonic_fencing_token_rejects_stale_tokens(self):
        """Edge node sync with lower/stale fencing token must be rejected with StaleFencingTokenError."""
        edge = EdgeResilienceEngine()

        tx1 = LocalEdgeTransaction(
            tx_id="TX-EDGE-01",
            node_id="EDGE_NODE_01",
            tx_type="OPD_REGISTRATION",
            entity_id="PAT-E01",
            payload={"dept": "GENERAL"},
            timestamp=datetime.now(timezone.utc)
        )

        # First sync with epoch token 100
        res1 = edge.sync_with_fencing_token(
            node_id="EDGE_NODE_01",
            fencing_token=100,
            transactions=[tx1]
        )
        self.assertIn(res1["status"], ("RECONCILIATION_COMPLETED", "QUEUED_OFFLINE_LOCAL"))

        # Subsequent sync with higher monotonic token 101 succeeds
        tx2 = LocalEdgeTransaction(
            tx_id="TX-EDGE-02",
            node_id="EDGE_NODE_01",
            tx_type="OPD_REGISTRATION",
            entity_id="PAT-E02",
            payload={"dept": "GENERAL"},
            timestamp=datetime.now(timezone.utc)
        )
        res2 = edge.sync_with_fencing_token(
            node_id="EDGE_NODE_01",
            fencing_token=101,
            transactions=[tx2]
        )
        self.assertIn(res2["status"], ("RECONCILIATION_COMPLETED", "QUEUED_OFFLINE_LOCAL"))

        # Regressed/stale token 99 or 100 must be rejected
        with self.assertRaises(StaleFencingTokenError) as ctx:
            edge.sync_with_fencing_token(
                node_id="EDGE_NODE_01",
                fencing_token=100,  # Stale! Current is 101
                transactions=[tx2]
            )
        self.assertIn("FENCING TOKEN REJECTED", str(ctx.exception))

    def test_edge_safe_unavailability_on_expired_lease(self):
        """Class A resource allocation during offline partition with expired lease must be blocked."""
        edge = EdgeResilienceEngine()

        # Grant lease with past expiration date
        now = datetime.now(timezone.utc)
        edge.grant_pessimistic_lease(
            node_id="EDGE_NODE_02",
            resource_id="ICU_BED_EXPIRED_01",
            resource_type="ICU_BED",
            duration_days=1
        )
        # Artificially expire the lease
        edge._leases["ICU_BED_EXPIRED_01"].expires_at = now - timedelta(hours=2)

        # Offline allocation attempt must raise ResourceNotLeasedError
        with self.assertRaises(ResourceNotLeasedError) as ctx:
            edge.execute_local_emergency_bed_allocation(
                node_id="EDGE_NODE_02",
                patient_id="PAT-CRITICAL-09",
                resource_id="ICU_BED_EXPIRED_01"
            )
        self.assertIn("expired", str(ctx.exception).lower())
        self.assertIn("Safe offline unavailability enforced", str(ctx.exception))

    def test_abdm_m3_genuine_aes_gcm_authenticated_encryption(self):
        """ABDM M3 FHIR payload encrypted with genuine AES-256-GCM and verified with 128-bit tag."""
        fhir_payload = {
            "resourceType": "Bundle",
            "id": "FHIR-BUNDLE-TEST-001",
            "entry": [
                {
                    "resource": {
                        "resourceType": "DiagnosticReport",
                        "code": {"coding": [{"code": "168537006", "display": "Non-contrast CT Brain"}]},
                        "conclusion": "No acute intracranial hemorrhage."
                    }
                }
            ]
        }

        # 1. Encrypt with genuine AES-GCM
        enc_package = ABDMDPDPGateway.encrypt_fhir_payload(fhir_payload)
        self.assertEqual(enc_package["encryption_protocol"], "ECDH-X25519-AES-GCM")
        self.assertEqual(enc_package["tag_bits"], 128)
        self.assertIn("iv_b64", enc_package)
        self.assertIn("auth_tag_b64", enc_package)
        self.assertIn("ciphertext_b64", enc_package)

        key = bytes.fromhex(enc_package["key_hex"])

        # 2. Decrypt with correct key -> recovers original payload
        decrypted = ABDMDPDPGateway.decrypt_fhir_payload(enc_package, key)
        self.assertEqual(decrypted["id"], "FHIR-BUNDLE-TEST-001")
        self.assertEqual(decrypted["entry"][0]["resource"]["conclusion"], "No acute intracranial hemorrhage.")

        # 3. Tamper detection: modifying ciphertext or auth tag must fail verification
        tampered_package = dict(enc_package)
        import base64
        raw_ct = base64.b64decode(tampered_package["ciphertext_b64"])
        tampered_ct = bytes([raw_ct[0] ^ 0xFF]) + raw_ct[1:]
        tampered_package["ciphertext_b64"] = base64.b64encode(tampered_ct).decode("utf-8")
        tampered_package.pop("encrypted_data_blob", None)  # Force using separate ciphertext + tag

        with self.assertRaises(ABDMError) as ctx:
            ABDMDPDPGateway.decrypt_fhir_payload(tampered_package, key)
        self.assertIn("tag verification failed", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
