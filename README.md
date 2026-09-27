# AI Companion v0.1 — Implementation Handoff

自立型AI / 継続人格型デジタルコンパニオンの **Text v0.1 実装着手用リポジトリ** です。

Text v0.1 は Definition of Ready 監査済みで、**P0 blocker = 0**。ここからは事前仕様を増やし続けず、まず最小Vertical Sliceを実装して実働ログから育てます。

## Codex / Luna が最初に読む順序

1. `PROJECT_HANDOFF.md` — 最上位handoff。目的・要件・設計・判断・実装順・再開情報
2. `docs/TEXT_V01_IMPLEMENTATION_SPEC.md` — P0実装仕様の入口
3. `docs/text_v01/01_CORE_CONTRACTS.md`
4. `docs/text_v01/02_COMPONENT_DETAILS.md`
5. `docs/text_v01/03_RUNTIME_ACCEPTANCE.md`
6. `docs/text_v01/04_EXPLICIT_COMMANDS.md`
7. `docs/TEXT_V01_READINESS_AUDIT.md`
8. `docs/ANALYZER_GOLDEN_SPEC.md`
9. `docs/RETRIEVAL_P0_SPEC.md`
10. `CODEX_START.md` — 着手順と実装時のルール

`PROJECT_HANDOFF.md` はGit実装用に読みやすく整理した版です。長期要求を削ったものではなく、Canonical requirementsは以下へ分割して保持しています。

- `docs/handoff/01_SCOPE.md`
- `docs/handoff/02_REQUIREMENTS_AI.md`
- `docs/handoff/03_REQUIREMENTS_V01_A.md`
- `docs/handoff/04_REQUIREMENTS_V01_B.md`

## 現在の状態

- Text v0.1: **READY FOR CODEX IMPLEMENTATION**
- P0 blocker: **0**
- 実コード / DB migration / deployment / automated test code: **未着手**
- Main / Analyzer / Embeddingの最終モデル: **未決・実測後に決定**
- Retrieval exact scoring / threshold / reranker: **実測後に調整**
- Voice / Avatar / Web / PC / Game / 自主活動等: **長期要求として保持、Text v0.1の着手ブロッカーにはしない**

## 実装開始順

```text
WP-TXT-01 Canonical Domain schema + repository contract
↓
WP-TXT-02 Turn / Event / Attempt lifecycle
↓
WP-TXT-03 Retrieval + WP-TXT-04 Context Builder
↓
WP-TXT-05 Gateway/Main streaming + WP-TXT-06 Delivery truth
↓
まず「1ターン普通に会話できる」foreground vertical slice
↓
WP-TXT-07 Turn Analyzer + WP-TXT-08 Validator/Projector
↓
WP-TXT-09 Developer Inspector + WP-TXT-10 Golden Harness
```

## 絶対に崩さない境界

- canonical stateはsingle-writer。
- UserとAI Selfを混同しない。
- `soft_deleted` MemoryをRecall / Prompt / Analyzer evidenceへ復活させない。
- 曖昧な`忘れて`では推測削除しない。
- secret / credentialを長期Memoryへ保存しない。
- assistant canonical messageは**実際にdeliveryされた範囲だけ**。
- Analyzerはproposal generator。Memory / Self / User / Relationship / Affectの確定mutationはValidator + Projector経由。
- delivery前のMain failureのみfallback可能。delivery後に別modelで文章を無言継続しない。
- Analyzer失敗はforeground conversationを止めない。
- 長期要求をv0.1外という理由で削除しない。
- 未決事項を勝手に仕様確定しない。

仕様矛盾やP0 blockerを見つけた場合は、大きな設計変更を独断で入れず、影響するRequirement / Component / Entity / Goldenと最小解決案を報告してください。
