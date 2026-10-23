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

### Step 1 — 两个入口都要拉（少拉一个就是漏数据）

| 入口 | 拿到什么 | 缺了会怎样 |
|---|---|---|
| 结构化结果表 `pharmcube-query-clinical-result-with-params`（`meeting_tags`） | curated 的 `evidence_source` / `evaluation` / `study_results` | 分桶失去依据 |
| **会议摘要库** `scripts/meeting_pull.py --conference "ESMO 2026"` | 全本摘要（ESMO 2026：4103 篇可用 vs 结构化表 646 篇）、`abstract_id`（= 报告形式）、`target` / `drug` / `moa` | 漏掉刚发布、还没入库的资产；丢掉最强的报告形式先验 |

实证：BG-C477（2567P，43 例 NSCLC，ORR 34.9%）在会议摘要库里有、在结构化结果表里查不到。只读结构化表 = 早期机会桶系统性失明。

```bash
python3 scripts/meeting_pull.py --conference "ESMO 2026" --out mm.json      # 5810 条，约 4 分钟
python3 scripts/meeting_join.py --meeting mm.json --rows rows.json \
    --out-annotations ann.json --out-supplement supplement.json
```

- `join` 按 title 匹配（ESMO 2026：646/646 命中，零损失），给结构化行补 `abstract_id` / `presentation` / `target` / `drug` / `moa` / 全文。
- `supplement.json` 是只在摘要库里的记录，**只进 early 桶**（期别是从散文正则抽的，不足以撑 pivotal/failed）。

禁止"先按 evaluation 筛一遍再拉"——`evaluation` 是记录级枚举，先筛会漏掉同一试验的其它摘要。

### Step 2 — 机械筛（确定性，无判断）

```bash
python3 scripts/triage.py --input rows_with_supplement.json --out-dir out --top 0
```

产出 `out/pool.json`（三桶 + excluded 计数）、`out/pool.md`（人眼速览）、`out/review.jsonl`（复核批次）。

脚本只做四件事：esid 去重 → 排除非试验证据源 → 按规则分桶 → 附非权威机器信号。
它**不打临床分、不排序推荐**。池内顺序按 `(报告形式, n)`，仅供阅读，不是推荐顺序。

分桶与排除规则见 `references/screening-rules.md`。三条不可改的硬规则：

- **n 不作入榜门槛**，只做展示与并列次级排序（样本 15 的 I 期和样本 900 的 III 期不是同一把尺子，但都不能因为 n 小就直接出局）。
- **真实世界 / 回顾性 / 汇总分析 / 试验进行中一律不进三桶**，单独计入 `excluded`。
- **试验分期取 `evidence_source`**，不是 `clinical_condition.clinical_stage`（那是疾病分期，不是试验期别）。

### Step 2.5 — 两条先验（v0.2 新增，实测有效）

**报告形式**：摘要号后缀就是报告等级 —— `1234O` 口头、`1234RO` 快速口头、`LBA1234` late-breaking、`1234P` 壁报、`1234eP` 电子壁报。ESMO 2026 候选池口头级占 25%，但内部专家挑的 7 条里 **4 条是口头（57%）**，富集 2.3 倍。用法：**加权 + 榜单标注，绝不做硬门槛**（专家也挑了 3 条壁报）；同分时口头优先。

**人群难度**：ORR 门槛分档 —— 一线/未治疗 ≥40%，后线（≥2 线）或明确耐药 ≥25%。降档的**前提是把人群写进 reason/evidence**。反例：9MW2821 在 TOP1i-ADC 耐药 TNBC ORR 30.0%、mPFS 3.7 mo、已开 III 期，按 40% 硬线会被误判成 weak。

### Step 3 — 逐条复核（模型，本 skill 的核心）

按 `references/review-protocol.md` 执行。要点：

- 每批 **15 条**，每条给"压缩摘要"（Background 320 字 / **Results 全文** / Conclusion 280 字）+ `summary` 独立字段 + 机器信号。
  **Results 绝不截断**：ESMO 2026 的 Results 段中位数 956 字符，截到 760 会让 52% 的摘要丢掉印出来的数字（实测直接把两条专家推荐误判成 weak）。
- 输出严格三键：`i`（原样抄）、`verdict ∈ {keep, weak, drop}`、`bucket ∈ {early, pivotal, failed}`（按证据强度重判，可覆盖机器分桶）、`reason ≤40 字`、`evidence`（**逐字**摘录 ≤120 字符）、`key_numbers`。
- 批次之间用顺序 `i` 索引合并，**合并前必须校验 i 覆盖 = 池子条数**；用 esid 对不上就说明批次错位，整批重跑，不要凑数。

`verdict` 的定义（不按"看起来有意思"，按**能不能支撑一句结论**）：

| verdict | 条件 |
|---|---|
| keep | 数字明确（ORR ≥ 40%，后线/耐药人群 ≥ 25% / HR ≤ 0.75 / OS 绝对获益 ≥ 3 月 / 明确阴性结论），且能引出具体数字 |
| weak | 有疗效数字但样本 < 20、单臂极小样本、关键数字落在未给出的表格里，或一般人群 ORR 25–40% 且无其它支撑 |
| drop | 只有安全性 / PK / 生物标志物 / HRQoL，或只说"将继续评估"而无结果 |

### Step 4 — 合并与定榜

1. 合并全部批次 → `judgements.csv`（全量判定，可追溯）。
2. 定榜时**再收一次**：判 `bucket` 与 `data_type`；同一试验的多篇摘要只留信息量最大的一篇（其余在"同试验其它摘要"里点名）。
3. **跑同资产历史对照**：`python3 scripts/history_for.py --pool out/pool.json --top 10 --out history.md`。ESMO 2026 实证：SYS6043 从 ASCO 2026 的 64.0%（n=502）到 ESMO 2026 的 45.7%（n=137），9MW2821 从 ESMO 2023 的 38.5% 一路降到 30.0% —— 单次会议快照看不出这种趋势。
4. 每桶 10 条，附「候补（差一位）」。**不要为了凑 10 条把 weak 提上来**——不足就写不足。

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
- ❌ 截断 Results 段：整篇摘要才 ~2 KB，截断零收益、纯丢数字（见 `references/pitfalls.md` §11）。
- ❌ 只信机器信号不看原文：两字母缩写曾被当子串匹配（`resp**os**e` → 总生存期），无标签的行会继承 `primary_endpoint_cn[0]`（多为一安全终点），把 ORR 52.5% 印成「剂量限制性毒性 52.5%」。
- ❌ 只看结构化结果表：它只收已入库的结构化记录，刚发布的 FIH 数据可能还没进去。

## 支持文件

| 文件 | 何时读 |
|---|---|
| `references/data-contract.md` | 每次拉数前（字段、MCP 调用、返回形状） |
| `references/screening-rules.md` | 改分桶/排除规则时；解释"为什么这条不在榜上" |
| `references/review-protocol.md` | 每次复核前（批次设计、verdict、证据校验） |
| `references/pitfalls.md` | 数据口径存疑时（字段缺失、统计稀疏、多摘要） |
| `templates/watchlist-report.md` | 写交付物时 |
| `dist/ESMO2026-watchlist.md` | 已完成的真实样例（ESMO 2026，30 条，v0.1 产出） |
| `dist/v02/ESMO2026-watchlist-v02.md` | v0.2 定榜（ESMO 2026，532 候选取 → 30 条），**当前参照样例** |
| `dist/v02/judgements.csv` | v0.2 全量逐条判定（532 行，机器桶与复核桶并排） |
| `dist/v02/history.md` | v0.2 同资产历次会议读数（10 个药、185 条记录） |
| `dist/v0.1-vs-expert-gap.md` | v0.1 与 7 条内部专家推荐的差距归因（v0.2 的立项依据） |

## 脚本

| 脚本 | 作用 | 依赖 |
|---|---|---|
| `scripts/triage.py` | 机械筛：去重 / 排除 / 分桶 / 机器信号 / 分批 | 零依赖 |
| `scripts/meeting_pull.py` | 拉会议摘要全本（MCP `medicalMeeting`） | 仅 urllib |
| `scripts/meeting_join.py` | 摘要库 ↔ 结构化表 join，产出 `annotations` + `supplement` | 需 triage.py |
| `scripts/history_for.py` | 同资产历次会议数据对照 | 需上面两个 |
| `scripts/make_watchlist.py` | 按给定顺序渲染定榜 md/csv + 全量判定 csv（**只渲染不排序**） | 零依赖 |

## 版本

- **v0.1** — 首版，基于 ESMO 2026 全量（945 篇 → 467 候选 → 206 keep → 30 定榜）实跑校验。
- **v0.2** — 针对 7 条内部专家推荐的差距归因做四项改造：① Results 不再截断（760 → 全文）+ `summary` 独立字段 + 批次 25 → 15；② 接入会议摘要库作为并列数据源（补 `abstract_id`/报告形式/靶点/药名，并把只在摘要库里的记录补进 early 桶）；③ 报告形式加权（口头优先）+ 人群难度分档 ORR 门槛；④ 同资产历史对照。候选池 467 → 532（early 248 / pivotal 235 / failed 49）。实测：判定覆盖 532/532、evidence 逐字命中 100%、专家 7 条 keep 3/7 → 5/7、进定榜 1/30 → 5/30。
