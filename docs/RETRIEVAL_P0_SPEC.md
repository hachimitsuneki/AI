# RETRIEVAL_P0_SPEC.md

- Project: 自立型AI / 継続人格型デジタルコンパニオン
- Scope: Text v0.1 P0 Retrieval
- Version: retrieval-p0-v1
- Updated: 2026-09-27 JST
- Status: 非コード実装仕様 / Codex着手前
- Principle: **実装前に必要な境界だけ固定し、scoringの細部は実測後に育てる**

---

# 1. 目的

Retrievalの役割は、現在のユーザー発言に関連する過去情報を **canonical stateから安全に候補化すること**。

Retrievalは以下をしない。

- Memory / Self / User / Relationshipを更新しない。
- 「この記憶を必ず会話で言う」と決めない。
- LLM用Promptの最終採否を決めない。
- soft-deleted / private suppression / secret境界を破らない。
- Analyzer未commit proposalを事実として検索対象へ昇格しない。

P0では、**extracted Memory + canonical raw conversation** のhybrid retrievalを扱えることを実装境界とする。

---

# 2. 所有権

```text
Canonical Domain
    ↓ read only
Retrieval
    ↓
RetrievalSnapshotV1
    ↓
Context Builder
    ↓
ContextCapsuleV1
```

- Retrieval: 「関連候補」を返す。
- Context Builder: token budget / provider privacy / prompt構造を見て、実際にMainへ入れる候補を決める。
- Domain Update Layer: Memory等の確定mutationを行う。
- Retrievalはcanonical Domainのwriterではない。

---

# 3. `RetrievalRequestV1`

実装言語の型名は変更可能だが、意味契約は維持する。

| Field | 必須 | 型の意味 | P0ルール |
|---|---:|---|---|
| `schema_version` | yes | const | `retrieval-request-v1` |
| `turn_id` | yes | canonical Turn reference | 実在Turn |
| `query_text` | yes | string | canonical user text。未確定ASR partialはText P0では不可 |
| `state_revision` | yes | integer/revision | 検索開始時のDomain revision |
| `scope` | yes | object | `ai_identity_id`, `user_profile_id`, `conversation_id`を最低限識別 |
| `allowed_source_classes` | yes | set enum | `memory_item`, `raw_message` |
| `excluded_memory_statuses` | yes | set enum | `soft_deleted`を必ず含む |
| `max_result_count` | yes | positive integer | 具体default/上限はRuntime Profile所有 |
| `context_budget_hint` | yes | token/size hint | Context Builderの最終budgetではない |
| `retrieval_profile_id` | yes | string/version ref | scoring/fusion設定の再現用 |

任意:

| Field | 用途 |
|---|---|
| `explicit_reference_hints` | 「前に話したX」「昨日の話」等、明示参照がdeterministicに取れた場合 |
| `hot_context_refs` | 直近Turnで既に使った候補の再利用ヒント |
| `prefetch_marker` | Voice将来用。P0 Textでは通常null |

## 3.1 `scope`

P0では少なくとも以下を区別できる。

```text
AI identity
User profile
Current conversation
```

current conversationだけへ検索を限定する、という意味ではない。
同じAI/Userの過去Conversationを横断Recallできることがv0.1の目的。

---

# 4. `RetrievalSnapshotV1`

| Field | 必須 | 型の意味 | P0ルール |
|---|---:|---|---|
| `schema_version` | yes | const | `retrieval-snapshot-v1` |
| `retrieval_run_id` | yes | unique reference | Traceへ接続 |
| `turn_id` | yes | reference | requestと一致 |
| `request_state_revision` | yes | revision | request時のrevision |
| `completion_state_revision` | yes | revision | 完了時に観測したrevision |
| `status` | yes | enum | `ok`, `degraded`, `unavailable` |
| `degraded_reasons` | yes | array enum | 空配列可 |
| `results` | yes | array | 0件が正常 |
| `profile_id` | yes | string/version | requestのprofileと対応 |
| `elapsed` | yes | structured metrics | lexical / semantic / fusion / totalを利用分だけ |

`results=[]`は失敗とは限らない。関連情報がない場合の正常結果を許す。

---

# 5. `RetrievalResultV1`

| Field | 必須 | 意味 |
|---|---:|---|
| `result_id` | yes | snapshot内の結果識別 |
| `source_kind` | yes | `memory_item` または `raw_message` |
| `source_ref` | yes | 実在canonical source ID |
| `source_class` | yes | `episode`, `claim`, `raw_user_message`, `raw_assistant_message` 等 |
| `source_time` | yes | event/message/claimに対応する時刻 |
| `temporal_role` | yes | `current`, `historical`, `event`, `unknown` |
| `source_status` | yes | 例: `active`, `archived`, `superseded`; soft_deletedは存在してはならない |
| `content_for_context` | yes | Context Builderが扱えるbounded text/summary |
| `evidence_refs` | yes | provenanceとして辿れるsource references |
| `signals` | yes | 実際に利用したscore signalだけ |
| `final_rank` | yes | 1始まり等の具体表現は実装で統一 |
| `privacy_class` | yes | Context Builderがremote送信可否を再評価できる分類 |

## 5.1 `signals`

P0で存在し得るsignal:

```text
lexical
semantic
recency
importance
explicit_reference
archive_penalty
```

すべて必須ではない。

**exact weight / normalization / fusion formulaはP0で固定しない。**

必要なのは、

> 「なぜこの候補がこの順位になったかを後から比較できる」

こと。

---

# 6. P0 Retrieval Strategy

```text
                query
                  │
         ┌────────┴────────┐
         ↓                 ↓
   lexical retrieval   semantic retrieval
         │                 │
         └────────┬────────┘
                  ↓
           versioned fusion
                  ↓
          bounded candidates
                  ↓
      RetrievalSnapshotV1
```

## 決定

- lexicalとsemanticを並列実行可能にする。
- extracted Memoryとcanonical raw messageの双方を候補にできる。
- rerankerはP0必須ではない。
- query rewriting用generative LLM callは通常critical pathに置かない。
- fusion方式は`retrieval_profile_id`で交換可能にする。

## 今は決めない

- semantic 45% / lexical 20% 等の固定weight。
- similarity thresholdの最終値。
- reranker起動threshold。
- embedding modelの最終採用。
- chunk sizeの最終値。
- raw conversationとMemoryの固定比率。

これらは初期実働ログとbenchmark後に決める。

---

# 7. Canonical Source Rule

## 7.1 Memory

候補化可能:
- ACTIVE Memory。
- ARCHIVED Memory。ただし通常は低優先。明示参照等で再浮上可能。
- historical/superseded Claimは「昔どうだったか」が必要な場合に利用可能な設計を妨げない。

候補化禁止:
- `soft_deleted`
- sourceが実在しないMemory
- forget/privacy境界により不可視なMemory

## 7.2 Raw Conversation

候補化できるのは **canonical MESSAGE** のみ。

Assistant messageでは、

> 実際にUIへdeliveryされたcontentだけ

が検索対象。

未render generation tail、cancelled output、Developer-only raw completionはraw conversation evidenceへ混入させない。

---

# 8. Current vs Historical

Retrievalは過去情報を「現在の事実」に変換しない。

例:

```text
2026-01: User dislikes jump scares
2026-08: User now likes jump scares
```

「現在の好み」へのRecallではactive/current Claimを優先できる。

「昔はどうだった？」ではhistorical/superseded evidenceを返せる。

そのため`RetrievalResultV1.temporal_role`とsourceのstatus/timeをContext Builderへ渡す。

最終的な会話上の解釈はMain/Context側で行い、Retrieval自身が過去を現在として書き換えない。

---

# 9. Revision / Forget Race

これはP0で細かく守る。

```text
Retrieval開始
state_revision = 100

↓
結果候補 M42 を取得

↓ その間

User Forget
state_revision = 101
M42 = soft_deleted

↓
Context Builder
```

`completion_state_revision != request_state_revision`の場合、Context Builder/Repository境界で候補参照を再検証する。

M42が現在不可視なら**Promptへ入れない**。

つまり、

> Retrieval Snapshotが一度作られたからといって、後のforgetを無視してよいわけではない。

Snapshot自体はaudit用に保持可能だが、privacy/forget ruleが常に優先される。

---

# 10. Degradation Contract

| 状況 | Retrieval結果 | Chat |
|---|---|---|
| semantic failure | lexical only / `degraded` | 継続 |
| lexical failure | semantic only / `degraded` | 継続 |
| optional auxiliary signal failure | 残りsignalでrank | 継続 |
| timeout | deadlineまでに得たcandidate、なければempty | 継続 |
| lexical + semantic failure | `results=[]`, `unavailable` | recent contextで継続 |
| source integrity violation | 該当resultをreject + trace | 継続可能 |
| privacy/forget revalidation failure | 該当sourceをContextから除外 | 継続 |

Recall障害だけで通常Chat全体を停止させない。

---

# 11. P0 Invariants

必須:

1. soft-deleted Memory returned = **0**
2. non-canonical / undelivered assistant tail returned = **0**
3. hallucinated source reference = **0**
4. RetrievalによるDomain mutation = **0**
5. lexical/semantic片系障害でも会話継続可能
6. 両系統障害でもempty degraded snapshotを返せる
7. exact source provenanceへ辿れる
8. state revisionが変化した場合、Context投入前にvisibilityを再検証できる
9. `Recall == Mention`にしない
10. profile/versionを変えたA/B比較がTraceから識別できる

---

# 12. 最小Golden

実装前には以下だけ固定する。score値の一致は要求しない。

## `RET-GOLD-001` Forget boundary

- Given: relevant Memoryが`soft_deleted`
- Expect: resultへ出ない
- Must not: Prompt候補/remote contextへ復活

## `RET-GOLD-002` Delivery truth

- Given: Assistant generationの後半がcancelされ、UIへ未render
- Expect: raw message retrieval対象はrender済みcanonical contentのみ
- Must not: 未delivery tailを検索結果に含める

## `RET-GOLD-003` Semantic failure

- Given: semantic backend failure
- Expect: lexical result + `degraded`
- Must not: Chat hard fail

## `RET-GOLD-004` Total recall failure

- Given: lexical/semantic両方 unavailable
- Expect: empty `RetrievalSnapshotV1`
- Chat: recent contextでMainへ進める

## `RET-GOLD-005` Forget race

- Given: Retrieval後、Context生成前にsourceがsoft delete
- Expect: revision mismatchを検出し再検証
- Must not: deleted sourceをMainへ渡す

これ以上のranking Goldenは、実働ログを得てから追加する。

---

# 13. ER影響

新Entity追加なし。

既存:

```text
CONVERSATION
  └─ RETRIEVAL_RUN
       └─ RETRIEVAL_RESULT
```

で足りる。

実装時に論理属性として以下をTrace可能にする:

`RETRIEVAL_RUN`
- `profile_id`
- request/completion state revision
- status/degraded reason
- elapsed breakdown

`RETRIEVAL_RESULT`
- source kind/ref
- temporal role/source status
- signal breakdown
- final rank
- privacy class

物理DB列にするかJSON traceへ持つかは実装時に決めてよい。

---

# 14. Codex着手時のDefinition of Done

`WP-TXT-03 Retrieval`は以下で完了とみなせる。

- `RetrievalRequestV1 → RetrievalSnapshotV1`の契約を満たす。
- lexical/semanticの双方を差替可能な境界で扱う。
- exact fusion weightをハードコードされた人格仕様として扱わない。
- degraded contractを満たす。
- canonical/forget/delivery truthを破らない。
- `RET-GOLD-001〜005`を通せる構造になっている。
- RetrievalだけではDomain stateを変更できない。
- Context Builderがcandidateを最終選択できる。

---

# 15. 保留（意図的）

初期実働後に決める:

- 最終Embedding model
- FTS tokenizer設定
- chunking方式
- exact score weight
- score normalization
- reranker有無/起動条件
- hot-context cache TTL
- archived penalty
- historical Claim ranking
- result count / token budgetの最終default
- entity-aware retrieval追加

これらは未検討ではなく、**育成型開発のため意図的に実測後へ保留**する。
