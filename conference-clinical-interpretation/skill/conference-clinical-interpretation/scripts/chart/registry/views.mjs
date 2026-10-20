/**
 * 会议临床解读的维度与图表注册表。
 *
 * 约定：一个视图 = 一章里的一张图；图型只用平台已开放渲染的四类
 * （bar / heatmap / sankey / scatter），维度不过门槛就整行跳过，不换图型重画。
 * 所有计数口径都是「研究摘要数」（一条 = 一个 extra_esid）。
 */

/** 枚举值的中英对照；取不到可靠译名时保留来源写法（不机翻、不音译） */
const EN = {
    domain: {
        肿瘤领域: 'Oncology',
        '罕见病(欧洲)': 'Rare disease (Europe)',
        '罕见病(美国)': 'Rare disease (US)',
        '罕见病(中国)': 'Rare disease (China)',
        血液领域: 'Hematology',
        免疫领域: 'Immunology',
        感染领域: 'Infectious disease',
        '内分泌及代谢领域': 'Endocrine & metabolic',
        诊断试剂领域: 'Diagnostics',
        消化领域: 'Gastroenterology',
        心脑血管领域: 'Cardiovascular',
        神经领域: 'Neurology',
        麻醉镇痛领域: 'Anesthesia & pain',
        呼吸领域: 'Respiratory',
    },
    evidence: {
        回顾性研究: 'Retrospective study',
        真实世界研究: 'Real-world study',
        前瞻性研究: 'Prospective study',
        汇总分析: 'Pooled analysis',
        其他: 'Other',
        Other: 'Other',
        'Not Applicable': 'Not applicable',
    },
    evaluation: {
        积极: 'Positive',
        不佳: 'Unfavorable',
        终止: 'Terminated',
        '-': 'Not assessed',
    },
    stage: {
        晚期: 'Advanced',
        局部晚期: 'Locally advanced',
        早期: 'Early',
        广泛期: 'Extensive stage',
        局限期: 'Limited stage',
        慢性期: 'Chronic phase',
        加速期: 'Accelerated phase',
        '0期': 'Stage 0',
        I期: 'Stage I',
        II期: 'Stage II',
        III期: 'Stage III',
        IV期: 'Stage IV',
    },
};

/** 靶点占位值（平台未标注时的兜底文案），不计入排名 */
const NON_TARGET_TOKENS = new Set(['not available', 'n/a', 'na', 'none', 'unknown', 'unclear', 'tbd', '其他', 'other']);

/** 中国口径：只认平台给的登记地/机构地区，不做名称白名单猜测 */
const CN_COUNTRIES = new Set(['中国内地', '中国(港澳台)']);
const isChinaUnit = (u) => u.companies.some((c) => CN_COUNTRIES.has(c.country));

const normName = (s2) => String(s2 ?? '').toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]/g, '');

/** 该研究是否由「非研发方」发起：申办方与全部药物研发机构无交集 */
const isExternallyLed = (u) => {
    const sponsors = new Set(u.companies.map((c) => normName(c.en || c.cn)).filter(Boolean));
    const owners = u.drugs.flatMap((d) => d.institutes.map((i) => normName(i.en || i.cn))).filter(Boolean);
    if (!sponsors.size || !owners.length) return false;
    return owners.every((n) => !sponsors.has(n));
};

const label = (dict, cn, en) => ({ cn, en: EN[dict]?.[cn] ?? (en || cn) });

/** 维度取值提取器：unit → [{ key, cn, en, id }]（同一 unit 内去重由聚合层做） */
export const DIMENSIONS = {
    indication: (u) => u.indications.map((p) => ({ key: p.cn, ...p, ids: u.indicationIds })),
    domain: (u) => u.domains.map((c) => ({ key: c, ...label('domain', c) })),
    company: (u) => u.companies.map((c) => ({ key: c.cn, cn: c.cn, en: c.en, ids: [c.id].filter(Boolean) })),
    /** 药物研发机构（药品的研发/持有方），与「申办方」是两个不同口径 */
    institute: (u) => u.drugs.flatMap((d) => d.institutes.map((i) => ({
        key: i.cn || i.en, cn: i.cn || i.en, en: i.en || i.cn, ids: [i.id].filter(Boolean),
    }))),
    /**
     * 只保留「申办方里没有该药研发方」的研究——即外部（学术/医院/其他公司）在推进别人的资产。
     * 用于看「谁在做外部验证」，与「谁在主导研究」区分开。
     */
    instituteExternal: (u) => (isExternallyLed(u) ? DIMENSIONS.institute(u) : []),
    country: (u) => {
        const seen = new Map();
        for (const c of u.companies) if (c.country && !seen.has(c.country)) seen.set(c.country, 1);
        return [...seen.keys()].map((c) => ({ key: c, cn: c, en: c }));
    },
    stage: (u) => u.stages.map((p) => ({ key: p.cn, ...label('stage', p.cn, p.en) })),
    evidenceSource: (u) => u.evidenceSources.map((c) => ({ key: c, ...label('evidence', c) })),
    evaluation: (u) => {
        if (!u.evaluation) return [];
        const l = label('evaluation', u.evaluation);
        // '-' 是平台的「未标注」占位，图上不能原样露出
        return [u.evaluation === '-'
            ? { key: '-', cn: '未评价', en: 'Not assessed' }
            : { key: u.evaluation, ...l }];
    },
    therapyLine: (u) => u.therapyLines.map((p) => ({ key: p.cn, cn: p.cn, en: p.en })),
    target: (u) => {
        const out = [];
        for (const d of u.drugs) d.targets.forEach((t, i) => {
            if (NON_TARGET_TOKENS.has(t.toLowerCase())) return;
            out.push({ key: t, cn: t, en: t, ids: [d.targetIds[i]].filter(Boolean) });
        });
        return out;
    },
    drug: (u) => u.drugs.map((d) => ({ key: d.cn, cn: d.cn, en: d.en, ids: [d.id].filter(Boolean) })),
    /** 披露日期（YYYY-MM-DD） */
    day: (u) => (u.day ? [{ key: u.day, cn: u.day, en: u.day }] : []),
    /** 中国口径：申办方登记地或药物研发机构地区在中国内地/港澳台 */
    chinaRegion: (u) => (isChinaUnit(u)
        ? [{ key: 'cn', cn: '中国主导研究', en: 'China-led' }]
        : [{ key: 'row', cn: '其他地区', en: 'Rest of world' }]),
    chinaSponsor: (u) => (isChinaUnit(u)
        ? u.companies.filter((c) => CN_COUNTRIES.has(c.country))
            .map((c) => ({ key: c.cn, cn: c.cn, en: c.en, ids: [c.id].filter(Boolean) }))
        : []),
    chinaTarget: (u) => (isChinaUnit(u) ? DIMENSIONS.target(u) : []),
    chinaIndication: (u) => (isChinaUnit(u) ? DIMENSIONS.indication(u) : []),
    /** 表现不佳或终止的研究所涉及的癌种（塌方口径） */
    negativeIndication: (u) => (u.evaluation === '不佳' || u.evaluation === '终止'
        ? DIMENSIONS.indication(u)
        : []),
    moa: (u) => u.drugs.flatMap((d) => d.moa.map((p) => ({ key: p.cn, cn: p.cn, en: p.en }))),
};

/** 章节骨架：报告章节顺序与图表归属的唯一来源 */
export const CHAPTERS = [
    {
        no: 1,
        act: '第一幕 · 一眼看完',
        actEn: 'Act I · The one-screen view',
        title: '本届一眼看完',
        titleEn: 'This meeting at a glance',
        narrative: '规模、节奏、地域：多少篇、什么时候放、谁的地盘。后面每一幕都建立在这一屏的基础上。',
        narrativeEn: 'Scale, tempo, geography: how many abstracts, when they dropped, and whose turf it is. Everything that follows builds on this screen.',
    },
    {
        no: 2,
        act: '第二幕 · 热点与成熟度',
        actEn: 'Act II · Heat and maturity',
        title: '热点在哪，证据成熟到什么程度',
        titleEn: 'Where the heat is, and how mature the evidence is',
        narrative: '癌种与领域说明「大家在抢什么」，分期、证据类型与总体评价说明「抢到的东西有多硬」。两张牌一起看，才知道哪些结论可以外推、哪些只是早期信号。',
        narrativeEn: 'Cancer types and domains say what everyone is racing for; staging, evidence type and overall assessment say how solid the result is. Read them together before carrying any conclusion forward.',
    },
    {
        no: 3,
        act: '第三幕 · 谁在抢位置',
        actEn: 'Act III · Who is taking the position',
        title: '谁在做研究，谁握着资产',
        titleEn: 'Who runs the studies, and who owns the assets',
        narrative: '申办方是「谁做这项研究」，药物研发机构是「药属于谁」，两者多数不是同一家；再看靶点、药物与机制的集中度，以及「癌种 → 靶点 → 药物」的传导路径。',
        narrativeEn: 'Sponsors say who runs the study; originators say who owns the drug — usually not the same party. Then the concentration of targets, drugs and mechanisms, plus the cancer type → target → drug pathways.',
    },
    {
        no: 4,
        act: '第四幕 · 中国声音',
        actEn: 'Act IV · The China voice',
        title: '中国研究在这届会上是什么位置',
        titleEn: 'Where China-based work stands at this meeting',
        narrative: '按「申办方登记地在中国内地/港澳台」这一条硬口径统计中国研究：谁在领跑、集中在哪些癌种与靶点、积极率与其他地区差多少。',
        narrativeEn: 'China-related work defined by one hard rule — the sponsor is registered in mainland China, Hong Kong, Macau or Taiwan: who leads, where it concentrates, and how its positivity rate compares with the rest of the world.',
    },
    {
        no: 5,
        act: '第五幕 · 可行动信号',
        actEn: 'Act V · Actionable signals',
        title: '哪几条能改变决策',
        titleEn: 'The few items that could change a decision',
        narrative: '把上千条平均信息压成一页清单：每条给出「为什么值得动」，以及它只能支持到什么程度。本章不放图，只放分级后的清单。',
        narrativeEn: 'Compressing a thousand average data points into one page: why each item deserves action, and how far it can support a decision. No charts here — only the graded list.',
    },
    {
        no: 6,
        act: '第六幕 · 塌方与空白',
        actEn: 'Act VI · Damage and gaps',
        title: '哪里在塌，哪里是空白，接下来盯谁',
        titleEn: 'Where it broke, where nobody goes, and what to watch',
        narrative: '不佳与终止集中在哪些癌种、哪些问题还没有答案，以及会后 6–12 个月值得盯的资产与时点。',
        narrativeEn: 'Where negative and terminated results cluster, which questions remain unanswered, and which assets and dates to watch over the next 6–12 months.',
    },
];

/** 视图注册表 */
export const VIEWS = [
    {
        id: 'rank-indication-bar',
        chapter: 2,
        type: 'bar',
        dim: 'indication',
        drillKey: 'indication_ids',
        topN: 20,
        tailBucket: true,
        title: { cn: '高披露癌种', en: 'Most disclosed cancer types' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '癌种', en: 'Cancer type' } },
        note: {
            cn: '提及该癌种的研究摘要数；一个摘要可涉及多个癌种，分别计入，占比之和大于 100%。',
            en: 'Abstracts mentioning the cancer type; one abstract can count for several types, so shares sum to more than 100%.',
        },
    },
    {
        id: 'rank-domain-bar',
        chapter: 2,
        type: 'bar',
        dim: 'domain',
        drillKey: null,
        topN: 12,
        tailBucket: false,
        title: { cn: '疾病领域构成', en: 'Disease domains' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '疾病领域', en: 'Domain' } },
        note: {
            cn: '按平台疾病领域标签统计，一个摘要可同时属于多个领域。',
            en: 'By platform disease-domain tags; one abstract can belong to several domains.',
        },
    },
    {
        id: 'rank-sponsor-bar',
        chapter: 3,
        type: 'bar',
        dim: 'company',
        drillKey: 'company_ids',
        topN: 15,
        tailBucket: true,
        title: { cn: '主要申办方', en: 'Leading sponsors' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '申办方', en: 'Sponsor' } },
        note: {
            cn: '按申办方计；一项研究有多个申办方时分别计入，IIT 与注册研究一并统计。',
            en: 'Counted per sponsor; multi-sponsor studies count once per sponsor, investigator-initiated and registrational studies alike.',
        },
    },
    {
        id: 'rank-institute-bar',
        chapter: 3,
        type: 'bar',
        dim: 'institute',
        drillKey: null,
        topN: 15,
        tailBucket: true,
        title: { cn: '主要药物研发机构', en: 'Leading drug originators' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '研发机构', en: 'Originator' } },
        note: {
            cn: '按「药物研发/持有方」计，与上图的「申办方」不是同一口径：一项研究的申办方可能是医院或 CRO，而药品的研发方另有其人。注意该字段记的是**当前药品持有方**，基础化疗药（卡铂、紫杉醇、吉西他滨、奥沙利铂等）的持有方多为仿制药企业，会把排名顶高；判断创新药格局时请结合药物榜一起读。',
            en: 'Counted per drug originator/holder — a different lens from sponsors above: the sponsor may be a hospital or CRO while the drug belongs to someone else. The field records the **current holder** of the drug, so backbone chemotherapies (carboplatin, paclitaxel, gemcitabine, oxaliplatin) are held by generic manufacturers and inflate their rank; read this together with the drug ranking when judging the innovative portfolio.',
        },
    },
    {
        id: 'rank-institute-external-bar',
        chapter: 3,
        type: 'bar',
        dim: 'instituteExternal',
        drillKey: null,
        topN: 12,
        tailBucket: false,
        title: { cn: '被外部发起研究最多的研发方', en: 'Originators most studied by external sponsors' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '研发机构', en: 'Originator' } },
        note: {
            cn: '只统计「申办方与该药研发方无交集」的研究：这类研究多为学术/医院/合作方发起的验证性研究，而非研发方自己主导的注册研究。同样受上面那条「当前持有方」的影响，仿制药持有方（如卡铂、紫杉醇、奥沙利铂）会集中出现在前列。',
            en: 'Only studies whose sponsors do not include the drug originator: mostly academic, hospital or partner-led validation rather than originator-run registrational work. The same current-holder caveat applies, so generic holders of backbone chemotherapies cluster near the top.',
        },
    },
    {
        id: 'rank-day-bar',
        chapter: 1,
        type: 'bar',
        dim: 'day',
        drillKey: null,
        topN: 20,
        tailBucket: false,
        title: { cn: '披露节奏（按日）', en: 'Disclosure tempo by day' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '日期', en: 'Date' } },
        note: {
            cn: '按平台记录的发布日期归日；同一天发布的摘要集中出现，用于判断会期内的信息密度。',
            en: 'Grouped by the release date on record; a burst shows the information density during the meeting window.',
        },
    },
    {
        id: 'rank-country-bar',
        chapter: 1,
        type: 'bar',
        dim: 'country',
        drillKey: null,
        topN: 12,
        tailBucket: false,
        title: { cn: '研究主体所在地区', en: 'Where the sponsors are based' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '地区', en: 'Region' } },
        note: {
            cn: '按申办方所在国家或地区统计；跨国企业以其登记地计入。',
            en: 'By the country or region where the sponsor is registered.',
        },
    },
    {
        id: 'rank-stage-bar',
        chapter: 2,
        type: 'bar',
        dim: 'stage',
        drillKey: null,
        topN: 12,
        tailBucket: false,
        title: { cn: '研究分期与阶段', en: 'Stage and setting' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '分期', en: 'Stage' } },
        note: {
            cn: '平台分期标签，含试验分期（Ⅰ/Ⅱ/Ⅲ期）与疾病阶段（早期、局部晚期、晚期等）；无该标签的摘要不进入本图。',
            en: 'Platform stage tags, mixing trial phase (I/II/III) with disease setting (early, locally advanced, advanced). Abstracts without the tag are excluded.',
        },
    },
    {
        id: 'rank-evidence-source-bar',
        chapter: 2,
        type: 'bar',
        dim: 'evidenceSource',
        drillKey: null,
        topN: 12,
        tailBucket: false,
        title: { cn: '证据类型', en: 'Evidence types' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '证据类型', en: 'Evidence type' } },
        note: {
            cn: '按平台证据来源标签统计；前瞻性与回顾性研究、真实世界研究、各期临床试验分别计数。',
            en: 'By platform evidence-source tags: prospective or retrospective studies, real-world studies and trial phases each count separately.',
        },
    },
    {
        id: 'rank-evaluation-bar',
        chapter: 2,
        type: 'bar',
        dim: 'evaluation',
        drillKey: null,
        topN: 6,
        tailBucket: false,
        title: { cn: '总体评价分布', en: 'Overall assessment' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '评价', en: 'Assessment' } },
        note: {
            cn: '按平台结果评价标签统计；未标注评价的摘要单列为「未评价」，不计入积极或不佳。',
            en: 'By platform result-assessment tags; unlabelled abstracts are shown as not assessed rather than counted as positive or unfavorable.',
        },
    },
    {
        id: 'matrix-stage-evaluation',
        chapter: 2,
        type: 'heatmap',
        dim: 'stage',
        dimY: 'evaluation',
        topN: 8,
        title: { cn: '分期 × 评价', en: 'Stage by assessment' },
        axis: { x: { cn: '分期', en: 'Stage' }, y: { cn: '评价', en: 'Assessment' } },
        note: {
            cn: '交叉组合的研究摘要数；格内为 0 的组合不画，读作「本届无该类研究」。',
            en: 'Abstracts per cross combination; empty cells are drawn as blank and mean no such study at this meeting.',
        },
    },
    {
        id: 'rank-target-bar',
        chapter: 3,
        type: 'bar',
        dim: 'target',
        drillKey: null,
        topN: 20,
        tailBucket: true,
        title: { cn: '热门靶点', en: 'Most studied targets' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '靶点', en: 'Target' } },
        note: {
            cn: '提及该靶点的研究摘要数；组合方案中的每个靶点分别计入。',
            en: 'Abstracts mentioning the target; each target in a combination counts separately.',
        },
    },
    {
        id: 'rank-drug-bar',
        chapter: 3,
        type: 'bar',
        dim: 'drug',
        drillKey: 'drug_earth_ids',
        topN: 20,
        tailBucket: true,
        title: { cn: '高披露药物', en: 'Most disclosed drugs' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '药物', en: 'Drug' } },
        note: {
            cn: '按药物统计的研究摘要数；同一摘要的多臂研究只计一次，联合方案中的每个药物分别计入。',
            en: 'Abstracts per drug; a multi-arm abstract counts once per drug, and each drug in a combination counts separately.',
        },
    },
    {
        id: 'rank-moa-bar',
        chapter: 3,
        type: 'bar',
        dim: 'moa',
        drillKey: null,
        topN: 15,
        tailBucket: true,
        title: { cn: '作用机制分布', en: 'Mechanisms of action' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '作用机制', en: 'Mechanism' } },
        note: {
            cn: '按平台药物作用机制标签统计；一个药物可带多个机制标签。',
            en: 'By platform mechanism-of-action tags; a drug may carry several.',
        },
    },
    {
        id: 'flow-indication-target-sankey',
        chapter: 3,
        type: 'sankey',
        topN: 8,
        title: { cn: '癌种 → 靶点 → 药物', en: 'Cancer type → target → drug' },
        note: {
            cn: '只保留披露最多的若干癌种及其下靶点、药物，用于读传导路径，不代表全量分布。',
            en: 'Only the most disclosed cancer types with their targets and drugs, to read the pathways rather than the full distribution.',
        },
    },
    {
        id: 'matrix-china-indication',
        chapter: 4,
        type: 'heatmap',
        dim: 'chinaRegion',
        dimY: 'indication',
        drillKey: null,
        topN: 10,
        title: { cn: '癌种 × 中国 / 其他地区', en: 'Cancer type × China / rest of world' },
        axis: { x: { cn: '口径', en: 'Cohort' }, y: { cn: '癌种', en: 'Cancer type' } },
        note: {
            cn: '同一癌种在中国口径与其他地区口径下的摘要数并列；中国口径 = 申办方登记地在中国内地/港澳台。缺少申办方的摘要无法归属，不计入任一侧。',
            en: 'Abstracts per cancer type for China-related work versus the rest of the world; China = sponsor registered in mainland China, Hong Kong, Macau or Taiwan. Records without a sponsor cannot be attributed and are excluded from both sides.',
        },
    },
    {
        id: 'rank-china-target-bar',
        chapter: 4,
        type: 'bar',
        dim: 'chinaTarget',
        drillKey: null,
        topN: 12,
        tailBucket: true,
        title: { cn: '中国研究最集中的靶点', en: 'Targets China-based work concentrates on' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '靶点', en: 'Target' } },
        note: {
            cn: '中国口径研究涉及的靶点排名；与全体的靶点排名对照，可以看出中国研究是跟随主流靶点还是自成一路。',
            en: 'Target ranking within China-related work; compare with the overall ranking to see whether it follows the global mainstream or runs on its own track.',
        },
    },
    {
        id: 'rank-china-sponsor-bar',
        chapter: 4,
        type: 'bar',
        dim: 'chinaSponsor',
        drillKey: 'company_ids',
        topN: 12,
        tailBucket: false,
        title: { cn: '中国申办方', en: 'China-based sponsors' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '申办方', en: 'Sponsor' } },
        note: {
            cn: '中国口径的唯一判定标准：申办方登记地在中国内地/港澳台。跨国药企的中国分公司按登记地计，不合并到总部。前列多为高校与医院（研究者发起研究），企业侧见上方「主要药物研发机构」。',
            en: 'Only sponsors registered in mainland China, Hong Kong, Macau or Taiwan; China subsidiaries of multinationals count where they are registered, not merged into the parent.',
        },
    },
    {
        id: 'rank-negative-indication-bar',
        chapter: 6,
        type: 'bar',
        dim: 'negativeIndication',
        drillKey: 'indication_ids',
        topN: 12,
        tailBucket: false,
        title: { cn: '不佳与终止集中在哪些癌种', en: 'Where negative and terminated results cluster' },
        axis: { x: { cn: '研究摘要数', en: 'Abstracts' }, y: { cn: '癌种', en: 'Cancer type' } },
        note: {
            cn: '只统计总体评价为「不佳」或「终止」的研究；这是「哪里在塌」的分母，不含未评价的研究。',
            en: 'Only studies assessed as negative or terminated; this is the denominator for where things broke, excluding unassessed work.',
        },
    },
];


export const viewsByChapter = (no) => VIEWS.filter((v) => v.chapter === no);
