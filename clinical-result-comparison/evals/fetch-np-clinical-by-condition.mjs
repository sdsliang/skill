import fs from "node:fs";
import path from "node:path";
import { getConfig } from "../../../POC/src/config.js";

const outputPath = process.argv[2] || "evals/fixtures/np-clinical-indications-516-517-phase-featured-false.json";
const size = Number.parseInt(process.argv[3] || "10", 10);
if (!Number.isInteger(size) || size < 1 || size > 100) {
  throw new Error("usage: node --env-file=/home/xupeipeioo1/apps/POC/.env evals/fetch-np-clinical-by-condition.mjs [output.json] [size]");
}

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
          {
            bool: {
              must: [
                { terms: { "indications.indications.meta.id": ["516", "517"] } },
                { terms: { "base.trial_phase.meta.id": ["9567bdf8567c48c3b5368659e63b12f7"] } },
                { terms: { "research_design.evaluation.meta.text": ["积极"] } },
                {
                  bool: {
                    must: [{ exists: { field: "base.nct_id.meta.text" } }],
                    must_not: [{ term: { "base.nct_id.meta.text": "" } }]
                  }
                }
              ]
            }
          },
          {
            bool: {
              must_not: [{ term: { deleted: true } }, { term: { is_delete: "是" } }]
            }
          },
          {
            bool: {
              should: [{ bool: { must: [{ bool: { must: [{ term: { featured: false } }] } }] } }],
              minimum_should_match: 1
            }
          }
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
const results = hits.map((hit) => normalizeSource(hit._source || {})).filter((source) => source.source_full_text.trim());
if (results.length === 0) throw new Error("np_clinical_condition_no_sources_with_full_text");

const output = JSON.stringify({ results }, null, 2) + "\n";
fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });
fs.writeFileSync(outputPath, output);
console.log(JSON.stringify({ output_path: outputPath, matched_total: payload.hits?.total?.value ?? null, returned_hits: hits.length, usable_results: results.length }, null, 2));

function normalizeSource(record) {
  const sourceTitle = firstNonBlank(readText(record?.base?.title), readText(record?.base?.paper_title));
  const sourceUrl = readText(record?.base?.full_article_link);
  const sourcePaperReleaseTime = readText(record?.base?.paper_release_time_str);
  const sourceFullText = readText(record?.source_full_text);
  if (sourceUrl && !/^https?:\/\//i.test(sourceUrl)) throw new Error("np_clinical_source_url_not_absolute");
  return { source_title: sourceTitle, source_url: sourceUrl, source_paper_release_time_str: sourcePaperReleaseTime, source_full_text: sourceFullText };
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
