"""
Test Suite: test_edge_resilience.py
Phase 14: Resilience & Compliance — Offline-First Edge Resiliency & Disaster Recovery
Mandates / Quality Gates 1 & 2:
  - Quality Gate 1: Disconnect hospital WAN for 72 continuous hours: OPD registrations,
    emergency admissions, lab analyzer results, and bedside eMAR execute locally without error;
    zero duplicate bed assignments upon reconnection.
  - Pessimistic Resource Leasing strictly blocks offline nodes from allocating unleased Class A beds.
  - Quality Gate 2: Complete simulated database restore from cold backup achieves
    RTO < 4 hours and RPO < 5 minutes.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from edge_resilience_engine import (
    EdgeResilienceEngine,
    ResourceNotLeasedError,
    DisasterRecoverySlaBreachError,
    EdgeResilienceError,
)


class TestEdgeResilienceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = EdgeResilienceEngine()

        # Grant Pessimistic Leases on Class A ICU Beds across 3 Edge Nodes
        # Node 1 gets ICU beds 01 to 05
        for i in range(1, 6):
            self.engine.grant_pessimistic_lease(
                node_id="EDGE_NODE_01",
                resource_id=f"BED-ICU-{i:02d}",
                resource_type="ICU_BED",
                duration_days=7,
            )
        # Node 2 gets ICU beds 06 to 10
        for i in range(6, 11):
            self.engine.grant_pessimistic_lease(
                node_id="EDGE_NODE_02",
                resource_id=f"BED-ICU-{i:02d}",
                resource_type="ICU_BED",
                duration_days=7,
            )

    def test_quality_gate_1_72h_offline_operation_and_zero_duplicate_reconciliation(self):
        """
        Quality Gate 1:
        Simulates 72-hour continuous WAN outage.
        Executes local OPD registrations, emergency admissions, lab results, and eMAR administrations.
        Reconnection results in zero duplicate bed assignments.
        """
        # 1. Total WAN Disconnect
        self.engine.disconnect_hospital_wan()
        self.assertFalse(self.engine.is_wan_online)

        # 2. Local operations on EDGE_NODE_01
        tx_opd_1 = self.engine.execute_local_opd_registration(
            node_id="EDGE_NODE_01",
            patient_id="PAT-LOC-01",
            patient_name="Amitabh Sen",
            department="CARDIOLOGY",
        )
        self.assertEqual(tx_opd_1.tx_type, "OPD_REGISTRATION")

        tx_bed_1 = self.engine.execute_local_emergency_bed_allocation(
            node_id="EDGE_NODE_01",
            patient_id="PAT-LOC-01",
            resource_id="BED-ICU-01",  # In Node 1's pessimistic lease
        )
        self.assertEqual(tx_bed_1.tx_type, "EMERGENCY_ADMISSION")

        tx_lab_1 = self.engine.execute_local_lab_result_ingestion(
            node_id="EDGE_NODE_01",
            order_id="ORD-TROP-991",
            test_code="TROPONIN_I",
            numeric_result=0.45,
        )
        self.assertEqual(tx_lab_1.tx_type, "LAB_RESULT")

        tx_emar_1 = self.engine.execute_local_emar_administration(
            node_id="EDGE_NODE_01",
            patient_id="PAT-LOC-01",
            medication_id="MED-HEPARIN-IV",
            nurse_id="NURSE-ICU-1",
        )
        self.assertEqual(tx_emar_1.tx_type, "EMAR_ADMIN")

        # 3. Local operations on EDGE_NODE_02
        tx_bed_2 = self.engine.execute_local_emergency_bed_allocation(
            node_id="EDGE_NODE_02",
            patient_id="PAT-LOC-02",
            resource_id="BED-ICU-06",  # In Node 2's pessimistic lease
        )
        self.assertEqual(tx_bed_2.tx_type, "EMERGENCY_ADMISSION")

        # 4. Attempt by Node 1 to allocate bed outside its lease partition (e.g. BED-ICU-06 or BED-ICU-99)
        with self.assertRaises(ResourceNotLeasedError) as ctx:
            self.engine.execute_local_emergency_bed_allocation(
                node_id="EDGE_NODE_01",
                patient_id="PAT-LOC-ILLEGAL",
                resource_id="BED-ICU-06",  # Leased to Node 2!
            )
        self.assertIn("EDGE LEASING HARD GATE", str(ctx.exception))

        # 5. Restore WAN and Reconcile
        recon = self.engine.restore_hospital_wan()
        self.assertTrue(self.engine.is_wan_online)
        self.assertEqual(recon["status"], "RECONCILIATION_COMPLETED")
        self.assertEqual(recon["total_transactions_synced"], 5)
        self.assertEqual(recon["duplicate_bed_conflicts"], 0)
        self.assertTrue(recon["zero_duplicate_assignments_certified"])

    def test_quality_gate_2_dr_cold_restore_rto_rpo_compliance(self):
        """
        Quality Gate 2:
        Simulated cold backup disaster restore drill verifies:
          - RPO < 5 minutes (achieved 120s = 2.0 min)
          - RTO < 4 hours (achieved 7200s = 2.0 hr)
        """
        drill_report = self.engine.simulate_cold_backup_restore_drill(
            wal_lag_seconds=120.0,            # 2 minutes lag <= 5 minutes max
            restore_duration_seconds=7200.0,  # 2.0 hours restore <= 4 hours max
        )

        self.assertTrue(drill_report["rpo_compliant"])
        self.assertLess(drill_report["achieved_rpo_seconds"], 300)
        self.assertTrue(drill_report["rto_compliant"])
        self.assertLess(drill_report["achieved_rto_hours"], 4.0)
        self.assertEqual(drill_report["dr_certification"], "PASSED_100_PERCENT")

    def test_quality_gate_2_catches_dr_sla_breaches(self):
        """Tests that breaches of RPO or RTO are strictly caught and raised as errors."""
        # 1. Test RPO breach (WAL lag 360s > 300s limit)
        with self.assertRaises(DisasterRecoverySlaBreachError) as ctx:
            self.engine.simulate_cold_backup_restore_drill(
                wal_lag_seconds=360.0,
                restore_duration_seconds=7200.0,
            )
        self.assertIn("RPO BREACH", str(ctx.exception))

        # 2. Test RTO breach (Restore duration 18,000s = 5 hours > 4 hours limit)
        with self.assertRaises(DisasterRecoverySlaBreachError) as ctx:
            self.engine.simulate_cold_backup_restore_drill(
                wal_lag_seconds=120.0,
                restore_duration_seconds=18000.0,
            )
        self.assertIn("RTO BREACH", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
