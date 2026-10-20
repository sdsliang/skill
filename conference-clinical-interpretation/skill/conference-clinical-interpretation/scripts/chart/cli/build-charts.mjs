#!/usr/bin/env node
/**
 * 第 2 步：会议全量结果集 → 两版（cn / en）可视化产物树 + 章节索引 + 报告读数底稿。
 *
 * 用法：
 *   node scripts/chart/cli/build-charts.mjs --meeting "ASCO 2026" \
 *        --input output/pharmcube-query-clinical-result-with-params/asco-2026-clinical-results.ndjson \
 *        --output-dir output/visualizations --report-dir output --lang both
 *
 * 产物：
 *   <output-dir>/<lang>/chapter-0N/<viewId>.json   图表 envelope
 *   <output-dir>/<lang>/summary-callout.json       总结块（骨架，正文留待写报告时填）
 *   <output-dir>/<lang>/index.json                 章节索引
 *   <report-dir>/build/<slug>/report-source-<lang>.md   读数底稿（写报告只读它）
 *   <report-dir>/build/<slug>/chapters-summary.json     运行汇总（判「跑完没有」看它）
 */
import fs from 'node:fs';
import path from 'node:path';
import { unitsFromLines } from '../lib/unit.mjs';
import { CHAPTERS, VIEWS } from '../registry/views.mjs';
import { RENDERERS, summaryCallout } from '../lib/build.mjs';

const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const pad = (n) => String(n).padStart(2, '0');

function parseArgs(argv) {
    const out = { langs: ['cn', 'en'] };
    for (let i = 0; i < argv.length; i += 1) {
        const key = argv[i].replace(/^--/, '');
        const val = argv[i + 1];
        if (key === 'lang') {
            out.langs = val === 'both' ? ['cn', 'en'] : [val];
            i += 1;
        } else { out[key] = val; i += 1; }
    }
    return out;
}

const args = parseArgs(process.argv.slice(2));
const meeting = args.meeting ?? 'ASCO 2026';
const input = args.input ??
    `output/pharmcube-query-clinical-result-with-params/${slugify(meeting)}-clinical-results.ndjson`;
const outputDir = args['output-dir'] ?? 'output/visualizations';
const reportDir = args['report-dir'] ?? 'output';
const buildDir = path.join(reportDir, 'build', slugify(meeting));

const lines = fs.readFileSync(input, 'utf8').split('\n');
const units = unitsFromLines(lines);
const metaPath = path.join(path.dirname(input), 'query-meta.json');
const meta = fs.existsSync(metaPath) ? JSON.parse(fs.readFileSync(metaPath, 'utf8')) : {};
const denominator = units.length;

if (!denominator) throw new Error(`${input}: 没有可用记录`);

const source = {
    cn: `本届会议（${meeting}）公开的研究摘要，共 ${denominator} 篇按研究去重`,
    en: `Abstracts published at ${meeting}: ${denominator} studies after deduplication`,
};

const summary = { meeting, langs: args.langs, denominator, input, outputDir, charts: {}, skipped: {}, failed: {}, indexFiles: {} };
const readouts = {};

for (const lang of args.langs) {
    const langRoot = path.join(outputDir, lang);
    fs.rmSync(langRoot, { recursive: true, force: true });
    fs.mkdirSync(langRoot, { recursive: true });
    const entries = [];
    const linesOut = [];
    for (const chapter of CHAPTERS) {
        const views = VIEWS.filter((v) => v.chapter === chapter.no);
        const dir = path.join(langRoot, `chapter-${pad(chapter.no)}`);
        fs.mkdirSync(dir, { recursive: true });
        for (const view of views) {
            const renderer = RENDERERS[view.type];
            try {
                const built = renderer({ units, view, meeting, lang, source });
                if (built?.skipped) {
                    (summary.skipped[lang] ??= []).push({ view: view.id, reason: built.skipped });
                    continue;
                }
                const file = path.join(dir, `${view.id}.json`);
                fs.writeFileSync(file, JSON.stringify(built, null, 4) + '\n');
                entries.push({
                    file: path.relative(outputDir, file),
                    view: view.id,
                    type: built.config.type,
                    chapter: chapter.no,
                    title: lang === 'en' ? view.title.en : view.title.cn,
                    requirement: lang === 'en' ? view.note.en : view.note.cn,
                    renderable: true,
                });
                (summary.charts[lang] ??= []).push(view.id);
                linesOut.push({ view, config: built.config });
            } catch (err) {
                (summary.failed[lang] ??= []).push({ view: view.id, error: String(err?.message ?? err) });
            }
        }
    }
    // 总结块：正文由写报告阶段填，这里只留骨架
    const callout = summaryCallout({
        lang,
        markdown: lang === 'en'
            ? 'Summary is written together with the report; it only restates figures already in the body.'
            : '总结正文在写报告时填入，只综合正文已有的数字与结论。',
    });
    fs.writeFileSync(path.join(langRoot, 'summary-callout.json'), JSON.stringify(callout, null, 4) + '\n');
    entries.push({
        file: path.posix.join(lang, 'summary-callout.json'),
        view: 'summary-callout',
        type: 'layout',
        chapter: CHAPTERS.length,
        title: lang === 'en' ? 'Summary' : '总结',
        requirement: '',
        renderable: true,
    });

    const index = {
        meeting,
        lang,
        denominator,
        totalCharts: entries.length,
        skippedCharts: (summary.skipped[lang] ?? []).length,
        failedCharts: (summary.failed[lang] ?? []).length,
        chapters: CHAPTERS.map((c) => ({
            no: c.no,
            act: lang === 'en' ? c.actEn : c.act,
            title: lang === 'en' ? c.titleEn : c.title,
            narrative: lang === 'en' ? c.narrativeEn : c.narrative,
            views: entries.filter((e) => e.chapter === c.no).map((e) => e.view),
        })),
        views: entries,
    };
    fs.writeFileSync(path.join(langRoot, 'index.json'), JSON.stringify(index, null, 4) + '\n');
    summary.indexFiles[lang] = path.relative(outputDir, path.join(langRoot, 'index.json'));
    readouts[lang] = linesOut;
}

// 读数底稿：写报告只读它，不要重算
fs.mkdirSync(buildDir, { recursive: true });
for (const [lang, list] of Object.entries(readouts)) {
    const out = [];
    out.push(`# report-source-${lang}`, '');
    out.push(`- 会议：${meeting}`);
    out.push(`- 分母：${denominator}（按研究去重的研究摘要数）`);
    if (meta.rawRows) out.push(`- 原始返回行（含多值 explode）：${meta.rawRows}`);
    out.push('');
    for (const chapter of CHAPTERS) {
        const views = list.filter((l) => l.view.chapter === chapter.no);
        if (!views.length) continue;
        out.push(`## ${lang === 'en' ? chapter.actEn : chapter.act} · ${lang === 'en' ? chapter.titleEn : chapter.title}`, '');
        for (const { view, config } of views) {
            out.push(`### ${view.id}`, '');
            out.push(`${config.title} — ${config.subTitle}`, '');
            const rows = config.data ?? [];
            const isSankey = config.type === 'sankey';
            rows.slice(0, 24).forEach((row, i) => {
                const key = `${view.id}#${i + 1}`;
                if (config.type === 'heatmap') out.push(`- ${key} ${row.group} × ${row.label} = ${row.value}`);
                else if (isSankey) out.push(`- ${key} ${row.source} → ${row.target} = ${row.value}`);
                else out.push(`- ${key} ${row.label} = ${row.value}`);
            });
            out.push('');
        }
    }
    fs.writeFileSync(path.join(buildDir, `report-source-${lang}.md`), out.join('\n'));
}

summary.exitCode = Object.values(summary.failed).some((v) => v.length) ? 1 : 0;
fs.writeFileSync(path.join(buildDir, 'chapters-summary.json'), JSON.stringify(summary, null, 4) + '\n');
console.log(JSON.stringify({
    meeting,
    denominator,
    langs: summary.langs,
    charts: Object.fromEntries(Object.entries(summary.charts).map(([k, v]) => [k, v.length])),
    skipped: summary.skipped,
    failed: summary.failed,
    indexFiles: summary.indexFiles,
    exitCode: summary.exitCode,
}, null, 2));
process.exit(summary.exitCode);
