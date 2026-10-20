/**
 * 跨视图事实表：报告正文里那些「不属于任何一张图」的数字的唯一来源。
 * 产出 output/build/<slug>/facts.json，中英各一份文案，数字只算一次。
 */
import fs from 'node:fs';
import path from 'node:path';
import { toUnit } from '../lib/unit.mjs';
import { rank, cross } from '../lib/build.mjs';
import { DIMENSIONS, CHAPTERS, VIEWS, viewsByChapter } from '../registry/views.mjs';

const arg = (name, dflt) => {
    const i = process.argv.indexOf(`--${name}`);
    return i > -1 ? process.argv[i + 1] : dflt;
};
const meeting = arg('meeting', 'ASCO 2026');
const slug = meeting.toLowerCase().replace(/[^a-z0-9]+/g, '-');
const dataFile = arg('data', 'output/pharmcube-query-clinical-result-with-params/asco-2026-clinical-results.ndjson');
const buildDir = path.join('output/build', slug);

const recs = fs.readFileSync(dataFile, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
const units = recs.map(toUnit);
const N = units.length;

const isChina = (u) => DIMENSIONS.chinaRegion(u)[0]?.key === 'cn';
const neg = (u) => u.evaluation === '不佳' || u.evaluation === '终止';
const pos = (u) => u.evaluation === '积极';
const pct = (a, b) => (b ? Math.round((a / b) * 1000) / 10 : 0);

const cohort = (name, sel) => {
    const set = units.filter(sel);
    const n = set.length;
    const byDim = (dim, topN = 5) => rank(set, { dim, topN }).rows.slice(0, topN).map((r) => ({ cn: r.cn, en: r.en, value: r.value, share: pct(r.value, n) }));
    return {
        name,
        n,
        share: pct(n, N),
        positive: set.filter(pos).length,
        positiveRate: pct(set.filter(pos).length, n),
        negative: set.filter(neg).length,
        negativeRate: pct(set.filter(neg).length, n),
        terminated: set.filter((u) => u.evaluation === '终止').length,
        unassessed: set.filter((u) => !u.evaluation || u.evaluation === '-').length,
        lba: set.filter((u) => /^lba$/i.test(String(u.lba ?? ''))).length,
        keyEvidence: set.filter((u) => u.keyEvidence).length,
        topIndications: byDim('indication'),
        topTargets: byDim('target'),
        topCompanies: byDim('company'),
        topStages: byDim('stage', 4),
        topEvidence: byDim('evidenceSource', 4),
    };
};

const china = cohort('china', isChina);
const row = cohort('row', (u) => !isChina(u));
const all = cohort('all', () => true);

// 可行动信号：积极 + 有关键证据，再按「能不能改决策」加权
// LBA(+3) > 标题含 III 期(+2) > 晚期/局部晚期(+1) > 有命名靶点(+1) > 主终点可读(+1)
const isLba = (u) => /^lba$/i.test(String(u.lba ?? ''));
const actionable = units
    .filter((u) => pos(u) && u.keyEvidence)
    .map((u) => {
        const stage = u.stages.map((p) => p.cn).join(' ');
        const title = String(u.title ?? '');
        const score = (isLba(u) ? 3 : 0)
            + (/phase\s*(iii|3)/i.test(title) || /III期/.test(stage) ? 2 : 0)
            + (/晚期|局部晚期/.test(stage) ? 1 : 0)
            + (u.drugs.some((d) => d.targets.length) ? 1 : 0)
            + (u.endpoints.length ? 1 : 0);
        return { u, score };
    })
    // 「同一药物 × 同一适应症」只留一条，避免同一资产刷满清单
    .filter(({ u }, i, arr) => {
        const key = u.drugs.map((d) => d.cn).sort().slice(0, 1).join() + '|' + u.indications.map((p) => p.cn).sort().slice(0, 1).join();
        return arr.findIndex(({ u: v }) => v.drugs.map((d) => d.cn).sort().slice(0, 1).join() + '|' + v.indications.map((p) => p.cn).sort().slice(0, 1).join() === key) === i;
    })
    .sort((a, b) => b.score - a.score || (a.u.title ?? '').localeCompare(b.u.title ?? ''));

const facts = {
    meeting,
    denominator: N,
    chapters: CHAPTERS.length,
    charts: { cn: VIEWS.length, en: VIEWS.length },
    evaluation: {
        积极: all.positive, 不佳: all.negative, 终止: all.terminated, 未评价: all.unassessed,
    },
    lba: { total: all.lba, china: china.lba, share: pct(all.lba, N) },
    cohorts: { china, row, all },
    actionablePool: { total: units.filter((u) => pos(u) && u.keyEvidence).length, screened: actionable.length },
    actionableTop: actionable.slice(0, 20).map(({ u, score }) => ({
        score,
        title: u.title,
        esid: u.esid,
        indication: u.indications.map((p) => p.cn).slice(0, 3).join('、'),
        stage: u.stages.map((p) => p.cn).slice(0, 2).join('、'),
        evaluation: u.evaluation,
        lba: /^lba$/i.test(String(u.lba ?? '')),
        keyEvidence: u.keyEvidence === true,
        endpoints: u.endpoints.map((e) => e.cn).slice(0, 3).join('、'),
        drugs: u.drugs.slice(0, 3).map((d) => d.cn),
        companies: u.companies.slice(0, 2).map((c) => c.cn),
    })),
    negativeByIndication: rank(units.filter(neg), { dim: 'indication' }).rows.slice(0, 10),
    gaps: VIEWS.filter((v) => v.type !== 'sankey').map((v) => ({
        id: v.id,
        skipped: false,
    })),
};

fs.mkdirSync(buildDir, { recursive: true });
fs.writeFileSync(path.join(buildDir, 'facts.json'), JSON.stringify(facts, null, 2) + '\n');
console.log(JSON.stringify({
    denominator: N,
    chinaShare: china.share,
    positiveRate: { china: china.positiveRate, row: row.positiveRate, all: all.positiveRate },
    negativeRate: { china: china.negativeRate, row: row.negativeRate },
    lba: facts.lba,
    actionablePool: facts.actionablePool,
    topChinaIndications: china.topIndications.slice(0, 3),
    topChinaTargets: china.topTargets.slice(0, 3),
}, null, 2));
