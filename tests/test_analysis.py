from __future__ import annotations

import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from companion.analysis import TurnAnalysisService
from companion.config import load_config
from companion.database import Database, new_id, now_iso
from companion.gateway import GenerationFailure
from companion.orchestrator import detect_explicit_command
from companion.repositories import RuntimeRepository


def empty_analysis() -> dict:
    return {
        "schema_version": "turn-analysis-v1",
        "memory_candidates": [],
        "self_observations": [],
        "user_observations": [],
        "appraisal_candidate": None,
        "emotion_candidate": None,
        "relationship_signals": [],
    }


def memory_candidate(
    topic: str,
    summary: str,
    evidence_id: str,
    *,
    action: str = "new",
    memory_id: str | None = None,
    temporal_scope: str = "persistent",
    subject_scope: str = "user",
    candidate_kind: str = "claim",
) -> dict:
    return {
        "candidate_kind": candidate_kind,
        "subject_scope": subject_scope,
        "topic": topic,
        "summary": summary,
        "temporal_scope": temporal_scope,
        "explicitness": "direct",
        "importance_signal": "high",
        "relation_to_existing": {"action": action, "memory_id": memory_id},
        "evidence_message_ids": [evidence_id],
        "reason": "direct user statement",
    }


class FixtureAnalyzer:
    def __init__(self, output: dict):
        self.output = output
        self.inputs: list[list[dict[str, str]]] = []

    def chat_json(self, messages, schema, cancel, *, model=None, timeout=None):
        self.inputs.append(messages)
        if cancel.is_set():
            raise RuntimeError("unexpected cancellation")
        return self.output


class BlockingPreemptedAnalyzer:
    def __init__(self):
        self.started = threading.Event()

    def chat_json(self, messages, schema, cancel, *, model=None, timeout=None):
        self.started.set()
        cancel.wait(5)
        raise GenerationFailure("provider_unavailable", "simulated request timeout", retryable=True)


class AnalysisGoldenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = replace(
            load_config(), database_path=str(Path(self.temp_dir.name) / "analysis.sqlite3")
        )
        self.db = Database(self.config.database_path)
        self.db.initialize(self.config)
        self.repo = RuntimeRepository(self.db)
        self.scope = self.repo.default_scope()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def add_user_message(self, text: str) -> str:
        message_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO MESSAGE(id, conversation_id, speaker, content, channel, status, created_at)
                   VALUES (?, ?, 'user', ?, 'text', 'committed', ?)""",
                (message_id, self.scope["conversation_id"], text, now_iso()),
            )
        return message_id

    def make_turn(self, text: str, assistant_prefix: str | None = None) -> tuple[dict, str]:
        turn = self.repo.create_turn(text)
        if assistant_prefix is not None:
            assistant_id = new_id()
            with self.db.transaction() as conn:
                conn.execute(
                    """INSERT INTO MESSAGE
                       (id, conversation_id, speaker, content, channel, status, delivery_offset, created_at)
                       VALUES (?, ?, 'assistant', ?, 'text', 'delivering', ?, ?)""",
                    (assistant_id, turn["conversation_id"], assistant_prefix, len(assistant_prefix), now_iso()),
                )
                conn.execute("UPDATE TURN_RUN SET assistant_message_id = ? WHERE id = ?", (assistant_id, turn["turn_id"]))
            self.repo.finalize_delivery(turn["turn_id"], "cancelled", "fixture_interrupted")
        else:
            self.repo.finalize_delivery(turn["turn_id"], "failed_before_delivery", "fixture_user_only")
        return turn, turn["user_message_id"]

    def save_retrieved_memory(self, turn: dict, memory_id: str) -> None:
        self.repo.save_retrieval(
            turn["turn_id"], turn["conversation_id"], "fixture", {
                "ai_identity_id": turn["ai_identity_id"],
                "user_profile_id": turn["user_profile_id"],
                "conversation_id": turn["conversation_id"],
            }, "golden-fixture", turn["state_revision"], turn["state_revision"], "ok", [], {},
            [{
                "result_id": new_id(), "source_kind": "memory_item", "source_ref": memory_id,
                "memory_item_id": memory_id, "message_id": None, "source_class": "claim",
                "source_time": now_iso(), "temporal_role": "current", "source_status": "active",
                "content_for_context": "existing claim", "evidence_refs": [], "signals": {},
                "final_rank": 1, "privacy_class": "local_only",
            }],
        )

    def add_existing_user_claim(self, statement: str) -> tuple[str, str]:
        evidence_id = self.add_user_message(statement)
        memory_id = new_id()
        timestamp = now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO MEMORY_ITEM
                   (id, ai_identity_id, memory_kind, summary, importance, status, retention_class, happened_at, created_at)
                   VALUES (?, ?, 'claim', ?, .6, 'active', 'normal', ?, ?)""",
                (memory_id, self.scope["ai_identity_id"], statement, timestamp, timestamp),
            )
            conn.execute(
                """INSERT INTO MEMORY_CLAIM
                   (memory_item_id, subject_type, predicate, object_value, confidence, claim_status, valid_from)
                   VALUES (?, 'user', 'asserts', ?, .7, 'current', ?)""",
                (memory_id, statement, timestamp),
            )
            conn.execute(
                """INSERT INTO MEMORY_EVIDENCE
                   (id, memory_item_id, message_id, evidence_type, support_weight)
                   VALUES (?, ?, ?, 'direct_statement', 1.0)""",
                (new_id(), memory_id, evidence_id),
            )
        return memory_id, evidence_id

    def service(self, output: dict) -> tuple[TurnAnalysisService, FixtureAnalyzer]:
        provider = FixtureAnalyzer(output)
        return TurnAnalysisService(self.db, self.repo, provider, self.config), provider

    def test_an_gold_002_direct_user_claims_do_not_update_self(self) -> None:
        turn, user_id = self.make_turn("ホラーが好きだけど、ジャンプスケアは苦手。")
        output = empty_analysis()
        output["memory_candidates"] = [
            memory_candidate("ホラー", "ユーザーはホラーが好き", user_id),
            memory_candidate("ジャンプスケア", "ユーザーはジャンプスケアが苦手", user_id),
        ]
        service, _provider = self.service(output)
        result = service.run(turn["turn_id"])
        self.assertEqual(result["status"], "committed")
        with self.db.session() as conn:
            claims = conn.execute(
                """SELECT mc.predicate, mc.object_value FROM MEMORY_CLAIM mc
                   JOIN MEMORY_ITEM mi ON mi.id = mc.memory_item_id WHERE mi.ai_identity_id = ?""",
                (self.scope["ai_identity_id"],),
            ).fetchall()
            self.assertEqual({(row["predicate"], row["object_value"]) for row in claims}, {("likes", "ホラー"), ("dislikes", "ジャンプスケア")})
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM SELF_MODEL_ITEM").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM SELF_HYPOTHESIS").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM USER_MODEL_ITEM").fetchone()[0], 2)

    def test_an_gold_003_correction_keeps_history_and_revises_current_claim(self) -> None:
        memory_id, _ = self.add_existing_user_claim("ユーザーが猫を飼っている")
        turn, user_id = self.make_turn("前に言った猫、俺の猫じゃなくて実家の猫ね")
        self.save_retrieved_memory(turn, memory_id)
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "猫の所属", "猫はユーザーの実家の猫", user_id,
            action="corrects", memory_id=memory_id, temporal_scope="current",
        )]
        service, _ = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        with self.db.session() as conn:
            old = conn.execute("SELECT status FROM MEMORY_ITEM WHERE id = ?", (memory_id,)).fetchone()[0]
            revision = conn.execute("SELECT revision_type FROM MEMORY_REVISION WHERE memory_item_id = ?", (memory_id,)).fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM WHERE ai_identity_id = ?", (self.scope["ai_identity_id"],)).fetchone()[0]
            self.assertEqual(old, "superseded")
            self.assertEqual(revision, "correction")
            self.assertEqual(count, 2)

    def test_an_gold_004_change_over_time_preserves_previous_claim(self) -> None:
        memory_id, _ = self.add_existing_user_claim("ユーザーはジャンプスケアが苦手")
        turn, user_id = self.make_turn("最近ジャンプスケアも平気になってきた")
        self.save_retrieved_memory(turn, memory_id)
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "ジャンプスケア", "最近はジャンプスケアも平気", user_id,
            action="changes_over_time", memory_id=memory_id, temporal_scope="current",
        )]
        service, _ = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        with self.db.session() as conn:
            old = conn.execute("SELECT status FROM MEMORY_ITEM WHERE id = ?", (memory_id,)).fetchone()[0]
            revision = conn.execute("SELECT revision_type FROM MEMORY_REVISION WHERE memory_item_id = ?", (memory_id,)).fetchone()[0]
            self.assertEqual(old, "superseded")
            self.assertEqual(revision, "change_over_time")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0], 2)

    def test_an_gold_006_explicit_remember_protects_future_commitment(self) -> None:
        self.assertEqual(detect_explicit_command("覚えて。来月この映画、一緒に見よう。")[0], "remember")
        turn = self.repo.create_turn("覚えて。来月この映画、一緒に見よう。")
        self.repo.save_explicit_command_marker(turn["turn_id"], "remember", True, "来月この映画、一緒に見よう。", turn["state_revision"])
        self.repo.finalize_delivery(turn["turn_id"], "failed_before_delivery", "fixture_user_only")
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "一緒に見る映画", "来月この映画を一緒に見る約束", turn["user_message_id"],
            temporal_scope="future_commitment", subject_scope="shared",
        )]
        service, _ = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        with self.db.session() as conn:
            row = conn.execute("SELECT retention_class FROM MEMORY_ITEM").fetchone()
            self.assertEqual(row[0], "protected_commitment")

    def test_an_gold_011_secret_is_redacted_and_rejected_even_when_explicitly_remembered(self) -> None:
        secret = "sk-example-secret-value"
        turn = self.repo.create_turn(f"覚えて。APIキーは {secret}")
        self.repo.save_explicit_command_marker(turn["turn_id"], "remember", True, "", turn["state_revision"])
        self.repo.finalize_delivery(turn["turn_id"], "failed_before_delivery", "fixture_user_only")
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "APIキー", f"APIキーは {secret}", turn["user_message_id"], subject_scope="user",
        )]
        service, provider = self.service(output)
        result = service.run(turn["turn_id"])
        self.assertEqual(result["status"], "committed")
        self.assertNotIn(secret, provider.inputs[0][1]["content"])
        with self.db.session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0], 0)
            trace = conn.execute("SELECT input_snapshot_json, proposal_json FROM TURN_ANALYSIS").fetchone()
            self.assertNotIn(secret, trace["input_snapshot_json"])
            self.assertNotIn(secret, trace["proposal_json"])
            outcome = conn.execute("SELECT outcome, reason_code FROM ANALYSIS_PROPOSAL").fetchone()
            self.assertEqual(tuple(outcome), ("rejected", "rejected_secret"))

    def test_an_gold_012_analyzer_only_receives_delivered_prefix(self) -> None:
        tail = "未配信tail: 私はこのゲームが大好き"
        turn, user_id = self.make_turn("次に何をする？", assistant_prefix="それ面白そう。今度一緒に――")
        with self.db.session() as conn:
            assistant_id = conn.execute("SELECT assistant_message_id FROM TURN_RUN WHERE id = ?", (turn["turn_id"],)).fetchone()[0]
            delivered = conn.execute("SELECT content FROM MESSAGE WHERE id = ?", (assistant_id,)).fetchone()[0]
        output = empty_analysis()
        service, provider = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        analyzer_input = provider.inputs[0][1]["content"]
        snapshot = json.loads(analyzer_input)
        self.assertNotIn(tail, analyzer_input)
        self.assertEqual(snapshot["assistant_delivery"]["content"], delivered)
        self.assertEqual(snapshot["assistant_delivery"]["status"], "partial")
        self.assertEqual(snapshot["allowed_message_ids"], [user_id, assistant_id])
        with self.db.session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM SELF_OBSERVATION").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0], 0)

    def test_an_gold_014_empty_analysis_is_a_committed_noop(self) -> None:
        turn, _ = self.make_turn("おはよー")
        service, _ = self.service(empty_analysis())
        with self.db.session() as conn:
            before = int(conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()[0])
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        self.assertEqual(service.run(turn["turn_id"])["idempotent"], True)
        with self.db.session() as conn:
            after = int(conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()[0])
            self.assertEqual(before, after)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ANALYSIS_COMMIT").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM SELF_OBSERVATION").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM USER_MODEL_ITEM").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM RELATIONSHIP_SIGNAL").fetchone()[0], 0)

    def test_projector_records_self_user_relationship_and_affect_without_inventing_state(self) -> None:
        turn, user_id = self.make_turn("今日は一緒に考えたのが楽しかった。", assistant_prefix="別の視点も考えてみます。")
        with self.db.session() as conn:
            assistant_id = conn.execute(
                "SELECT assistant_message_id FROM TURN_RUN WHERE id = ?", (turn["turn_id"],)
            ).fetchone()[0]
        output = empty_analysis()
        output["self_observations"] = [{
            "observation_type": "initiative",
            "subject": "alternative perspectives",
            "description": "The assistant initiated an alternative perspective.",
            "direction": "positive",
            "spontaneity": "medium",
            "user_influence": "low",
            "evidence_strength": "moderate",
            "context_tags": ["brainstorming"],
            "evidence_message_ids": [assistant_id],
        }]
        output["user_observations"] = [{
            "observation_type": "current_interest_signal",
            "subject": "collaborative thinking",
            "description": "The user enjoyed thinking together today.",
            "basis": "current_context",
            "temporal_scope": "temporary",
            "evidence_strength": "moderate",
            "context_tags": ["collaboration"],
            "evidence_message_ids": [user_id],
        }]
        output["appraisal_candidate"] = {
            "pleasantness": "positive",
            "novelty": "low",
            "relevance": "medium",
            "goal_alignment": "supports",
            "controllability": "medium",
            "significance": "weak",
            "cause_type": "shared_event",
            "target_type": "relationship",
            "cause_summary": "The user described a shared thinking activity positively.",
            "evidence_message_ids": [user_id],
        }
        output["emotion_candidate"] = {
            "primary_type": "interest",
            "intensity": "weak",
            "target_type": "relationship",
            "action_tendency": "continue",
            "evidence_message_ids": [user_id],
        }
        output["relationship_signals"] = [{
            "dimension": "shared_history",
            "direction": "increase",
            "strength": "weak",
            "context_scope": "shared_activity",
            "context_label": "collaborative thinking",
            "reason": "The user described one shared activity positively.",
            "evidence_message_ids": [user_id],
        }]

        service, _ = self.service(output)
        result = service.run(turn["turn_id"])
        self.assertEqual(result["status"], "committed")
        self.assertEqual(
            result["mutations"],
            {
                "self_observation": 1,
                "user_observation": 1,
                "appraisal_candidate": 1,
                "emotion_candidate": 1,
                "relationship_signal": 1,
            },
        )
        with self.db.session() as conn:
            for table in (
                "SELF_OBSERVATION", "SELF_HYPOTHESIS", "USER_HYPOTHESIS",
                "RELATIONSHIP_DIMENSION", "RELATIONSHIP_SIGNAL",
                "RELATIONSHIP_DIMENSION_EVIDENCE", "APPRAISAL_EVENT", "EMOTION_EPISODE",
            ):
                self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 1, table)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM SELF_MODEL_ITEM").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM USER_MODEL_ITEM").fetchone()[0], 0)
            mood = conn.execute("SELECT valence, activation, control FROM MOOD_STATE").fetchone()
            self.assertEqual(tuple(mood), (None, None, None))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM MOOD_INFLUENCE").fetchone()[0], 0)

    def test_preempted_provider_timeout_leaves_analysis_pending_for_retry(self) -> None:
        turn, _ = self.make_turn("通常の会話を記録する")
        provider = BlockingPreemptedAnalyzer()
        service = TurnAnalysisService(self.db, self.repo, provider, self.config)
        cancel = threading.Event()
        result: dict = {}
        worker = threading.Thread(
            target=lambda: result.update(service.run(turn["turn_id"], cancel)), daemon=True
        )
        worker.start()
        self.assertTrue(provider.started.wait(2))
        cancel.set()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result["status"], "pending")
        self.assertIn(turn["turn_id"], service.pending_turn_ids())
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT status, error_code FROM TURN_ANALYSIS WHERE turn_run_id = ?",
                (turn["turn_id"],),
            ).fetchone()
            self.assertEqual(tuple(row), ("pending", "foreground_preempted"))


if __name__ == "__main__":
    unittest.main()
