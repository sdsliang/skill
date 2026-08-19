# PROJECT_STATE — 会议临床解读 (Conference Clinical Interpretation)

更新于：2026-08-19

## 状态

- **阶段**：v0.1 完成（Skill 资产 + 数据管线 + 首个示例运行 + dist 打包 + 契约校验）
- **仓库**：`git@github.com:sdsliang/skill.git`（子目录 `apps/skill/conference-clinical-interpretation/`）
- **Git 分支**：main

## 目标

- 对某医学会议（默认 ASCO 2026）在 `np_clinical` 索引中的全部临床结果做统计解读，产出两类交付物：①带图表的 Markdown 报告；②推荐关注清单（watchlist.csv）。
- 复用 Tool Smith 可视化协议（`/workspace/visualizations/` + `::visualization[...]` 引用 + Skill-defined data file 免 read_me + 模型不生成图表 options）。
- 核心立场：热度 ≠ 记录数。

## 已实现

### Skill 资产（`skill/conference-clinical-interpretation/`）
- `SKILL.md`：渐进披露主文件（frontmatter name/description），工作流 8 步，触发条件，输出契约。
- `references/`：
  - `data-contract.md`：快照/统计文件 JSON 结构、字段口径表、排除规则、可复现命令。
  - `statistics.md`：统计维度 + 热度≠记录数原则 + 代表性证据选择 + 主题聚类。
  - `chart-contract.md`：图表类型枚举白名单（10 种）、维度白名单、数据文件命名、`::visualization[...]` 引用格式、颜色 token 契约、禁止事项。
  - `report-structure.md`：10 章报告结构。
  - `watchlist.md`：评分维度（阶段25/评价25/样本20/终点15/新颖15）+ CSV 字段 + 生成步骤。
- `templates/`：`conference-report.md`（10 章模板）、`watchlist.csv`（表头）。

### System prompt
- `system-prompts/conference-clinical-interpretation-v0.1.md`：开场声明、Required workflow、可视化契约、边界约束。

### 数据管线（`evals/`）
- `fetch-conference-np-clinical.mjs`：从 `np_clinical` 拉取 `base.journal` 精确匹配会议名的全部记录（分页 + search_after），排除 deleted/is_delete=是，输出快照 JSON。
- `build-conference-stats.mjs`：确定性统计生成器 → `*-stats.json`（overview/distributions/evidence_scatter/entity_network）。
  - 阶段双维度：`trial_phase`（研发阶段）+ `disease_stage`（疾病阶段，归一化）。
  - 终点识别：10 类正则模式。
- fixtures：`asco-2026-np-clinical.json`（136MB，本地留档，不入 Git）、`asco-2026-stats.json`（1.7MB）。

### 数据验证（ASCO 2026）
- 匹配 1639 条，分析合格 1639 条。
- 评价：积极 1201 / 不佳 153 / 终止 12。
- 阶段：II期 445 / I期 227 / III期 170 / I/II期 147。
- 疾病阶段：晚期/转移 799 / III期 125 / II期 75 / IV期 61 / 早期 61。
- 唯一药物 750、适应症 338、标志物 185；Top 药物含化疗辅药（奥沙利铂 109、氟尿嘧啶 84、卡铂 71）→ 印证"热度≠记录数"。
- 实体网络 3750 条边。

## 待办

- [x] 跑示例运行（iteration-01）：生成 chart-data.json + watchlist.csv + 报告 md（16 图 + 15 条 watchlist）
- [x] 写 `test/` 契约校验脚本（validate-contract.mjs：枚举白名单/watchlist 字段/::visualization 引用/证据 ID/SKILL↔sys prompt↔dist 同步）— 全部通过
- [x] 打包 `dist/conference-clinical-interpretation-v0.1.zip`（8 文件，字节级一致）
- [x] PROJECT_INDEX 注册新项目

## Git/Docker 状态

- Git：新项目首次 commit/push 到 origin（`git@github.com:sdsliang/skill.git`），分支 main。
  - 原始快照 136MB 已通过 `.gitignore`（`evals/fixtures/*-np-clinical.json`）排除，不入库。
- Docker：无 Docker 配置（纯数据/文档技能，无需镜像）。

## 同步契约

- SKILL 资产变更 ⇒ 同步 `system-prompts/conference-clinical-interpretation-v0.1.md` + 重建 `dist/` zip（`node evals/build-dist.mjs`）。
- 图表类型枚举变更 ⇒ 更新 `chart-contract.md` + system prompt + 前端模板。
- 数据口径变更 ⇒ 更新 `data-contract.md` + `build-conference-stats.mjs`。

## 关键决策记录

- **数据源 = `np_clinical`**（1639 条 vs np_result 1079），字段更丰富（含 source_full_text、trial_details.arms、opt_dose_effect）。
- **可视化 = Workspace Visualization 文件协议**（非 show_widget）：多图、脚本生成、需正文穿插、需复用留档。
- **模型不生成图表 options**：只输出枚举类型 + 白名单维度 + 数据，前端映射到维护好的模板。
- **原始快照不进模型上下文**：消费 `*-stats.json`。
- **推荐关注清单独立 CSV**：可下载复用，报告内以表格呈现。
- 与多临床结果对比 skill 明确分工：本 skill 统计解读，彼 skill 比较分析。
