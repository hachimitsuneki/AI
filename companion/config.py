from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class RuntimeConfig:
    database_path: str
    host: str
    port: int
    ollama_base_url: str
    main_model: str
    embedding_model: str
    context_budget_tokens: int
    max_generation_tokens: int
    retrieval_max_results: int
    retrieval_candidate_limit: int
    retrieval_rrf_k: int
    request_timeout_seconds: float
    profile_id: str
    identity_name: str
    identity_role: str


def _integer(name: str, default: int, minimum: int = 1) -> int:
    value = int(os.environ.get(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def load_config() -> RuntimeConfig:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("P0 runtime accepts local Ollama only; remote context transmission is not enabled.")
    return RuntimeConfig(
        database_path=os.environ.get("COMPANION_DB_PATH", "data/text-v01.sqlite3"),
        host=os.environ.get("COMPANION_HOST", "127.0.0.1"),
        port=_integer("COMPANION_PORT", 8765),
        ollama_base_url=base_url,
        main_model=os.environ.get("COMPANION_MAIN_MODEL", "qwen3.5:2b-q4_K_M"),
        embedding_model=os.environ.get("COMPANION_EMBEDDING_MODEL", "nomic-embed-text:latest"),
        context_budget_tokens=_integer("COMPANION_CONTEXT_BUDGET_TOKENS", 8192),
        max_generation_tokens=_integer("COMPANION_MAX_GENERATION_TOKENS", 1024),
        retrieval_max_results=_integer("COMPANION_RETRIEVAL_MAX_RESULTS", 12),
        retrieval_candidate_limit=_integer("COMPANION_RETRIEVAL_CANDIDATE_LIMIT", 500),
        retrieval_rrf_k=_integer("COMPANION_RETRIEVAL_RRF_K", 60),
        request_timeout_seconds=float(os.environ.get("COMPANION_REQUEST_TIMEOUT_SECONDS", "180")),
        profile_id=os.environ.get("COMPANION_PROFILE_ID", "local-provisional-v1"),
        identity_name=os.environ.get("COMPANION_IDENTITY_NAME", "AI"),
        identity_role=os.environ.get("COMPANION_IDENTITY_ROLE", "digital companion"),
    )
