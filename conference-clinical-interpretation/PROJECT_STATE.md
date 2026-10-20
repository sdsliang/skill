# PROJECT_STATE — 会议临床解读 (Conference Clinical Interpretation)

更新于：2026-08-19

## 状态

- **阶段**：v0.2 交互式渲染完成（ECharts 仪表盘 + 药物机制增强）；v0.1（Skill 资产 + 数据管线 + dist + 契约校验）保持完成
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
- `render-report.mjs`：**本地预览渲染器（v1，静态 SVG 版）**（不进 dist）——把 `report.md` 的 `::visualization[...]` 引用替换为真实图表，输出自包含 `report.html`（纯内联 SVG、离线可读、颜色走 `--viz-*` token）。
- fixtures：`asco-2026-np-clinical.json`（136MB，本地留档，不入 Git）、`asco-2026-stats.json`（1.7MB）。

### 药物机制增强（DrugBank 同源，v0.2 新增）
- `evals/enrich-drug-profiles.mjs`：批量查询 Linking API `/linking/drug`（drug_earth 药物字典，含 `drugbank_id` 可关联 DrugBank），为代表药物/重点清单补充靶点、MOA、modality、阶段、别名、研发机构、获批信息 → `drug-profiles.json`（59 药，含 `lookup` 索引）。
- `evals/report-template.html` + `evals/render-echarts.mjs`：**ECharts 交互式仪表盘渲染器（v2）**——内嵌 `runtime/echarts.min.js`（1.1MB）自包含离线可读，输出 `report.html`：KPI 卡组、重点清单（靶点/MOA 标签 + 下钻）、阶段×结果气泡矩阵、适应症×终点热力图、药物成熟度四象限、发布节奏时间线、药物×适应症/标志物关系网络、证据明细表 + 全字段搜索（含靶点/MOA/别名）+ 抽屉画像下钻。
- `references/drug-enrichment.md`：药物画像增强规则、数据来源、短代码化、噪声过滤、**中国企业/中国创新药判定**（companies 匹配 + license-out 手动白名单，标注近似）。
- fixtures：`asco-2026-np-clinical.json`（136MB，本地留档，不入 Git）、`asco-2026-stats.json`（1.7MB）、`asco-2026-drug-profiles.json`（0.6MB，含 `china_drugs` 21 药）。

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
- [x] **渲染器升级 v2（ECharts 交互式仪表盘）**：5 图 + KPI + watchlist + 证据表 + 搜索 + 抽屉；CDP 交互验证通过（点击下钻、PD1 搜索命中 344 条）
- [x] **药物机制增强**：59 个代表药物补充靶点/MOA（Linking API drug 字典），渲染层标签 + 画像下钻 + 搜索增强
- [x] **报告去清单化 + 分析维度扩展**（本次 turn）：
  - report-structure/模板/示例报告：第 8 章改为「推荐关注概览」（Top 3-5 摘要 + CSV 引用），完整明细只在 `watchlist.csv`
  - 新增 `references/analysis-dimensions.md`：网络调研 ASCO 2026 媒体维度（世易医健 95 项/丁香通 94 项+LBA/良医汇按癌种报告类型/妇产科在线按癌种精粹）→ 数据支持度对照表
  - 新增「中国企业/中国创新药参与」维度：drug-profiles 增加 `is_china_origin`/`china_company` 判定 + `china_drugs`（21 药），渲染器 Tab 1 新增中国创新药面板（记录数/评价分布/机制/下钻）；报告新增 8a 章节；局限说明（报告级别字段缺失、企业归属近似）
  - 修复 enrich 脚本 `i?car` 正则误判（瑞卢戈利）；契约校验通过；dist 10 文件

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
- **推荐关注清单独立 CSV**：正文只给概览（Top 3-5 摘要 + CSV 引用），完整明细只在 `watchlist.csv`（避免重复维护）。
- **中国企业/中国创新药维度**：经 drug_earth companies 近似判定 + license-out 手动白名单；`originator_regions` 太宽泛不作依据；报告级别（Oral/LBA）字段缺失不臆造。
- **药物画像增强**：drug_earth 字典（Linking API `/linking/drug`）提供靶点/MOA/modality/阶段/DrugBank ID；`drug-profiles.json` 含 `lookup` 索引供 O(1) 检索。
- **渲染器 v2 = ECharts 交互式仪表盘**：内嵌 echarts.min.js 保持自包含离线可读；与 v1 静态 SVG 版（`render-report.mjs`）并存，二者均为本地预览用途、不进 dist。
- 与多临床结果对比 skill 明确分工：本 skill 统计解读，彼 skill 比较分析。

## 2026-10-20 重构：交付形态切到产品 v3.1

- 用户拍板「A + 按产品 v3.1」：仍在 `skill/conference-clinical-interpretation/` 这一套工程里改，交付形态照 v3.1
  （`output/report-{cn,en}.md` + `citations-{cn,en}.json` + `output/visualizations/<lang>/…` + `index.json` + `summary-callout`）。
- 数据源换成平台 MCP 工具 `pharmcube-query-clinical-result-with-params`（会议靠 `meeting_tags` 过滤），
  全量 ASCO 2026 已拉齐：1648 → 合并后 **1639 条**（`output/pharmcube-query-clinical-result-with-params/asco-2026-clinical-results.ndjson`，40MB）。
- 新流水线（node，无第三方依赖，运行在交付根）：
  - `scripts/chart/cli/merge-batches.mjs`：批量响应 → NDJSON（数组并集、标量首个非空）
  - `scripts/chart/cli/build-charts.mjs`：→ 两版图表树 + `index.json` + `summary-callout` + `report-source-<lang>.md` + `chapters-summary.json`
  - `scripts/chart/cli/check-drill.mjs`：下钻载荷批量过 `list-filter-json` 白名单
  - `scripts/chart/registry/views.mjs`：4 章 12 视图（bar / heatmap / sankey）
- 已验证：26 个 envelope 全部过 `chart-component-layout-json-validation` 校验；两版各 245 条 drill 载荷 `failed=0`；
  本地预览 `evals/preview/index.html`（`python3 -m http.server 8811` + `?lang=cn|en`）渲染正常。
- 依赖技能已拉到 `working/deps-skills/`，并在 `skill/` 下建了 symlink（本地开发用；平台上它们是兄弟技能）。
- 未完成：报告正文（report-cn/en）、引文 JSON（`--citations --picks`）、preflight、SKILL.md/references 重写、
  system prompt、dist 打包、TS 发布配置与线上实测。
- 已知限制：该工具不返回实体 ID 字段（无 `indication_ids`/`drug_earth_ids`），
  `clinical_result_.*` 里只有 `disease_id`；臂内 `drugs[]` 才带 `drug_earth_id`/`company_ids`。按维度下钻因此只能部分生效。

## 2026-10-20 支线：可交互解读页（HTML fragment）

- 参考件 `D:\Users\feishu_download\药物闭环.html`（2.2MB、three.js WebGL 单场景、镜头/粒子/导览/`/` 搜索）。
- 平台事实（`toolsmith-visualization/references/visualization-integration.md`）：`::visualization[标题]{path="/workspace/visualizations/x.html"}`
  可以交付 **HTML fragment**，隔离 iframe 渲染，CDN 白名单 cdnjs/esm.sh/jsdelivr/unpkg（three.js 可用），
  限制：≤1 MiB、不能有 doctype/html/head/body、**点击不下钻**（宿主只处理 resize/render-ready/render-error）。
  → 结论：**双轨**。JSON envelope 负责「可下钻到证据列表」的定量图；HTML fragment 负责质感/动画/页内联动。
- 原型：`evals/preview/gen-interactive.mjs` → `evals/preview/interactive-demo.html`（520KB，数据内联，无 CDN 依赖）。
  5 个块：KPI 条 / 披露节奏（日期曲线 + LBA 点）/ 癌种热度环（极坐标，点选筛选）/ 药物星座（阶段×摘要数×积极率）/
  靶点×癌种矩阵 / 可行动信号 Top12 / 当前筛选摘要列表。全部共享一份筛选状态（癌种·阶段·评价·日期·搜索）。
  本地预览 `evals/preview/demo.html`（`.preview.html` 副本才补 charset，正式 fragment 保持纯净）。

### 2026-10-20 决策与增补（支线 `feature/interactive-html-track`）

- **HTML 轨不进交付包**（用户 2026-10-20 拍板），只作本地 demo / 设计探针：
  `evals/preview/gen-interactive.mjs` + `interactive-demo.html`（+ 预览副本）。打包脚本必须排除 `evals/`，`::visualization` 仍只能指 `.json`。
- **不做「vs 上届」对比**（用户拍板），章节不做 cohort 化。
- **新增「药品研发机构」口径**（除申办方之外）：
  - `rank-institute-bar`（主要药物研发机构，Top15，口径内总数 5703，带该维度标注 1539 篇）
  - `rank-institute-external-bar`（被外部发起研究最多的研发方，Top12，577 篇）——只统计「申办方与该药研发方无交集」的研究
  - 实测：997 篇同时有申办方与研发方，其中 576 篇（57.8%）**完全无交集**；542 篇只有研发方、没有申办方。说明「谁做研究」与「药属于谁」是两个口径，值得并列。
- 顺带修掉校验器的 12 条 `subTitle 建议精练` 告警：副标题压成「会议 · 研究摘要数（按研究去重）」，
  「Top-N 覆盖 / 口径内总数 / 长尾占比 / 带该维度标注的摘要数」全部下沉到 notes 的**口径行**（说明 → 口径 → 数据来源 三行）。现 14 张 × 2 语言 0 告警。
