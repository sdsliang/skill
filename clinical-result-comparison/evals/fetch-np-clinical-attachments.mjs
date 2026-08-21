import fs from "node:fs";
import path from "node:path";
import { getConfig } from "../../../POC/src/config.js";

// Pull a batch of np_clinical results by condition and write one attachment
// file (.md) per selected source, per the attachment input contract.
//
// Default condition: non-small-cell lung cancer (indications 135/5718/5719)
// + phase 3 + positive evaluation ("非小 三期 积极"). Override with env:
//   NP_CLINICAL_ATTACH_INDICATIONS="135,5718,5719"
//   NP_CLINICAL_ATTACH_PHASES="9567bdf8567c48c3b5368659e63b12f7"
//   NP_CLINICAL_ATTACH_EVALUATION="积极"
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

const config = getConfig();
if (!config.esHost) throw new Error("es_host_not_configured");

const indexName = process.env.NP_CLINICAL_INDEX || "np_clinical";
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
      "source_full_text"
    ],
    sort: [{ _id: "asc" }],
    query: {
      bool: {
        must: [
          { terms: { "indications.indications.meta.id": indicationIds } },
          { terms: { "base.trial_phase.meta.id": phaseIds } },
          { terms: { "research_design.evaluation.meta.text": [evaluation] } },
          { bool: { must_not: [{ term: { deleted: true } }, { term: { is_delete: "是" } }] } }
        ]
      }
    }
  })
});

if (!response.ok) {
  throw new Error(`np_clinical_search_failed:${response.status}:${(await response.text()).slice(0, 500)}`);
}

const payload = await response.json();
const hits = payload.hits?.hits || [];
const usable = hits.map((hit) => normalizeSource(hit._source || {})).filter((s) => s.source_full_text.trim());
if (usable.length === 0) throw new Error("np_clinical_condition_no_sources_with_full_text");

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
}
fs.writeFileSync(path.join(absOut, "manifest.json"), JSON.stringify({ condition: { indications: indicationIds, phases: phaseIds, evaluation }, total_matched: payload.hits?.total?.value ?? null, returned_hits: hits.length, usable: usable.length, files }, null, 2) + "\n");

// Round-trip validation: re-read each file and confirm the four consumer fields
// parse back to exactly what was written.
const roundTripErrors = [];
for (let i = 0; i < usable.length; i++) {
  const filePath = path.join(absOut, `source-${String(i + 1).padStart(3, "0")}.md`);
  const parsed = parseSourceFile(fs.readFileSync(filePath, "utf8"));
  const original = usable[i];
  for (const key of ["source_title", "source_url", "source_paper_release_time_str", "source_full_text"]) {
    if (parsed[key] !== original[key]) {
      roundTripErrors.push(`${files[i]}.${key}`);
    }
  }
}
if (roundTripErrors.length > 0) {
  throw new Error(`attachment_roundtrip_mismatch:${roundTripErrors.join(",")}`);
}

console.log(JSON.stringify({
  output_dir: absOut,
  condition: { indications: indicationIds, phases: phaseIds, evaluation },
  matched_total: payload.hits?.total?.value ?? null,
  returned_hits: hits.length,
  written_files: usable.length,
  roundtrip_ok: roundTripErrors.length === 0
}, null, 2));

function renderSourceFile(n, source) {
  return [
    `# 临床结果来源 ${n}`,
    "",
    `source_title: ${source.source_title}`,
    `source_url: ${source.source_url}`,
    `source_paper_release_time_str: ${source.source_paper_release_time_str}`,
    "",
    "## source_full_text",
    "",
    source.source_full_text,
    ""
  ].join("\n");
}

function parseSourceFile(md) {
  const title = md.match(/^source_title: (.*)$/m)?.[1] || "";
  const url = md.match(/^source_url: (.*)$/m)?.[1] || "";
  const time = md.match(/^source_paper_release_time_str: (.*)$/m)?.[1] || "";
  const bodyMatch = md.split("## source_full_text");
  const fullText = bodyMatch.length >= 2 ? bodyMatch.slice(1).join("## source_full_text").trim() : "";
  return { source_title: title, source_url: url, source_paper_release_time_str: time, source_full_text: fullText };
}

function normalizeSource(record) {
  const sourceTitle = firstNonBlank(readText(record?.base?.title), readText(record?.base?.paper_title));
  const sourceUrl = readText(record?.base?.full_article_link);
  const sourcePaperReleaseTime = readText(record?.base?.paper_release_time_str);
  const sourceFullText = readText(record?.source_full_text);

  if (sourceUrl && !/^https?:\/\//i.test(sourceUrl)) throw new Error("np_clinical_source_url_not_absolute");
  return {
    source_title: sourceTitle,
    source_url: sourceUrl,
    source_paper_release_time_str: sourcePaperReleaseTime,
    source_full_text: sourceFullText
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
