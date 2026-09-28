const conversation = document.querySelector("#conversation");
const messageList = document.querySelector("#message-list");
const welcome = document.querySelector("#welcome");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const stopButton = document.querySelector("#stop-button");
const turnStatus = document.querySelector("#turn-status");
const connectionState = document.querySelector("#connection-state");
const loadOlderButton = document.querySelector("#load-older");
const latestButton = document.querySelector("#scroll-latest");
const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#history-search");
const searchResults = document.querySelector("#search-results");
const replyPreview = document.querySelector("#reply-preview");
const replyPreviewText = document.querySelector("#reply-preview-text");

const messages = [];
const messageNodes = new Map();
const canonicalMessages = new Map();
let conversationId = null;
let historyCursor = null;
let historyHasMore = false;
let latestReplyTarget = null;
let currentTurn = null;
let historyAtLatest = true;
let sendPreparing = false;

function setStatus(text = "", isError = false) {
  turnStatus.textContent = text;
  turnStatus.classList.toggle("error", isError);
}

function isNearLatest() {
  return conversation.scrollHeight - conversation.scrollTop - conversation.clientHeight < 100;
}

function updateLatestButton() {
  latestButton.hidden = isNearLatest();
}

function scrollToLatest(behavior = "smooth") {
  conversation.scrollTo({ top: conversation.scrollHeight, behavior });
  updateLatestButton();
}

function localDay(timestamp) {
  const date = new Date(timestamp);
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function formatDay(timestamp) {
  return new Intl.DateTimeFormat("ja-JP", { year: "numeric", month: "long", day: "numeric", weekday: "short" })
    .format(new Date(timestamp));
}

function safeHref(raw) {
  const value = raw.trim();
  if (/^https?:\/\//i.test(value)) return value;
  if (/^\/(?!\/)/.test(value) || /^\.{1,2}\//.test(value) || /^#[A-Za-z0-9_-]/.test(value)) return value;
  return null;
}

function appendInline(parent, text) {
  const tokenPattern = /`([^`\n]+)`|\[([^\]\n]+)\]\(([^\s)]+)(?:\s+"([^"]*)")?\)|\*\*([^*\n]+)\*\*|~~([^~\n]+)~~|(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)/g;
  let offset = 0;
  let match;
  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > offset) parent.append(document.createTextNode(text.slice(offset, match.index)));
    if (match[1] !== undefined) {
      const code = document.createElement("code");
      code.textContent = match[1];
      parent.append(code);
    } else if (match[2] !== undefined) {
      const href = safeHref(match[3]);
      if (!href) {
        parent.append(document.createTextNode(match[0]));
      } else {
        const link = document.createElement("a");
        link.href = href;
        link.rel = "noopener noreferrer";
        if (/^https?:\/\//i.test(href)) link.target = "_blank";
        appendInline(link, match[2]);
        parent.append(link);
      }
    } else if (match[5] !== undefined) {
      const strong = document.createElement("strong");
      strong.textContent = match[5];
      parent.append(strong);
    } else if (match[6] !== undefined) {
      const deleted = document.createElement("del");
      deleted.textContent = match[6];
      parent.append(deleted);
    } else if (match[7] !== undefined || match[8] !== undefined) {
      const emphasis = document.createElement("em");
      emphasis.textContent = match[7] ?? match[8];
      parent.append(emphasis);
    }
    offset = tokenPattern.lastIndex;
  }
  if (offset < text.length) parent.append(document.createTextNode(text.slice(offset)));
}

// Allowlisted Markdown subset. All source text is emitted through text nodes;
// raw HTML is displayed literally and never parsed by the browser.
function renderSafeMarkdown(target, source) {
  target.replaceChildren();
  const lines = String(source).replace(/\r\n?/g, "\n").split("\n");
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }
    if (/^\s*```/.test(line)) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !/^\s*```/.test(lines[index])) codeLines.push(lines[index++]);
      if (index < lines.length) index += 1;
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = codeLines.join("\n");
      pre.append(code);
      target.append(pre);
      continue;
    }
    const heading = line.match(/^\s{0,3}(#{1,3})\s+(.+)$/);
    if (heading) {
      const node = document.createElement(`h${heading[1].length + 1}`);
      appendInline(node, heading[2]);
      target.append(node);
      index += 1;
      continue;
    }
    if (/^\s*>/.test(line)) {
      const quoteLines = [];
      while (index < lines.length && /^\s*>/.test(lines[index])) quoteLines.push(lines[index++].replace(/^\s*>\s?/, ""));
      const blockquote = document.createElement("blockquote");
      renderSafeMarkdown(blockquote, quoteLines.join("\n"));
      target.append(blockquote);
      continue;
    }
    if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const list = document.createElement(ordered ? "ol" : "ul");
      const marker = ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*+]\s+/;
      while (index < lines.length && marker.test(lines[index])) {
        const item = document.createElement("li");
        appendInline(item, lines[index++].replace(marker, ""));
        list.append(item);
      }
      target.append(list);
      continue;
    }
    const paragraphLines = [];
    while (index < lines.length && lines[index].trim()
      && !/^\s*```/.test(lines[index]) && !/^\s*>/.test(lines[index])
      && !/^\s{0,3}#{1,3}\s+/.test(lines[index])
      && !/^\s*[-*+]\s+/.test(lines[index]) && !/^\s*\d+[.)]\s+/.test(lines[index])) {
      paragraphLines.push(lines[index++]);
    }
    const paragraph = document.createElement("p");
    paragraphLines.forEach((part, lineIndex) => {
      if (lineIndex) paragraph.append(document.createElement("br"));
      appendInline(paragraph, part);
    });
    target.append(paragraph);
  }
}

function replyDataFor(message) {
  if (!message.reply_to_message_id) return null;
  const resolved = canonicalMessages.get(message.reply_to_message_id);
  return {
    id: message.reply_to_message_id,
    speaker: resolved?.speaker ?? message.reply_to_speaker ?? "message",
    content: resolved?.content ?? message.reply_to_content ?? "引用元のメッセージ",
  };
}

function createMessageRow(message) {
  const row = document.createElement("article");
  row.className = `message-row ${message.speaker}`;
  row.dataset.messageId = message.id;
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = message.speaker === "user" ? "あなた" : document.querySelector("#identity-name").textContent;
  const quote = replyDataFor(message);
  if (quote) {
    const quoted = document.createElement("button");
    quoted.type = "button";
    quoted.className = "quoted-message";
    quoted.dataset.targetMessageId = quote.id;
    quoted.setAttribute("aria-label", "引用元へ移動");
    const quotedLabel = document.createElement("span");
    quotedLabel.textContent = `${quote.speaker === "user" ? "あなた" : document.querySelector("#identity-name").textContent}への返信`;
    const quotedText = document.createElement("span");
    quotedText.textContent = quote.content.slice(0, 160);
    quoted.append(quotedLabel, quotedText);
    row.append(quoted);
  }
  const bubble = document.createElement("div");
  bubble.className = "bubble" + (message.status === "delivering" ? " pending" : "");
  renderSafeMarkdown(bubble, message.content);
  const time = document.createElement("time");
  time.className = "message-time";
  time.dateTime = message.created_at;
  time.textContent = new Intl.DateTimeFormat("ja-JP", { hour: "2-digit", minute: "2-digit" })
    .format(new Date(message.created_at));
  const actions = document.createElement("div");
  actions.className = "message-actions";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.textContent = "コピー";
  copy.setAttribute("aria-label", "メッセージをコピー");
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setStatus("メッセージをコピーしました。");
    } catch {
      setStatus("クリップボードへコピーできませんでした。", true);
    }
  });
  const reply = document.createElement("button");
  reply.type = "button";
  reply.textContent = "返信";
  reply.setAttribute("aria-label", "このメッセージに返信");
  reply.addEventListener("click", () => setReplyTarget(message));
  actions.append(copy, reply);
  row.append(label, bubble, time, actions);
  messageNodes.set(message.id, { row, bubble, message });
  return row;
}

function renderAllMessages() {
  messageNodes.clear();
  canonicalMessages.clear();
  messages.forEach((message) => {
    if (!String(message.id).startsWith("pending:")) canonicalMessages.set(message.id, message);
  });
  const fragment = document.createDocumentFragment();
  let previousDay = null;
  for (const message of messages) {
    const day = localDay(message.created_at);
    if (day !== previousDay) {
      const separator = document.createElement("div");
      separator.className = "date-separator";
      separator.textContent = formatDay(message.created_at);
      fragment.append(separator);
      previousDay = day;
    }
    fragment.append(createMessageRow(message));
  }
  messageList.replaceChildren(fragment);
  welcome.hidden = messages.length > 0;
}

function addMessage(message, forceLatest = false) {
  if (message.id && canonicalMessages.has(message.id)) return canonicalMessages.get(message.id);
  const shouldFollow = forceLatest || isNearLatest();
  const compare = (left, right) => left.created_at.localeCompare(right.created_at) || left.id.localeCompare(right.id);
  let index = messages.findIndex((existing) => compare(existing, message) > 0);
  if (index < 0) index = messages.length;
  const isAppend = index === messages.length;
  const oldHeight = conversation.scrollHeight;
  const oldTop = conversation.scrollTop;
  const day = isAppend && messages.length ? localDay(messages[messages.length - 1].created_at) : null;
  messages.splice(index, 0, message);
  if (message.id && !String(message.id).startsWith("pending:")) canonicalMessages.set(message.id, message);
  if (isAppend && (day === null || day !== localDay(message.created_at))) {
    const separator = document.createElement("div");
    separator.className = "date-separator";
    separator.textContent = formatDay(message.created_at);
    messageList.append(separator);
  }
  if (isAppend) messageList.append(createMessageRow(message));
  else {
    renderAllMessages();
    conversation.scrollTop = oldTop + (conversation.scrollHeight - oldHeight);
  }
  welcome.hidden = true;
  if (shouldFollow) scrollToLatest("auto");
  else updateLatestButton();
  return message;
}

function mergeOlderPage(page) {
  const oldHeight = conversation.scrollHeight;
  const oldTop = conversation.scrollTop;
  const seen = new Set(messages.map((message) => message.id));
  const older = page.filter((message) => !seen.has(message.id));
  if (!older.length) return;
  messages.unshift(...older);
  renderAllMessages();
  conversation.scrollTop = oldTop + (conversation.scrollHeight - oldHeight);
  updateLatestButton();
}

function setReplyTarget(message) {
  latestReplyTarget = message;
  replyPreviewText.textContent = `${message.speaker === "user" ? "あなた" : document.querySelector("#identity-name").textContent}: ${message.content.slice(0, 120)}`;
  replyPreview.hidden = false;
  input.focus();
}

function clearReplyTarget() {
  latestReplyTarget = null;
  replyPreview.hidden = true;
  replyPreviewText.textContent = "";
}

function setBusy() {
  // The composer stays enabled while a turn is generating so a new submit can interrupt it.
  input.disabled = false;
  sendButton.disabled = !input.value.trim();
  stopButton.hidden = !currentTurn || currentTurn.finished || !currentTurn.turnId;
  stopButton.disabled = false;
}

async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || data.error || (`HTTP ${response.status}`));
  return data;
}

async function paintAndAcknowledge(view, event) {
  if (view.superseded) return;
  if (!view.assistantMessage) {
    view.assistantMessage = {
      id: `pending:${view.turnId}`,
      speaker: "assistant",
      content: "",
      status: "delivering",
      created_at: new Date().toISOString(),
    };
    addMessage(view.assistantMessage, false);
    view.assistantRow = messageNodes.get(view.assistantMessage.id);
  }
  const shouldFollow = isNearLatest();
  const startOffset = view.renderedCodePoints;
  view.assistantMessage.content += event.text;
  view.renderedCodePoints += Array.from(event.text).length;
  renderSafeMarkdown(view.assistantRow.bubble, view.assistantMessage.content);
  view.assistantRow.bubble.classList.add("pending");
  if (shouldFollow) scrollToLatest("auto");
  else updateLatestButton();
  // Record only after a paint boundary. A following submit waits for this ACK.
  view.deliveryPromise = new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    .then(() => postJson(`/api/turns/${view.turnId}/delivery`, { offset: startOffset, text: event.text }))
    .then((result) => { view.renderedCodePoints = Math.max(view.renderedCodePoints, result.offset); });
  try {
    await view.deliveryPromise;
  } catch (error) {
    if (!view.superseded) throw error;
  }
}

async function finishFromClient(view) {
  try {
    await postJson(`/api/turns/${view.turnId}/finalize`);
  } catch (error) {
    if (!view.superseded) setStatus(`配信確定に失敗しました: ${error.message}`, true);
  }
}

function applyFinalizedMessage(view, event) {
  if (view.assistantMessage) {
    const pendingId = view.assistantMessage.id;
    const node = messageNodes.get(pendingId);
    view.assistantMessage.status = event.status === "completed" ? "delivered" : "delivery_partial";
    if (event.assistant_message_id) view.assistantMessage.id = event.assistant_message_id;
    if (node) {
      messageNodes.delete(pendingId);
      node.row.dataset.messageId = view.assistantMessage.id;
      node.bubble.classList.remove("pending");
      messageNodes.set(view.assistantMessage.id, node);
    }
    canonicalMessages.delete(pendingId);
    if (event.assistant_message_id) canonicalMessages.set(event.assistant_message_id, view.assistantMessage);
    if (!event.assistant_message_id) {
      const index = messages.indexOf(view.assistantMessage);
      if (index >= 0) messages.splice(index, 1);
      node?.row.remove();
      messageNodes.delete(pendingId);
    }
  }
  view.finished = true;
  if (currentTurn === view) {
    if (event.status === "completed") setStatus("");
    else if (event.status === "completed_partial") setStatus("途中までの応答を会話履歴に保存しました。", true);
    else if (event.status === "cancelled") setStatus("表示済みの部分だけを会話履歴に保存しました。");
    else if (event.status === "failed_before_delivery") setStatus("応答を表示できませんでした。もう一度お試しください。", true);
    setBusy();
  }
}

async function handleEvent(view, event) {
  if (event.type === "turn_started") {
    view.turnId = event.turn_id;
    view.userMessageId = event.user_message_id;
    view.renderedCodePoints = 0;
    addMessage({
      id: event.user_message_id,
      speaker: "user",
      content: view.text,
      status: "committed",
      created_at: event.created_at || new Date().toISOString(),
      reply_to_message_id: view.replyToMessageId,
      reply_to_speaker: view.replySpeaker,
      reply_to_content: view.replyContent,
    }, !view.superseded && currentTurn === view);
    try { if (localStorage.getItem(view.draftKey) === view.text) localStorage.removeItem(view.draftKey); } catch { /* storage may be disabled */ }
    if (latestReplyTarget?.id === view.replyToMessageId) clearReplyTarget();
    if (!view.superseded && currentTurn === view) {
      setStatus("応答を準備しています…");
      setBusy();
    }
    return;
  }
  if (event.type === "turn_finalized") {
    applyFinalizedMessage(view, event);
    return;
  }
  if (view.superseded) return;
  switch (event.type) {
    case "retrieval_started": setStatus("会話の文脈を確認しています…"); break;
    case "retrieval_ready":
      setStatus(event.status === "degraded" ? "一部の関連情報を使わずに続けます。"
        : event.status === "unavailable" ? "過去の関連情報は使わずに続けます。" : "応答を作成しています…");
      break;
    case "context_ready": setStatus("応答を作成しています…"); break;
    case "delta": await paintAndAcknowledge(view, event); break;
    case "generation_completed":
      await finishFromClient(view);
      setStatus("応答を確定しています…");
      break;
    case "generation_failed":
      setStatus(event.delivered_char_count === 0 ? `応答を開始できませんでした: ${event.message}`
        : "途中まで表示した応答を確定しています。", true);
      await finishFromClient(view);
      break;
    case "turn_failed": setStatus(`応答できませんでした: ${event.message}`, true); break;
    default: break;
  }
}

async function consumeTurnStream(view, response) {
  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || error.error || (`HTTP ${response.status}`));
  }
  const stream = response.body.getReader();
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
      if (line) await handleEvent(view, JSON.parse(line));
    }
  }
  pending += decoder.decode();
  if (pending.trim()) await handleEvent(view, JSON.parse(pending));
  if (!view.finished && !view.superseded) {
    setStatus("接続が切れました。履歴を読み直しています。", true);
    await loadLatestHistory(false);
  }
}

async function sendMessage() {
  if (sendPreparing) return;
  const text = input.value.trim();
  if (!text) return;
  sendPreparing = true;
  sendButton.disabled = true;
  if (!historyAtLatest) {
    try { await loadLatestHistory(true); }
    catch (error) { setStatus(`最新の履歴を読み込めませんでした: ${error.message}`, true); sendPreparing = false; return; }
  }
  sendPreparing = false;
  const previous = currentTurn;
  if (previous && !previous.finished) {
    previous.superseded = true;
    if (previous.assistantRow) previous.assistantRow.bubble.classList.remove("pending");
  }
  const reply = latestReplyTarget;
  const view = {
    text,
    replyToMessageId: reply?.id ?? null,
    replySpeaker: reply?.speaker ?? null,
    replyContent: reply?.content ?? null,
    superseded: false,
    finished: false,
    turnId: null,
    assistantMessage: null,
    assistantRow: null,
    deliveryPromise: Promise.resolve(),
    renderedCodePoints: 0,
    draftKey: `text-v01-draft:${conversationId}`,
  };
  currentTurn = view;
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  setBusy();
  setStatus(previous && !previous.finished ? "応答を切り替えています…" : "送信しています…");

  view.startPromise = (async () => {
    if (previous) {
      try { await previous.deliveryPromise; } catch { /* failed ACK is handled by the originating turn */ }
      if (previous.startPromise) await previous.startPromise.catch(() => null);
    }
    const responsePromise = fetch("/api/turns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, reply_to_message_id: view.replyToMessageId }),
    });
    return responsePromise;
  })();
  try {
    const response = await view.startPromise;
    await consumeTurnStream(view, response);
  } catch (error) {
    if (view.turnId && !view.superseded) {
      postJson(`/api/turns/${view.turnId}/cancel`, { reason: "client_stream_error" }).catch(() => {});
    }
    if (!view.superseded && currentTurn === view) {
      setStatus(`送信または接続に失敗しました: ${error.message}`, true);
      if (!input.value) input.value = text;
      try { localStorage.setItem(view.draftKey, input.value); } catch { /* storage may be disabled */ }
      sendButton.disabled = !input.value.trim();
      if (view.turnId) await loadLatestHistory(false).catch(() => {});
    }
  }
}

async function stopGeneration() {
  const view = currentTurn;
  if (!view?.turnId || view.finished) return;
  stopButton.disabled = true;
  setStatus("停止しています…");
  try {
    await postJson(`/api/turns/${view.turnId}/cancel`, { reason: "user_cancelled" });
  } catch (error) {
    setStatus(`停止要求に失敗しました: ${error.message}`, true);
  } finally {
    stopButton.disabled = false;
  }
}

async function loadLatestHistory(scroll = true) {
  const response = await fetch("/api/history?limit=60", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const page = await response.json();
  messages.splice(0, messages.length, ...page.messages);
  historyCursor = page.next_cursor;
  historyHasMore = page.has_more;
  historyAtLatest = true;
  loadOlderButton.hidden = !historyHasMore;
  renderAllMessages();
  if (scroll) scrollToLatest("auto");
  else updateLatestButton();
}

async function loadOlderHistory() {
  if (!historyHasMore || !historyCursor) return;
  loadOlderButton.disabled = true;
  try {
    const params = new URLSearchParams({
      limit: "60",
      before_created_at: historyCursor.created_at,
      before_id: historyCursor.id,
    });
    const response = await fetch(`/api/history?${params}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const page = await response.json();
    mergeOlderPage(page.messages);
    historyCursor = page.next_cursor;
    historyHasMore = page.has_more;
    loadOlderButton.hidden = !historyHasMore;
  } catch (error) {
    setStatus(`過去の履歴を読み込めませんでした: ${error.message}`, true);
  } finally {
    loadOlderButton.disabled = false;
  }
}

async function jumpToMessage(messageId) {
  const existing = messageNodes.get(messageId);
  if (existing) {
    existing.row.scrollIntoView({ behavior: "smooth", block: "center" });
    existing.row.classList.add("highlight");
    setTimeout(() => existing.row.classList.remove("highlight"), 1600);
    return;
  }
  const response = await fetch(`/api/history/around?id=${encodeURIComponent(messageId)}&radius=30`, { cache: "no-store" });
  if (!response.ok) throw new Error("引用元の履歴が見つかりません。");
  const page = await response.json();
  historyAtLatest = false;
  messages.splice(0, messages.length, ...page.messages);
  historyHasMore = page.has_older;
  historyCursor = page.messages.length ? { created_at: page.messages[0].created_at, id: page.messages[0].id } : null;
  loadOlderButton.hidden = !historyHasMore;
  renderAllMessages();
  messageNodes.get(messageId)?.row.scrollIntoView({ behavior: "smooth", block: "center" });
  messageNodes.get(messageId)?.row.classList.add("highlight");
}

function showSearchResults(results, query) {
  searchResults.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "search-results-heading";
  heading.textContent = `${results.length} 件の検索結果: ${query}`;
  searchResults.append(heading);
  for (const result of results) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "search-result";
    const speaker = document.createElement("strong");
    speaker.textContent = result.speaker === "user" ? "あなた" : document.querySelector("#identity-name").textContent;
    const excerpt = document.createElement("span");
    excerpt.textContent = result.content.slice(0, 180);
    const date = document.createElement("time");
    date.textContent = formatDay(result.created_at);
    button.append(speaker, excerpt, date);
    button.addEventListener("click", () => jumpToMessage(result.id).catch((error) => setStatus(error.message, true)));
    searchResults.append(button);
  }
  searchResults.hidden = false;
}

async function searchHistory(event) {
  event.preventDefault();
  const query = searchInput.value.trim();
  if (!query) { searchResults.hidden = true; searchResults.replaceChildren(); return; }
  const params = new URLSearchParams({ q: query, limit: "50" });
  try {
    const response = await fetch(`/api/search?${params}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    showSearchResults(data.results, query);
  } catch (error) {
    setStatus(`履歴を検索できませんでした: ${error.message}`, true);
  }
}

async function loadHistory() {
  const response = await fetch("/api/bootstrap", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  conversationId = data.conversation_id;
  document.querySelector("#identity-name").textContent = data.identity.name;
  document.title = `${data.identity.name} · Text v0.1`;
  connectionState.textContent = "ローカル会話";
  try {
    const draft = localStorage.getItem(`text-v01-draft:${conversationId}`);
    if (draft) input.value = draft;
  } catch { /* storage may be disabled */ }
  await loadLatestHistory(true);
  sendButton.disabled = !input.value.trim();
}

sendButton.addEventListener("click", sendMessage);
stopButton.addEventListener("click", stopGeneration);
loadOlderButton.addEventListener("click", loadOlderHistory);
latestButton.addEventListener("click", () => loadLatestHistory(true).catch((error) => setStatus(error.message, true)));
searchForm.addEventListener("submit", searchHistory);
document.querySelector("#clear-reply").addEventListener("click", clearReplyTarget);
conversation.addEventListener("scroll", updateLatestButton, { passive: true });
messageList.addEventListener("click", (event) => {
  const quote = event.target.closest("[data-target-message-id]");
  if (quote) jumpToMessage(quote.dataset.targetMessageId).catch((error) => setStatus(error.message, true));
});
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 190)}px`;
  sendButton.disabled = !input.value.trim();
  if (conversationId) {
    try {
      if (input.value) localStorage.setItem(`text-v01-draft:${conversationId}`, input.value);
      else if (!currentTurn || currentTurn.finished) localStorage.removeItem(`text-v01-draft:${conversationId}`);
    } catch { /* storage may be disabled */ }
  }
});
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

loadHistory().catch((error) => {
  setStatus(`ローカルアプリに接続できません: ${error.message}`, true);
  connectionState.textContent = "接続できません";
});
