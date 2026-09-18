import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

const validator = fileURLToPath(new URL("../evals/validate-entity-refs.mjs", import.meta.url));
function run(t, report, { metadata, charts } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "entity-refs-test-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const reportFile = path.join(root, "report.md");
  fs.writeFileSync(reportFile, report);
  let sources = "";
  if (metadata !== undefined) {
    sources = path.join(root, "sources");
    fs.mkdirSync(sources);
    fs.writeFileSync(path.join(sources, "source-001.md"), metadata);
  }
  let viz = "";
  if (charts) {
    viz = path.join(root, "visualizations");
    fs.mkdirSync(viz);
    for (const [name, contents] of Object.entries(charts)) {
      const filename = path.join(viz, name);
      fs.mkdirSync(path.dirname(filename), { recursive: true });
      fs.writeFileSync(filename, contents);
    }
  }
  return spawnSync(process.execPath, [validator, reportFile, sources, viz], { encoding: "utf8" });
}

const metadata = "source_nct_id: NCT05840016\nsource_drug_entities: 依沃西单抗|drug_earth|12483\nsource_company_entities: 康方|company|99\n";
const validReport = "[依沃西单抗](entity:drug:12483){{ref_1}} [康方](entity:company:99) [HARMONi-6](entity:trial:NCT05840016)";

test("valid current entity syntax and optional legacy metadata pass", (t) => {
  for (const options of [{}, { metadata }]) {
    const result = run(t, validReport, options);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /ENTITY_REF_PASS/);
  }
  assert.equal(run(t, "Plain report with no entity IDs").status, 0);
});

test("empty, malformed, unsupported and nested entity links fail", (t) => {
  for (const report of [
    "[broken](entity:drug:)", "[broken](entity:drug: )", "[](entity:drug:1)", "[ ](entity:drug:1)",
    "[name](entity::1)", "[name](entity:target:1)", "[name](entity:Drug:1)",
    "[name](entity:drug:1", "[name(entity:drug:1)", "[name](entity:drug)",
    "[name](entity:drug:1:2)", "[name](entity:drug:1 2)", "[name](ENTITY:drug:1)",
    "[[name](entity:drug:1)](entity:drug:1)", "[prefix [name]](entity:drug:1)",
    "[valid](entity:drug:1) [broken](entity:drug:)", "entity:drug:1",
  ]) {
    const result = run(t, report);
    assert.equal(result.status, 1, `${report}: ${result.stdout} ${result.stderr}`);
    assert.match(result.stderr, /ENTITY_REF_FAIL/);
  }
});

test("legacy attachment checks retain ID provenance and completeness failures", (t) => {
  const invented = run(t, validReport.replace("12483", "99999"), { metadata });
  assert.equal(invented.status, 1);
  assert.match(invented.stderr, /entity id not in metadata lines: drug:99999/);
  const missing = run(t, "[依沃西单抗](entity:drug:12483)", { metadata });
  assert.equal(missing.status, 1);
  assert.match(missing.stderr, /available entity not referenced anywhere/);
});

test("current JSON charts and legacy HTML/SVG charts exclude entity links", (t) => {
  const good = run(t, validReport, { charts: {
    "chart.json": JSON.stringify({ id: "chart", option: { type: "bar", data: [1] }, iframe_template: "<div>Trial</div>" }),
    "chart.html": "<div>Trial</div>", "chart.svg": "<svg><text>Trial</text></svg>",
  } });
  assert.equal(good.status, 0, good.stderr);
  for (const [name, text] of [
    ["chart.json", JSON.stringify({ option: { label: "[drug](entity:drug:12483)" } })],
    ["nested/chart.json", '{"label":"[drug](ent\\u0069ty:drug:12483)"}'],
    ["chart.json", JSON.stringify({ "entity:drug:": "bad key" })],
    ["chart.json", JSON.stringify({ iframe_template: '<a href="entity:drug:12483">drug</a>' })],
    ["chart.html", "[drug](entity:drug:)"], ["chart.svg", '<a href="ENTITY:drug:1"/>'],
  ]) {
    const result = run(t, validReport, { charts: { [name]: text } });
    assert.equal(result.status, 1, `${name}: ${result.stdout}`);
    assert.match(result.stderr, /contains entity: text/);
  }
});

test("malformed JSON charts fail rather than silently skipping inspection", (t) => {
  const result = run(t, validReport, { charts: { "chart.json": "{" } });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /invalid JSON/);
});
