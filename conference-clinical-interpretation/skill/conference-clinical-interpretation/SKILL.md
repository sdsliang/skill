---
name: conference-clinical-interpretation
description: >-
  会议临床解读：对某个医学会议（默认 ASCO 2026）在 np_clinical 索引中的全部临床试验结果做统计分析，
  产出 (1) 带图表的 Markdown 解读报告与 (2) 推荐关注清单（watchlist.csv）。面向外部学术会议数据，
  统计视角优先（热度≠记录数），模型只输出受约束的结构化分析计划，图表由前端按协议渲染。
---

# 会议临床解读 (Conference Clinical Interpretation)

对给定医学会议在 `np_clinical` 索引中的全部临床试验结果记录进行**统计分析式解读**，产出两类交付物：
1. **带图表的 Markdown 解读报告** —— 会议全景、热点主题、代表性证据、趋势与缺失。
2. **推荐关注清单** —— 按临床价值（而非记录数）筛选的高优先级试验列表，独立成 `watchlist.csv` 并在报告中以表格呈现。

本 skill 是**统计解读面板**（data-analysis oriented），**不是**单药/多药孰优孰劣的比较分析（那属于多临床结果对比 skill）。核心立场：**热度≠记录数**，数量最多的记录不等于临床价值最高。

## 触发条件

当用户要求解读某医学会议的全部临床结果、生成会议统计面板/解读报告/推荐关注清单，且数据来源为 `np_clinical` 索引（`base.journal` 精确匹配会议名）时使用。典型表述：解读 ASCO 2026、生成会议热点报告、某会议的推荐关注清单等。

## 输入

- **数据**：由数据适配器拉取的会议快照 + 确定性统计文件（见 `references/data-contract.md`）。
  - 快照 `*.np-clinical.json`：`base.journal` 精确匹配会议名（`text` 或 `meta.text`），排除 `deleted=true` / `is_delete=是`。
  - 统计文件 `*-stats.json`：`distributions`、`evidence_scatter`、`entity_network`、`overview`。
- **会议名**：通过环境变量 `JOURNAL` 指定，默认 `ASCO 2026`。
- 若原始数据不在输入中，先运行拉取适配器（见 `references/data-contract.md` 的复现命令）。

## 工作流

1. **读取数据协议**（`references/data-contract.md`）——确认输入快照与统计文件结构、字段口径、排除规则。
2. **读取统计方法**（`references/statistics.md`）——明确"热度≠记录数"的统计维度、代表性与归一化规则。
3. **读取图表协议**（`references/chart-contract.md`）——确认允许的图表类型枚举、维度白名单、数据文件名与 `::visualization[...]` 引用格式。
4. **读取报告结构**（`references/report-structure.md`）与**推荐清单规则**（`references/watchlist.md`）。
5. **生成统计产物**：
   - 确定性统计（若未提供）→ 写入 `/workspace/visualizations/conference-stats.json`。
   - 前端图表数据文件 `chart-data.json` → 按 `chart-contract.md` 的枚举类型与维度白名单生成（Skill-defined data file，**不需要**调用 `read_me`）。
   - 复杂/由脚本生成的图表 HTML/SVG → 写入 `/workspace/visualizations/`，正文**独占一行**输出 `::visualization[标题]{path="/workspace/visualizations/name.ext"}`。
6. **撰写报告**（Markdown）→ 严格遵循 `templates/conference-report.md`。
7. **生成推荐关注清单** → 严格遵循 `references/watchlist.md` 与 `templates/watchlist.csv`，写入 `/workspace/visualizations/watchlist.csv`，报告中以表格呈现。
8. **证据引用**：报告中每个关键论断必须引用证据 ID（`evidence_scatter[].id`）；不引用原始全文，只引用统计口径与代表性证据条目。
9. **药物机制增强（可选）**：为代表性药物/重点清单中的药物补充靶点、MOA、modality、阶段等画像（来源：drug_earth 药物字典，DrugBank 同源），写入 `drug-profiles.json` 并随报告/清单/可视化展示；规则见 `references/drug-enrichment.md`。

## 输出与可视化交付（Visualizer 协作契约）

- 本 skill **定义数据协议**（`.json`/`.csv`），因此写入 `/workspace/visualizations/` 的统计/图表数据文件**不需要**调用 `read_me`。
- 只有当你同时创建内置 SVG/HTML/chart/map/interactive/art 视觉时，才在创建前调用 `read_me(modules=[...])`。
- 模型**不生成 ECharts/Chart.js 的 options 代码**；只生成**受约束的结构化分析计划**（图表类型枚举 + 白名单维度），前端按协议映射到维护好的图表模板。
- 图表与报告文件必须写入 `/workspace/visualizations/` 之后，才能在正文用 `::visualization[标题]{path=...}` 引用；**永远不要直接引用 `/workspace/skills/<name>/` 下的资源**。
- 颜色：若你直接写 SVG/HTML，只使用 renderer 注入的 `--viz-*` 语义 token（`--viz-background`/`--viz-surface`/`--viz-text`/`--viz-border`/`--viz-info`/`--viz-success`/`--viz-warning`/`--viz-danger`/`--viz-series-1..5`）；Canvas/Chart.js 用 `resolveColorToken(name)` 获取规范化 sRGB 色值。**不要在 prompt/文件中维护固定色板**。
- Mermaid 图只走普通 Markdown fenced block，不进 visualizer widget/artifact。

## 限制与边界

- 热度（记录数）≠ 临床重要性；报告必须明确这一区别，不能把"记录最多"当作"价值最高"。
- 模型只输出结构化分析计划与数据协议文件，不输出图表库 options；图表映射是前端的职责。
- 每个论断都要可溯源到证据 ID 或统计口径；不臆造数值。
- 报告使用 Markdown；图表用 `::visualization[...]` 引用，不嵌入 base64 图片。
- 本 skill 不做头对头疗效比较，不做跨试验等效性推断。

## 支持文件

- `references/data-contract.md` —— 输入快照/统计文件结构、字段口径、复现命令。
- `references/statistics.md` —— 统计维度、"热度≠记录数"原则、代表性证据选择。
- `references/chart-contract.md` —— 图表类型枚举、维度白名单、数据文件命名与引用格式。
- `references/report-structure.md` —— 报告章节结构。
- `references/watchlist.md` —— 推荐关注清单评分与生成规则。
- `references/drug-enrichment.md` —— 药物画像（靶点/MOA/modality）增强规则与数据来源。
- `templates/conference-report.md` —— 报告模板。
- `templates/watchlist.csv` —— 推荐关注清单 CSV 模板。
