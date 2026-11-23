// Constitution Ai web page. Talks to server.py:
//   GET  /api/providers, /api/datasets     POST /api/datasets, /api/extract
//   POST /v1/chat/completions  (OpenAI-style request, server-sent events back)
// Chats and settings are kept in this browser's localStorage.

const DISCLAIMER =
  "This assistant gives general legal information, not legal advice. It is not a lawyer, it can make " +
  "mistakes, and talking to it does not create a lawyer-client relationship. Laws change and differ by " +
  "place, so check anything important against official sources, and talk to a qualified lawyer before " +
  "you act on a real case, sign a document, or go to court.";
const JURISDICTIONS = ["India", "United States", "United Kingdom", "Canada", "Australia", "Other / General"];
const LANGUAGES = ["", "English", "Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Gujarati", "Kannada", "Spanish", "French"];
const TOPICS = [
  { icon: "i-home", label: "Tenancy", text: "My landlord won't return my security deposit. What can I do?" },
  { icon: "i-cart", label: "Consumer", text: "How do I file a consumer complaint against a company for a defective product?" },
  { icon: "i-shield", label: "Police", text: "The police are refusing to register my complaint. What are my options?" },
  { icon: "i-family", label: "Family", text: "How does mutual consent divorce work, and how long does it take?" },
  { icon: "i-work", label: "Work", text: "My employer hasn't paid my last two months of salary. What can I do?" },
];
const MAX_IMAGE_SIDE = 1600;

// ---------- small helpers ----------
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
  },
};
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined) node.append(kid);
  return node;
};
const icon = (id) => {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  const use = document.createElementNS(ns, "use");
  use.setAttribute("href", `#${id}`);
  svg.append(use);
  return svg;
};
let toastTimer;
function toast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3600);
}
function ago(ts) {
  const s = Math.round((Date.now() - ts) / 1000);
  if (s < 45) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} hour${h > 1 ? "s" : ""} ago`;
  const d = Math.round(h / 24);
  if (d < 7) return `${d} day${d > 1 ? "s" : ""} ago`;
  return new Date(ts).toLocaleDateString();
}
function renderMarkdown(text) {
  if (window.marked && window.DOMPurify) {
    return DOMPurify.sanitize(marked.parse(text, { breaks: true, gfm: true }));
  }
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML.replace(/\n/g, "<br>");
}

// ---------- state ----------
const state = {
  settings: Object.assign(
    { provider: "", model: "", jurisdiction: "India", language: "", effort: "high", webSearch: false,
      showReasoning: true, temperature: "", maxTokens: "", topK: 5, instructions: "", datasets: [] },
    store.get("ca.settings", {})
  ),
  chats: store.get("ca.chats", []),
  currentId: null,
  draft: null, // a new chat that has no messages yet
  providers: [],
  defaultProvider: "",
  datasets: [],
  pending: [], // attachments waiting to be sent: {kind: "image"|"doc", name, url|text}
  controller: null,
  period: "weekly",
  view: "dashboard",
};

function saveSettings() { store.set("ca.settings", state.settings); }
function saveChats() {
  if (!store.set("ca.chats", state.chats)) {
    toast("Browser storage is full. Delete some old chats (photos take the most space).");
  }
  updateCounts();
}
function currentChat() {
  return state.chats.find((c) => c.id === state.currentId) || state.draft;
}
function newChat() {
  if (state.controller) state.controller.abort();
  state.draft = { id: `c${Date.now()}`, title: "New chat", created: Date.now(), updated: Date.now(), messages: [] };
  state.currentId = null;
  renderMessages();
  $("#prompt").focus();
}
function provider() {
  return state.providers.find((p) => p.name === state.settings.provider);
}

// ---------- navigation ----------
function showView(name) {
  state.view = name;
  for (const v of $$(".view")) v.hidden = v.id !== `view-${name}`;
  for (const b of $$(".nav button")) {
    if (b.dataset.view === name) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  }
  if (name === "chats") renderChatList();
  if (name === "datasets") loadDatasets();
  if (name === "dashboard") renderDashboard();
  $(".left").scrollTop = 0;
}

// ---------- dashboard ----------
function renderDashboard() {
  const s = state.settings;
  const p = provider();
  const sub = $("#hero-sub");
  sub.replaceChildren(
    el("span", { class: "chip" }, el("span", { class: `dot ${p && p.has_key ? "" : "warn"}` }),
      p ? `${p.title} · ${s.model || p.default_model}` : "Loading providers…"),
    el("span", { class: "chip" }, s.language ? `Answers in ${s.language}` : "Answers in your language"),
  );
  if (p && !p.has_key) {
    sub.append(el("span", { class: "chip" }, `Add ${p.env_key} to .env`));
  }
  const adjective = { India: "Indian", "United States": "US", "United Kingdom": "UK", Canada: "Canadian", Australia: "Australian" };
  $("#status-title").textContent = adjective[s.jurisdiction]
    ? `You’re asking about ${adjective[s.jurisdiction]} law`
    : "You’re asking a general legal question";
  const total = state.datasets.length;
  const active = s.datasets.filter((n) => state.datasets.some((d) => d.name === n)).length;
  $("#status-fill").style.width = total ? `${Math.max(12, (active / total) * 100)}%` : "12%";
  $("#status-label").replaceChildren(String(active), el("span", {}, `/${total} datasets on`));
  renderSummary();
}

function renderTiles() {
  $("#tiles").replaceChildren(...TOPICS.map((t) =>
    el("button", { class: "tile", onclick: () => usePrompt(t.text) },
      el("span", { class: "ico" }, icon(t.icon)), t.label)));
}

function usePrompt(text) {
  const box = $("#prompt");
  box.value = text;
  autosize();
  updateSend();
  box.focus();
}

function periodBuckets(period) {
  const now = new Date();
  const buckets = [];
  if (period === "daily") {
    const start = new Date(now); start.setHours(0, 0, 0, 0);
    for (let i = 0; i < 12; i++) buckets.push([start.getTime() + i * 2 * 3600e3, start.getTime() + (i + 1) * 2 * 3600e3]);
  } else {
    const days = period === "weekly" ? 7 : 30;
    const end = new Date(now); end.setHours(24, 0, 0, 0);
    for (let i = days; i > 0; i--) buckets.push([end.getTime() - i * 864e5, end.getTime() - (i - 1) * 864e5]);
  }
  return buckets;
}

function renderSummary() {
  const buckets = periodBuckets(state.period);
  const from = buckets[0][0];
  const counts = buckets.map(() => 0);
  let questions = 0, answered = 0, grounded = 0;
  for (const chat of state.chats) {
    for (const m of chat.messages) {
      if (!m.ts || m.ts < from) continue;
      if (m.role === "user") {
        questions++;
        const i = buckets.findIndex(([a, b]) => m.ts >= a && m.ts < b);
        if (i >= 0) counts[i]++;
      } else if (m.role === "assistant" && m.text && !m.error) {
        answered++;
        if (m.text.includes("Reference passages used")) grounded++;
      }
    }
  }
  const max = Math.max(1, ...counts);
  $("#bars").replaceChildren(...counts.map((c) => {
    const bar = el("div", { class: "b", title: `${c} question${c === 1 ? "" : "s"}` }, el("i"));
    bar.firstChild.style.height = c ? `${Math.max(10, (c / max) * 100)}%` : "0";
    return bar;
  }));
  $("#sum-questions").textContent = questions.toLocaleString();
  $("#sum-answered").replaceChildren(String(answered), el("small", {}, `/${questions}`));
  $("#sum-grounded").replaceChildren(String(grounded), el("small", {}, `/${answered}`));
  $("#arc-inner").setAttribute("stroke-dasharray", `${questions ? (answered / questions) * 100 : 0} 100`);
  $("#arc-outer").setAttribute("stroke-dasharray", `${answered ? (grounded / answered) * 100 : 0} 100`);
  $("#sum-chats").textContent = state.chats.length.toLocaleString();
}

function updateCounts() {
  $("#nav-chats").textContent = state.chats.length;
  $("#nav-datasets").textContent = state.datasets.length;
}

// ---------- chat rendering ----------
function bubbleFor(m, index, chat) {
  if (m.role === "user") {
    const files = el("div", { class: "attach-list" },
      (m.images || []).map((url) => el("span", { class: "attach" }, el("img", { src: url, alt: "" }), "Photo")),
      (m.docs || []).map((d) => el("span", { class: "attach" }, `📎 ${d.name}`)));
    return el("div", { class: "msg user" },
      files.childElementCount ? files : null,
      m.text ? el("div", { class: "bubble" }, m.text) : null,
      el("div", { class: "time" }, ago(m.ts)));
  }
  const bubble = el("div", { class: "bubble md" });
  if (m.reasoning && state.settings.showReasoning) {
    bubble.append(el("details", { class: "thinking" }, el("summary", {}, "Reasoning"), el("div", {}, m.reasoning)));
  }
  const body = el("div");
  if (m.error) {
    body.append(el("p", { class: "err" }, m.error));
  } else if (!m.text && m.streaming) {
    body.append(el("span", { class: "typing", "aria-label": "Thinking" }, el("i"), el("i"), el("i")));
  } else {
    body.innerHTML = renderMarkdown(m.text);
  }
  bubble.append(body);
  const isLast = index === chat.messages.length - 1;
  const actions = el("div", { class: "time" });
  if (!m.streaming) {
    if (m.text) {
      actions.append(el("button", {
        class: "icon-btn", title: "Copy", "aria-label": "Copy answer",
        onclick: () => navigator.clipboard.writeText(m.text).then(() => toast("Copied"), () => toast("Couldn't copy")),
      }, icon("i-copy")));
    }
    if (isLast) {
      actions.append(el("button", {
        class: "icon-btn", title: m.error ? "Try again" : "Regenerate", "aria-label": m.error ? "Try again" : "Regenerate answer",
        onclick: regenerate,
      }, icon("i-redo")));
    }
    actions.append(el("span", {}, ago(m.ts)));
  }
  return el("div", { class: "msg bot", "data-index": index }, bubble, actions);
}

function renderWelcome() {
  return el("div", { class: "welcome" },
    el("div", { class: "bubble" },
      "Hi! Tell me what happened, where, and when. You can also attach a notice, contract, FIR or court order."),
    el("div", { class: "starters" }, TOPICS.slice(0, 3).map((t) => el("button", { onclick: () => usePrompt(t.text) }, t.text))));
}

function renderMessages() {
  const box = $("#msgs");
  const chat = currentChat();
  if (!chat || !chat.messages.length) {
    box.replaceChildren(renderWelcome());
    return;
  }
  box.replaceChildren(...chat.messages.map((m, i) => bubbleFor(m, i, chat)));
  box.scrollTop = box.scrollHeight;
}

let frame = 0;
function renderStreaming(chat, reply) {
  if (frame) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    const box = $("#msgs");
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
    const index = chat.messages.indexOf(reply);
    const old = box.querySelector(`.msg.bot[data-index="${index}"]`);
    const fresh = bubbleFor(reply, index, chat);
    if (old) old.replaceWith(fresh); else box.append(fresh);
    if (nearBottom) box.scrollTop = box.scrollHeight;
  });
}

// ---------- sending ----------
function toApiMessages(chat) {
  const out = [];
  if (state.settings.instructions.trim()) out.push({ role: "system", content: state.settings.instructions.trim() });
  for (const m of chat.messages) {
    if (m.role === "user") {
      let text = m.text || "";
      for (const d of m.docs || []) text += `\n\nAttached document: ${d.name}\n###\n${d.text}\n###`;
      if (!text.trim()) text = "Please look at the attached file(s) and explain what they mean for me.";
      if (m.images && m.images.length) {
        out.push({ role: "user", content: [
          ...m.images.map((url) => ({ type: "image_url", image_url: { url } })),
          { type: "text", text },
        ] });
      } else {
        out.push({ role: "user", content: text });
      }
    } else if (m.text && !m.error) {
      out.push({ role: "assistant", content: m.text });
    }
  }
  return out;
}

async function send() {
  if (state.controller) return;
  const box = $("#prompt");
  const text = box.value.trim();
  if (!text && !state.pending.length) return;
  let chat = currentChat();
  if (!chat) { newChat(); chat = state.draft; }
  const images = state.pending.filter((a) => a.kind === "image").map((a) => a.url);
  const docs = state.pending.filter((a) => a.kind === "doc").map((a) => ({ name: a.name, text: a.text }));
  chat.messages.push({ role: "user", text, images, docs, ts: Date.now() });
  if (chat === state.draft) {
    chat.title = (text || docs[0]?.name || "Photo question").slice(0, 70);
    state.chats.unshift(chat);
    state.currentId = chat.id;
    state.draft = null;
  }
  box.value = "";
  state.pending = [];
  renderPending();
  autosize();
  renderMessages();
  await generate(chat);
}

async function generate(chat) {
  const s = state.settings;
  const reply = { role: "assistant", text: "", reasoning: "", ts: Date.now(), streaming: true };
  const messages = toApiMessages(chat);
  chat.messages.push(reply);
  renderMessages();
  state.controller = new AbortController();
  updateSend();

  const body = {
    provider: s.provider, model: s.model, stream: true, messages,
    jurisdiction: s.jurisdiction, language: s.language,
    effort: s.effort, web_search: s.webSearch, show_reasoning: s.showReasoning,
    datasets: s.datasets, top_k: Number(s.topK) || 5,
    temperature: s.temperature, max_tokens_value: s.maxTokens,
  };
  try {
    const res = await fetch("/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal: state.controller.signal,
    });
    if (!res.ok) {
      let message = `${res.status} ${res.statusText}`;
      try { message = (await res.json()).error?.message || message; } catch { /* not JSON */ }
      throw new Error(message);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const raw of lines) {
        const line = raw.trim();
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (!data || data === "[DONE]") continue;
        try {
          const obj = JSON.parse(data);
          for (const choice of obj.choices || []) {
            const delta = choice.delta || choice.message || {};
            if (typeof delta.reasoning_content === "string") reply.reasoning += delta.reasoning_content;
            if (typeof delta.content === "string") reply.text += delta.content;
          }
        } catch { /* ignore keep-alive or partial lines */ }
      }
      renderStreaming(chat, reply);
    }
    if (!reply.text.trim()) reply.error = "The model sent an empty answer. Try again, or pick another model in Settings.";
  } catch (err) {
    if (err.name === "AbortError") {
      if (reply.text) reply.text += "\n\n_(Stopped.)_";
      else chat.messages.splice(chat.messages.indexOf(reply), 1);
    } else {
      reply.error = err.message || "Something went wrong.";
    }
  } finally {
    delete reply.streaming;
    state.controller = null;
    chat.updated = Date.now();
    saveChats();
    renderMessages();
    updateSend();
    if (state.view === "dashboard") renderSummary();
  }
}

function regenerate() {
  const chat = currentChat();
  if (!chat || state.controller) return;
  while (chat.messages.length && chat.messages[chat.messages.length - 1].role === "assistant") chat.messages.pop();
  if (chat.messages.length) generate(chat);
}

function updateSend() {
  const btn = $("#send");
  const busy = Boolean(state.controller);
  btn.replaceChildren(icon(busy ? "i-stop" : "i-send"));
  btn.setAttribute("aria-label", busy ? "Stop" : "Send");
  btn.disabled = !busy && !$("#prompt").value.trim() && !state.pending.length;
}

function autosize() {
  const box = $("#prompt");
  box.style.height = "auto";
  box.style.height = `${Math.min(box.scrollHeight, 180)}px`;
  box.style.overflowY = box.scrollHeight > 180 ? "auto" : "hidden";
}

// ---------- attachments ----------
function renderPending() {
  $("#pending").replaceChildren(...state.pending.map((a, i) =>
    el("span", { class: "attach" },
      a.kind === "image" ? el("img", { src: a.url, alt: "" }) : "📎",
      a.name,
      el("button", { "aria-label": `Remove ${a.name}`, onclick: () => { state.pending.splice(i, 1); renderPending(); updateSend(); } }, "×"))));
  updateSend();
}

function shrinkImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(`Couldn't read ${file.name}`));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error(`${file.name} isn't a supported image`));
      img.onload = () => {
        const scale = Math.min(1, MAX_IMAGE_SIDE / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.82));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

async function addAttachments(files) {
  for (const file of files) {
    try {
      if (file.type.startsWith("image/")) {
        state.pending.push({ kind: "image", name: file.name, url: await shrinkImage(file) });
      } else {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch("/api/extract", { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error?.message || res.statusText);
        state.pending.push({ kind: "doc", name: data.name, text: data.text });
        if (data.truncated) toast(`${data.name} is long; only the first part will be sent.`);
      }
    } catch (err) {
      toast(err.message);
    }
    renderPending();
  }
}

// ---------- voice input ----------
function setupMic() {
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = $("#mic");
  if (!Rec) { btn.hidden = true; return; }
  const codes = { Hindi: "hi-IN", Bengali: "bn-IN", Marathi: "mr-IN", Tamil: "ta-IN", Telugu: "te-IN", Gujarati: "gu-IN", Kannada: "kn-IN", Spanish: "es-ES", French: "fr-FR" };
  let rec = null;
  btn.addEventListener("click", () => {
    if (rec) { rec.stop(); return; }
    rec = new Rec();
    rec.lang = codes[state.settings.language] || (state.settings.jurisdiction === "India" ? "en-IN" : navigator.language);
    rec.interimResults = true;
    const base = $("#prompt").value;
    rec.onresult = (e) => {
      const said = [...e.results].map((r) => r[0].transcript).join("");
      $("#prompt").value = (base ? `${base} ` : "") + said;
      autosize(); updateSend();
    };
    rec.onerror = (e) => { if (e.error !== "aborted") toast(e.error === "not-allowed" ? "Allow microphone access to speak." : "Couldn't hear that. Try again."); };
    rec.onend = () => { rec = null; btn.classList.remove("rec"); };
    btn.classList.add("rec");
    rec.start();
  });
}

// ---------- chats view ----------
function chatMarkdown(chat) {
  const lines = [`# ${chat.title}`, "", `_${new Date(chat.created).toLocaleString()}_`, ""];
  for (const m of chat.messages) {
    if (m.role === "user") {
      lines.push("## You", "");
      for (const d of m.docs || []) lines.push(`[Attached: ${d.name}]`);
      if (m.images?.length) lines.push(`[${m.images.length} photo(s) attached]`);
      lines.push(m.text || "", "");
    } else if (m.text) {
      lines.push("## Assistant", "", m.text, "");
    }
  }
  lines.push("---", DISCLAIMER);
  return lines.join("\n");
}

function download(chat) {
  if (!chat || !chat.messages.length) { toast("Nothing to download yet."); return; }
  const blob = new Blob([chatMarkdown(chat)], { type: "text/markdown" });
  const a = el("a", { href: URL.createObjectURL(blob), download: `${chat.title.replace(/[^\w\- ]+/g, "").slice(0, 40) || "chat"}.md` });
  document.body.append(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}

function renderChatList() {
  const q = $("#chat-search").value.trim().toLowerCase();
  const chats = state.chats.filter((c) => !q || c.title.toLowerCase().includes(q) ||
    c.messages.some((m) => (m.text || "").toLowerCase().includes(q)));
  const list = $("#chat-list");
  if (!chats.length) {
    list.replaceChildren(el("div", { class: "empty" }, state.chats.length ? "No chats match your search." : "No saved chats yet. Ask your first question in the chat panel."));
    return;
  }
  list.replaceChildren(...chats.map((c) =>
    el("div", { class: `item${c.id === state.currentId ? " active" : ""}` },
      el("span", { class: "icon-btn" }, icon("i-chats")),
      el("button", { class: "meta", style: "text-align:left", onclick: () => { state.currentId = c.id; state.draft = null; renderMessages(); renderChatList(); } },
        el("b", {}, c.title),
        el("small", {}, `${c.messages.filter((m) => m.role === "user").length} questions · ${ago(c.updated)}`)),
      el("button", { class: "icon-btn", title: "Download", "aria-label": `Download ${c.title}`, onclick: () => download(c) }, icon("i-down")),
      el("button", { class: "icon-btn", title: "Delete", "aria-label": `Delete ${c.title}`, onclick: () => {
        if (!confirm(`Delete “${c.title}”? This can't be undone.`)) return;
        state.chats = state.chats.filter((x) => x.id !== c.id);
        if (state.currentId === c.id) newChat();
        saveChats(); renderChatList();
      } }, icon("i-trash")))));
}

// ---------- datasets view ----------
async function api(url, options) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error?.message || res.statusText);
  return data;
}

async function loadDatasets() {
  try {
    state.datasets = (await api("/api/datasets")).datasets;
    const names = state.datasets.map((d) => d.name);
    state.settings.datasets = state.settings.datasets.filter((n) => names.includes(n));
    saveSettings();
  } catch (err) {
    toast(`Couldn't load datasets: ${err.message}`);
  }
  renderDatasets();
  updateCounts();
  if (state.view === "dashboard") renderDashboard();
}

function renderDatasets() {
  const list = $("#ds-list");
  if (!state.datasets.length) {
    list.replaceChildren(el("div", { class: "empty" }, "No datasets yet."));
    return;
  }
  list.replaceChildren(...state.datasets.map((d) => {
    const toggle = el("input", { type: "checkbox", "aria-label": `Use ${d.name}` });
    toggle.checked = state.settings.datasets.includes(d.name);
    toggle.addEventListener("change", () => {
      const set = new Set(state.settings.datasets);
      if (toggle.checked) set.add(d.name); else set.delete(d.name);
      state.settings.datasets = [...set];
      saveSettings();
    });
    const kb = d.size < 1024 * 1024 ? `${(d.size / 1024).toFixed(1)} KB` : `${(d.size / 1048576).toFixed(1)} MB`;
    return el("div", { class: "item" },
      el("span", { class: "icon-btn" }, icon("i-data")),
      el("div", { class: "meta" }, el("b", {}, d.name), el("small", {}, `${kb} · ${d.chunks} passages`)),
      el("label", { class: "toggle", title: "Use for answers" }, toggle, el("span")),
      el("button", { class: "icon-btn", title: "Delete", "aria-label": `Delete ${d.name}`, onclick: async () => {
        if (!confirm(`Delete the dataset “${d.name}” from the server? This can't be undone.`)) return;
        try { await api(`/api/datasets/${encodeURIComponent(d.name)}`, { method: "DELETE" }); } catch (err) { toast(err.message); }
        loadDatasets();
      } }, icon("i-trash")));
  }));
}

async function uploadDatasets(files) {
  for (const file of files) {
    const form = new FormData();
    form.append("file", file);
    try {
      const data = await api("/api/datasets", { method: "POST", body: form });
      if (!state.settings.datasets.includes(data.name)) state.settings.datasets.push(data.name);
      saveSettings();
      toast(`${data.name} added`);
    } catch (err) {
      toast(err.message);
    }
  }
  loadDatasets();
}

// ---------- settings view ----------
function option(value, label, selected) {
  const o = el("option", { value }, label);
  o.selected = selected;
  return o;
}

function renderSettings() {
  const s = state.settings;
  $("#set-provider").replaceChildren(...state.providers.map((p) =>
    option(p.name, p.has_key ? p.title : `${p.title} (no API key)`, p.name === s.provider)));
  const p = provider();
  $("#set-model").replaceChildren(...(p ? p.models : []).map((m) => option(m, m, m === s.model)));
  $("#provider-hint").textContent = !p ? "" : p.has_key
    ? "Ready."
    : `No API key yet. Add ${p.env_key}=… to the .env file next to server.py, then reload this page.`;
  $("#set-jurisdiction").replaceChildren(...JURISDICTIONS.map((j) => option(j, j, j === s.jurisdiction)));
  $("#set-language").replaceChildren(...LANGUAGES.map((l) => option(l, l || "Same as my question", l === s.language)));
  $("#set-effort").value = s.effort;
  $("#set-web").checked = s.webSearch;
  $("#set-temp").value = s.temperature;
  $("#set-maxtok").value = s.maxTokens;
  $("#set-reasoning").checked = s.showReasoning;
  $("#set-instructions").value = s.instructions;
  $("#set-topk").value = s.topK;
  const isClaude = s.provider === "claude";
  $("#claude-card").hidden = !isClaude;
  $("#other-card").hidden = isClaude;
  updatePromo();
}

function selectProvider(name) {
  state.settings.provider = name;
  const p = provider();
  if (p && !p.models.includes(state.settings.model)) state.settings.model = p.default_model;
  saveSettings();
}

function bindSettings() {
  const s = state.settings;
  const on = (id, evt, fn) => $(id).addEventListener(evt, (e) => { fn(e.target); saveSettings(); renderSettings(); renderDashboard(); });
  on("#set-provider", "change", (t) => selectProvider(t.value));
  on("#set-model", "change", (t) => { s.model = t.value; });
  on("#set-jurisdiction", "change", (t) => { s.jurisdiction = t.value; });
  on("#set-language", "change", (t) => { s.language = t.value; });
  on("#set-effort", "change", (t) => { s.effort = t.value; });
  on("#set-web", "change", (t) => { s.webSearch = t.checked; });
  on("#set-temp", "change", (t) => { s.temperature = t.value; });
  on("#set-maxtok", "change", (t) => { s.maxTokens = t.value; });
  on("#set-reasoning", "change", (t) => { s.showReasoning = t.checked; renderMessages(); });
  on("#set-instructions", "change", (t) => { s.instructions = t.value; });
  on("#set-topk", "change", (t) => { s.topK = Math.min(20, Math.max(1, Number(t.value) || 5)); });
}

function updatePromo() {
  const india = state.settings.jurisdiction === "India";
  $("#promo-text").textContent = india
    ? "Free legal aid is available. In India, call the NALSA helpline on 15100."
    : "Many places offer free legal aid. Search for legal aid services near you.";
  $("#promo-link").href = india ? "https://nalsa.gov.in" : "https://www.google.com/search?q=free+legal+aid+near+me";
}

async function loadProviders() {
  try {
    const data = await api("/api/providers");
    state.providers = data.providers;
    state.defaultProvider = data.default;
    if (!provider()) selectProvider(data.default);
    else if (!provider().models.includes(state.settings.model)) selectProvider(state.settings.provider);
  } catch (err) {
    toast(`Couldn't reach the server: ${err.message}`);
  }
  renderSettings();
  renderDashboard();
}

// ---------- start ----------
function init() {
  $("#disclaimer-text").textContent = DISCLAIMER;
  $("#about-disclaimer").textContent = DISCLAIMER;
  if (!store.get("ca.accepted", false)) {
    $("#disclaimer").showModal();
  }
  $("#accept").addEventListener("click", () => { store.set("ca.accepted", true); $("#disclaimer").close(); $("#prompt").focus(); });
  $("#disclaimer").addEventListener("cancel", (e) => e.preventDefault());

  for (const b of $$(".nav button")) b.addEventListener("click", () => showView(b.dataset.view));
  for (const b of $$("[data-go]")) b.addEventListener("click", () => showView(b.dataset.go));
  for (const b of $$(".seg button")) {
    b.addEventListener("click", () => {
      state.period = b.dataset.period;
      for (const x of $$(".seg button")) x.setAttribute("aria-pressed", String(x === b));
      renderSummary();
    });
  }

  const prompt = $("#prompt");
  prompt.addEventListener("input", () => { autosize(); updateSend(); });
  prompt.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
  });
  $("#send").addEventListener("click", () => (state.controller ? state.controller.abort() : send()));
  $("#new-chat").addEventListener("click", newChat);
  $("#chats-new").addEventListener("click", () => { newChat(); renderChatList(); });
  $("#download-chat").addEventListener("click", () => download(currentChat()));
  $("#attach").addEventListener("click", () => $("#attach-file").click());
  $("#attach-file").addEventListener("change", (e) => { addAttachments([...e.target.files]); e.target.value = ""; });
  $("#chat-search").addEventListener("input", renderChatList);
  $("#chats-clear").addEventListener("click", () => {
    if (!state.chats.length || !confirm(`Delete all ${state.chats.length} saved chats? This can't be undone.`)) return;
    state.chats = [];
    newChat();
    saveChats();
    renderChatList();
  });

  const drop = $("#drop");
  $("#ds-file").addEventListener("change", (e) => { uploadDatasets([...e.target.files]); e.target.value = ""; });
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); uploadDatasets([...e.dataTransfer.files]); });

  bindSettings();
  setupMic();
  renderTiles();
  state.currentId = state.chats[0]?.id || null;
  if (!state.currentId) newChat();
  renderMessages();
  updateCounts();
  updateSend();
  renderSettings();
  renderDashboard();
  loadProviders();
  loadDatasets();
  // Keep "2 min ago" labels fresh.
  setInterval(() => { if (!state.controller) renderMessages(); }, 60000);
}

init();
