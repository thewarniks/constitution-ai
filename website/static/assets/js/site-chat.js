// Chat page of the Constitution Ai website. Uses the same backend as the dashboard (server.py):
//   GET /api/providers, /api/datasets   POST /api/extract, /v1/chat/completions (streamed)
// Chats and settings use the same localStorage keys as the dashboard (/app), so both share history.
(() => {
  "use strict";

  const CFG = window.CHAT_CONFIG || {};
  const JURISDICTIONS = ["India", "United States", "United Kingdom", "Canada", "Australia", "Other / General"];
  const LANGUAGES = [""].concat(CFG.languages || ["English", "Hindi"]);
  const MAX_IMAGE_SIDE = 1600;
  // Set by export_static.py on the GitHub Pages copy, which has no Python server behind it.
  const STATIC = Boolean(window.CA_STATIC);
  const STATIC_NOTE = "This is the static preview of Constitution Ai on GitHub Pages. The AI chat needs the Python server: " +
    "download the project and run it (see the README), and this page will answer your questions.";

  const $ = (s) => document.querySelector(s);
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch { return false; } },
  };
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") n.className = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid !== null && kid !== undefined) n.append(kid);
    return n;
  };
  const iconEl = (name) => el("i", { class: `icon ${name}` });

  function status(msg, isError) {
    const s = $("#cs-status");
    s.textContent = msg || "";
    s.classList.toggle("err", Boolean(isError));
    if (msg && !isError) setTimeout(() => { if (s.textContent === msg) s.textContent = ""; }, 3500);
  }
  function ago(ts) {
    const s = Math.round((Date.now() - ts) / 1000);
    if (s < 45) return "just now";
    const m = Math.round(s / 60); if (m < 60) return `${m} min ago`;
    const h = Math.round(m / 60); if (h < 24) return `${h} hour${h > 1 ? "s" : ""} ago`;
    const d = Math.round(h / 24); if (d < 7) return `${d} day${d > 1 ? "s" : ""} ago`;
    return new Date(ts).toLocaleDateString();
  }
  function md(text) {
    if (window.marked && window.DOMPurify) return DOMPurify.sanitize(marked.parse(text, { breaks: true, gfm: true }));
    const d = document.createElement("div"); d.textContent = text; return d.innerHTML.replace(/\n/g, "<br>");
  }

  // ---------- state (shared format with /app) ----------
  const state = {
    settings: Object.assign(
      { provider: "", model: "", jurisdiction: "India", language: "", effort: "high", webSearch: false,
        showReasoning: true, temperature: "", maxTokens: "", topK: 5, instructions: "", datasets: [] },
      store.get("ca.settings", {})
    ),
    chats: store.get("ca.chats", []),
    currentId: null,
    draft: null,
    providers: [],
    datasets: [],
    pending: [],
    controller: null,
  };
  const saveSettings = () => store.set("ca.settings", state.settings);
  const saveChats = () => { if (!store.set("ca.chats", state.chats)) status("Browser storage is full. Delete some old chats.", true); renderHistory(); };
  const currentChat = () => state.chats.find((c) => c.id === state.currentId) || state.draft;
  const provider = () => state.providers.find((p) => p.name === state.settings.provider);

  function newChat() {
    if (state.controller) state.controller.abort();
    state.draft = { id: `c${Date.now()}`, title: "New chat", created: Date.now(), updated: Date.now(), messages: [] };
    state.currentId = null;
    renderMessages(); renderHistory();
    $("#cs-prompt").focus();
  }

  // ---------- rendering ----------
  function welcome() {
    return el("div", { class: "chat-welcome" },
      STATIC ? el("div", { class: "bubble bot static-note" }, STATIC_NOTE) : null,
      el("div", { class: "bubble bot" }, "Hi! Tell me what happened, where, and when. You can also attach a notice, contract, FIR or court order."),
      el("div", { class: "chat-starters" }, (CFG.starters || []).map((q) => el("button", { type: "button", onclick: () => usePrompt(q) }, q))));
  }

  function messageEl(m, i, chat) {
    if (m.role === "user") {
      const files = el("div", { class: "chat-files" },
        (m.images || []).map((u) => el("span", { class: "chat-file" }, el("img", { src: u, alt: "" }), "Photo")),
        (m.docs || []).map((d) => el("span", { class: "chat-file" }, iconEl("icon-paperclip-solid"), d.name)));
      return el("div", { class: "msg user" },
        files.childElementCount ? files : null,
        m.text ? el("div", { class: "bubble user" }, m.text) : null,
        el("div", { class: "msg-meta" }, ago(m.ts)));
    }
    const bubble = el("div", { class: "bubble bot md" });
    if (m.reasoning && state.settings.showReasoning) {
      bubble.append(el("details", { class: "thinking" }, el("summary", {}, "Reasoning"), el("div", {}, m.reasoning)));
    }
    const body = el("div");
    if (m.error) body.append(el("p", { class: "err" }, m.error));
    else if (!m.text && m.streaming) body.append(el("span", { class: "typing", "aria-label": "Thinking" }, el("i"), el("i"), el("i")));
    else body.innerHTML = md(m.text);
    bubble.append(body);
    const meta = el("div", { class: "msg-meta" });
    if (!m.streaming) {
      if (m.text) meta.append(el("button", { type: "button", class: "meta-btn", onclick: () => navigator.clipboard.writeText(m.text).then(() => status("Copied")) }, "Copy"));
      if (i === chat.messages.length - 1) meta.append(el("button", { type: "button", class: "meta-btn", onclick: regenerate }, m.error ? "Try again" : "Regenerate"));
      meta.append(el("span", {}, ago(m.ts)));
    }
    return el("div", { class: "msg bot", "data-index": i }, bubble, meta);
  }

  function renderMessages() {
    const box = $("#cs-msgs");
    const chat = currentChat();
    if (!chat || !chat.messages.length) { box.replaceChildren(welcome()); return; }
    box.replaceChildren(...chat.messages.map((m, i) => messageEl(m, i, chat)));
    box.scrollTop = box.scrollHeight;
  }

  let frame = 0;
  function renderStreaming(chat, reply) {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      const box = $("#cs-msgs");
      const near = box.scrollHeight - box.scrollTop - box.clientHeight < 140;
      const idx = chat.messages.indexOf(reply);
      const fresh = messageEl(reply, idx, chat);
      const old = box.querySelector(`.msg.bot[data-index="${idx}"]`);
      if (old) old.replaceWith(fresh); else box.append(fresh);
      if (near) box.scrollTop = box.scrollHeight;
    });
  }

  function renderHistory() {
    const list = $("#cs-history");
    if (!state.chats.length) { list.replaceChildren(el("p", { class: "cs-hint" }, "No saved chats yet.")); return; }
    list.replaceChildren(...state.chats.slice(0, 30).map((c) =>
      el("div", { class: `cs-chat${c.id === state.currentId ? " active" : ""}` },
        el("button", { type: "button", class: "cs-chat-open", title: c.title, onclick: () => { state.currentId = c.id; state.draft = null; renderMessages(); renderHistory(); closeSide(); } },
          el("span", { class: "cs-chat-title" }, c.title), el("small", {}, ago(c.updated))),
        el("button", { type: "button", class: "cs-chat-del", "aria-label": `Delete ${c.title}`, onclick: () => {
          if (!confirm(`Delete “${c.title}”? This can't be undone.`)) return;
          state.chats = state.chats.filter((x) => x.id !== c.id);
          if (state.currentId === c.id) newChat();
          saveChats();
        } }, "×"))));
  }

  function option(value, label, selected) { const o = el("option", { value }, label); o.selected = selected; return o; }

  function renderSettings() {
    const s = state.settings;
    $("#cs-provider").replaceChildren(...state.providers.map((p) => option(p.name, p.has_key ? p.title : `${p.title} (no key)`, p.name === s.provider)));
    const p = provider();
    $("#cs-model").replaceChildren(...(p ? p.models : []).map((m) => option(m, m, m === s.model)));
    $("#cs-jurisdiction").replaceChildren(...JURISDICTIONS.map((j) => option(j, j, j === s.jurisdiction)));
    $("#cs-language").replaceChildren(...LANGUAGES.map((l) => option(l, l || "Same as my question", l === s.language)));
    $("#cs-provider-hint").textContent = p && !p.has_key ? `No API key yet: add ${p.env_key} to the .env file on the server.` : "";
  }

  function renderDatasets() {
    const block = $("#cs-datasets-block");
    block.hidden = !state.datasets.length;
    $("#cs-datasets").replaceChildren(...state.datasets.map((d) => {
      const box = el("input", { type: "checkbox" });
      box.checked = state.settings.datasets.includes(d.name);
      box.addEventListener("change", () => {
        const set = new Set(state.settings.datasets);
        box.checked ? set.add(d.name) : set.delete(d.name);
        state.settings.datasets = [...set]; saveSettings();
      });
      return el("label", { class: "cs-check" }, box, el("span", {}, d.name), el("small", {}, `${d.chunks} passages`));
    }));
  }

  // ---------- sending ----------
  function apiMessages(chat) {
    const out = [];
    if ((state.settings.instructions || "").trim()) out.push({ role: "system", content: state.settings.instructions.trim() });
    for (const m of chat.messages) {
      if (m.role === "user") {
        let text = m.text || "";
        for (const d of m.docs || []) text += `\n\nAttached document: ${d.name}\n###\n${d.text}\n###`;
        if (!text.trim()) text = "Please look at the attached file(s) and explain what they mean for me.";
        out.push(m.images && m.images.length
          ? { role: "user", content: [...m.images.map((url) => ({ type: "image_url", image_url: { url } })), { type: "text", text }] }
          : { role: "user", content: text });
      } else if (m.text && !m.error) {
        out.push({ role: "assistant", content: m.text });
      }
    }
    return out;
  }

  async function send() {
    if (state.controller) return;
    if (STATIC) { status("The chat needs the Python server; this is the static preview.", true); return; }
    const box = $("#cs-prompt");
    const text = box.value.trim();
    if (!text && !state.pending.length) return;
    let chat = currentChat();
    if (!chat) { newChat(); chat = state.draft; }
    const images = state.pending.filter((a) => a.kind === "image").map((a) => a.url);
    const docs = state.pending.filter((a) => a.kind === "doc").map((a) => ({ name: a.name, text: a.text }));
    chat.messages.push({ role: "user", text, images, docs, ts: Date.now() });
    if (chat === state.draft) {
      chat.title = (text || docs[0]?.name || "Photo question").slice(0, 70);
      state.chats.unshift(chat); state.currentId = chat.id; state.draft = null;
    }
    box.value = ""; state.pending = []; renderPending(); autosize();
    renderMessages(); renderHistory();
    await generate(chat);
  }

  async function generate(chat) {
    const s = state.settings;
    const reply = { role: "assistant", text: "", reasoning: "", ts: Date.now(), streaming: true };
    const messages = apiMessages(chat);
    chat.messages.push(reply);
    renderMessages();
    state.controller = new AbortController();
    updateSend();
    try {
      const res = await fetch("/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({
          provider: s.provider, model: s.model, stream: true, messages,
          jurisdiction: s.jurisdiction, language: s.language,
          effort: s.effort, web_search: s.webSearch, show_reasoning: s.showReasoning,
          datasets: s.datasets, top_k: Number(s.topK) || 5,
          temperature: s.temperature, max_tokens_value: s.maxTokens,
        }),
        signal: state.controller.signal,
      });
      if (!res.ok) {
        let msg = `${res.status} ${res.statusText}`;
        try { msg = (await res.json()).error?.message || msg; } catch { /* not JSON */ }
        throw new Error(msg);
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();
        for (const raw of lines) {
          const line = raw.trim();
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (!data || data === "[DONE]") continue;
          try {
            for (const c of JSON.parse(data).choices || []) {
              const d = c.delta || c.message || {};
              if (typeof d.reasoning_content === "string") reply.reasoning += d.reasoning_content;
              if (typeof d.content === "string") reply.text += d.content;
            }
          } catch { /* partial line */ }
        }
        renderStreaming(chat, reply);
      }
      if (!reply.text.trim()) reply.error = "The model sent an empty answer. Try again, or pick another model.";
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
      saveChats(); renderMessages(); updateSend();
    }
  }

  function regenerate() {
    const chat = currentChat();
    if (!chat || state.controller) return;
    while (chat.messages.length && chat.messages[chat.messages.length - 1].role === "assistant") chat.messages.pop();
    if (chat.messages.length) generate(chat);
  }

  function updateSend() {
    const btn = $("#cs-send");
    const busy = Boolean(state.controller);
    btn.replaceChildren(busy ? el("span", { class: "stop-square" }) : iconEl("icon-long-arrow-alt-up-solid"));
    btn.setAttribute("aria-label", busy ? "Stop" : "Send");
    btn.disabled = !busy && !$("#cs-prompt").value.trim() && !state.pending.length;
  }
  function autosize() {
    const b = $("#cs-prompt");
    b.style.height = "auto";
    b.style.height = `${Math.min(b.scrollHeight, 180)}px`;
    b.style.overflowY = b.scrollHeight > 180 ? "auto" : "hidden";
  }
  function usePrompt(text) {
    const b = $("#cs-prompt"); b.value = text; autosize(); updateSend(); b.focus();
  }

  // ---------- attachments ----------
  function renderPending() {
    $("#cs-pending").replaceChildren(...state.pending.map((a, i) =>
      el("span", { class: "chat-file" },
        a.kind === "image" ? el("img", { src: a.url, alt: "" }) : iconEl("icon-paperclip-solid"),
        a.name,
        el("button", { type: "button", "aria-label": `Remove ${a.name}`, onclick: () => { state.pending.splice(i, 1); renderPending(); } }, "×"))));
    updateSend();
  }
  function shrink(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onerror = () => reject(new Error(`Couldn't read ${file.name}`));
      r.onload = () => {
        const img = new Image();
        img.onerror = () => reject(new Error(`${file.name} isn't a supported image`));
        img.onload = () => {
          const k = Math.min(1, MAX_IMAGE_SIDE / Math.max(img.width, img.height));
          const c = document.createElement("canvas");
          c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
          c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
          resolve(c.toDataURL("image/jpeg", 0.82));
        };
        img.src = r.result;
      };
      r.readAsDataURL(file);
    });
  }
  async function addFiles(files) {
    for (const f of files) {
      try {
        if (f.type.startsWith("image/")) {
          state.pending.push({ kind: "image", name: f.name, url: await shrink(f) });
        } else {
          const form = new FormData(); form.append("file", f);
          const res = await fetch("/api/extract", { method: "POST", body: form });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error?.message || res.statusText);
          state.pending.push({ kind: "doc", name: data.name, text: data.text });
          if (data.truncated) status(`${data.name} is long; only the first part will be sent.`);
        }
      } catch (e) { status(e.message, true); }
      renderPending();
    }
  }

  // ---------- voice ----------
  function setupMic() {
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const btn = $("#cs-mic");
    if (!Rec) { btn.hidden = true; return; }
    const codes = { Hindi: "hi-IN", Bengali: "bn-IN", Marathi: "mr-IN", Tamil: "ta-IN", Telugu: "te-IN", Gujarati: "gu-IN", Kannada: "kn-IN", Spanish: "es-ES", French: "fr-FR" };
    let rec = null;
    btn.addEventListener("click", () => {
      if (rec) { rec.stop(); return; }
      rec = new Rec();
      rec.lang = codes[state.settings.language] || (state.settings.jurisdiction === "India" ? "en-IN" : navigator.language);
      rec.interimResults = true;
      const base = $("#cs-prompt").value;
      rec.onresult = (e) => { $("#cs-prompt").value = (base ? `${base} ` : "") + [...e.results].map((r) => r[0].transcript).join(""); autosize(); updateSend(); };
      rec.onerror = (e) => { if (e.error !== "aborted") status(e.error === "not-allowed" ? "Allow microphone access to speak." : "Couldn't hear that. Try again.", true); };
      rec.onend = () => { rec = null; btn.classList.remove("rec"); };
      btn.classList.add("rec");
      rec.start();
    });
  }

  // ---------- misc ----------
  function download() {
    const chat = currentChat();
    if (!chat || !chat.messages.length) { status("Nothing to download yet."); return; }
    const lines = [`# ${chat.title}`, ""];
    for (const m of chat.messages) {
      if (m.role === "user") { lines.push("## You", ""); (m.docs || []).forEach((d) => lines.push(`[Attached: ${d.name}]`)); lines.push(m.text || "", ""); }
      else if (m.text) lines.push("## Assistant", "", m.text, "");
    }
    lines.push("---", CFG.disclaimer || "");
    const a = el("a", { href: URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/markdown" })), download: `${chat.title.replace(/[^\w\- ]+/g, "").slice(0, 40) || "chat"}.md` });
    document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }
  function openSide() { $("#chat-side").classList.add("open"); }
  function closeSide() { $("#chat-side").classList.remove("open"); }

  async function loadProviders() {
    try {
      const data = await (await fetch("/api/providers")).json();
      state.providers = data.providers;
      if (!provider()) state.settings.provider = data.default;
      const p = provider();
      if (p && !p.models.includes(state.settings.model)) state.settings.model = p.default_model;
      saveSettings();
    } catch (e) { status(`Couldn't reach the server: ${e.message}`, true); }
    renderSettings();
  }
  async function loadDatasets() {
    try {
      state.datasets = (await (await fetch("/api/datasets")).json()).datasets || [];
      const names = state.datasets.map((d) => d.name);
      state.settings.datasets = state.settings.datasets.filter((n) => names.includes(n));
      saveSettings();
    } catch { state.datasets = []; }
    renderDatasets();
  }

  function init() {
    if (!store.get("ca.accepted", false) && $("#cs-disclaimer").showModal) $("#cs-disclaimer").showModal();
    $("#cs-accept").addEventListener("click", () => { store.set("ca.accepted", true); $("#cs-disclaimer").close(); $("#cs-prompt").focus(); });
    $("#cs-disclaimer").addEventListener("cancel", (e) => e.preventDefault());

    const prompt = $("#cs-prompt");
    prompt.addEventListener("input", () => { autosize(); updateSend(); });
    prompt.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
    $("#cs-send").addEventListener("click", () => (state.controller ? state.controller.abort() : send()));
    $("#cs-new").addEventListener("click", () => { newChat(); closeSide(); });
    $("#cs-download").addEventListener("click", download);
    $("#cs-attach").addEventListener("click", () => $("#cs-file").click());
    $("#cs-file").addEventListener("change", (e) => { addFiles([...e.target.files]); e.target.value = ""; });
    $("#cs-toggle").addEventListener("click", () => ($("#chat-side").classList.contains("open") ? closeSide() : openSide()));

    const bind = (id, fn) => $(id).addEventListener("change", (e) => { fn(e.target.value); saveSettings(); renderSettings(); });
    bind("#cs-provider", (v) => { state.settings.provider = v; const p = provider(); if (p && !p.models.includes(state.settings.model)) state.settings.model = p.default_model; });
    bind("#cs-model", (v) => { state.settings.model = v; });
    bind("#cs-jurisdiction", (v) => { state.settings.jurisdiction = v; });
    bind("#cs-language", (v) => { state.settings.language = v; });

    setupMic();
    const q = new URLSearchParams(location.search).get("q");
    if (q) newChat(); else state.currentId = state.chats[0]?.id || null;
    if (!state.currentId && !state.draft) newChat();
    renderMessages(); renderHistory(); renderSettings(); updateSend();
    if (q) usePrompt(q.slice(0, 2000));
    if (STATIC) {
      document.querySelectorAll(".cs-block").forEach((b, i) => { if (i > 0) b.hidden = true; }); // settings need the server
    } else {
      loadProviders(); loadDatasets();
    }
    setInterval(() => { if (!state.controller) renderMessages(); }, 60000);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
