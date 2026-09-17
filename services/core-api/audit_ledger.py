# ====================================================================================================
# PROJECT "HOSPITAL" — UNIVERSAL CRYPTOGRAPHIC AUDIT HASH LEDGER
# ====================================================================================================
# Module: services/core-api/audit_ledger.py
# Purpose: Provides an immutable, append-only SHA-256 cryptographic hash-chained audit ledger
#          across all clinical, operational, and administrative mutations, with tamper-detection verification.
# ====================================================================================================

import os
import json
import uuid
import hmac
import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple


GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


class UniversalAuditLedger:
    """
    Cryptographic Append-Only Audit Ledger.
    Every event is chained to the preceding entry using HMAC-SHA256 hash chaining:
    H_n = HMAC-SHA256(Key, H_{n-1} || timestamp || tenant_id || event_type || aggregate_id || actor_id || payload_hash)
    """

    def __init__(self, db_path: Optional[str] = None, hmac_key: Optional[str] = None):
        self._lock = threading.Lock()
        self.db_path = db_path or os.getenv("AUDIT_DB_PATH", os.path.join(os.path.dirname(__file__), "hospital_audit.db"))
        env_mode = os.getenv("HOSPITAL_ENV", "development").lower()
        key = hmac_key or os.getenv("AUDIT_LEDGER_HMAC_KEY")
        if not key:
            if env_mode in ("production", "prod"):
                raise RuntimeError("FATAL SECURITY EXCEPTION: AUDIT_LEDGER_HMAC_KEY environment variable is required in production mode.")
            key = os.getenv("AUDIT_LEDGER_DEV_SECRET", "HOSPITAL_AUDIT_LEDGER_DEFAULT_HMAC_KEY_2026")
        self._hmac_key = key.encode("utf-8") if isinstance(key, str) else key
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_chain (
                        entry_index INTEGER PRIMARY KEY AUTOINCREMENT,
                        entry_id TEXT NOT NULL UNIQUE,
                        timestamp TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        aggregate_id TEXT NOT NULL,
                        actor_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        payload_hash TEXT NOT NULL,
                        prev_hash TEXT NOT NULL,
                        current_hash TEXT NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_chain(tenant_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_chain(event_type);")
        finally:
            conn.close()

    def _compute_hash(self, prev_hash: str, timestamp: str, tenant_id: str, event_type: str, aggregate_id: str, actor_id: str, payload_hash: str) -> str:
        chain_input = f"{prev_hash}|{timestamp}|{tenant_id}|{event_type}|{aggregate_id}|{actor_id}|{payload_hash}"
        return hmac.new(self._hmac_key, chain_input.encode("utf-8"), hashlib.sha256).hexdigest()

    def record_event(
        self,
        tenant_id: str,
        event_type: str,
        aggregate_id: str,
        actor_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Atomically computes the next cryptographic hash and appends the record to the ledger."""
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        with self._lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
            try:
                cursor = conn.cursor()
                cursor.execute("BEGIN EXCLUSIVE;")
                cursor.execute("SELECT current_hash FROM audit_chain ORDER BY entry_index DESC LIMIT 1;")
                last_row = cursor.fetchone()
                prev_hash = last_row[0] if last_row else GENESIS_HASH

                current_hash = self._compute_hash(prev_hash, timestamp, tenant_id, event_type, aggregate_id, actor_id, payload_hash)

                cursor.execute("""
                    INSERT INTO audit_chain (
                        entry_id, timestamp, tenant_id, event_type, aggregate_id,
                        actor_id, payload_json, payload_hash, prev_hash, current_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    entry_id, timestamp, tenant_id, event_type, aggregate_id,
                    actor_id, payload_str, payload_hash, prev_hash, current_hash
                ))
                idx = cursor.lastrowid
                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

        return {
            "entry_index": idx,
            "entry_id": entry_id,
            "timestamp": timestamp,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "actor_id": actor_id,
            "prev_hash": prev_hash,
            "current_hash": current_hash
        }

    def verify_chain_integrity(self) -> Tuple[bool, Optional[int], str]:
        """
        Traverses the entire cryptographic ledger to mathematically verify tamper-evident invariants.
        Returns: (is_valid: bool, compromised_index: Optional[int], message: str)
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT entry_index, timestamp, tenant_id, event_type, aggregate_id,
                       actor_id, payload_json, payload_hash, prev_hash, current_hash
                FROM audit_chain
                ORDER BY entry_index ASC;
            """)
            rows = cursor.fetchall()

            if not rows:
                return True, None, "Ledger is empty. Verification passed (Genesis state)."

            expected_prev = GENESIS_HASH
            for row in rows:
                idx, ts, tid, etype, agg_id, actor, pjson, phash, prev_h, cur_h = row

                # 1. Verify previous hash pointer
                if prev_h != expected_prev:
                    return False, idx, f"Chain linkage broken at index {idx}: expected prev_hash {expected_prev}, got {prev_h}"

                # 2. Verify payload hash integrity
                computed_phash = hashlib.sha256(pjson.encode("utf-8")).hexdigest()
                if computed_phash != phash:
                    return False, idx, f"Payload tampering detected at index {idx}: payload hash mismatch"

                # 3. Verify current node hash
                computed_cur_h = self._compute_hash(prev_h, ts, tid, etype, agg_id, actor, phash)
                if computed_cur_h != cur_h:
                    return False, idx, f"Cryptographic signature mismatch at index {idx}: computed {computed_cur_h}, recorded {cur_h}"

                expected_prev = cur_h

            return True, None, f"All {len(rows)} ledger entries verified with 100% cryptographic integrity."
        finally:
            conn.close()

    @property
    def total_entries(self) -> int:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM audit_chain;")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_ledger_length(self) -> int:
        """Returns the total number of committed ledger entries."""
        return self.total_entries

    def get_recent_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent audit entries in ascending order."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT entry_index, entry_id, timestamp, tenant_id, event_type, aggregate_id, actor_id, prev_hash, current_hash
                FROM audit_chain
                ORDER BY entry_index DESC
                LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "entry_index": r[0],
                    "entry_id": r[1],
                    "timestamp": r[2],
                    "tenant_id": r[3],
                    "event_type": r[4],
                    "aggregate_id": r[5],
                    "actor_id": r[6],
                    "prev_hash": r[7],
                    "current_hash": r[8]
                }
                for r in reversed(rows)
            ]
        finally:
            conn.close()


# Global singleton instance for core API service
audit_ledger = UniversalAuditLedger()
AuditLedger = UniversalAuditLedger

