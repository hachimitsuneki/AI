# 6. 参照資料

## 6.1 実際に調査・参照した主な公開情報
- Levinson & Torreira (2015), *Timing in turn-taking*: 人間会話のturn gapが約200msで、応答準備が相手発話中から重なるという設計根拠。
- LiveKit Agents docs (2026-09確認): audio turn detector、dynamic endpointing、preemptive generation、adaptive interruption、AEC/noise/echo cancellation。
- Pipecat Smart Turn v3.2 (2026-09確認): 日本語を含むaudio-native turn detection、local CPU inference、VADとの組合せ。
- Pipecat Audio Metrics (2026-09確認): mic stop→bot system-audio startを同一clockで測るend-to-end latency計測例。
- llama.cpp server docs/source (2026-09確認): warmup、continuous batching、`cache_prompt` KV prefix reuse、`n_predict=0` prompt-only cache prefill、speculative decoding。
- Neuro-sama: 体験参考。内部実装は非公開。
- AIRI: GitHub/docsのPlugin/Capability/Local inference/Avatar関連。
- Open-LLM-VTuber: GitHub。
- AIKanojyo: Zenn上の長期Memory/Recall/Relationship開発記録。
- 個人AITuber事例: かこ、AIニケちゃん、AITuber OnAir、Toki、Pippin等。
- BDI / Generative Agents / Voyager / Letta / Memory survey / Proactive conversation等の研究。
- llama.cpp / whisper.cpp / MCP等の一次資料。
- UI参考: transitions.dev、各種Chat UI。UI参考は機能要件へ直接持ち込まない。
- Hikari07jp/Ternary-Bonsai-2-27B-Abliterated-GGUF model card: quant-native edit、amplitude sweep、regression harness、preview caveats。
- PrismML Ternary Bonsai 2 27B model card / known issues: PTQ1/PQ2 footprint、runtime要件、packing別性能、prompt cache既知問題。
- llama.cpp server docs: OpenAI-compatible APIs、schema-constrained JSON、continuous batching、prompt/cache reuse、reranking、speculative decoding。
- vLLM docs: speculative decoding / draft model / routing候補比較用。
- LongMemEval (ICLR 2025) / Redis 2026 evaluation: long-term memory能力とraw+extracted hybrid retrieval。
- Mem0 2026 research: single-pass ADD-only extraction、async extraction/retrieval、multi-signal retrieval、memory decay。
- Qwen3 Embedding/Reranker 0.6B model cards: local retrieval helper候補（未採用、benchmark対象）。
- Hugging Face PEFT/TRL docs: LoRA/QLoRA/SFT/DPOの将来中間進化候補。

### 6.1.1 参照トレーサビリティ上の注意
- 本ファイルr4は **参照可能なProject会話サマリ + 現在チャット + r3ファイル** を照合して機能/要件を復元した。過去別チャットの全生ログを逐語的に再読できたわけではない。
- 公開調査のうちURLが現在の会話に残っているものは以下を再開時の一次参照候補とする（確認時点: 2026-09-26 JST）:
  - Hikari07jp Bonsai edit: https://huggingface.co/Hikari07jp/Ternary-Bonsai-2-27B-Abliterated-GGUF
  - PrismML Ternary Bonsai 2: https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf
  - llama.cpp server/docs: https://github.com/ggml-org/llama.cpp
  - vLLM docs: https://docs.vllm.ai/
  - Qwen3 Embedding/Reranker model cards: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B , https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
- 個人AI/AITuber事例の一部は内容要約はProject会話サマリに残っているが、元URLを本handoffへ完全転記できていない。未確認のURLを推測で作らず、必要な論点で再検索する。

## 6.2 今回未確認/不足
- Hikari/Bonsai公開情報は確認済み。ただしHikari版のdirection extraction/reference construction/rounding schedule詳細は本人が未公開。
- 実機Hardware条件未取得。
- v0.1 Orchestratorの性能比較は未実施。
- 候補Local modelの日本語キャラチャット/structured extraction実測未実施。
- 過去の全会話発言単位のsource IDまでは復元できていないため、要件の出典は現在「ユーザー明示/方向性/AI提案/調査」粒度。Codex着手前の最終仕様化時に、重要な明示決定へ会話日付/節を追加する。

---
