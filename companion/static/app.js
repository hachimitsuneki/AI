const messageList = document.querySelector("#message-list");
const welcome = document.querySelector("#welcome");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const stopButton = document.querySelector("#stop-button");
const turnStatus = document.querySelector("#turn-status");
const providerDot = document.querySelector("#provider-dot");
const modelLabel = document.querySelector("#model-label");
const connectionState = document.querySelector("#connection-state");

let activeTurnId = null;
let activeAssistantBubble = null;
let renderedCodePoints = 0;
let submittedText = "";

function scrollToLatest() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

function setStatus(text = "", isError = false) {
  turnStatus.textContent = text;
  turnStatus.classList.toggle("error", isError);
}

function createMessage(speaker, content, timestamp = new Date().toISOString(), pending = false) {
  welcome.hidden = true;
  const row = document.createElement("article");
  row.className = "message-row " + speaker;
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = speaker === "user" ? "あなた" : document.querySelector("#identity-name").textContent;
  const bubble = document.createElement("div");
  bubble.className = "bubble" + (pending ? " pending" : "");
  bubble.textContent = content;
  const time = document.createElement("time");
  time.className = "message-time";
  time.dateTime = timestamp;
  time.textContent = new Intl.DateTimeFormat("ja-JP", { hour: "2-digit", minute: "2-digit" }).format(new Date(timestamp));
  row.append(label, bubble, time);
  messageList.append(row);
  scrollToLatest();
  return { row, bubble, time };
}

function setBusy(busy) {
  input.disabled = busy;
  sendButton.disabled = busy || !input.value.trim();
  stopButton.hidden = !busy;
  if (!busy) input.focus();
}

async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || data.error || ("HTTP " + response.status));
  }
  return data;
}

async function paintAndAcknowledge(event) {
  if (!activeAssistantBubble) {
    const created = createMessage("assistant", "", new Date().toISOString(), true);
    activeAssistantBubble = created.bubble;
  }
  const startOffset = renderedCodePoints;
  activeAssistantBubble.textContent += event.text;
  activeAssistantBubble.classList.add("pending");
  renderedCodePoints += Array.from(event.text).length;
  scrollToLatest();
  // Wait through a paint boundary before recording this span as delivered.
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const result = await postJson("/api/turns/" + activeTurnId + "/delivery", {
    offset: startOffset,
    text: event.text,
  });
  renderedCodePoints = Math.max(renderedCodePoints, result.offset);
}

async function finishFromClient() {
  try {
    await postJson("/api/turns/" + activeTurnId + "/finalize");
  } catch (error) {
    setStatus("配信確定に失敗しました: " + error.message, true);
  }
}

async function handleEvent(event) {
  switch (event.type) {
    case "turn_started":
      activeTurnId = event.turn_id;
      setStatus("応答を準備しています…");
      createMessage("user", submittedText, new Date().toISOString());
      break;
    case "retrieval_started":
      setStatus("会話の文脈を確認しています…");
      break;
    case "retrieval_ready":
      if (event.status === "degraded") {
        setStatus("一部の関連情報を使わずに続けます。");
      } else if (event.status === "unavailable") {
        setStatus("過去の関連情報は使わずに続けます。");
      } else {
        setStatus("応答を作成しています…");
      }
      break;
    case "context_ready":
      setStatus("応答を作成しています…");
      break;
    case "first_token":
      break;
    case "delta":
      await paintAndAcknowledge(event);
      break;
    case "generation_completed":
      await finishFromClient();
      setStatus("応答を確定しています…");
      break;
    case "generation_failed":
      if (event.delivered_char_count === 0) {
        setStatus("応答を開始できませんでした: " + event.message, true);
      } else {
        setStatus("途中まで表示した応答を確定しています。", true);
      }
      await finishFromClient();
      break;
    case "turn_failed":
      if (activeAssistantBubble) activeAssistantBubble.classList.remove("pending");
      setStatus("応答できませんでした: " + event.message, true);
      break;
    case "turn_finalized":
      if (activeAssistantBubble) activeAssistantBubble.classList.remove("pending");
      if (event.status === "completed") {
        setStatus("");
      } else if (event.status === "completed_partial") {
        setStatus("途中までの応答を会話履歴に保存しました。", true);
      } else if (event.status === "cancelled") {
        setStatus("応答を停止しました。表示済みの部分だけを保存しました。");
      } else if (event.status === "failed_before_delivery") {
        setStatus("応答を表示できませんでした。もう一度お試しください。", true);
      }
      activeTurnId = null;
      activeAssistantBubble = null;
      renderedCodePoints = 0;
      setBusy(false);
      break;
    default:
      console.debug("Unknown runtime event", event.type);
  }
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || activeTurnId) return;
  setStatus("");
  submittedText = text;
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  setBusy(true);
  renderedCodePoints = 0;

  let stream = null;
  try {
    const response = await fetch("/api/turns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok || !response.body) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || error.error || ("HTTP " + response.status));
    }
    stream = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    while (true) {
      const result = await stream.read();
      if (result.done) break;
      pending += decoder.decode(result.value, { stream: true });
      let newline;
      while ((newline = pending.indexOf("\n")) >= 0) {
        const line = pending.slice(0, newline).trim();
        pending = pending.slice(newline + 1);
        if (line) await handleEvent(JSON.parse(line));
      }
    }
    pending += decoder.decode();
    if (pending.trim()) await handleEvent(JSON.parse(pending));
    if (activeTurnId) {
      setStatus("接続が切れました。履歴を読み直しています。", true);
      await loadHistory();
      activeTurnId = null;
      activeAssistantBubble = null;
      setBusy(false);
    }
  } catch (error) {
    if (activeTurnId) {
      postJson("/api/turns/" + activeTurnId + "/cancel", { reason: "client_stream_error" }).catch(() => {});
      if (stream) await stream.cancel().catch(() => {});
      activeTurnId = null;
    }
    setStatus("送信または接続に失敗しました: " + error.message, true);
    setBusy(false);
  }
}

async function stopGeneration() {
  if (!activeTurnId) return;
  stopButton.disabled = true;
  setStatus("停止しています…");
  try {
    await postJson("/api/turns/" + activeTurnId + "/cancel", { reason: "user_cancelled" });
  } catch (error) {
    setStatus("停止要求に失敗しました: " + error.message, true);
  } finally {
    stopButton.disabled = false;
  }
}

async function loadHistory() {
  const response = await fetch("/api/bootstrap", { cache: "no-store" });
  if (!response.ok) throw new Error("HTTP " + response.status);
  const data = await response.json();
  document.querySelector("#identity-name").textContent = data.identity.name;
  document.title = data.identity.name + " · Text v0.1";
  connectionState.textContent = "ローカル会話";
  modelLabel.textContent = data.runtime_profile.main_model + " · 仮プロファイル";
  const ready = data.provider.main_model_available;
  providerDot.classList.toggle("ready", ready);
  providerDot.classList.toggle("offline", !ready);
  if (!ready) {
    setStatus("ローカルモデルが見つかりません。Ollama とモデル設定を確認してください。", true);
  }
  messageList.replaceChildren();
  for (const message of data.history) {
    createMessage(message.speaker, message.content, message.created_at);
  }
  welcome.hidden = data.history.length > 0;
}

sendButton.addEventListener("click", sendMessage);
stopButton.addEventListener("click", stopGeneration);
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 190) + "px";
  sendButton.disabled = Boolean(activeTurnId) || !input.value.trim();
});
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

loadHistory().catch((error) => {
  setStatus("ローカルアプリに接続できません: " + error.message, true);
  modelLabel.textContent = "接続できません";
  providerDot.classList.add("offline");
});
