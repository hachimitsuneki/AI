## 5.3 `CMP-CTX-01` Context Builder

### 責務
Main Dialogue Modelへ渡す**その生成専用のimmutable Context Capsule**を構築。

### Input
- canonical current user turn
- `state_revision`
- Identity Kernel / hard rules
- current AI_STATE / Mood snapshot
- selected Self / User / Relationship state
- bounded Recent Conversation
- `RetrievalSnapshotV1`
- provider/model context budget profile

### Output: `ContextCapsuleV1`
最低限保持する意味:
- capsule ID / schema version
- turn ID
- state revision
- user transcript revision
- retrieval run ID
- stable prefix fingerprint
- included recent message IDs
- included Memory/Self/User/Relationship IDs
- per-section token allocation
- omitted/truncated categories + reason
- remote privacy class

### Prompt section order（P0）
1. Hard behavioral/system constraints
2. Identity Kernel / initial persona
3. Dialogue behavioral instructions
4. Current state summary（Mood/AI_STATE）
5. Relevant learned Self
6. Relevant User Model / relationship context
7. Relevant retrieved memory/evidence
8. Bounded recent conversation
9. Current user turn

実runtimeではcache効率とのbenchmarkで順序微調整可能。ただしHard rulesとcurrent user turnを落としてはならない。

### Budget trimming priority
budget超過時に先に削る:
1. low-score raw evidence
2. low-score/archived memory
3. older recent turns
4. non-critical learned context detail

最後まで保持:
- hard rules
- identity minimum
- current user turn
- explicit forget/privacy constraints

### Must not
- soft-deleted Memoryを含める。
- Analyzer未commit proposalをcanonical fact扱いする。
- provider limitのためIdentity hard ruleを無言で削る。

---

## 5.4 `CMP-GW-01` Model Gateway

### 責務
- Local / Colab / Cloud / runtime固有差を正規化。
- Main Dialogue、Analyzer等のroleごとにprovider profileを解決。
- streamをCore共通Eventへ変換。
- warm session / connection / cacheはGateway以下の最適化として扱う。

### Input: `GenerationRequestV1`
- invocation role (`dialogue` etc.)
- context capsule ID + normalized context payload
- model profile ID
- attempt ID
- deadline
- cancellation scope ID
- generation limits
- delivery_started flagはfallback判定時に参照

### Output
- `GenerationStarted`
- `GenerationFirstToken`
- ordered `GenerationTextDelta`
- `GenerationCompleted`
- `ComponentAttemptResult`

### Provider abstraction rules
Coreへ露出しないもの:
- provider独自chunk format
- HTTP/WebSocket固有エラー型
- Colab tunnel固有session detail
- runtime-specific token IDs

Coreへ正規化して出すもの:
- status
- retryability
- latency
- normalized text delta
- terminal reason
- usage/metrics

### Fallback policy
- **delivery前**: profileで許可されたfallback providerを試せる。
- **delivery後**: providerを切り替えて同一文を継続しない。
- fallback attemptは別`attempt_id`。
- cancelled old attemptのlate deltaはdiscard。

### Remote policy
- Canonical DBをremoteへ置かない。
- Context Capsuleのremote-safe subsetだけ送る。
- remote runtime消失はcache/session lossとして扱い、人格state lossと扱わない。

---

## 5.5 `CMP-DLV-01` Delivery

### P0責務
- Mainのnormalized text streamをChat UIへ逐次render。
- **実際にrender済みの文字範囲**をdelivery truthとして追跡。
- stream failure/cancel時も未render tailとrender済みcontentを区別。

### Input
- generation attempt ID
- ordered text delta
- cancel/stop command

### Output
- `AssistantDeliveryCheckpoint`
- `AssistantDeliveryCompleted`
- `PlaybackStopped`相当のtext stop event（共通contract上）
- delivery failure result

### Canonicalization rule
- Assistant `MESSAGE.content` = 最終delivery checkpointまでのrender済み内容。
- model final buffer ≠ canonical assistant message。
- stream途中failureで一部だけ表示された場合、その一部を`completed_partial`としてcanonical化可能。

### Queue policy
- ordered bounded stream。
- cancelled/superseded attemptのdeltaはrenderしない。
- UIが追いつかずbackpressureが発生した場合は、canonical順序を壊すdropはしない。必要ならgeneration側をbackpressure/cancel。

### Future Voice compatibility
Voiceでは同じ責務が「speakerへ実際にplayoutされたtext span」に拡張される。Text v0.1でdelivery truth原則を先に固定する。

---

## 5.6 `CMP-ANL-01` Turn Analyzer

### 責務
- 完了したcanonical turnからsemantic proposalを1回で抽出。
- Memory / Self / User / Appraisal / Emotion / Relationshipを**提案**する。
- Domain stateを直接変更しない。

### Input
既存`TurnAnalysisInputV1`を使用。
必須基準:
- canonical user turn
- assistant delivered content only
- bounded recent conversation
- bounded relevant committed state
- state revision
- evidence reference whitelist

### Output
既存`TurnAnalysisV1`。
- Memory Candidate: 0..6
- Self Observation: 0..4
- User Observation: 0..4
- Appraisal: 0..1
- Emotion: 0..1
- Relationship Signal: 0..3

Empty resultは正常。

### Failure
- schema invalid → reject, no Domain mutation, retry候補。
- timeout/OOM/provider loss → pending retry, no foreground影響。
- stale base revision → proposalはDomain Update Layerで再検証。

---

## 5.7 `SUB-DUP-01` Domain Update Layer

### 責務
Analyzer等のsemantic proposalをcanonical Domain mutationへ変換できる**唯一の共通経路**。

内部責務を2段階に分ける。

#### Validator
- schema validity
- evidence/reference existence
- secret filter
- forget/soft-delete boundary
- duplicate/correction/change-over-time validation
- state revision conflict
- per-turn cap
- protected Memory Archive rule

#### Projector
- accepted ordinal signalをcode-owned mappingへ変換
- canonical ID/time/revisionを付与
- entity insert/update/revision/lifecycle eventを作成
- one transactionとしてcommit

### Commit outcomes
- `accepted`
- `accepted_as_evidence_only`
- `merged_duplicate`
- `rejected_invalid_reference`
- `rejected_secret`
- `rejected_forget_boundary`
- `rejected_stale`
- `rejected_policy`

### Atomicity
一つのanalysis commit中に途中失敗した場合、partial Domain mutationを残さない。

---
