# R59 — 文体门禁内联（A+B）：把 6% 的条件式引用换成 100% 的确定性检查

日期：2026-10-13 ｜ branch `v0.15-remove-html` ｜ 前置：R58（`docs/evidence/r58-fact-row-recipe-deletion-2026-10-13.md`）、R57、R42
触发：用户问「引用外部 human skill 是否增加耗时」，并在看到数据后拍板 **A+B**（A = 把 humanizer 的文件复制进我们自己的包；B = 把选定的文体规则内联进 SKILL.md/提示词），同时问「必过？是不是更耗时了……」与「如果整合进来，② 的问题就不存在了吧」。

## 1. 决策：为什么是 A+B，而不是继续引用

先回答「引用是否增加耗时」——用全历史的真实调用数据（`~/.local/state/toolsmith-runs/2026*/messages.json` 的 `tool-load_skill` part）而不是估计：

| 量 | 实测 |
|---|---|
| `load_skill` 目标计数（全历史） | `multi-clinical-result-comparison` **115x**、`report-humanizer-zh` **7x**、`chart-visualization-json` **2x** |
| 触发率 | **6.1 %**（R58 三跑 **0/3**；最近一次是 `20261012-183501-r57b-shard-3`） |
| 引用本身的成本 | `load_skill` 返回 **5,933 字符**（≈1.5 K input token），**一次**，之后走 cache |
| 引用的边际墙钟 | **落在噪声内**：唯一在 R57 三 shard 里载入它的 `r57b-shard-3` 墙钟 445.9 s ≈ 中位数；未载入的 `r57b-shard-1` 反而最慢（465.5 s） |
| 真正的成本在「应用」 | 载入后模型会跑 humanizer 自带脚本 → 改报告 → 重跑门禁。`r44-a`（step 43 载入后 write_file + polish + 复查）墙钟 511 s / out 94,797；估**一轮应用 ≈ +1 次全文 `write_file`（8–20 KB out）+ 重跑 render/check ≈ +30–60 s / +10–20 K out** |
| 现状（引用存在但 6 % 触发） | 付了提示词字节，产出风格仍不一致 —— 与 R57 facts 分片**同一失效模式**：条件式许可（"may also mount… *When it does*: apply at most one"）打不过成本 |
| 漂移点 | 平台部署的 `report-humanizer-zh` 是 **v1.0.0**（实测载入 ≈5,933 字符），而本地仓库已到 **v0.1.1**（`SKILL.md` 14,112 B）—— **本地领先线上**，两条路径本就不同源 |

**决策：把 6 % 的条件式引用换成 100 % 的确定性检查 + 必然生效的内联规则。** 关键是把「必过」限定在**门禁**上，而不是限定在**改写**上：

- **门禁必跑**（新）：定稿后跑一次 `tell-scan.py`，成本 = 1 次本地 `execute`（1–3 s、**0 token**、输出 ≈200 B）。它落在噪声里（R57 三 shard 墙钟 445.9 / 465.5 / 384.9 s）。
- **改写按强命中触发**（不是无条件重写）：强命中才改；弱命中只作线索。实测样本报告 **强 0 / 弱 1** ⇒ 实际上**基本不触发**重写。
- **比现状更省**：现状是 100 % 的 run 都付条件式引用那 6 % 的字节（换来 6 % 生效），新方案是 100 % 的 run 付一次 0 token 的本地扫描 + 6 %（或更少）的场景付重写。

## 2. 改动（A + B，净加法但**零运行时依赖**）

| 位置 | 改动 |
|---|---|
| `skill/.../scripts/tell-scan.py`（**新，22,558 B**） | A：从 `report-humanizer-zh` 仓库逐字节复制（sha256 `1992a4c4…`）；零依赖确定性扫描器，`exit 0` 无强命中 / `3` 有强命中 / `2` 用法错误，`--json` `--allow` `--weak` `--lang` |
| `skill/.../references/prose-style-zh.md`（**新，13,071 B / 200 行**） | B：只内联**报告文体相关**的条目（A1–A10 结构级 / B1–B10 用词级 / C1–C8 中文特有 / D1–D3 草稿残留），每条带 改写前/改写后 与「保留」例；末尾给出与扫描器编号（`S-PROC-*`/`S-INFL-*`/`S-STRUCT-*`/`W-*`）的映射、退出码语义与「强命中必须处理」 |
| `skill/.../SKILL.md` | 脚本清单加 `scripts/tell-scan.py`；工作流 §5 加**必跑门禁**命令（与 `check_report.py` 同一个 `execute`）；旧的 `## Report prose style (when a report-humanizer skill is mounted)` 整节替换为 `## Report prose style (self-contained)`（内联〔强〕规则 + 〔弱〕线索 + 必跑门禁块 + 受保护集合 + 明写 **不加载、不等待、不依赖任何外部文体 skill**）；参考文件清单加第 11 项 |
| `skill/.../references/toolbox.md` | 表加 `Prose gate (finished file) | scripts/tell-scan.py`；新增 `## 9. tell-scan.py — the prose gate`（命令、退出码表、旗标、强/弱语义、「助手不是判官」、永不改数字、改完重跑） |
| `system-prompts/…-v0.16.md` | 工作流步 8 加「跑文体门禁并处理强命中」；脚本清单加 `tell-scan.py`；`## Report prose style` 整节重写为自包含版；交付前检查里的 `check_report.py` 一条改为「机械检查 + 文体门禁」；`if a report-humanizer skill was applied…` 一条改为「文体门禁跑过且无未处理强命中」 |
| `tools/pack-dist.py` | `EXPECTED 27 → 29`（两个新文件） |
| `evals/scripts/test-tell-scan.py`（**新，10 例**） | 契约 + 接线双面：退出码 0/3/2、强 vs 弱、`--allow` 只压判断过的规则、`--json` 形状、**只读**（扫描前后报告字节相同）、**与上游副本 sha256 一致**（兄弟仓库不在时 skip）、SKILL.md 仍指向扫描器与清单、清单仍解释四族编号 |
| `evals/runner-gate/test-runner.py` | 正向夹具补上「提示词规定的门禁调用 + `SCAN_EXIT=0`」；新增 4 例：门禁缺失 → FAIL、`SCAN_EXIT=3/2` → FAIL、无 `SCAN_EXIT` 标记 → **WARN 不 FAIL**（不惩罚宿主形状）、干净扫描不得同时触发 WARN |
| runner（`~/.local/bin/toolsmith-publish`，备份 `toolsmith-publish.v10.bak`） | 新增**第 18 项断言**：`execute` 调用里必须出现过 `tell-scan.py`（缺 → FAIL）；能读到 `SCAN_EXIT` 时必须为 0（脏 → FAIL）；调用过但没回显退出码 → WARN。拒绝分支（`--expect refusal`）不受影响 |
| `vendor/README.md` | 溯源表：上游来源、内联落点、sha256、漂移拦截测试；说明为什么它**不放** vendor（必须随包发布并在运行期执行） |

**保留（避免以后误删）**：`scripts/merge_ref_facts.py` 与 `build_ledger.py --scaffold` 的逃生口语义不变；`check_report.py` 的 `report voice` 组不动（扫描器与它是两层：机械契约 vs 文体候选）；`deps` 基线**未变**（`report-humanizer-zh/-en` 是**项目挂载**的事实，来自平台装配，不是我们文本扫描出来的依赖 ⇒ 删掉引用不会动基线）。

## 3. ② 为什么消失了

问题②（单一真源 / 双份维护）在**运行期**层面已消失：扫描器进了我们的包，运行期**不再依赖** `report-humanizer-zh` 是否被挂载、是否被模型记起、线上是 1.0.0 还是别的构建。残留的只是**仓库级两份拷贝**的漂移问题，用一条**字节同一性回归**兜住（`test_bundled_copy_matches_the_upstream_repo`，sha256 比对 `../report-humanizer-zh/skill/report-humanizer-zh/scripts/tell-scan.py`，兄弟目录不在时 skip 而不是假绿）——**能漂移但会被拦**，与「运行期不可见、没人拦」是两回事。上游改规则时的动作写死在两处：清单尾节（重拷 → 跑回归 → 若清单要跟进则改本文档）与 `vendor/README.md`。

## 4. 本地门禁（全绿）

`test-tell-scan` **10**（新）/ `test-skill-scripts` **62** / `test-check-report` **25** / `test-build-ledger-scaffold` **9** / `test-merge-ref-facts` **16** / `test-render-facts` **28** / `test_regressions` **35** / `test-runner` **41 → 45** / `test_pack_dist` **5** / `test_replay_run` **14** / node **8 + 8** / `mutations.py` **arm a 44/44 + arm b 12/12 + never flipped [] + GATE: PASS** / `verify-run-chain.py` **GATE: PASS**（145 histories / 5 comparable / 140 skipped）。
`pack-dist.py --check` → **IDENTICAL**；dist **180,675 B / 29 entries / sha `099504055d79`**；prompt **81,614 B / sha `aaf77e7c284b`**（+3,459 B，= §2 那节的内联规则与门禁）。

修复过程中撞到两处**真问题**（已修，不是改测试迁就实现）：

1. 正向夹具（7 例）在门禁变成硬断言后全红 —— 正确行为：契约变了夹具就得跟着变，同时补负向例（缺门禁 / 脏退出 / 无回显）。
2. 第一版把「无回显」写成了 `add(True, …, warn=True)`，而 `lvl = "PASS" if ok else ("WARN" if warn else "FAIL")` ⇒ `ok=True` 时 `warn` 被吞成 **PASS**（假绿）。改成 `add(False, …, warn=True)` 才是 WARN，且 `fails` 只收 `FAIL`，所以它不会误判 run 失败。

## 5. 发布（原地，用户授权「原地实测」）

- `deps`：**unchanged since the recorded baseline**（0 upstream change）→ **无需 `--accept`**。
- prompt **v1.8 原地**：78,155 B `6d507fb8fff7` → **81,614 B `aaf77e7c284b`**；`POST /api/prompts/…/versions (ifadd=false)` → HTTP 200，read-back `current=v1.8 matches_local=True`（逐字节）。
- skill **v1.0.9 原地**：dist 160,567 B / 27 entries → **180,675 B / 29 entries / `099504055d79`**；`POST /api/skills/update_skill_file` → HTTP 200，`skill_id=16aeb0406e12425bad27a2444f17225e version=1.0.9 is_current=True`。
- 回读 `status`：**`prompt deployed == local: True`、skill `29/29 identical`（0 differing / 0 missing）、`STATUS: in sync`**。

### 5.1 项目挂载集 4 → 2：**用户主动取消**（不是平台缺陷）

发布前后各跑了一次 `status`，项目的 `skills=` 一栏：

| 时刻 | `PROJECT … skills=` |
|---|---|
| 发布前（10:11 左右） | `['chart-visualization-json', 'multi-clinical-result-comparison', 'report-humanizer-en', 'report-humanizer-zh']` |
| 发布后（10:12 之后） | `['chart-visualization-json', 'multi-clinical-result-comparison']` |

- 直接读 API 确认不是显示问题：`GET /api/projects/<pid>/resources` 与 `GET /api/projects/<pid>` 都只回 2 个 family（`ee7d944445134cbba5771714f2188cb1` = chart、`9fe0035bdd324b998436c6cb9c2de212` = 我们），`/api/agent/info?project_id=…` 的 `skills` 同样只有 2 个 ⇒ **部署运行时确实只挂 2 个**。
- 项目行：`updated_at=2026-10-13T10:12:03.359711`、`updated_by=徐佩佩`、`version=1`。两个 humanizer family 本身**健在**（`is_current=True`，`updated_at` 仍是 2026-10-10T10:35:5x）——丢的是项目挂载关系，不是技能。
- **我们的 `publish` 写不到项目记录**：runner 只发两个文档化 POST（`/api/prompts/{family}/versions`，body 仅 `version/content/ifadd/is_current`；`/api/skills/update_skill_file`，body 仅 `skill_id/skill_name` + zip）；全仓 grep 无写项目接口（`GET /api/projects/{id}/resources` 只用于读）。
- 曾经按「平台侧副作用 vs 带外改动」立过问题单 **P-R59-2**；**当日由用户澄清：这次取消是本人从项目配置里做的**——因为规则已内联进本包（本轮 A+B），外部 humanizer 引用不再需要挂载，所以主动从配置里取消引用。**P-R59-2 因此作废（不是缺陷，也不需要恢复）**。
- 事后看，客户端的自我归因是对的：我们的 `publish` 只发两个文档化 POST，确实写不到项目记录。真正失效的是**归因线索不足**——平台无审计端点（`/api/projects/{id}/{history,logs,audit,versions,snapshots}` 全 404），`updated_by` 也区分不了「人改」与「服务端改」，所以在没有用户澄清时只能停在「无法本地确证」。这一条留作**平台可用性建议**（不指认为 bug、不开单）。
- 对本轮实测的影响：**不构成阻断，也不需要任何「不可比」折扣**。R59 的设计目标正是让 skill/提示词**不依赖**外部风格技能；被移出的两条从来没被加载过（R58 三跑挂在 4 挂载下也是 0 次加载，全历史只有 7/115），对本轮 run 唯一的影响是「技能目录少两条」（少两条目录项、少 ≈0 token）。§6 的成本对比里那句话保留，但差异来源已知且无害。

## 6. 实测（n=2，live）

输入 `/tmp/prompt-r53-4.txt`（4 esids → 4 refs）、`DeepSeek Flash`、web off、10:14:19 并发启动，tag `r59-gate-{1,2}`，目录 `~/.local/state/toolsmith-runs/20261013-101419-r59-gate-{1,2}`。

| run | wall s | out tok | reasoning | steps | `tell-scan` 调用 | `SCAN_EXIT` | facts | 断言 |
|---|---|---|---|---|---|---|---|---|
| r59-gate-1 | 332.1 | 52,794 | 37,399 | 30 | 2 | `[0, 0]` | 42 | 21 PASS / 2 FAIL |
| r59-gate-2 | 394.5 | 70,063 | 56,677 | 25 | 2 | `[0, 0]` | 43 | 21 PASS / 1 FAIL |
| **中位** | **363.3** | **61,429** | — | 27.5 | **2** | 全 0 | 42.5 | — |
| R58 中位（4 挂载） | 443.9 | 76,848 | — | 26 | 0 | — | 47.5 | — |
| R55 紧基线 | 405.4 | 70,187 | — | — | 0 | — | — | — |

判据：

1. **门禁真被调用 2/2 跑，且每跑 2 次**（一次在初稿成型后、一次在补丁改写后；模型自述「两处补丁只改措辞、未动数字与 marker，但为稳妥再扫一次」）。断言 #18 现场输出：`[PASS] prose gate ran and exited clean — 2 call(s), SCAN_EXIT=[0, 0] strong-free=True`。
2. **强命中 0**：两跑 `SCAN_EXIT` 全 0 ⇒ 无条件改写**没有被动触发**，「必跑」拿到了 100%（旧口径 6.1% 的条件式引用），而「贵的那一步」仍然只按需发生。
3. **弱命中被当线索而不是命令**：模型明确写 `tell-scan: 0 strong hits; 2 weak (bold count, mixed numeric notation). Weak only — acceptable`、`tell-scan exit 0 (only a weak bold-count clue — acceptable, not a reason to change)`——正是 `W-*` 的语义。
4. **没有外部依赖回流**：两跑的 `report-humanizer` 字符串都出现在**我们自己的自包含节**里（`Do not load, wait for, or depend on any external style skill.`），`load_skill` 只调本 skill；humanizer 未被加载（用户已在配置里取消其挂载，见 §5.1）。
5. **无分片回潮**：`task` / `subagent_type` 出现 **0** 次，`build_ledger.py --scaffold` **0** 次调用，`merge_ref_facts.py` **0** 次调用（transcript 里的字符串出现属阅读 SKILL.md/推理叙述，不是执行）。
6. **质量未退**：每跑 21 PASS——`citations` 4 refs 键集齐 + 日期格式 + 标题非空、`{{ref_n}}` 双向齐、图表 envelope 与 `::visualization` 一致、`present_artifact` 收尾、无残留占位符/嵌套锚点。
7. **FAIL 明细**：两跑共有 = `tool_results receipts archived`（平台侧 P-R53-1，历史每次命中）；`r59-gate-1` 多一条 = `no tool errors`，源自一次 `execute timeout_seconds=180`（平台上限 120）被拒后框架自动重发成功——见 §7 的 **R59-4 / P-R59-3**。

## 7. 判定与记账

**结论：KEEP（A+B 成立）。** 门禁从「6.1% 靠模型记起」变成「100% 必跑」，成本是每跑 2 次本地 `execute`（0 token、输出约 200 B、1–3 s），而 n=2 的墙钟与 out **都低于** R58 中位（−18% / −20%，紧基线 R55 下 −10% / −12%）——差异**不可归因**（n=2；挂载集虽然不同，但被移出的两条从未被加载，见 §5.1），但足以说明**没有可测的变慢**。

记账项：

- **R59-1**（双副本漂移）：已由 `test_bundled_copy_matches_the_upstream_repo`（sha256 字节同一性）兜住，兄弟目录缺失时 skip。
- **R59-2**（WARN 语义）：「跑过但读不到 exit 码」= WARN（不计 FAIL）；若后续实跑发现模型**从不**回显 `SCAN_EXIT`，再收紧为 FAIL。
- **R59-3**：断言 #18 只挂在 artifacts 分支（refusal 分支不跑，符合设计）。
- **R59-4（新）**：模型会给主线程 `execute` 传 `timeout_seconds: 180`（>120 上限）→ 被拒后自动重发成功，但仍计入 `no tool errors` FAIL。我们的文本已写「main thread 120 s」，属模型越界；候选动作 = 在 toolbox 的 `execute` 行把上限再显眼一点（内容改动，下一轮再议）。

平台侧（转开发，全文见 Obsidian）：

- **P-R59-3（新，轻）**：`execute.timeout_seconds` 的 `inputSchema` 没有 `maximum` 约束、描述只有一句 *Optional timeout override for this command.* ⇒ 只有越界执行时才收到 `timeout_seconds exceeds the maximum allowed (120s)`；建议在 schema 上加 `maximum: 120` 并把上限写进描述。
- **P-R59-1**（承接）：`execute` 参数名不一致（期望 `shell_command`，模型常发 `command`），断言 #18 已两种键都读自保。
- **P-R53-1**（仍在）：`tool_results receipts archived` 每跑必 FAIL，与本批改动无关。
