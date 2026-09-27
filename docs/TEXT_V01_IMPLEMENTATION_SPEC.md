# TEXT_V01_IMPLEMENTATION_SPEC.md

- Project: 自立型AI / 継続人格型デジタルコンパニオン
- Spec: Text v0.1 非コード実装仕様
- Version: 2026-09-27-r2
- Status: 実装仕様化済み / 実コード未着手
- Canonical parent: `PROJECT_HANDOFF.md` r16

このファイルはGitHub上の**実装仕様ナビゲータ**です。元の単一文書は、内容を落とさず以下の4ファイルへ分割しています。Codexは番号順にすべて読んでください。

1. [`text_v01/01_CORE_CONTRACTS.md`](text_v01/01_CORE_CONTRACTS.md) — 実装対象、component topology、Contract Matrix、State ownership、Orchestrator / Retrieval
2. [`text_v01/02_COMPONENT_DETAILS.md`](text_v01/02_COMPONENT_DETAILS.md) — Context / Gateway / Delivery / Analyzer / Domain Update
3. [`text_v01/03_RUNTIME_ACCEPTANCE.md`](text_v01/03_RUNTIME_ACCEPTANCE.md) — normal sequence、degradation、priority、deployment、privacy、observability、acceptance、WP、保留事項、ER/status
4. [`text_v01/04_EXPLICIT_COMMANDS.md`](text_v01/04_EXPLICIT_COMMANDS.md) — r16 Explicit Remember / Forget P0 boundary

## 実装開始順

`WP-TXT-01 → WP-TXT-02 → WP-TXT-03 + WP-TXT-04 → WP-TXT-05 + WP-TXT-06`

まずforegroundの「1ターン普通に会話できる最小Vertical Slice」を完成・検証し、その後`WP-TXT-07 + WP-TXT-08`へ進みます。

## 不変条件

- canonical stateはsingle-writer。
- assistant canonical messageは実際にdeliveryされた範囲だけ。
- `soft_deleted` MemoryはRecall/Prompt/Analyzer evidenceへ復活させない。
- Analyzerはproposalのみ生成し、Domain mutationはValidator + Projector経由。
- secret / credentialは長期Memoryへ保存しない。
- delivery前のMain failureのみfallback可能。delivery後の無言model継ぎ足しは禁止。
- Analyzer失敗はforeground conversationを止めない。

詳細は上記4ファイルを正とします。
