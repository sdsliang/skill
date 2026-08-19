# 会议临床解读 (Conference Clinical Interpretation)

Tool Smith 技能：对某个医学会议（默认 ASCO 2026）在 `np_clinical` 索引中的全部临床试验结果做**统计分析式解读**，产出两类交付物：

1. **带图表的 Markdown 解读报告** —— 会议全景、热点主题洞察、代表性证据、负面/终止信号、推荐关注清单。
2. **推荐关注清单** —— 独立 CSV（`watchlist.csv`）+ 报告内表格。

核心立场：**热度 ≠ 记录数**。记录曝光多不代表临床价值高；价值判断综合评价质量、样本量、阶段、终点证据强度与机制新颖度。

## 与多临床结果对比 skill 的关系

- 本 skill 是**统计解读面板**（data-analysis oriented），回答"这个会议在哪些方向有进展/值得关注"。
- 多临床结果对比 skill 是**比较分析**（comparison-first），回答"某几个药孰优孰劣"。
- 两者数据口径不同（本 skill 用 `np_clinical` 会议级全量；对比 skill 用选定的试验结果对象）。

## 目录结构

```
conference-clinical-interpretation/
├── system-prompts/conference-clinical-interpretation-v0.1.md   # 运行时系统提示词（与 SKILL/dist 同步）
├── skill/conference-clinical-interpretation/
│   ├── SKILL.md                  # Skill 主文件（渐进披露）
│   ├── references/
│   │   ├── data-contract.md      # 输入快照/统计文件结构、字段口径、复现命令
│   │   ├── statistics.md         # 统计维度、热度≠记录数、代表性证据
│   │   ├── chart-contract.md     # 图表类型枚举、维度白名单、可视化交付协议
│   │   ├── report-structure.md   # 报告章节结构
│   │   └── watchlist.md          # 推荐关注清单评分与生成规则
│   └── templates/
│       ├── conference-report.md  # 报告模板
│       └── watchlist.csv         # 清单 CSV 模板
├── evals/
│   ├── fetch-conference-np-clinical.mjs   # 拉取适配器（可复现）
│   ├── build-conference-stats.mjs         # 确定性统计生成器
│   ├── fixtures/                          # 数据快照（本地留档）+ 统计文件
│   └── iteration-01/asco-2026/            # 示例运行输出
├── test/                       # 校验脚本
└── dist/conference-clinical-interpretation-v0.1.zip  # 打包资产（与 sys prompt/SKILL 同步）
```

## 数据获取

数据从 `np_clinical` 索引拉取（ES），凭据由 POC 环境提供（`/home/xupeipeioo1/apps/POC/.env`），**凭据绝不写入本项目文件**。

```bash
# 1) 拉取原始快照
node --env-file=/home/xupeipeioo1/apps/POC/.env \
  evals/fetch-conference-np-clinical.mjs \
  evals/fixtures/asco-2026-np-clinical.json "ASCO 2026"

# 2) 生成确定性统计文件
node evals/build-conference-stats.mjs \
  evals/fixtures/asco-2026-np-clinical.json \
  evals/fixtures/asco-2026-stats.json
```

原始快照含全文（体积大），本地留档；模型消费轻量的 `*-stats.json`。

## 可视化接入（Tool Smith 契约）

- 交付走 **Workspace Visualization 文件协议**：模型把统计/图表数据文件写入 `/workspace/visualizations/`，正文用独占一行 `::visualization[标题]{path=...}` 引用。
- 本 skill 定义数据协议（`.json`/`.csv`），数据文件**不需要**调用 `read_me`；只有同时创建内置 SVG/HTML/chart/map/interactive/art 视觉时才调用 `read_me`。
- **模型不生成 ECharts/Chart.js options**，只输出受约束的结构化分析计划（图表类型枚举 + 白名单维度 + 数据），前端按协议映射到维护好的图表模板。
- 颜色只用 renderer 注入的 `--viz-*` 语义 token（SVG/HTML）或 `resolveColorToken(name)`（Canvas/Chart.js/D3）。
- 详见 `skill/.../references/chart-contract.md`。

## 校验与迭代

- `test/` 下运行结构/契约校验（确保 SKILL ↔ system-prompts ↔ dist 同步、图表枚举合法、watchlist 字段完整）。
- 每次 skill 资产变更：同步 system-prompts、重建 dist zip，三者保持一致。
