# AGENTS.md — 常驻 program.md（autoresearch 循环）

## R59 完成（2026-10-13，**已原地发布** + n=2 实测，KEEP）

文体门禁**内联**：把上游确定性扫描器**逐字节复制**进本包（`skill/.../scripts/tell-scan.py`，22,558 B）＋新增自包含 `references/prose-style-zh.md`（13,071 B / 200 行），`SKILL.md` / `toolbox.md` / 系统提示词六处明写 **不加载、不等待、不依赖任何外部文体 skill**。口径：**门禁必跑（定稿后 1 次本地 `execute`，0 token）≠ 改写必做（只由强命中触发，弱命中仅线索）**；历史触发率 6.1 %（`load_skill` 7/115）→ 现在 2/2 跑、每跑 2 次必跑，两跑 `SCAN_EXIT=[0, 0]`（强命中 0）。runner 加**第 18 项断言**（缺调用 FAIL / 脏退出 FAIL / 无回显 WARN），`test-runner.py` **41 → 45**。

- 线上（原地）：prompt **v1.8 81,614 B / `aaf77e7c284b`**、skill **v1.0.9 dist 180,675 B / 29 entries / `099504055d79`**；回读 prompt 逐字节一致 + skill **29/29 identical** + **`status: in sync`**。
- 实测（`DeepSeek Flash`，固定 4-esid 输入，web off）：`r59-gate-1/2` wall **332.1 / 394.5 s**、out **52,794 / 70,063**、facts 42 / 43、各 **21 PASS**；断言 #18 = `prose gate ran and exited clean — 2 call(s), SCAN_EXIT=[0, 0] strong-free=True`。未回潮：`task` 0、`--scaffold` 0、`merge_ref_facts` 0 次调用。
- 记账：**R59-1** 双副本漂移（由 sha256 同一性测试兜住）、**R59-2** WARN 语义、**R59-3** 断言只在 artifacts 分支、**R59-4** 模型给 `execute` 传 `timeout_seconds=180`（上限 120）被拒后自动重发成功。平台侧：**P-R59-1** `execute` 参数名 `command` vs `shell_command`、**P-R59-2（已作废）** 发布窗口内项目挂载 4 → 2 系**用户主动从配置取消**（规则已内联，不再需要挂载 humanizer；无需恢复）、**P-R59-3** `execute.timeout_seconds` schema 无 `maximum`。详见 `docs/evidence/r59-prose-gate-inline-2026-10-13.md` 与 `docs/toolsmith-verification-log.md` R59。
- 计数口径见下方「离线测试计数（2026-10-13，R59 后实测）」（合计 **221**，含 numeric-integrity 249）。

## R52 回退完成（2026-10-12）

用户已授权回退。运行资产与 dist 恢复到 R51 commit `3adb77c`（**其后 R58 / R59 又依次原地更新过，见上方 R59 节**），R52 新增两份接口测试随实现撤销，失败证据保留在 docs/evidence 与 Git 历史。TS 采用原地恢复内容：当前标签仍 prompt 1.8 / skill 1.0.9（skill_id `16aeb0406e12425bad27a2444f17225e`），实际内容 == R51 的 prompt 1.7 / skill 1.0.8。prompt SHA `bf7b45dbf5d0`，dist SHA `081cd850befc` / 152,558 B；回读 26/26 identical、status in sync、项目绑定正确。此前“尚未回退”段落为历史实验状态，本段覆盖它。


## R52 交接（2026-10-12）

本轮用户授权流程梳理 + TS **新版本** + TS 真测，不是原地更新。运行资产收敛为五阶段执行契约；候选 facts 改为显式差量审校（`--apply-review`），组装不替代原证据校验；prompt/file-delivery 整份重写矛盾与时间轴 weight 残留已清。冻结评分器、事实清单、输入和 runner 未动。新增 review 10 + workflow 3，本地合计 244 绿，变异 44/12 与链路 GATE PASS。发布与实跑已完成，判定不 keep；TS 当前仍为 1.8/1.0.9，回到旧版本须另行取得 TS 写入授权。结果见 PROJECT_STATE / 台账 / R52 证据。


本文件是这个仓库的**常驻程序说明**，任何新会话先读它，再读
`PROJECT_STATE.md`（当前实现快照）、`docs/toolsmith-verification-log.md`（台账）、
`docs/autoresearch-iteration-plan.md`（为什么这么做）。

一句话：**我们把这个 skill 当成「agent 唯一可改的 `train.py`」来迭代 —— 改规则 → 发版 → 真跑 →
离线判分 → keep/discard。**

---

- R52 已完成一次新版本实验：prompt 1.8 / skill 1.0.9 已发布；真实固定回归 4/18/14 的机械断言各 22/22，但耗时分别 680.1 / 569.5 / 691.6 s，高于 R51；B 拒绝断言通过，离线措辞 11/12。R52 判定不 keep，内容问题与 schema 参数漂移证据见 `docs/evidence/r52-workflow-review-2026-10-12.md` 和台账 R52。

## 历史 R49+R50 交接

**触发（R49）**：用户在共享报告上提四条交付层投诉（附录开头 ≈600 字版式规格；附录列头不可读/注册号重复；同一小节里图与表重复交付同一批数值；交付耗时）。**触发（R50）**：用户投诉交付报告里出现**模型自己的方法/分类叙述**（现场：`**分析模式：** 跨试验、非头对头、按指标域对齐。` / `**可比性结论：** 可绘图。…`），要求「全篇排查同类思考表述并优化 → 原地更新 TS → 再测试」。两轮内容改动**同批原地发布**（prompt v1.7 / Skill v1.0.8，标签不变）。

1. **R49.1 附录版式**：`render-facts.py` 删 `APPENDIX_INTRO`（≈600 字规格说明），只留一行 `APPENDIX_LEGEND`；`check_report.py` 新增两条 FAIL —— 附录标题与其表格之间出现 **>100 字**散文块、附录标题出现 **>1 次**（手写附录 + 渲染附录并存）。4 模板写明「标题/图例/列由渲染器拥有」。
2. **R49.2 附录列头**：单试验 ≥2 披露 = `**可读短标签**<br>ref_n`（无标签回退 `**ref_n**`）；第二行注册号若已出现在展示名里则删除（`_column_header` / `_column_label`）。
3. **R49.3 一数一处（方案 1：图全留、只删重复）**：制度性根因是两个速览模板同时规定「表 + 图」。`check_report.py` 新增两条 FAIL —— 图自身散文（`subTitle`/`describe`/`data[].description`）复述自己的绘图值；非附录小节「有图 + 表里含该图 ≥2 个绘图值」。豁免：剂量/时点/例数数字、研究内对照值与边界值、附录与时间线图。两模板「图表后保留上表」→「不重复上表」。
4. **R49.4 四条提速杠杆**：`references/toolbox.md` FAQ（别再翻脚本源码）；prompt 禁回读自产文件 + `check_report.py` 一次定稿；`build_ledger.py --scaffold`（原始 payload → 候选事实行，**永不直接写 `ledger.json`**，默认 `work/facts.candidates.json`）；图表 spec 一次成稿。
5. **R50 第四语域 —— 报告不得叙述自己（本轮核心）**：`check.py` 现有守卫族（A-P1 覆盖行 / `op_original_check_names_class` / A-P5 / A-P7 模板规格回抄 / A-P8 规则元陈述 / A-P10 运行后勤）**都不覆盖**「报告叙述自身方法/分类/处理过程」。新增落点全部在 `check_report.py`（**判分器 `check.py` 一行未动**，保住 44/12 变异套件语义）：6 个常量 + `_meta_narration_findings()` + `main()` 里独立的 `report voice` 检查组。**FAIL** = 自述标签（bullet 或表列：`分析模式`/`分析口径`/`选择依据`/`可比性结论`/`对齐等级`/`不绘图原因`/`有限并列原因`/`纳入标准`/`检索策略`/`报告结构`）、分类判断语（`可绘图`/`只能有限并列`/`不具备绘图条件`/`部分对齐`/`仅背景对齐`）、过程短语（`本次选择`/`本次纳入`/`我们选择`/`本轮`）、内部与运行环境词（`src=`/`esid`/`payload`/`JSONL`/`MCP`/`工作区`/`沙箱`）、自证尾巴（`无未复核记录`/`无遗漏`/`全部通过`）。**WARN** = 宽口径自指（`本报告`/`本次`，负向断言排除合法的「本次披露」）。刻意**不**禁 `token`/`轮次`（会误伤「治疗轮次」）；**`比较口径` 不计 FAIL**（4 模板本来就带该 blockquote）；保留位 = 非头对头声明一句 + `原文核对：` 覆盖行（只写材料与深度）。同一条规则同时写进 `SKILL.md`、prompt 交付前检查段、`references/toolbox.md` §7 + 两条 FAQ、`references/input-contract.md`（覆盖行只写来源类**文字**，`src=N` 等内部字段名不进交付物，且**不写自证尾巴**），4 模板的 `分析模式`/`选择依据`/`对齐等级` 全部删除、差异改写为时点/人群/定义/方向。
6. **现场取证**：对用户看到的旧产物 `…-r48-a` 回放新检查器，四类语域逐条被抓（`the report labels its own method ('**分析模式：')`、`('**选择依据：')`、`('**可比性结论：')`、4 处 `对齐等级` 表列、`纳入本次`/`只能有限并列`/`不生成优效排序`/`部分对齐`、`self-audit tail: '无未复核记录'`、`internal field or runtime vocabulary: 'src=1'`）。
7. **本地门禁（全绿）**：`mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS`；`test-render-facts.py` 28；`test-skill-scripts.py` **54 → 58**（R51 新增 4 条：时间轴 `weight` / `weightLegend` / `legend`+`shape` 被拒、骨架与两份 reference 文档不得再出现已退役字段）；`test-check-report.py` **12 → 20 → 25**（前 8 条是 R50 语域规则，含两条「不得误报」：材料化覆盖行、解读边界散文；后 5 条是 R51 时间轴退役编码的成品/正文守卫）；`test-build-ledger-scaffold.py` 9；`test_regressions.py` 35；`test-runner.py` **40 → 41**（新增「本地 `__pycache__/*.pyc` 不得算作线上缺失」，见 O48）；`test_pack_dist.py` 5；`test_replay_run.py` 14；`node --test` 16/16；`verify-run-chain.py` `GATE: PASS`（**115** histories / 5 可比 / 110 跳过）。**计数纪律 = runner 41 + scorer 35 + tools 19 + Node 16 + skill-scripts 58 + check-report 25 + build-ledger-scaffold 9 = 203**（加 numeric-integrity 28 = **231**）。
8. **打包/发布**：dist **152,558 B / sha256 `081cd850befc` / 26 entries**（R49 时为 151,330 B / `df993fdddf83`；**EXPECTED 仍 26** —— R49/R50/R51 三轮都不新增 bundle 文件，`--scaffold` 挂在既有 `build_ledger.py` 上）；prompt = **76,578 B / sha256 `bf7b45dbf5d0`**（R51 **未改 prompt**；**有意不再激进瘦身** —— 缓存命中率 96–98%，丢规则的风险大于省 token）；发布前 `deps` = `unchanged since the recorded baseline`（⚠ **R51 实证 `deps` 只比版本标签，上游原地更新看不出来**，见 O50）；`status` = **in sync**。
9. **真跑：2 组 2 esid（与 r48-a/r48-a2 同输入）+ 固定三组回归（4/18/14 esid，输入逐字节复用 R48）**：`r50-a` **24 PASS / 1 FAIL**（唯一 FAIL = **O48** runner 假 FAIL）、`r50-a2` **25 PASS / 0 FAIL / exit 0**；**`r50-4` / `r50-18` / `r50-14` 各 25 PASS / 0 FAIL / exit 0**（25 / 46 / 31 tool calls，墙钟 383.2 / 617.3 / 510.8 s）⇒ 新语域闸门**零 thrash**，**O49 未在 18 esid 组复发**（图表行只点自己那条观察的对照臂）。**语域修法在生产侧生效**：正文无 `分析模式`/`选择依据`/`可比性结论`；速览段只写核心终点要点 + 图，数值表移到 §四并带 `解读边界` 列；覆盖行写成「来源类均为 PubMed 期刊论文，深度为期刊摘要级（库内正文即原文摘要，未取 PMC 全文）」——无 `src=`、无自证尾巴；本地 `check_report.py` 回放两份产物 `report voice` 全绿（余下 FAIL 仅为本地回放的 `::visualization` 前缀差异）。**速度**：同输入 r50-a2 的 tool calls **45 → 26**、out token 69,610 → 63,097、reasoning 51,506 → 43,373、墙钟 359.5 → 343.3 s。**离线 scenario a**：`r50-a` **43/44**（= r48-a 基线，唯一 A-ATTR）、`r50-a2` 38/44。
10. **本轮新增/结案 O 条目**：**O48 已修**（runner 支撑文件清单把本地 `scripts/__pycache__/*.pyc` 当「线上缺失」⇒ 假 FAIL；改法 = 清单比对前过滤 `__pycache__`/`*.pyc`；备份 `toolsmith-publish.v16.bak` + `py_compile` + 零网络闸门 + `test-runner.py` 40 → **41**）；**O49 待修（1/3 样本：r50-a2 触发，r50-a 与 18 esid 回归组均未复发）**（图表行 `description` 提到另一治疗臂的剂量/间隔 ⇒ 行身份不再唯一 ⇒ `A-S9`/`A-S9b`/`A-S10` 三条同源 FAIL；改法 = 报告侧一句硬规则，随下一次内容改动发版）；O40 / O44 / O46 / O47 状态不变。
11. **未做**：O49 的报告侧硬规则（下一次内容轮）、O44/O47 等第 2 份样本、O40 在新样本上的复现观察。

## 历史交接（2026-10-10 R48 完成：随包六脚本 L2 + 单遍正文 L3 + 合批调用 L4；**已原地发布并六次真跑验证**）

**触发**：R47 的 per-step token 归因（`/tmp/l2/attr.py`）——自写脚本 + heredoc 占各 run 输出 25–55%（`r47-14`：11 个一次性脚本共 59,598 out tokens；`r47-a`：`report prose draft.md` 13,978 + `execute: other` 17,919；`r47-18`：自写脚本 36,511 B），根因是 R45「`edit_file` 只限报告正文」把模型逼成「用一次性脚本原地打补丁」。用户「L2-4都想要」⇒ 三条杠杆同轮落地，归因改用**历史 16 run 基线 + per-lever 签名**。

1. **L2 — 六个随包脚本已入库**（`skill/multi-clinical-result-comparison/scripts/`，与既有 `render-facts.py` 并列）：`prep_sources.py`（拉取 → `work/sources/ref_<n>.txt` + `work/refs.json` + digest；`--tool-results` 默认 FALLBACK 链 `/workspace/tool_results` → `tool_results` → `/workspace/work/tool_results`）、`build_ledger.py`（facts → 严格 `work/ledger.json`，唯一的校验点；`--check`/`--stats`）、`patch.py`（带断言原子替换：`--count`/`--insert-after`/`--dry-run`；**`--find` 取值以 `-` 开头必须用 `--find=<text>` 等价形式**）、`make_chart.py`（只写内容 spec，envelope 从运行期 chart skill 现取）、`make_citations.py`（引文 JSON，键 = 报告实引 ref）、`check_report.py`（交稿机械检查；退出码 0/3/2——**WARN 只打印、不阻塞**，`--vis-prefix` 供镜像/测试布局覆写）。**六脚本各自内联小工具函数、不共享 `_lib.py`**；所有写入点 `except OSError` → 一行 `ERROR: cannot write …` + exit 2，**不吐 traceback、不半写文件**。契约文档 = 新增 `references/toolbox.md`（精确 CLI/IO/退出码），写进 SKILL.md 支持文件清单，**取代「读源码/自己拼 envelope」的步骤**。
2. **L3 — 正文只写一次**：`work/draft.md` 从流水线移除；带 `[[fact:…]]` token 的正文直接写 `/workspace/output/report.md`，再用**一次** `render-facts.py` **原地**渲染（`--draft` == `--out`，已证 `_atomic_write` 先读后写、安全）；后续小改走 `patch.py`。落在 prompt 第 6 条 + `SKILL.md` 第 9/9b 项 + `references/file-delivery.md` + 输出契约段。
3. **L4 — 合批调用**：prompt 第 7 条给出**目标 ≤ ~25–30 tool calls**；禁止「写 N 个分块再拼接」「重复读同一文件」「手工复查脚本已校验过的东西」。
4. **本地门禁（全绿）**：`py_compile` 六文件 OK；`evals/scripts/test-skill-scripts.py` **54/54 OK（15.0 s）**；`test_pack_dist.py` 5；`test_replay_run.py` 14；`test-runner.py` **40**（R48 +1：`test_cjk_punctuation_delimits_a_receipt_path`）；`test_regressions.py` 35；`test-render-facts.py` 28；`node --test 'test/*.test.mjs'` 16/16；`verify-run-chain.py` `GATE: PASS`（5 可比）；`mutations.py` `arm a 44/44` + `arm b 12/12` + `never flipped []`；`deps` = `unchanged since the recorded baseline`。
5. **运行时路径**：包挂在 `/workspace/skills/multi-clinical-result-comparison/`，脚本一律 `python3 /workspace/skills/multi-clinical-result-comparison/scripts/<name>.py …` —— cwd `/workspace` 下裸写 `scripts/…` **不解析**；prompt / `SKILL.md` / `references/toolbox.md` / 五个 reference 文件与本轮脚本自身的 usage 均已写明。
6. **打包**：`tools/pack-dist.py` `EXPECTED` 19 → **26**（+6 脚本 +`references/toolbox.md`）；dist **138,171 B / 26 entries / sha256 `bf0c9cf84ecf`**；`--check` IDENTICAL。
7. **计数纪律更新**：**164 = runner 40 + scorer 35 + tools 19（pack 5 + replay 14）+ Node 16 + 新增 skill-scripts 54**（numeric-integrity 28 仍单列）。
8. **发布 + 验证（用户「原地」已获批）**：`push-prompt --version 1.7` / `push-skill --version 1.0.8` 均 HTTP 200、回读 `matches_local=True`，`status` = **in sync**（zip `entries=26 identical=26 differing=0`）；六次真跑 = `r48-a` 28 attempts / 312.9 s / **21 PASS 1 FAIL**（模型侧 `read_file offset 越界`）、`r48-4` 42/391.1 s（O45）、`r48-18` 首次 `inconclusive` + 复跑 59/496.0 s（O45）、`r48-14` 28/303.4 s（O45）、修复后 `r48-4b` 51/425.9 s 与 `r48-a2` 45/359.5 s 均 **22 PASS / 0 FAIL**。per-lever 归因：L2 `artifacts/scripts/` 四组全空（基线 r47-14 为 11 脚本 / 61,470 B ≈54% 输出）、L3 四组皆无 `work/draft.md`、L4 attempts a 40→28 / 4 56→42 / 18 56→59（持平）/ **14 66→28（−58 %）**；`read_file` 仍 8–20 次/run。离线 scenario a：r48-a **43/44**（= R47 基线）、r48-a2 40/44。
9. **本轮新增 O 条目**：**O45**（runner 收据正则不认全角 `）` 等 CJK 标点 ⇒ 3/4 组 FAIL；**已修**：`_RECEIPT_STOP` 重建 `TOOL_RESULTS_RX` + 回归测试，离线重放四组全转 PASS；备份 `toolsmith-publish.v16.bak`）、**O46**（模型 `read_file offset` 越界，1/2 组 ⇒ R49 内容轮加一条可检查硬规则）、**O47**（`A-C7` 只认「第 ?16 ?周」，1 样本 ⇒ 待样本）。
10. **未做**：O46 的 prompt 硬规则（R49 内容轮）、O44/O47 等第 2 份样本、O40 报告侧机制在新样本上的复现观察。

## 历史交接（2026-10-10 R47 完成：O43 结案 + O40/O41 报告侧习惯句已原地发布；四组真跑 + 一次耗时 A/B）

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

**离线测试计数（2026-10-13，R59 后实测）**：runner **45**、scorer（`test_regressions.py`）**35**、tools **19**（`test_pack_dist.py` 5 + `test_replay_run.py` 14）、Node **16**、`evals/scripts/test-skill-scripts.py` **62**、`evals/scripts/test-check-report.py` **25**、`evals/scripts/test-build-ledger-scaffold.py` **9**、**新增长条 `evals/scripts/test-tell-scan.py` 10**；另有 `evals/numeric-integrity/test-render-facts.py` **28** 与 `evals/scripts/test-merge-ref-facts.py` **16** 单列（历来不计入合计口径）。**R59 合计 = 45 + 35 + 19 + 16 + 62 + 25 + 9 + 10 = 221（含 numeric-integrity 为 249）**；R51 口径为 203 / 231（runner 41、skill-scripts 58）。

**离线测试计数（2026-10-12，R51 后实测）**：runner **41**、scorer（`test_regressions.py`）**35**、tools **19**（`test_pack_dist.py` 5 + `test_replay_run.py` 14）、Node **16**、`evals/scripts/test-skill-scripts.py` **58**、`evals/scripts/test-check-report.py` **25**、`evals/scripts/test-build-ledger-scaffold.py` **9**；另有 `evals/numeric-integrity/test-render-facts.py` **28** 单列。**R51 合计 = 41 + 35 + 19 + 16 + 58 + 25 + 9 = 203（含 numeric-integrity 为 231）**；R49/R50 口径为 194 / 222。旧口径（R48）：：runner **40**、scorer（`test_regressions.py`）**35**、tools **19**（`test_pack_dist.py` 5 + `test_replay_run.py` 14）、Node **16**、`tools/test_pack_dist.py` **5/5**；另有 **`evals/numeric-integrity/test-render-facts.py` 28** 与 **`evals/scripts/test-skill-scripts.py` 54**，两者本来就不计入上面那 105/117 的合计口径（README 旧行的 105 = runner 38 + scorer 32 + tools 19 + Node 16，不含 numeric-integrity；R43 把 scorer 提到 35、R46 把 runner 提到 39、**R48 把 runner 提到 40**）。**R48 合计口径 = 40 + 35 + 19 + 16 + 54 = 164**。

## 历史交接（2026-10-10 Phase 2 完成）

**Phase 2「交付物不写运行物流」已原地发布并四组验证（2026-10-10）**：用户诉求是「取回失败/环境限制」这一类叙述不该出现在对比报告里。落法是**契约 + 机械门禁**双管：

1. **口径**：交付物只写**材料/来源属性 + 分析深度**（`src=1` / 库内正文即原文摘要 / `非 OA` / 未收录 PMC / 无登记号或 DOI / `N 条按摘要级`）；**我们这一侧的取回过程一律不写**（`本次运行无外网`、`全文抓取失败`、`接口返回 500`、`未能发起检索`、`重试`、工具名、链路）。`非 OA` 只能由明确元数据支撑，**HTTP 500 不是非 OA 证据**。
2. **门禁 `A-P10-no-run-logistics`**（`check.py` `op_no_run_logistics`，fail 级，逐句匹配）；**A-P4 词表删掉 `抓取受限`**、改为接受「来源类或来源侧属性」。
3. **变异/基线**：`M43`（覆盖行尾部追加运行物流 → 只翻 A-P10）；R17 基线带旧措辞 → 新增 `seed_a()`（**只改覆盖行措辞**，保留 route/来源类/深度），`MUT_SEED_A=0` 复现未种子证据。
4. **计数**：scenario A **45 条（44 fail + 1 warn）**；变异 **64 项**；回归 **32 项**（`NoRunLogisticsTests` 5 项）。
5. **发布**：dist **100,422 B / sha `4d92d3b4b7c3`**（已被 R41 的 `ab1efaccf624` 取代）、prompt **v1.7 59,154 B / sha `2aac60f1c992`**（已被 R41 的 `78c1a2a71efe` 取代）、Skill **v1.0.8**，`status` in sync。**R40 四组（2/4/18/14）各 22 PASS / 0 FAIL**，四份覆盖行物流 grep 全 0。
6. **R40-1 遗留已由 R41 处理**：场景 A 下 5 项 FAIL，根因 = 模型未用记录自带 `drug_earth_name_cn`（软规则已存在，属指令遵循偏差）→ R41 锐化为硬规则后 `A-C1`/`A-C2` 转 PASS，剩 3 项见 R41 的 F2。

**两个 humanizer skill（`report-humanizer-zh` / `-en`，Phase B 已完成）**：加①数字/符号排版统一规则 + 文档级弱命中 `W-FMT-MIXED`（`tell-scan.py` + 两份 `SKILL.md` + 两份 `patterns-*.md` + 各 2 项回归 → 25/25）；②过程口吻边界（宿主契约要求的声明写成**材料属性**，不写运行环境/链路）。bump **v0.1.1**（zh 28,406 B / en 30,765 B），**TS 原地更新成功**（平台版本号仍 1.0.0）。原地更新脚本 = `apps/skill/tools/push-skill-inplace.py`（五道护栏），校验脚本 = `apps/skill/tools/verify-skill-upload.py`（只读）。

## 历史交接（2026-09-18 全项目审查后）

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
python3 evals/scripts/test-skill-scripts.py                              # R48 随包脚本回归（62 项；**不能**用 unittest discover，直接脚本跑；跑的是 subprocess，无 __pycache__ 污染）
python3 evals/scripts/test-tell-scan.py                                  # R59 文体门禁回归（10 项：退出码 0/3/2、强 vs 弱、`--allow`、`--json`、**只读**、与上游 tell-scan.py sha256 一致（缺兄弟目录则 skip）；**不能**用 unittest discover）
python3 evals/fact-check/mutations.py                                     # 负向对照闸门（64 项变异/合法对照；`MUT_SEED_A=0` 关掉 A-P10 基线种子）
python3 evals/fact-check/test_regressions.py                              # 门禁回归（35 项，含 A-P10 的 NoRunLogisticsTests 5 项）
python3 evals/scripts/test-check-report.py                                 # 交付层机械检查回归（25 项，含 R49 附录/图表去重、R50 第四语域与 R51 时间轴退役编码；**不能**用 unittest discover）
python3 evals/scripts/test-build-ledger-scaffold.py                       # `build_ledger.py --scaffold` 回归（9 项；**不能**用 unittest discover）
python3 evals/runner-gate/test-runner.py                                   # runner 单测（45 项，含 R48 的 CJK 收据分隔符回归与 R59 的文体门禁 4 例；**不能**用 unittest discover）
python3 skill/multi-clinical-result-comparison/scripts/tell-scan.py <report.md>   # R59 文体门禁本体（exit 0 干净 / 3 强命中 / 2 用法；`--json` / `--allow` / `--weak`）
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
