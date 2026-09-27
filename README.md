# AI Companion v0.1 — Implementation Handoff

自立型AI / 継続人格型デジタルコンパニオンの **Text v0.1 実装着手用リポジトリ**。

## 重要: 仕様書を要約版だけで読まない

Git化時に長文Markdownを短い要約へ置き換えてしまう問題が一度発生したため、現在は**元の独立仕様書の個数と内容を台帳管理**しています。

- Canonical source specs: **5冊**
- Registry: [`docs/SPEC_REGISTRY.md`](docs/SPEC_REGISTRY.md)
- `PROJECT_HANDOFF r16`完全版: [`docs/canonical/r16/MANIFEST.md`](docs/canonical/r16/MANIFEST.md) に従う19part
- `TEXT_V01_IMPLEMENTATION_SPEC r2`完全版: [`docs/text_v01/MANIFEST.md`](docs/text_v01/MANIFEST.md) に従う4part

ルートの`PROJECT_HANDOFF.md`や`docs/TEXT_V01_IMPLEMENTATION_SPEC.md`は**入口/index**であって、全文仕様の代替ではありません。

## Canonical specification set

1. `PROJECT_HANDOFF.md r16` — 全体handoff。Gitでは19partに物理分割
2. `TEXT_V01_IMPLEMENTATION_SPEC.md r2` — Text P0実装仕様。Gitでは4partに物理分割
3. `TEXT_V01_READINESS_AUDIT.md`
4. `ANALYZER_GOLDEN_SPEC.md`
5. `RETRIEVAL_P0_SPEC.md`

`README.md` / `CODEX_START.md` / manifest / indexはnavigationであり、上記5冊を統合・削除しません。

## Codex / Luna reading order

1. [`PROJECT_HANDOFF.md`](PROJECT_HANDOFF.md)
2. [`docs/SPEC_REGISTRY.md`](docs/SPEC_REGISTRY.md)
3. [`docs/canonical/r16/MANIFEST.md`](docs/canonical/r16/MANIFEST.md) の順序でr16全文
4. [`docs/TEXT_V01_IMPLEMENTATION_SPEC.md`](docs/TEXT_V01_IMPLEMENTATION_SPEC.md)
5. [`docs/text_v01/MANIFEST.md`](docs/text_v01/MANIFEST.md) の順序でText実装仕様4part全文
6. [`docs/TEXT_V01_READINESS_AUDIT.md`](docs/TEXT_V01_READINESS_AUDIT.md)
7. [`docs/ANALYZER_GOLDEN_SPEC.md`](docs/ANALYZER_GOLDEN_SPEC.md)
8. [`docs/RETRIEVAL_P0_SPEC.md`](docs/RETRIEVAL_P0_SPEC.md)
9. [`CODEX_START.md`](CODEX_START.md)

## Current state

- Text v0.1: **READY FOR CODEX IMPLEMENTATION**
- P0 blocker: **0**
- 実コード / DB migration / deployment / automated test code: **未着手**
- Main / Analyzer / Embedding最終モデル: 未決、実測後
- Retrieval exact scoring / threshold / reranker: 実働後調整
- Voice / Avatar / Web / PC / Game / 自主活動等: 長期要求として保持

## Initial implementation order

```text
WP-TXT-01
↓
WP-TXT-02
↓
WP-TXT-03 + WP-TXT-04
↓
WP-TXT-05 + WP-TXT-06
↓
1ターン会話できるforeground vertical slice
↓
WP-TXT-07 + WP-TXT-08
↓
WP-TXT-09 + WP-TXT-10
```

## Do not break

- canonical state single-writer
- Self/User separation
- soft-deleted Memory resurrection禁止
- ambiguous forgetでguess-delete禁止
- secret/credential persistence禁止
- delivered assistant spanだけをcanonical message化
- Analyzerから直接Domain mutation禁止
- delivery後のsilent model fallback禁止
- Analyzer failureでChat停止禁止
- v0.1外という理由で長期要求を削除しない

概要に書かれていない機能を「不要/却下」と解釈せず、必ずcanonical r16とRegistryを確認してください。
