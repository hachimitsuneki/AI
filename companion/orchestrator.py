from __future__ import annotations

import queue
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Iterator

from .config import RuntimeConfig
from .analysis import TurnAnalysisService
from .context_builder import ContextBuilder, CriticalContextError
from .database import Database
from .gateway import (
    GenerationCancelled,
    GenerationDelta,
    GenerationFailure,
    GenerationMetrics,
    OllamaClient,
)
from .repositories import RuntimeRepository, TERMINAL_STATUSES
from .retrieval import Retriever


MAX_USER_TEXT_CHARS = 20_000


@dataclass
class ActiveTurn:
    turn: dict[str, Any]
    command_marker: dict[str, Any] | None
    cancel: threading.Event = field(default_factory=threading.Event)
    finalized: threading.Event = field(default_factory=threading.Event)
    lock: threading.RLock = field(default_factory=threading.RLock)
    finalize_lock: threading.Lock = field(default_factory=threading.Lock)
    generated_text: str = ""
    acknowledged_offset: int = 0
    generation_finished: bool = False
    requested_terminal_status: str | None = None
    terminal_reason: str | None = None
    terminal_result: dict[str, Any] | None = None
    first_token_seen: bool = False
    invocation_id: str | None = None
    analysis_scheduled: bool = False


def detect_explicit_command(text: str) -> tuple[str, str] | None:
    stripped = text.strip()
    remember_prefix = re.match(
        r"^(?:(?:これ|それ)\s*)?(?:を|は)?\s*(?:覚えておいて|覚えといて|覚えてください|覚えてね|記憶してください|記憶して|覚えて|remember\s+(?:this|that))\s*[、。.!！?？:：-]*\s*(.+)$",
        stripped,
        re.I | re.S,
    )
    if remember_prefix:
        return "remember", remember_prefix.group(1).strip()
    forget_suffix = re.search(
        r"^(?P<target>.*?)(?:のこと)?(?:を|は)?\s*(?:忘れておいて|忘れといて|忘れてください|忘れて|消して|forget\s+(?:this|that))[\s。.!！?？]*$",
        stripped,
        re.I | re.S,
    )
    if forget_suffix:
        target = forget_suffix.group("target").strip()
        return "forget", target
    if re.search(r"(?:覚えておいて|覚えといて|覚えてください|覚えてね|記憶してください|記憶して|覚えて|remember\s+(?:this|that))[\s。.!！?？]*$", stripped, re.I):
        return "remember", ""
    return None


class ConversationRuntime:
    def __init__(
        self,
        db: Database,
        repository: RuntimeRepository,
        provider: OllamaClient,
        retriever: Retriever,
        context_builder: ContextBuilder,
        config: RuntimeConfig,
    ):
        self.db = db
        self.repository = repository
        self.provider = provider
        self.retriever = retriever
        self.context_builder = context_builder
        self.config = config
        self._active: dict[str, ActiveTurn] = {}
        self._active_lock = threading.Lock()
        self._begin_lock = threading.Lock()
        self.analysis = TurnAnalysisService(db, repository, provider, config)
        self._analysis_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="turn-analysis")
        self._analysis_lock = threading.Lock()
        self._analysis_cancel_events: dict[str, threading.Event] = {}
        self._analysis_running: set[str] = set()
        if hasattr(provider, "chat_json"):
            for pending_turn_id in self.analysis.pending_turn_ids():
                self._schedule_analysis_id(pending_turn_id)

    def begin(self, text: str, reply_to_message_id: str | None = None) -> ActiveTurn:
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        text = text.strip()
        if not text:
            raise ValueError("text must not be empty")
        if len(text) > MAX_USER_TEXT_CHARS:
            raise ValueError(f"text must be {MAX_USER_TEXT_CHARS} characters or fewer")
        with self._begin_lock:
            self._preempt_running_analyses()
            with self._active_lock:
                previous = [session for session in self._active.values() if not session.finalized.is_set()]
            for session in previous:
                self._interrupt_for_new_turn(session)
            turn = self.repository.create_turn(text, reply_to_message_id)
            detected = detect_explicit_command(text)
            marker = None
            if detected:
                kind, target_text = detected
                if kind == "forget":
                    marker = self.repository.resolve_and_apply_explicit_forget(
                        turn["turn_id"], target_text, self.config.retrieval_candidate_limit
                    )
                    turn["state_revision"] = marker["state_revision"]
                else:
                    marker = self.repository.save_explicit_command_marker(
                        turn["turn_id"], kind, True, target_text, turn["state_revision"]
                    )
            session = ActiveTurn(turn=turn, command_marker=marker)
            with self._active_lock:
                self._active[turn["turn_id"]] = session
            return session

    def _interrupt_for_new_turn(self, session: ActiveTurn) -> None:
        turn_id = session.turn["turn_id"]
        with session.lock:
            if session.finalized.is_set():
                return
            session.terminal_reason = "superseded_by_new_user_turn"
            session.requested_terminal_status = "cancelled"
            session.cancel.set()
        self.repository.cancel_turn(turn_id, "superseded_by_new_user_turn")
        # Stop accepting delivery first, then atomically freeze the acknowledged prefix.
        self._finalize(session, "cancelled", "superseded_by_new_user_turn")

    def get_active(self, turn_id: str) -> ActiveTurn | None:
        with self._active_lock:
            return self._active.get(turn_id)

    def _remove_active(self, turn_id: str) -> None:
        with self._active_lock:
            self._active.pop(turn_id, None)

    def acknowledge_delivery(self, turn_id: str, offset: int, text: str) -> dict[str, Any]:
        session = self.get_active(turn_id)
        if not session:
            raise KeyError(f"turn is no longer active: {turn_id}")
        if not isinstance(offset, int) or offset < 0 or not isinstance(text, str) or not text:
            raise ValueError("delivery checkpoint requires a non-empty text and non-negative offset")
        with session.lock:
            if session.cancel.is_set() or session.finalized.is_set():
                raise RuntimeError("turn no longer accepts delivery checkpoints")
            end = offset + len(text)
            if end > len(session.generated_text):
                raise ValueError("delivery checkpoint extends beyond generated text")
            if session.generated_text[offset:end] != text:
                raise ValueError("delivery checkpoint does not match the current generation")
            if offset < session.acknowledged_offset:
                if end <= session.acknowledged_offset:
                    return {
                        "offset": session.acknowledged_offset,
                        "duplicate": True,
                    }
                raise ValueError("delivery checkpoint overlaps an acknowledged span")
            if offset != session.acknowledged_offset:
                raise ValueError("delivery checkpoints must be contiguous")
            result = self.repository.append_delivery_checkpoint(
                turn_id,
                session.invocation_id or "",
                offset,
                text,
            )
            session.acknowledged_offset = result["offset"]
            return result

    def finalize_from_client(self, turn_id: str) -> dict[str, Any]:
        session = self.get_active(turn_id)
        if not session:
            with self.db.session() as conn:
                row = conn.execute("SELECT status, assistant_message_id FROM TURN_RUN WHERE id = ?", (turn_id,)).fetchone()
            if not row:
                raise KeyError(f"unknown turn: {turn_id}")
            return {"status": row["status"], "assistant_message_id": row["assistant_message_id"]}
        if not session.generation_finished:
            raise RuntimeError("generation has not reached a delivery finalization point")
        status = session.requested_terminal_status or "completed"
        return self._finalize(session, status, session.terminal_reason)

    def cancel(self, turn_id: str, reason: str = "user_cancelled") -> dict[str, Any]:
        session = self.get_active(turn_id)
        if not session:
            with self.db.session() as conn:
                row = conn.execute("SELECT status FROM TURN_RUN WHERE id = ?", (turn_id,)).fetchone()
            if not row:
                raise KeyError(f"unknown turn: {turn_id}")
            return {"status": row["status"]}
        if session.finalized.is_set():
            return session.terminal_result or {"status": "completed"}
        self.repository.cancel_turn(turn_id, reason)
        session.terminal_reason = reason
        session.requested_terminal_status = "cancelled"
        session.cancel.set()
        if session.generation_finished:
            return self._finalize(session, "cancelled", reason)
        return {"status": "cancelling"}

    def disconnect(self, session: ActiveTurn) -> None:
        if session.finalized.is_set():
            return
        try:
            self.repository.cancel_turn(session.turn["turn_id"], "client_disconnected")
        except Exception:
            pass
        session.terminal_reason = "client_disconnected"
        session.requested_terminal_status = "cancelled"
        session.cancel.set()
        self._finalize(session, "cancelled", "client_disconnected")

    def _finalize(
        self,
        session: ActiveTurn,
        requested_status: str,
        reason: str | None,
    ) -> dict[str, Any]:
        with session.finalize_lock:
            if session.finalized.is_set():
                return session.terminal_result or {}
            with session.lock:
                generated_len = len(session.generated_text)
                acked = session.acknowledged_offset
            status = requested_status
            if status == "completed" and acked != generated_len:
                status = "completed_partial" if acked else "failed_before_delivery"
                reason = reason or "not all generated text had a rendered delivery checkpoint"
            if status == "completed_partial" and acked == 0:
                status = "failed_before_delivery"
            result = self.repository.finalize_delivery(session.turn["turn_id"], status, reason)
            session.terminal_result = result
            session.finalized.set()
            self._schedule_terminal_analysis(session)
            return result

    def _preempt_running_analyses(self) -> None:
        with self._analysis_lock:
            for turn_id in self._analysis_running:
                cancel = self._analysis_cancel_events.get(turn_id)
                if cancel:
                    cancel.set()

    def _schedule_terminal_analysis(self, session: ActiveTurn) -> None:
        if session.analysis_scheduled or not hasattr(self.provider, "chat_json"):
            return
        session.analysis_scheduled = True
        turn_id = session.turn["turn_id"]
        for pending_id in (*self.analysis.pending_turn_ids(), turn_id):
            self._schedule_analysis_id(pending_id)

    def _schedule_analysis_id(self, turn_id: str) -> None:
        if not hasattr(self.provider, "chat_json"):
            return
        with self._analysis_lock:
            existing = self._analysis_cancel_events.get(turn_id)
            if existing is not None and not existing.is_set():
                return
            cancel = threading.Event()
            self._analysis_cancel_events[turn_id] = cancel
        self._analysis_pool.submit(self._run_analysis_after_idle, turn_id, cancel)

    def _run_analysis_after_idle(self, turn_id: str, cancel: threading.Event) -> None:
        try:
            while not cancel.is_set():
                with self._begin_lock:
                    with self._active_lock:
                        foreground_active = any(not session.finalized.is_set() for session in self._active.values())
                    if not foreground_active:
                        with self._analysis_lock:
                            if cancel.is_set():
                                return
                            self._analysis_running.add(turn_id)
                        break
                cancel.wait(.05)
            if not cancel.is_set():
                self.analysis.run(turn_id, cancel)
        except Exception:
            # Analysis is background work; its failure must not affect delivery.
            return
        finally:
            with self._analysis_lock:
                self._analysis_running.discard(turn_id)
                if self._analysis_cancel_events.get(turn_id) is cancel:
                    self._analysis_cancel_events.pop(turn_id, None)

    def _wait_for_finalization(self, session: ActiveTurn) -> dict[str, Any]:
        if session.finalized.wait(15):
            return session.terminal_result or {}
        with session.lock:
            generated_len = len(session.generated_text)
            acked = session.acknowledged_offset
        status = session.requested_terminal_status or "completed"
        if status == "completed" and acked != generated_len:
            status = "completed_partial" if acked else "failed_before_delivery"
        if status == "completed_partial" and acked == 0:
            status = "failed_before_delivery"
        return self._finalize(
            session,
            status,
            session.terminal_reason or "client did not acknowledge turn finalization before timeout",
        )

    def stream(self, session: ActiveTurn) -> Iterator[dict[str, Any]]:
        turn = session.turn
        current_attempt: str | None = None
        current_invocation: str | None = None
        try:
            yield {
                "type": "turn_started",
                "turn_id": turn["turn_id"],
                "user_message_id": turn["user_message_id"],
                "transcript_revision": turn["transcript_revision"],
                "created_at": turn["committed_at"],
            }
            if session.cancel.is_set():
                raise GenerationCancelled("cancelled before retrieval")
            yield {"type": "retrieval_started", "turn_id": turn["turn_id"]}
            current_attempt, _ = self.repository.create_attempt(
                turn["turn_id"], turn["cancellation_scope_id"], "CMP-RETR-01", "retrieve"
            )
            scope = {
                "ai_identity_id": turn["ai_identity_id"],
                "user_profile_id": turn["user_profile_id"],
                "conversation_id": turn["conversation_id"],
            }
            retrieval = self.retriever.execute(
                turn,
                self.repository.get_message(turn["user_message_id"])["content"],
                turn["user_message_id"],
                scope,
            )
            self.repository.finish_attempt(
                current_attempt,
                "succeeded",
                payload={"snapshot_status": retrieval.status, "result_count": len(retrieval.results)},
            )
            current_attempt = None
            yield {
                "type": "retrieval_ready",
                "turn_id": turn["turn_id"],
                "status": retrieval.status,
                "result_count": len(retrieval.results),
                "degraded_reasons": list(retrieval.degraded_reasons),
            }
            if session.cancel.is_set():
                raise GenerationCancelled("cancelled after retrieval")

            current_attempt, _ = self.repository.create_attempt(
                turn["turn_id"], turn["cancellation_scope_id"], "CMP-CTX-01", "build_context"
            )
            try:
                capsule = self.context_builder.build(turn, retrieval, session.command_marker)
            except CriticalContextError as exc:
                self.repository.finish_attempt(
                    current_attempt, "failed", failure_code="critical_context", retryable=False
                )
                current_attempt = None
                result = self._finalize(session, "failed_before_delivery", str(exc))
                yield {"type": "turn_failed", "turn_id": turn["turn_id"], "message": str(exc), **result}
                return
            context_id = self.repository.save_context_snapshot(
                turn["turn_id"], retrieval.retrieval_run_id, capsule.to_record()
            )
            self.repository.finish_attempt(
                current_attempt,
                "succeeded",
                payload={"context_snapshot_id": context_id, "estimated_tokens": capsule.estimated_tokens},
            )
            current_attempt = None
            yield {
                "type": "context_ready",
                "turn_id": turn["turn_id"],
                "context_snapshot_id": context_id,
                "estimated_tokens": capsule.estimated_tokens,
                "token_budget": capsule.token_budget_total,
            }
            if session.cancel.is_set():
                raise GenerationCancelled("cancelled before generation")

            self.repository.set_generating(turn["turn_id"])
            current_attempt, _ = self.repository.create_attempt(
                turn["turn_id"], turn["cancellation_scope_id"], "CMP-GW-01", "dialogue"
            )
            current_invocation = self.repository.create_invocation(
                turn["turn_id"], context_id, current_attempt, self.config.main_model
            )
            session.invocation_id = current_invocation
            event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

            def produce() -> None:
                try:
                    for delta, metrics in self.provider.stream_chat(capsule.generation_messages(), session.cancel):
                        if metrics is not None:
                            event_queue.put(("completed", metrics))
                            return
                        event_queue.put(("delta", delta))
                except GenerationCancelled as exc:
                    event_queue.put(("cancelled", exc))
                except Exception as exc:
                    event_queue.put(("failed", exc))

            producer = threading.Thread(target=produce, name=f"dialogue-{turn['turn_sequence']}", daemon=True)
            producer.start()
            metrics: GenerationMetrics | None = None
            while True:
                if session.cancel.is_set():
                    raise GenerationCancelled(session.terminal_reason or "turn cancelled")
                try:
                    kind, value = event_queue.get(timeout=0.1)
                except queue.Empty:
                    if not producer.is_alive():
                        raise GenerationFailure("provider_stream_ended", "Model stream ended unexpectedly.", retryable=True)
                    continue
                if session.cancel.is_set():
                    raise GenerationCancelled(session.terminal_reason or "turn cancelled")
                if kind == "delta":
                    delta: GenerationDelta = value
                    with session.lock:
                        offset = len(session.generated_text)
                        session.generated_text += delta.text
                    if not session.first_token_seen:
                        session.first_token_seen = True
                        self.repository.mark_first_token(turn["turn_id"], current_invocation)
                        yield {"type": "first_token", "turn_id": turn["turn_id"]}
                    yield {
                        "type": "delta",
                        "turn_id": turn["turn_id"],
                        "offset": offset,
                        "text": delta.text,
                    }
                elif kind == "completed":
                    metrics = value
                    break
                elif kind == "cancelled":
                    raise GenerationCancelled(str(value))
                else:
                    error = value
                    if isinstance(error, Exception):
                        raise error
                    raise GenerationFailure("provider_failure", str(error), retryable=True)

            self.repository.finish_invocation(
                current_invocation,
                "completed",
                input_tokens=metrics.input_tokens if metrics else None,
                output_tokens=metrics.output_tokens if metrics else None,
                ttft_ms=metrics.ttft_ms if metrics else None,
            )
            self.repository.finish_attempt(
                current_attempt,
                "succeeded",
                payload={"duration_ms": metrics.duration_ms if metrics else None},
            )
            current_attempt = None
            current_invocation = None
            session.generation_finished = True
            session.requested_terminal_status = "completed"
            yield {
                "type": "generation_completed",
                "turn_id": turn["turn_id"],
                "generated_char_count": len(session.generated_text),
                "output_tokens": metrics.output_tokens if metrics else None,
                "ttft_ms": metrics.ttft_ms if metrics else None,
                "duration_ms": metrics.duration_ms if metrics else None,
            }
            result = self._wait_for_finalization(session)
            yield {"type": "turn_finalized", "turn_id": turn["turn_id"], **result}
        except GenerationCancelled as exc:
            if current_invocation:
                self.repository.finish_invocation(current_invocation, "cancelled", failure_code="cancelled")
                current_invocation = None
            if current_attempt:
                self.repository.finish_attempt(
                    current_attempt, "cancelled", failure_code="cancelled", retryable=False
                )
                current_attempt = None
            result = self._finalize(session, "cancelled", str(exc))
            yield {"type": "turn_finalized", "turn_id": turn["turn_id"], **result}
        except Exception as exc:
            failure_code = exc.code if isinstance(exc, GenerationFailure) else "runtime_failure"
            if current_invocation:
                try:
                    self.repository.finish_invocation(
                        current_invocation, "failed", failure_code=failure_code
                    )
                except Exception:
                    pass
                current_invocation = None
            if current_attempt:
                try:
                    self.repository.finish_attempt(
                        current_attempt,
                        "failed",
                        failure_code=failure_code,
                        retryable=isinstance(exc, GenerationFailure) and exc.retryable,
                    )
                except Exception:
                    pass
                current_attempt = None
            with session.lock:
                has_delivery = session.acknowledged_offset > 0
            suggested = "completed_partial" if has_delivery else "failed_before_delivery"
            session.generation_finished = True
            session.requested_terminal_status = suggested
            session.terminal_reason = failure_code
            message = str(exc) if str(exc) else failure_code
            yield {
                "type": "generation_failed" if session.first_token_seen else "turn_failed",
                "turn_id": turn["turn_id"],
                "failure_code": failure_code,
                "message": message,
                "delivered_char_count": session.acknowledged_offset,
                "fallback_attempted": False,
            }
            if session.first_token_seen:
                result = self._wait_for_finalization(session)
            else:
                result = self._finalize(session, "failed_before_delivery", failure_code)
            yield {"type": "turn_finalized", "turn_id": turn["turn_id"], **result}
        finally:
            if session.cancel.is_set() and not session.finalized.is_set():
                try:
                    self._finalize(session, "cancelled", session.terminal_reason or "cancelled")
                except Exception:
                    pass
            if session.finalized.is_set():
                self._remove_active(turn["turn_id"])

    def trace(self, turn_id: str) -> dict[str, Any]:
        return self.repository.turn_trace(turn_id)
