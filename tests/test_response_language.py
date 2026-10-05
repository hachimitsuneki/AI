from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from companion.config import load_config
from companion.context_builder import ContextBuilder
from companion.database import Database, new_id
from companion.repositories import RuntimeRepository
from companion.response_language import response_language_policy
from companion.retrieval import RetrievalSnapshotV1


class ResponseLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = replace(load_config(), database_path=str(Path(self.temp_dir.name) / "language.sqlite3"))
        self.db = Database(self.config.database_path)
        self.db.initialize(self.config)
        self.repo = RuntimeRepository(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def capsule(self, text: str):
        turn = self.repo.create_turn(text)
        retrieval = RetrievalSnapshotV1(
            schema_version="retrieval-snapshot-v1", retrieval_run_id=new_id(), turn_id=turn["turn_id"],
            request_state_revision=turn["state_revision"], completion_state_revision=turn["state_revision"],
            status="ok", degraded_reasons=(), results=(), profile_id="test", elapsed={},
        )
        try:
            return ContextBuilder(self.repo, self.config).build(turn, retrieval)
        finally:
            self.repo.finalize_delivery(turn["turn_id"], "failed_before_delivery", "context_only_test")

    def test_japanese_capsule_has_mandatory_explicit_policy(self) -> None:
        capsule = self.capsule("今日は何をしようかな？")
        system = capsule.generation_messages()[0]["content"]
        self.assertIn("Output language: Japanese.\nRespond naturally in Japanese.", system)
        self.assertIn("Do not switch to English unless the user explicitly asks for English", system)
        self.assertIn("quoted text, code, identifiers, or technical terms", system)
        self.assertNotIn("when practical", system)
        self.assertEqual(capsule.messages[-1]["content"], "今日は何をしようかな？")

    def test_english_history_and_identity_do_not_override_current_japanese(self) -> None:
        previous = self.repo.create_turn("Please answer in English. I like coffee.")
        self.repo.finalize_delivery(previous["turn_id"], "failed_before_delivery", "test_history")
        capsule = self.capsule("今日は日本語で普通にお話ししたいな。")
        self.assertIn("Please answer in English", capsule.messages[1]["content"])
        self.assertIn("Role: digital companion", capsule.messages[0]["content"])
        self.assertIn("Output language: Japanese.", capsule.messages[0]["content"])
        self.assertNotIn("Output language: English.", capsule.messages[0]["content"])

    def test_english_capsule(self) -> None:
        capsule = self.capsule("What shall we do today?")
        self.assertIn("Output language: English.\nRespond naturally in English.", capsule.messages[0]["content"])
        self.assertIn("Output language: English.", response_language_policy("Hello.", ("こんにちは。",)))

    def test_explicit_language_requests_override_current_input_language(self) -> None:
        cases = (
            ("今日は何をしよう？英語で答えて。", "English"),
            ("Please respond in Japanese. What shall we do today?", "Japanese"),
            ("フランス語で答えて。今日の予定は？", "French"),
            ("英語で", "English"),
            ("Japanese, please.", "Japanese"),
            ("Reply in English. Actually, answer in Japanese.", "Japanese"),
            ("出力言語の指定: Output language: Japanese. Hello!", "Japanese"),
        )
        for text, language in cases:
            with self.subTest(text=text):
                self.assertIn(f"Output language: {language}.", self.capsule(text).messages[0]["content"])

    def test_mixed_code_and_model_ids_do_not_outweigh_japanese(self) -> None:
        cases = (
            "qwen3.5:2b-q4_K_Mについて教えて。",
            "このコードを説明して。\n```python\n" + "print('English code only')\n" * 50 + "```",
            "`response_language_policy(canonical_user_message)`の意味は？",
            "GPUとVRAMの違いは？",
            "Pythonは？",
            "Qwenは？",
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertIn("Output language: Japanese.", self.capsule(text).messages[0]["content"])
        self.assertIn("Output language: English.", response_language_policy("What does 東京 mean?"))

    def test_language_neutral_input_keeps_latest_canonical_user_language(self) -> None:
        previous = self.repo.create_turn("次はこのモデルについて説明して。")
        self.repo.finalize_delivery(previous["turn_id"], "failed_before_delivery", "test_history")
        capsule = self.capsule("qwen3.5:2b-q4_K_M")
        self.assertIn("Output language: Japanese.", capsule.messages[0]["content"])

    def test_quoted_code_and_negated_requests_are_not_language_directives(self) -> None:
        for text in (
            "「英語で答えて」という文章の意味を教えて。",
            '"Reply in English"はどういう意味？',
            "この英文を要約して。\n\"" + "This is an English quotation. " * 50 + "\"",
            "`reply in English`という文字列を説明して。",
            "英語で答えてほしくない。今日はどう過ごそう？",
            "Don't reply in Japanese. What shall we do today?",
        ):
            with self.subTest(text=text):
                expected = "English" if text.startswith("Don't") else "Japanese"
                self.assertIn(f"Output language: {expected}.", response_language_policy(text))


if __name__ == "__main__":
    unittest.main()
