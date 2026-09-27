# 7. 再開情報

## 7.0 r4変更点
- r3を参照可能なProject会話内容と再照合し、「カテゴリは残ったが詳細が落ちた」箇所を監査・復元。
- `REQ-AI-054`〜`REQ-AI-058`を追加: 明示依頼優先、Intent詳細、Action scoring、Self-perception分離、Affect非操作。
- `REQ-V01-MEM-13`〜`15`を追加: 明示remember、Memory Gate判断軸、Archive保護条件。
- `REQ-V01-AFF-07`〜`09`を追加: AI_STATE意味、Emotion prompt表現、Affect非操作。
- v0.1コアEntity属性/PK/FK/任意性を§3.3.1へ復元。r3のERは関係だけで、以前詰めた属性がhandoff上不足していたため。
- 長期Intentへmotivation/origin/preferred_context/interruptibility、Action Attemptへselection factorsを復元。
- Test caseへexplicit remember / social-state override / analyzer failure / affect non-manipulationを追加。
- 参照トレーサビリティの限界と、実際に残っている一次URLを明記。

## 7.0.1 完全性監査の結果
- **r3は「主要機能カテゴリ」は概ね復元できていたが、詳細仕様まで完全ではなかった。** r4で上記欠落を復元した。
- 現時点で「機能をMVP理由で削除した」と認識している項目はない。v0.1外は後続要求として保持している。
- ただし、過去別チャットの全生ログを逐語監査したわけではないため、**絶対に一語も欠落していないという保証はしない**。今後も新しい決定/訂正のたびにこのhandoffへ差分反映する。
- Codexへ渡す前に、少なくとも `要件表 ↔ ER ↔ first implementation ↔ acceptance tests` のID整合性チェックをもう一度行う。

## 7.0.2 r5変更点
- Turn Analyzerを直接DB更新モデルではなくEvidence/Update Proposal generatorとして具体化。
- `REQ-V01-ORCH-13`〜`19`を追加。
- Analyzer schemaでordinal enumを使い、LLMにpseudo-precise float/新規IDを決めさせない方針を追加。
- referential integrity / forget境界 / secret filter / duplicate・correction / stale revision / atomic transaction / idempotencyをcommit policyとして追加。
- application-level foreground schedulerを明示し、backend slot/process priorityだけに依存しない方針を追加。
- Analyzer候補をQwen3.5-0.8B/2B、Qwen3-1.7B、Gemma 3 4Bの比較候補として記録。
- Benchmark Harness v1のruntime/analyzer/system metricsを定義。
- Analyzer proposal/commit audit用ER addendumを追加。

## 7.0.4 r7変更点
- ユーザー指摘「AI VTuberはゴリゴリ遅いわけではない」を受け、Voice latencyを総生成時間ではなく`user speech end → first audio`中心に再設計。
- Open-LLM-VTuberで採られているfirst sentence fragment優先・複数TTS segment並列化・interruptionの考え方を設計へ反映。
- VAD単独ではなくsemantic/acoustic turn detection、dynamic endpointing、optional preemptive generationを比較対象へ追加。
- `REQ-V01-ORCH-24`〜`31`を追加し、streaming ASR/LLM/TTS、barge-in、warm state、voice latency breakdownを正式に保持。
- 将来Voice用`VOICE_TURN_TRACE / AUDIO_UTTERANCE / AUDIO_SEGMENT`概念ERを追加。text-only v0.1 ERは変更しない。
- 暫定の体感目標としてvoice first-audio p50≈1秒 / p95≤2秒、text TTFT p50<1秒を置いた。これは外部事実ではなくbenchmark開始用の設計目標で、実測により更新する。

## 7.0.5 r8変更点
- Voice latencyを「処理段階一覧」から**0ms基準のend-to-end budget**へ具体化。`last user audio sample → first bot playout sample`を主要KPIとする。
- `REQ-V01-ORCH-32`〜`42`を追加: speech中prefetch、cache-friendly prompt、warm-prefix prefill、delivery truth、bounded audio lookahead、resource isolation、AEC、audio-level実測、Safe/Balanced/Aggressive profile、context budget、persistent remote connection。
- 人間会話の短いturn gapを参考に、ユーザー発話中から処理を重ねる設計を明示。人間の約200ms gap自体をAI SLAとはせず、先読みの設計根拠として扱う。
- Voice既定候補を`Balanced`: STT final到着後にMainをpreemptive startし、semantic turn確定後にTTSを解放。partial transcriptからのAggressive generationは実験用。
- Prompt cacheを壊しにくい`Stable Prefix → Session Prefix → Dynamic Turn Context`構造と、idle中`n_predict=0`等を使うWarm Prefix Mirror案を追加。
- partial transcriptは検索prefetchに利用してもcanonical stateへmutationしない。lexical prefetch→debounced semantic prefetch→final validationの順を追加。
- barge-in時は実際にdeliveryされたassistant範囲だけをcanonical conversationへ確定し、未発話tailをMemory/Relationship evidenceに使わない。
- Voice trace ERを拡張し、turn detector/AEC/Context/TTS/playout/barge-in/device latencyを分解記録。


## 7.0.6 r9変更点
- ユーザー指定に従い、実コードではなく**Orchestratorの型・境界契約まで**を定義。
- `Command / Event / Snapshot`を分離し、共通`EventEnvelope`、turn内sequence、causation、monotonic timing、persistence classを追加。
- `UserSpeechStarted / TranscriptUpdated / UserEndpointCandidate / UserTurnCommitted / RecallSnapshot / ContextCapsule / StartGeneration / Generation* / SpeakableFragmentReady / SpeechSegmentReady / Playback* / AssistantDeliveryCheckpoint / BargeInDetected / InterruptionDecision / CancelScope / AnalyzeCommittedTurn`を型として整理。
- Voiceのdelivery truthを`AssistantDeliveryCheckpoint`で文字spanとして追跡し、Turn Analyzerもdelivery済みcanonical textだけを学習するよう固定。
- queue/backpressure/drop policyとevent保存級を定義。raw audio/token delta等は既定でephemeralとし、全streamをDBへ保存しない。
- Text v0.1もVoiceと同じEvent骨格のsubsetを利用する方針を追加。
- `REQ-V01-ORCH-43`〜`54`を追加。
- Technical trace ERへ`TURN_EVENT_TRACE / CONTEXT_SNAPSHOT / CANCELLATION_SCOPE / DELIVERY_SPAN`を追加。

## 7.0.7 r10変更点
- r9で定義したEvent/Command/Snapshotについて、producer / required consumer / canonical state ownerを固定。
- `RunRecall / BuildContextCapsule / QueuePlaybackSegment / CommitAnalysisProposals`のCommand境界を追加。
- `UserEndpointRevoked / GenerationAdoptedForCommittedTurn / PlaybackStopped / ComponentAttemptResult`を追加し、preemptive generationのcommit検証とfailure telemetryを明示。
- Input / Generation / Delivery / Analysisの許可状態遷移を表形式で定義。`committed`なUser Turnは同一turn内で巻き戻さない。
- failureをhard fail-closed / foreground critical / foreground degradable / backgroundへ分類し、Recall障害等ではdegraded continuationを許可。
- Remote Mainはdelivery前のみ同一turn fallback可能。delivery後の別modelによる無言mid-sentence continuationは禁止。
- barge-in/cancel propagation、late-result discard、state revision conflict、transaction rollbackをfailure/cancel matrixとして固定。
- Text streamingにもdelivery truthを適用し、`ui_rendered`をdelivery basisへ追加。
- Technical Trace ERへ`COMPONENT_ATTEMPT`を追加。Domain ERは変更なし。
- `REQ-V01-ORCH-55`〜`64`を追加。


## 7.0.8 r11変更点
- `REQ-V01-ORCH-65〜68`を追加し、Golden Sequenceを正式な回帰仕様として定義。
- `GS-ORCH-001〜015`を追加。Text正常、Voice Balanced、endpoint撤回、barge-in、backchannel、remote failure前/後、cancel後late result、Analyzer vs Forget競合、ASR final訂正、TTS failure、Retrieval timeout、Text streaming割込、Analyzer retry、Explicit Remember保護Archiveを網羅。
- Goldenはmodel文面ではなくEvent causation / truth state / canonical delivery / Domain mutation / terminal phaseで比較する。
- race/late eventではUUID/時刻を正規化し、happens-before constraintで判定する。
- Golden追加は試験仕様のみで、Domain ER/Technical ERのEntityは増やしていない。

## 7.0.9 r12変更点
- `TurnAnalysisInputV1 / TurnAnalysisV1`を実コードではなくfield-level型契約として固定。
- `REQ-V01-ANL-01〜12`を追加。Strict schema、no-op valid、bounded context、Memory/Self/User/Affect/Relationship各proposal上限、LLM/code ownershipを正式化。
- `MemoryCandidateV1 / SelfObservationV1 / UserObservationV1 / AppraisalCandidateV1 / EmotionCandidateV1 / RelationshipSignalV1`の必須/任意field、enum、最大件数、文字列上限、semantic constraintを定義。
- Direct User FactはMemory Claim、Behavioral inferenceはUser Observationへ分離。Self Observationはspontaneity/user influenceを必須化。
- UUID/timestamp/numeric confidence/lifecycle/Self promotion/Relationship value/Mood delta/Permissionはcode-ownedと明示。
- Analyzer semantic Golden `AN-GOLD-001〜014`を追加。Correction/change-over-time/temporary state/explicit remember/self-user separation/attachment inference/secret/interrupted delivery/empty resultを回帰対象化。
- Domain ER Entity追加なし。`ANALYSIS_PROPOSAL.proposal_type`だけv1の6種へ明確化。


## 3.18 Retrieval P0 field-level contract（r15）

Canonical詳細: `RETRIEVAL_P0_SPEC.md`

固定した境界:
- `RetrievalRequestV1`はcanonical user text / state revision / scope / source class / budget hint / retrieval profileを受ける。
- `RetrievalSnapshotV1`はimmutableなranked candidate snapshot。0件を正常扱いできる。
- result sourceは`memory_item | raw_message`。raw assistant messageは**実際にdeliveryされたcanonical contentだけ**。
- `soft_deleted`は結果0件を保証。ARCHIVEDは除外ではなく通常低優先で、明示参照時の再浮上を妨げない。
- exact scoring weight / threshold / reranker条件 / embedding modelは実装前に固定しない。`retrieval_profile_id`で比較可能にする。
- Retrieval開始後にDomain revisionが変わった場合、Context Builder側でsource visibilityを再検証する。特にUser Forgetを古いsnapshotから復活させない。
- Retrievalはcandidate生成まで。Promptへの最終採否はContext Builderが所有する。
- semantic/lexical障害はdegraded snapshotへ縮退し、Recall障害だけでChatを停止しない。

P0 Goldenは`RET-GOLD-001〜005`の5件だけ:
1. soft-delete境界
2. delivery truth
3. semantic片系failure
4. total recall failure
5. retrieval→context間のforget race

Domain ER Entity追加なし。既存`RETRIEVAL_RUN / RETRIEVAL_RESULT`で表現し、物理列かJSON traceかは実装時に決める。

---


## 3.19 Text v0.1 Definition of Ready監査（r16）

Canonical詳細: `TEXT_V01_READINESS_AUDIT.md`

監査結果: **READY FOR CODEX IMPLEMENTATION / P0 blocker 0**。

監査で見つかった唯一のP0曖昧点は、自然言語`forget`の対象解決境界。
`TEXT_V01_IMPLEMENTATION_SPEC.md §17`で以下の最小契約を追加した。

```text
Forget command
   ↓
Target resolution
   ├─ exact / unique → resolved → foreground atomic soft-delete
   └─ ambiguous     → mutation 0 → clarification
```

- `remember`はforegroundでdurable marker化し、semantic Memory抽出はAnalyzer経由でよい。
- `forget`はAnalyzerを待たず、resolved時に即soft-delete。
- ambiguity時にLLM推測で破壊的削除しない。
- command marker / stale Analyzer / stale Retrievalから忘却内容を復活させない。

DoR監査の結果、Main/Analyzer/Embedding/Vector store/fusion weight/Context budget等の最終選択は**着手非ブロッカー**と確認した。
これらはGateway/Profile/Runtime設定または実働後tuningとして保持する。

Domain/Technical ERへのEntity追加なし。

---

## 7.0.10 r13変更点
- ユーザー指示「実コード無しで実装」を、application code未着手のまま**非コード実装仕様を完成させる**意味として反映。
- 詳細仕様 `TEXT_V01_IMPLEMENTATION_SPEC.md` を新設。P0 Text v0.1のcomponent contract、state ownership、failure/degrade、privacy、observability、acceptance、Codex work packageを固定。
- `REQ-V01-ORCH-69〜76`を追加。Component boundary、single-writer、Retrieval degrade、immutable Context、delivery truth、Validator/Projector、Local/Colab contract共通化、Codex work packageを要件化。
- Domain ER/Technical ERのEntity追加なし。今回の変更はcomponent/interface/ownershipレベル。
- 実コード、DB migration、model server deployment、test code、benchmarkは未実施であり「実装済み」とは扱わない。

## 7.0.11 r14変更点
- ユーザー確認を受け、**実装前の過剰仕様化を避ける**方針へ明示変更。
- `AN-GOLD-001〜014`は保持しつつ、実装前にfixture詳細化するのは高リスクP0 7件（002/003/004/006/011/012/014）のみとした。
- `ANALYZER_GOLDEN_SPEC.md`を新設し、P0についてinput fixture / expected proposal / validator outcome / Domain mutation / must-not-mutateを固定。
- P1 Goldenは初期実働ログ後に具体化する。削除・却下ではない。
- numeric threshold / prompt wording / exhaustive conversational variantsは実働前に固定しない。
- Domain ER / Technical ER変更なし。

## 7.0.12 r15変更点
- `RETRIEVAL_P0_SPEC.md`を新設し、`RetrievalRequestV1 / RetrievalSnapshotV1 / RetrievalResultV1`の最小field-level contractを固定。
- `REQ-V01-RETR-01〜07`を追加。read-only ownership、canonical source、hybrid retrieval、profile-versioning、forget-race revalidation、Context Builderとの責務分離、degradeを要件化。
- exact score weight / threshold / reranker条件 / embedding model / chunking等は初期実働後へ意図的に保留。
- Retrieval GoldenはP0 5件だけ固定。rankingの細かいfixtureは着手ブロッカーにしない。
- Domain ER Entity追加なし。


## 7.0.13 r16変更点
- Text v0.1 Definition of Ready監査を実施し、Requirement ↔ Component Contract ↔ Type/Ownership ↔ ER ↔ P0 Golden ↔ Acceptanceを照合。
- 監査前に唯一残ったP0曖昧点として、自然言語Forgetのtarget resolutionを特定。
- `TEXT_V01_IMPLEMENTATION_SPEC.md`へ`Explicit Remember / Forget P0 boundary`を追加。resolved/ambiguous、foreground soft-delete、durable remember marker、negative invariants、`CMD-GOLD-001〜003`を固定。
- `REQ-V01-CMD-01〜04`, `REQ-V01-DOR-01〜02`を追加。
- `TEXT_V01_READINESS_AUDIT.md`を新設。
- 監査結果は**P0 blocker 0 / READY FOR CODEX IMPLEMENTATION**。ただし実コードは未着手。
- Main/Analyzer/Embedding/Vector実装/fusion weight/Context token budget/P1 Golden/Voice詳細は着手ブロッカーにしない。
- Domain ER / Technical ER Entity追加なし。

## 7.1 現在地
Text v0.1の非コード実装仕様とDefinition of Ready監査が完了した段階。**Codex実装着手Ready / P0 blocker 0**。foreground 1 Main call + async Analyzer、6 component + deterministic Domain Update Layer、Retrieval/Analyzer P0 contract、delivery truth、forget/secret/stale境界まで固定済み。

実装前の追加仕様化はここで原則停止する。P1 Golden、exact retrieval scoring、model/hardware tuning、Voice詳細は初期実働または各フェーズ直前へ回す。

現在の最重要問いは仕様ではなく、実装開始後に **最小Text vertical sliceが実際に動き、ログから次の育成点を発見できるか**。

## 7.2 次の作業
1. ユーザーが実コード着手を指示した時点で、Codexへ`WP-TXT-01`から引き継ぐ。
2. 実装は`WP-TXT-01 → 02 → (03+04) → (05+06) → 07+08 → 09+10`の順を基本とする。
3. 最初のforeground vertical sliceが動いたら、仕様を増やす前に実測ログを採る。
4. 初期実働からMemory false positive / Recall miss / Self-User contamination / persona drift / TTFTを観測し、必要なP1 Goldenだけ追加する。
5. Hardware情報が判明した時点でMain/Analyzer/Embedding候補とLocal/Colab profileをbenchmarkする。
6. Voice詳細はVoiceフェーズ直前に再開する。
7. 実装中にownership/forget/privacy/ER/Goldenの矛盾が見つかった場合だけ企画側へ戻す。

## 7.3 中間進化（将来Fine-tuning）の方向性
ユーザー提案: HikariのBonsai系チューニングを参考に、外部Memoryだけでなくモデル自体も段階的に進化する「中間進化」を将来目指す。

公開情報上、Hikari07jp版はPersona tuningそのものではなくquant-native targeted editのpreview。今回採るのは「狙った変化だけを加え、能力回帰をharnessで守る」という方法論。

区別する:
- Memory Learning: 外部状態が増える。
- Behavioral Adaptation: Self/Preference/Relationshipが変わる。
- Model Evolution: adapter/weightsを更新する。

推奨段階:
1. v0.1ではweightsを変えず、ログと評価を集める。
2. curated dialogue examples + failure/negative cases + regression setを作る。
3. Base frozen + versioned Persona LoRAでSFTを比較。
4. accepted/edited/rejected応答が十分集まったらDPO等のpreference tuningを比較。
5. 世代更新前にpersona/memory/tool/coding/general能力のregression gateを必須化。
6. 深いweight edit/quant-native editは、その評価基盤が成熟した後の研究フェーズ。

実装方式・採用model・開始時期は未決。

## 7.4 次チャットで読む順序
1. `PROJECT_HANDOFF.md` の 1, 4, 7（r16）
2. 2.3 v0.1要件
3. `TEXT_V01_READINESS_AUDIT.md` → `TEXT_V01_IMPLEMENTATION_SPEC.md` → `ANALYZER_GOLDEN_SPEC.md` → `RETRIEVAL_P0_SPEC.md`
4. 3.2会話フロー / 3.3 Domain ER図
5. 5 最初の実装
6. 必要に応じて6 参照資料
