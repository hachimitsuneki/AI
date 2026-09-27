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

