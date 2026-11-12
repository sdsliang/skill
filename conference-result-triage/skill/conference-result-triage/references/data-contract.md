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
| `listed_company.ticker` | **只写代码本体**（`09966`），市场信息只在 `exchange`（`HKEX`）。`09966.HK` + `exchange=HKEX` 是同一事实印两遍，也让按「市场 + 裸代码」查询的路径无法复用；`check_cards.py` 直接拒 `.HK/.SH/.SS/.SZ/.T/.L/.DE/.PA/.AS/.SW` 后缀 |
| `listed_company` | ✅（可以是 `null`） | 上市：`{name, ticker, exchange, source_url}`，`source_url` 必须 http(s)；未上市/查不到：`null`。**缺键 = 没查**。**纯身份字段**：v0.9 起不含任何价格（见下一行） |
| 任何行情字段 | ❌ | `stock` / `reaction` / `change_pct` / `excess_pct` / `bench_change_pct` / `price_source` 在卡片或 `listed_company` 上出现即判失败（`A-N1-no-price-claims`） |
| `promoted` | 仅破格入榜 | 固定 `"web"` |
| `lba` / `manual` / `abstract_id` | ✅（值可为 null） | `manual`、`abstract_id` 在平台上恒 `null`，不猜 |

上限：**每桶 10 / 全场 30**（机器短名单 15/45 是另一回事，`work/shortlist.json`）。

### 6.5.1 行情为什么不在卡片里

v0.8 曾要求每张卡带 `listed_company.reaction`（会议窗口涨跌幅，含 `prev_close`/`close`/`basis`）并逐条对账。v0.9 整层删除，依据是重算：

- 按**每条摘要自己的披露日**重新锚定、并扣掉所属市场板块基准后，24 条行情里 **18 条落在 ±0.6% 内** —— 那个数字本来就是板块 beta，与这条摘要无关。
- 同一公司的多张卡拿到**同一个**数字：MRK 的 8 张卡全是 −3.83%，因为涨跌属于公司那一刻，不属于任何一条读数。
- 结果库里没有价格，价格也不是"该不该读这条摘要"的判断依据；把 beta 印成 reaction，读者会把它读成信号。

`listed_company` 保留（身份信息：谁在做这个药、能不能对上交易所披露），字段固定为 `{name, ticker, exchange, source_url}`。防回潮由两道闸门守着：`check_cards.py` 的 `PRICE_KEYS` 扫描，与事实项 `A-N1-no-price-claims`（mutation：`reaction` 回潮；NEG：只写身份字段仍绿）。

### 6.5.2 结果本身怎么被识别（`report.md`）

交付物是 `/workspace/output/report.md`，`watchlist.json` 是它的数据底稿。报告顶部 frontmatter：

```markdown
---
skills: [conference-result-triage]
title: ESMO 2026 临床结果推荐阅读清单
date: 2026-10-23
lang: zh-CN
citations: /workspace/output/citations.json   # 仅当确实有可引用来源
---
```

- **`skills` 取代业务 `type`**：非空数组、只写这一回合真的用过的 skill（本 skill 必在其列）。宿主按它选渲染主题；未识别的 skill 由宿主报错或用通用布局，**不允许静默退回普通 Markdown**。为了命中主题而编一个没执行过的 skill 名，是把下游骗到底。
- `title` / `date`（`YYYY-MM-DD`）/ `lang` 必填。
- **引文与正文分离**：正文只写 `{{ref_N}}`，`title`/`link`/`date` 只在 `citations.json`；键集与正文标记**双向一一对应**，任一侧缺项即失败。路径必须以 `/workspace/output` 开头。
- **没有可引用来源就不写 `citations`、也不留 `{{ref_…}}`**（平台内拿不到摘要原文链接，编一个引用比不给引用糟）。
- 一次请求一套最终产物（除明确要求多语言）。

审计落在事实项 `A-C2-report-frontmatter`（mutation：用 `type` 顶替 `skills` / 正文 `{{ref_1}}` 无对应条目；NEG：声明引文且双向对得上仍绿）。

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
| `drug` / `target` / `moa` | 结构化表常缺；ESMO 2026 分别 1954 / 1797 条有值 |
| `abstract_release_date` / `meeting_date` / `url` | 时间线与引用 |
| `session_type` | 报告形式（也可从 `abstract_id` 后缀直接得，更稳） |

**注意**：会议摘要库没有 `study_results`、没有 `evidence_source`、没有 `evaluation`。所以它只能**补充**，不能**替代**结构化表的分桶依据。

> 这些是**样例产物**，不是随 skill 发布的固定答案；换会议必须重跑。
