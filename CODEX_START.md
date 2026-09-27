# Codex Start Instruction

このリポジトリのText v0.1を実装します。

## 最初に必ず読む

`PROJECT_HANDOFF.md`は入口であり、短い概要だけを仕様全文として扱わないでください。

1. `PROJECT_HANDOFF.md`
2. `docs/SPEC_REGISTRY.md`
3. `docs/canonical/r16/MANIFEST.md`の順序で**PROJECT_HANDOFF r16 全19part**
4. `docs/TEXT_V01_IMPLEMENTATION_SPEC.md`
5. `docs/text_v01/MANIFEST.md`の順序で**Text v0.1 implementation spec 全4part**
6. `docs/TEXT_V01_READINESS_AUDIT.md`
7. `docs/ANALYZER_GOLDEN_SPEC.md`
8. `docs/RETRIEVAL_P0_SPEC.md`

Canonical source specsは5冊です。index/READMEだけを読んで、そこに記載のない要求を削除・未要求扱いしないでください。

## 目的

Text v0.1 の P0 を実装します。最初から全機能を実装するのではなく、まず foreground conversation path の最小Vertical Sliceを動かします。

## 着手順

1. `WP-TXT-01` Canonical Domain schema + repository contract
2. `WP-TXT-02` Turn/Event/Attempt lifecycle
3. `WP-TXT-03` Retrieval + `WP-TXT-04` Context Builder
4. `WP-TXT-05` Gateway/Main streaming + `WP-TXT-06` Delivery truth
5. ここで「1ターン普通に会話できる」foreground pathを実装・検証
6. その後に `WP-TXT-07` Turn Analyzer + `WP-TXT-08` Validator/Projector
7. `WP-TXT-09` Inspector + `WP-TXT-10` Golden Harness

## 守ること

- 長期要求は削除しない。
- 未決事項を勝手に確定しない。
- Main / Embedding / Analyzer 等の最終モデル選定を仕様上の確定事項として扱わない。
- Retrievalのexact scoring weight / threshold / reranker条件を先に固定しない。
- AnalyzerのP1 Golden完全化を実装着手のブロッカーにしない。
- Domain mutationは Validator + Projector 経由に限定する。
- `soft_deleted` MemoryをRecall/Prompt/Analyzer evidenceへ復活させない。
- secret / credentialを長期Memoryへ保存しない。
- assistantのcanonical messageは、実際にdeliveryされた範囲だけとする。
- delivery前のMain failureのみfallback可能。delivery後に別modelで文章を無言継続しない。
- Analyzer失敗はforeground conversationを止めない。
- overview/indexにない項目でもcanonical r16に存在する要求を無視しない。

## 仕様矛盾を見つけた場合

推測で大きく設計変更せず、以下を報告してください。

- 矛盾している仕様箇所
- 影響するRequirement / Component / Entity / Golden
- 最小の解決候補
- 実装を止める必要があるか、独立部分は進められるか

## 最初の完了報告で欲しいもの

- 実装したWP
- 実際に動作確認した範囲
- 未実装の範囲
- 仕様から変更した点（あれば）
- テスト結果
- known issue / 次に決める必要がある事項

「コードが存在する」ことと「実装・検証済み」を分けて報告してください。
