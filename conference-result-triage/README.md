# conference-result-triage

会议临床结果推荐榜：从一个会议的结果库里挑出**值得看的**三类研究，而不是把会议复述一遍。

- **早期机会** — Phase I/II，新机制 + 单臂疗效数字超出该适应症历史水位
- **重磅 II/III 期** — 随机对照、主要终点达成且有临床意义
- **失败的研究** — 主要终点未达 / 提前终止 / OS 反向

## 设计原则

**机器只筛，模型只读，谁都不自算数字。**

| 角色 | 职责 | 不做什么 |
|---|---|---|
| `scripts/triage.py`（零依赖） | esid 去重、排除非试验证据、分桶、附非权威机器信号、切复核批次 | 不打分、不排序推荐、不算疗效 |
| 模型 | 逐条读摘要，判 `keep/weak/drop`，写理由 + **逐字**证据摘录 | 不自算 ORR/HR/PFS，不猜缺失数字 |
| 人（定榜） | 压同质、标注 `data_type`、补药名/靶点、写"看点" | 不用 weak 凑数 |

三条硬规则：**n 不作入榜门槛**（只展示）；**真实世界/回顾性/汇总分析不进桶**（单独计 excluded）；**试验期别取 `evidence_source`**（不是疾病分期）。

## 跑在哪（v0.3）

**跑在 ToolSmith 平台里**：用户在会话里给一个会议名，agent 按 `SKILL.md` 的 7 步走完，交付
`/workspace/output/watchlist.json`（卡片清单）并 `present_artifact`。不是本地跑批脚本。

```
conference-result-triage/
├── SKILL.md                       # 平台内 7 步工作流 + 脚本 CLI + 闸门
├── references/                    # 数据契约、筛选手则、复核协议、坑清单
├── templates/watchlist-report.md
├── scripts/                       # 随包 ship 到 /workspace/skills/<name>/scripts/
├── system-prompts/…v0.3.md        # 部署到 TS 的系统提示词
├── tools/pack-dist.py             # 确定性打包 -> dist/*.zip
└── dist/                          # 包 + ESMO 2026 实跑样例
```

脚本（全部零第三方依赖）：

| 脚本 | 作用 |
|---|---|
| `pull_results.py` | 走 MCP 拉整场结果行（先 id 全量、再 esids 切片，防 6 MB 静默截断） |
| `mcp_client.py` | 最小 MCP streamable-HTTP 客户端 + 工具名自动发现 |
| `meeting_pull.py` | 拉会议摘要全本（补 `abstract_id` / 报告形式） |
| `triage.py` | 机械筛：去重 / 排除 / 分桶 / 机器信号 / 切批 / `--self-test` |
| `attach_abstract_ids.py` | 标题 join 补 `abstract_id`（ESMO 2026：551/551，LBA 编号 57/57） |
| `make_cards.py` | 按 plan 顺序渲染卡片 JSON（只渲染不排序） |
| `check_cards.py` | 交付前 fail-closed 校验，exit 3 = 有问题 |
| `history_for.py` | 同资产历次会议对照 |

## 快速开始（在平台工作区）

```bash
S=/workspace/skills/conference-result-triage/scripts
python3 $S/pull_results.py --conference "ESMO 2026" --out /workspace/work/rows.json
python3 $S/triage.py /workspace/work/rows.json --out-dir /workspace/work/pool --top 0
# … 逐批判读（见 references/review-protocol.md）→ 写 plan.json
python3 $S/make_cards.py --pool /workspace/work/pool_labeled.json \
    --plan /workspace/work/plan.json --out /workspace/output/watchlist.json --pretty
python3 $S/check_cards.py --cards /workspace/output/watchlist.json \
    --pool /workspace/work/pool_labeled.json   # 必须 exit 0
```

本地（研发机）等价自检：

```bash
python3 skill/conference-result-triage/scripts/triage.py --self-test
python3 evals/test_triage.py
python3 tools/pack-dist.py --check
```

