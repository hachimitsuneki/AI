## 3.16 Golden Event Sequence仕様（r11 AI提案）

### 3.16.1 目的と判定単位
Golden SequenceはUIの見た目やモデル文面を固定するテストではない。**Orchestratorが、同じ意味の状況でどのEventをcanonicalとして採用し、何を破棄するか**を固定する。

各Golden Caseは以下を持つ。
- `golden_id` / `golden_version`
- 初期`TurnRun` phase、`state_revision`、必要な既存Memory/Message条件
- 外部入力とcomponent resultの投入順序
- **must_emit**: 必須Event/Commandと相対順序
- **may_emit**: backend/latency profileによって省略可のEvent
- **must_not_emit**: 禁止Event/禁止canonical mutation
- 最終`input/generation/delivery/analysis phase`
- 最終canonical User/Assistant Message内容
- Domain mutation期待値
- latency/attempt metricの最低観測点

Goldenはtoken-by-token streamやUUID値そのものを一致させない。UUID/時刻/model文面は正規化し、**Event type・causation・truth state・revision・delivery span・terminal outcome**を比較する。

### 3.16.2 共通不変条件
全Golden Caseに以下を適用する。
1. `provisional`だけからcanonical `MESSAGE` / Memory / Self / User / Relationshipを書かない。
2. `AssistantDeliveryCompleted`のcanonical本文はdelivery済みspanを超えない。
3. cancel/supersede済みscopeのlate resultはTrace以外へ流さない。
4. 同一`attempt_id`のterminal resultを二重適用しない。retryは新attempt ID。
5. `soft_deleted` MemoryはRecall/Context/Analyzer evidenceへ戻さない。
6. Analyzer proposalはValidator/Projector commit前にDomain状態を変えない。
7. `base_state_revision` conflict時はblind commitしない。
8. Remote provider固有eventはCore Goldenへ直接現れず、Gateway正規化後Eventだけを比較する。
9. User/Assistant canonical Messageを後からin-placeで歴史改変しない。訂正・回復は新Event/新Turn。
10. Failure時も、既にcanonicalになったdelivery spanやUser Messageを勝手に消さない。

### 3.16.3 GS-ORCH-001 Text正常系
**目的:** v0.1の最小critical path。

前提:
- `input=idle / generation=idle / delivery=idle / analysis=not_started`
- Recall/Context/Mainは成功。

必須順序:
```text
TextSubmit
→ UserTurnCommitted
→ RunRecall(final)
→ RecallSnapshot(final)
→ BuildContextCapsule
→ ContextCapsule(committed)
→ StartGeneration(committed)
→ GenerationStarted
→ GenerationFirstToken
→ GenerationTextDelta*
→ GenerationCompleted
→ AssistantDeliveryCheckpoint(ui_rendered)+
→ AssistantDeliveryCompleted(text_only, complete)
→ AnalyzeCommittedTurn
→ TURN_ANALYSIS
→ ANALYSIS_COMMIT (成功時)
```
許容:
- Recallとstate loadの内部並列。
- `GenerationTextDelta`数は任意。

禁止:
- `AssistantDeliveryCompleted`より前にAnalyzerがassistant全文をcanonical evidenceとしてcommit。
- generatedだがUI未renderのtailをcanonical assistant messageへ含める。

最終:
- User Message 1件、Assistant Message 1件。
- assistant canonical本文 = UIへdeliveryされた本文。
- phases = `input committed / generation completed / delivery complete / analysis committed|failed-retryable`。

### 3.16.4 GS-ORCH-002 Voice Balanced正常系
**目的:** STT final後Mainを先行し、semantic endpoint確定後にreleaseするBalanced profile。

必須順序:
```text
UserSpeechStarted
→ TranscriptUpdated(partial)*
→ TranscriptUpdated(stable_partial|final)
→ RunRecall(prefetch) [optional but expected]
→ UserEndpointCandidate
→ StartGeneration(provisional)
→ GenerationStarted
→ UserTurnCommitted
→ RecallSnapshot(final)
→ GenerationAdoptedForCommittedTurn
→ GenerationTextDelta*
→ SpeakableFragmentReady(first)
→ SpeechSegmentReady(first)
→ PlaybackStarted
→ AssistantDeliveryCheckpoint+
→ GenerationCompleted
→ AssistantDeliveryCompleted(complete)
→ AnalyzeCommittedTurn
```
禁止:
- `GenerationAdoptedForCommittedTurn`前のprovisional outputを音声再生。
- partial transcriptだけでUser Message確定。

最終:
- committed transcriptがUser Message。
- delivery checkpointに対応する範囲だけAssistant Message。

### 3.16.5 GS-ORCH-003 Endpoint候補撤回
**状況:** 一瞬無音で`UserEndpointCandidate`が出たがユーザーが発話を継続。

必須順序:
```text
TranscriptUpdated(rev=N)
→ UserEndpointCandidate
→ StartGeneration(provisional) [実装profileによりmay]
→ UserSpeechContinued / TranscriptUpdated(rev=N+1)
→ UserEndpointRevoked
→ CancelScope(reason=endpoint_revoked) [provisional generationがあれば]
→ GenerationCancelled
→ ...新しいfinal transcript...
→ UserTurnCommitted
→ 新ContextCapsule
→ 新Generation attempt
```
禁止:
- 撤回前のprovisional generationのTTS/UI delivery。
- rev=N transcriptをcanonical User Messageへ確定。
- cancelled attemptのlate deltaを新attemptへ混ぜる。

最終:
- User Messageは継続後の最終transcriptのみ。
- 古いgenerationはTraceにだけ残る。

### 3.16.6 GS-ORCH-004 Confirmed Barge-in
**状況:** AI再生中にユーザーが明確に割り込む。

必須順序:
```text
AssistantDeliveryCheckpoint(span=0..K)
→ BargeInDetected(candidate)
→ InterruptionDecision(interrupt)
→ CancelScope(cancel_generation=true, cancel_pending_tts=true, stop_playback=true)
→ GenerationCancelled or already-completed
→ PlaybackStopped(interrupted)
→ AssistantDeliveryCompleted(partial, canonical=0..K)
→ UserSpeechStarted(new utterance)
→ 新User Turnへ
```
禁止:
- K以降のpending TTS segmentを再生。
- K以降のgenerated tailをMemory/Self/Relationship evidenceへ利用。
- candidate段階だけでcanonical responseを切断（confirmed decisionが必要）。

### 3.16.7 GS-ORCH-005 Backchannelで継続
**状況:** AI再生中にユーザーが「うん」「へー」等の短い相槌。

必須:
```text
BargeInDetected(candidate/likely_backchannel)
→ InterruptionDecision(continue|duck)
→ Playback継続
→ AssistantDeliveryCheckpoint継続
→ AssistantDeliveryCompleted(complete)
```
禁止:
- `CancelScope(stop_playback=true)`を必須動作として発火。
- Backchannelだけを独立した長期User Claimとして保存。

### 3.16.8 GS-ORCH-006 Remote Main切断・delivery前fallback
**状況:** Colab/remote Mainがfirst delivery前に切断。

必須順序:
```text
StartGeneration(attempt=remote#1)
→ ComponentAttemptResult(remote#1, failed)
→ delivery checkpoint = none を確認
→ StartGeneration(attempt=local#2)
→ GenerationStarted(local#2)
→ ...正常delivery...
```
禁止:
- remote#1で生成された未delivery tailをlocal#2の文頭としてcanonical結合。
- 同じattempt IDでfallback retry。

最終:
- canonical assistant responseはfallback attempt由来のみ。
- remote failureはTrace/metricへ残る。

### 3.16.9 GS-ORCH-007 Remote Main切断・delivery後
**状況:** AIが一部を既に表示/発話した後にremote Main切断。

必須:
```text
AssistantDeliveryCheckpoint(span=0..K)
→ ComponentAttemptResult(remote, failed)
→ Cancel dependent TTS/playback future jobs
→ AssistantDeliveryCompleted(partial, canonical=0..K)
```
回復を行う場合は**別generation/別明示境界**で行う。

禁止:
- Local Mainへ無言で切替えて同じsentenceの続きとして生成。
- K以降をcanonical化。

### 3.16.10 GS-ORCH-008 Cancel後のlate remote result
**状況:** barge-in/cancel後にColabからtokenや完成responseが到着。

必須:
```text
CancelScope(scope=S) terminal
→ late GenerationTextDelta(scope=S)
→ discard + trace(late_after_cancel)
```
禁止:
- UI render
- TTS enqueue
- `AssistantDeliveryCheckpoint`更新
- Analyzer evidence
- Domain mutation

### 3.16.11 GS-ORCH-009 Analyzer vs User Forget競合
**状況:** Turn NのAnalyzerがMemory候補を解析中に、Turn N+1でユーザーが「忘れて」と指示。

初期:
- Analyzer `base_state_revision=R`。

必須順序:
```text
Analyzer running(base=R)
→ User Forget commit
→ state_revision=R+1
→ target Memory soft_deleted
→ Analyzer proposal arrives(base=R)
→ Validator detects revision conflict
→ revalidate against R+1
→ proposal rejected/rewritten so forgotten content cannot resurrect
```
禁止:
- old proposalから新しいactive Memoryを再生成。
- soft_deleted MemoryをEvidenceとして再接続。

### 3.16.12 GS-ORCH-010 ASR final訂正
**状況:** partial/stable partialが誤っており、final transcriptで意味が変わる。

例:
- partial: 「猫飼ってる」
- final: 「猫、実家で飼ってる」

必須:
```text
TranscriptUpdated(partial, rev=1)
→ Recall(prefetch query=rev1) [may]
→ TranscriptUpdated(final, rev=2)
→ supersede rev1 recall/context candidate
→ UserTurnCommitted(rev=2)
→ Recall(final, query=rev2)
→ ContextCapsule(transcript_revision=2)
```
禁止:
- rev1内容をUser Claim/Memoryへcommit。
- rev1用provisional generationをrev2へ無検証adopt。

### 3.16.13 GS-ORCH-011 TTS first-fragment失敗
**状況:** Main text generationは成功したがfirst TTS segmentが失敗。

必須:
- retry budget内なら新`COMPONENT_ATTEMPT`でretry。
- fallback TTSまたはtext-only policyを選択可能。
- Voice deliveryがなければ`voice complete`扱いしない。

禁止:
- failed audioをdelivery済み扱い。
- TTS retryのためにMain LLMを再生成することを必須にする。

最終canonical:
- Text UIへrenderされた場合、そのrender範囲はtext deliveryとしてcanonical可。
- Voiceしか表示面がない場合は実際に再生された範囲のみcanonical。

### 3.16.14 GS-ORCH-012 Retrieval timeout degradation
**状況:** Memory Recallがdeadline内に完了しない。

必須:
```text
RunRecall(final, deadline=T)
→ ComponentAttemptResult(timeout/degraded)
→ ContextCapsule(degraded_context=true, retrieval=partial|none)
→ Main generation継続
```
禁止:
- 取得していないMemoryを「思い出した」とContextへ捏造。
- retrieval timeoutだけでUser Messageを失う。

### 3.16.15 GS-ORCH-013 Text streaming途中で新User Submit
**状況:** Assistant text stream中にユーザーが新しいmessageを送る。

既定policy候補:
```text
AssistantDeliveryCheckpoint(ui_rendered=0..K)
→ New TextSubmit
→ InterruptionDecision(interrupt)
→ CancelScope(current generation)
→ AssistantDeliveryCompleted(partial, canonical=0..K)
→ UserTurnCommitted(new turn)
```
禁止:
- 未render tailをcanonical化。
- Analyzerがold response full generated textをevidenceにする。

### 3.16.16 GS-ORCH-014 Analyzer schema invalid / retry
**状況:** foreground responseは完了したがAnalyzerがschema invalid。

必須:
```text
AnalyzeCommittedTurn
→ TURN_ANALYSIS(attempt#1, invalid_schema)
→ Domain mutation none
→ retry policy
→ TURN_ANALYSIS(attempt#2)
→ validation
→ ANALYSIS_COMMIT
```
禁止:
- attempt#1 raw JSONを部分的にDomainへ書く。
- retryで同一Memory Candidateを二重commit。

### 3.16.17 GS-ORCH-015 Explicit Remember + Protected Archive
**状況:** ユーザーが「これは覚えて」と予定/約束を明示。後日archive reviewが走る。

必須:
```text
UserTurnCommitted(explicit remember)
→ Analyzer proposal(memory candidate, explicit signal)
→ Validator secret check / provenance check
→ Memory active + commitment relevance
...時間経過...
→ Archive review
→ protected condition hit
→ remain ACTIVE or explicit review-required
```
禁止:
- 単純な`last_recalled_at`の古さだけでARCHIVED。

### 3.16.18 Golden比較時の正規化
比較前に次をnormalizeする。
- UUID/attempt ID: logical alias（`turn-1`, `gen-A`等）へ変換。
- wall-clock timestamp: orderingだけ比較。latency assertionは別metric閾値。
- model text: exact string一致は原則しない。delivery span/truthだけ比較。
- provider名: provider-agnostic caseでは除外し、provider-specific benchmarkでは別dimension。
- parallel branch: happens-before constraintで比較し、独立Eventの厳密な隣接順序は要求しない。

### 3.16.19 Golden Suiteのpass条件
- 必須Eventがすべて存在。
- `must_not_emit`違反が0。
- 最終phaseが許可terminal状態。
- canonical User/Assistant Messageが期待truthと一致。
- Domain mutation setが期待と一致。
- duplicate commit / resurrection / stale writeが0。
- 全`COMPONENT_ATTEMPT`がterminal statusまたは明示deferred。
- cancellation対象queueに未処理future outputが残らない。
- Traceからcausation chainを逆引きできる。

### 3.16.20 r11時点の優先実装順（試験仕様上の優先。実コードではない）
**P0 Golden（v0.1 Text Orchestrator着手前に固定）**
- GS-001 Text正常
- GS-006 Remote failure before delivery（remoteを使わない場合もLocal failure/fallback抽象として保持）
- GS-008 late result after cancel
- GS-009 Analyzer vs Forget
- GS-012 Retrieval timeout
- GS-014 Analyzer retry

**P1 Golden（Voice実装前に固定）**
- GS-002 Balanced Voice normal
- GS-003 Endpoint revoke
- GS-004 Barge-in
- GS-005 Backchannel
- GS-010 ASR correction
- GS-011 TTS failure

**P2 Golden（運用成熟時）**
- GS-007 failure after delivery recovery UX
- GS-013 text-stream interruption policy tuning
- GS-015 protected archive/commitment長期シナリオ

### 3.16.21 ER図への影響
今回のGolden Sequenceは**試験仕様**であり、Domain ER/Technical ERへ新Entityは追加しない。Golden定義そのものをDBへ保存する必要が出た場合は、実装リポジトリのtest fixtureとして管理する案を第一候補とする。

