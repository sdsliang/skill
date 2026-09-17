# 对比结果 skill：用 autoresearch 范式做下一轮迭代（规划，**待执行**）

> **状态：规划，未执行。** 本文只沉淀诊断与方案 —— **没有改任何 skill/sys 文件、没有发布、没有 commit**。
> 拟于 2026-09-16。接手者先读 §1（TL;DR）、§4（闸门 1，必须先修）、§12（执行顺序与授权）。
> 姐妹文档：`docs/toolsmith-run-v2-polling-plan.md`（run 通道改造）—— 两者在 §4/§7 有交叠，建议先修 §4。

**触发**：用户先要求学习 `karpathy/autoresearch`（自主预训练研究 loop：人写 `program.md` → agent 改 `train.py` →
固定预算跑 → 看单一标量 `val_bpb` → 好则 commit 保留、差则 `git reset` → NEVER STOP），随后说
**「你用对比结果那个 skill 规划试试？先不改动那个skill本身」**。

**本文对这句话的解读**（若不符原意，只需重写 §8–§10，§3–§7 的诊断仍然成立）：
把 autoresearch 那套（固定预算 + 可比标量 + keep/discard + 防 metric gaming）**移植成本项目下一轮迭代的
工作协议**，先出规划、不动 skill 文件。

---

## 1. TL;DR

| # | 结论 | 依据 |
|---|---|---|
| 1 | **`toolsmith-publish status` 现在是假警报**：prompt 侧永远报 `LOCAL NOT DEPLOYED`（exit 3），而实际线上与本地逐字节一致 | §4.1 自相矛盾输出 + live API `current_version_id` |
| 2 | **`publish`/`push-prompt` 的 in-place 路径现在会「写完再报失败」**（POST 成功后 `die("read-back mismatch")`） | `toolsmith-publish:362` 用同一坏键 |
| 3 | 项目真实状态 = **in-sync**（prompt v1.6 == 本地 `-v0.15.md`，skill 1.0.7 19/19 逐文件相同） | §3 表 |
| 4 | 我们**没有可比基线**：场景 A 两次 run 是 23 vs 41 次调用（+78%）、18 vs 34 turns，但**跨了 17:41 那次发布** → 台账里无法归因 | §6 离线重放表 |
| 5 | 拒绝路径（场景 B）**极稳**：8 vs 7 turns、8 vs 8 calls、33 vs 32s（还跨版本）→ 天然是廉价回归闸门 | §6 |
| 6 | **现在无法离线核「引用真的来自拉取结果」**：params 的 tool-return 是「预览 + 落盘指针」，`artifacts.zip` **不含 `tool_results/**`** | §7 |
| 7 | sys prompt 44516 B 里涉委派/子代理段落 **2 段 = 6908 B = 15.5%**，而 5 个 run **一次都没委派** → 可做「删段实验」 | §6/§10 E2 |
| 8 | 真正的结构性差距只有一条：autoresearch 有 `val_bpb`，我们**只有 13 项布尔断言 + 人工读产物** → 只能判「契约破没破」，判不了「这轮改动值不值得 keep」 | §5 映射表 |
| 9 | **差距已部分补上（S1.5，2026-09-16）**：`evals/fact-check/` = 必含事实清单 + 离线打分器，输出 `facts_ok/facts_total`；基线 A 31/31、B 12/12（2026-09-17 清单修订后；修订前 A 30/30），负向对照 GATE PASS（每条都能翻 FAIL） | `evals/fact-check/README.md` |

---

## 2. 用到的固定坐标（接手者直接用，勿改）

| 资源 | 值 |
|---|---|
| 仓库 / 子目录 / 分支 | `git@github.com:sdsliang/skill.git` / `clinical-result-comparison/` / `main` |
| 本地 sys（部署态） | `system-prompts/multi-clinical-result-comparison-v0.15.md`（44516 B，sha `fa80094e9d41`） |
| 本地 dist | `dist/multi-clinical-result-comparison-v0.15.zip`（19 entries，sha `de7c16b44910`） |
| 线上 prompt | family `91febc286412479a8b6d569fa3b8025e`，current `1f7586c0…` = **v1.6** == 本地文件 |
| 线上 skill | family `9fe0035bdd324b998436c6cb9c2de212`，current **v1.0.7**，`skill_id=ad75ec2c44334f389a0394895a47b765` |
| 项目 | `a7cdda6508e0423c8b7afaaf3a68e50d`（`resources.prompt = 1f7586c0…`；skills=`[chart-visualization-json, multi-clinical-result-comparison]`） |
| 工具 | `toolsmith-publish`（`~/.local/bin/`，单文件 Python，65790 B，mtime 2026-09-14 17:34；**非 git 仓库**，改它就是改本体） |
| 运行台账 | `~/.local/state/toolsmith-runs/<时间戳>-<tag>/`（`debug-history.json` / `stream.sse` / `artifacts.zip` / `artifacts/` / `verification.md`） |
| 验证日志 | `docs/toolsmith-verification-log.md`（`R<n>` 记录 + 两栏：我方/平台侧） |
| 凭证 | `$TS_BASE` / `$TS_TOKEN`（`~/.secrets`，勿写入任何文件） |

> 已 settled、**不必再查**：`project.prompt_id = ba2533ff…` 是 v1.3（v0.13 遗留字段），运行时用的是
> `current_version_id`，不构成漂移。

---

## 3. 现状核对（2026-09-16，live API 逐项对齐）

| 检查项 | 线上 | 本地 | 结论 |
|---|---|---|---|
| prompt family current | v1.6，bytes 44516，sha `fa80094e9d41` | `-v0.15.md` 同 sha | **一致** |
| 项目绑定 prompt | `1f7586c0…`（即 v1.6） | — | **一致** |
| skill current | v1.0.7，zip `entries=19 identical=19 differing=0` | `dist/…-v0.15.zip` | **一致** |
| `toolsmith-publish status` | 报 `OUT OF SYNC`（exit 3） | — | **工具误报**（§4） |

---

## 4. ⚠️ 闸门 1：`toolsmith-publish` prompt 侧「当前版本」解析坏了（**必须先修**）

### 4.1 证据：同一次 `status` 输出自相矛盾

```
PROMPT family 91febc286412479a8b6d569fa3b8025e  title='multi-clinical-result-comparison'
   v1.6   bytes= 44516 sha=fa80094e9d41 == local multi-clinical-result-comparison-v0.15.md
   local multi-clinical-result-comparison-v0.15.md bytes=44516 sha=fa80094e9d41
   -> prompt deployed == local: False  (LOCAL NOT DEPLOYED)
STATUS: OUT OF SYNC — publish needed          # exit 3
```

本地 sha 与线上 v1.6 sha 相同，却判「未部署」。

### 4.2 根因：平台返回 snake_case，工具读 camelCase

- Live API：`GET $TS_BASE/api/prompts/91febc28…` 顶层键是 **`current_version_id`**（值 `1f7586c0…`），
  没有 `currentVersionId`；`versions[]` 里也没有 `is_current` 字段。
- 工具：`~/.local/bin/toolsmith-publish` 第 **272 / 362 / 787 / 936 / 1094** 行读 `fam.get("currentVersionId")`
  → `None` → `prompt_ok = False`。
- 平台源码侧佐证：`apps/tool-smith/backend/src/toolsmith/schemas/prompt.py` 里
  `current_version_id: str = Field(alias="currentVersionId")`（`populate_by_name: True`）——
  部署端序列化没走 alias，字段名即 `current_version_id`。本地 clone 停在 `50f048b`，**部署端比它新**。
- 对照组：skill 侧走 `/api/skills/list`（每项带 `is_current`）→ 所以 skill 侧判断正常（能打出 `current=v1.0.7`）。

### 4.3 影响

1. `status` 永久 exit 3 → **不能再当提交前闸门**（`AGENTS.md` 里定义的用法失效）。
2. `push-prompt` / `publish` 的 in-place 路径是「先 POST 再读回校验」，读回用同一个坏键
   （`:362`）→ **真的写进线上之后 `die("read-back mismatch after publish")`**。
   人看到「失败」可能重发或回滚 —— 这是会把线上搞乱的那类 bug。
   （旁证：线上 v1.6 的 `updated_at` = 2026-09-14T17:41:40，正是当天发布动作；当时是否已报错未留记录。）

### 4.4 修法（改工具本体，非 skill）

- 5 处统一改成 `fam.get("currentVersionId") or fam.get("current_version_id")`（或抽一个 `_current_prompt_version()` helper）。
- 回读校验同样改；改完 `toolsmith-publish status` 应 **exit 0** 且打印 `in sync`。
- 验收：`status`（只读）绿 → 才算 S0 完成。**这是后续所有 write 动作的前置条件。**
- 交叠：`docs/toolsmith-run-v2-polling-plan.md` 的执行闸门也依赖 status/read-back，**先修本项再落地那份**。

---

## 5. 映射：autoresearch ↔ 本项目

| autoresearch | 本项目 | 现状 |
|---|---|---|
| `train.py`（agent 唯一可改） | `system-prompts/*-v0.15.md` + `skill/multi-clinical-result-comparison/**` | 改完 in-place 重发 |
| `prepare.py`（只读：数据 + tokenizer + `evaluate_bpb`） | **冻结面**：场景集（§8）+ `evals/fixtures` + 断言 harness + `runtime/citation-renderer.mjs` + `test/` + params 工具 schema（字段名权威） | ⚠️ **现在没明文冻结**，谁都能改 |
| `program.md`（人改） | 工作区 `AGENTS.md` 规则 + `docs/toolsmith-verification-log.md` §0 流程 | 已有雏形，就是我们的 program.md |
| 固定 5 分钟预算 | 单轮 run 的**成本上限**（墙钟 / 调用数） | 有数据，**无预算线** |
| `val_bpb`（单一可比标量） | **缺失** ← 唯一结构性差距 | 只有 13 项布尔断言 + 人工读产物 |
| `results.tsv` | `docs/toolsmith-verification-log.md` 的 `R<n>` | 有记录，**无「每轮一个数」** |
| keep commit / 差 `git reset` | `main`（或特性分支）上 commit / revert + in-place 重发上一版 | 已有 |
| NEVER STOP 通宵 | 现在：人给 A/B/C 决策清单 → 落地 → 跑 R → 报两栏 | 半自动 |

---

## 6. 基线证据：5 个 run 离线重放（**零新 run**）

数据源：`~/.local/state/toolsmith-runs/20260914-*`（`debug-history.json` 里 `part_kind=tool-call/tool-return/thinking`；
`instructions` 前缀比对本地 sys 判定当轮部署版本）。

| run | 时间 | 部署 sys | turns | calls | wall | execute | read_file | edit_file | params |
|---|---|---|---|---|---|---|---|---|---|
| `171953-cite-date` | 17:19 | 更早版本（`e6d9c5fd`，非本地前缀） | 16 | 21 | 127s | 8 | 3 | 0 | **8** |
| `173645-a-2valid`（场景 A） | 17:36 | `b3050f32`（v1.5 系） | 18 | **23** | 173s | 8 | 9 | 1 | 2 |
| `173947-b-refusal`（场景 B） | 17:39 | `b3050f32` | 8 | 8 | 33s | 3 | 0 | 0 | 3 |
| `174145-b2-refusal`（场景 B） | 17:41 | `1998f37d`（== 本地） | 7 | 8 | 32s | 4 | 0 | 0 | 2 |
| `174222-a2-2valid`（场景 A） | 17:42 | `1998f37d`（== 本地） | 34 | **41** | 207s | **18** | 13 | **5** | 2 |

**三条结论**：

1. **没有干净重复**。场景 A 的两次（23 → 41 calls，+78%；18 → 34 turns）**跨了 17:41 那次发布**
   → 「A 组六项硬化到底帮了还是害了」**无法归因**。这就是「没有噪声带就不能 keep/discard」。
2. **拒绝路径极稳**（8/7 turns、8/8 calls、33/32 s，且跨版本）→ 廉价回归闸门（~30 s/次，每次改动后必跑）。
3. **`params` 调用数 2 ↔ 8 波动**（同一句话输入，v1.5 内也出现过 8）→ 有可硬化的纪律空间，但目前无人量它。

**工作方式差异（同场景、跨版本）**：A1 artifacts = `scripts/gen_report.py` + `scripts/digest.txt`；
A2 = `digest/records.txt` + `scripts/build_report.py`，且 A2 多花 10 次 execute / 4 次 edit_file
（推测与「digest ≤300 行」新规有关）。**成本升了，质量有没有升？现有台账答不了** —— 这正是 §9 要解决的。

**其余事实**：sys 44516 B 中涉委派/子代理段落 **2 段 = 6908 B（15.5%）**；5 个 run 的 `calls` 里 **都没有 `task`**
（即从未委派）；场景 A 两次都只产 1 张图 `visualizations/endpoint-bar-1.json`（无 timeline 图 —— 两条 esid 是否同
试验未核，**不要**据此判规则违反）。

复现命令见 §13.1 / §13.2。

**返工的另一条观测通道**：持久化消息里的 `retry-prompt` 能看到 SSE 看不见的**模型工具参数返工**
（姐妹文档 `docs/toolsmith-run-v2-polling-plan.md` 实测：5 次运行中 1 次，`a2-2valid` 把 `shell_command` 写成 `command`）
→ E3（正文返工）的计数应同时统计 `retry-prompt`，否则会漏掉这一类返工。

---

## 7. ⚠️ 闸门 2 / harness 缺口：receipt 通道没归档

`pharmcube` 的 tool-return **不是全文**，而是「预览 + 落盘指针」：

```
.../tool_results/pharmcube-query-clinical-result-with-params/call_f79508d1c721.jsonl for script access
```

实测：A1 两次返回 5503 B / 11900 B；A2 为 5503 B / **717 B（基本只有指针）**（A2 改走 jsonl → digest）。
`artifacts.zip` **只含 output/visualizations/scripts 等产物，不含 `tool_results/**`**。后果：

- **无法**验证 citations 的 `title`/`link` 是否逐字节来自拉取结果 —— 而现有 R 断言只查「键集 / 日期格式 /
  `title` 非空」，正是「空壳也能过」的那类（对照 2026-09-14 的教训）。
- **不能**用「title 是否出现在 tool-return 文本里」当断言：预览被截断 → 必然假警报。
- 初步观察（**待样本、勿当结论**）：A1 的 `ref_2`、A2 的 `ref_1` 的 title/link 都没出现在各自工具返回**预览**里。
  两种解释未区分：① 预览截断；② 条目并非来自本次拉取。补齐归档后即可定论。

**要做的**：run harness 增加归档 `/workspace/tool_results/**/*.jsonl`（或在 run 结束时落一份），
receipt 类断言一律从**工具返回真值**取，不从产物自述取。

---

## 8. 循环协议（我们版的 `program.md`）

### 8.1 固定场景集（写进冻结面；改它 = 开新基线）

| 场景 | 输入（用户话术） | 期望 | 用途 |
|---|---|---|---|
| **A** | `解读这几个结果 24_1_30561610 24_1_36342163` | 出 `report.md` + 1 图 + `citations.json` | 主战场，**需 3 次重复**取噪声带；判分 `check.py --scenario a`（30 条 fail 级事实） |
| **B** | `解读这几个结果 24_1_30561610 24_1_45608045` | **拒绝产出**（1 有效 1 无效） | 廉价回归闸门（~30 s）；判分 `check.py --scenario b`（12 条 fail 级事实） |
| **C** | 18 esid 跨试验 | 多图 + 分组契约 | 只在改图表/委派时跑（贵）；**尚无清单** |
| **D** | 4 esid 同试验 | 时间轴图 ≤1 且稳定 | 只测「图数是否被规则钉住」；**尚无清单** |

**事实清单（S1.5，已落地）**：`evals/fact-check/` —— ground truth 来自 `POST /api/tools/debug` 的真实返回
（`records/*.json`），清单先于产物撰写，`check.py` 离线判分并输出 `SCORE scenario=<a|b> facts <ok>/<total>`；
`mutations.py` 用负向对照证明每条都能翻 FAIL（当前 A 31/31、B 12/12）。用法见 `evals/fact-check/README.md`。

### 8.2 一轮 = 一个假设（硬纪律；A 组六项一起改就是反例）

1. **写假设**：改哪条规则 → 期望动哪个指标 → 方向。
2. **只改一个变量**。
3. `pack`（打包脚本，见 `docs/toolsmith-verification-log.md`）→ `publish`（in-place）→ `status` 必须绿。
4. `toolsmith-publish run --prompt-file … --tag r<n>`（场景 A；质量可疑时 A×3）。
5. 读 harness 分数 → **keep**（前进）或 **discard**（`git revert` 该改动 + in-place 重发上一版）。
6. 在 `docs/toolsmith-verification-log.md` 记一条 `R<n>` + 一行 TSV。
7. **再跑一遍事实清单**（`check.py --scenario a`；动了拒产路径则加 `--scenario b`），把 `facts_ok/facts_total`
   记进同一条 `R<n>`：成本层降了但事实分掉了 = discard，成本层不动而事实分升了 = keep。

### 8.3 `results.tsv`（我们版；tab 分隔，**不入库**）

```
r  commit  deployed_sys_sha  scenario  turns  calls  wall_s  params_calls  execute  edit_file  thinking_chars  gate_pass  facts_ok  facts_total  status  description
```

全部字段可从 `debug-history.json` 离线抽（§13.1）。§6 的 5 行可直接回填（**零新 run**）。

---

## 9. 指标：双层，不要单一总分

- **成本层（唯一「可比的数」）**：`calls`（辅助 `turns`、`wall_s`）—— 在质量门不掉的前提下越低越好。
  它扮演 `val_bpb` 的角色，但**只在成本维度**。
- **质量层（gate，布尔，不进总分）**：现有 13 项断言 + 新增 receipt 类（§7）。
- **质量层现在另有一个离线标量（S1.5，已落地）**：`evals/fact-check` 的 `facts_ok/facts_total`。它不同于
  `val_bpb`：只衡量「清单里写明的事实说对了多少条」，不含任何与成本无关的加权；用途是给 keep/discard 提供一个
  不随 run 抖动的下界（同样两段报告，一条把 `−13.9%` 写成 `−19.9%`，只有它会掉分）。**成本层仍不能拿它换**：
  命中率相同不等于报告一样好，漏掉清单没写的事照样 PASS（README 已明写这条缺口）。
- **为什么拒绝单一标量**：autoresearch 的 `val_bpb` 被 gaming（该仓 issue #599：agent 拥有 `train.py`，
  可以不调 `optimizer.step()`、可以包一层 `evaluate_bpb`，照样打出 `KEEP`）；我们这里的等价作弊是
  「临床判断写错但引用齐全，分数照样好看」。质量永远当 gate，不当分数。
- **预算线**：等 §6 的噪声带出来后再定（初值：场景 A `calls ≤ 30` 且 `wall ≤ 240 s`，**待基线修正**）。

---

## 10. 反 gaming 三条硬约束（issue #599 的直接移植）

1. **来源类断言必须从工具返回取真值**，不读产物自述 → 前置：补齐 §7 的 `tool_results` 归档。
   *（S1.5 已部分取代这条：事实清单的真值直接取自 `POST /api/tools/debug` 的 record，与产物完全解耦。）*
2. **评测面冻结**：场景集 + fixtures + 断言脚本不可被被评测方改；改 = 开新基线，不许原地调参。
3. **产物不自证**：分数由 harness 计算并追加，不由产出方写。
   附带一问（把 2026-09-14 的教训泛化）：**这条断言能被空产物糊过吗？能被「不调工具」糊过吗？能被「改自己」糊过吗？**

---

## 11. 候选实验队列（按性价比排序）

| # | 假设 | 证据 | 改动面 | 判定信号 | 成本 | 风险 / 回滚点 |
|---|---|---|---|---|---|---|
| **E0** | citations 里存在「非本次拉取」的条目 | §7 的两处缺失（解释待定） | 只加 harness 检查 | receipts 命中率 | **0（离线回测）** | 先立口径（用归档 jsonl 而非预览），否则假警报 |
| **E1** | 场景 A 有可测量的噪声带 | 23 vs 41 calls 跨版本 → 无干净重复 | 无（同版本跑 3 次） | calls 均值 ± σ | 3 run ≈ 3×3 min | 无；这是所有后续判定的前提 |
| **E2** | **委派段可大幅精简/删除** | sys 中该段 6908 B = 15.5%；5 个 run 从未委派 | sys 一段 | `calls`/`thinking_chars` 不升 | 1 publish + 3 run | 大样本（C）退化 → 留 C 基线；回滚 = revert 该段 |
| **E3** | 正文返工可在源头消掉 | A2：execute 18 / edit_file 5；台账 O4「句子级 `s.replace()` 8 次」 | skill 的一条渲染纪律 | execute / edit_file 计数 | 1 publish + 3 run | 规则越写越长反而升本 → 简优先 |
| **E4** | `params` 调用纪律可收敛到 ≤2 | 同版内 2 ↔ 8；`cite-date` 8 次只拉 2 个 esid | 现有「最多再一次批调用」硬化 | **`params_calls ≤ 2` 可硬断言** | 1 publish + 3 run | 误伤「确认缺失」合法路径 |
| **E5** | 图表张数受规则钉住 | 场景 A 两次都是 1 张 bar；A7 上限规则只观测 1 次 | 无（复用 E1 的 run 观测） | 图数方差 | 0（搭 E1） | 无 |
| **E6** | B8–B10 对外沟通项（bar 负值问题单 / `{{ref_n}}` 前端报备 / CLI 路径口径） | 用户已拍板「攒着」 | — | — | — | **不做** |
| **E7** | **删规则也能赢**：在事实清单不掉分的前提下压 `calls` | S1.5 基线分已拿到（A 31/31、B 12/12） | sys/skill 各一段 | `facts_ok` 不掉 + `calls` 降 | 1 publish + 3 run + 0 新 run 判分 | 事实分掉了就 revert（这正是清单存在的意义） |

---

## 12. 明确不做

- **不做通宵自主循环**：本项目的真值面（临床正确性）需要人；单轮 ~3 min 跑不出意义，无人值守只会把错误规则固化。
- **不做单一总分替代人工判读**（§9）。
- **不为分数改规则**：每加一条规则都多一份权衡思考成本 —— simplicity criterion 在这里的形态是「删规则也能赢」（E2）。
- **不动挂起项**：表格整表复制/下载（等何林杰）、bar 柱下钻、`drillDownValue` 契约。

---

## 13. 执行顺序与授权清单

| 步 | 内容 | 写动作 | 授权 | 成本 |
|---|---|---|---|---|
| **S0** | 修 `toolsmith-publish` 5 处键名 → `status` 应 exit 0 | 改工具本体 | 需用户点头 | 分钟级 |
| **S1** | harness 骨架 + §6 五行离线回填 TSV；补 `tool_results/**` 归档 → 跑 E0 receipts 回测 | 新增脚本（**不动 skill**） | 需点头 | 0 新 run |
| ~~**S1.5**~~ | ✅ **已完成 2026-09-16**：必含事实清单 + 离线打分器 + 负向对照 → `evals/fact-check/`（A 30 条 / B 12 条，基线全 PASS，`mutations.py` GATE PASS） | 新增 eval 资产（**不动 skill/sys**） | 已执行 | 0 新 run |
| **S2** | 场景 A ×3 取噪声带（E1）；顺带白拿 E5 图数方差 | 3 次 `run`（创建线程） | 需点头 | ~10 min 墙钟 |
| **S3** | 按噪声带选 2 个最稳实验（建议 E2 删段 + E3 返工），一次一个变量 | publish ×2 + run 若干 | 每次 publish/run 前确认 | 半天内 |
| **S4** | 把「冻结面 + 场景集 + TSV 列」写进 `AGENTS.md`/`PROJECT_STATE.md`，形成常驻 program.md | 文档 | 需点头 | 分钟级 |

**未授权事项一律不做**：本文写完后**没有** commit、没有 publish、没有 run、没有改 skill/sys。
按仓库规矩，任何 git 写动作（commit/push）与 ToolSmith 发布**都要单独再确认**。

---

## 14. 附录：复现命令

### 14.1 离线重放一组 run（turns / calls / wall / thinking / 工具分布）

```bash
cd ~/.local/state/toolsmith-runs && python3 - <<'EOF'
import json,glob,collections,datetime
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
for r in sorted(glob.glob('20260914-*')):
    m=json.load(open(f'{r}/debug-history.json'))['raw_model_messages']
    turns=sum(1 for x in m if x['kind']=='response'); calls=collections.Counter(); think=0; times=[]
    for x in m:
        for p in (x.get('parts') or []):
            k=p.get('part_kind')
            if x['kind']=='response' and k=='tool-call': calls[p.get('tool_name')]+=1
            if x['kind']=='response' and k=='thinking': think+=len(p.get('content') or '')
            if p.get('timestamp'): times.append(ts(p['timestamp']))
    print(f"{r}: turns={turns} calls={sum(calls.values())} think={think} wall={((max(times)-min(times)).total_seconds()):.0f}s {dict(calls)}")
EOF
```

### 14.2 判定某一 run 当轮部署的 sys 版本（是否等于本地）

```bash
python3 - <<'EOF'
import json,glob,hashlib
local=open('system-prompts/multi-clinical-result-comparison-v0.15.md','rb').read()
for r in sorted(glob.glob('/home/xupeipeioo1/.local/state/toolsmith-runs/20260914-*')):
    m=json.load(open(f'{r}/debug-history.json'))['raw_model_messages']
    b=(m[0].get('instructions') or '').encode()
    print(r.split('/')[-1], len(b), hashlib.sha256(b).hexdigest()[:12], 'local_prefix=', b[:len(local)]==local)
EOF
```

### 14.3 读「工具返回」的正确姿势（注意：tool-return 在 `kind == "request"` 的消息里）

```python
rets = [(p.get('tool_name'), p.get('content'))
        for x in m for p in (x.get('parts') or []) if p.get('part_kind')=='tool-return']
# content 可能是「预览 + `.../tool_results/<tool>/call_xxx.jsonl for script access`」指针 → 断言前先确认是否被截断
```

### 14.4 核对线上/本地是否真的一致（只读）

```bash
toolsmith-publish status                     # 注意：修 §4 之前 prompt 侧恒为假警报
curl -sS -H "Authorization: Bearer $TS_TOKEN" "$TS_BASE/api/prompts/91febc286412479a8b6d569fa3b8025e" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['current_version_id'], [ (v['version'], len(v['content'])) for v in d['versions'] ])"
curl -sS -H "Authorization: Bearer $TS_TOKEN" "$TS_BASE/api/projects/a7cdda6508e0423c8b7afaaf3a68e50d/resources" | python3 -m json.tool
```
