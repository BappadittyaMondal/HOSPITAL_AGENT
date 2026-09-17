"""
Test Suite: test_production_scorecard_redteam.py
Phase 15: AI Governance, Red-Team, Simulation & Production Release Gate
Mandate / Quality Gate 1:
  - 12-Persona External Red-Team Audit confirming zero unmitigated High or Critical security/clinical risks.
  - Inviolable Quality Gate 1: All 20 items on the Production Release Scorecard pass without exception.
  - Generates 30-Day Supervised Clinical Pilot Protocol.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from production_scorecard_audit import (
    ProductionScorecardAuditEngine,
    ScorecardEvaluationError,
)


class TestProductionScorecardRedTeam(unittest.TestCase):

    def setUp(self):
        self.engine = ProductionScorecardAuditEngine()

    def test_12_persona_red_team_audit(self):
        """Validates that 12-Persona Red-Team Audit confirms 0 unmitigated Critical or High risks."""
        report = self.engine.execute_12_persona_red_team_audit()

        self.assertEqual(report["total_personas_tested"], 12)
        self.assertEqual(report["unmitigated_critical_or_high_risks"], 0)
        self.assertTrue(report["risk_register_passed"])

    def test_quality_gate_1_final_20_point_production_scorecard(self):
        """
        Quality Gate 1:
        All 20 items on the Production Release Scorecard pass without exception (100.0% compliance).
        Certifies STATUS = QUALIFIED FOR 30-DAY SUPERVISED CLINICAL PILOT.
        """
        scorecard = self.engine.evaluate_20_point_production_scorecard()

        self.assertEqual(scorecard["total_gates_evaluated"], 20)
        self.assertEqual(scorecard["passed_gates_count"], 20)
        self.assertEqual(scorecard["compliance_pct"], 100.0)
        self.assertEqual(scorecard["overall_status"], "QUALIFIED_FOR_30_DAY_SUPERVISED_CLINICAL_PILOT")

        # Verify specific critical gates
        results = scorecard["scorecard_results"]

        # Gate 1: Wrong patient medication
        g1 = next(g for g in results if g["gate_number"] == 1)
        self.assertEqual(g1["required_answer"], "MUST BE NO")
        self.assertEqual(g1["achieved_answer"], "NO")

        # Gate 2: GenAI autonomous prescribing
        g2 = next(g for g in results if g["gate_number"] == 2)
        self.assertEqual(g2["required_answer"], "MUST BE NO")
        self.assertEqual(g2["achieved_answer"], "NO")

        # Gate 4: Offline edge bed double-allocation
        g4 = next(g for g in results if g["gate_number"] == 4)
        self.assertEqual(g4["required_answer"], "MUST BE NO")
        self.assertEqual(g4["achieved_answer"], "NO")

        # Gate 9: 72h offline operation
        g9 = next(g for g in results if g["gate_number"] == 9)
        self.assertEqual(g9["required_answer"], "MUST BE YES")
        self.assertEqual(g9["achieved_answer"], "YES")

        # Gate 10: RTO < 4h
        g10 = next(g for g in results if g["gate_number"] == 10)
        self.assertEqual(g10["required_answer"], "MUST BE YES")
        self.assertEqual(g10["achieved_answer"], "YES")

        # Gate 17: NPO meal block
        g17 = next(g for g in results if g["gate_number"] == 17)
        self.assertEqual(g17["required_answer"], "MUST BE NO")
        self.assertEqual(g17["achieved_answer"], "NO")

        # Gate 20: 5,000 concurrent users at P99 < 200ms
        g20 = next(g for g in results if g["gate_number"] == 20)
        self.assertEqual(g20["required_answer"], "MUST BE YES")
        self.assertEqual(g20["achieved_answer"], "YES")

    def test_30_day_supervised_pilot_protocol(self):
        """Tests generation of 30-Day Supervised Clinical Pilot protocol."""
        proto = self.engine.generate_pilot_deployment_protocol()
        self.assertEqual(proto["protocol_name"], "30_DAY_SUPERVISED_CLINICAL_PILOT_DEPLOYMENT_PROTOCOL")
        self.assertEqual(len(proto["rollout_stages"]), 5)
        self.assertEqual(proto["emergency_rollback_time_minutes"], 5)
        self.assertTrue(proto["clinical_safety_board_convened"])


if __name__ == "__main__":
    unittest.main()
