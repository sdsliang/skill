# 全项目审查与修复记录（2026-09-18）

## 范围与结论

用户要求：「A10 给我个示例 id，别的你都改。另外 6-astra 你来，审查整个项目」。本轮覆盖 runner、评估器、本地工具、引用/实体校验及运行规则；**本地修复已验证，TS 资产未发布，没有新增线上 run**。不能把离线绿灯写成发布验收或 R21。

A10 示例：**`24_1_39054491_1`**（PMID 39054491，ECHO-307/KEYNOTE-672）。库内 `clinical_result.blinded=['开放']`，原文为 double-blind。全文中的揭盲后治疗与参考文献只是可能误抽上下文，不证明实际抽取根因。本轮不写数据库、不发送问题单。

## P1 发现

| 编号 | 风险与证据 | 修复位置 / 当前状态 |
|---|---|---|
| O33 | 不可信归档/回执路径可能越界或经过符号链接；轮询未见指针曾能得到无需回执的假绿，外 turn 指针也可能污染当前验证 | runner `~/.local/bin/toolsmith-publish`：路径防护、最终目标 turn 必需集、文件字节/哈希、重试与收集线程 join；[永久回归](../evals/runner-gate/test-runner.py) 与[累计补丁](../evals/runner-gate/runner-patches/review-hardening.patch)。本地已修，无新线上 run |
| O34 | 尝试数减拒参数不等于实际返回数；缺返回、空产物、错 chart 引用、缺部署支持文件清单可能假绿；宽泛错误归类可能隐藏故障 | 同一 runner 与[历史链闸门](../evals/runner-gate/verify-run-chain.py)：实际 tool-return 计数、目标 turn 隔离、未知归属/缺返回失败、产物/manifest 检查、分类正则收紧。本地已修 |
| O35 | 标签/剂量/时间与值错配、单点符号错误、伪全文头/文件名、外 turn 或嵌套伪造查询可能被旧评估器接受 | [check.py](../evals/fact-check/check.py)、[fulltext.py](../evals/fact-check/fulltext.py)、[history.py](../evals/fact-check/history.py)、[mutations.py](../evals/fact-check/mutations.py)。观察值与源身份绑定；无证据/歧义失败。已修并显式开 r2 新基线 |
| O38 | live 工具已经 `+esids -extra_esids`，旧 sys/skill 仍明文要求 `extra_esids`；`group_count` 被误教为臂数；L3 引用与取证边界分散冲突 | [当前 prompt](../system-prompts/multi-clinical-result-comparison-v0.15.md)、[input-contract.md](../skill/multi-clinical-result-comparison/references/input-contract.md)、[citation-and-ref.md](../skill/multi-clinical-result-comparison/references/citation-and-ref.md) 等 17 份运行文件已适配，schema 镜像已 live 重生成。**仅仓库已修，线上仍旧内容** |

**R19/R20 归因更正**：`args-refused` 说明参数被拒，不说明参数是模型发明。旧提示词明确要求 `extra_esids`，所以此前将首发拒参归因为模型从记录字段名臆造参数不成立/证据不足。以 live schema 为当前权威；记录字段 `clinical_result.extra_esid` 并未因此改名。台账 R19/R20、F6 与 O3 已就地补充更正，旧运行数值未改写。

## P2 发现

| 编号 | 风险与修复 | 状态 |
|---|---|---|
| O36 | [pack-dist.py](../tools/pack-dist.py) 的路径/符号链接与缺输入防护；[replay-run.py](../tools/replay-run.py) 的调用、场景识别、评分失败处理，防止把坏输入或旧分数当成功 | 本地已修，19 tests PASS，dist 已确定性重建 |
| O37 | [citation-renderer.mjs](../runtime/citation-renderer.mjs)、[validate-entity-refs.mjs](../evals/validate-entity-refs.mjs) 的引用值、URL、marker parity 与实体检查缺口 | 本地已修，21 Node tests PASS；它们不是生产渲染器，也不是 HTML sanitizer |
| O38 补充 | HTTP 500、无 PMCID 被过度解释为非 OA；全文取回与引用落点规则不统一 | 运行规则已纠正并以 input-contract 为 L3 权威；失败原因只能描述证据支持的事实，未做线上验证 |
| 文档 | 旧 branch、临时 gate 路径、旧部署哈希、冻结面与自动 revert 授权混在当前指引中 | README/AGENTS/PROJECT_STATE/台账/计划已补当前快照；历史分数保留，不全局替换 |

## 验证结果

以下为父任务已完成的实跑结果，本次文档整理不重跑网络请求、不修改证据文件。

| 检查 | 结果与范围 |
|---|---|
| 测试 | **97 PASS**：runner 30、scorer 27、tools 19、Node 21 |
| 负向/正向对照 | **63 controls PASS**，A 43/43、B 12/12 fail items 均可被对应变异触发；must-remain-clean 对照整轮通过 |
| runner 历史链 | **5 comparable / 36 histories / 31 skipped / 4 no-history**；无可比样本 exit 2，不报 PASS |
| 历史产物 r2 重判 | R17/R18 **43/43**，R20 **12/12**；R14 不是场景 A，只对其自身来源做两条定向全文核验，均通过 |
| 图表模板 | 3 个 clinical templates 对上游 **1.0.12** 的 `validateVisualizationFile` 全 PASS；隔离 Zod **4.6.5** 在 `~/.local/state/clinical-comparison-review-20260918/node_modules`，不代表 TS runtime 校验或浏览器渲染验收 |
| 本地 dist | **85,633 B / 19 entries**，SHA-256 `4d20d48faeeee012c347aa28eb5956e5238a3e95020999c6b9bd6084fba53b1e` |
| runner 可恢复性 | 先备份 v9，后备份 v10；累计补丁相对**原始 v9**，应用结果与安装 runner 字节一致；不得把累计补丁继续叠到 v10 |

**评估器基线必须分开读**：[2026-09-18-r2 修订记录](../evals/fact-check/EVALUATOR_REVISION.md) 明确冻结 A **43 fail + 1 warn**、B **12 fail + 1 warn**。旧 41→43 是新增/修正评估约束，不是同一把尺下质量增长；43 个项目也不是 43 个独立统计信号。R17/R18 用相同历史产物重判，不是新生成报告。历史 TSV 与旧 R 分数保留当时口径。

## 部署与授权

| 资产 | 本地待发布 | 当前线上（只读回读） |
|---|---|---|
| prompt | v0.15 文件，54,311 B，SHA 前缀 `2ff672b5aa9b` | 平台 **1.6**，53,347 B，`b9bfcec19538` |
| skill | 上述新 dist `4d20d48faeee` | 平台 **1.0.7**，skill_id `ad75ec2c44334f389a0394895a47b765`，旧 dist `404dbccf5058` |
| status | **OUT OF SYNC / exit 3，预期** | 19 个文件中 16 个与本地不同 |

live `deps` 已核对上游；完成适配后 `deps --accept` **仅接受本地依赖基线，不写 TS 资产**。本次未 `publish`，未创建新的线上运行记录。下一步须取得本批 **prompt + skill 原地发布**的具体确认，再回读至 in sync，跑 B 廉价闸门与 A；质量结论要求同一配置 A×3。不得沿用先前 B1 发布授权宣称本批也获授权。

## 残余风险

- runner 慢速持续返回数据时仍不是严格硬墙钟 deadline；不要把当前 timeout 称为完整总时限保证。
- 全文正文/身份/归档验证能拒绝空壳与错误来源，不能证明每个报告数字确实从该全文提取，也不能替代科学语义审查。
- C/D 仍缺可判分基线；委派、多分组、多图行为不能凭 A/B 绿灯宣称完整覆盖。
- 本地 chart schema 测试与引用渲染测试，不验证 TS 生产依赖、实际浏览器表现或 HTML 安全。
- 当前线上仍含已发现的旧规则，只有发布授权、回读与新 run 才能关闭线上验收。

Git 分支 `v0.15-remove-html`，本轮修复已提交并推送为 `ea4807c`；TS 发布仍待确认。未发现 Docker 配置，不构建或推送镜像。未修改 TS 平台源码，未把本地测试结论包装成平台修复。
