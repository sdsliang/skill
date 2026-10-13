# R60 — 运行期文本不再点名外部文体技能（依赖面收窄到 1）（2026-10-13）

**触发**：R59 之后用户问「（正文里还写着）`report-humanizer-zh` / `report-humanizer-en`，**这肯定要改啊……都没有这个 skill 了**」——
项目挂载已从 4 收敛到 2（R59 记录：用户主动取消），但**运行期文本（Skill + 系统提示词）仍在点名这两个技能**，于是：

1. 读起来像「它们还在被使用」的依赖错觉；
2. `toolsmith-publish deps` 每次都把它们当成**被扫描的上游依赖源**（`skills: 3`），发布闸门里挂着两条与本项目无关的新鲜度。

**本轮的假设（一轮 = 一个假设）**：删掉运行期文本里的字面点名，`deps` 的依赖面就会收窄到「真正运行期会调用的东西」（只剩图表技能），
而**行为不变**（R59 已内联全部文体规则，从未依赖挂载）。

## 1. 改动（3 个运行期文件，纯措辞收窄）

| 文件 | 改前 | 改后 |
|---|---|---|
| `skill/.../SKILL.md:185` | `A deployment may also mount \`report-humanizer-zh\` / \`report-humanizer-en\`; that is not this pass and is not needed — applying both pays twice…` | `If a deployment happens to mount another style skill, do not apply it here: applying both pays twice for the same edit and leaves two competing styles.` |
| `system-prompts/multi-clinical-result-comparison-v0.16.md:152` | 同款点名句 | 同款泛指句（保留「本 Skill 与宿主提示词在重合处优先」） |
| `skill/.../references/prose-style-zh.md`（维护节 3 行） | `源自上游 \`report-humanizer-zh\` 仓库：\`skill/report-humanizer-zh/{references/patterns-zh.md, scripts/tell-scan.py}\`（仓库版本 v0.1.1）`；`与上游逐字节一致`；`上游改规则时…` | `随本 Skill 发布的**自包含副本**（基线：内部中文文体资产 v0.1.1）…运行期不加载、不等待、不依赖任何外部技能或挂载`；`与**基线副本**逐字节一致`；`**基线**改规则时…` |

仓库级（**不进交付包**）留档照旧并追加一行：`vendor/README.md` 保留完整溯源表 + sha256，
新增「2026-10-13：用户已取消挂载，运行期文本不再点名任何外部文体技能 ⇒ `deps` 依赖面收窄」。

顺带修工具 docstring：`tools/pack-dist.py` 的条目说明 `27 entries` → `29 entries`（R48 / R57 / R59 沿革补到 R59 两项）。

**语义保留**：`references/prose-style-zh.md` 的实质规则、扫描器契约（exit `0` 无强命中 / `3` 有强命中 / `2` 用法错误；弱命中只作线索；永不改数字、永不授权删 局限/缺口/未报告 语句与可比性 caveat）一字未动；
`SKILL.md` / 系统提示词的**禁止加载外部文体技能**这条硬指令反而更明确（点名 → 泛指，覆盖任何外部挂载）。

## 2. 依赖面：`deps` 现场证据

```
$ toolsmith-publish deps          # 改后、未再接受基线
  UPSTREAM CHANGED since the recorded baseline:
     - GONE skills report-humanizer-en
     - GONE skills report-humanizer-zh
  exit=3   ← 闸门按预期挡下，正是本次改动的目标

$ toolsmith-publish deps --accept # 适配完成，记新基线（本机 ~/.config/toolsmith/deps.json）
$ toolsmith-publish deps
  skills: 1
     chart-visualization-json      v1.0.12
  MCP tools: 1
  built-in tools: 16
  DEPS: unchanged since the recorded baseline
```

**更正 R59 的一条归因**：R59 写「`deps` 里的 humanizer 是**项目挂载**事实、不是文本扫描出的依赖」——**不准确**。
`collect_deps` 只扫 `skill/` 与 `system-prompts/` 下的 `.md/.json/.py` 文本，对 `/api/skills/list` 的每个非本家族技能名做整词匹配
（`(?<![\w-])name(?![\w-])`），**挂载与否与它无关**；两条 `GONE` 只可能来自文本点名的消失，反过来证明 R59 那次「unchanged」是**巧合**（当时文本里仍有点名）。
正确表述：`deps` = **文本引用面**，本轮之后它才第一次等于「运行期真的会加载的依赖」。

## 3. 发布（原地更新，用户「原地实测」授权）

```
prompt : system-prompts/multi-clinical-result-comparison-v0.16.md  bytes=81576 sha=713f4333b74e
         family=91febc286412479a8b6d569fa3b8025e version=1.8 mode=in-place   POST /api/prompts/…/versions -> HTTP 200
skill  : dist/multi-clinical-result-comparison-v0.16.zip  bytes=180652 sha=0b8ba50448b6  29 entries
         family=9fe0035bdd324b998436c6cb9c2de212 version=1.0.9 mode=in-place (current version)
         POST /api/skills/update_skill_file -> HTTP 200   skill_id=16aeb0406e12425bad27a2444f17225e

回读：prompt deployed == local: True（v1.8 81576 B 713f4333b74e **CURRENT**）
      skill  deployed == local tree: True（29/29 identical）
      PROJECT prompt=475039ccebfe46a3a39002febe28b1f4 (= current version) skills=[chart-visualization-json, multi-clinical-result-comparison]
      STATUS: in sync — deployed matches the worktree
```

体积差：prompt `81,614 → 81,576 B`（**−38 B**）、dist `180,675 → 180,652 B`（**−23 B**）、条目数不变（29）。

## 4. 本地门禁（发布前全绿）

| 测试 | 结果 | 测试 | 结果 |
|---|---|---|---|
| `test-skill-scripts.py` | `Ran 62 tests … OK` | `test-render-facts.py` | `Ran 28 tests … OK` |
| `test-tell-scan.py` | `Ran 10 tests … OK` | `test_regressions.py` | `Ran 35 tests … OK` |
| `test-check-report.py` | `Ran 25 tests … OK` | `test-runner.py` | `Ran 45 tests … OK` |
| `test-build-ledger-scaffold.py` | `Ran 9 tests … OK` | `test_pack_dist.py` | `Ran 5 tests … OK` |
| `test-merge-ref-facts.py` | `Ran 16 tests … OK` | `test_replay_run.py` | `Ran 14 tests … OK` |

另：`mutations.py` arm a **44/44** + arm b **12/12** + `never flipped []` + `GATE: PASS`；`verify-run-chain.py` `147 histories; 5 comparable; 142 skipped` + `GATE: PASS`；
node `test/citation-renderer.test.mjs` **8 pass / 0 fail**、`test/citation-validation.test.mjs` **8 pass / 0 fail**；
`tools/pack-dist.py --check` → `IDENTICAL (180652 B / sha 0b8ba50448b6 vs rebuilt … 0b8ba50448b6)`。
计数口径：**221**（含 numeric-integrity 28 + merge-ref-facts 16 为 **249**）。

## 5. 实测（原地发布后真跑，n=2，`DeepSeek Flash`，固定 4-esid 输入，web off）

| run | wall s | out tok | reasoning | tool calls | `tell-scan` 调用 | `SCAN_EXIT` | facts | report | 断言 |
|---|---|---|---|---|---|---|---|---|---|
| `r60-prose-generic` | 502.7 | 89,145 | 73,317 | 33 | 1 | `[0]` | 63 | 19,022 B | 22 PASS / 1 FAIL |
| `r60-prose-generic-2` | 357.2 | 61,049 | 46,759 | 27 | 1 | `[0]` | 53 | 20,355 B | 22 PASS / 1 FAIL |
| **中位** | **430.0** | **75,097** | — | 30 | 1 | 全 0 | 58 | 19,689 B | — |
| R59（n=2） | 363.3 | 61,429 | — | 27.5 | 2 | 全 0 | 42.5 | — | 21 PASS |
| R58（n=3） | 443.9 | 76,848 | — | 26 | 0 | — | 47.5 | — | 21 PASS |
| 紧基线 R55 | 405.4 | 70,187 | — | — | 0 | — | — | — | — |

**判据**

1. **运行期文本干净**：两跑 `messages.json` / `transcript.md` 中 `humanizer` 出现 **0** 次（交付物 `report.md` 亦 0）。
2. **没有偷偷去加载外部技能**：`load_skill` 各 **1** 次，参数均为 `{"skill_name": "multi-clinical-result-comparison"}`（只调本 skill，全项目挂载的两个技能其余均未被载入）。
3. **文体门禁仍然必跑**：断言 #18 两跑均 `[PASS] prose gate ran and exited clean — 1 call(s), SCAN_EXIT=[0] strong-free=True`；
   现场弱命中依旧是线索而非判决（`W-FMT-MIXED` 数字记号混用、`W-AIWORD 闭环`），`合计强命中 0 条` ⇒ 无条件改写未触发（口径「必跑 ≠ 必改」成立）。
4. **交付契约未动**：两跑各 **22 PASS**；唯一 FAIL 都是平台侧 `tool_results receipts archived`（**P-R53-1**，与 R53 起每跑同一项）；
   交付物固定路径、图表 envelope 与 `::visualization` 一一对应、`{{ref_n}}` 双向齐、citations 4 refs 键集/日期/标题、`present_artifact` 收尾全部 PASS。
5. **无回潮**：`task` / `subagent_type` **0** 次、`--scaffold` **0** 次、`merge_ref_facts.py` **0** 次（方法论约束仍生效）。
6. **成本不可归因**：中位 wall `430.0 s` vs R59 `363.3 s` / R58 `443.9 s` / 紧基线 R55 `405.4 s`，单跑跨度 `357–503 s`；本轮改的是**一句话的措辞**，
   没有任何可加时间的机制（门禁调用数还是 1 次、0 token）。`r60-1` 的 out `89,145`（reasoning 73,317）是历史最高值，同批次 `r60-2` 只有 `61,049` ⇒ 记为方差而非回归。
7. **改动是可达成的**：`deps` 由 `skills: 3` → `skills: 1`，且只有这一条路径能让两条 `GONE` 出现（正文点名消失）。

**判定：KEEP。** 目标（运行期文本不再引用不存在的技能、依赖面收窄到运行期真实依赖）**达成且被现场证据证明**；行为契约全绿；成本落在已知方差带内、无可归因代价。

## 6. 记账

- **R60-1（记账，无需动作）**：门禁调用数由 R59 的 **2 次/跑** 降为 **1 次/跑** —— 模型把 `tell-scan.py` 并进了同一条 `execute` 链
  （`make_citations.py … ; check_report.py … ; tell-scan.py … ; echo SCAN_EXIT=$?`）。断言只要求 **≥1 次**且 `SCAN_EXIT=0`，两跑都在链尾拿到干净的 `SCAN_EXIT=0`。
- **R60-2（更正）**：R59 关于 `deps` 归因的说法（「项目挂载事实」）在本轮修正为 **「文本引用面」**，证据见 §2；已回填 R59 记录。
- **R60-3（观察，低优先）**：`execute` 链式命令尾部的 `SCAN_EXIT` 依赖模型自己回显；若后续出现「跑过但无回显」的 WARN，再评估是否把扫描器改为总是自带退出码回显（当前两轮 n=2 都自带）。
- **未变**：`--scaffold` / `merge_ref_facts` 仍为零调用（R58 结论继续成立）；`deps` 无需再 `--accept`（已记新基线）。

## 7. 平台侧（转开发，本轮无新增）

- **P-R53-1（已知，每跑命中）**：`tool_results receipts archived` —— `/workspace/tool_results/…/result.jsonl: unsafe or unsupported receipt path`，两跑各一次 `[FAIL]`。
- **P-R59-1**（`execute` 参数名 `command` vs `shell_command`）、**P-R59-3**（`execute.timeout_seconds` schema 无 `maximum: 120`）、**P-R56-1~4**、**P-R58-1** 均维持原状态。
- **P-R59-2 已作废**（挂载 4 → 2 系用户主动取消；本轮进一步把文本里的点名也去掉，与该决定一致）。
