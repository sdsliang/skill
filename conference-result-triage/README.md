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

## 快速开始

```bash
# 自检
python3 scripts/triage.py --self-test
python3 evals/test_triage.py

# 机械筛（输入：MCP 拉取的行数组）
python3 scripts/triage.py --input rows.json --out-dir work --top 0
# → work/pool.json / pool.md / review.jsonl
```

复核与定榜流程见 `references/review-protocol.md`，报告模板见 `templates/watchlist-report.md`。

## 目录

```
conference-result-triage/
├── SKILL.md                         入口（触发条件、流程、反模式）
├── references/
│   ├── data-contract.md             MCP 调用、15 个字段、study_results 形状
│   ├── screening-rules.md           排除/去重/分桶/data_type 规范
│   ├── review-protocol.md           批次设计、verdict 标准、合并校验、定榜
│   └── pitfalls.md                  11 条实测数据坑
├── scripts/triage.py                机械筛（零依赖，Py3.9+）
├── templates/watchlist-report.md    三桶报告模板
├── evals/
│   ├── test_triage.py               fixture 回归
│   └── fixtures/mini_rows.json      4 条最小样例（early/pivotal/failed/RWE）
├── system-prompts/conference-result-triage-v0.1.md
└── dist/                            实跑样例（ESMO 2026）
    ├── ESMO2026-watchlist.md        三桶榜 30 条
    ├── ESMO2026-watchlist.csv       机器可读 30 条
    └── esmo2026-judgements.csv      467 条全量逐条判定
```

## 实跑基线（ESMO 2026）

945 篇会议文献 → 1338 原始行 → 988 esid → 排除 494 非试验 → 467 候选（早期 180 / 重磅 238 / 失败 49）→ 逐条复核 206 keep（181 weak / 80 drop）→ 定榜 30。

耗时口径：全量拉取 ~1 s；复核 467 条分 19 片、6 个子任务并行。
