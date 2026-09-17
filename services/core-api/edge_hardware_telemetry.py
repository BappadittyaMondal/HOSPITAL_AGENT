"""
====================================================================================================
PROJECT "HOSPITAL" — PHASE 17.2: EDGE HARDWARE & PERIPHERAL TELEMETRY MONITOR
====================================================================================================
Module: services/core-api/edge_hardware_telemetry.py
Purpose: Real-time telemetry surveillance for physical hospital hardware: 203 DPI thermal barcode
         printers, IP54 2D area-imaging scanners, 3-node Edge Cluster Raft consensus, disk capacity
         for 72h WAL logs, and laboratory analyzer ASTM/HL7 MLLP socket connectivity.
====================================================================================================
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional


class HardwareTelemetryException(Exception):
    """Base exception for hardware telemetry failures."""
    pass


class CriticalHardwareAlarm(HardwareTelemetryException):
    """Raised when physical hardware failure threatens clinical operations."""
    pass


class EdgeHardwareTelemetryEngine:
    """Surveillance engine for physical edge servers, barcode printers, and clinical scanners."""

    def __init__(self):
        self._printers: Dict[str, Dict] = {}
        self._scanners: Dict[str, Dict] = {}
        self._edge_nodes: Dict[str, Dict] = {}
        self._lab_analyzer_links: Dict[str, Dict] = {}
        self._alarms: List[Dict] = []

    # ----------------------------------------------------------------------------------------------
    # 1. 203 DPI THERMAL BARCODE PRINTER SURVEILLANCE
    # ----------------------------------------------------------------------------------------------

    def register_printer(
        self,
        printer_id: str,
        location: str,
        dpi: int = 203,
        model: str = "Zebra ZD421-HC"
    ) -> Dict:
        printer = {
            "printer_id": printer_id,
            "location": location,
            "dpi": dpi,
            "model": model,
            "status": "ONLINE",
            "paper_level_percent": 100.0,
            "head_temperature_c": 35.0,
            "cutter_status": "OK",
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
        self._printers[printer_id] = printer
        return printer

    def update_printer_telemetry(
        self,
        printer_id: str,
        paper_level_percent: float,
        head_temperature_c: float,
        cutter_jammed: bool = False,
        is_online: bool = True
    ) -> Dict:
        if printer_id not in self._printers:
            raise HardwareTelemetryException(f"Printer '{printer_id}' not registered.")

        p = self._printers[printer_id]
        p["paper_level_percent"] = paper_level_percent
        p["head_temperature_c"] = head_temperature_c
        p["cutter_status"] = "CUTTER_JAM" if cutter_jammed else "OK"
        p["status"] = "ONLINE" if is_online else "OFFLINE"
        p["last_heartbeat"] = datetime.now(timezone.utc).isoformat()

        # Hard Operational Gates: Alert when thermal printing is compromised
        if not is_online:
            self._raise_alarm("PRINTER_OFFLINE", f"Printer {printer_id} at {p['location']} is OFFLINE.")
        elif cutter_jammed:
            self._raise_alarm("PRINTER_CUTTER_JAM", f"Printer {printer_id} cutter is JAMMED.")
        elif paper_level_percent <= 5.0:
            self._raise_alarm("PRINTER_PAPER_EXHAUSTED", f"Printer {printer_id} paper critical ({paper_level_percent}%).")
        elif head_temperature_c >= 65.0:
            self._raise_alarm("PRINTER_HEAD_OVERHEAT", f"Printer {printer_id} thermal head overheating ({head_temperature_c}°C).")

        return p

    # ----------------------------------------------------------------------------------------------
    # 2. IP54 2D BARCODE SCANNER SURVEILLANCE
    # ----------------------------------------------------------------------------------------------

    def register_scanner(
        self,
        scanner_id: str,
        location: str,
        model: str = "Honeywell Xenon 1950h"
    ) -> Dict:
        scanner = {
            "scanner_id": scanner_id,
            "location": location,
            "model": model,
            "status": "ONLINE",
            "total_scans": 0,
            "decode_failures": 0,
            "error_rate_percent": 0.0,
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
        self._scanners[scanner_id] = scanner
        return scanner

    def record_scan_metrics(
        self,
        scanner_id: str,
        total_scans_in_batch: int,
        failed_decodes_in_batch: int
    ) -> Dict:
        if scanner_id not in self._scanners:
            raise HardwareTelemetryException(f"Scanner '{scanner_id}' not registered.")

        s = self._scanners[scanner_id]
        s["total_scans"] += total_scans_in_batch
        s["decode_failures"] += failed_decodes_in_batch
        if s["total_scans"] > 0:
            s["error_rate_percent"] = round((s["decode_failures"] / s["total_scans"]) * 100.0, 2)
        s["last_heartbeat"] = datetime.now(timezone.utc).isoformat()

        # Alert if decode failure rate exceeds 5.0%
        if s["error_rate_percent"] > 5.0 and s["total_scans"] >= 20:
            self._raise_alarm("SCANNER_DIRTY_LENS", f"Scanner {scanner_id} error rate {s['error_rate_percent']}% exceeds 5% SLA.")

        return s

    # ----------------------------------------------------------------------------------------------
    # 3. 3-NODE EDGE CLUSTER & RAFT HEALTH
    # ----------------------------------------------------------------------------------------------

    def register_edge_node(
        self,
        node_id: str,
        ip_address: str,
        raft_role: str = "FOLLOWER",
        free_disk_gb: float = 250.0
    ) -> Dict:
        node = {
            "node_id": node_id,
            "ip_address": ip_address,
            "raft_role": raft_role,
            "free_disk_gb": free_disk_gb,
            "status": "HEALTHY",
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
        self._edge_nodes[node_id] = node
        return node

    def update_edge_node_telemetry(
        self,
        node_id: str,
        free_disk_gb: float,
        raft_role: str,
        is_healthy: bool = True
    ) -> Dict:
        if node_id not in self._edge_nodes:
            raise HardwareTelemetryException(f"Edge Node '{node_id}' not registered.")

        node = self._edge_nodes[node_id]
        node["free_disk_gb"] = free_disk_gb
        node["raft_role"] = raft_role
        node["status"] = "HEALTHY" if is_healthy else "DEGRADED"
        node["last_heartbeat"] = datetime.now(timezone.utc).isoformat()

        # Hard Gate: 72-hour WAL requires minimum 20GB free space
        if free_disk_gb < 20.0:
            self._raise_alarm("EDGE_DISK_CAPACITY_LOW", f"Node {node_id} free disk {free_disk_gb}GB < 20GB safety limit.")

        return node

    def verify_edge_cluster_quorum(self) -> Dict:
        """Verifies 3-node edge cluster quorum (at least 2 of 3 healthy, with exactly 1 Leader)."""
        healthy_nodes = [n for n in self._edge_nodes.values() if n["status"] == "HEALTHY"]
        leaders = [n for n in healthy_nodes if n["raft_role"] == "LEADER"]

        has_quorum = len(healthy_nodes) >= 2 and len(leaders) == 1
        return {
            "cluster_healthy": has_quorum,
            "total_nodes": len(self._edge_nodes),
            "healthy_nodes": len(healthy_nodes),
            "active_leader": leaders[0]["node_id"] if leaders else None,
            "quorum_status": "QUORUM_OK" if has_quorum else "QUORUM_LOST"
        }

    # ----------------------------------------------------------------------------------------------
    # 4. LABORATORY ANALYZER ASTM / HL7 MLLP SOCKET MONITOR
    # ----------------------------------------------------------------------------------------------

    def register_analyzer_link(
        self,
        analyzer_id: str,
        analyzer_type: str, # "Sysmex XN-1000" or "Roche Cobas 6000"
        connection_type: str = "HL7_MLLP"
    ) -> Dict:
        link = {
            "analyzer_id": analyzer_id,
            "analyzer_type": analyzer_type,
            "connection_type": connection_type,
            "socket_state": "CONNECTED",
            "consecutive_ack_timeouts": 0,
            "last_sample_received": datetime.now(timezone.utc).isoformat()
        }
        self._lab_analyzer_links[analyzer_id] = link
        return link

    def update_analyzer_link_state(
        self,
        analyzer_id: str,
        socket_connected: bool,
        consecutive_ack_timeouts: int = 0
    ) -> Dict:
        if analyzer_id not in self._lab_analyzer_links:
            raise HardwareTelemetryException(f"Analyzer '{analyzer_id}' not registered.")

        link = self._lab_analyzer_links[analyzer_id]
        link["socket_state"] = "CONNECTED" if socket_connected else "DISCONNECTED"
        link["consecutive_ack_timeouts"] = consecutive_ack_timeouts

        if not socket_connected or consecutive_ack_timeouts >= 3:
            self._raise_alarm("ANALYZER_SOCKET_DISCONNECTED", f"Lab analyzer {analyzer_id} MLLP link severed.")

        return link

    # ----------------------------------------------------------------------------------------------
    # ALARM MANAGEMENT
    # ----------------------------------------------------------------------------------------------

    def _raise_alarm(self, alarm_type: str, message: str):
        alarm = {
            "alarm_type": alarm_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._alarms.append(alarm)

    def get_active_alarms(self) -> List[Dict]:
        return self._alarms
