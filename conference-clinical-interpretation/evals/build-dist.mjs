#!/usr/bin/env node
/**
 * Build dist/conference-clinical-interpretation-v0.1.zip from skill assets.
 * Mirrors the multi-clinical-result-comparison dist layout:
 *   conference-clinical-interpretation/SKILL.md
 *   conference-clinical-interpretation/references/...
 *   conference-clinical-interpretation/templates/...
 * Uses Python's zipfile (zip/unzip binaries are not installed here).
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const SKILL_ROOT = path.join(ROOT, "skill/conference-clinical-interpretation");
const DIST_DIR = path.join(ROOT, "dist");
const ZIP_PATH = path.join(DIST_DIR, "conference-clinical-interpretation-v0.1.zip");

if (!fs.existsSync(SKILL_ROOT)) {
  console.error(`skill root missing: ${SKILL_ROOT}`);
  process.exit(1);
}

fs.mkdirSync(DIST_DIR, { recursive: true });
if (fs.existsSync(ZIP_PATH)) fs.rmSync(ZIP_PATH);

// Build zip via a temp python script using zipfile; archive root = skill name.
const tmpScript = path.join(DIST_DIR, "_build_dist.py");
const script = `
import zipfile, os
root = ${JSON.stringify(SKILL_ROOT)}
out = ${JSON.stringify(ZIP_PATH)}
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for dirpath, _, files in os.walk(root):
        for f in files:
            full = os.path.join(dirpath, f)
            arc = os.path.join('conference-clinical-interpretation', os.path.relpath(full, root))
            z.write(full, arc)
print('wrote', out)
`;
fs.writeFileSync(tmpScript, script);
execSync(`python3 "${tmpScript}"`, { stdio: "inherit" });
fs.rmSync(tmpScript, { force: true });

const stat = fs.statSync(ZIP_PATH);
console.log(`[dist-build] wrote ${ZIP_PATH} (${(stat.size / 1024).toFixed(1)} KB)`);

// List archive contents for verification
const listing = execSync(
  `python3 -c "import zipfile; [print(n) for n in zipfile.ZipFile('${ZIP_PATH}').namelist()]"`,
  { encoding: "utf8" }
);
console.log(listing);
