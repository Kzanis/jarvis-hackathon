"""
Audit store — SQLite WAL avec chaîne de signatures HMAC.

Garanties :
- Append-only (pas de UPDATE/DELETE exposés)
- Chaque événement signé : HMAC(secret, previous_signature + canonical_payload)
- Détection de modification, suppression, réordonnancement
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.domain.types import AuditEvent


class SqliteAuditStore:
    """Implémente le Protocol AuditStore avec SQLite local."""

    def __init__(self, db_path: Path, hmac_secret: bytes):
        self.db_path = db_path
        self.hmac_secret = hmac_secret
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    sensitivity TEXT,
                    command_name TEXT,
                    payload_json TEXT NOT NULL,
                    previous_signature TEXT,
                    signature TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_events(ts DESC)")

    def _canonical_payload(self, event: AuditEvent) -> str:
        return json.dumps(
            {
                "ts": event.ts.isoformat(),
                "correlation_id": event.correlation_id,
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "mode": event.mode.value,
                "sensitivity": event.sensitivity.value if event.sensitivity else None,
                "command_name": event.command_name,
                "payload": event.payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _sign(self, previous_signature: str | None, canonical: str) -> str:
        msg = (previous_signature or "GENESIS").encode() + canonical.encode()
        return hmac.new(self.hmac_secret, msg, hashlib.sha256).hexdigest()

    def append(self, event: AuditEvent) -> str:
        canonical = self._canonical_payload(event)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT signature FROM audit_events ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            previous = row[0] if row else None
            signature = self._sign(previous, canonical)
            conn.execute(
                """
                INSERT INTO audit_events
                (ts, correlation_id, event_type, user_id, mode, sensitivity,
                 command_name, payload_json, previous_signature, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.ts.isoformat(),
                    event.correlation_id,
                    event.event_type.value,
                    event.user_id,
                    event.mode.value,
                    event.sensitivity.value if event.sensitivity else None,
                    event.command_name,
                    json.dumps(event.payload, ensure_ascii=False),
                    previous,
                    signature,
                ),
            )
        return signature

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def verify_chain(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_events ORDER BY id ASC"
            ).fetchall()
            previous = None
            for r in rows:
                payload = r["payload_json"]
                # Reconstitue le canonical
                canonical = json.dumps(
                    {
                        "ts": r["ts"],
                        "correlation_id": r["correlation_id"],
                        "event_type": r["event_type"],
                        "user_id": r["user_id"],
                        "mode": r["mode"],
                        "sensitivity": r["sensitivity"],
                        "command_name": r["command_name"],
                        "payload": json.loads(payload),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                expected = self._sign(previous, canonical)
                if expected != r["signature"]:
                    return False
                if r["previous_signature"] != previous:
                    return False
                previous = r["signature"]
        return True
