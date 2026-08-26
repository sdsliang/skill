import fs from "node:fs";
import path from "node:path";
import { getConfig } from "../../../POC/src/config.js";

// Pull a batch of np_clinical results by condition (or by NCT) and write one
// attachment file (.md) per selected source, per the attachment input contract,
// including optional entity-ID metadata lines (v0.10 drug/company/trial-registry
// and v0.11 trial-abbreviation): source_nct_id / source_trial_abbr /
// source_drug_entities / source_company_entities.
//
// Default condition: non-small-cell lung cancer (indications 135/5718/5719)
// + phase 3 + positive evaluation ("非小 三期 积极"). Override with env:
//   NP_CLINICAL_ATTACH_INDICATIONS="135,5718,5719"
//   NP_CLINICAL_ATTACH_PHASES="9567bdf8567c48c3b5368659e63b12f7"
//   NP_CLINICAL_ATTACH_EVALUATION="积极"
//   NP_CLINICAL_ATTACH_NO_EVALUATION=1        # drop the evaluation filter entirely
//   NP_CLINICAL_ATTACH_NCT="NCT01996267"      # pull a single trial by registry number
//   NP_CLINICAL_ATTACH_ORDER="<doc_id>,<doc_id>"  # explicit output order by document _id (reproduces a historical selection order)
//
// Usage:
//   node --env-file=/home/xupeipeioo1/apps/POC/.env \
//     evals/fetch-np-clinical-attachments.mjs <outputDir> [size]

const outputDir = process.argv[2] || "evals/iteration-16/np-clinical-attachments";
const size = Number.parseInt(process.argv[3] || "50", 10);
if (!Number.isInteger(size) || size < 1 || size > 200) {
  throw new Error("usage: node --env-file=/home/xupeipeioo1/apps/POC/.env evals/fetch-np-clinical-attachments.mjs [outputDir] [size]");
}

const indicationIds = (process.env.NP_CLINICAL_ATTACH_INDICATIONS || "135,5718,5719").split(",").map((s) => s.trim()).filter(Boolean);
const phaseIds = (process.env.NP_CLINICAL_ATTACH_PHASES || "9567bdf8567c48c3b5368659e63b12f7").split(",").map((s) => s.trim()).filter(Boolean);
const evaluation = process.env.NP_CLINICAL_ATTACH_EVALUATION || "积极";
const noEvaluation = process.env.NP_CLINICAL_ATTACH_NO_EVALUATION === "1";
const nctFilter = process.env.NP_CLINICAL_ATTACH_NCT || "";

const config = getConfig();
if (!config.esHost) throw new Error("es_host_not_configured");

const indexName = process.env.NP_CLINICAL_INDEX || "np_clinical";
const notDeleted = { bool: { must_not: [{ term: { deleted: true } }, { term: { is_delete: "是" } }] } };
const query = nctFilter
  ? { bool: { must: [{ match: { "base.nct_id.text": nctFilter } }, notDeleted] } }
  : {
      bool: {
        must: [
          { terms: { "indications.indications.meta.id": indicationIds } },
          { terms: { "base.trial_phase.meta.id": phaseIds } },
          ...(noEvaluation ? [] : [{ terms: { "research_design.evaluation.meta.text": [evaluation] } }]),
          notDeleted
        ]
      }
    };

const response = await fetch(`${config.esHost.replace(/\/$/, "")}/${indexName}/_search`, {
  method: "POST",
  headers: buildHeaders(config),
  body: JSON.stringify({
    size,
    track_total_hits: true,
    _source: [
      "base.title",
      "base.paper_title",
      "base.full_article_link",
      "base.paper_release_time_str",
      "base.nct_id",
      "base.trial_abbreviation",
      "base.trial_drug",
      "trial_details",
      "source_full_text"
    ],
    sort: [{ _id: "asc" }],
    query
  })
});

if (!response.ok) {
  throw new Error(`np_clinical_search_failed:${response.status}:${(await response.text()).slice(0, 500)}`);
}

const payload = await response.json();
const hits = payload.hits?.hits || [];
const usable = hits.map((hit) => normalizeSource(hit._source || {}, hit._id)).filter((s) => s.source_full_text.trim());
if (usable.length === 0) throw new Error("np_clinical_condition_no_sources_with_full_text");

// Optional explicit ordering by document _id (NP_CLINICAL_ATTACH_ORDER), used to
// reproduce a historical selection order (e.g. a single-trial batch that was
// previously hand-ordered). Ids that did not match or have no full text are skipped.
const orderIds = (process.env.NP_CLINICAL_ATTACH_ORDER || "").split(",").map((s) => s.trim()).filter(Boolean);
if (orderIds.length > 0) {
  const byId = new Map(usable.map((s) => [s._docId, s]));
  const reordered = [];
  for (const id of orderIds) {
    const item = byId.get(id);
    if (item) { reordered.push(item); byId.delete(id); }
  }
  usable.length = 0;
  usable.push(...reordered);
}

// Enrich each usable source with optional entity-ID metadata lines (v0.10):
// source_nct_id, source_drug_entities (drug_earth), source_company_entities (base_company).
await enrichEntityMetadata(usable, config);

const absOut = path.resolve(outputDir);
fs.mkdirSync(absOut, { recursive: true });

const files = [];
for (let i = 0; i < usable.length; i++) {
  const n = i + 1;
  const filename = `source-${String(n).padStart(3, "0")}.md`;
  const filePath = path.join(absOut, filename);
  const md = renderSourceFile(n, usable[i]);
  fs.writeFileSync(filePath, md);
  files.push({ order: n, filename, source: usable[i] });
}fs.writeFileSync(path.join(absOut, "manifest.json"), JSON.stringify({ condition: { nct_id: nctFilter || null, indications: nctFilter ? [] : indicationIds, phases: nctFilter ? [] : phaseIds, evaluation: noEvaluation || nctFilter ? null : evaluation }, total_matched: payload.hits?.total?.value ?? null, returned_hits: hits.length, usable: usable.length, files }, null, 2) + "\n");

// Round-trip validation: re-read each file and confirm the four consumer fields
// parse back to exactly what was written.
const roundTripErrors = [];
for (let i = 0; i < usable.length; i++) {
  const filePath = path.join(absOut, `source-${String(i + 1).padStart(3, "0")}.md`);
  const parsed = parseSourceFile(fs.readFileSync(filePath, "utf8"));
  const original = usable[i];
  for (const key of ["source_title", "source_url", "source_paper_release_time_str", "source_nct_id", "source_trial_abbr", "source_drug_entities", "source_company_entities", "source_full_text"]) {
    if ((parsed[key] || "") !== (original[key] || "")) {
      roundTripErrors.push(`${files[i].filename}.${key}`);
    }
  }
}
if (roundTripErrors.length > 0) {
  throw new Error(`attachment_roundtrip_mismatch:${roundTripErrors.join(",")}`);
}

console.log(JSON.stringify({
  output_dir: absOut,
  condition: { nct_id: nctFilter || null, indications: nctFilter ? [] : indicationIds, phases: nctFilter ? [] : phaseIds, evaluation: noEvaluation || nctFilter ? null : evaluation },
  matched_total: payload.hits?.total?.value ?? null,
  returned_hits: hits.length,
  written_files: usable.length,
  roundtrip_ok: roundTripErrors.length === 0
}, null, 2));

function renderSourceFile(n, source) {
  const lines = [
    `# 临床结果来源 ${n}`,
    "",
    `source_title: ${source.source_title}`,
    `source_url: ${source.source_url}`,
    `source_paper_release_time_str: ${source.source_paper_release_time_str}`
  ];
  if (source.source_nct_id) lines.push(`source_nct_id: ${source.source_nct_id}`);
  if (source.source_trial_abbr) lines.push(`source_trial_abbr: ${source.source_trial_abbr}`);
  if (source.source_drug_entities) lines.push(`source_drug_entities: ${source.source_drug_entities}`);
  if (source.source_company_entities) lines.push(`source_company_entities: ${source.source_company_entities}`);
  lines.push("", "## source_full_text", "", source.source_full_text, "");
  return lines.join("\n");
}

function parseSourceFile(md) {
  const title = md.match(/^source_title: (.*)$/m)?.[1] || "";
  const url = md.match(/^source_url: (.*)$/m)?.[1] || "";
  const time = md.match(/^source_paper_release_time_str: (.*)$/m)?.[1] || "";
  const nct = md.match(/^source_nct_id: (.*)$/m)?.[1] || "";
  const abbr = md.match(/^source_trial_abbr: (.*)$/m)?.[1] || "";
  const drugs = md.match(/^source_drug_entities: (.*)$/m)?.[1] || "";
  const companies = md.match(/^source_company_entities: (.*)$/m)?.[1] || "";
  const bodyMatch = md.split("## source_full_text");
  const fullText = bodyMatch.length >= 2 ? bodyMatch.slice(1).join("## source_full_text").trim() : "";
  return { source_title: title, source_url: url, source_paper_release_time_str: time, source_nct_id: nct, source_trial_abbr: abbr, source_drug_entities: drugs, source_company_entities: companies, source_full_text: fullText };
}

async function enrichEntityMetadata(usable, config) {
  const headers = buildHeaders(config);
  const es = config.esHost.replace(/\/$/, "");

  for (const s of usable) {
    s.source_nct_id = extractNctId(s._record);
    s.source_trial_abbr = extractTrialAbbr(s._record);
    s.source_drug_entities = serializeTuples(extractDrugEntities(s._record));
    s.source_company_entities = await resolveCompanyTuples(s._record, es, headers);
  }

  // Drop the raw record and doc-id references before rendering/manifest
  // (never printed into the file; _id must not leak into the manifest either).
  for (const s of usable) { delete s._record; delete s._docId; }
}

function extractNctId(record) {
  const raw = readText(record?.base?.nct_id);
  if (!raw) return "";
  const tokens = raw.split(/\s*\|\s*|\s*[,，;；]\s*/).map((t) => t.trim()).filter(Boolean);
  if (tokens.length === 0) return "";
  const preferred = tokens.find((t) => /^NCT[\dA-Z]+$/i.test(t)) || tokens[0];
  return /^[A-Za-z][A-Za-z0-9-]*$/i.test(preferred) ? preferred : "";
}

// Trial abbreviation / study short name from base.trial_abbreviation. Shape is
// either an object {text} or an array of such objects (aliases). All non-blank
// texts are kept (dedup, order preserved) joined with "; " (v0.11). Values
// containing ";" or "|" are dropped to stay consistent with the tuple rule.
function extractTrialAbbr(record) {
  const raw = record?.base?.trial_abbreviation;
  if (!raw) return "";
  const texts = [];
  const items = Array.isArray(raw) ? raw : [raw];
  for (const item of items) {
    const t = typeof item === "string" ? item : item?.text;
    if (typeof t === "string" && t.trim() && !/[|;]/.test(t)) texts.push(t.trim());
  }
  return [...new Set(texts)].join("; ");
}

function extractDrugEntities(record) {
  const items = Array.isArray(record?.base?.trial_drug) ? record.base.trial_drug : [];
  const out = [];
  for (const item of items) {
    const metas = Array.isArray(item?.meta) ? item.meta : [];
    for (const m of metas) {
      if (!m || !m.id) continue;
      const index = m.index || "drug_earth";
      const name = firstNonBlank(m.text, item.text);
      if (!name || /[|;]/.test(name)) continue;
      out.push({ name, index, id: String(m.id) });
    }
  }
  return out;
}

async function resolveCompanyTuples(record, es, headers) {
  const ids = collectCompanyIds(record);
  if (ids.length === 0) return "";
  const names = await batchResolveCompanyNames(ids, es, headers);
  const tuples = [];
  for (const id of ids) {
    const name = names.get(id);
    if (!name || /[|;]/.test(name)) continue;
    tuples.push({ name, index: "base_company", id });
  }
  return serializeTuples(tuples);
}

function collectCompanyIds(record) {
  const found = new Set();
  (function walk(node) {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) { node.forEach(walk); return; }
    if (Array.isArray(node.company_ids)) {
      for (const id of node.company_ids) if (typeof id === "string" && /^\d+$/.test(id)) found.add(id);
    }
    for (const value of Object.values(node)) walk(value);
  })(record?.trial_details);
  return [...found];
}

async function batchResolveCompanyNames(ids, es, headers) {
  const map = new Map();
  for (let i = 0; i < ids.length; i += 200) {
    const chunk = ids.slice(i, i + 200);
    const response = await fetch(`${es}/base_company/_search`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        size: chunk.length,
        _source: ["id", "name", "short_name", "name_show_cn"],
        query: { terms: { id: chunk } }
      })
    });
    if (!response.ok) continue;
    const payload = await response.json();
    for (const hit of payload.hits?.hits || []) {
      const src = hit._source || {};
      const name = firstNonBlank(src.name_show_cn, src.short_name, src.name);
      if (src.id && name) map.set(String(src.id), name);
    }
  }
  return map;
}

function serializeTuples(tuples) {
  return tuples.map((t) => `${t.name}|${t.index}|${t.id}`).join("; ");
}

function normalizeSource(record, docId) {
  const sourceTitle = firstNonBlank(readText(record?.base?.title), readText(record?.base?.paper_title));
  const sourceUrl = readText(record?.base?.full_article_link);
  const sourcePaperReleaseTime = readText(record?.base?.paper_release_time_str);
  const sourceFullText = readText(record?.source_full_text);

  if (sourceUrl && !/^https?:\/\//i.test(sourceUrl)) throw new Error("np_clinical_source_url_not_absolute");
  return {
    source_title: sourceTitle,
    source_url: sourceUrl,
    source_paper_release_time_str: sourcePaperReleaseTime,
    source_full_text: sourceFullText,
    _record: record,
    _docId: docId
  };
}

function readText(value) {
  if (typeof value === "string") return value;
  if (value && typeof value.text === "string") return value.text;
  if (Array.isArray(value?.meta)) return value.meta.map((item) => item?.text).find((item) => typeof item === "string" && item.trim()) || "";
  return "";
}

function firstNonBlank(...values) {
  return values.find((value) => typeof value === "string" && value.trim()) || "";
}

function buildHeaders(config) {
  const headers = { "content-type": "application/json" };
  if (config.esApiKey) headers.authorization = `ApiKey ${config.esApiKey}`;
  else if (config.esUsername && config.esPassword) headers.authorization = `Basic ${Buffer.from(`${config.esUsername}:${config.esPassword}`).toString("base64")}`;
  return headers;
}
