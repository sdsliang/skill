# 数据协议 (Data Contract)

本文定义「会议临床解读」skill 的输入数据结构、字段口径、排除规则与可复现命令。所有统计与图表产物都建立在本文定义的口径之上，口径变更必须同步本文与统计脚本。

## 1. 数据来源

- **索引**：`np_clinical`（环境变量 `NP_CLINICAL_INDEX`，默认 `np_clinical`）。
- **会议匹配**：`base.journal.text` **或** `base.journal.meta.text` 与会议名（`JOURNAL` 环境变量，默认 `ASCO 2026`）**精确匹配**（ES `term`）。
- **排除规则**：`deleted=true` 或 `is_delete=是` 的记录排除。
- **分析口径**：`latest`（text 或 meta.text）≠ `否` 且 `is_show`（text 或 meta.text）≠ `否` 的记录才进入统计与图表（`analysis_eligible`）。

## 2. 输入文件

### 2.1 原始快照 `<conference>-np-clinical.json`

由拉取适配器生成，供统计脚本读取，**不直接作为模型输入**（体积大，含全文）。

```jsonc
{
  "schema_version": "1.0.0",
  "conference": "ASCO 2026",
  "index": "np_clinical",
  "generated_at": "<ISO 时间>",
  "query": {
    "index": "np_clinical",
    "conference": "ASCO 2026",
    "exact_fields": ["base.journal.text", "base.journal.meta.text"],
    "excluded": ["deleted=true", "is_delete=是"],
    "analysis_eligible_rule": "latest/meta.text != 否 AND is_show/text.meta.text != 否"
  },
  "overview": { "matched_records": 1639, "returned_records": 1639, "analysis_eligible_records": 1639 },
  "records": [ { "_id": "<证据 ID>", "_source": { /* 原始文档 */ } } ]
}
```

### 2.2 统计文件 `<conference>-stats.json`

模型的主要输入之一（确定性、轻量、无全文）。结构如下：

```jsonc
{
  "schema_version": "1.0.0",
  "generated_at": "<ISO 时间>",
  "conference": "ASCO 2026",
  "query": { /* 同快照 query */ },
  "overview": {
    "matched_records": 1639,
    "analysis_eligible_records": 1639,
    "unique_drugs": 750,
    "unique_indications": 338,
    "unique_biomarkers": 185,
    "records_with_sample_size": 1603
  },
  "distributions": {
    "evaluation":      [{ "label": "积极", "count": 1201 }, ...],   // 评价（research_design.evaluation 中文优先）
    "trial_phase":     [{ "label": "II期", "count": 445 }, ...],    // 研发阶段（base.trial_phase 中文优先）
    "disease_stage":   [{ "label": "晚期/转移", "count": 799 }, ...],// 疾病阶段（归一化）
    "indication":      [{ "label": "实体瘤", "count": 162 }, ...],  // 适应症（中文优先）
    "drug":            [{ "label": "帕博利珠单抗", "count": 134 }, ...],
    "biomarker":       [{ "label": "...", "count": ... }, ...],
    "therapy_line":    [{ "label": "二线治疗", "count": 418 }, ...],
    "endpoint":        [{ "label": "ORR", "count": 333 }, ...],
    "release_date":    [{ "label": "2026-06-01", "count": ... }, ...],
    "source":          [{ "label": "np_clinical_conference", "count": 1639 }]
  },
  "evidence_scatter": [
    {
      "id": "<证据 ID，即原始 _id>",
      "title": "<论文标题>",
      "trial": "<试验缩写或 NCT>",
      "phase": "II期",
      "disease_stage": "晚期/转移",
      "sample_size": 61,          // 整数，可能为 null
      "evaluation": "积极",        // 积极 / 不佳 / 终止 / 其他
      "indications": ["结直肠癌", ...],
      "drugs": ["68Ga-FAPI-46", ...],
      "biomarkers": [],
      "endpoints": ["ORR", ...],
      "efficacy_text": "<research_design.opt_dose_effect 拼接文本，不截断>",
      "release_date": "2026-06-01" // 可能为 null
    }
  ],
  "entity_network": [
    { "source": "<药物>", "target": "<适应症/生物标志物>", "weight": <出现次数> }
  ]
}
```

## 3. 字段口径

| 统计维度 | 来源字段 | 取值逻辑 | 备注 |
|---|---|---|---|
| 评价 | `research_design.evaluation` | `meta.text` 优先（积极/不佳/终止/-） | 英文 `text` 为 Positive/Unfavorable/Terminated |
| 研发阶段 | `base.trial_phase` | `meta.text` 优先（I期/II期/III期...） | `text` 为 Phase 1/2/3... |
| 疾病阶段 | `indications.clinical_stage_new` | 归一化到 晚期/转移、早期、局部晚期/局部、I期、II期、III期、IV期、其他/未明确 | 原文五花八门，必须归一化，见统计脚本 `normalizeDiseaseStages` |
| 适应症 | `indications.indications` | `meta.text` 优先（中文） | `text` 为英文 |
| 药物 | `base.trial_drug` | 数组，`meta.text` 优先 | 注意含化疗辅药（奥沙利铂/卡铂/氟尿嘧啶），见「热度≠记录数」 |
| 生物标志物 | `indications.bio_labels` | `meta.text` 优先 | 可能为空数组 |
| 治疗线 | `indications.therapy_labels` | `meta.text` 优先 | 二线/一线/新辅助... |
| 终点 | `research_design.opt_dose_effect`（文本） | 按正则模式识别 OS/PFS/ORR/CR/DCR/DoR/DFS/EFS/RFS/ctDNA-MRD/Safety | 未命中归为 Other/unspecified |
| 发布日期 | `base.paper_release_time_str` | 取首个值 | 可能为 null |
| 样本量 | `trial.group_count` | 解析首个数字 | 可能为 null |

## 4. 可复现命令

```bash
# 1) 拉取原始快照（POC env 提供 ES 凭据；凭据绝不写入本项目文件）
node --env-file=/home/xupeipeioo1/apps/POC/.env \
  evals/fetch-conference-np-clinical.mjs \
  evals/fixtures/asco-2026-np-clinical.json "ASCO 2026"

# 2) 生成确定性统计文件
node evals/build-conference-stats.mjs \
  evals/fixtures/asco-2026-np-clinical.json \
  evals/fixtures/asco-2026-stats.json

# 3) （可选）模型生成的统计产物写入 /workspace/visualizations/conference-stats.json
```

## 5. 模型在运行时如何获得数据

- 若数据已由外部提供（快照 + 统计文件），直接读取。
- 若只有会议名而无数据：运行上述命令或调用提供数据的外部适配器，然后将**统计文件**（非原始快照）纳入上下文，原始快照仅保留在 `/workspace/` 供统计脚本读取。
- **原始快照含全文与 ES 文档结构，不应整体塞入模型上下文**；模型消费 `*-stats.json`。
