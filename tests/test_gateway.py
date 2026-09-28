from __future__ import annotations

import json
import unittest
from dataclasses import replace
from threading import Event
from unittest.mock import patch

from companion.config import load_config
from companion.gateway import GenerationFailure, OllamaClient


class FakeResponse:
    def __init__(self, values: list[dict]):
        self.lines = [json.dumps(value).encode("utf-8") + b"\n" for value in values]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __iter__(self):
        return iter(self.lines)


class GatewayThinkingTests(unittest.TestCase):
    def client(self) -> OllamaClient:
        return OllamaClient(replace(load_config(), think=False))

    def test_stream_sends_profile_think_false_and_never_surfaces_thinking_field(self) -> None:
        client = self.client()
        response = FakeResponse([
            {"message": {"role": "assistant", "content": "", "thinking": "PRIVATE THOUGHT"}, "done": False},
            {"message": {"role": "assistant", "content": "Visible answer", "thinking": "PRIVATE THOUGHT"}, "done": False},
            {"message": {"role": "assistant", "content": "", "thinking": "PRIVATE THOUGHT"}, "done": True,
             "prompt_eval_count": 12, "eval_count": 2, "done_reason": "stop"},
        ])
        with patch.object(client._opener, "open", return_value=response) as open_request:
            values = list(client.stream_chat([{"role": "user", "content": "hi"}], Event()))
        payload = json.loads(open_request.call_args.args[0].data.decode("utf-8"))
        visible = [delta.text for delta, metrics in values if delta.text]
        self.assertFalse(payload["think"])
        self.assertEqual(visible, ["Visible answer"])
        self.assertNotIn("PRIVATE THOUGHT", "".join(visible))

    def test_analyzer_uses_content_only_and_never_parses_thinking_as_json(self) -> None:
        client = self.client()
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
        with patch.object(
            client,
            "_post_json",
            return_value={"message": {"content": '{"ok":true}', "thinking": "PRIVATE THOUGHT"}},
        ) as post:
            result = client.chat_json([], schema, Event(), model="thinking-model")
        self.assertEqual(result, {"ok": True})
        self.assertFalse(post.call_args.args[1]["think"])
        with patch.object(
            client,
            "_post_json",
            return_value={"message": {"content": "", "thinking": "PRIVATE THOUGHT"}},
        ):
            with self.assertRaises(GenerationFailure) as caught:
                client.chat_json([], schema, Event())
        self.assertEqual(caught.exception.code, "invalid_analysis_response")
        self.assertNotIn("PRIVATE THOUGHT", str(caught.exception))

    def test_runtime_profile_can_leave_think_at_ollama_default(self) -> None:
        with patch.dict("os.environ", {"COMPANION_THINK": "auto"}):
            self.assertIsNone(load_config().think)
        with patch.dict("os.environ", {"COMPANION_THINK": "high"}):
            self.assertEqual(load_config().think, "high")


if __name__ == "__main__":
    unittest.main()
