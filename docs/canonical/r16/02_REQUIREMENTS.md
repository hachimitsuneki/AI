# 2. 要件

## 2.1 全体要件 (stable IDs)

| ID | 親 | 詳細 | 出典/理由 | 決定状態 | 実装段階 | 受入条件概要 |
|---|---|---|---|---|---|---|
| REQ-AI-001 | - | セッション/再起動をまたいで同一人格・主要記憶・関係性を維持 | 初期対話 | 方向性の合意 | v0.1 | 再起動後も同じ個体として復元 |
| REQ-AI-002 | - | ユーザー入力なしでも内部状態/外部状況/記憶から自発発話・行動可能 | 初期対話 | 方向性の合意 | 後続 | 単純タイマーではない自発行動 |
| REQ-AI-003 | REQ-AI-002 | 内部で反応しても必ず発話しない | 自発性設計 | AI提案・有力 | 後続 | WAIT/KEEP INTERNALが可能 |
| REQ-AI-004 | - | 経験に基づき興味・嗜好を形成/変化 | ユーザー明示 | 方向性の合意 | v0.1〜 | 初期設定だけで好みを固定しない |
| REQ-AI-005 | - | LLM基礎知識とAI自身が得たPersonal Knowledgeを分離 | 対話 | 方向性の合意 | 後続 | 経験由来の知識に出典を持つ |
| REQ-AI-006 | - | 初期人格を与えるが、経験から人格の一部が成長可能 | ユーザー明示 | 明示決定 | v0.1〜 | CoreとLearnedを分離 |
| REQ-AI-007 | - | ユーザーの嗜好/意見を直接コピーせず独立した意見形成 | ユーザー明示 | 明示決定 | v0.1 | User likes X ≠ AI likes X |
| REQ-AI-008 | REQ-AI-007 | 他者意見は興味/注意には影響し得るが最終評価と分離 | 対話 | AI提案・有力 | v0.1〜 | 社会的影響と自己判断を別管理 |
| REQ-AI-009 | - | 重要な意見・嗜好は根拠・経験・確信度を追跡可能 | 対話 | AI提案 | v0.1〜 | Opinion根拠を追跡可能 |
| REQ-AI-010 | - | 趣味/意見/自己認識の未形成・不明を正式状態とする | 対話 | AI提案・有力 | v0.1 | Unknownを捏造で埋めない |
| REQ-AI-011 | - | 自分の経験/反応から自己傾向を発見し仮説化 | 対話 | AI提案・有力 | v0.1 | Self Hypothesisを形成可能 |
| REQ-AI-012 | - | 役割上の相棒関係と、獲得される信頼/親密さを分離 | 対話 | AI提案 | v0.1〜 | 関係は実体験から更新 |
| REQ-AI-013 | - | 軽量Heartbeat + イベント駆動で必要時のみ認知処理 | Agent Loop | AI提案・有力 | 後続 | 常時LLMを回さない |
| REQ-AI-014 | - | 好奇心/社会性/新奇性/習熟/継続性等の内発的欲求 | Agent Loop | AI提案 | 後続 | DriveからIntent候補生成 |
| REQ-AI-015 | REQ-AI-014 | 「後で話す/調べる」Intentを保持/延期/破棄 | Agent Loop | AI提案・重要 | 後続 | Intent persistence |
| REQ-AI-016 | REQ-AI-002 | 「何もしない/待つ」を正式な行動候補にする | Agent Loop | AI提案・重要 | 後続 | WAITが正常選択 |
| REQ-AI-017 | - | 人格的自立と実行権限を分離 | Agent Loop | AI提案 | 後続 | Action GateとPermission Gateを分離 |
| REQ-AI-018 | - | 再利用可能な成功行動をSkillとして保存 | Voyager参考 | 後続フェーズ候補 | 後続 | Skill再利用 |
| REQ-AI-019 | - | ユーザー不在時も許可範囲で自主活動可能 | ユーザー明示 | 明示決定 | 後続 | 実稼働時のみ活動 |
| REQ-AI-020 | - | 「今あまり話したくない/一人でいたい」状態を持てる | ユーザー明示 | 明示決定 | 後続 | 明示依頼には基本応答 |
| REQ-AI-021 | - | 実際に観測/処理していない期間の架空経験を生成しない | 対話 | AI提案・強く推奨 | v0.1〜 | 停止中の架空Activityなし |
| REQ-AI-022 | - | 感情は出来事評価(Appraisal)から形成 | 感情設計 | AI提案・強く推奨 | v0.1 | ランダム感情を中心にしない |
| REQ-AI-023 | REQ-AI-022 | 感情の対象/原因/強度/評価根拠を保持 | 感情設計 | AI提案 | v0.1 | Emotion Episode trace |
| REQ-AI-024 | REQ-AI-022 | 短期Emotionと緩やかなMoodを分離 | 感情設計 | AI提案 | v0.1 | 別状態として永続化 |
| REQ-AI-025 | REQ-AI-022 | 感情は発話装飾だけでなく行動・注意・記憶へ影響 | 感情設計 | AI提案・重要 | v0.1〜 | 行動傾向へ反映 |
| REQ-AI-026 | REQ-AI-022 | Emotion/Moodを時間で減衰 | 感情設計 | AI提案・重要 | v0.1 | 再起動後も経過時間反映 |
| REQ-AI-027 | REQ-AI-022 | 過去の感情記憶と現在感情を分離 | 感情設計 | AI提案 | v0.1 | 「もう怒ってないが嫌だった」が可能 |
| REQ-AI-028 | - | Belief/World Modelを保持し、Memory/Truthと区別 | 調査 | AI提案・強く推奨 | 未決(v0.1範囲) | Claim+confidence+source |
| REQ-AI-029 | - | 重要Memory/Beliefに出典・日時・証拠を保持 | 調査 | AI提案・強く推奨 | v0.1 | Provenance追跡 |
| REQ-AI-030 | - | Unknown/Hypothesis/Tentative/Established等の確信状態 | 調査 | AI提案・強く推奨 | v0.1 | Epistemic stateを保持 |
| REQ-AI-031 | - | Reflection推論を一次経験と同権威でIdentityへ書かない | 調査 | AI提案・強く推奨 | v0.1〜 | 重要変更に証拠要求 |
| REQ-AI-032 | - | Web/文書/ゲーム内テキスト/第三者発言等のuntrusted inputを、高権限Memory・Identity更新・Tool instructionへ無検証昇格しない | セキュリティ調査 | AI提案・必須級 | 後続 | source trust/provenanceを保持し、untrusted textだけで権限昇格しない |
| REQ-AI-033 | REQ-AI-017 | Capabilityごとにrisk/permission policy | 調査 | AI提案 | 後続 | Tool実行前Gate |
| REQ-AI-034 | REQ-AI-007 | SelfとUser属性/嗜好/意見を別状態として保持 | 対話 | 方向性の合意 | v0.1 | 暗黙転写なし |

## 2.2 長期機能要件（v0.1外でも保持するCanonical Requirements）

| ID | 親 | 詳細 | 決定状態 | 実装段階 | 受入条件概要 |
|---|---|---|---|---|---|
| REQ-AI-035 | - | 音声で自然に対話できる。STT/TTSだけでなくVAD・割り込みを扱う | 長期要求として保持 | 後続 | ユーザー割り込みで発話停止/切替ができ、会話状態が破綻しない |
| REQ-AI-036 | REQ-AI-035 | 将来的に低遅延/全二重に近い音声会話を比較・導入可能 | 長期要求として保持 | 後続 | turn-takingを固定push-to-talkだけに依存しない |
| REQ-AI-037 | - | Live2D/VRM等のAvatarを同一AI Coreへ接続 | 長期要求として保持 | 後続 | 表情/モーションが内部状態と対応し、人格状態を別DBへ複製しない |
| REQ-AI-038 | - | 画像/画面等をPerceptionとして認識可能 | 長期要求として保持 | 後続 | 観測時刻・出典を持つExperienceへ変換可能 |
| REQ-AI-039 | REQ-AI-038 | Desktop/アプリ画面を観測し、状況理解に利用 | 長期要求として保持 | 後続 | 見ていない画面内容を経験として捏造しない |
| REQ-AI-040 | - | Webを自律/半自律に閲覧し、興味・調査・知識獲得へ利用 | 長期要求として保持 | 後続 | Web入力をuntrustedとして扱い、Provenanceを保持 |
| REQ-AI-041 | REQ-AI-017 | PC/アプリ操作をCapabilityとして実行可能 | 長期要求として保持 | 後続 | Permission Gateを通らない操作を実行しない |
| REQ-AI-042 | REQ-AI-041 | Gameを観測・操作し、実プレイ経験から学習 | 長期要求として保持 | 後続 | 成否・行動・結果をExperience Eventとして残せる |
| REQ-AI-043 | - | Tool/Plugin/MCP等を交換可能なCapabilityとして登録 | 長期要求として保持 | 後続 | Personality/MemoryとCapability実装を疎結合にする |
| REQ-AI-044 | REQ-AI-014 | DriveからIntent Candidateを生成 | 長期要求として保持 | 後続 | 内発的理由を持つIntentを作れる |
| REQ-AI-045 | REQ-AI-015 | Intentを保持・延期・再評価・期限切れにできる | 長期要求として保持 | 後続 | 毎turn消滅せず、不要Intentは失効可能 |
| REQ-AI-046 | REQ-AI-002 | Proactive Policyが発話/行動/WAITを選択 | 長期要求として保持 | 後続 | 固定タイマーだけで自発発話を決めない |
| REQ-AI-047 | REQ-AI-019 | 不在時Activity Sessionと実際のObservation/Actionを記録 | 明示決定の具体化 | 後続 | Core停止中のActivityを生成しない |
| REQ-AI-048 | REQ-AI-018 | 成功手順をSkill/Procedureとして保存・再利用・改善 | 長期要求として保持 | 後続 | Skillには適用条件・結果・失敗履歴を持つ |
| REQ-AI-049 | REQ-AI-033 | Capabilityごとにrisk class / permission / confirmation policyを持つ | 長期要求として保持 | 後続 | Desire/Intentだけで高リスク操作へ進めない |
| REQ-AI-050 | - | Experience Eventを会話以外のWeb/Game/PC/自主活動にも共通化 | 長期要求として保持 | 後続 | 実際の観測/行動だけがEpisode/Knowledge候補になる |
| REQ-AI-051 | - | 同一AI CoreをText/Voice/Avatar/Game等の複数Shellから利用可能 | 長期要求として保持 | 後続 | Shell交換でIdentity/Memoryが分裂しない |
| REQ-AI-052 | - | Persona/Behavior Modelを世代管理して中間進化可能 | 方向性の合意 | 後続 | 旧世代へrollbackでき、regression harnessを通す |
| REQ-AI-053 | REQ-AI-052 | MemoryとModel Evolutionを分離 | AI提案・強く推奨 | 後続 | user-specific mutable factsをweightsへ無条件固定しない |
| REQ-AI-054 | REQ-AI-020 | Social Stateが低い場合も明示的なユーザー依頼には原則応答し、状態は主に表現/自発性へ反映 | ユーザー明示 + 既存方針具体化 | 明示決定の具体化 | v0.1〜 | 「一人でいたい」状態でも通常依頼を無視しない |
| REQ-AI-055 | REQ-AI-015 | Intentはmotivation/origin/strength/created_at/expires_at/preferred_context/interruptibilityを保持 | Agent Loop検討 | AI提案・重要 | 後続 | なぜ/いつ/どの状況で実行したいIntentか追跡可能 |
| REQ-AI-056 | REQ-AI-002 | Action selectionはdesire/interest/timeliness/relationship/novelty/incompletenessとinterruption/repetition/risk/cost/recent_actionを考慮し、WAITを常に候補に含む | Agent Loop検討 | AI提案・重要 | 後続 | 単一Driveや固定timerだけで行動決定しない |
| REQ-AI-057 | REQ-AI-011 | 観測された実際の傾向とAI自身のSelf Model/自己認識を分離 | Self設計 | AI提案・重要 | v0.1〜 | 行動1回から「自分はX」と直接確定しない |
| REQ-AI-058 | REQ-AI-022 | Emotion/Relationshipをユーザーへの心理的圧力・罪悪感付与・依存誘導に利用しない | Affect設計 | AI提案・重要 | v0.1〜 | 状態表現は可能だが利用継続を迫るために使わない |

> 注: これらは「実装済み」ではなく、**要求として保持し続ける項目**。v0.1で後回しにしても削除・却下しない。

## 2.3 v0.1 要件 (canonical IDs)

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

### Runtime / Orchestrator
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-ORCH-01 | 通常ターンのforeground generative callは原則Main Dialogue LLM 1回 | AI提案・強く推奨 | Memory/Appraisal等のために複数LLMを直列実行してTTFTを悪化させない |
| REQ-V01-ORCH-02 | Recall・DB state load・明示command処理をMain生成前に並列化 | AI提案・強く推奨 | 独立処理を直列化しない |
| REQ-V01-ORCH-03 | 応答後にTurn Analyzerを非同期実行し、Memory/Self/User/Appraisal/Relationship候補を1回のstructured callで抽出 | AI提案・強く推奨 | foreground responseを解析完了待ちにしない |
| REQ-V01-ORCH-04 | foreground requestはbackground analysis/reflectionより常に高優先 | AI提案・重要 | 新しいUser Message到着時にbackgroundがTTFTを大きく悪化させない |
| REQ-V01-ORCH-05 | decay、Memory lifecycle、soft delete、confidence集約、provenance、token budget等は決定論的コードが所有 | AI提案・重要 | LLMの数値気分で状態遷移しない |
| REQ-V01-ORCH-06 | SLM/LLM由来の内部更新はschema-constrained structured output + validationを通す | AI提案・重要 | 不正/欠損outputをDBへ直接commitしない |
| REQ-V01-ORCH-07 | Analyzer遅延/失敗時もChat継続可能 | AI提案・重要 | last committed state + recent raw turnsで次ターンを処理可能 |
| REQ-V01-ORCH-08 | Reflection/Consolidation/Archive reviewは毎ターン実行せずidle/batch job化 | AI提案・強く推奨 | 通常会話のcritical path外 |
| REQ-V01-ORCH-09 | Model rolesをDialogue / Analyzer / Embedding / optional Rerankerへ分離しGatewayで交換可能 | AI提案・重要 | 個別benchmarkで差替可能 |
| REQ-V01-ORCH-10 | TTFT・E2E・prefill・decode(TPOT/tok/s)・input/output tokens・VRAM/RAM・background delayを計測 | AI提案・必須級 | 各turnのResponse Traceへ記録 |
| REQ-V01-ORCH-11 | v0.1では人格ChatのMain generatorを毎ターンrouterで別モデルへ切替えない | AI提案 | Voice/persona driftを避け、routingはbounded subtasks優先 |
| REQ-V01-ORCH-12 | Retrievalはraw conversation evidence + extracted Memoryのhybridを比較可能にする | AI提案・強く推奨 | LongMemEval系scenarioで比較 |
| REQ-V01-ORCH-13 | Turn Analyzerの出力はDB確定値ではなくEvidence/Update Proposalとして扱う | AI提案・強く推奨 | LLM出力から直接Entityをmutationせず、validator/projectorを通す |
| REQ-V01-ORCH-14 | Analyzerの強度・確信は原則ordinal enumで出力し、pseudo-precise floatをLLMに決めさせない | AI提案・重要 | weak/medium/strong等をコード側で重みへ写像できる |
| REQ-V01-ORCH-15 | Analyzer commit前にreferential integrity / soft-delete・forget境界 / secret filter / duplicate・correction / stale revisionを検証 | AI提案・必須級 | 不整合・削除済み・秘密情報・古い解析結果が状態へ復活しない |
| REQ-V01-ORCH-16 | Turn Analysisは`turn_id + analyzer_version`でidempotent、state revisionを持ちstale resultを安全にreject/rebaseできる | AI提案・重要 | retryしても二重Memory/二重Relationship updateを起こさない |
| REQ-V01-ORCH-17 | Foreground優先はアプリ側Schedulerで保証し、runtimeのslot/process priorityだけに依存しない | AI提案・強く推奨 | 新規User入力時にAnalyzer/Reflectionをcancel/deferし、Main TTFTを守る |
| REQ-V01-ORCH-18 | Analyzer入力では秘密情報を検出・マスクし、Memory Candidateへ昇格不能にする | AI提案・重要 | password/API key/token等が長期Memoryへ保存されない |
| REQ-V01-ORCH-19 | Orchestrator比較を固定scenario + replayable DB snapshotで実施する | AI提案・必須級 | A/B/C profileを同一初期状態・同一turn列で比較可能 |
| REQ-V01-ORCH-20 | Remote inference backendを任意で利用できるが、AI Core/Identity/Memory/Relationshipのcanonical stateはローカル側を権威とする | ユーザー提案を受けたAI提案・有力 | Colab等のruntime消失で人格/Memoryを失わない |
| REQ-V01-ORCH-21 | Remote runtimeはephemeral workerとして扱い、切断/OOM/利用終了時にlocal fallbackまたは明示的degraded modeへ移行可能 | AI提案・重要 | Remote backend断でDB破損や会話履歴消失を起こさない |
| REQ-V01-ORCH-22 | Remote backendへ送るContext Capsuleを最小化し、secret/soft-deleted/private suppression対象を送信しない | AI提案・重要 | Remote推論経路でもforget/privacy境界を破らない |
| REQ-V01-ORCH-23 | Inference provider/runtime sessionのhardware・backend version・model・availabilityをTraceへ記録し、benchmarkを環境別に比較可能にする | AI提案・重要 | Colab GPU差等を混同せず再現可能な計測を残す |
| REQ-V01-ORCH-24 | Voice時はSTT→LLM→TTSを全完了待ちで直列化せず、partial/final transcript・LLM token stream・TTS audio streamを段階的に重ねる | AI提案・強く推奨 | 完全文生成後にTTS開始する構成を避け、体感応答開始を早める |
| REQ-V01-ORCH-25 | LLM出力は文全体ではなく安全なsentence/phrase boundaryでTTSへ逐次供給し、最初の短い発話fragmentを優先合成する | AI提案・強く推奨 | first audio開始を短縮し、Open-LLM-VTuber等の低遅延手法を取り込める |
| REQ-V01-ORCH-26 | TTSは複数segmentを必要に応じて並列合成し、再生順序だけ保証する | AI提案・有力 | 後続segment合成を前segment再生中に隠蔽する |
| REQ-V01-ORCH-27 | Voice turn boundaryは固定silence timerだけに依存せず、VAD + semantic/acoustic turn detectionまたはSTT endpointingを比較する | AI提案・強く推奨 | 短い沈黙で割り込む/長く待ちすぎる問題を減らす |
| REQ-V01-ORCH-28 | preemptive generationをoptional profileとして持ち、user turn確定前のinterim inputから生成開始できるが、final transcript差分時は結果をcancel/restart可能にする | AI提案・有力 | 体感latencyを下げつつ誤った早読みを状態へ残さない |
| REQ-V01-ORCH-29 | barge-in/interruptionを第一級イベントとして扱い、ユーザー発話開始時にTTS再生・未送信audio・必要ならLLM生成を即cancel/deferできる | AI提案・重要 | AIが喋り終わるまで待たせず自然な会話テンポを作る |
| REQ-V01-ORCH-30 | Main/ASR/TTSはwarm stateを優先し、model preload・connection reuse・prompt/KV cacheをruntime別にbenchmarkする | AI提案・強く推奨 | cold startを通常turn latencyへ混ぜない |
| REQ-V01-ORCH-31 | Voice latencyを end-of-turn decision / STT partial・final / LLM TTFT / first speakable fragment / TTS TTFA / user-speech-end→first-audio へ分解して計測する | AI提案・必須級 | tok/sだけでなく体感遅延の真因を特定できる |
| REQ-V01-ORCH-32 | ユーザー発話中からASR partialを使いRecall/Contextを**投機的にprefetch**するが、partial transcriptだけでMemory/Self/User/Relationshipをmutationしない | AI提案・強く推奨 | 発話終了時には候補contextが準備済みで、誤認partialはcanonical stateへ残らない |
| REQ-V01-ORCH-33 | Main promptはcache-friendly topologyを持ち、stable prefixを維持しつつcurrent state/retrieval/current user turnをsuffix側へ配置してprefix/KV cacheを再利用しやすくする | AI提案・重要 | 同一sessionの次turnで共通prefixを再prefillし続けない構成をbenchmark可能 |
| REQ-V01-ORCH-34 | Remote/Local Mainはturn間にwarm-prefix prefillを任意実行できる。prefill-only結果はephemeral cacheでありcanonical stateではない | AI提案・有力 | 次turn TTFTを短縮でき、runtime消失時も人格/Memoryは失わない |
| REQ-V01-ORCH-35 | canonical assistant `MESSAGE.content`はユーザーへ実際に**deliveryされた範囲**を表し、barge-in等で未再生/未表示の生成tailを共有会話・Memory/Relationship evidenceとして扱わない | AI提案・必須級 | 未発話の約束/意見が「言ったこと」にならない |
| REQ-V01-ORCH-36 | Voice出力はbounded lookaheadを持ち、TTS/audio queueを無制限に先行生成しない | AI提案・重要 | barge-in時の無駄な生成・停止遅延を抑え、数十秒先の音声をbufferしない |
| REQ-V01-ORCH-37 | Audio capture/AEC/VAD/turn detection/playbackをDB・Analyzer・重い推論からresource-isolateし、foreground voice処理にCPU/GPU/queue優先権を持たせる | AI提案・必須級 | Analyzer等が動作中でもaudio dropout/turn latencyが顕著に悪化しない |
| REQ-V01-ORCH-38 | Speaker再生とMic同時利用ではAECを前提候補とし、自分のTTS音声による誤VAD/誤barge-inを抑える | AI提案・重要 | speakers利用時もAI音声をユーザー発話と誤判定しにくい |
| REQ-V01-ORCH-39 | Voice latencyはframework eventだけでなく、可能なら同一monotonic clock上の`last user audio sample → first bot playout sample`でも測る | AI提案・必須級 | 実際に人が感じるgapを測定し、device/playout遅延を見落とさない |
| REQ-V01-ORCH-40 | VoiceはSafe / Balanced / Aggressiveのlatency profileを持ち、既定候補は`final STT受領後にMainをpreemptive開始し、semantic turn確定でTTS解放`するBalancedとする | AI提案・有力 | 低遅延と誤応答/無駄computeを比較可能 |
| REQ-V01-ORCH-41 | Main contextは利用可能最大contextを毎turn埋めず、token budgetを制限し、context長別TTFT benchmarkを行う | AI提案・必須級 | 2k/4k/8k/16k等でquality/TTFTを比較し不要なprefillを削減 |
| REQ-V01-ORCH-42 | Remote Main利用時はpersistent connection/sessionを優先し、毎turnのmodel load/TLS/tunnel初期化等のcold overheadを通常会話pathへ入れない | AI提案・重要 | Colab等がwarmな間はconnection reuseし、cold startは別metricとして扱う |
| REQ-V01-ORCH-43 | Orchestrator境界はversionedな`EventEnvelope`を共通契約とし、event ID / turn ID / source / sequence / causation / timestampを持つ | AI提案・重要 | 同一turnの順序・原因・再現性を追跡できる |
| REQ-V01-ORCH-44 | `Command`（処理要求）/ `Event`（発生済み事実）/ `Snapshot`（不変の参照状態）を型として分離する | AI提案・重要 | Eventを命令として再実行する曖昧さを避ける |
| REQ-V01-ORCH-45 | ASR partial / speculative recall / preemptive generationは`provisional`として扱い、`committed`状態と型上区別する | AI提案・必須級 | provisional情報がMemory/Relationship/canonical conversationへ混入しない |
| REQ-V01-ORCH-46 | Turn内eventはlocal Orchestratorが単調増加`sequence`とmonotonic観測時刻を付与し、remote clockを順序判定の権威にしない | AI提案・重要 | Colab/remote時計差やnetwork reorderでもtrace順序を再構成できる |
| REQ-V01-ORCH-47 | cancelはidempotentな第一級Command/Eventとし、generation→segment→TTS→playbackへ明示的に伝播できる | AI提案・必須級 | barge-inやpartial修正時に古い出力が後から再生されない |
| REQ-V01-ORCH-48 | stream queueはboundedとし、backpressure/drop policyをevent種別ごとに定義する | AI提案・重要 | token/partial/audio backlogが無限成長せずforeground latencyを守る |
| REQ-V01-ORCH-49 | Voiceでは`AssistantDeliveryCheckpoint`を通して実際にdelivery済みのtext spanを追跡し、canonical assistant messageをそこから確定する | AI提案・必須級 | interruption途中でも「実際に言った範囲」を共有履歴の権威にする |
| REQ-V01-ORCH-50 | Eventは`canonical audit / metric trace / ephemeral stream`の保存級を持ち、高頻度token/audio chunkを既定で永続化しない | AI提案・重要 | 観測可能性を保ちつつDB肥大・音声プライバシーリスクを抑える |
| REQ-V01-ORCH-51 | `ContextCapsule`は生成開始時点のimmutable Snapshotとし、`state_revision` / `transcript_revision` / `retrieval_run_id`へ固定する | AI提案・必須級 | 後から変わったMemory/Stateが同一generationの根拠として混ざらない |
| REQ-V01-ORCH-52 | Turn Analyzerはcanonical user inputと実際にdeliveryされたassistant範囲を解析対象とし、未delivery generation tailをSelf/Relationship/Memory根拠にしない | AI提案・必須級 | delivery truthをbackground learningにも一貫適用 |
| REQ-V01-ORCH-53 | Text v0.1もVoiceと同じTurn/Event契約のsubsetを用い、Voice追加時にOrchestratorを作り直さない | AI提案・強く推奨 | Text→Voice拡張の構造的互換性を保つ |
| REQ-V01-ORCH-54 | Remote model streamはlocal Gatewayで正規化し、provider固有token/event形式をCoreへ露出しない | AI提案・重要 | Local/Colab/Cloud差替時も上位Orchestrator型を維持する |
| REQ-V01-ORCH-55 | 各Event/Commandのproducer・required consumer・state ownerを一意に定義し、複数componentが同じcanonical stateを直接書換えない | AI提案・必須級 | producer/consumer表とownership表から責務が一意に追える |
| REQ-V01-ORCH-56 | Domain Stateの確定mutationはValidator/Projector経由に限定し、ASR/LLM/TTS/Playback等のcomponent eventから直接書込まない | AI提案・必須級 | component失敗やlate eventでMemory/Self/User/Relationshipが直接壊れない |
| REQ-V01-ORCH-57 | `committed`なUser Turn/Deliveryは同一turn内で巻き戻さず、訂正・追加発話は新Event/新Turnとして表現する | AI提案・重要 | audit historyを破壊せず再現できる |
| REQ-V01-ORCH-58 | Foreground failureを`critical / degradable / background`へ分類し、Recall/Turn detector等のdegradable failureでは可能なら会話を継続する | AI提案・重要 | 非本質subsystem障害で会話全体を停止しない |
| REQ-V01-ORCH-59 | Main providerがdelivery前に失敗した場合のみLocal/別provider fallbackを同一turnで試行可能とし、delivery後の無言model切替で文章を継ぎ足さない | AI提案・強く推奨 | persona/voice driftと不整合な途中継続を避ける |
| REQ-V01-ORCH-60 | cancelled/superseded scopeに属するlate resultは全componentでdiscardし、retryは新attempt IDで追跡する | AI提案・必須級 | remote遅延結果や二重retryが再生/DB更新されない |
| REQ-V01-ORCH-61 | ASR/Recall/Turn detector/Context/Main/Segmenter/TTS/Playback/Analyzer等の各attemptを共通telemetryで追跡し、status/failure code/retryability/deadlineを記録する | AI提案・重要 | model call以外の遅延・失敗もend-to-endで原因特定できる |
| REQ-V01-ORCH-62 | Text streamingでもUIへ実際にrenderされた範囲をdelivery truthとして扱い、Voiceと同じcanonical-delivery原則を適用する | AI提案・重要 | stream途中失敗時に未表示tailを「言ったこと」にしない |
| REQ-V01-ORCH-63 | `BargeInDetected`のcandidateだけでは即cancelせず、InterruptionDecisionでbackchannel/false positive/confirmed interruptを分離する | AI提案・重要 | 「うん」「へー」等で不要にAI発話を切らない |
| REQ-V01-ORCH-64 | Turn Analysis commit時に`base_state_revision`が古い場合は最新Stateへ再検証し、stale proposalをblind overwriteしない | AI提案・必須級 | forget/correction等と競合した古いAnalyzerが状態を復活・上書きしない |
| REQ-V01-ORCH-65 | Orchestratorの主要正常系・競合・障害系をversionedなGolden Event Sequenceとして保持し、実装変更時の回帰試験へ使用する | AI提案・必須級 | 同じ入力/初期snapshotに対し、必須Event順序・終端phase・canonical state不変条件を検証できる |
| REQ-V01-ORCH-66 | Golden Sequenceは「起きるべきEvent」だけでなく「絶対に起きてはいけないcanonical mutation / delivery / resurrection」も明示する | AI提案・必須級 | late/cancel/provisional resultがMemoryやMessageへ漏れないことをnegative assertionで検証できる |
| REQ-V01-ORCH-67 | Provider固有streamを正規化した後のCore Event列をGoldenの比較対象とし、Local/Colab/Cloud差替でGolden自体を作り直さない | AI提案・重要 | backend差替後も同じCore契約を再利用できる |
| REQ-V01-ORCH-68 | Race系GoldenではEvent到着順を意図的に並べ替え、cancel / revision / attempt ID / state revisionにより結果が決定論的に収束することを確認する | AI提案・必須級 | late remote result・stale Analyzer・endpoint revoke等で状態が復活/二重commitしない |
| REQ-V01-ORCH-69 | Text v0.1のP0 component boundaryをOrchestrator / Retrieval / Context / Gateway / Delivery / Analyzer + deterministic Domain Update Layerとして固定する | 非コード実装仕様・明示採用 | 各責務・input/output・state owner・failure degradeが一意に追える |
| REQ-V01-ORCH-70 | Canonical stateはsingle-writer原則を取り、Turn lifecycleはOrchestrator、delivery truthはDelivery、semantic Domain mutationはDomain Update Layerが所有する | 非コード実装仕様・必須級 | 複数componentが同じcanonical stateを直接更新しない |
| REQ-V01-ORCH-71 | Retrieval failureはvector/lexical片系またはempty degraded snapshotへ縮退し、Recall障害だけで通常Chatを停止しない | 非コード実装仕様・重要 | soft-deletedを返さず、両retrieval失敗でもrecent contextで会話継続可能 |
| REQ-V01-ORCH-72 | Context Builderは生成開始時点のimmutable Context Capsuleを作り、hard rules/current input/privacy境界をtoken trimより優先して保持する | 非コード実装仕様・必須級 | budget超過時もhard constraints/current inputが欠落しない |
| REQ-V01-ORCH-73 | Delivery componentをcanonical assistant contentの根拠とし、Textでも実際にUIへrenderされた範囲だけを共有会話へ確定する | 非コード実装仕様・必須級 | stream途中失敗/cancel時に未render tailをMessage/Memory evidenceへ含めない |
| REQ-V01-ORCH-74 | Domain Update LayerをValidator + Projectorの共通境界とし、Analyzer proposalや明示commandからのsemantic updateをatomic transactionで確定する | 非コード実装仕様・必須級 | invalid/stale/secret/forget-boundary proposalをrejectし、partial mutationを残さない |
| REQ-V01-ORCH-75 | P0はLOCAL_ONLYとHYBRID_COLAB_MAINで同一component/event contractを維持し、remote runtime差をGateway以下に封じる | 非コード実装仕様・重要 | Main provider差替でCore contract/Domain schemaを変更しない |
| REQ-V01-ORCH-76 | Text v0.1のCodex実装単位をWP-TXT-01〜10へ分割し、foreground vertical slice→persistent state→Inspector/Goldenの順で着手可能にする | 非コード実装仕様・重要 | 依存順と完了条件が仕様文書から追える |

### Turn Analyzer v1
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-ANL-01 | `TurnAnalysisV1`はversioned strict schemaとし、top-level/child fieldを固定する | AI提案・必須級 | schema外field、型違反、上限超過をcommitしない |
| REQ-V01-ANL-02 | Analyzerは「何も更新すべきでない」を正常結果として返せる | AI提案・必須級 | 全配列empty + optional candidate nullがvalid |
| REQ-V01-ANL-03 | Analyzer入力はcanonical user turn / delivery済assistant範囲 / bounded recent context / bounded relevant stateだけに制限する | AI提案・重要 | 未delivery tail、soft-deleted memory、無制限履歴を入力しない |
| REQ-V01-ANL-04 | Memory Candidateは1 turn最大6件とし、Episode/Claim、subject、temporal scope、direct/inferred、importance signal、existing-memory relation、evidenceを出す | AI提案・重要 | 大量Memory生成をschema段階で抑制し、全候補にevidenceを要求 |
| REQ-V01-ANL-05 | Direct user factとBehavioral User Observationを分離する | AI提案・必須級 | 直接発言はUser Claim候補、行動からの推測はUser Observation/Hypothesis signalとして扱う |
| REQ-V01-ANL-06 | Self Observationはspontaneityとuser influenceをordinalで出し、AIの自発反応と迎合可能性を区別する | 既存独立人格要求の具体化 | user influenceが高い1件だけでSelf Modelへ昇格しない |
| REQ-V01-ANL-07 | Appraisal/Emotionは毎turn必須にせず、意味のある変化がある場合のみ最大1件ずつ提案する | AI提案・重要 | 雑談ごとに感情イベントを乱造しない |
| REQ-V01-ANL-08 | Relationship Signalは疎に生成し、1 turn最大3件。Trust等は可能ならcontext scopeを伴う | AI提案・必須級 | 利用頻度/単発褒め言葉だけで親密さ・信頼を大幅更新しない |
| REQ-V01-ANL-09 | UUID、timestamp、numeric confidence/weight/delta、lifecycle status、soft-delete/archive、Self昇格、Relationship数値はcode-owned | AI提案・必須級 | LLMが直接canonical state値や削除権限を決めない |
| REQ-V01-ANL-10 | Analyzerが出すordinal signalはValidator/Projectorがcode-owned mappingと1-turn capを適用してDomain updateへ変換する | AI提案・必須級 | 同一schemaでもmapping versionを追跡しrollback可能 |
| REQ-V01-ANL-11 | 全semantic proposalは許可されたMessage/Memory referenceへevidenceを持ち、参照不能な主張をDomainへcommitしない | AI提案・必須級 | hallucinated IDや根拠なしproposalをreject |
| REQ-V01-ANL-12 | Analyzerはfield-level semantic golden casesで検証し、文面一致ではなく分類/evidence/no-mutation invariantで評価する | AI提案・必須級 | correction/change-over-time/temporary state/self-user separation等のfixtureを回帰可能 |

### Retrieval v1
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-RETR-01 | `RetrievalRequestV1 / RetrievalSnapshotV1`をversioned contractとして固定し、Retrievalをcanonical Domainのread-only componentとする | 非コード実装仕様・必須級 | Retrieval単独でMemory/Self/User/Relationshipをmutationしない |
| REQ-V01-RETR-02 | P0はextracted Memory + canonical raw messageを対象に、lexical / semanticを並列利用可能にする | 非コード実装仕様・重要 | raw assistant sourceはdelivery済canonical contentだけを対象 |
| REQ-V01-RETR-03 | soft-deleted / forbidden / source不整合を候補化せず、ARCHIVEDは除外せず低優先で扱える | 非コード実装仕様・必須級 | soft-deleted result 0、明示参照時のArchive再浮上を妨げない |
| REQ-V01-RETR-04 | fusion方式・weight・thresholdは`retrieval_profile_id`でversion管理し、exact数値は初期実働前に固定しない | 育成型開発の明示方針 | profile別A/B可能、score式変更でDomain schemaを変えない |
| REQ-V01-RETR-05 | Retrieval中にDomain revisionが変化した場合、Context投入前にsource visibilityを再検証する | 非コード実装仕様・必須級 | Retrieval後のUser ForgetがPromptへ漏れない |
| REQ-V01-RETR-06 | Promptへの最終採否はContext Builderが所有し、Retrievalはranked candidate snapshotを返す | 非コード実装仕様・重要 | Recallされたこと自体を発話/Prompt投入義務にしない |
| REQ-V01-RETR-07 | lexical/semantic failureは片系またはempty degraded snapshotへ縮退し、Recall障害だけで通常Chatを停止しない | 既存ORCH要件の具体化 | 両系統停止でもrecent contextでMainへ進行可能 |

### Explicit Command / Readiness
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-CMD-01 | `remember` / `forget`等の明示commandをforeground deterministic pathで認識し、Analyzer完了を待たず処理できる | r16監査で具体化・必須級 | command marker/target resolution/適用結果をTraceできる |
| REQ-V01-CMD-02 | Forget対象を`exact / unique / ambiguous / not_found`として解決し、曖昧時は破壊的mutationを行わない | r16監査で具体化・必須級 | ambiguousではmutation 0 + clarification |
| REQ-V01-CMD-03 | resolved Forgetはforegroundでatomic soft-deleteし、state revisionを進め、stale Analyzer/Retrievalから復活不能にする | r16監査で具体化・必須級 | delete後Recall/Prompt/Self evidenceへ0件 |
| REQ-V01-CMD-04 | Explicit Rememberはdurable markerとして保持し、Analyzer failure/retryでも「覚えて」の意図を失わない | r16監査で具体化・重要 | secret filterを優先しつつ、semantic Memory抽出を後から再実行可能 |
| REQ-V01-DOR-01 | Text v0.1はRequirement ↔ Component Contract ↔ Type/Ownership ↔ ER ↔ P0 Golden ↔ AcceptanceのDoR監査を通してからCodex着手する | r16監査済み | P0 blocker 0 |
| REQ-V01-DOR-02 | Model/Embedding/Vector store/fusion weight/Context budget等のRuntime選択は着手blockerにせず、contractを変えない範囲で実装/benchmark時に決める | 育成型開発方針 | 未決項目がP0 vertical slice実装を妨げない |

現時点の推奨call profile（未確定、実機benchmark前）:
- foreground: Main Dialogue LLM ×1。
- retrieval: embedding ×1（generative LLM callに数えない）、lexical searchと並列。
- reranker: ambiguous時のみoptional。
- post-response: Turn Analyzer SLM ×1 async。
- reflection/consolidation: idle/batch。
- high-spec profileのみ、pre-turn SLM ×1をRecallと並列で試験し、品質改善がTTFT増を上回る場合だけ採用。

---
