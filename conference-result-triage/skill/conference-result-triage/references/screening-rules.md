# 筛选规则（分桶 / 排除 / 机器信号）

本文件是 `scripts/triage.py` 的规范来源。改脚本前先改这里。

## 1. 排除（excluded，不进任何桶）

按 `evidence_source` 判断：

| evidence_source | 处理 | ESMO 2026 条数 |
|---|---|---|
| `Phase I` … `Phase IV` | 进入候选 | 470 |
| `前瞻性研究` | **进入候选**（分期未声明，不算非试验证据） | 252 |
| `真实世界研究` | 排除 | 210 |
| `回顾性研究` | 排除 | 49 |
| `Not Applicable` | 排除 | 4 |
| `汇总分析` | 排除 | 1 |
| 空 / 未知且非 LBA | 不进桶，计入「无法归类」 | 19 |

> **v0.6 修正（`前瞻性研究` 从排除改为放行）**：`evidence_source` 是平台唯一的分期信号，但 73 条 ESMO 2026 LBA 里有 **16 条把它填成了研究设计**（`前瞻性研究`）而不是期别。按旧规则这 16 条整类消失——包含 VOLGA、KRASCENDO-1、CLARITY-Gastric01 三场 Presidential。**分期缺失不是排除理由**：真前瞻性研究恰恰是我们想要的证据类型。
>
> 这 16 条进桶靠 `lba` 标记（见 §2），期别字段仍按原值（多为空），卡片上照实写「分期未在摘要中声明」。
>
> **教训**：穷举「哪些值算排除」比穷举「哪些值算纳入」安全。一个值没进白名单只是漏，进了黑名单就是系统性删除。

理由：真实世界与回顾性研究的入组、终点定义、随访强度与注册试验不可比。放进"重磅/早期"等于用两把尺子量同一件事，且榜单读者会当成注册数据引用。

如需单独看这类证据，另开一档「真实世界信号」，**不要混进三桶**。

### 1.1 试验进行中（TiP）也排除

三个来源都要拦：`abstract_id` 后缀 `eTiP`/`TiP`、只有 `Trial design`/`Expected results` 段、正文出现 "trial in progress / results will be reported"。TiP 没有结果，进榜就是把计划当成数据。

### 1.1.1 分期缺失 ≠ 非试验（v0.6）

`evidence_source` 有时填的是**研究设计**而非期别。这种行进入 `bucket_of` 后：

1. 期别属于 `Phase II/II-III/III/IV` → pivotal；
2. 期别属于 `Phase I/I-II` → early；
3. 期别缺失但 `lba` 为真 → **pivotal**（LBA 是会议的议程中心，不是 FIH 海报）；
4. 其余（期别空缺，或填的是「前瞻性研究」这类设计词）→ **按研究设计归档**（v0.10，见下）。

第 3 条是**分类判断**，不是评分：期别字段不改、不猜，卡片照实标「未声明」。

#### 1.1.2 按设计归档（v0.10，跨领域必需）

肿瘤会议会为每条摘要填期别；**心血管、代谢、肝病、神经、眼科基本不填**。实测三场同一天的会议：

| 会议 | 结果记录 | 期别缺失 | 旧规则丢弃 | 旧候选数 → 新候选数 |
|---|---|---|---|---|
| ADA 2026 | 191 | 40（21%） | 40 | 98 → 138 |
| EASL 2026 | 214 | 55（26%） | 55 | 80 → 135 |
| ESC 2026 | 242 | **123（51%）** | 123 | 54 → 164 |

ESC 那 123 条里就有 ACACIA-HCM（aficamten）、ENRICH-AF、SAL003 —— 整个会议的主场读数。按「无法归类」整批丢掉，等于把榜单做成了会议边角料，而 `coverage` 照样报满（覆盖按已取行算）。

规则（`triage.design_bucket()`）：

- `evaluation ∈ {不佳, 终止}` → failed（先于设计判据）；
- `randomized ∈ {随机化, 是}` 或 `trial_control ∈ {平行分组, 交叉设计, 析因设计}` → **pivotal**；
- 其余真试验 → **early**；
- 条目上写 `phase_inferred`，取值只有三种：`随机化对照（按设计判定）` / `平行/交叉对照（按设计判定）` / `单臂或未标注设计（按设计判定）`。

纪律：

- **这是补字段，不是加分**：`phase` 仍照原样（通常是 `null`），`phase_inferred` 单独一列；卡片正文写「期别未标注（按设计判定：随机化对照）」，**不许写成 `Phase III`**；
- `phase_inferred` 非空时，判读 `evidence_strength` 不得因为"看着像 III 期"就按 III 期给分上限，要按设计给（单臂 → 低）；
- 只在期别缺失时生效。期别填了就以期别为准，不要再叠加设计判据。

### 1.2 会议摘要库独有记录只补 early

结构化结果表只收**已入库结构化**的记录。会前一天才放出的 FIH 数据可能还没走完流水线——ESMO 2026 实证：BG-C477（2567P，43 例 NSCLC，ORR 34.9%）在会议摘要库里，在结构化表里查不到。

因此增加**并列第二入口** `scripts/meeting_pull.py` + `meeting_join.py`：

- 会议摘要库（`medicalMeeting`）**只在有外网时**才可用：按 title join 补 `abstract_id` / `presentation` / `target` / `drug` / `moa` / 全文。平台内没有这个工具，`abstract_id` 恒为 `null`，报告形式只剩 `lba` 一个信号（见 3.1）；
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

**平台内没有摘要号**（v0.3 复核结论）：结果表 111 列里没有 `abstract_id`，35 个工具里没有会议摘要库，`abstract_text` 以 `#### Background` 开头不带编号。平台内唯一可用的报告形式信号是 `clinical_result.lba`：

| presentation | 条件 | rank |
|---|---|---|
| `Late-breaking Oral` | `lba` 为真 / `abstract_id` 以 `LBA` 开头 | 0 |
| `Oral` / `eOral` | 后缀 `O`（仅外网补号后） | 1 |
| `Rapid Oral` / `eRapid Oral` | 后缀 `RO` | 2 |
| `Poster` | 后缀 `P` | 4 |
| `ePoster` | 后缀 `eP` | 5 |
| `Unknown` | 无信号（平台内的绝大多数） | 9 |

ESMO 2026 实测：592 候选里 51 条拿到 `lba`（early 6 / pivotal 45 / failed 6），其余 541 条 `Unknown`。**这是诚实的覆盖现状**，不要为了"看起来有层级"造信号。

### 3.1b `featured` ≠ 头条（重要更正）

`clinical_result.featured`（`是`/`否`）是**人工生产 / AI 生产**标记，**不是**编辑精选：

- `featured='是'` 在 ESMO 2026 **100/100 等于** `source='np_result_conf'`（人工核对过的结果行）；
- 其余 1000 条 `source='np_clinical_conference'`（流水线抽取）全是 `否`。

所以它**只能**用于卡片上的生产方式标注（"人工核对" / "流水线抽取"），**禁止**参与排序或当作报告等级。`triage.py` 里它叫 `manual`，`presentation_of()` 完全不读它 —— 有 self-test 断言守着（"manual production does not create a presentation tier"）。

用法边界（对 `lba` 这一层依然成立）：

1. **只用于加权与提示，不做硬门槛。** 专家也挑了 3 条 wall poster（1015P / 1029P / 2567P）。
2. **池内排序**为 `(presentation_rank, -n)`：late-breaking 先被读到；**全量条目仍然都会进复核**，顺序只影响注意力优先级，不减少覆盖。
3. 榜单每一条都要标出报告形式（如「late-breaking」）与生产方式。

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
