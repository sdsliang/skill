# AGENTS.md — 常驻 program.md（autoresearch 循环）

本文件是这个仓库的**常驻程序说明**，任何新会话先读它，再读
`PROJECT_STATE.md`（当前实现快照）、`docs/toolsmith-verification-log.md`（台账）、
`docs/autoresearch-iteration-plan.md`（为什么这么做）。

一句话：**我们把这个 skill 当成「agent 唯一可改的 `train.py`」来迭代 —— 改规则 → 发版 → 真跑 →
离线判分 → keep/discard。**

---

## 当前交接（2026-09-18 全项目审查后）

**三组已跑完（覆盖下文运行中状态）**：R27 4/4、R28 18/18、R29 14/14 均产出报告。R27断言全过；R28写文件冲突导致断言FAIL；R29无FAIL但3次拒参/2次全文500已披露。设计冲突披露部分生效，三组内容审查均有待改项，不宣称全绿。详见台账 R27–R29。以后固定全跑三组。Git本轮仅提交任务相关资产/证据文档，Docker未涉及。

**最新：数值事实账本版本已原地发布并完成 R30 固定三组测试。** 发布前 config/status/deps 均通过，prompt v1.6 本地 57,656 B / SHA `115bac4e5295`，skill v1.0.7 / skill_id `ad75ec2c44334f389a0394895a47b765`，20/20 文件回读一致，dist 93,090 B / SHA `dd4d83f871692bd4c70b98cbf6787af1b6f839426312aee017e75630d95a06bb`。R30-1/2/3 分别覆盖 4/18/14 条，均成功产出报告，引用、图表、实体锚点、固定路径和回执断言通过；R30-1 因本地 `__pycache__` 污染支持文件清单，R30-2/R30-3 因平台重复 `write_file` 已存在文件导致 `no tool errors` 失败。报告未丢失，原始证据保留；不能宣称本轮三组无工具错误全绿。详见 `docs/toolsmith-verification-log.md` R30。

**附录形态升级 + 时间线加「发表时间」+ 移除实体内联引用（2026-10-09 已按 `--new-version` 发布为 prompt v1.7 / Skill v1.0.8）**：附录从「每行一个数值的 11 列宽表」改为**一张矩阵**——**列 = 试验**（同试验多披露按账本新增的 `records[].trial` 合并键合并为一列，表头标披露条数；缺键时回退注册号 → `study` → `ref`，绝不凭名字合并），**行 = 维度与终点父级**，按 `试验设计 → 试验结论 → 有效性 → 安全性 → PK/PD → PRO` 分段；治疗臂/时点/评估/人群与终点口径细分标签写进单元格（`治疗臂·时点·评估·人群：结果 单位（统计量）{{ref_n}}`，未报告 `—`），同一终点的不同时点/口径统一到同一行。账本 `records[]` 新增**必填** `conclusion`（缺失即门禁失败），`kind` 收成封闭词表（含英文映射），`endpoint` 必须是**最小可比父级**，`version` 只放披露版本/数据截止。附录标题改为 `## 附录：证据对齐矩阵（数值事实账本）`。四个模板的时间线表首列加**发表时间**（原文披露日期优先，`paper_release_time` 日期部分兜底，都没有写「未报告」；只作最后排序依据，不得按输入顺序推断）。**实体内联引用（v0.10/v0.11 的 `[名字](entity:type:id)`）整体移除**：删 `references/entity-inline-reference.md`、`evals/validate-entity-refs.mjs`、`test/entity-refs.test.mjs`；渲染器先把旧账本展示字段里的 `entity:` 包装**确定性剥离**（`quote`/`source_file` 除外），再由 `ENTITY_LINK_RE` 门禁拦残渣；正文/表格/图表/账本一律写纯名。回归：`python3 evals/numeric-integrity/test-render-facts.py` **21/21 绿**。**已按用户授权改用 `--new-version` 发新版本（不原地更新）**：本地 prompt `system-prompts/multi-clinical-result-comparison-v0.16.md`（54,264 B / sha `a638a93fe934`）→ 线上 **prompt v1.7**（project prompt id `394a6e51617842a0ae9403579dcf8f45`）；dist `dist/multi-clinical-result-comparison-v0.16.zip`（93,757 B / 19 entries / sha `e5aad92c2618`）→ 线上 **Skill v1.0.8** / skill_id `cd93a42af72b4828b1690b3a7bccfa06`（19/19 文件一致）；`toolsmith-publish status` → **in sync**。发布前依赖闸门拦下两处上游变化并复核：chart skill v1.0.12 被重新发布（运行期取模板，无需改本地）、内置 `read_file` schema 变化（`limit` 默认 100）→ 相应把 prompt 的 digest 上限从 ≤300 行收紧为 **≤100 行**。**固定三组回归（2026-10-09）**：R33 三组跑出两个**我方**缺陷——①`APPENDIX_INTRO` 把字面 `{{ref_n}}` 写进交付报告导语，被 runner 占位符断言判 FAIL；②跑动期间改仓库/跑本地测试，导致「支持文件清单」断言报 `missing=[…pyc]`（该断言的 `missing` 方向是**本地有、线上没有**，纠正了 R30/R32 的旧归因）。两处均已修（导语改写 + 新增断言并做负向对照，回归 21 → **22/22**；测试顶部 `sys.dont_write_bytecode = True`；`AGENTS.md` §7 新增「真跑期间冻结仓库」硬性条目）。修后 dist 重打为 **93,792 B / 19 entries / sha `dd9c2998c2b6`**，并用 `toolsmith-publish push-skill --version 1.0.8` **原地更新**同一版（`skill_id` 不变、prompt v1.7 未动、`status` in sync），再跑 **R34 三组全绿：22 PASS / 0 FAIL、exit 0**，附录列数 4 条→1 列、18 条→10 列、14 条→11 列。详见台账 R33（缺陷）与 R34（修复验证）。

**R32 固定回归已完成（2026-09-21）**：图表文档去重复后，prompt v1.6 / Skill v1.0.7 原地更新并回读一致。固定 4/18/14 三组均 `outcome=succeeded`、产物和主要契约断言通过；R32-1/R32-2/R32-3 均有 `__pycache__` 支持文件清单 FAIL，R32-1/R32-2 另有重复 `write_file` 冲突，R32-2/R32-3 有 Europe PMC 503。不能宣称本轮全绿。证据见 `docs/toolsmith-verification-log.md` R32 和三组 run 目录。

**图表协议重复内容已同步从 v0.15 prompt 移除（2026-09-20）**：prompt 的 Chart contract 现在只指向上游 chart-visualization-json skill，并保留临床选型、可比性、事实绑定和交付边界；删除重复的协议字段、Schema、envelope、默认值、排序和 CLI 细节。TS 资产尚未发布，需单独授权后再同步线上。





用户最新决定：试验设计相关 MCP 字段来自登记平台，重点对照原文，冲突以原文为准并披露差异。测试输入缺真实 `_id` 的兼容只在调用 TS 前用只读 SQL 解析，**不加入 Skill**；显式字段按该字段匹配，未标字段按 `_id OR extra_esid` 匹配，真实 `_id` 去重后传 `esids`，未解析项单列。故意无效 ID 的冻结拒绝测试保持原始输入。决策与证据见 [test-input-resolution.md](docs/test-input-resolution.md)。本轮仅文档与本地证据，未改运行资产/runner、未发布、无需 Docker；转换清单已核对 86 命中/68 未解析。


本地修复与线上原地发布已完成，部署回读 in sync；R26 拒绝契约与回执归档通过。R22/R23 的报告内容人工复核仍有缺陷，不能宣称标准 A/全文验收全绿。完整验收记录见 [online-acceptance-2026-09-18.md](docs/evidence/online-acceptance-2026-09-18.md)。

评估器已明确开新基线 **`2026-09-18-r2`**：A **43 fail + 1 warn**、B **12 fail + 1 warn**。41→43 是评估器修订，**不是质量提高**；跨基线不可直接比较。详见 [修订记录](evals/fact-check/EVALUATOR_REVISION.md)。本次一次性审查含冻结面修复，不属于「一轮一个变量」的规则实验；后续迭代以 r2 冻结。

## 1. 四层资产，改哪层要说清（别用「工具本体」这种含糊说法）

| 层 | 实体 | 我们能改吗 | 改动前的必要动作 |
|---|---|---|---|
| **仓库资产** | 本仓库 `skill/`、`system-prompts/`、`evals/`、`docs/`、`tools/` | ✅ 改，`commit`/`push` 本项目免确认 | 改完更新本文件 + `PROJECT_STATE.md` + 台账 |
| **TS 资产** | 平台上已发布的 prompt / 技能内容 | ✅ 改，但**每次都要先问、拿到明确同意** | `tools/pack-dist.py` → `toolsmith-publish publish`（默认 **in-place**）→ `status` 回读必须绿 → 真跑留 `R<n>` |
| **TS 平台** | 远端 ToolSmith 服务后端 | ❌ 改不了 | 写问题单（全文进 Obsidian，仓库只留摘要 + 指向），**功能性缺陷与文档缺口均记录，由开发判断是否处理** |
| **runner** | 本机 CLI `~/.local/bin/toolsmith-publish` | ✅ 改，但先备份到 `~/.local/state/toolsmith-publish/toolsmith-publish.v*.bak` | `python3 -B -m py_compile`（**加 `-B`**，别在包内留 `__pycache__`）→ `evals/runner-gate/verify-run-chain.py` 必须 `GATE: PASS` → 台账留 `R`/`O` 记录 |

**TS 资产写入必须逐次点头**：`publish` / `push-prompt` / `push-skill`（往平台写 skill/prompt）。
Git 免确认仅限本项目 `commit` / `push`；`revert`、merge、rebase、分支操作等仍须明确授权。
`run` 会创建线程，按写动作处理；`status` / `deps` / `tools` / `instructions` / 离线脚本都是只读。

---

## 2. 冻结面（改它 = 旧基线作废，必须开新基线并在台账写明）

「冻结」= 迭代期间**不随规则一起动**，否则分数变化无法归因：

- `evals/fixtures/`（ground truth：`records/*.json`，来自 `POST /api/tools/debug` 的真实返回）
- `evals/fact-check/scenario-a.facts.json` / `scenario-b.facts.json`（必含事实清单）
- `evals/fact-check/check.py`（离线打分器）、`evals/fact-check/mutations.py`（负向对照）
- `runtime/citation-renderer.mjs`、`test/`
- **params 工具 schema 的字段名**（运行期权威 = 工具自身 `selected_fields` 参数描述）
- 本文件 §3 的场景集与 §4 的 TSV 列定义

**可改面**（= 「`train.py`」）：`system-prompts/multi-clinical-result-comparison-v0.16.md` +
`skill/multi-clinical-result-comparison/**`。

---

## 3. 固定场景集

| 场景 | 输入（用户话术） | 期望 | 判分 | 成本 |
|---|---|---|---|---|
| **A** | `解读这几个结果 24_1_30561610 24_1_36342163` | `output/report.md` + 1 图 + `output/citations.json` | `check.py --scenario a`（**43 条 fail 级 + 1 warn**） | ~200 s / ~30 calls；**质量结论需 A×3** |
| **B** | `解读这几个结果 24_1_30561610 24_1_45608045` | **拒绝产出**（1 有效 1 无效） | `check.py --scenario b`（**12 条 fail 级 + 1 warn**） | ~33 s / 8 calls —— **每次改动后都跑，当廉价闸门** |
| **C** | 18 esid 跨试验 | 多图 + 分组契约 | 尚无清单（跑之前先补） | 贵，只在改图表/委派时跑 |
| **D** | 4 esid 同试验 | 时间轴图 ≤1 且稳定 | 尚无清单 | 只测「图数是否被规则钉住」 |

命令行（场景 A）：

```bash
tools/pack-dist.py --check                     # 门 1：dist 是否等于当前仓库字节
source ~/.secrets 2>/dev/null
toolsmith-publish publish --message "…"        # in-place；先问授权
toolsmith-publish status                       # 门 2：必须 in sync
toolsmith-publish run --prompt "解读这几个结果 24_1_30561610 24_1_36342163" \
    --tag r<n> --web --poll-interval 8         # 门 3：真跑（写动作）
python3 evals/fact-check/check.py --run ~/.local/state/toolsmith-runs/<dir> --scenario a
```

---

## 4. `results.tsv` 列定义（每轮一行；由脚本产出，禁止手抄）

```
r  commit  deployed_sys_sha  scenario  turns  calls  wall_s  params_calls  execute  edit_file
thinking_chars  gate_pass  facts_ok  facts_total  status  description
```

```bash
tools/replay-run.py --tsv --score \
    --commit <sha> --status keep|discard|baseline --description '改了什么' <run-dir>
```

口径（易错，见 `docs/evidence/autoresearch-baseline-tsv-backfill-2026-09-18.txt`）：

- `deployed_sys_sha` = **装配后** instructions 的 sha256[:12]（≠ 本地文件哈希）；`--details` 另报哪份本地
  prompt 是其字节前缀。**它只在同一 web 设定下可比**：`enable_web=on` 时装配串多出平台的
  `## Web Tools` 段（654 B），所以 R18（`--web`，71,481 B）与 R19/R20（无 web，70,827 B）的 sha 不同是
  **配置差异不是随机位**；`--details` 现在并排打 `web=on|off`。
- `calls` / `params_calls` 数的是**调用尝试**（含被拒的），与 `verification.md` 的 `tool calls:` 同口径。
  没拿到 tool-return 的尝试分两桶（runner O32）：**`args-refused`**（参数被工具拒，框架重发）与
  **`fetch-failed`**（外部抓取失败：4xx/5xx / 主机不可达）。抓取失败**必须写进交付物的核对覆盖行**，
  桶本身只保证「看得见」，不作为 FAIL。
- `turns` 在 2026-09-15 前后语义不同（平台 `stats.turns` vs 老 harness 的模型轮次）⇒ 老行看 `--details` 的 `model_turns`。
- `facts_ok/facts_total` 必须来自 `--score`（离线 `check.py`），**不许手写**。

---

## 5. 一轮 = 一个假设（硬纪律）

1. **写假设**：改哪条规则 → 期望动哪个指标 → 方向。
2. **只改一个变量**（「A 组六项一起改」是反例：跨版本、无法归因）。
3. `pack-dist.py` → `publish`（**先拿授权**）→ `status` 必须绿。
4. `run`（场景 A；质量结论要 A×3 取噪声带；场景 B 每次都跑）。
5. **看两层数**：成本层 `calls` / `wall_s`，质量层 `facts_ok/facts_total` + 断言 gate。
   - 成本降、事实分掉 → **discard**；成本不降、事实分升 → keep；两者都不动 → 待样本，别宣布胜利。
6. **keep**：前进并提交（遵守当次任务的 Git 限制）。**discard**：先准备回退方案；`git revert` 须取得授权，in-place 重发上一版也须单独取得 TS 发布授权。
7. 台账记一条 `R<n>`（线程/模型/墙钟/调用/token/产物/断言）+ 一行 TSV（§4）。
8. 发现缺陷按两栏记：**我们自己能改的（O 编号）** / **平台侧（问题单）**。

**禁止**：用一个总分同时代表质量与成本（原因见 plan §9：`val_bpb` 被 gaming 的教训）。
质量永远是 gate，不是可换的数。

---

## 6. 反「假绿」（本项目吃过两次教训）

每写一条断言/清单条目，先问：**一个空壳产物能不能糊过去？**

- 「键集对 + 日期格式对」能被 `{"title": ""}` 糊过去 ⇒ 必须查 `title` 非空（已有）。
- 只认 `ref_<n>` 前缀的归档文件名 ⇒ 真产物（`PMC11270764_fulltext_jats.xml`）根本不匹配 ⇒
  规则**空转还 PASS**（O29 就是这么来的）⇒ 变异的**命名必须照真产物的来**。
- 负向对照必须断言**整轮干净**（`rc == 0 && flipped == []`），不能只说「我这条没翻」。
- 回执要求由**最终目标 turn** 的持久化消息推导，不以轮询是否看到指针为准；0 polls / 0 poll pointers 不能证明无需回执。要求匹配落盘文件、字节与哈希；缺失清单、缺失回执、未知形状或归属歧义均失败。无指针仅在目标 turn 的最终证据明确完整时才可 n/a。
- `returned` 数实际 tool-return；未归入已知拒参/抓取失败的无返回调用仍 FAIL，不能靠减法补成「已返回」。调用与回执均限定目标 turn。
- 回执类断言只能证明「取回来了」，不能证明「数字取自它」——写边界，别越界宣称。
- **只统计「有 tool-return 的调用」的断言会被「工具自身失败」骗过去**（O32）：抓取 500 / 主机不可达时框架
  直接重发、不留 tool-return，若把这类事件塞进「schema 被拒」桶再从 `errors` 里跳过，`no tool errors`
  就成大号空转（R15–R18 四轮全绿而每轮都有一条欧洲 PMC 全文 500）⇒ 归因必须按**原因文本**分桶，
  且失败类要**可见**（打印 + 入 `verification.md`）；未解释的缺返回、未知归属和其它工具错误仍判 FAIL。`args-refused` 只说明参数被拒，不说明模型发明参数：R19/R20 的 `extra_esids` 是旧提示词明文要求，live schema 已改为 `esids`（F7 更正）。

---

## 7. 常用命令速查

```bash
python3 evals/fact-check/check.py --run <run-dir> --scenario a|b [-v]     # 离线判分（exit 0/3/4）
python3 evals/numeric-integrity/test-render-facts.py                      # 附录渲染/账本门禁回归（文件名含连字符，**不能**用 unittest discover，直接脚本跑）
python3 evals/fact-check/mutations.py                                     # 负向对照闸门
python3 evals/runner-gate/verify-run-chain.py                             # runner 零网络回归
tools/replay-run.py --tsv --score <run>…                                  # 成本 + 质量一行一 run
tools/replay-run.py --details <run>                                       # 全字段（含 model_turns / 前缀版本）
tools/pack-dist.py --check                                                # dist 是否等于仓库字节
toolsmith-publish status | deps | tools | instructions                    # 平台只读核对
```

产物落点：`~/.local/state/toolsmith-runs/<时间戳>-<tag>/`（`receipts.jsonl`、`tool_results/**`、
`verification.md`、`transcript.md`、`artifacts.zip`）；**不要用 `/tmp`**（会被清空）。

### 真跑期间冻结仓库（R33 教训，硬性）

`run` 的「支持文件清单」断言比的是**断言时刻的本地 Skill 目录**与线上包，所以**真跑跑动期间不要改
仓库、不要跑本地测试**，否则必然 FAIL 且是假 FAIL：

- 跑动中改 `skill/**`（哪怕只是收尾）⇒ `xxx: platform 29.0 KB != local 29.09 KB`。
- 跑动中跑 `evals/numeric-integrity/test-render-facts.py` ⇒ 旧的 `importlib` 加载会在
  `skill/multi-clinical-result-comparison/scripts/__pycache__/` 留 `.pyc` ⇒ `missing=['…pyc']`
  （`missing = local - platform`，**报的是本地多出来的文件**，不是线上包脏）。该测试已在加载渲染器前
  设 `sys.dont_write_bytecode = True`；别的脚本加载渲染器时同样加这句或 `python3 -B`。
- 要边跑边干别的：只改 `docs/**`、`AGENTS.md`、`PROJECT_STATE.md` 这类**不在 Skill 包内**的文件。
