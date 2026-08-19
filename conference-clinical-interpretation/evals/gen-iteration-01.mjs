#!/usr/bin/env node
/**
 * Generate the Skill-defined data files for iteration-01:
 *   - chart-data.json   (whitelisted chart types + whitelisted dimensions only)
 *   - watchlist.csv     (value-ranked, NOT volume-ranked, watchlist)
 *
 * This simulates the model's constrained structured-analysis output per
 * chart-contract.md / watchlist.md. Deterministic; frontend maps enums to templates.
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STATS = process.argv[2] || path.join(HERE, "fixtures/asco-2026-stats.json");
const OUT_DIR = process.argv[3] || path.join(HERE, "iteration-01/asco-2026");

const stats = JSON.parse(fs.readFileSync(STATS, "utf8"));
const { distributions, evidence_scatter: scatter, entity_network: network, overview } = stats;
const byId = new Map(scatter.map((row) => [row.id, row]));

const charts = [];
const push = (chart) => charts.push(chart);

// 1) kpi_summary
push({
  type: "kpi_summary",
  title: "会议关键指标",
  dimension: "overview",
  data: [
    { label: "匹配记录数", value: overview.matched_records },
    { label: "分析合格记录数", value: overview.analysis_eligible_records },
    { label: "唯一药物数", value: overview.unique_drugs },
    { label: "唯一适应症数", value: overview.unique_indications },
    { label: "唯一生物标志物数", value: overview.unique_biomarkers },
    { label: "有样本量记录数", value: overview.records_with_sample_size },
  ],
});

// 2) bar_distribution: evaluation / trial_phase / disease_stage / therapy_line
for (const [dim, key] of [
  ["evaluation", "evaluation"],
  ["trial_phase", "trial_phase"],
  ["disease_stage", "disease_stage"],
  ["therapy_line", "therapy_line"],
]) {
  push({
    type: "bar_distribution",
    title: `记录按${dim}分布`,
    dimension: key,
    data: distributions[key],
  });
}

// 3) horizontal_bar_topN: indication / drug / biomarker / endpoint
for (const [dim, key, title] of [
  ["indication", "indication", "Top 15 适应症曝光"],
  ["drug", "drug", "Top 15 药物曝光"],
  ["biomarker", "biomarker", "Top 10 生物标志物曝光"],
  ["endpoint", "endpoint", "Top 10 终点类型"],
]) {
  push({
    type: "horizontal_bar_topN",
    title,
    dimension: key,
    top_n: dim === "biomarker" || dim === "endpoint" ? 10 : 15,
    data: distributions[key].slice(0, dim === "biomarker" || dim === "endpoint" ? 10 : 15),
  });
}

// 4) pie_donut_share: evaluation / trial_phase
for (const [dim, key] of [
  ["evaluation", "evaluation"],
  ["trial_phase", "trial_phase"],
]) {
  push({
    type: "pie_donut_share",
    title: `${dim}占比`,
    dimension: key,
    data: distributions[key],
  });
}

// 5) stacked_bar_phase_eval: trial_phase × evaluation
{
  const map = new Map();
  for (const row of scatter) {
    const key = `${row.phase}\u0000${row.evaluation}`;
    map.set(key, (map.get(key) || 0) + 1);
  }
  const data = [...map.entries()].map(([k, count]) => {
    const [phase, evaluation] = k.split("\u0000");
    return { phase, evaluation, count };
  });
  push({
    type: "stacked_bar_phase_eval",
    title: "研发阶段 × 评价",
    dimension: ["trial_phase", "evaluation"],
    data,
  });
}

// 6) stacked_bar_indication_eval: indication(TopN) × evaluation
{
  const topIndications = new Set(distributions.indication.slice(0, 10).map((x) => x.label));
  const map = new Map();
  for (const row of scatter) {
    const indication = row.indications[0] || "Unknown";
    if (!topIndications.has(indication)) continue;
    const key = `${indication}\u0000${row.evaluation}`;
    map.set(key, (map.get(key) || 0) + 1);
  }
  const data = [...map.entries()].map(([k, count]) => {
    const [indication, evaluation] = k.split("\u0000");
    return { indication, evaluation, count };
  });
  push({
    type: "stacked_bar_indication_eval",
    title: "Top 10 适应症 × 评价",
    dimension: ["indication", "evaluation"],
    data,
  });
}

// 7) scatter_evidence: representative evidence (phase>=2 & positive, large n)
{
  const evaluationRank = { 积极: 3, 不佳: 1, 终止: 0 };
  const candidates = scatter
    .filter((row) => row.sample_size != null && (row.phase.includes("II") || row.phase.includes("III")))
    .sort((a, b) => (evaluationRank[b.evaluation] || 0) - (evaluationRank[a.evaluation] || 0) || b.sample_size - a.sample_size);
  const data = candidates.slice(0, 60).map((row) => ({
    id: row.id,
    title: row.title,
    trial: row.trial,
    phase: row.phase,
    sample_size: row.sample_size,
    evaluation: row.evaluation,
    indication: row.indications[0] || "Unknown",
  }));
  push({
    type: "scatter_evidence",
    title: "代表性证据（样本量 × 评价）",
    dimension: ["sample_size", "evaluation"],
    data,
  });
}

// 8) line_release_cumulative: release_date cumulative
{
  const byDate = new Map();
  for (const row of scatter) {
    if (!row.release_date) continue;
    byDate.set(row.release_date, (byDate.get(row.release_date) || 0) + 1);
  }
  const dates = [...byDate.keys()].sort();
  let cumulative = 0;
  const data = dates.map((date) => {
    cumulative += byDate.get(date);
    return { date, count: byDate.get(date), cumulative };
  });
  push({
    type: "line_release_cumulative",
    title: "发布日期累计曲线",
    dimension: ["release_date"],
    data,
  });
}

// 9) network_entity: drug ↔ indication / biomarker
{
  const data = network
    .map((edge) => ({ ...edge }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 120);
  push({
    type: "network_entity",
    title: "药物–适应症/标志物关系网络（Top 120 边）",
    dimension: ["drug", "indication|biomarker"],
    data,
  });
}

// ---------- watchlist.csv (value-ranked, NOT volume-ranked) ----------
const evaluationRank = { 积极: 3, 不佳: 1, 终止: 0 };
const phaseScore = { "III期": 25, "II/III期": 22, "II期": 18, "I/II期": 14, "I期": 10, "IV期": 10 };
const endpointScore = (endpoints) =>
  Math.min(15, endpoints.length * 6 + (endpoints.includes("OS") ? 4 : 0));

// Prefer immunotherapy/targeted/novel mechanisms over chemo adjuvants when
// picking the representative drug for the watchlist (热度≠记录数 principle).
const CHEMO_ADJUVANT = /(奥沙利铂|氟尿嘧啶|卡铂|亚叶酸|顺铂|卡培他滨|表柔比星|多柔比星|紫杉醇|多西他赛|环磷酰胺|吉西他滨|伊立替康|培美曲塞)/;
const NOVEL_MECHANISM = /(免疫|双抗|ADC|细胞|CAR-T|疫苗|偶联|单抗|抑制剂|抗体)/;
function pickDrug(drugs) {
  if (!drugs.length) return "";
  const novel = drugs.find((d) => NOVEL_MECHANISM.test(d) && !CHEMO_ADJUVANT.test(d));
  return novel || drugs[0];
}

function scoreRow(row) {
  const phase = phaseScore[row.phase] ?? 10;
  const evaluation = (evaluationRank[row.evaluation] || 0) * 8; // 0..24
  const sample = row.sample_size == null ? 12 : Math.min(20, Math.round((row.sample_size / 1500) * 20));
  const endpoint = endpointScore(row.endpoints);
  const novelty = row.drugs.some((d) => /(免疫|双抗|ADC|细胞|CAR-T|疫苗|偶联)/.test(d)) ? 10 : row.drugs.length ? 6 : 4;
  return Math.min(100, Math.round(phase + evaluation + sample + endpoint + novelty));
}

const watchlist = scatter
  .filter((row) => (evaluationRank[row.evaluation] || 0) >= 1)
  .map((row) => ({ ...row, score: scoreRow(row) }))
  .sort((a, b) => b.score - a.score)
  .slice(0, 15);

fs.mkdirSync(OUT_DIR, { recursive: true });

const chartData = {
  schema_version: "1.0.0",
  conference: stats.conference,
  generated_at: new Date().toISOString(),
  charts,
};
fs.writeFileSync(path.join(OUT_DIR, "chart-data.json"), JSON.stringify(chartData, null, 2) + "\n");

const csvHeader = "rank,evidence_id,title,trial,indication,drug,phase,sample_size,evaluation,score,reason";
const csvRows = watchlist.map((row, i) => {
  const reason = buildReason(row, i + 1);
  const csvCell = (value) => `"${String(value ?? "").replace(/"/g, '""').replace(/\n/g, " ")}"`;
  return [
    i + 1,
    csvCell(row.id),
    csvCell(row.title),
    csvCell(row.trial),
    csvCell(row.indications[0] || ""),
    csvCell(pickDrug(row.drugs)),
    csvCell(row.phase),
    row.sample_size ?? "",
    csvCell(row.evaluation),
    row.score,
    csvCell(reason),
  ].join(",");
});
fs.writeFileSync(path.join(OUT_DIR, "watchlist.csv"), [csvHeader, ...csvRows].join("\n") + "\n");

console.log(`[gen-iteration-01] charts=${charts.length} watchlist=${watchlist.length}`);
console.log(`[gen-iteration-01] wrote ${path.join(OUT_DIR, "chart-data.json")} and ${path.join(OUT_DIR, "watchlist.csv")}`);

function buildReason(row, rank) {
  const parts = [];
  parts.push(`${row.phase}${row.evaluation === "积极" ? "积极结果" : "证据"}`);
  if (row.sample_size != null) parts.push(`n=${row.sample_size}`);
  if (row.endpoints.length) parts.push(`终点:${row.endpoints.slice(0, 3).join("/")}`);
  if (row.drugs.length) parts.push(`药物:${row.drugs.slice(0, 2).join("/")}`);
  return parts.join("；");
}
