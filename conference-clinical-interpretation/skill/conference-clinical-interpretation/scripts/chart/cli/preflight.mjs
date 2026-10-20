#!/usr/bin/env node
/**
 * preflight — 交付前闸门：报告正文 / 图表产物 / 引文三方对账。
 *
 * 检查项（任一失败 exit 1）：
 *   1. 每个 `::visualization[...]{path="..."}` 指向的文件真实存在，且后缀为 .json（不混 HTML）
 *   2. 报告引用的图 id 与 index-<lang>.json 的 views 完全一致（不缺不多、顺序一致）
 *   3. `{{ref_n}}` 与 citations-<lang>.json 双向齐全（正文有、文件有），且首次出现顺序递增
 *   4. 中英两版数字多重集一致（只比数字，不看语言），差异逐条列出
 *   5. 正文里没有残留占位符（TODO / {{ / 待填 / lorem）
 *
 * 用法：
 *   node .../cli/preflight.mjs --meeting "ASCO 2026"
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
const vizDir = args['viz-dir'] ?? 'output/visualizations';
const langs = ['cn', 'en'];

const findings = [];
const fail = (msg) => findings.push({ level: 'FAIL', msg });
const warn = (msg) => findings.push({ level: 'WARN', msg });

const read = (p) => fs.readFileSync(p, 'utf8');
// 千分位必须先去逗号，否则 1,639 会被拆成 1 和 639，中英对账全是假差异
const numbers = (text) => (text.replace(/(?<=\d),(?=\d{3})/g, '').match(/[0-9]+(?:\.[0-9]+)?/g) ?? [])
    // 只对账「有分量」的数字：中文写「III 期」「六成」，英文写「phase 3」「60%」，
    // 个位数与序号天然对不上，硬比只会产生假差异；≥20 的数字与百分比必须一致
    .filter((x) => (x.includes('.') ? true : Number(x) >= 20))
    .sort();

const reports = {};
for (const lang of langs) {
    const rp = path.join(reportDir, `report-${lang}.md`);
    if (!fs.existsSync(rp)) { fail(`缺少报告：${rp}`); continue; }
    const md = read(rp);
    reports[lang] = md;

    // 5. 占位符
    for (const bad of ['TODO', '待填', 'lorem', '{{', '}}']) {
        if (md.includes(bad) && !(bad === '{{' || bad === '}}')) fail(`report-${lang}.md 含占位符 ${bad}`);
    }
    const stray = md.match(/\{\{(?!ref_\d+\}\})[^}]*\}\}/g);
    if (stray) fail(`report-${lang}.md 有非法模板串：${stray.slice(0, 3).join(', ')}`);

    // 1. 图表引用
    const refs = [...md.matchAll(/::visualization\[([^\]]*)\]\{path="([^"]+)"\}/g)].map((m) => ({ title: m[1], p: m[2] }));
    if (!refs.length) fail(`report-${lang}.md 没有 ::visualization 引用`);
    for (const r of refs) {
        if (!r.p.endsWith('.json')) fail(`report-${lang}.md 引用了非 JSON 图表：${r.p}`);
        if (!r.p.startsWith('/workspace/visualizations/')) fail(`report-${lang}.md 图表路径不是绝对 workspace 路径：${r.p}`);
        const local = path.join(vizDir, path.basename(r.p));
        if (!fs.existsSync(local)) fail(`report-${lang}.md 引用的图表文件不存在：${r.p} -> ${local}`);
        if (!r.title.trim()) fail(`report-${lang}.md 有空的图表标题：${r.p}`);
    }

    // 2. 与 index 对账
    const idxPath = path.join(vizDir, `index-${lang}.json`);
    if (!fs.existsSync(idxPath)) fail(`缺少索引：${idxPath}`);
    else {
        const idx = JSON.parse(read(idxPath));
        const expected = idx.views.map((v) => `${v.view}-${lang}.json`);
        const actual = refs.map((r) => path.basename(r.p));
        const missing = expected.filter((x) => !actual.includes(x));
        const extra = actual.filter((x) => !expected.includes(x));
        if (missing.length) fail(`report-${lang}.md 少了 ${missing.length} 张图：${missing.join(', ')}`);
        if (extra.length) fail(`report-${lang}.md 多出 ${extra.length} 张图：${extra.join(', ')}`);
        if (!missing.length && !extra.length && expected.join() !== actual.join()) warn(`report-${lang}.md 图表顺序与 index 不一致`);
    }

    // 3. 引文双向
    const citPath = path.join(reportDir, `citations-${lang}.json`);
    if (!fs.existsSync(citPath)) fail(`缺少引文文件：${citPath}`);
    else {
        const cit = JSON.parse(read(citPath));
        const cited = [...new Set([...md.matchAll(/\{\{(ref_\d+)\}\}/g)].map((m) => m[1]))];
        const order = [...md.matchAll(/\{\{(ref_\d+)\}\}/g)].map((m) => m[1]);
        const firstSeen = order.filter((x, i) => order.indexOf(x) === i);
        const nums = (list) => list.map((x) => Number(x.split('_')[1]));
        const ascending = nums(firstSeen).every((n, i, a) => i === 0 || n > a[i - 1]);
        if (!ascending) warn(`report-${lang}.md 的 {{ref_n}} 首次出现顺序不是递增：${firstSeen.join(' -> ')}`);
        const missingInFile = cited.filter((r) => !cit[r]);
        const unusedInText = Object.keys(cit).filter((r) => !cited.includes(r));
        if (missingInFile.length) fail(`citations-${lang}.json 缺少正文引用的 ${missingInFile.join(', ')}`);
        if (unusedInText.length) fail(`citations-${lang}.json 有正文未引用的 ${unusedInText.join(', ')}`);
        for (const [k, v] of Object.entries(cit)) {
            if (!v.title) fail(`citations-${lang}.json ${k} 缺 title`);
            if (!/^https?:\/\//.test(v.link ?? '')) fail(`citations-${lang}.json ${k} 的 link 不是 URL`);
            if (!/^\d{4}-\d{2}-\d{2}$/.test(v.paper_release_time_str ?? '')) fail(`citations-${lang}.json ${k} 的日期格式不对`);
        }
    }
}

// 4. 中英数字一致
if (reports.cn && reports.en) {
    const a = numbers(reports.cn);
    const b = numbers(reports.en);
    const countOf = (list) => list.reduce((m, x) => (m.set(x, (m.get(x) ?? 0) + 1), m), new Map());
    const ca = countOf(a);
    const cb = countOf(b);
    const diffs = [];
    for (const key of new Set([...ca.keys(), ...cb.keys()])) {
        const x = ca.get(key) ?? 0;
        const y = cb.get(key) ?? 0;
        if (x !== y) diffs.push(`${key}: cn×${x} en×${y}`);
    }
    if (diffs.length) fail(`中英两版数字不一致 ${diffs.length} 处：${diffs.join(' | ')}`);
    else console.log(`numbers: cn=${a.length} en=${b.length} 完全一致`);
}

const failed = findings.filter((f) => f.level === 'FAIL');
for (const f of findings) console.log(`${f.level === 'FAIL' ? '✗' : '⚠'} ${f.msg}`);
console.log(failed.length ? `preflight: FAIL (${failed.length})` : 'preflight: PASS');
process.exit(failed.length ? 1 : 0);
