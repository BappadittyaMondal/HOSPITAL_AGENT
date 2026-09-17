"""
====================================================================================================
TEST SUITE: PHASE 17.2 — EDGE HARDWARE & PERIPHERAL TELEMETRY MONITOR
====================================================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/core-api")))

from edge_hardware_telemetry import (
    EdgeHardwareTelemetryEngine,
    HardwareTelemetryException,
    CriticalHardwareAlarm
)


class TestEdgeHardwareTelemetry(unittest.TestCase):

    def setUp(self):
        self.telemetry = EdgeHardwareTelemetryEngine()

    def test_thermal_barcode_printer_monitoring(self):
        """Quality Gate 2: Printer cutter jam, low paper (<5%), and head overheat trigger alarms."""
        p = self.telemetry.register_printer("PRN-OPD-01", "OPD Registration Desk 1")
        self.assertEqual(p["status"], "ONLINE")

        # Update normal telemetry
        self.telemetry.update_printer_telemetry("PRN-OPD-01", paper_level_percent=80.0, head_temperature_c=38.0)
        self.assertEqual(len(self.telemetry.get_active_alarms()), 0)

        # Trigger paper low (4.0%)
        self.telemetry.update_printer_telemetry("PRN-OPD-01", paper_level_percent=4.0, head_temperature_c=40.0)
        alarms = self.telemetry.get_active_alarms()
        self.assertTrue(any(a["alarm_type"] == "PRINTER_PAPER_EXHAUSTED" for a in alarms))

        # Trigger cutter jam
        self.telemetry.update_printer_telemetry("PRN-OPD-01", paper_level_percent=50.0, head_temperature_c=40.0, cutter_jammed=True)
        alarms = self.telemetry.get_active_alarms()
        self.assertTrue(any(a["alarm_type"] == "PRINTER_CUTTER_JAM" for a in alarms))

    def test_scanner_decode_error_rate_alarm(self):
        """Quality Gate 2: Scanner decode error rate > 5.0% triggers dirty lens alarm."""
        self.telemetry.register_scanner("SCN-EMR-01", "Trauma Bay 1")

        # 30 scans with 3 decode failures = 10% error rate (> 5% threshold)
        s = self.telemetry.record_scan_metrics("SCN-EMR-01", total_scans_in_batch=30, failed_decodes_in_batch=3)
        self.assertEqual(s["error_rate_percent"], 10.0)

        alarms = self.telemetry.get_active_alarms()
        self.assertTrue(any(a["alarm_type"] == "SCANNER_DIRTY_LENS" for a in alarms))

    def test_edge_cluster_quorum_and_disk_capacity(self):
        """Quality Gate 2: 3-Node Raft cluster verifies quorum and warns on disk < 20GB."""
        self.telemetry.register_edge_node("NODE-A", "192.168.1.10", raft_role="LEADER", free_disk_gb=150.0)
        self.telemetry.register_edge_node("NODE-B", "192.168.1.11", raft_role="FOLLOWER", free_disk_gb=150.0)
        self.telemetry.register_edge_node("NODE-C", "192.168.1.12", raft_role="FOLLOWER", free_disk_gb=150.0)

        quorum = self.telemetry.verify_edge_cluster_quorum()
        self.assertTrue(quorum["cluster_healthy"])
        self.assertEqual(quorum["active_leader"], "NODE-A")

        # Node disk drops below 20GB for continuous WAL logs
        self.telemetry.update_edge_node_telemetry("NODE-A", free_disk_gb=14.5, raft_role="LEADER")
        alarms = self.telemetry.get_active_alarms()
        self.assertTrue(any(a["alarm_type"] == "EDGE_DISK_CAPACITY_LOW" for a in alarms))

    def test_analyzer_mllp_link_disconnection_alarm(self):
        """Verifies severed MLLP socket to Sysmex/Roche lab analyzers triggers critical alarm."""
        self.telemetry.register_analyzer_link("HEM-SYSMEX-01", "Sysmex XN-1000")
        self.telemetry.update_analyzer_link_state("HEM-SYSMEX-01", socket_connected=False)

        alarms = self.telemetry.get_active_alarms()
        self.assertTrue(any(a["alarm_type"] == "ANALYZER_SOCKET_DISCONNECTED" for a in alarms))


if __name__ == "__main__":
    unittest.main()
