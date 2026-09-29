from __future__ import annotations

import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from companion.analysis import TurnAnalysisService, analysis_json_schema
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


def relation_schema_variants(schema: dict) -> list[dict]:
    memory = schema["properties"]["memory_candidates"]["items"]["properties"]
    relation = memory["relation_to_existing"]
    return relation.get("anyOf", [relation])


class FixtureAnalyzer:
    def __init__(self, output: dict):
        self.output = output
        self.inputs: list[list[dict[str, str]]] = []
        self.schemas: list[dict] = []

    def chat_json(self, messages, schema, cancel, *, model=None, timeout=None):
        self.inputs.append(messages)
        self.schemas.append(schema)
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
            user_model_id = new_id()
            conn.execute(
                """INSERT INTO USER_MODEL_ITEM
                   (id, user_profile_id, category, subject, value, confidence, temporal_scope,
                    status, valid_from, updated_at)
                   VALUES (?, ?, 'fact', ?, ?, .7, 'persistent', 'active', ?, ?)""",
                (user_model_id, self.scope["user_profile_id"], "猫", statement, timestamp, timestamp),
            )
            conn.execute(
                """INSERT INTO USER_MODEL_EVIDENCE(user_model_item_id, memory_claim_id, support_weight)
                   VALUES (?, ?, .75)""",
                (user_model_id, memory_id),
            )
        return memory_id, evidence_id

    def service(self, output: dict) -> tuple[TurnAnalysisService, FixtureAnalyzer]:
        provider = FixtureAnalyzer(output)
        return TurnAnalysisService(self.db, self.repo, provider, self.config), provider

    def test_analyzer_schema_separates_canonical_message_and_memory_ids(self) -> None:
        message_id = "11111111-1111-4111-8111-111111111111"
        assistant_id = "22222222-2222-4222-8222-222222222222"
        memory_id = "33333333-3333-4333-8333-333333333333"
        schema = analysis_json_schema([message_id, assistant_id], [memory_id])
        memory = schema["properties"]["memory_candidates"]["items"]["properties"]
        evidence_ids = memory["evidence_message_ids"]["items"]["enum"]
        relation_variants = relation_schema_variants(schema)
        self.assertEqual(evidence_ids, [message_id, assistant_id])
        self.assertEqual(relation_variants[0]["properties"]["action"]["enum"], ["new", "uncertain"])
        self.assertEqual(relation_variants[0]["properties"]["memory_id"]["enum"], [None])
        self.assertEqual(
            relation_variants[1]["properties"]["memory_id"]["enum"], [memory_id]
        )
        self.assertEqual(
            set(relation_variants[1]["properties"]["action"]["enum"]),
            {"duplicate", "supports", "contradicts", "corrects", "changes_over_time", "clarifies"},
        )
        self.assertNotIn(message_id, relation_variants[1]["properties"]["memory_id"]["enum"])
        self.assertNotIn(memory_id, evidence_ids)

        empty_schema = analysis_json_schema([], [])
        empty_memory = empty_schema["properties"]["memory_candidates"]["items"]["properties"]
        empty_relation = relation_schema_variants(empty_schema)[0]["properties"]
        self.assertEqual(
            empty_relation["action"]["enum"], ["new", "uncertain"]
        )
        self.assertEqual(
            empty_relation["memory_id"]["enum"], [None]
        )
        self.assertEqual(
            empty_memory["evidence_message_ids"]["items"]["enum"], ["__NO_ALLOWED_MESSAGE_ID__"]
        )

    def test_an_gold_002_direct_user_claims_do_not_update_self(self) -> None:
        turn, user_id = self.make_turn("ホラーが好きだけど、ジャンプスケアは苦手。")
        output = empty_analysis()
        output["memory_candidates"] = [
            memory_candidate("ホラー", "ユーザーはホラーが好き", user_id),
            memory_candidate("ジャンプスケア", "ユーザーはジャンプスケアが苦手", user_id),
        ]
        service, provider = self.service(output)
        result = service.run(turn["turn_id"])
        self.assertEqual(result["status"], "committed")
        memory_schema = provider.schemas[0]["properties"]["memory_candidates"]["items"]["properties"]
        relation = relation_schema_variants(provider.schemas[0])[0]["properties"]
        self.assertEqual(relation["action"]["enum"], ["new", "uncertain"])
        self.assertEqual(relation["memory_id"]["enum"], [None])
        self.assertEqual(
            memory_schema["evidence_message_ids"]["items"]["enum"], [user_id]
        )
        self.assertIn("it is never a Message ID", provider.inputs[0][0]["content"])
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

    def test_direct_user_fact_misclassified_as_episode_is_rejected(self) -> None:
        turn, user_id = self.make_turn("私は青色が好きです。")
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "青色", "ユーザーは青色が好き", user_id,
            candidate_kind="episode", subject_scope="user",
        )]
        service, _provider = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        with self.db.session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM USER_MODEL_ITEM").fetchone()[0], 0)
            proposal = conn.execute(
                "SELECT outcome, reason_code FROM ANALYSIS_PROPOSAL WHERE proposal_type = 'memory_candidate'"
            ).fetchone()
        self.assertEqual(tuple(proposal), ("rejected", "direct_user_fact_requires_claim"))

    def test_direct_user_claim_rejects_duplicate_user_hypothesis(self) -> None:
        turn, user_id = self.make_turn("My favorite color is cobalt.")
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "favorite_color", "User's favorite color is cobalt.", user_id,
        )]
        output["user_observations"] = [{
            "observation_type": "preference_signal",
            "subject": "favorite_color",
            "description": "User states a preference for cobalt.",
            "basis": "current_context",
            "temporal_scope": "persistent",
            "evidence_strength": "strong",
            "context_tags": [],
            "evidence_message_ids": [user_id],
        }]
        service, _provider = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        with self.db.session() as conn:
            memory_count = conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0]
            user_model_count = conn.execute("SELECT COUNT(*) FROM USER_MODEL_ITEM").fetchone()[0]
            hypothesis_count = conn.execute("SELECT COUNT(*) FROM USER_HYPOTHESIS").fetchone()[0]
            decision = conn.execute(
                "SELECT outcome, reason_code FROM ANALYSIS_PROPOSAL WHERE proposal_type = 'user_observation'"
            ).fetchone()
        self.assertEqual((memory_count, user_model_count, hypothesis_count), (1, 1, 0))
        self.assertEqual(tuple(decision), ("rejected", "direct_claim_covers_user_observation"))

    def test_delayed_analysis_recent_context_excludes_future_turns(self) -> None:
        _prior, prior_id = self.make_turn("事前の話です。")
        target_turn, _target_id = self.make_turn("このターンを分析してください。")
        _future, future_id = self.make_turn("これは後から来た訂正です。")
        with self.db.transaction() as conn:
            conn.execute("UPDATE MESSAGE SET created_at = '2020-01-01T00:00:00.000+00:00' WHERE id = ?", (prior_id,))
            conn.execute(
                "UPDATE MESSAGE SET created_at = '2020-01-02T00:00:00.000+00:00' WHERE id = ?",
                (target_turn["user_message_id"],),
            )
            conn.execute("UPDATE MESSAGE SET created_at = '2020-01-03T00:00:00.000+00:00' WHERE id = ?", (future_id,))
        service, _provider = self.service(empty_analysis())
        snapshot = service.build_input(target_turn["turn_id"])
        recent_ids = [item["message_id"] for item in snapshot["recent_context_messages"]]
        self.assertIn(prior_id, recent_ids)
        self.assertNotIn(future_id, recent_ids)

    def test_an_gold_003_correction_keeps_history_and_revises_current_claim(self) -> None:
        memory_id, _ = self.add_existing_user_claim("ユーザーが猫を飼っている")
        turn, user_id = self.make_turn("前に言った猫、俺の猫じゃなくて実家の猫ね")
        self.save_retrieved_memory(turn, memory_id)
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "猫の所属", "猫はユーザーの実家の猫", user_id,
            action="corrects", memory_id=memory_id, temporal_scope="current",
        )]
        service, provider = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        memory_schema = provider.schemas[0]["properties"]["memory_candidates"]["items"]["properties"]
        relation_variants = relation_schema_variants(provider.schemas[0])
        self.assertEqual(
            relation_variants[1]["properties"]["memory_id"]["enum"], [memory_id]
        )
        input_snapshot = json.loads(provider.inputs[0][1]["content"])
        self.assertEqual(
            memory_schema["evidence_message_ids"]["items"]["enum"],
            input_snapshot["allowed_message_ids"],
        )
        self.assertIn(user_id, input_snapshot["allowed_message_ids"])
        self.assertNotIn(memory_id, input_snapshot["allowed_message_ids"])
        with self.db.session() as conn:
            old = conn.execute("SELECT status FROM MEMORY_ITEM WHERE id = ?", (memory_id,)).fetchone()[0]
            revision = conn.execute("SELECT revision_type FROM MEMORY_REVISION WHERE memory_item_id = ?", (memory_id,)).fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM WHERE ai_identity_id = ?", (self.scope["ai_identity_id"],)).fetchone()[0]
            user_models = conn.execute(
                "SELECT value, status FROM USER_MODEL_ITEM WHERE user_profile_id = ? ORDER BY valid_from",
                (self.scope["user_profile_id"],),
            ).fetchall()
            current_user_models = [row["value"] for row in user_models if row["status"] in {"active", "current", "confirmed"}]
            context_user_models = self.repo.learned_context(
                self.scope["ai_identity_id"], self.scope["user_profile_id"]
            )["user_model"]
            self.assertEqual(old, "superseded")
            self.assertEqual(revision, "correction")
            self.assertEqual(count, 2)
            self.assertEqual(sum(row["status"] == "superseded" for row in user_models), 1)
            self.assertEqual(len(current_user_models), 1)
            self.assertEqual(len(context_user_models), 1)
            self.assertEqual(context_user_models[0]["value"], "猫はユーザーの実家の猫")

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
            models = conn.execute(
                "SELECT value, status FROM USER_MODEL_ITEM ORDER BY valid_from"
            ).fetchall()
            self.assertEqual(old, "superseded")
            self.assertEqual(revision, "change_over_time")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM MEMORY_ITEM").fetchone()[0], 2)
            self.assertEqual(sum(row["status"] == "superseded" for row in models), 1)
            context_models = self.repo.learned_context(
                self.scope["ai_identity_id"], self.scope["user_profile_id"]
            )["user_model"]
            self.assertEqual([row["value"] for row in context_models], ["最近はジャンプスケアも平気"])

    def test_contradiction_is_counterevidence_and_does_not_supersede_current_user_claim(self) -> None:
        memory_id, _ = self.add_existing_user_claim("ユーザーは猫が好き")
        turn, user_id = self.make_turn("実は猫が好きではない")
        self.save_retrieved_memory(turn, memory_id)
        output = empty_analysis()
        output["memory_candidates"] = [memory_candidate(
            "猫", "ユーザーは猫が好きではない", user_id,
            action="contradicts", memory_id=memory_id,
        )]
        service, _ = self.service(output)
        self.assertEqual(service.run(turn["turn_id"])["status"], "committed")
        with self.db.session() as conn:
            item = conn.execute("SELECT status FROM MEMORY_ITEM WHERE id = ?", (memory_id,)).fetchone()[0]
            claim = conn.execute("SELECT claim_status FROM MEMORY_CLAIM WHERE memory_item_id = ?", (memory_id,)).fetchone()[0]
            counter = conn.execute(
                "SELECT message_id, evidence_type FROM MEMORY_EVIDENCE WHERE memory_item_id = ? AND evidence_type = 'counterevidence'",
                (memory_id,),
            ).fetchone()
            models = conn.execute("SELECT value, status FROM USER_MODEL_ITEM").fetchall()
        self.assertEqual((item, claim), ("active", "current"))
        self.assertIsNotNone(counter)
        self.assertEqual(counter["message_id"], user_id)
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["status"], "active")

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
