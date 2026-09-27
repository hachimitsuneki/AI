# 1. 目的と範囲

## 1.1 利用者
- 主利用者は開発者本人。
- 長期的には、単なるQ&Aアシスタントではなく、友人・相棒として自然に共存できるAIを想定する。

## 1.2 解決したい課題
既存の対話AIは、多くの場合以下が弱い。
- 会話セッションをまたいだ「同じ個体」としての連続性
- 自分自身の経験・趣味・意見の形成
- ユーザーと別人格としての独立した判断
- 自発的に話す/行動するタイミングの自然さ
- 長期記憶を「保存」するだけでなく、自然に想起・訂正・忘却すること
- ユーザー不在時にも実際に活動し、その実体験を後から話せること

## 1.3 提供したい体験
目標は「呼び出された時だけ回答するAI」ではなく、PC内で継続して存在する相棒型AI。

例:
1. AIを起動すると前回までの関係・記憶が続いている。
2. ユーザーの趣味をコピーせず、自分なりの興味・意見を持つ。
3. 経験から「自分はこういうものが好きかもしれない」と自己発見する。
4. 将来的には画面を見る、ゲームをする、Webを読む、PCを操作する。
5. ユーザーが見ていない間にも、実際にAI Coreが稼働している時だけ自主活動できる。
6. 話したい時でも状況によって黙る。「何もしない」を正式な選択とする。

## 1.4 成功条件
### 長期目標
- 同一人格として認識できるが、反応や成長は完全に予測可能ではない。
- 趣味・意見・自己認識・関係性が、実際の経験に基づいて徐々に形成・変化する。
- 「優しい/親しい」と「ユーザーの意見へ同意する」を分離する。
- LLMを交換してもAI個体のSelf / Memory / Relationshipが維持される。

### v0.1成功条件
- 3日以上の別セッションをまたいでも「昨日話した同じ相手」と感じられる。
- 過去の重要情報を必要な時に自然に使える。
- ユーザーと異なる意見を自然に言える。
- 未形成の趣味・意見を捏造せず「まだ分からない」と言える。
- 数日利用したログから次の改善領域を特定できる。

## 1.5 制約
- 開発はCodexを主要実装手段として想定。
- ローカルファースト。必要に応じてクラウドLLMを併用可能。
- AI本体を特定モデルへ固定しない。
- 育成型開発: 完成仕様を最初に全固定せず、最小個体を動かし、ログと実体験から要件を育てる。
- 長期構想をMVP縮小のために削除しない。

## 1.6 主要参考
- Neuro-sama: 体験・人格の参考。内部実装は非公開なので推測で模倣しない。
- AIRI: Plugin / Capability / Avatar / Local inferenceなどシステム構成の参考。
- Open-LLM-VTuber: 音声・割り込み・VTuber shellの参考。
- AIKanojyo等の個人AI Chat: 長期記憶・想起・関係性を運用しながら育てる過程の参考。
- BDI (Belief-Desire-Intention): 自律行動の骨格候補。
- Generative Agents / Voyager / Letta: Memory / Reflection / Skill / persistent stateの参考。

## 1.7 最終目標として保持する機能範囲
以下は **v0.1で実装しない場合も要求から削除しない**。実装順序は未決であり、MVP縮小は却下を意味しない。

- 永続人格: Self / User / Relationship / Memoryをモデル交換や再起動をまたいで維持する。
- 自発性: ユーザー入力がなくても、状況・欲求・未完Intentから「話す / 考える / 行動する / 待つ」を選べる。
- 不在時活動: AI Coreが実際に稼働している間、許可範囲で自主活動し、その**実体験だけ**を後で話せる。
- 音声会話: STT/TTS、VAD、割り込み、将来的な低遅延/全二重会話。
- 身体表現: Live2D/VRM等のAvatar、表情・視線・モーションを内部状態/会話へ接続。
- 視覚/画面認識: 画像、デスクトップ画面、将来的なカメラ等をPerceptionとして扱う。
- Web活動: Webを読み、調査し、必要なら継続的な興味や経験へつなげる。
- PC操作: 明示的なCapability Permissionの下でアプリ/OSを操作。
- Game interaction: ゲーム状態を認識し、操作・学習・再挑戦し、実際のプレイ経験をMemoryへ残す。
- Skill learning: 成功した手順を再利用可能なSkill/Procedureとして保存・改善。
- Drive / Intent: 好奇心、社会性、新奇性、習熟、継続性などからIntentを生成・保持・延期・失効できる。
- Relationship growth: 単一好感度ではなく、共有履歴・信頼・気軽さ・二人固有のノリが経験で形成される。
- Emotion / Mood: 演出だけでなく、注意、行動傾向、Memory重要度、会話へ影響する。
- Knowledge / Belief: 基礎LLM知識とAI自身が得た知識を分離し、出典・確信度・更新履歴を持つ。
- Capability / Permission: 「やりたい」と「実行を許可されている」を分離し、危険度ごとにGateする。
- Plugin / MCP等の外部能力: Personality層と分離したCapabilityとして追加・交換可能にする。
- Model Evolution: 利用ログと評価Harnessを使い、Persona LoRA/SFT/DPO等で世代管理された中間進化を可能にする。Memoryをweightsへ無条件に焼き込まない。
- Multi-surface: 最初はDesktop/Textでも、将来的にVoice/Avatar/Web/Game等のShellへ同一AI Coreを接続できる構造を保つ。
- Explicit-request priority: AIが「今は一人でいたい」等のSocial Stateを持っていても、ユーザーからの明示依頼には原則応答する。Mood/Social Stateは主に口調・熱量・自発性へ影響し、通常依頼を無視する理由にはしない。
- Non-manipulative affect: Emotion/Relationshipを、罪悪感を煽る・離脱を妨げる・依存を強める等のユーザー操作へ利用しない。
- Self-perception separation: 実際に観測された行動傾向と「自分はこういう存在だ」というSelf Modelを分け、自己認識は証拠から更新される仮説として扱う。
- Intent richness: Intentはgoalだけでなくmotivation/origin/strength/created/expires/preferred context/interruptibilityを保持し、延期・再評価できる。
