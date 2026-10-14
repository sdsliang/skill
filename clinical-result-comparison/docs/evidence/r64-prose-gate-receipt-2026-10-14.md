# R64 —— 文体门禁假 FAIL：把「扫描器回执」从「提到 tell-scan 的任何输出」里区分出来（2026-10-14）

**层次**：**runner**（`~/.local/bin/toolsmith-publish`，本地 CLI）。**不改运行期文本、不改交付包、不发版、不起真跑。**
**账目**：O51（runner 缺陷）/ R61-3（同一编号在 R61 节已预登记，本轮落地）/ 旧名 B9。

---

## 1. 动机：每轮验收只有这一个信号

`r61-sem-2`（`20261013-134217-r61-sem-2`）的 2 条 FAIL 里，1 条是平台侧（`P-R53-1`），另 1 条是**我们自己的假 FAIL**：

- 第 25 步把 4 条命令串成一条 `execute`：
  `patch.py … && patch.py … && … check_report.py -v … && tell-scan.py /workspace/output/report.md; echo "SCAN_EXIT=$?"`
- **第一个 `patch.py` 断言失败**（`ASSERT FAILED: /workspace/output/report.md contains 0 occurrence(s) of the pattern, wanted 1` / `nothing written`），`patch.py` 的失败退出码**也是 3**；
- `&&` 短路 ⇒ `check_report.py` / `tell-scan.py` **在该命令里从未执行**，`echo` 打出的 `SCAN_EXIT=3` 是 **`patch.py` 的退出码**；
- 旧 runner 把「命令文本里提到 `tell-scan.py` 的**所有** return」拼成一整块再全局 `re.findall(r"SCAN_EXIT=(\d+)")` ⇒ 采到这个 3；
- 同跑第 34 步（另一条命令）**真的跑过扫描器**：`强 0 / 弱 1`（W-FMT-MIXED 弱命中）、`SCAN_EXIT=0`。

`run.json` 逐字留证：

```
"fails": ["prose gate exited clean (or its strong hits were --allow'ed)", "tool_results receipts archived"]
"exit": 3
```

⇒ **该 run 的文体门禁实际干净，这条 FAIL 是假 FAIL。** 危害在于验收侧：本仓每轮只有「断言数」这一个信号，**假 FAIL 与内容回潮（真 FAIL）不可区分**。

## 2. 顺带查出 R63 自己埋的雷（本轮消掉一半）

R63 统一教全脚本调用形态 `… 2>&1 | tail -30; echo "EXIT=${PIPESTATUS[0]}"`，而 tell-scan 的专项写法仍是 `… report.md; echo "SCAN_EXIT=$?"`（prompt L166 / `SKILL.md` L141·L206 / `toolbox.md` L340 **四处仍在教**）。**两套并存的实测后果**：

| 情形 | 三跑实测 | 旧 runner 结论 |
|---|---|---|
| 模型照专项写法（本次三跑都是） | `SCAN_EXIT=0` 出现，banner 未被 `tail` 截掉（tell-scan 的 `合计强命中` 合计行打在最后） | PASS（正确，**未造成损失**） |
| 模型照通用写法 `EXIT=${PIPESTATUS[0]}` | 干净跑 | PASS（靠 banner 兜底）——**正确** |
| 同上，但**脏跑**（强命中未处理） | — | **降级成 WARN，照样绿** ⇒ **信号漏洞** |

⇒ runner 侧本轮一并补上；**文本里的双写法冲突本身留到 R65** 收紧（改文本要发版，不塞进这一轮）。

## 3. 改动（只在 runner 层）

| 改前 | 改后 |
|---|---|
| 把「提到 `tell-scan.py`」的所有 return **拼成一整块**，全局 `re.findall(r"SCAN_EXIT=(\d+)")` | **逐 tool-return** 判定：只有自带扫描器 banner（`强 N / 弱 M` 表头 或 `合计强命中 N 条` 合计行）的 return 才算「扫描器回执」；**没有 banner 的 return 完全不计** |
| 只认 `SCAN_EXIT=`，且在整个 return 文本里找 | 退出码只从 **banner 之后**的文本里找（管道后的 `echo` 正落在那儿）；接受 `SCAN_EXIT=` / `EXIT=` / 预留 `[tell-scan] exit=`；**同名冲突时 `SCAN_EXIT` 优先**（防同链后续命令的 `EXIT=3` 污染） |
| 无 | 原修法①（`tell-scan.py` 自打 `[tell-scan] exit=N`）**不做**（banner 本身就是回执），但 runner **预先接受**该标记：日后若加，无需再改 runner |

断言名与 WARN 语义一字未改（`prose gate ran and exited clean` / `… exit code was not echoed (verdict unreadable)`），FAIL 详情里加了回执条数。

`evals/runner-gate/test-runner.py`：**45 → 48**

- 脏样本改成 tell-scan 的**真实打印形态**（`[zh] 强 N / 弱 M` 表头 + `合计强命中 N 条` 合计行）——旧样本 `'L3 [强] …\nSCAN_EXIT=3'` 是现实里不会出现的片段（扫描器任何时候都会打表头与合计行）；
- 新增 3 例：① **B9 形状**（同链 `patch.py` 断言失败 + `SCAN_EXIT=3`，无 banner）必须**不 FAIL**；② R63 的 `EXIT=` 形态必须**可读**；③ 同链后续命令的 `EXIT=3` **不得污染**已判定的干净扫描。

## 4. 验收：三层证据（不需要真跑）

### 4.1 单元 A/B（旧 runner vs 新 runner）

```
$ python3 -B evals/runner-gate/test-runner.py                        # 新
Ran 48 tests in 0.540s — OK
$ TOOLSMITH_PUBLISH=~/.local/state/toolsmith-publish/toolsmith-publish.v12.bak \
    python3 -B evals/runner-gate/test-runner.py                     # 旧
FAIL: test_scanner_exit_code_from_a_non_scanner_command_is_ignored
AssertionError: ["prose gate exited clean (or its strong hits were --allow'ed)"] != []
```

⇒ 新例对旧 runner **必 FAIL**（回归哨），对新 runner PASS。

### 4.2 存档 run A/B 复现（同 `r61-sem-2`，同 `run.json`）

`/tmp/r64/ab.py` 直接 import 两个 runner 版本并调 `check_run`（与 O48 先例同法）：

```
$ python3 -B /tmp/r64/ab.py v12.bak ~/.local/bin/toolsmith-publish \
    ~/.local/state/toolsmith-runs/20261013-134217-r61-sem-2
### OLD runner: .../toolsmith-publish.v12.bak
   total=23 FAIL=5 | FAILS: ['deployed system prompt == local', 'deployed skill body == local SKILL.md',
     'deployed support-file manifest matches local (28 files)',
     "prose gate exited clean (or its strong hits were --allow'ed)", 'tool_results receipts archived']
   FAIL: prose gate exited clean (or its strong hits were --allow'ed) -- SCAN_EXIT=[0, 3, 0]: …
### NEW runner: ~/.local/bin/toolsmith-publish
   total=23 FAIL=4 | FAILS: ['deployed system prompt == local', 'deployed skill body == local SKILL.md',
     'deployed support-file manifest matches local (28 files)', 'tool_results receipts archived']
   PASS: prose gate ran and exited clean -- 3 call(s), 2 scanner receipt(s), SCAN_EXIT=[0, 0] strong-free=True
```

旧 arm 的 `SCAN_EXIT=[0, 3, 0]` 与 `run.json.fails` 逐字相同 ⇒ 复现成立；新 arm 把 3 条 return 分成 **3 call(s) / 2 扫描器回执**，采到 `[0, 0]`。
另 3 条 FAIL 两 arm 相同且与本次无关：前两条是「拿今天本地树去比 R61 时期部署内容」的必然结果（会随每次内容轮变化），第三条 `P-R53-1` 是已知平台项。

### 4.3 全量本地闸门

```
py_compile rc=0 | test-render-facts 29 OK | test-skill-scripts 62 OK | test-tell-scan 10 OK
test-check-report 25 OK | test-build-ledger-scaffold 9 OK | test-merge-ref-facts 16 OK
test_regressions 35 OK | mutations arm a 44/44 b 12/12 GATE PASS | test-runner 48 OK
verify-run-chain GATE: PASS (5 comparable) | test_pack_dist 5 OK | test_replay_run 14 OK
node --test rc=0 | pack-dist --check IDENTICAL (181638 B / sha 39640fd6e679)
==== GATES_FAILED=0 ====
```

**不发版**：本轮未动 `skill/` 与 `system-prompts/` 一个字节；`toolsmith-publish status` 仍报 **in sync**（prompt v1.8 `91febc286412479a8b6d569fa3b8025e` / 80,960 B；skill v1.0.9 `16aeb0406e12425bad27a2444f17225e` / 181,638 B / 29 entries）。runner **不在交付包内**（`pack-dist` 的 29 条目不含它），所以 F↔A 两本账都不受影响。

## 5. 回滚

```
cp ~/.local/state/toolsmith-publish/toolsmith-publish.o51-before-20261014.bak ~/.local/bin/toolsmith-publish
# md5 f3a25b7487293c1acdb134f3ef5a685a（= 改前，= toolsmith-publish.v12.bak）
```

## 6. 遗留

- **R65 候选 A（首选）**：token 契约唯一化 + 提交前可自查（打输出 token 量，见 R63-0 的相关性结论）——**顺带把双退出码写法冲突在文本里一次说清**。
- **R66 候选 B（降级）**：惰性段条件化（按 R63-0，只作用于每步固定开销）。
- **R61-4**：`references/same-trial-evolution.md` 三轮 0 真读（改运行期文本 ⇒ 需发布授权）。
- 平台侧：`P-R53-1`（每跑命中）、`P-R59-1`、`P-R59-3`、`P-R56-1~4` 状态不变。

## 7. 复算命令

```bash
cd ~/.local/state/toolsmith-runs
python3 -B /tmp/r64/ab.py <旧runner> <新runner> 20261013-134217-r61-sem-2   # 存档 run A/B
python3 -B /tmp/r64/scan.py 20261014-110640-r63-4 20261014-111536-r63-18 20261014-112254-r63-14   # 三跑回执清点
cd /home/xupeipeioo1/apps/skill/clinical-result-comparison && bash /tmp/r63/gates.sh   # 全量本地闸门
```
