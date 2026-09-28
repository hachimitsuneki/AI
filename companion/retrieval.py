from __future__ import annotations

import hashlib
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .config import RuntimeConfig
from .database import Database, new_id
from .gateway import OllamaClient
from .repositories import RuntimeRepository


@dataclass(frozen=True)
class RetrievalRequestV1:
    schema_version: str
    turn_id: str
    query_text: str
    state_revision: int
    scope: Mapping[str, str]
    allowed_source_classes: tuple[str, ...]
    excluded_memory_statuses: tuple[str, ...]
    max_result_count: int
    context_budget_hint: int
    retrieval_profile_id: str


@dataclass(frozen=True)
class RetrievalResultV1:
    result_id: str
    source_kind: str
    source_ref: str
    source_class: str
    source_time: str
    temporal_role: str
    source_status: str
    content_for_context: str
    evidence_refs: tuple[Mapping[str, str], ...]
    signals: Mapping[str, float | int]
    final_rank: int
    privacy_class: str
    message_id: str | None
    memory_item_id: str | None

    def to_record(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "memory_item_id": self.memory_item_id,
            "message_id": self.message_id,
            "source_class": self.source_class,
            "source_time": self.source_time,
            "temporal_role": self.temporal_role,
            "source_status": self.source_status,
            "content_for_context": self.content_for_context,
            "evidence_refs": [dict(ref) for ref in self.evidence_refs],
            "signals": dict(self.signals),
            "final_rank": self.final_rank,
            "privacy_class": self.privacy_class,
        }


@dataclass(frozen=True)
class RetrievalSnapshotV1:
    schema_version: str
    retrieval_run_id: str
    turn_id: str
    request_state_revision: int
    completion_state_revision: int
    status: str
    degraded_reasons: tuple[str, ...]
    results: tuple[RetrievalResultV1, ...]
    profile_id: str
    elapsed: Mapping[str, int]

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "retrieval_run_id": self.retrieval_run_id,
            "turn_id": self.turn_id,
            "request_state_revision": self.request_state_revision,
            "completion_state_revision": self.completion_state_revision,
            "status": self.status,
            "degraded_reasons": list(self.degraded_reasons),
            "results": [result.to_record() for result in self.results],
            "profile_id": self.profile_id,
            "elapsed": dict(self.elapsed),
        }


def _terms(text: str) -> set[str]:
    terms: set[str] = set()
    for match in re.finditer(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u3400-\u9fff]+", text.lower()):
        token = match.group(0)
        if re.fullmatch(r"[\u3040-\u30ff\u3400-\u9fff]+", token):
            if len(token) == 1:
                terms.add(token)
            else:
                terms.update(token[i : i + 2] for i in range(len(token) - 1))
        elif len(token) > 1:
            terms.add(token)
    return terms


def lexical_search(query: str, sources: list[dict[str, Any]]) -> list[tuple[str, float]]:
    query_terms = _terms(query)
    if not query_terms:
        return []
    results: list[tuple[str, float]] = []
    for source in sources:
        body = source["content"].lower()
        source_terms = _terms(body)
        overlap = query_terms.intersection(source_terms)
        score = len(overlap) / len(query_terms)
        if query.strip() and query.strip().lower() in body:
            score += 1.0
        if score > 0:
            results.append((source["source_key"], score))
    return sorted(results, key=lambda item: (-item[1], item[0]))


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return product / (left_norm * right_norm)


class Retriever:
    def __init__(
        self,
        db: Database,
        repository: RuntimeRepository,
        provider: OllamaClient,
        config: RuntimeConfig,
        lexical_fn: Callable[[str, list[dict[str, Any]]], list[tuple[str, float]]] = lexical_search,
    ):
        self.db = db
        self.repository = repository
        self.provider = provider
        self.config = config
        self.lexical_fn = lexical_fn
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="retrieval")

    def execute(
        self,
        turn: dict[str, Any],
        query_text: str,
        exclude_message_id: str,
        scope: dict[str, str],
    ) -> RetrievalSnapshotV1:
        request = RetrievalRequestV1(
            schema_version="retrieval-request-v1",
            turn_id=turn["turn_id"],
            query_text=query_text,
            state_revision=turn["state_revision"],
            scope=scope,
            allowed_source_classes=("memory_item", "raw_message"),
            excluded_memory_statuses=("soft_deleted",),
            max_result_count=self.config.retrieval_max_results,
            context_budget_hint=self.config.context_budget_tokens,
            retrieval_profile_id=f"{self.config.profile_id}/raw-hybrid-rrf-v1",
        )
        started = time.monotonic_ns()
        sources = [
            source
            for source in (
                self.repository.memory_sources(
                    scope["ai_identity_id"], self.config.retrieval_candidate_limit
                )
                + self.repository.retrieval_sources(
                    scope["ai_identity_id"],
                    scope["user_profile_id"],
                    self.config.retrieval_candidate_limit,
                )
            )
            if source.get("message_id") != exclude_message_id
        ]
        leg_started = {"lexical": time.monotonic_ns(), "semantic": time.monotonic_ns()}

        def run_lexical() -> list[tuple[str, float]]:
            return self.lexical_fn(request.query_text, sources)

        def run_semantic() -> list[tuple[str, float]]:
            return self._semantic_search(request.query_text, sources) if sources else []

        lexical_values: list[tuple[str, float]] = []
        semantic_values: list[tuple[str, float]] = []
        lexical_error: str | None = None
        semantic_error: str | None = None
        lexical_future = self._executor.submit(run_lexical)
        semantic_future = self._executor.submit(run_semantic)
        deadline = max(0.001, float(self.config.retrieval_foreground_deadline_seconds))
        # Bound the foreground wait without shutting down a context-managed pool
        # that would otherwise join a timed-out semantic request before returning.
        from concurrent.futures import wait

        wait((lexical_future, semantic_future), timeout=deadline)
        if lexical_future.done():
            try:
                lexical_values = lexical_future.result()
            except Exception:
                lexical_error = "lexical_unavailable"
        else:
            lexical_future.cancel()
            lexical_error = "lexical_timeout"
        if semantic_future.done():
            try:
                semantic_values = semantic_future.result()
            except Exception:
                semantic_error = "semantic_unavailable"
        else:
            semantic_future.cancel()
            semantic_error = "semantic_timeout"
        lexical_elapsed = int((time.monotonic_ns() - leg_started["lexical"]) / 1_000_000)
        semantic_elapsed = int((time.monotonic_ns() - leg_started["semantic"]) / 1_000_000)

        lexical_rank = {source_key: rank for rank, (source_key, _) in enumerate(lexical_values, start=1)}
        lexical_score = {source_key: score for source_key, score in lexical_values}
        semantic_rank = {source_key: rank for rank, (source_key, _) in enumerate(semantic_values, start=1)}
        semantic_score = {source_key: score for source_key, score in semantic_values}
        reasons = [reason for reason in (lexical_error, semantic_error) if reason]
        status = "unavailable" if lexical_error and semantic_error else ("degraded" if reasons else "ok")
        fused: list[tuple[str, float]] = []
        if status != "unavailable":
            for source_key in set(lexical_rank) | set(semantic_rank):
                # Rank fusion is replaceable by profile. This provisional RRF profile has no fixed
                # semantic/lexical score weights or similarity cutoff.
                score = 0.0
                if source_key in lexical_rank:
                    score += 1.0 / (self.config.retrieval_rrf_k + lexical_rank[source_key])
                if source_key in semantic_rank:
                    score += 1.0 / (self.config.retrieval_rrf_k + semantic_rank[source_key])
                fused.append((source_key, score))
        fused.sort(
            key=lambda item: (
                -item[1],
                item[0],
            )
        )
        source_by_key = {source["source_key"]: source for source in sources}
        records: list[RetrievalResultV1] = []
        for rank, (source_key, fusion_score) in enumerate(fused[: request.max_result_count], start=1):
            source = source_by_key.get(source_key)
            if not source:
                continue
            content = source["content"]
            if len(content) > 1200:
                content = content[-1200:]
            source_class = source["source_class"]
            records.append(
                RetrievalResultV1(
                    result_id=new_id(),
                    source_kind=source["source_kind"],
                    source_ref=source["source_ref"],
                    source_class=source_class,
                    source_time=source["source_time"],
                    temporal_role=(
                        "current"
                        if source["source_kind"] == "memory_item" and source["source_status"] == "active"
                        else "historical"
                    ),
                    source_status=source["source_status"],
                    content_for_context=content,
                    evidence_refs=tuple(source["evidence_refs"]),
                    signals={
                        **({"lexical": lexical_score[source_key]} if source_key in lexical_score else {}),
                        **({"lexical_rank": lexical_rank[source_key]} if source_key in lexical_rank else {}),
                        **({"semantic": semantic_score[source_key]} if source_key in semantic_score else {}),
                        **({"semantic_rank": semantic_rank[source_key]} if source_key in semantic_rank else {}),
                        "fusion_rrf": fusion_score,
                    },
                    final_rank=rank,
                    privacy_class=source["privacy_class"],
                    message_id=source.get("message_id"),
                    memory_item_id=source.get("memory_item_id"),
                )
            )
        current_revision = turn["state_revision"]
        request_sources = [
            {"source_kind": result.source_kind, "source_ref": result.source_ref}
            for result in records
        ]
        visible_sources, completion_revision = self.repository.validate_retrieval_sources(
            request_sources, current_revision
        )
        if len(visible_sources) != len(request_sources):
            visible = {(source["source_kind"], source["source_ref"]) for source in visible_sources}
            records = [
                RetrievalResultV1(
                    **{
                        **result.__dict__,
                        "final_rank": rank,
                    }
                )
                for rank, result in enumerate(
                    (
                        result
                        for result in records
                        if (result.source_kind, result.source_ref) in visible
                    ),
                    start=1,
                )
            ]
        elapsed = {
            "lexical_ms": lexical_elapsed,
            "semantic_ms": semantic_elapsed,
            "fusion_ms": 0,
            "total_ms": int((time.monotonic_ns() - started) / 1_000_000),
        }
        profile_id = (
            f"{request.retrieval_profile_id};rrf-k={self.config.retrieval_rrf_k};"
            f"embedding={self.config.embedding_model};foreground-deadline-s={deadline:g}"
        )
        run_id = self.repository.save_retrieval(
            turn_id=turn["turn_id"],
            conversation_id=turn["conversation_id"],
            query_text=request.query_text,
            scope=dict(request.scope),
            profile_id=profile_id,
            request_revision=request.state_revision,
            completion_revision=completion_revision,
            status=status,
            degraded_reasons=reasons,
            elapsed=elapsed,
            results=[result.to_record() for result in records],
        )
        return RetrievalSnapshotV1(
            schema_version="retrieval-snapshot-v1",
            retrieval_run_id=run_id,
            turn_id=request.turn_id,
            request_state_revision=request.state_revision,
            completion_state_revision=completion_revision,
            status=status,
            degraded_reasons=tuple(reasons),
            results=tuple(records),
            profile_id=profile_id,
            elapsed=elapsed,
        )

    def _semantic_search(self, query: str, sources: list[dict[str, Any]]) -> list[tuple[str, float]]:
        bounded = {
            source["source_key"]: source["content"][-4000:]
            for source in sources
        }
        hashes = {
            source_key: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for source_key, text in bounded.items()
        }
        source_refs = {
            source["source_key"]: (source["source_kind"], source["source_ref"])
            for source in sources
        }
        cache_keys = {source_refs[key]: value for key, value in hashes.items()}
        cached_by_ref = self.repository.load_embeddings(cache_keys, self.config.embedding_model)
        cached = {f"{kind}:{ref}": vector for (kind, ref), vector in cached_by_ref.items()}
        missing_keys = [source_key for source_key in bounded if source_key not in cached]
        inputs = [query] + [bounded[source_key] for source_key in missing_keys]
        vectors = self.provider.embed(
            inputs, timeout=self.config.retrieval_foreground_deadline_seconds
        )
        if not vectors:
            return []
        query_vector = vectors[0]
        for source_key, vector in zip(missing_keys, vectors[1:]):
            cached[source_key] = vector
            kind, ref = source_refs[source_key]
            self.repository.store_embedding(
                kind, ref, hashes[source_key], self.config.embedding_model, vector
            )
        scored = [
            (source_key, _cosine(query_vector, vector))
            for source_key, vector in cached.items()
            if source_key in bounded
        ]
        return sorted(scored, key=lambda item: (-item[1], item[0]))
