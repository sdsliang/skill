import fs from "node:fs";
import path from "node:path";
import { getConfig } from "../../POC/src/config.js";

const nctId = String(process.argv[2] || "").trim().toUpperCase();
const outputPath = process.argv[3] || "";
if (!/^NCT\d+$/i.test(nctId)) {
  throw new Error("usage: node --env-file=/home/xupeipeioo1/apps/POC/.env evals/fetch-np-clinical-by-nct.mjs <NCT_ID> [output.json]");
}

const config = getConfig();
if (!config.esHost) {
  throw new Error("es_host_not_configured");
}

const indexName = process.env.NP_CLINICAL_INDEX || "np_clinical";
const response = await fetch(`${config.esHost.replace(/\/$/, "")}/${indexName}/_search`, {
  method: "POST",
  headers: buildHeaders(config),
  body: JSON.stringify({
    size: 1000,
    track_total_hits: true,
    _source: [
      "base.nct_id",
      "base.title",
      "base.paper_title",
      "base.full_article_link",
      "base.paper_release_time_str",
      "source_full_text"
    ],
    query: buildNctQuery(nctId)
  })
});

if (!response.ok) {
  throw new Error(`np_clinical_search_failed:${response.status}:${(await response.text()).slice(0, 500)}`);
}

const payload = await response.json();
const results = (payload.hits?.hits || [])
  .map((hit) => normalizeSource(hit._source || {}))
  .filter((source) => source.source_full_text.trim())
  .sort((left, right) => `${left.source_title}\n${left.source_url}`.localeCompare(`${right.source_title}\n${right.source_url}`));

if (results.length === 0) {
  throw new Error(`np_clinical_nct_not_found:${nctId}`);
}

const output = JSON.stringify({ results }, null, 2) + "\n";
if (outputPath) {
  fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });
  fs.writeFileSync(outputPath, output);
}
process.stdout.write(output);

function buildNctQuery(value) {
  return {
    bool: {
      should: [
        { term: { "base.nct_id.text": value } },
        { term: { "base.nct_id.keyword": value } },
        { match_phrase: { "base.nct_id": value } },
        { match_phrase: { "base.nct_id.text": value } }
      ],
      minimum_should_match: 1
    }
  };
}

function normalizeSource(record) {
  const sourceTitle = firstNonBlank(readText(record?.base?.title), readText(record?.base?.paper_title));
  const sourceUrl = readText(record?.base?.full_article_link);
  const sourcePaperReleaseTime = readText(record?.base?.paper_release_time_str);
  const sourceFullText = readText(record?.source_full_text);

  if (sourceUrl && !/^https?:\/\//i.test(sourceUrl)) {
    throw new Error("np_clinical_source_url_not_absolute");
  }

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
  if (Array.isArray(value?.meta)) {
    return value.meta.map((item) => item?.text).find((item) => typeof item === "string" && item.trim()) || "";
  }
  return "";
}

function firstNonBlank(...values) {
  return values.find((value) => typeof value === "string" && value.trim()) || "";
}

function buildHeaders(config) {
  const headers = { "content-type": "application/json" };
  if (config.esApiKey) {
    headers.authorization = `ApiKey ${config.esApiKey}`;
  } else if (config.esUsername && config.esPassword) {
    headers.authorization = `Basic ${Buffer.from(`${config.esUsername}:${config.esPassword}`).toString("base64")}`;
  }
  return headers;
}
