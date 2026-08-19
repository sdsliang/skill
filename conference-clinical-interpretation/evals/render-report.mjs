#!/usr/bin/env node
/**
 * Render the ASCO 2026 iteration-01 sample report into a self-contained HTML file.
 *
 * - Parses report.md into HTML (headings / lists / tables / quotes / inline code / bold).
 * - Replaces each `::visualization[标题]{path="..."}` reference with a real chart:
 *     - path .../conference-stats.json -> KPI card grid
 *     - path .../watchlist.csv         -> watchlist table
 *     - path .../chart-data.json       -> chart matched by title keywords, drawn as
 *                                        inline SVG (no CDN, no ECharts, offline-safe)
 * - Uses the Skill's semantic color tokens (--viz-*) declared locally.
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ITER_DIR = path.join(HERE, "iteration-01/asco-2026");

const reportMd = fs.readFileSync(path.join(ITER_DIR, "report.md"), "utf8");
const stats = JSON.parse(fs.readFileSync(path.join(HERE, "fixtures/asco-2026-stats.json"), "utf8"));
const chartData = JSON.parse(fs.readFileSync(path.join(ITER_DIR, "chart-data.json"), "utf8"));
const watchlistCsv = fs.readFileSync(path.join(ITER_DIR, "watchlist.csv"), "utf8");

/* ------------------------------------------------------------------ */
/* 1. Mini markdown -> html                                            */
/* ------------------------------------------------------------------ */

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inline(s) {
  // code spans first
  let out = s.replace(/`([^`]+)`/g, (_m, c) => `<code>${escapeHtml(c)}</code>`);
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return out;
}

function renderTable(lines) {
  const header = lines[0]
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((x) => x.trim());
  const rows = lines.slice(2).map((l) =>
    l
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((x) => x.trim())
  );
  const thead = `<thead><tr>${header.map((h) => `<th>${inline(h)}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map(
      (r) =>
        `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`
    )
    .join("")}</tbody>`;
  return `<table>${thead}${tbody}</table>`;
}

function markdownToHtml(md) {
  const lines = md.split("\n");
  const html = [];
  let i = 0;
  let listBuffer = [];
  const flushList = () => {
    if (listBuffer.length) {
      html.push(`<ul>${listBuffer.map((l) => `<li>${l}</li>`).join("")}</ul>`);
      listBuffer = [];
    }
  };

  while (i < lines.length) {
    const line = lines[i];

    if (/^::visualization\[/.test(line)) {
      flushList();
      const m = line.match(/^::visualization\[([^\]]*)\]\{path="([^"]+)"\}/);
      html.push(`<div class="viz-slot" data-title="${escapeHtml(m ? m[1] : "")}" data-path="${escapeHtml(m ? m[2] : "")}"></div>`);
      i++;
      continue;
    }
    if (/^#{1,6}\s/.test(line)) {
      flushList();
      const level = line.match(/^(#{1,6})\s/)[1].length;
      html.push(`<h${level}>${inline(line.replace(/^#{1,6}\s*/, ""))}</h${level}>`);
      i++;
      continue;
    }
    if (/^\|.*\|$/.test(line)) {
      flushList();
      const tbl = [];
      while (i < lines.length && /^\|.*\|$/.test(lines[i])) {
        tbl.push(lines[i]);
        i++;
      }
      html.push(renderTable(tbl));
      continue;
    }
    if (/^>\s?/.test(line)) {
      flushList();
      html.push(`<blockquote>${inline(line.replace(/^>\s?/, ""))}</blockquote>`);
      i++;
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      listBuffer.push(inline(line.replace(/^\s*[-*]\s+/, "")));
      i++;
      continue;
    }
    if (/^\s*$/.test(line)) {
      flushList();
      i++;
      continue;
    }
    flushList();
    html.push(`<p>${inline(line)}</p>`);
    i++;
  }
  flushList();
  return html.join("\n");
}

/* ------------------------------------------------------------------ */
/* 2. Chart renderers (pure SVG, offline)                              */
/* ------------------------------------------------------------------ */

const EVAL_COLORS = { 积极: "var(--viz-success)", 不佳: "var(--viz-danger)", 终止: "var(--viz-warning)" };
const SERIES = [
  "var(--viz-series-1)",
  "var(--viz-series-2)",
  "var(--viz-series-3)",
  "var(--viz-series-4)",
  "var(--viz-series-5)",
];

function svg(w, h, inner) {
  return `<svg class="chart-svg" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
}

function chartCard(title, subtitle, svgBody) {
  return `<div class="chart-card"><div class="chart-title">${escapeHtml(title)}</div>${
    subtitle ? `<div class="chart-subtitle">${escapeHtml(subtitle)}</div>` : ""
  }${svgBody}</div>`;
}

// --- KPI cards -------------------------------------------------------
function renderKpi() {
  const items = [
    ["匹配记录数", stats.overview.matched_records],
    ["分析合格记录数", stats.overview.analysis_eligible_records],
    ["唯一药物", stats.overview.unique_drugs],
    ["唯一适应症", stats.overview.unique_indications],
    ["唯一生物标志物", stats.overview.unique_biomarkers],
    ["含样本量记录", stats.overview.records_with_sample_size],
  ];
  return `<div class="kpi-grid">${items
    .map(
      ([k, v]) =>
        `<div class="kpi-card"><div class="kpi-label">${escapeHtml(k)}</div><div class="kpi-value">${v}</div></div>`
    )
    .join("")}</div>`;
}

// --- vertical bar ----------------------------------------------------
function renderBarDist(chart) {
  const data = chart.data;
  const max = Math.max(...data.map((d) => d.count));
  const W = 640;
  const H = 320;
  const padL = 46;
  const padB = 46;
  const padT = 16;
  const padR = 16;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const n = data.length;
  const slot = plotW / n;
  const barW = Math.min(64, slot * 0.62);
  let bars = "";
  let ticks = "";
  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const y = padT + plotH - f * plotH;
    const val = Math.round(max * f);
    ticks += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" class="grid-line"/>`;
    ticks += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" class="axis-label">${val}</text>`;
    return { y, val };
  });
  data.forEach((d, idx) => {
    const h = (d.count / max) * plotH;
    const x = padL + idx * slot + (slot - barW) / 2;
    const y = padT + plotH - h;
    bars += `<rect x="${x}" y="${y}" width="${barW}" height="${h}" rx="3" fill="${SERIES[idx % SERIES.length]}"><title>${escapeHtml(d.label)}: ${d.count}</title></rect>`;
    bars += `<text x="${x + barW / 2}" y="${padT + plotH + 18}" text-anchor="middle" class="axis-label">${escapeHtml(String(d.label).slice(0, 8))}</text>`;
    bars += `<text x="${x + barW / 2}" y="${y - 6}" text-anchor="middle" class="bar-value">${d.count}</text>`;
  });
  return chartCard(chart.title, `维度: ${chart.dimension}`, svg(W, H, ticks + bars));
}

// --- horizontal top-N -------------------------------------------------
function renderHorizTopN(chart) {
  const data = chart.data;
  const max = Math.max(...data.map((d) => d.count));
  const W = 640;
  const H = Math.max(320, data.length * 30 + 40);
  const padL = 150;
  const padR = 60;
  const padT = 12;
  const rowH = 26;
  let bars = "";
  data.forEach((d, idx) => {
    const bw = (d.count / max) * (W - padL - padR);
    const y = padT + idx * rowH;
    bars += `<rect x="${padL}" y="${y}" width="${bw}" height="18" rx="3" fill="${SERIES[idx % SERIES.length]}"><title>${escapeHtml(d.label)}: ${d.count}</title></rect>`;
    bars += `<text x="${padL - 8}" y="${y + 14}" text-anchor="end" class="axis-label">${escapeHtml(String(d.label).slice(0, 16))}</text>`;
    bars += `<text x="${padL + bw + 6}" y="${y + 14}" class="bar-value">${d.count}</text>`;
  });
  return chartCard(chart.title, `维度: ${chart.dimension}（Top ${data.length}）`, svg(W, H, bars));
}

// --- donut -----------------------------------------------------------
function renderDonut(chart) {
  const data = chart.data;
  const total = data.reduce((s, d) => s + d.count, 0);
  const W = 420;
  const H = 300;
  const cx = 170;
  const cy = 150;
  const r = 100;
  const strokeW = 40;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  let arcs = "";
  let legend = "";
  data.forEach((d, idx) => {
    const frac = d.count / total;
    const len = frac * circ;
    const color = d.label === "积极" ? EVAL_COLORS.积极 : d.label === "不佳" ? EVAL_COLORS.不佳 : d.label === "终止" ? EVAL_COLORS.终止 : SERIES[idx % SERIES.length];
    arcs += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="${strokeW}" stroke-dasharray="${len} ${circ - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})"><title>${escapeHtml(d.label)}: ${d.count} (${(frac * 100).toFixed(1)}%)</title></circle>`;
    offset += len;
    legend += `<div class="legend-item"><span class="legend-swatch" style="background:${color}"></span>${escapeHtml(d.label)} — ${d.count} (${(frac * 100).toFixed(1)}%)</div>`;
  });
  arcs += `<text x="${cx}" y="${cy - 4}" text-anchor="middle" class="donut-total">${total}</text>`;
  arcs += `<text x="${cx}" y="${cy + 18}" text-anchor="middle" class="axis-label">记录</text>`;
  const legendHtml = `<div class="legend">${legend}</div>`;
  return chartCard(chart.title, `维度: ${chart.dimension}`, `<div class="donut-wrap">${svg(W, H, arcs)}${legendHtml}</div>`);
}

// --- stacked bar (phase/indication x evaluation) ----------------------
function renderStacked(chart, xKey) {
  const groups = {};
  for (const row of chart.data) {
    const g = row[xKey];
    if (!groups[g]) groups[g] = { 积极: 0, 不佳: 0, 终止: 0 };
    groups[g][row.evaluation] = (groups[g][row.evaluation] || 0) + row.count;
  }
  const keys = Object.keys(groups);
  const max = Math.max(...keys.map((k) => Object.values(groups[k]).reduce((a, b) => a + b, 0)));
  const W = 640;
  const H = Math.max(280, keys.length * 34 + 50);
  const padL = 160;
  const padR = 40;
  const padT = 20;
  const rowH = 28;
  let bars = "";
  keys.forEach((k, idx) => {
    const y = padT + idx * rowH;
    let x = padL;
    for (const evalName of ["积极", "不佳", "终止"]) {
      const c = groups[k][evalName] || 0;
      if (!c) continue;
      const bw = (c / max) * (W - padL - padR);
      bars += `<rect x="${x}" y="${y}" width="${bw}" height="20" rx="2" fill="${EVAL_COLORS[evalName]}"><title>${escapeHtml(k)} · ${evalName}: ${c}</title></rect>`;
      x += bw;
    }
    bars += `<text x="${padL - 8}" y="${y + 15}" text-anchor="end" class="axis-label">${escapeHtml(String(k).slice(0, 18))}</text>`;
  });
  const legend = `<div class="legend"><span class="legend-swatch" style="background:${EVAL_COLORS.积极}"></span>积极<span class="legend-swatch" style="background:${EVAL_COLORS.不佳}"></span>不佳<span class="legend-swatch" style="background:${EVAL_COLORS.终止}"></span>终止</div>`;
  return chartCard(chart.title, `维度: ${chart.dimension.join(" × ")}`, `${legend}${svg(W, H, bars)}`);
}

// --- scatter (evidence) ----------------------------------------------
function renderScatter(chart) {
  const rows = chart.data;
  const maxN = Math.max(...rows.map((r) => r.sample_size || 0), 1);
  const W = 680;
  const H = 340;
  const padL = 60;
  const padB = 44;
  const padT = 16;
  const padR = 24;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const yOf = (e) => (e === "积极" ? 0.22 : e === "不佳" ? 0.5 : 0.78);
  let dots = "";
  rows.forEach((r) => {
    const n = r.sample_size || 0;
    const x = padL + (n / maxN) * plotW;
    const y = padT + yOf(r.evaluation) * plotH;
    const color = EVAL_COLORS[r.evaluation] || "var(--viz-text-muted)";
    dots += `<circle cx="${x}" cy="${y}" r="4.5" fill="${color}" opacity="0.75"><title>${escapeHtml(r.trial || r.title || "")} · n=${n} · ${r.evaluation}</title></circle>`;
  });
  let labels = "";
  for (const [e, f] of [["积极", 0.22], ["不佳", 0.5], ["终止", 0.78]]) {
    const y = padT + f * plotH;
    labels += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" class="grid-line" stroke-dasharray="3 4"/>`;
    labels += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" class="axis-label">${e}</text>`;
  }
  for (const f of [0, 0.25, 0.5, 0.75, 1]) {
    const x = padL + f * plotW;
    labels += `<text x="${x}" y="${H - 18}" text-anchor="middle" class="axis-label">${Math.round(f * maxN)}</text>`;
  }
  labels += `<text x="${padL + plotW / 2}" y="${H - 4}" text-anchor="middle" class="axis-title">样本量</text>`;
  return chartCard(chart.title, `维度: ${chart.dimension.join(" × ")} · ${rows.length} 条证据`, svg(W, H, labels + dots));
}

// --- line (release cumulative) ---------------------------------------
function renderLineCumulative(chart) {
  const rows = chart.data;
  const max = Math.max(...rows.map((r) => r.cumulative || 0), 1);
  const W = 680;
  const H = 320;
  const padL = 56;
  const padB = 44;
  const padT = 16;
  const padR = 24;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const pts = rows.map((r, i) => {
    const x = padL + (i / Math.max(rows.length - 1, 1)) * plotW;
    const y = padT + plotH - ((r.cumulative || 0) / max) * plotH;
    return { x, y, r };
  });
  let path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  let area = `${path} L${pts[pts.length - 1].x},${padT + plotH} L${pts[0].x},${padT + plotH} Z`;
  let inner = "";
  for (const f of [0, 0.25, 0.5, 0.75, 1]) {
    const y = padT + plotH - f * plotH;
    inner += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" class="grid-line"/>`;
    inner += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" class="axis-label">${Math.round(f * max)}</text>`;
  }
  inner += `<path d="${area}" fill="var(--viz-series-1)" opacity="0.18"/>`;
  inner += `<path d="${path}" fill="none" stroke="var(--viz-series-1)" stroke-width="2.5"/>`;
  pts.forEach((p) => {
    inner += `<circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--viz-surface)" stroke="var(--viz-series-1)" stroke-width="2"><title>${p.r.date}: ${p.r.count} 条，累计 ${p.r.cumulative}</title></circle>`;
    inner += `<text x="${p.x}" y="${padT + plotH + 18}" text-anchor="middle" class="axis-label">${p.r.date.slice(5)}</text>`;
  });
  return chartCard(chart.title, `维度: ${chart.dimension.join(",")}`, svg(W, H, inner));
}

// --- network (bipartite layout) --------------------------------------
function renderNetwork(chart) {
  const edges = chart.data;
  const bySource = {};
  const byTarget = {};
  for (const e of edges) {
    bySource[e.source] = (bySource[e.source] || 0) + 1;
    byTarget[e.target] = (byTarget[e.target] || 0) + 1;
  }
  const sources = Object.keys(bySource).sort((a, b) => bySource[b] - bySource[a]);
  const targets = Object.keys(byTarget).sort((a, b) => byTarget[b] - byTarget[a]);
  const maxW = Math.max(...edges.map((e) => e.weight || 1));
  const maxDeg = Math.max(...[...sources, ...targets].map((n) => bySource[n] || byTarget[n] || 1));
  const W = 680;
  const H = Math.max(360, Math.max(sources.length, targets.length) * 26 + 40);
  const colS = 170;
  const colT = W - 170;
  let inner = "";
  edges.forEach((e) => {
    const ys = (sources.indexOf(e.source) + 0.5) * 26 + 20;
    const yt = (targets.indexOf(e.target) + 0.5) * 26 + 20;
    const o = 0.15 + 0.55 * ((e.weight || 1) / maxW);
    inner += `<path d="M${colS},${ys} C${(colS + colT) / 2},${ys} ${(colS + colT) / 2},${yt} ${colT},${yt}" fill="none" stroke="var(--viz-series-2)" stroke-width="${Math.max(0.5, (e.weight || 1) / maxW) * 3}" opacity="${o}"><title>${escapeHtml(e.source)} ↔ ${escapeHtml(e.target)} (${e.weight})</title></path>`;
  });
  sources.forEach((n, i) => {
    const y = (i + 0.5) * 26 + 20;
    const r = 5 + (bySource[n] / maxDeg) * 7;
    inner += `<circle cx="${colS}" cy="${y}" r="${r}" fill="var(--viz-info)"><title>${escapeHtml(n)} (${bySource[n]})</title></circle>`;
    inner += `<text x="${colS - 10}" y="${y + 4}" text-anchor="end" class="axis-label">${escapeHtml(String(n).slice(0, 14))}</text>`;
  });
  targets.forEach((n, i) => {
    const y = (i + 0.5) * 26 + 20;
    const r = 5 + (byTarget[n] / maxDeg) * 7;
    inner += `<circle cx="${colT}" cy="${y}" r="${r}" fill="var(--viz-series-3)"><title>${escapeHtml(n)} (${byTarget[n]})</title></circle>`;
    inner += `<text x="${colT + 10}" y="${y + 4}" class="axis-label">${escapeHtml(String(n).slice(0, 14))}</text>`;
  });
  return chartCard(chart.title, `维度: ${chart.dimension.join(" × ")} · ${edges.length} 条边（Top 120）`, svg(W, H, inner));
}

/* ------------------------------------------------------------------ */
/* 3. Match ::visualization slots to chart data                        */
/* ------------------------------------------------------------------ */

const KEYWORD_RULES = [
  ["评价", (c) => c.type === "bar_distribution" && c.dimension === "evaluation"],
  ["研发阶段", (c) => c.type === "bar_distribution" && c.dimension === "trial_phase"],
  ["疾病阶段", (c) => c.type === "bar_distribution" && c.dimension === "disease_stage"],
  ["治疗线", (c) => c.type === "bar_distribution" && c.dimension === "therapy_line"],
  ["适应症曝光", (c) => c.type === "horizontal_bar_topN" && c.dimension === "indication"],
  ["药物曝光", (c) => c.type === "horizontal_bar_topN" && c.dimension === "drug"],
  ["标志物曝光", (c) => c.type === "horizontal_bar_topN" && c.dimension === "biomarker"],
  ["终点类型", (c) => c.type === "horizontal_bar_topN" && c.dimension === "endpoint"],
  ["占比", (c) => c.type === "pie_donut_share"],
  ["堆叠", (c) => c.type === "stacked_bar_phase_eval"],
  ["适应症 × 评价", (c) => c.type === "stacked_bar_indication_eval"],
  ["证据", (c) => c.type === "scatter_evidence"],
  ["累计", (c) => c.type === "line_release_cumulative"],
  ["网络", (c) => c.type === "network_entity"],
];

function matchChart(title) {
  for (const [kw, test] of KEYWORD_RULES) {
    if (title.includes(kw)) {
      const hit = chartData.charts.find(test);
      if (hit) return hit;
    }
  }
  return null;
}

function renderChart(c) {
  switch (c.type) {
    case "bar_distribution":
      return renderBarDist(c);
    case "horizontal_bar_topN":
      return renderHorizTopN(c);
    case "pie_donut_share":
      return renderDonut(c);
    case "stacked_bar_phase_eval":
      return renderStacked(c, "phase");
    case "stacked_bar_indication_eval":
      return renderStacked(c, "indication");
    case "scatter_evidence":
      return renderScatter(c);
    case "line_release_cumulative":
      return renderLineCumulative(c);
    case "network_entity":
      return renderNetwork(c);
    default:
      return `<div class="chart-card"><div class="chart-title">${escapeHtml(c.title)}</div><pre>${escapeHtml(JSON.stringify(c.data, null, 1))}</pre></div>`;
  }
}

/* ------------------------------------------------------------------ */
/* 4. Assemble                                                         */
/* ------------------------------------------------------------------ */

const bodyHtml = markdownToHtml(reportMd)
  .replace(/<div class="viz-slot" data-title="([^"]*)" data-path="([^"]*)"><\/div>/g, (_m, title, p) => {
    const file = p.split("/").pop();
    if (file === "conference-stats.json") return renderKpi();
    if (file === "watchlist.csv") return `<div class="chart-card"><div class="chart-title">推荐关注清单</div><pre class="csv-pre">${escapeHtml(watchlistCsv)}</pre></div>`;
    const chart = matchChart(title);
    if (!chart) return `<div class="chart-card"><div class="chart-title">${escapeHtml(title)}</div><p class="muted">未匹配到图表数据</p></div>`;
    return renderChart(chart);
  });

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ASCO 2026 临床解读报告</title>
<style>
  :root {
    --viz-background: #f6f8fb;
    --viz-surface: #ffffff;
    --viz-text: #1f2933;
    --viz-text-muted: #6b7a90;
    --viz-border: #dbe3ec;
    --viz-info: #3b82f6;
    --viz-success: #22c55e;
    --viz-warning: #f59e0b;
    --viz-danger: #ef4444;
    --viz-series-1: #3b82f6;
    --viz-series-2: #10b981;
    --viz-series-3: #8b5cf6;
    --viz-series-4: #f59e0b;
    --viz-series-5: #ec4899;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--viz-background);
    color: var(--viz-text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.65;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 32px 20px 80px; }
  h1 { font-size: 26px; border-bottom: 2px solid var(--viz-border); padding-bottom: 10px; }
  h2 { font-size: 20px; margin-top: 34px; border-left: 4px solid var(--viz-info); padding-left: 10px; }
  h3 { font-size: 16px; margin-top: 24px; }
  p { margin: 8px 0; }
  blockquote { margin: 10px 0; padding: 10px 14px; background: color-mix(in oklch, var(--viz-info) 8%, var(--viz-surface)); border-left: 3px solid var(--viz-info); color: var(--viz-text); border-radius: 4px; }
  code { background: color-mix(in oklch, var(--viz-info) 10%, var(--viz-surface)); border-radius: 4px; padding: 1px 5px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em; }
  ul { margin: 8px 0; padding-left: 22px; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }
  th, td { border: 1px solid var(--viz-border); padding: 7px 9px; text-align: left; vertical-align: top; }
  th { background: color-mix(in oklch, var(--viz-info) 8%, var(--viz-surface)); }
  .chart-card { background: var(--viz-surface); border: 1px solid var(--viz-border); border-radius: 10px; padding: 16px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
  .chart-title { font-weight: 600; font-size: 15px; margin-bottom: 2px; }
  .chart-subtitle { color: var(--viz-text-muted); font-size: 12px; margin-bottom: 8px; }
  .chart-svg { width: 100%; height: auto; display: block; }
  .grid-line { stroke: var(--viz-border); stroke-width: 1; }
  .axis-label { fill: var(--viz-text-muted); font-size: 11px; }
  .axis-title { fill: var(--viz-text-muted); font-size: 12px; }
  .bar-value { fill: var(--viz-text); font-size: 11px; font-weight: 600; }
  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 16px 0; }
  .kpi-card { background: var(--viz-surface); border: 1px solid var(--viz-border); border-radius: 10px; padding: 14px 16px; }
  .kpi-label { color: var(--viz-text-muted); font-size: 12px; }
  .kpi-value { font-size: 26px; font-weight: 700; color: var(--viz-info); margin-top: 4px; }
  .legend { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; font-size: 12px; color: var(--viz-text-muted); margin: 6px 0 10px; }
  .legend-item { display: inline-flex; align-items: center; gap: 6px; }
  .legend-swatch { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
  .donut-wrap { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
  .donut-total { fill: var(--viz-text); font-size: 28px; font-weight: 700; }
  .csv-pre { background: #fbfcfe; border: 1px solid var(--viz-border); border-radius: 6px; padding: 10px; font-size: 11px; overflow-x: auto; white-space: pre; line-height: 1.5; color: var(--viz-text-muted); max-height: 420px; }
  .muted { color: var(--viz-text-muted); }
</style>
</head>
<body>
<div class="wrap">
${bodyHtml}
</div>
</body>
</html>
`;

const outPath = path.join(ITER_DIR, "report.html");
fs.writeFileSync(outPath, html, "utf8");
console.log(`[render] wrote ${outPath} (${(fs.statSync(outPath).size / 1024).toFixed(1)} KB)`);
