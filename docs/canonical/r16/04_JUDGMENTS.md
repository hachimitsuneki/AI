# 4. 判断

## 4.1 明示決定
- 主体は便利な助手より友人・相棒寄り。ただし必要時は助手にもなる。
- 自分から発話/行動してよいが、過剰に常時話しかけない。
- 将来、ゲーム/画面/Web/PC操作まで目指す。
- 初期人格はある程度与える。経験で変化してよい。
- ユーザーと異なる意見を持ってよい。
- ユーザーの意見だからAIも同じ意見になる挙動は避ける。
- Neuro-samaを人格体験の主要参考とする。
- ユーザー不在時の自主活動を許可。
- AIは「今話したくない/一人でいたい」状態を持ってよい。
- ただし明示的なユーザー依頼には原則応答し、Social Stateは主に口調・熱量・自発性へ影響させる。
- User forgetはsoft deleteでAIから完全不可視。
- AI自身のMemory Archiveをv0.1から許可。
- 育成型開発を採用。
- v0.1 UIは汎用的なChat系。
- transitions.devをMotion参考にする。

## 4.2 方向性の合意
- LLMとAI本体を分離し、モデル交換可能にする。
- 人格の芯は安定させつつ、趣味/意見/自己認識は経験で変化。
- 「頭に浮かんだ」と「口に出す」を分離。
- 何もしないことを正常動作とする。
- 初期趣味・個別意見は多くを空白にする。
- Unknownを成長余地として扱う。

## 4.3 暫定案 / AI提案
- v0.1通常turnは「Main Dialogue LLM 1 blocking call + async Turn Analyzer 1 call」を第一候補とする。
- Recall/DB loadはMain call前に並列化し、Memory/Appraisal/User/Self/RelationshipごとにLLMを直列呼出ししない。
- Appraisalの永続状態化はpost-turn Analyzerで行い、current responseのニュアンス反応はMain Dialogue Model自身へ任せる。
- Turn Analyzerは一回のstructured multi-task出力に集約し、DB state transition自体はdeterministic codeで検証・適用する。
- Memory retrievalはextracted factsだけでなくraw conversation evidenceとのhybridを比較する。
- Persona chatのMain generatorを毎turn別modelへroutingする方式はv0.1では避け、model routingはsubtask/将来cloud escalationへ限定する案。
- Hikari/Bonsaiからは「targeted edit + sweep + regression harness + rollback可能なartifact」という進化方法を参考にし、具体的な安全除去編集は模倣しない。
- BDIを骨格に使う。
- Appraisal-based emotion。
- Mood = valence / activation / control。
- Relationshipを多次元管理。
- Self Hypothesisの昇格をv0.1では慎重にする。
- Memory Episode/Claim分離。
- Beliefを独立Entityにするかは未決。
- Emotion/Relationshipをユーザーへの罪悪感付与・依存誘導・利用継続圧力に使わない。
- Intentにはmotivation/origin/preferred_context/interruptibility等を持たせ、Action scoringとWAITを将来実装する。
- Turn Analyzerは「状態を決めるモデル」ではなくEvidence/Update Proposal generatorとして扱い、ordinal output→deterministic projector→atomic commitを第一候補とする。
- Foreground優先はapplication schedulerで保証し、llama.cpp/vLLM等のbackend queue/slotだけに依存しない。
- Analyzer候補はQwen3.5-0.8B/2B、Qwen3-1.7B、必要ならGemma 3 4Bを同一schema harnessで比較する。採用は未決。
- Colabを含むremote GPUをInference Provider候補に追加する。ただしColabをAI Core/Memoryの居住先にはせず、ephemeral computeとして扱う案を有力候補とする。採用は未決。
- AI VTuber/Voiceの低遅延方式として、`streaming ASR/turn detection → streaming Main LLM → first-fragment優先TTS + 後続並列合成 → barge-in cancellation`を将来Voice実装の第一候補とする。Voice自体の実装段階は後続だが、Orchestratorはこのstreaming接続を阻害しないinterfaceにする。
- Voice既定候補はSafeではなくBalanced latency profile: STT final到着後、semantic turn確定を待つ間にMain LLMをpreemptive開始し、turn確定後にTTSを解放する。Aggressive partial-transcript generationは実験用。
- 生成済みでもユーザーへ未deliveryのassistant tailはshared conversation/Memory/Relationship evidenceへ含めない。

## 4.4 保留
- AIの名前。
- 性別表現。
- 一人称。
- 細かい口調。
- v0.1でBeliefを独立Entity化するか。
- Dialogue OrchestratorのLLM呼出回数/役割分担。
- 実際のLocal LLM/SLM候補と量子化形式。
- ユーザー実機Hardware profile。
- Fine-tuning/LoRA開始時期と訓練方式。
- Orchestratorの最終profileはユーザー実機のGPU/VRAM/RAM/CPU/OSと実測benchmark後に決定。
- Colabをv0.1の通常Main推論へ使うか、benchmark/training専用に留めるか。無料/有料/専用VMのどの運用を想定するか。

## 4.5 却下/後回し
- **後回しだが要求として保持**: Voice / VAD / interruption / full-duplex候補 / Avatar / Live2D / VRM / Vision / Screen perception / Web autonomy / PC control / Game control / autonomous absent-time activity / Drive / Intent persistence / Proactive Policy / Skill learning / Tool/Plugin/MCP capability / Permission Gate / Reflection / Consolidation / Dream-like idle processing / model fine-tuning・中間進化。
- 上記はv0.1から外すだけで、機能削除・却下ではない。実装順序もまだ固定しない。
- 「一定時間ごとに機械的に話しかける」方式は基本方式にしない。
- Relationship = 単一の親密度スコアという設計は採用しない。
- 感情 = 単なる喜怒哀楽ゲージ中心の設計は採用しない。

## 4.6 訂正・置換
- 2026-09-26 r2ではv0.1整理の際、長期機能の多くを「後続」の一行へ圧縮し、要求詳細が実質的に弱く見える状態になっていた。r3で長期機能をCanonical Requirementsと概念ERへ復元。MVP縮小は要求削除を意味しない。
- 過去会話でv0.1要件IDが重複したため、本ファイルのドメイン別IDを正とする。
- UI参考調査から機能を追加/変更しない方針を明示。

---

## 4.X 仕様化の深さに関する決定（r14）
- **明示方向変更**: 実装前に全Golden/全例外を完全fixture化する方針は採らない。
- 育成型開発に合わせ、誤ると長期人格・Memory・privacy・canonical historyを壊す境界だけをP0として詳細化する。
- `AN-GOLD-001〜014`は要求としてすべて保持するが、実装前の詳細fixtureはP0 7件（002/003/004/006/011/012/014）に限定する。
- 残りP1（001/005/007/008/009/010/013）は却下ではなく、初期実働ログから失敗例を得た後に詳細化する。
- exact numeric weight / confidence threshold / prompt wording / exhaustive colloquial variationは実働前に固定しない。
- 詳細: `ANALYZER_GOLDEN_SPEC.md`。
