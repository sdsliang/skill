# PROJECT_STATE — conference-result-triage

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
