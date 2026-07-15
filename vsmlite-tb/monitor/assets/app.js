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
      <a href="runs.html"    class="${active==='runs'?'active':''}">Раны (${(((D.eval||{}).runs)||[]).length})</a>
      <a href="issues.html"  class="${active==='issues'?'active':''}">Запросы корректировки (${(D.issues||[]).length})</a>
      <a href="reference.html" class="${active==='reference'?'active':''}">Памятка VSM↔vsmlite</a>
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
function renderRunsPage() {   // VSM-029: хедер + навигация для runs.html; таблицу рисует inline-скрипт страницы
  renderHeader("runs");
}

// ════════════════════════ Памятка VSM ↔ vsmlite (reference.html) ════════════════════════
// Статичный reference-контент + живая таблица систем из window.VSM_DATA.
// Канон берётся из ref/vsm-theory.md, meta/reference-mapping.md, systems/README.md.
function sysHealthDot(h) {
  const map = { healthy: "green", unknown: "amber", alert: "red" };
  return `<span class="dot ${map[h] || 'amber'}"></span>`;
}
function renderReference() {
  renderHeader("reference");
  const root = document.getElementById("reference"); if (!root) return;

  // ── живая таблица систем: имена агентов и health — из data.js, остальное — канон ──
  const SYS = [
    { k:"S1",  horizon:"now",             canon:"Реальная работа. Может состоять из множества автономных операционных единиц.",
      lite:"<code>synthesis-operator</code> (планирует) + <code>child-dispatcher</code> (единственный исполнитель, трогает <code>../vsm/</code> и <code>../src/</code>). S1 = <b>синтез</b> дочернего VSM. Продукт после <b>VSM-007 Split</b> = мульти-агент (<code>planner</code>+<code>executor</code>+<code>verifier</code>).",
      shift:"переинтерпретация" },
    { k:"S2",  horizon:"now",             canon:"Анти-осцилляция: гасит конфликты между S1-единицами, синхронизирует, изолирует.",
      lite:"<code>s2-coordinator</code> — anti-looping, изоляция, маршрутизация; статус дочернего VSM → <code>state/status.json</code>.",
      shift:"аналог" },
    { k:"S3",  horizon:"inside-and-now",  canon:"Исполнительный уровень: ресурсы, KPI, бюджет, перераспределение; балансирует S1-единицы.",
      lite:"<code>s3-optimizer</code> — <code>A(t) ∈ [0,1]</code>, бюджет созревания, тройной индекс → <code>state/metrics.json</code>.",
      shift:"аналог" },
    { k:"S3*", horizon:"inside-and-now",  canon:"Независимый канал только-для-чтения: проверяет что <i>реально</i> происходит — другой наблюдатель, не S1/S3.",
      lite:"<code>s3-star-auditor</code> — аудит <b>жизнеспособности</b> child (структурно), <b>ДРУГАЯ модель-провайдер</b>, read-only → <code>state/audit.json</code>.",
      shift:"аналог + мандат" },
    { k:"S4",  horizon:"outside-and-then",canon:"Скан внешней среды: угрозы/возможности, R&D, сценарии будущего.",
      lite:"<code>s4-scout</code> — среда прикладного домена child: пробелы, дрейф child-vs-seed, weak signals → <code>state/intel.json</code>. <b>≠ QA.</b>",
      shift:"аналог" },
    { k:"S5",  horizon:"meta",            canon:"«Кто мы»; ценности; балансирует гомеостаз S3↔S4; решения на уровне идентичности.",
      lite:"<code>s5-guardian</code> + <code>CLAUDE.md</code> (конституция). <b>Архитектор (VSM-005)</b>: вмешивается в child при алгедонике от S3/S3*/S4, рутинно бездействует; каждое вмешательство = +1 к <code>interventions.json</code>. <code>prepare_only</code> — только для родительских решений человека.",
      shift:"аналог + архитектор" },
  ];
  const sysRows = SYS.map(s => {
    const live = (D.systems || {})[s.k] || {};
    const agent = live.name ? `<code>${esc(live.name)}</code>` : "—";
    const health = sysHealthDot(live.health);
    const shiftCls = s.shift.startsWith("переинтерпретация") ? "badge warn" : "badge phase";
    return `<tr>
      <td><b>${s.k}</b><div class="muted" style="font-size:11px;margin-top:2px">${s.horizon}</div></td>
      <td>${s.canon}</td>
      <td>${agent} ${health}<div class="task" style="margin-top:6px">${s.lite}</div></td>
      <td><span class="${shiftCls}">${esc(s.shift)}</span></td>
    </tr>`;
  }).join("");

  root.innerHTML = `
  <div class="note" style="margin-bottom:20px">
    <b>VSM ↔ vsmlite.</b> Это не «VSM минус фичи» — vsmlite <em>полноценный</em> родительский VSM
    (все S1–S5 + S3*), но <b>S1 переинтерпретирован</b>: операция здесь — не код, а
    <b>организационный синтез</b> дочернего VSM (<code>../vsm/</code>) по модели OSM. Имена агентов и
    health ниже — <b>живые</b> (из <code>window.VSM_DATA</code>); остальное — канон из
    <code>ref/vsm-theory.md</code>, <code>meta/reference-mapping.md</code>, <code>systems/README.md</code>.
  </div>

  <section>
    <h2>Dual-layer: родитель-оценщик ↔ продукт-agnostic</h2>
    <div class="card" style="padding:0;overflow-x:auto">
      <table>
        <thead><tr><th>Слой</th><th>Что знает про Terminal Bench</th><th>Файлы</th><th>Роль</th></tr></thead>
        <tbody>
          <tr>
            <td><b>Родитель</b> <code>vsmlite-tb/</code></td>
            <td><span class="badge phase">знает</span> — это оценочный стенд</td>
            <td><code>vsmlite.yaml</code>, <code>eval/</code>, <code>state/dev_metrics.json</code>, <code>state/interventions.json</code></td>
            <td>Выращивает + оценивает продукт. Мембрана (VSM-002) снимает TB-фрейминг на границе.</td>
          </tr>
          <tr>
            <td><b>Продукт</b> <code>../vsm/</code> + <code>../src/</code></td>
            <td><span class="badge warn">НЕ знает</span> — benchmark-agnostic failure-aware coding harness</td>
            <td><code>../vsm/vsm.yaml</code>, <code>../src/runtime/</code> (multi-agent solver: planner+executor+verifier)</td>
            <td>Решает generic coding tasks. Не имеет пути к родителю (parent isolation, VSM-005).</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="note" style="margin-top:10px">
      <b>Мембрана (VSM-002)</b> = структурная, не фильтр. Три механизма (VSM-005):
      <b>(1)</b> MCP tool surface продукта не включает eval-access (отсутствие инструмента);
      <b>(2)</b> <code>vsm/</code> и <code>src/</code> не ссылаются на <code>../../vsmlite-tb/</code>;
      <b>(3)</b> в <code>eval/membrane.py</code> TB-инструкция транслируется в нейтральный <code>task_prompt</code> + <code>verify_neutrality()</code> бросает ошибку при утечке. Проверяется <code>scripts/validate.sh §2c</code>.
    </div>
  </section>

  <section>
    <h2>Системы — постолбцовое сравнение</h2>
    <div class="card" style="padding:0;overflow-x:auto">
      <table>
        <thead><tr><th>Система</th><th>VSM — канон (Beer)</th><th>vsmlite — реализация (живое)</th><th>статус</th></tr></thead>
        <tbody>${sysRows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Чем vsmlite легче — конкретные отличия</h2>
    <div class="card" style="padding:0;overflow-x:auto">
      <table>
        <thead><tr><th>В VSM (эталон opensiro-arctic/vsm)</th><th>В vsmlite</th><th>Что изменилось</th></tr></thead>
        <tbody>
          <tr><td>Управляет 6 S1-репо (флот)</td><td>Управляет <b>одним</b> дочерним VSM + оценивает его</td><td>Фокус на синтезе+оценке одного домена</td></tr>
          <tr><td><code>s1-dispatcher</code> (boundary в <code>../&lt;repo&gt;</code>)</td><td><code>child-dispatcher</code> (в <code>../vsm/</code> + <code>../src/</code>)</td><td>Та же идея, другой target</td></tr>
          <tr><td>Mono-agent S1 (single solver)</td><td>Продукт S1 = <b>multi-agent</b> (planner+executor+verifier, VSM-007 Split)</td><td>OSM Split: session sync активирован, verifier ловит failure раньше recovery</td></tr>
          <tr><td><code>issue-liaison</code> → Gitea</td><td><span class="badge warn">убран</span></td><td>Решения в REPL-дайджесте + <code>issues/VSM-NNN.yaml</code></td></tr>
          <tr><td>HTML-дашборд (<code>monitor/*.html</code>)</td><td>только телеметрия <code>monitor/data.js</code></td><td>UX — терминальный; UI — этот самый монитор (lite)</td></tr>
          <tr><td>Heartbeats как основной режим</td><td>On-demand (<code>/vsmlite-cycle</code>)</td><td>Юзер запускает цикл; heartbeats опциональны</td></tr>
          <tr><td>Доменные скрипты (<code>bench_match.py</code>…)</td><td>Свои: <code>autonomy.py</code>, <code>collect_metrics.py</code>, <code>cycle_digest.py</code>, <code>render_data.py</code></td><td>Паттерн сохранён, скрипты свои</td></tr>
          <tr><td>Алгедонический → Gitea</td><td>Алгедонический → <code>VSM-NNN</code> + REPL</td><td>Gitea → forward-контракт vsmforge</td></tr>
          <tr><td>Без оценочного слоя</td><td><code>eval/</code> — Terminal-Bench Dev Set v2 пайплайн (VSM-008)</td><td>docker-exec MCP bridge + <code>state/dev_metrics.json</code> как ВХОДНОЙ индикатор A(t)</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px" id="ref-twocol">
    <section>
      <h2>Матрица коммуникаций VSM</h2>
      <div class="card" style="padding:0;overflow-x:auto">
        <table style="font-size:12px;text-align:center">
          <thead><tr><th style="text-align:left">От ↓ / К →</th><th>S1</th><th>S2</th><th>S3</th><th>S3*</th><th>S4</th><th>S5</th><th>human</th></tr></thead>
          <tbody>
            <tr><th style="text-align:left">S1</th><td>—</td><td style="color:var(--green)">✅ only</td><td>—</td><td>—</td><td>—</td><td style="color:var(--red)">⚡</td><td>—</td></tr>
            <tr><th style="text-align:left">S2</th><td style="color:var(--green)">✅</td><td>—</td><td style="color:var(--green)">✅</td><td style="color:var(--green)">✅</td><td style="color:var(--green)">✅</td><td style="color:var(--green)">✅</td><td>—</td></tr>
            <tr><th style="text-align:left">S3</th><td style="color:var(--green)">✅</td><td style="color:var(--green)">✅</td><td>—</td><td>—</td><td>—</td><td>—</td><td>digest</td></tr>
            <tr><th style="text-align:left">S3*</th><td style="color:var(--amber)">ro</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td style="color:var(--red)">⚡</td></tr>
            <tr><th style="text-align:left">S4</th><td>—</td><td style="color:var(--green)">✅</td><td>—</td><td>—</td><td>—</td><td style="color:var(--green)">✅</td><td>brief</td></tr>
            <tr><th style="text-align:left">S5</th><td>—</td><td style="color:var(--green)">✅</td><td style="color:var(--green)">✅</td><td>—</td><td style="color:var(--green)">✅</td><td>—</td><td style="color:var(--red)">⚡</td></tr>
          </tbody>
        </table>
      </div>
      <div class="muted" style="font-size:11px;margin-top:6px">
        <span style="color:var(--green)">✅</span> говорит · <span style="color:var(--amber)">ro</span> только чтение · <span style="color:var(--red)">⚡</span> алгедонический байпас (severity S0/S1)
      </div>
    </section>

    <section>
      <h2>Карта цикла vsmlite</h2>
      <div class="card" style="padding:0;overflow-x:auto">
        <table>
          <thead><tr><th>Система</th><th>Что делает за <code>/vsmlite-cycle</code></th><th>Пишет</th></tr></thead>
          <tbody>
            <tr><td><b>S2</b></td><td>статус child, конфликты, изоляция</td><td><code>state/status.json</code></td></tr>
            <tr><td><b>S3</b></td><td>A(t) / бюджет, готовность к фазе</td><td><code>state/metrics.json</code></td></tr>
            <tr><td><b>S3*</b></td><td>независимый аудит (ДРУГАЯ модель)</td><td><code>state/audit.json</code></td></tr>
            <tr><td><b>S4</b></td><td>среда домена: weak signals, дрейф</td><td><code>state/intel.json</code></td></tr>
            <tr><td><b>S5</b></td><td>архитектор: дайджест → REPL-вопрос; при алгедонике — структурное изменение</td><td><code>issues/VSM-NNN.yaml</code> + <code>state/interventions.json</code></td></tr>
            <tr><td><b>eval</b> <span class="muted">(VSM-008)</span></td><td>прогон продукта на TB Dev Set v2 (docker-exec MCP bridge)</td><td><code>state/dev_metrics.json</code> (pass_rate по категориям/сложности)</td></tr>
          </tbody>
        </table>
      </div>
      <div class="note" style="margin-top:10px">
        <b>Recovery cycle продукта</b> (multi-agent S1, VSM-007):
        <code>S1 (executor) → verifier → S3 (classify) → S3* (audit) → recovery executor → S2 (isolate) → retry</code>.
        Verifier ловит failure раньше, чем он станет observation для S3; session sync связывает sub-agents per-task.
      </div>
    </section>
  </div>

  <section>
    <h2>A(t) — двойной индикатор автономности (VSM-004/005)</h2>
    <div class="card" style="padding:0;overflow-x:auto">
      <table>
        <thead><tr><th>Индикатор</th><th>Направление</th><th>Что измеряет</th><th>Источник</th><th>Рост автономии</th></tr></thead>
        <tbody>
          <tr>
            <td><b>pass_rate</b> (Dev Set)</td>
            <td><span class="badge phase">ВХОДНОЙ</span></td>
            <td>Продукт справляется с задачами сам</td>
            <td><code>state/dev_metrics.json</code> ← <code>eval/</code></td>
            <td>↑ к 1.0</td>
          </tr>
          <tr>
            <td><b>intervention count</b></td>
            <td><span class="badge warn">ОБРАТНЫЙ</span></td>
            <td>Сколько раз S5 пришлось вмешаться (автономии не хватило)</td>
            <td><code>state/interventions.json</code> ← S5</td>
            <td>↓ к 0</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="muted" style="font-size:12px;margin-top:6px">
      <code>pass_rate ↑</code> + <code>interventions ↓</code> = автономность растёт. Показывается в dashboard (публично), НЕ владеется S5.
    </div>
  </section>

  <section>
    <h2>Ключевой инвариант (сохранён в обеих)</h2>
    <div class="note">
      Контрольная плоскость <b>никогда не трогает операции напрямую</b> — только через boundary-агента
      (<code>child-dispatcher</code>). S2–S5 и <code>synthesis-operator</code> (как планировщик) только читают
      <code>state/</code>, пишут <code>issues/</code> и <code>monitor/data.js</code>, спавнят субагентов.
      Проверяется <code>scripts/validate.sh</code>. Это сердце архитектуры VSM и vsmlite.
    </div>
  </section>

  <section>
    <div class="note">
      <b>Источники в репозитории:</b>
      <a href="../ref/vsm-theory.md">ref/vsm-theory.md</a> ·
      <a href="../meta/reference-mapping.md">meta/reference-mapping.md</a> ·
      <a href="../systems/README.md">systems/README.md</a> ·
      <a href="../CLAUDE.md">CLAUDE.md</a> ·
      <a href="../vsmlite.yaml">vsmlite.yaml</a> ·
      <a href="../synthesis/phases.yaml">synthesis/phases.yaml</a> ·
      <a href="../synthesis/primitives.yaml">synthesis/primitives.yaml</a> ·
      <a href="../eval/README.md">eval/README.md</a> ·
      <a href="../note.md">note.md</a>
      <br><br>
      Эта страница — статичный HTML (как весь <code>monitor/</code>). Живые данные (имена агентов, health)
      берутся из <code>monitor/data.js</code> → <code>window.VSM_DATA.systems</code>. Регенерация:
      <code>python3 scripts/render_data.py</code>. Текущий контекст: VSM-008 <span class="badge phase">done</span>,
      VSM-007 Split S1 <span class="badge phase">approved</span>, продукт = benchmark-agnostic (VSM-002), S5 = архитектор (VSM-005).
    </div>
  </section>
  `;
}
