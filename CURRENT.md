# Current implementation state

Updated: 2026-09-28 (JST)

## Handoff position

- Repository: https://github.com/hachimitsuneki/AI
- Branch: codex/text-v01-p0 (based on origin/main)
- Base commit: 6c319c71a0aab3dcdefb3bab151fb0a5893485d2
- This branch carries the WP-TXT-01 through WP-TXT-06 implementation, the
  `agent.md` project workflow, and this status document. `AGENTS.md` is the
  Codex auto-discovered entry that directs agents to read `agent.md` in full.
- No commit or push has been made.

## Read order

1. AGENTS.md, then the full project workflow in agent.md
2. PROJECT_HANDOFF.md
3. docs/SPEC_REGISTRY.md
4. docs/canonical/r16/MANIFEST.md, then all 19 parts in manifest order
5. docs/TEXT_V01_IMPLEMENTATION_SPEC.md
6. docs/text_v01/MANIFEST.md, then all 4 parts in manifest order
7. docs/TEXT_V01_READINESS_AUDIT.md
8. docs/ANALYZER_GOLDEN_SPEC.md
9. docs/RETRIEVAL_P0_SPEC.md
10. CODEX_START.md, README.md, then this file

## WP state

| Work package | Implementation | Execution evidence | State |
|---|---|---|---|
| WP-TXT-01 Domain schema / repository contract | SQLite schema contains v0.1 Domain entities and technical trace entities; user-message commit and delivery projection use repository transactions | Schema initializes; PRAGMA foreign_key_check is empty; delivery content update is append-only | Implemented and locally verified |
| WP-TXT-02 Turn / Event / Attempt lifecycle | Turn state transitions, ordered durable event trace, component attempts, cancellation scope, process-restart recovery | Unit tests assert event sequence, cancellation, and interrupted-turn recovery including an in-flight attempt | Implemented and locally verified |
| WP-TXT-03 Retrieval | Cross-conversation same-identity/user message retrieval and provenance-backed memory reads; lexical/semantic rank fusion and degraded outcomes | Unit cases verify hybrid sources, soft-delete exclusion, semantic degradation, and total-unavailable empty snapshot | Implemented and locally verified |
| WP-TXT-04 Context | Frozen ContextCapsuleV1, identity/current-input retention, bounded retrieved/recent context, budget and omission trace | Unit test forces budget trim and confirms the oldest message is omitted while identity and current input remain | Implemented and locally verified |
| WP-TXT-05 Gateway / streaming | Local-only Ollama adapter, normalized streamed deltas and metrics, cancel boundary | Local API found both configured models; real qwen3.5:2b-q4_K_M generated a Japanese response through the browser | Implemented and live-verified |
| WP-TXT-06 Delivery truth | Browser paint-boundary ACK, contiguous append-only DELIVERY_SPAN, canonical assistant content from acknowledged spans only | Browser rendered and ACKed the response spans; trace and persisted assistant MESSAGE match; server restart + browser reload retained both messages | Implemented and live-verified |
| WP-TXT-07 Analyzer | Not started | Not run | Not implemented |
| WP-TXT-08 Validator / Projector | Not started | Not run | Not implemented |
| WP-TXT-09 Inspector | Not started | Not run | Not implemented |
| WP-TXT-10 Golden Harness | Not started | Not run | Not implemented |

## Current vertical-slice boundary

- Input is committed as a canonical user MESSAGE before retrieval/generation.
- Retrieval returns canonical raw conversation and can read existing
  provenance-backed Memory rows. It does not mutate Domain state. Soft-deleted,
  secret, credential, or unprovenanced Memory rows are excluded.
- The runtime profile currently sets local provisional Main/Embedding model
  identifiers, RRF k, context size estimate, result limits, and generation
  limit. These are configurable values, not finalized product choices.
- Explicit remember/forget detection writes a command event without duplicating
  command text into that event. Semantic memory extraction and Domain
  mutation are outside this slice. Forget currently resolves to not_found
  because this runtime exposes no Memory selector or Domain Update Layer; no
  deletion is attempted.
- Provider fallback is not configured in the local runtime profile. A
  generation failure after delivery finalizes the acknowledged prefix as
  completed_partial; no second model appends text.
- agent.md requires commit scoping and remote permissions; those operations
  have not been performed.

## Verification run

Executed:

- Python compile check: python -m compileall -q companion — passed.
- SQLite initialization smoke check — created 43 tables, no FK violations,
  default identity and canonical user-turn commit succeeded.
- JavaScript syntax check: node --check companion/static/app.js — passed.
- python -m unittest discover -s tests -v — 9 tests passed:
  - schema and append-only delivery projection
  - process-restart recovery of partial delivery and running attempts
  - hybrid retrieval with soft-delete exclusion and provenance
  - semantic-only failure with lexical continuation
  - total recall failure with empty unavailable snapshot
  - normal foreground stream and canonical delivery completion
  - provider failure after partial delivery without model swap
- Local /api/health — Ollama and both configured models reported available.
- Browser exercise — sent a Japanese message, received a live model response,
  observed the rendered output, verified all delivery checkpoints and
  completed Turn trace, stopped and restarted the local server, then reloaded
  the same two-message history in the browser.
- A browser automation selector wait timed out; a fresh accessibility tree,
  direct rendered-DOM read, screenshot, and completed persisted Turn trace
  confirmed the response had finished. This was a selector-wait issue, not a
  runtime failure.
- Real Ollama + browser end-to-end rendering, restart readback, explicit
  cancellation, and interrupted-process recovery have been exercised, except
  cancellation used the deterministic fake provider rather than live Ollama.

## Next concrete work

1. Review the live local slice and decide whether to continue.
2. Next work package is WP-TXT-07 Turn Analyzer, followed by WP-TXT-08
   Validator/Projector; keep the remaining long-term capabilities from the
   canonical specifications.
3. Compare and tune the provisional local runtime profile only after collecting
   real conversation/retrieval evidence; its model, budget, and ranking values
   are not final decisions.

No specification conflict requiring a redesign was found in WP-TXT-01 through
WP-TXT-06. Explicit forget mutation remains intentionally outside this
foreground-only boundary; it depends on the later Domain Update Layer.
