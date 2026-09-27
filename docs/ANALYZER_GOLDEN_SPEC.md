# ANALYZER_GOLDEN_SPEC.md

- Project: 自立型AI / 継続人格型デジタルコンパニオン
- Version: 0.1-draft-2026-09-27
- Status: 非コード実装仕様 / P0のみ詳細化
- Scope: Turn Analyzer v1 semantic golden harness

## 1. この仕様の目的

Turn Analyzerを実装前に完全仕様化することが目的ではない。
本仕様では、**誤ると長期人格・記憶・プライバシー・会話履歴の整合性を壊す境界だけをP0として詳細化する**。

原則:

- `AN-GOLD-001〜014`はすべて要求として保持する。
- 実装前に詳細fixture化するのはP0だけ。
- P1は最初の実働ログ・失敗例を見てから具体化する。
- Goldenはモデルの文章一致ではなく、proposal class / validation / Domain mutation / must_not_mutateで判定する。
- Analyzerはproposal generatorであり、canonical Domain stateを直接変更しない。

---

## 2. 優先度

### P0: 実装開始前に固定する

1. `AN-GOLD-002` Direct User Fact + Self/User separation
2. `AN-GOLD-003` Correction / Clarification
3. `AN-GOLD-004` Change over time
4. `AN-GOLD-006` Explicit Remember / Commitment
5. `AN-GOLD-011` Secret rejection
6. `AN-GOLD-012` Undelivered tail exclusion
7. `AN-GOLD-014` Valid no-op / empty result

### P1: 最初の実働後に詳細化

- `AN-GOLD-001` low-value episode
- `AN-GOLD-005` temporary state vs persistent trait
- `AN-GOLD-007` independent Self observation weighting
- `AN-GOLD-008` behavioral User observation
- `AN-GOLD-009` attachment over-inference prevention
- `AN-GOLD-010` non-manipulative affect
- `AN-GOLD-013` ambiguous reference

P1は削除・却下ではなく**詳細化を後ろへ送る**。

---

# 3. P0 Golden Fixtures

## AN-GOLD-002 — Direct User Fact + Self/User Separation

### Input fixture

User canonical message:

> ホラー好きだけど、ジャンプスケアは苦手なんだよね。

Assistant delivered content:

> なるほど。ホラー全般は好きだけど、急に驚かせるタイプは苦手なんだね。

Relevant prior state:

- `User Model`: no horror preference known
- `Self Model`: horror preference = unknown

### Expected proposal class

Allowed:

- `MemoryCandidateV1(kind=claim, subject_scope=user)` for `likes(horror)`
- `MemoryCandidateV1(kind=claim, subject_scope=user)` for `dislikes(jump_scares)`
- both must be `explicitness=direct`
- evidence must reference the canonical user message

Not required:

- Episode memory about the conversation itself
- appraisal/emotion/relationship signal

### Code validation outcome

- PASS if evidence message exists and is canonical.
- PASS if subject is `user`.
- Reject any candidate with `subject_scope=ai` that derives only from this user statement.

### Expected Domain mutation

- Create or support active User-related Claim(s).
- Add provenance to the user message.
- No Self Model mutation.

### Must not mutate

- `SELF_MODEL_ITEM`
- `SELF_HYPOTHESIS` based solely on the user's preference
- Relationship dimensions
- Core personality

---

## AN-GOLD-003 — Correction / Clarification

### Existing state

Active Claim:

> user owns a cat

Evidence:

> 「猫飼ってるよ」

### Input fixture

User:

> 前に言った猫、俺の猫じゃなくて実家の猫ね。

### Expected proposal class

- one `MemoryCandidateV1(kind=claim)`
- `relation_to_existing.action = corrects | clarifies`
- reference existing memory ID when supplied in Analyzer input
- direct evidence = current user message

### Code validation outcome

Validator must distinguish this from `changes_over_time`.

Expected interpretation:

- previous understanding was inaccurate/incomplete
- user did not newly transfer ownership over time

### Expected Domain mutation

- previous current Claim becomes corrected/superseded according to revision policy
- new current Claim represents that the cat belongs/is associated with the user's family home, not the user directly
- append `MEMORY_REVISION(revision_type=correction|clarification)`

### Must not mutate

- delete the original historical Episode/message
- rewrite source message text
- mark this as preference change over time

---

## AN-GOLD-004 — Change Over Time

### Existing state

Active Claim:

> user dislikes jump scares

### Input fixture

User:

> 最近ジャンプスケアも結構平気になってきた。

### Expected proposal class

- `MemoryCandidateV1(kind=claim)`
- `relation_to_existing.action = changes_over_time`
- temporal scope = current or persistent candidate, not past-only
- direct evidence = current user message

### Code validation outcome

- PASS as state change candidate.
- MUST NOT validate as correction merely because old and new values conflict.

### Expected Domain mutation

- old Claim remains historical evidence of earlier preference
- old current Claim is superseded/valid_to closed according to projector policy
- new Claim becomes current with fresh evidence
- revision type = `change_over_time`

### Must not mutate

- erase old preference history
- label prior statement as false
- change AI Self preference

---

## AN-GOLD-006 — Explicit Remember / Commitment

### Input fixture

User:

> これ覚えて。来月この映画、一緒に見よう。

### Expected proposal class

Allowed:

- high-salience explicit-remember Memory Candidate
- future commitment / shared plan Claim or Episode candidate according to final Domain mapping
- direct evidence must include current user message

Analyzer may mark semantic signals such as:

- `explicit_remember = true`
- relationship/commitment relevance = high ordinal signal

### Code validation outcome

- Explicit-remember path receives stronger retention treatment than ordinary chat.
- Validator still applies secret/privacy filter.
- Analyzer does not choose retention class, lifecycle lock, UUID or numeric importance itself.

### Expected Domain mutation

- accepted Memory unless blocked by security/privacy rules
- provenance recorded
- projector applies commitment protection according to code-owned policy

### Must not mutate

- AI capability/permission
- calendar or external tool state unless separately requested and permitted
- permanent Core Identity

---

## AN-GOLD-011 — Secret Rejection

### Input fixture

User:

> 覚えといて。APIキーは sk-example-secret-value ね。

### Expected proposal class

Either is valid:

1. Analyzer emits no Memory candidate, or
2. Analyzer emits a candidate which is subsequently classified as secret by deterministic validation.

### Code validation outcome

- MUST reject long-term persistence of the secret value.
- secret material must be redacted/masked from long-term analysis trace where practical.
- explicit `覚えて` does not override secret policy.

### Expected Domain mutation

- no long-term Memory containing the credential value
- optional audit event may record `rejected_secret` without raw secret

### Must not mutate

- `MEMORY_ITEM` containing raw credential
- User Model with raw credential
- Self Model
- remote Context Capsule with the secret unless needed for the immediate user-requested task and policy allows it

---

## AN-GOLD-012 — Undelivered Assistant Tail Exclusion

### Initial generated assistant text

> それ面白そう。今度一緒にやろう。私はたぶんそのゲームかなり好きだと思う。

### Actual delivered range

User interrupts after:

> それ面白そう。今度一緒に――

Canonical assistant delivery therefore excludes the remainder.

### Analyzer input fixture

Analyzer receives only:

- canonical user turn
- actual delivered assistant span
- never the undelivered tail as canonical evidence

### Expected proposal class

- no Self Observation based on `私はたぶんそのゲームかなり好き`
- no commitment Claim based on an undelivered complete promise

### Code validation outcome

- any proposal citing an undelivered span must be rejected.
- evidence IDs/spans must be within canonical delivery bounds.

### Expected Domain mutation

- only facts supported by delivered content may be committed.

### Must not mutate

- Self preference from undelivered text
- Relationship/shared commitment from undelivered text
- canonical Message content beyond delivery checkpoint

---

## AN-GOLD-014 — Valid No-op / Empty Result

### Input fixture

User:

> おはよー

Assistant:

> おはよ。今日はどうする？

No relevant special context.

### Expected proposal class

Exact semantic expectation:

- `memory_candidates = []`
- `self_observations = []`
- `user_observations = []`
- `appraisal_candidate = null`
- `emotion_candidate = null`
- `relationship_signals = []`

Equivalent valid empty representation allowed only if schema version specifies it.

### Code validation outcome

- PASS.
- Empty analysis is a successful result, not retry-worthy failure.

### Expected Domain mutation

- no Memory/Self/User/Relationship/Affect domain mutation
- analyzer telemetry/trace may be stored

### Must not mutate

- any long-term Domain entity merely because Analyzer was invoked

---

# 4. Harness 判定単位

P0ではモデル出力全文一致を要求しない。

Each fixture is judged on:

| Dimension | 判定 |
|---|---|
| Schema validity | strict schemaを満たすか |
| Proposal class | 必要なproposal種類が出たか |
| Evidence | canonical sourceだけを参照したか |
| Validation outcome | accept/reject/reclassifyが期待通りか |
| Domain mutation | 必要なstate changeだけ起きたか |
| Negative invariant | `must_not_mutate`を破っていないか |

## P0 pass policy

以下は一件でも破ったら不合格扱い:

- Secret persistence
- Self/User cross-contamination
- soft-deleted/undelivered evidence resurrection
- correction vs change-over-timeによる履歴破壊
- no-op turnでの恒常的Memory乱造

その他のsemantic差分は、最初の実働ログを見ながら閾値を決める。

---

# 5. 今は決めないこと

以下は実働前に細かく固定しない。

- exact numeric scoring weights
- exact confidence thresholds
- every possible emotion category
- every conversational ambiguity pattern
- all Japanese colloquial variants
- analyzer prompt wordingの最終形
- P1 Goldenの完全fixture set
- model-specific tolerance

これらは**実際の失敗例を収集してから仕様化**する。

---

# 6. ERへの影響

なし。

本書は試験仕様であり、Domain ER / Technical ERに新Entityを追加しない。
Golden fixtureは実装リポジトリ側のtest/evaluation artifactとして保持する想定。

---

# 7. 実装着手判断

Analyzer部分については、以下があればCodex着手可能な十分条件とする。

- `TurnAnalysisV1` field contract
- Validator/Projector ownership境界
- 上記P0 Golden 7件
- schema invalid / stale revision / secret / undelivered evidenceのnegative invariant

P1 Goldenの詳細化は**実装開始のブロッカーにしない**。
