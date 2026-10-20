#!/usr/bin/env node
/**
 * 第 2 步交付前自检：把两版可视化产物里所有 `drill` 下钻载荷逐单元格过
 * `list-filter-json` 的白名单校验（pageType=evidence），写成 filters/report-<lang>.json。
 *
 * 用法：node scripts/chart/cli/check-drill.mjs --meeting "ASCO 2026"
 * 通过标准：两版都 failed === 0。
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { validateDrillPayloads } = require('../../../../list-filter-json/scripts/drill-payload.js');

const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, cur, i, all) => {
    if (cur.startsWith('--')) acc.push([cur.slice(2), all[i + 1]]);
    return acc;
}, []));

const meeting = args.meeting ?? 'ASCO 2026';
const outputDir = args['output-dir'] ?? 'output/visualizations';
const reportDir = args['report-dir'] ?? 'output';
const langs = !args.lang || args.lang === 'both' ? ['cn', 'en'] : [args.lang];
const buildDir = path.join(reportDir, 'build', slugify(meeting), 'filters');

let worst = 0;
fs.mkdirSync(buildDir, { recursive: true });
for (const lang of langs) {
    // 扁平产物：<viewId>-<lang>.json
    const files = fs.readdirSync(outputDir)
        .filter((n) => n.endsWith(`-${lang}.json`) && !n.startsWith('index-') && !n.startsWith('summary-callout-'))
        .map((n) => path.join(outputDir, n));
    const visualizations = files.map((f) => ({ name: path.relative(outputDir, f), envelope: JSON.parse(fs.readFileSync(f, 'utf8')) }));
    const result = await validateDrillPayloads({ visualizations, pageType: 'evidence' });
    const out = { lang, ...result, files: visualizations.length };
    fs.writeFileSync(path.join(buildDir, `report-${lang}.json`), JSON.stringify(out, null, 4) + '\n');
    console.log(`${lang}: files=${visualizations.length} total=${result.total} passed=${result.passed} failed=${result.failed} skippedNull=${result.skippedNull}`);
    if (result.failed) {
        worst = 1;
        for (const d of (result.entries ?? []).filter((x) => x.success === false).slice(0, 8)) console.log('  FAIL', JSON.stringify(d).slice(0, 400));
    }
}
process.exit(worst);
