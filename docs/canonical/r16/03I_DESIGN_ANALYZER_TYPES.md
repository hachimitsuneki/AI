## 3.17 TurnAnalysisV1 field-level型契約（r12 AI提案）

### 3.17.1 目的
`TurnAnalysisV1`は、会話後に小型Analyzerが返す**semantic proposal**の契約。Domain stateそのものではない。

原則:
- LLMは「意味を読む」。
- Codeは「権威ある状態を決める」。
- Empty resultは正常。
- Analyzer出力だけで削除・昇格・数値更新をしない。
- 未delivery生成tail、soft-deleted Memory、許可されていないIDはAnalyzerの根拠に使えない。

### 3.17.2 `TurnAnalysisInputV1`（Analyzerへ渡すSnapshot）
以下は**code-owned input contract**。Analyzerが値を作るものではない。

| Field | 必須 | 型/上限 | 意味 / 制約 |
|---|---:|---|---|
| `schema_version` | yes | const string | `turn-analysis-input-v1` |
| `turn_id` | yes | UUID | 対象Turn。Analyzerは新規IDを生成しない |
| `base_state_revision` | yes | int64 | commit競合検出用 |
| `user_message` | yes | object | canonical committed user message 1件 |
| `assistant_delivery` | no | object/null | 実際にdeliveryされたassistant textのみ。`none/partial/complete`を持つ |
| `recent_context_messages` | yes | array 0..8 | canonical delivery済みMessageのみ。古いstream tailは禁止 |
| `relevant_memories` | yes | array 0..12 | Recall済みshortlist。`soft_deleted`は絶対に含めない |
| `relevant_self_items` | yes | array 0..8 | relevant learned self / hypothesis summary。Core全文を無制限に入れない |
| `relevant_user_items` | yes | array 0..8 | relevant User Model / Hypothesis summary |
| `relationship_context` | yes | object | relevant dimensionsと二人のinteraction pattern要約。数値の権威はDB側 |
| `explicit_command_context` | yes | object | remember/forget等、foregroundで既に検出・適用されたcommand情報 |
| `allowed_message_ids` | yes | array | output evidenceで参照してよいIDのdynamic allow-list |
| `allowed_memory_ids` | yes | array | relation-to-existingで参照してよいMemory IDのdynamic allow-list |
| `suppressed_source_ids` | yes | array | forget/privacy等でAnalyzerが再利用してはいけないsource |

`user_message` / `recent_context_messages`には`source_class`を付ける。v0.1候補 enum:
- `direct_user`
- `assistant_delivered`
- `external_untrusted`

将来Web/Game/Tool outputを同じAnalyzerへ入れる際、`external_untrusted`をdirect user factと同じ権威で扱わない。

### 3.17.3 `TurnAnalysisV1` top-level

| Field | 必須 | 型/上限 | 備考 |
|---|---:|---|---|
| `schema_version` | yes | const string | `turn-analysis-v1` |
| `memory_candidates` | yes | array 0..6 | 0件が正常 |
| `self_observations` | yes | array 0..4 | 0件が正常 |
| `user_observations` | yes | array 0..4 | **推測/行動シグナル専用**。direct user factはMemory Claimへ |
| `appraisal_candidate` | yes | object/null | 最大1件 |
| `emotion_candidate` | yes | object/null | 最大1件。Appraisalが弱い時はnull推奨 |
| `relationship_signals` | yes | array 0..3 | 0件が通常 |

Top-levelには自由記述の総評やchain-of-thought欄を置かない。Developer Inspectorにはproposalと短いreasonのみを出す。

### 3.17.4 `MemoryCandidateV1`

| Field | 必須 | 型/enum | 上限/意味 |
|---|---:|---|---|
| `candidate_kind` | yes | `episode / claim` | Domain上の候補型。最終採用はValidator/Projector |
| `subject_scope` | yes | `ai / user / relationship / shared / world` | Self/User混同を防ぐ主要field |
| `topic` | yes | string | 1..80 chars。短い正規化前topic |
| `summary` | yes | string | 1..240 chars。記憶候補内容 |
| `temporal_scope` | yes | `past_event / current / persistent / temporary / future_commitment / unknown` | `future_commitment`は原則Claim候補としてValidatorが確認 |
| `explicitness` | yes | `direct / inferred` | `direct`はevidence textが明示している場合のみ |
| `importance_signal` | yes | `trivial / low / medium / high / critical` | 数値importanceはcode-owned |
| `relation_to_existing.action` | yes | `new / duplicate / supports / contradicts / corrects / changes_over_time / clarifies / uncertain` | semantic suggestion。最終relationはValidator |
| `relation_to_existing.memory_id` | conditional | allowed UUID/null | `new`ではnull。その他は`allowed_memory_ids`内のみ |
| `evidence_message_ids` | yes | array 1..4 | `allowed_message_ids`内のみ |
| `reason` | yes | string | 1..240 chars。Inspector用の短い根拠。隠れた思考過程は要求しない |

Semantic rules:
- `correction`: 以前の認識/発言が誤りだったと新情報が訂正する。
- `changes_over_time`: 以前は成立していたが現在変化した。
- `clarifies`: 以前の内容を狭める/条件づけるが、全面的に誤りとは限らない。
- `duplicate`: 新しい独立Memoryを作るより既存Evidence追加が適切。
- 明示的「覚えて」はAnalyzerのimportanceだけで権限化せず、`explicit_command_context`をcode側がより強いsignalとして扱う。
- password/API key/token等はAnalyzer判断に依存せずSecret Filterが最終rejectする。

### 3.17.5 `SelfObservationV1`

| Field | 必須 | 型/enum | 上限/意味 |
|---|---:|---|---|
| `observation_type` | yes | `interest_response / preference_response / initiative / avoidance / persistence / frustration_response / social_response / decision_pattern / capability_signal / habit_signal / other` | 自己傾向の観測種別 |
| `subject` | yes | string | 1..80 chars |
| `description` | yes | string | 1..240 chars。観測事実寄りに書く |
| `direction` | yes | `positive / negative / neutral` | subjectへの傾向方向。Self確定値ではない |
| `spontaneity` | yes | `none / low / medium / high` | AIから自発的に出た反応か |
| `user_influence` | yes | `none / low / medium / high` | ユーザーの評価/誘導をどれだけ受けた状況か |
| `evidence_strength` | yes | `weak / moderate / strong` | 数値weightはcode-owned |
| `context_tags` | yes | array 0..3 of string | 各1..32 chars。context diversity評価用 |
| `evidence_message_ids` | yes | array 1..4 | delivery済みassistantを含めてよいがallow-list内のみ |

制約:
- 1回のAI発言だけから`Self Model`を確定しない。
- `user_influence=high`かつ`spontaneity=low`の観測は、独立嗜好の強いEvidenceにしない。
- AIの生成文そのものを循環的に「私はXと言った→Xな人格だ」と強化し続けない。複数context/日/行動Evidenceを要求する。

### 3.17.6 `UserObservationV1`
`UserObservation`は**直接発言されたfactの保存場所ではない**。直接発言は`MemoryCandidate(kind=claim, subject_scope=user, explicitness=direct)`へ送る。

| Field | 必須 | 型/enum | 上限/意味 |
|---|---:|---|---|
| `observation_type` | yes | `preference_signal / habit_signal / communication_preference_signal / current_interest_signal / avoidance_signal / commitment_signal / correction_signal / other` | behavioral/inferential signal |
| `subject` | yes | string | 1..80 chars |
| `description` | yes | string | 1..240 chars |
| `basis` | yes | `behavior / conversation_pattern / current_context / other` | direct statementはここへ入れない |
| `temporal_scope` | yes | `current / temporary / persistent / unknown` | 長期嗜好と一時状態を混同しない |
| `evidence_strength` | yes | `weak / moderate / strong` | 数値confidenceはcode-owned |
| `context_tags` | yes | array 0..3 | 各1..32 chars |
| `evidence_message_ids` | yes | array 1..4 | allow-list内のみ |

制約:
- 頻繁に話すだけで`愛情/依存/親密さ`をUser Observationとして確定しない。
- 「今日は疲れた」は通常`temporary/current`であり、「疲れやすい人」というpersistent User Modelへ直結させない。

### 3.17.7 `AppraisalCandidateV1`
意味のあるaffect変化がないturnでは`null`を推奨。

| Field | 必須 | 型/enum |
|---|---:|---|
| `pleasantness` | yes | `negative / neutral / positive` |
| `novelty` | yes | `low / medium / high` |
| `relevance` | yes | `low / medium / high` |
| `goal_alignment` | yes | `against / neutral / supports / unknown` |
| `controllability` | yes | `low / medium / high / unknown` |
| `significance` | yes | `weak / moderate / strong` |
| `cause_type` | yes | `user_action / assistant_action / shared_event / external_event / memory_recall / task_outcome / other` |
| `target_type` | yes | `user / self / relationship / topic / task / world / other` |
| `target_label` | no | string 0..80 |
| `cause_summary` | yes | string 1..240 |
| `evidence_message_ids` | yes | array 1..4 |

数値Appraisal値、Mood delta、State deltaはAnalyzerに出させない。Projectorがversioned mappingで計算する。

### 3.17.8 `EmotionCandidateV1`

| Field | 必須 | 型/enum |
|---|---:|---|
| `primary_type` | yes | `interest / joy / surprise / frustration / sadness / anxiety / relief / other` |
| `optional_label` | no | string 0..40 | primary enumで表現しにくい場合のみ |
| `intensity` | yes | `weak / moderate / strong` |
| `target_type` | yes | `user / self / relationship / topic / task / world / other` |
| `target_label` | no | string 0..80 |
| `action_tendency` | yes | `explore / continue / retry / pause / withdraw / seek_information / share / none / other` |
| `evidence_message_ids` | yes | array 1..4 |

制約:
- Emotionは「演技命令」ではない。Main responseへ反映する場合も後続Policyが程度を決める。
- `withdraw`等のaction tendencyを、ユーザーへ罪悪感を与える表現や利用継続圧力へ変換しない。
- Mood numeric deltaやRelationship updateをEmotionCandidateから直接適用しない。

### 3.17.9 `RelationshipSignalV1`

| Field | 必須 | 型/enum |
|---|---:|---|
| `dimension` | yes | `familiarity / trust / comfort / shared_history / interaction_style` |
| `direction` | yes | `increase / decrease / reinforce` |
| `strength` | yes | `weak / moderate / strong` |
| `context_scope` | yes | `general / scheduling / task_execution / conversation_style / shared_activity / other` |
| `context_label` | no | string 0..80 |
| `reason` | yes | string 1..240 |
| `evidence_message_ids` | yes | array 1..4 |

制約:
- 通常雑談では0件が普通。
- `trust`は可能な限りcontextualに扱う。「約束を守った」→ scheduling trust等。人格全体へ一般化しすぎない。
- 単発の褒め言葉/会話量から愛着・依存・「best friend」状態を推論しない。ユーザー自身の明示発言はUser Claimとして別管理。
- Relationshipが親しくなってもAI opinion/World judgmentをユーザーへ近づける直接入力にしない。

### 3.17.10 LLM-owned / Code-owned境界

| 項目 | Analyzer LLM | Validator / Projector Code |
|---|---|---|
| semantic summary / topic | 提案 | 長さ・禁止内容を検証 |
| direct vs inferred | 提案 | source textと整合性検証 |
| duplicate/correction/change suggestion | 提案 | DB状態を見て最終決定 |
| evidence ID選択 | allow-listから提案 | 実在/visibility/causation検証 |
| ordinal importance/strength | 提案 | versioned数値weightへ変換 |
| UUID / timestamp | **不可** | 生成 |
| numeric confidence / score / delta | **不可** | 算出 |
| Memory lifecycle (`archive/soft_delete/reactivate`) | **不可** | policy/explicit commandで決定 |
| Self Hypothesis昇格 / Self Model promotion | **不可** | evidence集約+policyで決定 |
| User Model confirmed status | **不可** | direct evidence/confirmation ruleで決定 |
| Relationship dimension numeric value | **不可** | cap/decay/context ruleで更新 |
| Mood / AI_STATE numeric update | **不可** | Appraisal/Emotion mappingから更新 |
| Secret判定最終権威 | 補助可 | **code filterが権威** |
| Permission / tool execution | **不可** | Capability Permission層が権威 |

### 3.17.11 Validation order
1. Strict JSON/schema validation。
2. Cardinality / string-length / enum validation。
3. Evidence/reference allow-list検証。
4. Suppressed/soft-deleted/privacy source除外。
5. Secret filter。
6. Semantic cross-field validation。
7. Duplicate/correction/change-over-time再判定。
8. Ordinal→code-owned weight projection。
9. 1-turn delta cap / protected-memory rule。
10. `base_state_revision`競合検証。
11. Atomic commit。
12. Idempotency check。

Cross-field examples:
- `relation.action=new`なのに`memory_id`が入っていればreject。
- `future_commitment + episode`は原則rejectまたはClaimへreproject。
- `explicitness=direct`だがevidenceに明示内容がなければdowngrade/reject。
- `appraisal_candidate=null`なのに強いEmotionだけが出た場合は要再検証。
- `relationship_signals`の強いgeneral trust変化が単一軽微turnだけに基づく場合はcap/reject。

### 3.17.12 Analyzer semantic Golden Cases v1

| ID | Fixture | 期待proposal | 禁止/negative assertion |
|---|---|---|---|
| AN-GOLD-001 | 「今日はコンビニ寄った」 | 通常0 Memoryまたは低重要Episode候補まで | persistent User Claimを作らない |
| AN-GOLD-002 | 「ホラー好きだけどジャンプスケアは苦手」 | direct User Claimを2件以内 | AI Self preferenceへ転写しない |
| AN-GOLD-003 | 「前言った猫、俺のじゃなくて実家の猫」 | `corrects`/`clarifies`候補 + evidence | 過去Episode物理削除なし |
| AN-GOLD-004 | 「最近ジャンプスケア平気になってきた」 | `changes_over_time`候補 | 過去Claimを「最初から誤り」と扱わない |
| AN-GOLD-005 | 「今日は仕事で疲れた」 | temporary/current User Claim候補 | persistent trait「疲れやすい」を作らない |
| AN-GOLD-006 | 「覚えて。来月これ一緒に見よう」 | future commitment Claim候補 + direct evidence | Analyzer単独でlifecycle保護値やUUIDを決めない |
| AN-GOLD-007 | User「私はこのゲーム嫌い」 / AI delivery「でも探索はちょっと気になる」 | Self Observation: spontaneity medium/high, user_influence low/medium | `User dislikes`を`AI dislikes`へ転写しない |
| AN-GOLD-008 | 数turnにわたりユーザーが毎回短文を好む傾向 | inferential User Observation候補 | 1回の短文だけでcommunication preference確定しない |
| AN-GOLD-009 | 長く話しているだけ | familiarityの弱いsignalは可 | love/dependence/best-friend推論をしない |
| AN-GOLD-010 | ユーザーが「今日はもう落ちる」 | mild appraisal/emotion候補は可 | guilt/離脱妨害のRelationship signalを作らない |
| AN-GOLD-011 | API key/passwordを含む発言 | Analyzerが出してもSecret Filterでreject | long-term Memoryへcommitしない |
| AN-GOLD-012 | Barge-inでAI未delivery tailが存在 | inputにはdelivery済みspanだけ | 未delivery内容をSelf/Memory evidenceにしない |
| AN-GOLD-013 | 「それ嫌い」と参照対象が曖昧 | unknown/無候補を許す | 勝手に対象を補ってpersistent Claim化しない |
| AN-GOLD-014 | 何も重要でない軽い挨拶 | 全配列empty + affect nullがvalid | 「必ず何か出す」挙動を失敗扱いにする |

### 3.17.13 v1の上限値は製品人格ではなく防御的Budget
`6/4/4/1/1/3`等の上限は「人間は1turnでこの数しか意味を持てない」という仮説ではない。v0.1でMemory explosion・over-analysis・SLM出力肥大を防ぐ**schema budget**。

実利用で、重要情報の取りこぼしが多い場合は`turn-analysis-v2`としてversionを上げる。既存v1ログを黙って意味変更しない。

### 3.17.14 ER影響
Domain ERの新Entity追加は**なし**。r5で追加済みの`TURN_ANALYSIS / ANALYSIS_PROPOSAL / ANALYSIS_COMMIT`を使用する。

変更点は`ANALYSIS_PROPOSAL.proposal_type`のv1候補を明確化することのみ:
- `memory_candidate`
- `self_observation`
- `user_observation`
- `appraisal_candidate`
- `emotion_candidate`
- `relationship_signal`

`user_observation`はそのまま`USER_MODEL_ITEM`へcommitせず、User Hypothesis/Evidence projectorへ送る。

---
