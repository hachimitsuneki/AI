# 17. Explicit Remember / Forget P0 boundary (r16 readiness patch)

この節はDefinition of Ready監査で見つかった唯一のP0曖昧点を埋める最小仕様。
自然言語のあらゆる削除表現を完全仕様化することは目的にしない。

## 17.1 共通原則

- `remember` / `forget` の**検出結果そのもの**はcanonical Turnへ紐づくdurable command markerとして残す。
- semantic Domain mutationは既存`SUB-DUP-01 Domain Update Layer`だけが行う。
- command detector / Main LLM / AnalyzerがMemoryを直接soft-delete/insertしない。
- commandが曖昧な場合に推測だけで破壊的変更を行わない。

## 17.2 Minimal `ExplicitCommandV1`

実装言語の型名は変更可能。意味契約のみ固定する。

| Field | 必須 | 意味 |
|---|---:|---|
| `schema_version` | yes | `explicit-command-v1` |
| `command_id` | yes | code-owned ID |
| `turn_id` | yes | commandを含むcanonical User Turn |
| `kind` | yes | `remember | forget` |
| `resolution_status` | yes | `resolved | ambiguous | not_found | blocked` |
| `target_refs` | yes | resolved時のcanonical Memory/Message refs。0件可 |
| `resolution_basis` | yes | `ui_selected | explicit_id_or_reference | unique_current_context | unique_retrieval_match | none` |
| `created_state_revision` | yes | 検出時Domain revision |

LLMに新規target IDを生成させない。

## 17.3 Forget

### Target resolution priority

1. UIでユーザーが明示選択したMemory/Message。
2. canonical IDや一意な明示参照で特定できる対象。
3. current context / bounded retrievalから**一意に**解決できる対象。
4. 複数候補/不明なら`ambiguous`。

### Ambiguous rule

`ambiguous` / `not_found`では**何もsoft-deleteしない**。
必要なら通常会話として「どの話を指しているか」を確認する。

### Resolved forget commit

`resolved`ならforegroundでDomain Update Layerへ送り、atomicに:

- target `MEMORY_ITEM.status = soft_deleted`へ遷移。
- `MEMORY_LIFECYCLE_EVENT(SOFT_DELETED, actor=user)`を追加。
- Domain `state_revision`を進める。
- 以後Recall / Context / Analyzer evidence / Self/User/Relationship evidence selectionから除外。
- in-flight Retrieval/Analyzerは新revisionで再検証し、復活を禁止。

Developer auditは残すが、AI側可視性は即座に失う。

## 17.4 Remember

`remember`はforegroundでcommand markerを確定するが、semantic Memory抽出自体はTurn Analyzer + Validator/Projectorを利用してよい。

- `explicit_remember=true`を`TurnAnalysisInputV1.explicit_command_context`へ渡す。
- Analyzerが遅延/失敗してもcommand markerが残るためretry可能。
- 通常Memoryより強いretention signalとして扱う。
- Secret / credential / privacy policyは必ず優先し、`覚えて`でも保存しない。

## 17.5 P0 negative invariants

- 曖昧な`忘れて`で複数Memoryを推測削除しない。
- User ForgetをAnalyzer待ちにしない。
- Forget済みsourceを古いRetrieval/Analyzerから復活させない。
- `覚えて`を理由にsecretを保存しない。
- command marker自体から、忘却対象の内容を新しい長期Memoryとして再生成しない。

## 17.6 Minimal Golden

### `CMD-GOLD-001` Exact forget
- Given: UI-selected / unique resolved Memory M1
- When: user forget command
- Expect: M1 soft_deleted + revision increment
- Must not: M1 appear in later Recall/Context/Analyzer evidence

### `CMD-GOLD-002` Ambiguous forget
- Given: 「この話忘れて」に2つ以上の妥当候補
- Expect: `resolution_status=ambiguous`, mutation 0
- Must not: guess-delete

### `CMD-GOLD-003` Remember secret
- Given: explicit remember + credential
- Expect: command marker remains, Memory persistence rejected/redacted
- Must not: raw secret in long-term Memory

この3件以上の自然言語variantは初期実働後に追加する。
