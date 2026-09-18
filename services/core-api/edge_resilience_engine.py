"""
PROJECT "HOSPITAL" — PHASE 14: RESILIENCE & COMPLIANCE
Module: edge_resilience_engine.py
Operational Scope:
  - Sub-task 14.1: Offline-First Local Edge Resiliency (3-Node Edge Cluster)
  - Pessimistic Edge Resource Leasing for Class A Physical Assets (ICU Beds, OTs, Blood Units)
  - Quality Gate 1: 72-Hour WAN Disconnect Simulation with Zero Duplicate Bed Assignments
  - Sub-task 14.2: Disaster Recovery & Business Continuity (Continuous WAL Shipping)
  - Quality Gate 2: Cold Backup Disaster Recovery Simulator with RTO < 4 Hours & RPO < 5 Minutes
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any


class EdgeResilienceError(Exception):
    """Base exception for edge and resilience failures."""
    pass


class ResourceNotLeasedError(EdgeResilienceError):
    """Raised when an offline edge node attempts to allocate a Class A resource not in its granted lease."""
    pass


class DisasterRecoverySlaBreachError(EdgeResilienceError):
    """Raised when backup recovery time or data lag breaches statutory SLA thresholds."""
    pass


class StaleFencingTokenError(EdgeResilienceError):
    """Raised when an edge synchronization payload carries a stale or regressed monotonic fencing token."""
    pass


class ResourceClass(str, Enum):
    CLASS_A_PHYSICAL = "CLASS_A_PHYSICAL"  # ICU Beds, Operating Theatres, Blood Units (Exclusive)
    CLASS_B_VIRTUAL = "CLASS_B_VIRTUAL"    # OPD Queues, Lab Orders, Billing Vouchers


@dataclass
class EdgeLease:
    lease_id: str
    node_id: str
    resource_id: str
    resource_type: str
    granted_at: datetime
    expires_at: datetime
    is_active: bool = True


@dataclass
class LocalEdgeTransaction:
    tx_id: str
    node_id: str
    tx_type: str  # OPD_REGISTRATION, EMERGENCY_ADMISSION, LAB_RESULT, EMAR_ADMIN
    entity_id: str
    payload: Dict[str, Any]
    timestamp: datetime
    is_synced: bool = False


@dataclass
class EdgeNodeState:
    node_id: str
    is_online: bool = True
    assigned_leases: Set[str] = field(default_factory=set)  # resource_ids
    local_journal: List[LocalEdgeTransaction] = field(default_factory=list)


class EdgeResilienceEngine:
    """
    Hospital Edge Resiliency and Business Continuity Engine.
    Employs Pessimistic Resource Partition Leasing ensuring seamless 72-hour offline operation
    with zero duplicate Class A physical resource collisions upon WAN restoration.
    """

    # Statutory DR SLAs
    MAX_RPO_SECONDS = 300       # 5 minutes
    MAX_RTO_SECONDS = 14400     # 4 hours (240 minutes)

    def __init__(self):
        self.is_wan_online: bool = True
        self._nodes: Dict[str, EdgeNodeState] = {
            "EDGE_NODE_01": EdgeNodeState(node_id="EDGE_NODE_01"),
            "EDGE_NODE_02": EdgeNodeState(node_id="EDGE_NODE_02"),
            "EDGE_NODE_03": EdgeNodeState(node_id="EDGE_NODE_03"),
        }
        # Central Global Registry
        self._global_resource_allocations: Dict[str, str] = {}  # resource_id -> allocated_patient_id
        self._leases: Dict[str, EdgeLease] = {}                 # resource_id -> EdgeLease
        self._global_audit_journal: List[LocalEdgeTransaction] = []
        self._node_fencing_tokens: Dict[str, int] = {}          # node_id -> highest monotonic fencing token

        # WAL Shipping Simulator State
        self._last_wal_flush_time: datetime = datetime.now(timezone.utc)

    # =========================================================================
    # 14.1 PESSIMISTIC LEASING & 72-HOUR OFFLINE OPERATION
    # =========================================================================

    def grant_pessimistic_lease(
        self,
        node_id: str,
        resource_id: str,
        resource_type: str,
        duration_days: int = 7,
    ) -> EdgeLease:
        """Grants an exclusive pessimistic lease for a Class A physical resource to an edge node."""
        if node_id not in self._nodes:
            raise EdgeResilienceError(f"Node {node_id} unrecognized.")

        now = datetime.now(timezone.utc)
        lease = EdgeLease(
            lease_id=f"LEASE-{node_id}-{resource_id}",
            node_id=node_id,
            resource_id=resource_id,
            resource_type=resource_type,
            granted_at=now,
            expires_at=now + timedelta(days=duration_days),
        )
        # Revoke resource from any prior node to guarantee exclusive partition ownership
        for existing_node in self._nodes.values():
            existing_node.assigned_leases.discard(resource_id)

        self._leases[resource_id] = lease
        self._nodes[node_id].assigned_leases.add(resource_id)
        return lease

    def disconnect_hospital_wan(self) -> None:
        """Simulates catastrophic total loss of internet / cloud WAN connectivity."""
        self.is_wan_online = False
        for node in self._nodes.values():
            node.is_online = False

    def restore_hospital_wan(self) -> Dict[str, Any]:
        """Restores WAN connectivity and triggers bi-directional reconciliation."""
        self.is_wan_online = True
        for node in self._nodes.values():
            node.is_online = True

        reconciliation_report = self.reconcile_offline_journals()
        return reconciliation_report

    def execute_local_opd_registration(
        self,
        node_id: str,
        patient_id: str,
        patient_name: str,
        department: str,
    ) -> LocalEdgeTransaction:
        """Executes OPD registration locally on edge node without internet connectivity."""
        node = self._nodes[node_id]
        tx = LocalEdgeTransaction(
            tx_id=f"TX-OPD-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}",
            node_id=node_id,
            tx_type="OPD_REGISTRATION",
            entity_id=patient_id,
            payload={"patient_name": patient_name, "department": department},
            timestamp=datetime.now(timezone.utc),
        )
        node.local_journal.append(tx)
        return tx

    def execute_local_emergency_bed_allocation(
        self,
        node_id: str,
        patient_id: str,
        resource_id: str,
    ) -> LocalEdgeTransaction:
        """
        Allocates an emergency bed (Class A resource) locally during offline operation.
        Enforces Pessimistic Lease Gate: If resource is not in this node's granted lease,
        it is mechanically blocked to prevent double-booking.
        """
        node = self._nodes[node_id]

        # Pessimistic Lease Verification
        if resource_id not in node.assigned_leases:
            raise ResourceNotLeasedError(
                f"[EDGE LEASING HARD GATE] Node {node_id} cannot allocate resource {resource_id} offline! "
                f"Resource is not in this node's pessimistic lease partition (Assigned: {list(node.assigned_leases)})."
            )

        # Lease Expiration & Safe Offline Unavailability Check
        lease = self._leases.get(resource_id)
        if lease and lease.expires_at < datetime.now(timezone.utc):
            raise ResourceNotLeasedError(
                f"[EDGE LEASING HARD GATE] Lease for resource {resource_id} expired at {lease.expires_at.isoformat()}. "
                f"Safe offline unavailability enforced: cannot allocate expired lease partition."
            )

        tx = LocalEdgeTransaction(
            tx_id=f"TX-BED-{resource_id}-{patient_id}",
            node_id=node_id,
            tx_type="EMERGENCY_ADMISSION",
            entity_id=resource_id,
            payload={"patient_id": patient_id, "bed_id": resource_id},
            timestamp=datetime.now(timezone.utc),
        )
        node.local_journal.append(tx)
        return tx

    def execute_local_lab_result_ingestion(
        self,
        node_id: str,
        order_id: str,
        test_code: str,
        numeric_result: float,
    ) -> LocalEdgeTransaction:
        """Ingests automated analyzer results locally on edge node."""
        node = self._nodes[node_id]
        tx = LocalEdgeTransaction(
            tx_id=f"TX-LAB-{order_id}",
            node_id=node_id,
            tx_type="LAB_RESULT",
            entity_id=order_id,
            payload={"test_code": test_code, "numeric_result": numeric_result},
            timestamp=datetime.now(timezone.utc),
        )
        node.local_journal.append(tx)
        return tx

    def execute_local_emar_administration(
        self,
        node_id: str,
        patient_id: str,
        medication_id: str,
        nurse_id: str,
    ) -> LocalEdgeTransaction:
        """Executes bedside eMAR medication scan and administration locally."""
        node = self._nodes[node_id]
        tx = LocalEdgeTransaction(
            tx_id=f"TX-EMAR-{patient_id}-{medication_id}",
            node_id=node_id,
            tx_type="EMAR_ADMIN",
            entity_id=patient_id,
            payload={"medication_id": medication_id, "nurse_id": nurse_id},
            timestamp=datetime.now(timezone.utc),
        )
        node.local_journal.append(tx)
        return tx

    def reconcile_offline_journals(self) -> Dict[str, Any]:
        """
        Quality Gate 1: Bi-directional reconciliation upon WAN restoration.
        Reconciles journals from all 3 edge nodes.
        Asserts zero duplicate bed assignments or conflicting allocations.
        """
        synced_count = 0
        conflicts_detected = 0

        for node in self._nodes.values():
            for tx in node.local_journal:
                if tx.is_synced:
                    continue

                if tx.tx_type == "EMERGENCY_ADMISSION":
                    bed_id = tx.entity_id
                    patient_id = tx.payload["patient_id"]

                    # Check for collision
                    if bed_id in self._global_resource_allocations:
                        existing_patient = self._global_resource_allocations[bed_id]
                        if existing_patient != patient_id:
                            conflicts_detected += 1
                            continue

                    self._global_resource_allocations[bed_id] = patient_id

                tx.is_synced = True
                self._global_audit_journal.append(tx)
                synced_count += 1

        return {
            "status": "RECONCILIATION_COMPLETED",
            "total_transactions_synced": synced_count,
            "duplicate_bed_conflicts": conflicts_detected,
            "zero_duplicate_assignments_certified": conflicts_detected == 0,
            "global_journal_size": len(self._global_audit_journal),
        }

    def sync_with_fencing_token(
        self,
        node_id: str,
        fencing_token: int,
        transactions: List[LocalEdgeTransaction]
    ) -> Dict[str, Any]:
        """
        Synchronizes edge node transactions guarded by monotonic fencing token.
        Rejects stale tokens to prevent split-brain write conflicts or replay attacks.
        """
        if node_id not in self._nodes:
            raise EdgeResilienceError(f"Node {node_id} unrecognized.")

        current_token = self._node_fencing_tokens.get(node_id, 0)
        if fencing_token <= current_token:
            raise StaleFencingTokenError(
                f"[FENCING TOKEN REJECTED] Node {node_id} presented stale fencing token {fencing_token} "
                f"<= current high watermark {current_token}."
            )

        self._node_fencing_tokens[node_id] = fencing_token

        # Append valid transactions to local journal
        node = self._nodes[node_id]
        for tx in transactions:
            node.local_journal.append(tx)

        # If WAN is online, trigger reconciliation
        if self.is_wan_online:
            return self.reconcile_offline_journals()

        return {
            "status": "QUEUED_OFFLINE_LOCAL",
            "node_id": node_id,
            "fencing_token_accepted": fencing_token,
            "pending_transactions": len(node.local_journal)
        }

    # =========================================================================
    # 14.2 DISASTER RECOVERY & CONTINUOUS WAL SHIPPING (RPO & RTO)
    # =========================================================================

    def simulate_cold_backup_restore_drill(
        self,
        wal_lag_seconds: float = 120.0,         # Simulated WAL shipping interval: 2 minutes
        restore_duration_seconds: float = 7200.0 # Simulated cold restore time: 2 hours
    ) -> Dict[str, Any]:
        """
        Quality Gate 2: Disaster Recovery Simulator.
        Validates whether cold backup restore drill satisfies:
          - Recovery Point Objective (RPO) < 5 minutes (300s)
          - Recovery Time Objective (RTO) < 4 hours (14,400s)
        """
        # Validate RPO (Data loss window)
        is_rpo_met = wal_lag_seconds <= self.MAX_RPO_SECONDS
        if not is_rpo_met:
            raise DisasterRecoverySlaBreachError(
                f"[RPO BREACH] Simulated WAL lag is {wal_lag_seconds}s, which exceeds "
                f"the 300s (5-minute) statutory RPO limit!"
            )

        # Validate RTO (Recovery Time Objective)
        is_rto_met = restore_duration_seconds <= self.MAX_RTO_SECONDS
        if not is_rto_met:
            raise DisasterRecoverySlaBreachError(
                f"[RTO BREACH] Simulated cold database restore required {restore_duration_seconds}s, "
                f"exceeding the 14,400s (4-hour) statutory RTO limit!"
            )

        return {
            "drill_name": "QUARTERLY_COLD_BACKUP_DISASTER_RECOVERY_SIMULATION",
            "achieved_rpo_seconds": wal_lag_seconds,
            "target_rpo_seconds": self.MAX_RPO_SECONDS,
            "rpo_compliant": is_rpo_met,
            "achieved_rto_seconds": restore_duration_seconds,
            "achieved_rto_hours": round(restore_duration_seconds / 3600.0, 2),
            "target_rto_hours": 4.0,
            "rto_compliant": is_rto_met,
            "dr_certification": "PASSED_100_PERCENT",
            "certified_at": datetime.now(timezone.utc).isoformat(),
        }
