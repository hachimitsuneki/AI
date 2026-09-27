# AI Companion v0.1 — Implementation Handoff

このリポジトリは、自立型AI / 継続人格型デジタルコンパニオンの **Text v0.1 実装着手用仕様** です。

## 最初に読む順序

1. `PROJECT_HANDOFF.md`
2. `docs/TEXT_V01_IMPLEMENTATION_SPEC.md`
3. `docs/TEXT_V01_READINESS_AUDIT.md`
4. `docs/ANALYZER_GOLDEN_SPEC.md`
5. `docs/RETRIEVAL_P0_SPEC.md`
6. `CODEX_START.md`

## 現在の状態

- Text v0.1 は Definition of Ready 監査済み。
- P0 blocker: 0。
- 実コード / DB migration / deployment / automated test code は未着手。
- 実装前の過剰仕様化はここで打ち止め。
- P1 Golden、Retrievalの最終スコア、最終モデル選定、Voice詳細は初期実働後または各フェーズ直前に決める。

## 実装開始順

`WP-TXT-01 → WP-TXT-02 → WP-TXT-03 + WP-TXT-04 → WP-TXT-05 + WP-TXT-06`

まず foreground の「1ターン普通に会話できる最小Vertical Slice」を完成・検証する。
その後 `WP-TXT-07 + WP-TXT-08` で persistent Memory / Self / User / Relationship の更新経路へ進む。

## 重要ルール

- `PROJECT_HANDOFF.md` を最上位の引継ぎ資料とする。
- 長期要求を v0.1 の範囲外という理由で削除しない。
- 未決事項を勝手に確定しない。
- 仕様矛盾や重大な不足を見つけたら、大きな設計変更を独断で入れず報告する。
- canonical state の single-writer、delivery truth、forget/secret 境界を崩さない。
