---
name: conference-result-triage
description: Use when someone names a conference and asks what is worth reading from its result library — "ESMO 2026 有什么值得看的"、"帮我挑这届会议的重磅/失败研究"、"会议结果推荐清单"、"早期机会有哪些"、会前选题、竞品会前扫描。Pulls the whole conference snapshot through the Tool Smith data server, mechanically dedupes and excludes non-trial evidence, splits into three buckets (early opportunity / pivotal Phase II-III / failed), reviews every candidate one by one, and delivers a JSON reading list of small cards (title + LBA tag + summary + why + result esid, plus the same-day stock move when one is supplied). Do not use it for interpreting one already-selected result, for drug-vs-drug comparison, for coverage checks against np_result, or for writing a full meeting report.
---

# Conference Result Triage

## Purpose

一场会议的登记结果有上千条，绝大多数不需要读。交付物是**一个 JSON 推荐清单**，每张卡片回答三件事：报告了什么、为什么值得读、对应哪条结果记录。

设计原则：**机器只做机械筛，模型只做阅读判断，谁都不自算数字。**

- `scripts/` 负责去重、排除非试验证据、分桶、切批、校验、渲染。零第三方依赖，确定性。
- 模型负责逐条读摘要，判 `keep | weak | drop`，写出理由与**逐字摘录**的证据。
- 卡片上的每个数字都必须能回指该条记录原文，不能回指的一律不写。

## Input

用户只需要给一个**会议标识**（`ESMO 2026` / `ASCO 2026` / `WCLC 2026`）。这个值精确匹配会议标签，写错就是空集，不是模糊搜索 —— 拉数后先看 `rows=` 是否合理，再往下走。

可选：限定瘤种/公司/期别、清单条数（默认三档共 30 条）。用户没说就不问，直接全量跑。

## Run sequence

所有路径是平台固定路径，不要带日期/会议名/序号后缀。

```bash
S=/workspace/skills/conference-result-triage/scripts
mkdir -p /workspace/work /workspace/output
```

按顺序执行，每一步都检查退出码。统一用 `… 2>&1 | tail -30; echo "EXIT=${PIPESTATUS[0]}"` 拿到真实状态（裸 `| tail` 会显示 tail 的 0）。

### Step 1 — 拉全量结果行（唯一允许取数通道）

```bash
python3 $S/pull_results.py --conference "ESMO 2026" --out /workspace/work/rows.json
```

它走 Tool Smith 数据服务器的 MCP 工具 `query-clinical-result-with-params`，**禁止**改去查 Elasticsearch：平台工作区读不到结果表，而 ES 侧的 `np_clinical` 没有 `lba` 列，一旦绕路就会把整个 late-breaking 层静默丢掉。

脚本内部做两件事，都是防静默失败的：先只取 id（一次回全量），再用 `esids` 切片取全字段（响应体约 6 MB 上限，35 字段的整场调用只会回 ~500 行且 `ok: true`）。成功输出形如：

```
rows=1097 requested=1097 missing=0 lba=73 with_abstract_text=1097 -> /workspace/work/rows.json
```

`missing>0` 说明有 id 没回记录：把那些 id 单独再查一次，不要带着缺口建池。

### Step 2 — 补摘要号与报告形式（可选但强烈建议）

结构化结果表只有布尔 `lba` 标记，**没有摘要号**。摘要号（`LBA3`、`1040O`、`2567P`）是"这是不是头条"最强的单一先验，所以在会议摘要库里按标题 join 补回来：

```bash
python3 $S/meeting_pull.py --conference "ESMO 2026" --out /workspace/work/meeting.json
python3 $S/attach_abstract_ids.py --pool /workspace/work/pool.json \
    --meeting /workspace/work/meeting.json --out /workspace/work/pool_labeled.json
```

ESMO 2026 实测 551/551 命中，池内 57 条 LBA 全部拿回编号。没有会议库（无外网/无 appkey）就跳过 —— 卡片里 `abstract_id` 留 `null`，`lba` 标记仍然有效，分类不受影响。

### Step 3 — 机械筛（无判断）

```bash
python3 $S/triage.py /workspace/work/rows.json --out-dir /workspace/work/pool --top 0
```

产出 `pool/pool.json`（三桶 + excluded）、`pool/pool.md`（人眼速览）、`pool/review.jsonl`（复核批次）。ESMO 2026 基准：1097 行 → **551 候选**（early 200 / pivotal 292 / failed 59）+ excluded 538，37 批。

脚本不打临床分、不排序推荐。池内顺序按 `(报告形式, n)`，仅供阅读。规则见 `references/screening-rules.md`，三条不可改：

- **n 不作入榜门槛**，只做展示与并列次级排序。
- **真实世界 / 回顾性 / 汇总分析 / 试验进行中不进三桶**，单独计入 `excluded`。
- **试验分期取 `evidence_source`**，不是疾病分期 `clinical_stage`。

### Step 4 — 逐条复核（模型，核心步骤）

按 `references/review-protocol.md` 执行。切批用 `triage.py` 的批次文件，**每批 15 条**。

候选超过 40 条时用 `task` 委派，把批文件分给子代理：一个 `task` 吃 2–3 个批文件，输出一个 `judged_<n>.json` 数组。子代理**不继承本 Skill 的 prompt**，所以它的 `description` 必须自带完整契约（`references/review-protocol.md` §2–§4 的内容），并明确要求写文件后回读校验。

每条输出六个键：

| 键 | 约束 |
|---|---|
| `i` | 原样抄，不得改动；**不要用 esid 索引** |
| `bucket` | `early` / `pivotal` / `failed`，按证据强度重判，可覆盖机器桶 |
| `verdict` | `keep` / `weak` / `drop`，见下表 |
| `reason` | ≤40 个汉字，必须点出人群难度档 |
| `evidence` | 该条 `results` 或 `background` 的**连续原文子串**，≤120 字符；不拼接、不改写、不去表格符号 |
| `key_numbers` | 只列带单位数字（%、月、HR、OR/CI、p），不列纯计数 |

| verdict | 条件 |
|---|---|
| keep | ORR 一线/初治 ≥40%，后线/耐药 ≥25%，或 HR ≤0.75，或 OS 绝对获益 ≥3 月，或明确阴性结论 |
| weak | 有疗效数字但 n<20、单臂极小、关键数字只在表里；或一般人群 ORR 25–40% 且无其它支撑 |
| drop | 只有安全性 / PK / 生物标志物 / HRQoL，或只说"将继续评估"而无结果 |

降档 ORR 门槛（后线 ≥25%）**必须把人群写进 `reason`/`evidence`**，否则不成立。

合并前先校验：`i` 覆盖必须等于池子条数、`evidence` 必须是原文子串、`reason` 长度合规。任一项不过整批重跑，不要凑数。

### Step 5 — 定榜（编辑决策，不在脚本里）

从 `keep` 里挑，**不要为了凑数把 `weak` 提上来**，不足就写不足。默认每桶 10 条：

1. 早期机会 10 条：新机制/新靶点，数字超出该适应症历史水位。
2. 重磅 II/III 期 10 条：随机对照、主要终点达成且有临床意义；late-breaking / 口头优先。
3. 失败 10 条：III 期或大型随机研究的主要终点未达 / 提前终止 / OS 反向。

写 `plan.json`：

```json
{"conference": "ESMO 2026", "cards": [
  {"esid": "...", "bucket": "pivotal", "title": "…", "summary": "…", "why": "…"}
]}
```

`title` / `summary` / `why` 三条必填，缺一条脚本直接停。`summary` 写报告了什么（带数字），`why` 写为什么值得读（自然语言，一句话，点出人群或对照）。

### Step 6 — 渲染交付物

```bash
python3 $S/make_cards.py --pool /workspace/work/pool_labeled.json \
    --plan /workspace/work/plan.json --out /workspace/output/watchlist.json --pretty
python3 $S/check_cards.py --cards /workspace/output/watchlist.json \
    --pool /workspace/work/pool_labeled.json
```

`check_cards.py` **必须 exit 0** 才能交付。它拦的是：编造的 esid、空字段、`lba` 与实际记录不符、占位符泄漏、`summary` 无带单位数字、以及 `summary`/`why` 里出现原文查不到的数字。

股票涨跌是同一天的市场数据，结果库里没有。给了 `--quotes`（`{"<esid>": {"ticker": "…", "change_pct": 5.2, "date": "2026-10-19"}}`）就附在对应卡片上；没给就留 `null`，**绝不用其它日期的涨跌顶替**。

### Step 7 — 交付

`present_artifact` 指向 `/workspace/output/watchlist.json`。这是唯一终端动作，不要改成把 JSON 贴进对话。

## Deliverable schema

```json
{"conference": "ESMO 2026", "count": 30, "cards": [
  {"esid": "24_37_p_...", "abstract_id": "LBA3", "lba": true,
   "bucket": "pivotal", "tag": "LBA",
   "title": "…", "summary": "…", "why": "…",
   "drug": "…", "target": "…", "indication": "…",
   "phase": "Phase III", "presentation": "Late-breaking Oral",
   "stock": null}
]}
```

- `esid` 是结果记录 id（用户要的"对应的结果id"）；`abstract_id` 是会议摘要号，可能为 `null`。
- 路径固定为 `/workspace/output/watchlist.json`：后端硬编码读取，改名即断链。同一工作区复跑就覆盖。
- `write_file` 一律带 `overwrite=True`，包括首次写入。

## 两个必须写进清单的诚实声明

1. **`data_type`（首次 / 更新 / 亚组·二次分析 / 未判定）**。会议摘要有大量"长期随访""post-hoc 亚组"，不是新数据。判不出来写「未判定」，**不要猜**。
2. **覆盖边界**。`summary` 里只有约一半记录带 p 或 HR；同一试验常拆成多篇。清单不是全覆盖，别让读者以为是。

## Anti-patterns

- ❌ 在本地/工作区直连 Elasticsearch 拉表。ES 侧没有 `lba` 列，v0.2 因此整类漏掉 12 条 Presidential LBA。取数只走 `pull_results.py`。
- ❌ 一次调用取全字段整场数据。响应体约 6 MB 上限，超出部分被静默截断成 ~500 行且返回 `ok: true`。
- ❌ 用规则给"重磅程度"打分：会把 `Grade≥3 TEAE 44.6%` 当疗效信号、`PR = 3 subjects` 当 3% 缓解率。只判不评。
- ❌ 让模型自己算 ORR 变化率/HR 差值。只抄不算。
- ❌ 用 `clinical_stage` 当试验期别（那是疾病分期）。
- ❌ 先按 `evaluation` 筛再拉：同试验亚组摘要的 evaluation 可能不同，先筛会丢主结果。
- ❌ 截断 Results 段。整篇摘要约 2 KB，Results 中位数 956 字符，截到 760 会让一半摘要丢掉印出来的数字。
- ❌ 批次用 esid 索引。批次内顺序与池子顺序不一致，必须用显式 `i`。
- ❌ 只为只在会议摘要库里的记录进 pivotal/failed。期别是从散文正则抽的，不足以撑高证据档；它们只进 early（**LBA 行例外**：late-breaking 是最高证据档，不适用此限制）。

## 支持文件

| 文件 | 何时读 |
|---|---|
| `references/data-contract.md` | 每次拉数前（字段、MCP 调用、返回形状、预算） |
| `references/screening-rules.md` | 改分桶/排除规则时；解释"为什么这条不在榜上" |
| `references/review-protocol.md` | 每次复核前（批次契约、verdict、证据校验） |
| `references/pitfalls.md` | 数据口径存疑时（字段缺失、静默截断、多摘要） |
| `dist/` | 已完成的 ESMO 2026 实跑样例（md 榜单 / 全量判定 csv / 历史对照） |

## 脚本

| 脚本 | 作用 | 依赖 |
|---|---|---|
| `scripts/pull_results.py` | 拉整场结果行（MCP `query-clinical-result-with-params`，自动切片） | 仅 urllib |
| `scripts/mcp_client.py` | 最小 MCP streamable-HTTP 客户端（工具名自动发现） | 仅 urllib |
| `scripts/meeting_pull.py` | 拉会议摘要全本（MCP `medicalMeeting`） | 仅 urllib |
| `scripts/attach_abstract_ids.py` | 按标题 join 补 `abstract_id` / `presentation` | 需 triage.py |
| `scripts/triage.py` | 机械筛：去重 / 排除 / 分桶 / 机器信号 / 切批 / `--self-test` | 零依赖 |
| `scripts/make_cards.py` | 按 plan 顺序渲染卡片 JSON（**只渲染不排序**） | 零依赖 |
| `scripts/check_cards.py` | 交付前 fail-closed 校验（exit 3 = 有问题） | 零依赖 |
| `scripts/history_for.py` | 同资产历次会议对照（辅助判断趋势） | 需上面两个 |

## 版本

- **v0.1** — 首版，ESMO 2026 全量实跑（467 候选 → 30 条）。
- **v0.2** — Results 不截断 + 会议摘要库并列数据源 + 报告形式加权 + 人群难度分档；候选 532，evidence 逐字 100%，专家 7 条 keep 3/7 → 5/7。
- **v0.3** — 改为平台内执行：取数唯一走 MCP（`pull_results.py` 两阶段切片），补 `clinical_result.lba`（v0.2 漏选导致整类 LBA 丢失），`PRESENTATION_RANK` 修正（Presidential/LBA 不再被压到普通口头之下），会议库标题 join 补回 LBA 编号（57/57），交付物改为 `/workspace/output/watchlist.json` 卡片清单。候选 551（early 200 / pivotal 292 / failed 59）。
