import { getConfig } from "../../POC/src/config.js";

const selectedIds = process.argv.slice(2).map((value) => String(value || "").trim()).filter(Boolean);
if (selectedIds.length === 0) {
  throw new Error("usage: node --env-file=/home/xupeipeioo1/apps/POC/.env evals/fetch-np-clinical-sources.mjs <selected-id> [...selected-id]");
}

const config = getConfig();
if (!config.esHost) {
  throw new Error("es_host_not_configured");
}

const indexName = process.env.NP_CLINICAL_INDEX || "np_clinical";
const ids = selectedIds.map(toElasticsearchId);
const response = await fetch(`${config.esHost.replace(/\/$/, "")}/${indexName}/_search`, {
  method: "POST",
  headers: buildHeaders(config),
  body: JSON.stringify({
    size: selectedIds.length,
    _source: [
      "base.title",
      "base.paper_title",
      "base.full_article_link",
      "base.paper_release_time_str",
      "source_full_text"
    ],
    query: {
      ids: {
        values: ids
      }
    }
  })
});

if (!response.ok) {
  throw new Error(`np_clinical_search_failed:${response.status}:${(await response.text()).slice(0, 500)}`);
}

const hits = (await response.json()).hits?.hits || [];
const recordsById = new Map(hits.map((hit) => [String(hit._id), normalizeSource(hit._source || {})]));
const missingIds = ids.filter((id) => !recordsById.has(id));
if (missingIds.length > 0) {
  throw new Error(`np_clinical_records_not_found:${missingIds.length}`);
}

const results = ids.map((id) => recordsById.get(id));
console.log(JSON.stringify({ results }, null, 2));

function normalizeSource(record) {
  const sourceTitle = firstNonBlank(readText(record?.base?.title), readText(record?.base?.paper_title));
  const sourceUrl = readText(record?.base?.full_article_link);
  const sourcePaperReleaseTime = readText(record?.base?.paper_release_time_str);
  const sourceFullText = readText(record?.source_full_text);

  if (!sourceFullText.trim()) {
    throw new Error("np_clinical_source_full_text_missing");
  }
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
  if (typeof value === "string") {
    return value;
  }
  if (value && typeof value.text === "string") {
    return value.text;
  }
  if (Array.isArray(value?.meta)) {
    return value.meta.map((item) => item?.text).find((item) => typeof item === "string" && item.trim()) || "";
  }
  return "";
}

function firstNonBlank(...values) {
  return values.find((value) => typeof value === "string" && value.trim()) || "";
}

function toElasticsearchId(value) {
  const parts = value.split("::");
  return parts.at(-1).trim();
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
