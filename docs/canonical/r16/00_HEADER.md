# PROJECT_HANDOFF.md

- Project: 自立型AI / 継続人格型デジタルコンパニオン
- Version: 0.1-draft-handoff-2026-09-27-r16
- Updated: 2026-09-27 JST
- Status: Text v0.1 Definition of Ready監査完了 / Codex実コード未着手
- Completeness audit: r4までの欠落監査を維持し、r5 Turn Analyzer、r6 remote ephemeral inference、r7 AI VTuber/Voice低遅延設計、r8でend-to-end latency budget・precompute/cache・delivery truth・resource isolationを具体化し、r9でOrchestratorのevent/command/snapshot型契約を固定し、r10でproducer/consumer・状態遷移・failure/cancel責務を仕様化し、r11でGolden Event Sequenceとcanonical-state不変条件を回帰試験仕様として固定し、r12でTurnAnalysisV1のfield-level型制約・LLM/code ownership・semantic golden casesを固定し、r13でText v0.1のP0 component contract / state ownership / degrade / work packageを非コード実装仕様として固定、r15でRetrieval P0の最小field-level contractとforget-race再検証境界を固定
- Canonical continuation file: このファイルを次チャット開始時に最優先で読む

> 注意: 会話中に `REQ-V01-016` / `REQ-V01-017` のID衝突が発生したため、本版でv0.1の詳細要件をドメイン別IDへ正規化した。旧IDは「後の決定で置換」とし、今後は本ファイル記載のIDを正とする。

---

