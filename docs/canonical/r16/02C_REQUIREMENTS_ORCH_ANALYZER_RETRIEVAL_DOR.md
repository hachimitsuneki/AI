### Runtime / Orchestrator
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-ORCH-01 | 通常ターンのforeground generative callは原則Main Dialogue LLM 1回 | AI提案・強く推奨 | Memory/Appraisal等のために複数LLMを直列実行してTTFTを悪化させない |
| REQ-V01-ORCH-02 | Recall・DB state load・明示command処理をMain生成前に並列化 | AI提案・強く推奨 | 独立処理を直列化しない |
| REQ-V01-ORCH-03 | 応答後にTurn Analyzerを非同期実行し、Memory/Self/User/Appraisal/Relationship候補を1回のstructured callで抽出 | AI提案・強く推奨 | foreground responseを解析完了待ちにしない |
| REQ-V01-ORCH-04 | foreground requestはbackground analysis/reflectionより常に高優先 | AI提案・重要 | 新しいUser Message到着時にbackgroundがTTFTを大きく悪化させない |
| REQ-V01-ORCH-05 | decay、Memory lifecycle、soft delete、confidence集約、provenance、token budget等は決定論的コードが所有 | AI提案・重要 | LLMの数値気分で状態遷移しない |
| REQ-V01-ORCH-06 | SLM/LLM由来の内部更新はschema-constrained structured output + validationを通す | AI提案・重要 | 不正/欠損outputをDBへ直接commitしない |
| REQ-V01-ORCH-07 | Analyzer遅延/失敗時もChat継続可能 | AI提案・重要 | last committed state + recent raw turnsで次ターンを処理可能 |
| REQ-V01-ORCH-08 | Reflection/Consolidation/Archive reviewは毎ターン実行せずidle/batch job化 | AI提案・強く推奨 | 通常会話のcritical path外 |
| REQ-V01-ORCH-09 | Model rolesをDialogue / Analyzer / Embedding / optional Rerankerへ分離しGatewayで交換可能 | AI提案・重要 | 個別benchmarkで差替可能 |
| REQ-V01-ORCH-10 | TTFT・E2E・prefill・decode(TPOT/tok/s)・input/output tokens・VRAM/RAM・background delayを計測 | AI提案・必須級 | 各turnのResponse Traceへ記録 |
| REQ-V01-ORCH-11 | v0.1では人格ChatのMain generatorを毎ターンrouterで別モデルへ切替えない | AI提案 | Voice/persona driftを避け、routingはbounded subtasks優先 |
| REQ-V01-ORCH-12 | Retrievalはraw conversation evidence + extracted Memoryのhybridを比較可能にする | AI提案・強く推奨 | LongMemEval系scenarioで比較 |
| REQ-V01-ORCH-13 | Turn Analyzerの出力はDB確定値ではなくEvidence/Update Proposalとして扱う | AI提案・強く推奨 | LLM出力から直接Entityをmutationせず、validator/projectorを通す |
| REQ-V01-ORCH-14 | Analyzerの強度・確信は原則ordinal enumで出力し、pseudo-precise floatをLLMに決めさせない | AI提案・重要 | weak/medium/strong等をコード側で重みへ写像できる |
| REQ-V01-ORCH-15 | Analyzer commit前にreferential integrity / soft-delete・forget境界 / secret filter / duplicate・correction / stale revisionを検証 | AI提案・必須級 | 不整合・削除済み・秘密情報・古い解析結果が状態へ復活しない |
| REQ-V01-ORCH-16 | Turn Analysisは`turn_id + analyzer_version`でidempotent、state revisionを持ちstale resultを安全にreject/rebaseできる | AI提案・重要 | retryしても二重Memory/二重Relationship updateを起こさない |
| REQ-V01-ORCH-17 | Foreground優先はアプリ側Schedulerで保証し、runtimeのslot/process priorityだけに依存しない | AI提案・強く推奨 | 新規User入力時にAnalyzer/Reflectionをcancel/deferし、Main TTFTを守る |
| REQ-V01-ORCH-18 | Analyzer入力では秘密情報を検出・マスクし、Memory Candidateへ昇格不能にする | AI提案・重要 | password/API key/token等が長期Memoryへ保存されない |
| REQ-V01-ORCH-19 | Orchestrator比較を固定scenario + replayable DB snapshotで実施する | AI提案・必須級 | A/B/C profileを同一初期状態・同一turn列で比較可能 |
| REQ-V01-ORCH-20 | Remote inference backendを任意で利用できるが、AI Core/Identity/Memory/Relationshipのcanonical stateはローカル側を権威とする | ユーザー提案を受けたAI提案・有力 | Colab等のruntime消失で人格/Memoryを失わない |
| REQ-V01-ORCH-21 | Remote runtimeはephemeral workerとして扱い、切断/OOM/利用終了時にlocal fallbackまたは明示的degraded modeへ移行可能 | AI提案・重要 | Remote backend断でDB破損や会話履歴消失を起こさない |
| REQ-V01-ORCH-22 | Remote backendへ送るContext Capsuleを最小化し、secret/soft-deleted/private suppression対象を送信しない | AI提案・重要 | Remote推論経路でもforget/privacy境界を破らない |
| REQ-V01-ORCH-23 | Inference provider/runtime sessionのhardware・backend version・model・availabilityをTraceへ記録し、benchmarkを環境別に比較可能にする | AI提案・重要 | Colab GPU差等を混同せず再現可能な計測を残す |
| REQ-V01-ORCH-24 | Voice時はSTT→LLM→TTSを全完了待ちで直列化せず、partial/final transcript・LLM token stream・TTS audio streamを段階的に重ねる | AI提案・強く推奨 | 完全文生成後にTTS開始する構成を避け、体感応答開始を早める |
| REQ-V01-ORCH-25 | LLM出力は文全体ではなく安全なsentence/phrase boundaryでTTSへ逐次供給し、最初の短い発話fragmentを優先合成する | AI提案・強く推奨 | first audio開始を短縮し、Open-LLM-VTuber等の低遅延手法を取り込める |
| REQ-V01-ORCH-26 | TTSは複数segmentを必要に応じて並列合成し、再生順序だけ保証する | AI提案・有力 | 後続segment合成を前segment再生中に隠蔽する |
| REQ-V01-ORCH-27 | Voice turn boundaryは固定silence timerだけに依存せず、VAD + semantic/acoustic turn detectionまたはSTT endpointingを比較する | AI提案・強く推奨 | 短い沈黙で割り込む/長く待ちすぎる問題を減らす |
| REQ-V01-ORCH-28 | preemptive generationをoptional profileとして持ち、user turn確定前のinterim inputから生成開始できるが、final transcript差分時は結果をcancel/restart可能にする | AI提案・有力 | 体感latencyを下げつつ誤った早読みを状態へ残さない |
| REQ-V01-ORCH-29 | barge-in/interruptionを第一級イベントとして扱い、ユーザー発話開始時にTTS再生・未送信audio・必要ならLLM生成を即cancel/deferできる | AI提案・重要 | AIが喋り終わるまで待たせず自然な会話テンポを作る |
| REQ-V01-ORCH-30 | Main/ASR/TTSはwarm stateを優先し、model preload・connection reuse・prompt/KV cacheをruntime別にbenchmarkする | AI提案・強く推奨 | cold startを通常turn latencyへ混ぜない |
| REQ-V01-ORCH-31 | Voice latencyを end-of-turn decision / STT partial・final / LLM TTFT / first speakable fragment / TTS TTFA / user-speech-end→first-audio へ分解して計測する | AI提案・必須級 | tok/sだけでなく体感遅延の真因を特定できる |
| REQ-V01-ORCH-32 | ユーザー発話中からASR partialを使いRecall/Contextを**投機的にprefetch**するが、partial transcriptだけでMemory/Self/User/Relationshipをmutationしない | AI提案・強く推奨 | 発話終了時には候補contextが準備済みで、誤認partialはcanonical stateへ残らない |
| REQ-V01-ORCH-33 | Main promptはcache-friendly topologyを持ち、stable prefixを維持しつつcurrent state/retrieval/current user turnをsuffix側へ配置してprefix/KV cacheを再利用しやすくする | AI提案・重要 | 同一sessionの次turnで共通prefixを再prefillし続けない構成をbenchmark可能 |
| REQ-V01-ORCH-34 | Remote/Local Mainはturn間にwarm-prefix prefillを任意実行できる。prefill-only結果はephemeral cacheでありcanonical stateではない | AI提案・有力 | 次turn TTFTを短縮でき、runtime消失時も人格/Memoryは失わない |
| REQ-V01-ORCH-35 | canonical assistant `MESSAGE.content`はユーザーへ実際に**deliveryされた範囲**を表し、barge-in等で未再生/未表示の生成tailを共有会話・Memory/Relationship evidenceとして扱わない | AI提案・必須級 | 未発話の約束/意見が「言ったこと」にならない |
| REQ-V01-ORCH-36 | Voice出力はbounded lookaheadを持ち、TTS/audio queueを無制限に先行生成しない | AI提案・重要 | barge-in時の無駄な生成・停止遅延を抑え、数十秒先の音声をbufferしない |
| REQ-V01-ORCH-37 | Audio capture/AEC/VAD/turn detection/playbackをDB・Analyzer・重い推論からresource-isolateし、foreground voice処理にCPU/GPU/queue優先権を持たせる | AI提案・必須級 | Analyzer等が動作中でもaudio dropout/turn latencyが顕著に悪化しない |
| REQ-V01-ORCH-38 | Speaker再生とMic同時利用ではAECを前提候補とし、自分のTTS音声による誤VAD/誤barge-inを抑える | AI提案・重要 | speakers利用時もAI音声をユーザー発話と誤判定しにくい |
| REQ-V01-ORCH-39 | Voice latencyはframework eventだけでなく、可能なら同一monotonic clock上の`last user audio sample → first bot playout sample`でも測る | AI提案・必須級 | 実際に人が感じるgapを測定し、device/playout遅延を見落とさない |
| REQ-V01-ORCH-40 | VoiceはSafe / Balanced / Aggressiveのlatency profileを持ち、既定候補は`final STT受領後にMainをpreemptive開始し、semantic turn確定でTTS解放`するBalancedとする | AI提案・有力 | 低遅延と誤応答/無駄computeを比較可能 |
| REQ-V01-ORCH-41 | Main contextは利用可能最大contextを毎turn埋めず、token budgetを制限し、context長別TTFT benchmarkを行う | AI提案・必須級 | 2k/4k/8k/16k等でquality/TTFTを比較し不要なprefillを削減 |
| REQ-V01-ORCH-42 | Remote Main利用時はpersistent connection/sessionを優先し、毎turnのmodel load/TLS/tunnel初期化等のcold overheadを通常会話pathへ入れない | AI提案・重要 | Colab等がwarmな間はconnection reuseし、cold startは別metricとして扱う |
| REQ-V01-ORCH-43 | Orchestrator境界はversionedな`EventEnvelope`を共通契約とし、event ID / turn ID / source / sequence / causation / timestampを持つ | AI提案・重要 | 同一turnの順序・原因・再現性を追跡できる |
| REQ-V01-ORCH-44 | `Command`（処理要求）/ `Event`（発生済み事実）/ `Snapshot`（不変の参照状態）を型として分離する | AI提案・重要 | Eventを命令として再実行する曖昧さを避ける |
| REQ-V01-ORCH-45 | ASR partial / speculative recall / preemptive generationは`provisional`として扱い、`committed`状態と型上区別する | AI提案・必須級 | provisional情報がMemory/Relationship/canonical conversationへ混入しない |
| REQ-V01-ORCH-46 | Turn内eventはlocal Orchestratorが単調増加`sequence`とmonotonic観測時刻を付与し、remote clockを順序判定の権威にしない | AI提案・重要 | Colab/remote時計差やnetwork reorderでもtrace順序を再構成できる |
| REQ-V01-ORCH-47 | cancelはidempotentな第一級Command/Eventとし、generation→segment→TTS→playbackへ明示的に伝播できる | AI提案・必須級 | barge-inやpartial修正時に古い出力が後から再生されない |
| REQ-V01-ORCH-48 | stream queueはboundedとし、backpressure/drop policyをevent種別ごとに定義する | AI提案・重要 | token/partial/audio backlogが無限成長せずforeground latencyを守る |
| REQ-V01-ORCH-49 | Voiceでは`AssistantDeliveryCheckpoint`を通して実際にdelivery済みのtext spanを追跡し、canonical assistant messageをそこから確定する | AI提案・必須級 | interruption途中でも「実際に言った範囲」を共有履歴の権威にする |
| REQ-V01-ORCH-50 | Eventは`canonical audit / metric trace / ephemeral stream`の保存級を持ち、高頻度token/audio chunkを既定で永続化しない | AI提案・重要 | 観測可能性を保ちつつDB肥大・音声プライバシーリスクを抑える |
| REQ-V01-ORCH-51 | `ContextCapsule`は生成開始時点のimmutable Snapshotとし、`state_revision` / `transcript_revision` / `retrieval_run_id`へ固定する | AI提案・必須級 | 後から変わったMemory/Stateが同一generationの根拠として混ざらない |
| REQ-V01-ORCH-52 | Turn Analyzerはcanonical user inputと実際にdeliveryされたassistant範囲を解析対象とし、未delivery generation tailをSelf/Relationship/Memory根拠にしない | AI提案・必須級 | delivery truthをbackground learningにも一貫適用 |
| REQ-V01-ORCH-53 | Text v0.1もVoiceと同じTurn/Event契約のsubsetを用い、Voice追加時にOrchestratorを作り直さない | AI提案・強く推奨 | Text→Voice拡張の構造的互換性を保つ |
| REQ-V01-ORCH-54 | Remote model streamはlocal Gatewayで正規化し、provider固有token/event形式をCoreへ露出しない | AI提案・重要 | Local/Colab/Cloud差替時も上位Orchestrator型を維持する |
| REQ-V01-ORCH-55 | 各Event/Commandのproducer・required consumer・state ownerを一意に定義し、複数componentが同じcanonical stateを直接書換えない | AI提案・必須級 | producer/consumer表とownership表から責務が一意に追える |
| REQ-V01-ORCH-56 | Domain Stateの確定mutationはValidator/Projector経由に限定し、ASR/LLM/TTS/Playback等のcomponent eventから直接書込まない | AI提案・必須級 | component失敗やlate eventでMemory/Self/User/Relationshipが直接壊れない |
| REQ-V01-ORCH-57 | `committed`なUser Turn/Deliveryは同一turn内で巻き戻さず、訂正・追加発話は新Event/新Turnとして表現する | AI提案・重要 | audit historyを破壊せず再現できる |
| REQ-V01-ORCH-58 | Foreground failureを`critical / degradable / background`へ分類し、Recall/Turn detector等のdegradable failureでは可能なら会話を継続する | AI提案・重要 | 非本質subsystem障害で会話全体を停止しない |
| REQ-V01-ORCH-59 | Main providerがdelivery前に失敗した場合のみLocal/別provider fallbackを同一turnで試行可能とし、delivery後の無言model切替で文章を継ぎ足さない | AI提案・強く推奨 | persona/voice driftと不整合な途中継続を避ける |
| REQ-V01-ORCH-60 | cancelled/superseded scopeに属するlate resultは全componentでdiscardし、retryは新attempt IDで追跡する | AI提案・必須級 | remote遅延結果や二重retryが再生/DB更新されない |
| REQ-V01-ORCH-61 | ASR/Recall/Turn detector/Context/Main/Segmenter/TTS/Playback/Analyzer等の各attemptを共通telemetryで追跡し、status/failure code/retryability/deadlineを記録する | AI提案・重要 | model call以外の遅延・失敗もend-to-endで原因特定できる |
| REQ-V01-ORCH-62 | Text streamingでもUIへ実際にrenderされた範囲をdelivery truthとして扱い、Voiceと同じcanonical-delivery原則を適用する | AI提案・重要 | stream途中失敗時に未表示tailを「言ったこと」にしない |
| REQ-V01-ORCH-63 | `BargeInDetected`のcandidateだけでは即cancelせず、InterruptionDecisionでbackchannel/false positive/confirmed interruptを分離する | AI提案・重要 | 「うん」「へー」等で不要にAI発話を切らない |
| REQ-V01-ORCH-64 | Turn Analysis commit時に`base_state_revision`が古い場合は最新Stateへ再検証し、stale proposalをblind overwriteしない | AI提案・必須級 | forget/correction等と競合した古いAnalyzerが状態を復活・上書きしない |
| REQ-V01-ORCH-65 | Orchestratorの主要正常系・競合・障害系をversionedなGolden Event Sequenceとして保持し、実装変更時の回帰試験へ使用する | AI提案・必須級 | 同じ入力/初期snapshotに対し、必須Event順序・終端phase・canonical state不変条件を検証できる |
| REQ-V01-ORCH-66 | Golden Sequenceは「起きるべきEvent」だけでなく「絶対に起きてはいけないcanonical mutation / delivery / resurrection」も明示する | AI提案・必須級 | late/cancel/provisional resultがMemoryやMessageへ漏れないことをnegative assertionで検証できる |
| REQ-V01-ORCH-67 | Provider固有streamを正規化した後のCore Event列をGoldenの比較対象とし、Local/Colab/Cloud差替でGolden自体を作り直さない | AI提案・重要 | backend差替後も同じCore契約を再利用できる |
| REQ-V01-ORCH-68 | Race系GoldenではEvent到着順を意図的に並べ替え、cancel / revision / attempt ID / state revisionにより結果が決定論的に収束することを確認する | AI提案・必須級 | late remote result・stale Analyzer・endpoint revoke等で状態が復活/二重commitしない |
| REQ-V01-ORCH-69 | Text v0.1のP0 component boundaryをOrchestrator / Retrieval / Context / Gateway / Delivery / Analyzer + deterministic Domain Update Layerとして固定する | 非コード実装仕様・明示採用 | 各責務・input/output・state owner・failure degradeが一意に追える |
| REQ-V01-ORCH-70 | Canonical stateはsingle-writer原則を取り、Turn lifecycleはOrchestrator、delivery truthはDelivery、semantic Domain mutationはDomain Update Layerが所有する | 非コード実装仕様・必須級 | 複数componentが同じcanonical stateを直接更新しない |
| REQ-V01-ORCH-71 | Retrieval failureはvector/lexical片系またはempty degraded snapshotへ縮退し、Recall障害だけで通常Chatを停止しない | 非コード実装仕様・重要 | soft-deletedを返さず、両retrieval失敗でもrecent contextで会話継続可能 |
| REQ-V01-ORCH-72 | Context Builderは生成開始時点のimmutable Context Capsuleを作り、hard rules/current input/privacy境界をtoken trimより優先して保持する | 非コード実装仕様・必須級 | budget超過時もhard constraints/current inputが欠落しない |
| REQ-V01-ORCH-73 | Delivery componentをcanonical assistant contentの根拠とし、Textでも実際にUIへrenderされた範囲だけを共有会話へ確定する | 非コード実装仕様・必須級 | stream途中失敗/cancel時に未render tailをMessage/Memory evidenceへ含めない |
| REQ-V01-ORCH-74 | Domain Update LayerをValidator + Projectorの共通境界とし、Analyzer proposalや明示commandからのsemantic updateをatomic transactionで確定する | 非コード実装仕様・必須級 | invalid/stale/secret/forget-boundary proposalをrejectし、partial mutationを残さない |
| REQ-V01-ORCH-75 | P0はLOCAL_ONLYとHYBRID_COLAB_MAINで同一component/event contractを維持し、remote runtime差をGateway以下に封じる | 非コード実装仕様・重要 | Main provider差替でCore contract/Domain schemaを変更しない |
| REQ-V01-ORCH-76 | Text v0.1のCodex実装単位をWP-TXT-01〜10へ分割し、foreground vertical slice→persistent state→Inspector/Goldenの順で着手可能にする | 非コード実装仕様・重要 | 依存順と完了条件が仕様文書から追える |

### Turn Analyzer v1
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-ANL-01 | `TurnAnalysisV1`はversioned strict schemaとし、top-level/child fieldを固定する | AI提案・必須級 | schema外field、型違反、上限超過をcommitしない |
| REQ-V01-ANL-02 | Analyzerは「何も更新すべきでない」を正常結果として返せる | AI提案・必須級 | 全配列empty + optional candidate nullがvalid |
| REQ-V01-ANL-03 | Analyzer入力はcanonical user turn / delivery済assistant範囲 / bounded recent context / bounded relevant stateだけに制限する | AI提案・重要 | 未delivery tail、soft-deleted memory、無制限履歴を入力しない |
| REQ-V01-ANL-04 | Memory Candidateは1 turn最大6件とし、Episode/Claim、subject、temporal scope、direct/inferred、importance signal、existing-memory relation、evidenceを出す | AI提案・重要 | 大量Memory生成をschema段階で抑制し、全候補にevidenceを要求 |
| REQ-V01-ANL-05 | Direct user factとBehavioral User Observationを分離する | AI提案・必須級 | 直接発言はUser Claim候補、行動からの推測はUser Observation/Hypothesis signalとして扱う |
| REQ-V01-ANL-06 | Self Observationはspontaneityとuser influenceをordinalで出し、AIの自発反応と迎合可能性を区別する | 既存独立人格要求の具体化 | user influenceが高い1件だけでSelf Modelへ昇格しない |
| REQ-V01-ANL-07 | Appraisal/Emotionは毎turn必須にせず、意味のある変化がある場合のみ最大1件ずつ提案する | AI提案・重要 | 雑談ごとに感情イベントを乱造しない |
| REQ-V01-ANL-08 | Relationship Signalは疎に生成し、1 turn最大3件。Trust等は可能ならcontext scopeを伴う | AI提案・必須級 | 利用頻度/単発褒め言葉だけで親密さ・信頼を大幅更新しない |
| REQ-V01-ANL-09 | UUID、timestamp、numeric confidence/weight/delta、lifecycle status、soft-delete/archive、Self昇格、Relationship数値はcode-owned | AI提案・必須級 | LLMが直接canonical state値や削除権限を決めない |
| REQ-V01-ANL-10 | Analyzerが出すordinal signalはValidator/Projectorがcode-owned mappingと1-turn capを適用してDomain updateへ変換する | AI提案・必須級 | 同一schemaでもmapping versionを追跡しrollback可能 |
| REQ-V01-ANL-11 | 全semantic proposalは許可されたMessage/Memory referenceへevidenceを持ち、参照不能な主張をDomainへcommitしない | AI提案・必須級 | hallucinated IDや根拠なしproposalをreject |
| REQ-V01-ANL-12 | Analyzerはfield-level semantic golden casesで検証し、文面一致ではなく分類/evidence/no-mutation invariantで評価する | AI提案・必須級 | correction/change-over-time/temporary state/self-user separation等のfixtureを回帰可能 |

### Retrieval v1
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-RETR-01 | `RetrievalRequestV1 / RetrievalSnapshotV1`をversioned contractとして固定し、Retrievalをcanonical Domainのread-only componentとする | 非コード実装仕様・必須級 | Retrieval単独でMemory/Self/User/Relationshipをmutationしない |
| REQ-V01-RETR-02 | P0はextracted Memory + canonical raw messageを対象に、lexical / semanticを並列利用可能にする | 非コード実装仕様・重要 | raw assistant sourceはdelivery済canonical contentだけを対象 |
| REQ-V01-RETR-03 | soft-deleted / forbidden / source不整合を候補化せず、ARCHIVEDは除外せず低優先で扱える | 非コード実装仕様・必須級 | soft-deleted result 0、明示参照時のArchive再浮上を妨げない |
| REQ-V01-RETR-04 | fusion方式・weight・thresholdは`retrieval_profile_id`でversion管理し、exact数値は初期実働前に固定しない | 育成型開発の明示方針 | profile別A/B可能、score式変更でDomain schemaを変えない |
| REQ-V01-RETR-05 | Retrieval中にDomain revisionが変化した場合、Context投入前にsource visibilityを再検証する | 非コード実装仕様・必須級 | Retrieval後のUser ForgetがPromptへ漏れない |
| REQ-V01-RETR-06 | Promptへの最終採否はContext Builderが所有し、Retrievalはranked candidate snapshotを返す | 非コード実装仕様・重要 | Recallされたこと自体を発話/Prompt投入義務にしない |
| REQ-V01-RETR-07 | lexical/semantic failureは片系またはempty degraded snapshotへ縮退し、Recall障害だけで通常Chatを停止しない | 既存ORCH要件の具体化 | 両系統停止でもrecent contextでMainへ進行可能 |

### Definition of Ready / Explicit Command P0
| ID | 詳細 | 状態 | 受入条件 |
|---|---|---|---|
| REQ-V01-CMD-01 | remember/forget検出をcanonical Turnへ紐づくdurable command markerとして保持 | DoR監査で追加・必須級 | Analyzer遅延/失敗でもcommand intentを失わない |
| REQ-V01-CMD-02 | Forget targetはUI選択/明示参照/一意なcurrent contextまたはretrievalでのみresolvedとし、曖昧時は削除せず確認する | DoR監査で追加・必須級 | ambiguous forgetでguess-delete 0 |
| REQ-V01-CMD-03 | resolved User ForgetはforegroundでDomain Update Layerからatomic soft-deleteし、state revisionを進める | 既存明示決定の具体化 | Analyzer待ちなし、以後Recall/Context/Evidenceから不可視 |
| REQ-V01-CMD-04 | Explicit Rememberはforeground marker化し、semantic保存はAnalyzer/Validatorを利用可。secret policyを上書きしない | 既存MEM-13具体化 | Analyzer retry可能、credential persistence 0 |
| REQ-V01-DOR-01 | Text v0.1はr16監査後、P0 blocker 0としてCodex実装着手可能 | 明示的な設計到達点 | Requirement↔Contract↔Type↔ER↔Golden↔Acceptanceに未解決P0矛盾なし |
| REQ-V01-DOR-02 | r16以降、P1 Golden/exact tuning/Voice詳細を実装開始の前提にせず、初期実働後に育てる | 育成型開発方針 | 事前仕様化が無期限に続かない |

現時点の推奨call profile（未確定、実機benchmark前）:
- foreground: Main Dialogue LLM ×1。
- retrieval: embedding ×1（generative LLM callに数えない）、lexical searchと並列。
- reranker: ambiguous時のみoptional。
- post-response: Turn Analyzer SLM ×1 async。
- reflection/consolidation: idle/batch。
- high-spec profileのみ、pre-turn SLM ×1をRecallと並列で試験し、品質改善がTTFT増を上回る場合だけ採用。

---
