import fs from "node:fs";
import { getConfig } from "../../POC2/src/config.js";

const config = getConfig();
const ids = [
  "40961953", "40961952", "40960239", "40934115", "40758358", "40555243",
  "40421736", "39536238", "39258838", "38912654", "38819983", "38330988",
  "37385278", "36322838", "35658024", "32233338"
];
const headers = { "content-type": "application/json" };
if (config.esApiKey) headers.authorization = `ApiKey ${config.esApiKey}`;
else if (config.esUsername) {
  headers.authorization = `Basic ${Buffer.from(`${config.esUsername}:${config.esPassword}`).toString("base64")}`;
}
const query = {
  bool: {
    must: [{ terms: { doc_id: ids } }],
    must_not: [{ term: { deleted: true } }, { term: { is_delete: "是" } }]
  }
};
const response = await fetch(`${config.esHost.replace(/\/$/, "")}/${config.npResultIndex}/_search`, {
  method: "POST",
  headers,
  body: JSON.stringify({
    size: ids.length + 10,
    track_total_hits: true,
    _source: ["doc_id", "source_full_text"],
    query
  })
});
if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
const payload = await response.json();
function sourceText(value) {
  if (typeof value === "string") return value;
  if (!value || typeof value !== "object") return "";
  if (typeof value.text === "string") return value.text;
  if (Array.isArray(value.meta)) {
    const text = value.meta.map((item) => item?.text).filter((item) => typeof item === "string").join("\n");
    if (text) return text;
  }
  return "";
}
const results = (payload.hits?.hits || []).map((hit) => ({
  result_id: `${hit._source?.doc_id}::${hit._id}`,
  source_full_text: sourceText(hit._source?.source_full_text)
}));
fs.writeFileSync("evals/fixtures/obesity-results-es-source-full-text.json", JSON.stringify({ results }, null, 2) + "\n");
console.log(JSON.stringify({ total: payload.hits?.total, results: results.length, path: "evals/fixtures/obesity-results-es-source-full-text.json" }));
