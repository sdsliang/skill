#!/usr/bin/env node
/**
 * Build a deterministic, lightweight conference-statistics artifact from the
 * raw np_clinical conference snapshot. This stats file is the primary Skill
 * input: it carries distributions, representative evidence, and entity-network
 * edges but NOT full texts. Full texts remain in the raw snapshot only.
 *
 * Usage:
 *   node evals/build-conference-stats.mjs \
 *     evals/fixtures/asco-2026-np-clinical.json \
 *     evals/fixtures/asco-2026-stats.json
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = process.argv[2] || path.join(HERE, "fixtures/asco-2026-np-clinical.json");
const OUT = process.argv[3] || path.join(HERE, "fixtures/asco-2026-stats.json");

const ENDPOINT_PATTERNS = [
  ["OS", /(?:^|[^A-Z])(?:m?OS|overall survival)(?:[^A-Z]|$)/i],
  ["PFS", /(?:^|[^A-Z])(?:m?PFS|progression[- ]free survival)(?:[^A-Z]|$)/i],
  ["DFS", /(?:^|[^A-Z])(?:m?DFS|disease[- ]free survival)(?:[^A-Z]|$)/i],
  ["EFS", /(?:^|[^A-Z])(?:m?EFS|event[- ]free survival)(?:[^A-Z]|$)/i],
  ["RFS", /(?:^|[^A-Z])(?:m?RFS|recurrence[- ]free survival)(?:[^A-Z]|$)/i],
  ["ORR", /(?:^|[^A-Z])(?:ORR|objective response rate)(?:[^A-Z]|$)/i],
  ["DCR", /(?:^|[^A-Z])(?:DCR|disease control rate)(?:[^A-Z]|$)/i],
  ["CR", /(?:^|[^A-Z])(?:c?CR|complete response)(?:[^A-Z]|$)/i],
  ["DoR", /(?:^|[^A-Z])(?:m?DOR|duration of response)(?:[^A-Z]|$)/i],
  ["ctDNA/MRD", /(?:ctDNA|MRD|minimal residual disease)/i],
  ["Safety", /(?:AE|TRAE|TEAE|adverse event|toxicity|safety)/i],
];

const snapshot = JSON.parse(fs.readFileSync(SRC, "utf8"));
const records = snapshot.records || [];
const eligible = records.filter(isAnalysisEligible);

const evaluationCounts = counter();
const phaseCounts = counter();
const diseaseStageCounts = counter();
const indicationCounts = counter();
const drugCounts = counter();
const biomarkerCounts = counter();
const therapyCounts = counter();
const endpointCounts = counter();
const releaseDateCounts = counter();
const sourceCounts = counter();
const scatter = [];
const edges = counter();

for (const row of eligible) {
  const src = row._source || {};
  const evaluations = values(src?.research_design?.evaluation, { preferMeta: true });
  const phases = values(src?.base?.trial_phase, { preferMeta: true });
  const diseaseStages = normalizeDiseaseStages(values(src?.indications?.clinical_stage_new, { preferMeta: true }));
  const indications = values(src?.indications?.indications, { preferMeta: true });
  const drugs = values(src?.base?.trial_drug, { preferMeta: true });
  const biomarkers = values(src?.indications?.bio_labels, { preferMeta: true });
  const therapies = values(src?.indications?.therapy_labels, { preferMeta: true });
  const efficacyText = values(src?.research_design?.opt_dose_effect).join(" | ");
  const endpoints = ENDPOINT_PATTERNS.filter(([, pattern]) => pattern.test(efficacyText)).map(([name]) => name);
  const releaseDate = firstValue(src?.base?.paper_release_time_str);

  addAll(evaluationCounts, evaluations);
  addAll(phaseCounts, phases);
  addAll(diseaseStageCounts, diseaseStages);
  addAll(indicationCounts, indications);
  addAll(drugCounts, drugs);
  addAll(biomarkerCounts, biomarkers);
  addAll(therapyCounts, therapies);
  addAll(endpointCounts, endpoints.length ? endpoints : ["Other/unspecified"]);
  addAll(releaseDateCounts, releaseDate ? [releaseDate] : ["Unknown"]);
  addAll(sourceCounts, src?.source ? [src.source] : ["Unknown"]);

  const sampleSize = parseFirstNumber(firstValue(src?.trial?.group_count));
  scatter.push({
    id: row._id,
    title: firstValue(src?.base?.paper_title),
    trial: firstValue(src?.base?.trial_abbreviation) || firstValue(src?.base?.nct_id),
    phase: phases[0] || "Unknown",
    disease_stage: diseaseStages[0] || "Unknown",
    sample_size: sampleSize,
    evaluation: evaluations[0] || "Unknown",
    indications,
    drugs,
    biomarkers,
    endpoints,
    efficacy_text: efficacyText,
    release_date: releaseDate || null,
  });

  for (const drug of drugs) {
    for (const indication of indications) increment(edges, `${drug}\u0000${indication}`);
    for (const biomarker of biomarkers) increment(edges, `${drug}\u0000${biomarker}`);
  }
}

const stats = {
  schema_version: "1.0.0",
  generated_at: new Date().toISOString(),
  conference: snapshot.conference || null,
  query: snapshot.query || null,
  overview: {
    matched_records: snapshot.overview?.matched_records ?? records.length,
    analysis_eligible_records: eligible.length,
    unique_drugs: drugCounts.size,
    unique_indications: indicationCounts.size,
    unique_biomarkers: biomarkerCounts.size,
    records_with_sample_size: scatter.filter((row) => row.sample_size != null).length,
  },
  distributions: {
    evaluation: sortedCounts(evaluationCounts),
    trial_phase: sortedCounts(phaseCounts),
    disease_stage: sortedCounts(diseaseStageCounts),
    indication: sortedCounts(indicationCounts),
    drug: sortedCounts(drugCounts),
    biomarker: sortedCounts(biomarkerCounts),
    therapy_line: sortedCounts(therapyCounts),
    endpoint: sortedCounts(endpointCounts),
    release_date: sortedCounts(releaseDateCounts, "key"),
    source: sortedCounts(sourceCounts),
  },
  evidence_scatter: scatter,
  entity_network: [...edges.entries()]
    .map(([key, weight]) => {
      const [source, target] = key.split("\u0000");
      return { source, target, weight };
    })
    .sort((a, b) => b.weight - a.weight || a.source.localeCompare(b.source)),
};

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(stats, null, 2) + "\n");
console.log(`[build-stats] eligible=${eligible.length} scatter=${scatter.length} edges=${stats.entity_network.length}`);
console.log(`[build-stats] wrote=${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(1)} KB)`);

function isAnalysisEligible(row) {
  const src = row._source || {};
  const latest = new Set(values(src.latest, { preferMeta: true }));
  const isShow = new Set(values(src.is_show, { preferMeta: true }));
  return !latest.has("否") && !isShow.has("否");
}

function values(node, { preferMeta = false } = {}) {
  const nodes = Array.isArray(node) ? node : node == null ? [] : [node];
  const output = [];
  for (const item of nodes) {
    if (item == null) continue;
    if (typeof item === "string" || typeof item === "number") {
      pushClean(output, item);
      continue;
    }
    const metaValues = (Array.isArray(item.meta) ? item.meta : item.meta ? [item.meta] : [])
      .map((meta) => meta?.text)
      .filter(Boolean);
    if (preferMeta && metaValues.length) {
      for (const value of metaValues) pushClean(output, value);
    } else if (item.text != null) {
      pushClean(output, item.text);
    } else {
      for (const value of metaValues) pushClean(output, value);
    }
  }
  return [...new Set(output)];
}

function firstValue(node) {
  return values(node)[0] || "";
}

function pushClean(output, value) {
  for (const part of String(value).split(/\s*\|\s*/)) {
    const clean = part.trim();
    if (clean && clean !== "-") output.push(clean);
  }
}

function normalizeDiseaseStages(stages) {
  const output = [];
  for (const stage of stages) {
    if (/晚期|advanced|metastatic|metastases|extensive|oligometastatic/i.test(stage)) {
      output.push("晚期/转移");
    } else if (/早期|early/i.test(stage)) {
      output.push("早期");
    } else if (/局部|locally advanced|loco-regional|localized/i.test(stage)) {
      output.push("局部晚期/局部");
    } else if (/III|IIIB|IIIA|II–III|II-III/i.test(stage)) {
      output.push("III期");
    } else if (/II\b|IIA|IIB|II–IIIA|II-IV/i.test(stage)) {
      output.push("II期");
    } else if (/I\b|I期/i.test(stage)) {
      output.push("I期");
    } else if (/IV|IVa/i.test(stage)) {
      output.push("IV期");
    } else {
      output.push("其他/未明确");
    }
  }
  return [...new Set(output)];
}

function parseFirstNumber(value) {
  const match = String(value || "").replace(/,/g, "").match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function counter() {
  return new Map();
}

function addAll(counts, labels) {
  for (const label of new Set(labels)) increment(counts, label);
}

function increment(counts, label) {
  counts.set(label, (counts.get(label) || 0) + 1);
}

function sortedCounts(counts, order = "count") {
  return [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => {
      if (order === "key") return a.label.localeCompare(b.label);
      return b.count - a.count || a.label.localeCompare(b.label);
    });
}
