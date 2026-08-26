import fs from "node:fs";
import path from "node:path";

// Validate entity inline references in a delivered report (v0.10).
//
// Checks, for a report file plus its attachment source files:
//   1. Every `[name](entity:type:id)` reference is well-formed (balanced
//      brackets/parens, non-empty name/type/id).
//   2. Every referenced type is one of drug / company / trial.
//   3. Every referenced id+type appears in the attachment metadata lines
//      (source_drug_entities / source_company_entities / source_nct_id).
//   4. No `entity:` text appears inside any chart product file (checked when
//      chart files are supplied under the visualizations dir).
//
// Usage:
//   node evals/validate-entity-refs.mjs <report.md> [sourcesDir] [visualizationsDir]
//
// Exit code 0 = PASS; nonzero = FAIL with reasons on stderr.

const [reportFile, sourcesDir, vizDir] = process.argv.slice(2);
if (!reportFile) {
  console.error("usage: node evals/validate-entity-refs.mjs <report.md> [sourcesDir] [visualizationsDir]");
  process.exit(2);
}

const entityRe = /\[([^\]]+)\]\(entity:([a-z_]+):([^)]+)\)/g;
const allowedTypes = new Set(["drug", "company", "trial"]);
const failures = [];
const report = fs.readFileSync(reportFile, "utf8");

const available = new Map(); // `${type}:${id}` -> true
if (sourcesDir) {
  const files = fs.readdirSync(sourcesDir).filter((f) => /^source-\d{3}\.md$/.test(f)).sort();
  if (files.length === 0) failures.push(`no attachment files matched in ${sourcesDir}`);
  for (const f of files) {
    const md = fs.readFileSync(path.join(sourcesDir, f), "utf8");
    const nct = md.match(/^source_nct_id: (.*)$/m)?.[1]?.trim();
    if (nct) available.set(`trial:${nct}`, true);
    for (const lineKey of ["source_drug_entities", "source_company_entities"]) {
      const line = md.match(new RegExp(`^${lineKey}: (.*)$`, "m"))?.[1] ?? "";
      const type = lineKey === "source_drug_entities" ? "drug" : "company";
      for (const tuple of line.split(";")) {
        const parts = tuple.split("|").map((p) => p.trim());
        if (parts.length === 3 && parts[1]) available.set(`${type}:${parts[2]}`, true);
      }
    }
  }
}

const seen = new Set();
let match;
while ((match = entityRe.exec(report)) !== null) {
  const [, name, type, id] = match;
  const ref = `${type}:${id}`;
  if (!allowedTypes.has(type)) failures.push(`disallowed entity type "${type}" in ${match[0]}`);
  if (!name.trim()) failures.push(`empty display name in ${match[0]}`);
  if (!id.trim()) failures.push(`empty id in ${match[0]}`);
  if (sourcesDir && !available.has(ref)) failures.push(`entity id not in metadata lines: ${ref} (${match[0]})`);
  seen.add(ref);
}

// Every available drug/company/trial should be referenced at least once when it
// is a single-item scope; report-level completeness is informational only here.
if (sourcesDir) {
  for (const ref of available.keys()) {
    if (!seen.has(ref)) failures.push(`available entity not referenced anywhere: ${ref} (informational)`);
  }
}

if (vizDir && fs.existsSync(vizDir)) {
  for (const f of fs.readdirSync(vizDir)) {
    if (!/\.(html|svg)$/i.test(f)) continue;
    const text = fs.readFileSync(path.join(vizDir, f), "utf8");
    if (/entity:[a-z_]+:/.test(text)) failures.push(`chart file ${f} contains entity: text`);
  }
}

if (failures.length > 0) {
  console.error("ENTITY_REF_FAIL");
  for (const f of failures) console.error(` - ${f}`);
  process.exit(1);
}
console.log("ENTITY_REF_PASS");
