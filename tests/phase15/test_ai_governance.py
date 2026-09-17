"""
Test Suite: test_ai_governance.py
Phase 15: AI Governance, Red-Team, Simulation & Production Release Gate
Mandates:
  - 3-tier model serving architecture (Tier 1 Edge Local, Tier 2 Cloud Multimodal, Tier 3 Batch).
  - Departmental monthly token budget capping with automated fallback degradation.
  - Latency SLA verification (Tier 1 < 50ms, Tier 2 < 10s).
  - Privacy-preserving federated learning with differential privacy guarantees (epsilon <= 1.0).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from ai_governance_serving import (
    AIGovernanceServingEngine,
    ModelServingTier,
    AIGovernanceError,
)


class TestAIGovernanceServingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AIGovernanceServingEngine()

        # Set budget for Emergency Department: 10,000 tokens
        self.engine.set_department_token_budget(
            department_id="DEPT-EMERGENCY",
            monthly_budget_tokens=10000,
            enforce_hard_cap=True,
        )

    def test_tier_1_latency_sla(self):
        """Tier 1 edge local inference must complete within sub-50ms latency SLA."""
        res = self.engine.route_ai_inference_request(
            request_id="REQ-SAFETY-01",
            department_id="DEPT-EMERGENCY",
            requested_tier=ModelServingTier.TIER_1_EDGE_LOCAL,
            input_token_estimate=150,
        )

        self.assertEqual(res["status"], "COMPLETED")
        self.assertTrue(res["sla_met"])
        self.assertLess(res["latency_ms"], 50.0)
        self.assertEqual(res["output"]["execution_engine"], "RUST_DRE_LOCAL")

    def test_token_budget_exceeded_fallback_chain(self):
        """
        When department exceeds its monthly token budget, system automatically
        degrades gracefully to Tier 1 local deterministic safety rules instead of halting.
        """
        # Consume almost full budget
        self.engine.route_ai_inference_request(
            request_id="REQ-LARGE-01",
            department_id="DEPT-EMERGENCY",
            requested_tier=ModelServingTier.TIER_2_CLOUD_MULTIMODAL,
            input_token_estimate=9500,
        )

        # Next request exceeds 10,000 limit -> Triggers automatic fallback
        fallback_res = self.engine.route_ai_inference_request(
            request_id="REQ-OVERFLOW-02",
            department_id="DEPT-EMERGENCY",
            requested_tier=ModelServingTier.TIER_2_CLOUD_MULTIMODAL,
            input_token_estimate=1000,
        )

        self.assertEqual(fallback_res["status"], "FALLBACK_DETERMINISTIC_RULES")
        self.assertEqual(fallback_res["active_tier"], ModelServingTier.TIER_1_EDGE_LOCAL.value)
        self.assertIn("exceeded monthly budget", fallback_res["reason"])

    def test_cloud_api_outage_fallback(self):
        """When Cloud AI API experiences an outage, system immediately executes local fallback."""
        res = self.engine.route_ai_inference_request(
            request_id="REQ-OUTAGE-01",
            department_id="DEPT-MEDICINE",
            requested_tier=ModelServingTier.TIER_2_CLOUD_MULTIMODAL,
            input_token_estimate=500,
            simulated_cloud_failure=True,
        )

        self.assertEqual(res["status"], "CLOUD_FAILURE_FALLBACK_EXECUTED")
        self.assertEqual(res["active_tier"], ModelServingTier.TIER_1_EDGE_LOCAL.value)
        self.assertIn("Tier 2 Cloud -> Tier 1 Edge Local Rules", res["fallback_chain"])

    def test_privacy_preserving_federated_learning(self):
        """Tests federated learning round with differential privacy (epsilon <= 1.0) and zero raw data transmission."""
        self.engine.register_federated_client("HOSP-01", "AIIMS Delhi", 5000, "HASH-W-01", epsilon=0.4)
        self.engine.register_federated_client("HOSP-02", "PGIMER Chandigarh", 4000, "HASH-W-02", epsilon=0.5)
        self.engine.register_federated_client("HOSP-03", "CMC Vellore", 3000, "HASH-W-03", epsilon=0.6)

        fed_round = self.engine.aggregate_federated_round()
        self.assertEqual(fed_round["participating_hospitals"], 3)
        self.assertEqual(fed_round["total_synthetic_training_samples"], 12000)
        self.assertTrue(fed_round["differential_privacy_guaranteed"])
        self.assertFalse(fed_round["raw_data_transmission_occurred"])


if __name__ == "__main__":
    unittest.main()
