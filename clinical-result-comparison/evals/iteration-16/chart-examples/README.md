# chart-examples · 图表示例（HTML 时代留存预览）

> **v0.15 起本目录只保留 `.png` 预览，所有 `.html` 成品已删除。** 这些 PNG 是 v0.8–v0.11「HTML fragment + `::visualization`」时代的渲染截图，仅作历史对照。
> 当前 Skill 的图表产物是**纯 JSON**（复用上游 `chart-visualization-json` skill 的协议与 CLI 校验，见 `references/chart-templates.md`），不再存在任何 HTML 形态；`templates/charts/` 下只有 `evidence-timeline.json` / `endpoint-bar.json` / `endpoint-line.json` 三个 JSON 骨架。

## 跨试验/混合报告的分组建图（v0.8 契约，历史）

跨试验/混合输入按临床问题分组后，每组各出一张柱状图（当时为 `endpoint-bar.html`，现为 `endpoint-bar-<n>.json`）。本组示例来自 NSCLC 多试验解读：10 项独立随机试验分三组，每组装一张图，图内并列该组各试验的**试验组结果值**；研究内对照数值与证据边界放悬停 note；标题/副标题注明「跨试验并列展示≠头对头比较」。

| 文件 | 组 | 指标 | 柱（试验组方案） |
|---|---|---|---|
| `nsc-group1-orr.png` | 组1 一线化疗 | ORR | CATAPULT I 27.5% / SWOG 25% / GP 41% / Spanish CG 42% |
| `nsc-group2-orr.png` | 组2 二线治疗 | ORR | TAX 320 多西他赛75 6.7% / 培美曲塞 9.1% / 厄洛替尼 8.9%（DISTAL 未报告跳过） |
| `nsc-group3-os.png` | 组3 辅助化疗 | 5年 OS | IALT 44.5% / 长春瑞滨+顺铂 69% |

## 其他示例

- `harmoni6-evidence-timeline.png`：同试验证据链时间轴（HARMONi-6）
- `harmoni6-pfs-bar.png`：PFS 柱状图（HARMONi-6）
- `mazdutide-weight-line.png`：体重随时间折线（单点/多点模式）
- `orr-bar.png`：多臂 ORR 柱状图

以上图像均来自模板复制、只改数据、未改渲染代码的产物；对应 HTML 源文件可在 git 历史 `e4f3bb7` 的 `docs/legacy-html-charts/` 与 `evals/iteration-16/chart-examples/` 中找回。
