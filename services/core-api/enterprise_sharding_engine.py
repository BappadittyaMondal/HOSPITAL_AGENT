# ====================================================================================================
# PROJECT "HOSPITAL" — ENTERPRISE MULTI-TENANT SHARDING & SCALABILITY ENGINE
# ====================================================================================================
# Module: services/core-api/enterprise_sharding_engine.py
# Purpose: Horizontal partitioning, consistent-hashing ring router, and dual-mode connection pool
#          manager scaling Project HOSPITAL from single-node edge WAL to 1,000,000+ patient clusters.
# ====================================================================================================

import hashlib
import bisect
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class ClusterOperatingMode(str, Enum):
    ENTERPRISE_DISTRIBUTED_CITUS = "ENTERPRISE_DISTRIBUTED_CITUS"
    EDGE_LOCAL_RESILIENT_WAL = "EDGE_LOCAL_RESILIENT_WAL"


@dataclass
class ShardNode:
    shard_id: str
    host: str
    port: int
    database_name: str
    is_primary: bool = True
    replica_hosts: List[str] = field(default_factory=list)
    healthy: bool = True


class ConsistentHashRing:
    """
    Consistent hashing ring with virtual nodes ensuring uniform distribution of
    patient partitions across physical database shards with minimal remapping.
    """

    def __init__(self, virtual_replicas: int = 100):
        self.virtual_replicas = virtual_replicas
        self._ring: List[int] = []
        self._hash_to_node: Dict[int, str] = {}
        self._nodes: Dict[str, ShardNode] = {}

    def _hash(self, key: str) -> int:
        return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)

    def add_node(self, node: ShardNode):
        self._nodes[node.shard_id] = node
        for i in range(self.virtual_replicas):
            v_key = f"{node.shard_id}#VN-{i}"
            h = self._hash(v_key)
            bisect.insort(self._ring, h)
            self._hash_to_node[h] = node.shard_id

    def remove_node(self, shard_id: str):
        if shard_id in self._nodes:
            del self._nodes[shard_id]
            new_ring = []
            for h in self._ring:
                if self._hash_to_node.get(h) == shard_id:
                    del self._hash_to_node[h]
                else:
                    new_ring.append(h)
            self._ring = new_ring

    def get_node(self, partition_key: str) -> Optional[ShardNode]:
        if not self._ring:
            return None
        h = self._hash(partition_key)
        idx = bisect.bisect_right(self._ring, h)
        if idx == len(self._ring):
            idx = 0
        shard_id = self._hash_to_node[self._ring[idx]]
        return self._nodes.get(shard_id)


class EnterpriseShardingRouter:
    """
    Routes clinical write and read transactions between distributed PostgreSQL Citus shards
    and local offline SQLite WAL caches.
    """

    def __init__(self, default_mode: ClusterOperatingMode = ClusterOperatingMode.EDGE_LOCAL_RESILIENT_WAL):
        self.operating_mode = default_mode
        self.ring = ConsistentHashRing(virtual_replicas=100)
        self._init_default_shards()

    def _init_default_shards(self):
        # Register 4 default enterprise shards
        for i in range(1, 5):
            self.ring.add_node(ShardNode(
                shard_id=f"SHARD-{i:02d}",
                host=f"citus-worker-{i:02d}.hospital.internal",
                port=5432,
                database_name=f"hospital_shard_{i:02d}",
                is_primary=True,
                replica_hosts=[f"citus-replica-{i:02d}.hospital.internal"]
            ))

    def resolve_patient_shard(self, tenant_id: str, mrn: str) -> Dict[str, Any]:
        """
        Determines the target database shard and routing endpoint for a given patient.
        """
        partition_key = f"{tenant_id}::{mrn}"
        node = self.ring.get_node(partition_key)

        if self.operating_mode == ClusterOperatingMode.ENTERPRISE_DISTRIBUTED_CITUS and node:
            return {
                "routing_mode": "DISTRIBUTED_CITUS",
                "shard_id": node.shard_id,
                "primary_host": node.host,
                "port": node.port,
                "database": node.database_name,
                "partition_key": partition_key,
                "connection_protocol": "postgresql+asyncpg"
            }
        else:
            return {
                "routing_mode": "EDGE_LOCAL_SQLITE_WAL",
                "shard_id": "EDGE_LOCAL_PRIMARY",
                "db_path": "hospital_outbox.db",
                "partition_key": partition_key,
                "connection_protocol": "sqlite3_wal"
            }

    def simulate_failover_to_edge(self):
        """Switches cluster routing mode to local edge WAL during network collapse."""
        self.operating_mode = ClusterOperatingMode.EDGE_LOCAL_RESILIENT_WAL

    def restore_enterprise_connectivity(self):
        """Restores distributed cluster routing upon network link recovery."""
        self.operating_mode = ClusterOperatingMode.ENTERPRISE_DISTRIBUTED_CITUS


enterprise_sharding_router = EnterpriseShardingRouter()
