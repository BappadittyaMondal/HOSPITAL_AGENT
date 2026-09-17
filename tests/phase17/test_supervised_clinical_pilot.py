"""
====================================================================================================
TEST SUITE: PHASE 17.3 — 5-STAGE SUPERVISED CLINICAL PILOT SURVEILLANCE ENGINE
====================================================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from supervised_clinical_pilot_engine import (
    SupervisedClinicalPilotEngine,
    PilotGateThresholdDeficitError,
    PilotSurveillanceException
)


class TestSupervisedClinicalPilot(unittest.TestCase):

    def setUp(self):
        self.orchestrator = SupervisedClinicalPilotEngine()

    def test_stage_1_opd_shadow_mode_and_advancement(self):
        """Quality Gate 3: Stage 1 shadow discrepancy rate must be <= 1.0% to advance."""
        # 1000 encounters with 5 discrepancies = 0.5% (passes <= 1.0% gate)
        self.orchestrator.record_stage_1_opd_metrics(
            total_shadow_encounters=1000,
            discrepant_encounters=5,
            smart_paper_qr_scans_successful=995
        )

        # Attempt advance without valid CSB token raises error
        with self.assertRaises(PilotSurveillanceException):
            self.orchestrator.advance_stage(from_stage=1, csb_auth_token="INVALID_TOKEN")

        # Advance with valid token succeeds
        res = self.orchestrator.advance_stage(from_stage=1, csb_auth_token="CSB-AUTH-STAGE-1-TOKEN-XYZ")
        self.assertEqual(res["next_stage"], 2)
        self.assertEqual(self.orchestrator.current_stage, 2)

    def test_stage_1_fails_when_discrepancy_exceeds_1_percent(self):
        """Quality Gate 3: Stage 1 blocks graduation if shadow discrepancy > 1.0%."""
        # 1000 encounters with 15 discrepancies = 1.5% (> 1.0% threshold)
        self.orchestrator.record_stage_1_opd_metrics(
            total_shadow_encounters=1000,
            discrepant_encounters=15,
            smart_paper_qr_scans_successful=985
        )

        with self.assertRaises(PilotGateThresholdDeficitError) as ctx:
            self.orchestrator.advance_stage(from_stage=1, csb_auth_token="CSB-AUTH-STAGE-1-TOKEN-XYZ")
        self.assertIn("exceeds 1.0%", str(ctx.exception))

    def test_full_5_stage_pilot_progression_and_enterprise_certification(self):
        """Quality Gate 3: Sequentially advances Stages 1 to 5 and certifies Enterprise Go-Live."""
        # Stage 1: OPD Shadow
        self.orchestrator.record_stage_1_opd_metrics(500, 2, 498)
        self.orchestrator.advance_stage(1, "CSB-AUTH-STAGE-1-VALID")

        # Stage 2: Emergency Department (100% financial decoupling)
        self.orchestrator.record_stage_2_emergency_metrics(120, 120, temp_id_generation_p99_ms=0.08)
        self.orchestrator.advance_stage(2, "CSB-AUTH-STAGE-2-VALID")

        # Stage 3: Inpatient Wards (99.8% eMAR scan, 0 NPO leaks)
        self.orchestrator.record_stage_3_inpatient_metrics(2000, 1996, npo_meal_attempts_blocked=14, npo_meals_dispatched_to_patient=0)
        self.orchestrator.advance_stage(3, "CSB-AUTH-STAGE-3-VALID")

        # Stage 4: ICU & OT (100% sub-5s alarms, 0 retained sponges)
        self.orchestrator.record_stage_4_icu_ot_metrics(45, 45, surgical_cases_completed=88, retained_sponge_discrepancies_at_closure=0)
        self.orchestrator.advance_stage(4, "CSB-AUTH-STAGE-4-VALID")

        # Stage 5: Enterprise Review & Go-Live Certification
        cert = self.orchestrator.certify_enterprise_go_live(
            nurse_ergonomics_score_out_of_5=4.6,
            p99_latency_ms=138.4,
            medical_superintendent_signature_token="MS-SIG-SHA256-BOARD-CERTIFIED-2026"
        )
        self.assertEqual(cert["status"], "PERMANENT_PRODUCTION_APPROVED")
        self.assertEqual(cert["pilot_duration_days"], 30)


if __name__ == "__main__":
    unittest.main()
