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

### 1.1 试验进行中（TiP）也排除

三个来源都要拦：`abstract_id` 后缀 `eTiP`/`TiP`、只有 `Trial design`/`Expected results` 段、正文出现 "trial in progress / results will be reported"。TiP 没有结果，进榜就是把计划当成数据。

### 1.2 会议摘要库独有记录只补 early

结构化结果表只收**已入库结构化**的记录。会前一天才放出的 FIH 数据可能还没走完流水线——ESMO 2026 实证：BG-C477（2567P，43 例 NSCLC，ORR 34.9%）在会议摘要库里，在结构化表里查不到。

因此增加**并列第二入口** `scripts/meeting_pull.py` + `meeting_join.py`：

- 摘要库全量 → 按 title 与结构化表 join（ESMO 2026：646/646 命中，零损失），补 `abstract_id` / `presentation` / `target` / `drug` / `moa` / 全文；
- 只在摘要库里的记录 → 需「有药名 + Results 段有数字 + 能解析出期别 + 非 RWE/回顾/综述」才转成补充行；
- **补充行只进 `early`**。期别是从散文里正则抽的，稳健度远低于 curated `evidence_source`，不够格撑 pivotal / failed 两桶。

ESMO 2026 实测：摘要库 5810 条 → 可用摘要 4103 → 补充行 305（口头 49）→ 进 early 68，其余 235 记入「会议库独有(非早期阶段)」。

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

### 3.1 报告形式（presentation tier）

`abstract_id` 后缀就是报告等级，不需要另找字段：

| 后缀 | 等级 | 排序权重 |
|---|---|---|
| `1234O` | Oral（口头） | 1 |
| `1234RO` | Rapid Oral（快速口头） | 2 |
| `LBA1234` | Late-breaking | 3 |
| `1234P` | Poster | 4 |
| `1234eP` | ePoster（仅在线） | 5 |
| `1234eTiP` | 试验进行中 | 排除 |

**这是最强的单一会议先验，必须用上。** ESMO 2026 实证：

- 候选池 532 条里，口头级（Oral + Rapid Oral）116 条，占 25%；
- 内部专家挑的 7 条里 **4 条是口头级（57%）**——富集 2.3 倍。

用法有两条边界：

1. **只用于加权与提示，不做硬门槛。** 专家也挑了 3 条 wall poster（1015P / 1029P / 2567P），砍掉 poster 会丢掉一半命中。
2. **池内排序**改为 `(presentation_rank, -n)`：口头先被读到；**全量条目仍然都会进复核**，顺序只影响注意力优先级，不减少覆盖。
3. 榜单每一条都要标出「口头 / 快速口头 / 壁报」，让读者知道数据的出场规格。

### 3.2 人群难度：verdict 不能只看绝对值

同样的 ORR，在后线耐药人群里含义完全不同。绝对阈值会把最有价值的资产剔掉：

| 情形 | ORR 门槛 |
|---|---|
| 一线 / 未治疗、非耐药人群 | ≥40% |
| 后线（≥2 线）、或明确耐药人群（如 TOP1i-ADC 耐药、TKI 全经治） | **≥25%** |
| 明确耐药且已进 III 期 | ≥25%，且应优先于同 ORR 的敏感人群数据 |

**前提**：人群必须在 `evidence` 或 `reason` 里写明（几线、既往用过什么）。只降门槛不写人群 = 放宽标准，不允许。

反例（就是这条规则要救的）：9MW2821 在 TOP1i-ADC 耐药 TNBC（62 例，48% 用过 TROP2 ADC，33% 用过 HER2 ADC）ORR 30.0%、mPFS 3.7 mo，已开 III 期 NCT07556848。按 40% 硬线会被判 weak；按耐药人群 25% 线是明确的 keep。

`triage.py` 已提供 `refractory` 字段（从正文抽「经治/耐药/prior lines」等表述），复核时先看它。

## 4. 机器信号（非权威，只做复核时的提示）

脚本为每条候选附两样东西，**都不进最终榜的数字**：

### 4.1 `machine_signal` = `best_efficacy_line(row)`

- 只从 `endpoint_attribute ∈ {有效性, 空}` 的行里选（`effective_results`）。
- 再过滤 `SAFETY_HINTS` 命中的标签：toxicity / adverse / death / DLT / dose-limiting / discontinuation / dose reduction / safety / tolerability。
- `clean_label` 把解析器产出的原始 label 映射到规范中文名（pCR→病理完全缓解率、ORR→客观缓解率、EFS→无事件生存期……），标签 >60 字符或命中噪声词（follow-up / cutoff / subgroup / analysis set / review / assessed / population / percentage / remaining on treatment）时**返回 None，不猜**。
- **两字母缩写必须用词边界匹配**（`\bos\b` / `\borr\b`），不能用子串：`re"response"` 里的 `os` 曾把 ORR 45.7% 标成「总生存期」。
- **无 label 的行不能继承 `primary_endpoint_cn[0]`**：该列表首项在多数 ADC 摘要是「剂量限制性毒性」，曾把 HS-20122 的 ORR 52.5% 印成「剂量限制性毒性 52.5%」。现在只在 `cn` 里挑出非安全性且能命中端点关键词的那一项，否则留空。
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
| 单臂 I 期 ORR 40–60% | 极常见（早期桶 248 条里大量 keep） | 靠复核阶段收，不靠规则；SCLC/胃癌这类高响应病种尤其要压 |
| `evaluation = 积极` 但 OS 未达 | 存在（postMONARCH） | 复核时以数字为准，不看枚举 |
| 同一试验主结果在别的摘要 | 去重会丢 | 定榜时回查 |
| 摘要库独有记录的期别 | 正则从散文抽，噪声更高 | 只进 early；补 `n`（从正文首个「N patients」抽，257/305 命中） |
| 无章节标题的摘要 | `guess_results()` 按证据词密度取段 | ESMO 2026 未出现（646 条全有 `####` 标题）；会议库正文是裸标题格式（B 型），已验证 |
