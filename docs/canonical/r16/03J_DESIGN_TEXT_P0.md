## 3.18 Text v0.1 P0 非コード実装仕様（r13）

詳細は `TEXT_V01_IMPLEMENTATION_SPEC.md` を正とする。本handoffでは要点のみ保持する。

### Component boundary
- `CMP-ORCH-01` Orchestrator: Turn/Event/Attempt/cancel/deadlineの統括。
- `CMP-RETR-01` Retrieval: canonical stateへのread-only recall。vector/lexical degradationを吸収。
- `CMP-CTX-01` Context Builder: immutable `ContextCapsuleV1`を構築。
- `CMP-GW-01` Model Gateway: Local/Colab/Cloud/runtime差を正規化。
- `CMP-DLV-01` Delivery: UIへ実際にrenderされた範囲のdelivery truthを所有。
- `CMP-ANL-01` Turn Analyzer: semantic proposalのみ生成しDomain mutationしない。
- `SUB-DUP-01` Domain Update Layer: Validator + Projector。canonical Memory/Self/User/Relationship/Affect mutationの共通境界。独立service化はP0で不要。

### P0 foreground vertical slice
```text
TextSubmit
  → canonical UserTurn commit
  → [parallel] Retrieval + current Domain snapshot + recent context
  → ContextCapsuleV1
  → Main Dialogue via Gateway
  → streaming Delivery
  → delivered spanからcanonical assistant Message確定
  → user-facing turn complete
  → async Turn Analyzer
  → deterministic Validator / Projector
  → atomic Domain commit
```

### Single-writer ownership
- Turn lifecycle / sequence / cancel scope: Orchestrator。
- Assistant delivery truth: Delivery。
- Memory/Self/User/Relationship/Affect canonical mutation: Domain Update Layer。
- Retrieval / Context / Analyzer / Gatewayはsemantic Domain stateを直接書き換えない。

### Degradation
- vector failure → lexical only。lexical failure → vector only。両方 failure → empty degraded recallで会話継続。
- Remote/Main failureはdelivery前だけfallback可。delivery後は別modelで文章を継ぎ足さずpartial確定。
- Analyzer failure/invalid schemaはChatへ影響させずpending retry。Domain mutationなし。
- Domain update failureはatomic rollback。会話履歴はdelivery truthに従って保持。

### Codex work packages（実コードはまだ未着手）
`WP-TXT-01` Domain schema → `02` Turn/Event lifecycle → `03` Retrieval + `04` Context → `05` Gateway + `06` Delivery → foreground vertical slice → `07` Analyzer + `08` Validator/Projector → persistent vertical slice → `09` Inspector + `10` Golden Harness。

### ER影響
今回の変更はcomponent/interface/ownership仕様であり、Domain ER/Technical ERのEntity追加なし。
