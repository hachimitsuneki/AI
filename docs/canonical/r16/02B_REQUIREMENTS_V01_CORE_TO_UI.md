### Core
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-CORE-01 | テキストで複数セッション継続会話 | 方向性の合意 | 再起動後も状態復元 |
| REQ-V01-CORE-02 | 初期人格: 好奇心やや高/遊び心やや高/自己主張中/少しいたずらっぽい | 方向性の合意 | 常にふざけず、軽い予測不能性 |
| REQ-V01-CORE-03 | Self/User分離 | 方向性の合意 | User preferenceがSelfへ自動転写されない |
| REQ-V01-CORE-04 | 未形成状態を許す | 方向性の合意 | 「まだ分からない」が正常 |
| REQ-V01-CORE-05 | Observability | AI提案・重要 | 各応答の構造化内部情報を追跡可能 |

### Memory
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-MEM-01 | Memory ItemをEpisode/Claimに分離 | AI提案・強く推奨 | 出来事と現在認識を別管理 |
| REQ-V01-MEM-02 | Memory Candidate Gate | AI提案・重要 | 保存/拒否/重複/訂正理由を記録 |
| REQ-V01-MEM-03 | Recall | AI提案・重要 | Semantic/keyword/recency/importance等で検索 |
| REQ-V01-MEM-04 | Recall ≠ Mention | 方向性の合意 | 取得した記憶を必ず口にしない |
| REQ-V01-MEM-05 | Memory Provenance | AI提案・重要 | 元Messageまで追跡可能 |
| REQ-V01-MEM-06 | Claim Correction | AI提案・重要 | 過去Episodeを壊さずactive Claimを更新 |
| REQ-V01-MEM-07 | Revision種別を区別 | AI提案 | correction/change_over_time/clarification/deletion |
| REQ-V01-MEM-08 | 非破壊的忘却 | AI提案 | v0.1は時間経過だけで物理削除しない |
| REQ-V01-MEM-09 | User Forget | 明示決定 | `soft_deleted`; AIから完全不可視、Developer履歴は残る |
| REQ-V01-MEM-10 | Autonomous Archive | 明示決定 | AIはACTIVE→ARCHIVEDのみ可能。soft delete不可 |
| REQ-V01-MEM-11 | Archived Memory再活性化 | AI提案 | 強い関連/明示言及でACTIVE候補に戻る |
| REQ-V01-MEM-12 | Mention/Recall回数を追跡 | AI提案 | 同じ記憶の蒸し返しを観測可能 |
| REQ-V01-MEM-13 | 明示的な「覚えて」を強い保存シグナルとして扱う | AI提案・強く推奨 | 通常Gateより強く保存するが、秘密情報/認証情報は除外 |
| REQ-V01-MEM-14 | Memory Gateの判断軸を記録 | AI提案・重要 | importance / future usefulness / novelty / stability / relationship-or-commitment relevance / duplication等を追跡 |
| REQ-V01-MEM-15 | Autonomous Archiveに保護条件を設ける | 明示決定の具体化 | Core相当・Promise/Commitment・重要なcurrent Claim・relationship-critical memoryを低重要度だけでArchiveしない |

### Self
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-SELF-01 | Self Observation生成 | AI提案 | 発言/行動から構造化観察を作る |
| REQ-V01-SELF-02 | ユーザー誘導と自発反応のEvidence Weightを分離 | 強く推奨 | independent evidenceを高く評価 |
| REQ-V01-SELF-03 | Hypothesis lifecycle | AI提案 | HYPOTHESIS→TENTATIVE→PROMOTION_CANDIDATE |
| REQ-V01-SELF-04 | 反証を保持 | AI提案 | contradictionでconfidence低下/仮説細分化 |
| REQ-V01-SELF-05 | Learned Self Model | AI提案・重要 | Core人格と経験由来自己認識を分離 |
| REQ-V01-SELF-06 | v0.1でSelf Model昇格を観察可能にする | AI提案 | 自動昇格は慎重/Developer確認可能 |

### User / Relationship
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-USER-01 | User Model | AI提案・重要 | 会話履歴と別に現在理解を保持 |
| REQ-V01-USER-02 | User Hypothesis | AI提案・強く推奨 | 直接確認と推測を分離 |
| REQ-V01-USER-03 | Temporal User Model | AI提案 | current interestとlong-term preference分離 |
| REQ-V01-REL-01 | Relationship多次元化 | AI提案・強く推奨 | familiarity/trust/comfort/shared history/style |
| REQ-V01-REL-02 | Shared Relationship History | AI提案 | 二人に起きた重要Episodeを証拠化 |
| REQ-V01-REL-03 | Relationship Independence | 既存要件具体化 | 親密さが同意圧力にならない |
| REQ-V01-REL-04 | 根拠のないユーザー愛着推論をしない | AI提案・重要 | 利用頻度だけで愛情/依存を断定しない |

### Affect
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-AFF-01 | Appraisal | AI提案・重要 | Self/User/Relationship/Stateを参照して意味評価 |
| REQ-V01-AFF-02 | Emotion Episode | AI提案 | 種類/対象/原因/強度/根拠/行動傾向 |
| REQ-V01-AFF-03 | Mood State | AI提案 | valence/activation/controlを分離保持 |
| REQ-V01-AFF-04 | Affect Decay | AI提案・強く推奨 | 停止中経過時間も反映 |
| REQ-V01-AFF-05 | Affect Separation | AI提案・必須級 | 単発感情でSelf/Relationshipを大幅変更しない |
| REQ-V01-AFF-06 | Emotional Memory Gate | AI提案 | Emotionを自動長期保存しない |
| REQ-V01-AFF-07 | AI_STATEを擬似人間生理ではなくAIとして意味のある状態として扱う | AI提案・重要 | curiosity/social_interest/engagement/fatigue_like等を用い、fatigue_likeを肉体疲労と偽装しない |
| REQ-V01-AFF-08 | Emotion表現を誇張命令にしない | AI提案 | Promptでは「mild frustration + behavior tendency」のように状態と傾向を渡し、演技過剰を避ける |
| REQ-V01-AFF-09 | Affectの非操作原則 | AI提案・重要 | 感情状態をユーザーの利用継続・同意・依存を強制するために使用しない |

### UI
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-UI-01 | Chat-centric UI | 方向性の合意 | 会話を主視覚要素にする |
| REQ-V01-UI-02 | Developer Inspector | AI提案・強く推奨 | Recall/State/Memory Gate/Model等を確認 |
| REQ-V01-UI-03 | Memory Management UI | AI提案・重要 | Memory検索/出典/訂正/削除 |
| REQ-V01-UI-04 | Self Inspector | AI提案 | CoreとLearned Selfを区別表示 |
| REQ-V01-UI-05 | User/Developer mode分離 | AI提案 | 通常UIと育成UIを論理分離 |
| REQ-V01-UI-06 | 汎用的で見やすいChatデザイン | 方向性の合意 | 特殊Dashboard化しない |
| REQ-V01-UI-07 | Motion Design | 方向性の合意 | transitions.devを主要参考; 意味ある状態遷移に限定 |
