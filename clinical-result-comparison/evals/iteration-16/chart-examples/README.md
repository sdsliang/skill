# chart-examples · 图表示例

按 `references/chart-templates.md` 契约生成的 HTML fragment 成品 + 本地渲染 PNG（品牌 fallback 色预览，接入 Tool Smith 后由 `--viz-*` token 覆盖）。

## 按临床问题分组绘图（跨试验/混合报告，v0.8 契约）

跨试验/混合输入按临床问题分组后，**每组各出一张 `endpoint-bar.html` 柱状图**（各组独立 CHART 文件）。本组示例来自 NSCLC 多试验解读：10 项独立随机试验分三组，每组装一张图，图内并列该组各试验的**试验组结果值**；研究内对照数值与证据边界放悬停 note；标题/副标题注明「跨试验并列展示≠头对头比较」。

| 文件 | 组 | 指标 | 柱（试验组方案） |
|---|---|---|---|
| `nsc-group1-orr.html/.png` | 组1 一线化疗 | ORR | CATAPULT I 27.5% / SWOG 25% / GP 41% / Spanish CG 42% |
| `nsc-group2-orr.html/.png` | 组2 二线治疗 | ORR | TAX 320 多西他赛75 6.7% / 培美曲塞 9.1% / 厄洛替尼 8.9%（DISTAL 未报告跳过） |
| `nsc-group3-os.html/.png` | 组3 辅助化疗 | 5年 OS | IALT 44.5% / 长春瑞滨+顺铂 69% |

数据来自各试验 source_full_text；三张图均为模板复制、只改 `CHART` 数据、未改渲染代码。

## 其他示例

- `harmoni6-evidence-timeline.html/.png`：同试验证据链时间轴（HARMONi-6）
- `harmoni6-pfs-bar.html/.png`：PFS 柱状图（HARMONi-6）
- `mazdutide-weight-line.html/.png`：体重随时间折线（单点/多点模式）
- `orr-bar.html/.png`：多臂 ORR 柱状图
