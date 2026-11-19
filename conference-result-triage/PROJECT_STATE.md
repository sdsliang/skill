# PROJECT_STATE — conference-result-triage

## v0.16（2026-11-20）：卡面标识变成闸门 —— `drug` / `target` 没有任何数据列兜底

出发点是用户一句「`drug_names` 那个不行就算了，**让 llm 写理由的时候兜底抽吧**」。查完才发现，兜底抽取
这件事此前**根本没人检查**：ADA 2026（v0.15）交付的 27 张卡 `drug` / `target` **27/27 全空**，卡头药物位印成
`—`、复核页左导退化成截断标题，而 `check_cards.py` `OK cards=27`、事实层 `28/28 PASS` —— 18 条规则里
没有一条问过这两个字段。

### 根因链（四步证伪）

1. **`base.trial_drug`**（用户猜的名字）不存在：`grep trial_drug` → 0 命中。
2. **`clinical_result.drug` / `.target` / `.moa`** 不在 `ALLOWED_FIELD_NAMES`（250 个名字），写进 `selected_fields`
   直接 `INVALID_INPUT`；唯一沾药的 `clinical_result.projects` 是**申办方/公司**（v0.13 明令禁用）。
3. **`clinical_result.arms[].drugs[]` 是真的**：`drug_earth_name_cn/_en/_all_name`、`target_name`、`target_all_name`、
   `moa_name_cn/en`、`is_primary_drug`、`latest_phase`；但**单条 ≈5.9 KB**（27 卡 159.9 KB，全场 1097 卡 ≈6.4 MB
   会撞工具结果 6 MB 截断）→ 只能是「短名单核对通道」，不能当常规取数。
4. 因此 `drug` / `target` 的合法来源只剩**判读者读标题/摘要时抽出来写进 `plan.json`**；而「模型自觉填」的
   字段没有任何闸门 → 空着不会有人知道。

### 改动（四件套）

| 层 | 改动 |
|---|---|
| 校验层 | `check_cards.py` 新增**第 19 条** `card_identity_gate()`：每卡 `drug` / `target` 必须为非空字符串；`target` 允许为空但只认 `editorial_overrides` 里 **`field: "target"`** 的声明（reason ≥10 字），**按字段分键**——「同机制让席」这类选择理由不能顺带豁免空卡面。`MIN_OVERRIDE_CHARS=10`、`IDENTITY_FIELDS` 常量同增 |
| 事实层 | `op_card_identity` + 事实项 **`A-P10-card-identity`**（fail，同一条字段级豁免语义）；`facts.json` **29 → 30 项（29 fail + 1 warn）**；`EVALUATOR_REVISION` → `2026-11-20-r7` |
| 夹具层 | `mutations.py` 新增 **`m_drug_blank`**（把一张卡的 `drug` 清空：卡仍合法、仍可溯源、仍在合法桶内，只是说不出是哪个药）；fixture 补 `drug`/`target`。`test_check_cards.py` 51 → **56 case**（含反向 case「选择跳过理由不许豁免空靶点」） |
| 文档层 | `review-protocol.md §7A` 删掉那句假话（原写「会议库已直接给出 `drug`/`target`/`moa`，优先用它」——平台内没有那个库，这句正是没人去读摘要的成因）；`data-contract.md` 的表标注「结构化表没有这三列」+ 规则数 18 → 19；`SKILL.md` 交付契约新增 `drug`/`target` 必填条款 + v0.16 版本块；`README.md` 补一段；`pitfalls.md` **§44** |

### 验证（本地，全部离线）

- `python3 evals/test_triage.py` → `fixture OK (6 rows, design-fallback + dedupe-alias covered)`。
- `python3 evals/test_check_cards.py` → `fixture OK`（新增 5 case 全绿）。
- `python3 evals/fact-check/mutations.py` → **`coverage: 29/29 fail items have a mutation; 7 negative controls green`**。
- **反例（真实产物）**：`20261119-144018-cards-ADA-26-v15` 的原始 `watchlist.json` 跑新事实层 → `facts 28/29 -> FAIL`，
  唯一红项 = `A-P10-card-identity`；同一产物跑 `check_cards.py` → **EXIT=3**、54 处空位（27 卡 × 2 字段）。
- **正例**：把 `dist/review/` 里已用 `attach_arms.py` 补齐的 27 卡（`ada2026-watchlist-v15.json`）喂同一套闸门 →
  只剩 3 处 `target` 为空（BCG × 2、二甲双胍），即「确实没有分子靶点」的那三条，也正是必须走
  `field: "target"` 声明的情形 —— 闸门不是空的。
- `dist/conference-result-triage-v0.16.zip` — **151730 B / 15 entries** / sha256 `bd2197a2cbaa3248…`。

### 发布与实跑（已完成）

- **原地发布**：`publish` → `entries=15 identical=15 differing=0`、**`STATUS: in sync`**（label 仍 `v0.3.0`，
  skill_id `230463cbc03d4fe5ba0e2e8964fe91dd`）。`deps: unchanged`、共享 SP `pin matches` v1.0 / 29311 B。
- **E2E `20261119-154031-cards-ENA-26-v16`**（ENA 2026，DeepSeek Flash + `--web`）：结果库仅 **17 条** → 交付
  **10 卡（early 8 / pivotal 1 / failed 1）**，墙钟 **413.3 s** / 78 次工具调用。
  - **`drug` / `target` 10/10 全非空，全部由模型从标题与摘要抽出**（本轮压根没调 `clinical_result.arms`、
    也没有手补），证明「让 llm 写理由时兜底抽」这条路在真跑里成立；`check_cards.py` **EXIT=0 `OK cards=10`**。
  - 事实层 **facts 28/28 warn 0/1 → PASS**，`A-P10-card-identity` → `drug+target named on 10 card(s)`；
    runner 断言 **24 PASS / 0 FAIL**；`coverage_notes` 6 条明写「只有 17 条、三桶凑不满、未用无读数记录凑数」，
    并声明库里没有的三条 late-breaking 未纳入。
  - 复核页 `dist/review/ena2026-watchlist-v16.html`（19818 B）——卡头与左导均印模型写的药名。

### 这轮抓到的评测器缺陷：`A-D2` 把语料规模写死成 ESMO 量级

17 行的会议 `plan_slices.py` 正确地不切分（`slices/` 只有 `_all_ids.txt`）、一次拉完，而 `op_query_slicing`
的 `sources` 分支用常数 `min_calls=7` 判「至少 7 次 dump」→ **正确的 17 行会议被判失败**。与 v0.12「断言写死 1097」
同类。修法：按已拉行数反推 `need = ceil(rows / max_slice)`；新增负控 `ngen_small_corpus_single_dump`（必须绿）
→ `coverage: 29/29 …; **8** negative controls green`。修完同一产物 `facts 28/28 PASS`。

### 第二场验收：ESMO 2026（1097 条）`20261119-173236-cards-ESMO-26-v16`

- 墙钟 **1376.5 s** / 103 次工具调用；交付 **30 卡 10/10/10**；runner **24 PASS / 0 FAIL**；
  事实层 **29/29 + warn 1/1 PASS**；`check_cards.py` **EXIT=0 `OK cards=30`**。
- **`drug`/`target` 30/30 非空**（同样零 `arms` 调用、零手补）；**`abstract_id` 30/30 有号** —— 与 R18 的
  ENA 空列对照，坐实 ENA 缺号是**数据侧缺口**，不是取数或渲染缺陷。
- 唯一 override 是**正当选择理由**（放弃 LBA11 88 分，让位给机制互补方案），不是缺失豁免。
- 复核页 `dist/review/esmo2026-watchlist-v16.html`。

### 未做（待定）

- **未把 `attach_arms.py` 接进 skill 包**：它现在只在 `dist/review/`（本地复核页工具链）。本轮证明「不拉 arms
  也能填满」之后，这条的优先级下降；保留它作为**核对通道**（短名单 45 卡 → 每 10 个 esid 切片拉 ≈265 KB）。
- **`lifileucel` 的 `target` 写成散文**（`肿瘤浸润淋巴细胞（TIL，非分子靶点）`）：诚实但走了非设计路径
  （应为 `editorial_overrides` 的 `field: "target"`）。若要连这种写法一起管，需新增「`target` 不得是解释性长句」
  规则，有误伤风险 → 先留证据（R18 第 1 条观察）。
- **`A-C1-heat-coverage` 0/12**（warn）：热议名单是 ESMO 2026 攒的，跨会议天然 0/12；应按会议取名单或在无名单时 SKIP。
- **小会议不适合当榜单质量评测对象**（ENA 17 条、同期 ENA 2025 43 条、库里缺三条 LBA），只适合契约验收。

## v0.15（2026-11-19）：交付物收敛成一份 JSON（删 report.md + citations 整条链）

用户原话：「不要 report.md 啊，citation 也不需要啊，只要 watchlist 就行了」。这不是"再修一遍引文三键"，
而是**这一整层本来就不该存在**：Markdown + frontmatter + `{{ref_N}}` + `citations.json` 唯一的用途是让宿主
渲染一份人读的页面，而这份 skill 的产物是 30 张卡的判读结果。删除按四层同删执行，少一层就留死代码或假红。

### 改动

| 层 | 改动 |
|---|---|
| 校验层 | `check_cards.py` 删 `--report` / `check_report()` / `_frontmatter()` / citation 常量；**规则 19 → 18**（原规则 14 删除，15–19 前移，交叉引用 rule 16→15 / 17→16）；44656 → 39018 B |
| 事实层 | `check.py` 删 `op_report_meta` / `_frontmatter` / `FRONTMATTER_RE` / `report`+`citations` 采集，`OPS` 去掉 `report_meta`；`facts.json` 删 `A-C2-report-frontmatter`，`A-T1-present-artifact` 的 `suffix` → `output/watchlist.json`；**30 → 29 项（28 fail + 1 warn）** |
| 夹具层 | `mutations.py` 删 `m_no_skills` / `m_citation_dangling` / `ngen_citations_legal`，fixture 不再写 `report.md`/`citations.json`，`present_artifact` 指 watchlist；**新增 `m_present_md`**（把路径改回 `report.md` 必须判红，这是回潮的唯一入口） |
| 渲染层 | `SKILL.md` Step 7 重写（交付物 = `watchlist.json`，`present_artifact` 指向它，无 frontmatter/引文段）；Step 6 去掉 `--report`；`description` 删掉早已过期的"stock move"；新增 v0.15 版本块。`templates/watchlist-report.md` **删除**，`pack-dist.py` 的 `templates/` 改为可选（references/scripts 仍强制） |
| 宿主契约 | `~/.config/toolsmith/projects.json` 的 `deliverables` → `["output/watchlist.json"]`（备份 `.bak-20261119-v15`） |
| runner（O57） | `toolsmith-publish` 的 `report_rel` 原来硬回落 `output/report.md`：无 md 时读空串 → `report contains nonempty content` 恒红。改为 **md 可选**（无 md 则跳过正文类断言并记一条说明），`present_artifact` 终端路径在无 md 时取「∈ deliverables」。备份 `toolsmith-publish.v15.bak` |
| 文档 | `README.md`（交付行 + 目录树 + CLI 注释）、`references/data-contract.md §6.5.2` 重写、`pitfalls.md` **§43**（新）+ §27/§32 标注「v0.15 起无对象」 |

### 验证

- `python3 evals/test_triage.py` → `fixture OK (6 rows, …)`。
- `python3 evals/test_check_cards.py` → `fixture OK`（report 相关 7 个 case 随 `check_report` 一起删除）。
- `python3 evals/fact-check/mutations.py` → **`coverage: 28/28 fail items have a mutation; 7 negative controls green`**；`m_present_md` 单跑翻红。
- `dist/conference-result-triage-v0.15.zip` — **146817 B / 15 entries**（templates 不再入包）/ sha256 `89003e4f3c24c288…`。

### 发布与实跑（已完成）

- 原地 publish：`POST /api/skills/update_skill_file` HTTP 200 → `entries=15 identical=15 differing=0`、**`STATUS: in sync`**（label 仍 `v0.3.0`，部署 `2026-11-19T14:40:10`）。共享 SP 未动（`pin matches` v1.0 / 29311 B；deployed instructions 23363 → 23408 chars 的差只是末尾 `Today's date`）。
- **E2E `20261119-144018-cards-ADA-26-v15`**（thread `ba885826`，DeepSeek Flash + `--web`）：191 行 → **27 卡（10/10/7）**，墙钟 **635.8 s** / 86 次工具调用。
  - `artifacts/output/` 下**只有 `watchlist.json`**；`present_artifact` = `/workspace/output/watchlist.json` 且是最后一个成功调用。
  - runner 断言 **24 PASS / 0 FAIL / 0 WARN**，含 `no markdown deliverable declared - report-body assertions skipped`（旧 runner 这行恒红）。
  - `check_cards.py` **EXIT=0 `OK cards=27`**；`check.py --scenario ada2026` **facts 28/28 warn 0/1 → PASS**。
  - 27/27 `is_recommand=null`、`tag` 只 `""`/`LBA`、卡面无公司代码与行情字段、桶内降序无回升。
  - failed 桶只有 7 张：ADA 本场候选不足，`PER_BUCKET_CAP=10` 是上限不是配额，未用 `weak` 凑数。
- **反证**：v0.14 的 ASH 产物跑新事实层 → 只红 `A-T1-present-artifact`（指向 `report.md`），其余 26 项绿。
- **R16 已落** `evals/EVALUATION_RESULTS.md`。

### runner 缺陷记账（共享 `toolsmith-publish`，本仓只记不占台账编号）

- **O57**：`report_rel` 原硬回落 `output/report.md`，无 md 时 `report contains nonempty content` 恒红 → 改为 md 可选 + `present_artifact` 路径取「∈ deliverables」。备份 `toolsmith-publish.v15.bak`。
- **O56**：`--resume` 不 `POST /api/chat`，模型不可能变，但旧代码把 CLI 默认值写进 `run.json` / `verification.md`（ASH 2026 的 GPT 6.1 Sol 回合被记成 DeepSeek Flash，同 `turn_id` 可证）。改为续跑继承原记录，显式 `--model` 冲突时告警。**R15 的「平台回落模型」结论据此更正。**

### 待办

- [ ] 统一判读文件命名 + 修 `load_judged` 对 `judged_all` 重复计入。
- [ ] `A-D4` 会议能力 gating；`A-C1-heat-coverage 0/12` 待查。

## v0.14（2026-11-19）：三态、席位、期别槽 —— 三条「看上去没问题」的规则补成闸门

R14 的教训是「文案里的规则不算闸门」。这一轮把三条只写在文档里、实际没被机械检查的规则，补成
**生成端 + 校验端 + 事实项 + mutation** 四件套，并用一场从没跑过的会（ASH 2026）验证。

### 改动

| 层 | 改动 |
|---|---|
| `triage.py` | 新增 `DESIGN_WORDS`（前瞻性/回顾性/随机/单臂/开放标签/双盲/…共 20 个设计词）与 **`phase_label()`**：`TRIAL_PHASES` 直通、含设计词 → `None`、其余原样。`phase_of()` 保持原样（**排除匹配用**，docstring 改为 raw/exclusion），卡面 `phase` 改走 `phase_label()`；`phase_inferred` **删掉 `not is_lba_row` 豁免**（LBA 也不例外） |
| `make_cards.py` | `bool(item.get("is_recommand"))` → **`_recommand_value()`**，`None` 原样输出 |
| `check_cards.py` | **`_recommand_of()`** 三态比对（卡上是 `false` 但库里是 `None` → fail）；新增 **`bucket_order_gate()`**（分组键 `(bucket, is_recommand)`，组内分数不回升）与 **`trial_seats_gate(cards, pool, overrides, max_seats=2)`**（第 3 席起 fail，`editorial_overrides` + `reason ≥10` 只记 note）；docstring 17 → **19 条规则** |
| 事实层 | **`A-P8-recommand-tristate`**（`op_recommand_tristate`，拿卡值逐条比 `rows.json`；`columns_present=False` 时只做类型检查并 note）、**`A-P9-trial-seats`**（`op_trial_seats`，无 `trial_abbreviation` 时返回「nothing to group by」而不是 PASS）。28 → **30 项（29 fail + 1 warn）** |
| `mutations.py` | `m_recommand_collapsed`（把 `null` 印成 `false`）/ `m_trial_seats`（三行同 trial）；fixture 的 `is_recommand` 改三态、`coverage` 行改按实际行数写 |
| 测试 | `card()` 的 `is_recommand` 改三态，新增 case 20b（null 印成 false → fail）/ 20c（`_recommand_of` 三态映射直测），共 **51 case** |
| **`A-D1` 动态化** | pattern 写死 `coverage:\s*1097/1097` → **`self_coverage`**：从 transcript 读 `n/n`，要求自洽且等于 `rows.json` 行数 |
| 文档 | `review-protocol.md §2.5`（`phase_inferred` 口径 + LBA 加分项三条纪律）、`data-contract.md`（三态 + 排序键 + 2 席）、`screening-rules.md §1.0`、`SKILL.md`（4 处 + v0.14 版本块）、`templates` 硬规则 7、`pitfalls.md` **§40 `bool(None)` / §41 顺序与席位 / §42 `phase` 印设计词** |

### 验证

- 本地全绿：`test_triage` fixture OK；`test_check_cards` **51 case OK**；`mutations` **29/29 fail 项有 mutation + 8 NEG green**（含 `A-P8` / `A-P9` / `A-D1` 各自翻红）。
- 手验两个新闸门：逆序 `[83,71,73]` 被抓、`[flagged 60, 83, 80]` 合法；同 trial 3 卡 → `trial HR17031 holds 3 cards … cap is 2`，加 override 后只 note。
- **旧产物 fail-closed 复核**：ESMO v12 产物 `facts 27/29 FAIL`（`A-N1` + `A-P8`）、ADA v13 产物 `26/28 FAIL`（`A-P4` + `A-P8`）——v0.13 产物在 `A-P8` 上必红，符合预期。

### dist 与发布

- `dist/conference-result-triage-v0.14.zip` — **151557 B / 16 entries / sha256 `f5b58c0614a1`**（首包 151221 B / `66f60f0bad74`，补完规则 18/19 的 docstring 与 case 计数后重打）。
- 原地 publish：`entries=16 identical=16 differing=0`、`STATUS: in sync`（label 仍 `v0.3.0`，部署时间 `2026-11-19T12:23:30`）。
- **发布前被共享 SP 变更硬拦一次**：`PharmCube AI Chat SP` 由 owner 原地改成 `6db755d1f080` / 29311 B（version 仍 `1.0`），我们的 pin 是 `a2b1581ef7cd` / 29169 B。按工具指示重读 deployed instructions（580 行，`## File Artifact Presentation` 契约未变），更新 `~/.config/toolsmith/projects.json` 的 `shared_prompt_pin` 后 `status` 转 `pin matches`。**没有写 SP 本体。**

### 实跑 ASH 2026（2026-11-19）

- run `20261119-120850-resume-cards-ASH-26-v14b`（thread `b10c7f03`）：**1524 行** → 排除 577 → **893 候选**（493/356/44）→ 全量判读 → **30 卡（10/10/10）**，墙钟 **3753 s**，64 次工具调用（`task` 21 批）。
- `check_cards.py` **EXIT=0**；`check.py` **facts 28/28 warn 0/1 → PASS**（`A-D1` 动态化后 `coverage 1524/1524` 通过）。
- 三个 v0.14 目标全部成立：**三态不坍缩**（30/30 `null`）、**桶内降序**（early 86→80 / pivotal 96→90 / failed 94→86）、**设计词不进期别槽**。
- 两条数据缺口（非 skill 缺陷）：ASH 2026 的 `clinical_result.lba` **1524 全 null**（`A-D4` → SKIP）、`is_recommand` **列不存在**。均写进 `coverage_notes`。
- 复核页 `dist/review/ash2026-watchlist-v14.html`（30 卡 / 50356 B）。
- **runner 缺陷**：`--resume` 未重传 `--model`，平台回落到 DeepSeek Flash（原起跑是 GPT 6.1 Sol），`verification.md` 记的是实际模型。续跑必须重带 `--model`。
- **run 期两条断言 FAIL 属发布态不同步**（我在 run 中改了 docstring / case 计数），12:23 republish 后 `identical=16` 消解；本轮没有「发布态全绿断言」快照，已在 R15 如实记。

## v0.13（2026-11-16）：把「股票」这个读法从卡面上彻底拿掉

两处改动是同一件事：卡面上任何能被读成"这只票怎么走了"的东西都不留。

### 起因

v0.12 复核页截图确认：30 张卡里 **16 张有 `listed_company`**（`AZN · NASDAQ` 那种彩色 chip），
全场唯一标星行 `LBA7` 的卡面上还多了一个「推荐」徽章。两个 chip 都在**卡片最显眼的一行**，
读者第一眼看到的是股票标签和自家背书，而不是读数。

### 改动（脚本 → 事实层 → 文档）

| 层 | 改动 |
|---|---|
| `check_cards.py` | 新增 `COMPANY_CODE_KEYS = ("listed_company","ticker","exchange")`，**键存在即 fail（`null` 也算）**；新增 `TAGS = ("","LBA")`，`tag` 非白名单即 fail；docstring 规则 12 合并为「no market data survives anywhere」，规则数 17 |
| `make_cards.py` | `tag` 只由 `lba` 推出（`_auto_tag` 不再看 `is_recommand`）；旧 plan 残留的代码字段打 `!` 警告后**丢弃**，不静默复制 |
| 事实层 | 删 `A-F5-listed-company`（29 → 28 条）；`A-N1-no-price-claims` → **`A-N1-no-market-claims`**，价格与公司代码一起拦；`op_no_price_claims` → `op_no_market_claims`；`op_listed_company_shape` 整段删除 |
| mutations | `m_listed_missing`/`m_listed_bare` → `m_ticker_returned`/`m_listed_returned`；`m_price_returned` 改在卡片顶层写 `reaction`；NEG「fully sourced HK company」换成 **「company named in prose, no code」**（删掉代码不等于删掉公司） |
| 测试 | `test_check_cards.py` 46 → **49 case**（`listed_company=null` 也算行情声明、裸 `ticker`、无代码合法卡通过、`tag="推荐"` fail / `tag="LBA"` 合法） |
| 文档 | `SKILL.md`（Step 5B 删「查上市公司」整段与「`ticker` 只写裸代码」段、交付 JSON 示例、必填四条、checker 拦截项、`## 版本` 新增 v0.13）、`data-contract.md §6.5/§6.5.1`、`pitfalls.md §26` 改口径 + **新增 §39**、`review-protocol.md`（检索三类、删 `listed_company` 用法段）、`templates` 硬规则 7 加「不加徽章」、`README.md` |
| 复核页 | `build_review_page.py` 删 ident chip 分支与 `.chip.ident` CSS；`tag` 只渲染 `LBA`；产出 `dist/review/esmo2026-watchlist-v13.html`（30 卡） |

### 验证

- 本地全套绿：`test_triage` fixture OK；`test_check_cards` fixture OK（49 case）；`mutations` **coverage 27/27 + 8 NEG green**。
- **旧产物 fail-closed**：拿 v0.12 的 ESMO 实跑产物跑新闸门 → **EXIT=3**，30 条 `listed_company is a company-code field` + 1 条 tag 越界。
- **同一批内容去掉身份层即通过**：把 30 张卡删掉代码字段、`tag` 归一到 `LBA/""` → **EXIT=0 `OK cards=30`**。说明删的是形状，不是内容。
- 复核页 v13 截图确认：`LBA7` 卡只剩 `LBA` + `LBA87`（abstract_id）chip，`AZN · NASDAQ` 类 chip 消失，「推荐」徽章消失。

### dist

`dist/conference-result-triage-v0.13.zip` — **143957 B / 16 entries / sha256 `a61a30d9523b320f`**。

### 发布与实跑（2026-11-17）

- 原地 publish：`entries=16 identical=16 differing=0`、`files=0`、`STATUS: in sync`（label 仍 `v0.3.0`）；发布前 `deps` 因 MCP schema 变化拦了一次（`+['is_recommand']`），确认是我们已在用的字段后 `deps --accept` 记新基线（备份 `deps.json.bak-v13`）。
- 实跑 **ADA 2026** `20261117-090551-cards-ADA-26-v13`：191 → 138 候选 → 30 卡（10/10/10），22 min，平台断言 **24 PASS / 0 FAIL**，`check_cards` **EXIT=0**。
- **v0.13 三个验证点全部成立**：卡面带代码键 **0**、`tag ∈ {'', 'LBA'}`、`abstract_id` 30/30。
- **检索成本**（同场对比）：`web_search` **29 → 25 → 17**（v0.9 → v0.10 → v0.13），降 32%。
- 事实层 **25/27**，两项 FAIL 都不是本版引入：`A-D1` 是**评测器把 ESMO 的 1097 写死**；`A-P4` 是真缺陷（pivotal 71/73/71 逆序）。

### 待办（v0.14）

- [ ] **`is_recommand` 三态被压成二值**：`make_cards.py:130` / `check_cards.py:622` 用 `bool(...)`，卡面 `false` 被读成「数据方标了否须排除」（平台新 schema 已明确 `否`=排除）。改成 `True`/`False`/`None` 三态直传 + 三态比较。
- [ ] **桶内降序没有交付前闸门**：`check_cards.py` 只查 top-k 跳分，不查已入选卡是否降序（`A-P4` 只能事后抓）。
- [ ] **同一试验的多个亚组**占用多席（`HR17031 vs iGlar` ×3）：同机制 ≤2 管不住，需要按 trial 限席。
- [ ] **`A-D1` 评测器硬编码 ESMO 行数**：pattern 改成从 `rows.json` 的 `requested` 动态构造。
- [ ] **卡片「期别未标注」丢推断依据**（v0.12 遗留）：`phase_of()` 把 `evidence_source` 里的设计词原样当 `phase`；`phase_inferred` 又带 `not is_lba_row` 豁免 → 7/30 卡印「前瞻性研究」。
- [ ] 用户新增两条需求（待落地）：**最终产物只要 `watchlist.json`，不要 `report.md`**；**LBA 应作为加分项**（当前只影响分桶与 `tag`，不进 `score_parts`）。

## v0.12（2026-11-16）：`abstract_id` / `is_recommand` 一直都在，是我们没请求

### 诊断：一个活了四个版本的负向结论

需求里提到「MCP 新增两个字段」。实测不是新增 —— 两个字段都在 `clinical_result.*` 白名单内：

| 字段 | ESMO 2026 实测 | 结论 |
|---|---|---|
| `clinical_result.abstract_id` | **1097/1097 非空** | 一直可选，`pull_results.py` 的 `DEFAULT_FIELDS` 从来没写过这个名字 |
| `clinical_result.is_recommand` | **1096 null + 1 `是`** | 稀疏但存在 |

同一实测还确认：ASCO 2026 `abstract_id` 1648/1648、AACR 2026 288/288 全非空；`is_recommand` 在 ASCO 2026 / AACR 2026 / ESMO 2025 / ASCO 2025 **均为 0**。唯一标星行：`LBA7` / `CLARITY-Gastric01` / esid `24_37_p_7d7447832f67fec70aaba31bc4cf721b_1`。

错因写进 `pitfalls.md §36`：当时拿一份旧 schema dump `grep` 不到就断言「表里没有这一列」，之后被自己写的文档反复说服。**负向结论的举证责任在提出者**，一次 `selected_fields` 实测就能证伪。

### 改动（数据层 → 闸门 → 交付）

1. **`pull_results.py`**：`DEFAULT_FIELDS` 加两字段；两处汇总打印 `is_recommand=` / `abstract_id=`；`rec == 0` 时打 NOTE（「absence of the flag is not evidence that nothing was recommended」）；末段三条缺列 WARNING。
2. **`triage.py`**：新增 `recommand_of()`（**`None` ≠ `False`**）；`forced` 行绕过 `excluded_reason` / TiP / `mm:` 独有排除，`bucket is None` 兜底落 `pivotal`；去重时标星行不输给同试验兄弟；排序键 `(forced, presentation_rank, -n, …)`；`pool.json` 顶层 `recommand: {flagged, column_present}`。
3. **`make_cards.py`**：卡片透传 `is_recommand`；`tag` = `推荐` 优先、其次 `LBA`。
4. **`check_cards.py`**：`abstract_id` 三态校验（缺失 / 与 rows 不符 / 凭空发明）+ `is_recommand` 布尔与一致性；新增 `recommand_gate()`（覆盖 + 顺序，**不吃 `editorial_overrides`**）。
5. **事实层**：`A-F1-abstract-id-null`（要求全 null，方向已反）→ **`A-F1-abstract-id-traceable`**；新增 **`A-P7-recommand-forced`**；`op_score_order` 从「降序」改成「标星优先、同类降序」；新增 mutation `m_recommand_dropped`。事实层 28 → **29 条（28 fail + 1 warn）**，`coverage: 28/28`，NEG 8 条仍绿。
6. **测试**：`test_check_cards.py` 40 → **46 case**（强制位覆盖/置顶、空列只是 note、`abstract_id` 三态、`is_recommand` 不许自宣）。
7. **文档**：`SKILL.md`（Step 1 字段、Step 3 撤销旧结论 + 强制位段、Step 5B 排序键与卡片键、Anti-patterns、v0.12 变更记）、`pitfalls.md §36–§38`、`data-contract.md §6.5.4`、`review-protocol.md`、`screening-rules.md §1.0`、`templates/watchlist-report.md` 规则 7。

### dist

`dist/conference-result-triage-v0.12.zip` — **142389 B / 16 entries / sha256 `354f8183c6ceebe1`**。

### 发布

2026-11-16 原地更新（`mode=in-place`，label 仍 `v0.3.0`）：`skill_id=230463cbc03d4fe5ba0e2e8964fe91dd`，`commit_id` 递增，
`entries=16 identical=16 differing=0`，**`STATUS: in sync`**。发布前 `guard OK`（共享 SP `d08570e9…` 只读，未写）。

### ESMO 2026 实跑（`20261116-162537-cards-ESMO-26-v12`）

1097 条记录、**28 min**、107 次工具调用、**24 PASS / 0 FAIL** 平台断言、**facts 28/28 + warn 1/1 PASS**、
交付 **30 卡（10/10/10）**，`check_cards.py --judged <work>` **EXIT=0**。

- 强制位生效：全场唯一标星 `LBA7` / `CLARITY-Gastric 01` 判读只 **81 分**，仍排在 95 分的 DeLLphi-305 之前（桶内首位），`tag=推荐`。
- `abstract_id`：30/30 非空且与 `rows.json` 逐字一致（R11/R12 的 EASL/ESC 全是 null —— 不是那些会没有摘要号，是没请求）。
- `coverage_notes` 第三条把三态说全：列已拉取 / 1097 行 1 行标星 / 未标星 ≠ 无价值。
- 选择闸门：floor 早期 69 / 重磅 81 / 失败 73，舍弃的更高分 keep 1 + 11 + 0 = **12 条全部写进 `editorial_overrides`**（12 条 overrides，最短 39 字）。

### 待办

- [ ] **卡片「期别未标注」丢了推断依据**：`LBA7` 的 `phase_inferred=随机化对照（按设计判定）`，报告正文只印「期别未标注」。数据层没错，是渲染措辞没照抄 → 下一轮把三种取值写死在 Step 5 渲染说明里。
- [ ] **判读文件命名仍在漂**：ESMO `judged_G01..G19 + judged_all.json` / EASL `judged_01..14` 无 `_all` / ESC `judged_a..f`。`--judged <目录>` 三种都能读，但要跨场自动化需统一。
- [ ] 用 v0.12 补跑 ADA 2026，补齐四场对照

## v0.11（2026-11-13）：同场评分暴露「判读对、选择错」——定榜必须按判读分取前 k

v0.10（多疾病领域三场并行）之后，把同一份 skill 在 ADA / ESC / EASL 2026 三场重跑一遍（run dirs
`20261113-092008-cards-*-v10`），按「**同场**评分」逐场核：卡片 `score` 与判读 `score` **62/62 全相等**
（ADA 14/14、EASL 24/24、ESC 24/24），所以缺陷不在「分被改写」，而在**「选了谁」**：

| 会议 | 桶 | 入选卡 | floor | 被舍弃、但判读 `keep` 且分更高的条目 |
|---|---|---|---|---|
| ADA 2026 | pivotal / failed | 10 / 2 | 71 / 52 | **5**（77 `HR17031-301`、74、73、73；failed 1 条 72） |
| EASL 2026 | pivotal | 10 | 74 | **3**（85 `PEMA-PBC`、79、76 `TRUTH`） |
| ESC 2026 | pivotal | 10 | 54 | **8**（73 `SYH2053-002`、65 `FINO-HF`、65 `VICTORION-Difference`…） |

三场 16 条，全都没有一句解释。**所有闸门只问「合不合法」，没有一条问「是不是最优的那一版」。**

同轮 GT 比对（同源 web provider，按 esid 匹配，三态「上榜 / 库内有未上榜 / 库里没有」）：ADA 9→4、
ESC 7→5、EASL 11→4；逐条读下来 14 条「真漏」里 12 条是**判读正确地判低**（`ASSURE` 只看血脂 → drop 32、
`NAVIGATE` 主终点未达 → weak 35、`ACHIEVE-2` 差 1 分落榜），另 2 条可争议。唯一确凿的判读错误是
`ENSURE`（随机、功能治愈 17% vs 6%、n=55）因「每组仅 18 例」被打成 `weak` 65，而同场「单臂 22 例 45.5%」
是 keep 68 —— **用 n 当了判决器**，与「`n` 不是纳入闸门」直接冲突。

改动（四项 + 文档）：

1. **判读契约加 `esid`（八键 → 九键）**：三场判读产物都没有 `esid`，`i` 是批次内序号（ADA 每批从 1 重数、
   ESC 全局 1..164），「85 分那条去哪了」只能靠猜批次对齐 —— 定榜的人反过来能换一份批次改答案。
2. **`check_cards.py --judged` 必传 + `selection_order()`**：逐桶算 `floor = min(入选卡 score)`，任何
   `keep` 分 > floor 却没上榜、且没进 `editorial_overrides`（`reason` ≥10 字才算）→ 判失败；CLI 侧拿不到
   可用判读 → **fail-closed**（in-process 侧只记 note，因为 CLI 才是交付路径）。`load_judged()` 只认
   `startswith("judged")` 且带 `verdict`+`score`+`esid` 的文件，避免把同目录 `selected.json` 读成「没人被判 keep」
   的**空对空通过**。
3. **`make_cards.py` 从 `plan.json` 顶层搬 `coverage_notes` / `editorial_overrides`**，不许渲染完手改 JSON。
4. **事实层 `A-P6-selection-order`（28 项）+ `m_selection_order`**：mutation 抬**被跳过者**的分（抬已入选卡会
   先被 `A-P4` 抓，验不到新项）；夹具里另放两条「合法输掉」的 keep（低于本桶 floor）当负控。
5. **判读纪律**：`review-protocol.md §2.5` + `SKILL.md` Step 4 写死「样本量只进 `evidence_strength`，不进
   `verdict`、不压 `effect_size`；`weak`/`drop` 的 `reason` 里只有『仅 N 例』不算理由」；`pitfalls.md §34`；
   `data-contract.md §6.5.3`（两个顶层键）；`watchlist-report.md` 硬规则第 6 条。

测试：`test_check_cards` 33 → **40 case**（7 条选择用例，含 `load_judged` 不许读 `selected.json`）；
`mutations.py` **27/27 + 8 负控绿**；`test_triage` 仍绿。
v0.11 包：`dist/conference-result-triage-v0.11.zip` **133599 B / 16 entries / sha256 `7389e00880a6a85f`**。
**已原地发布（in-place，平台 v0.3.0，`status` → in sync，16/16 identical）。**

重跑验证（R12）：EASL 2026 `…094709-cards-EASL-26-v11`、ESC 2026 `…094710-cards-ESC-26-v11`。
两场判读 **136/136、164/164 全部带 `esid`**；pivotal floor 74→**81**（EASL）、54→**62**（ESC）；
舍弃更高分 keep 的违规 3→**0**、8→**1（已写 `editorial_overrides`，reason 78 字）**；事实层两场
**25/25 PASS**（含新增 `A-P6-selection-order`）。EASL 唯一那条平台 FAIL 是交付后又调 `write_todos`
（`present_artifact` 不再是最后一个成功调用）→ 已写进 `pitfalls.md §35` + `SKILL.md` Step 7。

## v0.10（2026-11-13）：跨疾病领域三场并行 E2E 暴露的问题，一次修到底

用户要求「多试几个不同疾病领域的会议推荐清单，拿 TS 的推荐与本地联网查到的大会热议内容比对，不符合就优化 skill」。
选 ADA 2026（代谢）/ ESC 2026（心血管）/ EASL 2026（肝病）三场并行跑同一份 skill、只换 `meeting_tags`
（run dirs `20261112-181722-cards-{ADA,ESC,EASL}26`）。三场都交付了，但暴露三类缺陷：

| 现场 | 事实 |
|---|---|
| 候选池缩水 | 旧 `bucket_of()` 在 `phase` 匹配不上时 `return None` → 落进 `excluded["无法归类"]`：**ESC 242 条丢 123（51%）**、ADA 丢 40、EASL 丢 55。丢掉的包括 `ACACIA-HCM`（mavacamten）、`ENRICH-AF`（因子 XIa）、`SAL003`、`bepirovirsen`、`pemvidutide` —— 整个会议的主线 |
| 成员资格被绕过 | ESC 现场出现 `work/pool/build_pool_ext.py`：模型把 110 条它认为"被误杀"的记录塞进手造 `pool_ext.json` 当 `--pool` 传进去。卡片闸门全绿，事实层报 9 个未知 esid + 61 个不可溯源数字 |
| 引文两场全红 | ESC/EASL 都红在 `every ref marker has a citation entry`（`markers=3 keys=0`）。**根因不在 skill**：runner 用 `deliverables` 配置决定要不要读 `citations.json`，而配置里没有这一项 → `cites={}` → 拿 3 个标记去比 0 个键。同时文档漏写平台要的 `paper_release_time_str` 键，13 条引文写成 `{title, link}` |
| 别名的假越界 | ESC 有一张卡写 `VESALIUS-CV` 的预设亚组分析，与主发表同 trial；`build_pools` 去重后兄弟 esid 消失 → 卡被判"外来记录" |

修法与验证：

1. **`triage.bucket_of()` 尾部无条件 `return design_bucket(row)`**：`随机化` 或 `平行分组/交叉设计/析因设计` → `pivotal`，其余真试验 → `early`，写 `phase_inferred`；`phase` 不动。候选量 191→138 / 242→164 / 214→135，`无法归类` 三场归零，抽查 6 条主线试验全部回归。
2. **`check_cards.py --rows` 改 `required=True`**，新增 `recompute_pool()` 用 shipped `triage.build_pools` 现场重算成员资格，`--pool` 降级为展示来源。测试 case 25 复现了手造 pool 被推翻；修这个时又踩到 `(by_calc or by_esid)` 在 `by_calc == {}` 时静默回退 —— 改成 `is not None`（同一个 bug 形态第二次出现）。
3. **引文三键契约**：`check_cards.py --report output/report.md` 复核 frontmatter 键、`{{ref_N}}` ↔ `citations.json` 双向、每条恰好 `{title, link, paper_release_time_str}`（`YYYY-MM-DD`）；事实层 `A-C2` 同口径（`EVALUATOR_REVISION` → `r6`）。runner 侧开关从「配置声明的 deliverables」改成「归档里有没有这个文件」。
4. **去重别名**：`build_pools` 在胜出条目上记 `alias_esids`，`recompute_pool` 把 alias 映射到同一条目（标 `_alias_of`），成员资格仍由 `rows.json` 决定。修后三场卡片全部有池子背书：ADA 18/18、ESC 26/26、EASL 20/20。
5. 领域无关化：单位表扩到 `mg/dL`/`mmol/L`/`mL/min`/`IU/mL`/`points`；判读 `verdict` 给六领域水位表并写明「表里没有就按主终点+效应量自判，不套肿瘤阈值」。

测试：`test_triage` 夹具 4→6 行（补 phase-less 随机化 HF + phase-less 单臂 HBV）+ 去重别名断言；
`test_check_cards` 23→**33 case**（含 7 条 report 引文闸门）；`mutations.py` 25/25 + 8 负控绿。
v0.10 包：`dist/conference-result-triage-v0.10.zip` **126956 B / 16 entries / sha256 `3a1810ccc1fe2507`**。
**待用户授权后 publish，再用 v0.10 重跑三场 E2E。**

## v0.9.2（2026-11-13）：E2E #8 全绿，并修掉「交付前闸门比事后校验宽」

E2E #8（`cards-e2e8`）是项目改挂共享 SP 后第一个跑通的回合（831.5 s / 74 steps / `succeeded`），`verification.md`
`24 PASS / 0 FAIL / 0 WARN`。事实层暴露一个真缺陷：`A-F4-numbers-traceable` 抓到 4 个数字（`44%` / `24%` / `16 个月` / `43 个月`，
原文分别是 `44.7` / `24.5` / `16.1 mo` / `43.6 mo`，模型自己四舍五入），而**同一份 JSON 在平台内 `check_cards.py` 是 exit 0**
—— 因为卡片闸门当时用子串匹配（`"44" in "44.7"`）、事实层用数值相等。修法两侧同源：

- `check_cards.py` 数字溯源改**数值比对**；新增 case 21–23（prefix 陷阱、逐字小数通过、中文月单位）⇒ 23 case 全绿；
  对 e2e8 原产物重跑 `FAIL (4)` ⇒ **fail-closed 恢复**。
- 事实层 `NUM_RE` 单位枚举补 `个?月`（原来只认 `月`，「16 个月」整段被跳过；英文 `16.1 mo` 却能抓到）⇒ `A-F4` 2→4 条。
- `mutations.py` 加 `m_number_round` + NEG `ngen_decimal_places` ⇒ 25/25 + 8 负控全绿；`EVALUATOR_REVISION` → `r5`。
- `SKILL.md` / `pitfalls.md §28` 记下口径：**照抄原文小数位**，要写"约/逾"就把原数原样放进去（`16.1 个月`，不写 `16 个月`）。
- `toolsmith-publish` 的三处验证器缺陷同轮修完（`prose_gate: false` 声明、manifest 以 shipped zip 为准、
  `--resume` 的 receipts 继承与重建、`web tools` 头部以 `run.json.enable_web` 为准）。

v0.9 包重新打包：`dist/conference-result-triage-v0.9.zip` 113079 B / 16 entries / sha256 `4f2ac9e5aefc67a1`。
**未改版本号**（原地更新语义）。下一步：重新 publish + E2E #9，以 `facts 26/26` 为通过条件。

## v0.9.1（2026-11-13）：项目改挂共享系统提示词，按「只读它、绝不写它」重建护栏

用户已自行完成平台侧动作：项目 `d1c193d7809d4c04ba5423942523f91c` 的 `prompt_id` 改绑到**「PharmCube AI Chat SP」的当前版本**（family `d08570e93c17466ca6a0308f69afdb5d`，owner 文超，`current_version_id=41132120…` = v1.0，29169 B / sha `a2b1581ef7cd`），**我们原来的 prompt family `3fa0f27e…` 已删除（GET → 404）**。平台侧修 ownership 无望（问题单已交，见下），于是改为本地自保。

| 面 | 改法 |
|---|---|
| 硬阻断 | runner 新增 `FOREIGN_PROMPTS = {d08570e9…}`：`assert_owned_targets` **第一段**就拒，且同时检查 `a.prompt_family` 与命令行传进来的 `cli_prompt_family`；`do_push_prompt` 再兜一层。**拦的是 id 本身**，不是配置路径——`--prompt-family d08570e9…` 也 abort（实测两种入口都 `ERROR: refusing to write`） |
| 配置 | `~/.config/toolsmith/projects.json` 本项目条目：`prompt_family: null` + `shared_prompt_family: d08570e9…` + `shared_prompt_pin: {version: "1.0", version_id, sha256: a2b1581ef7cd…, bytes: 29169}` |
| `publish` | shared 模式下**跳过 prompt 推送**（打印 SKIPPED + 原因），只推 skill；`guard OK` 行改为「skill family 是我们的；prompt 是共享 SP（owner 文超，v1.0，sha），只读、永不写」 |
| `status` | 新增 `status_shared_prompt()` 三段证明：① 线上 current 版本 sha == 钉住的 sha（**owner 原地改内容会在这里炸**，因为平台不会升版本号）；② 项目仍绑在那个 version id；③ `agent/info.instructions` **仍以该 SP 文本开头**（证明 agent 真的跑在这个提示词上）。缺失的面 → SKIP，不自动 PASS |
| `run` 断言 | 「deployed system prompt == local」在 shared 模式下会**永远假失败**（我们不再发布那个文件）→ 换成两条：`deployed system prompt == shared SP`（首字节前缀）+ `project prompt is the shared SP, not our repo file`（`system-prompts/*.md` 只是本地参考，不得出现在 deployed 里） |
| 仓库里的 v0.9 系统提示词 | 降级为**本地参考**：内容已全部搬进 `SKILL.md`，不再发布。留着它是为了让「skill 自己承载规范」可审计（哪天要切回自管 prompt 还能用） |

**发布结果（原地更新，未新建版本）**：`toolsmith-publish publish` → prompt SKIPPED，skill `v0.3.0` / skill_id `230463cbc03d4fe5ba0e2e8964fe91dd` / `POST /api/skills/update_skill_file → 200`，回读 **16 entries / identical=16 / differing=0**，`STATUS: in sync`。

**平台侧问题单**（prompt 无 owner 校验、`project_manager` 带 `skill:manage`、`is_current` 缺失时静默 200、`current_version_id` 可指向更小的版本号）全文在 Obsidian `03-技术与VibeCoding/01-AI与LLM/TS平台问题单-提示词资源缺ownership维度-项目管理员跨作者可写-2026-11-13.md`。

## v0.9（2026-11-13）：删掉整个行情层，交付物改成带 `skills` frontmatter 的 Markdown 报告

两条需求都来自用户，方向相反于 v0.8：**v0.8 花了一整版把涨跌幅做精确，v0.9 把它整块删掉。**

**需求 1（用户）**：「查股价」这个功能跟会议结果压根没关系 → 移除。**需求 2（用户）**：后续 `ts` 系列 skill 不再各带系统提示词，统一挂「PharmCube AI Chat SP」，细节全部下沉到 SKILL.md；同时结果识别改用 `skills` 数组 + 独立 `citations.json`（依据《产品经理使用 Skill 的通用约束》）。

**为什么是删而不是修口径**（这条要留档，否则下一版会重新长出来）：按每条摘要自己的披露日重锚、并扣掉所属市场板块基准后，**24 条行情里 18 条落在 ±0.6% 内**；同一公司的多张卡拿到**同一个**数字（MRK 8 张卡全是 −3.83%），因为涨跌属于公司那一刻，不属于任何一条读数。精确的 beta 仍是 beta，且越精确越容易被读成信号。

| 面 | 内容 |
|---|---|
| 删除 | `scripts/fetch_quotes.py`（整文件）、`listed_company.reaction`、卡片 `stock`、`work/web/quotes.jsonl`、`check_cards.py --quotes-evidence` 与 `_check_reactions()`/`REACTION_FIELDS`/`REACTION_TOLERANCE`、事实项 `A-F7-reaction-traceable`、`build_review_page.py` 的行情 chip、SKILL/review-protocol 里的东财 kline 端点与 secid 前缀表 |
| 保留 | `listed_company` = 纯身份 `{name, ticker, exchange, source_url}`；`ticker` 仍只写裸代码，`MARKET_SUFFIXES` 闸门不变 |
| 防回潮 | `check_cards.py` 扫 `PRICE_KEYS`（`stock`/`reaction`/`change_pct`/`excess_pct`/`bench_change_pct`/`price_source`）→ 卡片与 `listed_company` 任一处出现即 FAIL；事实项 **`A-N1-no-price-claims`**（mutation：把 `reaction` 塞回一张卡；NEG：只写身份字段仍绿） |
| 交付物 | `/workspace/output/report.md`（Markdown + YAML frontmatter `skills`/`title`/`date`/`lang`[/`citations`]），`watchlist.json` 降为数据底稿。`present_artifact` 指向 `report.md` |
| 结果识别 | **`skills` 非空数组，只写这一回合真跑过的 skill**，取代旧的业务 `type`；`A-C2-report-frontmatter` 双 mutation（用 `type` 顶替 `skills` / 正文 `{{ref_1}}` 无条目）+ NEG「声明引文且双向对得上仍绿」 |
| 引文 | 正文只写 `{{ref_N}}`，标题/链接/日期只在 `/workspace/output/citations.json`，双向一一对应；**没有可引用来源就不写 `citations`、不留 `{{ref_…}}`**（平台拿不到摘要链接，编一个更糟） |
| 排序 | 每桶输出前按 `score` 降序（`A-P4-score-order` 的根因是模型漏排，不是评分规则错）；`make_cards.py` 只渲染不排序 |
| 打包 | `pack-dist.py` `VERSION=v0.9`，并把 `scripts/make_watchlist.py` 列入 `EXCLUDE`（v0.1 的 md/csv 渲染器，不认识 cards/`listed_company`/`promoted`，留在仓库但不发布）→ **16 entries** |

**验证**：`evals/test_check_cards.py` **20 case 全绿**（identity-only 通过 / `reaction` 回潮被拒 / `stock` 回潮被拒）·
`mutations.py` **coverage 25/25 fail items + 7 NEG green** · `pack-dist.py` → `dist/conference-result-triage-v0.9.zip` **16 entries / 111674 B / sha256=dc88978b67b2d6c9**。

**平台侧问题单（2026-11-13，已全文交用户转开发）**：用户要求把系统提示词改挂共享的「PharmCube AI Chat SP」（`d08570e93c17466ca6a0308f69afdb5d`，owner 文超），核查「我们能不能改到它」时查出平台缺陷 —— **prompt 只有一把全局 `prompt:write`，服务端零 owner 校验**（`prompt_routes.py` 四个写接口只到权限层），而 `project_manager` 角色恰好持有它；同一角色还带 `skill:manage`，按 `_ensure_editable` 的实现也可绕过技能 owner 判定。附带两条：无 `is_current` 行时原地更新静默返回 200（`update_current_prompt_content` 的 bool 被 route 丢弃）；`current_version_id` 可指向版本号更小的行（实测该 SP current=1.0 而 1.1 存在），「取最大版本号」的调用方会拿错。全文与证据（文件:行号）在 Obsidian `03-技术与VibeCoding/01-AI与LLM/TS平台问题单-提示词资源缺ownership维度-项目管理员跨作者可写-2026-11-13.md`，仓库只留此摘要。**自保**：runner 三重护栏（CLI family 必须等于配置 / `owned: true` / 平台 owner 比对）+ 不把共享 family 写进任何写目标位 + 对共享 SP 钉 sha 做漂移检测。

**遗留（待用户拍板）**：项目 `prompt_id` 是否切到「PharmCube AI Chat SP」`d08570e93c17466ca6a0308f69afdb5d`（v1.1 仅 3268 chars，不含交付物规范——规范已全部搬进 SKILL.md，但切换是平台写动作，需授权）；不切则继续用本仓库 `system-prompts/` 的 v0.9 版本。

## v0.8（2026-11-12）：`reaction` 从短句变成带口径的行情对象

**起因**：用户看完 v0.7 的复核页只问了一句「怎么只查到股票代码，没有对应的事件日涨幅」。

**复盘 e2e6（108 次工具调用）**：`web_search` **0 次**，`web_fetch` **29 次全部**落在公司 IR 落地页
（`merck.com/investor-relations/stockholder-services` 这类只有代码、交易所、过户代理的页），
所以不是"没查"，是**查错了页面**。另有 3 个真实障碍叠加：`106.AMGN/JAZZ/ELTX` 的 secid 前缀不对（`rc:100`）、
SIX（Roche）东财完全不覆盖（`rc:102` × 12 个候选前缀）、`make_cards.py` 需要 `--quotes` 才有 `stock`。

**改了什么**

| 面 | 内容 |
|---|---|
| 端点 | SKILL.md / 系统提示词 / review-protocol 三处都写进东财 kline JSON：`push2his.eastmoney.com/api/qt/stock/kline/get?secid=<mkt>.<code>&fields1=f1,f2&fields2=f51,f53&klt=101&fqt=1&beg=&end=`，附 secid 前缀表（105/106/107/116 补零 5 位/155）与 `rc:100`/`rc:102` 语义 |
| 口径 | 涨跌幅 = **该市场**早于会议首日的最后收盘 → **该市场** ∈ 会议窗口的第一个收盘；`from_date`/`to_date`/`basis` 必须印进 JSON，`basis` 写「非归因」。**不许写成"因为这条摘要涨了 X%"** |
| 分市场基准 | 各市场休市日不同（台风/黄金周/祝日都会让某天的 K 线直接缺席），一个全局基准日会静默算错；会议首日必须查（ESMO 2026 = **10-23 至 10-27，IFEMA Madrid**） |
| 不覆盖就留空 | SIX 省略 `reaction`；**禁止**用 OTC ADR `RHHBY` 近似 `ROG.SW` |
| 数据形状 | `listed_company.reaction` = `{from_date,to_date,prev_close,close,change_pct,basis,source_url}`（7 键）；省略合法 |
| 闸门 | `check_cards.py --quotes-evidence` 验「`change_pct` 能否由 `prev_close→close` 算出（0.05pp 容差）」+「能否在 `work/web/quotes.jsonl` 里按 `ticker + to_date` 对上」；不给证据文件却印了数字 → 直接 FAIL |
| 事实层 | 新增 `A-F7-reaction-traceable`（fail，双 mutation：涨跌幅篡改 / 证据文件缺失）→ **24 fail + 1 warn**；NEG「reaction omitted entirely」保证「拿不到行情」不会退化成「暂不交付」（6 → **7** 条 NEG） |
| 本地预计算 | 新增 `scripts/fetch_quotes.py`（3 次重试，实测 24/26 张卡拿到行情，2 张 RO/SIX 按设计 skip）；`make_cards.py --quotes` 把 `reaction` 折进 `listed_company` |
| 顺手修的 bug | 占位符扫描原来对 `json.dumps(card)` 做子串匹配 → **任何把嵌套对象放最后的卡都因字面量 `}}` 被判"占位符泄漏"**；改成只扫叶子字符串 `leaf_text()` |

**验证**：`evals/test_check_cards.py` **19 case 全绿**（新增 4 条 reaction 用例）·
`mutations.py` **coverage 24/24 fail items + 7 NEG green** · e2e6 旧产物重判 **facts 24/24 warn 1/1 -> PASS**（无 reaction 走合法分支）·
`pack-dist.py` → `dist/conference-result-triage-v0.8.zip` **18 entries / 116751 B** · `toolsmith-publish publish` 原地更新后 **STATUS: in sync**
（prompt v1.0 21856 B sha `04ab6bf97e76`；skill v0.3.0 18/18 identical）。

**为什么 `reaction` 是增强项而不是必填**：行情端点会挂、交易所会不覆盖、公司可能根本没上市。
把它设成必填，代价是又一次「查不到 → 暂不交付」（pitfalls §24 的原始教训）。

## v0.7（2026-11-12）：15 → 10 的编辑收敛、`why` 变判断、上市公司字段

三处改动都来自「45 张卡交出去之后读者会问什么」，而不是脚本能算出来的东西。

| 改动 | 为什么 | 落成什么 |
|---|---|---|
| **两段收敛**：机器短名单 15/45 → **交付清单 10/30** | 15 条是防止池子变倾倒场的天花板，但它不是阅读上限；一份 15 条的清单读不完，10 条的会 | `check_cards.py` `PER_BUCKET_CAP=10` / `TOTAL_CAP=30`；`work/shortlist.json`（≤15）与 `work/plan.json`（≤10）分开 |
| **联网终选（Step 5B）** | 只从会议库挑，永远不知道会议室里真正被讨论的是哪一条，也不知道研发公司是上市公司、披露当天股价怎么走 | 每桶 ≥6 次 `web_search`，证据落 `work/web/<bucket>.jsonl`；允许 `promoted:"web"` 把池外记录提上来（必须在 `rows.json` 里） |
| **`why` 从标签变判断** | 「报告了主要终点读数」等于没写；读者要的是「这项研究值什么」 | `MIN_WHY_CHARS=60`、2–4 句、禁止与 `summary` 互相包含前 20 字 |
| **`listed_company`** | 这类读数是股价的重定价日；查不到就该空着，而不是让读者猜 | 每张卡必有该键，非 null 时 `name/ticker/exchange/source_url` 齐全且 URL 可解析 |

**实探到的坑**：平台的 `web_search`（模型侧可能显示成 `web.run`）有**双重开关** —— 项目 `capabilities_config.web=true`
**且** 回合 `enable_web=true`。只开前者时模型看到的工具表里根本没有检索工具，它会一路"没有联网工具"地编下去；
`debug-history.json` 里 `web_search` 只出现在 prompt 与回复里、零条工具定义。`settings.WEB_SEARCH_API_KEY` 为空时是
**返回一条 message**（`WEB_SEARCH_NOT_CONFIGURED_MESSAGE`），不是隐藏工具——两种现象要分开报。

**事实层**：19 → **23 条 fail 项 + 1 warn**。新增 `A-P5-why-depth`（短 / 复写 `summary` 两个分支）·
`A-F5-listed-company` · `A-F6-promotion-traceable` · `A-W1-web-evidence`，各配 mutation；NEG 从 2 条加到 4 条
（合法的桶间重排、热点标题、`why` 踩 60 字下限、带交易所来源的港股公司）。`EVALUATOR_REVISION = 2026-11-12-r2`。
基线 `facts 23/23`，`mutations.py` 输出 `coverage: 23/23 fail items have a mutation; 4 negative controls green`。

**端到端（2026-11-12）**：v0.7 原地发布（prompt v1.0 in-place / skill v0.3.0 in-place，`STATUS: in sync`）后跑了两轮。

| 轮次 | 结果 | 暴露的缺陷 |
|---|---|---|
| `cards-e2e5` `20261112-105154` | **零交付**（1097 行取数 + 592 条判读都完成，`output/watchlist.json` 不存在） | `web_fetch` 打开 amgen.com 失败后，模型把「一个 IR 页打不开」读成「检索整体不可用」，写下"暂未交付最终 JSON"并结束回合。**文档只写了"要联网核实"，没写"核实不了怎么办"** → 三处补「降级不中止」条款 |
| `cards-e2e6` `20261112-111250` | **`facts 23/23 -> PASS`**；28 卡（10/10/8）；`work/web/*.jsonl` 26 行 / 18 行带 URL；`listed_company` 26/28；`why` 132–160 字 | `A-W1` 原要求「每条检索记录都带 URL」，把「查了但没结果」的如实记录判成漏证（先假红一次）→ 改为「总行数 ≥6 ∧ 带 URL 行 ≥6 ∧ 无 URL 行必须写 note」，并补 `m_web_no_urls` mutation + NEG「零结果但已注明」 |

`e2e6` 未出现 `promoted` 卡片：外部讨论没有改变入选集，模型把 CS2009 的外部更新写进 `coverage_notes`（"会议库只有初步小队列，未用外部数字补写卡片"）。
NEG 从 4 条加到 **6 条**（新增「检索零结果但已注明」「联网不可用但已声明」）。

**未做**：`featured` 白名单仍是 dev ticket（`manual` 恒 `null`）；`scripts/make_watchlist.py` 已从发布包 `EXCLUDE`（v0.1 遗留，不发布即不需同步）；`plan.json` 的 `editorial_policy.max_cards_per_bucket` 仍是 15（机器短名单上限，交付上限在 `check_cards.py` 里是 10，两者不再混用）。

## v0.6.1（2026-11-12）：原地重跑两次，facts 19/19 全绿

v0.6 发布后原地跑全量（592 候选 / 40 批），**第一次 `facts 16/19`，暴露的三个面全部修掉后第二次 `19/19`**。

| 失败项 | 现象 | 性质 |
|---|---|---|
| `A-D4` | `73 lba rows … 19 dropped` | **审计脚本 bug**：比对键用 `extra_esid`（无 `nr_`），池内键是 `_id`（带 `nr_`）→ 归一后 73/73 |
| `A-D2` | `0 sliced calls` | 分片在 `task` 子代理里跑，父回合只看到 id-only 调用；v0.5 依赖的 `slice_counts.json` 这次没写 |
| `A-H1` | `0 notes` | 模型把边界写进 `coverage.boundary`；而 `coverage_notes` **在 SKILL.md 里从没定义过**（v0.5 是运气通过） |

修法（一律修面，不修阈值）：

1. `pull_results.py` 让 `rows.json` 自带 `sources`（每 dump 名 + 行数）——分片证据随数据走，不再依赖调用方记得写账本。
2. `check.py` 分片项改三级回退：`work/slices/slice_*.json` → `rows.json.sources` → 父回合调用；并要求切片 id 与 `rows.json` id **双向相等**。
3. 两条诚实声明升级成闸门：`check_cards.py` 要求顶层 `coverage_notes`（措辞不查，只查事实），同时把 schema 补进 SKILL.md / 系统提示词 / `Deliverable schema`——先有定义才有闸门。`evals/test_check_cards.py` 加 3 例（缺字段 / 少一条 / 合法改写必须过）。

**交付基线**：prompt `conference-result-triage-v0.6.md`（v1.0 原地更新，sha `4a65bf34c51a`）、skill v0.3.0 / dist 17 项、`status: in sync`。
**run 2 `cards-e2e4`**：1520 s、55 次工具调用、45 卡（15/15/15）、17 个不同分数、`facts 19/19 warn 1/1 -> PASS`、VOLGA / KRASCENDO-1 / CLARITY-Gastric01 全部进榜。
**未做**：45 张卡的人工可读性复核；`featured` 白名单（`manual` 恒 `null`）。

**复核页（2026-11-12）**：把 run 2 的交付物渲染成单文件 HTML 供人工读，
`dist/review/esmo2026-watchlist.html`，生成器 `dist/review/build_review_page.py`（只读 `output/watchlist.json`，
不改判读结果）。**只渲染 45 条 card 记录本身**：桶 / 分数 / `title` / `summary` / `why` / `key_numbers` /
`evidence` 以及卡片自带的 `tag`、`phase`、`presentation`、`drug`-`target`-`indication`、`data_type`。
不做漏斗、不做分布图、不重算覆盖率、不抄 `coverage_notes` 或 `verification_points`——
用户口径：**“我只想要推荐卡片，用输出的那 45 个 JSON 组织就行，不需要额外补充字段”**（第一版把派生统计和图都画上了，被否）。

## v0.6（2026-11-11）：排除规则的静默删除 + 事实层首次落地

**被外部热度对照逼出来的真缺陷**：`excluded_reason()` 用 `evidence_source` 判断研究类型，
而平台没有独立分期列——`evidence_source` 就是分期来源，**73 条 ESMO 2026 LBA 里有 16 条该字段填的是研究设计「前瞻性研究」**。
把它放进 `NON_TRIAL_SOURCES` 黑名单的后果是 VOLGA（LBA2）/ KRASCENDO-1（LBA5）/ CLARITY-Gastric01（LBA7）
三场 Presidential 整类消失，而交付物仍报 `coverage: 1097/1097`（分子分母都取自同一份已取数据，能自证一致，证明不了完整）。

| | 修前 | 修后 |
|---|---:|---:|
| 候选 | 551 | **592** |
| pivotal / early / failed | 292 / 200 / 59 | **306 / 200 / 86** |
| excluded 中 `前瞻性研究` | 252 | **0** |

修法：黑名单只留 回顾性/真实世界/汇总分析/Not Applicable/其他；分期缺失的行交 `bucket_of`，`lba` 为真进 pivotal，
**期别字段不改不猜**，卡片照实写「未声明」。`--top/--limit-per-bucket` 降级为**试跑专用**（ESMO 2026 设 60 会切掉 pivotal 第 64 名 SAFFRON）。

**质量层从布尔门升级成标量**：新建 `evals/fact-check/{check.py,facts.json,mutations.py}`（移植 `clinical-result-comparison` 的范式）：
`EVALUATOR_REVISION = 2026-11-11-r1`，**20 项 = 19 fail + 1 warn**，**19 个 mutation + 2 个合法变体负对照**全部有牙（`mutations.py` exit 0）。
对真实跑批 `cards-e2e2`（41 卡）实测 **18/19**，唯一失败项 `A-D4-lba-not-dropped` 报的就是上面那个缺陷
（`73 lba rows in the corpus, 37 in the pool, 50 dropped, phase-as-design exclusions=['前瞻性研究']`）。

**外部热度对照**：同一份 X 检索（23 帖 / 112 提及），12 个 Presidential LBA 命中 v0.2 **0/12** → v0.5 **7/12** → v0.6 池内 **12/12**。
5 个漏项分三层：上限（SAFFRON，`--top 60` 切掉）/ 分组（HERON-Lung01，keep 86 分 vs 榜尾 87 分）/ 分类（三场 Presidential，即上述缺陷）。
详见 `dist/v06/heat-check-v06.md`、`evals/EVALUATION_RESULTS.md`。

**未做**：v0.6 尚未发布 TS、尚未重跑 E2E（12/12 是**池内**结论，不是榜单结论；目标 `facts 19/19`）。

## 平台内实跑验证（2026-11-11，v0.4）

**数据层已在 ToolSmith 真跑打通**（标签 `slice-e2e`，模型 `GPT 6.1 Sol`，606 s，31 次工具调用，9 次落盘 18.4 MB）：

```
rows=1097 lba=73 with_abstract_text=1097 -> /workspace/work/rows.json
coverage: 1097/1097 ids present
self-test: OK
candidates 551 / missing abstract 0
```

两条实测硬事实（写进 SKILL.md Step 1、系统提示词 step 2、pitfalls §21）：

| 事实 | 证据 |
|---|---|
| **工作区没有网络** | `172.17.26.74:30080` → `Network is unreachable`；公网 → `gaierror -3`；`env` 无 MCP 端点。脚本不能自己连数据服务 |
| **宽字段一次拉静默截断** | 32 字段 + `meeting_tags` 只回 **458/1097**，`ok: true` 无报错；id-only 回全 1097 |
| `selected_fields` 混入线上白名单外的名字 | `research_design.evaluation.text` / `base.abbreviation_label.text` → 整次调用 `INVALID_INPUT`，**一行都不回** |
| `featured` 取不到 | 不在白名单；`TEST_execute-sql` 不能绑项目（400） → `manual` 恒 `null`（三态，`check_cards` 拒绝改成 true/false） |

**取数四阶段**（平台版）：id-only 调用 → `plan_slices.py --size 150` → 每片 `esids` 调用 → `pull_results.py --from-tool-results --expect-ids` 合并校验。落盘路径 `/workspace/tool_results/<tool>/<call-id>.jsonl`，**turn 结束时清除**。

TS 侧：project `d1c193d7809d4c04ba5423942523f91c`，prompt family `3fa0f27ef41648c0a968bb7b9a76adfb`，skill family `69db628c867b4bf2acf8477789562c96` / skill_id `230463cbc03d4fe5ba0e2e8964fe91dd`（v0.3.0，17 entries），`toolsmith-publish status` → **in sync**。

## 现状（2026-11-11，v0.3 改为平台内执行）

**状态**：v0.3 完成，**目标形态是 ToolSmith 平台内运行**（不是本地脚本跑批）：用户在 TS 会话里给一个会议名，agent 拉全量结果 → 机械筛 → 逐批判读 → 输出 `/workspace/output/watchlist.json` 卡片清单 → `present_artifact`。仍未发布 TS（用户要求发布前须单独确认）。

**目录已对齐 `clinical-result-comparison` 的形态**：

```
skill/conference-result-triage/{SKILL.md, references/, templates/, scripts/}
system-prompts/conference-result-triage-v0.4.md
tools/pack-dist.py     -> dist/conference-result-triage-v0.4.zip (17 entries)
```

平台把 zip 解到 `/workspace/skills/conference-result-triage/`，所以 SKILL.md 里的脚本一律按 `/workspace/skills/conference-result-triage/scripts/...` 调用。

## v0.3 改了什么（相对 v0.2）

| 项 | v0.2 | v0.3 |
|---|---|---|
| 取数 | 本地直连 `/api/tools/debug`，缺 `lba` | `scripts/pull_results.py` 走 MCP，`lba` 在 `DEFAULT_FIELDS` |
| 大响应 | 一次取全字段，静默只回 ~500 行 | 两阶段：先 id 全量，再 `esids` 切片 120/次（1097/1097） |
| LBA 排序 | 纯 `LBA<n>` rank 3，被压到普通口头下 | `Late-breaking Oral: 0`，高于 `Oral: 1` |
| LBA 分桶 | 「只在会议库 ⇒ 只进 early」把 LBA 一并误伤 | LBA 行豁免，可进 pivotal/failed |
| 摘要号 | 平台内**拿不到**（无 `abstract_id` 列、无会议库工具） | `abstract_id` 恒 `null`；报告形式只有 `lba`（51/551 有层级） |
| 报告形式 | 只有 `lba`（进池 51/551） | `featured` 是**人工/AI 生产**标记（`是` 100/100 = `source=np_result_conf`），**不是头条**，只做卡片生产方式标注 |
| 交付物 | `watchlist.md` + 两个 csv | `/workspace/output/watchlist.json` 卡片清单（固定路径） |
| 闸门 | 无 | `check_cards.py` fail-closed（exit 3） |
| 候选池 | 532 | **551**（early 200 / pivotal 292 / failed 59），37 批 |

NATALEE / NSABP B-42 / INTerpath-001 / DASL-HiCaP / LOMAC / CAPItello-281 / DUO-E / CheckMate 8HW / DeLLphi-305 等 LBA 已全部进 pivotal 桶。

## 交付 schema

```json
{"conference":"ESMO 2026","count":30,"cards":[
 {"esid":"...","abstract_id":"LBA3","lba":true,"bucket":"pivotal","tag":"LBA",
  "title":"...","summary":"...","why":"...","drug":"","target":"","indication":"",
  "phase":"Phase III","presentation":"Late-breaking Oral","stock":null}]}
```

`esid` = 结果记录 id；`stock` 只在给了 `--quotes` 同日行情时非空，否则 `null`（不用其它日期顶替）。

## 是什么

会议临床结果推荐榜 skill：输入一个会议标识（`meeting_tags`，如 `ESMO 2026`），输出三桶榜单
（早期机会 / 重磅 II/III / 失败）+ 排除档 + 待人工核实清单。

与两个既有 skill 的边界：

| skill | 分析对象 | 输出 |
|---|---|---|
| `conference-clinical-interpretation` | 一个会议的**统计概览** | 会议整体解读报告 + 图表 |
| `clinical-result-comparison` | 2 个以上**已选定**的结果 | 药物间疗效/安全性对比 |
| **本 skill** | 一个会议的**全部候选** | 值得看的 30 条 + 为什么 |

## 关键设计决策（含理由，勿回退）

1. **机器评分被显式废弃**。实测规则打分产生假精度：安全性行会压过疗效行（`Grade≥3 TEAE 44.6%` 被当疗效）、`PR = 3 subjects` 被读成 3% 缓解率、约一半 `study_results` 没有 p/HR。现 `triage.py` 只做机械操作 + 附**非权威**提示。
2. **n 不作入榜门槛**（用户 2026-10-23 决定）。只做展示与并列次级排序。
3. **真实世界/回顾性/前瞻性非注册研究不进桶**（用户决定）。单独计入 `excluded`，在交付物里明示条数。
4. **失败桶由 `evaluation ∈ {不佳, 终止}` 或复核阶段证实的「主要终点未达/未显著/提前终止」驱动**，p/HR 只作佐证。
5. **试验期别取 `evidence_source`**，不是 `clinical_stage_new`（后者是疾病分期）。
6. **`data_type` 四分类**（首次 / 更新 / 亚组 / 未判定）为强制列。理由：会议摘要大量是长期随访与 post-hoc 分析，不标会把 7 年 OS 更新写成新药突破。未命中一律 `未判定`，不猜。
7. **批次 15 条/片**（v0.1 为 25）。硬约束来自工具单文件读取上限（~50 KB）与"Results 全文不截断"的叠加要求：36 片实测 max 40,804 B / avg 35,964 B。
8. **索引用显式顺序 `i`**，不用 esid 下标。此前一次 6 路并行复核因为 esid 与顺序错位，合并结果不可用。
9. **两条数据源是并联关系，不是主备**（v0.2 新增）。`drugClinicalResult`（结构化结果表）只有 646 条 ESMO 2026 记录；`medicalMeeting`（会议库）有 5810 条、可用 4103 条。只走前者会漏掉 3638 篇没进结果库的摘要，其中 141 篇是口头档、358 篇带药名+数字+期别。
10. **会议库独有记录硬性只进 early 桶**（v0.2 新增，在 `build_pools` 层强制）。因为它们的期别是从正文正则出来的，撑不起"重磅"或"失败"两种断言。ESMO 2026：补录 305 条 → 68 条进 early，235 条被这条闸门挡在桶外。
11. **平台内报告形式只剩 `lba`**（v0.3）。没有摘要号，`featured` 是人工/AI 生产标记（用户确认 + SQL 100/100 验证），只做生产方式标注。551 候选里 51 条有 `lba`，其余 `Unknown` 是诚实结果。用法：排序权重 + 每条必须标注，**绝不当准入门槛**。详见 `references/pitfalls.md` §20。
12. **ORR 门槛按人群难度分档**（v0.2 新增）：一线/非耐药 ≥40%，后线≥2 线/明确耐药 ≥25%，**降档必须在理由里写明人群**。用例：9MW2821 在 TOP1i-ADC 耐药 TNBC 里 30.0%。
13. **机器排序 ≠ 推荐排序**。池子按 `(presentation_rank, -n)` 排只为决定"读的顺序"；定榜顺序由读完 keep 的人给。实证：7 条专家选择在机器序里排 2/19/27/72/101，两条壁报被 n 大的平庸研究压到 72、101 名。`make_watchlist.py` 只按给定顺序渲染，不做排序。

## 已完成

- `scripts/triage.py`（零依赖）：去重 / 排除 / 三桶 / `data_type` / 机器信号 / 批次输出 / `--self-test` / `--require-detail` 两段式。
- `scripts/meeting_pull.py`：最小 MCP streamable-HTTP 客户端，拉 `medicalMeeting` 全量（290 页 / 4m04s / 5810 条），支持 `--conference -` 跨会议检索（用于同资产历史）。
- `scripts/meeting_join.py`：归一化标题归并（646/646 零漏配）+ 会议库独有记录保守补录（305 条，49 oral 档）+ `enrolled_from_text` 补 n（257/305）。
- `scripts/history_for.py`：同资产历次会议读数对照（只列摘要印出的数字，不做判断）。
- `scripts/make_watchlist.py`：渲染 `judgements.csv` / `watchlist.csv`，机器桶与复核桶并排。
- `references/` 四份（data-contract 含 §7 会议库契约 / screening-rules / review-protocol / pitfalls 17 条）。
- `templates/watchlist-report.md`、`system-prompts/conference-result-triage-v0.1.md` + `v0.2.md`、`SKILL.md`、`README.md`。
- `evals/test_triage.py` + `evals/fixtures/mini_rows.json`（4 条固定样例）。
- **ESMO 2026 v0.2 实跑**：5810 会议记录 → 4103 可用 → 结构化 646 + 补录 305 = 951 → 候选 532 → 逐条判定 532 → keep 232 → 定榜 30。产物在 `dist/v02/`（判 532 / 榜 30 / 历史 185 条）。

## 验证记录

| 项 | v0.1 | v0.2 |
|---|---|---|
| `triage.py --self-test` | OK | OK |
| `evals/test_triage.py` | OK（4 组断言） | OK |
| 全部脚本 `ast.parse` | — | 5/5 OK |
| 候选池 | 467 | **532**（early 248 / pivotal 235 / failed 49） |
| 复核覆盖 | 467/467 | **532/532**，`i` 无缺口无重复 |
| evidence 逐字命中 | 400/467（86%） | **532/532（100%）** |
| `reason` 超 40 字 | — | 0 条 |
| 专家 7 条：在候选池 | 7/7 | 7/7 |
| 专家 7 条：判 keep | 3/7 | **5/7** |
| 专家 7 条：进定榜 30 | 1/30 | **5/30** |

**v0.2 首轮踩的坑（已修，记在 pitfalls §16）**：直接用 `pool.json` 切片导致 36 片 `condensed` 全为空，6 个子任务 4 个拒绝、2 个改用 `summary`，keep 率从 24% 掉到 2%。改成从 `review.jsonl` 的 batch item 拼 `Background + 完整 Results + DB summary`，并加落盘断言。

## 已知问题 / 待办

- [ ] **口径不一致 1 处**：`1015P` CM518D1 按"后线 25%"应 keep，模型判 weak 且理由未写人群。已列候补，未强行改判（规则与判定冲突时以原文为准，由人定夺）。
- [ ] `judgements.csv` 的 `key_numbers` 已做单位过滤（只留 % / 时间 / HR / p），但仍会混入 `60 years` 这类；`evidence` 才是权威字段。
- [ ] `data_type` 未判定 279/532，规则命中率仍是主要短板。
- [ ] `clean_label()` 残留噪声：`...; percentage`、`Patients who completed N cycles`。
- [ ] 机器重判后的桶分布明显偏移：机器 pivotal 235 条里 146 条被复核降到 early（单臂 II 期的"分期 = 确证级证据"误解）。若下游要按桶出数，需固定用的是机器桶还是复核桶。
- [ ] ToolSmith 发布（用户暂缓）：`system-prompts/conference-result-triage-v0.2.md` + `SKILL.md` 已备好；发布前须在 `~/.config/toolsmith/projects.json` 注册 family 并标 `owned: true`。

## Git

仓库根 `/home/xupeipeioo1/apps/skill`，分支 `feature/interactive-html-track`。
v0.1 提交 `ea90305`；v0.2 提交见 `git log`。
