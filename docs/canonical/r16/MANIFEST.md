# PROJECT_HANDOFF r16 Canonical Manifest

このdirectoryは、Git化前の完全版 `PROJECT_HANDOFF.md` r16を、内容を落とさず読みやすい単位へ分割して保持するためのcanonical setです。

## Original source identity

- Source name: `PROJECT_HANDOFF.md`
- Version: `0.1-draft-handoff-2026-09-27-r16`
- Original byte size: **201,327 bytes**
- Original SHA-256: `26ba528e595089adb22a4f950ba7db311271bd8c4d2060dd562c5dfebc721177`

> Git Contents API経由の書込みでは末尾空行の有無などで各chunkのbyte hashが元ローカル分割と数byte異なる場合がある。そのため、現時点では「Git上の全chunkを再結合したbyte列が元ファイルと完全一致した」とは主張しない。**section contentは元r16から復旧済み**であり、byte-for-byte完全性は別途再結合検証を行う場合に確定する。

## Required reading order

1. `00_HEADER.md`
2. `01_SCOPE.md`
3. `02A_REQUIREMENTS_AI.md`
4. `02B_REQUIREMENTS_V01_CORE_TO_UI.md`
5. `02C_REQUIREMENTS_ORCH_ANALYZER_RETRIEVAL_DOR.md`
6. `03A_DESIGN_3_1_3_7.md`
7. `03B_DESIGN_3_8_3_10.md`
8. `03C_DESIGN_ANALYZER.md`
9. `03D_DESIGN_VOICE.md`
10. `03E_DESIGN_LATENCY.md`
11. `03F_DESIGN_EVENT_CONTRACT.md`
12. `03G_DESIGN_STATE_FAILURE.md`
13. `03H_DESIGN_GOLDENS.md`
14. `03I_DESIGN_ANALYZER_TYPES.md`
15. `03J_DESIGN_TEXT_P0.md`
16. `04_JUDGMENTS.md`
17. `05_FIRST_IMPLEMENTATION.md`
18. `06_REFERENCES.md`
19. `07_RESUME.md`

この19ファイルが**1冊のPROJECT_HANDOFF r16**を構成する。

## Pre-Git exact split reference

Git復旧前にローカルで元r16を上記19区間へ分割し、順番に再結合した結果は元sourceと完全一致した。

- reconstructed bytes: **201,327**
- reconstructed SHA-256: `26ba528e595089adb22a4f950ba7db311271bd8c4d2060dd562c5dfebc721177`

したがって、分割境界そのものによる情報欠落はない。Git転記時の末尾newline正規化だけは上記注意の対象。

## Pre-Git chunk references

以下は元sourceをローカル分割した時点のbyte size / SHA-256。Git上のファイル監査時の比較基準に使う。

| File | Source bytes | Source SHA-256 |
|---|---:|---|
| `00_HEADER.md` | 1,416 | `7098964391478c894b9cb7f6e5be917e8136be26edc97c5a92a6cd26178a27e7` |
| `01_SCOPE.md` | 6,495 | `7f4cc54c161a9faff299ed763dcc5d8df2a798c6869971bff22978764780fff0` |
| `02A_REQUIREMENTS_AI.md` | 10,971 | `4a03cf9052cc5dfadd57eadefbb9d51989a96bd235c903c21172ed363da97248` |
| `02B_REQUIREMENTS_V01_CORE_TO_UI.md` | 6,338 | `964fffa7a88a2c34cb05d3cc0971f451bddb025b8831b9dd0a68f76fc171b385` |
| `02C_REQUIREMENTS_ORCH_ANALYZER_RETRIEVAL_DOR.md` | 25,852 | `a6fa0c3f51f151ea62a5f362339649dded8c6a549a2e543278afa8f0c9b065e6` |
| `03A_DESIGN_3_1_3_7.md` | 15,794 | `9b8c60c6bb0bdf331447ac0125a574dc9645049704681bde02a42e4b8f9d8f45` |
| `03B_DESIGN_3_8_3_10.md` | 9,661 | `20ad663735986fcb330cb2ce17081b6d3a8efcc93d25999353a786ac61e74192` |
| `03C_DESIGN_ANALYZER.md` | 8,022 | `13fc02f5a7da133be531e57d1315d8eba9ef63ad7d78383a77dc20753209eb76` |
| `03D_DESIGN_VOICE.md` | 5,382 | `a0c5f13c73363be3df4529239232a3c5db73ef5c240f9c2396a0bb48003bbde1` |
| `03E_DESIGN_LATENCY.md` | 10,520 | `3f9654c0a841f61e77e79fc9ce9e8387ecae9787b280c9df6fe1607711e9dcb5` |
| `03F_DESIGN_EVENT_CONTRACT.md` | 14,447 | `8e47b0ba0f45e4b8af4f700a62831aafa56b21e9a15cbfa06a64550381778c44` |
| `03G_DESIGN_STATE_FAILURE.md` | 19,817 | `2c5a30f53b9ccc7a01821b31cd04a225665789f64a8a150b65ef87bab8526d6b` |
| `03H_DESIGN_GOLDENS.md` | 13,789 | `3f583d5bca31507cca416f3d10d946a94273d185253485a919b0e9db14e6a52c` |
| `03I_DESIGN_ANALYZER_TYPES.md` | 16,286 | `3634cbcc0be2f8b617749d6238d8dc5c7d0069b6398a0395a879161ff2c721f1` |
| `03J_DESIGN_TEXT_P0.md` | 2,518 | `a7bfb9a9aabc076c75bf855c785631578e0fe1be2f1e4b52f1a7e93b0923da46` |
| `04_JUDGMENTS.md` | 6,993 | `01a867df43fc4b3991c9d7191eef8d165dd3f937b89fb97823246bb85bc5a76a` |
| `05_FIRST_IMPLEMENTATION.md` | 4,929 | `f447b19ce5cce63e0b71316997683eacf93d296eaa71d97eda23345720991f0d` |
| `06_REFERENCES.md` | 4,099 | `52c909459a2c96462aa3d535aeb2f059c2ff2e28c48613009fbed2beb3b4bfae` |
| `07_RESUME.md` | 17,998 | `7f8b3cfc5f5045e27350be8e2c943033844130c337cf7ea6b95db2bd24a07d68` |

## Canonical precedence

- 内容上の正本: この19-part r16 set + r16以後に明示された訂正。
- ルート `PROJECT_HANDOFF.md`: navigation/overview。完全版の代替ではない。
- `docs/handoff/*`: 読みやすい補助分割。canonical r16と矛盾した場合は本directoryを優先。
- standalone detail specs (`TEXT_V01_IMPLEMENTATION_SPEC`, `ANALYZER_GOLDEN_SPEC`, `RETRIEVAL_P0_SPEC`, `TEXT_V01_READINESS_AUDIT`) は各領域の詳細正本として併読する。
