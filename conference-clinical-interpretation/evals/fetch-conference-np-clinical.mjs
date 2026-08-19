#!/usr/bin/env node
/**
 * Fetch all np_clinical records for a medical conference (base.journal match)
 * and write a reproducible, consumer-safe snapshot used as Skill input.
 *
 * Usage:
 *   node --env-file=/home/xupeipeioo1/apps/POC/.env evals/fetch-conference-np-clinical.mjs \
 *     evals/fixtures/asco-2026-np-clinical.json "ASCO 2026"
 *
 * Output JSON shape (stable schema):
 * {
 *   "schema_version": "1.0.0",
 *   "conference": "ASCO 2026",
 *   "index": "np_clinical",
 *   "generated_at": "<iso>",
 *   "query": {...},                 // reproducible filter definition
 *   "overview": {...},              // matched / eligible counts
 *   "records": [ ... ]              // one per matched record, normalized
 * }
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { getConfig } from "../../../POC/src/config.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = process.argv[2] || path.join(HERE, "fixtures/asco-2026-np-clinical.json");
const CONFERENCE = process.argv[3] || "ASCO 2026";

const config = getConfig();
const host = (config.esHost || config.host || "").replace(/\/$/, "");
const indexName = config.npClinicalIndex || "np_clinical";
const pageSize = 500;

const headers = { "Content-Type": "application/json" };
if (config.esApiKey) headers.Authorization = `ApiKey ${config.esApiKey}`;
else if (config.esUsername && config.esPassword) {
  headers.Authorization = `Basic ${Buffer.from(`${config.esUsername}:${config.esPassword}`).toString("base64")}`;
}

const FILTER = {
  bool: {
    filter: [
      {
        bool: {
          should: [
            { term: { "base.journal.text": CONFERENCE } },
            { term: { "base.journal.meta.text": CONFERENCE } },
          ],
          minimum_should_match: 1,
        },
      },
    ],
    must_not: [{ term: { deleted: true } }, { term: { is_delete: "是" } }],
  },
};

async function search(size, cursor) {
  const body = {
    size,
    track_total_hits: cursor == null,
    query: FILTER,
    sort: [{ _id: { order: "asc" } }],
    ...(cursor ? { search_after: cursor } : {}),
  };
  const response = await fetch(`${host}/${indexName}/_search`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120_000),
  });
  if (!response.ok) {
    throw new Error(`conference_search_failed:${response.status}:${(await response.text()).slice(0, 500)}`);
  }
  return response.json();
}

async function fetchAll() {
  const records = [];
  let cursor = null;
  let page = 0;
  let total = null;
  while (true) {
    page += 1;
    const payload = await search(pageSize, cursor);
    if (total == null) total = normalizeTotal(payload?.hits?.total);
    const hits = payload?.hits?.hits || [];
    for (const hit of hits) records.push({ _id: hit._id, _source: hit._source || {} });
    console.error(`[fetch-conference] page=${page} fetched=${hits.length}${total == null ? "" : ` total=${total}`}`);
    if (hits.length < pageSize) break;
    cursor = hits.at(-1)?.sort;
    if (!cursor) throw new Error("conference_pagination_missing_sort");
  }
  return { records, total };
}

const { records, total } = await fetchAll();
const eligible = records.filter(isAnalysisEligible);

fs.mkdirSync(path.dirname(OUT), { recursive: true });
const snapshot = {
  schema_version: "1.0.0",
  conference: CONFERENCE,
  index: indexName,
  generated_at: new Date().toISOString(),
  query: {
    index: indexName,
    conference: CONFERENCE,
    exact_fields: ["base.journal.text", "base.journal.meta.text"],
    excluded: ["deleted=true", "is_delete=是"],
    analysis_eligible_rule: "latest.text/meta.text != 否 AND is_show.text/meta.text != 否",
  },
  overview: {
    matched_records: total == null ? records.length : total,
    returned_records: records.length,
    analysis_eligible_records: eligible.length,
  },
  records,
};
fs.writeFileSync(OUT, JSON.stringify(snapshot, null, 2) + "\n");
console.log(`[fetch-conference] matched=${total} returned=${records.length} eligible=${eligible.length}`);
console.log(`[fetch-conference] wrote=${OUT}`);

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

function pushClean(output, value) {
  for (const part of String(value).split(/\s*\|\s*/)) {
    const clean = part.trim();
    if (clean && clean !== "-") output.push(clean);
  }
}

function normalizeTotal(total) {
  if (typeof total === "number") return total;
  return typeof total?.value === "number" ? total.value : null;
}
