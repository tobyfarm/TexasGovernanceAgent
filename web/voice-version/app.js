// Texas Governance Agent — single-page UI
// Four screens: login, upload, thinking, home. Hash-routed.

const SCREENS = ["login", "upload", "thinking", "home"];

function showScreen(name) {
  if (!SCREENS.includes(name)) name = "login";
  for (const s of SCREENS) {
    const el = document.getElementById(`screen-${s}`);
    if (el) el.classList.toggle("active", s === name);
  }
}

window.addEventListener("hashchange", () => {
  showScreen(location.hash.slice(1) || "login");
});

window.addEventListener("DOMContentLoaded", () => {
  // Default screen
  showScreen(location.hash.slice(1) || "login");

  // ----- login -----
  const tryBtn = document.getElementById("btn-try");
  if (tryBtn) tryBtn.addEventListener("click", () => { location.hash = "upload"; });

  // ----- upload -----
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const uploadStatus = document.getElementById("upload-status");

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", (e) => {
      // Label triggers automatically; nothing extra needed
    });
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) handleFile(f);
    });
    fileInput.addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (f) handleFile(f);
    });
  }

  // ----- home / download buttons -----
  const dlBtn = document.getElementById("download-docx-btn");
  if (dlBtn) {
    dlBtn.addEventListener("click", () => {
      if (!window.RUN_ID) {
        alert("No report yet — run the demo first.");
        return;
      }
      const a = document.createElement("a");
      a.href = `/runs/${window.RUN_ID}.docx`;
      a.download = `board_prep_${window.RUN_ID}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  }
  const printBtn = document.getElementById("print-pdf-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      if (!window.FINAL_MD) {
        alert("No report yet — run the demo first.");
        return;
      }
      window.print();
    });
  }

  // ----- home / voice -----
  const voiceBtn = document.getElementById("voice-btn");
  if (voiceBtn) {
    voiceBtn.addEventListener("click", async () => {
      const status = document.getElementById("voice-status");
      if (status) status.textContent = "loading…";
      if (!window.startVoice) {
        try {
          await new Promise((res, rej) => {
            const s = document.createElement("script");
            s.src = "/static/voice.js";
            s.onload = res;
            s.onerror = rej;
            document.head.appendChild(s);
          });
        } catch (err) {
          if (status) status.textContent = "voice unavailable";
          alert("Voice unavailable: voice.js failed to load.");
          return;
        }
      }
      if (typeof window.startVoice === "function") {
        try {
          window.startVoice(window.RUN_ID);
          voiceBtn.classList.add("active");
          if (status) status.textContent = "listening…";
        } catch (err) {
          if (status) status.textContent = "error";
          alert("Voice error: " + (err && err.message ? err.message : err));
        }
      } else {
        if (status) status.textContent = "unavailable";
        alert("Voice unavailable");
      }
    });
  }

  // If we land on #home directly with FINAL_MD already set (e.g. dev), render it.
  if ((location.hash.slice(1) || "login") === "home" && window.FINAL_MD) {
    renderDoc(window.FINAL_MD);
    updateThreadFooter();
  }
});

// ---------- file handling ----------
function handleFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    setUploadStatus("Please choose a PDF.");
    return;
  }
  window.UPLOADED_FILENAME = file.name;
  setUploadStatus(`Uploading ${file.name}…`);
  // jump to thinking screen immediately so user sees feedback
  resetThinking();
  location.hash = "thinking";
  uploadAndStream(file).catch((err) => {
    appendThinking(`✗ Upload error: ${err && err.message ? err.message : err}`);
  });
}

function setUploadStatus(msg) {
  const el = document.getElementById("upload-status");
  if (el) el.textContent = msg || "";
}

// ---------- streaming ----------
async function uploadAndStream(file) {
  const fd = new FormData();
  fd.append("file", file);
  let res;
  try {
    res = await fetch("/analyze", { method: "POST", body: fd });
  } catch (err) {
    appendThinking(`✗ Network error: ${err.message}`);
    return;
  }
  if (!res.ok || !res.body) {
    appendThinking(`✗ Server returned ${res.status}`);
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      processChunk(chunk);
    }
  }
  // any trailing chunk without double newline
  if (buf.trim()) processChunk(buf);
}

function processChunk(chunk) {
  // SSE chunk: lines starting with "event: " and "data: "
  const eventMatch = chunk.match(/^event:\s*(.+)$/m);
  const dataMatch = chunk.match(/^data:\s*([\s\S]+)$/m);
  if (!dataMatch) return;
  const type = eventMatch ? eventMatch[1].trim() : "message";
  let data = {};
  try { data = JSON.parse(dataMatch[1]); } catch (e) { data = { raw: dataMatch[1] }; }
  handleEvent(type, data);
}

function handleEvent(type, data) {
  if (type === "stage_start") {
    setPillState(data.stage, "active");
    appendThinking(`▸ ${data.label || data.stage}`);
  } else if (type === "thinking") {
    appendThinking(`  ${data.text || ""}`);
  } else if (type === "partial") {
    appendPartial(data.markdown_delta || "");
  } else if (type === "stage_complete") {
    setPillState(data.stage, "done");
    appendThinking(`✓ ${data.summary || data.stage + " complete"}`);
  } else if (type === "flag") {
    appendThinking(`  [${(data.severity || "INFO").toUpperCase()}] ${data.summary || ""}`);
  } else if (type === "final") {
    window.RUN_ID = data.run_id;
    window.FINAL_MD = data.markdown || "";
    appendThinking(`✓ Final pre-read ready (${(window.FINAL_MD.length || 0).toLocaleString()} chars)`);
    setTimeout(() => {
      renderDoc(window.FINAL_MD);
      updateThreadFooter();
      location.hash = "home";
    }, 600);
  } else if (type === "error") {
    appendThinking(`✗ ERROR: ${data.message || "unknown"}`);
  } else {
    appendThinking(`  · ${type}: ${JSON.stringify(data).slice(0, 160)}`);
  }
}

// ---------- thinking screen helpers ----------
function resetThinking() {
  const log = document.getElementById("thinking-log");
  if (log) log.textContent = "";
  const partial = document.getElementById("partial-md");
  if (partial) partial.textContent = "";
  for (const stage of ["generator", "legal", "redteam"]) {
    setPillState(stage, "idle");
  }
}

function setPillState(stage, state) {
  if (!stage) return;
  const pill = document.querySelector(`.pill[data-stage="${stage}"]`);
  if (!pill) return;
  pill.classList.remove("active", "done");
  if (state === "active") pill.classList.add("active");
  if (state === "done") pill.classList.add("done");
}

function appendThinking(line) {
  const log = document.getElementById("thinking-log");
  if (!log) return;
  log.textContent += (log.textContent ? "\n" : "") + line;
  log.scrollTop = log.scrollHeight;
}

function appendPartial(delta) {
  const el = document.getElementById("partial-md");
  if (!el) return;
  el.textContent += delta;
  // keep last ~1200 chars to avoid bloat
  if (el.textContent.length > 1500) {
    el.textContent = el.textContent.slice(-1200);
  }
  el.scrollTop = el.scrollHeight;
}

// ---------- home rendering ----------
function renderDoc(md) {
  const el = document.getElementById("doc-card");
  if (!el) return;
  if (!md) {
    el.innerHTML = `<div class="doc-empty mono">No document yet — run the demo to populate.</div>`;
    return;
  }
  let html;
  try {
    if (window.marked && typeof window.marked.parse === "function") {
      html = window.marked.parse(md);
    } else {
      html = `<pre class="mono">${escapeHtml(md)}</pre>`;
    }
  } catch (e) {
    html = `<pre class="mono">${escapeHtml(md)}</pre>`;
  }
  el.innerHTML = html;
  // Annotate flag blockquotes
  el.querySelectorAll("blockquote").forEach((bq) => {
    const t = bq.textContent || "";
    if (/RED FLAG/i.test(t)) bq.classList.add("flag-red");
    else if (/WATCH/i.test(t)) bq.classList.add("flag-orange");
    else if (/POSITIVE/i.test(t)) bq.classList.add("flag-green");
  });
}

function updateThreadFooter() {
  const el = document.getElementById("thread-footer");
  if (!el) return;
  el.textContent = `Q/A Context: ${window.UPLOADED_FILENAME || "current document"}`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Expose a tiny dev hook so we can manually test event handling without backend.
// In console: __fakeRun()  then __fake("thinking", {text: "..."})
window.__fake = (type, data) => handleEvent(type, data || {});
window.__fakeRun = () => {
  resetThinking();
  location.hash = "thinking";
  const seq = [
    ["stage_start", { stage: "generator", label: "Generator drafting pre-read" }],
    ["thinking", { text: "Parsing 142-page packet…" }],
    ["thinking", { text: "Indexed 11 agenda items" }],
    ["partial", { markdown_delta: "# Brock ISD Pre-Read\n\n## Executive Summary\n\n" }],
    ["stage_complete", { stage: "generator", summary: "Generator drafted 11 items" }],
    ["stage_start", { stage: "legal", label: "Legal verification" }],
    ["thinking", { text: "Checking TEC §11.151 citations…" }],
    ["flag", { severity: "watch", summary: "Item 6 cites unverified TGC section" }],
    ["stage_complete", { stage: "legal", summary: "9/11 citations verified" }],
    ["stage_start", { stage: "redteam", label: "Strategic red-team" }],
    ["flag", { severity: "red flag", summary: "Item 8 delegates without oversight" }],
    ["stage_complete", { stage: "redteam", summary: "3 red flags, 2 watch, 1 positive" }],
    ["final", {
      run_id: "demo-run",
      markdown: `# Brock ISD — April 13, 2026 Pre-Read\n\n## Executive Summary\n\n| # | Item | Flag |\n|---|---|---|\n| 1 | Budget amendment | WATCH |\n| 2 | Bond resolution | RED FLAG |\n\n## Item 1 — Budget amendment\n\n**What is happening:** Routine reallocation.\n\n> WATCH: Reallocation pulls from contingency without restoring it.\n\n## Item 2 — Bond resolution\n\n> RED FLAG: Tariff exposure not disclosed in cost memo.\n\n> POSITIVE: Cadence of quarterly review is documented.\n` }],
  ];
  let i = 0;
  const tick = () => {
    if (i >= seq.length) return;
    const [type, data] = seq[i++];
    handleEvent(type, data);
    setTimeout(tick, 350);
  };
  tick();
};
