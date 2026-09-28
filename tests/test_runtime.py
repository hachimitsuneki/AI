from __future__ import annotations

import hashlib
import math
import sqlite3
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from threading import Event

from companion.config import load_config
from companion.context_builder import ContextBuilder
from companion.database import Database, new_id, now_iso
from companion.gateway import GenerationDelta, GenerationFailure, GenerationMetrics
from companion.orchestrator import ActiveTurn, ConversationRuntime
from companion.repositories import RuntimeRepository
from companion.retrieval import RetrievalSnapshotV1, Retriever, lexical_search


class FakeProvider:
    main_model = "fake-main"

    def __init__(self, failure: Exception | None = None, embeddings_available: bool = True):
        self.failure = failure
        self.embeddings_available = embeddings_available

    def embed(self, inputs: list[str]) -> list[list[float]]:
        if not self.embeddings_available:
            raise RuntimeError("embedding unavailable")
        vectors: list[list[float]] = []
        for text in inputs:
            lower = text.lower()
            vectors.append(
                [
                    1.0 if "京都" in lower else 0.0,
                    1.0 if "コーヒー" in lower or "coffee" in lower else 0.0,
                    1.0 if "札幌" in lower else 0.0,
                    1.0 if "会話" in lower else 0.0,
                    0.1,
                ]
            )
        return vectors

    def stream_chat(self, messages: list[dict[str, str]], cancel: Event):
        started = time.monotonic_ns()
        first = None
        for text in ("こんにちは。", " 会話できます。"):
            if cancel.is_set():
                from companion.gateway import GenerationCancelled

                raise GenerationCancelled("test cancelled")
            now = time.monotonic_ns()
            first = first or now
            yield GenerationDelta(text, now), None
            if self.failure:
                raise self.failure
        completed = time.monotonic_ns()
        yield (
            GenerationDelta("", completed),
            GenerationMetrics(12, 8, "stop", first, started, completed),
        )


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = replace(
            load_config(),
            database_path=str(Path(self.temp_dir.name) / "runtime.sqlite3"),
            context_budget_tokens=8192,
            retrieval_candidate_limit=100,
        )
        self.db = Database(self.config.database_path)
        self.db.initialize(self.config)
        self.repo = RuntimeRepository(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_retriever(self, provider: FakeProvider, lexical_fn=lexical_search) -> Retriever:
        return Retriever(self.db, self.repo, provider, self.config, lexical_fn=lexical_fn)

    def add_old_message(self, conversation_id: str, content: str) -> str:
        message_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO MESSAGE
                   (id, conversation_id, speaker, content, channel, status, created_at)
                   VALUES (?, ?, 'user', ?, 'text', 'committed', ?)""",
                (message_id, conversation_id, content, now_iso()),
            )
        return message_id

    def add_memory(self, identity_id: str, evidence_message_id: str, summary: str, status: str) -> str:
        memory_id = new_id()
        timestamp = now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO MEMORY_ITEM
                   (id, ai_identity_id, memory_kind, summary, importance, status, retention_class,
                    happened_at, created_at)
                   VALUES (?, ?, 'claim', ?, 0.6, ?, 'normal', ?, ?)""",
                (memory_id, identity_id, summary, status, timestamp, timestamp),
            )
            if status != "soft_deleted":
                conn.execute(
                    """INSERT INTO MEMORY_CLAIM
                       (memory_item_id, subject_type, predicate, object_value, confidence, claim_status)
                       VALUES (?, 'user', 'likes', ?, 0.8, 'current')""",
                    (memory_id, summary),
                )
                conn.execute(
                    """INSERT INTO MEMORY_EVIDENCE
                       (id, memory_item_id, message_id, evidence_type, support_weight)
                       VALUES (?, ?, ?, 'direct_statement', 1.0)""",
                    (new_id(), memory_id, evidence_message_id),
                )
            conn.execute("UPDATE APP_META SET value = '1' WHERE key = 'state_revision'")
        return memory_id

    def make_runtime(self, provider: FakeProvider, lexical_fn=lexical_search) -> ConversationRuntime:
        return ConversationRuntime(
            self.db,
            self.repo,
            provider,  # type: ignore[arg-type]
            self.make_retriever(provider, lexical_fn),
            ContextBuilder(self.repo, self.config),
            self.config,
        )

    def test_schema_and_single_writer_delivery_projection(self) -> None:
        with self.db.session() as conn:
            table_count = conn.execute(
                "SELECT COUNT(*) AS n FROM sqlite_master WHERE type = 'table'"
            ).fetchone()["n"]
            self.assertGreaterEqual(table_count, 40)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

        runtime = self.make_runtime(FakeProvider())
        session = runtime.begin("絵文字も含む応答を確認して")
        session.generated_text = "表示された文章🌱未表示の末尾"
        session.invocation_id = new_id()
        # Minimal technical references are created as the normal Gateway/Context path would.
        context_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO CONTEXT_SNAPSHOT
                   (id, turn_run_id, schema_version, state_revision, transcript_revision, input_truth,
                    identity_version, persona_version, privacy_filter_version, token_budget_total,
                    estimated_tokens, sections_json, selected_refs_json, omissions_json, context_json, created_at)
                   VALUES (?, ?, 'context-capsule-v1', 0, 1, 'canonical_user_message',
                           'id-v1', 'p-v1', 'local-only-v1', 8192, 5, '{}', '{}', '[]', '[]', ?)""",
                (context_id, session.turn["turn_id"], now_iso()),
            )
        attempt_id, _ = self.repo.create_attempt(
            session.turn["turn_id"],
            session.turn["cancellation_scope_id"],
            "CMP-GW-01",
            "dialogue",
        )
        session.invocation_id = self.repo.create_invocation(
            session.turn["turn_id"], context_id, attempt_id, "fake-main"
        )
        self.repo.set_generating(session.turn["turn_id"])

        visible = "表示された文章🌱"
        ack = runtime.acknowledge_delivery(session.turn["turn_id"], 0, visible)
        self.assertEqual(ack["offset"], len(visible))
        finalized = self.repo.finalize_delivery(
            session.turn["turn_id"], "completed_partial", "provider failure after a visible prefix"
        )
        self.repo.finish_invocation(session.invocation_id, "failed", failure_code="simulated")
        self.repo.finish_attempt(attempt_id, "failed", failure_code="simulated")
        canonical = self.repo.get_message(finalized["assistant_message_id"])
        self.assertEqual(canonical["content"], visible)
        self.assertEqual(canonical["status"], "delivery_partial")
        self.assertNotIn("未表示の末尾", canonical["content"])
        sources = self.repo.retrieval_sources(
            session.turn["ai_identity_id"], session.turn["user_profile_id"], 50
        )
        assistant_sources = [source for source in sources if source["speaker"] == "assistant"]
        self.assertEqual([source["content"] for source in assistant_sources], [visible])

    def test_retrieval_hybrid_excludes_soft_deleted_and_tracks_provenance(self) -> None:
        scope = self.repo.default_scope()
        evidence = self.add_old_message(scope["conversation_id"], "京都の喫茶店でコーヒーを飲んだ")
        active_memory = self.add_memory(
            scope["ai_identity_id"], evidence, "京都でコーヒーを楽しむ", "active"
        )
        deleted_memory = self.add_memory(
            scope["ai_identity_id"], evidence, "京都の非公開情報", "soft_deleted"
        )
        turn = self.repo.create_turn("京都のコーヒーの話をして")
        provider = FakeProvider()
        snapshot = self.make_retriever(provider).execute(
            turn,
            self.repo.get_message(turn["user_message_id"])["content"],
            turn["user_message_id"],
            {
                "ai_identity_id": turn["ai_identity_id"],
                "user_profile_id": turn["user_profile_id"],
                "conversation_id": turn["conversation_id"],
            },
        )
        memories = [result for result in snapshot.results if result.source_kind == "memory_item"]
        self.assertTrue(any(result.source_ref == active_memory for result in memories))
        self.assertFalse(any(result.source_ref == deleted_memory for result in memories))
        chosen = next(result for result in memories if result.source_ref == active_memory)
        self.assertTrue(chosen.evidence_refs)
        self.assertEqual(chosen.temporal_role, "current")
        self.assertEqual(snapshot.request_state_revision, snapshot.completion_state_revision)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.transaction() as conn:
                conn.execute(
                    "UPDATE MEMORY_ITEM SET status = 'active' WHERE id = ?",
                    (deleted_memory,),
                )

    def test_retrieval_degrades_when_semantic_backend_fails(self) -> None:
        scope = self.repo.default_scope()
        self.add_old_message(scope["conversation_id"], "京都のコーヒーが好きです")
        turn = self.repo.create_turn("京都のコーヒーについて")
        provider = FakeProvider(embeddings_available=False)
        snapshot = self.make_retriever(provider).execute(
            turn,
            self.repo.get_message(turn["user_message_id"])["content"],
            turn["user_message_id"],
            {
                "ai_identity_id": turn["ai_identity_id"],
                "user_profile_id": turn["user_profile_id"],
                "conversation_id": turn["conversation_id"],
            },
        )
        self.assertEqual(snapshot.status, "degraded")
        self.assertIn("semantic_unavailable", snapshot.degraded_reasons)
        self.assertTrue(snapshot.results)
        self.assertTrue(all("lexical" in result.signals for result in snapshot.results))

    def test_total_retrieval_failure_returns_empty_unavailable_snapshot(self) -> None:
        scope = self.repo.default_scope()
        self.add_old_message(scope["conversation_id"], "過去の会話を含める")
        turn = self.repo.create_turn("前に話したことは？")

        def fail_lexical(_query, _sources):
            raise RuntimeError("lexical unavailable")

        provider = FakeProvider(embeddings_available=False)
        snapshot = self.make_retriever(provider, lexical_fn=fail_lexical).execute(
            turn,
            self.repo.get_message(turn["user_message_id"])["content"],
            turn["user_message_id"],
            {
                "ai_identity_id": turn["ai_identity_id"],
                "user_profile_id": turn["user_profile_id"],
                "conversation_id": turn["conversation_id"],
            },
        )
        self.assertEqual(snapshot.status, "unavailable")
        self.assertEqual(snapshot.results, ())
        self.assertEqual(set(snapshot.degraded_reasons), {"lexical_unavailable", "semantic_unavailable"})

    def test_foreground_turn_streams_and_persists_only_rendered_text(self) -> None:
        runtime = self.make_runtime(FakeProvider())
        session = runtime.begin("こんにちは")
        events = []
        for event in runtime.stream(session):
            events.append(event)
            if event["type"] == "delta":
                runtime.acknowledge_delivery(
                    session.turn["turn_id"], event["offset"], event["text"]
                )
            elif event["type"] == "generation_completed":
                runtime.finalize_from_client(session.turn["turn_id"])
        self.assertEqual(events[-1]["type"], "turn_finalized")
        self.assertEqual(events[-1]["status"], "completed")
        trace = runtime.trace(session.turn["turn_id"])
        self.assertEqual(trace["turn"]["status"], "completed")
        self.assertEqual([event["sequence"] for event in trace["events"]], list(range(1, len(trace["events"]) + 1)))
        self.assertEqual({attempt["status"] for attempt in trace["attempts"]}, {"succeeded"})
        self.assertEqual(trace["invocations"][0]["status"], "completed")
        assistant_id = trace["turn"]["assistant_message_id"]
        assistant = self.repo.get_message(assistant_id)
        self.assertEqual(assistant["content"], "こんにちは。 会話できます。")
        self.assertEqual(assistant["status"], "delivered")
        self.assertEqual(sum(span["char_end"] - span["char_start"] for span in trace["delivery_spans"]), len(assistant["content"]))
        self.assertEqual(len(self.repo.history()), 2)

    def test_provider_failure_after_delivery_finalizes_partial_without_swap(self) -> None:
        provider = FakeProvider(GenerationFailure("network_lost", "simulated stream loss"))
        runtime = self.make_runtime(provider)
        session = runtime.begin("途中で失敗する応答の確認")
        events = []
        for event in runtime.stream(session):
            events.append(event)
            if event["type"] == "delta":
                runtime.acknowledge_delivery(
                    session.turn["turn_id"], event["offset"], event["text"]
                )
            elif event["type"] == "generation_failed":
                runtime.finalize_from_client(session.turn["turn_id"])
        failure = next(event for event in events if event["type"] == "generation_failed")
        self.assertFalse(failure["fallback_attempted"])
        self.assertEqual(events[-1]["status"], "completed_partial")
        trace = runtime.trace(session.turn["turn_id"])
        self.assertEqual(len(trace["invocations"]), 1)
        self.assertEqual(trace["invocations"][0]["status"], "failed")
        assistant = self.repo.get_message(trace["turn"]["assistant_message_id"])
        self.assertEqual(assistant["content"], "こんにちは。")
        self.assertNotIn("会話できます。", assistant["content"])

    def test_user_cancel_keeps_only_acknowledged_prefix(self) -> None:
        runtime = self.make_runtime(FakeProvider())
        session = runtime.begin("応答を止めるテスト")
        events = []
        for event in runtime.stream(session):
            events.append(event)
            if event["type"] == "delta":
                runtime.acknowledge_delivery(
                    session.turn["turn_id"], event["offset"], event["text"]
                )
                runtime.cancel(session.turn["turn_id"])
        self.assertEqual(events[-1]["type"], "turn_finalized")
        self.assertEqual(events[-1]["status"], "cancelled")
        trace = runtime.trace(session.turn["turn_id"])
        self.assertEqual(trace["turn"]["status"], "cancelled")
        message = self.repo.get_message(trace["turn"]["assistant_message_id"])
        self.assertEqual(message["content"], "こんにちは。")
        self.assertEqual(message["status"], "delivery_partial")

    def test_process_restart_recovers_partial_delivery_and_attempts(self) -> None:
        turn = self.repo.create_turn("再起動前の入力")
        context_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO CONTEXT_SNAPSHOT
                   (id, turn_run_id, schema_version, state_revision, transcript_revision, input_truth,
                    identity_version, persona_version, privacy_filter_version, token_budget_total,
                    estimated_tokens, sections_json, selected_refs_json, omissions_json, context_json, created_at)
                   VALUES (?, ?, 'context-capsule-v1', 0, 1, 'canonical_user_message',
                           'id-v1', 'p-v1', 'local-only-v1', 8192, 5, '{}', '{}', '[]', '[]', ?)""",
                (context_id, turn["turn_id"], now_iso()),
            )
        attempt_id, _ = self.repo.create_attempt(
            turn["turn_id"], turn["cancellation_scope_id"], "CMP-GW-01", "dialogue"
        )
        invocation_id = self.repo.create_invocation(
            turn["turn_id"], context_id, attempt_id, "fake-main"
        )
        self.repo.set_generating(turn["turn_id"])
        self.repo.append_delivery_checkpoint(
            turn["turn_id"], invocation_id, 0, "保存された途中応答"
        )

        restarted_db = Database(self.config.database_path)
        restarted_db.initialize(self.config)
        restarted_repo = RuntimeRepository(restarted_db)
        trace = restarted_repo.turn_trace(turn["turn_id"])
        self.assertEqual(trace["turn"]["status"], "completed_partial")
        self.assertEqual(trace["invocations"][0]["status"], "cancelled")
        self.assertEqual(trace["attempts"][0]["status"], "cancelled")
        assistant = restarted_repo.get_message(trace["turn"]["assistant_message_id"])
        self.assertEqual(assistant["status"], "delivery_partial")
        self.assertEqual(assistant["content"], "保存された途中応答")

    def test_context_budget_drops_old_history_but_keeps_identity_and_current_input(self) -> None:
        scope = self.repo.default_scope()
        old_id = self.add_old_message(
            scope["conversation_id"], "old " * 50
        )
        latest_id = self.add_old_message(
            scope["conversation_id"], "new " * 50
        )
        turn = self.repo.create_turn("CURRENT INPUT MUST REMAIN")
        retrieval = RetrievalSnapshotV1(
            schema_version="retrieval-snapshot-v1",
            retrieval_run_id=new_id(),
            turn_id=turn["turn_id"],
            request_state_revision=0,
            completion_state_revision=0,
            status="ok",
            degraded_reasons=(),
            results=(),
            profile_id="test",
            elapsed={},
        )
        builder = ContextBuilder(
            self.repo, replace(self.config, context_budget_tokens=650)
        )
        capsule = builder.build(turn, retrieval)
        self.assertLessEqual(capsule.estimated_tokens, 650)
        self.assertEqual(capsule.messages[-1]["content"], "CURRENT INPUT MUST REMAIN")
        self.assertIn(scope["ai_identity_id"], capsule.selected_refs["ai_identity_ids"])
        self.assertIn(latest_id, capsule.selected_refs["recent_message_ids"])
        self.assertNotIn(old_id, capsule.selected_refs["recent_message_ids"])
        self.assertTrue(any(item["ref"] == old_id for item in capsule.omissions))
        with self.assertRaises(TypeError):
            capsule.messages[-1]["content"] = "modified"


if __name__ == "__main__":
    unittest.main()
