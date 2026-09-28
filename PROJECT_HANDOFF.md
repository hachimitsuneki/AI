# PROJECT_HANDOFF.md — r16 Canonical Entry Point

- Project: 自立型AI / 継続人格型デジタルコンパニオン
- Canonical source version: `0.1-draft-handoff-2026-09-27-r16`
- Updated: 2026-09-28 JST
- Status: **WP-TXT-01〜06 + WP-TXT-06.5実装済み / WP-TXT-07〜08はfixture Golden検証済み / 実Ollama Analyzerは未検証**
- Target branch: `codex/text-v01-p0`
- Task implementation commit: `3c74754` (`Implement chat usability and semantic projection`); this handoff status is recorded in a following documentation-only commit.
- Uncommitted changes after handoff: none

> **重要:** このルートファイルはGit上の入口/索引です。元の約20万bytesの`PROJECT_HANDOFF.md r16`を要約して置換するものではありません。完全なr16本文は `docs/canonical/r16/` の19partを順番に読んでください。

## Canonical r16

- Original source bytes: **201,327**
- Original SHA-256: `26ba528e595089adb22a4f950ba7db311271bd8c4d2060dd562c5dfebc721177`
- Manifest / reading order: [`docs/canonical/r16/MANIFEST.md`](docs/canonical/r16/MANIFEST.md)

Canonical r16の主な内容:
- 目的・利用者・成功条件・制約・長期要求
- `REQ-AI-001〜058`
- v0.1 Core / Memory / Self / User / Relationship / Affect / UI / Orchestrator / Analyzer / Retrieval / Explicit Command / DoR要件
- Domain ER / Technical Trace ER / long-term Capability ER
- Voice/AI VTuber low-latency設計
- Event / Command / Snapshot型契約
- producer/consumer、state transition、failure/cancel契約
- `GS-ORCH-001〜015`
- `TurnAnalysisV1` field-level型契約
- 判断履歴、保留、却下/後回し、訂正
- 最初の実装、試験、参照資料、r4〜r16変更履歴

**概要に書かれていない項目を「要求なし」と解釈しないこと。** 必ずcanonical r16を確認する。

## Standalone canonical specifications

Git化前に独立仕様書として存在した文書は、r16 handoffを含めて計5冊。台帳: [`docs/SPEC_REGISTRY.md`](docs/SPEC_REGISTRY.md)

1. `PROJECT_HANDOFF.md r16` — 上記19part
2. [`docs/TEXT_V01_IMPLEMENTATION_SPEC.md`](docs/TEXT_V01_IMPLEMENTATION_SPEC.md) — 4partへのcanonical index
3. [`docs/TEXT_V01_READINESS_AUDIT.md`](docs/TEXT_V01_READINESS_AUDIT.md)
4. [`docs/ANALYZER_GOLDEN_SPEC.md`](docs/ANALYZER_GOLDEN_SPEC.md)
5. [`docs/RETRIEVAL_P0_SPEC.md`](docs/RETRIEVAL_P0_SPEC.md)

`README.md` / `CODEX_START.md` / manifestsはnavigation資料であり、この5冊を置換しない。

## Current implementation state

- Text v0.1: **WP-TXT-01〜06.5実装済み。WP-TXT-07〜08はP0 fixture GoldenとProjector経路を検証済み。実モデルによるAnalyzer意味投影は未確認。**
- Application code: Chat usability, async Turn Analyzer, schema/reference/privacy Validator, atomic idempotent Projectorを追加。機能ごとの実装・実動・未確認範囲は [`CURRENT.md`](CURRENT.md) を参照
- DB schema / migration: `0002_chat_usability.sql` and `0003_turn_analysis.sql` を追加。返信ID、turn analysis/proposal/commitを永続化
- automated tests: bundled Python runtimeで24件成功。7 P0 Analyzer Goldensも全て成功
- model server: ローカルOllama health確認は成功したが、実Analyzer呼出しは設定済み60秒timeout後に`provider_unavailable`。WP07/08は本番用モデル応答をまだ実証していない
- hardware benchmark: 未実施。モデル/runtime tuningはしていない

## Implementation path and current position

```text
WP-TXT-01 Canonical Domain schema + repository contract — implemented / locally verified
↓
WP-TXT-02 Turn / Event / Attempt lifecycle — implemented / locally verified
↓
WP-TXT-03 Retrieval + WP-TXT-04 Context Builder — implemented / locally verified
↓
WP-TXT-05 Gateway/Main streaming + WP-TXT-06 Delivery truth — implemented / locally verified
↓
foreground: 1ターン普通に会話できるVertical Slice — implemented / live-verified
↓
WP-TXT-06.5 Chat Usability — implemented / UI mostly live-verified
↓
WP-TXT-07 Turn Analyzer + WP-TXT-08 Validator/Projector — implemented / seven P0 fixture Goldens pass / real Analyzer model unverified
↓
persistent Memory / Self / User / Relationship projector paths — fixture-backed Domain writes pass; real model projection unverified
↓
WP-TXT-09 Developer Inspector + WP-TXT-10 Golden Harness — not started
```

現行position・browser evidence・失敗したOllama実行・未確認項目は [`CURRENT.md`](CURRENT.md) を先に参照する。Retrieval foreground deadlineの2秒はlocal provisional defaultであり、最終製品値ではない。Analyzer/Projectorのnumeric mappingsも`domain-projector-p0-provisional-v1`として記録された暫定値で、製品決定として固定しない。

## Non-negotiable boundaries for v0.1

- User / AI Selfを自動転写しない。
- Unknownを正常状態として許す。
- canonical stateはsingle-writer。
- User Forgetは`soft_deleted`。AI Recall/Prompt/Evidenceから不可視。
- 曖昧なforgetはguess-deleteしない。
- secret/credentialをlong-term Memoryへ保存しない。
- assistant canonical messageは**実際にdeliveryされた範囲だけ**。
- Analyzerはproposal generator。Domain mutationはValidator + Projector経由。
- stale Analyzer/Retrievalからforgotten contentを復活させない。
- Main provider fallbackはdelivery前のみ。同一文をdelivery後に別modelで無言継続しない。
- Analyzer failureはforeground Chatを止めない。
- Voice / Avatar / Vision / Web / PC / Game / Skill / Drives / absence autonomy / Permission / Plugin-MCP / Model Evolution等の長期要求をText v0.1外という理由で削除しない。

## Codex reading order

1. このファイル
2. [`docs/SPEC_REGISTRY.md`](docs/SPEC_REGISTRY.md)
3. [`docs/canonical/r16/MANIFEST.md`](docs/canonical/r16/MANIFEST.md) に従ってr16全文
4. [`docs/TEXT_V01_IMPLEMENTATION_SPEC.md`](docs/TEXT_V01_IMPLEMENTATION_SPEC.md) → 4part全文
5. [`docs/TEXT_V01_READINESS_AUDIT.md`](docs/TEXT_V01_READINESS_AUDIT.md)
6. [`docs/ANALYZER_GOLDEN_SPEC.md`](docs/ANALYZER_GOLDEN_SPEC.md)
7. [`docs/RETRIEVAL_P0_SPEC.md`](docs/RETRIEVAL_P0_SPEC.md)
8. `CODEX_START.md`

仕様矛盾・不足が見つかった場合は、独断で大きく再設計せず、影響するRequirement / Component / Entity / Goldenと最小解決案を報告する。
