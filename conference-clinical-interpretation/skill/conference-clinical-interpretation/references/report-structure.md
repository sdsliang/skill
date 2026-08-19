# 报告结构 (Report Structure)

「会议临床解读」的 Markdown 报告严格遵循 `templates/conference-report.md` 的章节结构。模型不改变章节顺序，只填充内容。报告是**统计解读**，不是逐条列试验。

## 章节总览

| # | 章节 | 内容 | 数据来源 |
|---|---|---|---|
| 1 | 元信息 | 会议名、记录数、分析口径、生成时间 | 快照 overview |
| 2 | 会议全景 (KPI + 分布) | 关键指标卡 + 评价/阶段/适应症分布图 | 统计 distributions |
| 3 | 热点主题洞察 | 3-7 个主题，每个含代表性证据引用与判断 | evidence_scatter + 统计 |
| 4 | 药物–适应症/标志物网络 | 实体关系网络图 + 解读 | entity_network |
| 5 | 研发阶段 × 评价 | 成熟度与积极信号交叉 | stacked_bar_phase_eval |
| 6 | 代表性证据精选 | 按「热度≠记录数」原则挑选的证据表 | evidence_scatter |
| 7 | 负面与终止信号 | 不佳/终止评价的代表性试验 | evaluation=不佳/终止 |
| 8 | 推荐关注概览 | watchlist **概览**（Top 3-5 + 一句话摘要 + CSV 引用），不列完整明细 | watchlist.csv |
| 8a（可选） | 中国企业/中国创新药参与 | 中国药企药物在会议中的参与度与代表性证据 | drug-profiles + evidence |
| 9 | 信息缺口与局限 | 缺失维度、方法局限 | — |
| 10 | 引用 | 证据 ID 与来源说明 | — |

## 写作规则

- **热度≠记录数**：所有涉及"多/热"的表述必须同时说明"是曝光多还是价值高"。
- **论断可溯源**：关键论断后加证据 ID，如 `(证据: 24_37_xxx)`。
- **数值以 evidence 为准**：`efficacy_text` 未提供的数值，标注"未报告"。
- **图表引用**：每个图表在正文用 `::visualization[标题]{path=...}` 独占一行引用，并在其后 1-2 句解读。
- **不池化/不等效推断**：不合并跨试验数值，不声称等效。
- **语气**：会议解读/行业观察语气，非注册文件语气。

## 清单不在正文展开

- 推荐关注清单的**完整明细只存在于 `watchlist.csv`**（可下载、可复用）；报告正文只呈现**概览**：Top 3-5 条的一句话摘要 + 指向 CSV 的 `::visualization` 引用。
- 理由：报告是**统计解读**，不是逐条罗列；详细清单属于数据交付物而非分析正文，避免正文与 CSV 重复维护、避免报告臃肿。
- 若用户明确要求"在报告里看到完整清单"，再以表格形式补第 8 章（此时仍以 CSV 为唯一数据源）。

## 分析维度（可在热点主题/章节中选用）

> 参考 ASCO 2026 媒体与分析框架（医药媒体常见维度），结合数据可得性选用；每章都要有证据引用，缺失维度在"信息缺口"中说明。

| 维度 | 说明 | 数据支持 |
|---|---|---|
| 评价/结果方向 | 积极/不佳/终止分布 | distributions.evaluation |
| 研发阶段/疾病阶段 | 成熟度交叉 | distributions.trial_phase / disease_stage |
| 癌种/适应症 | 按癌种热度与信号 | distributions.indication |
| 治疗线数 | 一线/后线/围手术期前移 | distributions.therapy_line |
| 终点类型 | 证据强度（OS/EFS/ORR…） | distributions.endpoint |
| 生物标志物 | 伴随诊断/转化医学 | distributions.biomarker |
| 发布节奏 | 披露峰值与趋势 | distributions.release_date |
| **中国企业/中国创新药参与** | 中国药企研发药物的参与度与代表性证据 | drug-profiles.companies + evidence（见 drug-enrichment.md） |
| **技术路线/机制聚类** | ADC/双抗/免疫/小分子/细胞治疗等模态分布 | drug-profiles.modality / moa_class + evidence |
| 联合治疗策略 | 免疫±靶向±化疗、新辅助/辅助等组合 | evidence.efficacy_text / drugs |

- 报告类型（口头报告/LBA/壁报）是媒体常用维度，但 `np_clinical` 当前**无此字段**，在"信息缺口"中说明，勿臆造。
- 企业归属通过药物画像 companies 判定，标注"近似"并说明局限（见 drug-enrichment.md 中国企业判定）。
