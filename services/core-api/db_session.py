# ====================================================================================================
# PROJECT "HOSPITAL" — DATABASE SESSION & PERSISTENT TRANSACTIONAL OUTBOX MANAGER
# ====================================================================================================
# Module: services/core-api/db_session.py
# Purpose: Manages database connectivity and an ACID-compliant disk-backed Transactional Outbox
#          Pattern ensuring audit events, clinical orders, and state transitions survive service restarts.
# ====================================================================================================

import os
import json
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class DatabaseConfig:
    """PostgreSQL and local persistence configuration with environment overrides."""
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "hospital_main")
        self.user = os.getenv("POSTGRES_USER", "hospital_admin")
        self.password = os.getenv("POSTGRES_PASSWORD", "")
        self.ssl_mode = os.getenv("POSTGRES_SSLMODE", "prefer")
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.db_path = os.getenv("OUTBOX_DB_PATH", os.path.join(os.path.dirname(__file__), "hospital_outbox.db"))

    @property
    def connection_url(self) -> str:
        pwd_part = f":{self.password}" if self.password else ""
        return f"postgresql+asyncpg://{self.user}{pwd_part}@{self.host}:{self.port}/{self.database}"

    @property
    def is_configured(self) -> bool:
        return bool(self.password)


class TransactionalOutboxManager:
    """
    Persistent Transactional Outbox Pattern Manager.
    Provides ACID disk-backed durability using SQLite WAL mode for offline resilience
    and local persistence across process reboots.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("OUTBOX_DB_PATH", os.path.join(os.path.dirname(__file__), "hospital_outbox.db"))
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        """Initializes the persistent outbox table schema."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS outbox_events (
                        outbox_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        aggregate_type TEXT NOT NULL,
                        aggregate_id TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        actor_id TEXT NOT NULL,
                        correlation_id TEXT NOT NULL,
                        staged_at TEXT NOT NULL,
                        dispatched_at TEXT,
                        status TEXT NOT NULL,
                        retry_count INTEGER DEFAULT 0,
                        last_error TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox_events(status);")
        finally:
            conn.close()

    def stage_event(
        self,
        *args,
        tenant_id: str = "GLOBAL",
        event_type: str = "EVENT",
        aggregate_type: str = "AGGREGATE",
        aggregate_id: str = "DEFAULT",
        payload: Optional[Dict[str, Any]] = None,
        actor_id: str = "SYSTEM",
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Atomically persists an audit/domain event to disk alongside clinical aggregate mutations.
        Supports both positional and keyword calling conventions:
          - stage_event(tenant_id, event_type, aggregate_type, aggregate_id, payload, actor_id, [corr_id])
          - stage_event(aggregate_type, aggregate_id, event_type, payload)
        Returns outbox event_id.
        """
        if len(args) == 4:
            aggregate_type, aggregate_id, event_type, payload = args
        elif len(args) >= 6:
            tenant_id, event_type, aggregate_type, aggregate_id, payload, actor_id = args[:6]
            if len(args) > 6:
                correlation_id = args[6]

        event_id = str(uuid.uuid4())
        corr_id = correlation_id or str(uuid.uuid4())
        staged_time = datetime.now(timezone.utc).isoformat()
        status = "PENDING_DISPATCH"
        payload_json = json.dumps(payload or {}, default=str)

        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            with conn:
                conn.execute("""
                    INSERT INTO outbox_events (
                        outbox_id, tenant_id, event_type, aggregate_type, aggregate_id,
                        payload, actor_id, correlation_id, staged_at, status, retry_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
                """, (
                    event_id, tenant_id, event_type, aggregate_type, aggregate_id,
                    payload_json, actor_id, corr_id, staged_time, status
                ))
        finally:
            conn.close()

        return event_id

    def get_pending_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves pending undispatched events in staging order."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT outbox_id, tenant_id, event_type, aggregate_type, aggregate_id,
                       payload, actor_id, correlation_id, staged_at, retry_count, last_error, status
                FROM outbox_events
                WHERE status = 'PENDING_DISPATCH'
                ORDER BY staged_at ASC
                LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            events = []
            for r in rows:
                try:
                    p = json.loads(r[5])
                except Exception:
                    p = r[5]
                events.append({
                    "outbox_id": r[0],
                    "event_id": r[0],
                    "tenant_id": r[1],
                    "event_type": r[2],
                    "aggregate_type": r[3],
                    "aggregate_id": r[4],
                    "payload": p,
                    "actor_id": r[6],
                    "correlation_id": r[7],
                    "staged_at": r[8],
                    "retry_count": r[9] or 0,
                    "last_error": r[10],
                    "status": "PENDING"
                })
            return events
        finally:
            conn.close()

    def mark_dispatched(self, outbox_id: str):
        """Marks an outbox event as successfully sealed and dispatched."""
        dispatched_time = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            with conn:
                conn.execute("""
                    UPDATE outbox_events
                    SET status = 'SEALED_AND_DISPATCHED', dispatched_at = ?
                    WHERE outbox_id = ?;
                """, (dispatched_time, outbox_id))
        finally:
            conn.close()

    def record_dispatch_failure(self, outbox_id: str, error_message: str, max_retries: int = 5):
        """Records a dispatch failure, increments retry count, and dead-letters after threshold."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT retry_count FROM outbox_events WHERE outbox_id = ?;", (outbox_id,))
                row = cursor.fetchone()
                current_retries = (row[0] or 0) + 1 if row else 1
                new_status = "DEAD_LETTER" if current_retries >= max_retries else "PENDING_DISPATCH"
                cursor.execute("""
                    UPDATE outbox_events
                    SET retry_count = ?, last_error = ?, status = ?
                    WHERE outbox_id = ?;
                """, (current_retries, error_message, new_status, outbox_id))
        finally:
            conn.close()

    def dispatch_pending_events(self, max_batch_size: int = 100) -> List[Dict[str, Any]]:
        """Reads pending outbox events from disk and marks them dispatched."""
        dispatched_time = datetime.now(timezone.utc).isoformat()
        dispatched_events: List[Dict[str, Any]] = []

        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT outbox_id, tenant_id, event_type, aggregate_type, aggregate_id,
                           payload, actor_id, correlation_id, staged_at
                    FROM outbox_events
                    WHERE status = 'PENDING_DISPATCH'
                    ORDER BY staged_at ASC
                    LIMIT ?;
                """, (max_batch_size,))
                rows = cursor.fetchall()

                for row in rows:
                    oid = row[0]
                    conn.execute("""
                        UPDATE outbox_events
                        SET status = 'SEALED_AND_DISPATCHED', dispatched_at = ?
                        WHERE outbox_id = ?;
                    """, (dispatched_time, oid))

                    try:
                        loaded_payload = json.loads(row[5])
                    except Exception:
                        loaded_payload = row[5]

                    dispatched_events.append({
                        "outbox_id": row[0],
                        "tenant_id": row[1],
                        "event_type": row[2],
                        "aggregate_type": row[3],
                        "aggregate_id": row[4],
                        "payload": loaded_payload,
                        "actor_id": row[6],
                        "correlation_id": row[7],
                        "staged_at": row[8],
                        "dispatched_at": dispatched_time,
                        "status": "SEALED_AND_DISPATCHED"
                    })
        finally:
            conn.close()

        return dispatched_events

    @property
    def pending_count(self) -> int:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM outbox_events WHERE status = 'PENDING_DISPATCH';")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    @property
    def processed_count(self) -> int:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM outbox_events WHERE status = 'SEALED_AND_DISPATCHED';")
            return cursor.fetchone()[0]
        finally:
            conn.close()


# Global singleton instance for local and in-process execution
TransactionalOutbox = TransactionalOutboxManager
OutboxManager = TransactionalOutboxManager
outbox_manager = TransactionalOutboxManager()
db_config = DatabaseConfig()
