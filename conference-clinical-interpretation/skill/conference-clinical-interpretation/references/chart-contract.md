# 图表协议 (Chart Contract)

本文定义「会议临床解读」的可视化契约：图表类型枚举、维度白名单、数据文件命名与 `::visualization[...]` 引用格式。**模型不生成 ECharts/Chart.js 的 options 代码**，只生成受约束的结构化分析计划与数据文件；前端把枚举类型 + 白名单维度映射到维护好的图表模板。

## 1. 交付方式：Workspace Visualization 文件协议

按 Tool Smith `agent-implementation.md` 的 Skill-Visualizer 协作规则：

- 本 skill **定义数据协议**，因此写入 `/workspace/visualizations/` 的统计/图表数据文件（`.json`/`.csv`/`.tsv`）是 **Skill-defined data files**，**不需要**调用 `read_me`。
- 只有当你同时创建内置 SVG/HTML/chart/map/interactive/art 视觉时，才在创建前调用 `read_me(modules=["chart", ...])`。
- 完成文件写入后，在正文**独占一行**输出引用：
  `::visualization[标题（用户语言）]{path="/workspace/visualizations/<ascii文件名>.ext"}`
- **先写文件，后引用**；绝不引用不存在的文件，也**绝不直接引用 `/workspace/skills/<name>/` 下的资源**。
- 文件名使用 ASCII；扩展名限 `.svg`/`.html`/`.png`/`.jpg`/`.jpeg`/`.webp`（图表文件）或 `.json`/`.csv`/`.tsv`（数据文件）。

## 2. 图表类型枚举（白名单）

模型只能从以下枚举中选择图表类型，每个类型绑定固定的白名单维度：

| 枚举类型 | 含义 | 绑定维度（白名单） | 建议 |
|---|---|---|---|
| `bar_distribution` | 分类分布条形图 | evaluation / trial_phase / disease_stage / therapy_line / source | 纵向条形，按 count 降序 |
| `horizontal_bar_topN` | Top-N 横向条形图 | indication / drug / biomarker / endpoint（取 Top N，N≤15） | 用于覆盖广度展示 |
| `pie_donut_share` | 环形占比图 | evaluation / trial_phase / disease_stage | 整体结构占比 |
| `stacked_bar_phase_eval` | 阶段×评价堆叠条形图 | trial_phase × evaluation | 成熟度 vs 积极信号 |
| `stacked_bar_indication_eval` | 适应症×评价堆叠条形图 | indication(TopN) × evaluation | 领域积极/不佳构成 |
| `scatter_evidence` | 代表性证据散点图 | x=sample_size, y=评价(积极/不佳/终止 映射), 气泡=? | 证据价值分布 |
| `line_release_cumulative` | 发布日期累计曲线 | release_date 累计记录数 | 会议日程热度趋势 |
| `network_entity` | 实体关系网络图 | drug ↔ indication / biomarker（entity_network） | 药物-适应症/标志物网络 |
| `kpi_summary` | 关键指标卡组 | overview（matched/eligible/unique_drugs/unique_indications...） | 顶部总览 |
| `table_watchlist` | 推荐清单表 | watchlist 字段（见 watchlist.md） | 报告中表格呈现 |

> 禁止新增枚举类型；如需新类型，先更新本文与前端模板，再使用。

## 3. 数据文件命名与结构

写入 `/workspace/visualizations/` 的数据文件命名约定：

- `conference-stats.json` —— 确定性统计（同 `*-stats.json`，供前端通用 JSON 预览）。
- `chart-data.json` —— 模型从统计文件裁剪出的**仅含白名单图表所需数据**的结构化数组，例如：

```jsonc
{
  "schema_version": "1.0.0",
  "conference": "ASCO 2026",
  "charts": [
    {
      "type": "bar_distribution",
      "title": "会议记录按评价分布",
      "dimension": "evaluation",
      "data": [ { "label": "积极", "count": 1201 }, { "label": "不佳", "count": 153 } ]
    },
    {
      "type": "horizontal_bar_topN",
      "title": "Top 15 适应症曝光",
      "dimension": "indication",
      "data": [ { "label": "实体瘤", "count": 162 }, ... ]
    },
    {
      "type": "stacked_bar_phase_eval",
      "title": "研发阶段 × 评价",
      "dimension": ["trial_phase", "evaluation"],
      "data": [ { "phase": "II期", "evaluation": "积极", "count": 1 }, ... ]
    },
    {
      "type": "network_entity",
      "title": "药物–适应症关系网络",
      "dimension": ["drug", "indication"],
      "data": [ { "source": "帕博利珠单抗", "target": "非小细胞肺癌", "weight": 12 }, ... ]
    },
    {
      "type": "scatter_evidence",
      "title": "代表性证据（样本量 × 评价）",
      "dimension": ["sample_size", "evaluation"],
      "data": [ { "id": "24_...", "sample_size": 61, "evaluation": "积极", "title": "..." }, ... ]
    }
  ]
}
```

- `watchlist.csv` —— 推荐关注清单（见 watchlist.md），可下载复用。

## 4. 颜色契约

- 若你直接写 SVG/HTML：只使用 renderer 注入的语义 token：
  `--viz-background` `--viz-surface` `--viz-text` `--viz-text-muted` `--viz-border` `--viz-info` `--viz-success` `--viz-warning` `--viz-danger` `--viz-series-1..5`。
  例如 `fill="var(--viz-series-1)"` 或 `color: var(--viz-text)`；可通过 `color-mix(in oklch, var(--viz-info) 14%, var(--viz-surface))` 派生浅色。
- Canvas / Chart.js / D3 需要具体色值：调用宿主提供的 `resolveColorToken('--viz-series-1')` 获取规范化 sRGB 色值；**不要**把 CSS token 表达式直接传给解析颜色的 JS API。
- **不要在 prompt/文件中维护固定色板**；颜色一律走 token。

## 5. 禁止事项

- 不生成 ECharts/Chart.js options 代码；只生成 `chart-data.json`（枚举类型 + 白名单维度 + 数据）。
- 不内嵌 base64 图片到 Markdown 报告。
- 不引用 `/workspace/skills/` 下的文件。
- 不使用枚举之外的图表类型或维度。
- Mermaid 只走普通 Markdown fenced block，不进 visualizer。
