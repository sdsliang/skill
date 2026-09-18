# `evals/fact-check/` — 必含事实清单与离线打分器

给 `clinical-result-comparison` 补上 autoresearch 范式里唯一缺失的东西：**一个能自动判分的真值标量**。
`docs/autoresearch-iteration-plan.md` §9 定了两层指标，其中成本层（`calls` / `wall_s` / `tokens`）由
`toolsmith-publish run` 直接产出，而质量层原本只有「布尔门」（跑没跑完、有没有产物）。本目录把质量层
从布尔门升级为 `facts_ok / facts_total` 标量：**一份清单写明「这次 run 必须说出哪些事实」，`check.py`
对 run 产物逐条判定**，于是「改动是让它更好还是更坏」第一次有了可比数字。

## 文件

| 路径 | 作用 |
| --- | --- |
| `records/scenario-a.records.json` | 场景 A 的 ground truth：`POST /api/tools/debug` 对 2 个有效 esid 的真实返回（5 行 / `actual_result_count=5`） |
| `records/scenario-b.records.json` | 场景 B：1 个有效 + 1 个不可用 esid 的真实返回（3 行 / `actual=3`） |
| `scenario-a.facts.json` | 场景 A 清单：**42 条（41 条 fail 级 + 1 条 warn 级）**（O17 新增 `A-S2b-chart-or-reason` 后为 32 条中 31 条 fail；2026-09-17 原文优先规则新增 `A-P1/P2/P3` 后为 35 条中 34 条 fail；同日按源类细化新增 `A-P4` → 36 条中 35 条 fail；按「库内 `abstract_text` 即原文 + `src=1` 努力取 PMC 全文」新增 `A-P5` → 37 条中 36 条 fail；同日 L3（最深可得体即分析面）新增 `A-P6` → 38 条中 37 条 fail；2026-09-18 `R15` 发现模板规格句被照抄进交付正文，新增 `A-P7` → 39 条中 38 条 fail；同日 `R16` 显示同一规格句被**换了措辞**照样泄漏（「未发现原文与库内记录在同一指标、同一口径上的数值不一致」），新增 `A-P8` → 40 条中 39 条 fail；同日按用户口径「两种数值写法都行、只要自洽」把 `A-C4`/`A-C5`/`A-S9` 放宽为**符号无关**并新增 `A-S10-sign-convention-consistent` → 41 条中 40 条 fail；2026-09-18 修两个**假阳性**：`O19`（混合句被误判错配，`attribution` 加 subject 豁免）+ `O20`（主题式标题被误判，`A-T1` 由 `line` 改为 `shape`/`title_scope` 并改名 `A-T1-title-identifies-scope`）→ 41 条中 40 条 fail；2026-09-18 修 `O29`（`A-P6` 在真产物上**空转假绿**）并补上反向的 `A-P9-fulltext-cite-has-body` → **42 条中 41 条 fail**） |
| `scenario-b.facts.json` | 场景 B 清单：**12 条 fail 级 + 1 条 warn 级** |
| `check.py` | 离线打分器（纯标准库，不联网、不调用平台） |
| `mutations.py` | 负向对照 harness：证明每条清单项都能翻 FAIL |

## 用法

```bash
# 对一份已跑完的 run 目录判分（run 目录由 `toolsmith-publish run` 落在
# ~/.local/state/toolsmith-runs/<时间戳>-<tag>/）
python3 check.py --run ~/.local/state/toolsmith-runs/20260916-104943-v2-poll --scenario a
python3 check.py --run ~/.local/state/toolsmith-runs/20260914-174145-b2-refusal --scenario b

python3 check.py --run <dir> --scenario a -v          # 逐条打印
python3 check.py --run <dir> --scenario a --json out.json

# 证明清单本身有牙（需要上面两个 run 目录仍在；可用 MUT_RUN_A / MUT_RUN_B 覆盖）
python3 mutations.py
```

退出码：`0` = 全部 fail 级条目 PASS；`3` = 有 fail 级条目 FAIL；`4` = 输入不可用（run 目录/清单读不到）。
`warn` 级条目只报告、不影响退出码。

打分输出最后一行是标量：

```
SCORE scenario=a facts 41/41 warn 1/1 -> PASS
```

## 清单条目的写法

`scenario-*.facts.json` 的 `items[]`，每条必须有 `id`、`kind`、`severity`（`fail` 默认 / `warn`）、`evidence`。

| `kind` | 字段 | 语义 |
| --- | --- | --- |
| `present` | `surface`, `patterns[]`, `anchors[]?`, `min_count?` | 图案必须出现在该 surface 上；给了 `anchors` 时只认「锚点所在块」内的命中 |
| `absent` | `surface`, `patterns[]` | 图案不得出现（用于「不许把 5 行返回写成 5 条结果」「不许把 `+3.6%` 写成 `−3.6%`」这类反向事实） |
| `attribution` | `surface`, `pairs[{token, owner}]` | 有引注的句/单元格里，token 必须归属其 owner ref |
| `line` | `surface`, `line_regex`, `patterns[]` | 同一行（如 H1 标题）必须同时命中全部图案 |
| `sent_if` | `surface`, `if_regex`, `patterns[]` | **条件句规则**：某句命中 `if_regex` 时，该句必须同时命中全部 `patterns`；没有任何句子命中时自动 PASS（用于「只在真的发生时才约束」的规则，如原文与库内不一致） |
| `shape` | `op`, 参数 | 结构化断言，见下表 |

`surface` 取值：`report`（`artifacts/output/report.md`）、`citations`、`charts`（`artifacts/visualizations/*.json`）、
`answer`（对话答复文本）、`transcript`（整段轨迹）、`any`（report + answer）。

`shape` 的 op：`artifact_present` / `artifact_absent`、`glob_count`、`citations_keys_exact`、
`citations_entry_key_set`、`citations_matches_record`（对 ground truth record 逐字比，日期按 `YYYY-MM-DD`）、
`citations_distinct`、`chart_envelope`（`id` / `iframe_template` 形状 / `option.type` / `group` / `stack` /
`data_len` / `label` 非空 / `title` 非空）、`chart_values`、`chart_set_allowed`、`chart_or_reason`、
`no_verbatim_copy`、`title_scope`、`report_excludes_literals`、`no_rule_metastatement`、
`fulltext_fetch_is_named`、`cite_link_is_deepest`、`fulltext_cite_has_body`、
`sign_convention_consistent`（见下）。

### 可选出图与「不出图必须说明原因」（2026-09-17，O17）

定量主图是**可选**的（`chart-templates.md:91`：需 ≥2 条入选结果给出同一终点、同一口径、**可明确对齐的时点**的纯数值）。
所以清单不能用「必出 `endpoint-bar-1.json`」去要求场景 A——那是从 R8 那一份产物倒推出来的期望（O17），
R11 同输入不画图并写明理由反而被判 FAIL。改成三条相互配套的断言：

| 条目 | op | 语义 |
| --- | --- | --- |
| `A-S2-chart-set` | `chart_set_allowed` | 出的每一张图**文件名必须合法**（`endpoint-bar-*.json` / `endpoint-line-*.json` / `evidence-timeline.json`）、**禁止的图不得出现**（场景 A 跨试验 → timeline 前置条件不成立）、**定量图不得超上限**（1 张）。**空集合不算违规** |
| `A-S2b-chart-or-reason` | `chart_or_reason` | 有定量图 → 直接 PASS（图由下面两条管）；没有定量图 → 正文**必须明确写出不出图**（`required_groups`）**并**给≥1 条实质理由（`supporting_groups`） |
| `A-S8` / `A-S9` | `chart_envelope` / `chart_values` + `"optional_when_absent": true` | 文件在 → 照旧硬断言封套/数值；文件不在 → PASS 并注明由 `A-S2b` 兜底 |

**「required 组」是必须的**：只查「支持理由」会漏——跨试验报告天然写「跨试验」「时点不同」，那样删掉图不说话也能过。
对应的负向对照是 `M16 drop-chart-silent`（删 `endpoint-bar-1.json`，报告不动）→ 必须翻 `A-S2b`；
正向对照是「删图 + 写明原因」→ 仍 31/31 PASS（手动验过，见台账 O17）。

### 原文优先的四条 + 全文声明/落点两条（2026-09-17，任务「原文第一优先级」）

规则本身在 `skill/.../references/input-contract.md` *Evidence source priority*：esid 字段值是**加工抽取**，
原文是第一优先级，冲突时原文为准且必须双值写明。**第一步先读库内 `abstract_text`——实测它多数类就是原文**
（期刊摘要对 Europe PMC 归一后 0.992–1.000、会议摘要对 OpenAlex 0.991–0.999、通稿带线报日期首发行、
注册平台数值与 CT.gov API 逐位一致），所以默认不抓；**唯一例外是 `src=1` PubMed：即使已有摘要，也要走
`R6`（Europe PMC search 读 `pmcid`）→ `R7`（`{PMCID}/fullTextXML` 取 PMC 全文）**（抽查 100 条 56% 有 PMID；
平台侧实测 R7 4/5 成功、63–99 KB JATS 全文，单条 500 属记录级「未进 PMC/OA」）。其余源类
（`1` PubMed、`2`/`187` 登记平台、`37` 会议、`49` 新闻稿、`120` 补录、`245`/`398`/未列出）依旧按类决定是否值得花额度。清单只查
**可机械判定**后果，不查「有没有努力去抓」（那是成本层的事）：

| 条目 | kind / op | 语义 |
| --- | --- | --- |
| `A-P1-original-check-line` | `present` | 证据范围段必须有一行 `原文核对：` + 数字（复核条数/总条数） |
| `A-P2-divergence-shows-both` | `sent_if`（`if_regex=库内记录`） | 一旦出现「原文 vs 库内」的分歧表述，该句必须同时含 `原文`、`库内记录`、`{{ref_n}}`——防的是一侧静默降级。本轮没有分歧时自动 PASS |
| `A-P3-no-long-verbatim` | `shape` / `no_verbatim_copy` | `/workspace/sources/**` 里归档的抓取原文，不得有 ≥60 连续字符（去空白后）原样出现在报告正文；没抓任何原文时不触发 |
| `A-P4-original-check-names-route-and-class` | `shape` / `original_check_names_class` | `原文核对：` 那一行必须同时点名**取回路径**（PMID/DOI/登记号/registry API/**PMC 全文**/**库内正文即原文**）与**来源类或原因类**（`src=`、新闻稿/会议/登记平台/SEC/补录/库内正文，或抓取受限/无登记号或 DOI/该来源不公开/**无 PMCID**/**非 OA**）。防的是「原文核对：2/2 条已复核」这种空壳能一路通过；报告里没有该行时由 `A-P1` 负责，本条不重复计分 |
| `A-P5-fulltext-fetch-is-declared` | `shape` / `fulltext_fetch_is_named` | 只要 `/workspace/sources/` 下归档了**全文正文**（文件名含 `pmc<数字>`/`fulltext`，或前 4 K 字符含 `<article>`/`<sec>`/`<body>`），覆盖行就必须出现 `PMC<号>` 或「全文」。防的是「实际取了 PMC 全文，覆盖行只写 PMID」这种无法从交付物分辨的含糊（反过来声称取了全文而没取，由 `A-P9` 管）；未归档全文时不触发 |
| `A-S10-sign-convention-consistent` | `shape` / `sign_convention_consistent` | `values` 里那几个**被画进图**的量，在报告与图表里必须用**同一符号口径**：报告带负号而图表是正幅度（或反向）⇒ FAIL。口径本身不写死（`−13.9` 与「降低 13.9%」等价，用户 2026-09-18 定案），所以 `A-C4`/`A-C5` 用 `[\u2212-]?` 接受两种写法、`A-S9` 比绝对值；**自洽**这件事由本条守住。只比被画的量：点估计写「降低 13.9%」、CI 写 `-19.3～-8.5` 不算混用。图表不存在时不触发（可选图）。
| `A-P7-no-template-spec-in-report` | `shape` / `report_excludes_literals` | 报告正文**不得逐字出现模板的规格句**（`原文优先于库内加工字段` / `不静默取一侧` / `库内记录值`）。防的是「交付物里混入指令性文字」：`R15`（已发布 v1.6/1.0.7）的覆盖行照抄了模板括号外那句「原文优先于库内加工字段，不一致处同时写出原文值与库内记录值；」——模板已把那三句挪进 `[...]` 规格括号，本条为防回归。注意 `A-P2` 也会因该句含「库内记录」而报错，但它的诊断信息（缺 `{{ref_n}}`）指不到真正原因，两条各有用途 |
| `A-P6-cite-link-is-deepest` | `shape` / `cite_link_is_deepest` | 若 `/workspace/sources/` 下归档了**全文正文**，**它归属的那条 ref** 的 `link` 必须指向全文载体（白名单 `https://pmc.ncbi.nlm.nih.gov/articles/PMC<id>/` 或 `…/rest/PMC<id>/fullTextXML`），或至少带同一个 `PMC<id>`；未归档全文、或归档了但四条归位通道都归不到任何 ref 时不触发（其 `link` 仍逐字节取自 `full_article_link`）。归位方式与 `O29` 见下 |
| `A-P9-fulltext-cite-has-body` | `shape` / `fulltext_cite_has_body` | **`A-P6` 的反向**：`link` 一旦指向全文载体（同一份白名单）就必须有对应字节落在 `/workspace/sources/` 下（文件名或前 4 K 里出现同一个 `PMC<id>`）。`A-P6` 问「归档了 ⇒ 引用指对了吗」，本条问「引用声称读了全文 ⇒ 到底取了没有」；`link` 逐字节等于记录自带 `full_article_link` 时**不算深度声明**、不触发 |

| `A-P8-no-rule-metastatement` | `shape` / `no_rule_metastatement` | 报告里不得出现**关于规则本身的句子**：同时点名库内一侧（`库内记录`/`库内抽取`/`库内字段`/`库内值`）与「一致/不一致」、且通篇**没有数字**的句子即判 FAIL。真实分歧必带双值 + `{{ref_n}}`，所以「无数字」正好切开元话语与结论。`A-P7` 抓逐字回抄，本条抓**改写**——`R16` 的覆盖行写的是改写版（无值、无引用，读者拿不到任何信息），说明只靠字面表抓不住 |
| `no_verbatim_copy` 把源文与报告都过一遍 `norm()`（Unicode 减号、全角百分号、NBSP 归一）再比，
否则「报告里 `−70.5%`、源文里 `-70.5%`」会让抄袭检查静默失效（M18 第一次跑就是这么漏的）。

**`A-P6` 的归位（`O29`，2026-09-18）**＋它的反向 `A-P9`：这两条是同一件事的两端。

| 条目 | 方向 | 断言 |
| --- | --- | --- |
| `A-P6` | 归档 → 引用 | `sources/` 里有全文正文 ⇒ **它归属的那条 ref** 的 `link` 必须指全文载体 |
| `A-P9` | 引用 → 归档 | `link` 指向全文载体 ⇒ `sources/` 里必须有带同一个 `PMC<id>` 的字节 |

**归位是 `O29` 的修复**：`A-P6` 旧实现只认「文件名以 `ref_<n>` 开头」的归档，而真产物不这么命名
（`R14` 是 `PMC11270764_fulltext_jats.xml` / `<esid>.<route>.xml`），于是它在**最该咬住的那份产物上**报了
`no per-ref full-text body archived (check not triggered)` ——**空转假绿**，一个 citation link 都没看。
现在按四条通道归位（顺序即优先级）：① 文件名 `ref_<n>` 前缀；② 记录 esid 出现在文件名或正文前 4 K；
③ 正文的 `PMC<id>` 与该 ref 的 `link` 相同；④ 正文的 PMID 与该 ref 的 `link` 相同。四条都归不上时
不猜（判 PASS，但把文件名写进诊断信息）；`PMC<id>` 的**数字本身**不算 PMID（`PMC11270764` → 先抹掉
`PMC\d+` 再扫 PMID，否则 PMCID 的数字会被当成 PMID 命中）。

**为什么 `A-P6` 单独不够**：它只覆盖「先有归档」这一支，而产物可以只在 `link` 里声称读了全文、磁盘上
一个字都没有——旧实现下这种形状唯一可能被咬的位置就是 `A-P6`，而 `A-P6` 恰好不看它。`A-P9` 补上反向。
两者的配套对照：`M21`（归档 + 不声明，翻 `A-P5`/`A-P6`）、`M22`（归档 + 已声明 + 引用仍指摘要页，翻 `A-P6`）、
`M28`（凭空指全文、无归档，翻 `A-P9`）、`N28`（`R14` 的合法形状：归档 + 引用指全文 + 覆盖行声明 → 三条全绿）。

**gate 看不见空转，所以另做了产物层证据**：变异 gate 只能证明「`M22` 能翻出 `A-P6`」，证明不了它在**真产物**上
真在评判。因此本目录另有一份产物层回归档：`docs/evidence/fact-check-l3-real-artifact-rescore-2026-09-18.txt`
——同一命令重打**全部 7 份拿得出来的场景 A 真产物**（`R14`/`R8`/`R12`/`R15`/`R16`/`R17`/`archive-scope` 探针），
逐份贴出 `A-P5`/`A-P6`/`A-P9` 三行：`R14` 由「未触发」变为 `1 full-text ref(s) cite their full-text carrier`，
其余 6 份必须报「未触发」而不是假绿。该文件同时写了一句**覆盖面自白**：只有 `R14` 一份真把全文归档了 ⇒
「触发后真的判对」只在 **1/7** 上验过，另外两条归位通道（`ref_<n>` 前缀、esid）只被 harness 练过。

### 标题必须点明比较对象或共同主题（`A-T1`，2026-09-18 修 `O20`）

标题是唯一被引注规则豁免的位置（没有 `{{ref_n}}`），所以单独断言：它得让读者知道**在比什么**。旧实现只认
「两个药名都出现」，把主题式标题判 FAIL——而模板第 1 行本来写的就是 `# [比较主题]跨试验对比报告`，
`R16`/`R17` 渲染成 `# 脂蛋白(a) 升高人群降脂治疗跨试验对比报告`（一个药名都没有）完全合规。新口径（`shape` / `title_scope`）：

| 形状 | 判定 |
| --- | --- |
| H1 两个 `subjects` 组都命中 | PASS（`# …：[依洛尤单抗] vs [奥帕司兰] 跨试验对比报告`） |
| 一个药名都不点，但 `theme_all` 全命中（人群/适应症 + 对比标记） | PASS（主题式标题） |
| **只点了一个** subject | **FAIL**，主题写得再好也不行——这正是本条存在的理由（把两条记录写成同一个药，`M06`） |
| 既不点两个 subject 也不点主题 | **FAIL**（`# 结果对比报告`，`M26`） |

`N26` 是假阳性回归对照：**两个 subject 都点名**的标题必须保持绿（主题式标题那一支由 arm A 基线本身证明——`R17` 的 H1 就是主题式）。

### 锚点归因（`anchors` + `attribution`）

`{{ref_n}}` 把 report 切成**块**（一行、表格行各为一块），块内再切成**单元**：散文按 `。；` 切句
（**只在括号/方括号深度 0 处切**——`（A{{ref_2}}；B{{ref_1}}）` 是一个单元，不然括号内的对比句会被拆开后失去对方的引注，
造成假归因失败），表格行按 `|` 切单元格（单元格没有标记时继承该行的标记）。规则是「**单元里出现的 token，其 owner ref
必须在该单元的引注里**」。落到句/单元格粒度是必须的：像「试验 A＝NCT02729025（依洛尤单抗）{{ref_1}}；
试验 B＝OCEAN(a)-DOSE（NCT04270760）（奥帕司兰）{{ref_2}}」这种一行两试验的写法，按整行判会让
「把 B 的药名写成 A 的药」这类错配逃过检查（`M15` 正是**表格单元格内**的这类错配：把 ref_2 行的药名换成 ref_1 的，该单元就只剩 ref_2 引注而不再点自己的身份证 ⇒ FAIL；`N25`/`N27` 是它的假阳性对照）。

无引注的单元不参与归因——这是刻意的，因为标题（H1）天然没有 `{{ref_n}}`；标题的正确性用
`A-T1-title-identifies-scope` 单独断言（`shape` / `title_scope`）。

**身份对豁免（`O19`，2026-09-18）**：`pairs` 里标了 `"subject": true` 的 token 是**记录的身份证**（药名 + 登记号/试验名）。
规则分两半：

- **身份对**：引注 A 的 unit 若**同时点了 A 自己的身份证**，这句就是在**比较两条记录**（比较句，或排除句「该构念与 B 的终点不是同一构念」），
  句尾 marker 挂哪一侧是写法问题 ⇒ 豁免，PASS 信息里记 `identity pairing(s) skipped as comparison`。
  `R15`（`…与 [奥帕司兰] 的 Lp(a) 降幅终点不是同一构念{{ref_1}}`）与 `R12`（`安全性维度只有 [OCEAN(a)-DOSE]…{{ref_2}}，
  [NCT02729025] 未报告安全性数据`）都是这个形状，旧实现都判 FAIL。
- **数值对**：**永不豁免**。unit 引注 ref_2 却带着 ref_1 的数值（或反向）＝真错配 ⇒ FAIL，`M27` 专门证明豁免不是全免。
- 引注一侧全句不提自己的身份证（`M15`，表格单元格内把 B 的药名写成 A 的）⇒ FAIL 不变；`arm a` 的覆盖率检查保证 `A-ATTR` 始终有牙。

假阳性回归对照：`N25`（药名对药名）、`N27`（R12 的登记号对照句）必须保持绿。

## 反 gaming 约束（硬性）

1. **先有 record，后有清单。** 清单必须自 `POST /api/tools/debug` 返回的真实 record 撰写，**不得**先看
   某次 run 的 report 再回填。否则等于拿产物自证产物，就是 autoresearch issue #599 那类作弊。
   本目录的撰写顺序是：`records/*.json` → 清单 → 再拿真实产物判分（首次是 R8）。
2. **不得回改清单迁就产物。** 判出 FAIL 只能三角分诊：真缺陷 / 清单笔误，二者都要在台账留痕。
3. **`warn` 级不计分。** 记录里读不出来的推断（如剂量↔降幅映射要靠 arms 顺序 + `arm_count` 推）不算事实。

## 已知缺口

- **`iframe_template` 无法离线校验**。envelope 里这个 URL 每次发布都变，且旧构建会被平台删掉；离线只能断言
  形状（`^https://\S+$`），无法断言它与部署端 `config.js` 全等。当前只有在线 `run` 的第 4 条断言覆盖这一层。
- **场景 B 的完整判定只对 v2 run 成立**。v1（SSE）run 目录没有 `messages.json`、`artifacts.zip` 也只有几十字节，
  `check.py` 只能从 `debug-history.json` 兜底重建 `answer` 与 `transcript`（会打一条 `[WARN] surfaces rebuilt`）。
  兜底能覆盖 B 的全部 12 条 fail 级条目（R6 实测 12/12 PASS），但 `transcript` 是重建的，不是原生产物。
- **清单只覆盖 2 个场景（A/B）**，还没有覆盖跨试验 18 esid（场景 C）与同试验多证据状态（场景 D）。
- **arm A 只绑在一份基线产物（R17）上**：清单项本身跨 run 通用（R8/R12/R15/R16 都能判分），但「每个变异
  真能翻出对应 FAIL」只在 R17 的字节上被证明。换了措辞差异大的产物，某些变异可能匹配不到而空转（本次重写
  已经踩过两次：`M01` 漏了不带负号的写法、`M03` 只改了 1/22 处）。harness 会把空转报成 `rc=0 flipped=[]`，
  不会静默通过。
- **`A-ATTR` 的数值 token 曾长期写错符号（`O28`，已修）**：三份真产物正文一律用 U+2212（`−13.9`），而 token 写的是 ASCII `-13.9`，
  于是「数值对」这一分支**从未命中过任何产物**——打分器静默少一层牙。已改成 `[\u2212-]`；改后再打四份产物（R8/R12/R15/R16/R17）
  没有新增 FAIL，说明真产物在数值归属上是干净的，缺的只是这层检查。
- **`A-S10` 是口径级、不是出现级**：`R17` 里 `13.9` 有 9 处带负号、1 处（散文「与 [依洛尤单抗] 的 13.9% 之差远超…」）不带，
  这是同一口径下的自然写法，不是混用；只有**被画进图的那几个量**在报告与图表之间口径相反才判 FAIL（逐处强判会误伤散文）。
- **「不满足前提就不触发」的断言有**空转**风险（`O29`，已修一代，机制上仍在）**：`A-P3`/`A-P5`/`A-P6`/`A-P9`、
  以及任何 `optional_when_absent` 都靠「前提不成立 ⇒ PASS」活着，而真正的 not-triggered 与「判断写错导致
  永远进不去」在输出上完全同形。本轮 `A-P6` 就是这么空转了整整一轮（详见上面 `O29` 一节）。对策是两道：
  变异样本改用**真产物的命名**（不再用断言自己假设的文件名），以及把真产物重打一遍落库
  （`docs/evidence/fact-check-l3-real-artifact-rescore-2026-09-18.txt`）。剩余风险：现在只有 `R14` 一份真产物
  进了全文分支，其余产物都是「0 归档 ⇒ 未触发」——**参数空间里只覆盖到一个点**。
- **`NEG_A` 的判据已收紧到「整轮干净」（2026-09-18）**：旧版只看「我想保绿的那一条没翻」，于是一个把别的
  条目打翻的负向对照也会报 `[OK]`。现在要求 `rc == 0` 且 `flipped == []`，否则 `[BAD]`。
- **`facts_ok/facts_total` 是清单覆盖率，不是事实完备率**：报告可以在全部条目 PASS 的同时漏掉清单没写的事。
  清单的覆盖面靠「对着 record 逐字段过一遍」手工保证。

## 负向对照（清单有牙的证明）

`mutations.py` 把真实 run 目录复制到临时目录、施加定向变异，要求 **① 判分退出码变 3、② 该变异期望的条目
出现在 FAIL 列表、③ 所有变异合起来覆盖清单里每一条 fail 级条目**。

变异手段分两类：`sub()`（按**正则**替换，带替换次数上限断言——上限防的是「字符串里的 `|` 被当成空分支交替、
一次改掉几千处」的静默灾难）与 `sub_lit()`（`re.escape` + `count=1`，用于含 `|` / `{}` 的**字面**锚点）。
当前结果：

```
arm a: flipped 41/41   (28 个变异，均按 R17 产物字节下手：改主终点数值（M01）、翻转安慰剂符号、
                        抹掉试验 B 的登记号与试验名（M03）、篡改时点、
                        把 ref_1 指向不存在的引用、把 H1 换成只点一个药的标题（M06）、
                        在表格单元格里把 B 的药名写成 A 的（M15）、把 2 条写成 5 条记录（M07，
                        同时打掉 A-C12 的「2 条」与 A-N1 的禁词）、改 citation 标题、
                        让两个 ref 指向同一条记录、改图表数值、多出一张时间轴图、
                        删掉 report、破坏 envelope、删掉 ref_2、
                        删掉定量主图且不说明原因（M16）、删掉原文核对行（M17）、
                        把抓取原文整段抄进正文（M18）、只写库内值不写原文值（M19）、
                        把覆盖行改成不点路径/来源类的空壳（M20）、
                        归档了 PMC 全文但覆盖行只声明摘要路径（M21）、
                        归档了全文且覆盖行已声明，但引用仍指摘要页（M22）、
                        把模板的规格句照抄进报告（M23，同时带动 A-P2/A-P8）、
                        把规则本身换个说法写进报告（M24：无值无引用的「未发现不一致」句）、
                        让图表与报告用不同符号口径（M25：只翻 A-S10，数值不动所以 A-S9 仍绿）、
                        把 H1 换成什么都不点明的「# 结果对比报告」（M26）、
                        在点了对方登记号的句子里塞进另一条记录的数值（M27：证明豁免只对身份对生效）、
                        凭空把引用指到 PMC 全文页而不取任何正文（M28：只翻反向的 A-P9）)
arm a 假阳性回归（`NEG_A`，要求**整轮干净**：退出码 0 且无任何 fail 级条目翻车——
                        不只要求「自己那一条保持绿」，否则别条目被打翻时它会报成 OK）：
                        N25 混合句（引注 ref_1 + 点两条记录的药名，形状取自 R15 真实产物）
                        N27 登记号对照句（引注 ref_2 + 提对方的试验，形状取自 R12 真实产物）
                        N26 两个 subject 都点名的标题（A-T1 的第一支合法形状）
                        N28 合法 L3 形状（归档 + 引用指全文 + 覆盖行声明 = R14 的真实形状；
                            同时守住 A-P5 / A-P6 / A-P9 三条）)
arm b: flipped 12/12   (11 个变异：写出 report/citations、写出图表、改口说「已生成报告」、
                        改掉不可用 esid 名、改掉有效 esid 名、删掉「未返回记录」表述、
                        删掉「不足以构成」表述、删掉请用户核对的表述、给死 esid 编造结论、
                        否认「什么都没写」、抹掉有效记录的药品名)
GATE: PASS
```

（上面这段的**完整输出（50 行）已落库**：`docs/evidence/mutation-gate-2026-09-18-r17-baseline.txt`，退出码 0。
L3 的产物层对照在 `docs/evidence/fact-check-l3-real-artifact-rescore-2026-09-18.txt`。）

**arm A 基线 = 真实产物本身（2026-09-18 起）**：基线是 `R17`（`20260918-095553-r17-sign-convention`）——
一份**逐条全绿**的真实产物（41/41 fail 级），也就是当前已发布内容（prompt v1.6 / skill v1.0.7）跑出来的那一版。
它天生带 `原文核对：` 行，所以 `mutations.py` **不再向临时副本注入任何内容**（旧的 `seed_original_check` 已随
R8 基线一起删除）；基线判分现在就是「把真实产物原样过一遍清单」。

换基线的代价不是一个路径常量：4 条变异原本绑定 R8 的字节，`M21` 的**前提**也挂在 R8 上，逐条按 R17 的真实措辞重写：

| 变异 | R8 版 | R17 版（现在） |
| --- | --- | --- |
| `M01` | 只替带负号的 `−13.9` | `13\.9` 全部替换（R17 散文里有一处不带负号的「13.9% 之差」，只替带号写法时 `A-C4` 仍是绿的——第一版重写就踩了这个坑） |
| `M03` | 替 `NCT04270760` | 替 `[OCEAN(a)-DOSE](entity:trial:NCT04270760)`（`count=0`，22 处；`A-C2` 要三条图案全中，只打掉登记号不够） |
| `M06` | 把首个「奥帕司兰」换成「依洛尤单抗」 | 把 H1 换成只点一个药的标题（走 `A-T1` 的「只点一个 subject」FAIL 分支；R8 版的跨归属角色现在由 `M15` 承担） |
| `M07` | 只改「纳入结果：2 条」 | `2 ?条` 全替（覆盖行里还有 `2/2 条`、「2 条仅摘要级」，只改一处两条项都翻不动） |
| `M15` | `\| 试验 B {{ref_2}} \|` 行内注入「（优于依洛尤单抗）」 | 把 ref_2 行的药名单元格换成 ref_1 的药名（同一语义，按 R17 的行措辞；`N25`/`N27` 是它的假阳性对照） |
| `M21` | 只加一个全文归档（假定基线不提全文 ⇒ `A-P5` 翻） | 加归档**并**把覆盖行改写成只声明摘要路径（R17 覆盖行本已提 `PMC6933872`/「全文」，只加归档翻不动 `A-P5`） |
| `N26` | 主题式标题（在 R17 里这已是基线形状 ⇒ 空转） | 两个 subject 都点名的标题（同一项的**另一支**合法形状） |

**实测新基线**：`baseline a: 41 fail-severity items, all PASS` → `arm a: flipped 41/41; never flipped []`
→ `GATE: PASS`。踩过的两个坑都留了痕：`M01` 只替带负号写法时 `A-C4` 保持绿；`M03` 用 `sub_lit` 默认
`count=1` 时 22 处只改 1 处，`rc=0 flipped=[]` 被 harness 直接点出——这正是「变异必须真能翻出对应 FAIL」的价值：
改动没生效时 harness 不会静默通过。

## `O29`：gate 全绿但 `A-P6` 在真产物上空转（2026-09-18 修）

上面那套 gate 本身有一个**它自己看不见的盲区**，值得单独记一笔——免得下次又把「gate 绿」当成「清单真有牙」：

变异 `M21`/`M22` 都是 harness **自己拼的**归档文件名（`ref_1.pmc-fulltext.xml`，带 `ref_` 前缀），而真产物
从不这么命名（`R14` 是 `PMC11270764_fulltext_jats.xml`）。旧 `A-P6` 只认 `ref_<n>` 前缀 ⇒ 拿 `R14` 原产物判分时
它报 `no per-ref full-text body archived (check not triggered)` 并 **PASS**——在最该咬住的产物上，它一个
citation link 也没看。`M22` 能翻它、`N28` 又能守住它，但两者都跟 harness 写下的文件名同源，于是**拿自己的
假设自证**。这不是写错一条正则，而是「被测对象只出现在自身构造的样本里」这一类盲区。

修法有两层，缺一不可：① 把归位拆成四条通道（见上面 `A-P6` 小节）；② 让对照样本改用**真产物的命名方式**
（`M22`/`N28` 现按 `PMC<id>_fulltext_jats.xml` + 真 PMID 构造），并额外把真产物本身重打一遍落库
（`docs/evidence/fact-check-l3-real-artifact-rescore-2026-09-18.txt`）。判据是那句可观测的差异：`R14` 的
`A-P6` 从「`check not triggered`」变成 `1 full-text ref(s) cite their full-text carrier`。

同类风险的识别口诀：**任何一条「不满足前提就不触发」的断言，都要问一遍「那个前提在真产物里到底长什么样」**
——`A-P3`（未抓原文不触发）、`A-P5`、`A-P6`、`A-P9` 都是一族；harness 里的样本若按断言自己的假设构造，
就会把空转洗成绿。

基线（未变异）两份清单都必须全 PASS——否则说明清单本身写错了。

**两份独立样本的基线**：R8（`20260916-104943-v2-poll`）与 R9（`20260916-112352-p8-kill`，同一场景 A、
客户端被 `kill -9` 后 `--resume` 补齐）都用 `scenario=a` 跑到 **31/31 PASS**（当时的清单版本）。两个不同 run 同一场景都给满分，
说明清单没有绑定单次运行的措辞（同时也说明它测不出“两轮之间的微小质量差”——那是后来场景 C/D 与人工抽检的事）。
