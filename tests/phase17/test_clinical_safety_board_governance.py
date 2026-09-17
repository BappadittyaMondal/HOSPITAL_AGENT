"""
====================================================================================================
TEST SUITE: PHASE 17.1 — CLINICAL SAFETY BOARD (CSB) GOVERNANCE ENGINE
====================================================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from clinical_safety_board_governance import (
    ClinicalSafetyBoardGovernanceEngine,
    QuorumNotMetError,
    EmergencySafetyPauseActiveError,
    GovernanceSafetyException
)


class TestClinicalSafetyBoardGovernance(unittest.TestCase):

    def setUp(self):
        self.csb = ClinicalSafetyBoardGovernanceEngine()
        # Register full statutory board members
        self.csb.register_board_member("MB-MS-01", "Dr. A. Sharma", "MEDICAL_SUPERINTENDENT", "NMC-10101")
        self.csb.register_board_member("MB-CNO-01", "Sister M. Roy", "CHIEF_NURSING_OFFICER", "INC-20202")
        self.csb.register_board_member("MB-PHARM-01", "Dr. P. Das", "HEAD_OF_PHARMACY", "PCI-30303")
        self.csb.register_board_member("MB-CIO-01", "Mr. R. Sen", "CHIEF_INFORMATION_OFFICER")
        self.csb.register_board_member("MB-LEGAL-01", "Adv. S. Bose", "LEGAL_COUNSEL")
        self.csb.register_board_member("MB-MED-01", "Dr. K. Ghosh", "HEAD_OF_INTERNAL_MEDICINE", "NMC-40404")
        self.csb.register_board_member("MB-SURG-01", "Dr. T. Banerjee", "HEAD_OF_SURGERY", "NMC-50505")

    def test_quorum_validation_requires_ms_and_cno(self):
        """Quality Gate 1: CSB quorum strictly blocks proceedings if MS or CNO is absent, or < 6 members."""
        # Case 1: MS is missing
        attending_without_ms = ["MB-CNO-01", "MB-PHARM-01", "MB-CIO-01", "MB-LEGAL-01", "MB-MED-01", "MB-SURG-01"]
        self.assertFalse(self.csb.verify_quorum(attending_without_ms))

        # Case 2: CNO is missing
        attending_without_cno = ["MB-MS-01", "MB-PHARM-01", "MB-CIO-01", "MB-LEGAL-01", "MB-MED-01", "MB-SURG-01"]
        self.assertFalse(self.csb.verify_quorum(attending_without_cno))

        # Case 3: Less than 6 members present
        attending_few = ["MB-MS-01", "MB-CNO-01", "MB-MED-01"]
        self.assertFalse(self.csb.verify_quorum(attending_few))

        # Case 4: Full quorum with MS, CNO and 6+ members
        attending_full = ["MB-MS-01", "MB-CNO-01", "MB-PHARM-01", "MB-CIO-01", "MB-LEGAL-01", "MB-MED-01"]
        self.assertTrue(self.csb.verify_quorum(attending_full))

    def test_cryptographic_stage_authorization_token_issuance(self):
        """Verifies HMAC-SHA256 stage-gate authorization token is issued when scorecard is 100%."""
        attending_full = ["MB-MS-01", "MB-CNO-01", "MB-PHARM-01", "MB-CIO-01", "MB-LEGAL-01", "MB-MED-01"]

        # Fails when scorecard compliance < 100%
        with self.assertRaises(GovernanceSafetyException):
            self.csb.issue_stage_authorization_token(
                stage_number=1,
                attending_member_ids=attending_full,
                scorecard_compliance_percent=95.0
            )

        # Fails when quorum not met
        with self.assertRaises(QuorumNotMetError):
            self.csb.issue_stage_authorization_token(
                stage_number=1,
                attending_member_ids=["MB-MS-01"],
                scorecard_compliance_percent=100.0
            )

        # Succeeds when 100% scorecard and quorum met
        auth_record = self.csb.issue_stage_authorization_token(
            stage_number=1,
            attending_member_ids=attending_full,
            scorecard_compliance_percent=100.0
        )
        self.assertIn("CSB-AUTH-STAGE-1-", auth_record["token"])
        self.assertEqual(auth_record["status"], "VALID")

    def test_emergency_safety_pause_and_dissent_recording(self):
        """Verifies emergency safety pause halts stage authorizations, and dissent is logged."""
        # Trigger emergency pause
        pause_event = self.csb.trigger_emergency_safety_pause(
            reason="Suspected barcode scanner misreads in phlebotomy",
            initiated_by_member_id="MB-CNO-01"
        )
        self.assertTrue(self.csb.is_paused)

        # Attempting stage authorization while paused raises error
        attending_full = ["MB-MS-01", "MB-CNO-01", "MB-PHARM-01", "MB-CIO-01", "MB-LEGAL-01", "MB-MED-01"]
        with self.assertRaises(EmergencySafetyPauseActiveError):
            self.csb.issue_stage_authorization_token(1, attending_full, 100.0)

        # Record clinical dissent
        dissent = self.csb.record_clinical_dissent(
            member_id="MB-SURG-01",
            stage_number=1,
            objection_details="Requested 24-hour additional shadow run in pre-op holding."
        )
        self.assertEqual(dissent["role"], "HEAD_OF_SURGERY")

        # Resolve pause with full quorum
        resolve_res = self.csb.resolve_emergency_safety_pause(
            resolution_notes="Scanner lens cleaned, firmware updated, re-verified.",
            attending_member_ids=attending_full
        )
        self.assertFalse(self.csb.is_paused)


if __name__ == "__main__":
    unittest.main()
