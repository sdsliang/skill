import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixturePaths = [
  "evals/fixtures/pws-phase3-selected-results.json",
  "evals/fixtures/harmoni6-selected-results.json",
  "evals/fixtures/adversarial-and-incomplete-results.json",
  "evals/fixtures/nct05840016-selected-results.json"
];

for (const relativePath of fixturePaths) {
  const fixture = readJson(relativePath);
  if (!Array.isArray(fixture.results) || fixture.results.length < 2) {
    fail(`${relativePath}: expected at least two results`);
  }

  fixture.results.forEach((source, index) => {
    const keys = Object.keys(source).sort();
    const expectedKeys = ["source_full_text", "source_paper_release_time_str", "source_title", "source_url"];
    if (JSON.stringify(keys) !== JSON.stringify(expectedKeys)) {
      fail(`${relativePath}: result ${index + 1} has invalid keys: ${keys.join(",")}`);
    }
    for (const key of expectedKeys) {
      if (typeof source[key] !== "string") {
        fail(`${relativePath}: result ${index + 1} ${key} must be a string`);
      }
    }
    if (!source.source_full_text.trim()) {
      fail(`${relativePath}: result ${index + 1} source_full_text is empty`);
    }
    if (source.source_url && !/^https?:\/\//i.test(source.source_url)) {
      fail(`${relativePath}: result ${index + 1} source_url is not absolute HTTP(S)`);
    }
  });
}

validateReport(
  "evals/iteration-13/harmoni6/report.md",
  "evals/fixtures/harmoni6-selected-results.json"
);

JSON.parse(fs.readFileSync(path.join(projectRoot, "evals/evals.json"), "utf8"));
console.log("v0.5_contract_ok");

function validateReport(reportPath, fixturePath) {
  const report = fs.readFileSync(path.join(projectRoot, reportPath), "utf8");
  const fixture = readJson(fixturePath).results;
  const refs = readJson("evals/iteration-13/harmoni6/report.refs.json");
  const markerKeys = new Set(
    [...report.matchAll(/\{\{(ref_\d+)\}\}/g)].map((match) => match[1])
  );
  const citationKeys = new Set(Object.keys(refs));

  if (!sameSet(markerKeys, citationKeys)) {
    fail(`${reportPath}: marker and citation-list numbers differ`);
  }
  if (citationKeys.size !== fixture.length) {
    fail(`${reportPath}: expected ${fixture.length} citation keys, found ${citationKeys.size}`);
  }

  fixture.forEach((source, index) => {
    const key = `ref_${index + 1}`;
    const citation = refs[key];
    if (!citation || Object.keys(citation).sort().join(",") !== "link,paper_release_time_str,title") {
      fail(`${reportPath}: ${key} must contain exactly title, link, and paper_release_time_str`);
    }
    if (citation.title !== source.source_title || citation.link !== source.source_url || citation.paper_release_time_str !== source.source_paper_release_time_str) {
      fail(`${reportPath}: ${key} metadata differs from fixture`);
    }
  });

  if (report.includes("## 引用来源")) fail(`${reportPath}: citation JSON must be separate from report body`);
  const forbidden = /\[Ref|来源索引|来源 Ref|\bresult_id\b|\bdoc_id\b|source_full_text|Elasticsearch|np_clinical/;
  if (forbidden.test(report)) fail(`${reportPath}: contains a forbidden implementation or legacy term`);
  if (/\{\{ref_n\}\}/.test(report)) fail(`${reportPath}: contains unresolved reference placeholder`);
}

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(projectRoot, relativePath), "utf8"));
}

function sameSet(left, right) {
  return left.size === right.size && [...left].every((value) => right.has(value));
}

function fail(message) {
  throw new Error(message);
}
