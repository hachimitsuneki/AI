# Current implementation state

Updated: 2026-10-05 (JST)

## Handoff position

- Repository: https://github.com/hachimitsuneki/AI
- Target branch: `codex/fix-chat-response-language` (PR targets `main`; merge remains a user decision).
- Current fix baseline: `main` at the requested Base HEAD `1a721b31c67e22d360a0941a9a42d21080ccbbf6` (`Merge Text v0.1 P0 implementation`).
- Response-language implementation/tests: `a3218c6ebb4051f528c738428cd7d930ddc0e746`.
- Independent README cleanup: `97b654fb604bbf91c911d9d2423e72d63d20f3a7`. The following documentation-only commit records this validation; the tracked worktree is clean after it is committed.
- Current scope: ordinary Main Dialogue response-language bugfix and README cleanup only; no product feature expansion or model/personality tuning.
- Previous P0 implementation branch: `codex/text-v01-p0`. The baseline and verification history below are retained.
- Prior task baseline: `e46228d1021296eae8e3a7734769326a1e0cd5db` (`Implement Text v0.1 foreground conversation slice`)
- Prior implementation commit: `3c74754` (`Implement chat usability and semantic projection`).
- Baseline before this P0 hardening: `ced97c9c32d3442063e4323e4bec7fc48efc9cfa`.
- P0 hardening implementation commit: `a8ed997` (`Harden Text v0.1 P0 memory handling`).
- Starting HEAD for final P0 validation: `fac3c1ea1af2fc5078970c20a82ce694f2e05918` on `codex/text-v01-p0`.
- Final P0 validation implementation/test commit: `ec72b83` (`Harden analyzer semantic projections`). The following documentation-only commit records this result.
- That previous P0 validation changed only Analyzer/Repository behavior, regression tests, and project progress/handoff records; its handoff worktree was clean.
- Scope in the previous validation: final WP-TXT-01〜08 P0 validation after the prior WP-TXT-06.5 and WP-TXT-07/08 implementation.
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
| WP-TXT-06.5 Chat Usability | Interruptible composer, canonical replies, search, staged history, date separators, scroll control, draft, Copy, safe Markdown, user-facing identity | 38 automated tests total and isolated localhost UI exercise; feature matrix below records the specific evidence and gaps | Implemented; mostly live-verified |
| WP-TXT-07 Turn Analyzer | Structured semantic proposals over canonical delivered evidence; async, retryable, secret-filtered; delayed analysis excludes future turns | Seven P0 Analyzer Goldens, future-turn exclusion, and isolated real-Ollama direct-claim → Recall → correction E2E; a rapid multi-turn background run also exposed timeout/preemption limits below | Implemented; semantic E2E verified on the configured local 2B Analyzer when each analysis completed before the next turn |
| WP-TXT-08 Validator / Projector | Reference and privacy validation, stale-revision fail-close, atomic Domain projections, idempotent commits; correction supersedes linked User Model; contradiction remains counterevidence | Fixture Goldens plus real Memory Claim/User Model commit and change-over-time projection; duplicate direct-claim hypothesis is rejected | Implemented; required real semantic projection verified; Self/Relationship semantic accuracy remains unverified |
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
| Context Builder learned read sections | Yes. Learned Self, User Model (including clearly marked hypotheses), and Relationship are read; empty means empty. | Real isolated-Ollama E2E confirmed the new current User Model is present after correction and the superseded User Model is absent; automated checks cover empty sections and hypotheses. | Real semantic Self/Relationship projection is not established by this P0 E2E. |
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

Explicit Remember is recognized, recorded, and covered through `AN-GOLD-006`; Memory/User/Self/Relationship/Affect projection code and fixture-backed DB writes are exercised. Earlier live runs failed/timed out or returned a Message ID in `relation_to_existing.memory_id`, which Validator rejected as `memory_reference_not_allowed`. The final run below now verifies real Memory/User projection, Recall, and correction after the reference schema and prompts were hardened. A separate ordinary background run still showed that a recall question can generate a rejected duplicate proposal and a later turn can preempt a slow Analyzer; these failures remain recorded rather than counted as semantic success. Analyzer failures remain independent from foreground delivery. Cancellation of in-flight Ollama computation itself is not verified.

## P0 hardening evidence (2026-09-29)

- Explicit Forget now resolves a unique target and atomically writes a per-command UUID marker, soft-delete lifecycle event, and `state_revision`; ambiguous targets mutate nothing. `CMD-GOLD-001〜003` pass through `ConversationRuntime.begin` and Analyzer/Projector fixture paths.
- Correction, clarification, and change-over-time supersede both the prior Memory Claim and linked current `USER_MODEL_ITEM`. `contradicts` records counterevidence without replacing the current claim. Regression tests assert only the new current User Model enters Context.
- Recall, recent Analyzer context, derived Self/User hypotheses, and Relationship signals with recorded provenance revalidate visibility after Forget. Delayed Analyzer input now excludes messages timestamped after its target User turn.
- Ollama `think` is configurable with `COMPANION_THINK`; the provisional local profile sends `think:false`. The adapter consumes only `message.content`, and empty Analyzer content fails without reading or storing `message.thinking`.
- Real-runtime tests used isolated temporary databases. A seeded canonical Memory was visible in a real pre-Forget Ollama turn, then a unique Forget resolved, soft-deleted it, and advanced revision by one. The next Retrieval omitted both the Memory and its source Message, and the Context snapshot omitted the forgotten summary. The generated post-Forget answer still mentioned Earl Grey as a general model guess; that text was not in Retrieval/Context.
- Historical 2026-09-29 real-runtime Memory-generation/correction attempts did **not** pass: initial Analyzer attempts failed or timed out; a later correction proposal used a Message ID as `memory_id` and Validator rejected it as `memory_reference_not_allowed`. No Memory or User Model was committed in that run. A missing future-turn cutoff was fixed afterward; the post-fix success and remaining timeout evidence is recorded in “Final P0 validation evidence” below.
- Direct Ollama diagnostic on `qwen3.5:2b-q4_K_M`: with `think` omitted, Main returned no `message.content`, produced 1,024 tokens, and ended with `done_reason=length` after 41.22s; with `think:false`, it returned visible content in 0.31s. A constrained synthetic Analyzer request timed out at 60.03s with `think` omitted and returned schema-valid JSON in 35.39s with `think:false`. These are local observations, not product latency decisions.
- Official Ollama API documents `think` and separate `message.thinking`/`message.content` fields: [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md).

## Final P0 validation evidence (2026-09-30)

- **Real Analyzer root cause for Message ID references:** an earlier Ollama result put a canonical Message ID in `relation_to_existing.memory_id`; Validator rejected it with `memory_reference_not_allowed`. The snapshot listed allowed message and memory IDs separately, but the submitted JSON Schema represented both output fields as an unconstrained generic string. That left the model a structurally valid way to cross ID types. The current schema places field-specific enums on evidence Message IDs and allowed Memory IDs and uses a conditional relation shape. In a post-change real correction run, the emitted `memory_id` exactly matched the existing claim ID and the emitted evidence ID exactly matched the current user Message ID. This points to the prior ID representation/schema boundary as the primary cause; it does not establish that prompt wording was irrelevant. Ollama documents passing JSON Schema through `format`; the type-specific enums use that supported structured-output boundary ([Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)).
- **Model capability diagnostic:** with the same `think:false` runtime setting and clarified prompt/schema, controlled live probes on `qwen3.5:2b-q4_K_M` and `qwen3.5:4b-q4_K_M` both selected the supplied existing Claim ID for the blue→green correction (the 2B proposal used `corrects`; 4B used `changes_over_time`). A separate full 2B run initially chose `new` for a changed preference. After clarifying the prompt and using an explicit “previously X, now Y” statement, the full 2B runtime path chose `changes_over_time`. These are diagnostic executions only; no final model choice, model tuning, or timeout product decision was made.
- **Real semantic E2E:** a fresh isolated SQLite DB with real local Ollama Analyzer `qwen3.5:2b-q4_K_M`, `think:false`, and the configured 60-second Analyzer timeout committed `My favorite color is cobalt.` as one active `MEMORY_ITEM(memory_kind=claim)` plus one current `USER_MODEL_ITEM` (30.22 seconds). The real next-turn Retriever returned the Claim and the Context capsule contained cobalt; its result was `degraded`, with the available lexical match providing Recall. On `Previously my favorite color was cobalt, but my preference has changed; now I prefer moss green.`, the real Analyzer proposed `changes_over_time` referencing the exact old Claim ID; Validator/Projector made the old Claim historical and its User Model superseded, and committed one new current green Claim/User Model (15.77 seconds). A subsequent Context read contained only the new current User Model; the old User Model ID/value was absent from the User Model section. The earlier blue source remains ordinary conversation history where permitted; the claim’s current User Model is not duplicated. A separate run with an isolated 120-second Analyzer timeout also passed and had `ok` Retriever results; that override was diagnostic only.
- The same live run first showed a duplicate low-confidence `USER_HYPOTHESIS` for the direct favorite-color Claim despite the prompt instruction. A narrow Validator guard now rejects a `user_observation` about the same subject when the same current user message already has an accepted direct Claim (`direct_claim_covers_user_observation`). The final isolated E2E produced exactly one Claim and no duplicate User Hypothesis.
- **Mixed-evidence Forget regression:** `CMD-GOLD-004` now creates Memory A and B from one canonical user Message, links Self/User/Relationship derived state to that source, forgets only A, and confirms fail-closed visibility: A-linked and mixed-source derived state is hidden even while B remains active; B-only User Model remains available. Follow-up real Retriever, Context, and Analyzer-input assertions exclude A-derived content.
- **Real unique Forget:** on a separate isolated DB, `ConversationRuntime.begin` resolved the explicit `cobaltを忘れて` command uniquely, soft-deleted the target and advanced `state_revision` by exactly one. Follow-up real Ollama Retrieval returned neither the target Memory nor source Message; Context and derived User Model omitted the forgotten fact, and the next Analyzer snapshot had no forgotten Memory or prior Forget-command message in recent evidence.
- **Foreground resilience:** `test_analyzer_failure_does_not_delay_successful_foreground_chat` confirms that a provider failure during background Analyzer work does not prevent a delivered foreground assistant message. Earlier ordinary rapid-turn live execution also surfaced Analyzer timeout/preemption behavior; this does not invalidate the sequential semantic E2E above and cancellation of Ollama compute itself remains unverified.
- **Timeout scope:** the acceptance E2E passed with the existing 60-second default. A separate diagnostic used an isolated 120-second Analyzer timeout to distinguish Analyzer latency from relation/schema behavior; product configuration remains unchanged, and 120 seconds is not a proposed product value.
- Full automated test suite: **38 tests passed**, including `AN-GOLD-002/003/004/006/011/012/014`, `CMD-GOLD-001/002/003/004`, command ID uniqueness, and foreground Analyzer-failure isolation. `python -m compileall -q companion` and `node --check companion/static/app.js` passed.

## Other retained boundaries and decisions

- `PROJECT_HANDOFF.md` and all canonical source documents remain authoritative; this progress record does not replace them.
- Canonical state remains single-writer. Analyzer output is proposal-only; Validator/Projector owns Domain mutation.
- Assistant canonical content is limited to browser-acknowledged delivery. Cancelled late output is not rendered, persisted, or recalled.
- P0 Explicit Forget is implemented. Memory Management UI, multiple chat threads, edit/delete/regenerate, Voice, full Developer Inspector, standalone Golden Harness, and model tuning remain deferred. Long-term requirements from r16 remain retained.
- An earlier local Main turn with `think` omitted generated no visible content and reached its output-token limit. Direct API probing reproduced that for the configured thinking-capable Qwen 2B; sending `think:false` returned visible content, and the current local runtime profile now applies it. The real model's response relevance remains unreliable; no model tuning was attempted.
- The temporary UI exercise used `http://127.0.0.1:8876/` and `%TEMP%\text-v01-chat-usability-qa.sqlite3`; it is isolated QA data, not user conversation data.

## Verification run

- `python -m unittest discover -s tests -v` using the bundled Python runtime: **38 tests passed**.
- `python -m compileall -q companion`: passed.
- `node --check companion/static/app.js`: passed.
- P0 Golden IDs listed above: all passed through `TurnAnalysisService` and its DB projector fixture path.
- Browser UI checks: streaming composer, new-submit cancellation, quote preview/rendering and stored target, search/jump, date separator/latest control, draft reload, Copy success, safe-Markdown rendering, and normal Chat header were checked on the local app.
- Retrieval timeout: bounded timeout and lexical degraded continuation verified with a deliberately slow fake embedding backend.
- Real local Main: health check passed and one response was delivered. A later request had no rendered output as recorded above.
- Real local Analyzer: the final isolated Memory → Recall → correction/change-over-time semantic E2E passed for Memory Claim and User Model projection. Real Self/Relationship semantic correctness remains unverified.
- Real local Forget: seeded-memory forward/query/forget/query path confirmed unique atomic mutation and Retrieval/Context invisibility; this does not prove a model can never name the same concept from general knowledge.
- `WP-TXT-06.5` browser history paging beyond the initial page and multi-page streaming suppression have not been exercised.
- Official Ollama API docs (checked 2026-09-28) distinguish the optional `think` parameter and the `message.thinking` and `message.content` fields. This is a possible diagnostic lead for the no-visible-delta run, not a confirmed cause; no model/runtime tuning was made. [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)

## Response language bugfix validation — 2026-10-05

Source: the user's current request, sections 1–6 and its completion criteria. This is a normal Chat behavior fix over the merged P0 baseline, with the canonical specifications and long-term requirements retained.

### Implementation and regression evidence

| Requested behavior | Implementation / automated evidence | Live evidence / remaining scope |
|---|---|---|
| Japanese current input requires Japanese output | `response_language.py` supplies mandatory `Output language: Japanese`, natural Japanese response, and explicit English-switch exceptions; `ContextBuilder` no longer relies on `when practical`. `test_japanese_capsule_has_mandatory_explicit_policy` passes. | Real local Main returned Japanese; canonical readback matched acknowledged output. |
| English history / Identity cannot override Japanese current input | Policy is chosen from the canonical current User Message, before Main-only substitutions. `test_english_history_and_identity_do_not_override_current_japanese` passes with English history and the existing English Identity. | The live normal turn also had earlier English user history and the existing Identity. |
| Resolved Japanese Forget retains its original language | `CMD-GOLD-001` now asserts original canonical input is unchanged, forgotten content stays absent, and both system instructions and the safe internal Main input retain the same Japanese policy. | Real `ConversationRuntime.begin` → Retrieval → Context → Ollama → delivery ACK → canonical readback completed in Japanese; target soft-deleted and revision advanced once. |
| English / explicit requested-language priority | `test_english_capsule` and `test_explicit_language_requests_override_current_input_language` pass, including Japanese→English, English→Japanese, French, concise requests, and last explicit request priority. | English and third-language output compliance were not live-tested in this fix. |
| Mixed code / model names / neutral input | Fenced/inline code, quoted instructions, URLs, and versioned identifiers are excluded from prose/explicit-request heuristics. Short Japanese questions retain Japanese. A language-neutral input uses the latest usable canonical user language; without such cues it falls back to English. Mixed-text, quoted/negated-request, and neutral-model-ID regressions pass. | This is a deterministic P0 heuristic, not exact multilingual classification. Explicit aliases cover Japanese, English, Chinese, Korean, French, German, and Spanish; arbitrary indirect requests and other languages remain unverified. |

- Language policy is counted in mandatory dialogue/current-input context and survives budget trimming. The old fixed 650-token test failed because the mandatory prompt grew; it now budgets against the actual full capsule while retaining all older-history omission, newest-history retention, identity/current-input, and immutability assertions, plus a language-policy assertion. The product context budget remains unchanged.
- An initial new test fixture also failed when repeated subcases left a turn active; the fixture now finalizes each context-only test turn. No tests were deleted, skipped, or weakened.
- **Final full automated suite: 45 tests passed** (38 existing + 7 language tests), including `AN-GOLD-002/003/004/006/011/012/014`, `CMD-GOLD-001/002/003/004`, correction/current User Model, contradiction, mixed-evidence Forget, Analyzer-failure isolation, and Delivery truth. `python -m compileall -q companion`, `node --check companion/static/app.js`, and `git diff --check` passed.
- Changed production code is confined to Main Context language policy and its safe Forget surrogate. Memory policy, Retrieval, command resolution/mutation, Analyzer/Projector semantics, delivery projection, Identity/personality, and model/runtime profile values are unchanged.
- README cleanup is an independent documentation-only commit: it describes implemented WP-TXT-06.5/07/08, semantic persistence, Remember/Forget boundaries, existing Goldens, and the remaining WP-TXT-09/10/live Self/Relationship limits. It links to the handoff, current evidence, and canonical registry without replacing source specifications.

### Real local Ollama execution

- Used an isolated SQLite DB under ignored `artifacts/response-language-live-20261005/`; existing user conversation data was not used. Real Main `qwen3.5:2b-q4_K_M`, embedding `nomic-embed-text:latest`, and the existing `think:false` profile were preserved. The probe exercised the actual foreground Runtime/Retriever/Context/Gateway/canonical path with headless delivery ACKs. The Forget target was seeded; background Analyzer calls and browser paint were outside this probe's scope.
- The first probe returned Japanese for normal Chat, but resolved Forget still returned English (`Understood. I've acknowledged...`) despite the Japanese system policy. This motivated repeating the policy, selected from the original canonical input, in the safe Main-facing Forget surrogate. The forgotten target text remains excluded. No model change or broad prompt rewrite was made.
- Successful normal turn: `9549718f-d8ce-4b08-8003-639e7e40a871`, user message `147725f1-d87e-4983-8076-4cf25c37bcec`; input `こんにちは。今日は少し休憩したい気分です。おすすめの気分転換を一つ、短く教えて。`; output began `こんにちは！少しお休みなさいね。` and remained Japanese. Completed in 4.00 seconds with 46 acknowledged spans and exact canonical readback.
- Successful Forget turn: `3e9e1792-f1c4-4896-a1b3-9d7b34d57b98`, user message `a7d5cc89-54de-47e3-a276-9cb04bcf6646`; input `ルイボスティーのことを忘れて。`; Main's English internal text retained `Output language: Japanese`; output `記憶は忘れています。さようなら。😊👋`. Completed in 4.36 seconds with 11 acknowledged spans and exact canonical readback. Marker was `resolved` / `mutation_applied=true`; Memory `f1f62b25-e316-4368-9a27-d57dd62fceb5` became `soft_deleted`; `state_revision` changed `0 → 1`; response did not repeat the target.
- Local probe details/DB remain in ignored artifacts; the acceptance evidence above is preserved in Git. Language compliance is live-verified for these two turns, not guaranteed for every stochastic response. Answer wording/relevance remained awkward (including the normal turn's “雲をつなぐ橋” suggestion and the Forget farewell); response quality/personality/model tuning was not attempted. Browser verification and real Analyzer semantic E2E were not rerun for this language-only fix; the existing regression suite passes and previous P0 live evidence remains above.

## Next concrete work

1. Review the small fix PR against `main`; merge only after the user's decision.
2. Use the resulting baseline for ordinary chats over several days, recording language switches, Memory/Recall/correction/Forget behavior, and awkward responses with their turn evidence.
3. Keep the earlier pending checks below deferred. WP-TXT-09/10, Voice, multiple threads, UI additions, and model tuning require a separate request.

### Retained earlier follow-ups (deferred)

1. No remaining P0 Analyzer/Projector validation blocker is known. Keep the rapid-turn Analyzer timeout/preemption case observable and retryable; choose a product timeout only after a product decision.
2. Exercise `load older` in the browser with multiple pages, and live-test retrieval timeout against a deliberately delayed local endpoint if such a test service is available.
3. Continue WP-TXT-09/10 only when separately requested; keep all future/long-term requirements in the ledger.
