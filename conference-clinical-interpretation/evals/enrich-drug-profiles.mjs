#!/usr/bin/env node
/**
 * Enrich representative drugs with target / MOA / modality / phase / aliases
 * from the drug_earth dictionary (the "drug table").
 *
 * v2 fixes:
 *   - proper CSV parsing (quoted fields) for watchlist
 *   - strip stray quotes from query names
 *   - noise filter for trial names / fragments
 *   - retry failed lookups (concurrency + limited retries)
 *   - build a name -> profile index (standard name + aliases) for the renderer
 *
 * Output: evals/iteration-01/asco-2026/drug-profiles.json
 *         evals/fixtures/asco-2026-drug-profiles.json
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ITER_DIR = path.join(HERE, "iteration-01/asco-2026");
const LK = "http://116.63.138.41:31887/linking/drug";

const stats = JSON.parse(fs.readFileSync(path.join(HERE, "fixtures/asco-2026-stats.json"), "utf8"));
const watchlistCsv = fs.readFileSync(path.join(ITER_DIR, "watchlist.csv"), "utf8");

/* --- CSV line parser (handles quoted fields) --- */
function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; } else inQuotes = false;
      } else cur += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ",") { out.push(cur); cur = ""; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}

/* --- build candidate drug name set --- */
const candidates = new Set();

for (const line of watchlistCsv.trim().split("\n").slice(1)) {
  const f = parseCsvLine(line);
  if (f[5]) f[5].split("/").forEach((d) => d && candidates.add(d.trim()));
}
for (const d of stats.distributions.drug.slice(0, 25)) candidates.add(d.label);
const reps = stats.evidence_scatter.filter((r) => r.evaluation === "积极" && r.sample_size).slice(0, 40);
for (const r of reps) {
  if (Array.isArray(r.drugs)) r.drugs.forEach((d) => d && candidates.add(d));
  else if (r.drug) candidates.add(r.drug);
}

const strip = (s) => s.replace(/^"+|"+$/g, "").trim();
const NOISE = /phase|study|trial|tumor|癌|症|combination|vs |line|disease|keystone|open|-?\d{2,}|(^|\s)[a-z]{2,3}$/i;
// known trial names that are NOT drugs
const TRIAL_NAMES = new Set(["CHART", "lidERA BC", "KEYNOTE-B15 EV-304", "EV-304", "PROTEUS", "POTOMAC", "MATTERHORN", "REDUSE", "TROPION-Breast02", "CheckMate 8HW", "EV-302", "KEYNOTE-A39", "KEYNOTE-522", "SAKK 96/12", "NCT06304974"]);

const clean = [...candidates].map(strip).filter((d) => d.length >= 2 && d.length <= 24 && !NOISE.test(d) && !TRIAL_NAMES.has(d) && !TRIAL_NAMES.has(d.toUpperCase()));
console.log(`[enrich] candidates=${candidates.size} clean=${clean.length}`);

/* --- query linking API --- */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function linkDrug(name) {
  const res = await fetch(LK, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      input_text: name,
      use_gpt_recommender: false,
      use_cache: true,
      meta_fields_for_output: [
        "name_short", "title", "name_show_cn", "all_name_for_show_en",
        "target_all_name", "moa_all_name", "moa_track_name_cn", "moa_track_name_en",
        "drug_type_1", "drug_type_2", "drug_type_3", "modality_manual",
        "latest_phase", "latest_phase_cn", "first_appr_date", "drugbank_id",
        "dar_value", "company_all_name", "regn_of_originator_right_full", "status",
      ],
      top_k: 1,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function extractProfile(name, data) {
  const md = data.raw_candidates?.[0]?.metadata?.[0];
  if (!md) return null;
  return {
    query: name,
    name: md.name_short || md.title || name,
    aliases: Array.isArray(md.all_name_for_show_en) ? md.all_name_for_show_en.slice(0, 12) : [],
    targets: Array.isArray(md.target_all_name) ? md.target_all_name.slice(0, 6) : [],
    moa_cn: md.moa_track_name_cn || null,
    moa_en: md.moa_track_name_en || null,
    moa_class: Array.isArray(md.moa_all_name) ? md.moa_all_name.slice(0, 4) : [],
    drug_type_1: md.drug_type_1 || null,
    drug_type_2: md.drug_type_2 || null,
    modality: Array.isArray(md.drug_type_3) ? md.drug_type_3 : md.modality_manual || null,
    latest_phase: md.latest_phase || null,
    latest_phase_cn: md.latest_phase_cn || null,
    first_appr_date: md.first_appr_date || null,
    drugbank_id: md.drugbank_id || null,
    dar_value: md.dar_value || null,
    companies: Array.isArray(md.company_all_name) ? md.company_all_name.slice(0, 6) : [],
    originator_regions: Array.isArray(md.regn_of_originator_right_full) ? md.regn_of_originator_right_full.slice(0, 8) : [],
    status: md.status || null,
  };
}

const CONCURRENCY = 5;
const MAX_ATTEMPTS = 3;
const queue = [...new Set(clean)];
const results = {};
let idx = 0;

async function worker() {
  while (idx < queue.length) {
    const name = queue[idx++];
    let data = null;
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      try {
        data = await linkDrug(name);
        break;
      } catch {
        await sleep(300 * attempt);
      }
    }
    if (!data) { process.stdout.write(`  ERR ${name} (after ${MAX_ATTEMPTS} attempts)\n`); continue; }
    const prof = extractProfile(name, data);
    if (!prof) { process.stdout.write(`  -   ${name} (no profile)\n`); continue; }
    // reject clearly-wrong matches: standard name far from query
    const normQ = name.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, "");
    const normN = (prof.name || "").toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, "");
    const related = normQ === normN || normQ.includes(normN) || normN.includes(normQ) || normQ.length < 4 || normN.length < 4;
    if (!related) { process.stdout.write(`  ~   ${name} -> ${prof.name} (mismatch, skip)\n`); continue; }
    results[name] = prof;
    process.stdout.write(`  ok ${name} -> ${prof.name} | ${prof.targets?.[0] || "-"} | ${prof.moa_cn || prof.moa_class?.[0] || "-"}\n`);
  }
}

await Promise.all(Array.from({ length: CONCURRENCY }, worker));

/* --- build lookup index (standard name + aliases + query) --- */
const index = {};
for (const prof of Object.values(results)) {
  const keys = new Set([prof.name, prof.query]);
  for (const a of prof.aliases || []) keys.add(a);
  for (const k of keys) if (k) index[k.toLowerCase()] = prof;
}

const out = {
  schema_version: "2.0.0",
  conference: stats.conference,
  generated_at: new Date().toISOString(),
  source: "drug_earth via Linking API /linking/drug",
  drug_count: Object.keys(results).length,
  profiles: results,
  lookup: index,
};

for (const p of [path.join(ITER_DIR, "drug-profiles.json"), path.join(HERE, "fixtures/asco-2026-drug-profiles.json")]) {
  fs.writeFileSync(p, JSON.stringify(out, null, 2), "utf8");
  console.log(`[enrich] wrote ${p} (${(fs.statSync(p).size / 1024).toFixed(1)} KB, ${Object.keys(results).length} drugs)`);
}
