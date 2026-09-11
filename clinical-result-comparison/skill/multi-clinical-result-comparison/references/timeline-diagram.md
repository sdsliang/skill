# 证据链时间轴图（JSON 可视化）

## 适用范围

- 仅用于**同一试验的多篇披露**（合并后 ≥2 个真正不同的证据状态）的输入。
- 不用于跨试验或混合输入：不同试验没有共享时间线，不生成该图。
- 交付方式：**先把图表 skill 的 `templates/timeline.json` 拷成固定成品名** `/workspace/visualizations/evidence-timeline.json`（拿到 envelope 三键 `id`/`iframe_template`/`option`，**三键原样保留**；`iframe_template` 每次发布都变，禁止硬编码），**再把本 skill `templates/charts/evidence-timeline.json`（`option` 内层，不是可交付成品）的内容整体放进 `option`**，只改数据与文案字段（`title`/`subTitle`/`dataSource`/`describe`、`data[]`、`legend`/`weightLegend`），JSON 无注释、无渲染代码可改。正文“证据链总览与时间线”一节中在时间线表格上方用 `::visualization[标题]{path="/workspace/visualizations/evidence-timeline.json"}` 绝对路径独占一行引用（写入 `/workspace/visualizations/` 后再引用；禁止目录穿越/反斜杠/前缀外路径，文件名 ASCII）。**不再输出 Mermaid 代码块、不再产出 HTML 图表。** 接入方不支持可视化文件时，正文保留时间线表格 + 文字结论，并提供图的下载链接。

## 图要回答的问题

一张图同时展示四件事：

1. **时间顺序**：证据状态按来源支持的时序从左到右排列。排序优先级为 数据截止 → 明确随访 → 分析里程碑 → 披露日期；绝不使用输入顺序、数据库顺序或运行时间戳。时间轴 `data[]` 数组顺序即时间顺序（前端不重排）。
2. **每个状态新增了什么**：节点 `label`/`content`/`description` 写明本状态新增的终点、估计、亚组、安全性或方法内容。
3. **相邻状态的关系**：用节点 `description` 或正文文字写明"更新 / 新增终点 / 确认 / 补充 / 取代 / 冲突 / 不确定"。
4. **证据链如何成熟**：`weight`（节点圆点大小）表示证据成熟度，配合正文说明整体判断是加强、基本不变、受到限定、削弱还是无法确定，并说明由哪些证据状态引起。

## 构建规则

1. **一个节点（timeline `data[]` 一条）= 一个证据状态**，不是一篇披露。合并为同一状态的来源共享一个节点：`label` 写状态名 + 分析阶段/披露形式（如"pCR 主要分析 · 摘要/主刊"），`description` 中并列列出该状态支持来源的引用标记（如 `{{ref_1}}{{ref_3}}`）；披露数量多不代表独立验证。
2. **节点内容字段**（camelCase，与上游 chart-visualization-json 协议一致）：
   - `label`：证据状态名 + 分析阶段/披露形式（string，必填）；
   - `time`：本状态来源支持的时间锚点文案（数据截止/随访/披露日期），缺失写「时间未明」，不得猜测或推算日期（string，必填）；
   - `group`：分类键，对应 `legend[].key`（如 milestone/disclosure/update）；
   - `weight`：节点权重 number ≥ 0，驱动圆点大小（越大越成熟）；里程碑/无成熟度贡献为 0；
   - `content`：本状态最关键数值/比较 + 关键新增内容，支持 `\n` 多行（string，可选）；
   - `description`：补充说明（悬停提示），可放本状态关键新增内容 + 引用标记（string，可选）。
3. **时间轴**：节点按时间先后在 `data[]` 内排好（数据截止 → 明确随访 → 分析里程碑 → 披露日期），前端不重排。某状态没有来源支持的时间时，`time` 写「时间未明」。`legend[].shape`：circle（实心圆）=披露/更新、empty-circle（空心圆）=里程碑。
4. **边关系与成熟度**：相邻状态的关系（更新/新增终点/确认/补充/取代/冲突/不确定）写在图下方正文或节点 `description` 中，格式为"关系 + 成熟度方向"，例如 `新增终点 + 更长随访，疗效判断加强（OS 仍属中期）`。只有原文支持才标注关系；无法确定的写"不确定"。
5. **成熟度边界**：只写来源支持的成熟度判断。首次/中期分析必须保留"首次/中期"字样，不得写成最终分析。
6. **标签安全**：`content`/`description` 数值只使用来源明确给出的数字。`value` 语义在本图不使用（timeline 用 `content` 承载数值文本）；不得插值、合并、排名或按披露数量制造时间点。
7. **回退规则**：
   - 合并后只有 1 个证据状态（其余都是纯重复），或任意两个状态的先后都无法由来源确定时，**不生成时间轴图**，仅保留时间线表格并明确说明顺序不确定。
   - 时间轴图是描述性示意图，不能替代表格中的精确数值；时间线表格必须始终保留。

## 数据填写示例（TRAIN-2：5 篇披露合并为 3 个证据状态）

来源 `{{ref_1}}` 与 `{{ref_3}}` 共享同一 pCR 主分析（同一 418 例可评估与数值），合并为一个 pCR 状态；来源 `{{ref_2}}` 与 `{{ref_4}}` 共享同一 3 年随访分析（同一 438 例、48.8 个月随访与数值），合并为一个 3 年随访状态。图中不产生五个独立节点，也不把重复披露解释为独立验证。

```json
{
  "type": "timeline",
  "title": "TRAIN-2（NCT01996267）证据链时间轴",
  "subTitle": "同一试验证据披露与结果演进 · 节点=合并后的证据状态",
  "dataSource": "数据来源：所选临床结果的 params 返回字段（论文题名 / 发布时间）",
  "describe": "节点=证据状态，weight=证据成熟度；证据边界：仅 params 返回字段",
  "legend": [
    { "key": "milestone",  "label": "研究里程碑", "shape": "empty-circle" },
    { "key": "disclosure", "label": "证据披露",   "shape": "circle" },
    { "key": "update",     "label": "数据更新",   "shape": "circle" }
  ],
  "weightLegend": { "show": true, "label": "证据成熟度" },
  "data": [
    { "time": "2013-12", "label": "研究启动（里程碑）", "group": "milestone", "weight": 0, "content": "2013-12-09 起入组、2016-01-14 完成；438 例 1:1 随机", "description": "" },
    { "time": "2016-08", "label": "早期毒性分析", "group": "disclosure", "weight": 1, "content": "FN 9% vs 0%", "description": "110 例早期子集毒性谱（FEC-T vs PTC）{{ref_5}}" },
    { "time": "2017-03/2018-12 · 中位随访 19 个月", "label": "pCR 主要分析 · 摘要/主刊", "group": "disclosure", "weight": 2, "content": "pCR 68% vs 67%", "description": "418 例可评估；摘要 p=0.75、主刊 p=0.95，数值一致、统计量有出入{{ref_1}}{{ref_3}}" },
    { "time": "2020-05/2021-05 · 中位随访 48.8 个月", "label": "3 年 EFS/OS 随访 · 摘要/主刊", "group": "update", "weight": 3, "content": "EFS HR 0.90", "description": "3 年 EFS 92.7% vs 93.6%、OS 97.7% vs 98.2%；蒽环组 2 例急性白血病{{ref_2}}{{ref_4}}" }
  ]
}
```

按此填写后保存为**固定文件名** `evidence-timeline.json`（写入 `/workspace/visualizations/`；**纯 JSON，无 HTML 包裹**，先跑 `node /workspace/skills/chart-visualization-json/scripts/validate-cli.js <成品>` 通过 PASS 再引用），正文用 `::visualization[标题]{path="/workspace/visualizations/evidence-timeline.json"}` 绝对路径引用，并始终保留精确数值的时间线表格。
