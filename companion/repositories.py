from __future__ import annotations

import json
import re
import sqlite3
import time
from collections.abc import Iterable
from typing import Any

from .database import Database, new_id, now_iso


ACTIVE_STATUSES = ("preparing", "generating", "streaming")
TERMINAL_STATUSES = ("completed", "completed_partial", "failed_before_delivery", "cancelled")


class RuntimeRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def emit_event(
        conn: sqlite3.Connection,
        turn_id: str,
        event_type: str,
        source: str,
        truth_state: str,
        persistence_class: str,
        payload: dict[str, Any] | None = None,
        causation_event_id: str | None = None,
    ) -> str:
        if causation_event_id is None:
            previous = conn.execute(
                "SELECT id FROM TURN_EVENT_TRACE WHERE turn_run_id = ? ORDER BY sequence DESC LIMIT 1",
                (turn_id,),
            ).fetchone()
            causation_event_id = previous["id"] if previous else None
        sequence = conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 AS next FROM TURN_EVENT_TRACE WHERE turn_run_id = ?",
            (turn_id,),
        ).fetchone()["next"]
        event_id = new_id()
        conn.execute(
            """INSERT INTO TURN_EVENT_TRACE
               (id, turn_run_id, sequence, event_type, source, truth_state,
                persistence_class, causation_event_id, observed_at_mono_ns, emitted_at_wall, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                turn_id,
                sequence,
                event_type,
                source,
                truth_state,
                persistence_class,
                causation_event_id,
                time.monotonic_ns(),
                now_iso(),
                json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        return event_id

    def default_scope(self) -> dict[str, str]:
        with self.db.session() as conn:
            row = conn.execute(
                """SELECT c.id AS conversation_id, c.ai_identity_id, c.user_profile_id,
                          ai.name, ai.role, ai.core_identity, ai.temperament,
                          ast.curiosity, ast.social_interest, ast.engagement, ast.fatigue_like,
                          mood.valence, mood.activation, mood.control
                   FROM CONVERSATION c
                   JOIN AI_IDENTITY ai ON ai.id = c.ai_identity_id
                   JOIN AI_STATE ast ON ast.ai_identity_id = ai.id
                   JOIN MOOD_STATE mood ON mood.ai_identity_id = ai.id
                   ORDER BY c.started_at DESC LIMIT 1"""
            ).fetchone()
            if not row:
                raise RuntimeError("local identity and conversation have not been initialized")
            return dict(row)

    def learned_context(self, ai_identity_id: str, user_profile_id: str) -> dict[str, list[dict[str, Any]]]:
        with self.db.session() as conn:
            self_rows = conn.execute(
                """SELECT id, category, subject, value, confidence, status
                   FROM SELF_MODEL_ITEM WHERE ai_identity_id = ?
                     AND status IN ('active', 'current', 'confirmed')
                   ORDER BY confidence DESC, valid_from DESC""",
                (ai_identity_id,),
            ).fetchall()
            self_hypotheses = conn.execute(
                """SELECT id, category, subject, statement AS value, confidence, status
                   FROM SELF_HYPOTHESIS WHERE ai_identity_id = ? AND status IN ('active', 'hypothesis')
                   ORDER BY confidence DESC, created_at DESC""",
                (ai_identity_id,),
            ).fetchall()
            user_rows = conn.execute(
                """SELECT id, category, subject, value, confidence, temporal_scope, status
                   FROM USER_MODEL_ITEM WHERE user_profile_id = ?
                     AND status IN ('active', 'current', 'confirmed')
                   ORDER BY confidence DESC, updated_at DESC""",
                (user_profile_id,),
            ).fetchall()
            user_hypotheses = conn.execute(
                """SELECT id, category, subject, statement AS value, confidence, status
                   FROM USER_HYPOTHESIS WHERE user_profile_id = ?
                     AND status IN ('active', 'hypothesis')
                   ORDER BY confidence DESC, created_at DESC""",
                (user_profile_id,),
            ).fetchall()
            relationship_rows = conn.execute(
                """SELECT rd.id, rd.dimension_type, rd.value, rd.confidence, rd.stability
                   FROM RELATIONSHIP r JOIN RELATIONSHIP_DIMENSION rd ON rd.relationship_id = r.id
                   WHERE r.ai_identity_id = ? AND r.user_profile_id = ?
                   ORDER BY rd.dimension_type LIMIT 8""",
                (ai_identity_id, user_profile_id),
            ).fetchall()
            self_items = [dict(row) for row in self_rows]
            self_items = [item for item in self_items if self._derived_item_visible(conn, "self_model", item["id"])]
            known_self_ids = {row["id"] for row in self_items}
            self_items.extend(
                {**dict(row), "status": "hypothesis"}
                for row in self_hypotheses
                if row["id"] not in known_self_ids and self._derived_item_visible(conn, "self_hypothesis", row["id"])
            )
            user_items = [dict(row) for row in user_rows if self._derived_item_visible(conn, "user_model", row["id"])]
            known_user_ids = {row["id"] for row in user_items}
            user_items.extend(
                {**dict(row), "status": "hypothesis"}
                for row in user_hypotheses
                if row["id"] not in known_user_ids and self._derived_item_visible(conn, "user_hypothesis", row["id"])
            )
            return {
                "learned_self": self_items[:8],
                "user_model": user_items[:8],
                "relationship": [dict(row) for row in relationship_rows if self._derived_item_visible(conn, "relationship", row["id"])],
            }

    @staticmethod
    def _turn_message_ids(conn: sqlite3.Connection, message_id: str) -> list[str]:
        turn = conn.execute(
            "SELECT user_message_id, assistant_message_id FROM TURN_RUN WHERE user_message_id = ? OR assistant_message_id = ?",
            (message_id, message_id),
        ).fetchone()
        return [value for value in (turn["user_message_id"], turn["assistant_message_id"]) if value] if turn else [message_id]

    @classmethod
    def _messages_have_visible_memory(cls, conn: sqlite3.Connection, message_ids: list[str]) -> bool:
        placeholders = ",".join("?" for _ in message_ids)
        rows = conn.execute(
            f"""SELECT mi.status FROM MEMORY_EVIDENCE me JOIN MEMORY_ITEM mi ON mi.id = me.memory_item_id
                WHERE me.message_id IN ({placeholders})""",
            message_ids,
        ).fetchall()
        return not rows or any(row["status"] != "soft_deleted" for row in rows)

    @classmethod
    def _observation_sources_visible(cls, conn: sqlite3.Connection, observation_ids: list[str]) -> bool:
        if not observation_ids:
            return True
        for observation_id in observation_ids:
            row = conn.execute(
                "SELECT source_message_id FROM SELF_OBSERVATION WHERE id = ?", (observation_id,)
            ).fetchone()
            if not row:
                continue
            if cls._messages_have_visible_memory(conn, cls._turn_message_ids(conn, row["source_message_id"])):
                return True
        return False

    @classmethod
    def _derived_item_visible(cls, conn: sqlite3.Connection, kind: str, item_id: str) -> bool:
        if kind == "self_model":
            rows = conn.execute(
                "SELECT self_observation_id FROM SELF_MODEL_EVIDENCE WHERE self_model_item_id = ?", (item_id,)
            ).fetchall()
            return cls._observation_sources_visible(conn, [row["self_observation_id"] for row in rows])
        if kind == "self_hypothesis":
            rows = conn.execute(
                "SELECT self_observation_id FROM HYPOTHESIS_EVIDENCE WHERE self_hypothesis_id = ?", (item_id,)
            ).fetchall()
            return cls._observation_sources_visible(conn, [row["self_observation_id"] for row in rows])
        if kind == "user_model":
            rows = conn.execute(
                """SELECT mi.status AS memory_status, mc.claim_status
                   FROM USER_MODEL_EVIDENCE ume
                   JOIN MEMORY_CLAIM mc ON mc.memory_item_id = ume.memory_claim_id
                   JOIN MEMORY_ITEM mi ON mi.id = mc.memory_item_id
                   WHERE ume.user_model_item_id = ?""",
                (item_id,),
            ).fetchall()
            return not rows or any(
                row["memory_status"] not in {"soft_deleted", "superseded"}
                and row["claim_status"] != "historical"
                for row in rows
            )
        if kind == "user_hypothesis":
            rows = conn.execute(
                """SELECT mi.status FROM USER_HYPOTHESIS_EVIDENCE uhe
                   JOIN MEMORY_ITEM mi ON mi.id = uhe.memory_item_id
                   WHERE uhe.user_hypothesis_id = ?""",
                (item_id,),
            ).fetchall()
            return not rows or any(row["status"] != "soft_deleted" for row in rows)
        if kind == "relationship":
            rows = conn.execute(
                """SELECT rs.source_message_id FROM RELATIONSHIP_DIMENSION_EVIDENCE rde
                   JOIN RELATIONSHIP_SIGNAL rs ON rs.id = rde.relationship_signal_id
                   WHERE rde.relationship_dimension_id = ?""",
                (item_id,),
            ).fetchall()
            if not rows:
                return True
            for row in rows:
                source_message_id = row["source_message_id"]
                if not source_message_id:
                    return True
                if cls._messages_have_visible_memory(conn, [source_message_id]):
                    return True
            return False
        return True

    def create_turn(self, user_text: str, reply_to_message_id: str | None = None) -> dict[str, Any]:
        timestamp = now_iso()
        with self.db.transaction() as conn:
            scope = conn.execute(
                """SELECT c.id AS conversation_id, c.ai_identity_id, c.user_profile_id
                   FROM CONVERSATION c ORDER BY c.started_at DESC LIMIT 1"""
            ).fetchone()
            if not scope:
                raise RuntimeError("local conversation is missing")
            if reply_to_message_id is not None:
                reply_target = conn.execute(
                    """SELECT id FROM MESSAGE WHERE id = ? AND conversation_id = ?
                       AND (speaker = 'user' AND status = 'committed'
                            OR speaker = 'assistant' AND status IN ('delivery_partial', 'delivered'))""",
                    (reply_to_message_id, scope["conversation_id"]),
                ).fetchone()
                if not reply_target:
                    raise ValueError("reply target must be a canonical message in this conversation")
            active = conn.execute(
                """SELECT id FROM TURN_RUN WHERE conversation_id = ?
                   AND status IN ('preparing', 'generating', 'streaming') LIMIT 1""",
                (scope["conversation_id"],),
            ).fetchone()
            if active:
                raise RuntimeError(f"conversation already has active turn {active['id']}")
            transcript_revision = conn.execute(
                "SELECT COUNT(*) AS n FROM MESSAGE WHERE conversation_id = ?",
                (scope["conversation_id"],),
            ).fetchone()["n"] + 1
            turn_sequence = conn.execute(
                "SELECT COALESCE(MAX(turn_sequence), 0) + 1 AS n FROM TURN_RUN WHERE conversation_id = ?",
                (scope["conversation_id"],),
            ).fetchone()["n"]
            turn_id = new_id()
            user_message_id = new_id()
            cancel_scope_id = new_id()
            revision = int(
                conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()["value"]
            )
            conn.execute(
                """INSERT INTO MESSAGE
                   (id, conversation_id, speaker, content, channel, status, created_at, reply_to_message_id)
                   VALUES (?, ?, 'user', ?, 'text', 'committed', ?, ?)""",
                (user_message_id, scope["conversation_id"], user_text, timestamp, reply_to_message_id),
            )
            conn.execute(
                """INSERT INTO TURN_RUN
                   (id, conversation_id, user_message_id, turn_sequence, status,
                    state_revision, transcript_revision, started_at)
                   VALUES (?, ?, ?, ?, 'preparing', ?, ?, ?)""",
                (
                    turn_id,
                    scope["conversation_id"],
                    user_message_id,
                    turn_sequence,
                    revision,
                    transcript_revision,
                    timestamp,
                ),
            )
            conn.execute(
                """INSERT INTO CANCELLATION_SCOPE(id, turn_run_id, status)
                   VALUES (?, ?, 'active')""",
                (cancel_scope_id, turn_id),
            )
            event_id = self.emit_event(
                conn,
                turn_id,
                "UserTurnCommitted",
                "CMP-ORCH-01",
                "canonical",
                "durable",
                {
                    "user_message_id": user_message_id,
                    "transcript_revision": transcript_revision,
                    "state_revision": revision,
                },
            )
            return {
                "turn_id": turn_id,
                "user_message_id": user_message_id,
                "conversation_id": scope["conversation_id"],
                "ai_identity_id": scope["ai_identity_id"],
                "user_profile_id": scope["user_profile_id"],
                "cancellation_scope_id": cancel_scope_id,
                "state_revision": revision,
                "transcript_revision": transcript_revision,
                "turn_sequence": turn_sequence,
                "committed_at": timestamp,
                "reply_to_message_id": reply_to_message_id,
                "causation_event_id": event_id,
            }

    def create_attempt(
        self,
        turn_id: str,
        cancellation_scope_id: str,
        component: str,
        operation: str,
        deadline_mono_ns: int | None = None,
    ) -> tuple[str, int]:
        with self.db.transaction() as conn:
            number = conn.execute(
                """SELECT COALESCE(MAX(attempt_no), 0) + 1 AS n FROM COMPONENT_ATTEMPT
                   WHERE turn_run_id = ? AND component = ? AND operation = ?""",
                (turn_id, component, operation),
            ).fetchone()["n"]
            attempt_id = new_id()
            started = time.monotonic_ns()
            conn.execute(
                """INSERT INTO COMPONENT_ATTEMPT
                   (id, turn_run_id, cancellation_scope_id, component, operation, status,
                    attempt_no, started_mono_ns, deadline_mono_ns)
                   VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)""",
                (
                    attempt_id,
                    turn_id,
                    cancellation_scope_id,
                    component,
                    operation,
                    number,
                    started,
                    deadline_mono_ns,
                ),
            )
            self.emit_event(
                conn,
                turn_id,
                "ComponentAttemptStarted",
                component,
                "trace",
                "durable",
                {"attempt_id": attempt_id, "operation": operation, "attempt_no": number},
            )
            return attempt_id, number

    def finish_attempt(
        self,
        attempt_id: str,
        status: str,
        failure_code: str | None = None,
        retryable: bool = False,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT turn_run_id, component, operation FROM COMPONENT_ATTEMPT WHERE id = ?",
                (attempt_id,),
            ).fetchone()
            if not row:
                raise KeyError(f"unknown component attempt: {attempt_id}")
            conn.execute(
                """UPDATE COMPONENT_ATTEMPT SET status = ?, failure_code = ?, retryable = ?,
                   ended_mono_ns = ? WHERE id = ? AND status = 'running'""",
                (status, failure_code, int(retryable), time.monotonic_ns(), attempt_id),
            )
            self.emit_event(
                conn,
                row["turn_run_id"],
                "ComponentAttemptFinished",
                row["component"],
                "trace",
                "durable",
                {
                    "attempt_id": attempt_id,
                    "operation": row["operation"],
                    "status": status,
                    "failure_code": failure_code,
                    "retryable": retryable,
                    **(payload or {}),
                },
            )

    def update_turn_status(
        self,
        turn_id: str,
        status: str,
        reason: str | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT status FROM TURN_RUN WHERE id = ?", (turn_id,)).fetchone()
            if not row:
                raise KeyError(f"unknown turn: {turn_id}")
            current = row["status"]
            if current in TERMINAL_STATUSES:
                if current == status:
                    return
                raise RuntimeError(f"terminal turn cannot transition from {current} to {status}")
            if status not in TERMINAL_STATUSES:
                allowed = {
                    "preparing": {"generating"},
                    "generating": {"streaming"},
                    "streaming": set(),
                }
                if status not in allowed[current]:
                    raise RuntimeError(f"invalid turn transition: {current} -> {status}")
            timestamp = now_iso() if status in TERMINAL_STATUSES else None
            conn.execute(
                """UPDATE TURN_RUN SET status = ?, terminal_reason = ?,
                   completed_at = COALESCE(?, completed_at) WHERE id = ?""",
                (status, reason, timestamp, turn_id),
            )
            self.emit_event(
                conn,
                turn_id,
                "TurnPhaseChanged",
                "CMP-ORCH-01",
                "canonical",
                "durable",
                {"from": current, "to": status, "reason": reason},
            )
            if status in TERMINAL_STATUSES:
                conn.execute(
                    "UPDATE CANCELLATION_SCOPE SET status = 'closed' WHERE turn_run_id = ? AND status = 'active'",
                    (turn_id,),
                )

    def set_generating(self, turn_id: str) -> None:
        self.update_turn_status(turn_id, "generating")

    def create_invocation(
        self,
        turn_id: str,
        context_snapshot_id: str,
        attempt_id: str,
        model_id: str,
    ) -> str:
        invocation_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO MODEL_INVOCATION
                   (id, turn_run_id, context_snapshot_id, component_attempt_id, role, backend,
                    model_id, blocking, schema_version, status, started_at)
                   VALUES (?, ?, ?, ?, 'dialogue', 'ollama', ?, 1, 'generation-request-v1', 'running', ?)""",
                (invocation_id, turn_id, context_snapshot_id, attempt_id, model_id, now_iso()),
            )
            self.emit_event(
                conn,
                turn_id,
                "GenerationStarted",
                "CMP-GW-01",
                "trace",
                "durable",
                {"invocation_id": invocation_id, "attempt_id": attempt_id, "model_id": model_id},
            )
        return invocation_id

    def mark_first_token(self, turn_id: str, invocation_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE TURN_RUN SET first_token_at = COALESCE(first_token_at, ?) WHERE id = ?",
                (now_iso(), turn_id),
            )
            status = conn.execute("SELECT status FROM TURN_RUN WHERE id = ?", (turn_id,)).fetchone()["status"]
            if status == "generating":
                conn.execute("UPDATE TURN_RUN SET status = 'streaming' WHERE id = ?", (turn_id,))
                self.emit_event(
                    conn,
                    turn_id,
                    "TurnPhaseChanged",
                    "CMP-ORCH-01",
                    "trace",
                    "durable",
                    {"from": "generating", "to": "streaming", "reason": None},
                )
            self.emit_event(
                conn,
                turn_id,
                "GenerationFirstToken",
                "CMP-GW-01",
                "provisional",
                "durable",
                {"invocation_id": invocation_id},
            )

    def finish_invocation(
        self,
        invocation_id: str,
        status: str,
        failure_code: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        ttft_ms: int | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT turn_run_id FROM MODEL_INVOCATION WHERE id = ?", (invocation_id,)
            ).fetchone()
            if not row:
                raise KeyError(f"unknown invocation: {invocation_id}")
            conn.execute(
                """UPDATE MODEL_INVOCATION SET status = ?, failure_code = ?, input_tokens = ?,
                   output_tokens = ?, ttft_ms = ?, duration_ms =
                   CAST((julianday(?) - julianday(started_at)) * 86400000 AS INTEGER),
                   completed_at = ? WHERE id = ?""",
                (status, failure_code, input_tokens, output_tokens, ttft_ms, now_iso(), now_iso(), invocation_id),
            )
            self.emit_event(
                conn,
                row["turn_run_id"],
                "GenerationCompleted" if status == "completed" else "GenerationFailed",
                "CMP-GW-01",
                "trace",
                "durable",
                {
                    "invocation_id": invocation_id,
                    "status": status,
                    "failure_code": failure_code,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "ttft_ms": ttft_ms,
                },
            )

    def save_retrieval(
        self,
        turn_id: str,
        conversation_id: str,
        query_text: str,
        scope: dict[str, str],
        profile_id: str,
        request_revision: int,
        completion_revision: int,
        status: str,
        degraded_reasons: list[str],
        elapsed: dict[str, int],
        results: Iterable[dict[str, Any]],
    ) -> str:
        retrieval_run_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO RETRIEVAL_RUN
                   (id, turn_run_id, conversation_id, query_text, scope_json, profile_id,
                    request_state_revision, completion_state_revision, status, degraded_reasons,
                    elapsed_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    retrieval_run_id,
                    turn_id,
                    conversation_id,
                    query_text,
                    json.dumps(scope, ensure_ascii=False),
                    profile_id,
                    request_revision,
                    completion_revision,
                    status,
                    json.dumps(degraded_reasons, ensure_ascii=False),
                    json.dumps(elapsed, ensure_ascii=False),
                    now_iso(),
                ),
            )
            for result in results:
                conn.execute(
                    """INSERT INTO RETRIEVAL_RESULT
                       (id, retrieval_run_id, source_kind, source_ref, memory_item_id, message_id,
                        source_class, source_time, temporal_role, source_status, content_for_context,
                        evidence_refs, signals, final_rank, privacy_class)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result["result_id"],
                        retrieval_run_id,
                        result["source_kind"],
                        result["source_ref"],
                        result.get("memory_item_id"),
                        result.get("message_id"),
                        result["source_class"],
                        result["source_time"],
                        result["temporal_role"],
                        result["source_status"],
                        result["content_for_context"],
                        json.dumps(result["evidence_refs"], ensure_ascii=False),
                        json.dumps(result["signals"], ensure_ascii=False),
                        result["final_rank"],
                        result["privacy_class"],
                    ),
                )
            self.emit_event(
                conn,
                turn_id,
                "RetrievalSnapshotReady",
                "CMP-RETR-01",
                "snapshot",
                "durable",
                {
                    "retrieval_run_id": retrieval_run_id,
                    "request_state_revision": request_revision,
                    "completion_state_revision": completion_revision,
                    "status": status,
                    "degraded_reasons": degraded_reasons,
                    "result_count": len(list(results)) if not isinstance(results, list) else len(results),
                    "profile_id": profile_id,
                },
            )
        return retrieval_run_id

    def validate_retrieval_sources(
        self, sources: list[dict[str, str]], expected_revision: int
    ) -> tuple[list[dict[str, str]], int]:
        with self.db.session() as conn:
            current_revision = int(
                conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()["value"]
            )
            visible: list[dict[str, str]] = []
            for source in sources:
                if source["source_kind"] == "raw_message":
                    row = conn.execute(
                        """SELECT id FROM MESSAGE WHERE id = ?
                           AND (speaker = 'user' AND status = 'committed'
                                OR speaker = 'assistant' AND status IN ('delivering', 'delivery_partial', 'delivered'))
                           AND NOT EXISTS (
                               SELECT 1 FROM MEMORY_EVIDENCE evidence
                               JOIN MEMORY_ITEM mi ON mi.id = evidence.memory_item_id
                               WHERE evidence.message_id = MESSAGE.id AND mi.status = 'soft_deleted'
                           )
                           AND NOT EXISTS (
                               SELECT 1 FROM TURN_RUN source_turn
                               JOIN MEMORY_EVIDENCE evidence
                                 ON evidence.message_id IN (source_turn.user_message_id, source_turn.assistant_message_id)
                               JOIN MEMORY_ITEM mi ON mi.id = evidence.memory_item_id
                               WHERE (source_turn.user_message_id = MESSAGE.id
                                      OR source_turn.assistant_message_id = MESSAGE.id)
                                 AND mi.status = 'soft_deleted'
                           )
                           AND NOT EXISTS (
                               SELECT 1 FROM TURN_RUN command_turn
                               JOIN TURN_EVENT_TRACE command_event ON command_event.turn_run_id = command_turn.id
                               WHERE (command_turn.user_message_id = MESSAGE.id
                                      OR command_turn.assistant_message_id = MESSAGE.id)
                                 AND command_event.event_type = 'ExplicitCommandDetected'
                                 AND command_event.payload LIKE '%"kind":"forget"%'
                           )""",
                        (source["source_ref"],),
                    ).fetchone()
                else:
                    row = conn.execute(
                        """SELECT mi.id FROM MEMORY_ITEM mi
                           WHERE mi.id = ? AND mi.status <> 'soft_deleted'
                             AND EXISTS (
                               SELECT 1 FROM MEMORY_EVIDENCE evidence
                               JOIN MESSAGE source ON source.id = evidence.message_id
                               WHERE evidence.memory_item_id = mi.id
                                 AND (source.speaker = 'user' AND source.status = 'committed'
                                      OR source.speaker = 'assistant'
                                         AND source.status IN ('delivery_partial', 'delivered'))
                             )""",
                        (source["source_ref"],),
                    ).fetchone()
                if row:
                    visible.append(dict(source))
            return visible, current_revision

    def save_context_snapshot(
        self,
        turn_id: str,
        retrieval_run_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        snapshot_id = snapshot["context_snapshot_id"]
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO CONTEXT_SNAPSHOT
                   (id, turn_run_id, retrieval_run_id, schema_version, state_revision,
                    transcript_revision, input_truth, identity_version, persona_version,
                    privacy_filter_version, token_budget_total, estimated_tokens,
                    sections_json, selected_refs_json, omissions_json, context_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot_id,
                    turn_id,
                    retrieval_run_id,
                    snapshot["schema_version"],
                    snapshot["state_revision"],
                    snapshot["transcript_revision"],
                    snapshot["input_truth"],
                    snapshot["identity_version"],
                    snapshot["persona_version"],
                    snapshot["privacy_filter_version"],
                    snapshot["token_budget_total"],
                    snapshot["estimated_tokens"],
                    json.dumps(snapshot["sections"], ensure_ascii=False),
                    json.dumps(snapshot["selected_refs"], ensure_ascii=False),
                    json.dumps(snapshot["omissions"], ensure_ascii=False),
                    json.dumps(snapshot["messages"], ensure_ascii=False),
                    now_iso(),
                ),
            )
            self.emit_event(
                conn,
                turn_id,
                "ContextCapsuleBuilt",
                "CMP-CTX-01",
                "snapshot",
                "durable",
                {
                    "context_snapshot_id": snapshot_id,
                    "retrieval_run_id": retrieval_run_id,
                    "state_revision": snapshot["state_revision"],
                    "transcript_revision": snapshot["transcript_revision"],
                    "estimated_tokens": snapshot["estimated_tokens"],
                    "token_budget_total": snapshot["token_budget_total"],
                    "selected_refs": snapshot["selected_refs"],
                    "omissions": snapshot["omissions"],
                },
            )
        return snapshot_id

    def append_delivery_checkpoint(
        self,
        turn_id: str,
        invocation_id: str,
        offset: int,
        text: str,
    ) -> dict[str, Any]:
        if not text:
            raise ValueError("delivery checkpoint must contain text")
        with self.db.transaction() as conn:
            run = conn.execute(
                "SELECT conversation_id, assistant_message_id, status FROM TURN_RUN WHERE id = ?",
                (turn_id,),
            ).fetchone()
            if not run:
                raise KeyError(f"unknown turn: {turn_id}")
            if run["status"] not in ("generating", "streaming"):
                raise RuntimeError(f"turn does not accept delivery checkpoints in {run['status']}")
            message_id = run["assistant_message_id"]
            if message_id is None:
                if offset != 0:
                    raise ValueError("first delivery checkpoint must start at offset zero")
                message_id = new_id()
                conn.execute(
                    """INSERT INTO MESSAGE
                       (id, conversation_id, speaker, content, channel, status, delivery_offset, created_at)
                       VALUES (?, ?, 'assistant', ?, 'text', 'delivering', ?, ?)""",
                    (message_id, run["conversation_id"], text, len(text), now_iso()),
                )
                conn.execute("UPDATE TURN_RUN SET assistant_message_id = ? WHERE id = ?", (message_id, turn_id))
            else:
                existing = conn.execute("SELECT content, delivery_offset FROM MESSAGE WHERE id = ?", (message_id,)).fetchone()
                if offset != existing["delivery_offset"]:
                    if offset < existing["delivery_offset"] and existing["content"][offset:offset + len(text)] == text:
                        return {"message_id": message_id, "offset": existing["delivery_offset"], "duplicate": True}
                    raise ValueError("delivery checkpoints must be contiguous and ordered")
                conn.execute(
                    """UPDATE MESSAGE SET content = content || ?, delivery_offset = ?, status = 'delivering'
                       WHERE id = ?""",
                    (text, offset + len(text), message_id),
                )
            conn.execute(
                """INSERT INTO DELIVERY_SPAN
                   (id, model_invocation_id, assistant_message_id, char_start, char_end,
                    delivery_basis, confidence_class, observed_at)
                   VALUES (?, ?, ?, ?, ?, 'ui_dom_painted_ack', 'high', ?)""",
                (new_id(), invocation_id, message_id, offset, offset + len(text), now_iso()),
            )
            self.emit_event(
                conn,
                turn_id,
                "AssistantDeliveryCheckpoint",
                "CMP-DLV-01",
                "canonical",
                "durable",
                {
                    "assistant_message_id": message_id,
                    "char_start": offset,
                    "char_end": offset + len(text),
                    "delivery_basis": "ui_dom_painted_ack",
                },
            )
            if run["status"] == "generating":
                conn.execute("UPDATE TURN_RUN SET status = 'streaming' WHERE id = ?", (turn_id,))
                self.emit_event(
                    conn,
                    turn_id,
                    "TurnPhaseChanged",
                    "CMP-ORCH-01",
                    "trace",
                    "durable",
                    {"from": "generating", "to": "streaming", "reason": "first delivery checkpoint"},
                )
            return {"message_id": message_id, "offset": offset + len(text), "duplicate": False}

    def finalize_delivery(self, turn_id: str, requested_status: str, reason: str | None = None) -> dict[str, Any]:
        if requested_status not in TERMINAL_STATUSES:
            raise ValueError("invalid terminal status")
        with self.db.transaction() as conn:
            run = conn.execute(
                "SELECT status, assistant_message_id FROM TURN_RUN WHERE id = ?", (turn_id,)
            ).fetchone()
            if not run:
                raise KeyError(f"unknown turn: {turn_id}")
            if run["status"] in TERMINAL_STATUSES:
                return {"status": run["status"], "assistant_message_id": run["assistant_message_id"]}
            message_id = run["assistant_message_id"]
            message = conn.execute("SELECT content FROM MESSAGE WHERE id = ?", (message_id,)).fetchone() if message_id else None
            delivered = message["content"] if message else ""
            final_status = requested_status
            if requested_status == "completed" and not delivered:
                final_status = "failed_before_delivery"
                reason = reason or "generation completed without rendered output"
            if requested_status in ("completed_partial", "cancelled") and not delivered:
                message_id = None
            if message_id:
                message_status = "delivered" if final_status == "completed" else "delivery_partial"
                conn.execute(
                    "UPDATE MESSAGE SET status = ?, completed_at = ? WHERE id = ?",
                    (message_status, now_iso(), message_id),
                )
            conn.execute(
                "UPDATE TURN_RUN SET assistant_message_id = ?, status = ?, terminal_reason = ?, completed_at = ? WHERE id = ?",
                (message_id, final_status, reason, now_iso(), turn_id),
            )
            self.emit_event(
                conn,
                turn_id,
                "AssistantDeliveryCompleted",
                "CMP-DLV-01",
                "canonical",
                "durable",
                {
                    "assistant_message_id": message_id,
                    "delivered_char_count": len(delivered),
                    "completion_status": final_status,
                    "reason": reason,
                },
            )
            self.emit_event(
                conn,
                turn_id,
                "TurnPhaseChanged",
                "CMP-ORCH-01",
                "canonical",
                "durable",
                {"from": run["status"], "to": final_status, "reason": reason},
            )
            conn.execute("UPDATE CANCELLATION_SCOPE SET status = 'closed' WHERE turn_run_id = ?", (turn_id,))
            return {
                "status": final_status,
                "assistant_message_id": message_id,
                "delivered_text": delivered,
            }

    def cancel_turn(self, turn_id: str, reason: str = "user_cancelled") -> None:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT status FROM TURN_RUN WHERE id = ?", (turn_id,)).fetchone()
            if not row:
                raise KeyError(f"unknown turn: {turn_id}")
            if row["status"] in TERMINAL_STATUSES:
                return
            conn.execute(
                """UPDATE CANCELLATION_SCOPE SET status = 'cancelled', cancel_reason = ?, cancelled_at = ?
                   WHERE turn_run_id = ?""",
                (reason, now_iso(), turn_id),
            )
            self.emit_event(
                conn,
                turn_id,
                "TurnCancellationRequested",
                "CMP-ORCH-01",
                "trace",
                "durable",
                {"reason": reason},
            )

    def interrupted_turn_ids(self) -> list[str]:
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT id FROM TURN_RUN WHERE status IN ('preparing', 'generating', 'streaming')"
            ).fetchall()
            return [row["id"] for row in rows]

    def recover_interrupted_turn(self, turn_id: str) -> None:
        with self.db.transaction() as conn:
            run = conn.execute(
                "SELECT status, assistant_message_id FROM TURN_RUN WHERE id = ?", (turn_id,)
            ).fetchone()
            if not run or run["status"] in TERMINAL_STATUSES:
                return
            message_id = run["assistant_message_id"]
            message = conn.execute("SELECT content FROM MESSAGE WHERE id = ?", (message_id,)).fetchone() if message_id else None
            has_delivery = bool(message and message["content"])
            status = "completed_partial" if has_delivery else "failed_before_delivery"
            if has_delivery:
                conn.execute(
                    "UPDATE MESSAGE SET status = 'delivery_partial', completed_at = ? WHERE id = ?",
                    (now_iso(), message_id),
                )
            else:
                conn.execute("UPDATE TURN_RUN SET assistant_message_id = NULL WHERE id = ?", (turn_id,))
                message_id = None
            conn.execute(
                """UPDATE TURN_RUN SET status = ?, terminal_reason = 'process_restart',
                   completed_at = ? WHERE id = ?""",
                (status, now_iso(), turn_id),
            )
            conn.execute(
                "UPDATE CANCELLATION_SCOPE SET status = 'closed', cancel_reason = 'process_restart' WHERE turn_run_id = ?",
                (turn_id,),
            )
            now = now_iso()
            invocation_rows = conn.execute(
                """SELECT id, role, model_id, component_attempt_id FROM MODEL_INVOCATION
                   WHERE turn_run_id = ? AND status = 'running'""",
                (turn_id,),
            ).fetchall()
            for invocation in invocation_rows:
                conn.execute(
                    """UPDATE MODEL_INVOCATION SET status = 'cancelled', failure_code = 'process_restart',
                       completed_at = ?, duration_ms = CAST((julianday(?) - julianday(started_at))
                       * 86400000 AS INTEGER) WHERE id = ?""",
                    (now, now, invocation["id"]),
                )
                self.emit_event(
                    conn,
                    turn_id,
                    "GenerationFailed",
                    "CMP-GW-01",
                    "trace",
                    "durable",
                    {
                        "invocation_id": invocation["id"],
                        "role": invocation["role"],
                        "model_id": invocation["model_id"],
                        "status": "cancelled",
                        "failure_code": "process_restart",
                    },
                )
            attempt_rows = conn.execute(
                """SELECT id, component, operation, cancellation_scope_id FROM COMPONENT_ATTEMPT
                   WHERE turn_run_id = ? AND status = 'running'""",
                (turn_id,),
            ).fetchall()
            for attempt in attempt_rows:
                conn.execute(
                    """UPDATE COMPONENT_ATTEMPT SET status = 'cancelled', failure_code = 'process_restart',
                       retryable = 1, ended_mono_ns = ? WHERE id = ?""",
                    (time.monotonic_ns(), attempt["id"]),
                )
                self.emit_event(
                    conn,
                    turn_id,
                    "ComponentAttemptFinished",
                    attempt["component"],
                    "trace",
                    "durable",
                    {
                        "attempt_id": attempt["id"],
                        "operation": attempt["operation"],
                        "status": "cancelled",
                        "failure_code": "process_restart",
                        "retryable": True,
                    },
                )
            self.emit_event(
                conn,
                turn_id,
                "TurnRecoveredAfterProcessRestart",
                "CMP-ORCH-01",
                "canonical",
                "durable",
                {"status": status, "assistant_message_id": message_id},
            )

    @staticmethod
    def _canonical_message_query(where: str) -> str:
        return f"""SELECT m.id, m.speaker, m.content, m.status, m.created_at, m.completed_at,
                          m.reply_to_message_id, reply.speaker AS reply_to_speaker,
                          reply.content AS reply_to_content,
                          tr.id AS turn_id, tr.status AS turn_status
                   FROM MESSAGE m
                   LEFT JOIN MESSAGE reply ON reply.id = m.reply_to_message_id
                   LEFT JOIN TURN_RUN tr ON tr.user_message_id = m.id OR tr.assistant_message_id = m.id
                   WHERE {where}
                     AND (m.speaker = 'user' AND m.status = 'committed'
                          OR m.speaker = 'assistant' AND m.content <> ''
                             AND m.status IN ('delivery_partial', 'delivered'))"""

    def history_page(
        self,
        limit: int = 60,
        before_created_at: str | None = None,
        before_id: str | None = None,
    ) -> dict[str, Any]:
        bounded_limit = max(1, min(int(limit), 100))
        with self.db.session() as conn:
            conversation = conn.execute(
                "SELECT id FROM CONVERSATION ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not conversation:
                return {"messages": [], "has_more": False, "next_cursor": None}
            where = "m.conversation_id = ?"
            params: list[Any] = [conversation["id"]]
            if before_created_at is not None or before_id is not None:
                if not before_created_at or not before_id:
                    raise ValueError("both history cursor fields are required")
                where += " AND (m.created_at < ? OR (m.created_at = ? AND m.id < ?))"
                params.extend((before_created_at, before_created_at, before_id))
            rows = conn.execute(
                self._canonical_message_query(where) + " ORDER BY m.created_at DESC, m.id DESC LIMIT ?",
                (*params, bounded_limit + 1),
            ).fetchall()
            has_more = len(rows) > bounded_limit
            page = [dict(row) for row in reversed(rows[:bounded_limit])]
            cursor = None
            if has_more and page:
                cursor = {"created_at": page[0]["created_at"], "id": page[0]["id"]}
            return {"messages": page, "has_more": has_more, "next_cursor": cursor}

    def history(self, limit: int = 500) -> list[dict[str, Any]]:
        # Compatibility helper for internal callers and older tests.
        page = self.history_page(min(limit, 100))
        return page["messages"]

    def search_history(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self.db.session() as conn:
            conversation = conn.execute(
                "SELECT id FROM CONVERSATION ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not conversation:
                return []
            rows = conn.execute(
                self._canonical_message_query("m.conversation_id = ? AND m.content LIKE ? ESCAPE '\\'")
                + " ORDER BY m.created_at DESC, m.id DESC LIMIT ?",
                (conversation["id"], f"%{escaped}%", max(1, min(int(limit), 100))),
            ).fetchall()
            return [dict(row) for row in rows]

    def history_around(self, message_id: str, radius: int = 30) -> dict[str, Any]:
        bounded_radius = max(1, min(int(radius), 50))
        with self.db.session() as conn:
            conversation = conn.execute(
                "SELECT id FROM CONVERSATION ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not conversation:
                raise KeyError(f"unknown message: {message_id}")
            target = conn.execute(
                self._canonical_message_query("m.conversation_id = ? AND m.id = ?"),
                (conversation["id"], message_id),
            ).fetchone()
            if not target:
                raise KeyError(f"unknown canonical message: {message_id}")
            older = conn.execute(
                self._canonical_message_query(
                    "m.conversation_id = ? AND (m.created_at < ? OR (m.created_at = ? AND m.id < ?))"
                ) + " ORDER BY m.created_at DESC, m.id DESC LIMIT ?",
                (conversation["id"], target["created_at"], target["created_at"], target["id"], bounded_radius + 1),
            ).fetchall()
            newer = conn.execute(
                self._canonical_message_query(
                    "m.conversation_id = ? AND (m.created_at > ? OR (m.created_at = ? AND m.id > ?))"
                ) + " ORDER BY m.created_at, m.id LIMIT ?",
                (conversation["id"], target["created_at"], target["created_at"], target["id"], bounded_radius + 1),
            ).fetchall()
            messages = [dict(row) for row in reversed(older[:bounded_radius])]
            messages.append(dict(target))
            messages.extend(dict(row) for row in newer[:bounded_radius])
            return {
                "messages": messages,
                "target_id": message_id,
                "has_older": len(older) > bounded_radius,
                "has_newer": len(newer) > bounded_radius,
            }

    def recent_messages(
        self,
        conversation_id: str,
        exclude_message_id: str,
        limit: int = 12,
        before_created_at: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.db.session() as conn:
            time_filter = " AND created_at < ?" if before_created_at is not None else ""
            parameters: list[Any] = [conversation_id, exclude_message_id]
            if before_created_at is not None:
                parameters.append(before_created_at)
            parameters.append(limit)
            rows = conn.execute(
                f"""SELECT id, speaker, content, status, created_at FROM MESSAGE
                   WHERE conversation_id = ? AND id <> ?
                     {time_filter}
                     AND (speaker = 'user' AND status = 'committed'
                          OR speaker = 'assistant' AND status IN ('delivery_partial', 'delivered'))
                     AND NOT EXISTS (
                       SELECT 1 FROM MEMORY_EVIDENCE evidence
                       JOIN MEMORY_ITEM mi ON mi.id = evidence.memory_item_id
                       WHERE evidence.message_id = MESSAGE.id AND mi.status = 'soft_deleted'
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM TURN_RUN source_turn
                       JOIN MEMORY_EVIDENCE evidence
                         ON evidence.message_id IN (source_turn.user_message_id, source_turn.assistant_message_id)
                       JOIN MEMORY_ITEM mi ON mi.id = evidence.memory_item_id
                       WHERE (source_turn.user_message_id = MESSAGE.id
                              OR source_turn.assistant_message_id = MESSAGE.id)
                         AND mi.status = 'soft_deleted'
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM TURN_RUN command_turn
                       JOIN TURN_EVENT_TRACE command_event ON command_event.turn_run_id = command_turn.id
                       WHERE (command_turn.user_message_id = MESSAGE.id
                              OR command_turn.assistant_message_id = MESSAGE.id)
                         AND command_event.event_type = 'ExplicitCommandDetected'
                         AND command_event.payload LIKE '%"kind":"forget"%'
                     )
                   ORDER BY created_at DESC, id DESC LIMIT ?""",
                parameters,
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def retrieval_sources(self, ai_identity_id: str, user_profile_id: str, limit: int) -> list[dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute(
                """SELECT m.id AS message_id, m.speaker, m.content, m.status, m.created_at
                   FROM MESSAGE m
                   JOIN CONVERSATION c ON c.id = m.conversation_id
                   WHERE c.ai_identity_id = ? AND c.user_profile_id = ? AND m.content <> ''
                     AND (m.speaker = 'user' AND m.status = 'committed'
                          OR m.speaker = 'assistant' AND m.status IN ('delivering', 'delivery_partial', 'delivered'))
                     AND NOT EXISTS (
                       SELECT 1 FROM MEMORY_EVIDENCE evidence
                       JOIN MEMORY_ITEM mi ON mi.id = evidence.memory_item_id
                       WHERE evidence.message_id = m.id AND mi.status = 'soft_deleted'
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM TURN_RUN source_turn
                       JOIN MEMORY_EVIDENCE evidence
                         ON evidence.message_id IN (source_turn.user_message_id, source_turn.assistant_message_id)
                       JOIN MEMORY_ITEM mi ON mi.id = evidence.memory_item_id
                       WHERE (source_turn.user_message_id = m.id OR source_turn.assistant_message_id = m.id)
                         AND mi.status = 'soft_deleted'
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM TURN_RUN command_turn
                       JOIN TURN_EVENT_TRACE command_event ON command_event.turn_run_id = command_turn.id
                       WHERE (command_turn.user_message_id = m.id OR command_turn.assistant_message_id = m.id)
                         AND command_event.event_type = 'ExplicitCommandDetected'
                         AND command_event.payload LIKE '%"kind":"forget"%'
                     )
                   ORDER BY m.created_at DESC, m.id DESC LIMIT ?""",
                (ai_identity_id, user_profile_id, limit),
            ).fetchall()
            return [
                {
                    **dict(row),
                    "source_kind": "raw_message",
                    "source_ref": row["message_id"],
                    "source_key": f"raw_message:{row['message_id']}",
                    "source_class": "raw_user_message" if row["speaker"] == "user" else "raw_assistant_message",
                    "source_time": row["created_at"],
                    "source_status": row["status"],
                    "evidence_refs": [{"source_kind": "raw_message", "source_ref": row["message_id"]}],
                    "privacy_class": "local_only",
                    "memory_item_id": None,
                }
                for row in rows
            ]

    def memory_sources(self, ai_identity_id: str, limit: int) -> list[dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute(
                """SELECT mi.id AS memory_item_id, mi.summary, mi.memory_kind, mi.status,
                          mi.importance, mi.happened_at, mi.created_at, mi.retention_class,
                          mc.subject_type, mc.predicate, mc.object_value,
                          me.event_type
                   FROM MEMORY_ITEM mi
                   LEFT JOIN MEMORY_CLAIM mc ON mc.memory_item_id = mi.id
                   LEFT JOIN MEMORY_EPISODE me ON me.memory_item_id = mi.id
                   WHERE mi.ai_identity_id = ?
                     AND mi.status IN ('active', 'archived', 'superseded')
                     AND COALESCE(mi.retention_class, '') NOT IN ('secret', 'credential')
                     AND EXISTS (
                         SELECT 1 FROM MEMORY_EVIDENCE evidence
                         JOIN MESSAGE source ON source.id = evidence.message_id
                         WHERE evidence.memory_item_id = mi.id
                           AND (source.speaker = 'user' AND source.status = 'committed'
                                OR source.speaker = 'assistant'
                                   AND source.status IN ('delivery_partial', 'delivered'))
                     )
                   ORDER BY CASE mi.status WHEN 'active' THEN 0 WHEN 'archived' THEN 1 ELSE 2 END,
                            mi.importance DESC, mi.created_at DESC LIMIT ?""",
                (ai_identity_id, limit),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                content = row["summary"]
                if row["memory_kind"] == "claim" and row["predicate"]:
                    content = (
                        f"{content}\nClaim: {row['subject_type']} {row['predicate']} "
                        f"{row['object_value']}"
                    )
                evidence_rows = conn.execute(
                    """SELECT evidence.message_id FROM MEMORY_EVIDENCE evidence
                       JOIN MESSAGE source ON source.id = evidence.message_id
                       WHERE evidence.memory_item_id = ?
                         AND (source.speaker = 'user' AND source.status = 'committed'
                              OR source.speaker = 'assistant'
                                 AND source.status IN ('delivery_partial', 'delivered'))
                       ORDER BY source.created_at DESC LIMIT 8""",
                    (row["memory_item_id"],),
                ).fetchall()
                result.append(
                    {
                        "source_kind": "memory_item",
                        "source_ref": row["memory_item_id"],
                        "source_key": f"memory_item:{row['memory_item_id']}",
                        "memory_item_id": row["memory_item_id"],
                        "message_id": None,
                        "speaker": None,
                        "content": content,
                        "status": row["status"],
                        "source_status": row["status"],
                        "source_class": row["memory_kind"],
                        "source_time": row["happened_at"] or row["created_at"],
                        "created_at": row["happened_at"] or row["created_at"],
                        "evidence_refs": [
                            {"source_kind": "raw_message", "source_ref": evidence["message_id"]}
                            for evidence in evidence_rows
                        ],
                        "privacy_class": "local_only",
                        "importance": row["importance"] or 0.0,
                    }
                )
            return result

    def store_embedding(
        self,
        source_kind: str,
        source_ref: str,
        text_hash: str,
        model_id: str,
        embedding: list[float],
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO RETRIEVAL_EMBEDDING_CACHE
                   (source_kind, source_ref, text_hash, model_id, embedding_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (source_kind, source_ref, text_hash, model_id, json.dumps(embedding), now_iso()),
            )

    def load_embeddings(
        self, source_hashes: dict[tuple[str, str], str], model_id: str
    ) -> dict[tuple[str, str], list[float]]:
        if not source_hashes:
            return {}
        with self.db.session() as conn:
            result: dict[tuple[str, str], list[float]] = {}
            for (source_kind, source_ref), text_hash in source_hashes.items():
                row = conn.execute(
                    """SELECT embedding_json FROM RETRIEVAL_EMBEDDING_CACHE
                       WHERE source_kind = ? AND source_ref = ? AND text_hash = ? AND model_id = ?""",
                    (source_kind, source_ref, text_hash, model_id),
                ).fetchone()
                if row:
                    result[(source_kind, source_ref)] = json.loads(row["embedding_json"])
            return result

    def get_run(self, turn_id: str) -> dict[str, Any]:
        with self.db.session() as conn:
            row = conn.execute(
                """SELECT tr.*, cs.id AS cancellation_scope_id
                   FROM TURN_RUN tr JOIN CANCELLATION_SCOPE cs ON cs.turn_run_id = tr.id
                   WHERE tr.id = ?""",
                (turn_id,),
            ).fetchone()
            if not row:
                raise KeyError(f"unknown turn: {turn_id}")
            return dict(row)

    def get_events(self, turn_id: str) -> list[dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT * FROM TURN_EVENT_TRACE WHERE turn_run_id = ? ORDER BY sequence", (turn_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_message(self, message_id: str) -> dict[str, Any] | None:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM MESSAGE WHERE id = ?", (message_id,)).fetchone()
            return dict(row) if row else None

    def save_explicit_command_marker(
        self,
        turn_id: str,
        kind: str,
        explicit: bool,
        target_text: str,
        state_revision: int,
    ) -> dict[str, Any] | None:
        if not explicit:
            return None
        command_id = new_id()
        with self.db.transaction() as conn:
            turn = conn.execute("SELECT id FROM TURN_RUN WHERE id = ?", (turn_id,)).fetchone()
            if not turn:
                raise KeyError(f"unknown turn: {turn_id}")
            event_id = self.emit_event(
                conn,
                turn_id,
                "ExplicitCommandDetected",
                "CMP-ORCH-01",
                "canonical",
                "durable",
                {
                    "schema_version": "explicit-command-v1",
                    "command_id": command_id,
                    "turn_id": turn_id,
                    "kind": kind,
                    "resolution_status": "resolved" if kind == "remember" else "not_found",
                    "target_refs": [],
                    "resolution_basis": "none",
                    "created_state_revision": state_revision,
                    "explicit_remember": kind == "remember",
                    "mutation_applied": False,
                },
            )
        return {
            "event_id": event_id,
            "command_id": command_id,
            "turn_id": turn_id,
            "kind": kind,
            "resolution_status": "resolved" if kind == "remember" else "not_found",
            "target_refs": [],
            "resolution_basis": "none",
            "mutation_applied": False,
        }

    def resolve_and_apply_explicit_forget(
        self, turn_id: str, target_text: str, candidate_limit: int = 500
    ) -> dict[str, Any]:
        """Resolve an explicit forget deterministically and commit marker + deletion atomically."""
        command_id = new_id()
        timestamp = now_iso()
        with self.db.transaction() as conn:
            turn = conn.execute(
                """SELECT tr.id, tr.conversation_id, c.ai_identity_id
                   FROM TURN_RUN tr JOIN CONVERSATION c ON c.id = tr.conversation_id
                   WHERE tr.id = ?""",
                (turn_id,),
            ).fetchone()
            if not turn:
                raise KeyError(f"unknown turn: {turn_id}")
            current_revision = int(
                conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()["value"]
            )
            rows = conn.execute(
                """SELECT mi.id, mi.summary, mi.status, mi.retention_class,
                          mc.subject_type, mc.predicate, mc.object_value
                   FROM MEMORY_ITEM mi
                   LEFT JOIN MEMORY_CLAIM mc ON mc.memory_item_id = mi.id
                   WHERE mi.ai_identity_id = ? AND mi.status <> 'soft_deleted'
                     AND COALESCE(mi.retention_class, '') NOT IN ('secret', 'credential')
                     AND EXISTS (
                       SELECT 1 FROM MEMORY_EVIDENCE me JOIN MESSAGE source ON source.id = me.message_id
                       WHERE me.memory_item_id = mi.id
                         AND (source.speaker = 'user' AND source.status = 'committed'
                              OR source.speaker = 'assistant'
                                 AND source.status IN ('delivery_partial', 'delivered'))
                     )
                   ORDER BY CASE mi.status WHEN 'active' THEN 0 WHEN 'archived' THEN 1 ELSE 2 END,
                            mi.importance DESC, mi.created_at DESC LIMIT ?""",
                (turn["ai_identity_id"], max(1, min(500, candidate_limit))),
            ).fetchall()
            candidates = [dict(row) for row in rows]
            matched_ids, basis = self._resolve_forget_candidates(target_text, candidates)
            if len(matched_ids) == 1:
                resolution_status = "resolved"
                mutation_applied = True
                target_id = matched_ids[0]
                updated = conn.execute(
                    "UPDATE MEMORY_ITEM SET status = 'soft_deleted' WHERE id = ? AND status <> 'soft_deleted'",
                    (target_id,),
                ).rowcount
                if updated != 1:
                    # A concurrent privacy transition wins. Record no successful target and do not retry by guess.
                    resolution_status = "not_found"
                    mutation_applied = False
                    matched_ids = []
                    basis = "none"
                else:
                    conn.execute(
                        """INSERT INTO MEMORY_LIFECYCLE_EVENT
                           (id, memory_item_id, event_type, actor_type, reason_type, reason, created_at)
                           VALUES (?, ?, 'SOFT_DELETED', 'user', 'explicit_forget', 'User requested forget.', ?)""",
                        (new_id(), target_id, timestamp),
                    )
                    current_revision += 1
                    conn.execute("UPDATE APP_META SET value = ? WHERE key = 'state_revision'", (str(current_revision),))
            elif len(matched_ids) > 1:
                resolution_status = "ambiguous"
                mutation_applied = False
                basis = "none"
            else:
                resolution_status = "ambiguous" if candidates and self._is_vague_forget_target(target_text) else "not_found"
                mutation_applied = False
                basis = "none"
            target_refs = [{"source_kind": "memory_item", "source_ref": memory_id} for memory_id in matched_ids] if resolution_status == "resolved" else []
            payload = {
                "schema_version": "explicit-command-v1",
                "command_id": command_id,
                "turn_id": turn_id,
                "kind": "forget",
                "resolution_status": resolution_status,
                "target_refs": target_refs,
                "resolution_basis": basis if resolution_status == "resolved" else "none",
                "created_state_revision": current_revision - (1 if mutation_applied else 0),
                "explicit_remember": False,
                "mutation_applied": mutation_applied,
            }
            event_id = self.emit_event(
                conn,
                turn_id,
                "ExplicitCommandDetected",
                "CMP-ORCH-01",
                "canonical",
                "durable",
                payload,
            )
        return {**payload, "event_id": event_id, "state_revision": current_revision}

    @staticmethod
    def _normalize_forget_text(value: str) -> str:
        return re.sub(r"[\s、。.!！?？:：,，「」『』\"'()（）\[\]{}]", "", value).casefold()

    @classmethod
    def _is_vague_forget_target(cls, target_text: str) -> bool:
        normalized = cls._normalize_forget_text(target_text)
        return normalized in {"", "これ", "それ", "あれ", "この話", "その話", "あの話", "このこと", "そのこと", "あのこと", "this", "that"}

    @classmethod
    def _resolve_forget_candidates(
        cls, target_text: str, candidates: list[dict[str, Any]]
    ) -> tuple[list[str], str]:
        target = cls._normalize_forget_text(target_text)
        if not target or cls._is_vague_forget_target(target_text):
            return [], "none"
        exact: list[str] = []
        for candidate in candidates:
            content = " ".join(
                str(candidate.get(key) or "")
                for key in ("summary", "subject_type", "predicate", "object_value")
            )
            normalized_content = cls._normalize_forget_text(content)
            if target == cls._normalize_forget_text(str(candidate["id"])) or target in normalized_content:
                exact.append(candidate["id"])
        if exact:
            return list(dict.fromkeys(exact)), "explicit_id_or_reference"

        terms = cls._forget_terms(target_text)
        if not terms:
            return [], "none"
        scored: list[tuple[str, float]] = []
        for candidate in candidates:
            content = " ".join(
                str(candidate.get(key) or "")
                for key in ("summary", "subject_type", "predicate", "object_value")
            )
            content_terms = cls._forget_terms(content)
            overlap = terms & content_terms
            if overlap:
                score = len(overlap) / len(terms)
                if cls._normalize_forget_text(target_text) in cls._normalize_forget_text(content):
                    score += 1.0
                scored.append((candidate["id"], score))
        if not scored:
            return [], "none"
        scored.sort(key=lambda value: (-value[1], value[0]))
        top_score = scored[0][1]
        tied = [memory_id for memory_id, score in scored if score == top_score]
        return (tied, "unique_retrieval_match") if len(tied) == 1 else (tied, "none")

    @classmethod
    def _forget_terms(cls, text: str) -> set[str]:
        terms: set[str] = set()
        ignored = {"この", "その", "あの", "これ", "それ", "あれ", "話", "こと", "もの", "this", "that", "the"}
        for match in re.finditer(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u3400-\u9fff]+", text.casefold()):
            token = match.group(0)
            if token in ignored:
                continue
            if re.fullmatch(r"[\u3040-\u30ff\u3400-\u9fff]+", token):
                if len(token) == 1:
                    terms.add(token)
                else:
                    terms.update(token[index : index + 2] for index in range(len(token) - 1))
            elif len(token) > 1:
                terms.add(token)
        return terms

    def turn_trace(self, turn_id: str) -> dict[str, Any]:
        with self.db.session() as conn:
            turn = conn.execute("SELECT * FROM TURN_RUN WHERE id = ?", (turn_id,)).fetchone()
            if not turn:
                raise KeyError(f"unknown turn: {turn_id}")
            attempts = conn.execute("SELECT * FROM COMPONENT_ATTEMPT WHERE turn_run_id = ? ORDER BY started_mono_ns", (turn_id,)).fetchall()
            invocations = conn.execute("SELECT * FROM MODEL_INVOCATION WHERE turn_run_id = ? ORDER BY started_at", (turn_id,)).fetchall()
            retrievals = conn.execute("SELECT * FROM RETRIEVAL_RUN WHERE turn_run_id = ? ORDER BY created_at", (turn_id,)).fetchall()
            contexts = conn.execute("SELECT * FROM CONTEXT_SNAPSHOT WHERE turn_run_id = ? ORDER BY created_at", (turn_id,)).fetchall()
            spans = conn.execute(
                """SELECT ds.*, m.content AS canonical_content FROM DELIVERY_SPAN ds
                   JOIN MESSAGE m ON m.id = ds.assistant_message_id
                   WHERE m.id = (SELECT assistant_message_id FROM TURN_RUN WHERE id = ?)
                   ORDER BY ds.char_start""",
                (turn_id,),
            ).fetchall()
            return {
                "turn": dict(turn),
                "events": self.get_events(turn_id),
                "attempts": [dict(row) for row in attempts],
                "invocations": [dict(row) for row in invocations],
                "retrieval_runs": [dict(row) for row in retrievals],
                "contexts": [dict(row) for row in contexts],
                "delivery_spans": [dict(row) for row in spans],
            }
