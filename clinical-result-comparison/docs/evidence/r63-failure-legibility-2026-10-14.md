# R63 — 失败可见性：fail-closed 脚本必须自己说出原因、调用方必须拿到真退出码（2026-10-14，原地发布 + 固定三组实测）

> 本轮是 R62-1 的收口：**只改「失败如何被看见」，不动任何规则文本**。
> 结论先写：**形态类判据全部达成（二分/`runpy`/`--help` 形态 7+4+1 → 全 0，`PIPESTATUS` 全组采用）；但本次三跑里新的 stderr 通道一次都没被触发，因此本轮不能宣称节省墙钟——反而修正了 R62 的一个断言（见 §7）。判定 KEEP（不劣化）。**

## 1. 单一假设与预登记判据

**假设**：R62-1 实测的「一次校验失败放大成 18 次调用」，主因是 **fail-closed 脚本静默 + 调用方拿到假退出码**。若把失败原因打到 stderr 并把真退出码交给调用方，则同样输入下**不再出现**探测形态（`head -n` 二分 / `runpy` 取 traceback / `--help` 钓鱼），且该组步数回落。

**预登记判据（跑之前写下，事后不改）**：

| 类 | 判据 | 达成条件 |
|---|---|---|
| 形态 | 三跑中 `head -n` / `runpy` / `--help` 形态计数 | 全 0 |
| 形态 | 管道调用的退出码不再被 `$?` 吞掉 | `PIPESTATUS` 出现在每次管道调用里 |
| 步数 | 14 组步数（R62 = 65） | 回落到 R48–R52 同输入带内 |
| 不劣化 | 三组断言 / 产物 / `args-refused` / `fetch-failed` | 零退化 |
| 红线 | 规则文本 | 一条不删 |

## 2. 改了什么（4 处运行期文件 + 1 处测试，字节账）

| 文件 | 改前 | 改后 | Δ | 内容 |
|---|---:|---:|---:|---|
| `scripts/render-facts.py` | 36,634 B | **37,696 B** | +1,062 | 新增 `_report_failure(audit, audit_path)`：失败时把 `render-facts: FAILED — nothing written` + `audit["errors"]` 逐条 + 汇总打到 **stderr**；`main` 由 `return 0 if render(...) else 1` 改为 **`else 3`**（与其余 7 个打包脚本的退出码约定统一） |
| `references/toolbox.md` | 26,272 B | **27,540 B** | +1,268 | 新增「Invoke them so a failure is readable」段：教 `… 2>&1 \| tail -30; echo "EXIT=${PIPESTATUS[0]}"`、点名 `$?` 吞码陷阱、「非 0 先读脚本自己指名的输入」、写明实测代价 **18 次调用 / 28% 步数** |
| `system-prompts/multi-clinical-result-comparison-v0.16.md` | 79,886 B | **80,960 B** | +1,074 | 同一调用形态（全脚本）；render-facts 段写明「fails closed（exit 3）并把每条 finding 打到 stderr」；**新规则「自我对话不算正文」**——禁止把修复旁白 / 自省片段写进任何交付文件 |
| `SKILL.md` | 44,780 B | **45,485 B** | +705 | 同上调用形态 + 同一条自我对话禁令 |
| `evals/numeric-integrity/test-render-facts.py` | 28 测试 | **29 测试** | +1 | `test_cli_failure_announces_itself_on_stderr_and_exits_3`：断言 returncode **3**、stdout `""`、stderr 含 `FAILED` 与 `unknown fact token`、输出文件未被改写、`audit["success"]` 为 False |
| `dist/…-v0.16.zip` | 180,410 B / `f5e32baa1c33` | **181,638 B / `39640fd6e679`** | +1,228 | 29 entries，重打后 `--check` IDENTICAL |

**红线核对**：`## Step discipline` 8 条规则、`## Numeric Integrity`、`## Final verification` 等规则文本**一条未删**；本轮只在既有段落里追加「如何调用 / 失败怎么办」的通道说明，以及一条只约束**交付物内容**的新禁令。发布前 diff 已逐段核对。

## 3. 本地闸门（全绿，发布前）

`py_compile` rc=0；`test-render-facts` **29 OK**（新增 1 项）；`test-skill-scripts` 62 OK；`test-tell-scan` 10 OK；`test-check-report` 25 OK；`test-build-ledger-scaffold` 9 OK；`test-merge-ref-facts` 16 OK；`test_regressions` 35 OK；mutations **arm a 44/44 + arm b 12/12 GATE PASS**；`test-runner` 45 OK；`verify-run-chain` GATE PASS（5 项可比）；`test_pack_dist` 5 OK；`test_replay_run` 14 OK；`node --test` 16 pass。

**`pack-dist --check` 先 rc=3 DIFFERS**（改脚本后未重打包）→ 重打 → **IDENTICAL**（181,638 B / 29 entries / `39640fd6e679`）→ 复检 rc=0。

**本地失败通道探针（真跑未触发时用离线证据顶上）**：

```bash
# draft 里放一个不存在的 fact id
printf '# t\n\n数值 [[fact:NOPE]]。\n' > /tmp/p.md
python3 -B skill/multi-clinical-result-comparison/scripts/render-facts.py \
  --ledger <真账本> --draft /tmp/p.md --out /tmp/o.md --audit /tmp/a.json
echo "EXIT=$?"   # → EXIT=3；stdout 0 B；stderr 223 B，含 FAILED + facts[0].source_file does not exist
```

## 4. 发布（原地更新，版本号标签不变、内容替换）

| 资源 | 版本 / id | 时间 | 结果 |
|---|---|---|---|
| prompt | **v1.8** `91febc286412479a8b6d569fa3b8025e` | 2026-10-14T11:06 前后 | 80,960 B / sha **`e7e84cdbf450`**，与本地逐字节一致 |
| skill | **v1.0.9** `16aeb0406e12425bad27a2444f17225e` | 同上 | 29/29 支持文件逐个一致 |

发布前 `toolsmith-publish status` → OUT OF SYNC（3 个技能文件差异：`SKILL.md` / `references/toolbox.md` / `scripts/render-facts.py`，正是本轮改动）⇒ 反向证明了改动确实进了包。`publish` → HTTP 200；`status` 回读 → **in sync**。project `a7cdda6508e0423c8b7afaaf3a68e50d`。

## 5. 真跑（固定三组 4 / 18 / 14，输入复用 R48/R50 逐字节、**串行**；`DeepSeek Flash`，web off）

| run | 目录 / thread | refs | wall s | 步 | 工具调用 | out tok | reasoning | PIPESTATUS 次数 | 形态探测 | 断言 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `r63-4` | `20261014-110640-r63-4` / `d2ac2bbc-19ef-46f3-90b4-7e849c05d35d` | 4 | 526.5 | 25 | 35 | 97,495 | 78,312 | 6 | 0/0/0 | 22 PASS / 1 FAIL |
| `r63-18` | `20261014-111536-r63-18` / `aba2e0c2-2d2b-4e34-850e-6fce519094b7` | 18 | 425.5 | 26 | 29 | 75,899 | 47,709 | 7 | 0/0/0 | 22 PASS / 1 FAIL |
| `r63-14` | `20261014-112254-r63-14` / `9ada5cde-3295-4750-9623-32dd8dc572f1` | 14 | 688.6 | 23 | 31 | 123,494 | 89,932 | 8 | 0/0/0 | 22 PASS / 1 FAIL |

三跑 `outcome=succeeded`、产物齐全、`args-refused=0`、`fetch-failed=0`、无 `tool-output-error`；**唯一 FAIL 三跑同一个 = 已知平台项 `P-R53-1`（`tool_results receipts archived`）**。`r63-18` 出现过一次平台参数形态重试（`execute: ['shell_command'] Field required; ['command'] Extra inputs…` = `P-R59-1`）。

## 6. 判据核对：形态类 → 全部达成

对照 `r62-14`（R63 前，同一输入）：`head -n` **7** 次 / `runpy` **4** 次 / `--help` **1** 次。

- **R63 三跑：`head -n` 0 / `runpy` 0 / `--help` 0。** 二分报告、取 traceback、钓 `--help` 三种探索形态**全部消失**。
- **`PIPESTATUS` 全面采用**：R62 三跑该写法出现 **0** 次；R63 三跑每次管道调用都带 `2>&1 | tail -N; echo "EXIT=${PIPESTATUS[0]}"`（`r63-14` 里连「探针试渲染」的临时调用也是这个形态，并正确读到了 `EXIT=2` 的 argparse 用法错误）。
- ⇒ **R62-1 里「模型拿到假退出码」这个机制已被关闭**，且模型不但照做，还把它推广到了自己的临时调试调用上。

## 7. 判据核对：步数类 → 达成，但**必须修正 R62 的因果结论**

**同输入历史带（R48 起、三组固定输入、有墙钟，各 run 用同一口径复算；n=39）**：

| 量 | 4 组（n=25） | 18 组（n=4） | 14 组（n=4） | R63 实测（4/18/14） | 落点 |
|---|---|---|---|---|---|
| 工具调用 | 23–69，中位 32 | 36–59，中位 46 | 28–66，中位 34 | 35 / **29** / 31 | 4、14 带内；**18 破历史下界** |
| 步 | 19–64，中位 26 | 32–50，中位 40 | 23–63，中位 31 | 25 / **26** / **23** | 4 带内；18、14 在下界 |
| out tok | 52.6k–112.6k，中位 70.2k | 85.7k–118.9k，中位 104.7k | 69.3k–113.4k，中位 87.6k | 97.5k / **75.9k** / **123.5k** | 4 带内偏高；18 破下界；**14 破历史上界** |
| wall s | 252–683，中位 405 | 465–617，中位 536 | 310–708，中位 506 | 526.5 / **425.5** / 688.6 | 全部带内 |

- **14 组的调用数终于回到带内**：`r62-14` 65 次（= 带内最差）→ `r63-14` **31 次**（≈ 中位 34）。**R62-1 的形态确实没有复现。**
- **18 组四项全破历史下界**（调用 36→29、步 32→26、out 85.7k→75.9k、wall 465→425.5）：这是三个组里唯一**四项同时偏好**的组。
- **但墙钟**：4 组 526.5（band 252–683，中位 405）偏高、18 组 425.5 偏低、14 组 688.6（band 310–708；`r62-14` = 690.3、`r52-14` = 708.3）≈ 持平。**没有任何一组给出可声明的提速。**

**修正 R62 的断言（本轮最重要的账目更正）**：R62 写的是「步数是时间的乘数，**减步数是最大可控项**」。用同口径 n=39 复算相关系数：

| 与 wall 的相关 | r |
|---|---:|
| **输出 token 总量** | **+0.924** |
| 其中推理 token | +0.862 |
| 工具调用数 | +0.735 |
| 步数 | +0.702 |
| 落笔（非推理）token | +0.628 |

⇒ **墙钟的驱动量是输出 token 量，不是步数**；步数只是它的弱代理（每步固定开销 1.6–3.2 s 是真的，但步次间 token 量的波动更大）。本轮就是活证：`r63-14` 调用数砍半（65→31）、墙钟**纹丝不动**（690.3→688.6），因为 out tok 从 94.5k 升到 123.5k。

同样据此撤回 R63 自己的预期：**「省 150–200 s」这个预测不成立**——18 次调用里大部分是低 token 的小步，砍掉它们省下的是每步固定开销（约 30–60 s 量级），而同一输入上 token 量的自然波动 ±30% 足以吞掉它。

## 8. 诚实记账：新 stderr 通道在真跑里**一次都没被触发**

三跑中 `render-facts: FAILED` 出现次数 = **0**；`unknown fact token` / `unresolved fact` / `not an exact source substring` 等校验失败字符串出现次数 = **0**（对照 `r62-14` = 1）。也就是说：**本轮改动的主路径（失败时发声）在三跑里没被走到**，因为它要防的那个触发源（把自我旁白写进交付正文）这次没发生——**预防生效与通道未被触发，在 n=1 上无法区分**。

所以本轮的证据结构是：

- **形态改进**：由三跑直接证据（0/0/0 + PIPESTATUS 采用）证明 ⇒ 可信。
- **失败通道本身**：由 ① 新增单测（exit 3 + stderr 非空 + 文件未改写）② 本地真探针（exit 3 / stdout 0 B / stderr 223 B）证明 ⇒ 只证明「装好了」，**不证明「在真跑里省了时间」**。

## 9. 新观察：模型仍在试错，只是换了个壳（R64 候选）

`r63-14` 里出现了 4 次 `render-facts.py` 调用（`r62-4` / `r62-18` / `r63-4` / `r63-18` 都只有 1 次），其中两次是**自造探针草稿**：写 `work/probe.md`（只放 4 个 token 的最小样张）→ `--out work/probe_out.md` 试渲染，第一次还漏了必需的 `--audit`（正确收到 `EXIT=2`）。同跑还有一次去读脚本源码（`make_chart.py` 的字段拼接逻辑）。

即：prompt 禁止的是「构造临时 ledger 试错探索语法」，模型改成「构造临时 **draft** 试错」——**禁令只改了试错的外形，没有消除试错的动机**。成本上它比二分便宜（2 次 vs 7 次），但配上该跑偏高的推理量，仍使 14 组停在 690 s。⇒ 下一轮若要继续打，应针对**「为什么模型不确定自己的输出是否会被校验器接受」**（即契约是否可静态自查），而不是继续加禁令。

## 10. 判定与下一步

**判定：KEEP（不劣化）。** 依据：① 形态类判据全达成且可归因；② 三组断言、产物、参数、抓取零退化；③ 三组调用/步数均在历史带内（18 组破下界）；④ 墙钟三组均在带内——**无一处可归因的劣化**；⑤ 规则文本一条未删。

**同时明确本轮没有交付提速**，并更正 R62 的因果归属：真正的可控项是**输出 token 量**，而非步数。

**下一步（按性价比）**：

1. **R64 候选 A（打动机，不打禁令）**：让「交付正文是否会被 `render-facts` 接受」可**静态自查**——例如把校验规则做成一条可跑的自检（`check_report --tokens` 已在做一部分），或在写正文前给模型**唯一一张 token 语法卡**（现已散落在 prompt / SKILL / toolbox 三处）。目标：降低那 2 次探针草稿 + 高推理量。
2. **R64 候选 B（仍在桌上）**：惰性段条件化（`## Subagent delegation` 5,067 B + `## Mixed or different-trial inputs` 1,035 B，预期 −4.3 KB）——但按 §7 的修正，**它最多作用于「每步固定开销」这一小项**，预期收益应下调。
3. **R61-3 / `B9`**：`tell-scan.py` 自打 `[tell-scan] exit=N`，runner 仅在扫描器 banner 同现时采纳 `SCAN_EXIT`。
4. **R61-4**：`same-trial-evolution.md` 三轮 0 真读。

## 11. 复算命令

```bash
cd /home/xupeipeioo1/apps/skill/clinical-result-comparison
# 三跑 + 历史带 + 相关性 + 形态探测（脚本在 /tmp，可重建）
python3 /tmp/r63/band.py     # 同输入历史带：调用/步/out/wall 的 min-max-中位
python3 /tmp/r63/corr.py     # r(wall, out)=+0.924 等相关系数 + render 调用/失败次数
python3 /tmp/r63/analyse.py  # 逐 run 工具分布、最贵步、阶段 token 归属
```
