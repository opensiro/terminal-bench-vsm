// monitor/assets/charts.js — ванильный SVG-чарты для metrics.html.
// Рисует линии из window.VSM_DATA.history[]. Без библиотек.
"use strict";

function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c])); }

// lineChart(series, opts) → SVG-строка.
// series: [{ name, color, points: [{x,y}], dashed?:bool }]
// opts: { w, h, pad, yMin, yMax, yTicks, xLabels, valueFmt }
function lineChart(series, opts) {
  opts = opts || {};
  const w = opts.w || 640, h = opts.h || 200, pad = opts.pad || 36;
  const yMin = opts.yMin != null ? opts.yMin : 0;
  const yMax = opts.yMax != null ? opts.yMax : 1;
  const innerW = w - pad * 2, innerH = h - pad * 2;
  const xLabels = opts.xLabels || [];
  const n = xLabels.length;
  const xAt = (i) => n <= 1 ? pad : pad + (i / (n - 1)) * innerW;
  const yAt = (v) => {
    if (yMax === yMin) return pad + innerH / 2;
    return pad + innerH - ((v - yMin) / (yMax - yMin)) * innerH;
  };

  // сетка + Y-метки
  const yTicks = opts.yTicks != null ? opts.yTicks : 4;
  let grid = "";
  for (let i = 0; i <= yTicks; i++) {
    const v = yMin + (i / yTicks) * (yMax - yMin);
    const y = yAt(v);
    grid += `<line x1="${pad}" y1="${y}" x2="${w - pad}" y2="${y}" stroke="var(--border)" stroke-width="1" stroke-dasharray="2 3"/>`;
    grid += `<text x="${pad - 6}" y="${y + 3}" text-anchor="end" font-size="10" fill="var(--muted)">${opts.valueFmt ? opts.valueFmt(v) : v}</text>`;
  }

  // X-метки (даты)
  let xlab = "";
  // показываем не больше ~8 меток, чтобы не сливались
  const step = Math.max(1, Math.ceil(n / 8));
  xLabels.forEach((lab, i) => {
    if (i % step !== 0 && i !== n - 1) return;
    xlab += `<text x="${xAt(i)}" y="${h - pad + 14}" text-anchor="middle" font-size="10" fill="var(--muted)">${esc(lab)}</text>`;
  });

  // серии
  let paths = "";
  for (const s of series) {
    if (!s.points || !s.points.length) continue;
    let d = "";
    s.points.forEach((p, i) => { d += (i === 0 ? "M" : "L") + xAt(p.x) + "," + yAt(p.y); });
    paths += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" ${s.dashed ? 'stroke-dasharray="4 3"' : ''}/>`;
    // точки
    s.points.forEach(p => {
      paths += `<circle cx="${xAt(p.x)}" cy="${yAt(p.y)}" r="2.5" fill="${s.color}"/>`;
    });
  }

  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img">
    ${grid}
    ${paths}
    ${xlab}
  </svg>`;
}
