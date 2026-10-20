#!/usr/bin/env node
/**
 * 第 1 步收尾：把模型分批拿回的 MCP 响应合并成一份会议全量结果集（NDJSON）。
 *
 * 为什么必须合并而不是直接拼：`pharmcube-query-clinical-result-with-params` 在
 * `selected_fields` 含 `clinical_result.arms` / `clinical_result.projects` 时单批最多回 500 行，
 * 多值字段（适应症、病理、生物标志物、终点…）会把一条结果 explode 成多行。合并口径：
 *   - 一条结果 = 一个 `clinical_result_extra_esid`；
 *   - 数组字段取各批并集去重（保序）；
 *   - 标量字段取首个非空；
 *   - 嵌套数组字段（arms / study_results / projects）按内容去重后并集。
 *
 * 用法：
 *   node scripts/chart/cli/merge-batches.mjs --dir output/build/asco-2026/batches \
 *        --out output/pharmcube-query-clinical-result-with-params/asco-2026-clinical-results.ndjson \
 *        --meeting "ASCO 2026"
 */
import fs from 'node:fs';
import path from 'node:path';

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const isEmpty = (v) => v === null || v === undefined || v === '' ||
    (Array.isArray(v) && v.length === 0);
const dedupeKey = (v) => (isPlainObject(v) || Array.isArray(v) ? JSON.stringify(v) : String(v));

/** 合并同一字段的多批取值：数组取并集、标量取首个非空、对象深合并 */
function mergeValue(a, b) {
    if (isEmpty(a)) return b;
    if (isEmpty(b)) return a;
    if (Array.isArray(a) && Array.isArray(b)) {
        const seen = new Set(a.map(dedupeKey));
        const out = [...a];
        for (const item of b) {
            const k = dedupeKey(item);
            if (!seen.has(k)) { seen.add(k); out.push(item); }
        }
        return out;
    }
    if (isPlainObject(a) && isPlainObject(b)) return mergeRecord(a, b);
    return a; // 标量冲突保留首个非空
}

function mergeRecord(target, source) {
    for (const [k, v] of Object.entries(source)) {
        target[k] = k in target ? mergeValue(target[k], v) : v;
    }
    return target;
}

function loadBatch(file) {
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    const rows = Array.isArray(raw) ? raw
        : Array.isArray(raw?.result?.data) ? raw.result.data
            : Array.isArray(raw?.data) ? raw.data
                : null;
    if (!rows) throw new Error(`${file}: 找不到 result.data / data 数组`);
    return rows;
}

export function mergeBatches(files) {
    /** @type {Map<string, any>} */
    const byId = new Map();
    let rawRows = 0;
    for (const file of files.sort()) {
        const rows = loadBatch(file);
        rawRows += rows.length;
        for (const row of rows) {
            const id = row.clinical_result_extra_esid || row.clinical_result__id;
            if (!id) throw new Error(`${path.basename(file)}: 有一行既无 extra_esid 也无 _id`);
            if (byId.has(id)) mergeRecord(byId.get(id), row);
            else byId.set(id, { ...row });
        }
    }
    return { records: [...byId.values()], rawRows, idCount: byId.size };
}

function parseArgs(argv) {
    const out = {};
    for (let i = 0; i < argv.length; i += 2) {
        const k = argv[i].replace(/^--/, '');
        out[k] = argv[i + 1];
    }
    return out;
}

if (import.meta.url === `file://${process.argv[1]}`) {
    const args = parseArgs(process.argv.slice(2));
    const dir = args.dir ?? 'output/build/asco-2026/batches';
    const meeting = args.meeting ?? 'ASCO 2026';
    const slug = meeting.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const out = args.out ??
        `output/pharmcube-query-clinical-result-with-params/${slug}-clinical-results.ndjson`;
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.json'))
        .map((f) => path.join(dir, f));
    if (!files.length) throw new Error(`${dir}: 没有批次文件（*.json）`);
    const { records, rawRows, idCount } = mergeBatches(files);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    const body = records.map((r) => JSON.stringify(r)).join('\n') + '\n';
    fs.writeFileSync(out, body);
    const meta = {
        meeting,
        batches: files.length,
        rawRows,
        records: idCount,
        bytes: Buffer.byteLength(body),
        generatedAt: new Date().toISOString(),
        mergedBy: 'scripts/chart/cli/merge-batches.mjs',
    };
    fs.writeFileSync(path.join(path.dirname(out), 'query-meta.json'),
        JSON.stringify(meta, null, 2) + '\n');
    console.log(JSON.stringify(meta, null, 2));
}
