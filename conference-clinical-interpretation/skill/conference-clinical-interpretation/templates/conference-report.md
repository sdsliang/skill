# {会议名} 临床解读报告

> 数据来源：`np_clinical`（`base.journal` = {会议名}）｜分析口径：见本文档末「信息缺口与局限」
> 生成时间：{ISO 时间}｜匹配记录数：{matched_records}｜分析合格记录数：{analysis_eligible_records}

## 1. 元信息

- **会议**：{会议名}
- **数据索引**：`np_clinical`
- **匹配规则**：`base.journal.text` / `base.journal.meta.text` 精确匹配 "{会议名}"
- **排除**：`deleted=true` / `is_delete=是`
- **分析口径**：`latest` / `is_show` ≠ 否
- **记录数**：匹配 {matched_records}，分析合格 {analysis_eligible_records}

## 2. 会议全景

::visualization[关键指标]{path="/workspace/visualizations/conference-stats.json"}

- 记录总数、唯一药物数、唯一适应症数、唯一生物标志物数（见 overview）。
- **热度提示**：记录最多的药物/适应症代表曝光广度，不代表临床价值（详见第 3 章）。

::visualization[记录按评价分布]{path="/workspace/visualizations/chart-data.json"}

::visualization[记录按研发阶段分布]{path="/workspace/visualizations/chart-data.json"}

- 评价分布：积极 {积极数} / 不佳 {不佳数} / 终止 {终止数}。
- 阶段分布：以 {top_phase} 为主，反映会议以 {phase_note} 为主。

## 3. 热点主题洞察

> 本 skill 的核心立场：**热度 ≠ 记录数**。以下主题综合曝光广度与临床价值判断，每个主题给出代表性证据 ID 引用。

### 主题 1：{主题标题}
- **观察**：{该主题对应的统计信号}
- **价值判断**：{是否值得关注的理由，结合评价质量/样本/阶段}
- **代表性证据**：(证据: {evidence_id}) {一句话要点}

...

## 4. 药物–适应症/标志物网络

::visualization[药物–适应症关系网络]{path="/workspace/visualizations/chart-data.json"}

- {网络解读：核心药物、高连接适应症、标志物绑定关系}

## 5. 研发阶段 × 评价

::visualization[研发阶段 × 评价堆叠图]{path="/workspace/visualizations/chart-data.json"}

- {交叉解读：哪个阶段积极信号最密/最弱}

## 6. 代表性证据精选

| 证据 ID | 试验 | 适应症 | 药物 | 阶段 | 样本量 | 评价 | 要点 |
|---|---|---|---|---|---|---|---|
| {id} | {trial} | {indication} | {drug} | {phase} | {n} | {evaluation} | {efficacy_text 要点} |

## 7. 负面与终止信号

| 证据 ID | 试验 | 适应症 | 评价 | 警示 |
|---|---|---|---|---|
| {id} | {trial} | {indication} | 不佳/终止 | {失败教训/风险提示} |

## 8. 推荐关注概览

::visualization[推荐关注清单]{path="/workspace/visualizations/watchlist.csv"}

> 完整清单见 `watchlist.csv`（按综合价值评分排序，非记录数）。以下为 Top 概览：

- **#1 {trial}**（{indication}，{drug}，{phase}，n={sample_size}）：{一句话理由}
- **#2 {trial}**（{indication}，{drug}，{phase}，n={sample_size}）：{一句话理由}
- **#3 {trial}**（{indication}，{drug}，{phase}，n={sample_size}）：{一句话理由}

## 8a. 中国企业/中国创新药参与（可选章节）

> 通过药物画像（drug_earth 字典）companies 判定中国药企归属，属**近似推断**，详见「信息缺口与局限」。

- 参与概况：会议记录中涉及中国药企研发药物的 {药物数} 个、{记录数} 条，主要机制为 {ADC/双抗/小分子…}。
- 代表性中国创新药证据（每个给出证据 ID）：
  - {药物}（{公司}，{机制}）：{证据 ID} {要点}
- 与全球对比：中国创新药在 {癌种/机制} 的占比与信号方向。

## 9. 信息缺口与局限

- {未报告完整终点数值的维度}
- {发布日期缺失情况}
- {报告类型（口头报告/LBA/壁报）字段缺失，无法按报告级别分层}
- {中国企业归属为近似推断：通过药物研发机构（companies）判定，非申办方字段；originator_regions 过于宽泛，仅作参考}
- {跨试验不可池化/不等效推断的说明}
- {其他方法局限}

## 10. 引用与证据

- 本报告所有论断可溯源到 `evidence_scatter[].id`；数值以 `efficacy_text` 为准，未报告则标注。
- 数据文件：`/workspace/visualizations/conference-stats.json`、`/workspace/visualizations/chart-data.json`、`/workspace/visualizations/watchlist.csv`。
