# AGENTS.md — 常驻 program.md（autoresearch 循环）

本文件是这个仓库的**常驻程序说明**，任何新会话先读它，再读
`PROJECT_STATE.md`（当前实现快照）、`docs/toolsmith-verification-log.md`（台账）、
`docs/autoresearch-iteration-plan.md`（为什么这么做）。

一句话：**我们把这个 skill 当成「agent 唯一可改的 `train.py`」来迭代 —— 改规则 → 发版 → 真跑 →
离线判分 → keep/discard。**

---

## 当前交接（2026-10-10 R47 完成：O43 结案 + O40/O41 报告侧习惯句已原地发布；四组真跑 + 一次耗时 A/B）

**R47（用户答复「改吧」+「分析下 2–3 条结果也要 5min+ 的耗时分布」）**：按「一次内容改动一轮」纪律，本轮只装 **O43 + O40/O41 报告侧习惯句**，把**耗时优化留作 R48 提案**（不混进本轮 keep/discard 归因）。

1. **已原地发布（同一授权，版本标签不变）**：prompt `v1.7` **65,959 B / `f63bf180822c` → 67,591 B / `c1641a46810a`**；Skill `v1.0.8` dist **103,982 B / `47c06e7aa6d4` → 105,347 B / `025aec791b1c`**（19 entries）；发布前 `deps` = `unchanged since the recorded baseline`，发布后 `status` = **in sync**。改 5 个文件：prompt 三条 hard rule（**每个图表行点名自己的试验** / **marker 绑定本条记录的内容** / **`库内记录` 只有一处合法写法**）、`SKILL.md` 两条中文硬规则、`references/chart-templates.md`、`references/citation-and-ref.md` 新节 `## Marker attribution`、`references/input-contract.md`。
2. **四组真跑 4/4 全绿**（顺序执行，`arguments refused = 0`）：`r47-a` 349.1 s / 40 attempts、`r47-4` 512.1 s / 56、`r47-18` 488.6 s / 56、`r47-14` 569.7 s / 66，**均 22 PASS / 0 FAIL / exit 0 / succeeded**。
3. **O43 结案（4/4 命中）**：r47-a 柱子 label 前缀 `OCEAN(a)-DOSE · …` / `NCT02729025 · …`；r47-18 `HARMONi-6（NCT05840016）· …`；r47-14 `…（NCT04987320）/（jRCT2051240068）`；r47-4 只有单试验时间线图（规则不适用）。对比 r46-a（0 个试验名 → 离线 40/44）。
4. **O41 收尾**：R47 五份产物 `库内记录` 出现 **0 次**（A-P2 无触发）⇒ 习惯句生效，不改评分器。
5. **O40 需在 R48 再收**（第 3 份样本 `r47-loweff-a`）：表格 cell「OCEAN(a)-DOSE 未评估该终点」**无标记 ⇒ 按 `units()` 继承本行 `ref_1`**，只点名 `ref_2` 的试验 ⇒ `A-ATTR` FAIL；R47 的正文侧习惯句覆盖不到表格继承 ⇒ R48 收窄为一条可机械检查的规则（阴性/缺测句必须带**被点名那条记录**自己的 `{{ref_n}}`，否则不点名对方）。
6. **新增 O44（待样本，n=1）**：`A-C9-mds-tbr-A` 的 `patterns` 硬编码 `-8\.3`/`-5\.3`，r47-a 写「降低 8.3%／降低 5.3%」（交付物内部一致、`A-S10` PASS）⇒ 离线 43/44 FAIL；同门径 `A-S10` 规格自称「符号由模型自选」⇒ 同 spec 口径不一致。修复=各加文字式备选，**按 O27/O28 先例等第 2 份样本**。
7. **耗时分析（只读）落 `docs/evidence/runtime-breakdown-2026-10-10.md`**：生成占墙钟 **65–92%**、reasoning 占输出 **46–76%**（180–330 s/run）、工具全部 **<15%**；2 esid 与 18 esid 同量级。**A/B 负结果：`--reasoning-effort low` 不减 reasoning 量（44,975 vs 40,304），墙钟 −39 s 全来自步数少 10 步** ⇒ 该旗标不是杠杆；R48 候选 = L2 随包发脚本（砍 10k–39k 生成 token/run）、L3 去 `draft.md` 两遍写、L4 压步数。

## 历史交接（2026-10-10 R46 完成：O42 已结案 —— 工具侧前置拒绝改判；prompt / Skill 该轮未动）

**R46（用户答复「谁好，你推荐谁」① +「你自己看着办吧」② +「不管了」③）**：按①执行 **O42 选项 B 的窄口径**，**只改本地 runner，prompt / Skill / dist 一字未改，TS 无写动作**（线上仍 = 下面的 R43–R45 值）。备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v15.bak`。

1. **改了什么**：`~/.local/bin/toolsmith-publish` 新增 `TOOL_REFUSED_RX`（`^` 锚定，只收编两种实测形状：`write_file` 的 `File '<path>' already exists…`、`edit_file` 的 `Could not find the target string in '<path>'`）⇒ `retry_kind()` 返回 `"rejected"`；新增 `REFUSAL_BUDGET = 3`，原恒 PASS 的信息行改成「拒绝次数 ≤ 3」判定（**断言仍 22 条**、`verification.md` 语义与退出码不变）。被包装的消息（`RuntimeError: File '…' already exists`、`MCP error: …`）**仍落 `errors`**（`^` 锚定 + 负例单测）。失败方向保守：若平台改写 re-prompt 文案 ⇒ 正则失配 ⇒ 回到旧口径。
2. **离线重打分 98 份归档**（零新 run / 零网络 / 不改产物）：`errors > 0` 的 run = **0**；拒绝次数直方图 `{0: 77, 1: 18, 2: 3}`；单 run 最大 **2**；超预算样本 **无**；五次历史 F1 FAIL（r41-fixed-4 / r42-hz-18 / r43-a / r44-18 / r45-14）**各恰好 1 次拒绝**。证据 `docs/evidence/o42-refusal-reclassification-2026-10-10.txt`。
3. **本机门禁**：`py_compile` OK；`evals/runner-gate/test-runner.py` **38 → 39 OK**（新增 `test_tool_side_precondition_refusals_are_not_errors`，含 2 负例）；`evals/runner-gate/verify-run-chain.py` **`GATE: PASS`**（98 / 5 可比 / 93 跳过）；`tools/test_replay_run.py` 14 OK；`tools/test_pack_dist.py` 5 OK；`evals/fact-check/test_regressions.py` 35 OK；Node 16/16；`evals/numeric-integrity/test-render-facts.py` 28 OK；`tools/pack-dist.py --check` **IDENTICAL**（103,982 B / `47c06e7aa6d4`）。
4. **线上真跑两次**（scenario A，R45 已发布内容）：`r46-a`（`4327dde4` / 330.0 / 349.2 s）、`r46-a2`（`f0e29144` / 360.7 / 371.2 s），均 **22 PASS / 0 FAIL / exit 0 / refused=0**。
5. **O40 / O41（② 自主处置）**：**不改评分器、不单独发版**；候选报告侧习惯句随**下一次内容改动**一轮进。**③「不管了」** ⇒ 撤回「`write_file` 提供 upsert/默认覆盖」的平台建议，不再提。
6. **新增待修 O43**：`A-S9`/`A-S9b`/`A-S10` 要求图表行（`label`+`description`）点名该观察所属**试验**，而 prompt/SKILL 从未把这条写成可检查规则 —— `r46-a` 的 5 根柱子只写「药名+剂量+间隔+时点」（`依洛尤单抗 420 mg 每月一次（第 16 周）`）⇒ 离线 **40/44**；同一 prompt 的 `r46-a2` 把试验写进 `description` ⇒ **44/44**；`R45-a` 亦 PASS ⇒ 同 prompt 3 次 scenario A 里 **1/3 丢试验名**。判分口径自洽（行内 5 维须全部出现在 label+description，互斥性另有 competing-identity 抽底），属**报告侧偶发漏写 + 规则只在 fixture 隐式存在** ⇒ **本轮不改**（n=1）；候选① prompt/SKILL 补一句硬规则（随下次内容改动发版）；候选②判分侧去试验维度（证据不足）。

## 历史交接（2026-10-10 R43–R45 完成：F1 三轮强化 + F2 修好）

**线上现状**：prompt **v1.7 = 65,959 B / sha `f63bf180822c`**；Skill **v1.0.8**（dist **103,982 B / 19 entries / sha `47c06e7aa6d4`**）；`status` **in sync**；`deps` unchanged。三轮都走**原地更新**（版本标签不变），发布记录：R43 = prompt `e23eef7201d0` / dist `2f4700a2f295`；R44 = prompt `5b8043bb3779` / dist `cdb4992f9b20`；R45 = 现值。

1. **F2（同一观察一套写法）已修好并复验**：生成侧 = prompt 新 hard rule「One wording per observation」+ `SKILL.md` 硬规则段 + `references/chart-templates.md` bullet（图表 `label`/`description` 逐字复用正文身份短语，原文说 `monthly` 就写「每月」）；判分侧 = `evals/fact-check/scenario-a.facts.json` 30 条 `identity_patterns`/`report_identity_patterns` 双向放宽（`(?:每月|每月一次|QM|Q4W)` 等），225 mg Q12W 与 Q24W 仍严格互斥。**证据**：`A-S9` / `A-S9b` / `A-S10` 在 R43-a / R44-a / R45-a **连续四次真跑全 PASS**；R41-A 重打分 **41/44 FAIL → 44/44 PASS**。
2. **O27 已结案**：`A-C16-hard-outcome-gap` pattern 1 放宽为 `硬结局|硬终点|心血管事件|心血管结局`（pattern 2 的否定式要求不变），配 `test_hard_outcome_gap_accepts_every_wording_but_still_needs_the_gap`；scorer **32 → 34 → 35**。
3. **F1（写文件被平台拒，`no tool errors` FAIL）三轮强化仍未清零** —— 这是本轮唯一的未结项：
   - R43 = 第 6 条覆盖面扩到「工作区里你写过的任何文件」→ 仍 **1/4 run** 失败（`work/draft.md`）。
   - R44 = **每次 `write_file` 一律带 `overwrite=True`（含全新路径首次写入）**、不判断路径新旧 → 仍 **1/4**，但换形态（`edit_file` 对自写脚本 `scripts/build_ledger.py` 目标串过期）。
   - R45 = **`edit_file` 只准用于 `/workspace/output/report.md`**，自写脚本/账本/digest 一律整文件重发 → 仍 **1/4**（回到 `work/draft.md` 缺 flag）。
   - 三轮共 12 个 run、失败 3 次，**报告侧其余 21 条断言全部照常通过**（平台 re-prompt 后 run 正常完成、产物完整）⇒ 判为「长 agentic run 里模型偶发漏传布尔参数」的**行为天花板**，不是合同缺口。台账 **O42** 给三个选项：A 接受为已知偶发 / B 改 runner 把「参数被拒但重发成功」降为 WARN / C 把正文改成「脚本从账本渲染一次成文」以减少写次数。**等用户选**。
4. **新增两条「待样本」（不改评分器）**：**O40** = `A-ATTR` 对「对对方记录的否定陈述」不给豁免（R43-a、R45-a 两样本）；**O41** = `A-P2-divergence-shows-both` 对「非分歧地提到库内记录」零容忍（R45-a 一样本，合同只规定「分歧时必须双值并附引用」）。
5. **R43 / R44 / R45 各四组真跑**（详见台账）：R43 22/21/22/22、R44 22/22/21/22、R45 22/22/22/21（每次恰一组栽在 F1）。**场景 A 离线判分**：R43-a 43/44、**R44-a 44/44 PASS（首次全绿）**、R45-a 42/44（余 A-ATTR 2 cell + A-P2 1 处）。
6. **本地门禁**（R43–R45 当时值；**R46 后 runner-gate 已 38 → 39**）：runner-gate **38** / scorer **35** / tools **5 + 14 = 19** / Node **16** / numeric-integrity **28** 全 OK；fact-check 变异闸门 `arm a 44/44, arm b 12/12` → **`GATE: PASS`**。

## 历史交接（2026-10-10 R41 完成 + R42 Phase A）

**R41（药名成对字段 + 附录可读名 + humanizer 交接段）已原地发布并四组验证（2026-10-10）**：

1. **(c) 药名硬规则**：中文报告写记录自带 `drug_earth_name_cn`（非空即用）、英文报告写 `_en`；目标语言字段空/`未报告` 才回退另一语言并保源拼写；**永不音译/翻译/归一化/凭记忆映射/查外部字典**。落点：prompt 5 处、`SKILL.md` 2 段、`references/input-and-extraction.md`、`references/input-contract.md`。效果：R40-1 的 `A-C1`/`A-C2` 转 PASS（场景 A 39/44 → **41/44**），R41-18 出现 `卡瑞利珠单抗` 15 / `替雷利珠单抗` 50。
2. **(b) 附录列头可读名优先**：`render-facts.py` `_identifier_only()` + `_column_label()` + `_column_header()`；**只在显示名本身是纯注册号时**才删第二行重复注册号。实测 `**NCT02729025**<br>NCT02729025 · 1 条披露` → `**NCT02729025**<br>1 条披露`，而 `**OCEAN(a)-DOSE**<br>NCT04270760 · 1 条披露` 不变。`test-render-facts.py` 26 → **28/28**。
3. **humanizer 交接段**（prompt + SKILL 各一节）：中文报告 → `report-humanizer-zh`、英文 → `report-humanizer-en`，绝不同用；顺序 = 报告 → 账本渲染门禁 → 语言 pass；**本 prompt 优先于 humanizer 风格规则**；受保护集合明确列出（结构、`原文核对：` 行、`{{ref_n}}`、数值/单位/精度/日期、发表时间列与顺序、表格形态、图表 JSON 与 `::visualization` 路径、citation JSON、两个交付路径）。
4. **清陈旧句**：`SKILL.md` 尾部「`entity:` … must be kept」与 v0.16 移除矛盾 → 改为「`entity:` 不属于本产品，出现即硬失败」；prompt entity 段改为「只用于选专有名词 + 填 `trial` 合并键」。
5. **发布（原地）**：dist **102,716 B / 19 entries / sha `ab1efaccf624`**、prompt **v1.7 = 63,422 B / sha `78c1a2a71efe`**、Skill **v1.0.8**，`status` **in sync**。发布前 `deps` 报 2 条上游变化（= 我们新建的两个 humanizer skill 首次进基线）→ 先 `deps --accept` 记新基线。
6. **R41 四组（2/4/18/14 esid）**：22 / 21 / 22 / 22 PASS；唯一 FAIL = 模型 `write_file` 重写 `/workspace/scripts/build_ledger.py` 被平台拒（平台行为正确，见 F1）。
7. **R42 = Phase A（18/14 esid 的 humanizer 臂）**：21 PASS（同 F1）/ 22 PASS；18 esid 粗体 47→26（−45%）、12-gram 重复率 0.0911→0.0643（−29%）；14 esid 方向相反；**两臂 strong 命中均 0、`{{ref_n}}` 逐条相等（18/18、14/14）**；代价 = 工具尝试 +45~51%、墙钟 +13~17%。**每臂 n=1 → 不宣称可测收益**，默认仍不强制调用 humanizer。
8. **两条待办（已给证据、未落盘，等用户点头）**：**F1** prompt 第 6 条文件写入纪律只覆盖报告正文 → 扩到「本工作区任何文件」（正文/辅助脚本/图表 JSON）；**F2** 同一观察身份词报告内混用（`每月` 3 次 vs `Q4W` 9 次，源文只有 `monthly`）→ 图表 label 取 `Q4W` 使 `A-S9`/`A-S9b`/`A-S10` FAIL；改法 = ①prompt/SKILL 加「一套写法 + 图表 label 复用正文身份短语」②`scenario-a.facts.json` 该观察 `identity_patterns` 放宽到 `每月|每月一次|QM|Q4W`。

**离线测试计数（2026-10-10，R46 后实测）**：runner **39**、scorer（`test_regressions.py`）**35**、tools **19**（`test_pack_dist.py` 5 + `test_replay_run.py` 14）、Node **16**、`tools/test_pack_dist.py` **5/5**；另有 **`evals/numeric-integrity/test-render-facts.py` 28** 与 `evals/runner-gate/test-runner.py` **39**，两者本来就不计入上面那 105/117 的合计口径（README 旧行的 105 = runner 38 + scorer 32 + tools 19 + Node 16，不含 numeric-integrity；R43 把 scorer 提到 35、R46 把 runner 提到 39）。

## 历史交接（2026-10-10 Phase 2 完成）

**Phase 2「交付物不写运行物流」已原地发布并四组验证（2026-10-10）**：用户诉求是「取回失败/环境限制」这一类叙述不该出现在对比报告里。落法是**契约 + 机械门禁**双管：

1. **口径**：交付物只写**材料/来源属性 + 分析深度**（`src=1` / 库内正文即原文摘要 / `非 OA` / 未收录 PMC / 无登记号或 DOI / `N 条按摘要级`）；**我们这一侧的取回过程一律不写**（`本次运行无外网`、`全文抓取失败`、`接口返回 500`、`未能发起检索`、`重试`、工具名、链路）。`非 OA` 只能由明确元数据支撑，**HTTP 500 不是非 OA 证据**。
2. **门禁 `A-P10-no-run-logistics`**（`check.py` `op_no_run_logistics`，fail 级，逐句匹配）；**A-P4 词表删掉 `抓取受限`**、改为接受「来源类或来源侧属性」。
3. **变异/基线**：`M43`（覆盖行尾部追加运行物流 → 只翻 A-P10）；R17 基线带旧措辞 → 新增 `seed_a()`（**只改覆盖行措辞**，保留 route/来源类/深度），`MUT_SEED_A=0` 复现未种子证据。
4. **计数**：scenario A **45 条（44 fail + 1 warn）**；变异 **64 项**；回归 **32 项**（`NoRunLogisticsTests` 5 项）。
5. **发布**：dist **100,422 B / sha `4d92d3b4b7c3`**（已被 R41 的 `ab1efaccf624` 取代）、prompt **v1.7 59,154 B / sha `2aac60f1c992`**（已被 R41 的 `78c1a2a71efe` 取代）、Skill **v1.0.8**，`status` in sync。**R40 四组（2/4/18/14）各 22 PASS / 0 FAIL**，四份覆盖行物流 grep 全 0。
6. **R40-1 遗留已由 R41 处理**：场景 A 下 5 项 FAIL，根因 = 模型未用记录自带 `drug_earth_name_cn`（软规则已存在，属指令遵循偏差）→ R41 锐化为硬规则后 `A-C1`/`A-C2` 转 PASS，剩 3 项见 R41 的 F2。

**两个 humanizer skill（`report-humanizer-zh` / `-en`，Phase B 已完成）**：加①数字/符号排版统一规则 + 文档级弱命中 `W-FMT-MIXED`（`tell-scan.py` + 两份 `SKILL.md` + 两份 `patterns-*.md` + 各 2 项回归 → 25/25）；②过程口吻边界（宿主契约要求的声明写成**材料属性**，不写运行环境/链路）。bump **v0.1.1**（zh 28,406 B / en 30,765 B），**TS 原地更新成功**（平台版本号仍 1.0.0）。原地更新脚本 = `apps/skill/tools/push-skill-inplace.py`（五道护栏），校验脚本 = `apps/skill/tools/verify-skill-upload.py`（只读）。

## 当前交接（2026-09-18 全项目审查后）

**三组已跑完（覆盖下文运行中状态）**：R27 4/4、R28 18/18、R29 14/14 均产出报告。R27断言全过；R28写文件冲突导致断言FAIL；R29无FAIL但3次拒参/2次全文500已披露。设计冲突披露部分生效，三组内容审查均有待改项，不宣称全绿。详见台账 R27–R29。以后固定全跑三组。Git本轮仅提交任务相关资产/证据文档，Docker未涉及。

**最新：数值事实账本版本已原地发布并完成 R30 固定三组测试。** 发布前 config/status/deps 均通过，prompt v1.6 本地 57,656 B / SHA `115bac4e5295`，skill v1.0.7 / skill_id `ad75ec2c44334f389a0394895a47b765`，20/20 文件回读一致，dist 93,090 B / SHA `dd4d83f871692bd4c70b98cbf6787af1b6f839426312aee017e75630d95a06bb`。R30-1/2/3 分别覆盖 4/18/14 条，均成功产出报告，引用、图表、实体锚点、固定路径和回执断言通过；R30-1 因本地 `__pycache__` 污染支持文件清单，R30-2/R30-3 因平台重复 `write_file` 已存在文件导致 `no tool errors` 失败。报告未丢失，原始证据保留；不能宣称本轮三组无工具错误全绿。详见 `docs/toolsmith-verification-log.md` R30。

**附录形态升级 + 时间线加「发表时间」+ 移除实体内联引用（2026-10-09 已按 `--new-version` 发布为 prompt v1.7 / Skill v1.0.8）**：附录从「每行一个数值的 11 列宽表」改为**一张矩阵**——**列 = 试验**（同试验多披露按账本新增的 `records[].trial` 合并键合并为一列，表头标披露条数；缺键时回退注册号 → `study` → `ref`，绝不凭名字合并），**行 = 维度与终点父级**，按 `试验设计 → 试验结论 → 有效性 → 安全性 → PK/PD → PRO` 分段；治疗臂/时点/评估/人群与终点口径细分标签写进单元格（`治疗臂·时点·评估·人群：结果 单位（统计量）{{ref_n}}`，未报告 `—`），同一终点的不同时点/口径统一到同一行。账本 `records[]` 新增**必填** `conclusion`（缺失即门禁失败），`kind` 收成封闭词表（含英文映射），`endpoint` 必须是**最小可比父级**，`version` 只放披露版本/数据截止。附录标题改为 `## 附录：证据对齐矩阵（数值事实账本）`。四个模板的时间线表首列加**发表时间**（原文披露日期优先，`paper_release_time` 日期部分兜底，都没有写「未报告」；只作最后排序依据，不得按输入顺序推断）。**实体内联引用（v0.10/v0.11 的 `[名字](entity:type:id)`）整体移除**：删 `references/entity-inline-reference.md`、`evals/validate-entity-refs.mjs`、`test/entity-refs.test.mjs`；渲染器先把旧账本展示字段里的 `entity:` 包装**确定性剥离**（`quote`/`source_file` 除外），再由 `ENTITY_LINK_RE` 门禁拦残渣；正文/表格/图表/账本一律写纯名。回归：`python3 evals/numeric-integrity/test-render-facts.py` **21/21 绿**。**已按用户授权改用 `--new-version` 发新版本（不原地更新）**：本地 prompt `system-prompts/multi-clinical-result-comparison-v0.16.md`（54,264 B / sha `a638a93fe934`）→ 线上 **prompt v1.7**（project prompt id `394a6e51617842a0ae9403579dcf8f45`）；dist `dist/multi-clinical-result-comparison-v0.16.zip`（93,757 B / 19 entries / sha `e5aad92c2618`）→ 线上 **Skill v1.0.8** / skill_id `cd93a42af72b4828b1690b3a7bccfa06`（19/19 文件一致）；`toolsmith-publish status` → **in sync**。发布前依赖闸门拦下两处上游变化并复核：chart skill v1.0.12 被重新发布（运行期取模板，无需改本地）、内置 `read_file` schema 变化（`limit` 默认 100）→ 相应把 prompt 的 digest 上限从 ≤300 行收紧为 **≤100 行**。**固定三组回归（2026-10-09）**：R33 三组跑出两个**我方**缺陷——①`APPENDIX_INTRO` 把字面 `{{ref_n}}` 写进交付报告导语，被 runner 占位符断言判 FAIL；②跑动期间改仓库/跑本地测试，导致「支持文件清单」断言报 `missing=[…pyc]`（该断言的 `missing` 方向是**本地有、线上没有**，纠正了 R30/R32 的旧归因）。两处均已修（导语改写 + 新增断言并做负向对照，回归 21 → **22/22**；测试顶部 `sys.dont_write_bytecode = True`；`AGENTS.md` §7 新增「真跑期间冻结仓库」硬性条目）。修后 dist 重打为 **93,792 B / 19 entries / sha `dd9c2998c2b6`**，并用 `toolsmith-publish push-skill --version 1.0.8` **原地更新**同一版（`skill_id` 不变、prompt v1.7 未动、`status` in sync），再跑 **R34 三组全绿：22 PASS / 0 FAIL、exit 0**，附录列数 4 条→1 列、18 条→10 列、14 条→11 列。详见台账 R33（缺陷）与 R34（修复验证）。

**R37 固定三组全绿 + v0.16.1 四点改动已原地发布（2026-10-09）**：R35/R36/R37 连续三轮跑「prompt 第 6 条文件写入纪律」的三次迭代（R35：`write_file` 拒覆盖；R36：改走 `edit_file` 长中文目标串失配；R37：第 6 条重写为「不要在长草稿上做外科式编辑，正文一次写成 `overwrite=True`」）——**R37 三组 22 PASS / 0 FAIL / exit 0**（`6143cc8f` / `a7c58280` / `15b0f2b5`，347.7 / 530.5 / 411.9 s，写文件次数降到 2–3 次），R36-3 的「16 s、零产物、却 `outcome=succeeded`」flake **未复现**（仍留平台问题单）。R37 产物取证发现四项产品面问题并按用户五点诉求整改为 **v0.16.1**：①**图表与表格去重**——证据链时间轴图原来逐字复述时间线表格（R37-1 图的 `content`/`description` 就是表格三列），现规定**图只画骨架、表格是数值唯一出处**（图内除 `time` 锚点外禁止任何数值，图内文本与表格单元格不得有 ≥8 字连续相同文本）；②**单试验附录改「每条披露一列」**（R37-1 原为 1 列 + `<br>` 堆叠长文本）；③**长散文不再进附录**——`records[]` 必填收成 `ref` / `identity` / `conclusion`（+ `trial`），`title` / `design` / `arms` / `coverage` 降级为「接受但不渲染」，四个散文行从 `DESIGN_ROWS` 删除；④**附录列头形态统一**由渲染器固定（多试验 `**试验名**<br>注册号 · N 条披露`；单试验 `**ref_n**<br>短版本标签`，`_short_version` 绝不留未闭合 `（`），并新增 audit `appendix_layout` / `appendix_columns`；⑤**行标签不稳定**（R37-1 账本含 14 条模型自造设计 fact：研究中心/分层因素/终点定义/基线性别分布…）改由 prompt/SKILL 白名单治理（只允许入组例数、分析集与分母、数据截止与随访、事件数、检验边界、给药方案），**渲染器不加硬截断**。本地门禁：`test-render-facts.py` **26/26 OK**、`verify-run-chain.py` `GATE: PASS`、`mutations.py` `arm a: flipped 43/43` + `arm b: flipped 12/12`。**发布方式：原地更新**（用户明确「ts 原地更新、不新开版本号」）——dist 重打 **99,640 B / 19 entries / sha `5457c8c4fd00`** → `push-skill --version 1.0.8`（`skill_id cd93a42af72b4828b1690b3a7bccfa06` 不变、`is_current=True`）；prompt **58,795 B / sha `1d9153c88f3c`** → `push-prompt --version 1.7`；`status` → **in sync**（19/19 支持文件一致）。另修 runner 文档悬空指针（**O39**：`cmd_param_doc` 删指向已删 `references/entity-inline-reference.md` 的从句；备份 `toolsmith-publish.v10.bak`；`docs/params-tool-schema.md` 31,729 → 31,671 B）。**R38 三组验收全绿**（`4014f791` / `5ddb5fac` / `c8851877`；390.9 / 494.2 / 534.4 s；各 **22 PASS / 0 FAIL / exit 0**）：单试验附录变 **4 列**（`appendix_layout=disclosure-columns`）且表头统一 `**ref_n**<br>短版本标签`；跨试验 10 / 11 列表头全为 `**试验名**<br>注册号 · N 条披露`（同表现三套命名混排消失）；R37-1 的 14 条自造设计行全部消失；时间轴图只剩 `time` 锚点 + 定性短语，与表格共享 **0 处** ≥8 字连续文本。详见台账 R35–R38。

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
python3 evals/fact-check/mutations.py                                     # 负向对照闸门（64 项变异/合法对照；`MUT_SEED_A=0` 关掉 A-P10 基线种子）
python3 evals/fact-check/test_regressions.py                              # 门禁回归（32 项，含 A-P10 的 NoRunLogisticsTests 5 项）
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
