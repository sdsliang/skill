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

**先记住一条硬事实：平台工作区没有任何网络。** 在 chat 里实测过：in-cluster 数据服务器 `172.17.26.74:30080` 报 `Network is unreachable`，公网域名全部 `Temporary failure in name resolution`，`env` 里也没有任何 MCP 端点变量。所以**脚本不可能自己去连 MCP**——数据必须由「你调用平台工具」进来，再由脚本解析。

好在平台自己会把工具结果落盘：MCP 工具的返回值只要是列表，就会被写到 `/workspace/tool_results/<工具名>/<call-id>.jsonl`（每行一个 JSON row，强制落盘，不看大小），你在上下文里只看到前 5 + 后 5 行预览。**这意味着整场 1097 行可以用一次工具调用取全，而且不花上下文。** 正确姿势就两步：

1. **你调用工具** `pharmcube-query-clinical-result-with-params`，参数 `meeting_tags="ESMO 2026"`（或对应会议名）、`selected_fields` 用 `pull_results.py --list-fields` 打出来的那份清单（**逐字复制，别改名**）。工具回一句 "too large … saved to /workspace/tool_results/…"，把那个路径记下来。
2. **脚本解析落盘文件**：

```bash
S=/workspace/skills/conference-result-triage/scripts
mkdir -p /workspace/work /workspace/output
python3 $S/pull_results.py --from-tool-results /workspace/tool_results --out /workspace/work/rows.json
```

`--from-tool-results` 接受目录、glob 或单个文件，会跨多个 dump 去重合并，所以工具被切成几次调用也没关系。

> **这些 dump 在 turn 结束时会被清空。** 必须在**同一个 turn 内**解析完，`rows.json` 才是持久的落点。

`featured`（`是`= 人工生产 / `否`= 流水线抽取，**不是头条**）不在 `with-params` 的白名单里，需要另一次 `TEST_execute-sql` 调用：

```sql
SELECT extra_esid, featured, lba FROM clinical_trial_result_structured WHERE journal='ESMO 2026'
```

同样会落成一个 jsonl，然后加 `--flags-from /workspace/tool_results/pharmcube-TEST_execute-sql` 合回主表。它只用于卡片上的生产方式标注、**不参与排序**；这一步失败只降级不中断（会打 `WARNING: featured sidecar matched 0 rows`）。

成功输出形如：

```
flags: sidecar=1100 matched=1097 featured=97
rows=1097 lba=73 featured=97 with_abstract_text=1097 -> /workspace/work/rows.json
```

`missing>0` 或 `WARNING: … requested fields are absent` 说明有 id/字段没回：把那些 id 单独再查一次，不要带着缺口建池。

有三件事容易静默出错，脚本已经内置防线：

1. `clinical_result.lba` 必须显式写进 `selected_fields`，否则这个键直接消失 —— 整层 late-breaking 变哑。
2. 宽字段一次性拉会被工具截断在 ~6 MB 且仍 `ok: true`；走落盘 dump 就没有这个问题，若你改成自己分片拉，先只取 id 再按 `esids` 切片。
3. `featured`/`lba` 旁表的 esid 在 SQL 侧是 `24_37_p_…`、在 `with-params` 侧是 `nr_24_37_p_…`，脚本会剥 `nr_` 前缀（不剥会静默丢 97 条正是人工核对的行）。

**不要**用 `pull_results.py` 的直连模式（不带 `--from-tool-results`）：那是给本地/有外网环境用的，在平台里必然 `Network is unreachable`。

### Step 2 — 机械筛（无判断）

```bash
python3 $S/triage.py /workspace/work/rows.json --out-dir /workspace/work/pool --top 0
```

产出 `pool/pool.json`（三桶 + excluded）、`pool/pool.md`（人眼速览）、`pool/review.jsonl`（复核批次）。ESMO 2026 基准：1097 行 → **551 候选**（early 200 / pivotal 292 / failed 59）+ excluded 538，37 批。

脚本不打临床分、不排序推荐。池内顺序按 `(报告形式, n)`，仅供阅读。规则见 `references/screening-rules.md`，三条不可改：

- **n 不作入榜门槛**，只做展示与并列次级排序。
- **真实世界 / 回顾性 / 汇总分析 / 试验进行中不进三桶**，单独计入 `excluded`。
- **试验分期取 `evidence_source`**，不是疾病分期 `clinical_stage`。

### Step 3 — 报告形式信号（平台内只剩 `lba`）

先说清两件事，避免重复踩坑：

**一、平台内拿不到摘要号。**

- 结果表 `clinical_trial_result_structured` 111 列里**没有 `abstract_id`**；
- 平台 35 个工具里**没有**会议摘要库（`medicalMeeting`），23 张可查表里也没有会议表；
- `abstract_text` 全部以 `#### Background` 开头，编号不在正文里；`paper_title` 也不带 `LBA` 前缀。

**二、`featured` 不是头条，是「人工 / AI 生产」标记。** 实测 `featured='是'` **100/100 就等于** `source='np_result_conf'` 那一档（人工核对过的结果），其余 1000 条 `np_clinical_conference` 全是 `否`（流水线抽取）。所以：

- ❌ 不能拿它排序、不能拿它代表报告等级；
- ✅ 只能作为每条卡片的生产方式标注（「人工核对」/「流水线抽取」），属于诚实声明的一部分。

`triage.py` 里 `manual` 字段就是它，`manual_of()` 只做布尔解析，`presentation_of()` **完全不看它**。

平台内真正可用的报告形式信号只有 `lba`（`clinical_result.lba`，白名单内，ESMO 2026 共 73 行）：

| presentation | 条件 | rank |
|---|---|---|
| `Late-breaking Oral` | `lba` 为真（或 `abstract_id` 以 `LBA` 开头） | 0 |
| `Oral` / `eOral` | `abstract_id` 后缀 `O`（仅外网补号后才有） | 1 |
| `Rapid Oral` / `eRapid Oral` | 后缀 `RO` | 2 |
| `Poster` | 后缀 `P` | 4 |
| `ePoster` | 后缀 `eP` | 5 |
| `Unknown` | 三个信号都没有（平台内的绝大多数） | 9 |

ESMO 2026 实测：551 候选里 **51 条**拿到 `lba`（early 6 / pivotal 45 / failed 6），其余 500 条是 `Unknown` —— 这是诚实结果，不要为了"看起来有层级"去造。

`abstract_id` 在平台内**恒为 `null`**，卡片照常输出该字段（schema 固定）；有外网且配了 `PHARMCUBE_MCP_APP_KEY` 时才可选用会议库补号：

```bash
python3 $S/meeting_pull.py --conference "ESMO 2026" --out /workspace/work/meeting.json
python3 $S/attach_abstract_ids.py --pool /workspace/work/pool/pool.json \
    --meeting /workspace/work/meeting.json --out /workspace/work/pool/pool_labeled.json
```

这一步是**纯标注**：只写 `abstract_id` / `presentation` / `presentation_rank`，不增删、不重排、不改判定。平台内跑不了就跳过 —— 分类不受影响。

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
  {"esid": "24_37_p_...", "abstract_id": null, "lba": true, "manual": true,
   "bucket": "pivotal", "tag": "LBA",
   "title": "…", "summary": "…", "why": "…",
   "drug": "…", "target": "…", "indication": "…",
   "phase": "Phase III", "presentation": "Late-breaking Oral",
   "stock": null}
]}
```

- `esid` 是结果记录 id（用户要的"对应的结果id"）；`abstract_id` 是会议摘要号，平台内**恒为 `null`**（见 Step 3），有外网补库时才有值。
- `manual` 是生产方式标记（人工核对 / 流水线抽取），**不是**推荐等级。
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
| `scripts/meeting_pull.py` | 拉会议摘要全本（MCP `medicalMeeting`，**需外网，平台内不可用**） | 仅 urllib |
| `scripts/attach_abstract_ids.py` | 按标题 join 补 `abstract_id` / `presentation`（纯标注） | 需 triage.py |
| `scripts/triage.py` | 机械筛：去重 / 排除 / 分桶 / 机器信号 / 切批 / `--self-test` | 零依赖 |
| `scripts/make_cards.py` | 按 plan 顺序渲染卡片 JSON（**只渲染不排序**） | 零依赖 |
| `scripts/check_cards.py` | 交付前 fail-closed 校验（exit 3 = 有问题） | 零依赖 |
| `scripts/history_for.py` | 同资产历次会议对照（辅助判断趋势） | 需上面两个 |

## 版本

- **v0.1** — 首版，ESMO 2026 全量实跑（467 候选 → 30 条）。
- **v0.2** — Results 不截断 + 会议摘要库并列数据源 + 报告形式加权 + 人群难度分档；候选 532，evidence 逐字 100%，专家 7 条 keep 3/7 → 5/7。
- **v0.3** — 改为平台内执行：取数唯一走 MCP（`pull_results.py` 两阶段切片），补 `clinical_result.lba`（v0.2 漏选导致整类 LBA 丢失），`PRESENTATION_RANK` 修正（Presidential/LBA 不再被压到普通口头之下），会议库标题 join 补回 LBA 编号（57/57），交付物改为 `/workspace/output/watchlist.json` 卡片清单。候选 551（early 200 / pivotal 292 / failed 59）。
- **v0.4** — 平台工作区实测**无网络**：取数改为「你调工具 → 结果落 `/workspace/tool_results/*.jsonl` → `pull_results.py --from-tool-results` 解析」，整场 1097 行 0 上下文成本；`featured` 更正为人工/AI 生产标记（`是` 100/100 = `source=np_result_conf`），撤掉 Featured 层级，报告形式只剩 `lba`；`featured` 字段改名 `manual`,只做卡片标注。
