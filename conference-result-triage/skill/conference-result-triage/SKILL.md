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
- 卡片上的每个数字都必须能回指该条记录原文，不能回指的一律不写。**照抄原文的写法与小数位**：原文 `44.7%` 就写 `44.7%`，写成 `44%` 是自算（四舍五入），闸门按**数值**比对，`44` 不等于 `44.7`；想写「随访约 16 个月」就把原数钉进去（`16.1 mo` → 「随访约 16.1 个月」）。

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

### Step 1 — 拉全量结果行（四阶段，唯一允许取数通道）

**两条硬事实先记住：**

1. **平台工作区没有任何网络。** 实测：in-cluster `172.17.26.74:30080` → `Network is unreachable`；公网 → `Temporary failure in name resolution`；`env` 里没有 MCP 端点变量。脚本不可能自己连数据服务，所以 `pull_results.py` 不带 `--from-tool-results` 时必然失败（那是本地/有外网用的直连模式）。
2. **宽字段一次拉会被静默截断。** 工具响应上限约 6 MB / ~500 行，超了照样回 `ok: true`。实测 `meeting_tags="ESMO 2026"` + 32 字段只回来 **458 行**（全场 1097），模型当时看到的是「500/1434」——没有任何报错。**所以必须切片，不能图省事一次拉完。**

数据进得来的唯一通道是「你调工具 → 平台把结果落盘 → 脚本解析」。MCP 工具返回 `data` 为列表时，平台**强制**把它写成 `/workspace/tool_results/<工具名>/<call-id>.jsonl`（一行一个 row），你在上下文里只看到 5 头 5 尾的预览。**所以整场 1097 行一次拉全也不占上下文**——但受限于上面第 2 条，仍要分片。

**阶段 A：只拉 id（一次就全）**

调 `pharmcube-query-clinical-result-with-params`：

- `meeting_tags = "ESMO 2026"`（会议名精确匹配，写错就是空集）
- `selected_fields = ["clinical_result.extra_esid"]`（**只这一个**）

1097 行 id ≈ 50 KB，不会截断。工具会告诉你落盘路径。

**阶段 B：切片**

```bash
S=/workspace/skills/conference-result-triage/scripts
mkdir -p /workspace/work /workspace/output
python3 $S/plan_slices.py --ids-from /workspace/tool_results --size 150 \
    --out-dir /workspace/work/slices
```

它会打印 `ids=1097 slices=8` 和每片的 id 数组，同时写出 `slice_01.json … slice_08.json` 与 `_all_ids.txt`。

**阶段 C：逐片拉全字段**

对每一片调一次同一个工具：

- `esids = <该片的数组，原样粘贴>`
- `selected_fields = pull_results.py --list-fields 的输出，逐字复制`

> ⚠️ **字段名只能取 `clinical_result.*`**。老笔记里的 `research_design.evaluation.text`、`base.abbreviation_label.text` **在线上白名单里不存在**，带上就会整次调用 `INVALID_INPUT: Invalid fields selected`，一行都不回（一个坏名字废掉整片，不是只废一列）。这两个值已分别由 `clinical_result.evaluation` / `clinical_result.abbreviation_label` 提供。

8 片就是 8 次工具调用、8 个 dump。

**阶段 D：合并**

```bash
python3 $S/pull_results.py --from-tool-results /workspace/tool_results \
    --expect-ids /workspace/work/slices/_all_ids.txt \
    --out /workspace/work/rows.json
```

`--from-tool-results` 接受目录 / glob / 单文件，跨多次调用去重合并（一个 esid 可能对应多行，脚本按 `clinical_result__id` 合并）。`--expect-ids` 会报覆盖缺口，正常输出：

```
rows=1097 lba=73 featured=0 with_abstract_text=1097 -> /workspace/work/rows.json
coverage: 1097/1097 ids present
```

若出现 `WARNING: … N missing`，把 `MISSING_IDS` 那批单独再查一次，**不要带着缺口建池**。

`rows.json` 自带 `sources`（每个 dump 名 + 它贡献了多少行）。这是分片有没有真的分过的**唯一持久证据**：分片调用常发生在 `task` 子代理里，父回合的 `debug-history.json` 看不到，而 `tool_results/` 在回合结束时被清空。v0.5 曾要求另写一份 `slice_counts.json` 账本，实跑里被漏掉 → 审计无从下口，所以改成让数据文件自己带出处。

```json
{"conference": "ESMO 2026", "rows": [...], "requested": 1097, "missing": [],
 "sources": [{"dump": "slice_01.jsonl", "rows": 150}, … 共 8 条]}
```

**两个已知拿不到的东西，别浪费时间：**

- **`featured`（人工/AI 生产标记）不在白名单**，`with-params` 选不出来；`TEST_execute-sql` 又**不能绑定到项目**（`400 MCP tools unavailable for pharmcube: pharmcube-TEST_execute-sql`）。所以平台内 `manual` 恒为 `null`，卡片上写「生产方式未知」，不要猜。
- **`abstract_id` 恒为 `null`**：结果表 111 列里没有摘要号，35 个工具里没有会议摘要库工具。输出这个键并置 `null`，**绝不编造编号**。

> dump 在 **turn 结束时清除**，必须同 turn 解析完，`rows.json` 才是持久的落点。

### Step 2 — 机械筛（无判断）

```bash
python3 $S/triage.py /workspace/work/rows.json --out-dir /workspace/work/pool --top 0
```

产出 `pool/pool.json`（三桶 + excluded）、`pool/pool.md`（人眼速览）、`pool/review.jsonl`（复核批次）。ESMO 2026 基准（v0.6）：1097 行 → **592 候选**（early 200 / pivotal 306 / failed 86）+ excluded 505，40 批。

> **`--top 0` 就是「不截断」。** 这个参数只用于压 token 试跑：ESMO 2026 设 `--top 60` 会把 pivotal 第 64 名的 SAFFRON（LBA2）切掉，而榜上照样显示"已覆盖"。正式出榜必须全量判读，`--top N` 只写进试跑记录。

脚本不打临床分、不排序推荐。池内顺序按 `(报告形式, n)`，仅供阅读。规则见 `references/screening-rules.md`，三条不可改：

- **n 不作入榜门槛**，只做展示与并列次级排序。
- **真实世界 / 回顾性 / 汇总分析 / 试验进行中不进三桶**，单独计入 `excluded`。但 **`前瞻性研究` 不是排除理由**——它是「真试验、分期没填」，73 条 ESMO 2026 LBA 里 16 条都是这个值，`lba` 为真仍进 pivotal（见 `references/screening-rules.md` §1.1.1）。
- **试验分期取 `evidence_source`**，不是疾病分期 `clinical_stage`。

### Step 3 — 报告形式信号（平台内只剩 `lba`）

先说清两件事，避免重复踩坑：

**一、平台内拿不到摘要号。**

- 结果表 `clinical_trial_result_structured` 111 列里**没有 `abstract_id`**；
- 平台 35 个工具里**没有**会议摘要库（`medicalMeeting`），23 张可查表里也没有会议表；
- `abstract_text` 全部以 `#### Background` 开头，编号不在正文里；`paper_title` 也不带 `LBA` 前缀。

**二、`featured` 不是头条，是「人工 / AI 生产」标记。** 实测 `featured='是'` **100/100 就等于** `source='np_result_conf'` 那一档（人工核对过的结果），其余 1000 条 `np_clinical_conference` 全是 `否`（流水线抽取）。所以：

- ❌ 不能拿它排序、不能拿它代表报告等级；
- ✅ 只能作为每条卡片的生产方式标注（「人工核对」/「流水线抽取」），属于诚实声明的一部分。**平台内取不到这个字段**（见 Step 1），所以卡片写 `manual: null` 并在正文说「生产方式未知」——`false` 是伪造结论，`null` 才是实话。

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

ESMO 2026 实测：592 候选里 **51 条**拿到 `lba`（early 6 / pivotal 45 / failed 6），其余 541 条是 `Unknown` —— 这是诚实结果，不要为了"看起来有层级"去造。

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

每条输出八个键：

| 键 | 约束 |
|---|---|
| `i` | 原样抄，不得改动；**不要用 esid 索引** |
| `bucket` | `early` / `pivotal` / `failed`，按证据强度重判，可覆盖机器桶 |
| `verdict` | `keep` / `weak` / `drop`，见下表 |
| `score` | **你判读出来的** 0–100 整数（评分卡见 `review-protocol.md` §2.5） |
| `score_parts` | 五维 `evidence_strength≤30` / `effect_size≤25` / `clinical_impact≤25` / `novelty≤10` / `readout_maturity≤10`，**相加必须等于 `score`** |
| `reason` | ≤40 个汉字，必须点出人群难度档 |
| `evidence` | 该条 `results` 或 `background` 的**连续原文子串**，≤120 字符；不拼接、不改写、不去表格符号 |
| `key_numbers` | 只列带单位数字（%、月、HR、OR/CI、p），不列纯计数 |

**分数只能由判读产生，不能由脚本算。** 试过按 `phase` + `n` + 正则抓 HR/p 加权：安全性摘要被排到疗效摘要前面，`PR count = 3 subjects` 被读成缓解率。那种分是假精确。所以：你读完给分，脚本只查「五维相加 == 总分、各维不超上限」。

| verdict | 条件 |
|---|---|
| keep | ORR 一线/初治 ≥40%，后线/耐药 ≥25%，或 HR ≤0.75，或 OS 绝对获益 ≥3 月，或明确阴性结论 |
| weak | 有疗效数字但 n<20、单臂极小、关键数字只在表里；或一般人群 ORR 25–40% 且无其它支撑 |
| drop | 只有安全性 / PK / 生物标志物 / HRQoL，或只说"将继续评估"而无结果 |

降档 ORR 门槛（后线 ≥25%）**必须把人群写进 `reason`/`evidence`**，否则不成立。

合并前先校验：`i` 覆盖必须等于池子条数、`evidence` 必须是原文子串、`reason` 长度合规。任一项不过整批重跑，不要凑数。

### Step 5 — 定榜（两段收敛：初选 15 → 联网终选 10）

#### 5A 初选（编辑取舍，≤15 条/桶）

从 `keep` 里挑，**不要用 `weak` 凑数**；不足就少给。压同质（同机制最多 2 条）、标数据类型（首次公布 > 更新 > 亚组）、看同资产历史读数（`history_for.py`）。产物写 `work/shortlist.json`，**它不是交付物**，只是终选的输入。

#### 5B 联网终选（≤10 条/桶、全场 ≤30）

这一步的作用是**把榜单从"会议库里挑出来的"变成"外部世界也认的"**：找出被机械筛和初选漏掉的热点，并把研发公司是否上市查清楚。**必须主 agent 亲自跑检索**，不要交给 `task` 子代理（子代理的成本策略与工具面不同，主 agent 也看不到原始 URL 标题，无法判断来源可靠性）。

**工具**：联网检索靠平台的 `web_search`（部分模型把它显示成 `web.run`，同一个东西：入参 `queries`/`query`，回 `sources` + `items[url,title]`）。它有个**双重开关**，缺一个就静默不可用：项目 `capabilities_config.web=true` **且** 本回合以 `enable_web=true` 发起（UI 上就是"联网"按钮）。实测过能力已开但回合没带 flag —— 模型看到的工具表里干脆没有检索工具，于是它会一路"没有联网工具"地编下去。发现没有这个工具时**停下来告诉用户开联网**，不要假装查过。`freshness` 只在需要时效时才收紧，默认不限。

**每桶至少 6 次查询**，四类模板各覆盖一次：

| 目的 | 查询模板 |
|---|---|
| 会议现场热度 | `"<会议> <药名/试验名> results"` |
| 适应症内定位 | `"<药名> <适应症> data <会议> <年份>"` |
| 未被收录的热点 | `"<会议> late-breaking abstract <适应症> most anticipated"` |
| 上市公司 | `"<公司名> listed ticker exchange"`（再用 `web_fetch` 打开交易所/公司 IR 页确认） |

**证据要落盘**：每次检索追加一行到 `work/web/<bucket>.jsonl`（`{"query","title","url","published_at","note"}`）。回合结束 `/workspace/tool_results/` 会清空，只有这个文件留下来能复核。**检索跑了但一条能用的来源都没有**时，也要写一行、`url` 留空、在 `note` 里写清"无可用返回"——空 `note` 的裸记录会被判为凑数；整份证据里**至少 6 行要带真实 http URL**。

**允许 `promote`（外部热议但初选漏了）**：前提是它在 `work/rows.json` 里 —— 卡片上的数字必须有原文出处。写卡时标 `"promoted": "web"`，并在 `why` 里点明外部讨论的是什么（例：多项报道把该读数列为该适应症本届最受关注的口头报告）。**`rows.json` 里根本没有的研究一律不进卡**，只在 `coverage_notes` 里写一句"外部讨论了 X，但会议库无对应记录，未纳入"。`check_cards.py --rows` 会按 `rows.json` 校验这类卡片；没有 `promoted` 标记却在池子外的 esid 直接拒绝。

**查上市公司**：每张卡都要落 `listed_company` 字段。上市 ⇒ 对象 `{name, ticker, exchange, source_url}`，`source_url` 必须是你真的打开过的页面；未上市或查不到 ⇒ `null`（**不要猜、不要用同名母公司顶替**）。这个字段只回答"谁在做这个药"，**不夹带任何行情**（v0.9 起）。

**为什么没有股价**：v0.8 曾要求每张卡印「会议期首个交易日 vs 会议前最后收盘」的涨跌幅，并逐条对账。v0.9 把整层删掉，理由是实测数据而不是口味——①按每条摘要自己的披露日重算后，24 条行情里 **18 条落在所属板块基准的 ±0.6% 以内**，即那个数字是板块 beta，"因为这条摘要涨了 X"不成立；②同一公司的多张卡拿到**同一个**数字（MRK 的 8 张卡都是 −3.83%），因为涨跌属于公司，不属于任何一条读数。会议当天的股价既不能归因于这条摘要，也不是推荐依据，留在清单里只会被读成信号。

**`ticker` 只写代码本体，市场写 `exchange`**：`09966` + `HKEX`，不是 `09966.HK` + `HKEX`（`check_cards.py` 会拒这类后缀——同一事实印两遍，也让「市场 + 裸代码」的查询没法复用）。

**联网失败是降级条件，不是中止条件**（v0.7 实跑教训）：`web_search` 无返回、`web_fetch` 单个站点 403/超时、IR 页打不开 —— 都只影响这一层，**清单照出**。处理顺序是：①换查询词/换源再试（检索结果里的标题与 URL 本身就能填 `listed_company.source_url`，不必打开页面）；②仍不行就按判读分收敛到 10 条，`listed_company` 一律 `null`；③在 `coverage_notes` 写一句「联网核实未完成（原因）」再交付。**绝对不要因为查不到上市公司或外部热度就"暂不交付 JSON"** —— 那等于用一个可选的增强步骤否决整份清单。已实测过：`web_search` 正常返回 12 条来源，模型却因为 `web_fetch` 打开 amgen.com 失败，写下"搜索无可用返回"并结束回合、零交付。

**终选原则**：每桶 ≤10 条。分数仍是内部定榜的主要依据，但**外部信号可以覆盖它**，覆盖了要在 `why` 里写清（"外部讨论集中在 X，而初选按分数把它排在 12 位"）。同机制仍最多 2 条。宁可 8 条也不要用 `weak` 补到 10。

写 `plan.json`：

```json
{"conference": "ESMO 2026", "cards": [
  {"esid": "...", "bucket": "pivotal", "score": 78,
   "score_parts": {"evidence_strength": 26, "effect_size": 22,
                   "clinical_impact": 20, "novelty": 4, "readout_maturity": 6},
   "title": "…", "summary": "…", "why": "…",
   "promoted": "web",
   "listed_company": {"name": "Tango Therapeutics", "ticker": "TNGX", "exchange": "NASDAQ",
                      "source_url": "https://investors.tangotx.com/"}}
]}
```

`title` / `summary` / `why` / `score` / `listed_company` 五条必填（`listed_company` 可以是 `null`，但键必须在），缺一条脚本直接停（`score_parts` 没给就沿用判读阶段的值）。

**模型必须在输出前对每桶按 `score` 降序排好**：`make_cards.py` 只按 `plan.json` 的顺序渲染，**不会替你排**（v0.8 的 e2e7 就跑出过 failed 桶 `[…,63,66]` 的升序尾巴，事实项 `A-P4-score-order` 判失败）。分桶内部一律降序，桶与桶之间的顺序没有意义（`early → pivotal → failed` 只是为了读者阅读）。

`summary` 写**报告了什么**（带数字）；`why` 写**这项研究值什么**，2–4 句、**≥60 字**，按「未满足需求 → 这次数据的定位 → 对治疗格局或后续研发的影响 → 主要局限」铺开，**不要复述 `summary` 的数字**，也不要写"数据很好、值得关注"这种空话。判读分不写进 `why`。

### Step 6 — 渲染交付物

```bash
python3 $S/make_cards.py --pool /workspace/work/pool_labeled.json \
    --plan /workspace/work/plan.json --out /workspace/output/watchlist.json --pretty \
    --rows /workspace/work/rows.json
python3 $S/check_cards.py --cards /workspace/output/watchlist.json \
    --pool /workspace/work/pool_labeled.json --rows /workspace/work/rows.json
```

`--rows` 只在有 `promoted` 卡片时才必需；给了它，池子外的 esid 必须带 `"promoted": "web"` 才放行。

`check_cards.py` **必须 exit 0** 才能交付。它拦的是：编造的 esid、空字段、`lba`/`manual` 与实际记录不符、占位符泄漏、`summary` 无带单位数字、`summary`/`why` 里出现原文查不到的数字（**按数值比对，不是子串**：`44%` 不会因为原文有 `44.7%` 或 `n=144` 而通过；`个月` 与 `mo` 一样会被扫描出来）、**每桶超过 10 条 / 全场超过 30 条**、**`score` 不是 0–100 整数或五维相加不等于总分**、**`why` 少于 60 字或只是复述 `summary`**、**`listed_company` 键缺失或给了假 ticker/假链接**、**任何行情字段回潮（`stock` / `reaction` / `change_pct` / `excess_pct`）**、**池子外的卡片没有 `promoted` 标记**、**`coverage_notes` 缺失或没写到两条边界**。

`coverage_notes` 必须写在交付 JSON 的顶层（见下「两个必须写进清单的诚实声明」）。v0.5 的实跑把它写成了别的字段名、v0.6 的实跑把边界写在 `coverage.boundary` 里 ⇒ 事实层 `A-H1` 两次都判失败：**边界只写在聊天回复里，下个月读 JSON 的人看不到**。所以这一条从"建议"升级成闸门，措辞不查（`无 p 或 HR` / `未列p或HR` / `没给 p 值或 HR` 都算），只查事实有没有落到交付物里。

「研发公司是否上市」只用 `listed_company` 表达（见 Step 5B）：它回答"谁在做这个药"，不含任何价格。v0.8 时期把当日行情塞进 `stock` / `reaction`，结果是"没查到涨跌"被读成"没上市"、板块 beta 被读成对这条摘要的反应，两件事一起错，所以整层移除。

### Step 7 — 写报告并交付

交付物是 **`/workspace/output/report.md`**（`watchlist.json` 是它的数据底稿，一起留着）。报告是 Markdown + 顶部 frontmatter，宿主靠 `skills` 数组决定用哪个布局渲染：

```markdown
---
skills: [conference-result-triage]
title: ESMO 2026 临床结果推荐阅读清单
date: 2026-10-23
lang: zh-CN
---

# ESMO 2026 …

## 早期机会提示（10）
- **<title>**（<drug> / <target> / <phase> / <presentation>）
  报告了什么：<summary>
  推荐理由：<why>

## 重磅 II/III 期（10）
…

## 失败的研究（10）
…

## 覆盖与边界
- <coverage_notes 逐条>
```

硬规则：

- `skills` **必须是非空数组**，且只写**这一回合真的用过**的 skill。`conference-result-triage` 是必须项（它是产出这份清单的那个 skill）；没有实际调用的 skill 一个都不许写——宿主会拿它选主题，写错就是骗下游。
- **不要用旧的业务字段 `type` 标识结果**（`type: 临床结果推荐` 这种）。宿主不再认它，写了也只是多一个不生效的键。
- `date` 用 `YYYY-MM-DD`；`lang` 写实际语言（`zh-CN` / `en`）。
- **引用机制可选，但声明了就必须对得上**：`citations: /workspace/output/citations.json` 里的键必须与正文的 `{{ref_N}}` **双向一一对应**（正文有 N 就必有 `ref_N` 条目，反之亦然），每个条目要有 `title` + http(s) `link`。平台内拿不到摘要原文链接，**没有任何可引用的外部来源时就不要写 `citations` 这一行，也不要在正文里留 `{{ref_…}}`** —— 编一个引用比不给引用糟得多。
- 正文**只写内容**，标题/链接/日期这些元数据留在 `citations.json`，不要在正文里重复贴 URL 列表。
- 一次请求只交**一套**最终产物（除用户明确要多语言版本）；不要在报告里同时放中英文两份清单。
- `report.md` 和 `watchlist.json` 用 `write_file(overwrite=True)` 覆盖写。

`present_artifact` 指向 `/workspace/output/report.md`。这是唯一终端动作，不要改成把 JSON 或 Markdown 全文贴进对话。

## Deliverable schema

```json
{"conference": "ESMO 2026", "count": 30,
 "coverage_notes": [
   "data_type 按摘要正文判断首次/更新/亚组，判不出的写「未判定」，不猜。",
   "约一半记录没有 p 或 HR，同一试验常拆成多篇；本清单不是会议书全覆盖。"
 ],
 "cards": [
  {"esid": "24_37_p_...", "abstract_id": null, "lba": true, "manual": null,
   "bucket": "pivotal", "tag": "LBA",
   "score": 78,
   "score_parts": {"evidence_strength": 26, "effect_size": 22,
                   "clinical_impact": 20, "novelty": 4, "readout_maturity": 6},
   "title": "…", "summary": "…", "why": "…",
   "drug": "…", "target": "…", "indication": "…",
   "phase": "Phase III", "presentation": "Late-breaking Oral",
   "listed_company": {"name": "…", "ticker": "…", "exchange": "…",
                      "source_url": "https://…"},
   "promoted": "web"}
]}
```

- `coverage_notes` 是**必填**的字符串数组，上面两条声明各至少一条；`check_cards.py` 会按语义（不是字面措辞）校验它。
- `esid` 是结果记录 id（用户要的"对应的结果id"）；`abstract_id` 是会议摘要号，平台内**恒为 `null`**（见 Step 3），有外网补库时才有值。
- `score` / `score_parts` 是判读结论（Step 4 给的分），不是脚本算的；总分只用来决定阅读顺序，`why` 里不出现分数。
- `why` 是**价值判断**（2–4 句、≥60 字），不是 `summary` 的改写：它要回答"这项研究为什么重要"，而 `summary` 回答"报告了什么"。
- `listed_company` **每张卡都有这个键**：上市填 `{name, ticker, exchange, source_url}`，未上市/查不到填 `null`。`null` 是"查过、没有"，不是"没查"。**该字段不含价格**——`stock` / `reaction` / `change_pct` 等键一旦出现，`check_cards.py` 直接判失败。
- `promoted` 只在**联网终选把池子外的记录提进来**时出现，值是 `"web"`；这类卡片必须能对上 `work/rows.json` 的 esid。
- `manual` 是生产方式标记（人工核对 / 流水线抽取），**不是**推荐等级。平台内**恒为 `null`**（`featured` 不可选），`check_cards.py` 会拒绝把它改成 `true`/`false`。
- 路径固定：交付物 `/workspace/output/report.md`，数据底稿 `/workspace/output/watchlist.json`（`check.py` 与宿主都按这两个路径取，改名即断链）。同一工作区复跑就覆盖。
- `write_file` 一律带 `overwrite=True`，包括首次写入。

## 两个必须写进清单的诚实声明

1. **`data_type`（首次 / 更新 / 亚组·二次分析 / 未判定）**。会议摘要有大量"长期随访""post-hoc 亚组"，不是新数据。判不出来写「未判定」，**不要猜**。
2. **覆盖边界**。`summary` 里只有约一半记录带 p 或 HR；同一试验常拆成多篇。清单不是全覆盖，别让读者以为是。

## Anti-patterns

- ❌ 在本地/工作区直连 Elasticsearch 拉表。ES 侧没有 `lba` 列，v0.2 因此整类漏掉 12 条 Presidential LBA。
- ❌ 用一次宽字段调用拉全场。超过 ~6 MB 会静默截断成 458/1097 且 `ok: true`，必须走 `plan_slices.py` 分片。
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

- **v0.9** — **删掉整个行情层，并把交付物改成带 `skills` frontmatter 的 Markdown 报告**。①**行情移除**：`reaction` / `stock` / `excess` / `fetch_quotes.py` / `work/web/quotes.jsonl` / `check_cards.py --quotes-evidence` / 事实项 `A-F7` 全部删除。依据是重算而不是偏好：按每条摘要自己的披露日重算后 **24 条行情里 18 条落在所属板块基准的 ±0.6% 内**（那个数字是 beta），同一公司多张卡拿同一个数字（MRK 8 张卡都是 −3.83%）。`listed_company` 保留为纯身份字段 `{name, ticker, exchange, source_url}`；新增**防回潮闸门**（`check_cards.py` + 事实项 `A-N1-no-price-claims`，双 mutation）：任何卡片再出现 `stock`/`reaction`/`change_pct`/`excess_pct`/`bench_change_pct`/`price_source` 即判失败。②**对齐 chat 联动约定**（《产品经理使用 Skill 的通用约束》）：交付物从纯 JSON 改为 **`/workspace/output/report.md`**（YAML frontmatter：`skills` 非空数组且含 `conference-result-triage`、`title`、`date`、`lang`；有引用时加 `citations: /workspace/output/citations.json`），正文只写 `{{ref_N}}`，标题/链接/日期只进引文文件，**双向一一对应**；不再用业务字段 `type` 标识结果。`present_artifact` 指向 `report.md`。新增事实项 `A-C2-report-frontmatter`（双 mutation：用 `type` 顶替 `skills` / 正文 `{{ref_1}}` 无对应条目）+ NEG「声明引文且对得上仍绿」。**不带引用是合法的**（平台内拿不到摘要链接，编一个就是造假），闸门只查"声明了就必须对得上"。事实层 24 → **25 条 fail + 1 warn**，NEG 7 条不变。
- **v0.8** — **`reaction` 从自由短句变成带口径的结构化对象**。起因是一条真实提问：「怎么只查到了股票代码，没有对应的事件日增长幅」。复盘 e2e6：108 次工具调用里 **29 次 `web_fetch` 全落在公司 IR 落地页**（`merck.com/investor-relations/stockholder-services/` 这类只有代码与股东服务的页），`web_search` 一次没调，28 张卡一个涨跌幅都没有。①**给出端点**：东财 kline `push2his.eastmoney.com/api/qt/stock/kline/get?secid=<mkt>.<code>&…` 返回纯 JSON（`klines:["2026-10-23,145.270"]`），`web_fetch` 直接可读，附 secid 前缀表（105/106/107/116 补零 5 位/155）与 `rc:100`/`rc:102` 语义；检索改查「`<ticker> 收盘 <日期> 涨跌幅`」（deepseek 源直接给券商页数字，bocha 源常给过期快照）。②**口径钉死**：涨跌幅 = **该市场早于会议首日的最后一个收盘 → 该市场 ∈ 会议窗口的第一个收盘**，`from_date/to_date/basis` 必须印进 JSON；**不许说成「因为这条摘要涨了 X%」**（e2e7 同一批 30 张卡里 MRK −1.34%、LLY −2.54%，板块整体在跌，这个对照本身就是信息）。③**基准日按市场各自取**：各市场休市日不同，统一成一个日历日就会算错；会议首日必须真的查过（ESMO 2026 = 10-23 至 10-27，Madrid）。④**不覆盖就留空**：SIX（Roche/Novartis）东财不覆盖，`reaction` 省略、不许拿 OTC ADR `RHHBY` 顶替 `ROG.SW`。⑤**可审计**：取数结果落 `work/web/quotes.jsonl`，`check_cards.py --quotes-evidence` 验「涨跌幅能否由两个收盘算出」+「能否逐条对上证据」，新增事实项 `A-F7-reaction-traceable`（fail，双 mutation：涨跌幅篡改 / 证据文件缺失）+ NEG「完全不印 reaction 仍绿」（增强项不否决清单）。⑥**本地预计算**：`scripts/fetch_quotes.py --meeting-start` 一次算完（沙箱无网，只能在 WSL 侧跑），`make_cards.py --quotes` 折进 `listed_company`。⑦顺手修掉一个真 bug：占位符扫描原来扫 `json.dumps(card)`，于是**任何把嵌套对象放最后一张卡都会因字面量 `}}` 被判泄漏**，改成只扫叶子字符串。事实层 23 → **24 条 fail + 1 warn**，NEG 6 → **7**。
- **v0.7** — 三道改动，都是「清单自己长出来的问题」。①**两段收敛**：机器短名单仍是每桶 15 / 全场 45，但交付清单收成**每桶 10 / 全场 30**（无上限的清单不再是阅读清单），中间插一道**联网终选**（每桶 ≥6 次检索，证据落 `work/web/<bucket>.jsonl`）；允许把机器筛掉但外部热议的研究提上来，条件是它在 `rows.json` 里、且卡片标 `promoted: "web"`、`why` 说明为什么破格——开门，但能查账。②**`why` 从标签变判断**：≥60 字、2–4 句，按「未满足需求 → 这次数据的定位 → 对格局的影响 → 局限」铺开，**不许复写 `summary`**；原来那种「报告了主要终点读数」等于没写。③**新增 `listed_company`**：这类读数披露当天常常就是股价的重定价日，每张卡都要这个键，上市填 `{name,ticker,exchange,reaction?,source_url}`、未上市或查不到填 `null`（`null` 是「查过、没有」）。踩过的坑：平台的 `web_search`（部分模型显示成 `web.run`）有**双重开关** —— 项目能力 `web=true` **且** 回合带 `enable_web=true`，缺一个就静默不可用，模型会一路编；发现工具不在工具表里必须停下让用户开联网。事实层 19 → **23 条 fail 项 + 1 warn**（新增 `A-P5-why-depth` / `A-F5-listed-company` / `A-F6-promotion-traceable` / `A-W1-web-evidence`，各配 mutation + 5 条 NEG）。**首次端到端（`cards-e2e5`）零交付**：1097 行取数、592 条判读全过，但 `web_fetch` 打开一个 IR 页失败后模型把「检索查不到」当成中止条件，写"暂未交付最终 JSON"就结束回合。所以三处文档补上**联网层失败只降级、不中止**：换词换源再试 → 仍不行就按判读分收敛、`listed_company` 全 `null`、`coverage_notes` 写明「联网核实未完成」→ 照常交付；`A-W1` 同时开了这条唯一例外通道（声明可用即通过，但清单必须存在）。第二次端到端（`cards-e2e6`）交付成功：1097 行 → 592 条判读 → **pivotal 10 / failed 10 / early 8**，26 行检索证据（18 行带 URL），`listed_company` 26/28 填实，`facts 23/23 -> PASS`。
    同日 `A-W1` 又修了一次：原来要求"每条记录都有 URL"，把"检索执行了但没结果"这种如实记录的检索判成漏证（`cards-e2e6` 就因此先假红）；现改成"总行数 ≥6 且带 URL 的行 ≥6，无 URL 的行必须写 note"。
- **v0.1** — 首版，ESMO 2026 全量实跑（467 候选 → 30 条）。
- **v0.2** — Results 不截断 + 会议摘要库并列数据源 + 报告形式加权 + 人群难度分档；候选 532，evidence 逐字 100%，专家 7 条 keep 3/7 → 5/7。
- **v0.3** — 改为平台内执行：取数唯一走 MCP（`pull_results.py` 两阶段切片），补 `clinical_result.lba`（v0.2 漏选导致整类 LBA 丢失），`PRESENTATION_RANK` 修正（Presidential/LBA 不再被压到普通口头之下），会议库标题 join 补回 LBA 编号（57/57），交付物改为 `/workspace/output/watchlist.json` 卡片清单。候选 551（early 200 / pivotal 292 / failed 59）。
- **v0.6** — 修一个会静默删数据的排除规则：`前瞻性研究` 原先在 `NON_TRIAL_SOURCES` 里，但平台没有独立分期列、`evidence_source` 就是分期来源，73 条 ESMO 2026 LBA 中 **16 条**该字段填的是研究设计 → VOLGA / KRASCENDO-1 / CLARITY-Gastric01 三场 Presidential 整类消失，而 `coverage: 1097/1097` 照样报满（覆盖按已取行算）。改为：只排除真实世界/回顾性/汇总分析/Not Applicable；分期缺失的行交 `bucket_of`，`lba` 为真进 pivotal，期别照实标「未声明」。候选 551 → **592**（pivotal 306 / early 200 / failed 86）。同时 `--limit-per-bucket` 降级为**试跑专用**（ESMO 2026 设 60 会切掉 SAFFRON 第 64 名），正式出榜必须全量判读。事实层加 `A-D4-lba-not-dropped`（19 条 fail 项 / 19 个 mutation）。
- **v0.5** — 判读评分卡：每条由模型给出 `score`(0–100) + 五维 `score_parts`，脚本只校验自洽（各维不超上限、相加等于总分），不做任何规则算分（`triage.py` 仍然是「mechanical shortlisting only」）。**每桶硬上限 15 条 / 全场 45 条**，超了 `check_cards.py` 直接 exit 3；定榜以判读分排序、可编辑覆盖但要在 `why` 说明。
- **v0.4** — 平台内实跑打通数据层。两条硬事实：①**工作区无网络**（in-cluster `Network is unreachable`、公网 DNS 全灭），取数改为「你调工具 → 结果落 `/workspace/tool_results/*.jsonl` → `pull_results.py --from-tool-results` 解析」；②**宽字段一次拉静默截断**（32 字段 + `meeting_tags` 只回 458/1097 且 `ok: true`），改为四阶段：id-only → `plan_slices.py` 切 150/片 → `esids` 逐片 → 合并 + `--expect-ids` 校验。实跑结果 `rows=1097 lba=73 coverage 1097/1097 candidates 551`（early 200 / pivotal 292 / failed 59），零网络、31 次工具调用、9 次落盘 18.4 MB、606 s。另修：`research_design.evaluation.text` / `base.abbreviation_label.text` 不在线上白名单（带上会让整次调用 `INVALID_INPUT`），`DEFAULT_FIELDS` 只用 32 个 `clinical_result.*`；`featured` 不可选 → `manual` 三态，平台内恒 `null`。
