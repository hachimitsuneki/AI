# Specification Registry

このファイルは、Git化の過程で仕様書が要約・統合されて消えないようにするための**仕様書台帳**です。

## Canonical source specifications

このチャットでCodex引継ぎ前に独立した正本として作成された仕様書は、以下の **5冊** です。

| # | Source specification | Pre-Git source | Source bytes | Source SHA-256 | Git preservation |
|---:|---|---|---:|---|---|
| 1 | `PROJECT_HANDOFF.md` r16 | `PROJECT_HANDOFF.md` | 201,327 | `26ba528e595089adb22a4f950ba7db311271bd8c4d2060dd562c5dfebc721177` | `docs/canonical/r16/` のordered chunks |
| 2 | `TEXT_V01_IMPLEMENTATION_SPEC.md` r2 | `TEXT_V01_IMPLEMENTATION_SPEC.md` | 29,854 | `c4b736ac99268b39e214ec11712ff967dc7698b7071f1788a5972206e5dfb59b` | `docs/text_v01/01_CORE_CONTRACTS.md` → `04_EXPLICIT_COMMANDS.md` |
| 3 | `TEXT_V01_READINESS_AUDIT.md` | `TEXT_V01_READINESS_AUDIT.md` | 8,045 | `25935126e09c6b0caf82665e820c07d9e755c598a4b1c92d90da0587334af697` | `docs/TEXT_V01_READINESS_AUDIT.md` |
| 4 | `ANALYZER_GOLDEN_SPEC.md` | `ANALYZER_GOLDEN_SPEC.md` | 11,016 | `dec482523b994ec4b68c695ea4566a6a3810bebe2f5c6db808d9e600a04914cb` | `docs/ANALYZER_GOLDEN_SPEC.md` |
| 5 | `RETRIEVAL_P0_SPEC.md` | `RETRIEVAL_P0_SPEC.md` | 12,191 | `cb35d283e9f4150e64068d05d5e841054a0172e76d1c730333be2a26928b1abd` | `docs/RETRIEVAL_P0_SPEC.md` |

### Important

- **5冊を1〜2冊へ統合した扱いにはしない。** もともと独立仕様書だったものは独立仕様として維持する。
- Git上で長文を複数Markdownへ分割していても、それは可読性のための**物理分割**であり、仕様書の論理個数を増減させるものではない。
- `README.md` / `CODEX_START.md` / 各index・manifestはナビゲーション文書であり、上記5冊とは別の製品仕様書として数えない。
- 過去の`PROJECT_HANDOFF_rXX_backup.md`は版履歴であり、独立仕様書の欠落とは数えない。

## Physical Git layout

### 1. PROJECT_HANDOFF r16

完全なr16の内容は `docs/canonical/r16/` に順番を保って分割している。
読み順・source hashは `docs/canonical/r16/MANIFEST.md` を参照。

ルートの `PROJECT_HANDOFF.md` は**入口/索引**であり、そこだけを全文正本として扱わない。

### 2. Text v0.1 implementation specification

完全な実装仕様は以下4partを順番に読む。

1. `docs/text_v01/01_CORE_CONTRACTS.md`
2. `docs/text_v01/02_COMPONENT_DETAILS.md`
3. `docs/text_v01/03_RUNTIME_ACCEPTANCE.md`
4. `docs/text_v01/04_EXPLICIT_COMMANDS.md`

`docs/TEXT_V01_IMPLEMENTATION_SPEC.md` はこの4partへのindexであり、単独で仕様全文ではない。

### 3–5. Standalone specifications

- `docs/TEXT_V01_READINESS_AUDIT.md`
- `docs/ANALYZER_GOLDEN_SPEC.md`
- `docs/RETRIEVAL_P0_SPEC.md`

これらは1ファイルのまま保持する。

## Integrity policy going forward

仕様を整理・分割するときは以下を守る。

1. 元の独立仕様書を勝手に統合・削除しない。
2. 要約版を作っても、要約版を完全版の代替として扱わない。
3. 要件・ER・Golden・判断履歴・長期要求を「実装に今不要」という理由で削除しない。
4. Canonical sourceを更新する場合は、何を置換したかと理由を記録する。
5. Git handoff前にこのregistryと実ファイルを照合する。

## Known limitation of this registry

この台帳は、現在このProject/会話から実際に参照できた生成ファイルを基準に作成した。過去の別チャットで独立仕様書が作られていたが現在の参照範囲に存在しない場合まで、存在しないと断定するものではない。そのような資料が後から見つかった場合は、削除扱いにせずregistryへ追加して差分監査する。
