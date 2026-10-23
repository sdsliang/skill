# PROJECT_STATE — conference-result-triage

## 现状（2026-10-23）

**状态**：v0.1 本地完成，未发布 ToolSmith（用户明确要求"先不碰 TS 发布"）。

## 是什么

会议临床结果推荐榜 skill：输入一个会议标识（`meeting_tags`，如 `ESMO 2026`），输出三桶榜单
（早期机会 / 重磅 II/III / 失败）+ 排除档 + 待人工核实清单。

与两个既有 skill 的边界：

| skill | 分析对象 | 输出 |
|---|---|---|
| `conference-clinical-interpretation` | 一个会议的**统计概览** | 会议整体解读报告 + 图表 |
| `multi-clinical-result-comparison` | 2 个以上**已选定**的结果 | 药物间疗效/安全性对比 |
| **本 skill** | 一个会议的**全部候选** | 值得看的 30 条 + 为什么 |

## 关键设计决策（含理由，勿回退）

1. **机器评分被显式废弃**。实测规则打分产生假精度：安全性行会压过疗效行（`Grade≥3 TEAE 44.6%` 被当疗效）、`PR = 3 subjects` 被读成 3% 缓解率、约一半 `study_results` 没有 p/HR。现 `triage.py` 只做机械操作 + 附**非权威**提示。
2. **n 不作入榜门槛**（用户 2026-10-23 决定）。只做展示与并列次级排序。
3. **真实世界/回顾性/前瞻性非注册研究不进桶**（用户决定）。单独计入 `excluded`，在交付物里明示条数。
4. **失败桶由 `evaluation ∈ {不佳, 终止}` 驱动**，p/HR 只作佐证；复核阶段按证据强度可把 III 期但 OS 未达的项从 pivotal 改判到 failed。
5. **试验期别取 `evidence_source`**，不是 `clinical_stage_new`（后者是疾病分期）。
6. **`data_type` 四分类**（首次 / 更新 / 亚组 / 未判定）为强制列。理由：会议摘要大量是长期随访与 post-hoc 分析，不标会把 7 年 OS 更新写成新药突破。规则命中率有限（成稿分布 90/77/53/247），定榜条目必须人工确认。
7. **批次上限 25 条/片**。硬约束来自工具单文件读取上限（~50 KB）；早期 6 路切分就是因为单文件 50 KB 行被 read 拒绝而全部失败。
8. **索引用显式顺序 `i`**，不用 esid 下标。此前一次 6 路并行复核因为 esid 与顺序错位，合并结果不可用。

## 已完成

- `scripts/triage.py`（620+ 行，零依赖）：去重 / 排除 / 三桶 / `data_type` / 机器信号 / 批次输出 / `--self-test` / `--require-detail` 两段式。
- `references/` 四份（data-contract / screening-rules / review-protocol / pitfalls 11 条）。
- `templates/watchlist-report.md`、`system-prompts/conference-result-triage-v0.1.md`、`SKILL.md`、`README.md`。
- `evals/test_triage.py` + `evals/fixtures/mini_rows.json`（4 条固定样例，覆盖安全性行不得成为疗效信号、RWE 必须排除、阴性 evaluation 进 failed、逗号数字解析）。
- **ESMO 2026 实跑**：945 篇 → 988 esid → 467 候选 → 467 条逐条判定 → 206 keep → 定榜 30。产物在 `dist/`。

## 验证记录

| 项 | 结果 |
|---|---|
| `python3 scripts/triage.py --self-test` | OK |
| `python3 evals/test_triage.py` | OK（4 组断言） |
| 全量重跑（467 条）与旧产物对比 | 0 条信号丢失 / 0 条意外获得（`SAFETY_HINTS` 扩展后） |
| lite 全量输入（1338 行） | 988 esid / 排除 494 / 候选 467，与漏斗表逐项一致 |
| 批次切分 | 467 条 → 19 批（batch-size 默认 25） |
| 复核覆盖 | 467/467，`i` 无缺口，evidence 逐字命中 400/467（86%） |
| 未命中 evidence | 67 条，未进入定榜；原因记录在 review-protocol §5 |

## 待办

- [ ] evidence 逐字未命中的 67 条：对 shard 原文重新取句后再入库（当前不影响榜）。
- [ ] `clean_label()` 残留噪声：`...; percentage`、`Patients who completed N cycles` 两类。
- [ ] `data_type` 规则误判（`final analysis` → 显示为「首次公布」）需要更多样本再调，当前靠人工兜底。
- [ ] ToolSmith 发布（用户暂缓）：`system-prompts/conference-result-triage-v0.1.md` + `SKILL.md` 已备好；发布前须在 `~/.config/toolsmith/projects.json` 注册 family 并标 `owned: true`。

## Git

仓库根 `/home/xupeipeioo1/apps/skill`（与其他 skill 共享）。首次提交包含整个 `conference-result-triage/` 目录。
