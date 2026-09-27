# TEXT_V01_IMPLEMENTATION_SPEC.md — Canonical Index

- Project: 自立型AI / 継続人格型デジタルコンパニオン
- Logical specification: **Text v0.1 非コード実装仕様**
- Version: `2026-09-27-r2`
- Status: 実装仕様化済み / 実コード未着手

> **注意:** このファイルは仕様全文の要約ではなく、完全版へのindexです。このファイルだけを読んで実装しないでください。

Git化前には `TEXT_V01_IMPLEMENTATION_SPEC.md` という**1冊の独立仕様書**として存在していました。長文を消さずGitで扱いやすくするため、現在は以下4partへ物理分割しています。

## Canonical reading order

1. [`text_v01/01_CORE_CONTRACTS.md`](text_v01/01_CORE_CONTRACTS.md) — sections 1–5.2
2. [`text_v01/02_COMPONENT_DETAILS.md`](text_v01/02_COMPONENT_DETAILS.md) — sections 5.3–5.7
3. [`text_v01/03_RUNTIME_ACCEPTANCE.md`](text_v01/03_RUNTIME_ACCEPTANCE.md) — sections 6–16
4. [`text_v01/04_EXPLICIT_COMMANDS.md`](text_v01/04_EXPLICIT_COMMANDS.md) — section 17 / r16 readiness patch

Integrity metadata:
- original source bytes: **29,854**
- original source SHA-256: `c4b736ac99268b39e214ec11712ff967dc7698b7071f1788a5972206e5dfb59b`
- manifest: [`text_v01/MANIFEST.md`](text_v01/MANIFEST.md)

## Relationship to the other specifications

この仕様書は5つのcanonical source specsのうち1冊です。全体台帳は [`SPEC_REGISTRY.md`](SPEC_REGISTRY.md)。

- `PROJECT_HANDOFF.md` r16 — 全体handoff
- **このText v0.1 implementation spec** — component / ownership / failure / acceptance / work package
- `TEXT_V01_READINESS_AUDIT.md` — 実装着手監査
- `ANALYZER_GOLDEN_SPEC.md` — Analyzer P0 semantic Golden
- `RETRIEVAL_P0_SPEC.md` — Retrieval P0 field contract

## Precedence

このindexと4partの内容に差異がある場合、**4partの本文**を正とする。`PROJECT_HANDOFF r16`の全体決定・訂正とも併読する。
