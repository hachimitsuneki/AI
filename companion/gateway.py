from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from threading import Event
from typing import Any

from .config import RuntimeConfig


class GenerationFailure(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class GenerationCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationDelta:
    text: str
    received_at_mono_ns: int


@dataclass(frozen=True)
class GenerationMetrics:
    input_tokens: int | None
    output_tokens: int | None
    done_reason: str | None
    first_token_mono_ns: int | None
    started_mono_ns: int
    completed_mono_ns: int

    @property
    def ttft_ms(self) -> int | None:
        if self.first_token_mono_ns is None:
            return None
        return int((self.first_token_mono_ns - self.started_mono_ns) / 1_000_000)

    @property
    def duration_ms(self) -> int:
        return int((self.completed_mono_ns - self.started_mono_ns) / 1_000_000)


class OllamaClient:
    """Local provider adapter; only normalized text deltas leave this boundary."""

    def __init__(self, config: RuntimeConfig):
        self.base_url = config.ollama_base_url
        self.timeout = config.request_timeout_seconds
        self.main_model = config.main_model
        self.embedding_model = config.embedding_model
        self.context_budget_tokens = config.context_budget_tokens
        self.max_generation_tokens = config.max_generation_tokens
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _post_json(self, path: str, payload: dict[str, Any], timeout: float | None = None) -> Any:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=timeout or self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise GenerationFailure("provider_http_error", detail or f"Ollama HTTP {exc.code}", retryable=exc.code >= 500) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise GenerationFailure("provider_unavailable", str(exc), retryable=True) from exc

    def health(self) -> dict[str, Any]:
        request = urllib.request.Request(self.base_url + "/api/tags", method="GET")
        try:
            with self._opener.open(request, timeout=min(self.timeout, 3.0)) as response:
                data = json.loads(response.read().decode("utf-8"))
            names = [model.get("name", "") for model in data.get("models", [])]
            return {
                "available": True,
                "main_model_available": self.main_model in names,
                "embedding_model_available": self.embedding_model in names,
                "main_model": self.main_model,
                "embedding_model": self.embedding_model,
            }
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, ValueError):
            return {
                "available": False,
                "main_model_available": False,
                "embedding_model_available": False,
                "main_model": self.main_model,
                "embedding_model": self.embedding_model,
            }

    def embed(self, inputs: list[str]) -> list[list[float]]:
        if not inputs:
            return []
        data = self._post_json(
            "/api/embed",
            {"model": self.embedding_model, "input": inputs, "truncate": True},
        )
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(inputs):
            raise GenerationFailure("invalid_embedding_response", "Ollama returned an invalid embedding batch.")
        return [[float(value) for value in vector] for vector in embeddings]

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        cancel: Event,
    ) -> Iterator[tuple[GenerationDelta, GenerationMetrics | None]]:
        payload = {
            "model": self.main_model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_ctx": self.context_budget_tokens,
                "num_predict": self.max_generation_tokens,
            },
        }
        request = urllib.request.Request(
            self.base_url + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
            method="POST",
        )
        started = time.monotonic_ns()
        first_token: int | None = None
        final: dict[str, Any] = {}
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                for raw_line in response:
                    if cancel.is_set():
                        raise GenerationCancelled("turn cancelled")
                    if not raw_line.strip():
                        continue
                    try:
                        event = json.loads(raw_line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise GenerationFailure("invalid_provider_stream", "Ollama returned malformed JSON.") from exc
                    if event.get("error"):
                        raise GenerationFailure("provider_stream_error", str(event["error"]), retryable=True)
                    message = event.get("message") or {}
                    text = message.get("content")
                    if isinstance(text, str) and text:
                        now = time.monotonic_ns()
                        if first_token is None:
                            first_token = now
                        yield GenerationDelta(text, now), None
                    if event.get("done"):
                        final = event
                        break
        except GenerationCancelled:
            raise
        except GenerationFailure:
            raise
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise GenerationFailure("provider_http_error", detail or f"Ollama HTTP {exc.code}", retryable=exc.code >= 500) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise GenerationFailure("provider_unavailable", str(exc), retryable=True) from exc
        if not final:
            raise GenerationFailure("incomplete_provider_stream", "Ollama stream ended without a completion event.", retryable=True)
        completed = time.monotonic_ns()
        metrics = GenerationMetrics(
            input_tokens=final.get("prompt_eval_count"),
            output_tokens=final.get("eval_count"),
            done_reason=final.get("done_reason"),
            first_token_mono_ns=first_token,
            started_mono_ns=started,
            completed_mono_ns=completed,
        )
        yield GenerationDelta("", completed), metrics
