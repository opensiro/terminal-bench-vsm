// monitor/assets/app.js — рендер дашборда vsmlite-tb. Ванильный JS.
// Читает window.VSM_DATA (из data.js). Адаптировано из opensiro-arctic/vsm/monitor/assets/app.js
// под maturation/OSM-домен (выкинуты GITEA/REPO_FOR/benchmarks/fanout; добавлены maturation-track,
// 4 знака A(t), доменные KPI).
"use strict";

const D = window.VSM_DATA || {};
const SYS_ORDER = ["S1", "S2", "S3", "S3*", "S4", "S5"];
const METRIC_HINTS = window.VSM_HINTS || {};

// ── утилиты ──
function splitSummary(text) {
  const t = String(text == null ? "" : text).trim();
  if (!t) return { short: "", full: "" };
  const m = t.match(/^(.{10,220}?[.!?\n])/);
  const short = m ? m[1].replace(/\s+$/,"") : t.slice(0, 220);
  return { short, full: t.length > short.length + 3 ? t : "" };
}
function taskBlock(text, summaryField) {
  const sum = String(summaryField || "").trim();
  const full = String(text || "").trim();
  if (sum && full && sum !== full) {
    return `<div class="task summary">${esc(sum)}</div>` +
           `<details class="task-appendix"><summary>полный вывод агента ▾</summary><div class="task-full">${esc(full)}</div></details>`;
  }
  if (full) {
    const s = splitSummary(full);
    if (s.full) {
      return `<div class="task summary">${esc(s.short)}</div>` +
             `<details class="task-appendix"><summary>полный текст ▾</summary><div class="task-full">${esc(s.full)}</div></details>`;
    }
    return `<div class="task">${esc(full)}</div>`;
  }
  return `<div class="task">${esc(sum) || "—"}</div>`;
}
function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}
function iso(z) { if (!z) return "—"; try { return new Date(z).toLocaleString(); } catch (_) { return z; } }
function sevClass(s) { return "badge sev-" + (s || "S3"); }
function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c])); }
function pct(x) { return x == null ? "—" : (Math.round(x * 1000) / 10) + "%"; }

// ════════════════════════ РЕШЕНИЯ ЧЕЛОВЕКА (мультивыбор / manual) ════════════════════════
const DEC_KEY = "vsmlite_tb_decisions_v1";
function loadDec() { try { return JSON.parse(localStorage.getItem(DEC_KEY) || "{}"); } catch (_) { return {}; } }
function saveDec(d) { localStorage.setItem(DEC_KEY, JSON.stringify(d)); }

function optionsFor(i) {
  if (Array.isArray(i.options) && i.options.length) {
    return i.options.map(o => typeof o === "string" ? { id: o, label: o, hint: "" } : o);
  }
  return [
    { id: "accept",  label: "✓ Принять предложенное" },
    { id: "defer",   label: "⏸ Отложить" },
    { id: "wontfix", label: "✗ Отклонить" },
  ];
}
function decOf(id) { return loadDec()[id] || null; }
function decLabel(i) {
  const d = decOf(i.id); if (!d) return null;
  if (d.manual && d.manual.trim()) return `manual — «${d.manual}»`;
  const opts = optionsFor(i);
  const sel = (d.choices || []).map(c => (opts.find(o => o.id === c) || {}).label || c);
  return sel.length ? `выбрано: ${sel.join(", ")}` : null;
}
// команда применения — vsmlite-tb не имеет /vsm-decide; формируем комментарий для сессии
function decCmd(i) {
  const d = decOf(i.id); if (!d) return null;
  if (d.manual && d.manual.trim()) return `# ${i.id}: manual — "${d.manual.trim().replace(/"/g, "'")}"\n# применить в сессии vsmlite-tb (см. CLAUDE.md)`;
  if (d.choices && d.choices.length) return `# ${i.id}: ${d.choices.join(",")}\n# применить в сессии vsmlite-tb: обновить issues/${i.id}.yaml (status/decision/selected_options)`;
  return null;
}
function setDec(id, patch) {
  const all = loadDec();
  if (patch === null) { delete all[id]; }
  else { all[id] = Object.assign({}, all[id] || {}, patch, { ts: new Date().toISOString() }); }
  saveDec(all);
  renderDecFile();
}
function toggleChoice(id, cid) {
  const d = decOf(id) || { choices: [] };
  const s = new Set(d.choices || []);
  if (s.has(cid)) s.delete(cid); else s.add(cid);
  setDec(id, { choices: Array.from(s) });
}

// ════════════════════════ Рендер ════════════════════════
function renderHeader(active) {
  const h = document.querySelector("header.top") || el("header", "top");
  const phase = (D.maturation || {}).state || (D.metrics || {}).maturation_phase || "—";
  const verdict = (D.maturation || {}).autonomy_verdict || "—";
  h.innerHTML = `
    <div>
      <h1>${D.project || "vsmlite-tb dashboard"}</h1>
      <div class="sub">vsmlite-tb · родительский VSM (Terminal Bench 2.1) · mode: <b>${D.operational_mode || "normal"}</b> · phase: <b>${esc(phase)}</b> · A(t) verdict: <b>${esc(verdict)}</b></div>
      <div class="meta-line">обновлено: ${iso(D.generated)}</div>
    </div>
    <nav class="top">
      <a href="index.html"   class="${active==='index'?'active':''}">Системы / maturation</a>
      <a href="metrics.html" class="${active==='metrics'?'active':''}">Метрики по датам</a>
      <a href="issues.html"  class="${active==='issues'?'active':''}">Запросы корректировки (${(D.issues||[]).length})</a>
    </nav>`;
}

// maturation track (OSM фазы)
const PHASES = [
  { key: "Initial State", label: "Initial" },
  { key: "Phase 0", label: "Ph0 · Intent" },
  { key: "Phase 1", label: "Ph1 · S1" },
  { key: "Phase 2", label: "Ph2 · S2" },
  { key: "Phase 3", label: "Ph3 · S3" },
  { key: "Phase 4", label: "Ph4 · S3*" },
  { key: "Phase 5", label: "Ph5 · S4" },
  { key: "Phase 6", label: "Ph6 · S5" },
  { key: "Autonomous", label: "Autonomous" },
];
function renderMaturation() {
  const root = document.getElementById("maturation"); if (!root) return; root.innerHTML = "";
  const m = D.maturation || {};
  const current = m.state || "Initial State";
  const curIdx = PHASES.findIndex(p => p.key === current);
  const pills = PHASES.map((p, i) => {
    let cls = "";
    if (i < curIdx) cls = "done";
    else if (i === curIdx) cls = "current";
    return `<span class="phase-pill ${cls}" title="${esc(p.key)}">${esc(p.label)}</span>`;
  }).join('<span class="muted" style="font-size:11px">→</span>');
  const at = (D.metrics || {}).autonomy_score;
  const card = el("div", "card");
  card.innerHTML = `
    <h3>Maturation (OSM) — <span class="badge phase">${esc(current)}</span></h3>
    <div class="phase-track" style="margin:10px 0">${pills}</div>
    <div class="foot">
      <span>A(t) = <b>${at == null ? "—" : at}</b> · verdict: <b>${esc(m.autonomy_verdict || "—")}</b> · target: ${m.autonomy_target == null ? "—" : m.autonomy_target}</span>
      <span>cycle: ${m.cycle_count == null ? "—" : m.cycle_count} · last primitive: ${esc(m.last_primitive || "—")}</span>
    </div>
    ${m.last_transition ? `<div class="foot"><span>last transition: ${esc(m.last_transition)}</span><span>child_initialized: ${m.child_initialized ? "✓" : "✗"}</span></div>` : ""}
  `;
  root.appendChild(card);
}

// 4 знака A(t)
function renderSigns() {
  const root = document.getElementById("signs"); if (!root) return; root.innerHTML = "";
  const signs = (D.maturation || {}).autonomy_signs || {};
  if (!Object.keys(signs).length) { root.innerHTML = `<div class="empty">знаки A(t) отсутствуют (state/maturation.json → autonomy.signs)</div>`; return; }
  const grid = el("div", "signs-grid");
  const order = ["s5_sign", "s4_sign", "s3_sign", "s1_sign"];
  const titles = { s5_sign: "S5-sign ← issues[]", s4_sign: "S4-sign ← intel[]", s3_sign: "S3-sign ← units[]", s1_sign: "S1-sign ← activity[]" };
  for (const k of order) {
    const s = signs[k]; if (!s) continue;
    const meets = s.meets === true;
    const c = el("div", "sign-card " + (meets ? "meets" : ""));
    c.innerHTML = `
      <span class="sign-stripe"></span>
      <h4>${esc(k)} <span class="muted" style="font-weight:400">${meets ? "✓ meets" : "✗"}</span></h4>
      <div class="sign-val">${s.value == null ? "—" : esc(s.value)}</div>
      <div class="sign-detail" title="${esc(METRIC_HINTS[k] || '')}">${esc(s.from ? "from " + s.from : titles[k])}</div>
    `;
    grid.appendChild(c);
  }
  root.appendChild(grid);
}

function renderSystems() {
  const root = document.getElementById("systems"); if (!root) return; root.innerHTML = "";
  const grid = el("div", "grid sys");
  for (const k of SYS_ORDER) {
    const s = (D.systems || {})[k]; if (!s) continue;
    const c = el("div", "card");
    const stripe = el("div"); stripe.style.cssText = `position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--${s.health || 'green'})`;
    c.appendChild(stripe);
    c.appendChild(el("h3", null, `<span class="dot ${s.health || 'green'}"></span>${k} · ${esc(s.name || s.role || '')}`));
    c.appendChild(el("div", "task-wrap", taskBlock(s.current_task, s.summary)));
    c.appendChild(el("div", "foot", `<span>health: ${esc(s.health || '—')}</span><span>${esc(s.status || '')}</span>`));
    grid.appendChild(c);
  }
  if (!grid.children.length) { root.innerHTML = `<div class="empty">системы не активированы (Phase 1 → только S1; S2–S5 «дремлют»)</div>`; return; }
  root.appendChild(grid);
}

function renderUnits() {
  const root = document.getElementById("units"); if (!root) return;
  const tbody = root.querySelector("tbody"); if (!tbody) return;
  const rows = (D.units || []).map(u => {
    return `<tr><td><span class="dot ${u.status === 'healthy' || u.exists ? 'green' : 'red'}"></span>${esc(u.name)}</td><td>${esc(u.role || u.path || '—')}</td><td class="num">${u.open_issues != null ? u.open_issues : 0}</td><td>${iso(u.last_commit_date || u.last_active)}</td></tr>`;
  }).join("");
  tbody.innerHTML = rows || `<tr><td colspan="4" class="empty">нет данных (collect_metrics.py подключит ../src на следующих фазах)</td></tr>`;
}

function renderMetrics() {
  const root = document.getElementById("metrics"); if (!root || !D.metrics) return;
  const m = D.metrics;
  root.innerHTML = "";
  const kpi = (v, label, hint) => `<div class="kpi" title="${esc(hint || '')}"><div class="v">${v}</div><div class="l">${label}${hint ? ' <span class="hint">ⓘ</span>' : ''}</div></div>`;
  const k = el("div", "kpis"); k.innerHTML =
    kpi(m.autonomy_score == null ? "—" : m.autonomy_score, "A(t)", METRIC_HINTS.autonomy_score) +
    kpi(esc(m.maturation_phase || "—"), "phase", METRIC_HINTS.maturation_phase) +
    kpi(m.coverage_ratio == null ? "—" : pct(m.coverage_ratio), "coverage", METRIC_HINTS.coverage_ratio) +
    kpi(m.validate_pass_rate == null ? "—" : pct(m.validate_pass_rate), "validate", METRIC_HINTS.validate_pass_rate) +
    kpi(m.drift_score == null ? "—" : m.drift_score, "drift", METRIC_HINTS.drift_score);
  root.appendChild(k);

  const ti = m.triple_index || {};
  if (ti && (ti.actuality || ti.capability || ti.potentiality)) {
    root.appendChild(el("div", "note",
      `<b>Triple index (S3):</b> ` +
      `<abbr title="${esc(METRIC_HINTS.triple_actuality || '')}">actuality</abbr> — ${esc(ti.actuality) || '—'} · ` +
      `<abbr title="${esc(METRIC_HINTS.triple_capability || '')}">capability</abbr> — ${esc(ti.capability) || '—'} · ` +
      `<abbr title="${esc(METRIC_HINTS.triple_potentiality || '')}">potentiality</abbr> — ${esc(ti.potentiality) || '—'}`));
  }
  const b = m.balance_s3_s4 || {};
  if (b && b.status) {
    root.appendChild(el("div", "note",
      `<b>Баланс S3↔S4 (S5):</b> ` +
      `<abbr title="${esc(METRIC_HINTS.balance_s3_share || '')}">S3</abbr> ${b.s3_share == null ? "—" : pct(b.s3_share)} / ` +
      `<abbr title="${esc(METRIC_HINTS.balance_s4_share || '')}">S4</abbr> ${b.s4_share == null ? "—" : pct(b.s4_share)} — ` +
      `<b title="${esc(METRIC_HINTS.balance_status || '')}">${esc(b.status)}</b>`));
  }
}

function renderSignals() {
  const root = document.getElementById("signals"); if (!root) return;
  const list = D.intel || [];
  if (!list.length) { root.innerHTML = `<div class="empty">сигналов S4 нет (S4 активируется на Phase 5; сейчас dormant)</div>`; return; }
  root.innerHTML = list.map(s => `<div class="card"><span style="position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent)"></span><h3><span class="badge signal">${esc(s.signal_type || s.status)}</span> <span class="badge">${esc(s.target_unit || '')}</span></h3><div class="task">${esc(s.summary || s.title || '—')}</div></div>`).join("");
}

function renderAudit() {
  const root = document.getElementById("audit"); if (!root) return;
  const list = D.audit || [];
  if (!list.length) { root.innerHTML = `<div class="empty">находок S3* нет — чисто (S3* активируется на Phase 4; сейчас dormant)</div>`; return; }
  root.innerHTML = list.map(a => `<div class="card"><span style="position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--${a.severity === 'S0' ? 'red' : a.severity === 'S1' ? 'amber' : 'green'})"></span><h3><span class="${sevClass(a.severity)}">${esc(a.severity)}</span> <span class="badge">${esc(a.target_unit || '')}</span></h3><div class="task">${esc(a.finding || a.summary || '—')}</div></div>`).join("");
}

// ── issues: карточка с мультивыбором ──
function issueCard(i) {
  const ev = (i.evidence || []).map(e => `<li>${esc(e)}</li>`).join("");
  const ac = (i.acceptance || []).map(a => `<li>${esc(a)}</li>`).join("");
  const opts = optionsFor(i).map(o => `<label class="opt" title="${esc(o.hint || '')}"><input type="checkbox" data-choice="${esc(o.id)}"> <span>${esc(o.label)}</span></label>`).join("");
  const dec = i.decision ? `<div class="note" style="margin-top:8px"><b>decision (из файла):</b> ${esc(i.decision)}</div>` : "";
  return `<div class="issue" data-id="${esc(i.id)}">
    <h3>${esc(i.title || i.id)}</h3>
    <div class="ids">
      <span class="badge">${esc(i.id)}</span><span class="${sevClass(i.severity)}">${esc(i.severity || 'S3')}</span>
      <span class="badge sys">${esc(i.source_system || '?')}</span><span class="badge signal">${esc(i.signal_type || '?')}</span>
      <span class="badge">${esc(i.target_unit || '?')}</span><span class="badge">status: ${esc(i.status || 'triage')}</span>
      ${i.needs_human_decision ? '<span class="badge warn">needs human</span>' : ''}
    </div>
    <div class="summary">${esc(i.summary || '')}</div>
    ${i.proposal ? `<details class="issue-details"><summary>Предложение (non-binding) ▾</summary><div>${esc(i.proposal)}</div></details>` : ''}
    ${ev ? `<details class="issue-details"><summary>Доказательства (${(i.evidence||[]).length}) ▾</summary><ul>${ev}</ul></details>` : ''}
    ${ac ? `<details class="issue-details"><summary>Критерии приёмки (${(i.acceptance||[]).length}) ▾</summary><ul>${ac}</ul></details>` : ''}
    ${i.policy_question ? `<details class="issue-details"><summary>Вопрос политики ▾</summary><div>${esc(i.policy_question)}</div></details>` : ''}
    ${dec}
    <div class="decision">
      <h4>Ваше решение — мультивыбор (локально, в браузере)</h4>
      <div class="opts">${opts}</div>
      <div class="manual"><textarea data-manual rows="2" placeholder="…или напишите manual (перекрывает выбор)"></textarea></div>
      <div class="dec-actions"><button data-act="manual">Использовать manual</button></div>
      <div class="dec-state" data-decstate></div>
    </div>
  </div>`;
}

function hydrateCard(card) {
  const id = card.getAttribute("data-id");
  const d = decOf(id) || {};
  card.querySelectorAll("input[data-choice]").forEach(cb => { cb.checked = (d.choices || []).includes(cb.getAttribute("data-choice")); });
  const ta = card.querySelector("[data-manual]"); if (ta) ta.value = d.manual || "";
  const st = card.querySelector("[data-decstate]");
  const issue = (D.issues.find(x => x.id === id) || {});
  const lbl = decLabel(Object.assign({ id }, issue));
  const cmd = decCmd({ id });
  if (!lbl) { st.innerHTML = `<span class="muted">Отметьте вариант(ы) либо напишите manual. Решение сохранится локально и в <code>decisions.json</code> ниже.</span>`; return; }
  st.innerHTML = `<div class="dec-done">✓ Решено: <b>${esc(lbl)}</b></div>
    <div class="dec-cmd"><code>${esc(cmd)}</code><button data-act="copy">копировать</button><button data-act="reset">сбросить</button></div>`;
}

function isResolved(i) {
  const st = String(i.status || "").toLowerCase();
  if (["accepted", "wontfix", "deferred", "resolved", "closed", "done"].includes(st)) return true;
  const dec = String(i.decision || "").trim();
  return !!dec && dec !== '""';
}
function renderIssues() {
  const root = document.getElementById("issues"); if (!root) return;
  const list = D.issues || [];
  if (!list.length) { root.innerHTML = `<div class="empty">открытых запросов корректировки нет</div>`; return; }
  const active = list.filter(i => !isResolved(i));
  const archive = list.filter(i => isResolved(i));
  let html = "";
  if (active.length) {
    html += `<h3 class="grp" style="font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em">▶ Активные запросы (${active.length})</h3>`;
    html += active.map(issueCard).join("");
  } else {
    html += `<div class="empty">активных запросов нет — все решены (см. архив ↓)</div>`;
  }
  if (archive.length) {
    html += `<details class="archive"><summary class="grp" style="font-size:13px;color:var(--muted)">📁 Архив — решённые (${archive.length})</summary>`;
    html += archive.map(issueCard).join("");
    html += `</details>`;
  }
  root.innerHTML = html;
  root.querySelectorAll(".issue").forEach(hydrateCard);
}

function renderDecisionsToolbar() {
  const tb = document.getElementById("dec-toolbar"); if (!tb) return;
  const n = Object.keys(loadDec()).length;
  tb.innerHTML = `
    <div class="dec-summary">Решений зафиксировано: <b>${n}</b></div>
    <div class="dec-tools">
      <button id="dec-export" ${n ? '' : 'disabled'}>⬇ скачать decisions.json</button>
      <button id="dec-clear" ${n ? '' : 'disabled'}>очистить все</button>
    </div>`;
}

function renderDecFile() {
  const pre = document.getElementById("dec-file"); if (!pre) return;
  const payload = { exported: new Date().toISOString(), decisions: loadDec() };
  pre.textContent = JSON.stringify(payload, null, 2) + "\n";
}

function exportDecisions() {
  const blob = new Blob([JSON.stringify({ exported: new Date().toISOString(), decisions: loadDec() }, null, 2)], { type: "application/json" });
  const a = el("a"); a.href = URL.createObjectURL(blob); a.download = "decisions.json"; document.body.appendChild(a); a.click(); a.remove();
}

function wireIssues() {
  const root = document.getElementById("issues");
  if (root) root.addEventListener("click", (e) => {
    const card = e.target.closest(".issue"); if (!card) return;
    const id = card.getAttribute("data-id");
    const act = e.target.getAttribute("data-act");
    if (act === "copy") { const cmd = decCmd({ id }); navigator.clipboard && navigator.clipboard.writeText(cmd).then(() => { e.target.textContent = "✓"; setTimeout(() => e.target.textContent = "копировать", 1200); }); return; }
    if (act === "reset") { setDec(id, null); hydrateCard(card); renderDecisionsToolbar(); return; }
    if (act === "manual") { const t = card.querySelector("[data-manual]"); const v = (t && t.value || "").trim(); if (!v) { t && t.focus(); return; } setDec(id, { manual: v, choices: [] }); hydrateCard(card); renderDecisionsToolbar(); return; }
  });
  if (root) root.addEventListener("change", (e) => {
    const cb = e.target.closest("input[data-choice]"); if (!cb) return;
    const card = cb.closest(".issue"); if (!card) return;
    toggleChoice(card.getAttribute("data-id"), cb.getAttribute("data-choice"));
    hydrateCard(card); renderDecisionsToolbar();
  });
  const tb = document.getElementById("dec-toolbar");
  if (tb) tb.addEventListener("click", (e) => {
    if (e.target.id === "dec-export") exportDecisions();
    if (e.target.id === "dec-clear") { if (confirm("Очистить все зафиксированные решения?")) { saveDec({}); renderIssues(); renderDecisionsToolbar(); renderDecFile(); } }
  });
}

// ── точки входа страниц ──
function renderHome() {
  renderHeader("index");
  renderMaturation();
  renderSigns();
  renderSystems();
  renderMetrics();
  renderAudit();
  renderSignals();
}
function renderIssuesPage() {
  renderHeader("issues");
  renderDecisionsToolbar();
  renderDecFile();
  renderIssues();
  wireIssues();
}
function renderMetricsPage() {
  renderHeader("metrics");
  if (window.renderMetricsHistory) window.renderMetricsHistory();
}
