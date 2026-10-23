---
name: conference-result-triage
description: Use when someone asks what is worth reading from a conference result library — "ESMO 2026 有什么值得看的"、"帮我挑这届会议的重磅/失败研究"、"会议结果推荐榜"、"早期机会有哪些"、会前选题、竞品会前扫描。Pulls one conference snapshot from np_clinical via the MCP clinical-result tool, mechanically dedupes and excludes non-trial evidence, splits into three buckets (early opportunity / pivotal Phase II-III / failed), then reviews every candidate abstract one by one and returns a ranked shortlist with verbatim-evidence reasons. Do not use it for interpreting one already-selected result, for drug-vs-drug comparison, for coverage checks against np_result, or for writing a meeting report from an existing shortlist.
---

# Conference Result Triage

## Purpose

一篇文章级的会议摘要库（如 np_clinical 的 `ESMO 2026`，945 篇）里，绝大部分是不需要看的。本 skill 的产出是**三桶候选榜 + 明确的排除档**：

1. **早期机会** — Phase I / I-II，新机制、单臂，但数字超出该适应症的历史水位。
2. **重磅 II/III 期** — 随机对照、主要终点达成且有临床意义。
3. **失败的研究** — III 期或大型随机研究，主要终点未达 / 提前终止 / OS 反向。

核心设计：**机器只做机械筛，模型只做阅读判断，谁都不自算数字。**

- 机械筛（`scripts/triage.py`，零依赖）负责：去重、排除非试验证据、分桶、摘机器信号（**非权威**）。
- 模型负责：逐条读摘要，判 `keep | weak | drop` + 一句话理由 + **逐字摘录**的关键证据。
- 榜上的每个数字都必须能回指摘要原文；不能回指的一律标「待核实」。

## When NOT to use

| 需求 | 走哪个 skill |
|---|---|
| 已选定 1–2 篇结果，要解读/写报告 | conference-clinical-interpretation |
| 多个结果做药物间疗效/安全性对比 | multi-clinical-result-comparison |
| 判断某条新结果是否已被 np_result 收录 | np-result-coverage-check |
| 已有榜单，要写成正式会议报告 | 本 skill 的 `templates/` 只到榜单级，成稿另接报告类 skill |

## Pipeline

### Step 0 — 明确会议与口径

必须问清（或从用户话里确认）三件事，缺一件就不要开跑：

1. **会议标识**（`meeting_tags` 的精确值，如 `ESMO 2026`、`ASCO 2026`）——它要求精确匹配，写错就是空集，不是模糊搜索。
2. **要不要限定瘤种/公司/期别**——不限定就是全量（ESMO 2026 量级 ~500 候选，可跑）。
3. **榜单条数**——默认每桶 10 条。

### Step 1 — 一次拉全量（不要按桶重复拉）

用 MCP 工具 `pharmcube-query-clinical-result-with-params` 拉**一次**全量，字段清单见 `references/data-contract.md`。
禁止"先按 evaluation 筛一遍再拉"——`evaluation` 是记录级枚举，先筛会漏掉同一试验的其它摘要。

### Step 2 — 机械筛（确定性，无判断）

```bash
python3 scripts/triage.py --input rows.json --out-dir out --top 0
```

产出 `out/pool.json`（三桶 + excluded 计数）、`out/pool.md`（人眼速览）、`out/review.jsonl`（复核批次）。

脚本只做四件事：esid 去重 → 排除非试验证据源 → 按规则分桶 → 附非权威机器信号。
它**不打临床分、不排序推荐**。池内顺序按 n 降序，仅供阅读。

分桶与排除规则见 `references/screening-rules.md`。三条不可改的硬规则：

- **n 不作入榜门槛**，只做展示与并列次级排序（样本 15 的 I 期和样本 900 的 III 期不是同一把尺子，但都不能因为 n 小就直接出局）。
- **真实世界 / 回顾性 / 汇总分析一律不进三桶**，单独计入 `excluded`。
- **试验分期取 `evidence_source`**，不是 `clinical_condition.clinical_stage`（那是疾病分期，不是试验期别）。

### Step 3 — 逐条复核（模型，本 skill 的核心）

按 `references/review-protocol.md` 执行。要点：

- 每批 **25 条**，每条给"压缩摘要"（Background 320 字 / Results 760 字 / Conclusion 280 字）+ 机器信号。
- 输出严格三键：`i`（原样抄）、`verdict ∈ {keep, weak, drop}`、`bucket ∈ {early, pivotal, failed}`（按证据强度重判，可覆盖机器分桶）、`reason ≤40 字`、`evidence`（**逐字**摘录 ≤120 字符）、`key_numbers`。
- 批次之间用顺序 `i` 索引合并，**合并前必须校验 i 覆盖 = 池子条数**；用 esid 对不上就说明批次错位，整批重跑，不要凑数。

`verdict` 的定义（不按"看起来有意思"，按**能不能支撑一句结论**）：

| verdict | 条件 |
|---|---|
| keep | 数字明确（ORR ≥ 40% / HR ≤ 0.75 / OS 绝对获益 ≥ 3 月 / 明确阴性结论），且能引出具体数字 |
| weak | 有疗效数字但样本 < 20、单臂极小样本、或关键数字落在未给出的表格里 |
| drop | 只有安全性 / PK / 生物标志物 / HRQoL，或只说"将继续评估"而无结果 |

### Step 4 — 合并与定榜

1. 合并全部批次 → `judgements.csv`（全量判定，可追溯）。
2. 定榜时**再收一次**：判 `bucket` 与 `data_type`；同一试验的多篇摘要只留信息量最大的一篇（其余在"同试验其它摘要"里点名）。
3. 每桶 10 条，附「候补（差一位）」。**不要为了凑 10 条把 weak 提上来**——不足就写不足。

### Step 5 — 输出

按 `templates/watchlist-report.md` 出：

- `watchlist.md` — 三桶表 + 排除档 + 待人工核实清单
- `watchlist.csv` — 30 条机器可读（含 `data_type`、`key_numbers`、`why`）
- `judgements.csv` — 全量逐条判定，供复现与抽查

## 两个必须写在交付物里的诚实声明

1. **`data_type`（首次 / 更新 / 亚组·二次分析 / 未判定）**。会议摘要里有大量"长期随访""post-hoc 亚组""Q-TWiST 二次分析"，它们不是新数据。不标这一列，读者会把 7 年 OS 更新当成新药突破。规则自动打，打不出来就写「未判定」，**不要猜**。
2. **待核实清单**。`lba` 字段在本库里全为 None、`study_results` 里只有约 5–6/10 行带 p 或 HR、同一试验常拆成多篇——这些都要写进交付物，而不是让读者以为榜单是全覆盖的。

## Anti-patterns（踩过的坑）

- ❌ 用规则给"重磅程度"打分：实测会把安全性终点排到疗效前面（`Grade≥3 TEAE 44.6%` 被当成疗效信号），`PR = 3 subjects` 被当成 3% 缓解率。所以本 skill **只判不评**。
- ❌ 让模型自己算 ORR 变化率/HR 差值：摘要里数字常以表格形式给出，模型重算必错。只抄不算。
- ❌ 用 `clinical_stage` 当试验期别（那是疾病分期 I–IV 期肿瘤）。
- ❌ 按 `evaluation` 先筛再拉：同试验的亚组摘要 evaluation 可能不同，先筛会丢掉主结果。
- ❌ 把 n 小当成排除理由：早期桶的价值恰在"样本小但信号强"，n 只用来排序和标注。
- ❌ 批次用 esid 直接索引：批次内顺序与池子顺序不一定一致，必须用显式 `i`。

## 支持文件

| 文件 | 何时读 |
|---|---|
| `references/data-contract.md` | 每次拉数前（字段、MCP 调用、返回形状） |
| `references/screening-rules.md` | 改分桶/排除规则时；解释"为什么这条不在榜上" |
| `references/review-protocol.md` | 每次复核前（批次设计、verdict、证据校验） |
| `references/pitfalls.md` | 数据口径存疑时（字段缺失、统计稀疏、多摘要） |
| `templates/watchlist-report.md` | 写交付物时 |
| `dist/ESMO2026-watchlist.md` | 已完成的真实样例（ESMO 2026，30 条） |

## 版本

v0.1 — 首版，基于 ESMO 2026 全量（945 篇 → 467 候选 → 206 keep → 30 定榜）实跑校验。
