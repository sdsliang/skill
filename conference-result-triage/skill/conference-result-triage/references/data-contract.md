# 数据契约（平台内执行版 v0.3）

## 0. 在 TS 上唯一允许的取数方式

**平台工作区没有网络**（`pitfalls.md` §21：in-cluster 端点 `Network is unreachable`、公网 DNS 全灭、`env` 无 MCP 端点），**且宽字段一次拉会静默截断**（32 字段 + `meeting_tags` 实测只回 458/1097 行，`ok: true` 无报错）。所以平台内是四阶段：

| 阶段 | 谁做 | 动作 | 产出 |
|---|---|---|---|
| A | 模型 | 调工具：`meeting_tags="ESMO 2026"` + `selected_fields=["clinical_result.extra_esid"]` | 全量 id（≈50 KB，不截断） |
| B | 脚本 | `plan_slices.py --ids-from /workspace/tool_results --size 150 --out-dir /workspace/work/slices` | `slice_NN.json` + `_all_ids.txt` |
| C | 模型 | 每片调一次工具：`esids=<该片数组>` + `selected_fields` = `--list-fields` 输出 | 每片一个 dump |
| D | 脚本 | `pull_results.py --from-tool-results /workspace/tool_results --expect-ids …/_all_ids.txt --out /workspace/work/rows.json` | `rows.json` + 覆盖率 |

落盘格式：`data` 是 list 时一行一个 row（JSONL），键就是 `clinical_result__id` / `clinical_result_lba` 等返回键，**无需映射**。dump 在 **turn 结束时清除**，必须同 turn 解析。

**字段名纪律**：只允许 `clinical_result.*`。线上白名单**没有** `research_design.evaluation.text` / `base.abbreviation_label.text`，带上任一个都会让整次调用 `INVALID_INPUT: Invalid fields selected`（一个坏名字废掉整片，不是只废一列）。对应值已由 `clinical_result.evaluation` / `clinical_result.abbreviation_label` 提供。

**两个必然为 `null` 的字段**：`featured` 不在白名单（且 `TEST_execute-sql` 无法绑定项目）→ `manual=null`；`abstract_id` 平台内不存在 → `null`。

直连模式（不带 `--from-tool-results`）只在本地/有外网时可用：`--conference "ESMO 2026"`，走 `MCP_PHARMCUBE_ENDPOINT_URL`（默认 `http://172.17.26.74:30080/mcp/`）+ `PHARMCUBE_MCP_APP_KEY`，内部自己完成 A/B/C/D（`esids` 切片，`DEFAULT_SLICE=120`）。

## 1. 直连调试入口（仅排查，不是 skill 的数据路径）

```
POST {TS_BASE}/api/tools/debug
Authorization: Bearer $TS_TOKEN
{
  "name": "pharmcube-query-clinical-result-with-params",
  "mcp_server_id": "pharmcube",
  "arguments": {"meeting_tags": "ESMO 2026", "selected_fields": [ ...见下... ]}
}
```

- `meeting_tags` **精确匹配**（不是模糊搜索），写错得到空集。
- 同一试验会按 arm / endpoint 拆多行，**必须按 esid 去重**。
- `selected_fields` 用字段白名单的原样字符串（大小写敏感）；写错 `BadRequestException`，但**漏写不会报错**——这就是 `lba` 被漏掉的方式。
- `clinical_result__id` 不能作为 `selected_fields` 传入（`INVALID_INPUT`），但会在返回行里出现，就是 `esid`。

## 2. 字段清单（15 个，实跑可用）

```
_id
trial_abbreviation
paper_title
abstract_text
summary
key_evidence
evaluation
evidence_source
group_count
randomized
blinded
trial_control
indication_name
primary_endpoint_cn
study_results
```

说明：

| 字段 | 含义 | 坑 |
|---|---|---|
| `_id` | esid | 去重键 |
| `trial_abbreviation` | 试验简称 | **可能为空**，且同试验不同摘要可能写法不同；为空时去重退化为 esid |
| `abstract_text` | 完整结构化摘要（Background/Methods/Results/Conclusion，~2500 字符） | 复核的**主输入** |
| `summary` | ~300–400 字符英文摘要（无中文） | 缺失率极低（467/467 命中），作降级输入 |
| `key_evidence` | 「是/否」类枚举 | 不是 LBA 标记，别误用 |
| `evaluation` | `积极` / `-` / `不佳` / `终止` | **记录级**，同试验不同摘要可能不同 |
| `evidence_source` | `Phase I` / `Phase I/II` / `Phase II` / `Phase II/III` / `Phase III` / `Phase IV` / `前瞻性研究` / `回顾性研究` / `真实世界研究` / `Not Applicable` / `汇总分析` | **这是试验期别的唯一来源**；注意它偶尔填的是研究设计而非期别（73 条 LBA 里 16 条如此），缺期别**不等于**非试验，见 `screening-rules.md` §1.1.1 |
| `group_count` | 样本量 | 展示用，不作门槛 |
| `randomized` / `blinded` / `trial_control` | 设计属性 | 缺失较多，只能作佐证 |
| `indication_name` | 适应症列表 | 列表，不是字符串 |
| `primary_endpoint_cn` | 主要终点（中文） | 列表 |
| `study_results` | 臂级终点行（见下） | 只在"详情拉取"里返回；lite 拉取常为空 |

## 3. `study_results` 行结构

```
arm_type, endpoint_type, endpoint_label, endpoint_attribute,
result, compare_result, result_unit,
p_value, outcome_p_value, hazard_ratio, hazard_ratio_ci, odd_ratio, relative_risk
```

实测分布（ESMO 2026，3445 行）：

- `endpoint_attribute`：有效性 1717 / 安全性 1475 / QOL 130 / PK-PD 120 / 空 3。
  → **取疗效信号前必须过滤掉安全性行**，否则 `Grade≥3 TEAE 44.6%` 会被当成疗效。
- 只有约 5–6/10 行带 `p_value` 或 `hazard_ratio`；多数结论只能来自 `abstract_text`。

## 4. 两段式拉取（省额度）

1. **lite 拉取**：只拉元数据（不含 `study_results`），用于分桶。ESMO 2026 → 988 esid。
2. **详情拉取**：只对进入复核的 esid 拉 `study_results` + 全文，每批 25 个 esid。

`scripts/triage.py --require-detail` 对应这个两段式：先在 lite 池里排名，再只对带 `study_results` 的记录重排。

## 5. 额度与时间

- 单次 `meeting_tags` 全量拉取 ≈ 1 s、~1300 行。
- 详情拉取：149 esid → 212 行 → ~3.7 MB。批量 25 个 esid 一轮，别一次塞几百个。
- 不要为了"确认一个数字"重复全量拉取；把结果落 JSON 再复用。

## 6. 本仓库已有的实跑产物

| 文件 | 内容 |
|---|---|
| `dist/esmo2026-judgements.csv` | 467 条逐条判定（含 data_type / key_numbers / reason） |
| `dist/ESMO2026-watchlist.csv` | 30 条定榜 |
| `dist/ESMO2026-watchlist.md` | 三桶报告 |

## 6.5 交付卡片的字段契约（v0.9）

每张卡（`output/watchlist.json` → `cards[]`）：

| 字段 | 必填 | 说明 |
|---|---|---|
| `esid` | ✅ | 临床结果记录 id；池子外的记录只有在 `promoted="web"` 时才允许出现，且必须在 `work/rows.json` 里 |
| `title` / `summary` | ✅ | `summary` 至少要有一个带单位的数字 |
| `why` | ✅ | **判断**，≥60 字、2–4 句；不许复述 `summary`；不写分数 |
| `score` / `score_parts` | ✅ | 模型判读；五维各不超上限且相加等于总分 |
| `tag` | ✅（`""` / `"LBA"`） | 只表达"是不是 late-breaking"。**v0.13 起 `is_recommand` 不写成徽章**：标星只决定桶内位置，`tag="推荐"` 直接判失败 |
| 公司代码字段 | ❌ | `listed_company` / `ticker` / `exchange` 在卡片上出现即判失败（`null` 也算）。v0.13 删了这一层：身份写正文散文，代码属于行情源 |
| 任何行情字段 | ❌ | `stock` / `reaction` / `change_pct` / `excess_pct` / `bench_change_pct` / `price_source` 出现即判失败（同一闸门 `A-N1-no-market-claims`） |
| `promoted` | 仅破格入榜 | 固定 `"web"` |
| `abstract_id` | ✅（值可为 null，但**有值必须照抄**） | 来自 `clinical_result.abstract_id`（v0.12 起请求）。必须与 `work/rows.json` 逐字一致：rows 有值而卡片空 / 值与 rows 不同 / rows 无值而卡片凭空填，三种都判失败。空值只允许出现在 rows 本身为空时 |
| `is_recommand` | ✅（**三态**：`true` / `false` / `null`） | 来自 `clinical_result.is_recommand`，**逐态照抄**：`是`→`true`、`否`→`false`、`null`→`null`。**`null` 不是 `false`**（v0.14 修正）：平台语义里 `否` = 不推荐、须在会议解读时排除，所以把空列印成 `false` 等于伪造一条排除指令——R14 的 ADA 2026 就是这样把 191/191 条空值全印成了 `false`。必须与 rows 完全一致（`A-P8-recommand-tristate`）；标星卡的**位置**置顶，**标签不加**（v0.13） |
| `lba` / `manual` | ✅（值可为 null） | `manual` 在平台上恒 `null`，不猜 |
| `phase` / `phase_inferred` | ✅ | `phase` 照抄记录（跨领域会议常为 `""`）；`phase_inferred` 只在期别缺失、由设计定桶时非空，取值固定三种（`随机化对照（按设计判定）` / `平行/交叉对照（按设计判定）` / `单臂或未标注设计（按设计判定）`）。**推断值不许写进 `phase`** |

上限：**每桶 10 / 全场 30**（机器短名单 15/45 是另一回事，`work/shortlist.json`）。

排序键是 **`(is_recommand, -score)`**：标星卡在桶内置顶，同类内按判读分降序。`is_recommand` 不进 `score_parts`、不改 `score` 的值 —— 它决定"读不读"，判读分回答"有多强"。

降序是**交付前硬闸门**（v0.14）：`check_cards.py` 按 `(bucket, is_recommand)` 分组逐组检查分数非增。R14 的 pivotal 是 `83,80,80,78,78,76,76,71,73,71` —— 其它闸门全绿，只有读者一眼能看出第 8/9 张反了，所以这条必须在交付前拦，而不是只靠事后 `A-P4`。

同一 `trial_abbreviation` 最多 **2 席**（v0.14）：第三个席位必须在 `editorial_overrides` 里写明理由，否则 `check_cards.py` 与 `A-P9-trial-seats` 都判失败。散文里的「同机制 ≤2」管不住「一个试验拆成主结果 + 亚组 + 安全性三篇」。

### 6.5.0 期别缺失要显式交付，不许静默丢

`bucket_of()` 在 v0.10 起对没有期别的记录按研究设计定桶（`screening-rules.md` §1.1.2）。这带来一个必须写进交付物的诚实声明：

- 卡片正文印「期别未标注（按设计判定：随机化对照）」，不印 `Phase III`；
- **`phase` 一栏不印设计词**（v0.14）：`evidence_source` 写「前瞻性研究」「单臂研究」时，`phase_of()` 保留原值供排除判断，`phase_label()` 返回空并把依据放进 `phase_inferred`。ESMO 2026 曾有 7 张卡在 `phase` 位印着「前瞻性研究」，既像期别又顶掉了推断依据；
- `coverage_notes` 里必须有一条说明**这批记录的期别是推断的**、依据是什么，例：`本次会议 51% 的记录未填期别，按研究设计归档（随机化对照→重磅、单臂→早期），phase_inferred 字段逐条标明；这不是策展期别`。

没有这一条时，读者会把 164 条候选误读成「都有期别的 164 条」，而实际只有 41 条有。

### 6.5.1 行情为什么不在卡片里

v0.8 曾要求每张卡带 `listed_company.reaction`（会议窗口涨跌幅，含 `prev_close`/`close`/`basis`）并逐条对账。v0.9 整层删除，依据是重算：

- 按**每条摘要自己的披露日**重新锚定、并扣掉所属市场板块基准后，24 条行情里 **18 条落在 ±0.6% 内** —— 那个数字本来就是板块 beta，与这条摘要无关。
- 同一公司的多张卡拿到**同一个**数字：MRK 的 8 张卡全是 −3.83%，因为涨跌属于公司那一刻，不属于任何一条读数。
- 结果库里没有价格，价格也不是"该不该读这条摘要"的判断依据；把 beta 印成 reaction，读者会把它读成信号。

v0.13 把那一层剩下的代码也删了（`listed_company` / `ticker` / `exchange`）。判断理由和行情同源：复核页上 `AZN · NASDAQ` 这样的 chip 被读成的仍是"这只股票怎么样"，读者的注意力从读数挪到市场；而"谁在做这个药"用正文里的公司名就能说清，不需要交易所身份声明。附带收益是不再逐卡查交易所页，检索轮次约省 1/3。

防回潮由两道闸门守着：`check_cards.py` 的 `PRICE_KEYS` + `COMPANY_CODE_KEYS` 扫描，与事实项 **`A-N1-no-market-claims`**（三条 mutation：`reaction` 回潮 / 裸 `ticker` 回来 / 整个 `listed_company` 回来；NEG：公司名写进正文散文仍绿）。

### 6.5.3 交付 JSON 的顶层还有两个键

| 键 | 谁写 | 内容 |
|---|---|---|
| `coverage_notes` | 模型（`plan.json` 顶层） | 两条诚实边界（`data_type` 未判定 / 摘要无 p 或 HR 或覆盖不全），v0.10 起第三条（期别是按设计推断的） |
| `editorial_overrides` | 模型（`plan.json` 顶层） | 每桶里被舍弃的 `keep` 比入选卡最低分更高时的理由清单：`[{"esid","reason"}]`，`reason` ≥10 字 |

两个键都由 `make_cards.py` 从 `plan.json` 原样搬进 `output/watchlist.json`，不要渲染完再手改。

`editorial_overrides` 为什么必须是交付物的一部分：桶内榜单的默认规则是**按判读分取前 k**。E2E #11（EASL 2026）实际交付里，pivotal 桶出现「入选 35 分 / 舍弃 85 分的 PBC 三期」，而当时 `A-P4`（桶内降序）、`A-P2`（五维相加）都是绿的 —— 那两条只证明「排序整齐、分数自洽」，证不了「该选的那条被选了」。把理由写进 JSON，取舍才是可复核的；写在聊天回复里，下个月读 JSON 的人看不到。

### 6.5.4 `is_recommand` / `abstract_id` 的来源与三态（v0.12）

两个字段都在 `clinical_result.*` 白名单内，走同一条 `with-params` 通道：

| 字段 | 实测覆盖 | 语义 |
|---|---|---|
| `clinical_result.abstract_id` | ESMO 2026 1097/1097 · ASCO 2026 1648/1648 · AACR 2026 288/288 | 会议摘要号（`LBA7` / `1029P`）。读者按它去摘要册查，**写错比留空更坏** |
| `clinical_result.is_recommand` | ESMO 2026 **1096 null + 1 `是`**；ASCO 2026 / AACR 2026 / ESMO 2025 / ASCO 2025 全 0 | 数据方标的「必读」位。稀疏是常态 |

两个字段必须**逐字写进 `selected_fields`**：少写一个不报错、不告警，只是静默缺列，然后卡片一路 `null` 到底（`abstract_id` 就是这么被误判四个版本的）。`pull_results.py` 已经在 `DEFAULT_FIELDS` 里带上它们，并在汇总行打印 `is_recommand=…` / `abstract_id=…`，缺列时打 WARNING。

`pool.json` 顶层记录 `recommand: {"flagged": N, "column_present": bool}`，用来区分三种状态：

- `flagged > 0` → 那些行是**强制位**：必上榜、桶内置顶，`recommand_gate` 不可豁免；
- `flagged == 0, column_present == true` → 列拉了、没人标星。**必须在 `coverage_notes` 里说出来**；
- `column_present == false` → 这一列根本没拉，属于数据层缺陷，不能解释成"没有推荐"。

### 6.5.2 交付物就是清单本身（v0.15）

交付物只有 `/workspace/output/watchlist.json`。**没有 `report.md`**，因此也没有 frontmatter、`skills` 数组、`{{ref_N}}` 标记与 `citations.json`——这一整层在 v0.9–v0.14 存在，唯一的用途是让宿主把一份人读的 Markdown 渲染出来；而这份 skill 的产物是 30 张卡的判读结果，多渲染一份 md 只会让同一份判断有两个源（改了一个忘了另一个才是真风险）。

- `present_artifact` 指向 `/workspace/output/watchlist.json`（事实项 `A-T1-present-artifact`，mutation `m_present_md`：把路径写回 `report.md` 即判失败）。
- `check_cards.py` 不再有 `--report`；它只校验卡片与池子的自洽（**19** 条规则，见脚本 docstring；v0.16 新增第 19 条卡面标识）。
- `projects.json` 的 `deliverables` 只剩 `["output/watchlist.json"]`；本地 runner 的交付物断言按这个列表取值，不再硬回落 `output/report.md`（旧的回退会让一份合法交付永远红在 `report contains nonempty content`）。
- 同一试验的多条记录只出一张卡，但兄弟 esid 仍然合法：`triage.build_pools` 按 `trial_abbreviation` 去重，胜出条目带 `alias_esids`（被合并的 esid 列表）。卡面写哪一条都可以，成员资格按 `rows.json` 现场重算后两者都认。
- 一次请求一套最终产物（除明确要求多语言）。

历史账：`A-C2-report-frontmatter` 与「引文三键」曾是我们最贵的一次文档缺口径——v0.9 文档只写 `title`/`link`/`date`，ESC 2026 与 EASL 2026 两场 13 条引文全写成 `{title, link}`，交付后被平台闸门判失败。v0.15 的结论不是「把三键再写一遍」，而是这一层本来就不该存在。

## 6.6 交付后的回复上限（v0.17）

交付完的那条消息是**回执**，不是第二份交付物。硬上限（事实项 `A-T3-reply-terse`）：**≤700 字 · 表格行 ≤4 · 列表项 ≤6**。写三样：条数（含三桶分布）、产物路径、真实缺口（有才写）。

不写：逐卡复述、按桶重排的表、"拉了几刀 / 判读了几条 / 怎么筛"这类过程叙事；断言、覆盖说明、override 理由这些证据归 `verification.md` / `coverage_notes` / `editorial_overrides`，它们已经在交付物里或就在产物旁边。

账：v0.16 三场实跑的回执分别是 **3966 / 3461 / 2094 字**，全部逐卡列表（ESMO 2026 36 行表格）。同一个清单刚被 `present_artifact` 交出去，对话里再抄一遍只会产生**两份会各自漂移的副本**；而且这三场里读者真正要看的三件事（几条、在哪、缺什么）都被埋在表格后面。

## 7. 会议摘要库（`medicalMeeting`）—— **仅限本地/有外网，平台内不可用**

> **平台内（v0.3 主运行时）这条路走不通**：Tool Smith 的 35 个工具里没有会议摘要库，`mcp-openapi.pharmcube.com` 不在容器网络内，23 张可查表里也没有会议表。所以平台内**拿不到摘要号**，`abstract_id` 恒为 `null`，报告形式只剩 `clinical_result.lba`（`featured` 是人工/AI 生产标记，不是头条，见 `screening-rules.md` §3.1b）。下面这节只在本地跑或容器能出网时适用。

结构化结果表不是会议全本。ESMO 2026 实测：

| 指标 | 结构化结果表 | 会议摘要库 |
|---|---|---|
| 记录数 | 646（去重后 esid） | **5810** |
| 可用摘要（有 abstract_id + 全文 + 非 TiP） | 646 | **4103** |
| 覆盖关系 | — | 646 条全部能匹配上（title 归一后 646/646，零损失） |

调用形态（endpoint `https://mcp-openapi.pharmcube.com/mcp`，Bearer appkey）：

```json
{"name":"pharmcube-mcp-medicalMeeting",
 "arguments":{"conference":"ESMO 2026","pageNo":1}}
```

可选过滤：`abstractId` / `drugName` / `target` / `disease`。20 条/页，ESMO 2026 共 290 页，8 并发约 4 分钟。

**`conference` 留空 = 跨全部会议检索**，`scripts/meeting_pull.py --conference -` 即用于拉某药的历史读出一览。

返回字段（对 triage 有用的）：

| 字段 | 用途 |
|---|---|
| `abstract_id` | **报告形式来源**（后缀 `O`/`RO`/`P`/`eP`/`eTiP`）+ 唯一标识 |
| `abstract_text` | 全文（B 型裸标题格式：`Background` / `Methods` / `Results` / `Conclusions` 各占一行） |
| `title` | join 键（`NFKD` + 小写 + 非字母数字转空格） |
| `drug` / `target` / `moa` | **会议摘要库**有：ESMO 2026 分别 1954 / 1797 条有值。**结构化结果表没有这三列**（v0.16 复核：`ALLOWED_FIELD_NAMES` 里不存在 `clinical_result.drug` / `.target` / `.moa`，唯一沾药的是 `clinical_result.projects`，那是申办方/公司、v0.13 已禁用）——平台内要用只能走嵌套的 `clinical_result.arms[].drugs[]`，单条 ≈5.9 KB，只适合对短名单核对，不适合全量拉取。所以卡片上的药名/靶点是**判读者从标题与摘要里读出来的**，闸门见 `review-protocol.md §7A` 第 4 条 |
| `abstract_release_date` / `meeting_date` / `url` | 时间线与引用 |
| `session_type` | 报告形式（也可从 `abstract_id` 后缀直接得，更稳） |

**注意**：会议摘要库没有 `study_results`、没有 `evidence_source`、没有 `evaluation`。所以它只能**补充**，不能**替代**结构化表的分桶依据。

> 这些是**样例产物**，不是随 skill 发布的固定答案；换会议必须重跑。
