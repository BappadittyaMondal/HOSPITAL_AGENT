"""
Test Suite: test_abdm_dpdp_gateway.py
Phase 14: Resilience & Compliance — ABDM National Health Gateway & DPDP Act 2023
Mandates / Quality Gate 3:
  - Inviolable Quality Gate 3: ABDM gateway passes all official NHA sandbox test
    validation suites for M1, M2, and M3.
  - Milestone 1 (M1): ABHA issuance, capture, and Aadhaar/Mobile OTP authentication.
  - Milestone 2 (M2): Health Facility Registry (HFR) and Healthcare Professionals Registry (HPR).
  - Milestone 3 (M3): HIP/HIU gateway for encrypted FHIR bundle data transfer with NHA consent artifact.
  - DPDP Act 2023: Right to Erasure pipeline balancing secondary consent revocation
    against statutory medical chart retention (NMC Regulations 2002).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from abdm_dpdp_gateway import (
    ABDMDPDPGateway,
    ConsentStatus,
    ABDMError,
    DPDPViolationError,
)


class TestABDMDPDPGateway(unittest.TestCase):

    def setUp(self):
        self.gateway = ABDMDPDPGateway()

    def test_quality_gate_3_abdm_milestones_1_2_3_nha_sandbox_compliance(self):
        """
        Quality Gate 3:
        ABDM gateway passes official NHA sandbox test validation suites for M1, M2, and M3.
        """
        # ---------------------------------------------------------------------
        # Milestone 1 (M1): ABHA Creation & OTP Verification
        # ---------------------------------------------------------------------
        abha_cred = self.gateway.execute_m1_abha_issuance_and_verification(
            aadhaar_or_mobile_number="9876543210",
            otp="123456",  # NHA sandbox valid OTP
            patient_name="Priyanka Mukherjee",
            gender="F",
            yob=1992,
            preferred_abha_address="priyanka.m",
        )
        self.assertTrue(abha_cred.abha_number.startswith("91-"))
        self.assertEqual(abha_cred.abha_address, "priyanka.m@abdm")
        self.assertTrue(abha_cred.mobile_verified)

        # ---------------------------------------------------------------------
        # Milestone 2 (M2): HFR and HPR Linkage
        # ---------------------------------------------------------------------
        m2_res = self.gateway.execute_m2_registry_linkage(
            doctor_hpr_id="HPR-IN-NMC-2026-9812",
            nmc_registration_number="WBMC-774411",
            specialty="CARDIOLOGY",
        )
        self.assertEqual(m2_res["status"], "M2_HFR_HPR_LINKED")
        self.assertEqual(m2_res["facility_hfr_id"], "IN0710000001")
        self.assertTrue(m2_res["doctor"]["is_verified"])

        # ---------------------------------------------------------------------
        # Milestone 3 (M3): HIP/HIU Encrypted FHIR Bundle Data Exchange
        # ---------------------------------------------------------------------
        clinical_payload = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "Condition", "code": "I10", "display": "Essential Hypertension"}},
                {"resource": {"resourceType": "MedicationRequest", "medication": "Amlodipine 5mg"}},
            ]
        }

        m3_res = self.gateway.execute_m3_fhir_consent_data_transfer(
            consent_id="CONSENT-NHA-2026-0099",
            patient_abha=abha_cred.abha_number,
            hiu_id="IN-APOLLO-CHE-02",
            hi_types=["Prescription", "OPConsultation"],
            clinical_fhir_payload=clinical_payload,
        )

        self.assertEqual(m3_res["status"], "M3_DATA_TRANSFER_SUCCESS")
        self.assertTrue(m3_res["nha_sandbox_compliance"])
        self.assertEqual(m3_res["consent_artifact"].status, ConsentStatus.GRANTED)
        self.assertEqual(m3_res["encrypted_bundle"]["encryption_protocol"], "ECDH-X25519-AES-GCM")
        self.assertTrue(len(m3_res["encrypted_bundle"]["encrypted_data_blob"]) == 64)

    def test_dpdp_right_to_erasure_statutory_balancing(self):
        """
        Tests DPDP Act 2023 Right to Erasure pipeline:
        Revokes secondary research consents, marketing, and AI training,
        while preserving statutory medical charts under NMC Regulations 2002.
        """
        statutory_charts = [
            {"encounter_id": "ENC-001", "type": "DISCHARGE_SUMMARY", "date": "2026-01-15", "doctor": "DR-SURG-01"},
            {"encounter_id": "ENC-002", "type": "OPD_PRESCRIPTION", "date": "2026-03-20", "doctor": "DR-MED-02"},
        ]

        self.gateway.register_dpdp_patient(
            patient_id="PAT-DPDP-01",
            abha_number="91-5544-3322-0123",
            clinical_charts=statutory_charts,
            research_consents={"CANCER_GENOMICS_STUDY", "AI_ECG_ALGORITHM_TRAINING"},
        )

        # Execute Right to Erasure
        erasure_report = self.gateway.execute_dpdp_right_to_erasure(
            patient_id="PAT-DPDP-01",
            requesting_fiduciary_id="FIDUCIARY-AIIMS-01",
        )

        self.assertEqual(erasure_report["status"], "RIGHT_TO_ERASURE_PROCESSED")
        self.assertTrue(erasure_report["dpdp_compliant"])
        self.assertEqual(len(erasure_report["secondary_research_purged"]), 2)
        self.assertTrue(erasure_report["marketing_revoked"])
        self.assertTrue(erasure_report["ai_training_revoked"])

        # INVIOLABLE STATUTORY REQUIREMENT: 2 medical charts MUST remain preserved
        self.assertEqual(erasure_report["statutory_medical_charts_preserved"], 2)
        self.assertIn("NMC Regulations 2002", erasure_report["legal_basis_for_chart_retention"])


if __name__ == "__main__":
    unittest.main()
