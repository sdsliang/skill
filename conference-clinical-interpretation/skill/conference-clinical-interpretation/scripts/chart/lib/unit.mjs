/**
 * 把合并后的原始结果（MCP 拍平键 `clinical_result_*`）归一化成分析单元 unit。
 *
 * 计数口径固定为「研究摘要数」：一条 unit = 一个 `clinical_result_extra_esid`。
 * 多值维度（癌种 / 靶点 / 机制 / 申办方…）在同一个 unit 内先去重再计数，
 * 因此各维度占比之和可能大于 100%，这是口径决定的，不是数据错误。
 */

export const arr = (v) => (v === null || v === undefined ? [] : Array.isArray(v) ? v : [v]);
export const txt = (v) => (v === null || v === undefined ? '' : String(v).trim());
export const uniq = (xs) => [...new Set(xs)];

/** 中英平行数组按位置配对，缺一侧时用另一侧兜底（语言底线：取不到译名就保留来源写法） */
function pairs(cnList, enList) {
    const cn = arr(cnList).map(txt);
    const en = arr(enList).map(txt);
    const out = [];
    for (let i = 0; i < Math.max(cn.length, en.length); i += 1) {
        const c = cn[i] ?? '';
        const e = en[i] ?? '';
        if (!c && !e) continue;
        out.push({ cn: c || e, en: e || c });
    }
    return out;
}

/** 日期取 YYYY-MM-DD */
export const day = (v) => txt(v).slice(0, 10);

function normalizeDrug(d) {
    const institutes = pairs(d.research_institute_names_cn, d.research_institute_names_en)
        .map((p, i) => ({ ...p, id: txt(arr(d.research_institute_ids)[i]) }));
    const moa = pairs(d.moa_name_cn, d.moa_name_en);
    return {
        id: txt(d.drug_earth_id),
        cn: txt(d.drug_earth_name_cn) || txt(d.drug_earth_all_name) || txt(d.drug_earth_name_en),
        en: txt(d.drug_earth_name_en) || txt(d.drug_earth_all_name) || txt(d.drug_earth_name_cn),
        targets: uniq(arr(d.target_name).map(txt).filter(Boolean)),
        targetIds: arr(d.target_ids).map(txt),
        moa: moa.length ? moa : pairs(d.moa_name_cn, d.moa_name_en),
        institutes,
    };
}

export function toUnit(rec) {
    const arms = arr(rec.clinical_result_arms);
    const drugs = [];
    for (const arm of arms) for (const d of arr(arm?.drugs)) drugs.push(normalizeDrug(d));

    const projects = arr(rec.clinical_result_projects);
    const companies = [];
    for (const p of projects) {
        const list = pairs(p.company_name_cn, p.company_name_en);
        const ids = arr(p.company_ids);
        list.forEach((pair, i) => {
            companies.push({ ...pair, id: txt(ids[i]), country: txt(arr(p.country_names)[0]) });
        });
    }

    const indications = pairs(rec.clinical_result_indication_name, rec.clinical_result_indication_name_en);
    return {
        esid: txt(rec.clinical_result_extra_esid) || txt(rec.clinical_result__id),
        title: txt(rec.clinical_result_paper_title),
        day: day(rec.clinical_result_paper_release_time),
        link: txt(rec.clinical_result_full_article_link),
        evaluation: txt(rec.clinical_result_evaluation),
        keyEvidence: txt(rec.clinical_result_key_evidence),
        lba: txt(rec.clinical_result_lba),
        indications,
        // 平台疾病 ID 只在「单癌种摘要」上无歧义，多癌种摘要不参与按 ID 下钻
        indicationIds: indications.length === 1 ? [txt(rec.disease_id)].filter(Boolean) : [],
        domains: uniq(arr(rec.clinical_result_indication_type_cn).map(txt).filter(Boolean)),
        stages: pairs(rec.clinical_result_clinical_stage_cn, rec.clinical_result_clinical_stage_en),
        pathologies: pairs(rec.clinical_result_pathology_cn, rec.clinical_result_pathology_en),
        biomarkers: pairs(rec.clinical_result_biomarker_cn, rec.clinical_result_biomarker_en),
        therapyLines: pairs(rec.clinical_result_therapy_line_cn, rec.clinical_result_therapy_line_en),
        evidenceSources: uniq(arr(rec.clinical_result_evidence_source).map(txt).filter(Boolean)),
        endpoints: pairs(rec.clinical_result_primary_endpoint_cn, rec.clinical_result_primary_endpoint_en),
        designs: {
            randomized: arr(rec.clinical_result_randomized).map(txt).filter(Boolean),
            blinded: arr(rec.clinical_result_blinded).map(txt).filter(Boolean),
            multiCenter: arr(rec.clinical_result_multi_center).map(txt).filter(Boolean),
            control: arr(rec.clinical_result_trial_control).map(txt).filter(Boolean),
        },
        groupCount: txt(rec.clinical_result_group_count),
        drugs,
        companies,
    };
}

export const unitsFromLines = (lines) =>
    lines.filter((l) => l.trim()).map((l) => toUnit(JSON.parse(l)));
