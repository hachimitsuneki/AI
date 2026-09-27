# TEXT_V01_READINESS_AUDIT.md

- Project: 自立型AI / 継続人格型デジタルコンパニオン
- Audit: Text v0.1 Definition of Ready
- Version: 2026-09-27-r1
- Scope: Codex実コード着手可否
- Result: **READY — P0 blocker 0（明示Remember/Forgetの曖昧点をr16で最小補完後）**

---

# 1. 判定

Text v0.1は、**これ以上の事前仕様化を実装開始の条件にしない**。

実装着手に必要な以下の対応関係を監査した。

```text
Requirement
  ↕
Component contract
  ↕
Type / State ownership
  ↕
ER / canonical state
  ↕
P0 Golden / negative invariant
  ↕
Acceptance criterion
```

監査前に1件だけP0の曖昧点があった:

> `忘れて`をforegroundで即時適用する方針はあったが、対象が曖昧な場合の最小target-resolution契約が未固定だった。

これを`TEXT_V01_IMPLEMENTATION_SPEC.md §17`で補完した。
曖昧なforgetは**推測削除せずclarification**、resolved forgetのみatomic soft-deleteする。

これによりP0 blockerは0。

---

# 2. Readiness Matrix

| Area | Requirement / intent | Contract / Type | ER / Owner | P0 verification | 判定 |
|---|---|---|---|---|---|
| Persistent identity | CORE-01〜04, AI-001/006/034 | Domain snapshot / ContextCapsule | AI_IDENTITY / STATE / SELF / USER | restart/session acceptance | READY |
| Text turn lifecycle | ORCH-43〜70 | EventEnvelope / TurnRun phases | Orchestrator single-writer | GS-ORCH Text/race cases | READY |
| Memory Episode/Claim | MEM-01〜07 | TurnAnalysisV1 proposals → Validator/Projector | MEMORY_ITEM / EPISODE / CLAIM / REVISION / EVIDENCE | AN-GOLD correction/change-over-time | READY |
| Remember | MEM-13 | ExplicitCommandV1 marker + Analyzer path | Domain Update only | AN-GOLD-006 + CMD-GOLD-003 | READY |
| Forget | MEM-09, ORCH-15/64, RETR-05 | ExplicitCommandV1 resolved/ambiguous | MEMORY_LIFECYCLE_EVENT + state_revision | GS-ORCH-009, RET-GOLD-001/005, CMD-GOLD-001/002 | READY |
| Retrieval | MEM-03/04, RETR-01〜07 | RetrievalRequest/Snapshot/Result V1 | RETRIEVAL_RUN/RESULT; read-only | RET-GOLD-001〜005 | READY |
| Context | ORCH-51/72 | immutable ContextCapsuleV1 | Context Builder owner | hard rule/current input/privacy acceptance | READY |
| Main inference | ORCH-01/09/54/59/75 | GenerationRequestV1 + normalized stream | Gateway owns provider session only | pre-delivery fallback / post-delivery no-swap | READY |
| Delivery truth | ORCH-35/49/62/73 | Delivery checkpoint/completed | Delivery truth; Message projection | partial/cancel Golden | READY |
| Analyzer | ANL-01〜12 | TurnAnalysisInputV1 / TurnAnalysisV1 | proposal only | P0 Analyzer Golden 7件 | READY |
| Domain mutation | ORCH-13〜16/56/64/74 | Validator + Projector | sole writer for semantic Domain | stale/secret/atomic/no resurrection | READY |
| Self/User separation | CORE-03, SELF-*, USER-* | SelfObservation/UserObservation separation | separate entities/evidence | AN-GOLD-002 | READY |
| Relationship | REL-* | sparse RelationshipSignal proposal | RELATIONSHIP + dimensions/evidence | no direct numeric LLM mutation | READY for P0 |
| Affect | AFF-* | Appraisal/Emotion proposal + code projection | APPRAISAL/EMOTION/MOOD/STATE | single-turn cap/separation | READY for P0; tuning deferred |
| Observability | CORE-05, ORCH-10/61 | ComponentAttempt / Context / model / analyzer trace | Technical ER | Inspector acceptance | READY |
| Local/Colab portability | ORCH-20〜23/42/54/75 | Model Gateway | canonical DB local | same Core contract | READY; provider choice deferred |
| UI minimum | UI-01/02/06/07 | Chat + Developer Inspector contract | no new Domain state | basic chat/trace visibility | READY |

---

# 3. ER整合監査

## Domain ER

P0のsemantic truthに必要な役割は既存Entityで表現できる。

- Identity / State / Mood
- Conversation / Message
- Memory Item / Episode / Claim / Evidence / Revision / Lifecycle
- Self Observation / Hypothesis / Model / Evidence
- User Model / Hypothesis / Evidence
- Relationship / Dimension / Signal / Evidence
- Appraisal / Emotion / Affect State Effect / Mood Influence
- Retrieval Run / Result

**新Entityは不要。**

Explicit commandも独立Domain Entityを必須にはしない。
P0ではTurn/Event audit payloadまたはcommand markerとして保持し、確定Memory mutationは既存Lifecycle/Revisionへ投影できる。
将来command historyをfirst-class Domain化する必要が出た場合だけ再検討する。

## Technical ER

Runtime再現に必要なものは既存Technical Traceで足りる。

- TURN_RUN
- TURN_EVENT_TRACE
- COMPONENT_ATTEMPT
- CONTEXT_SNAPSHOT
- MODEL_INVOCATION
- DELIVERY_SPAN
- CANCELLATION_SCOPE
- TURN_ANALYSIS / ANALYSIS_PROPOSAL / ANALYSIS_COMMIT

判定: **整合**。

---

# 4. 実装開始をブロックしない保留

以下は未決だが、component contractの外側/差替可能profileなので着手ブロッカーにしない。

- Main model最終採用（Bonsai 2等）
- Analyzer model最終採用
- Embedding model
- Local Main / Colab Mainの既定値
- SQLite vector拡張 / 別vector storeの最終選択
- retrieval fusion weight / threshold / reranker条件
- Context token budgetの最終値
- Prompt文面の微調整
- Emotion/Relationship numeric mappingの最終値
- UI polish / transitions詳細
- Voice ASR/TTS/VAD/turn detector
- P1 Golden完全化

これらは**実装で交換可能なprofile/config、または実働ログ後の育成対象**。

---

# 5. 初回Codex着手時に必要な前提

Codexへ渡す資料順:

1. `PROJECT_HANDOFF.md`
2. `TEXT_V01_IMPLEMENTATION_SPEC.md`
3. `ANALYZER_GOLDEN_SPEC.md`
4. `RETRIEVAL_P0_SPEC.md`
5. 本`TEXT_V01_READINESS_AUDIT.md`

最初に実装するVertical Slice:

```text
WP-TXT-01 Domain/repository boundary
    ↓
WP-TXT-02 Turn/Event lifecycle
    ↓
WP-TXT-03 Retrieval + WP-TXT-04 Context
    ↓
WP-TXT-05 Gateway + WP-TXT-06 Delivery
    ↓
まず「1ターン話せる」
    ↓
WP-TXT-07 Analyzer + WP-TXT-08 Domain Update
    ↓
「会話後に正しく記憶/自己/ユーザー状態が育つ」
    ↓
WP-TXT-09 Inspector + WP-TXT-10 Golden Harness
```

**最初から全機能を同時に作らない。**

---

# 6. 実装中に止めて確認する条件

Codexが自由判断で仕様を広げず、以下に遭遇した時だけ企画側へ戻す。

- canonical ownershipが2 componentへ跨がないと実装不能に見える
- soft-delete/forget境界を破らないと成立しない
- ERの意味では表現不能な新Domain概念が必須になった
- P0 Golden同士が矛盾する
- Context privacy境界とremote runtime要件が両立しない
- delivery truthを追うため既存Message意味を変更する必要が出た
- Analyzer proposalから直接DB更新しないと著しく複雑になる、と実測で判明した

それ以外のライブラリ選択・内部関数分割・物理列/JSON trace選択等は実装判断へ委ねる。

---

# 7. v0.1 Release Readyとは別

本判定は**Codex実装開始Ready**であり、v0.1完成判定ではない。

v0.1完成前には最低限:

- 3日以上/複数session continuity test
- Memory recall/correction/forget
- Self/User separation
- explicit remember protection
- basic autonomous archive（v0.1明示決定分）
- persona independence / sycophancy check
- Developer Inspectorで失敗原因追跡
- latency/TTFT計測

を実働で確認する。

Voice / Avatar / Web / PC / Game / autonomous absent activity / Skill / Model Evolutionは長期要求として保持し、Text v0.1のCodex着手ブロッカーにはしない。

---

# 8. Final DoR

**Text v0.1: READY FOR CODEX IMPLEMENTATION**

条件:
- 本監査以降、実装前の新規詳細仕様化を原則停止する。
- 新しい仕様は、P0 blockerが実装で発見された場合か、初期実働ログから必要性が確認された場合に追加する。
- ユーザーから実コード着手の指示があるまではコードを作らない。
