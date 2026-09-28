from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from threading import Event

from companion.config import load_config
from companion.context_builder import ContextBuilder
from companion.database import Database, new_id, now_iso
from companion.orchestrator import ConversationRuntime, detect_explicit_command
from companion.repositories import RuntimeRepository
from companion.retrieval import Retriever
from companion.analysis import TurnAnalysisService


class LocalFixtureProvider:
    main_model = "fixture"

    def embed(self, inputs: list[str], timeout: float | None = None) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in inputs]

    def stream_chat(self, _messages, _cancel):
        raise AssertionError("the foreground model is not needed for command resolution tests")


class FixtureAnalyzer:
    def __init__(self, proposal: dict):
        self.proposal = proposal
        self.inputs: list[list[dict[str, str]]] = []

    def chat_json(self, messages, _schema, cancel, *, model=None, timeout=None):
        self.inputs.append(messages)
        if cancel.is_set():
            raise AssertionError("unexpected cancellation")
        return self.proposal


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


class ExplicitCommandRuntimeGoldenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = replace(
            load_config(),
            database_path=str(Path(self.temp_dir.name) / "commands.sqlite3"),
            retrieval_candidate_limit=500,
        )
        self.db = Database(self.config.database_path)
        self.db.initialize(self.config)
        self.repo = RuntimeRepository(self.db)
        self.scope = self.repo.default_scope()
        self.provider = LocalFixtureProvider()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def runtime(self) -> ConversationRuntime:
        retriever = Retriever(self.db, self.repo, self.provider, self.config)
        return ConversationRuntime(
            self.db,
            self.repo,
            self.provider,  # type: ignore[arg-type]
            retriever,
            ContextBuilder(self.repo, self.config),
            self.config,
        )

    def add_source_memory(self, summary: str) -> tuple[str, str, str, str]:
        source_turn = self.repo.create_turn(summary)
        timestamp = now_iso()
        assistant_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO MESSAGE
                   (id, conversation_id, speaker, content, channel, status, delivery_offset, created_at)
                   VALUES (?, ?, 'assistant', ?, 'text', 'delivered', ?, ?)""",
                (assistant_id, source_turn["conversation_id"], f"わかった。{summary}だね。", len(f"わかった。{summary}だね。"), timestamp),
            )
            conn.execute("UPDATE TURN_RUN SET assistant_message_id = ? WHERE id = ?", (assistant_id, source_turn["turn_id"]))
        self.repo.finalize_delivery(source_turn["turn_id"], "completed")
        memory_id = new_id()
        user_model_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO MEMORY_ITEM
                   (id, ai_identity_id, memory_kind, summary, importance, status, retention_class, created_at)
                   VALUES (?, ?, 'claim', ?, .7, 'active', 'normal', ?)""",
                (memory_id, self.scope["ai_identity_id"], summary, timestamp),
            )
            conn.execute(
                """INSERT INTO MEMORY_CLAIM
                   (memory_item_id, subject_type, predicate, object_value, confidence, claim_status, valid_from)
                   VALUES (?, 'user', 'likes', ?, .8, 'current', ?)""",
                (memory_id, summary, timestamp),
            )
            conn.execute(
                """INSERT INTO MEMORY_EVIDENCE(id, memory_item_id, message_id, evidence_type, support_weight)
                   VALUES (?, ?, ?, 'direct_statement', .9)""",
                (new_id(), memory_id, source_turn["user_message_id"]),
            )
            conn.execute(
                """INSERT INTO USER_MODEL_ITEM
                   (id, user_profile_id, category, subject, value, confidence, temporal_scope,
                    status, valid_from, updated_at)
                   VALUES (?, ?, 'preference', 'topic', ?, .8, 'persistent', 'active', ?, ?)""",
                (user_model_id, self.scope["user_profile_id"], summary, timestamp, timestamp),
            )
            conn.execute(
                """INSERT INTO USER_MODEL_EVIDENCE(user_model_item_id, memory_claim_id, support_weight)
                   VALUES (?, ?, .9)""",
                (user_model_id, memory_id),
            )
        return memory_id, source_turn["user_message_id"], assistant_id, source_turn["turn_id"]

    def test_cmd_gold_001_unique_forget_is_atomic_and_immediately_invisible(self) -> None:
        summary = "ユーザーは京都が好き"
        memory_id, source_user_id, source_assistant_id, _source_turn_id = self.add_source_memory(summary)
        timestamp = now_iso()
        user_hypothesis_id = new_id()
        self_hypothesis_id = new_id()
        relationship_id = new_id()
        dimension_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO USER_HYPOTHESIS
                   (id, user_profile_id, category, subject, statement, confidence, status, created_at, updated_at)
                   VALUES (?, ?, 'habit', 'travel', 'often discusses Kyoto', .55, 'hypothesis', ?, ?)""",
                (user_hypothesis_id, self.scope["user_profile_id"], timestamp, timestamp),
            )
            conn.execute(
                """INSERT INTO USER_HYPOTHESIS_EVIDENCE(user_hypothesis_id, memory_item_id, polarity, evidence_weight)
                   VALUES (?, ?, 'supports', .5)""",
                (user_hypothesis_id, memory_id),
            )
            observation_id = new_id()
            conn.execute(
                """INSERT INTO SELF_OBSERVATION
                   (id, ai_identity_id, source_message_id, observation_type, subject, description,
                    spontaneity, user_influence, context_key, observed_at)
                   VALUES (?, ?, ?, 'interest_response', 'Kyoto', 'The topic seemed engaging.', .5, .2, '', ?)""",
                (observation_id, self.scope["ai_identity_id"], source_assistant_id, timestamp),
            )
            conn.execute(
                """INSERT INTO SELF_HYPOTHESIS
                   (id, ai_identity_id, category, subject, statement, confidence, status, created_at, updated_at)
                   VALUES (?, ?, 'interest_response', 'Kyoto', 'Shows interest in Kyoto', .4, 'hypothesis', ?, ?)""",
                (self_hypothesis_id, self.scope["ai_identity_id"], timestamp, timestamp),
            )
            conn.execute(
                """INSERT INTO HYPOTHESIS_EVIDENCE
                   (id, self_hypothesis_id, self_observation_id, polarity, evidence_weight, independence_weight, created_at)
                   VALUES (?, ?, ?, 'positive', .5, .5, ?)""",
                (new_id(), self_hypothesis_id, observation_id, timestamp),
            )
            conn.execute(
                """INSERT INTO RELATIONSHIP(id, ai_identity_id, user_profile_id, started_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (relationship_id, self.scope["ai_identity_id"], self.scope["user_profile_id"], timestamp, timestamp),
            )
            conn.execute(
                """INSERT INTO RELATIONSHIP_DIMENSION
                   (id, relationship_id, dimension_type, value, confidence, stability, updated_at)
                   VALUES (?, ?, 'shared_history', .6, .4, .3, ?)""",
                (dimension_id, relationship_id, timestamp),
            )
            signal_id = new_id()
            conn.execute(
                """INSERT INTO RELATIONSHIP_SIGNAL
                   (id, relationship_id, signal_type, strength, reason, observed_at, source_message_id)
                   VALUES (?, ?, 'shared_history_increase', .1, 'Discussed Kyoto', ?, ?)""",
                (signal_id, relationship_id, timestamp, source_user_id),
            )
            conn.execute(
                """INSERT INTO RELATIONSHIP_DIMENSION_EVIDENCE
                   (id, relationship_dimension_id, relationship_signal_id, support_weight)
                   VALUES (?, ?, ?, .5)""",
                (new_id(), dimension_id, signal_id),
            )

        before = self.repo.learned_context(self.scope["ai_identity_id"], self.scope["user_profile_id"])
        self.assertTrue(any(item["id"] == self_hypothesis_id for item in before["learned_self"]))
        self.assertTrue(any(item["id"] == user_hypothesis_id for item in before["user_model"]))
        self.assertEqual(len(before["relationship"]), 1)
        with self.db.session() as conn:
            before_revision = int(conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()[0])

        forget_runtime = self.runtime()
        forget = forget_runtime.begin(f"「{summary}」を忘れて")
        marker = forget.command_marker
        self.assertIsNotNone(marker)
        assert marker is not None
        self.assertEqual(marker["resolution_status"], "resolved")
        self.assertEqual(marker["resolution_basis"], "explicit_id_or_reference")
        self.assertEqual(marker["target_refs"], [{"source_kind": "memory_item", "source_ref": memory_id}])
        self.assertTrue(marker["mutation_applied"])
        with self.db.session() as conn:
            current_revision = int(conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()[0])
            item_status = conn.execute("SELECT status FROM MEMORY_ITEM WHERE id = ?", (memory_id,)).fetchone()[0]
            lifecycle = conn.execute(
                "SELECT event_type, actor_type FROM MEMORY_LIFECYCLE_EVENT WHERE memory_item_id = ?",
                (memory_id,),
            ).fetchone()
            event = conn.execute(
                "SELECT payload FROM TURN_EVENT_TRACE WHERE id = ?", (marker["event_id"],)
            ).fetchone()
        self.assertEqual(current_revision, before_revision + 1)
        self.assertEqual(item_status, "soft_deleted")
        self.assertEqual(tuple(lifecycle), ("SOFT_DELETED", "user"))
        self.assertEqual(json.loads(event["payload"])["turn_id"], forget.turn["turn_id"])
        self.assertEqual(self.repo.learned_context(self.scope["ai_identity_id"], self.scope["user_profile_id"]),
                         {"learned_self": [], "user_model": [], "relationship": []})
        forget_scope = {
            "ai_identity_id": forget.turn["ai_identity_id"],
            "user_profile_id": forget.turn["user_profile_id"],
            "conversation_id": forget.turn["conversation_id"],
        }
        forget_retrieval = forget_runtime.retriever.execute(
            forget.turn,
            self.repo.get_message(forget.turn["user_message_id"])["content"],
            forget.turn["user_message_id"],
            forget_scope,
        )
        forget_capsule = ContextBuilder(self.repo, self.config).build(
            forget.turn, forget_retrieval, marker
        )
        forget_context_text = json.dumps([dict(message) for message in forget_capsule.messages], ensure_ascii=False)
        self.assertNotIn(summary, forget_context_text)
        memory_sources = self.repo.memory_sources(self.scope["ai_identity_id"], 500)
        self.assertNotIn(memory_id, [row["source_ref"] for row in memory_sources])
        raw_sources = self.repo.retrieval_sources(self.scope["ai_identity_id"], self.scope["user_profile_id"], 500)
        self.assertNotIn(source_user_id, [row["source_ref"] for row in raw_sources])
        self.assertNotIn(source_assistant_id, [row["source_ref"] for row in raw_sources])
        visible, _ = self.repo.validate_retrieval_sources(
            [
                {"source_kind": "memory_item", "source_ref": memory_id},
                {"source_kind": "raw_message", "source_ref": source_user_id},
            ],
            before_revision,
        )
        self.assertEqual(visible, [])

        self.repo.finalize_delivery(forget.turn["turn_id"], "failed_before_delivery", "golden_forget")
        followup = self.repo.create_turn("京都のこと、前に何を話した？")
        scope = {
            "ai_identity_id": followup["ai_identity_id"],
            "user_profile_id": followup["user_profile_id"],
            "conversation_id": followup["conversation_id"],
        }
        retrieval = self.runtime().retriever.execute(
            followup,
            self.repo.get_message(followup["user_message_id"])["content"],
            followup["user_message_id"],
            scope,
        )
        self.assertNotIn(memory_id, [result.source_ref for result in retrieval.results])
        capsule = ContextBuilder(self.repo, self.config).build(followup, retrieval)
        capsule_text = json.dumps([dict(message) for message in capsule.messages], ensure_ascii=False)
        self.assertNotIn(summary, capsule_text)
        self.repo.finalize_delivery(followup["turn_id"], "failed_before_delivery", "golden_followup")
        analysis_input = TurnAnalysisService(self.db, self.repo, self.provider, self.config).build_input(followup["turn_id"])
        self.assertNotIn(summary, json.dumps(analysis_input, ensure_ascii=False))
        recent_ids = [message["message_id"] for message in analysis_input["recent_context_messages"]]
        self.assertNotIn(source_user_id, recent_ids)
        self.assertNotIn(source_assistant_id, recent_ids)

    def test_cmd_gold_002_ambiguous_forget_keeps_all_candidates_and_revision(self) -> None:
        first_id, _, _, _ = self.add_source_memory("ユーザーはホラーが好き")
        second_id, _, _, _ = self.add_source_memory("ユーザーはSF映画が好き")
        with self.db.session() as conn:
            before_revision = int(conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()[0])
        session = self.runtime().begin("この話を忘れて")
        marker = session.command_marker
        self.assertIsNotNone(marker)
        assert marker is not None
        self.assertEqual(marker["resolution_status"], "ambiguous")
        self.assertEqual(marker["target_refs"], [])
        self.assertFalse(marker["mutation_applied"])
        with self.db.session() as conn:
            after_revision = int(conn.execute("SELECT value FROM APP_META WHERE key = 'state_revision'").fetchone()[0])
            statuses = conn.execute(
                "SELECT id, status FROM MEMORY_ITEM WHERE id IN (?, ?) ORDER BY id", (first_id, second_id)
            ).fetchall()
        self.assertEqual(after_revision, before_revision)
        self.assertEqual({row["status"] for row in statuses}, {"active"})

    def test_cmd_gold_003_remember_secret_keeps_unique_code_owned_marker_but_saves_no_memory(self) -> None:
        secret = "sk-example-secret-value"
        user_text = f"覚えて。APIキーは {secret}"
        self.assertEqual(detect_explicit_command(user_text), ("remember", f"APIキーは {secret}"))
        output = empty_analysis()
        output["memory_candidates"] = [{
            "candidate_kind": "claim",
            "subject_scope": "user",
            "topic": "API key",
            "summary": f"The API key is {secret}",
            "temporal_scope": "persistent",
            "explicitness": "direct",
            "importance_signal": "critical",
            "relation_to_existing": {"action": "new", "memory_id": None},
            "evidence_message_ids": [],
            "reason": "secret fixture",
        }]
        session = self.runtime().begin(user_text)
        marker = session.command_marker
        self.assertIsNotNone(marker)
        assert marker is not None
        self.assertTrue(marker["command_id"])
        self.assertEqual(marker["resolution_status"], "resolved")
        payload = output["memory_candidates"][0]
        payload["evidence_message_ids"] = [session.turn["user_message_id"]]
        self.repo.finalize_delivery(session.turn["turn_id"], "failed_before_delivery", "golden_remember")
        analyzer = FixtureAnalyzer(output)
        service = TurnAnalysisService(self.db, self.repo, analyzer, self.config)
        result = service.run(session.turn["turn_id"])
        self.assertEqual(result["status"], "committed")
        with self.db.session() as conn:
            memories = conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0]
            analysis = conn.execute("SELECT input_snapshot_json, proposal_json FROM TURN_ANALYSIS").fetchone()
            proposal = conn.execute("SELECT outcome, reason_code, proposal_json FROM ANALYSIS_PROPOSAL").fetchone()
            event_payload = conn.execute(
                "SELECT payload FROM TURN_EVENT_TRACE WHERE id = ?", (marker["event_id"],)
            ).fetchone()[0]
        self.assertEqual(memories, 0)
        self.assertNotIn(secret, analysis["input_snapshot_json"])
        self.assertNotIn(secret, analysis["proposal_json"])
        self.assertNotIn(secret, proposal["proposal_json"])
        self.assertEqual((proposal["outcome"], proposal["reason_code"]), ("rejected", "rejected_secret"))
        self.assertTrue(json.loads(event_payload)["explicit_remember"])

    def test_command_ids_are_unique_code_owned_uuids(self) -> None:
        first_runtime = self.runtime()
        first = first_runtime.begin("覚えて")
        self.assertIsNotNone(first.command_marker)
        first_id = first.command_marker["command_id"]
        self.repo.finalize_delivery(first.turn["turn_id"], "failed_before_delivery", "marker_fixture")
        second_runtime = self.runtime()
        second = second_runtime.begin("忘れて")
        self.assertIsNotNone(second.command_marker)
        second_id = second.command_marker["command_id"]
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(len(first_id), 36)
        self.assertEqual(len(second_id), 36)


if __name__ == "__main__":
    unittest.main()
