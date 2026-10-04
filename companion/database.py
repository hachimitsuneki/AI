from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import RuntimeConfig


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Database:
    def __init__(self, path: str):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        if str(self.path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = FULL")
        return conn

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self, config: RuntimeConfig) -> None:
        migrations = Path(__file__).resolve().parent.parent / "migrations"
        with self.session() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS SCHEMA_MIGRATION (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )"""
            )
            applied = {
                row["version"]
                for row in conn.execute("SELECT version FROM SCHEMA_MIGRATION").fetchall()
            }
        for migration in sorted(migrations.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            version = migration.name.split("_", 1)[0]
            if version in applied:
                continue
            # 0001 is idempotent and predates the migration ledger, so it also
            # safely recognizes existing installations without replacing data.
            with self.session() as conn:
                conn.executescript(migration.read_text(encoding="utf-8"))
            with self.transaction() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO SCHEMA_MIGRATION(version, applied_at) VALUES (?, ?)",
                    (version, now_iso()),
                )
        self.seed_defaults(config)
        self.recover_interrupted_turns()

    def seed_defaults(self, config: RuntimeConfig) -> None:
        timestamp = now_iso()
        with self.transaction() as conn:
            if conn.execute("SELECT 1 FROM AI_IDENTITY LIMIT 1").fetchone():
                return
            identity_id = new_id()
            user_id = new_id()
            conversation_id = new_id()
            identity = {
                "summary": "A curious, playful digital companion; clear, honest, and considerate."
            }
            temperament = {
                "curiosity": "somewhat high",
                "playfulness": "somewhat high",
                "assertiveness": "medium",
                "mischievousness": "slight",
                "humor": "occasional, situational",
            }
            conn.execute(
                """INSERT INTO AI_IDENTITY
                   (id, name, entity_type, role, core_identity, temperament, created_at, updated_at)
                   VALUES (?, ?, 'digital_companion', ?, ?, ?, ?, ?)""",
                (
                    identity_id,
                    config.identity_name,
                    config.identity_role,
                    json.dumps(identity, ensure_ascii=False),
                    json.dumps(temperament, ensure_ascii=False),
                    timestamp,
                    timestamp,
                ),
            )
            conn.execute(
                """INSERT INTO AI_STATE(id, ai_identity_id, curiosity, social_interest, engagement,
                   fatigue_like, updated_at) VALUES (?, ?, NULL, NULL, NULL, NULL, ?)""",
                (new_id(), identity_id, timestamp),
            )
            conn.execute(
                """INSERT INTO MOOD_STATE(id, ai_identity_id, valence, activation, control, last_updated_at)
                   VALUES (?, ?, NULL, NULL, NULL, ?)""",
                (new_id(), identity_id, timestamp),
            )
            conn.execute(
                """INSERT INTO USER_PROFILE(id, display_name, stable_attributes, created_at, updated_at)
                   VALUES (?, 'You', '{}', ?, ?)""",
                (user_id, timestamp, timestamp),
            )
            conn.execute(
                """INSERT INTO CONVERSATION(id, ai_identity_id, user_profile_id, started_at)
                   VALUES (?, ?, ?, ?)""",
                (conversation_id, identity_id, user_id, timestamp),
            )

    def recover_interrupted_turns(self) -> None:
        from .repositories import RuntimeRepository

        repo = RuntimeRepository(self)
        active_ids = repo.interrupted_turn_ids()
        for turn_id in active_ids:
            repo.recover_interrupted_turn(turn_id)
