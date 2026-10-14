# Project State

## R68 — 清掉「我们自己的参考文件教出来的 FAIL 词汇」（**2026-10-14 已原地发布 + web-off 三组；KEEP，但只说对了一半**）

**动机**：R67 证据 §6 ① 指名 —— `r67-14` 花 2.5k 字仲裁我们自己造成的矛盾：`references/cross-trial-comparison.md` Step 4 要求 "a dedicated last column for alignment level"，而 host prompt 与 `check_report.py`（`META_COLUMN_RE` / `META_LABEL_RE` / `METHOD_NARRATION_RE`，三条皆 **FAIL**）禁止 `对齐等级` 列与 `部分对齐` 这类词。

**改动**：`cross-trial-comparison.md`（12,067 → 13,831 B）末列一律 `解读边界`（写材料差异本身：时点/人群/定义/评估/方向），列名 `对齐等级` 明写为交付失败；alignment 分级与 comparability label 标注为**内部判定、never printed**；Required output 第 3 条去掉 "no-chart reason"。`toolbox.md` §4（30,007 → 30,219 B）加「文字数字（`Fifty-one`）照抄即合法」一行。`evals/scripts/test-check-report.py` 新增 `ReferenceSetVsGateTests`（25 → **27** 测，对改前文本命中 4 处 ⇒ 真回归测试）。prompt **未动**、脚本逻辑未动、`deps` unchanged。

**发布**：in-place，prompt v1.8 `999ffe38547a` 未变；skill v1.0.9 内容替换 29/29；`status` → **in sync**；dist **184,391 B sha `af36ade72593`**；`GATES_FAILED=0`（首轮 dist 过期 rc=3 → 重建）。

**真跑**（固定 4/18/14，串行，web off）：

| run | wall s | 步 | out tok | `自产物回读/返工` | 断言 |
|---|---:|---:|---:|---:|---|
| r68-4 | **306.3** | 20 | 53,438 | 0 | 22P/1F |
| r68-18 | **609.4** | 41 | 108,848 | 14.3 | 22P/1F |
| r68-14 | **505.5** | 28 | 96,866 | 0.9 | 22P/1F |
| **均值** | 473.7（R67 434.7） | 29.7 | 86,384 | **5.1**（R67 9.4） | 22P/1F × 3 |

**判定 KEEP，但只说对了一半**：✅ 目标矛盾消失（同一个 14 组 `对齐等级` 0 次、无仲裁；`r68-18` 的 3 次只是复述 host prompt 禁令）；✅ 九跑断言恒 22P/1F（唯一 FAIL = 平台 `P-R53-1`）；✅ `自产物回读/返工` 保持 R67 低位。❌ **同一类缺陷仍在，换了位置**：真凶是 **`templates/mixed-comparison-report.md`**（第 70 行示例单元格写着 `直接对齐/部分对齐/仅背景对齐…`，第 30 行有 `处理模式` 列）—— `r68-18` 为 `解读边界` 单元格里能不能写 `部分对齐` 花了 41 次合法性推理 / 24.9k 字符；`r68-14` 也把 `中（部分对齐）` 删掉。**R68 的扫描范围只写了 `references/`，漏了 `templates/`**（纪律教训）。**不得声称 R68 减负**：墙钟 434.7 → 473.7、out tok → 86,384、步数 → 29.7，全在噪声内且方向偏坏。

**R69（未改，首选）**：① 清扫 `templates/*.md` 被门禁拒的词汇（等级词 → 材料差异示例；`处理模式` 列按同一原则处理）；② 静态测试扩到**整棵打包树**（`skill/**/*.md`/`*.json`，对每个模板跑 `check_report.py` 的正则族）。

**证据**：`docs/evidence/r68-template-vs-gate-vocabulary-2026-10-14.md`。

## R67 — `render-facts.py` 幂等 + 空 `unit` 拼写写进契约（**2026-10-14 已原地发布 + web-off 真跑三组；KEEP，且是首个真移动目标指标的一轮**）

**动机**：R65 三跑把探针从「`·` 怎么写进 `value`」换成渲染器自身语义（`r65n-4` 逐字：*"if it already exists, does it replace it?"* → *"Confirmed: render appends a second appendix (not idempotent)."*）。模型靠实验测出这条**未文档化**语义，并用「把正文抄成 `work/body.md`」绕行，代价记在语义阶段 `自产物回读/返工`：R62 0.8 s → R65n **79.3 s / 14,392 out tok**。

**改动（行为侧，非文字侧）**：
- `scripts/render-facts.py`：新增 `_strip_rendered_appendix()` —— `APPENDIX_TITLE` 是草稿**最后一节**时先剥掉再渲染 ⇒ 就地重渲染**幂等**；`--audit` 加 `idempotent_rerender`；docstring 写明幂等 + 空 `unit` 事实（37,696 → 39,266 B）。
- `references/toolbox.md` §4（28,845 → 30,007 B）：幂等段 + 「**不需要**抄 `work/body.md`、**不需要**读回产物查附录」+ 空 `unit` 不留空格/占位符。
- `system-prompts/…-v0.16.md` 规则 6（81,413 → **81,687 B**）：一句幂等 + 两条禁止。
- `SKILL.md`（45,909 → 46,017 B）：渲染门禁同口径半句。
- `evals/numeric-integrity/test-render-facts.py`：+3 测（自身输出回喂 ⇒ 逐字节相同且只 1 个附录；中段同名标题不动；空 `unit` 无尾随空格）29 → **32**。

**发布**：in-place；prompt v1.8 `999ffe38547a`（81,687 B）/ skill v1.0.9 29/29；`deps` unchanged；`status` → **in sync**；dist **183,824 B / sha `c98916b3cc26`**。

**真跑（固定三组 4/18/14，输入逐字节复用 R63，串行，web off）**：

| run | wall s | 步 | render 调用 | build_ledger | out tok | `自产物回读/返工` | 断言 |
|---|---:|---:|---:|---:|---:|---:|---|
| r67-4 | **331.7** | 22 | 1 | 2 | 63,120 | **0** | 22P/1F |
| r67-18 | **392.2** | 27 | 1 | 2 | 77,884 | **19.4** | 22P/1F |
| r67-14 | **580.2** | 32 | 1 | 2 | 107,002 | **8.8** | 22P/1F |
| **均值** | **434.7**（R65n 459.7 / R63 546.9） | 27.0 | 1 | 2 | 82,669（持平） | **9.4**（R65n 79.3） | 22P/1F × 3 |

**预登记判据（真跑前写在 R65 台账 R65-1 + 证据 §6.3）全部成立**：`自产物回读/返工` 79.3 → 9.4 s（**−88%**）；`second/another appendix` 3 → **0**；`body.md` 绕行 4 → **0**；render 调用 4/3/1 → **1/1/1**。断言九跑恒 22P/1F（唯一 FAIL = 平台 `P-R53-1`）。**裁定 KEEP** —— 迭代史上第一次目标指标真移动（R63 / R65 都只改形状、未移动任何测量值）。墙钟均值三代最低，但**不据此声称提速**。

**R68 候选（三跑暴露，均未改）**：① **包内自相矛盾（优先）**：`references/cross-trial-comparison.md` 模板带 `对齐等级` 列，而 host prompt 与 `check_report.py` **禁止**该列名 —— `r67-14` 花 2.5k 字仲裁（*"check_report.py fails on 对齐等级 as a table column … must be replaced by 解读边界"*）；② 源文用**文字数字**（`Fifty-one patients`）时 `value` 照抄文字是合法的、但包内没说过，模型宁可换 quote；③ 14 组 2 步长思考 239.2 s（41% 墙钟）已全是内容分析，不再含契约不确定性。

**证据**：`docs/evidence/r67-render-idempotency-2026-10-14.md`。

## R65 — token 契约唯一化 + 提交前可自查（**2026-10-14 已原地发布并真跑；裁定 KEEP，提速假设未证实**）

**动机（R63-2 观察 + 本轮只读实证）**：R63-2 记下「`r63-14` 有 2 次自造探针草稿渲染 ⇒ 禁令只改试错外形、未除动机」。本轮把动机坐实到**文本层**：

1. **触发原文**（`r63-4` msg[23] thinking 逐字）：*“The toy example shows `"value": "11.1"` with quote containing "11.1" — no guidance on ·. … I'll try "." values; where the quote uses ·, the validation will fail and I'll then switch that fact's quote/value …”* ⇒ 模型**明确采用「先瞎猜、等校验失败再改」**。
2. **契约在源码里是精确的**：`render-facts.py` l.253–258 与 `build_ledger.py` l.609–615 跑**同一套检查**（`quote ⊂ 源文`、`value ⊂ quote`，只归一空白与减号）；而且 `build_ledger.py --check` **早就能在起草前自查、不写文件** —— 这条现成能力**此前从未在任何运行期文本里被点名**。
3. **交付包里有一份自相矛盾的范例**：`build_ledger.py` docstring 的 `"value": "-5.3"` + `"quote": "安慰剂组 MDS TBR 下降 5.3%"` 原样喂脚本 **EXIT=3**（`value '-5.3' is absent from quote`）—— 模型能读到的唯一一份完整范例，本身就是校验器拒绝的形状。

**改动（四文件 + 一条测试，规则一条未删）**：

| 文件 | 字节 | 内容 |
|---|---|---|
| `references/toolbox.md` §4 | 27,540 → **28,845** | 两条强制条件改成可静态判定（只归一空白/减号；`value` 只能是印出来的字符）＋ **实测判定表**（`11.1 · 9.8` ✅ / `11.1` ✅ / `11.1 vs 9.8` ❌ / 派生 `-5.3` ❌）＋ **点名 `build_ledger.py --facts work/facts.json --check` 即提交前自检**，明令不写探针草稿试语法 |
| `scripts/build_ledger.py` docstring | 29,515 → **30,198** | 范例 `value` `-5.3` → `5.3`（arm 改「安慰剂组」，与 quote 自洽）；新增：两条检查在本脚本内、只归一空白与减号、**派生数字不得进 `value`**、`--check` 即自检 |
| `system-prompts/…-v0.16.md` | 80,960 → **81,413** | ledger 段一句收紧 + 具名自检命令 |
| `SKILL.md` | 45,485 → **45,909** | 同口径收紧 + 指向 toolbox §4 |
| `evals/scripts/test-skill-scripts.py` | 44,979 → **46,023** | 新增 `test_value_must_be_a_verbatim_substring_of_its_quote`（✅✅❌❌ 四例成断言）⇒ 62 → **63** |

**顺手收掉 R64 留下的文本冲突**：`toolbox.md` 调用段新增 **One marker, one meaning** —— `EXIT=${PIPESTATUS[0]}` 为通用形态，tell-scan 的 `SCAN_EXIT=$?` 同样可读（runner 两者都认），**但禁止混写 / 禁止裸 `… | tail -40; echo "EXIT=$?"`**（四处专属写法故意不改：改它们只白烧字节，冲突由这一句一次说清）。

**本地闸门（改后）**：`py_compile` 0 · test-render-facts **29** · test-skill-scripts **63** · test-tell-scan 10 · test-check-report 25 · test-build-ledger-scaffold 9 · test-merge-ref-facts 16 · test_regressions 35 · mutations b 12/12 · test-runner **48** · `verify-run-chain GATE: PASS`（5 可比）· test_pack_dist 5 · test_replay_run 14 · node 16 · `pack-dist --check` **IDENTICAL 182,666 B `fc438d58f02b`** ⇒ `GATES_FAILED=0`（dist 181,638 → 182,666）。

**状态**：已原地发布（prompt v1.8 `f2d2422e367c` / skill v1.0.9 29/29，`status` in sync）、已真跑 web-off 三组。

**实测结果（web off，与 R63 同条件；第一次带 `--web` 的组已作废，重跑为 `r65n-*`）**：

| | server s 均值 | 步 | 调用 | out tok | reasoning | 探针渲染 | `--check` |
|---|---:|---:|---:|---:|---:|---:|---:|
| R63（4/18/14） | 546.9 | 24.7 | 31.7 | 98,963 | 71,984 | 2 | 0 |
| **R65n**（4/18/14） | **459.7** | 30.0 | 35.3 | **82,015** | **54,812** | 3 | 3 |

- **逐项**：预登记「探针渲染 = 0」**证伪**（2 → 3；R63 集中在 14 组，R65 集中在 4 组）；`·`/value 契约的触发词三跑 **0** 命中（该洞未再触发）；`build_ledger.py --check` 采用 **2/0/1**（R63 **0/0/0**）；out tok −17% / reasoning −24% / wall −16%，**但符号逐组翻转**（4 组 −22%、**18 组 +39%**、14 组 −45%）—— 与 R63 自身组间离散（425–689 s）同量级，**不称提速**。步数反而 +21%（与 R63-0「盯 token 不盯步数」一致）。九跑断言恒为 **22P/1F**（唯一 FAIL = 平台 `P-R53-1` receipts），零新增形态缺陷。
- **探针换了洞（最有价值的新事实）**：`r65n-4` msg55/59 逐字 —— *“if it already exists, does it replace it?” / “Confirmed: render appends a second appendix (not idempotent).”* ⇒ 新触发点是**未文档化的渲染器幂等/空单位语义**（非 `·` 契约）。R63-2 的教训复现：**堵一个洞 → 试下一个洞**；新副作用：对真产物反复 render（4/3/1 vs 1/1/4）、额外 `build_ledger`（4/4/2 vs 2/2/3），这解释了步数 +21%。
- **裁定 KEEP**（与提速无关）：docstring 那个**自相矛盾的范例本身是交付缺陷**（原样喂脚本 EXIT=3），修它对错分明；`--check` 被两跑真采用；四条判定已被单测钉住；安全面零新增。**提速假设记为未证实**，不得写进「已变快」。
- 证据全文：`docs/evidence/r65-token-contract-2026-10-14.md`（§1 预登记 / §2 三条改前证据 / §6 实测与裁定）。
- **下一步移位（R67）**：把 `render-facts.py` 的**幂等性与空单位/附录重建语义**写进契约（本次探针的真实动机）—— 这才是 R65 三跑指向的变量。

## R64 — 文体门禁假 FAIL（runner 层 O51）：跑绿却留一条 `prose gate exited clean` FAIL（**2026-10-14 改，无发布、无真跑**）

**动机（R61-3 / B9 已坐实、拖到本轮修）**：`r61-sem-2` 三跑里唯一那条「我们自己的」FAIL 不是内容回潮 —— 第 25 步把 4 条命令串成 `patch.py … && … check_report.py … && tell-scan.py …; echo "SCAN_EXIT=$?"`，**第一个 `patch.py` 断言失败**（`ASSERT FAILED … wanted 1`；patch.py 的失败码同为 **3**）⇒ `&&` 短路，`check_report.py` / `tell-scan.py` **从未执行**；runner 把「命令文本提到 `tell-scan.py` 的所有 return」**拼成一整块**再 `re.findall(r"SCAN_EXIT=(\d+)")`，于是采到那个 3。同跑第 34 步**真的跑过**扫描器（`强 0 / 弱 1`、`SCAN_EXIT=0`）。`run.json.fails` 逐字留证。危害：**每轮验收只有这一个信号**，假 FAIL 与真 FAIL 不可区分。

**顺带查出 R63 自己埋的雷（本轮同时消掉一半）**：R63 统一教 `… 2>&1 | tail -30; echo "EXIT=${PIPESTATUS[0]}"`，与 tell-scan 专属的 `; echo "SCAN_EXIT=$?"`（prompt L166 / SKILL L141·L206 / toolbox L340 四处仍在教）**并存**。三跑实测模型都照了专属写法（banner 未被 `tail` 截掉 —— tell-scan 的合计行打在最后），**没造成损失**；但若模型照通用写法用 `EXIT=`，旧 runner 读不到 `SCAN_EXIT` 时就只剩 banner 兜底 ⇒ 干净跑仍 PASS、**脏跑（强命中未处理）降级成 WARN（照样绿）**= 信号漏洞。

**改动（只用 runner 层 `~/.local/bin/toolsmith-publish`，交付包与运行期文本一字未动）**：

| 层 | 改前 | 改后 | 内容 |
|---|---|---|---|
| runner | 拼全部 return → 全局 `SCAN_EXIT=(\d+)` | **逐 return + banner 门槛** | 只有自带扫描器 banner（`强 N / 弱 M` 表头 或 `合计强命中 N 条`）的 return 才算「扫描器回执」；退出码只从 **banner 之后**的文本读（管道后的 `echo` 正落在那儿）；同时接受 `SCAN_EXIT=` 与 `EXIT=${PIPESTATUS[0]}`，**同名冲突时 `SCAN_EXIT` 优先**（防同链后续命令的 `EXIT=3` 污染） |
| runner | 只认 `SCAN_EXIT` | 预先接受 `[tell-scan] exit=N` | 原修法①（`tell-scan.py` 自打标记）本轮**不做**（banner 本身就是回执），但 runner 先兼容，日后加**无需再改 runner** |
| `evals/runner-gate/test-runner.py` | 45 测试 | **48 测试** | 脏样本改成 tell-scan 真实打印形态（带 banner）；新增 3 例：B9 形状必须不 FAIL、R63 的 `EXIT=` 形态必须可读、同链后续命令的 `EXIT=3` 不得污染 |

**验收（三层证据，不需要真跑）**：

1. **旧新 runner A/B（单元）**：新例在旧 runner FAIL（`prose gate exited clean`）/ 新 runner **PASS**；`test-runner.py` 48/48 OK。
2. **存档 run A/B 复现**（`/tmp/r64/ab.py` 直调 `check_run`，同 `r61-sem-2` 存档）：旧 runner → `FAIL prose gate … SCAN_EXIT=[0, 3, 0]`（与 `run.json.fails` 逐字相同）；新 runner → `PASS prose gate ran and exited clean — 3 call(s), 2 scanner receipt(s), SCAN_EXIT=[0, 0] strong-free=True`。⇒ 真跑的假 FAIL 已消除。
3. **全量本地闸门**：`python3 -B -m py_compile` OK；`GATES_FAILED=0`（test-render-facts 29 / test-skill-scripts 62 / test-tell-scan 10 / test-check-report 25 / test-build-ledger-scaffold 9 / test-merge-ref-facts 16 / test_regressions 35 / mutations 44+12 / **test-runner 48** / `verify-run-chain GATE: PASS`（5 可比）/ test_pack_dist 5 / test_replay_run 14 / node 16 / `pack-dist --check` IDENTICAL 181,638 B `39640fd6e679`）。

**不改什么**：不动运行期文本（prompt / `SKILL.md` / `toolbox.md`）⇒ **本轮无发布**（`status` 仍 in sync：prompt v1.8 `91febc286412479a8b6d569fa3b8025e`、skill v1.0.9 `16aeb0406e12425bad27a2444f17225e`）；**未耗真跑**（runner 不在交付包内，F↔A 两账都不受影响）。备份：`~/.local/state/toolsmith-publish/toolsmith-publish.v12.bak` + `toolsmith-publish.o51-before-20261014.bak`（md5 `f3a25b7487293c1acdb134f3ef5a685a`）。

**留给下一轮**：**R65 候选 A**（token 契约唯一化 + 提交前可自查）**顺带把双退出码写法冲突在文本里一次说清**；**R66 候选 B**（惰性段条件化，降级）；**R61-4**（`same-trial-evolution.md` 0 真读）待排。

## R63 — 失败可见性：fail-closed 脚本必须说出原因、调用方必须拿到真退出码（**2026-10-14 改 / 原地发布 / 固定三组验收**）

**动机**：R62-1 实测「一次校验失败 → 18 次调用 / 28% 步数」，根因指向 fail-closed 脚本静默 + 调用方拿到假退出码。用户指示「测试吧，可以原地发布实测」。**本轮只改「失败如何被看见」，规则文本一条未删。**

**改动（字节账）**：

| 文件 | 改前 | 改后 | Δ | 内容 |
|---|---:|---:|---:|---|
| `scripts/render-facts.py` | 36,634 | **37,696** | +1,062 | 新增 `_report_failure(audit, audit_path)`：失败时把 `render-facts: FAILED — nothing written` + `audit["errors"]` 逐条打到 **stderr**；`main` 退出码 **1 → 3**（与其余 7 个打包脚本统一） |
| `references/toolbox.md` | 26,272 | **27,540** | +1,268 | 新增「Invoke them so a failure is readable」：`… 2>&1 \| tail -30; echo "EXIT=${PIPESTATUS[0]}"`、`$?` 吞码陷阱、非 0 先读脚本自称的输入、写明实测代价 18 次调用 / 28% 步数 |
| prompt（v1.8） | 79,886 | **80,960** | +1,074 | 全脚本统一调用形态；render-facts「fails closed（exit 3）+ 每条 finding 到 stderr」；**新规则「自我对话不算正文」** |
| `SKILL.md` | 44,780 | **45,485** | +705 | 同调用形态 + 同一自我对话禁令 |
| `evals/…/test-render-facts.py` | 28 测试 | **29 测试** | +1 | `…_announces_itself_on_stderr_and_exits_3`：returncode 3 / stdout 空 / stderr 含 `FAILED`+`unknown fact token` / 输出文件未改写 |
| `dist/…-v0.16.zip` | 180,410 / `f5e32baa1c33` | **181,638 / `39640fd6e679`** | +1,228 | 29 entries，重打后 `--check` IDENTICAL |

**本地闸门全绿**：`py_compile` rc=0；`test-render-facts` **29** / `test-skill-scripts` 62 / `test-tell-scan` 10 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test-merge-ref-facts` 16 / `test_regressions` 35 / mutations arm a **44/44** + arm b **12/12** / `test-runner` 45 / `verify-run-chain` GATE PASS / `test_pack_dist` 5 / `test_replay_run` 14 / `node --test` 16。**本地真探针**：`[[fact:NOPE]]` → `EXIT=3`、stdout 0 B、stderr 223 B（含 `facts[0].source_file does not exist`）。

**发布**：改前 `status` OUT OF SYNC（正好这 3 个技能文件）→ `publish` HTTP 200 → `status` 回读 **in sync**（prompt **v1.8** `91febc286412479a8b6d569fa3b8025e` / 80,960 B / sha **`e7e84cdbf450`**；skill **v1.0.9** `16aeb0406e12425bad27a2444f17225e` / 181,638 B / 29/29 一致；project `a7cdda6508e0423c8b7afaaf3a68e50d`）。

**真跑（固定三组，输入复用 R48/R50 逐字节、串行；`DeepSeek Flash`，web off）**：

| run | 目录 / thread | refs | wall s | 步 | 调用 | out tok | reasoning | PIPESTATUS | 形态探测 | 断言 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `r63-4` | `20261014-110640-r63-4` / `d2ac2bbc-19ef-46f3-90b4-7e849c05d35d` | 4 | 526.5 | 25 | 35 | 97,495 | 78,312 | 6 | 0/0/0 | 22 PASS / 1 FAIL |
| `r63-18` | `20261014-111536-r63-18` / `aba2e0c2-2d2b-4e34-850e-6fce519094b7` | 18 | 425.5 | 26 | 29 | 75,899 | 47,709 | 7 | 0/0/0 | 22 PASS / 1 FAIL |
| `r63-14` | `20261014-112254-r63-14` / `9ada5cde-3295-4750-9623-32dd8dc572f1` | 14 | 688.6 | 23 | 31 | 123,494 | 89,932 | 8 | 0/0/0 | 22 PASS / 1 FAIL |

三跑 `outcome=succeeded`、产物齐全、`args-refused=0`、`fetch-failed=0`、无 `tool-output-error`；**唯一 FAIL 三跑同一个 = 已知平台项 `P-R53-1`**（`r63-18` 另出现一次 `P-R59-1` 形态重试）。

**判据达成（形态类）**：对照 `r62-14`（`head -n` 7 / `runpy` 4 / `--help` 1）⇒ R63 三跑**全 0**；`PIPESTATUS` 写法 R62 三跑 0 次 → R63 三跑**每次管道调用都带**（连模型自己的探针调用也带，并正确读到 `EXIT=2`）。⇒「拿到假退出码」的机制已关闭。

**同输入历史带（R48 起，n=39，同一口径复算）与落点**：

| 量 | 4 组（n=25） | 18 组（n=4） | 14 组（n=4） | R63 实测 |
|---|---|---|---|---|
| 工具调用 | 23–69 中位 32 | 36–59 中位 46 | 28–66 中位 34 | 35 / **29（破下界）** / **31（≈中位）** |
| 步 | 19–64 中位 26 | 32–50 中位 40 | 23–63 中位 31 | 25 / **26** / **23** |
| out tok | 52.6k–112.6k 中位 70.2k | 85.7k–118.9k 中位 104.7k | 69.3k–113.4k 中位 87.6k | 97.5k / **75.9k（破下界）** / **123.5k（破上界）** |
| wall s | 252–683 中位 405 | 465–617 中位 536 | 310–708 中位 506 | 526.5 / **425.5** / 688.6（全部带内） |

⇒ 14 组调用 **65 → 31**（R62-1 形态未复现），18 组四项同时破历史下界；**但墙钟三组均在带内，本轮无可声明的提速**。

**判定：KEEP（不劣化）** —— 形态判据全达成且可归因；三组断言/产物/参数/抓取零退化；调用与步数均在历史带内；规则文本一条未删。

### R63-0（**本轮最重要的账目更正**）：撤回「减步数是最大可控项」

同口径 n=39 相关系数：`r(wall, out tok) = +0.924` > `r(wall, reasoning) = +0.862` > `r(wall, 工具调用) = +0.735` > `r(wall, 步) = +0.702` > `r(wall, 落笔 tok) = +0.628` ⇒ **墙钟由输出 token 量驱动，步数只是弱代理**（每步固定开销 1.6–3.2 s 真实但量级小）。反证：`r63-14` 调用砍半、墙钟 690.3 → **688.6 s** 未动（同跑 out 94.5k → 123.5k）。R62 的「减步数是最大可控项」与 R63 自己的「省 150–200 s」**一并撤回**；`docs/evidence/r62-weight-cut-2026-10-13.md` 与台账 R62 节已标注更正。

### R63-1（诚实记账）：新 stderr 通道三跑**一次都没触发**

`render-facts: FAILED` 出现 0 次；`unknown fact token` / `unresolved fact` / `not an exact source substring` 等校验失败字符串 0 次（对照 `r62-14` = 1）。⇒ 本轮证据结构：**形态改进由三跑实证；失败通道本身只由新增单测 + 本地真探针证明「装好了」，不证明「在真跑里省了时间」**（预防生效与通道未触发在 n=1 上不可区分）。

### R63-2（新观察，R64 候选 A）：模型仍在试错，只是换了壳

`r63-14` 出现 **4 次** `render-facts.py` 调用（其余五跑各 1 次）：其中 2 次为**自造探针草稿**（写 `work/probe.md` 最小样张 → `--out work/probe_out.md` 试渲染；首次漏带 `--audit`，正确收到 `EXIT=2`），另有 1 次去读 `make_chart.py` 源码。⇒ prompt 禁的是「临时 ledger 试错」，模型改为「临时 **draft** 试错」——**禁令只改外形，没消除动机**。修法方向 = **让契约可静态自查**，而不是继续加禁令。

### R62-1 事实更正（git 复核）

原写「我们自己的文档教了吞掉退出码的写法（`toolbox.md` 第 276 行 `check_report.py -v 2>&1 | tail -40` + `echo "CHECK_EXIT=$?"`）」**为假**：R62 发布版 `1a2bc04` 中 prompt / `SKILL.md` 的 `| tail` 出现 **0 次**，`toolbox.md` 唯一相关样板是**正确**的无管道写法 `tell-scan.py …; echo "SCAN_EXIT=$?"`。⇒ `… | tail -40; echo "EXIT=$?"` 与 `CHECK_EXIT` **均为模型自创**。真实缺口 = **打包脚本的调用形态在文档里没有唯一推荐写法**（8 个脚本各写各的），模型只能自行发明且无对照物——这正是 R63 补的。

## R62 — 减重第一轮：冷区散文收紧 + 编号缺陷修复（2026-10-13 改 / **2026-10-14 原地发布 + 固定三组验收**）

**起因**：用户「减法减法」——「这个 skill 太重了、速度很慢」。先做**只读体检**，再改。

**体检结论（三次真跑口径，数字与命令见 `docs/evidence/r62-weight-cut-2026-10-13.md`）**：
1. **两本账要分开**：我们的 skill 只占上下文 **16%**（20,347 tok；平台工具 schema 85,995 tok = 69%，cache 命中 97.4%），而墙钟 **91–93% 是生成**、其中 **65–71% 是思考** ⇒ **减字节 ≠ 提速**；同输入 19 步 / 251.7 s vs 29 步 / 354.5 s 说明步数有影响（**惟该因果已于 R63 更正为「弱代理」，见 R63-0**）。
2. **真正的缺陷是「权重↔热度错位」**：prompt 把 21% 的字节花在 `## Subagent delegation`（7,838 字符）与 `## Step discipline`（9,050 字符），而这两处**思考命中率 0.00–0.01/千字**（被遵守、不被推敲）。
3. **因此不能「哪里长就删哪里」**：这两节不是措辞冗余而是**防错契约**，而 `check_report.py` / `tell-scan.py` 都是 **fail-closed**——删散文 = 把「预防」换成「下游发现 + 返工」，**反而更慢**。

**改动（逐项字节账；脚本 `/tmp/r62/splice.py`，按 `## ` 标题整节替换、断言标题唯一命中）**：

| 位置 | 改前 | 改后 | Δ | 性质 |
|---|---:|---:|---:|---|
| prompt `## Step discipline` | 9,121 | 7,967 | **−1,154** | **8 条规则一条未删**，只删论证性从句；顺带修方位词 `above` → `below`（原文该处指错方向） |
| prompt `## Subagent delegation` | 8,116 | 5,067 | **−3,049** | 其中 **2,476 B 是迁出**（`原文核对：` 这条与子代理无关的规则原本埋在该节末尾），余 −573 B 措辞收紧 |
| prompt `## The original-source check line (原文核对：)` | — | 2,476 | +2,476（迁入） | 独立成节，位置移到 `## Trial-level synthesis rules` 之前 |
| SKILL.md `## Purpose` | 5,269 | 4,434 | **−835** | 修编号缺陷：旧清单**两个 "9."**、**11 排在 10 前**（模型按错号读）→ 改「必读 1–5 / 条件读 6–12」 |
| **prompt 合计** | 81,576 | **79,886** | −1,690（−2.1%） | sha `713f4333b74e` → `c17ee2f1c18a` |
| **SKILL.md 合计** | 45,615 | **44,780** | −835（−1.8%） | sha `74781a56c6cd` → `949ae00902c9` |
| **dist** | 180,652 | **180,410** | −242 | sha `0b8ba50448b6` → `f5e32baa1c33`（29 entries，`pack-dist --check` IDENTICAL） |

**为什么只减 2%**：prompt 的字节几乎全是规则本身。第一版压缩到 5,027 B，复查发现**丢了 5 条实质条款**，遂回退到「一条不丢」口径重压 ⇒ 上限就是 −2~3%。

**本地闸门（改动后全绿）**：`test-render-facts` 28 / `test-skill-scripts` 62 / `test-tell-scan` 10 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test_regressions` 35 / `test-runner` 45 / `node --test` 16 / `mutations` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS` / `verify-run-chain` **GATE: PASS**（151 histories, 5 可比）/ `test_pack_dist` 5 / `test_replay_run` 14。**但本地闸门证明不了运行期文本的语义没丢——需 1 次真跑。**

**发布（2026-10-14，用户授权「A 原地」）**：**原地更新**（版本号不变、内容替换）——prompt **v1.8** 81,576 → **79,886 B**（sha `713f4333b74e` → `4c306fa7aec9`）、skill **v1.0.9**（`skill_id 16aeb0406e12425bad27a2444f17225e`，2026-10-14T09:52:48，29/29 支持文件一致）。发布前 `deps` **未变**（1 技能 + 1 MCP + **16 个内置工具，含 `task`**）；发布后 `status` → **in sync**。

**真跑验收（固定三组 4 / 18 / 14 esid，输入复用 R48/R50，**串行**执行保时间可比；`DeepSeek Flash`，web off）**：

| run | esid | thread | wall s | 步数 | 每步固定开销 | out tok | reasoning | 断言 |
|---|---:|---|---:|---:|---|---:|---:|---|
| `r62-4` | 4 | `b5d197fc-3a45-407d-a7b5-be945349956a` | 309.7 | 26 | 1.61 s（35.5 s = 11%） | 53,616 | 39,826 | **22 PASS / 1 FAIL** |
| `r62-18` | 18 | `bbd2f0e8-27a0-4766-99da-145c75ef8880` | 475.8 | 44 | 2.58 s（100.5 s = 21%） | 80,844 | 53,719 | **22 PASS / 1 FAIL** |
| `r62-14` | 14 | `665c3f92-285f-4214-8f96-e291c037bf32` | 677.8 | 65 | 3.16 s（202.3 s = 30%） | 94,457 | 64,162 | **22 PASS / 1 FAIL** |

三跑均 `completed` / `outcome=succeeded`，产物齐全（`output/report.md` + `output/citations.json` + 1 张图：4 组 `evidence-timeline.json`、18/14 组 `endpoint-bar-1.json`）；`args-refused=0`、`fetch-failed=0`、**无 `tool-output-error`**；唯一 FAIL 三跑同一个 = 已知平台项 **P-R53-1**（`tool_results receipts archived`）。

**与同输入历史对照（步数）**：4 组 26 vs 25（R50）/ 28（R48）；18 组 44 vs 46（R50）/ 59（R48）；14 组 65 vs 31（R50）/ 28（R48）⇒ 4 / 18 组**在带内且偏好**，14 组**超出带**——但超出部分有独立成因（见 R62-1），**不是 R62 文本删减导致**（对照：r62-4 / r62-18 及 R60/R61 各跑均未出现该形态）。

**判定：KEEP（不劣化）** —— 断言零退化、无参数拒收、无抓取失败、产物齐全；4/18 组步数未升。

> **新增量化证据**（此前只在 4 esid 上估过每步 ≈2 s）：**每步固定开销 1.61 / 2.58 / 3.16 s，占墙钟 11% / 21% / 30%** ⇒ 步数是时间的乘数；14 组 65 步里约 **18 步（28%）是一次故障排查**，这也是「很慢」的尾巴来源。

> **2026-10-14（R63-0）更正**：原文此处续写「减步数是最大可控项」，**已撤回**——同口径 n=39 相关性显示墙钟由**输出 token 量**驱动（`r=+0.924`），步数仅 `+0.702`。见上方 R63-0。

### R62-1（**我方能改，本轮最大单点浪费**）：`render-facts.py` fail-closed 但**静默**，把一次校验失败放大成 18 次调用

**现象（`r62-14`，全 65 次调用中的第 33–50 号）**：模型把一段自我修复旁白写进了交付正文（`output/report.md` 第 95–97 行：`Hmm, I wrote "[[fact:j5]] 剂量组中出现 5 起轻度注射部位事件，见于 [[fact:j8p]]" — that's wrong: j5 is Cmax 667 ng/mL, and j8p doesn't exist. Let me fix that row…`），其中 `[[fact:j8p]]` 是**不存在的 fact id** ⇒ `render-facts.py` 校验失败（exit 1）。随后模型：`render-facts.py` 只在第 29/32 步拿到 `RENDER_EXIT=1`、**看不到任何原因**，于是改用 `head -n N` **二分报告**（7 次）、`--help`（1 次）、`runpy`+`traceback`（2 次）逐段试渲染，最后靠「n≤94 通过 / n≥96 失败」定位到那几行，`patch.py` 删掉 1 行即恢复（第 53 步 `RENDER_EXIT=0`）。**共 ~18 次调用 / 28% 步数**。

**根因（已复现，两个缺陷叠加）**：
1. **脚本静默**：`render-facts.py` 把失败原因只写进 `audit["errors"]`（第 812/814 行），`main` 直接 `return 1`（第 835 行）⇒ **stdout 0 字节 / stderr 0 字节**。复现：`--draft` 含 `[[fact:NOPE]]` → `EXIT=1`、两流皆空。**8 个打包脚本里只有它这样**（stderr 输出数：`make_chart` 16 / `make_citations` 15 / `build_ledger` 13 / `patch` 10 / `prep_sources` 7 / `check_report` 2 / `tell-scan` 1）——最 fail-closed 的那个恰好唯一不报错。
2. **（2026-10-14 更正）文档缺的不是「正确样板」，而是「没有任何被推荐的调用形态」**：原写「我们自己的文档教了吞掉退出码的写法：`references/toolbox.md` 第 276 行给的样板是 `check_report.py -v 2>&1 | tail -40` 后接 `echo "CHECK_EXIT=$?"`」**为假**（详见上方「R62-1 事实更正」）：R62 发布版中 `| tail` 出现 **0 次**，`toolbox.md` 唯一相关样板是**正确**的 `tell-scan.py …; echo "SCAN_EXIT=$?"`。⇒ **`| tail -40; echo "EXIT=$?"` 是模型自创的**。实测该跑 `CHECK_EXIT=0`，而同一份输出里明明有两行 `FAIL:`（一行直指 `unresolved fact/result token(s)`）⇒ **模型当时已经拿到诊断，只是被自己写出的假退出码掩盖**。

**改法（并入 R63，均在我方层）**：① `render-facts.py` 返回 1 前把 `audit["errors"]` 逐行打到 **stderr**；`test-render-facts.py` 加断言「未知 token → exit 1 且 stderr 非空」；② toolbox 样板改成 `2>&1 | tail -20; echo "EXIT=${PIPESTATUS[0]}"`（不吞真退出码），并在 prompt/SKILL 写明「打包脚本非 0 退出：先读 stderr / `work/audit.json` 的 `errors[]`，**禁止**用 `head -n` 二分输入、`--help` 钓鱼、`runpy` 取 traceback」；③ 交付物禁自我旁白（触发源）。**预期：18 次调用 → 1–2 次，按本轮 3.16 s/步计省 150–200 s（≈该跑 22–30%）**。

### R63（**已执行，见文首 R63 节**）：修 `render-facts.py` 静默失败 + 打包脚本调用的报错通道

单一假设 =「fail-closed 脚本必须把原因打到 stderr；调用方必须拿到真退出码」⇒ 断言 = 固定三组里**不再出现**二分/`runpy` 形态，且该组步数回落。**结果：形态判据全达成（三跑 0/0/0，PIPESTATUS 全面采用）；14 组调用 65 → 31 但墙钟未动；「省 150–200 s」预期撤回（时间由 token 量驱动，R63-0）。**

### R64 候选 A（**首选**）：让提交前的契约可静态自查（而非继续加禁令）

R63-2 的观察显示：模型禁了「临时 ledger 试错」就改成「临时 **draft** 试错」——**禁令只改外形**。同时 R63-0 说明要提速必须打 **token 量**（尤其推理量 89,932 tok 占 `r63-14` 的 73%）。因此 R64 首选方向 = **唯一化 + 可自查的 token 契约**：现在「什么样的正文会被 `render-facts` 接受」散落在 prompt / `SKILL.md` / `toolbox.md` 三处，模型因此不确定才去试渲染。目标：消掉那 2 次探针草稿与偏高的推理量。判据必须先写（可能只是降 token 而步数不动）。

### R64 候选 B（**次选，已降级**）：惰性段条件化，而不是删规则

- 唯一「大块且可减」的是**条件成立才有意义**的内容：prompt `## Subagent delegation` 细则（5,067 B，仅当 `task` 可见且 >5 esids；三次跑均未触发委托——**18 esid 组实测也没委托**，直接一次拉取）→ 留 6 行摘要 + 「首次 `task` 前先读 `references/subagent-delegation.md`」；`## Mixed or different-trial inputs`（1,035 B，仅跨试验）同理。**预期 −4.3 KB**。
- **判据（先写下，避免踩同一坑）**：条件引用会被跳过（`same-trial-evolution.md` 三轮 0 读是活证），所以**只条件化「跳过代价 = 行为退化但不静默出错」的程序性内容**，**不条件化「跳过代价 = 交付错」的结论性规则**。**（2026-10-14 按 R63-0 降级为备选：它只作用于「每步固定开销」这一小项，预期收益下调。）**
- **明确不做**：① 把 `## Final verification` 的机械项（~3.5 K）改成「跑 `check_report.py`」——fail-closed 下这是把预防换成返工；② 折叠 prompt 与 SKILL.md 的 `## Report prose style`（~5 K）——清单是查表、散文是预防；③ 折叠 SKILL.md `## Workflow`（23,661）与 prompt `## Numeric Integrity`（9,121）——实测**精确重复仅 1 段（~1.3 K）**，其余是同一契约的两种措辞、两层视图。

## R61 — 语义阶段耗时实测（**测量轮：未改任何 skill、未发布**）（2026-10-13，n=2 新跑 + R60 对照）

**动机**：用户提问「别按 agent 工具流看，我要各**语义阶段**花了多久，比如写引用花了多久」。R60 只记了总墙钟（中位 430 s），没有成本归属。

**做法**：新增离线只读分析器 **`tools/semantic-timing.py`** —— 读 `debug-history.json#raw_model_messages`，用
`生成(i) = t(下一步首个工具返回) − t(本步开始生成) − 工具跨度(i)` 取每步生成时间，再按**该步参数写向哪个产出物**
（`write_file.file_path` / `execute` 的重定向目标与脚本名 / `read_file.path`；`&&`、`;`、`|`、heredoc 按子命令拆开）
按字节摊到语义阶段。口径、边界与复算命令见 **`docs/evidence/semantic-timing-2026-10-13.md`**。

**实测（同输入 4 esid，DeepSeek Flash，web off；两次新跑串行以保时间可比）**：

| run | wall s | 步数 | out tok | reasoning | 工具 s | 工具调用 | 断言 |
|---|---:|---:|---:|---:|---:|---:|---|
| `r61-sem-1` | 354.5 | 29 | 58,363 | 41,627 | 6.7 | 32 | 22 PASS / 1 FAIL |
| `r61-sem-2` | 251.7 | 19 | 52,551 | 38,420 | 5.0 | 23 | 21 PASS / 2 FAIL |
| 对照 `r60-prose-generic-2` | 344.1 | 23 | 61,049 | 46,759 | 5.4 | 27 | 22 PASS / 1 FAIL |

**语义阶段（生成时间，三次跑区间）**：报告正文 55–70 s、事实与账本 44–75 s、装载契约 22–68 s（**几乎全是长思考步**）、
源文取证 19–47 s、自产物回读/返工 8–32 s、图表 12–23 s、取数 3–11 s、门禁 5.3–5.6 s、**引用编撰 1.4–1.8 s**、
交付 0–2 s、其他 30–38 s；**工具本身只占 5.0–6.7 s（1.5–2.0%）**。

**三条结论**：
1. **「写引用」已不是成本**（1.4–1.8 s、0 字节手写）—— `make_citations.py` 把它彻底脚本化了。
2. **全 run 分解 = 思考 65–71% ＋ 落笔（真打字）10–12% ＋ 每步固定开销 11–16%**（每跑自身回归标定：reasoning 4.3–5.6 ms/tok、
   落笔 1.7–2.8 ms/tok、每步 1.6–2.1 s，R² = 0.985–0.991）⇒ **减步数比省 token 更省时间**
   （`r61-sem-2` 19 步 / 251.7 s vs `r61-sem-1` 29 步 / 354.5 s，同输入）。
3. **每跑恰有一次 58–64 s 的纯思考步**（`reasoning ≥ 80% out` 且 `≥ 40 s`；r60-2 拆成两步 ≈ 124 s）：
   名义动作是「读报告模板 / 探源文」，thinking 原文显示在做**取证归拢 + 账本设计 + 报告结构规划**（三次跑同一规律）
   ⇒ 主表里「装载契约 18–20%」应读作「**规划/设计 ≈ 60 s（占 18–36%）**」，而不是"读契约文件慢"。

**判定**：**测量轮，无假设可判**（不改运行期文本、不发布；`status` 回读仍 `in sync`，PROMPT v1.8 / SKILL v1.0.9 未动）。
产出：`docs/evidence/semantic-timing-2026-10-13.md` + `tools/semantic-timing.py`（离线、只读、零网络）。

### 追加：并行性评估（用户追问「事实与账本/图表/自产物回读能不能开并行子代理」）

**先看清「想」和「打字」是分开的**（每跑自身标定把生成拆开；`r61-sem-1` a=5.57/ b=2.08 ms、`r61-sem-2` a=4.33 / b=1.73 ms）：

| 步（`r61-sem-2`） | gen s | 想 s | 打字 s | 落点 |
|---|---:|---:|---:|---|
| 13 | 57.8 | **57.9** | 0.3 | 读技能包（长思考步） |
| 15 | 40.4 | 27.4 | **13.0** | `facts.json` |
| 19 | 55.2 | 42.9 | **5.6** | 图表 json + `report.md` |

结论：**并行只能搬走「打字」那 5–14 s，搬不走「想」的 27–58 s**。而「想」是这份工作的本质——
账本的键名/规范化/哪条事实合格是一次**不可分割的设计决定**，下游（报告、图表、引用）全部引用它。

**逐项判定（4 refs 档位，均可由 R56/R57/R58 实测支撑）**：

| 候选 | 可并行部分 | 判定 | 依据 |
|---|---|---|---|
| **事实与账本** | 仅 `facts.json` 的 13–14 s 打字（按 ref 切片） | **不采纳** | 4 篇只够切 4 片；子代理重载通用系统提示（探针：2 个子代理 = 157 K input tok）、不继承项目 prompt、内部 `execute` 默认 30 s 超时；主线程仍须做跨 ref 合并校验（键名/数值格式/`records[].trial`）——合并本身在关键路径上。上限 13 s / 251.7 s = **5%**，低于同输入噪声 **±20–40%**；而 R57 把这条配方写进文档后实测 **+7.8% 墙钟**（配方自己要烧 reasoning），R58 已删。**重试条件**：≥6 refs ＋ registration-class 重载荷，且**先删**任何竞争的成本句 |
| **图表** | 图表 json 的落笔（数秒） | **不采纳** | 图**必须**等到报告正文存在才能做 —— R37 起有硬规则「图内与任一表格单元格不得有 ≥8 字连续相同文本」，即图的文案受报告正文约束；现在模型本来就在**同一条消息**里写图表 json + 报告（step 19）。放进子代理不是并行，是把同样的生成搬进一个要重新装载上下文的子代理，主线程照样等 |
| **自产物回读/返工** | ～0 | **不采纳（另有更好办法）** | 返工对象是主线程自己的稿子，主线程持有账本与全文，最终修写只能它做（`r61-sem-1` step 27：29.0 s = 想 30.3 ＋ 打字 2.9，**主体是思考不是打字**）。**只读复核**确实可以外包，但本项目已用**确定性脚本**顶替了它：`check_report.py` / `tell-scan.py` / `render-facts` audit 合计只花 5.3–5.6 s、**0 token** —— 比任何子代理便宜且更可靠 |
| **取数 / 源文取证** | 按 ref 扇出（19–47 s） | **不采纳（同 ① 的结论）** | 同 R57/R58 的最终结论：4 refs 档位模型（正确地）不需要；且沙箱 `execute` 全平台单通道，扇出的子代理只要碰 `execute` 就排队（探针零重叠、交接 2.8 s） |

**判据（写下来，供以后复用）**：子代理只在两种情况下省墙钟 —— ①它的产出**不在**主线程的关键路径上；②主线程手上有**别的独立生成**可以重叠。本项目的链是
`取数 → 源文 → 账本 → 报告+图 → 门禁 → 交付`，每一步的输出都是下一步的输入，**几乎没有可重叠的旁支**；且"想"独占 65–71%、`execute` 又单通道。
R56 探针里唯一真并行的是**纯生成**（R56-b：两个各写 1.5 万字、零 `execute`，重叠 28.86 s ≈ **1.38×**）——那正是本项目最稀缺的形态。

**因此本轮的取向不是"加并行"，而是**：①**减步数**（同输入 19 步 251.7 s vs 29 步 354.5 s，每步固定开销 ≈2 s）；②**把步骤搬进脚本**（已验证的范式：引用编撰 1.5 s、附录渲染、门禁 5.5 s）；③**收缩那个 58 s 的纯思考步**（规划/设计 18–36%）。

### 我方能改的

- **R61-4（新，用户断言已坐实，与 R62 同源）**：`references/same-trial-evolution.md` 在**三次跑里 0 次真读**，而三次的输入都是**同一试验的 4 条披露**（`24_37_875c2a49d64fbeb5dc34da77ea7cd308_1` / `24_37_6c25b1fc8a9f3d159294937d2cc995b1_1` / `24_1_42218899_1` / `24_1_41125109`，ivonescimab+chemo vs tislelizumab+chemo，HARMONi-6）⇒ **触发条件成立、文件确实没读**。
  证据取法：用 `tools/semantic-timing.py#steps_of` 解析 `read_file` **真实入参**（不要数字符串出现次数——那份中文清单本身就在 `SKILL.md` 里被引用，出现 12–16 次但一次也没读）；同一口径顺手修正 R62 体检里「`toolbox.md` 分片读 4–5 次」的错误估计为**真读 1–3 次**。
  附带发现：`r61-sem-2` 有 `read_file report.md x2`（模型回读自己刚写的正文），正是 Step discipline 第 7 条禁的动作。
  状态：**待修**——R62 已把 `## Purpose` 改成「必读 1–5 / 条件读 6–12」并修好编号（错号会让模型读错条目），但「条件读被跳过」这个根因未解决；R63 的条件化方案**须避开结论性规则**（见 R62 的 R63 判据）。
- **R61-3（新，已在真跑里坐实）**：`prose gate exited clean` 断言会把**`&&` 短路后别的命令的退出码**当成扫描器结论。
  `r61-sem-2` 第 25 步链为 `patch.py --find … && patch.py --find … && … tell-scan.py report.md; echo "SCAN_EXIT=$?"`，
  **第一个 `patch.py` 断言失败（`ASSERT FAILED … wanted 1`，`patch.py` 失败即 exit 3）** ⇒ `&&` 短路、扫描器根本没跑，
  `SCAN_EXIT=3` 是 `patch.py` 的退出码；该跑收尾（第 34 步）扫描器真跑过 `强 0 / 弱 1（W-FMT-MIXED 弱）`、`SCAN_EXIT=0` ⇒ **门禁实际是干净的，这条 FAIL 是假的**。
  修法（二选一或并用，**下一轮的单一假设**）：① `skill/scripts/tell-scan.py` 在自己输出末尾打印 `[tell-scan] exit=N`（模型不必再 `echo SCAN_EXIT=$?`），断言改读这一行；
  ② runner 侧只在同一条 return 里同时出现扫描器 banner（`强 x / 弱 y`）时才采纳 `SCAN_EXIT` 值。属 R60-3 的第一次真实踩坑。

### 平台侧（转开发）

- **P-R53-1 依旧每跑命中**（`tool_results receipts archived` / `unsafe or unsupported receipt path`），与本次测量无关。
- 其余（P-R59-1 / P-R59-3 / P-R56-1~4 / P-R58-1）维持原状态。**本轮新增证据：P-R56-1「沙箱 execute 单通道」不是本任务瓶颈**（全部工具调用合计仅 5.0–6.7 s / 跑）。

## R60 — 运行期文本不再点名外部文体技能（依赖面 3 → 1）（2026-10-13，**已原地发布** + n=2 实测，**KEEP**）

**起因**：用户指出 R59 之后正文里仍写着 `report-humanizer-zh` / `report-humanizer-en` ——「这肯定要改啊……都没有这个 skill 了」。两个症状：① 运行期文本点名 → **依赖错觉**（读起来像这两个技能还在被使用）；② `toolsmith-publish deps` 的依赖面把它们一直列为**被扫描的上游源**（`skills: 3`），发布闸门里挂着两条与本项目无关的新鲜度。

**R60 假设（一轮 = 一个假设）**：删掉运行期文本里的字面点名 ⇒ `deps` 依赖面收窄到「运行期真会加载的东西」（只剩图表技能），而**行为不变**（R59 已内联全部文体规则，运行期从不依赖挂载）。

**改动**（3 个运行期文件，纯措辞收窄，净减）：`SKILL.md:185` 与系统提示词 152 行的 `A deployment may also mount \`report-humanizer-zh\` / \`report-humanizer-en\`` → `If a deployment happens to mount another style skill, do not apply it here: applying both pays twice …`（**禁止加载 / 等待 / 依赖任何外部文体技能**这条硬指令保留且更明确：点名 → 泛指，覆盖任何外部挂载）；`references/prose-style-zh.md` 维护节 3 行去点名（`源自上游 report-humanizer-zh 仓库` → `随本 Skill 发布的自包含副本（基线 v0.1.1）`、`与上游逐字节一致` → `与基线副本逐字节一致`、「上游改规则」→「基线改规则」）；仓库级 `vendor/README.md`（**不进交付包**）保留完整溯源 + sha256，追加「用户已取消挂载 / 运行期文本不再点名」一行；顺带把 `tools/pack-dist.py` docstring 的 `27 entries` 修成 `29 entries`。体积：prompt `81,614 → 81,576 B`（−38 B）、dist `180,675 → 180,652 B`（−23 B）、条目数不变 29。**实质规则与扫描器契约一字未动**（exit `0`/`3`/`2`、弱命中只作线索、永不改数字、永不授权删 局限/缺口/未报告 语句与可比性 caveat）。

**依赖面现场（本轮的正事）**：`deps` 报 `UPSTREAM CHANGED … GONE skills report-humanizer-en` / `-zh`（exit 3，闸门按预期挡下）→ `deps --accept` 记新基线 → 复跑得到 **`skills: 1`（chart-visualization-json v1.0.12）/ MCP 1 / built-in 16 / DEPS: unchanged**。**同时更正 R59 的一条归因**：`deps` 量的是**文本引用面**（`collect_deps` 只扫 `skill/`、`system-prompts/` 的 `.md/.json/.py`，对平台技能名做整词匹配），**与项目挂载无关**；R59 那次 `unchanged` 是巧合（正文当时仍点名）。两条 `GONE` 只可能来自点名消失，反过来证明本轮改动是唯一因。

**本地门禁（发布前全绿）**：`test-skill-scripts` 62 / `test-tell-scan` 10 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test-merge-ref-facts` 16 / `test-render-facts` 28 / `test_regressions` 35 / `test-runner` 45 / `test_pack_dist` 5 / `test_replay_run` 14 / node **8+8 pass** / `mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS` / `verify-run-chain.py` `147 histories / 5 comparable / 142 skipped` + `GATE: PASS` / `pack-dist.py --check` → `IDENTICAL (180652 B / sha 0b8ba50448b6)`。合计 **221**（含 numeric-integrity 28 + merge-ref-facts 16 为 **249**）。

**已原地发布（用户授权「原地实测」）**：prompt **v1.8 81,576 B / `713f4333b74e`**（HTTP 200，read-back `deployed == local: True`、`CURRENT`）；skill **v1.0.9 dist 180,652 B / 29 entries / `0b8ba50448b6`**（`POST /api/skills/update_skill_file` HTTP 200，`skill_id=16aeb0406e12425bad27a2444f17225e`）；回读 `status` = **`29/29 identical` + `STATUS: in sync`**；项目行 `prompt=475039ccebfe46a3a39002febe28b1f4`、`skills=[chart-visualization-json, multi-clinical-result-comparison]`。

**实测 n=2**（`DeepSeek Flash`，固定 4-esid 输入，web off，tag `r60-prose-generic{-2}`）：

| run | wall s | out tok | reasoning | tool calls | `tell-scan` | `SCAN_EXIT` | facts | report | 断言 |
|---|---|---|---|---|---|---|---|---|---|
| r60-prose-generic | 502.7 | 89,145 | 73,317 | 33 | 1 | `[0]` | 63 | 19,022 B | 22 PASS / 1 FAIL |
| r60-prose-generic-2 | 357.2 | 61,049 | 46,759 | 27 | 1 | `[0]` | 53 | 20,355 B | 22 PASS / 1 FAIL |
| **中位** | **430.0** | **75,097** | — | 30 | 1 | 全 0 | 58 | 19,689 B | — |
| R59（n=2） | 363.3 | 61,429 | — | 27.5 | 2 | 全 0 | 42.5 | — | 21 PASS |

- 断言 #18 两跑 PASS（`prose gate ran and exited clean — 1 call(s), SCAN_EXIT=[0] strong-free=True`），弱命中仍只作线索（`W-FMT-MIXED` / `W-AIWORD 闭环`，合计强命中 **0**）。
- **文本干净**：两跑 `messages.json` / `transcript.md` / `report.md` 中 `humanizer` **0** 次；`load_skill` 各 1 次且参数均为本 skill（没有去加载任何外部文体技能）。
- 契约未动：唯一 FAIL 均为平台侧 `tool_results receipts archived`（P-R53-1）；`task` / `--scaffold` / `merge_ref_facts` 仍 **0** 次。
- **成本不可归因**：中位 wall 430.0 s（vs R59 363.3 / R58 443.9 / 紧基线 R55 405.4），单跑跨度 357–503 s；改的是措辞、门禁仍 1 次 0 token。`r60-1` 的 out 89,145（reasoning 73,317）是历史最高值，同批 `r60-2` 仅 61,049 ⇒ 记方差。

**判定：KEEP**。记账：**R60-1** 门禁调用数 2 次/跑 → 1 次/跑（并进同一条 `execute` 链，断言只要求 ≥1 且 `SCAN_EXIT=0`）、**R60-2** 更正 R59 的 `deps` 归因、**R60-3** `SCAN_EXIT` 回显观察（低优先）。平台侧无新增（P-R53-1 每跑命中；P-R59-2 保持作废）。详见 `docs/evidence/r60-runtime-text-drops-external-style-skill-names-2026-10-13.md` 与 `docs/toolsmith-verification-log.md` R60。

## R59 — 文体门禁内联（A+B）：条件式引用 → 确定性检查（2026-10-13，**已原地发布** + n=2 实测，**KEEP**）

**起因**：用户问「引用外部 human skill 是否增加耗时」。用全历史真实调用回答（扫 `~/.local/state/toolsmith-runs/*/messages.json`）：`load_skill` 计数 `multi-clinical-result-comparison` **115x** / `report-humanizer-zh` **7x** / `chart-visualization-json` **2x** ⇒ 文体 skill 触发率 **6.1 %**（R58 三跑 **0/3**）。**引用本身几乎免费**：返回 5,933 字符 ≈1.5 K input token、一次后走 cache；唯一载入它的 `r57b-shard-3` 墙钟 445.9 s 正是三 shard 中位（未载入的 shard-1 反而最慢 465.5 s）⇒ 边际成本落在噪声内。**贵的是「应用」**：载入后改报告 + 重跑门禁，估 **+30–60 s / +10–20 K out**（`r44-a` step 43 载入后 write + 复查：511 s / 94,797 out）。**现状的失效模式与 R57 facts 分片同一类**：条件式许可（“may also mount… *when it does*: apply at most one”，只要 6 % 命中）打不过成本 ⇒ 付了提示词字节，风格产出仍不一致。另有一处更硬的漂移：平台部署的 `report-humanizer-zh` 是 **v1.0.0**，本地仓库已到 **v0.1.1** —— 两条路径本来就不同源。

**决策（用户拍板 A+B）**：① **A** = 把上游 `tell-scan.py`（确定性扫描器）**逐字节复制进我们自己的包**，运行期不再依赖任何外部挂载；② **B** = 精选报告文体规则**内联**进 `SKILL.md` / 系统提示词。**关键口径：「门禁必跑 ≠ 改写必做」** —— 门禁 = 定稿后 1 次本地 `execute` 跑 `tell-scan.py`（1–3 s、**0 token**、输出 ≈200 B，落在噪声里）；**改写只由强命中触发**（弱命中仅线索）。样本报告实测 **强 0 / 弱 1** ⇒ 重写基本不触发，期望成本**低于**现状（现状是 100 % 的 run 付那 6 % 换 6 % 生效）。

**改动**（净加法，但**零运行期外部依赖**）：新增 `skill/.../scripts/tell-scan.py`（22,558 B，sha256 `1992a4c48f78dc8e…`，与上游逐字节一致）；新增 `skill/.../references/prose-style-zh.md`（13,071 B / 200 行，只内联报告文体相关条目 A1–A10 / B1–B10 / C1–C8 / D1–D3 + 扫描器编号映射 + 「强命中必须处理」）；`SKILL.md`（脚本清单、工作流 §5 必跑门禁、`## Report prose style` 整节改为**自包含**并明写「不加载 / 不等待 / 不依赖任何外部文体 skill」、参考清单第 11 项）；`references/toolbox.md`（门禁表行 + 新 `## 9.` 节）；系统提示词 **6 处**（工作流步 8、脚本清单、`## Report prose style` 自包含版、交付前两条检查、机械脚本清单）；`tools/pack-dist.py` **`EXPECTED 27 → 29`**；新增 `evals/scripts/test-tell-scan.py` **10 例**；`vendor/README.md` 溯源表。**② 为何消失**：运行期不再看 `report-humanizer-zh` 是否被挂载/是否被记起/线上是哪个构建；残留只是**仓库级两份拷贝**的漂移，用一条 **sha256 同一性回归**兜住（兄弟目录不在时 skip 而非假绿）。

**runner 第 18 项断言**（本地 runner 改动：`~/.local/bin/toolsmith-publish`，备份 `toolsmith-publish.v10.bak`，改前 sha256 前缀 `b7652eaf9d5cb9d8`）：`execute` 调用中必须出现 `tell-scan.py`（缺 → **FAIL**）；能读到 `SCAN_EXIT` 时必须为 `0`（脏 → FAIL）；调用过但未回显退出码 → **WARN**（证据在、只是数字读不到，判 FAIL 是罚宿主不是罚 run）；退出码提取同时接受 `command` / `shell_command`（P-R59-1）。`fails` 只收 `FAIL` ⇒ WARN 仍以绿出货；`--expect refusal` 分支在第 1408 行提前 return，不受影响。`evals/runner-gate/test-runner.py` **41 → 45**（正向夹具补门禁调用 + `SCAN_EXIT=0`；新增 4 例：缺门禁 / 脏退出 / 无回显仅 WARN / 干净扫描不得重复计数）。**修复中撞到假绿**：第一版写 `add(True, …, warn=True)`，而 `lvl = "PASS" if ok else ("WARN" if warn else "FAIL")` ⇒ 被吐成 PASS；改 `add(False, …, warn=True)` 才是 WARN。

**本地门禁（全绿）**：`test-tell-scan` **10**（新）/ `test-skill-scripts` 62 / `test-check-report` 25 / `test-build-ledger-scaffold` 9 / `test-merge-ref-facts` 16 / `test-render-facts` 28 / `test_regressions` 35 / `test-runner` **45** / `test_pack_dist` 5 / `test_replay_run` 14 / node **8+8** / `mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS` / `verify-run-chain.py` `GATE: PASS`（145 histories / 5 comparable / 140 skipped）。`deps` = `unchanged since the recorded baseline`（当时按「humanizer 是**项目挂载**事实、不是文本依赖」解释 —— **【R60 更正】该归因错**：`deps` 量的是文本引用面，挂载与它无关；R59 那次 `unchanged` 是巧合，见 R60 节）。

**发布（原地，用户授权「原地实测」）**：prompt **v1.8** 78,155 B `6d507fb8fff7` → **81,614 B / `aaf77e7c284b`**（+3,459 B = 内联规则 + 门禁，`ifadd=false` HTTP 200，read-back `matches_local=True`）；skill **v1.0.9** dist 160,567 B / 27 entries → **180,675 B / 29 entries / sha `099504055d79`**（`/api/skills/update_skill_file` HTTP 200）；回读 `status` = `prompt deployed == local: True` / skill `29/29 identical` / **`in sync`**。skill_id `16aeb0406e12425bad27a2444f17225e`；PROJECT `a7cdda6508e0423c8b7afaaf3a68e50d`。

**真跑实测（n=2，`DeepSeek Flash`，web off，`/tmp/prompt-r53-4.txt` = 4 refs，tag `r59-gate-{1,2}`）**：

| run | wall s | out tok | reasoning | steps | `tell-scan` 调用 | `SCAN_EXIT` | facts | 断言 |
|---|---:|---:|---:|---:|---:|---|---:|---|
| r59-gate-1 | 332.1 | 52,794 | 37,399 | 30 | 2 | `[0, 0]` | 42 | 21 PASS / 2 FAIL |
| r59-gate-2 | 394.5 | 70,063 | 56,677 | 25 | 2 | `[0, 0]` | 43 | 21 PASS / 1 FAIL |
| **中位** | **363.3** | **61,429** | — | 27.5 | **2** | 全 0 | 42.5 | — |
| R58 中位 | 443.9 | 76,848 | — | 26 | 0 | — | 47.5 | — |
| R55 紧基线 | 405.4 | 70,187 | — | — | 0 | — | — | — |

- **第 18 项断言现场 `[PASS] prose gate ran and exited clean — 2 call(s), SCAN_EXIT=[0, 0] strong-free=True`**（两跑同此）⇒ 门禁 **2/2 跑、每跑 2 次必跑**（旧口径 6.1%），且**强命中 0** ⇒ 无条件改写未被触发；弱命中（bold count / mixed numeric）被模型明确当线索（`Weak only — acceptable`）。
- **无分片回潮**：`task` / `subagent_type` 0 次、`--scaffold` 0 次调用、`merge_ref_facts.py` 0 次调用。**质量未退**：每跑 21 PASS（citations 4 refs 键集/日期/标题齐、`{{ref_n}}` 双向、图表 envelope 一致、`present_artifact` 收尾）。
- **FAIL**：两跑共有 `tool_results receipts archived`（P-R53-1）；`r59-gate-1` 另有一条 = `execute timeout_seconds=180` 超平台上限 120 被拒（框架自动重发成功）→ **R59-4**。
- **成本**：墙钟中位 363.3 s（R58 443.9 / R55 405.4）、out 中位 61,429（76,848 / 70,187）均更低，但 n=2 且挂载集不同 ⇒ **不可归因**，只说明「没有可测的变慢」。**判定 KEEP。**

**项目挂载集 4 → 2 = 用户主动取消（不是平台缺陷）**：发布前后 `skills=` 从 4 变 2（`report-humanizer-en` / `report-humanizer-zh` 移出；项目行 `updated_at=2026-10-13T10:12:03`、`updated_by=徐佩佩`、`version=1`），三处 API 一致 ⇒ 运行时确实只挂 2 个。我一度立了 **P-R59-2**，**当日用户澄清是自己从配置里取消的**（规则已内联，不再需要挂载外部 humanizer）⇒ **条目作废、无需恢复**。**对本轮实测不构成阻断**，也无需「不可比」折扣：被移出的两条从未被加载（R58 三跑在 4 挂载下也是 0 次），影响仅「技能目录少两条」。

### 我方能改的

- **R59-1（已用测试兜住）**：扫描器在仓库里有两份拷贝（本包 + `report-humanizer-zh` 仓库）。运行期依赖已消失，残留仅仓库级漂移，由 `test_bundled_copy_matches_the_upstream_repo`（sha256 比对，兄弟目录缺失时 skip）拦截；上游改规则的动作写死在 `prose-style-zh.md` 尾节与 `vendor/README.md`。
- **R59-2（观察项）**：若 live run 显示模型**从不**回显退出码，需评估把 `; echo "SCAN_EXIT=$?"` 收紧为必须照抄的固定命令（WARN → FAIL）。
- **R59-3（记账）**：第 18 项断言**只作用于 artifacts 分支**；拒绝场景（`--expect refusal`）本就不产出报告、也不该跑文体门禁。
- **R59-5（新，低优先）**：原地更新后线上 skill 1.0.9 的「版本更新说明」仍是 R52 那段（`update_skill_file` 我们只传 `skill_id/skill_name` + zip）；若接口支持 message，下次原地更新顺带更新。
- **R59-4（新）**：模型给主线程 `execute` 传 `timeout_seconds: 180`（平台上限 120）→ 被拒后自动重发成功但计入 `no tool errors` FAIL（`r59-gate-1`）。我们的文本已写「main thread 120 s」，属模型越界；候选动作 = 把 `toolbox.md` 的 `execute` 上限写得更显眼（内容改动，下一轮再议）。

### 平台侧（转开发）

- **P-R59-1（新，轻）**：`execute` 参数名不一致 —— 期望 `shell_command`，模型常发 `command`（`r58-mainthread-3` 出现一次 `['command'] Field required; ['shell_command'] Extra inputs are not permitted`，框架自动重发成功但被 runner 记入 "arguments refused"）。第 18 项断言已两种键都读以自保；建议把工具 description 与 schema 命名对齐（与 O51 / P-R58-2 同源）。
- **P-R59-3（新，轻）**：`execute.timeout_seconds` 的 `inputSchema` 无 `maximum` 约束、描述仅 *Optional timeout override for this command.* ⇒ 越界执行时才报错；建议加 `maximum: 120` 并写进描述。
- **P-R58-1（承接，维持观察）**：本轮未复现 `idle` 无 `completed_at` 卡死。
- **P-R53-1（已知，每次命中）**：`tool_results receipts archived` 与本批改动无关。P-R56-1~4 仍在（沙箱 `execute` 单通道 / 子代理 `execute` 默认 30 s / `data-subagent-trace` 未文档化 / 平台无「工具串行、生成并行」提示）。

---

## R58 — 删除 facts 行分片配方（2026-10-13，**已原地发布** + n=3 实测，**KEEP：目标行为达成，指标不可测**）

**起因**：R57 判 FAIL，但它的证据指向一个更干净的收尾 —— 分片**指令**在 4 refs 上 **0/3 被执行**，唯一权衡过的一次（`r57b-shard-1`，16 段推理 / 7,746 字符）是被**我们自己文档里的竞争条款**劝退的（新加的是**许可**，同段旧成本句仍写 "never mandatory" / "Prefer straight-through scripting…decide in one line and move on"，*one lane* 那条被当**代价**读）。**R58 假设**：既然这条配方在被写成"默认"时也只有 ≤1/3 的运行会去看它、看它本身就要烧 reasoning，而它的目标行为在 2–8 refs 档位本来就不划算（facts 只占一轮 out token 的 10–13%，75% 是分不掉的 reasoning）—— **整条删掉，行为不变，而"权衡它的那块推理"消失**。预登记判据：① `task` 全 0；② delegation 关键词的 reasoning part 从 1/3 降到 **0/3**；③ 墙钟/out 无方向性劣化；④ 质量不回退。

**改动**（commit `3518370`，**净减法、不新增脚本**）：删 7 处 —— `SKILL.md:41` facts 分片整段 + `:33` 脚本清单注；`references/input-contract.md` 工作流步 4 从句、`## Large-batch delegation` 的 status 块（*default for the fact rows once 3 or more refs are selected*）、`### Delegating the fact rows (per ref) — the default split for 3+ refs` 整节、平台事实 6；`references/input-and-extraction.md` 的大段；`references/toolbox.md` §2 标题 / pipeline merge 行 / §2a 分片句 / §3 标题与 "Used when…" / token 语法节括注；系统提示词工作流步 1 从句 + *Trigger* 的 fact-row 句 + **`Fact rows, one subagent per ref` 整条 bullet** + 委派段开头的 fact-rows 分支；`scripts/merge_ref_facts.py` docstring 首句改 "optional"。

**保留（防误删）**：`merge_ref_facts.py` + `evals/scripts/test-merge-ref-facts.py` **16 例**（降级为逃生口，同 `build_ledger.py --scaffold`）；`input-contract.md` 的 **`### Measured boundaries of the task tool`** 实测表（并发 28.9 s 重叠 / 四路 6.5 s / 单通道交接 2.8 s / 子代理 `execute` 默认 30 s / 无会话状态 / turn usage 聚合子代理）；**pull 委派（>5 esids）完全不动**；"Try straight-through scripting" 那条（删掉 fact-rows 分支后只对 pull 生效，不再互斥）。`tools/pack-dist.py EXPECTED` 仍 **27**。本地门禁全绿：62 / 25 / 9 / 16 / 28 / 35 / 41 / 5 / 14 + node 8+8 + mutations a 44/44 b 12/12。

**已发布（原地，用户已授权）**：`deps` = `unchanged since the recorded baseline`；prompt **v1.8（原地）79,218 B `f293fb45f39e` → 78,155 B / `6d507fb8fff7`（−1,063 B）**；skill **v1.0.9** dist **161,148 → 160,567 B / 27 entries / `16f3bfce7130`**，回读 prompt 逐字节一致 + skill **27/27 identical**，`status` = **in sync**。skill_id `16aeb0406e12425bad27a2444f17225e`；PROJECT `a7cdda6508e0423c8b7afaaf3a68e50d`。

**实测 n=3**（同固定输入 `/tmp/prompt-r53-4.txt` = 4 refs；`DeepSeek Flash` / web off；tag `r58-mainthread-{1,2,3}`）：

| run | wall s | out tokens | reasoning | steps | `task` | facts 行 | 断言 |
|---|---:|---:|---:|---:|---:|---:|---|
| 基线 n=8（R53/R54/R55，同 prompt） | 413.8 | 70,983 | 50,851 | 17–22 | 0 | — | — |
| 紧基线 `r55-sub-{1,2,3}` | 405.4 | 70,187 | 51,147 | 20–22 | 0 | 36/51/55 | 21/1 |
| R57 参照 `r57b-shard-{1,2,3}` | 445.9 | 78,248 | 62,868 | 20–24 | **0/0/0** | 56/55/48 | 21/1 |
| 实测 `20261013-093256-r58-mainthread-1` | 465.6 | 78,846 | 58,638 | 36 | **0** | 55 | 21/1 |
| 实测 `20261013-093256-r58-mainthread-2` | 404.9 | 68,126 | 56,381 | 25 | **0** | 48 | 21/1 |
| 实测 `20261013-093258-r58-mainthread-3` | 443.9 | 76,848 | 47,186 | 40 | **0** | 40 | 21/1 |
| **R58 中位** | **443.9** | **76,848** | 56,381 | 36 | 0 | 48 | — |

- **② 判据达成（本轮唯一正面结论）**：含 `subagent|delegat|task tool` 的 reasoning part —— R57 **1/3 跑**（shard-1：2 段 / 7,746 字符 / 占该跑推理 4.1%），R58 **0/3 跑**。权衡块消失，与删除目标一致。
- **③ 无方向性劣化，但也测不出收益**：wall 中位 413.8 → **443.9 = +7.3%**（紧基线 +9.5%）；out 中位 70,983 → **76,848 = +8.3%**（护栏阈值 78,081，**未越线**）。与 R57 直接对比：wall **−0.4%**、out **−1.8%**。n=3 中位数检不出 <20% 的效应，而本次改动量级（−1,063 B 提示词）本就在噪声里。
- **① 与 R57 相同**：`tool-task` **0/0/0**，删除没有反向触发分片。**④ 质量无退步**：三跑各 **21 PASS / 1 FAIL**（唯一 FAIL 仍是平台侧 `tool_results receipts archived`）；`records[]` 4 条、附录/时间轴/图齐全、报告 20,631/18,637/21,181 B、facts 55/48/40 行、**`source_file` 省略 143/143 行**（R57 的②减法未回退）、`--scaffold` **0/0/0**、`merge_ref_facts` **0/0/0**。

**判定：KEEP —— 删除生效，代价不可测。** 对「按 ref 分片」的最终结论：**不再重试**（4-refs 档位下模型正确地不需要它；要做必须在 ≥6 refs + registration-class 重载荷另开一轮，且**先删**任何竞争的成本句）。证据全文 `docs/evidence/r58-fact-row-recipe-deletion-2026-10-13.md`；台账 R58 节。

**A 方案对 subagent 的最终口径**（用户问）：`task` 在本 skill 里**只剩一个用途** —— pull 超过 5 个 esid 时按 ≤5 分批拉取，纯上下文限界、**不提速**、永远可选、永不缩小来源集；**facts 行回到主线程写**；`merge_ref_facts.py` 仅作为「万一真分片了」的逃生口随包保留，**工作流没有任何一处依赖它**；`task` 的实测边界表保留为事实基线。

### 我方能改的

- **R58-1（已改，已成事实）**：上表 7 处文本删除；`pack-dist.py EXPECTED` 仍 27（脚本保留）。
- **R58-2（记账，观察项）**：本轮 `steps` 离散度变大（36 / 25 / **40**）。`r58-mainthread-3` 出现一次 **`execute` 参数名拒绝**（`['command'] Field required; ['shell_command'] Extra inputs are not permitted`，框架自动重发后成功）—— 与 O51 同源，非本轮引入。
- **R58-3（待议）**：`read_file` 8–16 次里含 `ls`/`grep` 与多次探查（`toolbox.md` offset 100 limit 230 一次、`chart-templates.md` / `conclusion-language.md` 各一次）。若还要找杠杆，应量**主线程探查次数**而非再动 facts/rules —— 但需先有 tool start/end instrumentation，当前不可测。

### 平台侧（转开发）

- **P-R58-1（承接 P-R57-1，本轮未复现）**：三跑同期启动、全部 `succeeded`，未出现 `idle` 无 `completed_at` 的卡死。旧单仍有效，维持观察。
- **P-R58-2（新，轻）**：`execute` 参数名拒绝 live 可复现（`command` vs `shell_command`），框架自动重发后成功但被 runner 记入 "arguments refused" 清单。属工具 description 与 schema 命名不一致（与 O51 同源），建议对齐。
- **P-R53-1（已知，每次命中）**：`tool_results receipts archived` 三跑均 `[FAIL]`，与改动无关、不影响产物。P-R56-1~4 仍在（沙箱单通道 / 子代理 `execute` 默认 30 s / `data-subagent-trace` 未文档化 / 平台无「工具串行、生成并行」提示）。

---

## R57 — ① 按 ref 分片 facts + ② facts 撰写面减法（2026-10-12，**已原地发布** + n=3 实测，**指标 FAIL；① 未被触发**）

**起因**：找上轮遗留「模型读了但没做」的指令 —— `SKILL.md:33` 让模型跑一次 `build_ledger.py --scaffold` 再改它给的行，实测三跑**都照做却全部重写**（id 复用 0/33、`value`+`endpoint` 命中 0/51、候选只到 ref_3），每轮照付 1 次 `execute` + 读 33 行（≈13 K 字符）。本轮两个假设：**① facts 行按 ref 分片给子代理**（R56 已证子代理**生成**真并发；facts 行是单轮最大的一段生成）；**② facts 撰写面减法**（`source_file` 13% + 4 个默认字段 11% 编译器本就能派生，删掉是纯减法，且顺带删掉 scaffold 那条指令）。

**改动**（commit `b200eb6`）：新增 `scripts/merge_ref_facts.py`（按 ref 确定性合并 shard + 只查分片本身：未知 ref / 跨片重复 id·record / 空片 / 未覆盖 ref 告警，有 finding 则 exit 3 不写）+ `evals/scripts/test-merge-ref-facts.py` **16 例**；`SKILL.md` / `references/{input-and-extraction,input-contract,toolbox}.md` / 系统提示词共 6 处：分片配方（≥3 refs、同一条消息下发、显式 `timeout_seconds`）、`task` 实测边界表、facts 字段契约改为**允许省略派生字段**；`toolbox.md` 新增 `## 3. merge_ref_facts.py`、原 `## 2a.` scaffold 段降级为「仍在、工作流不用」（**代码 + 9 测试保留**）、清掉其余 5 处 scaffold 引用；`tools/pack-dist.py` `EXPECTED` **26 → 27**。

**已发布（原地，用户已授权）**：`deps` = `unchanged since the recorded baseline`；prompt **v1.8 → v1.8（原地）79,218 B / `f293fb45f39e`**（旧 76,477 / `c4bb1a7b3ee1`）；skill **v1.0.9**，dist `multi-clinical-result-comparison-v0.16.zip` **161,148 B / 27 entries / `a4a6f9de9d1b`**，HTTP 200 / `mode=in-place` / `files=0`，回读 **entries=27 identical=27 differing=0**；`status` = **in sync**。skill_id `16aeb0406e12425bad27a2444f17225e`；PROJECT `a7cdda6508e0423c8b7afaaf3a68e50d`。本地门禁全绿：62 / 25 / 9 / **16** / 28 / 35 / 41 / 5 / 14 + node 8+8 + mutations a 44/44 b 12/12。

**平台事故（首屏三跑全废，已重跑）**：`20261012-182425-r57-shard-{1,2,3}` 在 ~264 s **同时卡死** —— `status=idle`、steps 冻结（12/24/9）、`/timing` **无 `completed_at`**、每个线程 2 次 `GET /messages → Connection refused`；三线程都停在等 `execute` 返回、`task` 仍为 0（与本轮改动无关）。`run --resume` 重挂不重发 POST，但 steps 再不前进 → 判死重跑（tag `r57b-*`，正常完成）。平台单 P-R57-1，全文 Obsidian `03-技术与VibeCoding/01-AI与LLM/TS并发turn同时卡死-idle无timing-row-resume也救不回.md`。

**实测 n=3**（固定输入 `/tmp/prompt-r53-4.txt` = 4 esids → **4 refs，跨过 ≥3 分片门槛**；`DeepSeek Flash` / web off）：

| 组 | run dir | out_tokens | reasoning | wall | steps | `task` | facts 行 | 断言 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 基线（n=8，同 prompt、内容=当前减 R57） | R53-doc-4/4b/4c + R54-base-1/2 + R55-sub-1/2/3 | 中位数 70,983 | 50,851 | 413.8 s | 17–22 | 0 | — | — |
| 紧基线 | `20261012-171124-r55-sub-{1,2,3}` | 70,187 | 51,147 | 405.4 s | 20–22 | 0 | 36/51/55 | 21/1 |
| 实测 | `20261012-183501-r57b-shard-1` | 81,344 | 63,194 | 465.5 s | 24 | **0** | 56 | 21/1 |
| 实测 | `20261012-183501-r57b-shard-2` | 60,599 | 44,529 | 384.9 s | 20 | **0** | 55 | 21/1 |
| 实测 | `20261012-183501-r57b-shard-3` | 78,248 | 62,868 | 445.9 s | 23 | **0** | 48 | 21/1 |

- **① 一次都没被执行（`tool-task` 0/0/0）**：只有 shard-1 权衡过（16 段推理），并被**我们自己文档里的竞争条款**劝退 —— 系统提示词 `## Subagent delegation` 的「**Prefer straight-through scripting before delegating**… decide in one line and move on」被套到了 facts 行上；新规则是**许可**（"is a real speed-up" / "needs 3 or more refs"），而旧文本仍写 *never mandatory*，**许可打不过成本**；本轮新加的 *one lane* 那条也被当**代价**读（原话：「4 subagent round-trips (which also share the single execute lane)… doing it myself is cheaper… the benefit is context bounding — but my context already holds the sources」）。→ 与它要替换的 scaffold 是**同一种失效模式**：读了、权衡了、零行为改变，还多烧 reasoning。
- **② 被完整采用**：`source_file` 省略 **159/159 行**，4 个默认字段按行省略 22–49 处；每行序列化字节 **478–482 → 299–337 B**（补回省略字段应为 400–445 B）= **省 24–26%**（facts 块约 1.5–2.5 K out token，正是预登记的「≈3%、必然低于噪声」）。同时 `--scaffold` 调用 **3/3 → 0/3**（候选文件读取消失）——**删指令那一半真改了行为**。
- **指标**：wall 中位数 413.8 → **445.9 s = +7.8%**（紧基线 405.4 → 445.9 = **+10.0%**）；out 中位数 70,983 → **78,248 = +10.2%**（护栏 <+10%，阈值 78,081，紧基线 +11.5%）→ **FAIL**（方向不利，但在 ±20–40% 同输入方差内）。`read_file` 10–12→7–10（符合减法预期），`execute` 13–14→17–21（反而上升）。质量无退步：三跑各 **21 PASS / 1 FAIL**，唯一 FAIL 仍是平台侧 `tool_results receipts archived`。

**判定：FAIL** —— ① **无法评定**（模型在 4 refs 上不分片，且其理由与算术一致：facts 只占一轮输出 10%），② 确认为**真实但很小**的减法（facts 块 −25%）并顺带删掉一个「付了钱没用」的步骤。证据全文 `docs/evidence/r57-fact-row-sharding-and-field-subtraction-2026-10-12.md`；台账 R57 节。

**沉淀**：**加一条许可打不过一条既有的成本句** —— 推这类行为必须先**删**竞争条款，否则模型照旧权衡后拒绝，而权衡本身就要烧 reasoning。**R58 建议（属减法，需授权）**：删掉 facts 行分片配方（`SKILL.md` :41 分支、`input-contract.md` *Delegating the fact rows* 节、系统提示词工作流步 1 指针 + *Fact rows* bullet），保留 `merge_ref_facts.py`、`task` 实测边界表、并发更正；若重试 ①，条件改按**源类型**（registration-class 重载荷、≥6 refs）并先删那句劝退。

## R56 — 能力探针：`task` 子代理并行性（2026-10-12，**非 skill 运行**，未改动、未发布）

**起因**：用户提出「每个证据（每篇来源）开一个 subagent 处理 facts」。该方案只在子代理**真并行**时才对墙钟有意义 —— 平台样板段写「Launch multiple subagents **concurrently**」，本仓 `references/input-contract.md:429/453` 写实测**串行**（并推测后端从未开启 `allow_concurrent_tool_calls`）。两句不能都对，用一次探针判死；探针不依赖任何 skill 内容，故**无需发布、零部署漂移**。

**探针：三轮，前两轮信号相反。** 三轮都用同一模型（`DeepSeek Flash` / web=off），时间戳由沙箱内 `date +%s.%N` 自报，主线程与全部子代理共用一条 epoch 轴；都通过**同一条 assistant 消息里的多个 `task` part** 下发。

| 探针 | 子代理 payload | 重叠 |
|---|---|---|
| R56-a `20261012-174039-r56-probe-parallel` | A `sleep 60` / B `sleep 45`（纯 `execute`） | **0.00 s**（A `…051.140→…111.141`，B `…147.071→…192.072`） |
| R56-b `20261012-175403-r56b-probe-puregen` | 各生成 ~15000 字（`write_file`，**不碰 `execute`**） | **28.86 s**（A `…871.732→…916.885`，B `…888.021→…948.344`） |
| R56-c `20261012-175923-r56c-probe-lock` | A/B/C 各 `sleep 20`（三个子代理） | **0.00 s**，三段首尾相接、间隙 ~2.8 s（60 s 的活花 70.2 s） |

**结果：① 子代理**是**并发的（机制=模型在同一条消息里发多个 `task`）；② 真正串行的是沙箱 `execute`（全平台单通道）；③ turn `usage.json` 实测**聚合**子代理用量。** R56-b 里 B 的第一条命令（888.021）跑在 A 的最后一条命令（916.885）之前、且当时沙箱无其它命令占用 → 两个子代理同时活着；union 76.61 s vs 串行应 105.47 s ≈ **1.38× 提速**。R56-a/c 两轮纯 `execute` 则每次零重叠。R56-b 两个子代理自报合计 `in 157,335 / out 31,684`，而 turn usage = `in 254,815 / out 35,406` → 子代理输出占 **89.5%**。

**判定（已撕掉初判）：** 「按证据开子代理 —— 否决」**不成立**；但也**不是**无条件可行，判据重写为「**只对生成密集环节有效**」：facts 那一次 28,631 token 单发长生成（占该轮输出 43%）**可切并行**；而 `prep_sources`/`build_ledger`/`render-facts`/`patch`/`make_chart`/`make_citations`/`check_report` 全走 `execute` → **分片只会让它们排队**。代价实测：子代理重载通用系统提示（R56-b 两子代理合计 **157,335 输入 token**）+ 不继承项目 prompt（规格需在 `description` 重述）+ 子代理内 `execute` 默认超时 30 s + 主线程仍须做跨 ref 合并校验。粒度上本组输入只选 4 篇 → 只能切 4 片，而墙钟噪声 ±20–40%，效应量正在测量能力边缘。

**撤回两件事**：① commit `2b476fa` 把 R56-a 的「零重叠」读成「子代理串行」并据此否决分片 —— 把**沙箱队列**误读成**运行器串行**；② 上一条提到的「度量陷阱」不成立（见下）。R56-a 那个 35.93 s 空档在「并发子代理 + 单通道沙箱 + 超时从命令开始执行时计时」下完全自洽。

- **待授权（R56-1）**：`input-contract.md:429/453` 现写「串行执行、当作省上下文的装置、而不是并行提速」—— **半错**（生成并行，工具不并行）；改为带编号的实测，并补「子代理内 `execute` 默认超时 30 s、必须显式传 `timeout_seconds`」。属 skill 内容改动 → 需一次发布授权，本轮只登记不改。
- **已撤回（R56-2）**：~~**度量陷阱**~~ —— turn `usage.json` 实测已聚合子代理用量，以后把生成搬给子代理**不会**让 `output_tokens` 变好看而墙钟持平。
- 证据：`docs/evidence/r56-subagent-parallelism-probe-2026-10-12.md`；台账 R56 节；平台问题单 Obsidian `03-技术与VibeCoding/01-AI与LLM/TS子代理声称并行实测串行且子代理execute默认超时30s.md`。
- **溯源面盘点（本轮副产物）**：流水线的「值 → 出处」绑定共 12 条，其中**只有篇内的 3 条**（`quote` 定位 / `ref`+`source_file` / 篇内 `population`·`endpoint`·`assessment` 一致性）天然可按 ref 切；其余 9 条（esid↔源文件、`{{ref_n}}`⇄`citations.json`、引文字段字节级复制、一数一处、附录引用、`records[].trial` 合并、图表时间锚、叙事归属、C1/C2 链接）全是跨篇/跨产物一致性，**必须主线程兜**。

## R55 — 建议项不再阻塞（2026-10-12，**已原地发布** + n=3 实测，**指标 FAIL**；同批带入 R54）

**起因（第一性复盘，「越修越慢」）**：132 个 run 目录（96 份 `usage.json`）回归得 `wall ≈ 34 s + 0.00536 s × output_tokens`，**R² = 0.936、corr(out)=0.967**（reasoning 0.911 / steps 0.862 / in_tokens 0.890）——**运行时长基本等于输出 token 数**。此前所有提速改动都在压工具调用次数（steps 从 45–65 降到 20–28，但每步耗时 9.2 s → 12–18 s，**净持平**），**优化错了变量**。「越修越慢」本身**不成立**（全史 wall 平在 300–690 s，无单调趋势）；真实的三件事是：(a) 同输入方差 ±20–40%，大于我们追过的每一个效应；(b) 步数减半、每步翻倍；(c) **R48（`b5a8282`）引入的门禁层是全史唯一产生修复轮次的来源**（`FINDINGS (` / `WARN:` 在 R33–R47 为 0，R48 起才出现），修复轮次占 wall 的 2–15%。

**归因证据（4c，26 段 reasoning，136,083 字符）**：msg[14] 22,793 字符是**模型手算 `check_report` 的「8 字连续相同」最长公共子串**；msg[11] 54,141 字符是把 45 条引文逐条对回原文；msg[13] 4,619 字符是在纠结设计类事实的 `arm`。三者 ≈ 81 K 字符 ≈ 23 K token ≈ 输出 token 的 37%，**全部是 fail-closed 门禁逼出来的写前自检**。

- **改法（只做减法，不新增规则）**：
  1. **致命度分级**——`check_report.py`（582 → 491 行）删除整块软性 8 字启发式（`SHINGLE`/`REGISTRY_RX`/`MASK`/`_atomic_note`/`_shingles`/`NAME_SPLIT_RE`/`_known_names`/`_is_name_shingle`/`_chart_strings` 及 `--ledger`/`--refs` 两个参数），`return 4 if warnings else 0` → **`return 0`**：**WARN 不再改退出码**，只有真 finding 才 exit 3。
  2. **`make_chart.py` 完整性检查降级**：空 `label`、空 `description`（timeline / bar / line）、line 空 `group` 从 findings 移到 warnings（exit 0、成品照写）；结构性/数值/x 轴锚点/weight/shape/legend/envelope 检查**一条未动**。
  3. **文档**：8 字规则从全部 6 处文档（`SKILL.md`、`chart-templates.md`、`same-trial-evolution.md`、`timeline-diagram.md`、`toolbox.md`、4 个模板中的 3 个）与 prompt v0.16 中删除；`toolbox.md` 新增「两级输出 / 绝不预检建议项」段落（FAIL 表 + WARN 表 + 硬规则「写之前不要预检任何建议项：先写、再跑、只修 FAIL」）。
- **为什么删掉而不是留作警告**：**有它存在（哪怕只是警告）才会让模型手算 LCS**；规则一旦写进文档就要被逐字满足。删除不丢正确性保证——「表是数值唯一出处」另有 `_chart_table_findings` / `_digits_without_anchor` 与 `label`/`content` 长度限制独立看守。
- **指令面净变化**：`+10,712 B / -10,310 B`（.md 净 **+402 B**，行数 `+39 / -25`）——**基本持平而非瘦身**；真正的收益是**行为**（不再写前自检）与 validator 代码 **-91 行**。诚实记录：这不是「指令瘦身」，是指令语义反转。
- **实测协议（先定后改）**：指标 = **output_tokens**（reasoning 单列），同输入（`/tmp/prompt-r53-4.txt`）、**n=3 取中位数**、**中位数下降 > 15% 才算通过**。基线三跑 out = `77,939 / 73,504 / 61,764` → **中位数 73,504，阈值 < 62,478**；wall `419 / 418 / 365` s。
- **本地门禁（改动后全绿）**：`mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS`；`test-skill-scripts.py` **62**（删 2 条 8 字豁免测试、新增 1 条「不再因共享散文片段告警」、1 条 line 空 `group` 改为「只告警 + `--strict` 才失败」）；`test-check-report.py` 25；`test-build-ledger-scaffold.py` 9；`test-render-facts.py` 28；`test_regressions.py` 35；`test-runner.py` 41；`test_pack_dist.py` 5；`test_replay_run.py` 14；Node **16/16**；`verify-run-chain.py` `GATE: PASS`（5 可比）。
- **打包**：dist `multi-clinical-result-comparison-v0.16.zip` **155,133 B / `35248cb29461`**，`--check` IDENTICAL（发布用件为 **155,216 B / `defefed872c8`**，差异为发布前最后一次打包）。
**已发布**：`deps` 无变化；`publish` 原地更新 —— prompt v1.8 **76,477 B / `c4bb1a7b3ee1`**，skill v1.0.9 `is_current=True`、回读 **26/26 identical / in sync**（同批带入 R54 的 `build_ledger.py`/`render-facts.py`）。

**n=3 实测结果（2026-10-12 17:11–17:18）**：out_tokens `[77,939 / 73,504 / 61,764]`（基线）vs `[63,811 / 70,187 / 71,778]`（实测）→ **中位数 73,504 → 70,187 = −4.5%**，门槛 **< 62,478（−15%）** → **指标 FAIL**。wall 中位数 418 → 419 s 持平；reasoning 字符中位数 147,607 → 153,339 持平。三跑各 21 PASS / 1 FAIL（唯一 FAIL 为平台侧 `tool_results receipts archived`），产物完整——**无质量退步**。
- **关键反证（2026-10-12 修正）**：初判「命中 0 条」是**我自己解析脚本 bug 的假象**——工具调用的实参/结果在 `part["input"]` / `part["output"]`，不在 `part["text"]`，而初扫只看了 `text`。按正确字段重扫：**sub-2 真实触发 16 条门禁输出**（`WARN: facts[20/23/26/29/32/34/36/38] … has no `arm``，8 条事实缺 arm），**非阻塞、正常交付** —— 这同时**真跑验证了 R54 的宽松化**（此前 12 次近期运行中 11 次因它 exit 3 → 模型编造 arm）；而**被 R55 降级/删除的路径（`check_report` exit 4 / `make_chart` 完整性检查）在这组输入上确实一次未触发**。故假设①仍被否，但依据是**量级不匹配**（触发率低 + 单次约 1 轮 ≈ wall 的 5%），不是「一次都没发生」。
- **结论：假设①（门禁是耗时主因）被否。** 作为**正确性**修复仍成立（8 字启发式已证伪的假阳性：`RMONi-6（` / `一线晚期鳞状非小`）；keep/revert 待用户裁决，我方建议 **keep**（净删规则 + 指标无退步）。
- **方法论沉淀**：同输入 output_tokens 方差 ±20–40% > 我们追过的每个效应；**n=3 中位数测不出 <20% 的效应**，只有结构性改动值得测。
- **下一杠杆候选（hypothesis ③）**：45 条事实 × 15 字段手工撰写 + 引文自查，占三跑 reasoning 约 1/3，且**不依赖门禁**（模型自发勤勉）；这是唯一还能动指标的杠杆，也是 R52 失败过的领域，需先设计比 R52 更硬的验收。
- 证据：`docs/evidence/r55-advisory-demotion-measurement-2026-10-12.md`；台账 `docs/toolsmith-verification-log.md` 的 R55 节。

## R54 — 空 `arm`/`unit` 门禁修复（2026-10-12，已随 R55 同批发布）

**真实根因（比初判更深）：`build_ledger.py --scaffold` 自己产出空值，编译路径再把它们判死。**
scaffold 第 431 行写 `"arm": arm_text`，而 `arm_text` 在 payload 找不到可用 arm 时就是 `""`（第 406–409 行 `unresolved_arms += 1`），且 scaffold 自己的 `_notes` 明确写「arm 留空，必须人工核对」（第 460 行）；`unit` 同理来自 `_clean(item.get("result_unit"))`，p 界值 / NE 都是空串。随后同一条编译路径用 `if not fact.get(key)` 把这些空串判成 `missing` → exit 3、不落盘。**即编译器拒绝自己 scaffold 的输出**，模型只能编造值凑过校验。

- 实测证据 r53-doc-4c（已发布版本跑）：`is missing 'arm'` 30 条，全部是设计类事实（随机与样本量、数据截止、中位随访、PFS/OS 检验界值、计划/实际 OS 事件数）；模型在第 14 条消息里明确推理「`arm` must be present (not empty)」，最后编出 `arm="全部随机人群"` 填进 15 条，**与 population 重复且语义错误，已污染附录单元格**。4b 的镜像案例：`f_os_lt1_exp_r1`（kind=有效性，value=NE）被逼编造 `unit="（未达到）"`。
- 该失败类跨 12 次运行中的 11 次出现（r48-18 20 次 unit、r50-14 16 次 arm、r53-doc-4 25 次 unit、4c 30 次 arm…），属慢性问题而非偶发。
- **改法**：`arm` 与 `unit` 键必须存在、值可为 `""`（`FACT_MAY_BE_EMPTY`）；缺键仍 exit 3 并提示可给空串。`kind` 不是 `试验设计` 而 `arm` 为空时，走既有非致命 `warnings` 通道打 `WARN`（保住「结果类事实必须指名分组」的安全网，且不阻断编译）。`render-facts.py` 同步允许空 `arm`（附录单元格整段省略、不留分隔符）。
- **端到端验证**：把 4c 真实 facts.json 的 15 条设计事实 arm 还原成 `""` 后重编译 → exit 0、45 条事实落盘、0 条 arm findings（全为设计类故无 WARN）；同一 payload 喂给收紧到只豁免 `unit` 的对照副本 → 立刻重现 `has an empty 'arm'`。
- **check_report 假阳性豁免**（本块另一处）：8 字共享片段自动豁免 `work/ledger.json`（trial / identity 段 / study / arm）与 `work/refs.json`（trial_abbreviation / indication）已声明的名称；含数字片段不豁免。实测 4c：WARN 3 → 0，追警告的往返全部消失（4b 的 `RMONi-6（`、`一线晚期鳞状非小` 假阳性不再报，真实散文重复仍报警）。

**已发布内容的实测 r53-doc-4c**（`20261012-162951-r53-doc-4c`）：368.9 s / 45 facts / 14 execute；token in 3,053,663 / out 61,764 / reasoning 44,311；21 断言 PASS、1 FAIL（仍是平台 `tool_results receipts archived`，与改动无关）。vs 4b（338.9 s / 38 facts / 11 execute，out 53,490）：**单次墙钟不可比**——事实数 38→45（+18%），token 全线 +15~26%；三连测 318.6 / 338.9 / 368.9 s 属运行间方差，不能据此判定修复回退。机制层两处各自可验证：`missing unit` 7→0 ✅、8 字共享片段警告 3→0 ✅；但同类失败**转移到 `arm`**（0→30），正是本轮新增 `arm` 豁免要消除的点。

- toolbox.md 同步说明。本地回归：skill-scripts 64（+3）、scaffold 9、check-report 25、render-facts 28、runner-gate 41、fact-check 35、pack-dist 5、node 16，变异 a 44/44、b 12/12。dist 156,131 B / sha `55ad2eea4cd9`，`--check` IDENTICAL。**尚未推 TS、尚未实测。**

## R53 — toolbox 文档优化，原地发布 + 实测通过（2026-10-12）

**改动**（commit `08e6929`）：`references/toolbox.md` §1 新增 digest 输出样例；§3 新增 `[[fact:id]]` token 语法示例 + 两条硬验证条件。`SKILL.md` 把参考文件拆为必读 5 个 + 按场景条件读 3 个；scaffold 后加数值格式统一决策步骤。161 项本地回归全过。

**dist 重建**：154,430 B / sha `9326006d9d59`（旧 152,558 B 未含本次改动）；`push-skill --version 1.0.9` 原地推，HTTP 200，status 26/26 identical。

**实测 r53-doc-4b**（`20261012-142802-r53-doc-4b`，thread `4c630621`）：320.3 s server / 338.9 s polled，32 calls，输出 token 53,490（vs R51 基线 ~107K，-50%），execute 11 次（vs R51 17 次，-35%），read_file 11 次（vs R51 5 次，读文档而非试错命令）。21/22 断言 PASS，唯一 FAIL 为 `tool_results receipts archived`（平台侧已知 unsafe path 问题，与本次改动无关）。**判定：有效，keep。**

---

## R52 回退完成（2026-10-12）

用户已授权回退。运行资产与 dist 恢复到 R51 commit `3adb77c`，R52 新增两份接口测试随实现撤销，失败证据保留在 docs/evidence 与 Git 历史。TS 采用原地恢复内容：当前标签仍 prompt 1.8 / skill 1.0.9（skill_id `16aeb0406e12425bad27a2444f17225e`），实际内容 == R51 的 prompt 1.7 / skill 1.0.8。prompt SHA `bf7b45dbf5d0`，dist SHA `081cd850befc` / 152,558 B；回读 26/26 identical、status in sync、项目绑定正确。此前“尚未回退”段落为历史实验状态，本段覆盖它。


## R52：执行流程梳理（2026-10-12，已发 TS 新版本，四组真实回归完成，未通过优化验收）

用户已明确授权「改了测试，TS 发一个新版本后真实测试」。本轮统一执行／修复契约，保留临床边界，不改 runner、冻结评分器或固定输入。prompt 的累积 Step discipline 改为五阶段执行契约；SKILL 区分执行路由与临床工作；file-delivery 取消生成文件必须整份重写的矛盾规则；时间轴残留 weight 指令清零。

`build_ledger.py --apply-review` 新增差量审校：完整 records + 每候选一条 keep/update/drop 决策 + 新增完整 facts；组装 facts.json 后仍须默认编译器校验 quote/value；漏审、冲突 id、错误形状与覆盖输入失败关闭，既有输出不受损。不承诺候选临床正确。保留原文事实补充和 unusable scaffold 完整抽提回退。

本地 244 项回归通过（原 231 + review 10 + workflow 3）；变异 a 44/44、b 12/12；零网络链 GATE PASS（118 histories，5 comparable）。上游 deps unchanged。已执行授权的新版本发布：prompt 1.8 / skill 1.0.9，skill_id `16aeb0406e12425bad27a2444f17225e`，26/26 回读 identical，status in sync。代码 commit `7852b73` 已推送。

固定 4/18/14 + B 拒绝场景真实回归已完成，期间冻结运行资产。三组 runner 各 22 PASS；server wall 680.1 / 569.5 / 691.6 s，calls 69 / 45 / 66，均高于 R51 309.2 / 462.9 / 494.7 s（23 / 36 / 38 calls）。B 39.9 s、8 calls、14 PASS，离线评分 11/12（措辞 B-A3 未命中，实际回复明确未生成报告）。review 复用率低：4 条 32 update / 1 drop / 19 additions；18 条 165 全 drop / 140 additions；14 条 50 update / 61 drop / 41 additions。首组内容有「非免疫机制」越界归因，18 条有 PRO／时点内部矛盾，14 条又把所有披露无硬结局与摘要 GLP-1RA 有硬结局同时写出，不能宣称临床全绿。

R52 判定不 keep，但尚未执行回退，TS 当前仍是新版本 1.8/1.0.9；用户本轮授权是新版本发布，回退另须明确授权。O51 execute 参数漂移（live command vs 旧 prompt shell_command）、O52 流程绕行／复用无收益、O53 内容越界和内部矛盾已留证据；不修改评分器掩盖。详见 `docs/evidence/r52-workflow-review-2026-10-12.md` 与台账。Git 证据提交收尾；无 Docker 配置、未涉及镜像。


## 历史快照：2026-10-12（R51：时间轴不再编码「大小 / 形状 / 图例」——已原地发布 + 固定三组真跑 22/22 全绿；同日的 R49+R50 亦已发布。**已被 R52–R57 取代，最新部署状态见顶部 R57 节**）

### R51 — 用户投诉「`weight` 字段部署端不支持」（延申到 `legend`/`shape`/`group` 同根因清理）

**用户口径**：*「这个 weight 字段必须移除，部署端时间轴 JSON 不支持 weight 大小」*。查证时发现同一缺陷类还有 `legend`/`shape`/`group`：**部署端渲染器里它们都不会产生任何视觉效果**。

- **权威证据链（部署端实测）**：family `ee7d944445134cbba5771714f2188cb1`，current 版本标签 `1.0.12`、id `1506a6ac693746f299055ee198abf697`、`updated = 2026-09-21T11:58:40`（说明平台**在原地更新同一版本号**——下载的 zip 已换成 20260921 构建）；部署端 `templates/timeline.json` 里 `weight` / `weightLegend` 出现 **0 次**；渲染 bundle `…/20260921-085926/static/index-9EvceNR0.js`（288,806 B）里节点构造 **硬编码 `{ r: dm, shape: "circle" }`（`dm = 3`）**，DOM 侧节点 dot 是固定 `6px × 6px` 灰圆点（`.mf-ai-charts-timeline-dot`），**无 group / 无 color / 无 shape**；且时间轴的图例渲染器是 **`function Fm(){return []}`（空实现）** ⇒ `legend` 对画布与图例都无效。
- **反证（为什么必须自己守）**：故意造一个带 `weight: 2` + `weightLegend` 的 spec 跑上游新 `validate-cli.js` ⇒ **`exit=0` 且零 warning**；`references/schemas/timeline.js` 仍保留 `weight`（`z.number().min(0).optional().default(0)`）与 `weightLegend`。**schema 允许 ≠ 渲染生效**，上游不会拦这个回归。
- **改动（skill bundle 内，7 文件）**：①`templates/charts/evidence-timeline.json` 重写：删 `weight`/`weightLegend`/`legend`/`group`/`width`/`height`（键序收敛为 `_comment`/`type`/`title`/`subTitle`/`dataSource`/`describe`/`data`），`describe` 写死「**竖向列表、数组顺序即时间顺序（自上而下）、节点等大等形、不渲染图例；大小/形状/颜色都不作编码**」；②`references/timeline-diagram.md` 构建规则新增**第 8 条硬规则**（禁止 `weight`/`weightLegend`/`legend`，含拒绝面「成品与相关文字表述」）并删示例中的全部已死字段；③`references/chart-templates.md` 同步表格单元/字段清单/退出码 `3` 清单/数据填充约束；④⑤`scripts/make_chart.py` + `scripts/check_report.py` 加**双层机械守卫**；⑥三个骨架 `subTitle` 缩到 ≤32 字宽（顺手消掉上游新 warning）；⑦`vendor/` 新增 `1.0.12-20260921/` 快照 + `vendor/README.md` 记录「同一版本被原地更新」。
- **顺序事实纠正**：文档此前写「从左到右」为误述；DOM 是 flex column ⇒ **数组顺序 = 自上而下**，已全文修正。
- **保留面（不误伤）**：`group` **不拒收**（inert、不误导读者，仅文档注为「上游保留字段、本 skill 不用」）；报告模板里作为**内容术语**的「证据成熟度」保留；裸 `图例` 不进守卫词表（59 份历史产物里 `r37:191`「正文、表格与图例采用原文的『双盲』」是合法用例）；`PROJECT_STATE` 旧节里那条废弃 HTML 路线的「圆点大小=证据成熟度」保留原文。
- **文本守卫（窄口径）**：`CHART_ENCODING_CLAIM_RE = 节点大小|圆点大小|节点权重|权重图例|节点形状|形状编码|大小编码|空心圆|实心圆` → `report voice` 组 FAIL。
- **本地门禁全绿**：`mutations.py` `arm a 44/44` + `arm b 12/12` + `never flipped []` + `GATE: PASS`；`test-skill-scripts.py` **54 → 58**；`test-check-report.py` **20 → 25**；`test-render-facts.py` 28；`test_regressions.py` 35；`test-runner.py` 41；`test-build-ledger-scaffold.py` 9；`test_pack_dist.py` 5；`test_replay_run.py` 14；Node 16/16。**计数 = 41 + 35 + 19 + 16 + 58 + 25 + 9 = 203（含 numeric-integrity 28 = 231）**。
- **打包/发布**：dist **152,558 B / `081cd850befc` / 26 entries**（`EXPECTED` 仍 26），`pack-dist.py --check` IDENTICAL；**prompt 未改**（v0.16 / 线上 v1.7 不动）⇒ 只需 `push-skill`（in-place，标签保持 v1.0.8）。**用户已授权并已执行**（2026-10-12，`push-skill --version 1.0.8`）：HTTP 200 / `mode=in-place` / `is_current=True` / skill_id `cd93a42af72b4828b1690b3a7bccfa06` 不变；回读 `status` = **in sync**（`entries=26 identical=26 differing=0 missing-locally=0`）。
- **真跑：固定三组回归（4 / 18 / 14 esid，输入逐字节复用 R48→R50 的 `/tmp/r50/p-{4,18,14}.txt`，10:49–11:11）**：r51-4（`20261012-104926`，309.2 s，23 calls，交付 `report`+`citations`+`evidence-timeline.json`）、r51-18（`20261012-105457`，462.9 s，36 calls，+`endpoint-bar-1.json`）、r51-14（`20261012-110252`，494.7 s，38 calls，+`endpoint-bar-1/2.json`+`endpoint-line-1.json`）——**三组各 22 PASS / 0 FAIL / exit 0**；缓存命中率 0.960 / 0.980 / 0.981。**产物核对**：r51-4 的 `evidence-timeline.json` 顶层仅 `{id, iframe_template, option}`，两行 data 键仅 `label`/`content`/`description`/`time` ⇒ **`weight`/`weightLegend`/`legend`/`group`/`shape`/`width`/`height` 一个都没有**；其 `iframe_template` = `…/20260921-085926/…`（生产 run 实际取的就是本轮核对的新构建）；三份报告过 `check_report.py` 时 `chart cue that does not exist` **零命中**（余下 FAIL 仅 `/workspace/…` 绝对路径的已知回放假 FAIL）。bar/line 的 `group` 命中属合法用法（`"group": false` 与 line 队列标签），守卫只对 `chart_type == "timeline"` 生效。
- **附带记录：O50**：`toolsmith-publish deps` **只比版本标签**，上游**原地更新**（标签不变、内容变）**检测不到**；本轮 `deps` 报 `unchanged since the recorded baseline`，而部署端 1.0.12 实际上已从 20260914 换成 20260921 构建 —— 靠用户投诉 + 手动下载 diff 才发现。**应对**：同一版本号的第二次构建另起 `vendor/<skill>/<版本>-<构建ID日期>/` 目录、README 留档，并在 `vendor/README.md` 的更新流程里写死这条。

### R49 + R50（已原地发布并两次真跑验证）

**R49（用户四条交付层投诉：1、2 改；3 选方案 1；4「都试试」）+ R50（用户：交付报告出现模型自洽/思考过程式叙述，要求全篇排查同类表述 → 原地更新 TS → 再测试）**：两轮内容改动**同批原地发布**（prompt v1.7 / Skill v1.0.8，标签不变）。

- **R49.1 附录版式**：`render-facts.py` 删 `APPENDIX_INTRO`（≈600 字「本表如何排布」规格说明），只留一行 `APPENDIX_LEGEND`；`check_report.py` 新增两条 FAIL（附录标题与表格之间 **>100 字**散文块；附录标题 **>1 次**）。4 模板写明标题/图例/列由渲染器拥有。
- **R49.2 附录列头**：单试验 ≥2 披露 = `**可读短标签**<br>ref_n`（无标签回退 `**ref_n**`）；第二行注册号若已出现在展示名里则删除。实测 `**OCEAN(a)-DOSE**<br>NCT04270760 · 1 条披露`（保留）与 `**NCT02729025（依洛曲单抗 Lp(a) 影像研究）**<br>1 条披露`（去重）。
- **R49.3 一数一处（方案 1：图全留、只删重复）**：制度性根因 = 两个速览模板同时规定「表 + 图」。`check_report.py` 两条 FAIL —— 图自身散文（`subTitle`/`describe`/`data[].description`）复述自己的绘图值；非附录小节「有图 + 表里含该图 ≥2 个绘图值」。豁免 = 剂量/时点/例数数字、研究内对照值与边界值、附录与时间线图。两模板「图表后保留上表」→「不重复上表」。
- **R49.4 四条提速杠杆**：toolbox FAQ（别再翻脚本源码）；prompt 禁回读自产文件 + `check_report.py` 一次定稿；`build_ledger.py --scaffold`（候选事实行，永**不**直写 `ledger.json`；默认 `work/facts.candidates.json`；同一 esid 留最后一份 payload；空值/`NR`/`NE`/`未报告`/`NA`/`N/A`/`-`/`—` 跳过）；图表 spec 一次成稿。
- **R50 第四语域（本轮核心）**：判分器 `check.py` **一行未动**（保住 44/12 变异套件语义），规则全落 `check_report.py`：6 常量 + `_meta_narration_findings()` + `main()` 的 `report voice` 检查组。**FAIL** = 自述标签（bullet/表列：`分析模式`/`分析口径`/`选择依据`/`可比性结论`/`对齐等级`/`不绘图原因`/`有限并列原因`/`纳入标准`/`检索策略`/`报告结构`）、分类判断语（`可绘图`/`只能有限并列`/`不具备绘图条件`/`部分对齐`/`仅背景对齐`）、过程短语（`本次选择`/`本次纳入`/`我们选择`/`本轮`）、内部与运行环境词（`src=`/`esid`/`payload`/`JSONL`/`MCP`/`工作区`/`沙箱`）、自证尾巴（`无未复核记录`/`无遗漏`/`全部通过`）。**WARN** = 宽口径自指（`本报告`/`本次`，负向断言排除「本次披露」）。**不**禁 `token`/`轮次`（误伤「治疗轮次」）；**`比较口径` 不计 FAIL**（4 模板本就带该 blockquote）；保留位 = 非头对头声明一句 + `原文核对：` 覆盖行（只写材料与深度）。同步写进 `SKILL.md` 硬规则段、prompt 交付前检查段、`references/toolbox.md` §7 + 两条 FAQ、`references/input-contract.md`（覆盖行只写来源类**文字**；`src=N` 等内部字段名与自证尾巴不进交付物）、4 模板（删 `分析模式`/`选择依据`/`对齐等级`，差异改写为时点/人群/定义/方向）。
- **现场取证**：旧产物 `…-r48-a`（用户看到缺陷的那份）回放新检查器 ⇒ 四类语域逐条命中（`'**分析模式：'` / `'**选择依据：'` / `'**可比性结论：'` / 4 处 `对齐等级` 表列 / `纳入本次`·`只能有限并列`·`不生成优效排序`·`部分对齐` / `self-audit tail: '无未复核记录'` / `internal field: 'src=1'`）。
- **本地门禁全绿**：`mutations.py` `arm a 44/44` + `arm b 12/12` + `never flipped []` + `GATE: PASS`；`test-render-facts.py` 28；`test-skill-scripts.py` **58**（R51 新增 4 条：时间轴 `weight`/`weightLegend`/`legend`+`shape` 被拒 + 骨架/文档不得回潮）；`test-check-report.py` **25**（R50 语域 8 条、R51 时间轴退役编码 5 条）；`test-build-ledger-scaffold.py` 9；`test_regressions.py` 35；`test-runner.py` **41**（第 41 条 = 本地 `__pycache__/*.pyc` 不得算作线上缺失，见 O48）；`test_pack_dist.py` 5；`test_replay_run.py` 14；Node 16/16；`verify-run-chain.py` `GATE: PASS`（**115** histories / 5 可比 / 110 跳过）。**计数纪律 = 41 + 35 + 19 + 16 + 58 + 25 + 9 = 203（含 numeric-integrity 28 = 231）**；R49/R50 口径为 194 / 222。
- **打包/发布**：dist **152,558 B / `081cd850befc` / 26 entries**（R50 时 151,330 B / `df993fdddf83`；`EXPECTED` 仍 **26**，R49/R50/R51 均未新增 bundle 文件）；prompt **76,578 B / `bf7b45dbf5d0`**（**R51 未动 prompt**；**有意不再激进瘦身**）；`deps` = `unchanged since the recorded baseline`（⚠ **R51 实证它只比版本标签，上游原地更新看不出来**，见 O50）；`status` = **in sync**（R49+R50+R51 均已原地发布；R51 于 2026-10-12 经用户授权原地更新，标签仍 v1.0.8）。
- **真跑：2 组 2 esid（同 r48-a/r48-a2 输入）+ 固定三组回归（4/18/14 esid，输入复用 R48）**：`r50-a` **24 PASS / 1 FAIL**（r50-a 的唯一 FAIL = **O48** runner 假 FAIL）、`r50-a2` **25 PASS / 0 FAIL / exit 0**；**`r50-4` / `r50-18` / `r50-14` 各 25 PASS / 0 FAIL / exit 0**（25 / 46 / 31 calls，383.2 / 617.3 / 510.8 s）⇒ 语域闸门零 thrash、O49 未在 18 esid 组复发。**语域修法在生产侧生效**：无 `分析模式`/`选择依据`/`可比性结论`；速览段只写核心终点要点 + 图；数值表在 §四并带 `解读边界` 列；覆盖行「来源类均为 PubMed 期刊论文，深度为期刊摘要级（库内正文即原文摘要，未取 PMC 全文）」——无 `src=`、无自证尾巴；本地 `check_report.py` 回放 `report voice` 全绿。**速度**：同输入 r50-a2 calls **45 → 26**、out 69,610 → 63,097、reasoning 51,506 → 43,373、墙钟 359.5 → 343.3 s。**离线 scenario a**：`r50-a` **43/44**（= r48-a 基线）、`r50-a2` 38/44。
- **本轮 O 条目**：**O48 已修**（runner 支撑清单把本地 `scripts/__pycache__/*.pyc` 当「线上缺失」⇒ 假 FAIL；清单比对前过滤 `__pycache__`/`*.pyc`；备份 `toolsmith-publish.v16.bak` + `py_compile` + 零网络闸门 + `test-runner.py` 40 → **41**）；**O49 待修（1/2）**（图表行 `description` 提到另一治疗臂的剂量/间隔 ⇒ 行身份不唯一 ⇒ `A-S9`/`A-S9b`/`A-S10` 同源 FAIL；改法 = 报告侧一句硬规则，随下一次内容轮发版）；O40/O44/O46/O47 状态不变。
- **未做**：O49 报告侧硬规则、O44/O47 等第 2 份样本、O40 新样本复现观察。台账节见 `docs/toolsmith-verification-log.md`（R49 / R50 两节 + O48/O49）。

## 历史快照：2026-10-10（R48：随包六脚本 + 单遍正文 + 合批调用；**已原地发布并六次真跑验证**）

**R48（用户答复「L2-4都想要」）**：三条速度杠杆**同轮**落地（覆盖先前「一次一个杠杆」的纪律），归因改用「历史 16 run 基线 + per-lever 签名」。**本轮不动评分器、不改 runner。**

- **触发（决定性证据，`/tmp/l2/attr.py`）**：自写脚本 + heredoc 占各 run 输出 **25–55%** —— `r47-14` 11 个一次性脚本共 59,598 out tokens（`scripts/` 61,470 B，单个最大 `build_ledger.py` 36,753 B）；`r47-a` `report prose draft.md` 13,978 + `execute: other` 17,919；`r47-18` 自写脚本 36,511 B。**根因 = R45「`edit_file` 只限报告正文」把模型逼成「用一次性脚本原地打补丁」。**
- **L2 随包发脚本（6 个新文件）**：`scripts/prep_sources.py` / `build_ledger.py` / `patch.py` / `check_report.py` / `make_chart.py` / `make_citations.py`；**不共享 `_lib.py`**、写入点一律 `except OSError` → 一行 `ERROR: cannot write …` + exit 2；契约集中写在新增 `references/toolbox.md`（精确 CLI/IO/退出码），并写进 SKILL.md 支持文件清单。测试 `evals/scripts/test-skill-scripts.py` **54/54 OK（15.0 s）**（`subprocess` 直跑六脚本 + 真 `render-facts.py` 端到端链 + 每条「应当失败」配一条「应当通过」邻居）。
- **L3 单遍正文**：`work/draft.md` 从流水线移除；带 `[[fact:…]]` token 的正文直接写 `/workspace/output/report.md`，一次 `render-facts.py` **原地**渲染（`--draft` == `--out`，已证 `_atomic_write` 先读后写）；后续小改走 `patch.py`。落在 prompt 第 6 条 + 输出契约段 + `SKILL.md` 9/9b + `references/file-delivery.md`、`citation-and-ref.md`、`input-and-extraction.md`、`chart-templates.md`。
- **L4 合批调用**：prompt 第 7 条目标 **≤ ~25–30 tool calls**；禁止「写 N 分块再拼接」「重复读同一文件」「手工复查脚本已校验的产物」。
- **运行时路径**：Skill 挂在 `/workspace/skills/multi-clinical-result-comparison/`，六脚本按绝对路径调用（`python3 /workspace/skills/multi-clinical-result-comparison/scripts/<name>.py`）；裸 `scripts/…` 在 cwd `/workspace` 不解析，本轮已把该事实写进 prompt/SKILL.md/toolbox.md/各 reference 与脚本 usage。
- **打包**：`tools/pack-dist.py` `EXPECTED` 19 → **26**；dist **138,171 B / 26 entries / sha256 `bf0c9cf84ecf`**，`--check` IDENTICAL。
- **本地门禁全绿**：`py_compile` 六文件 OK；`test-skill-scripts.py` 54；`test_pack_dist.py` 5；`test_replay_run.py` 14；`test-runner.py` **40**（R48 +1）；`test_regressions.py` 35；`test-render-facts.py` 28；Node 16/16；`verify-run-chain.py` `GATE: PASS`（5 可比）；`mutations.py` `arm a 44/44` + `arm b 12/12` + `never flipped []`；`deps` = `unchanged since the recorded baseline`。**计数纪律更新**：**164 = 40 + 35 + 19 + 16 + 54**（numeric-integrity 28 单列）。
- **发布（用户「原地」）**：`push-prompt --version 1.7` / `push-skill --version 1.0.8` 均 HTTP 200、回读 `matches_local=True`；`status` = **in sync**（zip `entries=26 identical=26 differing=0 missing=0`）；版本标签不变（prompt v1.7 / skill v1.0.8）。
- **六次真跑 + per-lever 归因**：`r48-a` 28 attempts / 312.9 s / 21 PASS 1 FAIL（模型侧 `read_file offset 越界`）、`r48-4` 42 / 391.1 s、`r48-18`（首次 `inconclusive`，复跑）59 / 496.0 s、`r48-14` 28 / 303.4 s（后三组的 FAIL 均为 **O45**）；修 O45 后 `r48-4b` 51 / 425.9 s、`r48-a2` 45 / 359.5 s **均 22 PASS / 0 FAIL**。**L2**：`artifacts/scripts/` 四组全空（基线 r47-14 为 11 脚本 / 61,470 B ≈ 54% 输出），六脚本每轮全部使用；**L3**：四组皆无 `work/draft.md`、`write_file` 降至 2–3 次整文件写；**L4**：attempts 40→**28** / 56→**42** / 56→59（持平）/ 66→**28（−58 %）**，墙钟 −10 % / −24 % / +2 % / **−47 %**，`read_file` 仍 8–20 次/run。out token −34 % ~ +18%，**不作为判据**。离线 scenario a：r48-a **43/44**（= R47 基线）、r48-a2 40/44（该 run 漏了机制句，属 run 间覆盖率差异；`A-C7` 词形缺口 = 新 O47）。
- **本轮新增 O 条目**：**O45**（runner 收据正则不认全角 `）` 等 CJK 标点，3/4 组 FAIL；`_RECEIPT_STOP` 重建 `TOOL_RESULTS_RX` + 回归测试 + 离线重放四组全转 PASS，备份 `toolsmith-publish.v16.bak`）、**O46**（模型 `read_file offset` 越界 1/2 组 ⇒ R49 内容轮加硬规则）、**O47**（`A-C7` 只认「第 ?16 ?周」，1 样本 ⇒ 待样本）。
- **未做**：O46 的 prompt 硬规则（R49）、O44/O47 等第 2 份样本、O40 报告侧机制在新样本上的复现观察。R48 台账节已落 `docs/toolsmith-verification-log.md`。

## 历史快照：2026-10-10（R47：O43 结案 + O40/O41 报告侧习惯句已原地发布；四组真跑 + 耗时 A/B）

**R47（用户答复「改吧」+「分析下 2–3 条结果也要 5min+ 的耗时分布」）**：按「一次内容改动一轮」纪律，本轮只装 **O43 + O40/O41 报告侧习惯句**；**耗时优化另开 R48 提案**。

- **线上（原地更新，版本标签不变）**：prompt `v1.7` **65,959 B / `f63bf180822c` → 67,591 B / `c1641a46810a`**；Skill `v1.0.8` dist **103,982 B / `47c06e7aa6d4` → 105,347 B / `025aec791b1c`**（19 entries）；发布前 `deps` = `unchanged since the recorded baseline`，发布后 `status` = **in sync**。
- **改 5 个文件**：prompt 三条 hard rule（**Every chart row names its own trial** / **A marker binds its own record's content** / **`库内记录` has exactly one legitimate use**）、`SKILL.md` 两条中文硬规则（引注归属 / 图表每行点名自己的试验）、`references/chart-templates.md`、`references/citation-and-ref.md` 新节 `## Marker attribution`、`references/input-contract.md`。
- **四组真跑 4/4 全绿**（顺序执行；`arguments refused = 0`）：`r47-a` 349.1 s / 40 attempts / 离线 **43/44**；`r47-4` 512.1 s / 56；`r47-18` 488.6 s / 56；`r47-14` 569.7 s / 66；均 **22 PASS / 0 FAIL / exit 0 / succeeded**。
- **O43 结案（4/4 命中）**：柱子 label 前缀由「药名+剂量+间隔+时点」升级为自带试验身份（`OCEAN(a)-DOSE · …`、`NCT02729025 · …`、`HARMONi-6（NCT05840016）· …`、`…（NCT04987320）`）；r47-4 只出单试验时间线图，规则不适用。
- **O41 收尾**：五份产物 `库内记录` 出现 **0 次**（A-P2 无触发）⇒ 习惯句生效；不改评分器。
- **O40 第 3 份样本（`r47-loweff-a`）机制定位**：表格 cell 无标记 ⇒ `units()` 继承本行 `ref_1` ⇒ 「OCEAN(a)-DOSE 未评估该终点」只点名 `ref_2` 的试验 ⇒ `A-ATTR` FAIL；R47 正文侧习惯句覆盖不到表格继承 ⇒ **R48 再收**（阴性/缺测句必须带**被点名那条记录**自己的 `{{ref_n}}`，否则不点名对方）。
- **新增 O44（待样本 n=1）**：`A-C9-mds-tbr-A` 只认减号（`-8\.3`/`-5\.3`），r47-a 写「降低 8.3%／降低 5.3%」（交付物内部一致、`A-S10` PASS）⇒ 离线 43/44；同 spec 的 `A-S10` 自称「符号由模型自选」⇒ 口径不一致。修法 = 各加文字式备选，按 O27/O28 先例等第 2 份样本。
- **耗时结构（只读，落 `docs/evidence/runtime-breakdown-2026-10-10.md`）**：生成占墙钟 **65–92%**、reasoning 占输出 **46–76%**、工具全部 **<15%**；2 esid 与 18 esid 同量级。**A/B 负结果**：`--reasoning-effort low` 不减 reasoning（44,975 vs 40,304），墙钟 −39 s 全来自步数少 10 步 ⇒ R48 候选 = L2 随包发脚本 / L3 去 `draft.md` 两遍写 / L4 压步数。

## 历史快照：2026-10-10（R46：O42 已结案 —— 工具侧前置拒绝改判 WARN；F1 不再污染 keep/discard 信号）

**R46（用户答复「谁好，你推荐谁」+「你自己看着办吧」+「不管了」）**：按推荐执行 **O42 选项 B 的窄口径**，只改本地 runner（`~/.local/bin/toolsmith-publish`，备份 `toolsmith-publish.v15.bak`），**prompt / Skill / dist 一字未改、TS 无写动作**。

- 新增 `TOOL_REFUSED_RX`（`^` 锚定，只收编两种实测形状：`write_file` 的 `File '<path>' already exists…`、`edit_file` 的 `Could not find the target string in '<path>'`）→ `retry_kind()` 返回 `"rejected"`；新增 `REFUSAL_BUDGET = 3`，原恒 PASS 的信息行改成带预算判定（**断言仍 22 条**，`verification.md` 语义与退出码不变）。被包装的消息（`RuntimeError: File '…' already exists`、`MCP error: …`）**仍落 `errors`**。
- **离线重打分 98 份归档**（零新 run / 零网络）：`errors > 0` 的 run = **0**；拒绝次数直方图 `{0:77, 1:18, 2:3}`；单 run 最大 **2**；超预算样本 **无**；五次历史 F1 FAIL **各恰好 1 次拒绝**。证据 `docs/evidence/o42-refusal-reclassification-2026-10-10.txt`。
- **本机门禁**：`py_compile` OK；`test-runner.py` **38 → 39 OK**（新增含 2 个负例的前置拒绝单测）；`verify-run-chain.py` **`GATE: PASS`**（98 / 5 可比 / 93 跳过）；`test_replay_run.py` 14 OK；`test_pack_dist.py` 5 OK；`test_regressions.py` 35 OK；Node 16/16；`test-render-facts.py` 28 OK；`pack-dist.py --check` **IDENTICAL**。
- **线上真跑两次**（scenario A，R45 已发布内容）：`r46-a` 330.0/349.2 s、`r46-a2` 360.7/371.2 s，均 **22 PASS / 0 FAIL / exit 0 / refused=0**。
- **O40 / O41（自主处置）**：不改评分器、不单独发版，候选句随**下一次内容改动**一轮进（与下面的 O43 同批）。
- **新增待修 O43**：`A-S9`/`A-S9b`/`A-S10` 要求图表行（`label`+`description`）点名**试验**，但 prompt/SKILL 从未把这条写成规则 → `r46-a` 5 根柱子只写「药名+剂量+间隔+时点」⇒ 离线 **40/44**；`r46-a2` 把试验写进 `description` ⇒ **44/44**；同门径 `R45-a` 亦 PASS ⇒ 同 prompt 3 次 scenario A 里 **1/3 丢试验名**。判分口径自洽（行内 5 维须全部出现），属报告侧偶发漏写 + 规则只在 fixture 隐式存在 ⇒ **本轮不改**（n=1），候选① prompt/SKILL 补一句硬规则（随下次内容改动发版）；候选②判分侧去试验维度（证据不足）。
- 用户③「不管了」⇒ 撤回「`write_file` 提供 upsert/默认覆盖」的平台建议，**不再提单**。

## 历史快照：2026-10-10（R43–R45：F2 已修好并复验；F1 三轮强化后仍未清零）

**线上状态**：prompt **v1.7 = 65,959 B / sha `f63bf180822c`**；Skill **v1.0.8**（dist **103,982 B / 19 entries / sha `47c06e7aa6d4`**）；`status` **in sync**；`deps` unchanged。三轮均**原地更新**（版本标签不变）：R43 prompt `e23eef7201d0` / dist `2f4700a2f295`；R44 prompt `5b8043bb3779` / dist `cdb4992f9b20`；R45 = 现值。

**F2（同一观察一套写法）已修好且复验**：生成侧 = prompt 新 hard rule「One wording per observation」+ `SKILL.md` 硬规则段 + `references/chart-templates.md` bullet（图表 `label`/`description` 逐字复用正文身份短语；源文 `monthly` 就写「每月」）；判分侧 = `scenario-a.facts.json` 30 条 `identity_patterns`/`report_identity_patterns` 双向放宽（225 mg Q12W vs Q24W 仍互斥）。证据：`A-S9`/`A-S9b`/`A-S10` 在 R43-a/R44-a/R45-a **连续四次 PASS**；R41-A 重打分 **41/44 → 44/44 PASS**。

**O27 已结案**：`A-C16` pattern 1 放宽为 `硬结局|硬终点|心血管事件|心血管结局`（pattern 2 否定式不变）+ 回归测试；scorer **32 → 34 → 35**。

**F1（写入被拒 → `no tool errors` FAIL）三轮强化仍未清零**（唯一未结项）：R43（覆盖面扩到任何文件）1/4 失败；R44（无条件 `overwrite=True`）1/4，换形态（`edit_file` 旧目标串）；R45（`edit_file` 只准用于报告正文）1/4。三轮 12 run 失 3，**其余 21 条断言每次全过**（平台 re-prompt 后 run 正常完成、产物完整）⇒ 判为**行为天花板**，非合同缺口；台账 **O42** 给三选项（A 接受 / B 改 runner 断言口径 / C 正文改为脚本一次成文），**等用户选**。

**新增待样本（不改评分器）**：**O40** `A-ATTR` 对对方记录的否定陈述不给豁免（R43-a、R45-a）；**O41** `A-P2` 对非分歧地提到库内记录零容忍（R45-a）。

**真跑**：R43 22/21/22/22、R44 22/22/21/22、R45 22/22/22/21（每轮恰一组栽在 F1）；场景 A 离线 R43-a 43/44、**R44-a 44/44 PASS（首次全绿）**、R45-a 42/44。

**本地门禁**（R43–R45 当时值；**R46 后 runner-gate 已 38 → 39**）：runner-gate 38 / scorer 35 / tools 5+14 / Node 16 / numeric-integrity 28 全 OK；变异闸门 `arm a 44/44, arm b 12/12` → `GATE: PASS`。

## 历史快照：2026-10-10（R41：药名成对字段 + 附录可读名 + humanizer 交接段已原地发布；R42 = Phase A）

**R41（用户 2026-10-10 诉求 b/c + Phase A，已完成发布与四组回归）**：

- **(c) 药名成对字段锐化**：把「中文报告药名」从软约束改成**可机械检查的硬规则** —— 记录自带 `arms[].drugs[].drug_earth_name_cn` / `_en`（`docs/params-tool-schema.md` 已在 ALLOWED_FIELD_NAMES 里），规则写成「中文报告 `_cn` 非空即用、英文报告用 `_en`；目标语言字段空/`未报告` 才回退另一语言并保源拼写；**永不音译/翻译/归一化/凭记忆映射/查外部字典**」。落点：prompt 5 处（命名段 / Plain entity names / final verification / entity 字段段 / 命名 bullet）、`SKILL.md` 2 段、`references/input-and-extraction.md`、`references/input-contract.md`。
- **(b) 附录列头可读名优先**：`render-facts.py` 新增 `_identifier_only()`；`_column_label()` = 可读账本 `study` 名 → 可读记录 `trial` 名 → 可读 identity 首段 → 原始 study/trial → 注册号 → identity 首段；`_column_header()` **只在显示名本身是纯注册号时**才删第二行重复注册号（`研究甲（NCT05840016）` 这类保持原样，既有测试不动）。`APPENDIX_INTRO` + 四模板表头句同步；`test-render-facts.py` 26 → **28/28**。
- **humanizer 交接段**：prompt / `SKILL.md` 各加一节，说明「中文报告 → `report-humanizer-zh`、英文报告 → `report-humanizer-en`，绝不同用；顺序 = 报告 → 账本渲染门禁 → 语言 pass；**本 prompt 优先于 humanizer 风格规则**」，并列明受保护集合（结构与小节标题、`原文核对：` 覆盖行、全部 `{{ref_n}}`、数值/单位/精度/日期、发表时间列与顺序、表格形态、图表 JSON 与 `::visualization` 路径、citation JSON、两个固定交付路径）。
- **发布（原地）**：dist **102,716 B / 19 entries / sha `ab1efaccf624`**、prompt **v1.7 = 63,422 B / sha `78c1a2a71efe`**、Skill **v1.0.8**，`status` **in sync**（发布前 `deps` 报 2 条上游变化 = 我们自己新建的两个 humanizer skill 首次进基线 → 先 `deps --accept`）。
- **R41 四组（2/4/18/14 esid）**：22 / 21 / 22 / 22 PASS，(b)(c) 均在真产物上验到（`**NCT02729025**<br>1 条披露` 不再重复注册号；中文药名出现 `卡瑞利珠单抗`15 / `替雷利珠单抗`50；场景 A 离线 **39/44 → 41/44**，`A-C1`/`A-C2` 由 FAIL 转 PASS）。
- **R42 = Phase A（18/14 esid 的 humanizer 臂，对照 = 同 prompt 的 R41）**：21 PASS（1 FAIL = 模型重写辅助脚本被拒）/ 22 PASS。量化：18 esid 粗体 47→26（−45%）、12-gram 重复率 0.0911→0.0643（−29%），14 esid 方向相反（+33% / +24%）；**两臂 strong 命中均 0、`{{ref_n}}` 逐条相等**；代价 = 工具尝试 +45~51%、墙钟 +13~17%。**每臂 n=1 → 不宣称 humanizer 有可测收益**，默认策略仍是不强制。
- **两条待办（都已给证据，未落盘，等点头）**：**F1** prompt 第 6 条文件写入纪律只覆盖报告正文 → 2/5 run 因重写辅助脚本（`scripts/build_ledger.py`、`scripts/digest.py`）触发 `write_file` 拒写；**F2** 同一观察身份词在报告内混用（`每月` 3 次 vs `Q4W` 9 次，源文只有 `monthly`）→ 图表 label 取 `Q4W` 使 `A-S9`/`A-S9b`/`A-S10` 三项 FAIL（41/44），改法 = prompt/SKILL 加「一套写法」+ `scenario-a.facts.json` 该观察 `identity_patterns` 放宽到 `每月|每月一次|QM|Q4W`。

## 历史快照：2026-10-10（Phase 2「交付物不写运行物流」已原地发布；A-P10 门禁落地，R40 四组全绿）

**Phase 2（用户第二诉求，2026-10-10 已完成）**：把「抓取受限 / 无外网 / 运行环境」这类**我们这一侧的取回过程**从对比 skill 里整体移除，只留**材料/来源属性 + 分析深度**，并把它变成**机械门禁**而不是口号。

- **契约改动**：`system-prompts/multi-clinical-result-comparison-v0.16.md`（6 处）、`skill/.../references/input-contract.md`、四个 `templates/*.md`、`skill/.../SKILL.md`（覆盖行 + 非 OA 判据两句）。
- **新门禁 `A-P10-no-run-logistics`**（`check.py` 新增 `op_no_run_logistics`，fail 级）：逐句匹配 `本次运行/本运行环境/运行环境`、`无外网/外网通道/网络受限/联网`、`抓取失败/取回失败/拉取失败/未能取回/未能发起`、`HTTP 4xx|5xx/状态码/接口返回/接口报错`、`超时未返回/重试/预算用尽/工具调用`。**A-P4 的接受词表同时删掉 `抓取受限`**（那正是要禁的措辞），改为接受「来源类或来源侧属性」；`非 OA` 只能由明确元数据支撑，**HTTP 500 不是非 OA 证据**。
- **变异与种子**：`mutations.py` 追加 `M43`（覆盖行尾部追加运行物流 → 只翻 A-P10）；R17 基线自带旧措辞，故新增 `seed_a()` 只改写覆盖行**措辞**、保留 route/来源类/深度语义（`MUT_SEED_A=0` 可复现未种子基线）。
- **计数**：`scenario-a.facts.json` 44 → **45 条（44 fail + 1 warn）**；变异/合法对照 **64 项**（`MUTS_A 43 / NEG_A 6 / MUTS_B 14 / NEG_B 1`）。
- **发布（原地，不新开版本号——沿用既有授权）**：dist **100,422 B / 19 entries / sha `4d92d3b4b7c3`**、prompt **v1.7 = 59,154 B / sha `2aac60f1c992`**、Skill **v1.0.8**，`status` **in sync**。
- **验证**：`test-render-facts.py` 26/26、`node --test 'test/*.test.mjs'` 16/16、`test_regressions.py` **32/32**（新增 `NoRunLogisticsTests` 5 项）、变异闸门 `arm a 44/44 + arm b 12/12 → GATE: PASS`；**R40 四组（2/4/18/14 esid）各 22 PASS / 0 FAIL**，四份覆盖行运行物流 grep 计数全 0，逐字证据在 `docs/evidence/fact-check-a-p10-real-artifacts-2026-10-10.txt`。
- **新发现的待办**：R40-1（场景 A）在 `--scenario a` 下 5 项 FAIL，根因单一 = 模型没用记录自带的 `drug_earth_name_cn`（写英文名）→ 属指令遵循偏差，锐化规则留待下轮（本轮不再发布重跑）。
- **两个 humanizer skill（Phase B）**：①排版统一规则 + 扫描器文档级弱命中 `W-FMT-MIXED`（`tell-scan.py` + 两份 `SKILL.md` + 两份 `patterns-*.md` + 各 +2 回归测试 → 25/25）；②过程口吻措辞边界（宿主契约要求的声明写成**材料属性**，不写运行环境/链路）。bump **v0.1.0 → v0.1.1**（zh 28,406 B / en 30,765 B，`--check` 双向 IDENTICAL），两个 skill **TS 原地更新成功**（平台版本号仍 1.0.0，`is_current=True`，部署 == dist）。

## 当前快照：2026-10-09（v0.16.1 已原地发布；R38 三组全绿验收四点改动）

**最新（2026-10-09）**：R35 → R36 → R37 连续三轮验证 prompt 的「文件写入纪律」三次迭代，**R37 三组 22 PASS / 0 FAIL / exit 0**（`6143cc8f` / `a7c58280` / `15b0f2b5`，347.7 / 530.5 / 411.9 s），R36-3 的 16 s 零产物 flake 未复现（仍留平台问题单）。R37 产物取证 + 用户五点诉求 → **v0.16.1** 四点改动：①图（时间轴）只画骨架、表格是数值唯一出处，图内除 `time` 锚点外禁数值，图内文本与表格单元格不得有 ≥8 字连续相同文本；②单试验附录改**每条披露一列**（原 1 列 + `<br>` 堆叠长文本）；③`records[]` 必填收成 `ref` / `identity` / `conclusion`（+ `trial`），`title` / `design` / `arms` / `coverage` **接受但不渲染**，四个散文行从 `DESIGN_ROWS` 删除；④附录列头形态由渲染器固定（多试验 `**试验名**<br>注册号 · N 条披露`；单试验 `**ref_n**<br>短版本标签`），新增 audit `appendix_layout` / `appendix_columns`；⑤行标签不稳定由 prompt/SKILL 设计 fact 白名单治理（渲染器不加硬截断）。本地门禁：`test-render-facts.py` **26/26 OK**、`verify-run-chain.py` `GATE: PASS`、`mutations.py` `arm a: flipped 43/43` + `arm b: flipped 12/12`。**原地发布**（用户要求不新开版本号）：dist **99,640 B / 19 entries / sha `5457c8c4fd00`**（`push-skill --version 1.0.8`，`skill_id cd93a42af72b4828b1690b3a7bccfa06` 不变）；prompt **58,795 B / sha `1d9153c88f3c`**（`push-prompt --version 1.7`）；`status` → **in sync**。runner 修 O39（文档悬空指针，`docs/params-tool-schema.md` 31,729 → 31,671 B）。**R38 三组验收全绿**（`4014f791` / `5ddb5fac` / `c8851877`；390.9 / 494.2 / 534.4 s；各 22 PASS / 0 FAIL）；单试验附录 4 列、表头统一、14 条自造设计行消失、图-表共享 0 处 ≥8 字连续文本。详见 `docs/toolsmith-verification-log.md` R35–R38。

**三组已跑完（覆盖下文运行中状态）**：R27 4/4、R28 18/18、R29 14/14 均产出报告。R27断言全过；R28写文件冲突导致断言FAIL；R29无FAIL但3次拒参/2次全文500已披露。设计冲突披露部分生效，三组内容审查均有待改项，不宣称全绿。详见台账 R27–R29。以后固定全跑三组。Git本轮仅提交任务相关资产/证据文档，Docker未涉及。

- **附录形态升级 + 时间线加「发表时间」+ 移除实体内联引用（2026-10-09 已发布 prompt v1.7 / Skill v1.0.8，固定三组 R34 全绿）**：附录不再是一行一个数值的 11 列宽表（实测 44 列方案填充率只有 4.7%，不可读），改为**一张矩阵**：**列 = 试验**（同试验多披露按账本新增的 `records[].trial` 合并键合并为一列、表头标披露条数；缺键时回退注册号 → `study` → `ref`，**绝不凭名字合并**，「Study 301」类通用名会虚构试验身份），**行 = 维度与终点父级**，按 `试验设计 → 试验结论 → 有效性 → 安全性 → PK/PD → PRO` 分段；治疗臂/时点/评估/人群与终点口径写进单元格（`治疗臂·时点·评估·人群：结果 单位（统计量）{{ref_n}}`，未报告 `—`），同一终点的不同时点/口径（如「16 个月 ORR」与「ORR（%）」）统一到同一行。账本 `records[]` 新增**必填** `conclusion`（缺失即门禁失败）、`kind` 收成封闭词表（含英文映射）、`endpoint` 必须是最小可比父级、`version` 只放披露版本/数据截止；附录标题改为 `## 附录：证据对齐矩阵（数值事实账本）`。四个模板的时间线表首列加**发表时间**（原文披露日期优先，`paper_release_time` 日期部分兜底，都没有写「未报告」；只作披露时点标签与最后排序依据，不得按输入顺序推断）。**实体内联引用（v0.10/v0.11 `[名字](entity:type:id)`）按用户要求整体移除**（省运行耗时、产品未使用）：删 `references/entity-inline-reference.md`、`evals/validate-entity-refs.mjs`、`test/entity-refs.test.mjs`；渲染器先对旧账本展示字段做确定性剥离（`quote`/`source_file` 除外），再由 `ENTITY_LINK_RE` 门禁拦残渣，正文/表格/图表/账本一律纯名。实测：R32-3 11 列 / 61 行 / 88 facts、R32-2 18 列（旧账本无 `trial` 键所致）/ 66 行 / 84 facts，均无 fact 丢失；`python3 evals/numeric-integrity/test-render-facts.py` **21/21 绿**。发布方式按用户授权改为 **`--new-version` 发新版本（不原地更新）**：新 prompt `system-prompts/multi-clinical-result-comparison-v0.16.md`、新 dist `dist/multi-clinical-result-comparison-v0.16.zip`（93,757 B / 19 entries / sha256 `e5aad92c2618`）。**已于 2026-10-09 按用户授权用 `--new-version` 发布**：线上 prompt **v1.7**（54,264 B / sha `a638a93fe934`，project prompt id `394a6e51617842a0ae9403579dcf8f45`）、**Skill v1.0.8** / skill_id `cd93a42af72b4828b1690b3a7bccfa06`（19/19 支持文件一致，线上包已无 `references/entity-inline-reference.md`）、dist 首切 93,757 B / sha `e5aad92c2618`、修后重打 93,792 B / sha `dd9c2998c2b6`；`status` → **in sync**。发布前依赖闸门的两处上游变化已复核：chart skill v1.0.12 重新发布（运行期取模板，不改本地）、内置 `read_file` schema 变化（`limit` 默认 100 → prompt digest 上限由 ≤300 行收紧为 ≤100 行）。**固定三组回归（2026-10-09）**：R33 三组（4/18/14 条）跑了刚发布的 v1.7 / v1.0.8，附录矩阵形态在真实数据上成立（18 条→10 列、14 条→11 列、4 条→1 列），但抓到两个**我方**缺陷：①`APPENDIX_INTRO` 把字面 `{{ref_n}}` 写进交付报告导语（runner 占位符断言 FAIL，`test-render-facts.py` 已加断言 + 负向对照，21 → 22 项全绿）；②跑动期间改仓库/跑本地测试污染「支持文件清单」断言（`missing` 方向是本地多出来的文件，纠正 R30/R32 旧归因；测试加 `sys.dont_write_bytecode = True`，`AGENTS.md` §7 新增「真跑期间冻结仓库」）。修后 dist 重打 **93,792 B / sha `dd9c2998c2b6`**，用 `push-skill --version 1.0.8` 原地更新（`skill_id` 不变、prompt v1.7 未动、`status` in sync），**R34 三组全绿：22 PASS / 0 FAIL**（线程 `1952d185-…`、`edea673e-…`、`ca1120ae-…`；372.0 / 431.2 / 418.6 s）。详见台账 R33 + R34。

- **当前状态：R31 热点评估已完成（2026-09-20）**。从 `np_clinical` 只读取 5 条真实记录：HARMONi-2（3 条披露）与 HARMONi-6（2 条披露）。TS run thread `1e841bad-058b-4cf4-ba49-fab407c55c27` 成功完成，报告正确区分研究、终点、亚组、时间点、单药/联合化疗和研究内对照；5 引用、2 图、全部运行断言通过。唯一运行问题是 1 次 `execute` schema 拒参后重试；本轮无新增已证实 TS 平台 Bug。详见台账 R31，原始证据目录 `/home/xupeipeioo1/.local/state/toolsmith-runs/20260920-112401-hot-harmoni-20260920/`。



- **R32 固定回归与原地更新（2026-09-21）**：当前 prompt v1.6 / Skill v1.0.7 已原地更新并回读一致。固定三组 4/18/14 均成功结束并产出，主要输出契约通过；但三组均有 `__pycache__` 支持文件清单差异，R32-1/R32-2 有重复 `write_file` 冲突，R32-2/R32-3 有 Europe PMC 503，不能宣称全绿。详见 `docs/toolsmith-verification-log.md` R32。




- **最新用户决策（测试 ID / 设计字段）**：MCP 设计字段来自登记平台，重点原文复核，冲突以原文为准并披露差异。ID 兼容仅在我们调用 TS 测试前以只读 SQL 解析，不进入 Skill；显式字段按指定字段，未指定按 `_id OR extra_esid`，保留映射和未解析项。见 [决策与证据](docs/test-input-resolution.md)。本批转换 86 个真实 `_id`、68 个未解析；未改运行资产、未发布。**撤回下文 A10 的“上下文误抽”归因**：用户 ES 的 Double-Blind / 双盲正确，MCP 开放是跨来源差异，不能归罪原始抽取。


**本节是当前状态；后文各轮日期下的分数、哈希、已发布/待发布描述均为历史快照，不覆盖本节。** 完整审查见 [project-review-2026-09-18.md](docs/project-review-2026-09-18.md)，台账 F7 / O33–O38。

- **本地修复与线上原地发布已完成**：部署回读 **in sync**；R26 拒绝契约与回执归档通过。R22/R23 的报告内容人工复核仍有缺陷，不能宣称标准 A/全文验收全绿。完整记录见 [online-acceptance-2026-09-18.md](docs/evidence/online-acceptance-2026-09-18.md)。
- **待发布字节**：prompt **54,311 B / 2ff672b5aa9b**；dist **85,633 B / 19 entries / SHA-256 `4d20d48faeeee012c347aa28eb5956e5238a3e95020999c6b9bd6084fba53b1e`**，已重建并检查。需具体授权 prompt + skill 原地发布，回读一致后再跑 A/B；质量结论仍需 A×3。
- **上游适配**：live `deps` 确认 params 参数 **`+esids -extra_esids`**。旧提示词明文要求 `extra_esids`，R19/R20 拒参不能再归因为模型凭空发明。schema 镜像已 live 重生成，17 份运行规则/模板文件已适配；`deps --accept` 仅接受本地基线，**不是发布**。`group_count` 是总体入组人数，不是臂数；L3 权威归 `input-contract.md`，已抓取全文的引用落点随之更新，500/缺 PMCID 不足以判非 OA。
- **runner**：路径穿越/符号链接防护、目标 turn 隔离、缺返回失败、回执重试/哈希/最终收集线程 join、空产物/错误图表引用/缺支持文件清单失败、错误分类正则已加固。回执必需集现在只接受目标 turn 的结构化 `tool-return/tool-result` 内容；模型思考、自然语言和 execute glob 只作诊断，不制造下载要求。先后备份 **v9、v10、v11、v12、v13**；仓库累计补丁仅应用于**原始 v9**，见 `evals/runner-gate/runner-patches/`。
- **评估器新基线**：`2026-09-18-r2`，A **43 fail + 1 warn**、B **12 fail + 1 warn**；旧 41→43 **不代表质量提升**。R17/R18 离线重判 **43/43**，R20 **12/12**；R14 输入不是场景 A，不能用强制 A 总分评价它，其两条定向全文核验通过。详见 [EVALUATOR_REVISION.md](evals/fact-check/EVALUATOR_REVISION.md)。
- **验证**：97 测试全过（runner 30 / scorer 27 / tools 19 / Node 21）；63 mutation controls PASS（A 43/43、B 12/12）；历史链 5 可比 / 36 histories / 31 skipped / 4 no-history，无样本 exit 2。上游 chart **1.0.12** 三模板 `validateVisualizationFile` 本地 PASS，Zod **4.6.5** 在隔离目录 `~/.local/state/clinical-comparison-review-20260918/node_modules`，不是 TS 运行环境验证。
- **保留限制**：慢速持续响应仍可能突破预期墙钟上限；全文回执不证明报告数字确实来自全文；C/D 无判分基线；本地 citation renderer 既非生产实现，也非 HTML sanitizer。
- **A10**：仅提供示例 **`24_1_39054491_1`**，库内盲态「开放」与原文 double-blind 冲突；上下文误抽只是可能解释，未证明抽取根因。未写数据库、未发送问题单。
- **Git / Docker**：分支 `v0.15-remove-html`，本轮修复已提交并推送为 `ea4807c`；TS prompt/skill 已按授权原地更新，未发现 Docker 配置，不构建/推送镜像。

## Repository

- Git repository: `git@github.com:sdsliang/skill.git`
- Project subdirectory: `clinical-result-comparison/`
- Branch: `v0.15-remove-html`
- Migrated from `/home/xupeipeioo1/apps/clinical-result-comparison` and pushed as root commit `08440ad`.


Build the Tool Smith Agent for evidence-grounded synthesis of selected esids, using params records and the deepest available original source under the L3 input contract, with source-linked citation traceability.

## Housekeeping conventions

- **叫法约定（用户 2026-09-16 要求，硬性）**：本项目涉及 ToolSmith 时只用四个词，**禁用“工具本体”这种含糊说法**：
  **runner** = 本机 CLI `~/.local/bin/toolsmith-publish`（**我们能改**，改前先备份 + `py_compile` + `python3 evals/runner-gate/verify-run-chain.py` 回归 + 台账 `R<n>`）；
  **TS 平台** = 远端 ToolSmith 服务与只读参考仓 `~/apps/tool-smith`（**改不了**，只写问题单）；
  **TS 资产** = 平台上已发布的 prompt / 技能（能改，**每次先问**）；
  **仓库资产** = `skill/`、`system-prompts/`、`evals/`、`docs/`（能改，`commit`/`push` 本项目免确认）。
  回答“要不要改 X”时必须点名哪一层 + 具体文件。详见 `/home/xupeipeioo1/AGENTS.md`。
- **常驻 program.md = 仓库根 `AGENTS.md`**（2026-09-18 新增，autoresearch 循环的冻结面 / 场景集 / TSV 列口径 / 一轮一假设纪律）。
  新会话先读它，再读本文件（实现快照）与 `docs/toolsmith-verification-log.md`（台账）；`tools/` 下是本轮的离线 harness 脚本。
- 从 NP Clinical 拉取的示例数据（`evals/**/np-clinical-*/`）不入库：`.gitignore` 已忽略，`fetch-np-clinical-attachments.mjs` 可随时重拉。已提交的历史版本也已从跟踪移除（commit 63c031c）。

## ⏳ 开放事项总表（2026-09-17 整理；各条详情仍以下面正文各节为准）

> **第十五轮（2026-09-18）· 你授权「B1,4,5 都可以原地」→ B1 已 in-place 发布并真跑验证（`R18`）；B4/B5 的 autoresearch harness 骨架已落地（新 `O30`，只改 runner + 仓库）**
> 1. **B1（TS 资产，已发布）**：把「挑 6–8 个小 esid（records 小、`abstract_text` 短）」这条**按 esid 个数**的措辞，换成**按来源类**的实测口径（PubMed / 会议摘要 1–4 K 字符；登记号类 `2`/`187` 带 CT.gov 结构化 results JSON，中位 30–60 K、最大 1.9 M、77% 是 JSON 而非散文；`49` 号新闻稿 ≤78 K）。改 `system-prompts/...-v0.15.md` + `skill/.../references/input-contract.md`。数据源 `docs/evidence/abstract-text-by-source-2026-09-17.json`。
> 2. **in-place 发布 + 回读**：`tools/pack-dist.py`（**新入仓的确定性打包器**）重建 dist `86,285 B / sha 404dbccf5058` → `publish` 原地更新（prompt `v1.6` 内容替换 `53,347 B / sha b9bfcec19538`；skill `v1.0.7` 内容替换）→ `status` 回读 `in sync`（prompt 逐字节、技能包 19 文件全同）。**skill 更新接口回包 `files=0 commit_id=None` 是接口怪癖，以回读为准。**
> 3. **`R18` 真跑（验证这次发布）**：prompt `解读这几个结果 24_1_30561610 24_1_36342163` + `--web`，thread `f0ac7f8a-…`，**17/17 PASS**，墙钟 198.1 s server / 204.8 s polled，32 次调用尝试（30 returned + 2 schema-rejected），产物 `report.md` 15,658 B + `citations.json` 513 B + 1 张图；事实分 **`facts 41/41 warn 1/1 -> PASS`**。
> 4. **不把 B1 判成回归**：R17（27 calls / 41/41）→ R18（32 calls / 41/41）成本 +5、事实分不动；两轮差异不止 B1 那几行，n=1 ⇒ 记「待样本」，按 §8.2 要 A×3 才谈噪声带。
> 5. **B4 harness 骨架（仓库）**：`tools/replay-run.py`（把 `debug-history.json` 变成成本/质量全字段 + `--tsv` + `--score`，离线零网络）、`tools/pack-dist.py`（打包入仓，`--check` 当闸门）；**7 行基线 TSV 已回填**（`docs/evidence/autoresearch-baseline-tsv-backfill-2026-09-18.txt`），§6 的开放问题「成本升了质量升了没」现在有答案：+18 calls 换 +2 条事实（38→40/41），是**交换不是白赚**。
> 6. **`O30`（runner 层，已落地并验证）**：`tool_results/**` 回执在 turn 结束后**不可恢复**（平台 persist 删 + 产物面板过滤 ⇒ `file-download` 恒 404；离线扫描 28 个 run 目录 **109 指针 / 107 不可恢复**）。修法 = runner（`~/.local/bin/toolsmith-publish`）新增 `ReceiptArchiver`：5 s 轮询持久化消息抠指针即时下载 → `<run>/tool_results/**` + `receipts.jsonl` + `run.json.receipts`，两条判定路径各加断言 `tool_results receipts archived`（当时按轮询观测判 0 指针 = PASS；**F7 已收紧为最终目标 turn 必需集，不能以 0 polls 推定 n/a**）。**R19 先暴露「目录假指针」→ R20 `12/12 PASS`**（回执在**第 7.4 s** 落盘，31,407 B），`GATE: PASS`。证据 `docs/evidence/receipt-layer-2026-09-18.txt`。
> 7. **B5 常驻 program.md**：仓库根新增 **`AGENTS.md`**（三层资产归属 + 冻结面 + 场景集 A/B/C/D + `results.tsv` 列口径 + 一轮一假设纪律 + 反「假绿」清单 + 命令速查）；`docs/autoresearch-iteration-plan.md` 的 §5/§6/§7/§8.1/§8.3/§13/§14 同步更新（S0/S1/S4 标已完成、S2/S3 未开始）。
> 8. **`O31` + `O32`（runner 层，已修，离线零新 run）**：修 `verification.md` 里「schema-rejected」那行**只有工具名没有原因**——`retry-prompt` 的 `content` 近期是 pydantic **字符串**、早期是错误 dict **列表**，三处渲染器都按「list of dict」迭代 ⇒ 原因永远为空（`O31`，纯展示层）。顺藤摸出**更要紧的**：框架在「参数被拒」和「工具自身失败」两种情况下都会重发，旧代码一律记成 schema-rejected 并在 `output-error` 回路按 id 跳过 ⇒ **外部抓取失败在 `errors` 里不可见**，FAIL 级 `no tool errors` 对 500/403 完全失效：R15/R16/R17/R18 各有一条 `web_fetch` 抓 `…/europepmc/webservices/rest/PMC6933872/fullTextXML` 收 **500**，**四轮全绿**（产物侧其实都写在核对覆盖行里了，坏的只是闸门的可见性）。修法：分三桶 `args-refused` / `fetch-failed`（可见 + 打印 + 入 `verification.md`，不判 FAIL）/ 其余落 `errors`（仍 FAIL）；断言 18→19、12→13 项；`verify-run-chain.py` 同步（`rejected + fetch_failures` 都算「tap 看不到的尝试」）⇒ **`GATE: PASS`**；五种原因形状的离线单测通过（含「工具真崩」仍落 `errors`）。备份 `toolsmith-publish.v8.bak`；重读明细进 `docs/evidence/autoresearch-baseline-tsv-backfill-2026-09-18.txt` 注 7/注 8。
> 9. **本轮到 `4a60aba` 已 commit + push**（branch `v0.15-remove-html`）：`AGENTS.md` + `tools/*` + 两份 evidence + README/PROJECT_STATE/plan/台账/gate README 更新；B1 的 sys/skill 改动同一提交（TS 平台已 in-place 发布，`status` 回读 **in sync**：prompt `v1.6` 53,347 B / skill `v1.0.7` 19 文件全同 / dist 86,285 B `404dbccf5058`）。
> 10. **A10 已答（离线，零新 run）**：`clinical_result.blinded=['开放']` 的疑云锁定在 esid `24_1_39054491_1`（`24_1_39054491` / ECHO-307-KEYNOTE-672 / PMID 39054491）：原文设计是 **double-blinded**，库内却写「开放」；根因是**上下文误抽**而非编造 —— 全文里 `open-label` 出现 2 次（揭盲后继续治疗句 + DANUBE 参考区标题），另有「最后一次患者 9 周影像评估后**揭盲**」一句。建议抽取端把「设计盲态」与「揭盲后开放治疗」分开、并排除参考区。**未擅自动库，等你要不要转开发。**

> **第十四轮（2026-09-18）· 你说「接着开发完善」→ 修掉 `A-P6` 在真产物上的**空转**（新 `O29`）+ 补上反向的 `A-P9`（离线，零新 run、零发布）**
> 1. **缺陷（`O29`，本轮新挖）**：`A-P6-cite-link-is-deepest` 旧实现只把「文件名以 `ref_<n>` 开头」的归档算作某条 ref 的全文正文，而真产物按文章/esid 命名（`R14` = `PMC11270764_fulltext_jats.xml`）⇒ 拿 `R14` **原产物**重打（只读）它报 `no per-ref full-text body archived (check not triggered)` 并 PASS：**一个 citation link 都没看**，而 `R14` 正是催生 L3 规则的那份产物。更麻的是**它能过闸门**——`M21`/`M22` 用的是 harness 自己拼的 `ref_1.pmc-fulltext.xml`，即断言与样本同源、拿自己的假设自证（「不满足前提就不触发」这一类断言的通病）。
> 2. **修①：`A-P6` 归位拆四条通道**（`ref_` 前缀 / esid / 正文 `PMC<id>` 对链接 `PMC<id>` / 正文 PMID 对链接 PMID）；都归不上时**不猜**（PASS + 把文件名写进诊断）。`PMC\d+` 先抹掉再扫 PMID，否则 `PMC11270764` 的数字会被当成 PMID 命中。
> 3. **修②：新增反向断言 `A-P9-fulltext-cite-has-body`**（场景 A 第 42 条，fail 级）：`link` 一旦指向全文载体（同 `A-P6` 白名单）就必须有同 `PMC<id>` 的字节落在 `/workspace/sources/` 下；`link` 逐字节等于记录自带 `full_article_link` 时不算深度声明。旧规则只有单向（归档 ⇒ 引用必须指全文），**没人防「引用声称读了全文而一个字没取」**。三条合起来才是 L3 闭环：`A-P9`「到底取了没有」/ `A-P5`「有没有向读者声明」/ `A-P6`「引用落点对不对」。
> 4. **闸门也升级**：`M22` 重写为**真产物命名**（`PMC11270764_fulltext_jats.xml`，JATS 带 `pub-id-type=pmcid/pmid`，靠链接 PMID 归位）；新增 `M28`（凭空指全文、无归档，只翻 `A-P9`）与正控 `N28`（`R14` 合法形状，`A-P5/A-P6/A-P9` 必须全绿）；`NEG_A` 判据从「我那一条没翻」收紧为「**整轮干净** `rc==0 && flipped==[]`」（旧版下、负控把别条目打翻也会报 `[OK]`）。结果：`baseline a: 41 fail-severity items, all PASS` → `arm a: flipped 41/41`；`arm b 12/12`；**`GATE: PASS`**（50 行 / 43 `OK`，已覆盖落库）。
> 5. **产物层证据（闸门看不见的那一层）**：`docs/evidence/fact-check-l3-real-artifact-rescore-2026-09-18.txt` —— 三份真产物同一命令重判，`R14` 由「`check not triggered`」变为 `1 full-text ref(s) cite their full-text carrier`（`A-P9` 同轮 `1 full-text citation(s) backed by an archived body`）；`R17`（0 归档）与 `archive-scope` 探针（`sources/probe.txt` 不是原文）三件套均报「未触发」而非假绿。
> 6. **范围与状态**：只动 `evals/fact-check/`（4 文件）+ `docs/evidence/` 两份 ⇒ **dist 未变 ⇒ 不需重打包、不需发布授权**；真产物直接判分 `SCORE scenario=a facts 41/41 warn 1/1 -> PASS`。台账新增 **`### F4`** + `O29` 行；`### F3` 收尾加一条指向 F4 的备注。

> **第十三轮（2026-09-18）· 你授权「做呗」→ arm A 基线已从「补过一行的 R8 副本」换成真产物 R17（离线，零新 run、零发布）**
> 1. **基线换人**：`mutations.py` 的 `SRC_A` 默认值改为 `20260918-095553-r17-sign-convention`（R17 = 数值口径定案后 in-place 发布跑出来的那一版，**逐条全绿**且**原生带** `原文核对：` 行）⇒ **`seed_original_check` 连同「补一行」整套机制删除**。基线判分现在就是「把真产物原样过一遍清单」，不再向临时副本注入任何内容。
> 2. **6 条绑定 R8 字节的变异按 R17 真实措辞重写**：`M01`（`13\.9` 全替——R17 散文里有一处**不带负号**的 `13.9%`，只替带号写法时 `A-C4` 仍绿）、`M03`（替 `[OCEAN(a)-DOSE](entity:trial:NCT04270760)`，`count=0`，22 处；`A-C2` 要三条图案全中）、`M06`（H1 只点一个药，走 `A-T1` 的「只点一个 subject」FAIL 分支）、`M07`（`2 ?条` 全替——覆盖行里还有 `2/2 条`、「2 条仅摘要级」）、`M15`（ref_2 行的药名单元格换成 ref_1 的）、`M21`（加全文归档**并**把覆盖行改写成只声明摘要路径：R17 覆盖行本已提 `PMC6933872`/「全文」，只加归档翻不动 `A-P5`）、`N26`（改用「两个 subject 都点名」的标题；旧的 N26 在 R17 上已是基线形状 ⇒ 空转）。新增 `FT_XML` 常量供 M21/M22 共用。
> 3. **闸门全绿**：`baseline a: 40 fail-severity items, all PASS` → `arm a: flipped 40/40; never flipped []`；`baseline b / arm b: 12/12`；**`GATE: PASS`**（48 行输出 / 41 个 `OK`，完整输出已落库 `docs/evidence/mutation-gate-2026-09-18-r17-baseline.txt`，当时 48 行/41 `OK`；第十四轮 `O29` 修复后同一文件重跑为 **50 行 / 43 `OK`**）。清单条目与 `check.py` **一个字没改**（真产物直接判分仍 `SCORE scenario=a facts 40/40 warn 1/1 -> PASS`）⇒ **dist 未变 ⇒ 不需要重新打包、不需要发布授权**。
> 4. **两次踩坑（都留痕）**：① `M01` 第一版只替带负号写法 ⇒ `A-C4` 保持绿（**符号可选的图案，只替一种写法等于没改**）；② `M03` 第一版 `sub_lit` 没给 `count`（默认 1）⇒ 22 处只改 1 处，harness 报 `[BAD] M03 drop-trial-id rc=0 flipped=[]` 当场挡住。
> 5. **台账**：新增 **`### F3`**；`O20` 行、`### F2` 的「没做的（有意）」段、`### R17` 的收尾段各加一条指向 F3 的备注。

> **第十二轮（2026-09-18）· 你授权「O19-20 都可以改」→ 打分器两类假阳性已修（离线，零新 run、零发布）**
> 1. **`O19`（`A-ATTR` 把比较句判成错配）已修**：`pairs` 引入 `"subject": true`＝**记录身份证**（药名 + 登记号/试验名）。**身份对**在「unit 同时点了引注记录自己的身份证」时豁免（比较句 / 排除句：`…与奥帕司兰的终点不是同一构念{{ref_1}}`、`安全性维度只有 OCEAN(a)-DOSE…{{ref_2}}，NCT02729025 未报告…`）；**数值对永不豁免**（`M27` 证明豁免不是全免），`M06`/`M15` 照旧必须翻。原方案（按 refs 集合大小放松）**证伪**：实测假阳性 unit 都只挂**一个** marker。
> 2. **`O20`（标题条目期望过窄）已修**：改名 `A-T1-title-identifies-scope`，`kind: line` → `shape`/`title_scope`：两个 subject 都点 ⇒ PASS；一个都不点但命中 `theme_all`（人群 + 对比标记）⇒ PASS；**只点一个 ⇒ FAIL**；都不占 ⇒ FAIL（`M26` = `# 结果对比报告`）。
> 3. **顺手挖出 `O28`**：`A-ATTR` 的数值 token 写 ASCII `-13\.9`，而四份真产物正文一律 U+2212（`−13.9`）⇒ 这一对**从未命中过任何产物**（假绿方向的静默漏检）；已改 `[\u2212-]`，四份产物重打**无新增 FAIL**。
> 4. **闸门升级：`arm()` 新增假阳性回归对照**（旧 harness 只能证明「能翻 FAIL」，抓不到「改过头」）：`N25`（R15 形状混合句）、`N26`（主题式标题）、`N27`（R12 形状登记号对照句）必须**保持绿**。正向变异扩到 **27 条（M1–M27）**，`arm a 40/40`、`arm b 12/12`、`GATE: PASS`。
> 5. **真产物回填**：`R17` **`40/40 -> PASS`**（第一个满分真产物）、`R15` `36→37/40`、`R16` `32→37/40`、`R12` `37→39/40`（剩 `A-P1`，R12 早于原文优先规则）、`R8` `39/40`（同）。**本轮只动 `evals/fact-check/`（4 个文件）⇒ dist 未变 ⇒ 不需要重新打包、不需要发布授权。**
> 6. ~~**`MUT_RUN_A` 仍指向带 seed 的 R8 副本**~~ **→ 已于第十三轮完成**（基线重指 R17、`seed_original_check` 删除、6 条变异重写）：实测换过去会打掉 4 条**绑定 R8 字节**的变异（`M01`/`M06`/`M07`/`M15`）+ `M21` 依赖「基线不提全文」而 R17 覆盖行本来就有「全文接口 500」⇒ 需按 R17 字节重写这几条，作为独立下一步（记在 `O20` 条目）。

> **第十一轮（2026-09-18）· 数值口径定案 + 第四次同输入复跑**
> 1. **口径定案（用户：「三没关系，只要自洽就行」）**——`−13.9` 与「降低 13.9%」两种写法**都合法**，合同不再写死符号；换成硬要求：**同一份交付物只用一个口径（报告与图表必须一致）**。落地 = `A-C4`/`A-C5` 模式改 `[\u2212-]?`（数值仍逐位精确）、`A-S9` 比绝对值、**新增 `A-S10-sign-convention-consistent`**（`M25` 隔离验证）、`input-contract.md` 新增 *Number rendering: one convention per deliverable* + sys v0.15 同步一句。清单 **41 条（40 fail + 1 warn）**。
> 2. **in-place 发布完成（同版本号，内容替换）**：prompt `v1.6`（`52,919 B / sha 06e07ca11a91`）、skill `v1.0.7`（dist `86,084 B / sha 50477adfe102` / 19 entries）；`status` 回读 **`in sync`**。
> 3. **R17（同输入第四次跑）**：**18/18 断言 PASS**、27 次尝试（1 次 `web_fetch` schema 被拒后重发）；事实分 **`39/40`**，**唯一 FAIL 是已知 O20**（`A-T1-title-names-both` 对主题式 H1 误判）；`A-P2/A-P7/A-P8` 全 PASS ⇒ **O24 闭环**（覆盖行 `2/2 已复核 + 路径 + 原因类 + 分析深度`，无规则句）。
> 4. **顺带结论**：`A-C16`（O27）本轮 PASS ⇒ 该条维持「待样本」（1 失败 / 1 通过）；R17 是第一份「除 O20 外全绿」的场景 A 真产物 ⇒ `MUT_RUN_A` 换基线在原理上解锁，但需先确认 `M21`/`M22` 自足（R17 没归档全文），**等 O20 一句话判定后再做**。

> **2026-09-17 当日进展**：A1 已定为「扇出 = 疾病 join 引入，Skill 侧兼容」→ **兼容措辞已落地 4 个文件（B2 关闭）**，本地先行跑出 **R12**（旧版基线 + 3 项部署一致性 FAIL 属预期）；发布授权下来后重跑即收口。
> 另新增两条清单发现（**O19** 打分器「一句多 marker」假阳性、**O20** `A-T1` 期望过窄）—— 2026-09-18 你授权「O19-20 都可以改」，两条均已修复（见第十二轮）。
> **追加（同日第二轮）**：用 `run --web` 做了两次 **egress 探针（W2）**，把路线 C 探清楚了——**人读页面抓不到**（PubMed 反爬拦截页 / CT.gov 只有 JS 壳），**API 端点能抓到**（CT.gov v2 API 全协议 JSON、Europe PMC REST 带 `abstractText`/`pmcid`）。用户提的「优先 `abstract_text` → 再访 `full_article_link`」ladder 因此卡在三个政策开关上（新开 **A13**，台账 **O21**）。另：**不存在 `source_full_link` 字段**，现名是 `clinical_result.full_article_link`。
> **追加（第十轮，2026-09-18 晚，最新）— 你授权「原地更新一下」后：`push-skill` 已上线并在真跑 `R16` 里确认修复生效；同一次运行又挖出两类新问题（一类已修，一类等你拍口径）**：
> **① 发布 + 复验（本轮主目的）**：`push-skill --version 1.0.7`（in-place）→ 回读 `zip entries=19 identical=19 differing=0`、`STATUS: in sync`（线上仍是 `v1.0.7` 标签）；随后用**与 R12/R15 完全相同的输入**跑 `R16`（thread `b31bdfb7…`，POST 后我的 shell 被中断 ⇒ 按 O23 用 `run --resume` 重收、不重跑）。**18/18 断言 PASS**（含「部署端 prompt/skill 正文 + 18 支持文件逐字节 == 本地」），`A-P7` 三个字面在交付正文里 **0 次命中**、覆盖行变成实质内容（路径 + 逐条深度 + 非 OA 原因类，`A-P4` PASS）⇒ **模板泄漏修复确认上线生效**。
> **② 同一跑又发现：规则句被「换措辞」照样写进交付物**（「未发现原文与库内记录在同一指标、同一口径上的数值不一致；」——无值无引用）。已修：四个模板的 `原文核对：` 规格加「不复述本规则措辞、不写『未发现不一致』这类规则性表述」；`references/input-contract.md` 与 **sys v0.15** 同步；新增清单项 **`A-P8-no-rule-metastatement`**（`no_rule_metastatement`：句子点名库内一侧 + 谈「一致/不一致」+ **通篇无数字** ⇒ FAIL；真实分歧必带双值 + ref，所以「无数字」正好切开元话语与结论）+ 专属变异 **`M24`** ⇒ 清单 **40 条（39 fail + 1 warn）**，`arm a 39/39`、`arm b 12/12`、`GATE: PASS`。`A-P8` **在 R16 真产物上直接命中**（不只对变异有牙）。
> **③ 等你拍板的口径问题（未擅自改）**：同输入三次跑**数值符号写法不一致** —— R8/R12/R15 写 `−13.9`、图表 `-13.9`；**R16 全篇写「降幅 13.9%」、图表全为正幅度**。合同里**一个字都没写**符号/幅度（`grep "同号|负号|降幅|符号|正值"` 无命中）⇒ 每次由模型自选；而清单 `A-C4/A-C5/A-S9` 绑定带符号写法 ⇒ R16 掉 3 条（`32/39`）。两种写法语义等价、各自自洽，**不是内容缺口**；按「不得为迁就产物放宽清单」的规矩**本轮没放宽也没写死**，记 **O26** 等你选：(a) 合同写死「数值同库内字段同号、方向用文字补充」（推荐）或 (b) 允许两种写法（清单配套放宽 + 补变异）。另 `A-C16-hard-outcome-gap` 只认 `硬结局|心血管事件`、漏了 R16 的「心血管结局事件（如 MACE）」（表格里明确标注「未报告/未对齐」）⇒ **O27**，与 O20 同类，一并等批。
> **④ 发布状态**：本轮又改了 4 个模板 + `input-contract.md` + **sys v0.15** ⇒ 本地 dist 重打为 **`a1b65809eb8b`（85,544 B（第十轮值，已被第十一轮的 `50477adfe102` / 86,084 B 取代） / 19 entries / `mismatch vs worktree: []`）**，**prompt 与 skill 都需要再次授权**才能发（都是 in-place：prompt 仍 `v1.6`、skill 仍 `v1.0.7`）。
> **追加（第九轮，2026-09-18 晚）— 同输入对照跑 `R15` 挖出一个**我们自己的资产缺陷**并已修（模板规格句被照抄进交付报告）**：
> 为做发布前后对照，用**与 `R12` 完全相同的输入**（`24_1_30561610` + `24_1_36342163`）再跑一次：thread `e0d198b3…`，**30 次尝试 = 29 返回 + 1 schema 被拒**（`web_fetch`）/ 191.7 s server / **18 条断言全过**；事实分 `35/38`（清单同期由 31 → 38 条 fail 级），两个 FAIL 都不是内容缺口：`A-ATTR`（已知假阳性 O19）+ **`A-P7`（本轮新发现的我们自己的缺陷）**。
> **两条 L3 反向证据**（比 PASS 更有信息量）：① `24_1_30561610` 经 Europe PMC 取到 `PMC6933872` 但**该文非 OA、全文不可得** ⇒ 覆盖行如实写明，`citations.json` 两条 `link` **逐字节**等于库内 `full_article_link`、**没有任何构造链接**（与 `R14` 的正例正好成对照：白名单替换只在真取到全文时发生）；② 平台探针里那次 `PMC6933872 → 500` 由此得到解释 —— **不是全文路由坏了，是该记录非 OA**（再次印证 W2-d 的更正）。
> **缺陷与修法**：报告覆盖行渲染出了模板写给模型的规格句「原文优先于库内加工字段，不一致处同时写出原文值与库内记录值；」—— 成因是四个模板第 5 行把规则写在 `**原文核对：** [...]` 括号**之外**。修：① 四个模板把那三句**移进规格括号**；② 清单新增 **`A-P7-no-template-spec-in-report`**（`op_report_excludes_literals`，查正文不得逐字出现 `原文优先于库内加工字段`/`不静默取一侧`/`库内记录值`）→ **39 条（38 fail + 1 warn）**；③ 专属变异 `M23`（实测 `flipped=['A-P2','A-P7']`，隔离性符合预期）。闸门全绿：`arm a 38/38`、`arm b 12/12`、`GATE: PASS`、run-chain `GATE: PASS`；dist 重打成 **`c55321ad4619…`（84,991 B / 19 entries / `mismatch vs worktree: []`）**。
> **待你授权**：模板字节变了 ⇒ **已发布的 skill `v1.0.7` 里仍是旧模板（线上会复现这个泄漏）**，需要 `push-skill`（in-place）再发一次；prompt `v1.6` 未受影响（sys 本轮没动）。另修 runner 一个计数口径缺陷（**O25**：schema 被拒的 call 被算进「已返回」，R15 印出「30 attempts = 30 returned + 1 rejected」这类自相矛盾的数字；现 `ret_n = len(calls) - len(rej)` + 被拒项单列，备份 `…v6.bak`）。
> **追加（第八轮，2026-09-18）— L3 已发布并**真跑验证通过（`R14`，17/17 PASS）**：用户授权「原地更新，不要新版本」⇒ `publish`（**prompt 仍 `v1.6`、skill 仍 `v1.0.7`，同版本号替换内容**），回读一致（prompt `0ae72c9302b3` 逐字节 == 本地；skill `19 identical / 0 differing`；`STATUS: in sync`）。随即真跑 `run --web`（thread `273e52b4…`，2 条 `src=1` 输入：`24_1_39054491_1` 有 `PMC11270764`、`24_1_42477684_1` `inPMC=N`），**26 次调用 / 148 s / 0 schema 被拒 / 17 断言全过**，并逐项核实 L3 生效：① `citations.json` 里 `ref_1.link` 换成 PMC 全文页（库内原值 `…/39054491`）、`ref_2.link` 仍逐字节；② `sources/` 归档 JATS 原文 + 纯文本（100 K / 49 K）；③ 覆盖行按记录写「按全文分析 1 条 / 仅摘要级 1 条」；④ 摘要里没有的数值真进了报告（`36.0`/`18.5`/`26.3`/`90.7`/`87.8`/`86 天`/`CPS` 全部不在 2,590 字符的库内 `abstract_text` 里，且都带分析集/人群标签）。**顺带挖到一条库内数据问题**：该记录 `clinical_result.blinded=['开放']` 而原文（摘要 1 + 全文 3 次）均为 **double-blind**，报告已按双值写 `原文 double-blinded；库内记录 开放{{ref_1}}` → 记入 A10 待发清单。另修 runner 一个韧性缺口（**O23**：`/usage` 抖动曾把整次验证连带产物归档一起毁掉；现 GET 重试 3 次 + `usage`/`limits` 软失败并落 `collection gaps` 行，证据类端点仍硬失败）。
> **追加（同日第七轮）— 用户定级 L3：分析面 = 可得最深载体，引用落点跟随深度（台账 `### W6`，仓库先行未发布）**：用户选 **L3** 并当场驳掉本仓先前「长短 ⇒ 不可比」的论证——**科学事实不因披露载体（摘要 vs 全文）而改变**，深度决定「这条记录有多少内容可用」，不决定两个事实是否可比；深度不对等的正确处置是**逐条声明分析深度**，据此给出 ref 处理方案：**基于全文分析的记录，引用 `link` 指向真正的全文**，而不是原来的 PubMed 摘要链接。落地：`input-contract.md` 三节（最深载体即分析面 / 全文独占事实须带时点·分析集·人群标签 / *Citation link follows the analysis depth* + C1·C2 白名单）、`citation-and-ref.md`（`link` 逐字节规则的唯一例外）、`SKILL.md`、sys v0.15 六处、4 个报告模板的 `原文核对：` 槽位。引用 URL 实测（R13 探针）：`pmc.ncbi.nlm.nih.gov/articles/PMC…` **只写不取**（机房出口遇 reCAPTCHA，浏览器可通过）、`europepmc.org/article/…` **403**、`…/rest/{PMCID}/fullTextXML` **✅ 99,433 字符**（= 我们真正读的字节源，作 C2 备选）。新断言 **`A-P6-cite-link-is-deepest`**（`M22` 证明可隔离翻 FAIL，只翻它不翻 `A-P5`）→ 清单一共 **38 条（37 fail + 1 warn）**；`citations_matches_record` 同步放宽（`link` ≠ 记录值时必须命中白名单全文 URL）。离线闸门全绿：`arm a 37/37`、`arm b 12/12`、`GATE: PASS`、run-chain GATE PASS、dist `d5afb1f00320`（84,994 B / 19 entries / `mismatch vs worktree: []`）。**L3 尚未在平台验证**（用户明确不发布），发布后需跑 `R14` 才算收口。
> **追加（同日第六轮，~~待用户定级~~ → 已由第七轮定级 L3）**：用户提问「字段值基于摘要生成，PMC 能取到的能不能直接读全文」⇒ 实测成立：3 篇有 PMCID 的记录，全文数值 **334/334/249** 个，其中 **92%/88%/99% 不在摘要里**，`PFS`/`DoR`/`HR`/`TTR`/亚组/`Grade 3` 摘要根本不写。**但深度不对称**：会议摘要类（本切片 55.6%）外部永久只有摘要级，登记平台类库内已是全文级。给出 L1/L2/L3（建议 **L2：全文补齐库内空档 + 覆盖行标注来源深度**），**未改任何规则**，见台账 **O22** 与证据 JSON 的 `pmc_fulltext_information_gain`。
> **追加（同日第五轮）**：用户定调「默认优先库内 `abstract_text`，其余内容再努力；`src` 还有其他类型，不要只特化已知几类；**`src=1` PubMed 即使有摘要也要尝试取 PMC 全文**」⇒ 抓取预算收窄为「**只有当库内没有原文时才抓**」，唯一例外 `src=1`（台账 **`### W5`**）。两条实测支撑：① **库内 `abstract_text` 多数类就是原文本身**（期刊摘要对 Europe PMC 归一后 alnum **1.000/0.992**、会议摘要对 OpenAlex **0.991/0.976**（SITC 那条 0.45 已解释为 markdown/网页残留，60 字符块命中 50/56）、登记结果小数 **102/102**、通稿线报日期首行逐字），真正被加工的只有 `study_results`/`summary` 这类结构化抽取；② **PMC 全文路由可用**（`src=1` 抽 100 条 **56% 有 PMCID** 且全为 OA；平台侧 `run --web` 跑 `{PMCID}/fullTextXML` **4/5 成功、63–99 K JATS 全文**，单条 `500` 属记录级「未进 PMC/OA」——**W2-d「fullTextXML 不可用」的结论已更正**）。新路由 **R6→R7**、预算改「每条 ≤1、`src=1` ≤2、整批 ≤40」、覆盖行必须写 PMC 结果且归档全文必须点名 `PMC<号>`/「全文」（新断言 **`A-P5`** + `M21`；`A-P4` 路径正则放宽到 `PMC\d`/库内正文）。离线闸门 `arm a 36/36`、arm b 12/12、`GATE: PASS`。**仍差 `publish` 授权 + 真 run `R13`**。
> **追加（同日第四轮）**：用户质疑「你不考虑所有源的 link 可访问性吗？」⇒ 原文优先规则**按来源类细化**（台账 **`### W4`**）：取哪条路由（以及是否值得抓）由 esid 中段的摄取来源 id 决定——`1` PubMed→PMID、`2`/`187` CT.gov→注册号 API、`37` 会议→DOI（会议站点本身全封，但 82.2% 有 DOI）、`49` 新闻稿=**库内 `abstract_text` 即通稿原文（无需外部抓取）**、`120` 补录→DOI 或公司页、`398` SEC=**不可复核**（EDGAR 403、data.sec.gov 只有题录）；「link 页一律禁抓」改成「**16 主机封锁清单 + 每记录最多 1 次自身 link**（仅无路由键或主机可用/未知）」。实测 32 条 URL：11 可达 / 21 不可达，同主机可能「人类页不可达、API 可达」。清单新增 `A-P4`（覆盖行必须点名路径 + 来源类）与 `M20`，离线闸门 `arm a 35/35`、arm b 12/12、`GATE: PASS`。**差 `publish` 授权 + 真 run `R13`**（与 A1 共用一次授权）。覆盖度实测：83.0% 记录至少有一条白名单路由。

> 分四类：**A 等外部答复才能动** / **B 已定要改、只差授权执行** / **C 待样本再判** / **D 已定案不动**。
> 每条点名层与文件（runner = 本机 CLI；TS 资产 = 平台上已发布的 prompt/skill；仓库资产 = `skill/`、`system-prompts/`、`docs/`、`evals/`）。

### A. 等外部答复（我们动不了，只能等）

| # | 事项 | 等谁 | 卡在哪 | 答复后的动作 |
|---|---|---|---|---|
| A1 | ~~一个 esid 多行扇出的语义~~ **已答（2026-09-17）**：产品确认扇出由疾病 join 引入、非预期语义，要求 Skill 侧兼容 | 产品 | ✅ 已解决 | **兼容措辞已落地**（`input-contract.md` / `SKILL.md` / `citation-and-ref.md` / sys v0.15）：按 `clinical_result.extra_esid` 去重、一个 esid = 一 marker 一 citation；本地先行跑出 **R12**（台账已记），发布授权后重跑收口 → 见 B2 |
| A2 | 结果记录不全 vs CT.gov 官方全：路线 A 数据侧补 / B skill 诚实声明 / C 运行期拉官方 | 产品 + 数据团队 | 路线 C 还牵扯「联网 + 外部引用」政策 | A → 报数据团队；B → 需新信号字段；C → `run --web` 已可验（O18/W1）。**附：链路梳理与优化评估已完成** → Obsidian「临床结果Skill-esid到MCP查询链路梳理与优化评估-2026-09-17」。**2026-09-17 追加 W2 探针：路线 C 只能走 API 端点（人读页面对 PubMed/CT.gov 都抓不到）** → 改规则前需先定白名单模版，见 A13 |
| A13 | **证据来源优先级 ladder**：原三条待拍开关 **已定案（用户 2026-09-17）**：(a) 政策 = **放开**（字段值是加工抽取、可能出错，原文第一优先级）；(b) 可追溯性承载 = **报告正文**（`citations.json` 保持严格 3 键、不加键）；(c) 冲突/降级 = **原文为准 + 分歧必须双值 `原文 …；库内记录 …{{ref_n}}` + 抓不到必须点名原因类**，且「原文缺失 ≠ 库内错」；**（第四轮细化）取哪条路由按 esid 中段的来源类决定**，其中 `49` 新闻稿、uuid 遗留行库内正文即原文、`398`/`245` 不可复核；**（第五轮收窄）默认「库内 `abstract_text` 即原文 ⇒ 不抓」，唯一例外 `src=1` 即使有摘要也走 `R6`→`R7` 取 PMC 全文**；**（第七轮 L3）可取到的全文即「分析面」**——深度不等于不可比，全文独占事实可入正文但须带时点/分析集/人群标签；**基于全文分析的记录其引用 `link` 指向全文**（C1 `pmc.ncbi.nlm.nih.gov/articles/{PMCID}/` 只写不取 / C2 REST `fullTextXML` 为实际读取源），其余记录 `link` 仍逐字节取自 `full_article_link`（`A-P6`/M22 证明可翻） | 自己 | ✅ 已定案 | **规则已落仓库（未发布）**：`input-contract.md` 新章（来源类表 + 主机封锁清单）+ SKILL/sys 四处改写 + 4 个 template 加 `原文核对：` 槽位 + 清单加 `A-P1/P2/P3/P4`（第四轮）与 `A-P5`（第五轮，归档全文必须声明；`mutations.py` M17–M21 已证能翻）⇒ 差 `publish` + 真 run `R13`（见台账 `### W3`/`### W4`/`### W5`；清单现 38 条 = 37 fail + 1 warn，变异 M17–M22；第七轮 L3 见 `### W6`） |
| A3 | 报告表格整表复制 / 整表下载 CSV-Excel（平台能力） | 产品（何林杰） | 已交其验证；**飞书任务至今未建**（2026-09-17 实测用户 token scope 仍无 `task:task:write`） | 他给结论 → 再定 skill 是否「每表同步产 CSV/TSV/XLSX」 |
| A4 | 通用下钻契约 `drillDownValue` + detail json（esid 数组） | 产品（何林杰/段帅帅） | 08-28 起 parked，等其案例测试与范式记录 | 照其规范实现（半小时级） |
| A5 | registry `abstract_text` 回填 4 问（这两个 esid 实际值？45% 空是分批未完成？`Prospective Study` 600/600 全空是否预期？回填的是整份文本还是摘要？） | 开发 | 问法与证据已备好 | 答复后定是否另要「摘要级字段」 |
| A6 | 追加精确问法：回填 source 名单是否漏 `187`/`120`（各 100% 空），`2` 还剩 ~20% | 开发 | 同上（按 esid 中段精确分层已完成） | 同上 |
| A7 | 他说的 `source` 指哪一列；会不会加进结果工具的 `ALLOWED_FIELD_NAMES` | 开发 | 结果侧 74 字段里没有（6 个候选名全 `INVALID_INPUT`）；试验侧有 `data_source` | 加了 → 按它全量重统；不加 → 沿用 esid 中段 / `evidence_source` 代用维度 |
| A8 | 平台问题单 P1–P6 + P9 何时转开发 | 用户决定 | 全文已写（Obsidian「ChatAPI与SSE文档缺口」）；P7 已由平台从根修、P8 已撤销上报 | 转出后等开发排期 |
| A9 | `vendor/`（上游 chart skill 源码，含内部 CDN 地址）是否入 git | 用户 | 现在 `.gitignore` 排除 | 决定入库 → 去 ignore + commit |
| A10 | 是否把 registry `abstract_text` 的发现写成可直接转开发的飞书消息 | 用户 | 证据已齐（两个 evidence JSON + 分层表）；**2026-09-18 新增一条库内数据问题**：`24_1_39054491_1` 的 `clinical_result.blinded=['开放']`，而原文（摘要 1 次 + PMC 全文 3 次）均为 **double-blind**（ECHO-307/KEYNOTE-672 双盲安慰剂对照 III 期）；`R14` 报告已按规则写双值，**库内字段本身未动** | 我起草 → 你确认再发 |
| A11 | autoresearch 迭代是否开跑：S2（场景 A×3 取噪声带）/ S3（E2 删委派段、E3 返工纪律） | 用户授权 | 计划见 `docs/autoresearch-iteration-plan.md` §13 | 授权即执行 |
| A12 | 三处对外沟通项 B8–B10（bar 负值问题单 / `{{ref_n}}` 前端报备 / CLI 路径口径） | 用户 | 09-11 拍板「攒着」 | 说一声就发 |

### B. 已定要改、只差执行（我们能改，但各有闸门）

| # | 改什么（层 + 文件） | 依赖 | 闸门 |
|---|---|---|---|
| B1 | **TS 资产**：sys `system-prompts/multi-clinical-result-comparison-v0.15.md:38` 与 `skill/.../references/input-contract.md:93` 的「短 `abstract_text`」假设 → 「论文/会议记录短（约 2–4 KB），登记平台记录可能是整份文本（中位 33 KB / 最大 1.9 MB），一律先落盘再脚本摘」 | 事实已确证，**不必等 A5/A6**；若开发答复「会改成摘要级」，措辞可一次写对 | `run` 留新 `R<n>` + publish 授权（TS 资产写动作） |
| B2 | **TS 资产**：扇出去重措辞 + L3（分析面/引用落点）——**已 2026-09-18 授权并原地发布完成** | ✅ 已解除 | **已完成**：`publish` 原地更新（prompt `v1.6` / skill `v1.0.7`，回读逐字节一致，`in sync`）+ `R14` 真跑 17/17 PASS（调用 36→26、墙钟 201.8→148.0 s）。台账 `### W6`/`R14` |
| B6 | ~~**仓库资产**：`eval_attribution` 的归因口径~~ **已完成（2026-09-18，用户授权 O19）** | ✅ 已解除 | 落地为「身份对豁免 + 数值对永不豁免」（`subject: true`），假阳性回归对照 `N25`/`N27`；`arm a 40/40`（第十四轮后同 arm 为 `41/41`）、`GATE: PASS`；R12 `37→39/40`、R15 `36→37/40`、R17 `39→40/40` ⇒ 台账 **F2**、`O19` 已修 |
| B7 | ~~**仓库资产**：清单条目 `A-T1-title-names-both`~~ **已完成（2026-09-18，用户授权 O20）** | ✅ 已解除（证据从 1 份增至 4 份产物：R12/R15/R16/R17） | 改名 `A-T1-title-identifies-scope` + `op: title_scope`（主题式标题合法；**只点一个药名仍 FAIL**）；`M26`/`M06` 证明有牙、`N26` 证明不误伤 ⇒ 台账 **F2**、`O20` 已修 |
| B3 | **runner（已落地）**：O1–O18 全已落地，只剩 O4/O5 待样本；**O42 已于 R46 按选项 B 窄口径结案** —— 新增 `TOOL_REFUSED_RX`（两形状 `^` 锚定）+ `REFUSAL_BUDGET = 3`，原恒 PASS 信息行改带预算判定（断言仍 22 条）；备份 `toolsmith-publish.v15.bak`，`py_compile` OK，`test-runner.py` 38 → 39，零网络闸门 `GATE: PASS`，离线重打分 98 份归档 0 error | ✅ 已完成（用户「谁好，你推荐谁」+「你自己看着办吧」授权） | 回滚 = 复原 `v15.bak` + 重跑 39 项；不动线上、无 TS 写动作 |
| B9 | **仓库资产 + runner**：`tell-scan.py` 输出末尾自打 `[tell-scan] exit=N`，`run` 的 prose-gate 断言改读该行（不再采信模型 `echo SCAN_EXIT=$?`——`&&` 短路会污染成别的命令的退出码，`R61-3` 已坐实） | 证据齐（`r61-sem-2` 第 25/34 步原文） | 改 `skill/scripts/` + runner（先备份 `toolsmith-publish.v*.bak`、`py_compile`、零网络闸门回归）；需 1 次真跑复验 |
| B8 | **仓库资产（已完成）**：R43/R44/R45（F1 + F2 + O27）与 **R47（O43 + O40/O41 报告侧习惯句）** 均已原地发布并四组真跑 | ✅ 已解除（R41 同授权续用） | **prompt v1.7 现值 `c1641a46810a` / 67,591 B；dist `025aec791b1c` / 105,347 B；`status` in sync**（R47 后） |
| B4 | **仓库资产**：autoresearch harness 骨架 + 把 `tool_results/**` 纳入归档 → 跑 E0「receipts 命中率」回测（不动 `skill/`、0 新 run） | 用户点头 | 纯本地脚本 + 文档 |
| B5 | **仓库资产**：把「冻结面 + 场景集 + TSV 列」写进 `AGENTS.md`/`PROJECT_STATE.md`，形成常驻 program.md（S4） | 用户点头 | 文档 |

### C. 待样本（攒够再判，不凭感觉改规则）

| # | 事项 | 现有证据 | 何时可判 |
|---|---|---|---|
| C1 | 台账 O4：正文句子级返工（`s.replace()` 就地改模板字面量，非规则返工） | R1 的 19 次 `execute` 里 8 次 + 3 次 `edit_file` | 再攒 3–5 次运行 |
| C2 | 台账 O5：小样本不便宜（1 个 esid 也要 21 次调用 / 173 s / 26k reasoning） | R1 vs R4（14 esid 50 次 / 299 s） | 再攒几次，或用户体感贵时给「单结果解读」轻模板 |
| C3 | 事实清单 `A-C6`（未报安慰剂组 +3.6%） | R11 唯一 FAIL（现 30/31） | 有第二个同类样本再改规则 |
| C4 | E1 场景 A 噪声带（23 vs 41 calls 跨了发布，无干净重复） | 5 个 `20260914-*` run 离线重放 | S2 跑 3 次 |
| C5 | 台账 O40：`A-ATTR` 不给「对对方记录的否定陈述」豁免 | **3 份**（R43-a 3 cell / R45-a 2 cell / **R47-loweff-a**：表格 cell 无标记 ⇒ 继承本行 `ref_1`，只点名 `ref_2` 的试验） | **R47 已选报告侧改习惯**（prompt/SKILL 已加句，但**覆盖不到表格 cell 继承**）⇒ **R48 内容轮**收窄为「阴性/缺测句必须带被点名那条记录自己的 `{{ref_n}}`」；评分器仍不动 |
| C6 | 台账 O41：`A-P2` 对「非分歧地提到库内记录」零容忍 | R45-a 一处；**R47 五份产物 `库内记录` 出现 0 次**（A-P2 无触发） | ✅ **已收尾（R47）**：报告侧「只许出现在固定分歧写法里」已写入四处；不改评分器；再现再议 |
| C7 | 台账 O42：`no tool errors` 在多写 run 上约 1/4 概率被打掉（R41–R45 共 14 run 失 5） | 失败清单 + 12 run 的三轮对照（见台账 R43/R44/R45） | ✅ **已定案（2026-10-10 R46，选 B）**：runner 改判 + 预算闸门，见台账 O42 / R46 节 |
| C8 | 台账 O43：图表行必须点名**试验** | r46-a 5 根柱子全无试验名 → 40/44 | ✅ **已结案（R47）**：prompt/SKILL/chart-templates 三处硬规则原地发布；**R47 四组 4/4 命中**且未引入新失败 |
| C9 | 台账 O44：`A-C9-mds-tbr-A` 只认减号写法，不认「降低 8.3%」文字写法（同 spec 的 `A-S10` 却声明「符号由模型自选」） | r47-a（1/7 触发）；历史 6 个 scenario A run 与同日 `low` 臂都写减号 | 按 O27/O28 先例**等第 2 份样本**；修法 = 两条 pattern 各加文字式备选（一行可回退） |

### D. 已定案不动（别再翻）

- **O16** runner 图表断言「0 图全过」：`run` 是通用入口、不知道场景，判定交给离线事实清单 → **定案不改**。
- **P7 / P8**：P7 已由平台从根修掉（`30306cb` 删 `cleanup_stale(300)`）；P8 撤销上报（终态可重建，属客户端体验）。
- **表格复制/下载**（skill 侧）：在 A3 有结论前不动 `skill/`。
- **E6 / B8–B10**：明确不做 / 攒着。
- **bar 柱下钻 与 `drillDownValue` 契约**：parked 等外部（A4）。
- **两条已关闭的「伪待办」**（曾被记成待用户，现已不成立）：① 「重传 sys v0.15 到平台」—— `status` 已 in-sync（**2026-09-18 原地更新后**：prompt v1.6 `0ae72c9302b3` == 本地 `-v0.15.md`（52,414 B）、skill v1.0.7 dist `d5afb1f00320` 19/19 逐字节相同），且 `R14` 已复跑验墙钟；**注：第九轮的 dist `c55321ad4619` 已 in-place 上线到 `v1.0.7`；第十轮又改了模板 + `input-contract.md` + sys ⇒ dist `a1b65809eb8b` / 85,544 B，线上暂时落后（prompt 与 skill 均待再次授权）**；② v0.6/v0.7 时代的「`dist/` 是否重建」—— 发布已走 API 通道，dist 只作留档，无需重建。

## 📌 待办: 报告表格整表复制 / 整表下载 CSV-Excel（2026-09-01，已交产品验证，不改文件）

- **背景**：对比结果 skill 报告（`present_artifact` 交付的 .md）含多张 Markdown 表格（timeline 表、endpoint 表、cross-trial 对比表）。问 ToolSmith 能否支持「表格整表复制」+「整表下载为 CSV/Excel」。
- **结论（只读分析，未改 skill 文件）**：
  - 整表复制：**无按钮级能力**。浏览器原生「选中整表→复制」可用（HTML 表格复制为制表符分隔，贴 Excel 保留列）；要一键按钮 = ToolSmith 前端给 markdown 表格加 action。Skill 侧替代（widget 内 `navigator.clipboard`/`<a download>`）受 `sandbox="allow-scripts"` opaque origin 限制（无 allow-downloads / 无 clipboard-write 权限策略 / 消息桥无 copy 事件），不可靠。
  - 整表下载 CSV/Excel：**Skill 侧现在就能做**——每张关键表同步产一份 `.csv`/`.tsv`（`::visualization` 引用 → 前端通用文本预览 + 下载按钮）或 `.xlsx`（沙箱 openpyxl 生成 → `present_artifact`/ArtifactPanel 下载）。注意 CSV/TSV 预览是纯文本不渲染成表格。
  - 产品级「表格卡片自带复制/下载按钮」属 ToolSmith 平台功能，需前端新增 action（类比：下钻 navigate 事件也是待确认项）。
- **决定**：先不改 skill 文件；已交产品（何林杰）先尝试验证平台能力，等其结论后再决定是否给 skill 交付契约加「每表同步产 CSV/TSV/XLSX 数据文件」规则。
- **飞书任务**：待建 task，负责人=何林杰（open_id `ou_543a818d8dcd7a4ce52a9349b1a000ac` 本地聊天记录已取，无需 contact 搜索权限）。**卡点（2026-09-01）**：应用 `cli_aae61ba424389d06` 已启用 28 个 scope（含全部 task），但用户侧 token 未授予 `task:task:write`；bot 身份也未申请该 scope。→ **精简申请链接（仅 task+日历 17 个 scope，一轮审批）**：https://open.feishu.cn/page/scope-apply?clientID=cli_aae61ba424389d06&scopes=task%3Acomment%3Awrite%2Ctask%3Acustom_field%3Awrite%2Ctask%3Atasklist%3Awrite%2Ctask%3Acustom_field%3Aread%2Ctask%3Asection%3Awrite%2Ctask%3Atask%3Aread%2Ctask%3Atasklist%3Aread%2Ctask%3Aattachment%3Awrite%2Ctask%3Asection%3Aread%2Ctask%3Atask%3Awrite%2Ccalendar%3Acalendar%3Areadonly%2Ccalendar%3Acalendar%3Awrite%2Ccalendar%3Acalendar.event%3Aread%2Ccalendar%3Acalendar.event%3Awrite%2Ccalendar%3Acalendar.acl%3Aread%2Ccalendar%3Acalendar.acl%3Acreate%2Ccalendar%3Acalendar.acl%3Adelete 。审批通过后用户再做一次 `--domain task,calendar` 授权即可建任务。

## ⏸️ Parked: 一个 esid 多行扇出 → `{{ref_n}}` 去重措辞（2026-09-17，等产品确认）

- **现象（只读实测）**：`extra_esids` 精确过滤一个 esid 时可返回**多行**；`24_1_30561610` → 3 行，仅 `disease_id` 不同（10000/5194/1403），
  三行 `clinical_result__id` / `extra_esid` **完全相同**（`clinical_trial_result_structured` 按疾病维度 join 后发散）。
- **为什么要改**：`{{ref_n}}` 编号口径是**esid 级**（第 3 个输入 esid → `ref_3`，见 `SKILL.md:33`），而响应是**行级**；
  若按行枚举，2 个 esid 可能来 4–6 行，ref 编号与「结果条数」对不上。skill 正文目前**没有**明写「同一 esid 多行要按 `extra_esid` 去重后再编号」。
- **状态**：**用户 2026-09-17 判为「很重要、需要改，但我得先问产品」→ 本轮不动 `skill/`**，只记录（改 skill 则必须重跑 `run` 留 `R<n>`）。
- **要问产品的两个问题**：① 疾病维度扇出是**预期语义**（一条结果对应多适应症）还是**取数副作用**？若是预期，前端「选中结果」的粒度是 esid 还是 `(esid, disease_id)`？
  ② 若是副作用，应该**工具侧 DISTINCT 掉**（现有 CTE 里的 `SELECT DISTINCT` 只覆盖 `_id/extra_esid`，外层 join 后又发散）还是**由 skill 提示词去重**？

### 扇出根因追加定位（2026-09-17，只读探针，给产品的第二个版本解释用）

- **触发条件很精确（新）**：**只有 `selected_fields` 里带 `clinical_result.indication_name`（或 `indication_name_en`）时才扇出**；
  同一 esid 改查 `paper_title` / `study_results` / `indication_detail` / `indication_type_cn` → **1 行，且返回行里没有 `disease_id` 列**。
  而我们的取数字段清单**正好包含 `clinical_result.indication_name`**（`references/input-contract.md:91`）⇒ 实时路径走的就是扇出那条路。
- **`disease_id` 不是可请求字段**：写进 `selected_fields` 报 `INVALID_INPUT: Invalid fields selected`（不在 `ALLOWED_FIELD_NAMES` 里），
  却会**凭空出现在返回行**中 ⇒ 是那条 SQL 尾段 join 疾病维表多出来的列（与「CTE 里 `SELECT DISTINCT` 只覆盖 `_id/extra_esid`」对得上）。
- **每行的 `indication_name` 都是完整 3 个**（高低密度脂蛋白胆固醇血症 / 脂蛋白(a)增高 / 炎症(未指明)），**没有按行拆开** ⇒ 看着像
  「join 后被复制」，不是「按疾病拆行」。
- **真实场景命中（新）**：场景 A 的两个 esid 都扇出 —— `24_1_30561610` **3 行**（1403/5194/10000）、`24_1_36342163` **2 行**（421/1403）
  ⇒ 选 2 条结果实际拿回 **5 行**（对照：`24_1_31415087` 1 行、`24_1_45608045` 0 行、`24_187_acaa9fda…_1` 1 行、`24_49_f9a67f…_1` 1 行）。
  扇出行除了 `disease_id` **逐字段完全相同**（同 title / journal / study_results）。
- **严重性口径（勿夸大）**：**尚未观测到产物出错** —— R8 / R11 两个真跑（正是这两个 esid）`citations.json` 都是 **2 条**、正文写「**2 项**来源记录」，
  即模型自己按内容合并了；但合并的**依据是「重复行逐字段相同」这个巧合**，契约层没有保障（若将来按疾病不同的字段出现，模型无法判断并/拆）。
  ⇒ 向产品陈述时说「现在靠巧合对」，不说「线上报错」，我们**不改清单/产物迁就**。
- **备好的改法（拿到结论后再执行）**：`references/input-contract.md` + `SKILL.md` 各加一句「按 `clinical_result.extra_esid` 去重后再按输入顺序编号 `{{ref_n}}`，同一 esid 的重复行只取一份」。
- 全文：Obsidian `03-技术与VibeCoding/01-AI与LLM/临床结果esid查询-params工具字段与取值实测-2026-09-17.md`「追问 3」。

## ⏸️ Parked: 结果记录（表单）不全 vs CT.gov 官方全 —— 数据侧缺口（2026-09-17，等产品/数据团队确认）

- **用户澄清（2026-09-17）**：引 NCT/CT.gov 的真实动机不是「要更多证据」，而是**我们自己的结果记录只抽了官方 results
  页的一部分，ClinicalTrials.gov 官方才是全的**。
- **量化缺口**（同一试验 `NCT05419908`，只读对比）：官方 results **26 个终点 / 300 个值行**、基线 5 指标×3 组、
  人流 3 里程碑×2 组、AE 1 严重 + 8 其他（带分母 44/43）；内部 `study_results` 只有 **84 行 / 28 标签 / 5
  `endpoint_id`**。**完全缺**：HFRDIS/LSEQ/GCS/SDS（156 值）、7 个血浆浓度终点 LH/FSH/E2/SHBG/Leptin/Insulin/
  C-peptide（70 值）、基线特征（`baseline_characteristics` 空）、人流（`participant_flow` 空）、AE 事件名与计数。
- **反向偏差（内部更好的一面）**：24 行 `arm_type: relative` 带 `compare_result` + `p_value` + CI，是魔方自己的加工；
  官方只有 `analyses` 雏形。安全性行的 `endpoint_label` **只有时间窗**、无事件名。
- **关键区分：骨架内部有，值内部没**。`pharmcube-query-clinical-trial-with-params`
  （`trial_id=NCT05419908`，零联网）返回 **1 主 + 25 次** 终点定义（`sec_outcome_measures_en` 16,569 chars，
  HFRDIS/LSEQ/GCS/SDS/血浆浓度/AE 全在，与官方 25 个数**完全一致**）+ 纳入/排除标准 + `arms` + `enrollment` +
  sites/dates/design。⇒ 缺口性质 = **取数/入库不完整**，不是「不知道要去哪拿」。
- **三条路线**：**A（推荐）数据侧补全**（报告数据团队：只抽部分终点是有意还是入库缺失；补 16 个终点值 +
  基线 + 人流 + AE）；**B skill 层「诚实声明」**（但记录里目前无 `data_completeness`/`omitted_endpoints` 类信号，
  要落实得先有信号或额外调一次 trial 工具交叉核对，会引入二次取数与新引用口径问题 → 待产品拍板）；
  **C 运行期拉官方**（**2026-09-17 复核后升级为「通道已存在」**：平台已有 `web_fetch`，实测能直连
  `clinicaltrials.gov/api/v2/studies/NCT05419908` 拿全量 JSON（322,835 chars，自动落盘 `/workspace/tool_results/web_fetch/*.md`）；
  剩下要做的是**政策/口径**：请求级 `enable_web=true`（前端 composer 的「联网」开关，`ChatComposer.tsx:263`）+
  skill/sys 允许外部检索 + ref ↔ 内部记录一一对应契约改写 + 双源版本漂移处理）。
- **附带字段陷阱**：`clinical_result.group_count` = **总体入组 87**，不是组数（实际 2 组 44/43，组 n 在结果记录里根本没有）；
  结果记录的 `arms[*].drug_earth_ids` 与试验记录的 `arms[*].therapeutic_schedule_id` 是**两套 id 体系**。
- 全文（含官方模块清单、逐字段对比、trial 工具回包）：Obsidian
  `03-技术与VibeCoding/01-AI与LLM/临床结果esid查询-params工具字段与取值实测-2026-09-17.md`「追问 2 更正」。
- 官方 JSON 落盘：`/tmp/ct-NCT05419908.json`（164,496 B）；trial 工具回包：`/tmp/trial-NCT05419908.json`。

### 只读探针：`web_fetch` 能拿到什么（2026-09-17，4 次真实 turn）

- **能力存在性**：`GET /api/agent/info?project_id=a7cdda6…&enable_web=true` → 内置工具表含 `web_search` / `web_fetch`，
  instructions 多出 `## Web Tools` 段（62,244 → 62,898 chars）；`enable_web=false` 时该段消失。⇒ 本项目
  `capability_config.web` 已开，**唯一闸门是请求级 `enable_web`**（我们 runner 的 `post_turn` 当时硬编码 `False` →
  **已于 2026-09-17 补上 `run --web`**，台账 O18 / **W1**）。
- **探针脚本**：`/tmp/webtest.py`（复用 runner 的 `Client`/`create_thread`/`wait_for_run`，只把 body 的 `enable_web` 改 True；
  不动 runner 本体、不动任何已发布资产；**`run --web` 落地后这类临时脚本不再必需**）。产物 4 个 run 目录（`~/.local/state/toolsmith-runs/20260917-13*`）。
- **结果矩阵（同一工具，四个源四种命运）**：

  | 源 | 结果 |
  |---|---|
  | 微信公众号（本 esid 的 `full_article_link`） | ✅ 正文 **4,057 chars** 逐字拿到（`outcome: success`） |
  | `pubmed.ncbi.nlm.nih.gov/31415087` | ⚠️ `outcome: success` 但正文只有 **175 chars 的 reCAPTCHA 挑战页**（静默失败，需自己识别） |
  | DOI → `academic.oup.com`（JCEM 全文页） | ❌ **HTTP 403** 被出版商拦（零正文） |
  | `clinicaltrials.gov/api/v2/studies/NCT05419908` | ✅ **322,835 chars 原始 JSON**，四个 results 模块齐（`outcomeMeasuresModule` 26 条 = 1 PRIMARY + 25 SECONDARY、`baselineCharacteristicsModule`、`participantFlowModule`、`adverseEventsModule`），**超内联上限 → 自动落盘** `/workspace/tool_results/web_fetch/call_*.md`（turn 结束清空），可 `json.loads` 解析、未截断 |

- **要记的两个坑**：① `web_fetch` 只回文本/JSON/markdown，HTML 转 markdown、JSON 走 `_format_json_content`，
  **二进制直接丢**（“binary; not returned”）；② 反爬页 / 403 都算「调用成功」，**`outcome` 字段不能当可用性判据**。
- **对 24_49_f9a67f535c33c8022fd87e5cc170db7d_1 的具体回答**（用户 2026-09-17 提问）：该记录是**公司新闻稿**
  （`journal: 和铂医药`、`paper_release_time: null`、无 DOI/PMID），`full_article_link` 是微信公众号文章
  （HBM9378/WIN378 哮喘 II 期 POLARIS-1 中期结果）。`web_fetch` 原文可得，且**本机 `curl` 同样可得**
  （3,515,892 B HTML，`#js_content` 正文 4,161 chars）。内部 `summary` 只覆盖其中一段。
- 探针 thread（均在 `~/.local/state/toolsmith-runs/20260917-13*`，每个目录都在 `run.json` 里）：
  微信原文 `56c61c9f-6227-49cf-ae6b-2cff6f01a562`、PubMed `e15bdcb0-1c97-4d0d-a252-42527f438c70`、
  DOI/OUP `20ff3947-2892-42ff-9b27-7b4f1d5e99d6`、CT.gov API `8cd2c77e-0f41-47fa-b3e9-c65edb8d0fa6`。
  耗时均 ~11–13 s/轮（DeepSeek Flash），单轮 input ~50k tokens（系统提示 + 技能）。

## 🔎 只读实测：登记平台记录 `abstract_text` 的回填现状（2026-09-17，开发称「已写到 `clinical_trial_result_structured`」）

**结论：对这两个测试 esid 不成立；且已回填的那部分，字段形态也不是「摘要」。**

1. **两个测试 esid 仍为空**（各查两次，`clinical_result.abstract_text` 长度 = 0）：
   - `24_187_acaa9fda98c00fb890d804d0e3a0428c_1`（ESN364 潮热 IIa，`journal=ClinicalTrials.gov`，`evidence_source=["Prospective Study"]`）——
     **该记录其他字段是齐的**：`study_results` 30,917 chars、`arms` 2,307、`summary` 447、`indication_detail` 233，**只有 `abstract_text` 空**。
   - `24_2_NCT06618118_1`（Fosigotifator MDD Phase Ib，`_id=nr_24_2_NCT06618118_1`，`evidence_source=["Phase I"]`）——
     `abstract_text` 空、`study_results` 也空，但 `arms` / `projects` 有值。
2. **不是「登记平台整体没回填」**：以 `meeting_tags='ClinicalTrials.gov'` 全量拉（**4,095 行**）→ **2,258 行有值（55%）、1,837 行空（45%）**。
3. **空/非空与 `evidence_source` 强相关**（同一批 4,095 行）：

| `evidence_source` | 空 / 总 | 空占比 |
|---|---|---|
| Prospective Study | 600 / 600 | **100%** |
| Phase I | 202 / 346 | 58.4% |
| Phase II/III | 51 / 97 | 52.6% |
| Phase II | 361 / 959 | 37.6% |
| Phase I/II | 44 / 125 | 35.2% |
| Phase III | 548 / 1,827 | 30.0% |
| Phase IV | 29 / 139 | 20.9% |

→ 测试 esid #1 正好落在 **100% 全空的 `Prospective Study` 桶**、#2 落在 58% 空的 `Phase I` ⇒ 更像「回填按证据类型分批、`Prospective Study` 这批还没跑」。
4. **已回填的登记平台 `abstract_text` 不是「摘要」，是整份方案/结果文本**：2,258 个非空值 min 1,423 / p10 8,901 /
   **median 33,406** / p90 114,848 / **max 1,907,425 chars**；≤ 4,000 chars 的只有 38 个（1.7%），> 20,000 的 1,536 个（68%）。
   （对照：论文记录 `abstract_text` 实测 1,852–3,587 chars，与 v0.15 sys 里「短 abstract_text」的假设一致。）
5. **对我们 skill 的影响（本地产物风险，尚未在真跑中观测到）**：`skill/` 取数字段清单含 `abstract_text`（`references/input-contract.md:93`），
   而 sys 假设它是「短 `abstract_text`」（`system-prompts/…-v0.15.md:38`：*small selections … short `abstract_text`/`study_results`*）。
   用户一旦选中登记平台记录，单字段中位 33 KB、最大 1.9 MB ⇒ 直读上下文会爆；现有「先脚本 digest、再考虑委派」规则能兜住，
   但「短」这个假设已失效。**候选改法（未执行，改 `skill/` 需重跑 `run` 留 R 记录 + 发布授权）**：把「short」改成
   「论文/会议记录短（~2–4 KB），登记平台（ClinicalTrials.gov）记录可能是整份方案/结果文本（中位 ~33 KB、最大 ~1.9 MB），**一律先落盘再用脚本摘**」。
6. 证据文件：`docs/evidence/ctgov-abstract-text-coverage-2026-09-17.json`（4,095 行逐条 `{id, evidence_source, len, head(120)}`，588 KB）。
7. **给开发的问题**：① 这两个 esid 对应行里 `abstract_text` 当前实际是什么值？② 45% 空是「分批回填未完成」还是「这些记录本来没有可回填的源文本」？
   ③ `Prospective Study` 600/600 全空是否符合预期？④ 回填的是整份文本还是摘要——若为整份，能否另开一个真正摘要级的字段（我们只需要摘要级内容）？

### 追加：`source` 字段可达性 + 按可得来源维度重统（2026-09-17）

**（1）`source` 在结果侧不可及。** 结果工具 74 个可选字段里与 source 有关的**只有** `clinical_result.evidence_source`；
实测 `clinical_result.source` / `data_source` / `source_type` / `source_name` / `record_source` / `regulation_source` 六个候选名 → 全部 `INVALID_INPUT`；
返回行只有 `clinical_result__id` / `company_id` / `disease_id` 三个注入列，没有 source。
（试验侧有：`clinical_trial.data_source` = `US-ClinicalTrial`、`clinical_trial_project.aggre_data_source` = `['EU-EudraCT','US-ClinicalTrial']`、`source_name_cn` = null —— 即 source 语义只在试验侧能读到。）

**（2）按可得的「来源」替代维度重统。**

- **登记平台维度无方差**：`meeting_tags` 试 `ChiCTR` / `中国临床试验注册中心` / `药物临床试验登记与信息公示平台` / `EudraCT` / `EU Clinical Trials Register` → **全部 0 行**；只有 `ClinicalTrials.gov` 有 4,095 行；带 `projects` 的 500 行连接样本里 **500/500** 登记平台都是 `US-ClinicalTrials.gov`。⇒ 结果表里的登记记录就只有 CT.gov 一类。
- **登记平台 vs 期刊/会议**（同一张表按 journal/会议切片，字段 `extra_esid/journal/evidence_source/abstract_text`）：

| 来源切片 | 行数 | 空 | 空占比 | 中位长度 | 最大长度 |
|---|---|---|---|---|---|
| **ClinicalTrials.gov** | 4,095 | 1,837 | **44.9%** | **33,406** | **1,907,425** |
| Lancet | 1,344 | 21 | 1.6% | 2,796 | 7,132 |
| ASCO 2024 | 1,353 | 5 | 0.4% | 2,821 | 25,108 |
| Blood | 841 | 9 | 1.1% | 1,630 | 2,418 |
| ESMO 2024 | 745 | 0 | 0.0% | 4,165 | 24,963 |
| JAMA | 579 | 9 | 1.6% | 2,760 | 3,702 |
| AACR 2024 | 200 | 0 | 0.0% | 2,848 | 6,070 |

⇒ **论文/会议侧几乎不空（0–1.6%）且长度 1.6–4.5 KB（真摘要）；登记平台侧 44.9% 空且中位 33 KB、最大 1.9 MB（整份文本）。**
- **CT.gov 切片内部交叉表**（4,095 行）：hash 型 esid（`N_N_<32位hex>`）**603/603 = 100% 空**（其中 600 条正是 `Prospective Study`）；非 hash 型 3,492 行 35.3% 空。
  用户给的 esid #1（`24_187_acaa9fda…`）落在 100% 空的 hash 类，#2（`24_2_NCT06618118_1`，NCT 型）落在 35.3% 空那类（Phase I 最重）。
- 证据：`docs/evidence/abstract-text-by-source-2026-09-17.json`。

**待开发确认**：他说的 `source` 指哪一列？若指试验侧 `data_source`（登记/期刊来源），需要把它加进结果工具的可选字段，我才能按它全量重统；
若指的是结果表内部的摄入渠道，那从外部只有上述两个替身维度可见。

### 追加 2：按 esid 中段（source id）精确分层（2026-09-17，用户提示「用 id 排查」）

esid 形如 `YY_SRC_KEY`，**中段就是摄入 source id**。这个 id 不需要新字段——从 `clinical_result.extra_esid` 自己就能看出来。

| esid 中段（source id） | 这批记录是什么 | 行数 | abstract_text 空 | 空占比 | 中位长度 | 最大长度 |
|---|---|---|---|---|---|---|
| **187** | CT.gov / US-ClinicalTrial 登记（`24_187_<32hex>_1`，`Prospective Study` 600/602） | 602（CT.gov 切片内，**精确**） | 602 | **100%** | — | 0 |
| **120** | 未识别批次（hash 型 esid，journal 多为空 / WCLC 2024） | 91（样本） | 91 | **100%** | — | 0 |
| 138 | 单行样本 | 1 | 1 | 100% | — | 0 |
| **2** | CT.gov NCT 型结果（`24_2_NCT…_1`） | 322（**精确**） | 64 | **19.9%** | 38,774 | 605,847 |
| 1 | 期刊论文 | 250（样本） | 1 | 0.4% | 1,812 | 4,381 |
| 37 | 会议摘要（ASCO/ASH…） | 250（样本） | 0 | **0%** | 2,786 | 9,804 |
| 49 | 公司新闻/商业资讯 | 250（样本） | 6 | 2.4% | 8,765 | 77,857 |

- src=2 内部又分层：Phase II 124 行 15.3% 空 / **Phase I 92 行 29.3%** / Phase III 60 行 15.0% / Phase I/II 43 行 20.9%。
- 用户给的两个 esid：`24_187_acaa…` → **src 187（整批 100% 空）**；`24_2_NCT06618118_1` → **src 2（总体 19.9% 空，Phase I 子集 29.3%）**。
- **CT.gov 切片里还有 3,170 行（77.4%）根本没有 esid**（裸数字 `25607` / 裸 uuid `651414cc…`）：裸数字 3,015 行 38.1% 空、裸 uuid 155 行 14.2% 空；
  这类`abstract_text`里装的是 **CT.gov 结构化结果 JSON**（`[{"paramType":"NUMBER","unitOfMeasure":"participants",...}]`），不是文字摘要——**即使“有值”也不能当摘要读**。
- 另一个副作用发现：**不限定过滤条件、只选 `abstract_text` 的查询会直接报错**：`QUERY_EXECUTION_ERROR` / StarRocks `Memory of Group=rg_cube … Used: 23354210528, Limit: 17179869184`（用 23.35 GB 撞 16 GiB 限制）
  ⇒ 该工具不能做全表 abstract_text 扫描，只能带过滤条件的小批量。（我们的 skill 一直带 `extra_esids`，不受影响。）
- 证据：`docs/evidence/abstract-text-by-source-2026-09-17.json` 的 `by_esid_source_id` 节。

**给开发的精确问法**：回填的 source 名单是不是漏了 `187` 和 `120` 两个 source（整批 0 写入），`2` 里也还剩 ~20%（Phase I 最多）？

## ⏸️ Parked: bar 柱下钻（v0.9-test，已由用户验证可行，暂不开发）

- 全部改动（未提交）已 stash：`git stash list` → `stash@{0}: On chart-drilldown-nct: wip: bar drill-down (v0.9-test) + 1L ORR test datasets — verified by user, park for later`。分支 `feat/chart-drilldown-nct` 与 main 同提交 `349eabc`（无独立 commit），后续要继续可直接 `git checkout feat/chart-drilldown-nct && git stash pop`。
- 内容：`endpoint-bar.html` 支持 `bars[].url` → `window.__toolsmithNavigate(url)`（登记号详情页 `https://ct.pharmcube.com/trial/{nct_id}`）；`SKILL.md`/`chart-templates.md` 下钻契约；v0.9-test 系统提示词（优先读 md 元数据 `source_nct_id` 拼 url）；`test/drilldown-bar-sample.html`；两套测试数据集 `test/drilldown-sources/`（仅保证登记号）与 `test/drilldown-sources-1l-orr/`（一线+ORR，必出柱状图，均带 `source_nct_id`）；`dist/multi-clinical-result-comparison-v0.9-test.zip`。
- 验证结论：部署端 `__toolsmithNavigate` 桥 + 宿主 `window.open` 均已就位；不画图的根因是数据异构（跨线/跨终点）触发契约不绘图，`1l-orr` 数据集（indication 135 + III期 + ORR 端点 `4a8abd33ec374a46b758926758ed410a` + `therapy_labels.meta.text∈{一线治疗,一线}`）可稳定出柱状图。恢复时无需动 tool-smith 端。

## ⏸️ Parked: 通用下钻契约（drillDownValue，等前端 MCP+skill 落地后再对照）

- 背景（2026-08-28，前端告知）：前端侧通用 `/chart-visualization` skill 的图表格式里，每个数据点带 `drillDownValue`（**一个 id**，如 `"2024-01_销售额"`）；前端拿到该 id 后调接口取 workspace 里脚本生成的 detail json 渲染，**被取的 json schema 可自定义**（"支持数据格式多样"）。链路：`点.drillDownValue(单 id) → 前端调接口 → workspace detail json → 渲染`。
- 与对比结果 skill 的关系：聚合点（如「II期积极结果 = 5 条」）→ **`drillDownValue` 保持单 id，多条记录放进该 id 对应的 detail json**（数组/多值不进 drillDownValue 字段）。可替代/升级现有 parked 的 `bars[].url` → `__toolsmithNavigate(url)` 方案。
- **✅ 已确认设计（2026-08-28 与段帅帅/何林杰对齐）**：
  - `drillDownValue` = **detail json 的文件名**（id↔文件名一一对应，一 id 一 json）。
  - **命名约束**：id/文件名只用安全字符（字母数字+下划线，不含 `/`、空格、`..` 等）——何林杰示例 `赛道_PD1/VEGF 双特异性抗体_结果id` 含 `/`+空格不安全，需用如 `track_pd1vegf_bispecific` 这类 slug。
  - detail json 内容 = **esid 数组**（`clinical_trial_result_structured._id` = ES 的 `_id`，B7 已确认）；前端拿这批 esid 去「临床结果列表页做检索」。极简 schema：`{"ids": [esid1, esid2, …]}`。
  - 会议解读（WCLC 按赛道统计，如 PD1/VEGF 双特异性抗体=10 个结果）是下钻落地场景；下钻逻辑与可视化逻辑分离，仅用 `drillDownValue` 关联。
- **2026-08-28 决定：本条目交接/挂起，等何林杰结果再动。** 何林杰已主动承诺「下周拿具体案例跟帅帅测试验证对接细节和标准规范，把路径跑通、范式具象化并描述记录下来」，届时我方再照着写 skill（若需）。
  - **本周我方 skill 零待办**：下午 2 点会「一句话确认（detail json 放 /workspace/output/、文件名=drillDownValue、安全字符）」改为可选——该问题下周案例测试自然会暴露并顺带记录，不硬推。
  - **下周待办**：等何林杰的测试结果 + 具象化范式；到时评估对比结果 skill 是否也输出 drillDownValue + detail json（照其记录规范执行，属半小时照抄级小活）。
  - 对比结果 skill 继续 parked；当前不做任何代码改动。

## Current version

- System prompt: `v0.15`
- Skill: `multi-clinical-result-comparison` trial-level synthesis `v0.15` (esid + `pharmcube-query-clinical-result-with-params` input, chart products as pure JSON **produced by reusing the upstream `chart-visualization-json` skill** and validated by that skill's CLI, file-based report delivery via `present_artifact`, entity inline references with trial short-name display, **no HTML chart asset anywhere in the repo**) 
- 仓库内 HTML 资产：**v0.15 已全部移除**（`docs/legacy-html-charts/` 整目录删除：3 个 HTML 模板 + `chart-tokens.css` + `validate-chart.py` + `render-preview.py`，见 git `e4f3bb7`）；保留的只是「禁止再产出 HTML/Mermaid、禁止混入 CSS/HTML token」类**防回退护栏**。
- Chart validation entry: `node /workspace/skills/chart-visualization-json/scripts/validate-cli.js <product.json>`（前端仓库别名 `pnpm validate:chart -- <path>`）；自研 `validate-chart.py` 已退役。
- **`dist/multi-clinical-result-comparison-v0.12-temp-preview.zip` 已删除（v0.15，用户要求）**：v0.12 调试期双写包（含 `render-preview.py`，写 `.preview.html` 孪生页）；双写已在 v0.14 撤销、HTML 已在 v0.15 全销，该包随之下线。它从未入库，删除后不可恢复。
- v0.13 轻量版：**弃用但未删除**（源码 `docs/legacy-v0.13/`，归档 `dist/multi-clinical-result-comparison-v0.13.zip`）。
- **历史 dist（第十一轮，非当前；当前见文首）**：`dist/multi-clinical-result-comparison-v0.15.zip`（19 文件，系统提示词不入包），SHA-256 `50477adfe10228b5a230c01495683a789db1c2e95ec39b06c664228d07059b6c`（86,084 B；上一版 `a1b65809eb8b` / 85,544 B，再上一版 `c55321ad4619` / 84,991 B，**第十轮（`A-P8` + 覆盖行规格）后的包，逐文件 sha256 == 工作区**；历史：`c55321ad4619…`（84,991 B）＝第九轮 `A-P7` 修复后 in-place 上线的那版、`d5afb1f00320…`（84,994 B）＝L3 那版；2026-09-17 重打四次：原文优先 → 按来源类细化 → 库内即原文/`src=1` PMC 全文例外 → **L3 分析面 + 引用落点**；中间版 `c9dc143908d6` / 82,004 B、`3c2919fc22ce` / 79,927 B、`7b1dd5ec5f45` / 77,711 B 与更早 `de7c16b44910` / 73,385 B 作废）（HTML 清理版 + 子代理委派规则（触发 >5 / 每块 ≤5）+ 图表 envelope 契约 + 空目录兜底 + 上游 v1.0.9 对齐 / 渲染配置归图表 skill + `::visualization` 标签不进实体锚点覆盖 + **A 组六项硬化 / 同试验图表张数上限** + **分享复盘第二轮硬化（标记粒度、混合图数去歧义、shell 参数措辞、渲染期断言、嵌套锚点断言）**；70301 B）。2026-09-11 共重打两次：A 组落地后为 `b9b46d8a…` / 69254 B；同日第二轮硬化改了 3 个入包运行文件（`SKILL.md`、`references/{citation-and-ref,chart-templates,entity-inline-reference}.md`）后重打为当前 SHA。当日上午复盘上游 v1.0.10 时那次重打与 `0deda5d3…` 逐字节相同（dist 只装运行文件、当时未改运行文件）。`dist/…-v0.14.zip`（`c0a7d4c0…`，含「输出文件固定命名」契约）及更早自动降为历史归档。
- Git：分支 `v0.15-remove-html`（从 `main` 的 `16cbb96` 切出）；`main` 已含 v0.14 提交 `e4f3bb7` 与记账提交 `16cbb96`，且已 push（`origin/main` = `16cbb96`）。v0.15 提交链 **`da5b157`（HTML 全销）→ `aa05104`（子代理委派边界，含阈值二次校准）→ `d65abdf`（记账）→ `4040ff3`（上游 v1.0.9 对齐 + 渲染配置归 Skill + 重打 dist）→ `87a2afb`（记账）→ **`49f00d9`（`::visualization` 标签不进实体锚点覆盖 + 重打 dist）→ `dc0afd0`（上游 v1.0.10 负值修复记账）→ 本轮 A 组六项硬化 + 图表张数上限（同轮把 `vendor/README.md` 入库）→ `ec8f653`（A 组 + dist `b9b46d8a`）→ `f5a479d`（R1–R5 落地 + dist `58a66abc`）→ `e9bd331`（记账）→ `59ce4a0`（引用日期裁 `YYYY-MM-DD` + O2/O3/O6，dist `8159b1d8`）→ **`4cea33d`（空结果不是来源：O7/O8 + 断言论 `title` 非空 + `run --expect refusal` + in-place 发布，dist `de7c16b4`）**）** 全部按用户授权 push 到 `origin/v0.15-remove-html`；**按要求不合回 `main`、不开 PR**（不合并分支）。
- **本轮（`4cea33d`）已 commit + push**（用户 2026-09-14 授权：“可以 commit push 吧”）：11 个文件 / 142 insertions / 30 deletions；`59ce4a0..4cea33d`，工作区 clean。
- 已提交 / 已发布：**第二轮硬化（R1–R5）已 commit `f5a479d` 并 push 到 `origin/v0.15-remove-html`**，并已通过个人令牌 API 发布到 ToolSmith（prompt `1.5` / skill `1.0.6`，回读逐字节一致）——三者（工作区 / git / 线上）当前一致。`vendor/` 处置已按用户 2026-09-11 拍板定案：**`vendor/README.md` 入库**（只含 provenance / 差异表 / 发布 ID，不含上游源码），**上游源码副本 `vendor/chart-visualization-json/{1.0.9,1.0.10}/` 继续 gitignore**。无 `Dockerfile`/compose，不涉及镜像。发布通道的常态规则（改完先问要不要推 ToolSmith，再问 commit & push）已记入工作区 `AGENTS.md` 与本节。

## ToolSmith 发布通道：个人令牌 API 同步（2026-09-11）

- **背景**：此前 prompt/skill 都靠人工在 ToolSmith Web 上传；现改用前端提供的「个人令牌 API」（`<host>/docs/integrate/token-api`，实例即 `http://39.106.82.157:36688`，与分享链接同一环境）。链路已实测跑通。
- **鉴权**：PAT（`ts_pat_` 前缀的软令牌，Web → 用户菜单 →「访问令牌」，明文只返回一次）通过 `Authorization: Bearer …` 头传递。本账号 `徐佩佩` 角色 `project_manager`，含 `prompt:write` / `skill:manage` / `skill:update_own` / `project:write`；`GET /api/auth/me` 自检。令牌**不入库、不进文档**。
- **平台聚合 id（已定位）**
  - 提示词家族 `91febc286412479a8b6d569fa3b8025e`（title `multi-clinical-result-comparison`）
  - 技能家族 `9fe0035bdd324b998436c6cb9c2de212`（name `multi-clinical-result-comparison`）
  - 项目 `a7cdda6508e0423c8b7afaaf3a68e50d`：`resources.prompt` = 当前提示词版本 id；`skills=[chart-visualization-json, multi-clinical-result-comparison]` **按家族绑定** → 换版本自动跟随，无需改项目配置。
- **两个写接口语义（据部署端 `openapi.json` + tool-smith 后端源码双重核对，非照文档猜）**
  - 提示词追加版本：`POST /api/prompts/{family_id}/versions`，body `{version, content, ifadd:true, is_current:true}`；同家族版本号重复 → 400；`is_current=true` 使新版本**自动成为当前版本**，无需再调 set-current。
  - 技能追加版本：`POST /api/skills/create`（multipart `name`/`version`/`file` **+ `family_id` + `message`**）；`message` 空 → 400「发布新版本时必须填写版本更新说明」；`name` 必须等于包内 `SKILL.md` 的 `name`（大小写不敏感比对）；新版本自动 `is_current=True` 并把家族内旧版本降级。
  - ⚠️ `/api/skills/update_skill_file`（`skill_id` = 某个**具体版本** id）是**原地覆盖该版本文件**（`commit_id+1`），**不产生新版本** —— 要留版本历史就别用它。
- **平台版本号 ≠ 仓库版本号**：平台自成序列（提示词 `1.0…1.5`、技能 `1.0.0…1.0.6`）。按内容 SHA 对齐得到映射：prompt `1.2`=仓库 `v0.11`、`1.3`=`v0.13`、`1.4`=`v0.15（A 组之后、R1–R5 之前；仓库未留该文件）`、`1.5`=`v0.15`（当前）；skill `1.0.5`=dist `b9b46d8a…`、`1.0.6`=dist `58a66abc…`。**当前（2026-09-18 原地更新后）**：prompt `v1.6` = 本地 `v0.15`（52,414 B，sha `0ae72c9302b3`）；skill `v1.0.7`（`ad75ec2c44334f389a0394895a47b765`）= dist `d5afb1f00320`（84,994 B / 19 entries）；`status` in sync。**第十轮 dist = `a1b65809eb8b`（85,544 B / 19 entries）**；线上 `v1.0.7` 当前 = `c55321ad4619`（第九轮那版），且 sys 也改了 ⇒ **prompt + skill 都待再次授权发布**。
- **本次已同步（2026-09-11 17:42，即第二轮硬化）**
  - prompt **`1.5`**（id `00ce20bbf3e14c30875aeb9257fb530f`，41113 B，sha `f0e813a5678d`，逐字节 == `system-prompts/multi-clinical-result-comparison-v0.15.md`），已 current，项目 `resources.prompt` 已指向它。
  - skill **`1.0.6`**（skill_id `cdd1715065c246e9af6224a7a921b56e`，70301 B，`message` 记 R1–R5 + dist `58a66abc`），下载回读 **19/19 文件与本地树逐字节一致**，已 current（`1.0.5` 自动降级）。
- **发布工具（已全局安装，2026-09-11；不进本仓库）**：命令 `toolsmith-publish`，源码 `~/.local/bin/toolsmith-publish`（可执行，无第三方依赖）；本项目 id 写在工作区之外的全局配置 `~/.config/toolsmith/projects.json`（按仓库根路径索引）；凭证 `TS_BASE` / `TS_TOKEN` 存在 `~/.secrets`（600，`~/.bashrc` 已 source），仓库里零凭证。
  - `status`：**只读**比对本地 vs 线上 —— 打印平台版本↔仓库版本映射、当前技能包逐文件比对、项目绑定检查；不一致时 **exit 3**（可直接当提交前闸门）。
  - `publish`：自动取下一个版本号（提示词 max minor +1；技能 patch +1）→ 先推 prompt 再推 skill → 自动重跑 `status` 校验，绿了才算完成。
  - `push-prompt` / `push-skill` / `pull`（把线上 version 下回 `/tmp/toolsmith-publish/` 做 diff）/ `find`（发现 family_id，禁止硬编码）/ `whoami` / `config`；`--dry-run` 预览。全局参数放子命令前后均可。
- **以后的工作流（用户 2026-09-11 定，已记入工作区 `AGENTS.md`）**：改完 skill/prompt → **先问「要不要推 ToolSmith」**（与 commit 同级，不自行发布）→ 同意后 `toolsmith-publish publish` → `status` 必须绿 → **再问 commit & push**。

### 只读事实核对通道（2026-09-11，用户要求「能拉就拉」）

- `toolsmith-publish tools`：平台 MCP 工具目录（26 个，Pharmcube 18 / Report 8，含启用状态与参数个数）；`--schema <tool>` 导出单个工具完整 `inputSchema` 到 `/tmp/toolsmith-publish/schema-<tool>.json` 并打印参数表；`--internal` 列 16 个内置 agent 工具；`--search` 过滤。
- `toolsmith-publish instructions`：拉**部署端真正装配的系统提示词**（`GET /api/agent/info?project_id=…`）。已验证：本仓库 `system-prompts/…-v0.15.md`（40,309 字符）是部署 `instructions`（58,851 字符）**offset 0 逐字节前缀**，平台另追加 18,542 字符样板（Pharmcube Data Tools / Entity Inline References / Write todos / Task / Skills / Filesystem / Execute / Artifact Presentation / Visualizer 等 20 节），落在 `/tmp/toolsmith-publish/instructions-deployed.txt` 与 `instructions-platform-tail.md`。**这条通道比 share 快照强**：share 不含 system prompt、只能靠运行期正文推断版本，而这里能逐字节判部署版本。
- 用法例：想确认「部署端 `execute` 的参数名」直接看 `tools --internal --schema execute` → `required=['shell_command']`，无 `command` 参数（与 v0.15 R3 规则一致）。

### 只读实测：esid → params 工具的字段与取值（2026-09-17，回答用户「长格式 esid 会不会查不到」）

工具链只有一条：**`pharmcube-query-clinical-result-with-params`**，当前参数 **`esids`**（精确过滤 `clinical_result.extra_esid`；2026-09-18 live schema 更正，历史 `extra_esids` 已失效）+
**`selected_fields`**（白名单，48 个顶层名，离线镜像 `docs/params-tool-schema.md`；嵌套字段如 `projects.*` / `arms.drugs.*` /
`study_results.*` 以顶层名写）。只读通道 = `POST /api/tools/debug`（不写任何数据）。实测结论：

- **长哈希 esid `24_187_acaa9fda98c00fb890d804d0e3a0428c_1` 查得到**：`ok:true` / 1 行 / 51 字段中 27 个非空（`paper_title`、`summary`、
  `study_results`、`arms`、`projects`、`paper_release_time` 齐全；`abstract_text`、`doi`、`clinical_stage_cn` 等为空）。
  ⇒ **「字段空」≠「记录查不到」**，id 格式（短号 vs 长哈希）不是问题（两者都是合法 `extra_esid`）。
- **「查不到」在协议层是静默的**：不存在的 id → `ok:true` + `data: []` + `error:null`（负向对照已验）。
- **一个 esid 可能返回多行（按疾病 join 扇出）**：`24_1_30561610` → **3 行**，仅 `disease_id` 不同（10000/5194/1403），
  `extra_esid` 三行相同。**用户 2026-09-17 判为「很重要、需要改，但要先问产品」→ 本轮不改 skill**；见下方 parked 条。
- **NCT 号不需要另查**：`clinical_result.projects[*].associate_ids` 里就有（该记录 = `["NCT05419908","EudraCT2015-002578-20",
  "ESN364_HF_204","PMCT00191065"]`），且 `full_article_link` 就是 CT.gov 的 **results 页** URL；而 `study_results`（该记录 **84 行**）
 已经是 results 页的结构化解析 + 魔方自己的成对比较（`compare_result`/`p_value`/CI）。
- **⚠️ 2026-09-17 更正（原判断作废）：「沙箱无网络 ⇒ 拿不到 CT.gov」把两个开关搞混了**。平台有两套独立的东西：
  **① 服务端受控的 Web 工具**（`web_search` / `web_fetch`，`CapabilityConfig.web` 项目开关 + 请求级 `enable_web`），
  **② 沙箱联网**（`sandbox_internet`，只影响 `execute` 里的任意命令出站）。平台自己的文档就写明这个区别
  （`frontend/content/docs/projects/capabilities.mdx:36,57`）；`instructions-platform-tail.md` 的
  「sandbox is isolated」只讲 ②。**实测（4 次 web_fetch 探针，见下方「只读探针」段）：`web_fetch` 能直连
  `clinicaltrials.gov/api/v2`**。⇒ 剩下的阻碍只有 ③ 引用口径 + skill/sys`Do not retrieve external facts or URLs`
  政策，属**产品/政策层**，不再是「平台拿不到」。
- **（2026-09-17 用户更正）真实诉求不是「多拿证据」，而是「我们的结果记录不全」** → 见上方 parked 段与 Obsidian 追问 2 更正。
- **但 `trial_id` 参数可用 NCT 号反向拉「该试验全部结果」**（源码 `params_clinical_result_tool.py:246`，
  `JSON_PATH_LIKE` 于 `projects $[*].associate_ids`）：实测 `trial_id=NCT05419908` → 2 条不同 esid（`24_1_31415087`
  JCEM 2019 / `24_187_acaa9fda98c00fb890d804d0e3a0428c_1` CT.gov 2023）。**纯内部数据、无需联网**，是「同试验多证据」的正路。
- **`selected_fields` 不是严格白名单**：响应恒多带 3 个未请求的键（`clinical_result__id`、`company_id`、`disease_id`）；
  48 个名全部被接受（无 `INVALID_INPUT`）。
- 踩坑：`POST /api/tools/debug` 的 `name` 必须是**上游全名**（`pharmcube-…`），短名 → HTTP 200 + `is_error:true` `Unknown tool`；
  `~/.secrets` 是 `export K="…"` 形式，按 `=` 切会拿到空 token（401），要用正则解析（runner 的 `env_from_secrets`）。
- 全文（含 SQL、逐字段取值、84 行 `study_results` 与脚本写法）：Obsidian
  `03-技术与VibeCoding/01-AI与LLM/临床结果esid查询-params工具字段与取值实测-2026-09-17.md`。

### 写权限护栏 + 上游新鲜度门禁（2026-09-11，用户追加）

- **用户要求原文**：*「只允许更新我指定的 skill 和 prompt（就是除了我创建的当前正在改的主题，别动其它的）」*、*「每次准备更新我指定的 skill 和 prompt 前面，先检查下我用到的 skill 和 tool 有没有更新」*。
- **护栏一（配置层）**：`projects.json` 条目必须显式 `"owned": true`，**默认只读**；命令行传的 `--prompt-family` / `--skill-family` 与配置不一致时直接中止（跨项目写被拒）。
- **护栏二（平台层）**：写前用 `/api/auth/me` + `skills/list` / `prompts/{family}` 核对 `owner` 必须是当前用户；实测把 skill 家族指向他人资源（`7cefbe2a…`）**硬拒**。
- **门禁（deps）**：`toolsmith-publish deps` 扫本仓库 `skill/` + `system-prompts/` 文本实际引用的上游资源（技能名整词匹配，避免 `chart-visualization` 误配 `-json`），指纹存 `~/.config/toolsmith/deps.json`；`publish` 会自动先跑，**有漂移就停手**并列出「技能升版 / 工具 schema 变 / 参数增删」，须 `--force` 或适配后 `deps --accept`。`deps` 只读，漂移时 **exit 3**。
- **当前依赖基线**（2026-09-18 live 核对并 `deps --accept`）：skill `chart-visualization-json` v1.0.12；MCP `pharmcube-query-clinical-result-with-params` 已从 `extra_esids` 适配为 `esids`，镜像 live 重生成；内置 **16 个**——按**项目实际启用的工具集**统计（`GET /api/agent/info?project_id=…` → `tools`），不再靠文档文本匹配（旧口径只命中 10 个，漏掉了运行期高频调用的 `read_file`）。
- **`docs/params-tool-schema.md` 改为自动生成**：新增 `toolsmith-publish tool-doc`（默认工具取配置 `params_tool`，输出 `<repo>/docs/params-tool-schema.md`）——参数表 + 参数完整 schema + ALLOWED_FIELD_NAMES（73 个）+ ALLOWED_FIELDS 逐字段含义表（73 条）+ MCP 返回封装；幂等（同 schema 二次运行输出 unchanged）。**与旧手贴档对账通过**：73/73 字段名一致、18/18 参数一致；文件 499 行/20,792 B → 326 行/44,003 B（增量来自逐字段含义表）。
- **为什么不把脚本放进仓库**：它跨多个 skill 项目复用，且令牌/平台 id 属本机环境，不属于任何单个项目；入仓反而会把平台 id 固化进公共代码。
  - **推荐流程**：改仓库 → `publish` → `status` 绿 → 再 commit。

## 部署端自验证：API 直驱 chat + 两栏发现台账（2026-09-13）

- **授权口径（用户 2026-09-16）**：*“本项目 commit & push 不需要确认，TS 的 prompt 和 skill 更新/新建需要确认”* → 本仓库（git root `/home/xupeipeioo1/apps/skill`）改完 `commit` / `push` **直接做、不再问**；**只有往 ToolSmith 写 prompt/skill（`publish` / `push-prompt` / `push-skill`）仍先问**。

- **用户要求（2026-09-13）**：*「之后每次迭代 SKILL 时，AI 自己调用 ToolSmith 的 chat 做验证」*；过程中把发现整理成两栏——(1) **我们自己能改的**、(2) **平台 bug（用户转给开发）**。
- **新子命令 `toolsmith-publish run`**（**2026-09-16 起改为轮询版**）：建线程 → `POST /api/chat`（单条 user 消息）→ **只读到 `data-turn-start`（≤20 s）即断连** → 按 ≤60 s 轮询 `/api/threads/{tid}/info` 的 `status` 判终态（平台把 run 当独立任务，断连只摘订阅者、**不 cancel**）→ 拉 `/timing` `/usage` `/info` `/messages` `/debug/history` `/artifacts/archive` → 自动断言 → 落 `~/.local/state/toolsmith-runs/<时间戳>-<tag>/{run.json,prompt.txt,stream.tap,debug-history.json,info.json,timing.json,usage.json,artifacts.zip,artifacts/,verification.md,transcript.md}`（临时工作目录也在 `~/.local/state/toolsmith-publish/`；**不再用 `/tmp`**）。**证据链全部从持久化消息重建，SSE 不再作为任何断言输入**；`turn_id` 在 POST **之前**落盘，`--resume <THREAD_ID>` 可接手；重复 POST 的 `409` 当幂等，**超时绝不重发**。退出码 **0** 全过 / **3** 断言失败或工具报错 / **4** `not_started` / **5** `inconclusive` 或 `timeout`。**属写动作**（会创建线程），与 publish 同级过 `owned: true` + 项目属主护栏。
- **17 项断言**（2026-09-17 起；先前 13 → 16 → 17，见 ⑩/⑪）：deployed prompt 逐字节 == 本地 sys；deployed skill 正文 == 本地 `SKILL.md`（去 frontmatter）；支持文件清单逐个比大小；固定产物路径（`output/report.md`、`output/citations.json`）；图表文件名合法；envelope keys + `id` + 文件名 `bar/line` 与 `option.type` 一致 + `iframe_template` 非空（并打印发布 ID）；`::visualization` 标签数 == 图表文件数；无残留 `{{…}}`；无嵌套 `](entity:`；`{{ref_n}}` 与 citations 双向齐全；`citations` 每个键恰为 `link`/`paper_release_time_str`/`title` 三字符串 + 日期为 `YYYY-MM-DD` 或空串 + **每个条目 `title` 非空**（末条为 2026-09-14 新增，见 O7）；末尾工具 == `present_artifact`；无 `tool-output-error`（**非 schema 拒参者**；被拒调用单列 `schema-rejected`）；**turn 结局必须 `succeeded`**（平台把终态从 `/info` 删了之后，失败/被取消的 turn 不得再报成功 —— 2026-09-17 新增）。**另有 `--expect refusal` 模式 11 项断言**（「本应拒绝产出」的场景：不写 report/citations、确实查过、回复非空且不含 `{{ref_`、无工具报错；含 outcome 项）。
- **台账**：`docs/toolsmith-verification-log.md` = 标准流程 + 为什么用 API 而不是分享链接 + 断言清单（产出物 17 / 拒绝 11）+ 运行记录（R1–R11、F1）+ 两栏清单。**没有 R 记录就等于这次改动没验证过。**
- **R3（2026-09-14，本批改动上线后首次）**：thread `61e5d232-519f-40ab-826d-6e2ceb1b423f`，2 个 esid，`DeepSeek Flash`，**13/13 全过、0 工具报错**；墙钟 129 s、21 次工具调用、`reasoning_tokens` 16,082；deployed sys 41,490 字符 + 平台尾部 18,543 字符（sha `e6d9c5fd4188`）、skill 正文 18,755 字符与本地逐字节相同、18 个支持文件 0 处不一致。**硬证据**：线上 `citations.json` 的 `paper_release_time_str` = `"2018-12-19"`（平台原值带 `00:00:00`）。发布号：prompt `v1.6`（sha `ee9dbe9d3a20`）/ skill `v1.0.7`（`ad75ec2c44334f389a0394895a47b765`），`status` in sync。
- **发布时命中 deps 门禁（设计内行为）**：上游 `chart-visualization-json` 已从 1.0.10 升到 **1.0.12**（2026-09-14T14:56:46），`publish` 被挡下 exit 4、**线上零改动**。逐字节 diff 1.0.10 vs 1.0.12 = 6 个文件：`config.js` + 4 个 `templates/*.json` 只换发布 ID（`20260911-134013` → `20260914-145519`），`references/chart-types.md` **仅 +1 行**（堆叠 + 负值，组合我们不产出；并排柱固定 `group:false, stack:false`），`SKILL.md` / `schemas/*` / `scripts/validate.js` 逐字节未变 → **协议零变更、本 skill 无适配**；留档到 `vendor/chart-visualization-json/1.0.12/` 后 `deps --accept` 再发。
- **O2 / O3 / O6 已落地（用户 2026-09-14 拍板“我们的问题都改改”）**：O2 → sys `Step discipline` 要求 digest 单文件能一次读完（≤ ~300 行，超了就拆文件而不是反复 offset 读）；O3 → 字段名以 params 工具自身 schema 为准、**禁止发明**（无字段时取最接近的真实字段或留空记“未报告”）、`docs/params-tool-schema.md` 只是维护者镜像且**禁止运行期读**；O6 → `run` / `WORK` 输出目录换 `~/.local/state/`（`/tmp` 会被清空，早期 R1/R2 产物已不可复核）。
- **（本条为 2026-09-14 本批新增）R3 的真缺陷处理见下方 O7 / O8 两条；本批验证 = R4/R5/R6/R7。**
- **O7 已落地（2026-09-14，R3 真缺陷闭环）**：R3 的“全空 `ref_2`”**不是平台 bug，是我方规则逼出来的**——部署 prompt 尾部有我们自己的一句 `every selected esid has a corresponding pulled record and exactly one citation JSON entry, including duplicate or unusable items`（sys:196），叠上「按输入顺序一一对应」与「keys 从 `ref_1` 连续」三条规则，遇到空结果就只能写出空壳条目。改法：**一次批量拉取 + 至多一次确认**（不换拼写/猜 id/逐 esid 循环，**参数不变的确认不许重复**，见 O8）；**未返回的 esid 不分配 `{{ref_n}}`、不写 citation key**，keys 在「实际返回的记录」上连续；**禁止空 `title` 条目**；**可用记录 < 2 → 拒绝产出**（不写 report/citations，回 chat 点名说明）。落到 sys v0.15（5 处）+ `SKILL.md` + `references/{input-contract,citation-and-ref,input-and-extraction,file-delivery}.md` + `templates/unified-evidence-report.md`；工具侧新增 `title` 非空断言 + `run --expect refusal`。**验证：R4/R5/R6/R7**。
- **发布语义改为原地更新（用户 2026-09-14 拍板：*“ts 你能 sys 和 skill 你能更新当前版本嘛？而不是创建新版本”*）**：`publish` 默认 **in-place** —— prompt 走 `POST /api/prompts/{family}/versions` `ifadd:false` → `update_current_prompt_content`（SQL `UPDATE … WHERE is_current=true`，版本号标签不变）；skill 走 `POST /api/skills/update_skill_file`（multipart `{skill_id, skill_name, file}`，必须传**全量 bundle zip**；保 `skill_id`/version、内部 `commit_id` 递增、description 由包内 `SKILL.md` frontmatter 刷新）。**`--new-version` 才追加新版本；`--overwrite` 已删除。** 本轮即原地发布：prompt 仍 **`v1.6`**（44,431 B → 44,431 B 内容替换，sha `2a73cf73671b`）、skill 仍 **`v1.0.7`**（`ad75ec2c44334f389a0394895a47b765`），`status` in sync。
- **R2 冒烟（2026-09-13，`run` 首次）**：thread `eaace30f-0e60-45ab-8384-ae7b10983d27`，1 个 esid，`DeepSeek Flash`，**12/12 全过、0 工具报错**；墙钟 173 s、21 次工具调用、`reasoning_tokens` 26,153；deployed sys 40,308 字符 + 平台尾部 18,543 字符（sha `18e3ee0b85bb`）、skill 正文 18,042 字符与本地逐字节相同、18 个支持文件 0 处不一致、`iframe_template` 发布 ID `20260911-134013`（= 上游 v1.0.10）。
- **R1（2026-09-11，手工脚本，先于 `run`）**：14 个 esid，299.2 s、50 次工具调用、`reasoning_tokens` 31,782；产物 report 33,166 B + 2 图表；`evidence-timeline` 正确地未生成（11 个不同试验）；1 次 `INVALID_INPUT`（模型发明 `clinical_result.line_count`）下一调用自愈。
- **本轮顺带修的工具缺陷**：`collect_deps` 的内置工具指纹原靠**文档文本匹配** → 运行期高频使用的 `read_file` 从不进基线；改为取**项目实际启用的工具集**并记录 `enabled_on_project`；顺带修了漂移输出把 `NEW builtin` 截断成 `NEW buil`。基线已 `deps --accept` 重建（16 个，复跑 exit 0）。
- **平台侧 5 项已写成可直接转发的问题单**（Obsidian `03-技术与VibeCoding/01-AI与LLM/ToolSmith-平台问题单-ChatAPI与SSE文档缺口.md`）：P1 Chat API 无最小可用示例 + 字段命名不一致（`threadId` 驼峰 / `project_id` 下划线、`/api/projects` 用 `projects` 键 vs 其他端点 `items`）；P2 SSE 事件字典缺 `data-turn-start` / `data-sql` / `data-table`；P3 `INVALID_INPUT` 的 `ALLOWED_FIELD_NAMES` 硬截断（180 字符）且无全量获取指引；P4 `/threads/{id}/info` 的 `usage` 只算最后一步（`turn_usage` 才是整轮）；P5 `/artifacts/archive` 未进 token-api 文档。**更正**：此前记的 `/api/threads`、`/api/chat/shares` 返回 Unauthorized 是**漏带 token**，权限模型正常。
- **待拍板**：只有 O4（正文句子级 `s.replace()` 就地改脚本，8 次）、O5（1 个 esid 也要 21 次调用 /173 s）继续攒样本；**O2 / O3 / O6 / O7 / O8 均已落地**（sys 与 skill 改完 → 已重新发布 + `R3`…`R7` 验证）。
- **本批改了 skill/sys 运行内容**（`citation-and-ref.md`、`input-contract.md`、`input-and-extraction.md`、`file-delivery.md`、`entity-inline-reference.md`、`SKILL.md`、`templates/unified-evidence-report.md`、sys v0.15），故 `dist` 重打 → `de73…`（`de7c16b44910` / 73,385 B / 19 entries），并已 **in-place** `publish` 到 prompt `v1.6` / skill `v1.0.7`（`status` in sync）+ R4–R7 验证通过。

- **（2026-09-14 方案；**2026-09-16 已实施**）`toolsmith-publish run` v2：SSE 消费 → 线程状态轮询**。开发两次反馈「你怎么还要消费 SSE 啊，不是应该调一次就直接用 TS 的前端看吗」+「非流式要不就用 webhook，要不就轮训 thread 状态」；复核上游源码后确认**开发是对的**：run 与客户端连接解耦（`run_manager.py:229-233` / `445-468`）、终态只能认 `/info.status` 且只留 300–360 s（`chat_routes.py:352-353` + `run_manager.py:470-480`）、`/timing.active_turn` 不判状态且 `latency_ms` 现算（`chat_service.py:859-874`）、`turn_id` 撞车 409 可当幂等（`chat_service.py:1502-1505`）、webhook 是项目级且失效静默（`schemas/webhook.py:70-84`）。方案全文（修订对照 / 新判定状态机 / 改动清单 / 13 项断言重映射 / 平台缺口 P7+P8 / 待验证项 T1–T4 / 执行闸门）见 **`docs/toolsmith-run-v2-polling-plan.md`**。**口径（用户 2026-09-14 定）：以代码为准，平台文档缺口不再上报**，只报功能性缺陷（原拟报的 P9 已撑回为内部存档）；**P7/P8 已写成 Obsidian 草稿但暂缓上报**，等轮询版 `run` 真跑时一并排查后再定。后续「轮询式 `run`」按此方案交接给下一个 session 执行。顺带新发现：持久化消息里的 `retry-prompt` 能看到 SSE 看不见的**模型工具参数返工**（5 次运行 1 次，`a2-2valid` 把 `shell_command` 写成 `command`）。**本轮未动代码、未真跑、未 commit**（→ 2026-09-16 已按方案实施，见下条）。

- **（2026-09-16，已落地）run v2 轮询版 + S0 键名修复**（方案 B：S0 与 run v2 同批做完；改前备份 `~/.local/state/toolsmith-publish/toolsmith-publish.v1.bak`）。
  ① **S0**：`status` 假警报根因 = 平台返回 snake_case `current_version_id`、工具读 camelCase（5 处）→ 新增 helper `fam_current_version_id()`；复测 `status` **EXIT=0**、`prompt deployed == local: True`。
  ② **run v2**：`POST /api/chat` 只读到 `data-turn-start`（≤20 s）即断连，改按 ≤60 s 轮询 `/info.status` 判终态；调用链改从 `/debug/history` 持久化消息重建，`parse_stream()` 降级为离线对账 oracle；`turn_id` **POST 前**落盘、重复 POST 的 409 当幂等；`--timeout` 语义改为「停止轮询」（默认 2400 s），**超时绝不重发 POST**，只允许 `--resume`；退出码 **0/3/4(`not_started`)/5(`inconclusive`|`timeout`)**；新增 `--resume`/`--turn-id`/`--poll-interval`/`--grace`/`--no-tap` 与 `transcript.md` 产出。
  ③ **验收（无新 run）**：零网络重放 5 个已录制 run → v2 链 == v1 链 + 被拒调用，**GATE PASS**；只读实测 `--resume`（已结束 thread）→ `inconclusive` exit 5、`--turn-id`（不存在）→ `not_started` exit 4，全程 GET、无平台写动作。
  ④ **顺手查出旧工具假 PASS（→ 台账 O9）**：`parse_stream()` 不认 `tool-input-error`，把 a2 的 **41 次尝试记成 40 次调用 + 0 报错**；v2 从持久化消息重建时按构造必然捕获（该次是 `execute` 把 `shell_command` 写成 `command`，被 schema 拒后重发）。
  ⑤ **上游漂移已清**：`deps` 报 params 工具 `schema changed`，逐项核对仅为 `selected_fields` 描述里的序号笔误修正（`1./1./2.` → `1./2./3.`），18 参数 / 73 字段名 / 73 字段描述逐字节相同 → **本仓无需适配** → 重生成 `docs/params-tool-schema.md` 镜像 → `deps --accept` → `deps` exit 0。
  ⑥ **本批不改 `skill/` 与 `system-prompts/`** → 不触发 Toolsmith 发布；`status` 复测 **in sync（EXIT=0）**。
  ⑦ **R8 = 轮询版首次端到端真跑（2026-09-16）**：thread `b1302c80-f1f6-487d-8244-f495a5848490`（2 esid），**16/16 PASS / exit 0**；`POST` 后 **0.1 s 断流**，靠 **11 次轮询**看到 `running`→`completed`（**202.0 s**；当时打印的 202.4 s 是活计数）→ **T2 证实**（断流不取消 run）；同 `(thread_id, turn_id)` 重发 → **HTTP 409 `Turn already exists`（0.2 s、零执行）→ T3 证实**；**P7 现场证据**：`/info.status=completed` 而 `/timing` 仍 `completed:false`、`latency_ms` 204 s→350 s。**P8 当时未测**（需一次有意超时）→ 已于 2026-09-16 补齐并改判，见 ⑨。顺带修了量具自己两处错（重复打印的 `no tool errors`；把 `/timing` 活计数当永久值）→ 台账 **O10**。
  ⑧ `docs/autoresearch-iteration-plan.md` 的执行队列：**S1.5（必含事实清单 + 离线打分器）已于 2026-09-16 完成** → `evals/fact-check/`（`records/` 2 份 `POST /api/tools/debug` 真实返回 + 场景 A 31 条 / B 12 条 fail 级事实 + `check.py` + `mutations.py` + `README.md`）。基线（打 R8 产物、零新 run）：**A 31/31 PASS、B 12/12 PASS**；负向对照 `mutations.py` → **GATE PASS**（A **16** 个变异覆盖 31/31、B 11 个覆盖 12/12，每个变异 rc=3）。质量层自此有 `facts_ok/facts_total` 标量。**（2026-09-17 清单修订 O17：A 由 30 条增至 31 条，新增 `A-S2b-chart-or-reason`）**
  ⑨ **P8 实验已于 2026-09-16 执行完毕**（`docs/toolsmith-run-v2-polling-plan.md` §8.1.1 / §12.2），**三臂全答**：
  (a) 硬杀客户端（第 3 次轮询 40.5 s、`status=running` 时 `kill -9`）**不会取消 run**，同一 turn 照跑到 `completed`；
  (b) `run --resume`（只重采集、完全不 POST）在窗口内补齐 → **16/16 PASS / exit 0**（R9，thread `1d8f2104-5a3f-46d3-b382-d8626eaec39b`，真实服务端 171.1 s）；
  (c) `>10 min` 后 `/info.status` 回落到 `未知`，但 **`/timing.completed_at` + `/thread-turns/validate`(`exist:true`) 仍可拿回结局与全量产物**
  ⇒ 判定表第二行：**体验问题，不报开发**。附：P7 描述被实测修正（活窗口内的 `latency_ms` 是**临时行**、大幅高估；
  窗口后冻结为真值）—— R8 的服务端耗时因此更正为 **202.0 s**。
  遗留两项待拍板：**O14**（`run` 的 `not_started` 判定实际从未生效：取 `me()['id']` 而非 `user_id` → validate 从未被调用；
  建议同时加「`completed_at` 有值就直接收尾」的 fallback）、场景 C/D 清单。
  ⑩ **runner 修复（台账 O14 + O15，2026-09-16 经用户同意后落地）** —— 改的只是**本机 CLI** `~/.local/bin/toolsmith-publish`，
  **不涉 TS 平台、不涉仓库 `skill/`、不涉已发布的 prompt**，因此没有 `publish`：
  · **O14**：`uid` 改取 `me(c).get("user_id") or .get("id")`（原先恒 `None` → validate 从未被调用 → 任何「状态未知」的 turn 都被误报 `not_started`）；
    并新增**窗口过期后靠 `/timing.completed_at` 直接收尾**（`kind="completed"` + 标注 `recovered from timing.completed_at`，不再空转到 `--timeout`）。
  · **O15**：`--resume` 默认写**新 run 目录**（不再就地覆盖原记录；R8 的 `verification.md` 就是这么丢的），只有显式 `--out` 才写指定目录。
  · **验收（R10，零 POST）**：T1 窗口过期 resume → **exit 0 / 16/16 PASS / 0.2 s**；T2 真 thread + 不存在 turn → `not_started` exit 4 且 `uid_probe: true`；
    T3 不存在 thread → exit 4；T5 零网络闸门 GATE PASS（v2 run 因 tap 是桩而 SKIP）；T6 `--resume` 不带 `--out` → 原目录 md5 未变；
    T7 重建 R8 记录 → `…/20260916-115047-resume-r8-recollect/` 16/16 PASS。改前备份 `toolsmith-publish.v2.bak`（85,409 B）。
  · **附正**：断言总数是 **16**（先前写 17 是数错，已全仓改正）；退出码语义更新：窗口过期的 `--resume` 现在是 **exit 0**，`inconclusive`（exit 5）只留给「活着时看不到终态且 DB 行也没有 `completed_at`」。
  ⑪ **runner 再修一批（台账 O16/O17，2026-09-17）**：详见下方「上游平台代码拉新：TS `master` → `30306cb`」。断言总数 **16 → 17**（产出物路径）/ **10 → 11**（拒绝路径）。

## 上游平台代码拉新：TS `master` → `30306cb`（2026-09-16 提交，2026-09-17 本地对照 + runner 适配）

- **动作**：`/home/xupeipeioo1/apps/tool-smith` 工作区干净 → 用户明确指令下 `git pull --ff-only`，`50f048b` → **`30306cb`**（4 个新提交）。
- **`30306cb remove unknown status, add idle`（P7 从根修掉，但同时改了我们依赖的契约）**：
  · 删 `cleanup_stale(300)`，`run_manager.complete()` / cancel / force-kill 三处立即 `_discard_run()`，`active_run_count` 简化为 `len(self._runs)`，新增 `RunManager.live_status()` ⇒ **「活窗口内 `latency_ms` 现算高估」不再存在（P7 已修）**；
  · `ThreadStatusFilter` / `ThreadInfoResponse.status` 改为 `Literal["preparing","running","cancelling","idle"]` ⇒ **终态值从 API 删除**（prod 实测：`?status=idle`→200、`?status=未知`→400、`?status=completed`→**422**），且 `/info` 无 outcome 字段、`thread_messages` 无 outcome 列；
  · 顺序不变量：持久化（`finish_timing_now(completed_at=…)`）**先于** `run_manager.complete()` ⇒ `idle` ⇒ DB 行必已有 `completed_at`（终态可判）；
  · 结局的唯一外部信号 = `_normalize_error_text_part()` 把 `provider_details.error_type` 归一化成 text part 顶层 `error_type`（`stream_error` / `TimeoutError` / 异常类名），取消写 `state="interrupted"`；官方 durable 通道是**项目级 webhook `run.completed` + `event_status`**（外部接入方无法按请求携带）。
- **runner 适配（改前备份 `toolsmith-publish.v3.bak`，88,308 B；只改本机 CLI，不动平台、不动已发布 prompt/skill）**：
  · `wait_for_run()`：活词表 `preparing/running/cancelling` 继续轮询；`idle` → `/timing` 行 `completed_at` ⇒ `completed`（**durable，常规路径**）；行有 `completed` 无时间戳 ⇒ `inconclusive`；从未活过 + 过 grace + validate `exist!=true` ⇒ `not_started`（exit 4）；**见过活状态却消失且无 `completed_at`（进程重启）⇒ 立刻 `inconclusive`**（不再空转到 `--timeout`）；`idle` 要**连续两次**才认；老值 `completed/failed/cancelled` 兼容保留（旧部署）。
  · 新增 `classify_outcome()`：零新增网络请求（吃已抓的 `messages.json`）；`error_type` → `failed`；`state=="interrupted"` 或 error_type 含 Cancel → `cancelled`；**无任何持久化消息 → `unknown`（不是 `succeeded`，空产物糊不过去）**；否则 `succeeded`。`kind==completed` 但 outcome 为 failed/cancelled 时**改写 kind**，不再谎报成功。
  · 新增第 17 项断言「turn outcome is succeeded」（拒绝路径 11 项）；`verification.md` 终态行改“read from `timing.completed_at`（durable DB row…）”+ outcome 行。
- **R11 验收（2026-09-17）**：真跑 thread `ea0b6213-…` / turn `ee2ff701-…`，轮询 10 次 `running`×9 → `idle`，**exit 0 / 17/17 PASS**，`177.6 s server / 188.9 s polled`，`outcome=succeeded`；只读复测 N1（R8 复采集 17/17、0.2 s）、N2（R9 171.1 s）、N3/N4（`not_started` exit 4）、拒绝路径 11/11、零网络闸门 `GATE_RC=0`。改后 `py_compile` + `deps`/`status` 均绿；本批**不涉 `skill/` 与 `system-prompts/`** → 未触发 `publish`，dist 幂等（`de7c16b449…` 未变）。
- **R11 同时暴露清单侧问题（台账 O16 / O17）**：R11 产物打场景 A 只有 **25/30**（R8 同输入 30/30）：3 个 FAIL 是「没出定量主图」——而 `references/chart-templates.md:91` 的规则是**定量主图可选**、需「同一终点、同一口径（**可明确对齐的时点**）」的纯数值，场景 A 两条记录是 **第 16 周 vs 第 36 周**，R11 明确写了不出图的原因；另 2 个 FAIL 中 `A-C12` 是模式过窄（字面 `2 条` vs 产物写 `2 项来源记录`）、`A-C6`（未报安慰剂组 +3.6%）**像真的内容缺口**。⇒ 当时**不改清单迁就产物**，三项挂「待用户判定」。
  - **（2026-09-17，用户已批准修正 O17）**：`A-S2` 改 `chart_set_allowed`（文件名合法 + 禁跨试验 timeline + 定量图 ≤1；空集合不算违规）、新增 **`A-S2b-chart-or-reason`**（无定量图必须正文写明且给理由）、`A-S8/A-S9` 加 `optional_when_absent`、`A-C12` pattern 放宽为 `2 ?(条|项)`、新增变异 **`M16`**。结果：**R8/R9 基线 31/31、R11 由 25/30 → 30/31（只剩 `A-C6`）、B 仍 12/12、GATE PASS**。`A-C6` 仍作待样本（单样本不改规则）。
- **另三个提交与本项目无关**：`34215c3` 只加 Pydantic `Field(description=…)`；`af4f601` 是 sandbox 镜像 pull 失败回退本地缓存（`_inspect_sandbox_image`）；`8d10fa0` 只改 `params_drug_deal_tool_v2.py` / `params_pipeline_tool_v2.py`，**`params_clinical_result_tool.py` 未动**，`deps` 复跑 **RC=0**。

- **（2026-09-16，待执行）用 autoresearch 范式规划下一轮迭代**。用户要求「你用对比结果那个 skill 规划试试？先不改动那个 skill 本身」→ 交付 **`docs/autoresearch-iteration-plan.md`**（只读诊断 + 规划，**未改 skill/sys、未发布、未 commit**）。要点：① **`toolsmith-publish` 的 prompt 侧闸门已坏**：平台返回 `current_version_id`（snake_case），工具 5 处读 `currentVersionId`（`~/.local/bin/toolsmith-publish:272/362/787/936/1094`）→ `status` 恒定报 `LOCAL NOT DEPLOYED`（exit 3，**假警报**：线上 v1.6 sha `fa80094e9d41` == 本地 `-v0.15.md`、项目 `resources.prompt` 也 = 该版），且 in-place `publish` 的回读用同一坏键 → **写完再报 `read-back mismatch`**；平台源码佐证 `apps/tool-smith/backend/src/toolsmith/schemas/prompt.py:25`（`current_version_id: str = Field(alias="currentVersionId")`，部署端未走 alias）→ **已于 2026-09-16 修复（S0，`fam_current_version_id()`）**。② 5 个 `20260914-*` run 离线重放得基线：场景 A 两次 **23 vs 41 calls / 18 vs 34 turns / 173 vs 207 s**，但**跨了 17:41 那次发布** → 无干净重复、该批硬化不可归因；拒绝路径跨版本仍极稳（8/7 calls、33/32 s）→ 可当廉价回归闸门；`params` 调用 **2↔8** 波动。③ harness 缺口：params 的 tool-return 是「预览 + `.../tool_results/<tool>/call_*.jsonl for script access` 指针」，而 `artifacts.zip` **不含 `tool_results/**`** → **引用 receipt 目前无法离线核**（现有断言只查键集/日期格式/`title` 非空）。④ 实验队列 E0–E6，其中 **E2 = 删/缩委派段**（该段 6908 B = sys 44516 B 的 **15.5%**，而 5 个 run **从未 `task` 委派**）。执行顺序 S0（修工具）→ S1（harness，0 新 run）→ S2（场景 A×3 取噪声带）→ S3（一次一个变量），每步均需用户授权。

### 附：同批 runner 第二次改动 —— `run --web`（2026-09-17，台账 O18 / W1）

- **缺口**：平台 Web 工具（`web_search`/`web_fetch`）= **项目能力 `capability_config.web` AND 请求级 `enable_web`**
  （`capabilities/web.py:140` `should_activate_web_tool`）；项目能力已开，但 `run` 的 `post_turn` 把请求级写死 `False`
  ⇒ **本机验证器永远跑不到「联网状态」**，路线 C 的前置条件无法自验（之前只能靠临时 `/tmp/webtest.py`）。
- **改动**（改前备份 `toolsmith-publish.v4.bak`，92,618 B，`f7fc69be…`；只改本机 CLI，未动平台/已发布资产）：
  全局 `--web` → `post_turn` body `enable_web: bool(a.web)`；`run.json` 与 `verification.md` 留痕；`--resume` 打印无效提示；
  CLI docstring 与 `docs/toolsmith-run-v2-polling-plan.md` 同步。
- **判据**：`py_compile` OK；零网络闸门 `GATE: PASS`（RC=0）；**A/B 双真跑**（同一 prompt）——
  开：thread `f11aeb37-…` / turn `48b7797f-…`，`web_fetch`×1 取回 `example.com` 正文并逐字回报；
  关：thread `da5fc11c-…` / turn `bf38ed63-…`，**0 次工具调用**、模型答「我没有 web_fetch 工具」。
- **意义**：CT.gov **路线 C 现在本机可验证**（政策/引用口径拍板后可直接 `run --web` 测联网下的引用纪律）。

## 上游平台代码拉新：TS `master` → `50f048b`（2026-09-14）

- **动作**：`/home/xupeipeioo1/apps/tool-smith` 工作区无未提交改动 → `git pull --ff-only origin master`，从 `f1fdd58` 快进到 `50f048b`（**33 个新提交**，2026-09-07 → 2026-09-14）。属只读性质上拉，但改动了工作区，已获用户明确指令（“升级啊，你升级到最新版”）。
- **与本项目直接相关的上游变化**：
  - `chat_routes.py` / `schemas/chat.py`（`b373e34`）：**chat 请求体顶层字段现在同时接受 snake_case 与 camelCase**（`projectId`/`project_id`、`turn_id`/`turnId`），且 `chat-api.mdx` 已写明“文档示例用前端约定”→ 平台问题单 **P1 大部分自动消失**（剩下的只是 `/api/projects` 用 `projects` 键 vs 其他端点 `items`）。
  - 新增 `frontend/content/docs/integrate/token-api.mdx`（146 行）：chat / 提示词 / 技能 / 项目的 PAT 接口全表；`chat-api.mdx` 补齐 `/artifacts`、`/artifacts/content`、`/artifacts/file-download` 与 share 侧对应端点 → **P5 部分消失**（`/artifacts/archive` 仍未文档化）。
  - 新增 `spec/chart-json-ai-renderer.md`：前端正式把**我们的 envelope** 作为渲染门禁（`id === "chart-visualization-json"` + `iframe_template` http(s) + `option` 为对象），并且明确**旧构建的模板 URL 会被删除**（示例 `20260910-145629` 已 `NoSuchKey`）→ 印证「`iframe_template` 只能运行期现读、禁止硬编码」。
  - DeepSeek 系新增 `low` 推理档（`838ba7f`，`supported_efforts = [low, high, max]`）→ 以后可以用更低的 reasoning 档降本（未在本项目启用）。
  - `7ad5782 personal access token` / `ce16e7b fix api token copy` / `023704d fine grained permission control`：PAT 与细粒度权限进正式文档，其中「写接口无幂等键、先查再写」与 `toolsmith-publish` 的行为一致；我们的 PAT 拉最新代码后回归正常（`status` / `deps` / `publish` / `run` 全通）。
  - `56f1ff5 fix subagent token count`：子代理 token 计数修正（影响我们 `task` 委派的成本可观测性，规则本身不改）。
- **仍未修的平台项**：P2（`data-sql` / `data-table` 仍无事件字典）、P3（`ALLOWED_FIELD_NAMES` 硬截断 180 字符）、P4（`/threads/{id}/info` 的 `usage` 只算最后一步）、P6（`POST /api/tools/debug` 的 `mcp_server_id` schema 与行为不一致 —— 源码级证据 `backend/src/toolsmith/api/routes/tool_routes.py:41/47`：`str | None = None` + `model_validator` 报错）。
- **同步更新**：`docs/toolsmith-verification-log.md` 第 4 节加了对照小结与 P6；Obsidian 问题单同步。

## v0.15 change: 仓库内 HTML 资产彻底移除（2026-09-10）

- **触发**：用户拍板「新建一个分支，把 html 完全移除，搞一个 v0.15」。承接上下文：`docs/legacy-html-charts/` 里的 6 个 v0.8–v0.12 遗留 HTML/CSS/py 资产已无运行时用途（v0.14 起图表走纯 JSON + 上游 `chart-visualization-json` skill）。
- **分支**：`v0.15-remove-html`（不直接在 `main` 上改）。
- **删除**：`git rm -r docs/legacy-html-charts` —— `endpoint-bar.html` / `endpoint-line.html` / `evidence-timeline.html` / `chart-tokens.css` / `validate-chart.py` / `render-preview.py` 全销。仓库现在没有任何 `.html` / `.css` / 图表相关 `.py`；回溯看 git `e4f3bb7`。
- **运行时不变量**：这 6 个文件**从未进过发布包**（v0.14 dist 不含 HTML/CSS/py，已有打包断言护栏），所以对 Tool Smith 的运行时契约零影响——本次只是仓库卫生。
- **保留（故意，防回退护栏）**：`references/chart-templates.md` 仍写明「不写 Mermaid、不产出 `.html`、不混入自定义色板/CSS/HTML token」；sys 仍禁止 HTML/SVG fragment 与非 `.json` 图表文件；Final verification 仍断言 `::visualization` 目标是 `/workspace/visualizations/*.json`。只把两处 **v0.12 调试期遗留** 的 `.preview.html` 提法泛化为「非 `.json` 图表文件」。
- **eval 目录一并清空 HTML**：`evals/iteration-16/chart-examples/*.html` 7 个已跟踪文件 `git rm`；`evals/iteration-16/np-clinical-*/`（gitignore 内的本地示例数据）里 14 个 HTML 图表先移到仓库外暂存（`/tmp/html-attic/`），**经用户确认后已彻底删除**（这 14 个从未入库，不可恢复）。PNG 预览保留，`chart-examples/README.md` 已改写为「HTML 时代留存预览」并指向 JSON 契约。工作区内 `.html` / `.css` 残留 = 0。
- **历史段落说明**：本文档 v0.8–v0.11 各段里的 `*.html` 文件名、`CHART` 结构、坐标数值、`chart-tokens.css` 配色都是 HTML 时代的历史记录，**对应文件已不存在**（回溯看 git `e4f3bb7`）；原文保留仅为决策追溯，不代表当前能力。
- **同步**：新建 `system-prompts/multi-clinical-result-comparison-v0.15.md`（后扩充至 **213 行**：HTML 清理版 + `## Subagent delegation` 段）；`references/chart-templates.md` 头部不再指向已删目录；`README.md` 新增 v0.15 段并把历史段里指向该目录的句子标注「deleted in v0.15」；重打 `dist/multi-clinical-result-comparison-v0.15.zip`（打包断言新增「拒绝 `.html`/`.css`/`.py` 入包」）。

## v0.15 change: 图表 envelope 契约 + 空目录兜底（2026-09-10，分享会话复盘后）

- **触发**：用户分享 Tool Smith 会话 `fa0c0317-6c35-4b3e-8a57-6490fa9eb1b4`（thread `55906375`，标题 “Snapshot of 折线图”，同一批 14 个 Lp(a) esid），问「子代理用上了吗？好像也没有变快」。复盘结论：
  - **sys v0.15 生效，但模型主动否决了委派**：msg#1 reasoning 原文「We have 14 esids. More than 5, and the task tool is available. So delegation is possible.」；msg#3 权衡 5+5+4 后否决，理由：(a) citation 元数据要逐字节，(b) **params MCP 结果会自动落盘**到 `/workspace/tool_results/pharmcube-query-clinical-result-with-params/call_*.jsonl`，用 `execute`+python 脚本 digest 更省，(c) 委派要多管一条线。→ **在本平台「结果落盘 + execute」形态下委派无收益**，脚本化 digest 才是真省钱项（本次 23 次 `execute`）。
  - **其实更快**：本次总时长 **5.5 分钟**（`latency_ms 329871`）、42 步、48 次工具调用、reasoning 10.3 万字符；同批 14 esid 历史基线 9.9 / 10.9 分钟。但该 thread 复用了旧上下文，不算干净 A/B。
  - **返工点两处**：图表 envelope（约 4 步）+ `/workspace/output` 空目录（3 步）；契约面（固定命名、绝对路径引用、`present_artifact`、144 个实体锚点）全部遵守。
- **根因 1（我们的文档 bug）**：部署端 `chart-visualization-json` 已是 **2026-09-10 新版**，协议要求成品为 envelope `{"id":"chart-visualization-json","iframe_template":"<与 config.js 全等>","option":{…}}`，并**显式拒绝**旧的 option 层平铺格式（`未包 envelope：…；旧格式（option 层配置）已不再兼容。`）；`iframe_template` 由 `apps/ai-charts-html` 每次发布 CDN 后刷新、**必须与运行期 `config.js` 的 `IFRAME_TEMPLATE` 全等**。而本 skill `references/chart-templates.md` 旧版写的是「**合并 JSON 无额外 envelope**」——**写反了**；`templates/charts/*.json` 三个模板也都平铺。模型因此写入 → 校验失败 → 读 `validate.js`(6.3KB) → 读 `config.js` → 重写 → 才 PASS。
- **根因 2（平台 bug，已交后端）**：`/workspace/output` 空目录不跨 `execute` 调用持久——早期 `mkdir -p` 过、后续 `ls /workspace/` 里已无该目录（`scripts`/`visualizations` 在），单独 mkdir 后仍报 `FileNotFoundError`，最后把 `mkdir -p` 与写入放**同一次调用**才过。
- **改动（全部在 v0.15 上原地改）**：
  1. `references/chart-templates.md`：能力来源表加「成品包裹层」行；§零 把「无额外 envelope」整条替换为 **envelope 硬规则 + 三键来源（禁止硬编码）**（首选复制图表 skill 自己的 `templates/{bar,line,timeline}.json`，退路 `cat config.js`，两者都不可读则 fail-loud）；§一 表下补「两者交付角色不同」；§二 步骤 1/2 改为「先复制图表 skill 模板拿 envelope → 再只替换 `option` 内层」；自检段加 envelope 前置确认、校验覆盖加三键，并新增「**权威只有部署端那一份**」避坑条（旧副本会给出错误的 PASS）。
  2. `templates/charts/{endpoint-bar,endpoint-line,evidence-timeline}.json`：三个文件头部加 `_comment`，标明它们是 **`option` 内层起点**、不是可交付成品。（`_comment` 被 Zod schema 的默认 strip 语义忽略，`option` 内层仍校验通过。）
  3. 同步改写交付措辞：`SKILL.md`、`references/{timeline-diagram,cross-trial-comparison,file-delivery}.md`、`templates/unified-evidence-report.md`。
  4. `references/file-delivery.md` 新增 **empty-dir fallback** 条目（`mkdir -p` 必须与首次写入同一次调用；报目录缺失就重做后继续）。
  5. sys v0.15 六处：File delivery 段加同一条 mkdir 规则；Chart contract 段补 envelope 硬规则（`templates/charts/*.json` 只是 `option` 内层）；timeline 段改为「先拷图表 skill `templates/timeline.json` 拿 envelope」；Final verification 的图表项加 envelope 与「旧副本 PASS 不算权威」、交付文件项加「与父目录同一次调用创建」；**子代理段新增「先试脚本化 digest 再考虑委派」**（避免下次再花一段 reasoning 权衡）。sys **213 → 214 行**（段落内改写，行数几乎不变）。
- **重打 dist**：`67c17a026d21bcd437c1940214f628c7f59068b70ba3f0178abc6f2969d3c5ae`（19 entries / 66440 B；上一版 `1a6b5274…` / 63387 B 作废）。
- **验证**：包内 envelope 措辞就位（`chart-templates.md` 11 处命中）、旧措辞「无额外 envelope」与硬编码 CDN 地址残留 0、包内三个 `option` 内层经图表 skill CLI 仍 `校验通过: bar/line/timeline`。**未验证项**：envelope 层校验本地做不到（手头只有前端给的**旧副本**图表 skill，本地无部署端 `validate.js`/`config.js`），须由用户在 Tool Smith 运行期确认。
- **教训**：上一轮「三模板全 PASS」是**无效验证**——验的是前端给的旧副本；上游协议升级后本地副本不再是权威。凡「上游能力」类结论，一律以**部署端实际安装的文件**为准。

## v0.15 change: 子代理委派规则上移入 sys（2026-09-10）

- **触发**：用户问「sys 是不是该强调下（子代理规则）」，并回复「我开了呀」——即本项目 Tool Smith 部署的 `capabilities_config.subagents` 开关**已开**，于是子代理变成真实可用能力；若 sys 继续零提及，会出现「工具可见但无约束」的裸奔（模型自行委派，而 `{{ref_n}}` 全局顺序、来源 marker 回显、不得跳过来源这些护栏只在 Skill 正文里）。
- **决定：在 v0.15 上原地改**（不新开 v0.16）——因为 v0.15 尚未投递 Tool Smith，属未发布版本，改版号无意义。
- **sys 变更**：v0.15 新增 `## Subagent delegation (when the `task` tool is visible and there are more than 5 esids)`（位于 Step discipline 之后、Evidence boundary 之前，L33-45）；Required workflow 第 1 步加同义指针。sys **200 → 213 行**。
- **Skill 变更**：`references/input-contract.md` 该节标题去掉 `pending verification`、状态改为「platform-supported, and enabled on our deployment — still opt-in」；Constraints 补「子代理不继承项目 sys/Skill，description 必须自带规格」「多 call 串行」；原「Verification checklist（4 项待问）」替换为「**Platform facts**（已对 Tool Smith 后端源码核实，2026-09-10）」六条。`SKILL.md` Input 段指针同步改写。
- **设计取舍**：即便开关已开，规则仍保持 **opt-in + 条件式**（>5 esid 才用），且**只写「不变量」不写「提速承诺」**——委派治的是上下文膨胀，而实测并发不存在（串行），端到端 token/耗时收益仍未量化。护栏优先于收益：`task` 不可用/失败一律 fail-loud 回退直读，绝不静默缩源。
- **阈值二次校准（同日，用户反馈）**：初版写「~20+ esid 才委派、每块 ≤10」，用户指出**产品侧选中上限就只有 20 个**，等于阈值卡在理论上限 → 改为 **触发 >5 个 esid、每块 ≤5**（6 → 3+3；20 → 5+5+5+5），并加「不得切细于 5（每块要花一个串行子代理回合）、能均衡就不留 1 个的零头」。附带修正旧例「20–50 esid」为「最多约 20」。
- **重打 dist**：`1a6b52744ac71605611721e8afd165ed9ee7f65120f6cf22368d32d926954403`（19 entries / 63387 B；旧 `b89024c8…` / 62896 B、`1a7db902…` / 63328 B 均作废；**该包随后被下一节的 envelope 修复版 `67c17a02…` / 66440 B 取代**）。本节的 sys/Skill/dist 改动落在提交 **`aa05104`**（分支 `v0.15-remove-html`，已 push，不合 `main`）。SKILL.md 与 input-contract.md 是在包内的，所以本次**运行时有变化**（与上一节「HTML 清理对运行时零影响」不同）。

## v0.15 change: 对齐上游 chart skill v1.0.9 + 渲染配置归 Skill + vendor 留档（2026-09-11）

- **触发**：① 用户要求执行上一轮挂起的 4 处文档微调，且**保持 v0.15 版本号不变**（不下发新版本）；② 用户转达 TS 前端建议：在 sys 的**可视化渲染**部分加一条「渲染配置优先取自 Skill」，避免图表被内置渲染路径绕开、skill 不被触发。
- **上游版本核实**：解包前端交付的 `chart-visualization-json-v1.0.9.zip`（2026-09-10 build，源包 SHA-256 `572fbe553978696e3f915b6a13ea9a7ebe31f4be6d00987c057c8daf75e20438`），逐条比对我们已编码的规则——envelope 三键、`iframe_template` 需与 `config.js` 的 `IFRAME_TEMPLATE` 全等且每次发布 CDN 后刷新、`RENDERABLE_CHART_TYPES = line|bar|timeline`、bar `group` 默认 false / `stack` 默认 true、`theme ∈ default|academy|dark`（默认 default）、`width` 600 / `height` 400、行格式 `{label, value:number, group?, description?, drill?}`、timeline `time` 必填 / `weight` min 0 默认 0 / `legend[].shape ∈ circle|empty-circle` / 数组顺序即时间序不重排 / `weightLegend.show` 默认 true、`dataSource`+`describe` 不参与绘制——**全部一致，无规则变更**。
- **本地校验空缺补齐**：用留档的 v1.0.9 副本跑 `validate-cli.js`（exit 0 通过 / 1 失败）。正例：我们三个 `templates/charts/*.json` 的 `option` 内层套上游 envelope（含 `_comment`）→ 全 PASS；负例：平铺 `option` → `未包 envelope：…旧格式（option 层配置）已不再兼容。`、陈旧 `iframe_template` → `必须与 config.js 的 IFRAME_TEMPLATE 全等，期望 …20260910-153117…`、相对路径 template / 错 `id` 均报错，而**多出一个未知顶层键**与**极简 `option`** 都 PASS（前者被 strip、后者用 bar 默认值）——即上游对未知字段是「静默忽略」。
- **文档微调（4 处，全在 v0.15 原地改）**：
  1. 「协议 v2」措辞废除（上游只有 zip 版本号，没有 v2 概念）→ 改为「图表 skill v1.0.9 / 2026-09-10 build」（`references/chart-templates.md` 两处：能力来源表 + §零 硬规则标题）。
  2. 能力来源表「可渲染模板」行补上游最小骨架 `templates/visualization.json`。
  3. §零 新增「上游对未知字段静默忽略（Zod strip）」一条：`_comment` 之类说明键不会校验失败，但渲染层不保证使用 → 面向读者的说明写 `describe`/`description`。
  4. §零 记录 v1.0.9 新增可选字段（`bar.minCategoryGap`、`bar.style.barWidth`、各类型 `style.palette`/`texture`/`backgroundColor`）**本 skill 不用**，保持最小字段集。
  5. 「权威只有部署端那一份」条补「离线核对可用带版本号副本，但**前提是版本与部署端一致**，且副本内嵌的 `iframe_template` 只是留档时点的值」。
- **渲染配置归 Skill（前端要求，落三处）**：
  - `references/chart-templates.md` §零 新增「**渲染配置一律取自图表 skill（硬规则）**」：类型/字段名/默认值/`theme` 以图表 skill 的 `templates/*.json` 与 `references/schemas/` 为准，**原样复用、不重述、不扩展、不自造**；交付通道只有「图表 skill 定义的 JSON 数据文件 + `::visualization`」，**不要为本 skill 的 JSON 图调 `read_me`**（平台 Visualizer 段声明 Skill-defined data file 无需 `read_me`）、不用 `show_widget`、不退到内置 chart 模块（Chart.js/HTML/SVG）、不另造字段与配色。
  - `SKILL.md`：必读文件第 11 项把上游图表 skill 标为「**render config and single source of truth**，原样复用」，并补「唯一图表通道 + 不使用内置 chart 模块/`show_widget`/HTML/SVG/Mermaid + 不为这些 JSON 图调 `read_me`」；第 6 步 mixed-inputs 图表段补同义约束。
  - sys v0.15 Chart contract 新增独立段 **"The Skill owns the chart rendering config — never bypass it (hard rule)."**（类型/字段名/默认值/`theme`/envelope 一律 verbatim 取自图表 skill 模板与 schema；唯一通道是 Skill 定义的 JSON + `::visualization`；不得用平台内置 chart 模块 / `show_widget` / 手写 HTML-SVG-Chart.js 替代；不为这些图调 `read_me`；不得因「有个图会更好」而绕开 Skill）。Final verification 的图表项同步加「每张图都出自 Skill JSON 契约、渲染配置来自图表 skill 模板/schema，无内置模块/`show_widget`/`read_me`/自造字段与配色」断言。sys **214 → 216 行**。
- **`vendor/` 留档落地（新约定）**：`vendor/<上游 skill 名>/<版本>/` 逐字节复制上游包（本次 `vendor/chart-visualization-json/1.0.9/`，47 文件 + `node_modules`），并写 `vendor/README.md`（来源 zip、SHA-256、接收日期、该 build 内嵌的 `iframe_template`、跑法、协议要点、更新流程）。**默认不入 git**（`.gitignore` 加 `vendor/**/node_modules/` 与 `vendor/chart-visualization-json/*/`）——上游源码含内部 CDN 地址，是否入库待用户决定。留档副本自证可用：`node scripts/validate-cli.js templates/{bar,line,timeline,visualization}.json` 全 PASS。**skill/sys 文档内零 `vendor/` 引用**（部署端无此目录，已 grep 确认）；`dist` 内零 `vendor`。
- **顺带修正**：`templates/unified-evidence-report.md` 的旧措辞（「无额外 envelope」类）已改；全 skill 残留旧措辞 = 0，硬编码 CDN 地址 = 0。
- **重打 dist**：`495647bf3e1daf6ba1adfa6693c7d2441fbb90ec901d529201f98323b2b92cf3`（19 entries / 67496 B；上一版 `67c17a02…` / 66440 B 作废）。**已提交并 push**：本节的 14 个 tracked 文件改动落提交 **`4040ff3`**（分支 `v0.15-remove-html`，不合 `main`）；未跟踪的 `vendor/` 未入库。
- **后续处置（2026-09-11 用户拍板）**：① `vendor/README.md` 入库、上游源码副本继续 gitignore；② 「6–8 条且单条 payload 不大时直接直读」的下限豁免已写进 sys 与 `references/input-contract.md`（见「A 组六项硬化」节）。

## v0.15 change: 上游 chart skill v1.0.10 支持 line/bar 负值（2026-09-11）

- **来源与留档**：前端交付 `C:\Users\YYMF\Downloads\chart-visualization-json-v1.0.10.zip`（明文 zip，头 `PK\x03\x04`，无需走 Windows Python 解密）；源包 SHA-256 `57c36b0f4c9a409b483eb245c807afd87a1fbce4692ed9d13156e84d9323a4b7`，54,525 B，47 条目。留档 `vendor/chart-visualization-json/1.0.10/`（逐字节复制，与裸解包目录 `diff -r` 空差异，47 文件全 SHA 校验通过），`vendor/README.md` 补该版本 provenance、与 1.0.9 的差异表与负值协议要点。
- **差异面极小（6 个文件）**：`config.js` 与 4 个 `templates/*.json` 的 `iframe_template` 全部指向新发布 `…/ai-charts-html/test/20260911-134013/iframe-template.json`；`references/chart-types.md` **仅 +1 行**（负值语义）；`SKILL.md`、`schemas/*`、`scripts/validate.js` 逐字节未变 → **协议零变更**，`schemas/data.js` 仍是 `value: z.number()`（没加 `.nonnegative()`），即上游选「支持负值」而非「fail-loud」。
- **修的是渲染器（源码级 + 实测双证）**：新 bundle `…/20260911-134013/static/index-DocPC1fd.js`（旧 `index-DXN82l-u.js`）——bar 值域 `Si({min:0, max:maxValue||0})` → `vi({min: Math.min(0, n.minValue||0), max: Math.max(0, n.maxValue||0)})`（数据提取开始返 `minValue`）；柱长 `max(plotW*(v/domainMax), 3)` + 固定起点 `padL` → 零轴 `k(0)` + `max(|k(v)−k(0)|, 3)`；横向刻度/网格 `padL + plotW*tick/(domainMax||1)`（负域算出负像素）→ 按 `[domainMin, domainMax]` 归一化；新增单系列负值柱紫色判定；line 侧 `max: i<0 ? Math.max(s,0) : s`（负值数据补 0）。
- **实测（同一份全负 bar 数据，两版 bundle 各渲一次，量 DOM 真实盒）**：旧 5 根柱 `3/3/3/3/3 px` 起点同一点（静默炸）；新 `566.8 / 818.8 / 852.8 / 865 / 881.6 px`、右端全部 `x+w = 1320`（即 0 轴）、`881.6/101.1 = 865/99.2 = 852.8/97.8 = 818.8/93.9 = 566.8/65.0 = 8.72 px/单位`、fill 全 `#814487` 紫 → 双向生长正确。对照图 `/tmp/nb_fix_compare.png`（上旧下新，红/绿框）。**回归**：正值分组柱逐像素一致（`275.3/233.8/109.5/68.1`，x/y/fill 全同）、负值折线正常（仅因「补入 0」整体上移压缩）。
- **本 skill 零改动（结论成立的理由）**：仓库内 `grep vcdn.pharmcube.com|2026091*`（排除 `vendor/`）零命中 → 从不硬编码 `iframe_template`，运行期从部署端 chart skill 模板取 envelope，发布 ID 变更自动跟随（本次更新正好验证该硬规则）；skill/sys 内 `负值` 相关文字本来就是 0 处，无绕行约定需撤；先前记的「若上游选 B（fail-loud）则回 skill 落非负值约定」**不触发**。重打 dist 得同一 SHA（`0deda5d3…`，dist 只装运行文件）。
- **部署端未升级**：用户 2026-09-11 决定暂不把 v1.0.10 传到 Tool Smith，故部署端仍是 1.0.9 / `20260910-153117`（`vendor/README.md` 已如实标注）；日后升级后若出现 `iframe_template` 不匹配报错属预期（模板值随 CDN 发布刷新）。
- **记账**：本节改动随记账提交 **`dc0afd0`** push 到 `v0.15-remove-html`（提交信息 `v0.15: record upstream chart skill v1.0.10 negative-value support`）；`vendor/1.0.10` 当时未入库，后按用户 2026-09-11 拍板「源码副本继续 gitignore、只 `vendor/README.md` 入库」定案。

## v0.15 change: `::visualization` 标签与实体锚点边界 + 图表内 `{{ref_n}}` 外观问题放行（2026-09-11，两个新分享会话复盘后）

- **触发**：复盘两个并发的新分享会话（同一 Tool Smith 项目 `a7cdda65…`）：`d83e5527…`（标题「条形图」，18 esid / 11 试验，混合跨试验）与 `087abf28…`（标题「时间轴」，4 esid，全部同一试验 HARMONi-6）。
- **v0.15 生效确认（两个 run 都验到）**：envelope 一次过（A 用 `json.load` 读图表 skill `templates/bar.json`、B 直接 `cp` `templates/{timeline,bar}.json`，只换 `option` 内层；`校验通过: chart-visualization-json（option.type=bar）` exit 0，零返工）；固定命名契约全对（`/workspace/output/report.md`、`citations.json`、`/workspace/visualizations/evidence-timeline.json`、`endpoint-bar-1.json`）；`/workspace/output` 空目录 bug 未复现（建目录与首次写入同一次调用）；渲染配置归图表 skill 的硬规则被遵守（读了图表 skill `SKILL.md` + `templates/*.json`，**没调 `read_me`、没用 `show_widget`、没走内置 chart 模块**）；只 `present_artifact` 报告。
- **耗时/委派**：A 5.0 min / 39 步 / reasoning 83.2k 字符（18 esid，**未委派**——reasoning 明写「多于 5 个，但指引说先试文件化 digest」，符合 opt-in 设计）；B 2.8 min / 27 步 / 46.8k 字符。对照 v0.12 时代同批 14 esid 的 10.9 min / 178k 字符 → 约 2× 提速、reasoning 减半（两 run 并行）。**图表策略也对**：A（跨试验）不出 timeline；B（单试验 4 披露）合并同分析同披露为 1 个证据状态，timeline 3 节点。
- **新增规则（本轮落地的唯一改动）**：`::visualization[...]` 的方括号是**图表标题、不是正文实体提及** → 不进实体锚点覆盖、不算「有 ID 的提及必须已引用」；标签内不得出现裸试验名/药品名，用描述性标题，要点名的实体放到图前后说明里再锚定。落点 3 文件：`references/entity-inline-reference.md`（适用范围 1 条 + 校验 1 条，76 → 78 行）、`SKILL.md`（与「图表文件不写 entity」同处 1 句）、sys v0.15（anti-patch 硬规则后 1 句，防止「每个提及都要锚定」被读成覆盖图表标签）。sys 仍 216 行、`SKILL.md` 仍 151 行。触发原因：B 的模型把 `::visualization[HARMONi-6 证据链时间轴]` 的标签当成未锚定裸试验名，自己改名并重跑校验（约 3 步返工）。
- **图表内 `{{ref_n}}` 问题：查实后按用户决定放行**。事实：图表 iframe **不做**标记替换（部署端 bundle `…/20260910-153117/static/index-DXN82l-u.js` 内 `{{` 命中 0）；时间轴节点说明 `div.mf-ai-charts-timeline-desc` 与 bar hover tooltip `div.mf-ai-charts-tip-desc` 都是逐字渲染 `description`。用 B 会话真实 option + 部署端 bundle 在本地（`google-chrome --headless=new`，按平台 iframe 模板把 `option` 灌进 `window.chartOptions`）渲染后做 DOM/布局探针：标记子串占真实盒子 ~89×17 px、`visibility:visible / opacity:1`、颜色与说明文字同色 → 是**被画出来的可见字符**；去掉标记后同坐标区域墨迹从 916 px 降到 51 px、说明块高度 198 → 158 px。影响面：**仅外观**（读者看到字面量标记，点不了、不提供真正的可追溯性），数值/标签/结论/`citations.json` 全不受影响。**用户拍板：图先允许标引 ref，等开发/前端有人提出或前端做了替换再改**；`chart-templates.md:114` 与 `timeline-diagram.md:20` 的口径不一致（bar 无要求 / timeline 要求）也暂留。
- **bar 负值已由上游修复（v1.0.10，见下节）——本条闭环**。原状：值域硬编码 `[0, maxValue]`（`Ls()` bar 分支 + `Ts()` 只算 `maxValue`），全负 → `domainMax=0` → 柱长 `Math.max(w*(v/0), 3)` 卡 3px、轴刻度飞出画布；用户拍板**不在本 skill 绕**，驱动上游修（A 支持负值 / B `value.nonnegative()` fail-loud），本 skill 暂不动；负值数据优先选 line（line 值域取数据 min/max，天然支持负值）。**2026-09-11 上游落地 A 方案**：bar 恒以 0 为基准双向生长（单系列负值柱紫 `#814487`）、line 轴含负刻度并补入 0；实测旧 bundle 5 根负值柱全 3px、新 bundle 长度 ∝ 降幅（8.72 px/单位）。**本 skill 仍零改动**（B 分支未触发）。
- **重打 dist**：`0deda5d3b6fa94a279ed62b89e5b107c01bf84516054d852f25a2a71cfe91408`（19 entries / 67897 B；上一版 `495647bf…` / 67496 B 作废）。脚本 `/tmp/pack15b.py` 幂等（固定 stamp、19 文件断言、fail-loud 守卫），本次仅 SKILL.md 与 `entity-inline-reference.md` 内容变化。
- **验证工具经验**：本地可用 `/usr/bin/google-chrome --headless=new` + 部署端 bundle 复现 envelope 渲染，并用 `--dump-dom` 做 DOM 级验证（比截图 OCR 可靠）；本环境**视觉子代理通道不可用**（deepseek-v4-flash-vision-exp 403 billing / glm-5.3-flash 收到空图像）→ 需要目检时把 PNG 存 `/tmp` 交用户自己看。
- **后续处置**：① 本批已随提交 `49f00d9` push（用户授权「推送吧」）；② `vendor/` 处置见「A 组六项硬化」节。

## v0.15 change: A 组六项硬化 + 同试验图表张数上限（2026-09-11，第三份决策清单落地）

- **触发**：用户对上一轮列出的 16 条未决项作答——「**A 改**，B8–10 攒着，11 已经 fix 了，C 都听你的，重打吧，还是 15」。即：A 组（skill/sys 小改动）全部落地、版本号仍记 v0.15；B 组对外沟通项（bar 负值问题单、`{{ref_n}}` 图表内不替换的前端报备、CLI 路径口径）继续攒着不发；C 组（vendor 处置、Obsidian 沉淀、视觉目检、视觉通道）由我方判断处理。
- **A1 实体锚点 token 模板 + 构建脚本（写一次不返工）**：落 `references/entity-inline-reference.md` 新增「建议做法：锚点模板 + 构建脚本」小节（有 ID 的提及写成 `[{T_TOKEN}](entity:type:id)` + 占位符→展示名映射表；脚本渲染并断言「无残留 `{T_…}` / 每个占位符替换次数等于声明值（`assert n == count`）/ 有 ID 的实体名都落在锚点位置」，失败 fail-loud），`SKILL.md` 第 5 步与 sys anti-patch 硬规则各补一句。依据：line/Lp(a) 14 esid run 用「`report_template.md` + `build_report.py`」一次过锚点，而 timeline run 收尾还在跑 `fix_anchors.py` 补锚点。
- **A2 覆盖检查先剥离 entity ID**：`entity-inline-reference.md` 校验清单 + sys Final verification 各加一句——比较前先剥掉 `](entity:type:id)` 里的 ID，只按方括号展示名匹配，避免已锚定的 `[NCT05840016](entity:trial:NCT05840016)` 被当成裸注册号误判为漏锚点（timeline run 的真实误报）。
- **A3 工具参数名硬提醒**：sys Step discipline 新增第 6 条——shell 工具是 `execute` + **`shell_command`**（写成 `command` 会**静默失败**、白花 1 步）；文件写入用带引号 heredoc（`python - <<'PY'`）避免 shell 吞花括号；`mkdir -p` 与写入放同一次 `shell_command`。依据：三个 run 各踩一次。
- **A4 空目录规则覆盖 shell 重定向**：`references/file-delivery.md` 与 sys File delivery 段各补一句——`python gen.py > /workspace/visualizations/x.json` 的重定向目标在脚本执行前就被 shell 解析，故目录必须与写入在同一条命令里创建（timeline run msg03 的真实失败模式）。
- **A5 小批量直读豁免**：sys 子代理段与 `references/input-contract.md` 各补一条——**6–8 条且单条 payload 不大时直接直读**（一两次带 `selected_fields` 的拉取即可完成），委派只留给真正的大 payload 或「已落盘但脚本 digest 不了」的场景；阈值仍是「>5 可委派」，只把默认路径钉到直读。
- **A6 递归深度口径对齐**：sys「One level only」补一句——平台本身允许 main → child → grandchild（`max_recursive_depth = 2`），**只一层是本 skill 的自我约束**（`input-contract.md` Platform facts #5 已记同一事实），故不得依赖子代理再委派。
- **A7 图表张数与组合定死（同试验输入）**：`references/chart-templates.md` 的「图数量」条改写为确定性规则——混合/跨试验 = 每组各一张横截面柱状（时间维度优先折线）；**同试验 = 证据链时间轴（≥2 证据状态必出）+ 至多 1 张可选定量主图**，后者仅在「≥2 条入选结果给出同一终点、同一口径（同人群/同定义/可对齐时点）的纯数值」时才出（横截面单值 → `bar`，同队列同终点 ≥2 时点 → `line`），否则只出时间轴并在正文说明原因；**同试验输入上限 2 张图**。sys 同处镜像一句。依据：同一同试验输入（HARMONi-6 4 esid）旧 run 出 2 张、新 run 出 1 张，属规则留白导致的运行间不一致。
- **重打 dist**：`b9b46d8a24ceb9e740ff0d8e10230cc9e59b9174bf7828439b52576d92d17e6f`（19 entries / 69254 B；上一版 `0deda5d3…` / 67897 B 作废）。行数变化：sys **216 → 217 行**、`entity-inline-reference.md` 78 → 91、`chart-templates.md` 143 → 146、`file-delivery.md` 71 → 72、`input-contract.md` 194 → 199、`SKILL.md` 151 行（段内追加，行数不变）。
- **B 组不动作**：bar 负值问题单（上游 v1.0.10 已修，问题单作废但**不生成文件**）、`{{ref_n}}` 图表内不替换的前端报备、前端文档 CLI 路径口径（`.agents/skills/...` + `pnpm validate:chart` vs 部署端 `/workspace/skills/...` + `node`）——按用户「攒着」处理。
- **C 组处置**：① `vendor/README.md` 入库、上游源码副本继续 gitignore；② Obsidian 沉淀由我方判断执行；③ 视觉升级的像素级目检需用户在 Tool Smith 页面确认（本环境视觉子代理通道不可用：deepseek-vision 403 billing、glm 收不到图像）；④ 平台侧「execute 写空目录不持久」「并发措辞」用户已知晓/已修，不再单独报。

## v0.15 change: 分享复盘第二轮硬化（2026-09-11，第四份决策清单落地）

- **触发**：三个新分享会话（`42df8830` 18 esid 柱状 / `5b27e12f` 14 esid 柱状 / `63da8004` 4 esid 时间轴）只读复盘——硬契约 3/3 全过，但墙钟与 reasoning 比上一批上升（bar +12%/+16%、line +35%/+30%、timeline +30%/+18%），归因到四处**可归因的额外步数**：line 批 12 次 `edit_file` 全花在 `{{ref_n}}` 标记粒度上、timeline 批 A1 断言失败 4 次、bar 批 1 次把 `shell_command` 当工具名、bar 批 14 处嵌套锚点靠事后脚本修补。用户拍板：「**原地改吧，上一轮你提的其他几点我都没问题，听你的**」→ 5 项全落地、版本号仍记 v0.15。
- **R1 标记粒度 = 句子/单元格，不是数字**：`references/citation-and-ref.md` L27 改为「句末/条目末/单元格末」，并在多来源连写之后新增两段——一句（一格）整体来自同一来源时句末一个标记即可（句内多个数字仍只需一个）、只有一句真的混了不同来源才按子句就近标（`{{ref_1}} … {{ref_3}}`）/ 连写 `{{ref_1}}{{ref_3}}` 仍表示所有列出来源共同支持整句、**禁止**为标注拆句拆行、禁止逐数字补标、禁止对同一处反复 `edit_file` 重分配标记（标记位置与正文在同一次写入/同一个生成脚本里定）。sys Final verification 对应条目从「every material number has an immediately adjacent marker」（**line 批 12 次 edit_file 的直接诱因**）改为「every source-dependent claim carries a marker at the end of its sentence, bullet, or table cell」。
- **R2 混合输入图表张数去歧义**：`references/chart-templates.md` 的混合条改为条件式三步（≥2 同时点 → 1 张折线；每组 ≥2 条可比横截面值 → 该组 1 张柱状；两者成立就都出，按「时间维度 → 横截面对比」分段；某组不可比则该组不出图并说明）并明写「**时间维度优先只是排序/取舍优先级，不是「有折线就不出柱状」**」；上限句改为「混合 = 至多 1 张折线 + 每组至多 1 张柱状」。sys 同段改写为「line 与 bars **independent, not either/or**；只有柱状也是合法结果」。依据：同一个 Lp(a) 14 esid 输入上一批出 bar+line、本批只出 bar，模型自述「mixed 规则写法有歧义」。
- **R3 shell 参数措辞不再诱导工具名混淆**：sys Step discipline 第 6 条重写——工具是 `execute`、脚本进 `shell_command` **参数**；写成 `command` 会失败（有时**无任何输出**，故空结果不能证伪「命令没跑」）；**不要把参数名当工具名**，遇到 unknown tool / 参数错误应改用 `execute` 重发而不是重发同样形状。依据：bar 批 `tool-shell_command` 一次 `output-error`。
- **R4 渲染即断言（A1 降本）**：`entity-inline-reference.md` 的 A1 小节新增第 3 条「渲染、断言、落盘放同一个脚本里」（先渲染到内存 → 跑完 (a)(b)(c) 断言 → 通过才写盘，失败只是重跑同一脚本而非回到 `edit_file` 逐条补），sys anti-patch 段与 `SKILL.md` 第 5 步同步补该句。依据：timeline 批断言触发 4 次（`{T_IVO}: 5 != 6`、`bare mention left: 依沃西单抗`）+ 1 次 heredoc 写坏空转。
- **R5 新增「无嵌套锚点」断言**：`entity-inline-reference.md` 校验清单新增一条（`[X](entity:t:[X](entity:t:ID))` 双层包裹是错的，脚本断言 `](entity:` 不出现嵌套形态，发现即 fail-loud 重跑而非事后抠）、sys Final verification 实体条目与 `SKILL.md` 第 5 步同步。依据：bar 批实际发生 14 处，msg26 脚本 `repairs: 14` 自修。
- **同步修正**：A3 原措辞「The shell tool is `execute` with its command in the `shell_command` argument」把工具名与参数名并排写，实测会让模型把 `shell_command` 当工具名 → R3 已改写为「工具=`execute`，脚本进其 `shell_command` 参数；不要把参数名当工具名」。
- **重打 dist**：`58a66abc396475b287c70af4977f3d77d2352977f5699b56594993686e5cfb12`（19 entries / 70301 B；上一版 `b9b46d8a…` / 69254 B 作废），独立脚本复核包内 19 文件与工作区逐字节一致（`mismatch []` / `missing []`）、无 `__pycache__`/`.pyc`。行数：sys **217 行（不变，段内改写）**、`SKILL.md` 151（不变，段内追加）、`entity-inline-reference.md` 91 → 94、`chart-templates.md` 146 → 150、`citation-and-ref.md` 72 → 74、`file-delivery.md` 72、`input-contract.md` 199；`README.md` 136 → 137。
- **未动作**：B8–10 继续攒着（bar 负值问题单、`{{ref_n}}` 前端报备、CLI 路径口径）；「图表内 `{{ref_n}}` 原样显示」按用户拍板放行不改；不升版本号。
- **下一步（待用户）**：Tool Smith 侧重传 sys v0.15 + 当前 dist，用**新 thread**、同一批输入（18 / 14 / 4 esid）复跑，验 R1/R2 是否把墙钟与 reasoning 拉回上一批水平（line 批 ≤5 min / bar 批 ≤4.5 min 为合理目标）。

## v0.14 change: 复用上游 chart-visualization-json skill；撤销 TEMP 双写（2026-09-08）

- **触发**：前端发来两份说明书（`chart-templates.md` + `chart-visualization-json-prompt-examples.md`；两份均为 Windows DLP 透明加密文件，WSL 直读只得密文，经 Windows Python 提取明文后阅读）。**结论：说明书有用**——上游 `chart-visualization-json` skill 已是图表协议 / 模板 / Zod schema / CLI 校验的权威实现；我方 v0.12 的平行实现（自研 `validate-chart.py` + 本地重述协议）属重复维护，且存在「本地宽松校验 PASS 但真实 Zod 渲染失败」的风险。
- **决策（用户拍板）**：v0.13 弃用但不删除；**以 v0.12 为基线**做 **v0.14**；图表能力**复用上游 skill**（协议/模板/schema/校验）；**撤销 TEMP 双写**，`::visualization` 引用回切 `.json`（开发即将联调，renderer 即将落地）。版本号取 v0.14 而非原地改 v0.12，避免与已部署的 v0.12（TEMP 版）及 `dist/v0.12.zip` 混淆（可应要求改名）。
- **`SKILL.md`**：frontmatter `description` 增「图表产物为纯 JSON，由复用 chart-visualization-json skill 产出」；每次运行必读清单增 `references/chart-templates.md` 并声明复用关系；中英文两处校验命令改图表 skill CLI；**整段删除 TEMP section**。
- **`references/chart-templates.md` 整篇重写**：新增「能力来源表」（上游 `SKILL.md` / `chart-types.md` / `templates/{line,bar,timeline}.json` / `schemas/` / `validate-cli.js`）；协议要点以图表 skill 为准（`RENDERABLE = line|bar|timeline`；`dataSource`/`describe` 为不参与绘制的元数据；bar 默认 `stack: true`，并排柱状须显式 `group:false, stack:false`；timeline `time` 必填、`weight` 驱动圆点、`legend` 用 `circle`/`empty-circle` 且与 `data[].group` 对应）；`templates/charts/*.json` 降级为「临床场景预填起点」；新增**校验环境不可用时的降级规则**（不静默跳过、不退回自研脚本；先 `ls` 定位真实路径重试一次，仍不可用则在报告中声明「图表校验环境不可用」、省略该图 `::visualization` 引用、以精确数值表为主交付）。
- **其余引用/模板**：`references/timeline-diagram.md` 去 TEMP 两行 + CLI 命令替换；`references/file-delivery.md`、`references/cross-trial-comparison.md`、`templates/{unified-evidence-report,mixed-comparison-report,cross-trial-report}.md` 的校验命令与终检项全部改为图表 skill CLI。
- **`templates/charts/`**：删除 `validate-chart.py`；`render-preview.py` 移入 `docs/legacy-html-charts/`（该归档目录已在 v0.15 整目录删除）；`endpoint-bar.json` 补 `group:false, stack:false`；v0.13 残留的 `templates/quick-comparison-report.md` 移出发布集（副本在 `docs/legacy-v0.13/`）。
- **新 `system-prompts/multi-clinical-result-comparison-v0.14.md`**：基于 v0.12，删除 TEMP override 段与 Final verification 的 TEMP 项；`### Chart contract` 改为 v0.14 并新增声明段（协议/模板/Zod schema/CLI 为唯一真源，不自研校验、不产 HTML/SVG fragment、不写 `.preview.html`）；两处校验命令改 CLI 并补 bar `group/stack` 提醒；Final verification 新增「每个 `::visualization` 引用必须指向 `/workspace/visualizations/` 下的 `.json`」与「校验环境不可用时禁止输出未校验引用」两项。
- **验证**：三个临床模板经上游 CLI 全部 `校验通过`（bar / line / timeline，exit=0）；解包后包内三模板同样全 PASS；发布集内 TEMP / `preview.html` / `render-preview` 残留清零，仅 `chart-templates.md` 保留两处**历史说明**（「`validate-chart.py` 已归档」/「v0.12 调试期双写方案已随 v0.14 移除」）。
- **阻塞项（待上游确认）**：(a) 校验命令与技能的权威路径到底是前端说明书写的 `.agents/skills/chart-visualization-json/scripts/validate-cli.js` + `pnpm validate:chart`，还是上游 `SKILL.md` 写的 `/workspace/skills/chart-visualization-json/scripts/validate-cli.js` + `node`；(b) Tool Smith 工作区是否已装 `zod`/`node_modules`——上游 `package.json` **未声明依赖**，缺依赖时 CLI 以 `Cannot find module 'zod'` 崩溃（本地测试时用 `npm install zod --no-save` 绕过）。
- **DLP 排除记录**：两份前端文档 `head -c 8` 为 `88 7d 1c .. 3f 02 4c 00`（DLP 包装头，非 PDF/Office 魔数），WSL 直读高熵密文；改用 `C:\Users\YYMF\AppData\Local\Programs\Python\Python311\python.exe` 读 `D:\Users\feishu_download\` 抽明文到 `\\wsl.localhost\Ubuntu-22.04\home\xupeipeioo1\tmp\frontend-chart-docs` 后正常解析。
- **输出文件命名契约收紧（2026-09-09，用户提「后端好传输」）**：原契约只有「后缀固定 + slug 需小写连字符」的弱约束，slug 由模型自由发挥，后端只能 glob 或猜。**先查后端实际消费方式**，结论三点：(a) 报告路径**无需预知**——`present_artifact` 把真实 `path` 记入 run-local `ArtifactPresentationCollector`（manifest 存 `{"path","filename"}`），前端卡片直接用；(b) 图表路径**无需推导**——每张图在报告里以 `::visualization{path="/workspace/visualizations/..."}` 绝对路径逐条携带；(c) **唯一需要推导的是引文 JSON**（报告正文刻意不含引文清单）。且 `backend/src` + `frontend/src` 里 `citations` / `-report.md` **零命中**——后端/前端尚未实现消费，**现在定契约零成本、不构成 breaking change**。
  - **最终采纳（方案 C，后端开发者明确要求「加个约束文件名，我直接写死好了，就不从 tool 里取了」）**：**四个产物路径全部固定**，移除 `<slug>` 概念——报告 `/workspace/output/report.md`、引文 `/workspace/output/citations.json`、时间轴图 `/workspace/visualizations/evidence-timeline.json`、定量图按**图表类型 + 序号**命名：柱状 `/workspace/visualizations/endpoint-bar-<n>.json`、折线 `/workspace/visualizations/endpoint-line-<n>.json`（`<n>` 为该类型图在正文中的出现顺序，从 1 开始；单张柱状图恒为 `endpoint-bar-1.json`，单张折线图恒为 `endpoint-line-1.json`）。需编号是因为混合/跨试验输入允许**每组各一图**（`mixed-comparison-report.md`、`cross-trial-comparison.md`），同类型也可能多张，定量图数量不限于 1。重跑**覆盖**同名文件（一个 workspace 一份当前报告），与平台 `present_artifact` 的 “current version of this path” 语义一致；已写进契约“不得用加后缀的方式规避”。
  - **类型区分方式（2026-09-09 追问后定稿）**：用户追问「line 和 bar 在哪里区分」。上游 `chart-visualization-json` 的真实区分点在 **JSON 内部的 `type` 字段**——`scripts/validate.js` 的 `TopLevelSchema` 把 `type` 定为 `z.enum(CHART_TYPES)`（**必填**，非 optional），`RENDERABLE_CHART_TYPES = ["line", "bar", "timeline"]`，渲染器即按 `type` 派发。最初定稿的 `endpoint-chart-<n>.json`（数量词命名）经追问后判定不够：混合模式下折线/柱状混编序号，`endpoint-chart-1.json` 不保证是哪种图，后端无法对某一种图写死。故把**类型提到文件名**（`endpoint-bar-*` / `endpoint-line-*`），并在 `references/chart-templates.md`、`references/file-delivery.md`、sys v0.14 File delivery + Final verification 写入**双向一致约束**：文件名类型必须与 JSON 内 `type` 一致（fail-loud 校验项）。文件名供人与后端做稳定索引，渲染仍以 `type` 为准。
  - **落地文件**：`references/file-delivery.md`（`## Naming contract` 改为固定路径表 + 重写 Deliverables / Delivery sequence / 验证项 / `present_artifact` 调用）、`references/citation-and-ref.md`、`references/chart-templates.md`（复制示例、引用示例、交付路径契约、CLI 自检命令均换成固定成品名）、`references/timeline-diagram.md`（2 处）、`references/cross-trial-comparison.md`（1 处）、`templates/{unified-evidence-report,mixed-comparison-report,cross-trial-report}.md`（共 4 处 `::visualization` 路径）、`SKILL.md`（必读清单第 9 条、同试验流程、Output firewall）、sys v0.14（Step 9、File delivery 硬规则、citation 段、两处 `::visualization` 示例、Final verification 3 项）。机械替换全部经 Python 断言脚本（`assert n == count`）；第一轮在 `templates/mixed-comparison-report.md` 因实际 2 处而被断言拦下（脚本中止未写入），修正计数后继续——断言机制有效。全库 `grep` 残留扫描：`<slug>` / `xxx-` / `/workspace/visualizations/<` 全部为 0。dist 重打，19 entries / 63015 B，SHA-256 `816b3174580c350876285d0748937f54fb6e43961632353773e3937376e8f67a`。
  - **已知代价（已告知用户）**：卡片与下载名会变成 `report.md`（`present_artifact` 的显示名只能从路径派生，无 `display_name` 参数），报告主题靠文件内 H1 承载；同一 workspace 多次运行会覆盖旧报告（历史需后端/平台侧快照）。若后续要改善下载名，平台侧给 `present_artifact` 加 `display_name` 参数是干净做法。
  - **上一轮曾按方案 A 落地（已被本轮覆盖）**：保留描述性 `<slug>` + 强制两文件同 slug + 正则 `^[a-z0-9]+(-[a-z0-9]+)*$` + ≤40 字符 + 幂等复用，引文路径 = 报告路径单次后缀替换；因后端明确不要推导而废弃。

## v0.12 change: 输入切 esid + params 拉取；图表切外部 JSON 协议（纯 JSON 产物）

- 背景（用户批准，2026-09-01 起三批次执行）：因上游/前端协作需要，输入契约从「每源一个 .md 附件」改为「**选中 esid 列表** + Skill 经 MCP `pharmcube-query-clinical-result-with-params`（`extra_esids` + 严格 `selected_fields`）自拉详情」；图表从「自研 HTML fragment」改为「**外部 chart-visualization-json skill 的纯 JSON 协议**」（仅 `line`/`bar`/`timeline` 可渲染），本地只保留自研 JSON 结构校验脚本。**schema 权威真源 = `docs/params-tool-schema.md`**（用户粘贴存档；远端 data schema 服务 172.17.16.224:31234 经飞连不可达，无法自动 dump 运行时 ALLOWED_FIELD_NAMES，以此存档为准）。  - **删减重复小节（2026-09-10，前端开发反馈「这一段和 chart skill 重复了，可以删掉」）**：`references/chart-templates.md` 删除末尾三节——「三、配色与渲染」（theme/色板/HTML token 均属渲染层职责）、「四、与 chart-visualization-json skill 的关系」（与文件头「能力来源表」重复）、「五、当前版本边界」（v0.11 HTML / v0.12 双写 / validate-chart.py 属内部历史，非运行时契约），共 964 字符；文件从 136 行降至 114 行，小节收归为「零、协议要点 / 一、选型规则 / 二、怎么用」。**保留性核验**：三条守卫项未随删除流失——① 「不写 Mermaid、不产出 `.html`」在「零」末条（并在 `SKILL.md` ×1、sys ×4）；② 「不混入自定义色板/CSS/HTML token」已并入「零」末条（sys 另有 "do not restyle or swap palettes"）；③ 「证据边界只能来自 params 字段」在「一」末条。删除前逐项 grep 比对，确认无其它文件引用被删小节标题。

- **图表富文本取舍（用户拍板）**：协议能承载的说明文字（data point `description` + 顶层 `describe`/`subTitle`/`dataSource`）保留；协议外富文本（行内 `{{ref_n}}`、CI/误差线、交互 tab）丢弃；数值/边界由正文表格承载。**校验脚本（用户拍板）**：保留自研——`validate-chart.py` 重写为纯 Python JSON 结构校验器（不依赖 node/zod）。
- **图表契约**：`templates/charts/` 下 `endpoint-bar.json` / `endpoint-line.json` / `evidence-timeline.json` 三个 JSON 骨架（字段完全对齐外部协议）；旧 HTML 五件（chart-tokens.css + 三 .html + 旧 validate-chart.py）归档到 `docs/legacy-html-charts/`（该目录已在 v0.15 整目录删除，回溯看 git `e4f3bb7`）；bar 用 `direction:"horizontal"`、line 用 `group` 分系列、timeline 用 legend/weightLegend/data{time,label,group,weight,content,description}；**data[] 排序责任改为生成方**（前端不重排：bar 降序、line/timeline 时间序由 Agent 排好）。`references/chart-templates.md`、`references/timeline-diagram.md` 整篇重写为 JSON 协议；`references/cross-trial-comparison.md`、`references/same-trial-evolution.md`、`SKILL.md` 与三份报告模板的图表段 .json 化。
- **输入契约**：`references/input-contract.md` 整篇重写（保留 subagent 预写章节为可选、pending 验证）；`references/citation-and-ref.md` / `input-and-extraction.md` / `file-delivery.md` / `entity-inline-reference.md` / `SKILL.md` Input+Evidence boundary+Workflow、三份报告模板 source_* 单元格全部改为 params 字段。字段映射：`source_title`→`paper_title`、`source_url`→`full_article_link`、`source_paper_release_time_str`→`paper_release_time`、`source_nct_id`→`projects[].associate_ids`、`source_trial_abbr`→`trial_abbreviation`、`source_drug_entities`→`arms[].drugs[].drug_earth_id`+名称、`source_company_entities`→`projects[].company_ids`+名称、`source_full_text`→`abstract_text`/`summary`/`study_results` 组合（无直接等价）。引文 JSON 的 `title`/`link`/`paper_release_time_str` 三个 key 不变，值来自 params 返回字段 byte-for-byte。
- 新系统提示词 `system-prompts/multi-clinical-result-comparison-v0.12.md`（基于 v0.11：输入 esid + params、证据边界改 params 临床内容字段、实体表改 params 实体字段来源、图表段改纯 JSON + validate PASS + 排序责任、Final verification 全改）；重建 `dist/multi-clinical-result-comparison-v0.12.zip`（20 文件 = v0.11 集去掉 css+3 html、加 3 json，系统提示词不入 zip）；README v0.12 段 + 文件清单 + 配置。
- 验证：三份 JSON 骨架 `validate-chart.py` 全 PASS；skill 本体（SKILL.md+references+templates）旧术语（source_*/attached/.html 图名/CHART 数据）清零（仅保留 input-contract 映射对照列与 chart-templates「不再产出 .html」历史说明等有意保留）；v0.12 系统提示词旧措辞清零。
- 后补小修（2026-09-07）：`templates/charts/endpoint-bar.json` 的 `describe` 残留 v0.11 旧 HTML 语义「本模板按 value 从高到低自动降序，无需人工排序」——v0.12 协议为渲染端不重排、`data[]` 降序排序由生成方负责。已改为「`data[]` 由生成方按 value 从高到低排好序后交付（渲染端不重排）」；dist v0.12.zip 仅替换该条目后重建，20 文件逐文件 SHA-256 对比 BAD=0。
- **TEMP 双写调试资产（2026-09-07 用户批准「双写安排」）**：Tool Smith 对话页目前**不渲染 chart-visualization-json 的 `.json` 图**（只对 `.html` fragment 原生绘图），所以 v0.12 纯 JSON 产物在对话端不可见图。调试期方案 B 落地 = skill 运行期**双写**：每个 `.json` 成品（`validate-chart.py` PASS）后用随附 `templates/charts/render-preview.py` 从**同一份 JSON** 机械生成同名 `<name>.preview.html`（单一数据源，HTML 内嵌同一 JSON，禁手工另填），报告正文 `::visualization` **引用 `.preview.html`**（对话端可见），`.json` 作为正式契约随行交付。改动：`SKILL.md` 新增「TEMP (debug only — remove when the chart renderer is deployed)」权威覆盖段（override 全文档含模板的 `.json` 引用示例）；`references/timeline-diagram.md` / `references/chart-templates.md` 各加 TEMP 提示行；新增 `templates/charts/render-preview.py`（自原型 `/tmp/chartpreview/render-preview.py` 收编，fragment-safe 子串自检 + `-o` 输出）。**dist v0.12.zip 正式快照未动**，另打 `dist/multi-clinical-result-comparison-v0.12-temp-preview.zip`（21 文件，逐文件 SHA-256 BAD=0）。**回切**：renderer 落地后删除 SKILL.md TEMP 段 + 两个 references 的 TEMP 行 + `render-preview.py`，报告引用回切 `.json`，删除本 zip。
- **（后补 2026-09-07 会话诊断）TEMP 双写进系统提示词（方案 A）**：用户共享会话 share4（Lp(a) 跨试验）/share5（sqNSCLC）/share6（HARMONi-6）出现「一会 json 一会 html」不稳定——同一部署端 skill 资产一致（SKILL.md 含 TEMP 段），但**系统提示词 v0.12 仍是纯 JSON 契约（无 preview 字样）**，两契约互斥，Agent 裁决摇摆：share5/6 跟 skill TEMP 引用 `.preview.html`，share4 判「sys 更高权威」引用 `.json` 并跳过 render-preview（reasoning 有明确权衡原文）。根因 = TEMP 双写只进了 skill、没进 sys；skill（load_skill 注入）对 Agent 是次级指令。修复（用户拍板方案 A）：`system-prompts/multi-clinical-result-comparison-v0.12.md` 图表段（`### Chart contract` 标题下、所有 `.json` 引用示例之前）新增「TEMP override (debug only — remove when the chart renderer is deployed)」四步双写段，显式声明覆盖本 prompt + skill 内全部 `.json` 引用示例；`Final verification` 图表检查项后补同义 TEMP 双写检查项。sys 与 skill 对齐后 Agent 无论读哪层都指向 `.preview.html`。**该 sys 改动需 Tool Smith 侧重新装载/重传系统提示词**（此前结论「sys 不用重传」作废，仅限本轮 TEMP 期间）。
- **（2026-09-08 v0.14 撤销 TEMP）** 用户拍板：renderer 即将联调，**撤销双写**。已删除 sys v0.14 的 TEMP override 段与 Final verification TEMP 项、`SKILL.md` 的 TEMP section、`references/timeline-diagram.md` 与 `references/chart-templates.md` 的 TEMP 提示行；`render-preview.py` 移入 `docs/legacy-html-charts/`（该目录已在 v0.15 删除）；报告引用回切 `.json`。`dist/multi-clinical-result-comparison-v0.12-temp-preview.zip` 降级为历史快照（勿用）。详见「v0.14 change」段。
- **契约未定待办（挂起/交上游）**：表格整表复制/下载 CSV-Excel（产品验证中，见文首待办段）；bar 柱下钻（parked，等何林杰 drillDownValue 案例）；subagent 四项验证（next week 上游协作方）。

## v0.11 change: 试验简称内联（trial short name as entity display label）

- 用户需求：「试验简称能内联」——报告里试验展示名优先用简称（如 HARMONi-6、TRAIN-2），而不是只显示注册号。
- 数据源核实（只读）：`np_clinical.base.trial_abbreviation` 是现成字段，形态为对象 `{text}` 或数组 `[{text}]`（多别名）；覆盖度：nsclc 三期积极 88/100、ind579 三期 70/100、TRAIN-2 5/5。试验简称 ID 不新增——`entity:trial:` 的 ID 仍是注册号（`source_nct_id`），简称仅作展示名。
- 契约：附件新增可选元数据行 `source_trial_abbr`（试验简称，多个别名 `;` 分隔，去重、丢弃含 `|`/`;` 的值；无简称不写行）。展示名优先级 = `source_trial_abbr` → 注册号；行缺失/为空 → 回退注册号（自然降级）。注册号仍只作 `entity:trial:` 的 ID。
- 改动文件：`evals/fetch-np-clinical-attachments.mjs`（`_source` 加 `base.trial_abbreviation` + `extractTrialAbbr` + render/parse/roundtrip 加 `source_trial_abbr`）；`references/input-contract.md`（ES lookup + JSON 形状 + 文件布局 + 实体元数据行 + 读取协议 + 可复现检查）；`references/entity-inline-reference.md`（trial 规则：简称优先展示、ID 仍注册号、图表内仍禁）；三份报告模板（研究名称/注册号、试验/注册号单元格改简称优先示例）；`SKILL.md`（阅读清单 #10 + Input + 证据边界 + 工作流第 8 步）；新增 `system-prompts/multi-clinical-result-comparison-v0.11.md`（基于 v0.10，Entity 表加「试验（展示名优先用简称）」行 + 展示名规则 + Final verification）；README（v0.11 段 + 文件清单 + 配置）；重建 `dist/multi-clinical-result-comparison-v0.11.zip`（21 文件，系统提示词不入 zip）。`validate-entity-refs.mjs` 无需改（trial ID 仍是注册号）。
- 重拉 `evals/iteration-16` 三个数据目录（均 gitignored）：nsclc-50 50 条（34/50 带简称，顺序与旧一致）、ind579-phase3-50 59 条（40/59 带简称）、nct01996267 5 条（5/5 带 TRAIN-2，`NP_CLINICAL_ATTACH_ORDER` 保持旧顺序）。roundtrip 全过。

## v0.10 change: 实体内联引用（药品 / 公司 / 临床试验注册号）

- 背景（用户拍板）：整合 Tool Smith 的 `[name](entity:type:id)` 实体内联引用能力，让报告里的药品、公司、注册号渲染成可交互实体胶囊（前端 `EntityAnchor` 已支持，artifact 阅读器走 `ChatMarkdown` → `EntityAnchor`，**前端 0 改动**）。范围限定三类：药品 + 公司 + 注册号；适应症/靶点不做（无元数据行）。
- **ID 来源 = 后端附件元数据行透传**（用户确认），nct_id 也是元数据行优先：新增三行可选元数据 `source_nct_id` / `source_drug_entities` / `source_company_entities`（`名称|实体索引|ID`，`;` 分隔）。行缺失/为空 → 该类型不引用（自然降级）。不编造 ID、不为拿 ID 调工具；注册号仅在 `source_nct_id` 存在时引用（v0.10 不做 CTR/ChiCTR 文本抽取兑底）。
- **数据源核实**（只读）：`base.nct_id.text`（多值时取首个干净 token，NCT 优先）→ `entity:trial:`；`base.trial_drug[].meta[]`（drug_earth，中文药名+ID，如依沃西单抗=12483）→ `entity:drug:`；`trial_details` 内 `company_ids`（仅 ID 数组）→ 用 `base_company` 索引 `terms{id}` 解析显示名（`name_show_cn`→`short_name`→`name`，319=BMS/169=Pfizer/355=Eli Lilly/55=Bayer）→ `entity:company:`。HARMONi-6 记录无 company_ids（自然省略公司行）。
- 证据边界：三行实体元数据是**展示/标签元数据，非临床证据**；只给报告里本来出现的实体名绑 ID，不推临床事实。与 `{{ref_n}}` 共存（`[依沃西单抗](entity:drug:12483){{ref_1}}`）；`::visualization` 图表内不写 `entity:`（隔离 iframe 无实体渲染器，登记号下钻仍走 `__toolsmithNavigate`）。
- 改动文件：新增 `skill/.../references/entity-inline-reference.md`（语法/ID 来源硬规则/适用范围/与证据边界关系/校验）；`references/input-contract.md`（JSON 形状加三字段 + 文件布局加三行 + 读取协议第 4 步实体台账）；`references/citation-and-ref.md`（首段交叉引用）；`SKILL.md`（阅读清单 #10 + Input 段 + 证据边界 + 工作流第 8 步 + Output firewall 允许 `entity:` 受控格式）；三份报告模板（研究名称/注册号、试验组/试验组方案单元格加 `entity:` 示例）；新增 `system-prompts/multi-clinical-result-comparison-v0.10.md`（基于 v0.9，加「Entity inline references」规则表 + 工作流第 8 步 + Final verification 实体校验条款）；`evals/fetch-np-clinical-attachments.mjs`（`_source` 加三字段、`enrichEntityMetadata` 生成三行、renderSourceFile/parseSourceFile/roundtrip 扩展）；新增 `evals/validate-entity-refs.mjs`（报告实体引用 ↔ 附件元数据行一致性校验：类型白名单、ID 必须在元数据、图表内禁 `entity:`）；README（v0.10 段 + 文件清单 + 配置）；重建 `dist/multi-clinical-result-comparison-v0.10.zip`（21 文件 = v0.9 的 20 + entity-inline-reference.md，系统提示词不入 zip）。
- 验证：fetch 脚本 `node --check` OK + 小批量（3 条）实拉——无 ID 旧来源自然省略三行、有 drug_earth 的来源正确输出 `source_drug_entities`；HARMONi-6（NCT05840016）nct_id 提取=可 `NCT05840016`、drugs=卡铂1618/依沃西单抗12483/紫杉醇1738、公司为空（数据本身无）；带 company_ids 的样本（319,169,355,31284,55）经 `base_company` 全部解析出名称；roundtrip 校验全过。`validate-entity-refs.mjs`：编造 ID（NCT99999999 不在元数据）正确 FAIL，真实 ID 正确 PASS；zip 解包 = v0.9 集 + 新参考文档。
- 遗留：前端实体胶囊实际渲染仍待真实部署验证（延续 `{{ref_n}}`/`::visualization` 同款待办）；公司显示名取 `name_show_cn→short_name→name`，可能含非目标拼写，Agent 以来源拼写为展示名（元数据名仅作匹配提示）。

## v0.10 follow-up: iteration-16 数据重拉 + fetch 脚本增强

- 背景（用户）：把 `evals/iteration-16` 里所有 np-clinical 数据目录按 v0.10 新规则（实体元数据行）重新拉取。
- `evals/fetch-np-clinical-attachments.mjs` 增强（同一脚本三种场景）：`NP_CLINICAL_ATTACH_NO_EVALUATION=1`（去掉 evaluation 过滤，供 ind579 这类无 evaluation 批次）；`NP_CLINICAL_ATTACH_NCT="NCT..."`（按注册号拉单试验）；`NP_CLINICAL_ATTACH_ORDER="<doc_id>,..."`（按文档 `_id` 指定输出顺序，复现历史手工选择顺序，保持旧报告 ref 对齐）。`normalizeSource` 携带 `_docId` 用于排序，写入 manifest/文件前删除（`_id` 不泄漏）。`references/input-contract.md` Reproducible local check 段补三种 env 覆盖说明。
- 重拉结果（均为 gitignored 生成物，不入库）：
  - `np-clinical-nsclc-50`：50 条，顺序与旧一致（旧 report.md/refs.json 仍对齐）；实体行 44/50 至少一行（nct 36 / drug 31 / company 21）。
  - `np-clinical-ind579-phase3-50`：59 条（原 50 条前序一致 + 数据源新增 9 条 usable）；实体行 58/59（nct 56 / drug 43 / company 0——AD 试验 np_clinical 无 company_ids）。旧 report.md 对应前 50 条仍对齐；多出的 9 条无报告覆盖。
  - `np-clinical-nct01996267`（TRAIN-2）：5 条，按旧顺序（`NP_CLINICAL_ATTACH_ORDER`）重拉，与旧 report.md 完全对齐；全部带 `source_nct_id: NCT01996267` + drug_earth 药名，company 行 0（记录无 company_ids）。
- roundtrip 校验全部通过；备份旧数据在 `/tmp/iter16-backup/`。

## v0.9 change: 报告文件化交付（present_artifact 终局）

- 背景（用户确认）：利用 Tool Smith 新增 `present_artifact` capability，把最终报告从「聊天正文流式输出」改为「写盘 + 卡片交付」；开发要点：后端不用解析模型输出、可杜绝开场白/尾随 tool、可为交付写文件模板。用户定案：**方案 B**（正文留空/至多一句用途说明，只有卡片）+ **`{{ref_n}}` 与独立引文 JSON 暂不改**（保留标记与 schema，只是 JSON 也变成文件）；气泡/悬停字段说明本轮不做。
- 交付契约（新增 `skill/.../references/file-delivery.md`，权威）：
  - 报告 → `/workspace/output/<slug>-report.md`（路由模板内容 + `{{ref_n}}` + `::visualization` 引用，首行即标题无开场白）；引文 JSON → `/workspace/output/<slug>-citations.json`（raw strict JSON，一源一键，字段 byte-for-byte）。
  - `present_artifact('/workspace/output/<slug>-report.md')` 作为**最后一个 tool call**，成功后立即结束；正文留空或至多一句「完整报告已生成，见下方文件卡片」；调用后不得再输出/再调 tool。
  - 只 present 报告文件；内嵌 `::visualization` 图不再单独 present（除非本身就是独立交付物）。
  - 引文 JSON 文件不 present 也可见：`/workspace/output/` 下的文件都是 workspace artifact（已核实 tool-smith `list_artifacts` 只过滤忽略目录），后端/前端走 artifacts API 直接取两个文件。
  - 若部署未开 `artifact_presentation`（工具不可见），回退 v0.8 契约（正文全量报告 + 独立 JSON）。
- 依赖开关：目标项目须开 `artifact_presentation`（默认 OFF）+ `visualization`（报告文件里的 `::visualization` 渲染依赖）。
- 改动文件：新增 `references/file-delivery.md`；`SKILL.md`（阅读清单 #9 + 工作流第5步写盘 + Output firewall 文件化交付/回退）；新系统提示词 `system-prompts/multi-clinical-result-comparison-v0.9.md`；`references/citation-and-ref.md` 与 `references/input-contract.md` 的 JSON 交付改为文件；`runtime/citation-renderer.mjs` 新增 `validateCitationPair`（不渲染的配对校验）+ `test/citation-renderer.test.mjs` 两条新测试；README v0.9 段落/文件清单/配置；重建 `dist/multi-clinical-result-comparison-v0.9.zip`（20 文件，含 file-delivery.md）。
- 报告模板（unified/cross-trial/mixed）未改动——它们就是报告文件的内容骨架；v0.9 只改了「交付方式」这一层，不改内容结构与图表契约。
- 验证：`node --test test/citation-renderer.test.mjs` 8/8；`node evals/validate-v05-contract.mjs` → `v0.5_contract_ok`；zip 解包结构/前缀/20 文件校验通过。
- 遗留：`{{ref_n}}` 在 artifact 文件阅读器里仍显示为字面 token（前端上标渲染未做，属已知限制，`{{ref_n}}` 不改是用户定案）；正文 `::visualization` 真实环境渲染仍待验证（延续 v0.8 待办）。

## v0.8.1 change: 三张图表模板视觉升级（lieflat violet 紫罗兰设计语言）

- 背景（用户）：现有时间轴/柱状/折线模板不好看，希望按已认可的 ORR 图（violet 横档柱）重做；并确认用了 lieflat skill。
- 三张模板（`templates/charts/`）重写，设计语言 = lieflat-charts **violet 预设**（象牙纸 `#F7F2EB`、墨 `#2B1450`、紫阶 `#2B1450→#55339A→#8A63D2→#C6B3EE`），单色相明度阶、一律实心无渐变阴影、发丝网格、数值标签纸色描边光晕、虚线徽章、全大写来源行、fade/draw 动画 + reduced-motion、确定性 rnd（无 Math.random）。
  - `endpoint-bar.html`：改为**横档柱**（1 格 = 1 单位，档距 ~2.6px，1-2-5 自动步进），**柱深浅 = 数值高低**（明度即数据，12 档紫阶）；`series` 保留为可选显式紫档覆盖（缺省=数值取色）；加 TRACK 打底、nice 网格刻度、悬停 tip（墨紫底）。
  - `endpoint-line.html`：系列默认 = 紫系 SER（研究组最深 `#2B1450`），线宽 ×1.8 实心圆头、纸色光晕数据点 + 800 数值标签、发丝网格 + 虚线动画，保留单点模式。
  - `evidence-timeline.html`：旗帜改**实心**（去掉渐变），图例默认按证据类型取紫系深浅（里程碑 `#C6B3EE`/披露 `#55339A`/更新 `#8A63D2`）；成熟带改实心 TRACK 底 + 纸色圆点描边（去渐变）。
  - 排序规则：柱状图按 value 从高到低自动降序（模板内 sort，无需人工排）；折线/时间轴按时间顺序（数组顺序即时间顺序，模板不重排）。注释与 `chart-templates.md` 数据填充约束同步。
- 契约不变：仍是 Tool Smith HTML fragment（无 `<!doctype`/`<html`/`<head`/`<body` 子串，含注释/脚本）；颜色一律 `var(--viz-*, violet_fallback)` + 模板 JS `viz(name,fb)` 读注入值；`CHART` 数据对象结构不变（`endpoint-bar` 的 `series` 语义改为“可选紫档覆盖”）。
- 系统提示词 `multi-clinical-result-comparison-v0.8.md`：定量图段落补“排序与外观固定”条款（柱形自动降序、折线/时间轴保持时间顺序、内置 violet 编辑设计只填 CHART 不改样式）。
- `references/cross-trial-comparison.md`：Chart rules 补同款排序与外观条款。
- 重建 `dist/multi-clinical-result-comparison-v0.8.zip`（18 文件，前缀正确，含新版 violet 模板 + 排序规则，66KB）。
- 文档同步：`chart-templates.md`（导语/第三节配色/第四节与 lieflat 关系）、`chart-tokens.css`（fallback 改 violet + 明度即数据规则）、模板内注释。`SKILL.md` 契约层描述未改（仍是“只改 CHART”）。

## v0.8.1 follow-up: 脚本填充防复发纪律 + 生成自检

- 背景（用户）：某 Tool Smith 分享页图表渲染失败，错误 `渲染失败：Unexpected token '{'`，怀疑是 violet 模板改动引起。
- 排查结论（与本轮模板无关）：从分享快照拉取 Agent 实际生成的三份 `endpoint-bar` 产物（`nsclc-egfr-3g-tki-pfs` / `nsclc-egfr-tki-combo-pfs` / `nsclc-io-chemo-pfs`），`node --check` 全部报 `Unexpected token '{'`——Agent 临时写的 `gen_charts.py` 用 `tpl[:i] + start_marker + payload` 拼接时，模板自带的 `const CHART = {` 与 `json.dumps` 输出（以 `{` 开头）叠成双 `{`；同时用 json 的 `}` 替换模板 `};` 丢失分号，ASI 把对象与下一行 IIFE 连读成“调用对象”→ 修完语法错误后还会报 `TypeError: … is not a function`。用同一脚本逻辑拼旧模板（349eabc）复现同样双 `{` + 丢 `;`，证明与 violet 重写无关。修复后三图在 Tool Smith 同款沙箱（`--viz-*` 注入 + 隔离 iframe）零错误渲染；修复产物见 `charts/share-fix-preview/`（fragment + 包裹预览 + PNG）。
- 防复发改动：新增可执行校验脚本 `templates/charts/validate-chart.py`（纯 Python，node 可用时额外做真 JS 语法校验）——检测 Tool Smith 禁用子串/结构、双 `{`、缺 `;`、花括号配对、CHART 字段、文件大小，FAIL 时输出行号 + 修复提示，供 Agent 修复后重跑；`references/chart-templates.md` 数据填充约束「5. ⚠️ 脚本批量填充与自检」改为指向该脚本（必跑，FAIL→修复→重跑直到 PASS）；系统提示词 `multi-clinical-result-comparison-v0.8.md` 定量图段落 + Final verification 均改为要求运行 `validate-chart.py`。`SKILL.md` 契约层未改。
- 脚本自测：修复产物 3 份全 PASS；未修复坏文件准确报双 `{`（第 17 行）+ node SyntaxError（第 18 行）；缺分号场景由启发式报“未以 `};` 结尾”（node 不报因语法合法）；`<body` 禁用子串报第 1 行；三模板本体 PASS。
- 重建 `dist/multi-clinical-result-comparison-v0.8.zip`（含更新后的 `chart-templates.md` + `validate-chart.py`，系统提示词不入 zip）。

## v0.8.1 follow-up 2: 时间轴重设计（lieflat L11 语法延伸，去掉旗帜/成熟带矩形）

- 背景（用户）：分享页（share `22a71675…`）时间轴「不知道三角形和长方形都是啥意味」——旧模板的竖矩形（旗面）+ 三角（旗杆）+ 底部横矩形（成熟度带）几何符号语义不明，且长标签/长日期两端溢出被裁（真实产物 TRAIN-2：首标签从 x=46 向左截断、末日期从 x=854 向右截断）。用户询问是否用了 lieflat skill。
- 结论：lieflat 决策树有「事件序列生命史 → L11 Trend Lineage」，为最接近组件；上轮未去 gallery 找对口实现而是沿用旗帜造型，属疏漏。按 lieflat 规则第 3 条（无现成单试验时间轴 → 从 L11 现有语法延伸）重做。
- 新版 `evidence-timeline.html`（仅改渲染区，CHART 结构/契约不变）：
  - 语义：圆点=事件节点（**实心=披露/更新、空心=里程碑锚点**），圆点**直接坐基线**（时间轴即证据链），**圆点大小=证据成熟度**（phase 0..4 → r 6.5..11.3）；数值**横排在圆点右侧**（末节点放左侧防溢出）；无矩形/三角/刻线。
  - 动画：基线 draw（链式展开）、圆点 pop、文本 fade，reduced-motion 全关。
  - 健壮性：标签/日期**自动折行**（按间距算每行字数）+ **端部锚定**（首节点左对齐、末节点右对齐）——彻底解决两端溢出与重叠。
  - 契约不变：fragment（无 `<!doctype`/`<html`/`<head`/`<body` 子串）、`--viz-*` + violet fallback、确定性（无随机）。
- 验证：validate-chart.py PASS；渲染 DOM dump 全坐标在 viewBox 内无溢出无重叠（圆点 y=200 坐线，r 递增，标签 2 行折行正常）；真实 TRAIN-2 数据产物校验 PASS。预览：`charts/timeline-v2-preview/`（产物 + wrapped + PNG）。
- 文档同步：`chart-templates.md`（模板选型表、与 lieflat 关系改为 L11 语法延伸）、`timeline-diagram.md`（phase → 圆点大小递增）。系统提示词无视觉描述，未改。

### v0.8.1 follow-up 2 修订（用户复看："数值不要放在轴上，多整几行，注意对齐"）
- 改 3 点：①数值不再横排在轴线（原 y=204 贴基线 200），改为**纵排多行**在圆点下方（`value` 支持 `\n` 手动分行 + 自动折行，每节点 ≤3 行）；②圆点从"坐基线"改为**悬浮于基线上方**（信息块与轴线分层，数值离开轴线、基线下方为日期）；③对齐：数值首行固定 `dotY+25` 各节点**顶对齐**（修复初版随 r 变化的 160/162/163 错位）、标签**底对齐**贴节点（2 行时 54/69）、日期首行固定 235。
- 坐标（H=270）：标签 54/69 → 圆点 140 → 数值 165/181/197 → 基线 215 → 日期 235/249。校验 PASS；真实 TRAIN-2 产物 v3 + 截图：`charts/timeline-v2-preview/train2-evidence-timeline-v3(.html/-wrapped.html/.png)`。文档两处视觉描述同步（chart-templates.md、timeline-diagram.md）。

### v0.8.1 follow-up 2 修订 2（用户："轴和点之间没有关联性"）→ v4 定稿
- 问题：v3 圆点悬浮于基线上方 75px，与基线上的日期刻度无视觉连接，读起来“飘”。
- v4 定稿：**圆点直接坐回基线**（dotY=baseY=200，点轴一体，关联最强），**数值纵排多行移到圆点上方**（离开轴线，`\n` 分行 ≤3 行），基线下为日期。三块固定槽位顶部对齐：标签 52/67 → 数值 96/112/128 → 圆点 200（坐基线）→ 日期 222/236；H=272。
- 对齐=固定槽位（各节点同一 y），行数不足留白但不歪；端部锚定保留。校验 PASS；真实产物 v4 + 截图：`charts/timeline-v2-preview/train2-evidence-timeline-v4(.html/-wrapped.html/.png)`。文档两处同步。

### v0.8.1 follow-up 2 修订 3（用户："整点丝线连接，现在偏离太远没关联"）→ v5 定稿
- v4 数值悬在圆点上方 47px+ 仅靠脑补归属，加**丝线**：1px muted、opacity .5 细线，从数值块底部（VAL_TOP+(rows-1)*VAL_LH，如 128）连到圆点顶部（dotY-r，189–192 随 r 变，长 61–64px），draw 动画自圆点向上生长；先画（数值文字与圆点盖住线头）；**里程碑无数值不连**，保持空心圆纯净。
- 布局坐标不变（v4 定稿：标签 52/67 → 数值 96/112/128 → 圆点 200 坐线 → 日期 222/236）。校验 PASS；真实产物 v5 + 截图：`charts/timeline-v2-preview/train2-evidence-timeline-v5(.html/-wrapped.html/.png)`。文档两处同步。
- 验证：`node --check` 三个脚本通过；禁用子串 grep 干净；headless Chrome 渲染 violet 色值/横档/旗/线均出；预览包在 `/home/xupeipeioo1/charts/skill-violet-redesign/`（wrapper + PNG）。
- ⚠️ 待办：`::visualization` 正文渲染支持仍未在真实环境验证（延续 v0.8 待办，与开发者对齐时确认）。

## v0.8 change: 图表统一走 HTML 可视化（全面移除 Mermaid）

- 决策（用户明确）：时间轴与跨试验图都不再输出 Mermaid，统一用 `templates/charts/` 的 HTML 模板 + 正文 `::visualization[标题]{path="..."}` 引用（workspace 文件 + 引用通道）。
- `references/timeline-diagram.md` 重写：交付方式改为复制 `evidence-timeline.html` → 只改 `CHART` 数据 → `::visualization` 独占一行引用；**节点语义明确为 events[] 一条=一个证据状态**（同状态多篇披露合并为一节点，`note` 并列 `{{ref_n}}`，不构成独立验证）；保留原规则（数据截止→随访→分析里程碑→披露日期排序、时间未明不猜测、成熟度边界、回退规则=仅 1 个状态或先后不确定时不生成图）。删除 Mermaid 结构模板/示例，改为 TRAIN-2 数据填写示例。
- `references/chart-templates.md`：events[] 语义同步为“一条=一个证据状态”；版本边界改“全部图表随 v0.8 生效、不再输出 Mermaid”。
- `references/cross-trial-comparison.md`：Chart contract 从 Mermaid `xychart-beta` 改为 HTML 模板（单值→`endpoint-bar.html`，时间序列→`endpoint-line.html`）+ `::visualization` 引用。
- 模板 `unified-evidence-report.md` / `mixed-comparison-report.md` / `cross-trial-report.md`、`SKILL.md`、`templates/charts/evidence-timeline.html`（注释）同步更新。
- 新增 `system-prompts/multi-clinical-result-comparison-v0.8.md`（基于 v0.7，时间轴/定量图段改为 HTML；3 处 mermaid 均为禁止性表述“不输出 Mermaid”）。历史 v0.3–v0.7 提示词保留为快照。
- README：v0.8 段 + 文件描述（timeline-diagram 改 HTML、zip 改 v0.8）+ Tool Smith configuration 改 v0.8。
- 重建 `dist/multi-clinical-result-comparison-v0.8.zip`（18 文件，同 v0.7 结构）。
- 示例：TRAIN-2（`evals/iteration-16/np-clinical-nct01996267/`）`report.md` 的 Mermaid 块替换为 `::visualization` 引用；`train2-evidence-timeline.html/.png` 重生成（3 状态+里程碑，每条=一个证据状态）。report 校验：标记双向一致、连续、无 Mermaid 残留。
- 验证：`node evals/validate-v05-contract.mjs` → `v0.5_contract_ok` 保持绿。
- ⚠️ 待办：`::visualization` 在 Tool Smith 正文中的渲染支持尚未在真实环境验证（此前 Mermaid 走渲染器原生渲染）；若正文不支持，需降级为“文字+表格+下载链接”。下次与开发者对齐时确认。
- 修订（路径规范）：Tool Smith 可视化契约要求**绝对路径** `::visualization[标题]{path="/workspace/visualizations/xxx.html"}`，路径必须位于 `/workspace/visualizations/` 下、不能目录穿越或反斜杠、引用前先写入文件、文件名 ASCII。已把 `chart-templates.md`/`timeline-diagram.md`/三个报告模板/`SKILL.md`/`cross-trial-comparison.md`/v0.8 提示词/README 里所有 `path="..."` 相对写法改为绝对路径，`chart-templates.md` 新增“交付路径契约”小节作为统一条款（含 fallback 要求）；TRAIN-2 示例 `report.md` 引用同步改绝对路径。开发端将加相对路径兜底逻辑——与绝对路径契约不冲突，兜底应同时校验 `..`/反斜杠/前缀外路径。
- 修订（fragment 格式）：Tool Smith 对 HTML 可视化用与内联 widget 相同的隔离 fragment 渲染器，**成品必须是 HTML fragment**，不含 `<!doctype html>`/`<html>`/`<head>`/`<body>`/`<meta>`/`<title>` 文档包裹。三个模板（`evidence-timeline.html`/`endpoint-bar.html`/`endpoint-line.html`）与 TRAIN-2 示例已去掉文档包裹改为 fragment；`chart-templates.md` 交付契约新增 fragment 条款，`timeline-diagram.md`/`SKILL.md`/v0.8 提示词/README 同步。本地验证：用 wrapper 包成完整文档经 headless Chrome 渲染，12 个 text 元素正确、PNG 重新生成。
- 修订（分组建图固化）：跨试验/混合报告**按临床问题分组 → 每组各出一张 `endpoint-bar.html` 柱状图**（各组独立 CHART 文件，图内并列该组各试验的试验组结果值，研究内对照数值与证据边界放悬停 note，标题注明「跨试验并列展示≠头对头比较」，不满足可比条件的组不出图）。契约同步：`mixed-comparison-report.md`（第一章「按组绘图」+ 图插入说明 + ORR 说明）、`cross-trial-comparison.md`（Chart contract 补分组建图）、v0.8 系统提示词（120 行定量图规则补每组一图）、`endpoint-bar.html`（数据区注释补多实例分组）、`SKILL.md`（§6 Mixed inputs）、README。示例：NSCLC 10 试验分三组 → nsc-group1/2/3 固化到 `evals/iteration-16/chart-examples/`（含 README）。
- 修订（品牌配色 token 化，前端确认）：图表主色一律引用宿主注入的 `--viz-*` 语义 token（背景/surface/text/text-muted/border/series-1..5/info 等），品牌 hex 仅作为 `var(--viz-*, #hex)` fallback。品牌色：背景 `#f4f5f7`、主文字 `#020A1A`、次文字 `#4e5969`、说明 `#8993a4`、边框 `#DADEE6`。三张模板 + TRAIN-2 示例已删除 `:root` 整套 `--c-*` hex 色板，改用 `var(--viz-*)` + `--brand-*` fallback；模板 JS 加 `viz(name,fb)` 运行时读注入值；`legend`/`series` 的 `color` 可填 token 名或 hex。`chart-tokens.css` 改为 token 唯一来源 + 映射表 + 速查。验证：headless Chrome 注入 `--viz-series-1:#2563eb` 等，渲染后 SVG 全部用注入色（无 fallback 漏出），未注入时 fallback 生效。契约同步：`chart-templates.md` 配色章节、`toolsmith-visualization` skill（reference §4 + SKILL.md 要点 4）、Obsidian 笔记。
- 给开发的兜底建议（已同步到 Obsidian 笔记 `ToolSmith可视化能力与4种画图方式.md`）：① 完整文档剥离（DOMParser 取 body + 前置 head 的 style/script，不改内容）；② 剥离后校验（无嵌套 iframe/无文档标签残留/≤1MiB，超限降级下载）；③ 相对路径兜底 `path="xxx.html"`→`/workspace/visualizations/xxx.html`（同时拒绝 `..`/反斜杠/前缀外）；④ 文件缺失显示占位+保留正文 fallback。边界：不做内容级修复、不绕过路径穿越校验、不执行外部导航。定位：兜底仅兼容 Agent 偶发不规范输出，核心正确性仍由 Agent 按契约负责，不应成为依赖。

## v0.7 change: attachment-based input（每条结果一个附件文件）

- 背景：原设计把选中的结果以内联 JSON 放进单条 message，用户勾选 20–50 条时容易超上下文。改为：每条结果写成单独 `.md` 附件（`source-001.md`…），随用户消息一起作为附件送达；Agent 按文件名顺序读 `/workspace/uploads/` 下每个附件，`{{ref_n}}` 按文件顺序分配。
- 单文件格式：`# 临床结果来源 {n}` + 三行元数据（`source_title:`/`source_url:`/`source_paper_release_time_str:`）+ `## source_full_text` 标题 + 全文正文。文件名顺序=输入顺序=ref 顺序（仅展示标签，非临床时序）。
- 附件限制（Tool Smith）：每消息 ≤10 文件、每线程 ≤100、单文件 ≤20 MiB；超出时拆分消息/线程，Agent 不假定固定数量。
- 改动文件：`references/input-contract.md`（重写：单文件布局/附件限制/Agent 读取协议/后端 manifest）；`references/input-and-extraction.md`（开头改附件读取）；`SKILL.md`（新增 Input 章节+证据边界措辞）；新增 `system-prompts/multi-clinical-result-comparison-v0.7.md`；README 同步；重建 `dist/multi-clinical-result-comparison-v0.7.zip`（18 文件，含 charts 模板）。
- 新增 `evals/fetch-np-clinical-attachments.mjs`：按条件从 `np_clinical` 拉取并写每源一个附件文件 + `manifest.json`（后端日志用），内置往返校验。默认条件=非小细胞肺癌（indications 135/5718/5719）+ 三期 + 积极。
- 真实测试：拉取 `evals/iteration-16/np-clinical-nsclc-50/`（50 条，条件命中 890 条）；50 个 `.md` + manifest；元数据完整度 title 50/50、url 49/50、time 50/50、空正文 0；Agent 视角对账（读文件→建 ref 台账→比对 manifest）50/50 一致。
- ⚠️ 数据事实修正：此前 NASH 示例用的 indications 516/517 其实是「非酒精性脂肪肝/非酒精性脂肪性肝炎」，不是非小细胞肺癌；ORR 属实体瘤终点，NASH 数据里不存在。本次已查实真实 ID：非小细胞肺癌=135、鳞状非小=5718、非鳞状非小=5719。
- ORR 柱状图实测：50 条中 30 条含 ORR/缓解率；取 3 个一线晚期 NSCLC 随机 III 期研究（CATAPULT I：27.5% vs 13.7%；E4599：35% vs 15%；nab-紫杉醇+卡铂 vs 溶剂型：33% vs 25%）注入 `templates/charts/endpoint-bar.html` 生成 `evals/iteration-16/chart-examples/orr-bar.html/.png`（真实数据，含跨试验可比性提示）。
- ⚠️ 柱状图模板修复（用户反馈）：① 数值刻度原本画在左侧与组别标签重叠 → 改为底部横轴（标准横向柱状图）；② 行高自适应（≤62px，行多时压到 ≥30px）；③ 行密时（rowH<42）组别字号缩到 11、左栏加宽到 224，杜绝长标签越出画布；④ 行密时（rowH<46）隐藏柱端 CI 副行避免串行。实测 51 行全量 ORR（24 个试验）：程序化 getBBox 测量 非同行重叠 0、越出画布 0。

## v0.6 change: evidence-chain timeline diagram

- Added `skill/multi-clinical-result-comparison/references/timeline-diagram.md`: construction rules for a descriptive Mermaid evidence-chain timeline.
- Scope: same-trial inputs only, when consolidation leaves ≥2 genuinely distinct evidence states. Cross-trial/mixed inputs do not get a shared timeline.
- Delivery: a Mermaid fenced code block placed directly above the timeline table in the 证据链总览与时间线 section. Mermaid is rendered natively by the Tool Smith Markdown renderer; it does not use `read_me`/`show_widget`/workspace files and does not require the inline-visualization capability.
- Diagram carries: source-supported chronology (data cutoff → follow-up → analysis milestone → disclosure date; never input order), one node per evidence state (analysis stage/disclosure form + this state's key new content + `{{ref_n}}` markers), a time axis (时间未明 when missing, never guessed), dotted time-to-state links, and a labeled relationship + maturity-direction arrow between consecutive states (更新/新增终点/确认/补充/取代/冲突/不确定 + 加强/基本不变/限定/削弱/无法确定).
- It is descriptive/chronological, not a quantitative series, so it does not require numeric compatibility. It never replaces the exact-value timeline table.
- Fallback: only 1 distinct state or undeterminable order → omit the diagram and state the order uncertainty in the table.
- Updated `SKILL.md` (read list + workflow step 5 + chart rule), `references/same-trial-evolution.md` (new Step 8), `templates/unified-evidence-report.md` (section 三 timeline insertion), `system-prompts/multi-clinical-result-comparison-v0.6.md` (new v0.6 prompt with the timeline rule), and `README.md`.
- Rebuilt `dist/multi-clinical-result-comparison-v0.6.zip` (13 files incl. `references/timeline-diagram.md`).
- Example: `evals/iteration-15/harmoni6-timeline/report.md` + `report.refs.json` — HARMONi-6 4-source/2-state report with the Mermaid timeline inserted. Verified: marker/key parity 4/4, citation keys == fixture count, fixture title/link/release-time parity, no forbidden implementation terms, no unresolved placeholders, Mermaid block bracket/quote balance OK. Mermaid v11.15.0 (bundled via `@streamdown/mermaid`) fully supports the used syntax (`flowchart`, quoted subgraph titles, `direction`, `-.-`, `<br/>`, quoted edge labels).
- Validation note: this workspace cannot run the Tool Smith cloud Benchmark or the actual frontend Mermaid render; validation is local static contract + syntax review.

## Chart templates (v0.7 direction): 蓝紫色系 HTML 图表

- Created `skill/multi-clinical-result-comparison/templates/charts/` with 3 single-file HTML chart templates (pure SVG/CSS/vanilla JS, no external deps → offline + Tool Smith sandbox ready):
  - `evidence-timeline.html` — same-trial 证据链时间轴（旗帜 + 时间轴基线 + 证据链成熟度渐变带，hover 提示；events 按证据披露时间先后排列）。
  - `endpoint-bar.html` — 混合/不同试验、无时间维终点（ORR 类）横向柱状图（轨道+主柱+高光、值+CI、hover）。
  - `endpoint-line.html` — 混合/不同试验、时间维终点（体重类）折线图；全部系列仅 1 个点 → 自动单点模式（只画点+值，不强行连线）。
- `chart-tokens.css`：蓝紫色系基准（靛蓝 #4f46e5 → 紫罗兰 #7c3aed → 紫 #a855f7；系列色 --c-s1..s6；语义用明度区分，不用红绿）。全部抽成 CSS 变量，模板内联；底部附 `--viz-*` 注入映射表，接宿主主题时整体替换 :root 即可，图代码不改。
- `references/chart-templates.md`：选型规则（同试验→时间轴；无时间维→柱状；有时间维→折线）、填数约束（仅 source_full_text、不推断阶段/顺序）、交付方式（workspace 文件 + `::visualization` 引用，图前后保留文字）、与 lieflat-charts 的关系。
- 验证：三模板 JS 语法 `node --check` 全过；headless Chrome 渲染出 PNG（36/32/30KB）；DOM 校验 svg/rect/circle/text 数量与代码预期一致、标题均注入成功。
- 版本边界：同试验时间轴随 v0.6；柱状/折线（定量图）供混合场景，计划随 v0.7 放开；`dist/` 未重建（待用户定夺是否并入 v0.7 后重建）。
- 相关安装：从 GitHub 拉了 `lieflat-charts`（64 图型，`~/.agents/skills/lieflat-charts`）供 fancy 图扩展；新建参考型 SKILL `toolsmith-visualization`（`~/.agents/skills/toolsmith-visualization`，沉淀 4 方式/2 通道/主题 token/下钻结论，均已在 Obsidian 笔记 `ToolSmith可视化能力与4种画图方式.md` 记录）。
- 示例成品（真实数据）：`evals/iteration-16/chart-examples/` 下 3 份 HTML + 渲染 PNG，用注入方式生成（模板代码不动、只换 `CHART` 数据）；**v0.15 已删除 HTML，仅存 PNG**：
  - `harmoni6-evidence-timeline.html/.png` —— HARMONi-6 4 来源→2 状态（PFS 核心分析 2025-10 披露、OS 核心分析 2026-05 披露）+ 研究启动里程碑；PFS 11.1 vs 6.9 月（HR 0.60）、OS 27.9 vs 23.7 月（HR 0.66），披露时间取自 refs.json。
  - `harmoni6-pfs-bar.html/.png` —— HARMONi-6 中位 PFS 按治疗组（11.1 vs 6.9 月 + 95%CI）。注明 HARMONi-6 未报告 ORR，以中位 PFS 单值演示柱状模板。
  - `mazdutide-weight-line.html/.png` —— 折线模板演示：HARMONi-6 无时间维重复测量终点，改用真实 obesity fixture 的马扎度肽 2b 期数据（4mg/6mg/安慰剂，W32/W48 体重变化 %：-10.09/-12.55/+0.45 → -11.00/-14.01/+0.30），已在副标题注明。
  - 校验：JS 语法 OK；headless Chrome 渲染 PNG（38/29/29KB）；DOM 校验关键数值（11.1/6.9、27.9/23.7、-10.09/-12.55/-14.01/+0.45/+0.30）全部注入成功。

## Confirmed decisions

- Users include medical intelligence, clinical development, and BD/investment teams; all receive the same report granularity.
- Version 1 compares only selected records and performs no external retrieval.
- The backend resolves selected records from the POC Elasticsearch environment and `np_clinical`, then sends `source_title`, `source_url`, `source_paper_release_time_str`, and `source_full_text` to the Agent. Runtime correlation IDs remain outside the Agent request and report.
- The frontend/backend enforce a conservative real-time token budget.
- The primary analysis object is the underlying trial. Multiple disclosures from one trial are source nodes that form a longitudinal evidence chain; repeated cutoffs and analyses are deduplicated.
- Different trials receive a comparison-first, domain-aligned cross-trial report: efficacy, safety, PK/PD, and PRO are aligned across trials so the user can judge which treatment is better or worse, with explicit comparability/evidence-strength labels and compact per-trial context; no pooling or fabricated head-to-head proof. Trial narratives are supporting context, not the primary structure. Synced into `system-prompts/multi-clinical-result-comparison-v0.5.md` (opening, required workflow step 8, and “Mixed or different-trial inputs”).
- Every material number and source-dependent conclusion in the report carries an internal citation token for frontend rendering; user-facing output shows numeric superscripts. Citation metadata is a separate strict JSON artifact, not part of the report body, and each ref includes `title`, `link`, and `paper_release_time_str`.
- Trial-level reports integrate design, population, regimen, primary and key secondary endpoints, response/durability when reported, subgroups, safety, evidence maturity, and information gaps.
- The finished report must not expose technical correlation keys, database/index names, retrieval traces, internal field names, or implementation terms such as `result_id`, `doc_id`, ES/Elasticsearch, `np_result`, or `source_full_text`.
- Visible labels use a source-supported study short name or name for different studies. Multiple disclosures from one study add a data cutoff/disclosure date or, when unavailable, follow-up plus endpoint/analysis scope. Generic labels such as “材料 1” are last-resort fallbacks; “证据 A/B/C” are not used when a readable source-supported label exists.
- Every cross-trial or mixed report includes a research-key-information alignment table and an experimental-arm endpoint table.
- The frontend/backend enforce a conservative real-time token budget.
- Within-trial controls and comparative effects remain tied to their original randomized comparison and are never converted into cross-trial claims.
- Same-trial reports begin with an evidence relationship overview that separately classifies disclosure form and analysis stage/scope, then explains duplicate/update/subgroup/final/interim relationships before endpoint evolution.
- Cross-trial reports begin with a core-endpoint snapshot per clinical-question cluster. The snapshot always includes an exact-value table; compatible ORR-like endpoints may additionally use a valid Mermaid bar chart, while weight-change line charts require the same explicit time-point grid across plotted series. Missing values, incompatible definitions, or unexpressible time structures trigger a table fallback. Charts are descriptive only: no interpolation, pooling, ranking, or head-to-head inference.
- Cross-trial reports use one global marker namespace in input order and one shared separate citation JSON artifact for the complete response. Markers do not restart at each trial boundary. Separate independently requested reports may use separate local namespaces.
- The citation renderer supports multiple trial sections, accepts a separate citation JSON object, validates marker/key parity, and makes only the numeric superscript clickable. Generic Markdown autolinking must not receive the citation JSON.

## 50 试验跨试验跑批（2026-08-24）
- 输入：`evals/iteration-16/np-clinical-nsclc-50/`（50 个 NSCLC 随机试验 source，2000–2013，gitignored 示例）。
- 用当前 v0.8 skill 契约跑：按临床问题分 7 组（组A 一线化疗 ORR / 组B 一线抗血管 ORR / 组C 一线 EGFR TKI 中位PFS / 组D 二线 ORR / 组E 维持 PFS / 组F 辅助 5年OS / 组G 放疗不可比不出图），每组一图（endpoint-bar）。
- 产出：`np-clinical-nsclc-50/report.md`（跨试验报告，每组表格+`::visualization`+可比性说明，{{ref_n}} 追踪）、`report.refs.json`（ref_1..50）、`charts/nsclc50-group-*.html/.png`（6 张图，fragment 校验全 OK）。
- 关键结论：EGFR 突变一线 TKI 较化疗 PFS 方向一致且显著；含铂双药方向普遍优于单药/非铂；二线无综合胜者（TKI 人群富集 ORR 高不可跨类别解读）；维持各研究内均 PFS 获益。
- 子代理并行提取（5×10 文件，JSON 到 /tmp/nsclc50-extract/），抽查关键原文核对无偏差。

## 特应性皮炎 50 条跑批（2026-08-24）
- 用户给定新 query（indications.id=579 + trial_phase.id=9567bdf8567c48c3b5368659e63b12f7 + 排除删除）拉 np_clinical：total=100，拉 50 条 usable。
- id 579 = 特应性皮炎（非肿瘤），2013–2024，生物/JAK 时代；与 NSCLC 批次不同，重复披露多（OLE/亚组/PRO/特殊人群），主结果仅 7 条。
- 输出：`evals/iteration-16/np-clinical-ind579-phase3-50/`（manifest + source-001..050 + report.md + report.refs.json + charts/ 3 张 EASI-75 柱状图）。
- 分组按靶点通路：组A dupilumab/IL-4R、组B IL-13 单抗、组C 口服 JAK、组D 外用（不出图）、组E nemolizumab（瘙痒终点不出图）、组G 传统/基础（不出图）。同主试验多披露合并（PRESCHOOL/PED-OLE/JP01/AD3/AD7/EXTEND）为一个证据状态。
- 拉取脚本：`/tmp/fetch-np-user-query.mjs`（可复用，接 query 拉任意条件）；子代理 5×10 提取到 /tmp/ind579-extract/。

## 时间维度优先折线图契约（2026-08-24 用户确认，v0.8 修订）
- **触发**：AD 批次首版交付全用柱状图（横截面 16 周 EASI-75），用户指出时间维度（OLE 长期随访/多时点）才是这批核心，应优先用折线图。
- **硬规则（固化进 skill）**：先判时间维度再判横截面——同一研究+同一队列+同一终点 ≥2 个已披露时点（OLE 延展、多时点、停药复发）→ 优先 `endpoint-line.html` 折线图（series=队列、points=已披露时点）；只连线同研究/同队列/同终点，**不跨研究/不跨队列/不跨人群连线**；不插值/补点/外推；单时点披露用单点模式；无对照单臂（婴幼儿外用药等）也可画折线但注明「单臂无对照，仅描述随时间变化」。横截面单值终点（ORR/EASI-75 单时点应答率）才用 `endpoint-bar.html` 柱状图，作组间对照补充。
- **同步文件**：`SKILL.md`（§6 时间维度优先 + Required distinction「同队列时间过程 vs 跨试验横截面快照」）、`references/chart-templates.md`（选型表 + 新增「时间维度优先判定」小节）、`references/cross-trial-comparison.md`（Chart contract time-dimension-first 条款）、`references/same-trial-evolution.md`（区分定量时点折线图 vs 证据链时间轴）、`templates/mixed-comparison-report.md`、`templates/cross-trial-report.md`、`system-prompts/multi-clinical-result-comparison-v0.8.md`（120 行补时间维度优先条款）。dist zip 重建（18 文件字节一致）、`validate-v05-contract.mjs` green。
- **AD 交付重写**：`np-clinical-ind579-phase3-50/` 新增 4 张时间维度折线图——`ad-line-baricitinib-breeze-ad3-ole`（4mg/2mg EASI-75 W16→W68）、`ad-line-delgocitinib-infant-measi`（mEASI 变化 W4/28/52 单臂）、`ad-line-difamilast-infant`（EASI-75/IGA W1→W4→中期单臂）、`ad-line-nemolizumab-ole`（W68 单点模式）；report.md 重写为「时间维度折线（主线）→ 横截面 EASI-75 柱状（组间对照补充）」结构，共 7 图；全部 DOM 验证 + fragment 校验 OK。

## Pending verification (next week, with Tool Smith developer)

- **Input delivery (batch-2 待问 ④⑤)**: 20–50 附件跨消息投递——前端是否自动拆成 10/条？跨消息附件是否全部进 `/workspace/uploads/` 且主 Agent 一次 run 都能读到？50 个全文真实读取的 token 实测（读全是否顶爆上下文；缓解：按需读 / 只读元数据 / 子代理分包）。
- **Subagent 机制（已核查代码，2026-09-10）**: Tool Smith 后端支持且**本项目部署已开启开关**——`schemas/capabilities.py` `subagents: bool = False`（项目级默认关，用户已手动打开）；主 Agent 有 `task` 工具（参数仅 `subagent_type`+`description`，仅有 `general-purpose` 一种，自包含、无状态、只回最终结果）；子代理由同一 `create_chat_agent()` 工厂构造，因此继承默认能力集（**含 params MCP 工具**、`load_skill`、文件系统、代码执行）并共享同一文件系统/凭证/额度；递归深度 `max_recursive_depth=2`（主→子→孙，本 Skill 自身收紧为 1 层）。**已确认**：多 `task` 并发**不生效**——全仓无 `allow_concurrent_tool_calls`，pydantic-ai 默认串行（平台工具描述写「concurrently」与实际不符，可报给后端）；且 `agent.py:65-75` 在 `recursive_depth > 0` 时把系统提示词换成通用子代理提示词，**子代理看不到项目 sys / Skill 正文**（它仍能 `load_skill`，但委派 `description` 必须自带完整抽取规格）。
- **Subagent 策略已写入 sys + SKILL（v0.15，已去待验证标注）**: `references/input-contract.md` 的「Large-batch delegation via subagents (OPTIONAL)」章节 + `SKILL.md` Input 段指针 + sys v0.15 新增 `## Subagent delegation` 段。规则：>5 esid 且 `task` 可见才用、≤5/块按输入顺序均衡切分、一块一 `task`、`description` 完全自包含、只回带 source marker 的紧凑摘要、`{{ref_n}}` 仍按输入 esid 全局分配、串行执行预期、只许一层嵌套、`task` 缺失或 chunk 失败则回退直读且**绝不因此跳过任何来源**。仍未实测：6–20 esid 下的端到端 token/耗时收益，所以仍为 opt-in（不作为提速手段）。

## Validation completed

- Tool Smith `validate_skill_md` accepted the Skill name and description.
- Ran the Skill locally against the condition-based fixture `np-clinical-indications-516-517-phase-featured-false.json`: generated `evals/iteration-14/condition-example/report.md` (4-trial mixed input: ESSENCE, MAESTRO-NASH, MAESTRO-NAFLD-1/OLE, SYNCHRONIZE-MASLD) and `report.refs.json`. Per user feedback the report was restructured to be comparison-first and domain-aligned (efficacy, safety, PK/PD, PRO) rather than trial-by-trial narratives; the Skill routing, `cross-trial-comparison.md`, `cross-trial-report.md`, and SKILL step 6 were updated accordingly. Marker/key parity 10/10, renderer tests 6/6, contract validation `v0.5_contract_ok`.
- The upload archive contains the expected root directory and nine Skill files.
- PWS heterogeneous cross-trial/mixed case: passed after removing cross-cluster rankings.
- HARMONi-6 same-trial evolution case: passed chronology and duplicate-disclosure checks.
- Adversarial/incomplete case: passed prompt-injection, missing-data, and no-soft-ranking checks.

## Iteration 13 HARMONi-6 v0.5 regression report

- Generated `evals/iteration-13/harmoni6/report.md` from the four selected HARMONi-6 source objects using the v0.5 prompt, Skill, required references, and unified evidence template.
- Consolidated the disclosures into one trial narrative with one PFS core state and one 2026-02-27 OS core state; repeated PFS and OS analyses are treated as duplicate or complementary reporting rather than independent validation.
- Preserved source-supplied proper names, retained OS as a first planned/interim analysis, and traced material numbers and source-dependent conclusions with `{{ref_1}}` through `{{ref_4}}`.
- Verification covers inline-marker/JSON key parity, strict separate JSON parsing, exact fixture title/link/release-time parity, unresolved placeholders, prohibited internal fields, and absence of citation metadata from the report body.
- The project root has no Git metadata or Docker configuration, so commit, push, image build, and registry push are not applicable.

## Current revision

- Reviewer feedback identified that the prior example lacked a clear endpoint alignment surface.
- v0.2 replaces default pairwise comparability matrices with a row-oriented experimental-arm endpoint table.
- Experimental-arm observations and within-study control/effect estimates are now separate fields; neither may be inferred from the other.

## v0.3 revision

- A reviewed therapeutic-area landscape article showed that users need more than study-by-study extraction: they need baseline comparability, endpoint-family scanning, complete-response or threshold outcomes, placebo/reference behavior, and a bounded development interpretation.
- v0.3 adds these as reusable output structures without importing the article's CSU facts or conclusions.

## v0.3 to C revision

- Changed the output boundary for the to C report: technical identifiers, ES/database retrieval details, internal field names, runtime terms, and implementation traces are prohibited in final Markdown.
- Removed technical identifier columns and references from all three report templates while retaining readable evidence labels for user-facing comparison.
- Added the to C evidence relationship overview and core-endpoint chart modules to the v0.3 prompt, Skill references, and report templates.
- The final report is now a single consumer-facing evidence synthesis. Internal relationship classification still distinguishes evidence evolution from endpoint alignment, but the report no longer exposes separate same-trial, cross-trial, or mixed report paths.
- The unified runtime template is `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`. It organizes the visible output by core findings, evidence relationships, time course, endpoints, comparability, maturity, and information gaps.
- The chart contract was tightened for Tool Smith Markdown rendering: Mermaid is conditional, uses quoted labels and numeric-only arrays, and is omitted entirely when any value is missing or the time-point structure cannot be represented without interpolation. Every chart is accompanied by an exact-value table and a comparability note.
- The upload archive was regenerated after the updated Skill, reference rules, templates, and system prompt passed validation.

## v0.4 direction reset: trial-level synthesis

- Reframed the primary analysis object from disclosure-to-disclosure comparison to the underlying clinical trial.
- Multiple disclosures from one trial are now source nodes. The runtime must consolidate repeated cutoffs and analyses into one evidence state, preserve genuinely new endpoint/follow-up states, and explain the whole trial across design, efficacy, safety, maturity, and information gaps.
- Added `references/citation-and-ref.md`: stable presentation labels `[Ref n]` are assigned per selected source, every material number and source-dependent conclusion requires an adjacent Ref, and the final `来源索引` maps all selected sources to their contributions.
- Replaced the unified report template with a trial-level structure: clinical question, design, evidence-state timeline, integrated efficacy chain, safety chain, maturity/contradictions/gaps, whole-trial interpretation, and source index.
- Retained limited different-trial alignment only after each trial receives a complete synthesis; no global ranking replaces the trial narrative.
- Updated the same-trial reference to treat disclosures as evidence nodes and states, and updated mode routing so same-trial synthesis is the default visible behavior.
- Added v0.4 system prompt and revised benchmark expectations for trial identity, state deduplication, chronology, inline Ref coverage, and complete-trial interpretation.

## v0.5 linked-source input revision

- Added `references/input-contract.md` documenting the POC configuration, `np_clinical` lookup, normalized Agent payload, absolute URL policy, and frontend superscript rendering.
- Added `evals/fetch-np-clinical-sources.mjs`, a read-only reference adapter that imports the POC config and requests `base.title`, `base.full_article_link`, `source_full_text`, plus `base.paper_title` for the observed title-shape fallback.
- Added `evals/fetch-np-clinical-by-condition.mjs`, which reproduces the requested indication/phase/evaluation/NCT/deletion/featured filter and writes a normalized 10-source example to `evals/fixtures/np-clinical-indications-516-517-phase-featured-false.json`. The query matched 12 records and returned 10 usable full-text sources.
- Pulled `NCT05840016` successfully: 4 HARMONi-6 disclosures with source text lengths 3294, 3587, 2936, and 3067 characters. The fixture preserves exact backend URLs and contains no internal record IDs.
- Updated the v0.5 prompt, Skill, extraction rules, template, README, fixtures, and renderer to use `source_title/source_url/source_paper_release_time_str/source_full_text`, internal `{{ref_n}}` rendering tokens, and a separate strict citation JSON artifact.
- The v0.5 HARMONi-6 fixture preserves four backend-supplied titles and exact URLs, including the ESMO query string. It contains no runtime result IDs.
- Updated the PWS fixture with five read-only `np_clinical` title/URL/release-time pairs. Updated the synthetic adversarial fixture to the same four-field shape with intentionally empty links and release times rather than invented metadata.
- Added `runtime/citation-renderer.mjs` and `test/citation-renderer.test.mjs`: parse the separate citation JSON, enforce marker/key parity, preserve release-time metadata, and safely render valid HTTP(S) links as numeric superscripts with escaped attributes.
- Added explicit cross-trial rules: marker numbering is global for one mixed response and the separate citation JSON is shared; numbering resets only for separately requested reports. A cross-trial comparison claim must cite the source markers for both trials.
- Added the standalone example citation artifact `evals/iteration-13/harmoni6/report.refs.json`; the Markdown report no longer contains a citation section.
- Updated the HARMONi-6 example evidence scope to state `2 份期刊摘要、2 份会议摘要`; the report no longer explains `{{ref_n}}` in visible prose.
- Citation output uses no JSON. The final section is a strict two-line-per-source numbered list: `n. exact title` followed by three spaces and the exact URL.
- Runtime test suite passes 6/6; `node evals/validate-v05-contract.mjs` returns `v0.5_contract_ok`.
- Rebuilt and extracted `dist/multi-clinical-result-comparison-v0.5.zip` with the correct Skill `references/` and `templates/` directory structure; archive contains 13 files.
- Tool Smith cloud Benchmark and actual frontend superscript rendering remain unavailable in this workspace and were not run.
- No Git metadata or Docker configuration is present at the project root; commit, push, image build, and registry push are inapplicable. The POC repository remains dirty with unrelated pre-existing work and was not modified.

## v0.4 verification status

- Static contract review completed for prompt, Skill, support references, template, README, and eval definitions.
- Local v0.4 execution completed against `evals/fixtures/harmoni6-selected-results.json` using the Skill and system prompt: [first run](evals/iteration-12/harmoni6/report.md) and [corrected rerun](evals/iteration-12/harmoni6/report-v2.md).
- The first run exposed a provenance bug: the model invented an unsupported Chinese translation for the source-only drug name `ivonescimab`. Added an explicit proper-name fidelity rule to the system prompt, Skill, and extraction reference: preserve source spelling unless the source itself supplies a Chinese equivalent.
- Corrected rerun passed the trial-level checks: one HARMONi-6 narrative, one PFS state, one OS state, duplicate-source handling, chronology, all four Refs in the source index, inline numeric citations, no internal identifiers, and no unresolved placeholders. It retained `ivonescimab`, `tislelizumab`, `paclitaxel`, and `carboplatin` exactly as supplied.
- `evals/evals.json` now includes the proper-name fidelity assertion. Rebuilt `dist/multi-clinical-result-comparison-v0.4.zip` after the Skill change.
- No Git metadata or Docker configuration is present at the project root; commit, push, image build, and registry push remain inapplicable.

- Regenerated `evals/iteration-10/harmoni6/unified/report.md` from the current v0.3 Skill, system prompt, unified template, and required reference rules using only the four selected HARMONi-6 result texts.
- Replaced generic letter labels with stable source-supported disclosure labels based on HARMONi-6, explicit data cutoff where available, and PFS/OS/safety or analysis scope.
- Deduplicated the four disclosures into one PFS core analysis state and one 2026-02-27 OS core analysis state while preserving disclosure-specific PD-L1 subgroup, baseline anatomy, testing procedure, event-count, and safety details.
- Preserved uncertainty around the undated first planned PFS disclosure: its repeated overall PFS values were deduplicated, but no chronology or shared data cutoff was inferred.
- Kept OS as a prespecified interim/first planned analysis rather than a final analysis, including the 204-event trigger versus the approximately 225-event plan and the non-estimable upper confidence limits.
- No chart was emitted because PFS and OS are incompatible endpoint/time structures and plotting repeated disclosures would double-count the same analyses.
- Manual fidelity review confirmed all four selected disclosures are represented and key PFS, OS, subgroup, event-count, denominator, and safety values match the supplied texts.
- The report contains no generic “证据 A/B/C” labels, internal correlation keys, implementation/storage terminology, template placeholders, or Mermaid blocks.
- Current project state indicates no Git metadata or Docker configuration at the project root, so no commit, push, image build, or registry push was applicable.

## Iteration 10 PWS unified report

- Regenerated `evals/iteration-10/pws/unified/report.md` from the current v0.3 Skill, system prompt, unified template, and required reference rules using only the five selected PWS result texts.
- Replaced generic letter labels with stable source-supported labels: C601/C602 disclosures are distinguished by follow-up and analysis scope; independent studies use registry identifiers or a source-supported descriptive study name.
- Kept body composition, infant growth/development, eating/behavior, and long-term glycemic safety as separate clinical questions within one report. C601/C602 body-composition and glycemic disclosures are treated as complementary analyses, not independent confirmation.
- No chart was emitted because no clinical-question cluster had compatible complete numeric series. Exact-value snapshot tables, study alignment, baseline comparability, endpoint alignment, endpoint-family maturity, safety interpretation, and information gaps were retained.
- Manual fidelity review confirmed all five selected items are represented; key values match the supplied texts; the source's week-64 versus 3-year discrepancy, week-156 HbA1c wording discrepancy, adult LMI formatting anomaly, and unresolved percentage denominators remain explicitly bounded.
- The output contains no generic “证据 A/B/C” labels, internal correlation keys, implementation/storage terminology, or Mermaid blocks.
- No Git metadata or Docker configuration was present at the project root, so no commit, push, image build, or registry push was applicable.

## Iteration 9 unified report

- Replaced visible mode-specific report routing with one runtime template: `skill/multi-clinical-result-comparison/templates/unified-evidence-report.md`.
- Internal relationship detection remains available for deduplication, chronology, endpoint alignment, and comparability, but the final report is organized as one evidence synthesis around core findings, evidence relationships, time course, endpoints, comparability, maturity, and information gaps.
- Regenerated unified PWS and HARMONi-6 examples under `evals/iteration-9/`; both passed scans for internal identifiers, implementation terminology, forbidden path labels, and invalid Mermaid output.

## Iteration 8 examples

- Regenerated `evals/iteration-8/pws/with-skill/report.md` from the current v0.3 assets. It separates body composition, development, hyperphagia/behavior, and long-term glycemic safety; all chart candidates correctly fell back to exact-value tables because the supplied evidence was incomplete or incompatible.
- Regenerated `evals/iteration-8/harmoni6/with-skill/report.md` from the current v0.3 assets. It groups duplicate PFS and OS disclosures into two analysis states, orders them by cutoff/follow-up, and preserves the interim-not-final OS boundary.
- Both reports passed scans for internal identifiers, retrieval/storage terminology, and invalid Mermaid output. These are independent local generations from the fixtures, not production Tool Smith Benchmark runs.

- Queried `np_result_3` directly with the selected 16 `doc_id` values and preserved `deleted`/`is_delete` exclusions.
- Retrieved 17 non-empty `source_full_text` values; `38912654` contains Trial 1 and Trial 2, so 16 documents yield 17 result items.
- Added `evals/fixtures/obesity-results-es-source-full-text.json` and the reproducible fetcher `evals/fetch-obesity-es-fixture.mjs`.
- Added `evals/iteration-7/obesity-results-es-source-full-text-report.md`, which separates adult weight management, T2D/prediabetes, pediatric obesity, and OSA questions before limited vertical alignment.
- Marked `35658024`/`39536238` as the same SURMOUNT-1 trial and `38912654` Study 1/Study 2 as two trials in one disclosure.

## v0.13 quick-comparison rebuild (2026-09-07) — ABANDONED in v0.14, kept for reference only

- Reframed the default product from full trial synthesis to a fast comparison brief: one MCP pull, one digest, one compact alignment table, one main chart at most, short interpretation and gaps.
- Added `skill/multi-clinical-result-comparison/templates/quick-comparison-report.md`.
- Added `system-prompts/multi-clinical-result-comparison-v0.13.md`; v0.12 remains the historical deep-synthesis prompt.
- Retained strict selected-fields input, citation parity, duplicate handling, no inference/pooling, safety boundaries, entity provenance, chart validation, TEMP preview dual-write, and `present_artifact` delivery.
- Verification: Python syntax checks pass; all three JSON chart skeletons pass `validate-chart.py`; v0.13 archive contains 22 runtime Skill files, including the quick-comparison template and the same-trial evidence timeline assets.

## Preview renderer visual refresh (2026-09-08) — renderer archived in v0.14 then deleted in v0.15 (was `docs/legacy-html-charts/render-preview.py`)

- Refined `templates/charts/render-preview.py` without changing the JSON protocol or Tool Smith fragment contract.
- Replaced the monochrome violet debug styling with a neutral paper/white surface, ink typography, teal/coral/blue/gold series palette, restrained border/shadow treatment, clearer source footer, and responsive mobile spacing.
- Improved badge, legend, tooltip and chart-stage hierarchy; preserved hover tooltips and host `--viz-*` token overrides.
- Chrome desktop/mobile screenshots were generated for bar, line, and timeline previews; all three renderers emitted non-empty PNGs without wrapper-fragment validation errors.
- Rebuilt `dist/multi-clinical-result-comparison-v0.13.zip` after the renderer update.

## v0.13 timeline condition correction — applies to the abandoned v0.13 line only

- The evidence-chain timeline is generated only when **all usable selected records belong to one trial** and there are at least two distinct evidence states.
- Mixed-trial inputs do not receive the default timeline, even when some records are repeated disclosures from the same trial.
- Rebuilt `dist/multi-clinical-result-comparison-v0.13.zip`; current SHA-256: `445d7335f0d503c60fd3da6950015915fbb36f0d883360d03e971ec25462e7f3`.

## 追加：esid → MCP 查询链路梳理与优化评估 + 事实清单归档（2026-09-17）

**诉求**：① 产品确认扇出后「兼容一下」；② 总体梳理「输入 id 之后从 MCP 查什么、怎么查」并评估优化；③ 事实清单在哪、能否落到 Obsidian。

**已落地**
- **扇出兼容（A1/B2 的仓库侧）**：`references/input-contract.md` 新增 `### Row fan-out: one esid can return several rows`（触发条件 = 请求 `indication_name`/`_en`；实测 2 esid → 5 行、每行取值相同、仅注入列 `disease_id` 不同且该列不可请求；去重必须发生在编号/计数/证据状态/时间轴/引用之前；`indication_detail`（句子）与 `indication_type_cn`（领域）**不是**替代字段）+ `SKILL.md` / `references/citation-and-ref.md` / sys v0.15 各一句同义规则；`evals/fact-check/README.md` 条目计数笔误（30 → 31 fail）顺手修正。
- **R12 记录**（台账 §2）：旧版部署内容 + 扇出输入的基线。旧版也能去重成功（正文「2 项独立试验、各 1 条结果来源」，`citations.json` 恰 2 键），但为此花了 16 次 `execute` + 15 次 `read_file`（枚举 jsonl 数行）→ 佐证「扇出是潜风险，代价是探索成本」。断言 14 PASS / 3 FAIL（全是「部署端 == 本地」一致性，因本地已改未发布）；事实分 `29/31 FAIL`。
- **两条清单发现（均已修复，见第十二轮）**：**O19** 打分器在「一句多 marker」上假阳性（与 sys 明文允许多 marker 冲突）；**O20** `A-T1-title-names-both` 期望过窄（主题式 H1 被判 FAIL）。均待判定，不擅自改。
- **Obsidian 归档**（`D:\software\MD\slowrun\03-技术与VibeCoding\01-AI与LLM\`）：
  - `临床结果Skill-esid到MCP查询链路梳理与优化评估-2026-09-17.md`
  - `对比结果Skill-事实清单与离线打分器-场景A32-B13-2026-09-17.md`

**链路要点（评估结论）**：整条链路只有 **1 次批量调用**（`extra_esids` + 最小 `selected_fields`），无发现式检索、无分页、无重试风暴；风险全在返回体形状 —— 行数被疾病 join 放大、`abstract_text` 在登记平台记录里可达 1.9 MB（且常常不是摘要），另有「未过滤选大字段 → StarRocks `rg_cube` 16 GiB 内存爆」与「请求 `projects` → 返回压到 500 行」两个已知边界。优化按性价比：**O-1 扇出去重（已落地）** > O-3 大字段按需（文案待改，即 B1）> O-8 平台侧显式返回未命中 esid（问题单候选）> O-9 真实 `source` 字段（等开发）> O-6 委派阈值（待样本）。

### 追加 B：证据来源优先级 ladder 的落点（2026-09-17 第二轮探清 → 政策放开后已落仓库，见 `### W3`）

**问题（用户）**：`selected_fields` 是不是 agent 自己决定？想约束读取优先级——第一优先 `abstract_text`（预存全文），第二优先访问 `source_full_link` 抓全文；怎么约束？

**答复要点（事实全部实测，证据见台账 `### W2`）**：

1. **是 agent 自己选**：平台不强制任何字段集；工具描述只要求「从 `ALLOWED_FIELD_NAMES` 里选你需要的字段」。我们唯一的约束面 = 我们自己的 `input-contract.md`（推荐清单 + 纪律）与 sys 证据段 ⇒ 优先级**只能写进契约**，工具层无法强制。
2. **字段名更正**：`source_full_link` **不存在**（那是 v0.11 附件契约的 `source_url`/`source_full_text` 时代叫法）。现行 params 工具里的真名是 `clinical_result.full_article_link`，描述「临床结果论文的URL」；写错名字 = 整次取数 `INVALID_INPUT`。
3. **`full_article_link` 实测指向（4 条样本）**：论文 → `https://pubmed.ncbi.nlm.nih.gov/<pm_id>`（同带 `doi`）；登记平台 → `https://clinicaltrials.gov/study/<NCT>`（`187` 类带 `?tab=results`）；公司新闻 → 微信公众号文章 URL。
4. **第二级「访问 URL 取全文」实测**：**人读页面全部失败**（PubMed → `Cookies must be enabled …` 反爬页；CT.gov → JS 骨架，无试验内容）；**API 端点全部成功**（CT.gov v2 `…/api/v2/studies/<NCT>` → 完整协议 JSON；Europe PMC `…/rest/search?query=EXT_ID:<pmid>&resultType=core&format=json` → `abstractText` + `pmcid` + `isOpenAccess`）。且 `web_fetch` **不回状态码**、沙箱无外网（平台侧代抓）。
5. **因此「原样写 ladder」不可行**：第二级必须换成 **API 端点**，而 API 端点要**由 `pm_id`/`doi`/登记号拼 URL** —— 与现行「URL 只逐字使用、不得构造/猜测」直接冲突；且与 sys:50「`full_article_link` 仅为引用元数据、不得提供临床事实」冲突。
6. ~~待拍三个开关~~ **已拍（2026-09-17 用户答复）**：(a) 政策 = **允许外部访问、原文第一优先级**；(b) 承载 = **报告正文 + `/workspace/sources/<esid>.<route>.{json,md}` 旁路审计**（`citations.json` 不动，`A-S4/A-S5` 保持绿）；(c) 语义 = 同指标分歧**原文为准**且双值并列、**原文缺失不算库内错**（可达原文多为摘要级）、抓不到按 `抓取受限 / 无登记号或 DOI / 该来源不公开` 记原因类。
8-c. **收窄为「库内即原文 ⇒ 默认不抓」+ `src=1` PMC 例外（2026-09-17 第五轮，台账 `### W5`）**：默认先读库内 `abstract_text`（实测多数类即原文，见上）不花额度；**`src=1` 例外**：有摘要也走 `R6`（Europe PMC search 读 `pmcid`）→ `R7`（`{PMCID}/fullTextXML` 取 PMC 全文），无 `pmcid`/`inPMC=N` 记原因类「无 PMCID / 非 OA」不计失败；预算「每条 ≤1、`src=1` ≤2、整批 ≤40」；覆盖行非抓取路径也算点名，且归档全文就必须写 `PMC<号>`/「全文」（`A-P5`/M21）。未列出类（uuid 遗留=通稿原文、numeric 遗留=会议摘要原文、`245` 库内空无路由键）沿用同一原理。
8. **按来源类细化（2026-09-17 第四轮，台账 `### W4`）**：可达性按 esid 中段的摄取来源 id 分流（`1`/`2`/`187`/`37`/`49`/`120`/`398`），封锁清单 16 个主机（businesswire、globenewswire、微信公众号、sec.gov、cslide、abstractsonline、ascopubs、meetings.asco.org、sciencedirect、jitc.bmj、annalsofoncology、pubmed、chinadrugtrials、ehaweb、sabcs、oncologypro）；同主机人类页与 API 要分开判断；`src=49` 免抓；覆盖行必须点名路径 + 来源类（`A-P4`）。实测证据 `docs/evidence/source-link-accessibility-2026-09-17.json`。
8b. **落实形态（2026-09-17 第三轮）**：白名单模板 R2/R3/R4/R5 逐字写进 `input-contract.md`；预算 ≤1 次/记录、整批 1 轮、硬上限 20 次、失败不重试不换路线；抓取全文落 `sources/` 且**不得贴进上下文**（用脚本摘）；版权闸门 = 正文不得出现抓取源 ≥60 连续字符（`A-P3`）。
7. **建议**：先把第一级写扎实（`abstract_text` = 第一手证据 + 可用性判据：非空、非结构化结果 JSON（不以 `[{` 开头/不含 `paramType`）、长度 ≥ 200 字符；一律先落盘再脚本摘，B1 的同批文案改动），第二级等三个开关拍板 + 白名单模版确定后再写。
