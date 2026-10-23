# 数据坑清单（实测，ESMO 2026 全量）

按"会不会让结论错"排序。

## 1. `lba` 字段全为 None

**现象**：`base.abbreviation_label` 里能查到 `lba / interim / final / subgroup` 等标记，但结构化表返回的 `lba` 对所有行都是 None。

**后果**：不能用 LBA 判断"是不是重磅/首次公布"。只能从 `abstract_text` 的措辞推断（见 `screening-rules.md` §5）。

**处置**：榜单不引入 LBA 信号；如需按 LBA 分组，得另行从 np_clinical 原始字段补。

## 2. `evaluation` 是记录级枚举，不是试验级

**现象**：同一试验的主结果摘要 `evaluation = 积极`，安全性摘要或亚组摘要可能是 `-`；反过来也有 `积极` 但 OS 未达（postMONARCH）。

**后果**：
- 按 `evaluation` 先筛再拉，会丢掉同试验的其它摘要。
- 用 `evaluation` 直接定"失败"，会把"主终点阳性 + OS 未达"错判成"积极"。

**处置**：拉全量再去重；失败判定以摘要里的 p/HR 为准，`evaluation` 只作初筛入口。

## 3. 统计量稀疏

**现象**：3445 行 `study_results` 里，只有约 5–6/10 行带 `p_value` 或 `hazard_ratio`；`machine_endpoint_call` 大面积返回 `无法判断`。

**后果**：任何"机器算出来的显著性"都是残缺的；规则打分看起来有分数，其实是假精度。

**处置**：数字一律从 `abstract_text` 抄；`machine_endpoint_call` 只作复核提示。

## 4. 安全性终点会冒充疗效

**现象**：`endpoint_attribute` 里安全性 1475 行、有效性 1717 行；但 label 命名混乱，`Grade≥3 TEAE 44.6%`、`anemia 9.2%` 这类行在不过滤时会被 `best_efficacy_line` 选中——因为它们同样带百分比。

**处置**（已在脚本里）：

1. 先按 `endpoint_attribute ∈ {有效性, 空}` 过滤（`effective_results`）。
2. 再按 `SAFETY_HINTS` 过滤 label（toxicity/adverse/death/DLT/discontinuation/dose reduction/safety/tolerability）。
3. 早期桶 `prefer_efficacy=True` 时优先"缓解类 + 带百分比"，跳过原始计数行。

> EIK1003-001 是典型：主要终点全是安全性（Grade≥3 TEAE 44.6%、贫血 9.2%），真实疗效在次要行（ORR 14.3%、DCR 38.8%）。不过滤就会把 44.6% 当疗效报出去。

## 5. `result_unit` 可能不是百分比

**现象**：`PR 7 subjects`、`缓解 3 patients` 这类计数行，`result` 是 7 或 3，若按百分比读会变成"部分缓解率 3.0%"。

**处置**：`signal_quality()` 把 `result_unit ∈ {subjects, patients, events, count}` 判为原始计数（第三返回值 False），早期桶排序时跳过。

## 6. `clean_label` 的残留噪声

**现象**：解析器产出的 label 常是拼接串，如 `Efficacy-evaluable patients; percentage`、`rate at 16 weeks 82.2%`、`Patients who completed 6 cycles (n=13) 84.6%`。

**处置**：`ENDPOINT_PHRASES` 做规范化映射；命中 `NOISY_LABEL`（follow-up / cutoff / data cut / population / subgroup / review / assessed / analysis set / **percentage / remaining on treatment / available data / pts with / patients who / part 1 and part 2**）或长度 >60 字符时**返回 `None`，不再拿别的字段兜底**。

**v0.2 修掉的两个具体错标**（都不是噪声，是错到会误导榜的）：

1. **两字母缩写做子串匹配**：`"response".find("os") >= 0` → 任何含 "Overall **res**p**o**n**s**e" 的标签都被映射成「总生存期」。SYS6043 曾显示「总生存期 45.7%」，实际是 ORR。现在 `ABBREV_KEYS = {orr, os, pfs, efs, dfs, dcr, pcr, dor, hr, bcr, rfs}` 一律用**词边界正则**。
2. **无 label 时继承 `primary_endpoint_cn[0]`**：该列表首项在多数 ADC 摘要是「剂量限制性毒性」，于是 HS-20122 的 ORR 52.5% 被印成「剂量限制性毒性 52.5%」。现在 `clean_label` 只在中文候选里挑出**非安全性且能命中端点关键词**的那一项，否则留 `None`。

## 7. 同一试验多摘要（去重会丢主结果）

**现象**：RINGSIDE 有疗效篇 + 安全性篇；NIAGARA 有主结果 + DDHS 亚组；MIRASOL 有主结果 + 1L-PROC 亚组；KEYNOTE-905 有主结果 + 三臂 ad hoc 比较。

**后果**：按 `trial_abbreviation` 去重会只留一条，可能恰好留到亚组/安全性篇——于是榜单上出现"ORR 56% vs 9%"配一个"本次报告 G≥3 AE 57%"的奇怪组合。

**处置**：

1. 定榜时逐条确认本篇是**主结果 / 更新 / 亚组**，写进 `data_type`。
2. 如果留下的是亚组篇，要么换主结果篇，要么在理由里明说"本次为亚组/安全性报告，疗效数据来自既往发表"。

## 8. `clinical_condition.clinical_stage` 不是试验期别

**现象**：`indications.clinical_stage_new.text` 给出的是**疾病分期**（I–IV 期肿瘤），不是试验 phase。

**后果**：用它分桶会把 III 期结肠癌的 Phase I 试验错分到 pivotal。

**处置**：试验期别只认 `evidence_source`。

## 9. 试验简称缺失 / 写法不一致

**现象**：`trial_abbreviation` 有空值（如 ABBV-706、IBI363 部分摘要）；同一试验不同摘要可能写 `ZG005-003` / `ZG 005 - 001`。

**处置**：去重键空值时退化为 esid；合并阶段允许漏合并（宁可多留一条，也不要错合并两条不同试验）。同一药的多个试验编号在定榜时人工归并。

## 10. `analysis` 类措辞会让 data_type 误判

**现象**：`interim analysis` / `primary analysis` 被规则判为「首次公布」，但实际可能是同一试验的**最终分析**（CA017-078）；反过来，Background 里的 `updated` 可能在描述既往发表、本文其实是亚组。

**后果**：把最终分析当首报，会高估信息增量。

**处置**：规则只做提示。**定榜条目必须人工回原文确认 `data_type`**；措辞与结论段冲突时以「本次报告了什么」为准，不以关键词为准。

## 11. 真实世界研究量大

**现象**：ESMO 2026 中真实世界研究 210 篇 + 前瞻性研究 235 篇 + 回顾性 49 篇 = 494 篇，占 50%。

**后果**：不过滤的话，榜单会被大量真实世界疗效对比占满，且这些研究的"ORR"与注册试验不可比。

**处置**：全部排除，单独计数，明示在交付物里。

## 12. `Results` 截断（v0.1 的主要缺陷，已修）

**现象**：v0.1 把摘要 Results 段截到 760 字符。ESMO 2026 实测 Results 段中位数 **956 字符**、最长 2094 —— **338/646（52%）的摘要把关键数字印在 760 之后**。

**后果**：低分条目里有 260 条 Results > 760，其中 **117 条（45%）在截断点之后还有带百分比的疗效数字**，真正“数字只在未展示的表里”的只有 4 条。两名内部专家推荐因此被误判：HS-20122 的 `52.5%` 在偏移 919，CM518D1 的 `33.3%` 在偏移 851。

**处置**：**Results 全文给模型**（整篇摘要才 ~2 KB，截断零收益），Background 320 / Conclusion 280 的压缩保留，`clinical_result_summary` 另作独立字段。批次 25 → 15 条以对标单文件读取上限。

## 13. 会议摘要库里有、结构化表里没有

**现象**：BG-C477（2567P）在摘要库里全文都有，在结构化结果表里 0 命中——会前一天才放出的 FIH 数据还没走完入库流水线。ESMO 2026 的 4103 篇可用摘要里只有 465 篇被结构化表覆盖，**3638 篇未覆盖**，其中 52 篇是口头级、带药名 + Results 数字 + 可解析期别。

**后果**：只读结构化表，早期机会桶会系统性漏掉“最新鲜”的资产——而那正是这一桶的全部价值。

**处置**：见 `references/screening-rules.md` §1.2。会议库独有记录转补充行，**只进 early 桶**（期别是正则抽的，稳健度不够撑 pivotal/failed）。

## 14. 报告形式是最容易被忽略的强先验

**现象**：摘要号后缀直接编码报告等级（`5RO` 快速口头、`1000O` 口头、`1015P` 壁报），不需要任何额外字段。

**后果**：ESMO 2026 候选池口头级只占 25%，但内部专家挑的 7 条里 **4 条是口头（57%）**。不用这个先验，等于白白丢掉 2.3 倍富集。

**处置**：池内排序改 `(presentation_rank, -n)`，榜单标出报告形式。**但仍不做硬门槛**——同一批专家也挑了 3 条壁报，砍掉壁报会丢掉一半命中。

## 15. 绝对 ORR 阈值会打压耐药人群里的好数据

**现象**：9MW2821 在 TOP1i-ADC 耐药 TNBC（62 例，48% 用过 TROP2 ADC）ORR 30.0%、mPFS 3.7 mo、已开 III 期 NCT07556848。按 40% 硬线会被判 weak。

**处置**：ORR 门槛按人群难度分档（一线 ≥40% / 后线、耐药 ≥25%），且**降档必须写明人群**。脚本已提供 `refractory` 字段。

## 16. 复核分片没有正文 —— 子任务会静默降级

**现象**：ESMO 2026 v0.2 首轮把 `pool.json` 的条目直接切成 36 片，`condensed` 字段为空（池子里只有 `abstract_text`，`condensed` 是复核批次阶段才拼装的）。6 个子任务全部读到 `condensed = null`：4 个直接拒绝判定并要求重给分片，2 个改用 `summary` 凑合。**keep 率从 24%（46+45+20+39+40+42）掉到 2%（0+0+14+0+6+2）**，且 `evidence` 全部无法逐字校验。

**原因**：池子层（`pool.json`）与复核层（`review.jsonl`）是两种 schema。切片必须基于复核层的 batch item（含 `background` / `results` / `summary`），拼成 `condensed = Background + 完整 Results + DB summary`。

**处置**：切片脚本落盘前断言 `all(it["condensed"] for it in items)`；再加体积断言（单文件 ≤40 KB）。这条断言比任何提示词都有效——两次跑到同一批文件，模型一次判 keep 3%、一次判 24%，差别全在输入。

## 17. 机器排序 ≠ 推荐排序

**现象**：池子按 `(presentation_rank, -n)` 排，本意是"先读重要档"。但 7 条专家选择在机器序里的位置是 2 / 19 / 27 / 72 / 101。壁报档里 `1029P`（CTS3497，28 例 MTAP 缺失 ORR 43%）、`2567P`（BG-C477，43 例 CEA ADC）被 n 更大的平庸壁报压到 72、101 名。

**处置**：机器序只决定"读的顺序"，定榜顺序交给读完 keep 的人。`scripts/make_watchlist.py` 只按给定顺序渲染，不做排序，就是为了不让这个隐含假设重新长回来。
