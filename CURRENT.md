# Current implementation state

Updated: 2026-09-29 (JST)

## Handoff position

- Repository: https://github.com/hachimitsuneki/AI
- Target branch: `codex/text-v01-p0`
- Prior task baseline: `e46228d1021296eae8e3a7734769326a1e0cd5db` (`Implement Text v0.1 foreground conversation slice`)
- Prior implementation commit: `3c74754` (`Implement chat usability and semantic projection`).
- Baseline before this P0 hardening: `ced97c9c32d3442063e4323e4bec7fc48efc9cfa`.
- P0 hardening implementation commit: `a8ed997` (`Harden Text v0.1 P0 memory handling`). This progress record is committed in the following documentation-only commit.
- Uncommitted changes after the handoff documentation commit: none.
- Scope in this task: WP-TXT-01〜08 P0 hardening after the prior WP-TXT-06.5 and WP-TXT-07/08 implementation.
- `PROJECT_HANDOFF.md` remains the top-level handoff entry point. This file holds the current status and verification evidence.
- Read order: `AGENTS.md`, `agent.md`, `PROJECT_HANDOFF.md`, `docs/SPEC_REGISTRY.md`, `docs/canonical/r16/MANIFEST.md` and all parts in manifest order, `docs/TEXT_V01_IMPLEMENTATION_SPEC.md` and its four parts, `docs/TEXT_V01_READINESS_AUDIT.md`, `docs/ANALYZER_GOLDEN_SPEC.md`, `docs/RETRIEVAL_P0_SPEC.md`, then `CURRENT.md`.

## Work package state

| Work package | Implementation | Verification | State |
|---|---|---|---|
| WP-TXT-01 Domain schema / repository contract | SQLite Domain and technical trace schema; canonical messages and delivery projection | Schema initialization, foreign-key check, repository tests | Implemented and locally verified |
| WP-TXT-02 Turn / Event / Attempt lifecycle | Ordered turn trace, attempts, cancellation, restart recovery | Automated lifecycle, cancellation, restart tests | Implemented and locally verified |
| WP-TXT-03 Retrieval | Lexical/semantic hybrid candidates, provenance, soft-delete and privacy filtering | Automated hybrid, degraded, empty/unavailable, timeout cases | Implemented and locally verified |
| WP-TXT-04 Context Builder | Frozen, budgeted `ContextCapsuleV1`; identity, state, learned sections, history, retrieval | Budget and empty/known learned-state tests | Implemented and locally verified |
| WP-TXT-05 Gateway / streaming | Local Ollama adapter, streaming, structured Analyzer request | Local model health and a completed browser response; later calls below did not all complete | Implemented; live behavior has a provider limitation recorded below |
| WP-TXT-06 Delivery truth | Browser paint ACK, contiguous append-only delivery spans, canonical delivered prefix | Browser response and database delivery trace; restart/readback from earlier slice | Implemented and live-verified |
| WP-TXT-06.5 Chat Usability | Interruptible composer, canonical replies, search, staged history, date separators, scroll control, draft, Copy, safe Markdown, user-facing identity | 33 automated tests total and isolated localhost UI exercise; feature matrix below records the specific evidence and gaps | Implemented; mostly live-verified |
| WP-TXT-07 Turn Analyzer | Structured semantic proposals over canonical delivered evidence; async, retryable, secret-filtered; delayed analysis excludes future turns | Seven P0 Analyzer Goldens and future-turn exclusion regression; local model produced unusable/rejected proposals and timed out | Implemented; live semantic behavior is not reliable or verified |
| WP-TXT-08 Validator / Projector | Reference and privacy validation, stale-revision fail-close, atomic Domain projections, idempotent commits; correction supersedes linked User Model; contradiction remains counterevidence | P0 Analyzer Goldens for correction/change-over-time and contradiction, persisted commit/no-op, and cross-domain projection checks | Implemented; fixture-backed behavior verified; real semantic projection remains unverified |
| WP-TXT-09 Developer Inspector | Not started | Not run | Not implemented |
| WP-TXT-10 Golden Harness | Existing P0 fixture tests only; no standalone harness UI/package | Tests are run with unittest | Not implemented as a separate work package |

## WP-TXT-06.5 feature evidence

| Feature | Implemented | Live-verified | Unverified / limit |
|---|---|---|---|
| Keep composer active; new submit interrupts current turn | Yes. Stop accepting old delivery ACKs, finalize only the acknowledged prefix, and start the new turn. | Yes. Local browser accepted a second prompt while the first generated; DB showed the prior turn `cancelled` and no assistant message because no prefix had been delivered. | The live interruption did not occur after a non-empty prefix. Prefix-only persistence and exclusion of the undelivered tail are verified by `test_new_submit_interrupts_and_canonicalizes_only_acknowledged_prefix` and AN-GOLD-012. |
| Reply/quote with canonical target ID | Yes. `reply_to_message_id` is validated and stored; rendered quote links to the source. | Yes. Quote preview and sent quote appeared in UI; isolated DB read showed the reply ID points to the source canonical message. | Cross-conversation/noncanonical rejection is automated, not browser-exercised. |
| Search conversation history | Yes. Canonical history search and jump-to-message. | Yes. A Japanese query returned the intended message and navigating to it showed the latest-message control. | Very large result sets are covered by repository/API limits, not load-tested. |
| Staged old-history loading | Yes. Keyset pagination, canonical-only pages, and around-message loading. | Not yet in the browser: the isolated conversation did not exceed one page. | UI “load older” control across multiple pages remains unverified in a browser. Repository pagination test passes. |
| Date separator | Yes. Local-day separator is rendered between dates. | Yes. The conversation displayed a Japanese date separator. | Multiple-day ordering and timezone-boundary behavior are not separately exercised. |
| Latest-scroll and suppression while reading older messages | Yes. Auto-follow only while near latest; an explicit latest control is shown away from latest. | Yes. Jumping to a searched message exposed the latest control; clicking it returned to the newest message. | Long streaming while scrolled far into a multi-page history was not live-tested. |
| Draft persistence | Yes. Draft is kept in local storage per conversation. | Yes. A draft survived page reload; the test draft was then cleared. | Browser storage eviction/private browsing behavior is not covered. |
| Message action: Copy only | Yes. Copy is available; success notification confirms clipboard write. No successful-message edit/delete/regenerate actions were added. | Yes. Copy action displayed “メッセージをコピーしました。” | Clipboard denial path is code-handled, not live-tested. |
| Safe Markdown | Yes. Allowlisted Markdown subset creates DOM nodes; raw HTML is text; links are limited to HTTP(S) and safe relative targets. | Yes. Bold rendered as bold; a `javascript:` link and raw `<img ...>` markup remained visible text, with no image rendered. | Other browser engines and broader hostile-input fuzzing are not covered. |
| Hide model/runtime development info in normal Chat | Yes. Bootstrap/UI omit provider and model details. | Yes. Normal Chat header showed identity and “ローカル会話” only. | Inspector remains deferred to WP-TXT-09. |
| Initial identity / temperament | Yes. New identities and the unchanged generic default receive the agreed curious/playful/medium-assertive/slightly-mischievous, occasional-humor profile. Existing customized identity data is preserved. | Database initialization and migrations are exercised; one ordinary local response completed. | A few responses cannot establish long-term behavioral consistency. No model tuning was attempted. |
| Context Builder learned read sections | Yes. Learned Self, User Model (including clearly marked hypotheses), and Relationship are read; empty means empty. | Builder/repository regression verifies empty sections and a known User Hypothesis without promotion to a confirmed fact. | Real-model use of these sections is not verified. |
| Configurable retrieval foreground deadline | Yes. `COMPANION_RETRIEVAL_FOREGROUND_DEADLINE_SECONDS` is finite/positive validated; current local default is a provisional 2 seconds, not a final product timeout decision. A semantic timeout returns available lexical matches as degraded continuation. | Automated slow-embedding test verified bounded return, `semantic_timeout`, and lexical results. | A timeout against the real local embedding service was not induced. Deadline value remains configurable and provisional. |

## WP-TXT-07 / 08 Golden and projection evidence

The following P0 Analyzer Goldens pass through the schema validator and Domain projector. Test assertions inspect persisted state and must-not-mutate boundaries, not model prose:

- `AN-GOLD-002` Direct User Fact + Self/User separation
- `AN-GOLD-003` Correction / Clarification
- `AN-GOLD-004` Change over time
- `AN-GOLD-006` Explicit Remember / protected future commitment
- `AN-GOLD-011` Secret rejection and redaction
- `AN-GOLD-012` Undelivered assistant tail exclusion
- `AN-GOLD-014` Valid no-op / idempotent commit

Additional non-Golden regressions `test_projector_records_self_user_relationship_and_affect_without_inventing_state` and `test_preempted_provider_timeout_leaves_analysis_pending_for_retry` exercise persisted Self observation/hypothesis, User hypothesis, Relationship signal/dimension, Appraisal, Emotion episode, and Analyzer retry after foreground preemption. They verify no automatic Self/User promotion and do not pin provisional numeric weights. Empty Mood state stays null; the projector does not invent a baseline.

Projector mapping is versioned as `domain-projector-p0-provisional-v1`. Numeric code-owned mappings/caps are provisional implementation values; the canonical judgments explicitly leave exact numeric weights and thresholds open. Do not describe them as finalized product decisions or tune them without evidence/user decision. P1 Goldens `001/005/007/008/009/010/013` remain requirements to detail after useful live evidence; they are not rejected or removed.

Explicit Remember is recognized, recorded, and covered through `AN-GOLD-006`; Memory/User/Self/Relationship/Affect projection code and fixture-backed DB writes are exercised. The real local Analyzer flow did not establish reliable semantic projection: initial attempts failed/timed out; a later correction proposal used a Message ID as `memory_id` and was rejected as `memory_reference_not_allowed`. No Memory/User Model was committed in that run. A delayed-analysis future-turn evidence leak was identified and fixed with a regression test; the real semantic flow has not yet been rerun after that fix. If a foreground turn preempts a provider call that later times out, Analyzer state returns to retryable `pending`; cancellation of in-flight Ollama computation itself is not verified. Keep Analyzer failure independent of foreground delivery.

## P0 hardening evidence (2026-09-29)

- Explicit Forget now resolves a unique target and atomically writes a per-command UUID marker, soft-delete lifecycle event, and `state_revision`; ambiguous targets mutate nothing. `CMD-GOLD-001〜003` pass through `ConversationRuntime.begin` and Analyzer/Projector fixture paths.
- Correction, clarification, and change-over-time supersede both the prior Memory Claim and linked current `USER_MODEL_ITEM`. `contradicts` records counterevidence without replacing the current claim. Regression tests assert only the new current User Model enters Context.
- Recall, recent Analyzer context, derived Self/User hypotheses, and Relationship signals with recorded provenance revalidate visibility after Forget. Delayed Analyzer input now excludes messages timestamped after its target User turn.
- Ollama `think` is configurable with `COMPANION_THINK`; the provisional local profile sends `think:false`. The adapter consumes only `message.content`, and empty Analyzer content fails without reading or storing `message.thinking`.
- Real-runtime tests used isolated temporary databases. A seeded canonical Memory was visible in a real pre-Forget Ollama turn, then a unique Forget resolved, soft-deleted it, and advanced revision by one. The next Retrieval omitted both the Memory and its source Message, and the Context snapshot omitted the forgotten summary. The generated post-Forget answer still mentioned Earl Grey as a general model guess; that text was not in Retrieval/Context.
- A separate real-runtime Memory-generation/correction flow did **not** pass: initial Analyzer attempts failed or timed out; a later correction proposal used a Message ID as `memory_id` and Validator rejected it as `memory_reference_not_allowed`. No Memory or User Model was committed in that flow. Code review also found and fixed a missing future-turn cutoff; live semantic projection has not been rerun after that code fix.
- Direct Ollama diagnostic on `qwen3.5:2b-q4_K_M`: with `think` omitted, Main returned no `message.content`, produced 1,024 tokens, and ended with `done_reason=length` after 41.22s; with `think:false`, it returned visible content in 0.31s. A constrained synthetic Analyzer request timed out at 60.03s with `think` omitted and returned schema-valid JSON in 35.39s with `think:false`. These are local observations, not product latency decisions.
- Official Ollama API documents `think` and separate `message.thinking`/`message.content` fields: [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md).

## Other retained boundaries and decisions

- `PROJECT_HANDOFF.md` and all canonical source documents remain authoritative; this progress record does not replace them.
- Canonical state remains single-writer. Analyzer output is proposal-only; Validator/Projector owns Domain mutation.
- Assistant canonical content is limited to browser-acknowledged delivery. Cancelled late output is not rendered, persisted, or recalled.
- P0 Explicit Forget is implemented. Memory Management UI, multiple chat threads, edit/delete/regenerate, Voice, full Developer Inspector, standalone Golden Harness, and model tuning remain deferred. Long-term requirements from r16 remain retained.
- An earlier local Main turn with `think` omitted generated no visible content and reached its output-token limit. Direct API probing reproduced that for the configured thinking-capable Qwen 2B; sending `think:false` returned visible content, and the current local runtime profile now applies it. The real model's response relevance remains unreliable; no model tuning was attempted.
- The temporary UI exercise used `http://127.0.0.1:8876/` and `%TEMP%\text-v01-chat-usability-qa.sqlite3`; it is isolated QA data, not user conversation data.

## Verification run

- `python -m unittest discover -s tests -v` using the bundled Python runtime: **33 tests passed**.
- `python -m compileall -q companion`: passed.
- `node --check companion/static/app.js`: passed.
- P0 Golden IDs listed above: all passed through `TurnAnalysisService` and its DB projector fixture path.
- Browser UI checks: streaming composer, new-submit cancellation, quote preview/rendering and stored target, search/jump, date separator/latest control, draft reload, Copy success, safe-Markdown rendering, and normal Chat header were checked on the local app.
- Retrieval timeout: bounded timeout and lexical degraded continuation verified with a deliberately slow fake embedding backend.
- Real local Main: health check passed and one response was delivered. A later request had no rendered output as recorded above.
- Real local Analyzer: `think:false` removed thinking-only/no-content behavior in direct probing, but the real semantic flow still failed/retried and produced a rejected correction proposal. Live Memory/User/Self/Relationship semantic projection remains unverified.
- Real local Forget: seeded-memory forward/query/forget/query path confirmed unique atomic mutation and Retrieval/Context invisibility; this does not prove a model can never name the same concept from general knowledge.
- `WP-TXT-06.5` browser history paging beyond the initial page and multi-page streaming suppression have not been exercised.
- Official Ollama API docs (checked 2026-09-28) distinguish the optional `think` parameter and the `message.thinking` and `message.content` fields. This is a possible diagnostic lead for the no-visible-delta run, not a confirmed cause; no model/runtime tuning was made. [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)

## Next concrete work

1. Re-run real-Ollama Analyzer after the new prior-turn evidence bound; verify a direct claim commits, a later query receives that Memory, and correction leaves only the new User Model current. Do not tune models or lock an Analyzer timeout without an explicit product decision.
2. Preserve the real Forget evidence and investigate whether the post-Forget general-model mention needs a product-level response policy; Retrieval and Context already excluded the stored source.
3. Exercise `load older` in the browser with multiple pages, and live-test retrieval timeout against a deliberately delayed local endpoint if such a test service is available.
4. Continue WP-TXT-09/10 only when separately requested; keep all future/long-term requirements in the ledger.
