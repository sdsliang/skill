# 数据坑清单（实测，ESMO 2026 全量）

按"会不会让结论错"排序。

## 1. `clinical_result.lba` 必须显式写进 `selected_fields`（v0.3 修正：旧结论「全部为 None」是错的）

**现象**：字段确实存在，返回 `"LBA"` 或 null。ESMO 2026 共 1097 行里有 **73 行 `lba=="LBA"`，且 73/73 带完整 `abstract_text`**。但如果 `selected_fields` 里没列它，返回的记录就**没有这个 key** —— 不报错、不警告，看起来就像这批数据根本没有 LBA 一样。v0.2 因此把整类 late-breaking 当普通记录处理，12 条 Presidential 摘要（DeLLphi-305、SAFFRON、INTerpath-001、VOLGA …）全部漏选。

**后果**：不只是少一列。
- 拿不到 LBA，`PRESENTATION_RANK` 就把 late-breaking 层压到普通口头之下；
- 分桶的「只在会议摘要库里 ⇒ 只进 early」硬门会误伤 LBA（它们是最高证据档，不是首次人体数据）；
- 定榜时读者看不到任何 LBA 标记。

**处置**：
1. 取数固定用 `scripts/pull_results.py`（`DEFAULT_FIELDS` 已含 `clinical_result.lba`），不要手写字段集。
2. 建池后断言 `lba` 计数非零，为零就说明字段没取回来。
3. `lba` 是**布尔标记，没有编号**。编号（`LBA3`、`LBA57`）只在会议摘要库里，靠标题 join 补回（ESMO 2026：57/57 命中，见 `scripts/attach_abstract_ids.py`）。

**教训**：「某字段不存在」这个结论，必须先读完运行时 `selected_fields` 的 `ALLOWED_FIELD_NAMES` 全文再下。

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

**处置**：真实世界与回顾性**全部排除**，单独计数，明示在交付物里。但 `前瞻性研究` 这一档 **v0.6 起不再排除**——它是「真试验、分期没填」，详见 §11.1。

## 11.1 把「前瞻性研究」当非试验证据，整类删掉 16 条 LBA（v0.6 修复）

**现象**：`excluded_reason()` 的 `NON_TRIAL_SOURCES` 里有 `前瞻性研究`，理由是「非注册试验」。但平台没有独立的分期列，`evidence_source` 就是期别来源；**73 条 ESMO 2026 LBA 里有 16 条的该字段填的是研究设计**。

**后果**：VOLGA（LBA2）、KRASCENDO-1（LBA5）、CLARITY-Gastric01（LBA7）三场 Presidential 直接不进池，而 `coverage: 1097/1097` 依然报满——覆盖是按**取到的行**算的，不是按**该到榜上的研究**算的。外部热度对照里这 12 个 LBA 有 4 个查无此项，根因就在这里。

**处置**：黑名单只留「回顾性 / 真实世界 / 汇总分析 / Not Applicable / 其他」；分期缺失的行交 `bucket_of`，`lba` 为真则进 pivotal。回归断言在 `triage.py --self-test`（`unstated phase is not an exclusion` / `unstated-phase LBA is still pivotal`），事实层在 `evals/fact-check` 的 `A-D4-lba-not-dropped`（19 条 fail 项之一，带 mutation）。

**教训**：覆盖率的分子分母都来自同一份已取数据，所以它能自证一致却证明不了完整。**凡是「按值排除」的规则，都要拿会议自己的议程（LBA 名单）反查一遍。**

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

## 18. 宽字段整场调用会被 ~6 MB 响应体上限静默截断

**现象**：`query-clinical-result-with-params` 一个 1 字段调用（`clinical_result.paper_title`）能回全量 1097 行；换成 6 个字段，仍然 `ok: true`、`actual_result_count` 看着正常，但实际只回了约 500 行。35 字段的整场调用同样止步在 ~500 行。没有任何错误码、没有 truncated 标志。

**后果**：如果直接建池，会得到一个"看起来跑通了"的半场候选池——failed 桶和 late-breaking 桶尤其容易整段消失（它们在表里位置靠后）。这类错误不会在断言里报出来，只会在复盘时发现"某某研究怎么没进榜"。

**处置**：`scripts/pull_results.py` 固定两阶段——先只取 id（单字段，一次回全量），再按 `esids` 切片（默认 120 个/次）取全字段。**不要为了省时间把 slice 调到一次装下全场**；判定标准是返回行数，不是 HTTP 200。

## 19. `PRESENTATION_RANK` 层级倒置：late-breaking 被压到普通口头之下

**现象**：v0.2 的 rank 表把纯 `LBA<n>`（如 `LBA3`）当成 rank 3，普通口头 `1234O` 是 rank 1，于是 Presidential 级读数在池内排序里排到所有普通口头后面。

**后果**：池内顺序决定读的顺序，也影响定榜时"同等证据、谁先上"的判断。DeLLphi-305 / SAFFRON 这类会议头条因此在 v0.2 里根本没进候选池（叠加了 §1 的字段漏选），复盘时表现为"专家挑的 7 条里有 4 条我们没进榜"。

**处置**：层级改为 `Late-breaking Oral: 0` → `Oral / Late-breaking: 1` → `Rapid Oral: 2` → `Poster: 4` → `ePoster: 5` → `Unknown: 9`；纯 `LBA<n>` 与 `LBA<n>O` 都按 `Late-breaking Oral` 处理。`triage.py --self-test` 里有对应断言（`presentation_of("2041P")[1] > presentation_of("LBA3")[1]`）。

## 20. 平台内**没有摘要号**，且 `featured` 不是头条

**现象**：v0.2 把"摘要号后缀"当成最强先验写进规则、脚本和系统提示词。但真到平台内执行时，三个来源全都断：

| 想用的来源 | 平台实际 |
|---|---|
| `clinical_trial_result_structured.abstract_id` | **无此列**（111 列里只有 `lba` / `abstract_text` / `journal` / `featured` / `listing_display`） |
| 工具目录里的会议摘要库 | **无此工具**（35 个工具：pharmcube 12 / report 7 / sales-mcp 8 / TEST 4，没有一个含 meeting/conference） |
| `abstract_text` / `paper_title` 自带编号 | `abstract_text` 全部以 `#### Background` 开头；`paper_title` 无一以 `LBA` 开头 |
| 23 张可查表 | 无会议表 |

**更隐蔽的错**：v0.3 初稿发现 `clinical_result.featured`（`是`/`否`，100/1100）里前段几乎全是 Presidential LBA（PACE-LUNG、BEATcc、HERON-Lung01、OptiTROP-Lung06、TALENT、RASolute 302），就把它当成"编辑精选/头条"，加了一个 `Featured Late-breaking` 层（rank 0）排在普通口头之前。

**用户一句纠正**：`featured` 是**人工生产 / AI 生产**标记，没有别的含义。SQL 交叉验证完全吻合：

```sql
SELECT source, featured, count(*) FROM clinical_trial_result_structured
WHERE journal='ESMO 2026' GROUP BY source, featured;
-- np_clinical_conference 否 1000
-- np_result_conf         是  100
```

`featured='是'` **100/100 等于** `source='np_result_conf'`。Presidential 研究看起来富集，只是因为人工核对优先做了这些大研究 —— 因果方向反了：不是"头条所以 featured"，而是"人工核对了所以 featured"。

**后果**：把它当 tier 会让 100 条记录仅因为"生产方式"被排到所有普通口头之前，且这个排序无法被证据复核 —— 卡片上会写出一个没有依据的"精选"标签。

**处置**：

1. `presentation_of()` **完全不读** `featured`；平台内报告形式只剩 `clinical_result.lba`（73/1097，进池 51 条，其余 500 条诚实标 `Unknown`）。
2. `featured` 改名进池为 `manual`（bool），只用于卡片的生产方式标注（人工核对 / 流水线抽取），属于诚实声明的一部分。
3. `make_cards.py` 的 `_auto_tag()` 只认 `lba`，绝不再生成"精选"。
4. self-test 断言 `manual production does not create a presentation tier`，防这个错再长回来。
5. `abstract_id` 在平台内恒为 `null`，卡片照常输出该键，**禁止**编造编号。

**顺带一个 join 陷阱**：同一记录在 SQL 侧键是 `24_37_p_<hash>_1`，在 `with-params` 侧是 `nr_24_37_p_<hash>_1`（`source='np_result_conf'` 的那 97 条）。不剥 `nr_` 前缀，旁表只能匹配 1003/1097，剩下 97 条静默拿到 `featured=null` —— 也就是**人工核对的记录被误报成流水线抽取**。剥了之后 1100/1100 全中。

## 21. 平台工作区**没有网络**，但工具结果会自动落盘

**现象**：`pull_results.py --conference "ESMO 2026"` 在平台 chat 里第一次跑就 `urllib.error.URLError: [Errno 101] Network is unreachable`，退出码 1。模型当时判断「平台数据端点不可达」，于是停手不再建池。

**探针（容器内 `execute`）**：

```
1) env | grep -iE "mcp|toolsmith|endpoint"     →  空
2) /etc/resolv.conf                            →  nameserver 100.100.2.136 / 138
3) socket 172.17.26.74:30080                   →  OSError 101 Network is unreachable
   socket mcp-openapi.pharmcube.com:443        →  gaierror -3 Temporary failure in name resolution
   socket k8s-node-test-inner…:36773           →  gaierror -3
```

三条全灭 + 无端点环境变量 = **沙箱没有任何出网/内网能力**，不是路径写错、不是 key 缺失。`--web` 也救不了：web 工具（`web_search` / `fetch_url`）是**后端**执行的，不经沙箱 socket。

**根因（正经机制，不是 bug）**：平台把 MCP 工具结果**强制落盘**再喂给模型 —— `agent/capabilities/pharmcube_mcp.py` 调 `maybe_offload_tool_result(..., force_save=True)`，`max_chars=MCP_TOOL_RESULT_MAX_CHARS=20_000`；`data` 是 list 时序列化成 **JSONL**（一行一个 row，`file_extension=".jsonl"`），落在 `/workspace/tool_results/<exposed_name>/<call-id>.jsonl`，模型只看到 `content_preview()` 的 5 头 5 尾 + 提示 `The result … was too large to keep inline`。

所以平台内**取数 = 你调工具 + 脚本读 dump**，而不是「脚本自己联网」。整场 1097 行一次拉完 **0 上下文成本**——这反而是比 v0.3 直连模式更好的架构。

**处置**：

1. `pull_results.py` 新增 `--from-tool-results`（目录 / glob / 单文件，跨多次调用去重合并）与 `--flags-from`；`--conference` 直连模式保留给本地。
2. **dump 在 turn 结束时删除**（提示原文：`This file is cleared at turn end`），所以必须在同一 turn 内解析完，`rows.json` 才是持久落点。
3. 落盘是原样 row dict，键仍是 `clinical_result__id` / `clinical_result_lba`，**不需要任何字段映射**。
4. `KNOWN_ABSENT` 里钉住两个「要了但永远不返回」的字段（`clinical_result.extra_esid` 实际以 `clinical_result__id` 回来、`clinical_result.layer_factor` 被 SQL projection 丢掉），否则完整性检查会误报「请重跑」。

**教训**：脚本报「网络不可达」时，先分清是**这个环境没有网**还是**地址写错**。在平台里一律是前者；再去改 endpoint、加重试、换库都是白费一轮。反过来，`getent`/`socket` 三连探针 10 秒就能定性，比猜快得多。

**补记（同日实跑）**：落盘这条路走通后，**一次宽字段调用仍然拉不全** —— 32 字段 + `meeting_tags` 只落 458 行 / 6.4 MB，工具在服务端就截断了，且 `ok: true`。id-only 调用（`selected_fields=["clinical_result.extra_esid"]`）回全 1097，不受限。所以正解是**四阶段**：id → `plan_slices.py` 切 150/片 → 每片 `esids` 调用 → 合并 + `--expect-ids` 校验覆盖。

**第二个静默杀手**：`selected_fields` 里混进一个线上白名单没有的名字（`research_design.evaluation.text`、`base.abbreviation_label.text`），整次调用返回 `INVALID_INPUT: Invalid fields selected`、`data=null`，**一行都没有**——不是丢一列。判断法：`INVALID_INPUT` 里直接点名列出来，别猜；`clinical_result.evaluation` / `clinical_result.abbreviation_label` 才是线上名字。

## 22. `web_search` 有**双重开关**，缺一个就静默消失（v0.7 实探）

`web_search` / `web_fetch` 是**后端执行**的工具，不受沙箱无网影响 —— 但它们只在两个条件同时成立时才进入工具表：

1. 项目级能力：`capabilities_config.web = true`（`schemas/capabilities.py` 的 `CapabilityConfig.web`）；
2. 回合级开关：`POST /api/chat` 的 `enable_web = true`（UI 上就是"联网"按钮）。

实测过程：项目 `web=false` 时模型回答"当前没有 web_search"；`PATCH /api/projects/{id}` 把 `web` 改成 `true` 后，回合仍**不带** `enable_web`，模型依旧回答"没有这个工具"，而 `debug-history.json` 里 `web_search` 只出现在用户 prompt 和模型回复里、**零条工具定义** —— 说明工具确实没被提供，不是它不会用。

**代码层还要看一件事**：`agent/capabilities/web.py` 的 gate 是 `capability_config.web and deps.enable_web`；`settings.WEB_SEARCH_API_KEY` 为空时是**返回一条 message**（`WEB_SEARCH_NOT_CONFIGURED_MESSAGE`），不是隐藏工具。所以"工具表里没有它"= 开关没开，"有它但一调就报 not configured"= 服务端缺 key。两种情况要分开报。

**处置**：`toolsmith-publish run ... --web` 会带 `enable_web=true`（`run.json` 里能看到）。复盘时先看 `run.json` 的 `enable_web`，再看 `debug-history.json` 有没有 `web_search` 的工具定义，最后才怀疑模型。**发现工具不在工具表里，必须停下让用户开联网**，不许按常识继续写"据报道……"。

**顺带**：模型侧工具名可能显示成 `web.run`（同一个工具，入参 `query`/`queries`，返回 `sources` + `items[url,title]`）。按 `web_search` 或 `web.run` 任何一个写文档都不算错，但**报"没有 web 工具"前先确认自己开没开开关**。

## 23. `why` 会退化成 `summary` 的复写（v0.7 加闸）

症状：45 张卡里 `why` 写成「报告了 ORR 47.5%、mPFS 6.8 个月」，与 `summary` 前 20 字几乎相同。这不是措辞问题 —— 读者从 `summary` 已经知道了数字，`why` 的唯一职责是回答**这项研究为什么重要**（未满足需求、改变了什么、对后续研发的影响、局限）。判据落成两条机械规则：**≥60 字**（少于 60 字写不完一个判断）、**不许与 `summary` 互相包含前 20 字**（否则就是把数字换个说法）。评分不写进 `why` —— 分数是内部排序依据，露出来只会让读者去比大小。
