# Text v0.1 Local Runtime

This repository contains the local Text v0.1 P0 runtime (WP-TXT-01 through
WP-TXT-08, including Chat Usability). The application uses only the Python
standard library, a local SQLite database, and a local Ollama server.

## Run locally

Requirements: Python 3.11 or later and Ollama running on this machine.

The default runtime profile uses qwen3.5:2b-q4_K_M for dialogue and
nomic-embed-text:latest for embeddings. Override these environment variables
to use another installed local model:

    $env:COMPANION_MAIN_MODEL = "qwen3.5:2b-q4_K_M"
    $env:COMPANION_EMBEDDING_MODEL = "nomic-embed-text:latest"
    python -m companion

Open http://127.0.0.1:8765. The database is created at
data/text-v01.sqlite3. The service binds to loopback by default; remote Ollama
URLs are rejected so this slice does not send conversation context to a remote
host.

The model, embedding, ranking, and context-budget values are provisional
runtime-profile settings. They are not final product decisions. OLLAMA_BASE_URL
may be changed only to another loopback address in this P0 runtime.

## Current slice

- WP-TXT-01: SQLite canonical Domain and runtime trace schema plus
  single-writer conversation/delivery repository methods.
- WP-TXT-02: durable TURN_RUN, ordered TURN_EVENT_TRACE,
  COMPONENT_ATTEMPT, cancellation scope, and interrupted-turn recovery.
- WP-TXT-03: versioned retrieval request/snapshot; raw messages across the
  same AI/user scope and provenance-backed active/archived/superseded memories;
  lexical and semantic legs run concurrently and degrade independently.
- WP-TXT-04: immutable context capsule, mandatory identity/current input,
  bounded retrieved/recent context, budget and omission trace.
- WP-TXT-05: normalized local Ollama adapter with streamed text deltas,
  metrics, cancellation boundary, and one provider attempt per turn.
- WP-TXT-06: the browser acknowledges a text span only after a paint boundary;
  only acknowledged spans are projected into the canonical assistant message.
- WP-TXT-06.5: interruptible chat input, canonical reply/quote references,
  history search and paging, scroll controls, saved drafts, Copy, and safe Markdown.
- WP-TXT-07: asynchronous Turn Analyzer proposes Memory/Self/User/Relationship
  updates from canonical user messages and delivered assistant content.
- WP-TXT-08: Validator/Projector validates references, privacy, and revisions,
  then commits accepted semantic state atomically and idempotently.

Explicit Remember retains a durable command marker and uses Analyzer plus
Validator/Projector for semantic persistence; a foreground acknowledgment alone
does not prove a memory was saved. A uniquely resolved Explicit Forget atomically
soft-deletes the target in the foreground and makes it invisible to subsequent
Recall/Context/Analyzer evidence. Unresolved forget requests never delete anything.

P0 Analyzer and command Golden regression tests are included. Developer Inspector
UI (WP-TXT-09) and a standalone Golden Harness (WP-TXT-10) remain deferred, as do
Voice, multiple chat threads, and Memory Management UI. Real local Ollama
Memory Claim/User Model commit, Recall, correction, and unique Forget have been
verified; live Self/Relationship semantic accuracy remains unverified. See
[`CURRENT.md`](CURRENT.md) for the exact evidence and remaining limits.

## Verify

    python -m unittest discover -s tests -v
    node --check companion/static/app.js

[`PROJECT_HANDOFF.md`](PROJECT_HANDOFF.md) is the top-level handoff entry point.
[`CURRENT.md`](CURRENT.md) records implementation state, evidence, known limits,
and next work. Canonical requirements and long-term capabilities remain in the
source specifications indexed by [`docs/SPEC_REGISTRY.md`](docs/SPEC_REGISTRY.md).
