/**
 * 聚合与渲染：unit 集合 → 视图行 → 可视化产物 envelope。
 * 只做「研究摘要数」一种计数，不引入第二个分母。
 */
import { ENVELOPE } from './envelope.mjs';
import { DIMENSIONS } from '../registry/views.mjs';

const MAX_DRILL_VALUES = 200;

/** 单维度排名：同一 unit 内先按 key 去重再计数 */
export function rank(units, view) {
    const extract = DIMENSIONS[view.dim];
    /** @type {Map<string, {key:string,cn:string,en:string,value:number,ids:Set<string>}>} */
    const buckets = new Map();
    let covered = 0;
    for (const unit of units) {
        const seen = new Set();
        for (const item of extract(unit)) {
            if (!item.key || seen.has(item.key)) continue;
            seen.add(item.key);
            let bucket = buckets.get(item.key);
            if (!bucket) {
                bucket = { key: item.key, cn: item.cn, en: item.en, value: 0, ids: new Set() };
                buckets.set(item.key, bucket);
            }
            bucket.value += 1;
            for (const id of item.ids ?? []) bucket.ids.add(String(id));
        }
        if (seen.size) covered += 1;
    }
    const rows = [...buckets.values()].sort((a, b) =>
        b.value - a.value || a.cn.localeCompare(b.cn, 'zh-Hans-CN'));
    return { rows, covered };
}

/** 交叉矩阵：X 轴取 Top N，Y 轴按固定顺序 */
export function cross(units, view, yOrder) {
    const xExtract = DIMENSIONS[view.dim];
    const yExtract = DIMENSIONS[view.dimY];
    const { rows: xRows } = rank(units, view);
    const xOrder = xRows.slice(0, view.topN).map((r) => r.key);
    const xLabel = new Map(xRows.map((r) => [r.key, r]));
    const yLabel = new Map();
    const counts = new Map();
    for (const unit of units) {
        const xs = new Set(xExtract(unit).map((i) => i.key));
        const ys = new Set(yExtract(unit).map((i) => i.key));
        for (const y of ys) if (!yLabel.has(y)) {
            const item = yExtract(unit).find((i) => i.key === y);
            yLabel.set(y, item);
        }
        for (const x of xs) {
            if (!xOrder.includes(x)) continue;
            for (const y of ys) {
                const k = `${x}\u0000${y}`;
                counts.set(k, (counts.get(k) ?? 0) + 1);
            }
        }
    }
    const cells = [];
    for (const x of xOrder) {
        for (const y of yOrder) {
            const value = counts.get(`${x}\u0000${y}`) ?? 0;
            if (!value) continue;
            cells.push({ x, y, value, label: xLabel.get(x), group: yLabel.get(y) });
        }
    }
    return { cells, xOrder, yOrder };
}

/** 桑基：癌种 → 靶点 → 药物，只保留 Top 癌种/靶点/药物，避免图不可读 */
export function flow(units, { topIndication = 8, topTarget = 10, topDrug = 10 } = {}) {
    const ind = rank(units, { dim: 'indication' }).rows.slice(0, topIndication);
    const keepInd = new Set(ind.map((r) => r.key));
    const indUnit = new Map();
    for (const unit of units) {
        const keys = unit.indications.map((p) => p.cn).filter((k) => keepInd.has(k));
        if (keys.length) indUnit.set(unit.esid, keys);
    }
    const sub = units.filter((u) => indUnit.has(u.esid));
    const targetRows = rank(sub, { dim: 'target' }).rows.slice(0, topTarget);
    const drugRows = rank(sub, { dim: 'drug' }).rows.slice(0, topDrug);
    const keepTarget = new Set(targetRows.map((r) => r.key));
    const keepDrug = new Set(drugRows.map((r) => r.key));

    const it = new Map(); // indication→target
    const td = new Map(); // target→drug
    for (const unit of sub) {
        const inds = indUnit.get(unit.esid);
        const targets = new Set(unit.drugs.flatMap((d) => d.targets).filter((t) => keepTarget.has(t)));
        const drugs = new Set(unit.drugs.map((d) => d.cn).filter((n) => keepDrug.has(n)));
        for (const i of inds) for (const t of targets) {
            const k = `${i}\u0000${t}`;
            it.set(k, (it.get(k) ?? 0) + 1);
        }
        for (const d of unit.drugs) {
            if (!keepDrug.has(d.cn)) continue;
            for (const t of d.targets) {
                if (!keepTarget.has(t)) continue;
                const k = `${t}\u0000${d.cn}`;
                td.set(k, (td.get(k) ?? 0) + 1);
            }
        }
    }
    const edges = [];
    for (const [k, value] of it) {
        const [source, target] = k.split('\u0000');
        edges.push({ source, target, value });
    }
    for (const [k, value] of td) {
        const [source, target] = k.split('\u0000');
        edges.push({ source, target, value });
    }
    return { edges, indications: ind, targets: targetRows, drugs: drugRows };
}

/** 说明 / 来源节点树（三处复用：图表 notes） */
export function sourceNote(rows) {
    return {
        kind: 'layout',
        role: 'source-note',
        rows: rows.map(([label, content]) => ({
            kind: 'layout',
            role: 'source-note-row',
            cols: [
                { kind: 'string', role: 'note-label', markdown: label },
                { kind: 'string', role: 'note-content', markdown: content },
            ],
        })),
    };
}

const envelope = (config) => ({ ...ENVELOPE, config });

const pct = (a, b) => (b ? `${((a / b) * 100).toFixed(1)}%` : '0.0%');

function meetingPart(meeting) {
    return { apiKey: 'meeting_tags', list: [{ label: meeting, value: meeting }] };
}

function drillFor(view, row, meeting) {
    const parts = [meetingPart(meeting)];
    if (view.drillKey && row?.ids?.size && row.ids.size <= MAX_DRILL_VALUES) {
        parts.push({ apiKey: view.drillKey, list: [...row.ids].map((id) => ({ label: row.cn, value: id })) });
    }
    return parts;
}

/** 条形图：排名 + 尾部合并 */
export function renderBar({ units, view, meeting, lang, source }) {
    const { rows, covered } = rank(units, view);
    if (!rows.length) return { skipped: 'empty' };
    const head = rows.slice(0, view.topN);
    const tail = rows.slice(view.topN);
    const total = rows.reduce((s, r) => s + r.value, 0);
    const data = head.map((r) => {
        const label = lang === 'en' ? r.en : r.cn;
        return { label, value: r.value, drill: drillFor(view, r, meeting) };
    });
    const headShare = pct(head.reduce((s, r) => s + r.value, 0), total);
    // 长尾不画成一根巨大的「其他」柱（会压扁头部）：尾部的类数与占比写进「口径」行
    const tailText = view.tailBucket && tail.length
        ? (lang === 'en' ? `; the remaining ${tail.length} values take ${pct(total - head.reduce((s, r) => s + r.value, 0), total)}`
            : `；其余 ${tail.length} 个取值合计占 ${pct(total - head.reduce((s, r) => s + r.value, 0), total)}`)
        : '';
    // 副标题只放「会议 + 统计单位」，口径细节（Top-N 覆盖 / 口径内总数 / 长尾 / 已标注）进 notes
    const subTitle = lang === 'en'
        ? `${meeting} · abstracts per study`
        : `${meeting} · 研究摘要数（按研究去重）`;
    const caliber = lang === 'en'
        ? `Top ${head.length} cover ${headShare} of ${total} mentions${tailText}; abstracts carrying this dimension: ${covered}`
        : `图中 Top ${head.length} 合计占 ${headShare}（口径内总数 ${total}${tailText}）；带该维度标注的摘要 ${covered} 篇`;
    return envelope({
        kind: 'chart',
        type: view.type,
        height: 'auto',
        maxHeight: view.type === 'bar' ? 520 : 460,
        title: lang === 'en' ? view.title.en : view.title.cn,
        subTitle,
        notes: [sourceNote(lang === 'en'
            ? [['Note: ', view.note.en], ['Counting: ', caliber], ['Source: ', source.en]]
            : [['说明：', view.note.cn], ['口径：', caliber], ['数据来源：', source.cn]])],
        axisXTitle: lang === 'en' ? view.axis.x.en : view.axis.x.cn,
        axisYTitle: lang === 'en' ? view.axis.y.en : view.axis.y.cn,
        data,
    });
}

/** 热力图：X 轴维度 × Y 轴维度 */
export function renderHeatmap({ units, view, meeting, lang, source }) {
    const yExtract = DIMENSIONS[view.dimY];
    const yOrderAll = rank(units, { dim: view.dimY }).rows.map((r) => r.key);
    const { cells, xOrder } = cross(units, view, yOrderAll);
    if (!cells.length) return { skipped: 'empty' };
    const total = cells.reduce((s, c) => s + c.value, 0);
    const data = cells.map((c) => ({
        label: lang === 'en' ? c.label.en : c.label.cn,
        group: lang === 'en' ? c.group.en : c.group.cn,
        value: c.value,
        drill: [meetingPart(meeting)],
    }));
    return envelope({
        kind: 'chart',
        type: 'heatmap',
        height: 'auto',
        maxHeight: 460,
        title: lang === 'en' ? view.title.en : view.title.cn,
        subTitle: lang === 'en' ? `${meeting} · abstracts per study` : `${meeting} · 研究摘要数（按研究去重）`,
        notes: [sourceNote(lang === 'en'
            ? [['Note: ', view.note.en],
               ['Counting: ', `${xOrder.length} × ${yOrderAll.length} grid, ${cells.length} non-empty cells, ${total} mentions in total; an empty cell means no abstract for that combination`],
               ['Source: ', source.en]]
            : [['说明：', view.note.cn],
               ['口径：', `${xOrder.length} × ${yOrderAll.length} 格，非空格 ${cells.length} 个，口径内合计 ${total} 条；空格 = 该组合没有摘要`],
               ['数据来源：', source.cn]])],
        axisXTitle: lang === 'en' ? view.axis.x.en : view.axis.x.cn,
        axisYTitle: lang === 'en' ? view.axis.y.en : view.axis.y.cn,
        data,
    });
}

/** 桑基：癌种 → 靶点 → 药物 */
export function renderSankey({ units, view, meeting, lang, source }) {
    const { edges } = flow(units);
    if (!edges.length) return { skipped: 'empty' };
    return envelope({
        kind: 'chart',
        type: 'sankey',
        height: 'auto',
        maxHeight: 520,
        title: lang === 'en' ? view.title.en : view.title.cn,
        subTitle: lang === 'en' ? `${meeting} · abstracts per study` : `${meeting} · 研究摘要数（按研究去重）`,
        notes: [sourceNote(lang === 'en'
            ? [['Note: ', view.note.en],
               ['Counting: ', `${edges.length} paths; only the most disclosed cancer types and their targets and drugs are kept, so this is a reading path rather than the full distribution`],
               ['Source: ', source.en]]
            : [['说明：', view.note.cn],
               ['口径：', `路径 ${edges.length} 条；只保留披露最多的癌种及其靶点、药物，用于读传导路径，不代表全量分布`],
               ['数据来源：', source.cn]])],
        levels: lang === 'en' ? ['Cancer type', 'Target', 'Drug'] : ['癌种', '靶点', '药物'],
        data: edges.map((e) => ({ ...e, drill: [meetingPart(meeting)] })),
    });
}

export const RENDERERS = { bar: renderBar, heatmap: renderHeatmap, sankey: renderSankey };

/** 总结块节点树（报告末尾唯一一个 ::visualization[总结] 占位） */
export function summaryCallout({ lang, markdown }) {
    return envelope({
        kind: 'layout',
        role: 'summary-callout',
        rows: [
            { kind: 'string', role: 'summary-label', text: lang === 'en' ? 'Summary' : '总结' },
            { kind: 'string', role: 'summary-text', markdown },
        ],
    });
}
