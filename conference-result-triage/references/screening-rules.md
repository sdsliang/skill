# 筛选规则（分桶 / 排除 / 机器信号）

本文件是 `scripts/triage.py` 的规范来源。改脚本前先改这里。

## 1. 排除（excluded，不进任何桶）

按 `evidence_source` 判断：

| evidence_source | 处理 | ESMO 2026 条数 |
|---|---|---|
| `Phase I` … `Phase IV` | 进入候选 | 470 |
| `前瞻性研究` | 排除 | 235 |
| `真实世界研究` | 排除 | 210 |
| `回顾性研究` | 排除 | 49 |
| `Not Applicable` | 排除 | 4 |
| `汇总分析` | 排除 | 1 |
| 空 / 未知 | 排除并计入「未知证据类型」 | 19 |

理由：真实世界与回顾性研究的入组、终点定义、随访强度与注册试验不可比。放进"重磅/早期"等于用两把尺子量同一件事，且榜单读者会当成注册数据引用。

如需单独看这类证据，另开一档「真实世界信号」，**不要混进三桶**。

## 2. 去重

1. 先按 `_id`（esid）合并：同一 esid 多行，逐字段取第一个非空值。
2. 再按 `trial_abbreviation`（大写）合并进桶；`trial_abbreviation` 为空时退回 `esid` 作键。
3. 合并时保留排序值更大的记录：`(has_study_results, n)` 字典序。

**注意**：同试验多摘要（主结果 / 亚组 / 安全性）去重后只会留一条。定榜阶段必须回查同试验其它摘要，主结果篇可能不在留下的那条里。

## 3. 分桶

顺序判定，命中即停：

```
if evaluation ∈ {不佳, 终止}:        failed
elif evidence_source ∈ {Phase II, II/III, III, IV}:  pivotal
elif evidence_source ∈ {Phase I, I/II}:              early
else:                                                excluded
```

- **失败优先**：一个 III 期阴性研究进 failed，不进 pivotal。
- `Phase II` 进 pivotal 是有意的：大量随机 II 期（如 COMPANION-002、AGITG MASTERPLAN）证据强度高于单臂 III 期。
- 复核阶段模型可覆盖分桶（按证据强度重判，见 `review-protocol.md`），但**排除档不可覆盖**——非试验证据不能因为"数字好看"被提进榜。

## 4. 机器信号（非权威，只做复核时的提示）

脚本为每条候选附两样东西，**都不进最终榜的数字**：

### 4.1 `machine_signal` = `best_efficacy_line(row)`

- 只从 `endpoint_attribute ∈ {有效性, 空}` 的行里选（`effective_results`）。
- 再过滤 `SAFETY_HINTS` 命中的标签：toxicity / adverse / death / DLT / dose-limiting / discontinuation / dose reduction / safety / tolerability。
- `clean_label` 把解析器产出的原始 label 映射到规范中文名（pCR→病理完全缓解率、ORR→客观缓解率、EFS→无事件生存期……），标签 >60 字符或命中噪声词（follow-up / cutoff / subgroup / analysis set / review / assessed / population）时退回 `primary_endpoint_cn[0]`。
- 早期桶用 `prefer_efficacy=True`：优先"带百分比的缓解类端点"，跳过原始计数行（`result_unit ∈ {subjects, patients, events, count}`）。

### 4.2 `machine_endpoint_call` = `endpoint_call(row)`

只看主要终点行与相对臂行：

- 有 p 值 → `met`（min p < 0.05）/ `missed`
- 只有 HR CI → `不完整`（给出 CI 上限）
- 都没有 → `无法判断`

**它经常是 `无法判断`，这是正常的**（统计量稀疏）。不要为了让它好看去降低阈值。

## 5. `data_type`（首次 / 更新 / 亚组 / 未判定）

规则优先级（先命中先返回）：

1. `亚组/二次分析`：post-hoc、ad hoc、subgroup analysis、secondary analysis、exploratory analysis、pooled analysis、biomarker analysis、patient-reported outcome
2. `更新/长期随访`：updated、update of、long-term、final analysis、extended/additional follow-up、end-of-trial、now report、previously reported/presented/shown、with longer follow-up、"N-yr follow-up"、sustained benefit
3. `首次公布`：first-in-human、first report、primary results/analysis、prespecified analysis、interim analysis、we report the primary/first、first disclosure、here we report/present/show
4. 都不命中 → `未判定`

只在摘要前 1200 字符内匹配（结论段常重复 Background 措辞）。

ESMO 2026 实测分布：首次 90 / 更新 77 / 亚组 53 / 未判定 247（53%）。**未判定比例高是设计上的诚实**，不是规则失败——很多摘要确实没写。定榜条目人工回原文确认后再落 `data_type`。

## 6. 已知规则的边界

| 情况 | 现状 | 处置 |
|---|---|---|
| `lba` 标记 | 全库为 None | 不用它判断重磅程度 |
| 单臂 I 期 ORR 40–60% | 极常见（早期桶 180 条里 137 条 keep） | 靠复核阶段收，不靠规则；SCLC/胃癌这类高响应病种尤其要压 |
| `evaluation = 积极` 但 OS 未达 | 存在（postMONARCH） | 复核时以数字为准，不看枚举 |
| 同一试验主结果在别的摘要 | 去重会丢 | 定榜时回查 |
