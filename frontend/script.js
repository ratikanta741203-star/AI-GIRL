/**
 * Prity AI – Frontend Logic
 * Supports Chat, Tasks, Memory, Settings, Android App Download, Voice (STT/TTS), and Avatar
 */

const API = window.location.origin;

// DOM Elements
const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("message-input");
const btnSend = document.getElementById("btn-send");
const btnMic = document.getElementById("btn-mic");
const btnStopSpeaking = document.getElementById("btn-stop-speaking");
const statusEl = document.getElementById("status-indicator");
const avatarFace = document.getElementById("avatar-face");
const avatarCaption = document.getElementById("avatar-caption");

const attachmentList = document.getElementById("attachment-list");
const attachmentButtons = [
  document.getElementById("btn-attach-file"),
  document.getElementById("btn-attach-image"),
  document.getElementById("btn-attach-audio"),
];
const attachmentInputs = [
  document.getElementById("file-input"),
  document.getElementById("image-input"),
  document.getElementById("audio-input"),
];

// App State
let activeTab = "home";
let isListening = false;
let recognition = null;
let isSpeaking = false;
let speechMuted = false;
let selectedFiles = [];
let isSending = false;

// Voice / Speech State (Optimized for sweet AI Girl voice)
let availableVoices = [];
let selectedVoiceURI = localStorage.getItem("ai_girl_voice_uri") || "";
let voicePitch = parseFloat(localStorage.getItem("ai_girl_voice_pitch")) || 1.20;
let voiceRate = parseFloat(localStorage.getItem("ai_girl_voice_rate")) || 1.0;
let autoSpeakEnabled = localStorage.getItem("ai_girl_voice_auto") !== "false";

const MAX_FILE_BYTES = 8 * 1024 * 1024;
const MAX_TOTAL_FILE_BYTES = 12 * 1024 * 1024;
const MAX_FILES = 4;

// ── Toast Helper ─────────────────────────────────────────
function showToast(msg, duration = 2500) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, duration);
}

// ── Tab Switcher Logic ───────────────────────────────────
function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll(".tab-view").forEach((view) => {
    view.classList.remove("active");
  });
  
  const targetView = document.getElementById(`view-${tabName}`);
  if (targetView) {
    targetView.classList.add("active");
  }

  document.querySelectorAll(".nav-item").forEach((item) => {
    if (item.dataset.tab === tabName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  if (tabName === "tasks") {
    loadTasks();
  } else if (tabName === "memory") {
    loadMemory();
  } else if (tabName === "settings") {
    loadSettings();
  }
}

// Global Nav Triggers
document.querySelectorAll(".nav-item, .nav-trigger, #btn-settings-header").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    if (tab) switchTab(tab);
  });
});

// ── Download App Modal ──────────────────────────────────
const downloadModal = document.getElementById("download-modal");
const btnHeaderDownload = document.getElementById("btn-header-download");
const btnHeroDownload = document.getElementById("btn-hero-download");
const btnCloseDownload = document.getElementById("btn-close-download");

function openDownloadModal() {
  if (downloadModal) downloadModal.classList.remove("hidden");
}

function closeDownloadModal() {
  if (downloadModal) downloadModal.classList.add("hidden");
}

if (btnHeaderDownload) btnHeaderDownload.addEventListener("click", openDownloadModal);
if (btnHeroDownload) btnHeroDownload.addEventListener("click", openDownloadModal);
if (btnCloseDownload) btnCloseDownload.addEventListener("click", closeDownloadModal);

if (downloadModal) {
  downloadModal.addEventListener("click", (e) => {
    if (e.target === downloadModal) closeDownloadModal();
  });
}

// ── Attachments ──────────────────────────────────────────
function formatFileSize(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderAttachments() {
  if (!attachmentList) return;
  attachmentList.replaceChildren();
  attachmentList.hidden = selectedFiles.length === 0;

  selectedFiles.forEach((file, index) => {
    const chip = document.createElement("div");
    chip.className = "attachment-chip";

    const label = document.createElement("span");
    label.className = "attachment-name";
    label.textContent = `${file.name} (${formatFileSize(file.size)})`;

    const remove = document.createElement("button");
    remove.className = "attachment-remove";
    remove.type = "button";
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      selectedFiles.splice(index, 1);
      renderAttachments();
    });

    chip.append(label, remove);
    attachmentList.appendChild(chip);
  });
}

function addFiles(fileList) {
  const incoming = Array.from(fileList);
  const errors = [];

  for (const file of incoming) {
    if (selectedFiles.length >= MAX_FILES) {
      errors.push(`Maximum ${MAX_FILES} files allowed.`);
      break;
    }
    if (file.size > MAX_FILE_BYTES) {
      errors.push(`${file.name} exceeds 8MB limit.`);
      continue;
    }
    const currentTotal = selectedFiles.reduce((t, f) => t + f.size, 0);
    if (currentTotal + file.size > MAX_TOTAL_FILE_BYTES) {
      errors.push("Total file size exceeds 12MB limit.");
      continue;
    }
    selectedFiles.push(file);
  }

  renderAttachments();
  if (errors.length) addMessage("assistant", errors.join(" "));
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const res = String(reader.result || "");
      const sep = res.indexOf(",");
      if (sep < 0) {
        reject(new Error(`Could not read ${file.name}`));
        return;
      }
      resolve({
        name: file.name,
        media_type: file.type || "application/octet-stream",
        data: res.slice(sep + 1),
      });
    };
    reader.onerror = () => reject(new Error(`Error reading ${file.name}`));
    reader.readAsDataURL(file);
  });
}

// ── Status Helper ────────────────────────────────────────
function setStatus(state, label) {
  if (statusEl) {
    statusEl.className = `status ${state}`;
    const lbl = statusEl.querySelector(".label");
    if (lbl) lbl.textContent = label;
  }
  if (avatarFace) avatarFace.className = `avatar-photo-wrap ${state}`;
  if (avatarCaption) {
    if (state === "listening") avatarCaption.textContent = "Listening…";
    else if (state === "thinking") avatarCaption.textContent = "Thinking…";
    else if (state === "speaking") avatarCaption.textContent = "Speaking…";
    else avatarCaption.textContent = 'Say “Hello Prity”';
  }
}

function updateSpeechButton() {
  if (!btnStopSpeaking) return;
  const icon = btnStopSpeaking.querySelector(".stop-speaking-icon");
  const label = btnStopSpeaking.querySelector(".stop-speaking-label");
  btnStopSpeaking.setAttribute("aria-pressed", String(speechMuted));
  if (icon) icon.textContent = speechMuted ? "🔇" : "🔊";
  if (label) label.textContent = speechMuted ? "Voice off" : "Voice on";
}

if (btnStopSpeaking) {
  btnStopSpeaking.addEventListener("click", () => {
    speechMuted = !speechMuted;
    if (speechMuted) {
      window.speechSynthesis?.cancel();
      isSpeaking = false;
      setStatus("idle", "Voice off");
    }
    updateSpeechButton();
  });
}

// ── Multi-Color Code Syntax Highlighter & Markdown Renderer ───────
function highlightCode(code, lang = "") {
  lang = (lang || "").toLowerCase().trim();
  let text = escapeHtml(code);

  const keywords = [
    "def", "class", "import", "from", "return", "if", "elif", "else", "for", "while",
    "try", "except", "finally", "with", "as", "pass", "break", "continue", "lambda",
    "yield", "global", "nonlocal", "async", "await", "function", "const", "let", "var",
    "new", "delete", "typeof", "instanceof", "switch", "case", "default", "throw",
    "catch", "package", "public", "private", "protected", "static", "final", "abstract",
    "interface", "implements", "extends", "struct", "enum", "fn", "mut", "pub",
    "impl", "match", "select", "where", "insert", "update", "join",
    "left", "right", "inner", "outer", "group", "order", "by", "having", "limit",
    "create", "table", "alter", "drop", "index", "primary", "key", "foreign"
  ];
  const booleans = ["true", "false", "null", "undefined", "none", "nan", "nil", "True", "False", "None"];

  // 1. Protect & highlight strings
  const stringStore = [];
  text = text.replace(/(&quot;[\s\S]*?&quot;|&#039;[\s\S]*?&#039;|`[\s\S]*?`|"[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g, (match) => {
    const id = `___STR_${stringStore.length}___`;
    stringStore.push(`<span class="tok-str">${match}</span>`);
    return id;
  });

  // 2. Protect & highlight comments
  const commentStore = [];
  text = text.replace(/(\/\*[\s\S]*?\*\/|\/\/[^\n]*|#[^\n]*)/g, (match) => {
    const id = `___COM_${commentStore.length}___`;
    commentStore.push(`<span class="tok-comment">${match}</span>`);
    return id;
  });

  // 3. Numbers
  text = text.replace(/\b(0x[a-fA-F0-9]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b/g, '<span class="tok-num">$1</span>');

  // 4. Booleans / Null
  const boolRegex = new RegExp(`\\b(${booleans.join("|")})\\b`, "g");
  text = text.replace(boolRegex, '<span class="tok-bool">$1</span>');

  // 5. Keywords
  const kwRegex = new RegExp(`\\b(${keywords.join("|")})\\b`, "g");
  text = text.replace(kwRegex, '<span class="tok-kw">$1</span>');

  // 6. Function calls / declarations: name(...)
  text = text.replace(/\b([a-zA-Z_]\w*)\s*(?=\()/g, '<span class="tok-func">$1</span>');

  // 7. Types / Classes: Capitalized identifiers
  text = text.replace(/\b([A-Z][a-zA-Z0-9_]*)\b/g, '<span class="tok-type">$1</span>');

  // 8. Operators
  text = text.replace(/(&amp;&amp;|\|\||===|!==|==|!=|&lt;=|&gt;=|=&gt;|-&gt;|\+=|-=|\*=|\/=|&lt;|&gt;|\+|\-|\*|\/|=)/g, '<span class="tok-op">$1</span>');

  // Restore protected comments and strings
  commentStore.forEach((c, idx) => {
    text = text.replace(`___COM_${idx}___`, c);
  });
  stringStore.forEach((s, idx) => {
    text = text.replace(`___STR_${idx}___`, s);
  });

  return text;
}

function renderMarkdown(rawText) {
  if (!rawText) return "";

  // 1. Process File Download Cards [FILE_CARD:type:url:title:desc]
  let text = rawText.replace(/\[FILE_CARD:([^:]+):([^:]+):([^:]+):([^\]]+)\]/g, (match, type, url, title, desc) => {
    let icon = "📄";
    let typeName = "Document";
    if (type === "pptx") { icon = "📽️"; typeName = "PowerPoint"; }
    else if (type === "xlsx") { icon = "📊"; typeName = "Excel Spreadsheet"; }
    else if (type === "docx") { icon = "📝"; typeName = "Word Document"; }

    return `
      <div class="file-download-card">
        <div class="file-card-info">
          <div class="file-card-icon">${icon}</div>
          <div class="file-card-texts">
            <h4>${escapeHtml(title)}</h4>
            <p>${escapeHtml(desc || typeName)}</p>
          </div>
        </div>
        <a href="${escapeHtml(url)}" class="file-card-btn" download>
          <span>📥 Download</span>
        </a>
      </div>
    `;
  });

  // 2. Process Code Blocks with Syntax Highlighting
  const codeBlocks = [];
  text = text.replace(/```([a-zA-Z0-9_+\-#]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const cleanLang = lang.trim() || "code";
    const highlighted = highlightCode(code.trimEnd(), cleanLang);
    const id = `___CODEBLOCK_${codeBlocks.length}___`;
    
    const blockHtml = `
      <div class="code-block-wrap">
        <div class="code-top-bar">
          <span class="code-lang-tag">${escapeHtml(cleanLang)}</span>
          <button class="btn-copy-code" type="button" data-code="${encodeURIComponent(code)}">
            <span>📋 Copy</span>
          </button>
        </div>
        <pre class="code-pre"><code>${highlighted}</code></pre>
      </div>
    `;
    codeBlocks.push(blockHtml);
    return id;
  });

  // 3. Process Markdown Tables
  text = text.replace(/((?:\|[^\n]+\|\r?\n){2,})/g, (tableMatch) => {
    const lines = tableMatch.trim().split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length < 2) return tableMatch;

    let headers = [];
    let rows = [];

    lines.forEach((line, idx) => {
      if (line.includes("---")) return; // skip delimiter
      const cells = line.split("|").slice(1, -1).map((c) => c.trim());
      if (idx === 0) headers = cells;
      else if (cells.length) rows.push(cells);
    });

    if (!headers.length) return tableMatch;

    let tableHtml = `<div class="chat-table-wrap"><table class="chat-table"><thead><tr>`;
    headers.forEach((h) => { tableHtml += `<th>${escapeHtml(h)}</th>`; });
    tableHtml += `</tr></thead><tbody>`;
    rows.forEach((row) => {
      tableHtml += `<tr>`;
      row.forEach((cell) => { tableHtml += `<td>${escapeHtml(cell)}</td>`; });
      tableHtml += `</tr>`;
    });
    tableHtml += `</tbody></table></div>`;
    return tableHtml;
  });

  // 4. Headers
  text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // 5. Blockquotes
  text = text.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

  // 6. Bold & Italics
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // 7. Inline Code
  text = text.replace(/`([^`]+)`/g, '<inline-code>$1</inline-code>');

  // 8. Bullet Lists
  text = text.replace(/^\s*[\-\*•]\s+(.*)$/gim, '<li>$1</li>');
  text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  // 9. Paragraphs and line breaks
  text = text.replace(/\n\n+/g, '</p><p>');
  text = text.replace(/\n/g, '<br/>');

  // Wrap in root paragraph
  text = `<p>${text}</p>`;

  // Restore Code Blocks
  codeBlocks.forEach((cb, idx) => {
    text = text.replace(`___CODEBLOCK_${idx}___`, cb);
  });

  return text;
}

// ── Chat Messages ────────────────────────────────────────
function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  
  if (role === "assistant") {
    div.innerHTML = `<div class="bubble clay">${renderMarkdown(text)}</div>`;
    
    // Attach Copy Code Listeners
    div.querySelectorAll(".btn-copy-code").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const rawCode = decodeURIComponent(btn.dataset.code || "");
        try {
          await navigator.clipboard.writeText(rawCode);
          btn.innerHTML = `<span>✓ Copied!</span>`;
          btn.classList.add("copied");
          setTimeout(() => {
            btn.innerHTML = `<span>📋 Copy</span>`;
            btn.classList.remove("copied");
          }, 2000);
        } catch (err) {
          showToast("Copied to clipboard!");
        }
      });
    });
  } else {
    div.innerHTML = `<div class="bubble clay"></div>`;
    div.querySelector(".bubble").textContent = text;
  }

  if (messagesEl) {
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  return div;
}

function addTyping() {
  const div = document.createElement("div");
  div.className = "msg assistant typing";
  div.innerHTML = `<div class="bubble clay">Thinking…</div>`;
  if (messagesEl) {
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  return div;
}

async function sendMessage(text) {
  text = (text || (inputEl ? inputEl.value : "")).trim();
  if ((!text && selectedFiles.length === 0) || isSending) return;

  if (activeTab !== "chat" && activeTab !== "home") {
    switchTab("chat");
  }

  if (inputEl) inputEl.value = "";
  const filesToSend = selectedFiles.slice();
  const displayed = [text, ...filesToSend.map((f) => `📎 ${f.name}`)].filter(Boolean).join("\n");

  addMessage("user", displayed);
  setStatus("thinking", "Thinking");
  const typing = addTyping();
  isSending = true;
  if (btnSend) btnSend.disabled = true;

  try {
    const attachments = await Promise.all(filesToSend.map(readFileAsBase64));
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, attachments }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    if (!data.reply) throw new Error("Empty response received");

    typing.remove();
    addMessage("assistant", data.reply);
    selectedFiles = selectedFiles.filter((f) => !filesToSend.includes(f));
    renderAttachments();
    setStatus(data.expression || "idle", "Ready");
    speak(data.reply);
  } catch (err) {
    typing.remove();
    addMessage("assistant", err.message || "Failed to send message.");
    setStatus("error", "Error");
  } finally {
    isSending = false;
    if (btnSend) btnSend.disabled = false;
  }
}

// ── Voice TTS & STT (AI GIRL VOICE ENGINE) ──────────────────
const GIRL_VOICE_KEYWORDS = [
  "jenny", "aria", "samantha", "victoria", "zira", "susan",
  "karen", "moira", "tessa", "heera", "hazel", "catherine",
  "fiona", "veena", "serena", "clara", "amy", "emma", "ava",
  "sophia", "olivia", "mia", "isabella", "female", "girl", "woman",
  "google uk english female", "google us english", "microsoft jenny",
  "microsoft aria", "microsoft zira", "natural"
];

function getGirlVoiceScore(voice) {
  if (!voice) return 0;
  const name = voice.name.toLowerCase();
  const lang = (voice.lang || "").toLowerCase();
  let score = 0;

  // Ultra-preferred natural AI girl voices
  if (name.includes("jenny") || name.includes("aria") || name.includes("samantha")) score += 50;
  if (name.includes("zira") || name.includes("victoria") || name.includes("heera")) score += 40;
  if (name.includes("female") || name.includes("girl") || name.includes("woman")) score += 30;
  if (GIRL_VOICE_KEYWORDS.some((kw) => name.includes(kw))) score += 20;

  // Bonus for English & Natural
  if (name.includes("natural") || name.includes("online")) score += 10;
  if (lang.startsWith("en")) score += 5;

  // Penalty for known male voice names
  const maleKeywords = ["guy", "david", "mark", "george", "richard", "james", "male", "man", "boy", "stefan", "ravi"];
  if (maleKeywords.some((kw) => name.includes(kw))) score -= 100;

  return score;
}

function isRecommendedAiGirlVoice(voice) {
  return getGirlVoiceScore(voice) > 10;
}

function getSelectedVoice() {
  if (!availableVoices.length) {
    if (window.speechSynthesis) availableVoices = window.speechSynthesis.getVoices() || [];
  }
  if (!availableVoices.length) return null;

  if (selectedVoiceURI) {
    const matched = availableVoices.find((v) => v.voiceURI === selectedVoiceURI || v.name === selectedVoiceURI);
    if (matched && getGirlVoiceScore(matched) > 0) return matched;
  }

  // Pick highest scoring AI Girl voice
  const sortedByGirlScore = [...availableVoices].sort((a, b) => getGirlVoiceScore(b) - getGirlVoiceScore(a));
  if (sortedByGirlScore.length && getGirlVoiceScore(sortedByGirlScore[0]) > 0) {
    return sortedByGirlScore[0];
  }

  // Fallback: English voice or first voice
  const englishVoice = availableVoices.find((v) => v.lang.startsWith("en"));
  return englishVoice || availableVoices[0] || null;
}

function updatePitchBadge(val) {
  const badge = document.getElementById("val-pitch");
  if (!badge) return;
  const num = parseFloat(val);
  let label = "Natural";
  if (num < 0.85) label = "Deep";
  else if (num < 1.05) label = "Natural";
  else if (num < 1.25) label = "Cute / Sweet ✨";
  else label = "Anime / High ✨";
  badge.textContent = `${num.toFixed(2)}x (${label})`;
}

function updateRateBadge(val) {
  const badge = document.getElementById("val-rate");
  if (!badge) return;
  const num = parseFloat(val);
  let label = "Normal";
  if (num < 0.85) label = "Slow";
  else if (num < 1.15) label = "Normal";
  else label = "Fast";
  badge.textContent = `${num.toFixed(2)}x (${label})`;
}

function populateVoiceList() {
  if (!window.speechSynthesis) return;
  availableVoices = window.speechSynthesis.getVoices() || [];
  const voiceSelect = document.getElementById("cfg-voice-view");
  if (!voiceSelect) return;

  if (availableVoices.length === 0) {
    voiceSelect.innerHTML = `<option value="">System voices loading…</option>`;
    return;
  }

  // Sort: Recommended female/sweet voices first, then others
  const sorted = [...availableVoices].sort((a, b) => {
    const scoreA = getGirlVoiceScore(a);
    const scoreB = getGirlVoiceScore(b);
    if (scoreA !== scoreB) return scoreB - scoreA;
    return a.name.localeCompare(b.name);
  });

  voiceSelect.innerHTML = "";
  const recommendedGroup = document.createElement("optgroup");
  recommendedGroup.label = "✨ Recommended AI Girl Voices";
  const otherGroup = document.createElement("optgroup");
  otherGroup.label = "🌐 Other System Voices";

  const currentSelected = getSelectedVoice();

  sorted.forEach((voice) => {
    const opt = document.createElement("option");
    opt.value = voice.voiceURI || voice.name;
    const isRec = isRecommendedAiGirlVoice(voice);
    opt.textContent = `${isRec ? "✨ " : ""}${voice.name} (${voice.lang})${voice.default ? " — Default" : ""}`;
    
    if (currentSelected && (voice.voiceURI === currentSelected.voiceURI || voice.name === currentSelected.name)) {
      opt.selected = true;
    }

    if (isRec) {
      recommendedGroup.appendChild(opt);
    } else {
      otherGroup.appendChild(opt);
    }
  });

  if (recommendedGroup.children.length > 0) voiceSelect.appendChild(recommendedGroup);
  if (otherGroup.children.length > 0) voiceSelect.appendChild(otherGroup);
}

// Initial populate + handle voiceschanged async event
if (typeof window !== "undefined" && window.speechSynthesis) {
  populateVoiceList();
  if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = populateVoiceList;
  }
}

function speak(text, force = false) {
  if (!window.speechSynthesis) return;
  if (!force && (speechMuted || !autoSpeakEnabled)) return;
  if (!text) return;

  // Clean markdown links/code formatting slightly for natural speech
  const speechText = text
    .replace(/```[\s\S]*?```/g, " [code snippet omitted] ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/[*_~#]/g, "")
    .trim();

  if (!speechText) return;

  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(speechText);
  u.pitch = voicePitch;
  u.rate = voiceRate;

  const chosenVoice = getSelectedVoice();
  if (chosenVoice) {
    u.voice = chosenVoice;
    u.lang = chosenVoice.lang;
  } else {
    u.lang = "en-US";
  }

  u.onstart = () => {
    isSpeaking = true;
    setStatus("speaking", "Speaking");
  };
  u.onend = () => {
    isSpeaking = false;
    if (!speechMuted) setStatus("idle", "Ready");
  };
  u.onerror = () => {
    isSpeaking = false;
    if (!speechMuted) setStatus("idle", "Ready");
  };

  speechSynthesis.speak(u);
}

function testVoice() {
  const chosenVoice = getSelectedVoice();
  const voiceName = chosenVoice ? chosenVoice.name : "Default AI Girl Voice";
  showToast(`Testing AI Girl voice: ${voiceName}`);
  speak("Hi there! I am Prity, your personal AI girl. I am so happy to chat with you! How can I help you today?", true);
}

function initVoiceControls() {
  const pitchSlider = document.getElementById("cfg-voice-pitch");
  const rateSlider = document.getElementById("cfg-voice-rate");
  const voiceSelect = document.getElementById("cfg-voice-view");
  const autoCheck = document.getElementById("cfg-voice-auto-view");
  const btnTest = document.getElementById("btn-test-voice");

  if (pitchSlider) {
    pitchSlider.value = String(voicePitch);
    updatePitchBadge(voicePitch);
    pitchSlider.addEventListener("input", (e) => {
      voicePitch = parseFloat(e.target.value);
      updatePitchBadge(voicePitch);
      localStorage.setItem("ai_girl_voice_pitch", String(voicePitch));
    });
  }

  if (rateSlider) {
    rateSlider.value = String(voiceRate);
    updateRateBadge(voiceRate);
    rateSlider.addEventListener("input", (e) => {
      voiceRate = parseFloat(e.target.value);
      updateRateBadge(voiceRate);
      localStorage.setItem("ai_girl_voice_rate", String(voiceRate));
    });
  }

  if (voiceSelect) {
    voiceSelect.addEventListener("change", (e) => {
      selectedVoiceURI = e.target.value;
      localStorage.setItem("ai_girl_voice_uri", selectedVoiceURI);
      const chosen = getSelectedVoice();
      if (chosen) showToast(`Selected: ${chosen.name}`);
    });
  }

  if (autoCheck) {
    autoCheck.checked = autoSpeakEnabled;
    autoCheck.addEventListener("change", (e) => {
      autoSpeakEnabled = e.target.checked;
      localStorage.setItem("ai_girl_voice_auto", String(autoSpeakEnabled));
    });
  }

  if (btnTest) {
    btnTest.addEventListener("click", () => {
      testVoice();
    });
  }
}

function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  recognition = new SR();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    isListening = true;
    if (btnMic) btnMic.classList.add("active");
    setStatus("listening", "Listening");
  };
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript.trim();
    if (transcript) {
      if (inputEl) inputEl.value = transcript;
      sendMessage(transcript);
    }
  };
  recognition.onerror = () => {
    isListening = false;
    if (btnMic) btnMic.classList.remove("active");
    setStatus("idle", "Ready");
  };
  recognition.onend = () => {
    isListening = false;
    if (btnMic) btnMic.classList.remove("active");
    if (!isSpeaking) setStatus("idle", "Ready");
  };
}

if (btnMic) {
  btnMic.addEventListener("click", () => {
    if (!recognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }
    if (isListening) recognition.stop();
    else recognition.start();
  });
}

// Event Listeners for Input Bar
if (btnSend) btnSend.addEventListener("click", () => sendMessage());
if (inputEl) {
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

document.getElementById("btn-attach-file")?.addEventListener("click", () => document.getElementById("file-input")?.click());
document.getElementById("btn-attach-image")?.addEventListener("click", () => document.getElementById("image-input")?.click());
document.getElementById("btn-attach-audio")?.addEventListener("click", () => document.getElementById("audio-input")?.click());

attachmentInputs.forEach((input) => {
  input?.addEventListener("change", () => {
    addFiles(input.files);
    input.value = "";
  });
});

// Quick Actions
document.querySelectorAll(".quick-actions button").forEach((btn) => {
  btn.addEventListener("click", () => {
    const act = btn.dataset.action;
    if (act === "plan") sendMessage("Plan my day");
    else if (act === "tasks") switchTab("tasks");
    else if (act === "motivate") sendMessage("Give me a short motivational message");
  });
});

// ── TASK MANAGER ─────────────────────────────────────────
let tasksCache = [];
let currentTaskFilter = "all";

async function loadTasks() {
  const container = document.getElementById("tasks-list");
  if (!container) return;
  container.innerHTML = `<div class="empty-state">Loading tasks…</div>`;

  try {
    const res = await fetch(`${API}/api/tasks`);
    if (!res.ok) throw new Error("Could not fetch tasks");
    tasksCache = await res.json();
    renderTasks();
    updateDashboardCounts();
  } catch (err) {
    container.innerHTML = `<div class="empty-state">Failed to load tasks.</div>`;
  }
}

function renderTasks() {
  const container = document.getElementById("tasks-list");
  if (!container) return;

  let filtered = tasksCache;
  if (currentTaskFilter === "pending") filtered = tasksCache.filter((t) => t.status !== "completed");
  else if (currentTaskFilter === "completed") filtered = tasksCache.filter((t) => t.status === "completed");

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">No tasks found.</div>`;
    return;
  }

  container.innerHTML = "";
  filtered.forEach((task) => {
    const item = document.createElement("div");
    item.className = `task-item ${task.status === "completed" ? "completed" : ""}`;

    let prioLabel = "Normal";
    if (task.priority === 1) prioLabel = "⭐ High";
    else if (task.priority === 2) prioLabel = "🔥 Urgent";

    item.innerHTML = `
      <div class="task-left">
        <input type="checkbox" class="task-checkbox" ${task.status === "completed" ? "checked" : ""} data-id="${task.id}" />
        <div>
          <div class="task-title">${escapeHtml(task.title)}</div>
          ${task.description ? `<div class="task-desc">${escapeHtml(task.description)}</div>` : ""}
        </div>
      </div>
      <div class="task-right" style="display:flex; align-items:center; gap:10px;">
        <span class="prio-badge prio-${task.priority}">${prioLabel}</span>
        <button class="clay-btn btn-delete-task" data-id="${task.id}" style="padding:4px 10px; font-size:0.75rem; color:var(--red);">🗑️</button>
      </div>
    `;

    item.querySelector(".task-checkbox").addEventListener("change", async (e) => {
      if (e.target.checked) {
        await fetch(`${API}/api/tasks/${task.id}/complete`, { method: "POST" });
        showToast("Task completed!");
      } else {
        // Re-open if unchecked
      }
      loadTasks();
    });

    item.querySelector(".btn-delete-task").addEventListener("click", async () => {
      await fetch(`${API}/api/tasks/${task.id}`, { method: "DELETE" });
      showToast("Task deleted.");
      loadTasks();
    });

    container.appendChild(item);
  });
}

// Task Form
const formCreateTask = document.getElementById("form-create-task");
if (formCreateTask) {
  formCreateTask.addEventListener("submit", async (e) => {
    e.preventDefault();
    const titleInput = document.getElementById("task-title-input");
    const descInput = document.getElementById("task-desc-input");
    const prioInput = document.getElementById("task-priority-select");

    const title = titleInput.value.trim();
    if (!title) return;

    try {
      await fetch(`${API}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description: descInput.value.trim(),
          priority: parseInt(prioInput.value || "0", 10),
        }),
      });
      titleInput.value = "";
      descInput.value = "";
      showToast("Task created!");
      loadTasks();
    } catch (err) {
      showToast("Error creating task.");
    }
  });
}

// Task Filter Chips
document.querySelectorAll(".filter-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    currentTaskFilter = chip.dataset.filter;
    renderTasks();
  });
});

// ── MEMORY BANK ───────────────────────────────────────────
let memoryCache = [];
let currentCatFilter = "all";

async function loadMemory() {
  const container = document.getElementById("memory-list");
  if (!container) return;
  container.innerHTML = `<div class="empty-state">Loading memory bank…</div>`;

  try {
    const categories = ["personal", "preference", "general"];
    const results = await Promise.all(
      categories.map((c) => fetch(`${API}/api/memory/${c}`).then((r) => r.json()))
    );
    memoryCache = results.flat().filter(Boolean);
    renderMemory();
    updateDashboardCounts();
  } catch (err) {
    container.innerHTML = `<div class="empty-state">Failed to load memory.</div>`;
  }
}

function renderMemory() {
  const container = document.getElementById("memory-list");
  if (!container) return;

  let filtered = memoryCache;
  if (currentCatFilter !== "all") {
    filtered = memoryCache.filter((m) => m.category === currentCatFilter);
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">No memory entries stored yet.</div>`;
    return;
  }

  container.innerHTML = "";
  filtered.forEach((mem) => {
    const item = document.createElement("div");
    item.className = "memory-item";
    item.innerHTML = `
      <div>
        <div class="memory-key">${escapeHtml(mem.key || "Note")} <span class="badge" style="margin-left:6px; font-size:0.65rem;">${mem.category || "general"}</span></div>
        <div class="memory-val">${escapeHtml(mem.value)}</div>
      </div>
      <button class="clay-btn btn-delete-mem" data-id="${mem.id}" style="padding:4px 10px; font-size:0.75rem; color:var(--red);">🗑️</button>
    `;

    item.querySelector(".btn-delete-mem").addEventListener("click", async () => {
      await fetch(`${API}/api/memory/${mem.id}`, { method: "DELETE" });
      showToast("Memory deleted.");
      loadMemory();
    });

    container.appendChild(item);
  });
}

// Memory Form
const formCreateMemory = document.getElementById("form-create-memory");
if (formCreateMemory) {
  formCreateMemory.addEventListener("submit", async (e) => {
    e.preventDefault();
    const catSelect = document.getElementById("memory-category-select");
    const keyInput = document.getElementById("memory-key-input");
    const valInput = document.getElementById("memory-val-input");

    const category = catSelect.value;
    const key = keyInput.value.trim();
    const value = valInput.value.trim();

    if (!key || !value) return;

    try {
      await fetch(`${API}/api/memory`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, key, value }),
      });
      keyInput.value = "";
      valInput.value = "";
      showToast("Memory saved!");
      loadMemory();
    } catch (err) {
      showToast("Error saving memory.");
    }
  });
}

// Memory Clear All
const btnClearMem = document.getElementById("btn-clear-all-memory");
if (btnClearMem) {
  btnClearMem.addEventListener("click", async () => {
    if (confirm("Are you sure you want to clear all stored memories?")) {
      await fetch(`${API}/api/memory/clear`, { method: "POST" });
      showToast("All memories cleared.");
      loadMemory();
    }
  });
}

// Category Tabs
document.querySelectorAll(".cat-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".cat-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    currentCatFilter = tab.dataset.cat;
    renderMemory();
  });
});

// ── SETTINGS ──────────────────────────────────────────────
async function loadSettings() {
  // Sync voice UI with state
  populateVoiceList();
  initVoiceControls();

  try {
    const res = await fetch(`${API}/api/settings`);
    if (!res.ok) return;
    const data = await res.json();

    const pSelect = document.getElementById("cfg-personality-view");
    const localCheck = document.getElementById("cfg-local-view");
    const proCheck = document.getElementById("cfg-proactive-view");

    if (pSelect && data.personality_style) pSelect.value = data.personality_style;
    if (localCheck && typeof data.local_mode === "boolean") localCheck.checked = data.local_mode;
    if (proCheck && typeof data.proactive_enabled === "boolean") proCheck.checked = data.proactive_enabled;
  } catch (err) {
    console.error("Failed to load backend settings", err);
  }
}

const btnSaveSettingsPage = document.getElementById("btn-save-settings-page");
if (btnSaveSettingsPage) {
  btnSaveSettingsPage.addEventListener("click", async () => {
    const pSelect = document.getElementById("cfg-personality-view");
    const localCheck = document.getElementById("cfg-local-view");
    const proCheck = document.getElementById("cfg-proactive-view");
    const voiceSelect = document.getElementById("cfg-voice-view");
    const pitchSlider = document.getElementById("cfg-voice-pitch");
    const rateSlider = document.getElementById("cfg-voice-rate");
    const autoCheck = document.getElementById("cfg-voice-auto-view");

    // Save voice preferences to localStorage
    if (voiceSelect) {
      selectedVoiceURI = voiceSelect.value;
      localStorage.setItem("ai_girl_voice_uri", selectedVoiceURI);
    }
    if (pitchSlider) {
      voicePitch = parseFloat(pitchSlider.value);
      localStorage.setItem("ai_girl_voice_pitch", String(voicePitch));
    }
    if (rateSlider) {
      voiceRate = parseFloat(rateSlider.value);
      localStorage.setItem("ai_girl_voice_rate", String(voiceRate));
    }
    if (autoCheck) {
      autoSpeakEnabled = autoCheck.checked;
      localStorage.setItem("ai_girl_voice_auto", String(autoSpeakEnabled));
    }

    try {
      await fetch(`${API}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          personality_style: pSelect ? pSelect.value : "friendly",
          local_mode: localCheck ? localCheck.checked : true,
          proactive_enabled: proCheck ? proCheck.checked : true,
        }),
      });
      showToast("✨ AI Voice & Settings saved successfully!");
    } catch (err) {
      showToast("Settings saved locally.");
    }
  });
}

// Helper: Update Dashboard Counts
async function updateDashboardCounts() {
  const taskCountEl = document.getElementById("home-task-count");
  const memCountEl = document.getElementById("home-memory-count");

  if (taskCountEl) {
    const pending = tasksCache.filter((t) => t.status !== "completed").length;
    taskCountEl.textContent = `${pending} pending task${pending === 1 ? "" : "s"}`;
  }
  if (memCountEl) {
    memCountEl.textContent = `${memoryCache.length} item${memoryCache.length === 1 ? "" : "s"} saved`;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Initialize
initVoiceControls();
initRecognition();
loadTasks();
loadMemory();
loadSettings();
