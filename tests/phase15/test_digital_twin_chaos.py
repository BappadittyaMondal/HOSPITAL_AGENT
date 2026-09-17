"""
Test Suite: test_digital_twin_chaos.py
Phase 15: AI Governance, Red-Team, Simulation & Production Release Gate
Mandates:
  - 100,000 synthetic patient journey simulation across 30 operational days (Gap 24).
  - High concurrency stress testing (5,000+ users at P99 < 200ms).
  - Catastrophic mass casualty surge: 200 simultaneous trauma arrivals with zero billing delays.
  - Chaos engineering: Injected database failover, network drops, PACS storage saturation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from hospital_digital_twin_chaos import (
    HospitalDigitalTwinChaosEngine,
    ChaosExperimentType,
)


class TestHospitalDigitalTwinChaos(unittest.TestCase):

    def setUp(self):
        self.engine = HospitalDigitalTwinChaosEngine()

    def test_full_hospital_30_day_simulation(self):
        """Validates execution of 100,000 synthetic patient journeys across 30 days."""
        sim = self.engine.run_full_hospital_30_day_simulation(
            total_synthetic_patients=100000,
            simulated_days=30,
        )

        self.assertEqual(sim["total_synthetic_patients"], 100000)
        self.assertEqual(sim["simulated_operational_days"], 30)
        self.assertEqual(sim["opd_encounters_completed"], 70000)
        self.assertEqual(sim["emergency_admissions_completed"], 15000)
        self.assertEqual(sim["surgical_procedures_completed"], 3000)
        self.assertGreaterEqual(sim["concurrency_peak_users"], 5000)
        self.assertLess(sim["p99_latency_ms"], 200.0)
        self.assertTrue(sim["zero_clinical_corruption_certified"])

    def test_mass_casualty_trauma_surge(self):
        """Validates simulated surge of 200 simultaneous trauma arrivals."""
        surge = self.engine.simulate_mass_casualty_surge(trauma_patient_count=200)

        self.assertEqual(surge.simulated_trauma_patients, 200)
        self.assertEqual(surge.admissions_completed_count, 200)
        self.assertEqual(surge.financial_billing_bypassed_count, 200)
        self.assertEqual(surge.duplicate_assignments, 0)
        self.assertEqual(surge.patient_death_due_to_system_delay, 0)

    def test_chaos_experiments_resilience(self):
        """Validates resilience against injected infrastructure chaos experiments."""
        # 1. Primary DB Failover
        db_chaos = self.engine.inject_chaos_experiment(ChaosExperimentType.DATABASE_PRIMARY_FAILOVER)
        self.assertTrue(db_chaos.passed_resilience_gate)
        self.assertLess(db_chaos.recovery_time_seconds, 3.0)
        self.assertEqual(db_chaos.transactions_lost, 0)

        # 2. WAN Network Drop
        wan_chaos = self.engine.inject_chaos_experiment(ChaosExperimentType.WAN_NETWORK_DROP)
        self.assertTrue(wan_chaos.passed_resilience_gate)
        self.assertEqual(wan_chaos.transactions_lost, 0)

        # 3. PACS Storage Saturation
        pacs_chaos = self.engine.inject_chaos_experiment(ChaosExperimentType.PACS_STORAGE_SATURATION)
        self.assertTrue(pacs_chaos.passed_resilience_gate)
        self.assertEqual(pacs_chaos.data_corruption_events, 0)


if __name__ == "__main__":
    unittest.main()
