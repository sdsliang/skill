# 会议结果推荐榜模板

> 用法：替换 `{{...}}`。三桶各 10 条，不足就写不足。每桶后面必须跟"候补"和"看点"。
> 硬规则：不写没有原文出处的数字；`data_type` 列不能空；排除档不能省。

---

# {{conference}} 会议临床结果推荐榜（三桶）

> 生成：conference-result-triage / 数据源 np_clinical `meeting_tags = "{{conference}}"`
> 数据截止：{{snapshot_time}}
> 说明：本榜是**机器机械筛 + 逐条摘要复核**的产物，不含模型自算数字。标「待核实」表示摘要内不足以确认。

---

## 0. 口径与筛选漏斗

| 步骤 | 数量 | 说明 |
|---|---|---|
| 会议文献（np_clinical） | {{n_docs}} | `base.journal.text = {{conference}}` |
| MCP structured 原始行 | {{n_raw}} | 同一 esid 多行（按 arms/endpoint 拆行） |
| 去重后 esid | {{n_esid}} | |
| 排除非试验证据源 | -{{n_excluded}} | 前瞻性 {{c_prosp}}、真实世界 {{c_rw}}、回顾性 {{c_retro}}、其它 {{c_other}} |
| 进入三桶候选 | {{n_pool}} | 早期 {{c_early}} / 重磅 {{c_pivotal}} / 失败 {{c_failed}} |
| 逐条复核 keep | {{n_keep}} | 其余 {{n_weak}} weak / {{n_drop}} drop |
| 定榜 | {{n_listed}} | 每桶 {{per_bucket}} 条 |

**硬规则**：

1. 真实世界 / 回顾性 / 汇总分析不进任何桶，单独计为 excluded。
2. n 不作入榜门槛，只做展示与并列次级排序。
3. 试验分期取自 `evidence_source`，不是 `clinical_stage_new`。
4. 失败首先由 `evaluation ∈ {不佳, 终止}` 驱动，p/HR 只作佐证。
5. 模型只写归因，不自算 ORR/HR/PFS。

**数据类型标注**：`首次公布` / `更新-长期随访` / `亚组-二次分析` / `未判定`。
本批分布：首次 {{dt_first}} / 更新 {{dt_update}} / 亚组 {{dt_sub}} / 未判定 {{dt_unknown}}。

---

## 一、早期机会（Phase I / I-II，新机制 + 数字超预期）

| # | 试验 / 药物 | 靶点机制 | 适应症 | 期 | n | 类型 | 关键数字 |
|---|---|---|---|---|---|---|---|
| 1 | **{{trial}}** | {{target}} | {{indication}} | {{phase}} | {{n}} | {{data_type}} | {{key_numbers}} |
| … | | | | | | | |

**候补（差一位）**：{{next_best}}

**看点**：{{insight}} —— 写"这几条共同指向什么"，不要逐条复述。

---

## 二、重磅 II/III 期（随机对照，主要终点达成且有临床意义）

| # | 试验 / 药物 | 适应症 | 期 | n | 类型 | 关键数字 |
|---|---|---|---|---|---|---|
| 1 | **{{trial}}** | {{indication}} | {{phase}} | {{n}} | {{data_type}} | {{key_numbers}} |
| … | | | | | | |

**候补**：{{next_best}}

**看点**：必须区分「首次 III 期阳性」与「既有试验的最终/长期分析」——后者的信息增量小得多。

---

## 三、失败的研究（III 期 / 大型随机，主要终点未达）

| # | 试验 / 药物 | 适应症 | 期 | n | 结论 |
|---|---|---|---|---|---|
| 1 | **{{trial}}** | {{indication}} | {{phase}} | {{n}} | {{negative_finding}} |
| … | | | | | |

**候补**：{{next_best}}

**看点**：写"分歧/反向信号"，如一治疗范式在不同试验里结论相反、OS HR > 1 的安全性假说。

---

## 四、明确排除（不进榜，单独留档）

| 类别 | 条数 | 例子 |
|---|---|---|
| 前瞻性研究（非注册试验） | {{c_prosp}} | {{eg}} |
| 真实世界研究 | {{c_rw}} | {{eg}} |
| 回顾性研究 | {{c_retro}} | {{eg}} |
| Not Applicable / 汇总分析 / 未知 | {{c_other}} | {{eg}} |

排除原因：入组与终点可比性不足。如需另开"真实世界信号"档，规则须单独定义。

---

## 五、待人工核实清单（不隐藏不确定性）

1. **数据类型**：{{n_pool}} 条中 {{dt_unknown}} 条摘要未写明首次/更新/亚组；本榜 {{n_listed}} 条已回原文确认，其余需抽查。
2. **`lba` 字段全为 None**，无法用 LBA 标记判断重磅程度。
3. **统计量稀疏**：`study_results` 仅约 5–6/10 行带 p 或 HR，多数结论依赖 `abstract_text`；所有 p/HR 均从原文抄录，未二次计算。
4. **同试验多摘要**：本届同一试验常拆成主结果 + 亚组 + 安全性多篇，去重后保留信息量最大的一篇，主结果篇可能落在别条。
5. {{other_caveats}} —— 如中国资产占比、随访时长差异等。

---

## 六、复现

```bash
# 1. 拉取（MCP structured，meeting_tags 精确匹配）
# 2. 机械筛
python3 scripts/triage.py --input rows.json --out-dir out --top 0
# 3. 逐条复核（每批 25 条）
# 4. 定榜
```

产物：`judgements.csv`（全量判定）/ `watchlist.csv`（定榜 30 条）/ `watchlist.md`（本文件）。
