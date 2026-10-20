#!/usr/bin/env node
/**
 * citations — 把写报告时用到的「选片规则」编译成 citations-cn.json / citations-en.json。
 *
 * 为什么要这么绕：正文里的 {{ref_n}} 必须指向真实存在、可点开的摘要；
 * 报告阶段手抄 esid 极易抄错，所以正文只写 ref 号，选片交给这里，
 * 由规则在合并后的全量数据里挑出唯一一条，再带上 asco.org 链接与发布日期。
 *
 * 用法：
 *   node .../cli/citations.mjs --meeting "ASCO 2026" --spec output/build/asco-2026/citation-select.json
 *
 * spec 形状（有序数组，ref 号即正文里的 {{ref_n}}）：
 *   [ { "ref": "ref_1", "indication": "非小细胞肺癌", "pos": true, "titleRe": "Phase III" }, ... ]
 * 可选字段：indication / drugName / target / country / lba / pos / neg / terminated /
 *           keyEvidence / titleRe / prefer（任一命中加分，按分排序取最高）
 * 输出：<report-dir>/citations-<lang>.json —— { "ref_1": { title, link, paper_release_time_str } }
 */
import fs from 'fs';
import path from 'path';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, cur, i, arr) => {
    if (cur.startsWith('--')) acc.push([cur.slice(2), arr[i + 1]?.startsWith('--') ? true : arr[i + 1] ?? true]);
    return acc;
}, []));

const meeting = args.meeting ?? 'ASCO 2026';
const slug = String(meeting).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const reportDir = args['report-dir'] ?? 'output';
const specPath = args.spec ?? path.join(reportDir, 'build', slug, 'citation-select.json');
const dataPath = args.data
    ?? path.join(reportDir, 'pharmcube-query-clinical-result-with-params', `${slug}-clinical-results.ndjson`);

import { toUnit, arr, txt } from '../lib/unit.mjs';

const pos = (u) => /\u79ef\u6781|\u9633\u6027|positive/i.test(u.evaluation);
const neg = (u) => /\u4e0d\u4f73|\u9634\u6027|negative/i.test(u.evaluation);
const terminated = (u) => /\u7ec8\u6b62|terminated/i.test(u.evaluation);

/** 选片规则：硬条件不满足直接淘汰，软条件累加分，取分最高的一条 */
function score(u, sel) {
    if (sel.pos && !pos(u)) return -1;
    if (sel.neg && !neg(u)) return -1;
    if (sel.terminated && !terminated(u)) return -1;
    if (sel.lba && !txt(u.lba)) return -1;
    if (sel.keyEvidence && !u.keyEvidence) return -1;
    if (sel.indication && !u.indications.some((i) => i.cn.includes(sel.indication) || i.en.toLowerCase().includes(String(sel.indication).toLowerCase()))) return -1;
    if (sel.drugName && !u.drugs.some((d) => `${d.cn} ${d.en}`.includes(sel.drugName))) return -1;
    if (sel.target && !u.drugs.some((d) => d.targets.some((t) => t.toUpperCase().includes(String(sel.target).toUpperCase())))) return -1;
    if (sel.country && !u.companies.some((c) => c.country.includes(sel.country))) return -1;
    if (sel.titleRe && !new RegExp(sel.titleRe, 'i').test(u.title)) return -1;

    let s = 0;
    if (pos(u)) s += 2;
    if (u.keyEvidence) s += 2;
    if (txt(u.lba)) s += 3;
    if (/phase\s*(iii|3)|III\s*\u671f|\u2162/i.test(`${u.title} ${u.endpoints.map((e) => e.cn).join(' ')}`)) s += 2;
    if (u.link) s += 1;
    if (arr(sel.prefer).some((kw) => u.title.toLowerCase().includes(String(kw).toLowerCase()))) s += 5;
    return s;
}

const units = fs.readFileSync(dataPath, 'utf8').split('\n').filter(Boolean).map((l) => toUnit(JSON.parse(l)));
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));

const picked = [];
const missing = [];
for (const sel of spec) {
    let best = null;
    let bestScore = -1;
    for (const u of units) {
        const s = score(u, sel);
        if (s > bestScore) { bestScore = s; best = u; }
    }
    if (!best || bestScore < 0) { missing.push(sel.ref); continue; }
    picked.push({
        ref: sel.ref,
        title: best.title,
        link: best.link,
        paper_release_time_str: best.day,
        esid: best.esid,
    });
}

if (missing.length) {
    console.error(`citations: 以下 ref 没有匹配到任何摘要，请修正 spec：${missing.join(', ')}`);
    process.exit(2);
}

const payload = Object.fromEntries(picked.map((p) => [p.ref, {
    title: p.title,
    link: p.link,
    paper_release_time_str: p.paper_release_time_str,
}]));

for (const lang of ['cn', 'en']) {
    const out = path.join(reportDir, `citations-${lang}.json`);
    fs.writeFileSync(out, JSON.stringify(payload, null, 4) + '\n');
    console.log(`${out}: ${picked.length} refs`);
}
console.log(`refs=${picked.length} missing=0`);
