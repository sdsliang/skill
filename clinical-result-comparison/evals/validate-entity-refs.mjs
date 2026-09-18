import fs from "node:fs";
import path from "node:path";

// Validate current entity inline syntax and charts, with optional legacy source
// attachment metadata checks. Without sourcesDir this cannot prove ID provenance.
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

const entityRe = /\[([^\[\]\r\n]*)\]\(entity:([^:()\s]*):([^():\s]*)\)/g;
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
        if (parts.length === 3 && parts.every(Boolean)) available.set(`${type}:${parts[2]}`, true);
      }
    }
  }
}

const seen = new Set();
const matchedEntityOffsets = new Set();
let match;
while ((match = entityRe.exec(report)) !== null) {
  const [, name, type, id] = match;
  matchedEntityOffsets.add(match.index + 1 + name.length + 2);
  const ref = `${type}:${id}`;
  if (!allowedTypes.has(type)) failures.push(`disallowed entity type "${type}" in ${match[0]}`);
  if (!name.trim()) failures.push(`empty display name in ${match[0]}`);
  if (!id.trim()) failures.push(`empty id in ${match[0]}`);
  if (sourcesDir && !available.has(ref)) failures.push(`entity id not in metadata lines: ${ref} (${match[0]})`);
  seen.add(ref);
}

// Account for every occurrence, including incomplete links and nested anchors
// that a regex matching only valid links would silently skip.
for (const occurrence of report.matchAll(/entity:/gi)) {
  if (!matchedEntityOffsets.has(occurrence.index)) {
    failures.push(`malformed entity reference at offset ${occurrence.index}`);
  }
}

// Every available drug/company/trial should be referenced at least once when it
// is a single-item scope; report-level completeness is informational only here.
if (sourcesDir) {
  for (const ref of available.keys()) {
    if (!seen.has(ref)) failures.push(`available entity not referenced anywhere: ${ref} (informational)`);
  }
}

if (vizDir) {
  if (!fs.existsSync(vizDir)) failures.push(`chart directory does not exist: ${vizDir}`);
  else checkCharts(vizDir);
}

function checkCharts(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      checkCharts(filename);
      continue;
    }
    if (!entry.isFile() || !/\.(json|html|svg)$/i.test(entry.name)) continue;
    let text = fs.readFileSync(filename, "utf8");
    if (/\.json$/i.test(entry.name)) {
      try {
        // Decode escapes as well as scanning keys, values and iframe templates.
        text = JSON.stringify(JSON.parse(text));
      } catch {
        failures.push(`chart file ${filename} is invalid JSON`);
        continue;
      }
    }
    if (/entity:/i.test(text)) failures.push(`chart file ${filename} contains entity: text`);
  }
}

if (failures.length > 0) {
  console.error("ENTITY_REF_FAIL");
  for (const f of failures) console.error(` - ${f}`);
  process.exit(1);
}
console.log("ENTITY_REF_PASS");
