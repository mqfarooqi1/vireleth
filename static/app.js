/* ---------------------------------------------------------------------------
   Nexus AI — front-end logic (vanilla JS, no build step)
--------------------------------------------------------------------------- */
(function () {
  "use strict";

  const CFG = window.APP_CONFIG || { brand: "Nexus AI", modes: [], demo: true };
  const $ = (sel) => document.querySelector(sel);

  // --- element refs ---------------------------------------------------------
  const el = {
    messages: $("#messages"),
    suggestions: $("#suggestions"),
    modeList: $("#modeList"),
    composer: $("#composer"),
    input: $("#input"),
    sendBtn: $("#sendBtn"),
    brandName: $("#brandName"),
    brandTagline: $("#brandTagline"),
    brandLogo: $("#brandLogo"),
    headIcon: $("#headIcon"),
    headName: $("#headName"),
    headDesc: $("#headDesc"),
    statusPill: $("#statusPill"),
    newChatBtn: $("#newChatBtn"),
    menuBtn: $("#menuBtn"),
    sidebar: $("#sidebar"),
    installBtn: $("#installBtn"),
  };

  let deferredInstall = null; // captured beforeinstallprompt event

  // --- state ----------------------------------------------------------------
  let currentMode = (CFG.modes[0] && CFG.modes[0].id) || "general";
  let history = []; // [{role, content}]
  let busy = false;

  // --- init -----------------------------------------------------------------
  function init() {
    document.title = CFG.brand;
    el.brandName.textContent = CFG.brand;
    el.brandTagline.textContent = CFG.tagline || "";
    el.brandLogo.textContent = (CFG.brand || "N").charAt(0).toUpperCase();

    // Status pill
    if (CFG.demo) {
      el.statusPill.className = "status demo";
      el.statusPill.textContent = "● Demo mode — add a Claude API key to go live";
    } else {
      el.statusPill.className = "status live";
      el.statusPill.textContent = "● Live · " + (CFG.model || "Claude");
    }

    renderModes();
    selectMode(currentMode, true);

    el.composer.addEventListener("submit", onSubmit);
    el.input.addEventListener("input", autoGrow);
    el.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        el.composer.requestSubmit();
      }
    });
    el.newChatBtn.addEventListener("click", () => selectMode(currentMode, true));
    el.menuBtn.addEventListener("click", () => el.sidebar.classList.toggle("open"));

    setupPwa();
  }

  // --- installable app (PWA) -----------------------------------------------
  function setupPwa() {
    // Register the service worker (enables install + offline shell).
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
    // Show our own Install button when the browser says it's installable.
    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      deferredInstall = e;
      el.installBtn.hidden = false;
    });
    el.installBtn.addEventListener("click", async () => {
      if (!deferredInstall) return;
      deferredInstall.prompt();
      await deferredInstall.userChoice;
      deferredInstall = null;
      el.installBtn.hidden = true;
    });
    window.addEventListener("appinstalled", () => {
      el.installBtn.hidden = true;
    });
  }

  // --- mode picker ----------------------------------------------------------
  function renderModes() {
    el.modeList.innerHTML = "";
    CFG.modes.forEach((m) => {
      const btn = document.createElement("button");
      btn.className = "mode-btn" + (m.id === currentMode ? " active" : "");
      btn.dataset.mode = m.id;
      btn.innerHTML =
        `<span class="m-icon">${m.icon || "•"}</span>` +
        `<span><span class="m-name">${escapeHtml(m.name)}</span>` +
        `<span class="m-desc">${escapeHtml(m.desc || "")}</span></span>`;
      btn.addEventListener("click", () => {
        selectMode(m.id, true);
        el.sidebar.classList.remove("open");
      });
      el.modeList.appendChild(btn);
    });
  }

  function currentModeObj() {
    return CFG.modes.find((m) => m.id === currentMode) || CFG.modes[0] || {};
  }

  function selectMode(id, reset) {
    currentMode = id;
    const m = currentModeObj();
    document.querySelectorAll(".mode-btn").forEach((b) =>
      b.classList.toggle("active", b.dataset.mode === id)
    );
    el.headIcon.textContent = m.icon || "✨";
    el.headName.textContent = m.name || "";
    el.headDesc.textContent = m.desc || "";
    el.input.placeholder = m.placeholder || "Ask me anything…";
    if (reset) {
      history = [];
      renderWelcome();
    }
    renderSuggestions(m.suggestions || []);
  }

  // --- rendering ------------------------------------------------------------
  function renderWelcome() {
    const m = currentModeObj();
    el.messages.innerHTML =
      `<div class="messages-inner"><div class="welcome">` +
      `<h2>Hi, I'm <span>${escapeHtml(CFG.brand)}</span></h2>` +
      `<p>${escapeHtml(m.desc || "")} Pick a suggestion below or type your own message to start.</p>` +
      `</div></div>`;
  }

  function messagesInner() {
    let inner = el.messages.querySelector(".messages-inner");
    if (!inner) {
      el.messages.innerHTML = `<div class="messages-inner"></div>`;
      inner = el.messages.querySelector(".messages-inner");
    }
    return inner;
  }

  function clearWelcome() {
    const w = el.messages.querySelector(".welcome");
    if (w) w.remove();
  }

  function addMessage(role, htmlContent, tools) {
    clearWelcome();
    const inner = messagesInner();
    const wrap = document.createElement("div");
    wrap.className = "msg " + (role === "user" ? "user" : "bot");
    const avatar = role === "user" ? "You" : (CFG.brand || "N").charAt(0).toUpperCase();
    const name = role === "user" ? "You" : CFG.brand;
    let toolHtml = "";
    if (tools && tools.length) {
      const uniq = [...new Set(tools)];
      toolHtml =
        `<div class="tool-tags">` +
        uniq.map((t) => `<span class="tool-tag">🔧 ${escapeHtml(prettyTool(t))}</span>`).join("") +
        `</div>`;
    }
    wrap.innerHTML =
      `<div class="avatar">${escapeHtml(avatar)}</div>` +
      `<div class="body"><div class="name">${escapeHtml(name)}</div>` +
      `<div class="bubble">${htmlContent}</div>${toolHtml}</div>`;
    inner.appendChild(wrap);
    scrollDown();
    return wrap;
  }

  function addTyping() {
    clearWelcome();
    const inner = messagesInner();
    const wrap = document.createElement("div");
    wrap.className = "msg bot";
    wrap.innerHTML =
      `<div class="avatar">${escapeHtml((CFG.brand || "N").charAt(0).toUpperCase())}</div>` +
      `<div class="body"><div class="name">${escapeHtml(CFG.brand)}</div>` +
      `<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div></div>`;
    inner.appendChild(wrap);
    scrollDown();
    return wrap;
  }

  function renderSuggestions(list) {
    el.suggestions.innerHTML = "";
    list.forEach((s) => {
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.type = "button";
      chip.textContent = s;
      chip.addEventListener("click", () => {
        if (busy) return;
        el.input.value = s;
        el.composer.requestSubmit();
      });
      el.suggestions.appendChild(chip);
    });
  }

  // --- sending --------------------------------------------------------------
  async function onSubmit(e) {
    e.preventDefault();
    const text = el.input.value.trim();
    if (!text || busy) return;

    addMessage("user", renderMarkdown(text));
    history.push({ role: "user", content: text });
    el.input.value = "";
    autoGrow();
    setBusy(true);
    el.suggestions.innerHTML = "";

    const typing = addTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history, mode: currentMode }),
      });
      const data = await res.json();
      typing.remove();
      const reply = data.reply || "(no response)";
      addMessage("bot", renderMarkdown(reply), data.tools_used);
      history.push({ role: "assistant", content: reply });
      renderSuggestions(followUps());
    } catch (err) {
      typing.remove();
      addMessage("bot", renderMarkdown("⚠️ Something went wrong reaching the server."));
    } finally {
      setBusy(false);
      el.input.focus();
    }
  }

  function followUps() {
    // Simple "predictive" next-step suggestions after a reply.
    if (currentMode === "business") {
      return ["Tell me more about that", "How do we get started?", "Can I see an example?"];
    }
    if (currentMode === "domain") {
      return ["Show me an R example", "Explain that in more depth", "What are common pitfalls?"];
    }
    return ["Explain that more simply", "Give me an example", "What should I do next?"];
  }

  function setBusy(v) {
    busy = v;
    el.sendBtn.disabled = v;
  }

  // --- helpers --------------------------------------------------------------
  function autoGrow() {
    el.input.style.height = "auto";
    el.input.style.height = Math.min(el.input.scrollHeight, 180) + "px";
  }

  function scrollDown() {
    el.messages.scrollTop = el.messages.scrollHeight;
  }

  function prettyTool(name) {
    return (
      {
        calculator: "calculator",
        current_datetime: "clock",
        forecast_trend: "trend forecast",
      }[name] || name
    );
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Minimal, safe markdown -> HTML (escapes first, then adds formatting).
  function renderMarkdown(src) {
    // Extract fenced code blocks first so their contents aren't touched.
    const blocks = [];
    let text = String(src).replace(/```([\s\S]*?)```/g, (_, code) => {
      blocks.push(code.replace(/^\n/, ""));
      return " CODE" + (blocks.length - 1) + " ";
    });

    text = escapeHtml(text);

    // Inline code
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Bold / italic
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    // Links [text](url)
    text = text.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );

    // Build paragraphs & lists line by line
    const lines = text.split("\n");
    let html = "";
    let listType = null; // 'ul' | 'ol'
    let para = [];

    const flushPara = () => {
      if (para.length) {
        html += "<p>" + para.join("<br>") + "</p>";
        para = [];
      }
    };
    const closeList = () => {
      if (listType) {
        html += "</" + listType + ">";
        listType = null;
      }
    };

    for (let raw of lines) {
      const line = raw.trimEnd();
      const ul = line.match(/^\s*[-*]\s+(.*)$/);
      const ol = line.match(/^\s*\d+\.\s+(.*)$/);
      if (ul) {
        flushPara();
        if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
        html += "<li>" + ul[1] + "</li>";
      } else if (ol) {
        flushPara();
        if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
        html += "<li>" + ol[1] + "</li>";
      } else if (line.trim() === "") {
        flushPara();
        closeList();
      } else {
        closeList();
        para.push(line);
      }
    }
    flushPara();
    closeList();

    // Restore code blocks
    html = html.replace(/ CODE(\d+) /g, (_, i) => {
      return "<pre><code>" + escapeHtml(blocks[Number(i)]) + "</code></pre>";
    });

    return html;
  }

  init();
})();
