#!/usr/bin/env node
/**
 * Render the ECharts interactive dashboard by inlining data + echarts.min.js
 * into report-template.html.
 *
 * Inputs:  evals/fixtures/asco-2026-stats.json
 *          evals/iteration-01/asco-2026/watchlist.csv
 *          evals/iteration-01/asco-2026/drug-profiles.json
 *          evals/report-template.html
 *          runtime/echarts.min.js
 * Output:  evals/iteration-01/asco-2026/report.html
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ITER_DIR = path.join(HERE, "iteration-01/asco-2026");

const stats = JSON.parse(fs.readFileSync(path.join(HERE, "fixtures/asco-2026-stats.json"), "utf8"));
const watchlistCsv = fs.readFileSync(path.join(ITER_DIR, "watchlist.csv"), "utf8");
const drugProfiles = JSON.parse(fs.readFileSync(path.join(ITER_DIR, "drug-profiles.json"), "utf8"));
const template = fs.readFileSync(path.join(HERE, "report-template.html"), "utf8");
const echartsSrc = fs.readFileSync(path.join(HERE, "../runtime/echarts.min.js"), "utf8");

/* ---- normalize stats into demo-compatible shape ---- */
const DIST = stats.distributions || {};
const dist = {
  evaluation: DIST.evaluation || [],
  stage: DIST.trial_phase || DIST.stage || [],
  disease_stage: DIST.disease_stage || [],
  indication: DIST.indication || [],
  drug: DIST.drug || [],
  biomarker: DIST.biomarker || [],
  therapy_line: DIST.therapy_line || [],
  endpoint: DIST.endpoint || [],
  release_date: DIST.release_date || [],
  source: DIST.source || [],
};

const evidence = stats.evidence_scatter.map((r) => ({
  id: r.id,
  title: r.title || "",
  trial: r.trial || "",
  stage: r.phase || r.stage || "",
  disease_stage: r.disease_stage || "",
  sample_size: r.sample_size ?? null,
  evaluation: r.evaluation || "",
  indications: r.indications || [],
  drugs: r.drugs || [],
  biomarkers: r.biomarkers || [],
  endpoints: r.endpoints || [],
  efficacy_text: r.efficacy_text || "",
  release_date: r.release_date || "",
}));

const network = stats.entity_network || [];

/* ---- watchlist parse ---- */
function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') { if (line[i + 1] === '"') { cur += '"'; i++; } else inQuotes = false; }
      else cur += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ",") { out.push(cur); cur = ""; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}
const watchlist = watchlistCsv.trim().split("\n").slice(1).map(parseCsvLine).map((f) => ({
  rank: f[0], evidence_id: f[1], title: f[2], trial: f[3], indication: f[4],
  drug: f[5], phase: f[6], sample_size: f[7], evaluation: f[8], score: f[9], reason: f[10],
}));

/* ---- drug lookup index ---- */
const lookup = {};
for (const prof of Object.values(drugProfiles.profiles || {})) {
  const keys = new Set([prof.name, prof.query]);
  for (const a of prof.aliases || []) keys.add(a);
  for (const k of keys) if (k) lookup[String(k).toLowerCase()] = prof;
}

const DATA = {
  overview: stats.overview,
  distributions: dist,
  evidence_scatter: evidence,
  entity_network: network,
  watchlist,
  drug_profiles: drugProfiles.profiles || {},
  drug_lookup: lookup,
};

const safeJson = (v) => JSON.stringify(v).replace(/</g, "\\u003c");

let html = template;
html = html.replace("__ECHARTS__", echartsSrc);
html = html.replace("__DATA__", `window.__CONF_DATA__ = ${safeJson(DATA)};`);
html = html.replace("__BUNDLE__", "window.__CONF_DATA__");
html = html.replace("__GENERATED_AT__", new Date().toLocaleString("zh-CN"));

const out = path.join(ITER_DIR, "report.html");
fs.writeFileSync(out, html);
console.log(`report=${out} (${(fs.statSync(out).size / 1024 / 1024).toFixed(2)} MB)`);
