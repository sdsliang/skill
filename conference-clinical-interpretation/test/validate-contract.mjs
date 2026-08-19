#!/usr/bin/env node
/**
 * Contract validation for the conference-clinical-interpretation skill.
 *
 * Checks:
 *  1. chart-data.json only uses whitelisted chart types + whitelisted dimensions
 *  2. watchlist.csv has the full field contract and evidence_ids exist in stats
 *  3. report.md ::visualization references point to existing files
 *  4. report.md evidence IDs exist in stats evidence_scatter
 *  5. SKILL.md <-> system prompt <-> dist zip sync markers
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");

const WHITELISTED_TYPES = new Set([
  "bar_distribution",
  "horizontal_bar_topN",
  "pie_donut_share",
  "stacked_bar_phase_eval",
  "stacked_bar_indication_eval",
  "scatter_evidence",
  "line_release_cumulative",
  "network_entity",
  "kpi_summary",
  "table_watchlist",
]);

const WHITELISTED_DIMENSIONS = new Set([
  "overview",
  "evaluation",
  "trial_phase",
  "disease_stage",
  "therapy_line",
  "indication",
  "drug",
  "biomarker",
  "endpoint",
  "release_date",
  "source",
  "sample_size",
  "trial_phase,evaluation",
  "indication,evaluation",
  "sample_size,evaluation",
  "drug,indication|biomarker",
]);

const failures = [];
const ok = (msg) => console.log(`  ok - ${msg}`);
const fail = (msg) => {
  failures.push(msg);
  console.error(`  FAIL - ${msg}`);
};

function readJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), "utf8"));
}

console.log("== 1. chart-data.json contract ==");
const chartDataPath = process.argv[2] || "evals/iteration-01/asco-2026/chart-data.json";
if (!fs.existsSync(path.join(ROOT, chartDataPath))) {
  fail(`chart-data.json not found: ${chartDataPath}`);
} else {
  const chartData = readJson(chartDataPath);
  for (const chart of chartData.charts) {
    if (!WHITELISTED_TYPES.has(chart.type)) fail(`chart type not whitelisted: ${chart.type}`);
    const dimKey = Array.isArray(chart.dimension) ? chart.dimension.join(",") : chart.dimension;
    if (!WHITELISTED_DIMENSIONS.has(dimKey)) fail(`chart dimension not whitelisted: ${dimKey}`);
    if (!Array.isArray(chart.data) || chart.data.length === 0) fail(`chart empty data: ${chart.type}`);
    for (const point of chart.data) {
      for (const key of ["label", "count"]) {
        if (point && typeof point[key] !== "undefined" && typeof point[key] !== "string" && typeof point[key] !== "number") {
          fail(`chart data point invalid ${key}: ${JSON.stringify(point[key]).slice(0, 40)}`);
        }
      }
    }
  }
  ok(`all ${chartData.charts.length} charts use whitelisted types/dimensions`);
}

console.log("== 2. watchlist.csv contract ==");
const watchlistPath = process.argv[3] || "evals/iteration-01/asco-2026/watchlist.csv";
const stats = readJson("evals/fixtures/asco-2026-stats.json");
const ids = new Set(stats.evidence_scatter.map((r) => r.id));
if (!fs.existsSync(path.join(ROOT, watchlistPath))) {
  fail(`watchlist.csv not found: ${watchlistPath}`);
} else {
  const csv = fs.readFileSync(path.join(ROOT, watchlistPath), "utf8");
  const lines = csv.trim().split("\n");
  const header = lines[0];
  const expectedHeader = "rank,evidence_id,title,trial,indication,drug,phase,sample_size,evaluation,score,reason";
  if (header !== expectedHeader) fail(`watchlist header mismatch: ${header}`);
  let rowsOk = 0;
  for (const line of lines.slice(1)) {
    if (!line.trim()) continue;
    const fields = parseCsvLine(line);
    if (fields.length !== 11) {
      fail(`watchlist row has ${fields.length} fields (expected 11): ${line.slice(0, 60)}`);
      continue;
    }
    const [rank, evidenceId] = fields;
    if (!/^\d+$/.test(rank)) fail(`watchlist rank not numeric: ${rank}`);
    if (!ids.has(evidenceId)) fail(`watchlist evidence_id not in stats: ${evidenceId}`);
    rowsOk++;
  }
  ok(`watchlist has ${rowsOk} valid rows`);
}

console.log("== 3. report.md ::visualization references ==");
const reportPath = process.argv[4] || "evals/iteration-01/asco-2026/report.md";
if (!fs.existsSync(path.join(ROOT, reportPath))) {
  fail(`report.md not found: ${reportPath}`);
} else {
  const report = fs.readFileSync(path.join(ROOT, reportPath), "utf8");
  const refs = [...report.matchAll(/::visualization\[[^\]]*\]\{path="([^"]+)"\}/g)];
  if (refs.length === 0) fail("report has no ::visualization references");
  const outDir = path.dirname(path.join(ROOT, reportPath));
  for (const match of refs) {
    const filePath = match[1];
    const filename = filePath.split("/").pop();
    if (!filePath.startsWith("/workspace/visualizations/")) {
      fail(`reference path not under /workspace/visualizations/: ${filePath}`);
    }
    if (!fs.existsSync(path.join(outDir, filename))) {
      fail(`referenced visualization file missing: ${filename} (not in ${outDir})`);
    }
  }
  ok(`report has ${refs.length} valid ::visualization references`);

  // evidence ids in report
  const idsInReport = [...report.matchAll(/证据:?\s*([0-9a-f_]{10,})/g)].map((m) => m[1]);
  let badIds = 0;
  for (const id of idsInReport) {
    if (!ids.has(id)) {
      fail(`report evidence id not in stats: ${id}`);
      badIds++;
    }
  }
  if (badIds === 0) ok(`all ${idsInReport.length} evidence ids in report are valid`);
}

console.log("== 4. SKILL <-> system prompt <-> dist sync markers ==");
const skill = fs.readFileSync(path.join(ROOT, "skill/conference-clinical-interpretation/SKILL.md"), "utf8");
const sysprompt = fs.readFileSync(path.join(ROOT, "system-prompts/conference-clinical-interpretation-v0.1.md"), "utf8");
const distDir = path.join(ROOT, "dist");
const distZip = path.join(distDir, "conference-clinical-interpretation-v0.1.zip");

const markerPairs = [
  ["热度≠记录数", "热度 ≠ 记录数"],
  ["chart-data.json", "chart-data.json"],
  ["watchlist.csv", "watchlist.csv"],
  ["::visualization", "::visualization"],
  ["不生成 ECharts", "不生成 ECharts"],
];
for (const [skillMarker, sysMarker] of markerPairs) {
  if (!skill.includes(skillMarker)) fail(`SKILL.md missing marker: ${skillMarker}`);
  if (!sysprompt.includes(sysMarker)) fail(`system prompt missing marker: ${sysMarker}`);
}
ok("SKILL.md and system prompt share all sync markers");

if (!fs.existsSync(distZip)) {
  fail(`dist zip missing: ${distZip} (run dist build script)`);
} else {
  ok(`dist zip exists: ${distZip}`);
}

if (failures.length) {
  console.error(`\n${failures.length} contract failure(s)`);
  process.exit(1);
}
console.log("\nAll contract checks passed");
process.exit(0);

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}
