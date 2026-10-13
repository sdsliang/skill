# vendor/ — 外部（上游）Skill 的只读留档

这里存放**由其他团队维护、我们自己不产出**的 skill 副本，用途只有一个：**本地能对上游协议做权威核对**。

## 为什么需要这个目录

`clinical-result-comparison` 的图表产物必须通过 `chart-visualization-json` 的校验器，协议细节（envelope、字段默认值、`iframe_template` 取值）**以上游发布版为准**。此前我们把副本随手放在 `/tmp/chartvis/`，结果：

- 前端在 2026-09-10 把图表的 skill 升级成 envelope 格式**但没有通知我们**；
- 我们拿 `/tmp/chartvis/` 的**旧副本**验证，得到「三个模板全 PASS」的**错误结论**，真实运行里被部署端校验器打回（多花约 4 步返工）。

结论：**上游副本必须有稳定路径、必须带版本号、验证时只能用它而不是随手抓的副本。**

## 目录约定

```
vendor/<上游 skill 名>/<版本>/
```

- 逐字节复制解压结果，不做任何编辑（含 `node_modules/`，便于直接跑 CLI）。
- **默认不入版本库**（见仓库根 `.gitignore` 的 `vendor/` 两行），原因：这是别人的内部源码、含内部 CDN 地址，是否要提交进 `sdsliang/skill` 由人决定。
  要让某个版本入库：删掉对应忽略行，或 `git add -f vendor/chart-visualization-json/1.0.9`。
- 新增版本**不要覆盖旧版本**——保留多版本才能看出上游改了什么。

## 当前留档

### `chart-visualization-json/1.0.12-20260921`（**部署端当前版本**，2026-10-12 实拉到）

| 项 | 值 |
| --- | --- |
| 来源 | 只读拉取平台当前版本：`POST /api/skills/list {family_id, only_latest:true}` → `GET /api/skills/{id}/download`（脚本 `/home/xupeipeioo1/tmp/get_chart_skill.py`） |
| 源包 SHA-256 | `423c50a5c857eeac4cfc2a1a342d47408694ebd9e2d6a71791e9e455bd83c104`（64,214 B） |
| 拉取日期 | 2026-10-12 |
| 包内文件数 | 48（比 `-20260914` **多 `docs/development.md`**，其余同集） |
| 内嵌 `config.js` 的 `IFRAME_TEMPLATE` | `https://vcdn.pharmcube.com/ai-charts-html/test/20260921-085926/iframe-template.json` |
| 与 Tool Smith 部署端是否一致 | **是**（平台 current 仍标 `1.0.12`，`updated = 2026-09-21T11:58:40`） |

**为什么单开一个目录**：平台把它**原地更新**了（版本标签仍是 1.0.12，内容换成 20260921 构建）。`toolsmith-publish deps` **只比版本标签**，所以当次 `deps` 报 `unchanged` —— 是**用户投诉“圆点大小没有任何效果”**后才把包拉下来 diff 发现的（台账 **O50**）。因此同一版本号的两次构建各留一份，目录名缀构建 ID 日期。

#### `1.0.12-20260914` → `1.0.12-20260921` 差异（2026-10-12 实测，7 个文件 + 1 个新目录）

| 文件 | 变化 |
| --- | --- |
| `config.js` | `IFRAME_TEMPLATE` 指向新发布 `…/20260921-085926/…` |
| `templates/{bar,line,timeline,visualization}.json` | envelope 的 `iframe_template` 同步；**并整块删除了 `width`/`height`**（尺寸不再由模板冻结） |
| `references/chart-types.md` | 新增**标题/副标题规则**：`title` ≤ 24 字宽、`subTitle` ≤ 32 字宽（中文字 1、英文词约 2），不重复/精练/合适，禁 `图表`/`统计` 类空词与句号；另加 `dataSource`/`describe` 禁前缀、`drill` 形状说明 |
| `scripts/validate.js` | 新增 `drillShapeWarnings()` / `collectDrillWarnings()` / `collectMetaLabelWarnings()`，以及 `TITLE_MAX_WIDTH=24` / `SUB_TITLE_MAX_WIDTH=32` / `LATIN_WORD_WIDTH=2` / `TITLE_NEST_RATIO=0.5` / `GENERIC_TITLE_PATTERN` / `MISPLACED_LABEL_PATTERN` 等常量 |
| `scripts/validate.test.js` | 同步新增用例 |
| `docs/development.md` | **新增文件**（上游自己的打包/发 CDN/测试命令说明） |
| `references/schemas/*`、`scripts/validate-cli.js`、`SKILL.md` | **逐字节未变** —— 包括 `schemas/timeline.js` 仍保留 `weight`（`z.number().min(0).optional().default(0)`）与 `weightLegend` |

**影响面（全部是 warning 级，不改我们据此判定的 exit code）**：

- 上游新校验**只出 warning**（标题/副标题字宽、`drill` 形状、`dataSource`/`describe` 前缀）⇒ 退出码仍为 `0`，我们 `make_chart.py` 的「校验器 PASS」判定不受影响；但超限 warning 会进生产 run，因此**顺手把我方三个骨架的 `subTitle` 缩到 ≤32 字宽**（`endpoint-bar.json` = `不同试验主要终点并列 · 非头对头比较`、`endpoint-line.json` = `同队列时点连线，不跨队列外推`、`evidence-timeline.json` = `同一试验证据披露与结果演进`；改后零 warning）。
- **时间轴的 `weight` / `weightLegend` 在上游被完全放行**（故意构造带这两键的 spec 跑新 `validate-cli.js` ⇒ `exit=0` 且无 warning）⇒ 上游不会拦住这个回归，**守卫只能在我们这边**（`make_chart.py` + `check_report.py`）。
- **渲染器真相（部署端 bundle `static/index-9EvceNR0.js`，288,806 B）**：时间轴节点构造硬编码 `{ r: 3, shape: "circle" }`（`r: dm`、`dm = 3`、色 `#8993A4`），调用者只有 DOM 渲染器；节点 dot 的 CSS 是固定 `6px × 6px` 灰圆点，**不带 group / color / shape** ⇒ 大小与形状都不可能表达任何东西。且渲染派发表里 `timeline` 的 legend 渲染器是 `function Fm(){return []}`（**空数组**）⇒ 时间轴**根本不渲染图例**，`legend`（含 `legend[].shape`）对画布与图例都无效果。
- 结论/适配：本 skill 的时间轴**不再使用 `weight`/`weightLegend`/`legend`**（骨架 + 两份 reference 文档已清空），并由 `make_chart.py`（`exit 3`、不写文件）与 `check_report.py`（findings、`exit 3`）双层拒收；报告正文也不得再解释“圆点大小/形状/图例”这类不存在的编码（`check_report.py` 的 `CHART_ENCODING_CLAIM_RE`）。上游 schema 保留这些字段是「允许」，不等于「渲染生效」。

### `chart-visualization-json/1.0.12-20260914`（历史；2026-09-14 由 `deps` 门禁发现，曾为部署端当前版本）

> 目录原名为 `1.0.12/`，2026-10-12 改为带构建 ID 的 `1.0.12-20260914/`（两个构建同为平台版本 1.0.12，同名会互相覆盖）。

| 项 | 值 |
| --- | --- |
| 来源 | 只读拉取平台当前版本：`POST /api/skills/list {family_id, only_latest:true}` → `GET /api/skills/{id}/download`（脚本 `/home/xupeipeioo1/tmp/get_chart_skill.py`） |
| 源包 SHA-256 | `644a97f32cc6e05e5fae5ce4abfd322e89e332103f10f3d1d378abacb29994b4`（54,684 B） |
| 拉取日期 | 2026-09-14 |
| 包内文件数 | 47（与 1.0.10 同集，无新增/删除文件） |
| 内嵌 `config.js` 的 `IFRAME_TEMPLATE` | `https://vcdn.pharmcube.com/ai-charts-html/test/20260914-145519/iframe-template.json` |
| 与 Tool Smith 部署端是否一致 | **否（历史记录）** —— 2026-09-14 起为部署端 current；2026-09-21 上游把同一版本号原地更新为 `1.0.12-20260921` 构建 |

#### 1.0.10 → 1.0.12 差异（2026-09-14 实测，共 6 个文件）

| 文件 | 变化 |
| --- | --- |
| `config.js` | `IFRAME_TEMPLATE` 指向新发布 `…/20260914-145519/…` |
| `templates/{bar,line,timeline,visualization}.json` | 仅 envelope 的 `iframe_template` 值同步为同一发布 ID（其余键逐字节相同） |
| `references/chart-types.md` | **仅 +1 行**：`**堆叠负值（bar stack: true）**：出现负值时正负分离堆叠——正值自 0 向上/向右累积、负值自 0 向下/向左累积，0 线落在绘图区内；端值合计按方向各标一个…纯正值堆叠与 group 并排不受影响。` |
| `SKILL.md` / `schemas/*` / `scripts/validate.js` | **逐字节未变** |

即：**协议零变更**，新增的只是「堆叠 + 负值」这一种我们**不产出**的组合（我们的并排柱固定 `group:false, stack:false`）；发布 ID 变化对我们是透明的（本仓库无硬编码 `iframe_template` 的规则已生效，运行期现读模板）。**本 skill 无适配改动**，`deps --accept` 记新基线即可。

### `chart-visualization-json/1.0.10`（历史；部署端曾为 1.0.10 一段时间）

| 项 | 值 |
| --- | --- |
| 来源 | 前端提供的 `C:\Users\YYMF\Downloads\chart-visualization-json-v1.0.10.zip`（明文 zip，`PK\x03\x04`，未走 DLP 透明加密） |
| 源包 SHA-256 | `57c36b0f4c9a409b483eb245c807afd87a1fbce4692ed9d13156e84d9323a4b7` |
| 收到日期 | 2026-09-11 |
| 包内文件数 | 47（不含 `node_modules/`，与 1.0.9 同集，无新增文件） |
| 内嵌 `config.js` 的 `IFRAME_TEMPLATE` | `https://vcdn.pharmcube.com/ai-charts-html/test/20260911-134013/iframe-template.json` |
| 与 Tool Smith 部署端是否一致 | **否（历史记录）**——2026-09-11 用户决定暂不升级部署端；之后部署端实际升到 1.0.10，2026-09-14 又升到 1.0.12 |

#### 1.0.9 → 1.0.10 差异（2026-09-11 实测，共 6 个文件）

| 文件 | 变化 |
| --- | --- |
| `config.js` | `IFRAME_TEMPLATE` 指向新发布 `…/20260911-134013/…` |
| `templates/{bar,line,timeline,visualization}.json` | 仅 envelope 的 `iframe_template` 值同步为同一发布 ID |
| `references/chart-types.md` | **仅 +1 行**：`**负值（line / bar）**：value 允许为负数。bar 恒以 0 为基准双向生长（正值向右/向上、负值向左/向下，单系列负值柱用紫色区分）；line 数值轴含负刻度并补入 0，但线色不随正负变化。` |
| `SKILL.md` / `schemas/*` / `scripts/validate.js` | **逐字节未变** |

即：**协议零变更**，`schemas/data.js` 仍是 `value: z.number()`（没加 `.nonnegative()`）→ 上游选的是「支持负值」而非「fail-loud」。

**渲染器确实修了（源码级 + 实测双证）**，新 bundle `static/index-DocPC1fd.js`：bar 值域 `Si({min:0, max:maxValue||0})` → `vi({min: Math.min(0, n.minValue||0), max: Math.max(0, n.maxValue||0)})`；柱长 `max(plotW*(v/domainMax), 3)` + 固定起点 `padL` → 零轴 `k(0)` + `max(|k(v)−k(0)|, 3)`；横向刻度/网格 `padL + plotW*tick/(domainMax||1)` → 按 `[domainMin, domainMax]` 归一化；新增单系列负值柱紫色判定；line 侧 `max: i<0 ? Math.max(s,0) : s`。实测同一份全负 bar 数据：旧版 5 根柱全 `3px`（起点同一处），新版 `566.8/818.8/852.8/865/881.6 px`、右端全部 `x+w=1320`（0 轴）、`8.72 px per unit` 五根一致、fill 全 `#814487` 紫。回归：正值分组柱逐像素一致，负值折线正常（仅因「补入 0」整体压缩）。

### `chart-visualization-json/1.0.9`（历史；曾是部署端等价物）

| 项 | 值 |
| --- | --- |
| 来源 | 前端提供的 `C:\Users\YYMF\Downloads\chart-visualization-json-v1.0.9.zip`（明文 zip，未走 DLP 透明加密） |
| 源包 SHA-256 | `572fbe553978696e3f915b6a13ea9a7ebe31f4be6d00987c057c8daf75e20438` |
| 收到日期 | 2026-09-11 |
| 包内文件数 | 47（不含 `node_modules/`） |
| 内嵌 `config.js` 的 `IFRAME_TEMPLATE` | `https://vcdn.pharmcube.com/ai-charts-html/test/20260910-153117/iframe-template.json` |
| 与 Tool Smith 部署端是否一致 | 否（历史记录，截至 2026-09-11 时为是） |

本地跑校验器（把 `<版本>` 换成实际版本，注意 `iframe_template` 需与该版本 `config.js` 一致）：

```bash
cd vendor/chart-visualization-json/<版本>
node scripts/validate-cli.js templates/bar.json          # 应输出「校验通过: chart-visualization-json（option.type=bar）」
```

若 `node_modules/` 缺失（例如别人 clone 后另装）：`npm install zod --no-save`（上游 `package.json` **未声明** `zod` 依赖，这是已知缺口）。

## 内联留档：`report-humanizer-zh` 的 prosa 风格扫描器（2026-10-13，R59）

例外于上面的「目录留档」约定：R59 把上游 `report-humanizer-zh` 的**确定性扫描器**逐字节内联进了我们自己的包（不再运行期依赖外部挂载）。路径与指纹：

| 项 | 值 |
| --- | --- |
| 上游来源 | `report-humanizer-zh/skill/report-humanizer-zh/scripts/tell-scan.py`（仓库版本 **v0.1.1**；平台部署版号 1.0.0） |
| 内联落点 | `skill/multi-clinical-result-comparison/scripts/tell-scan.py`（随 dist 发布） |
| 字节同一性 | sha256 `1992a4c48f78dc8e3ec2d0c96a2752eb1b9a076fd05dda37720e94a4fe8873f4`（22,558 B） |
| 日期 | 2026-10-13 |
| 漂移拦截 | `evals/scripts/test-tell-scan.py::test_bundled_copy_matches_the_upstream_repo`（兄弟目录不在时 skip） |

同时内联了上游 `references/patterns-zh.md` 中**报告文体相关**的条目，改写为我方 `references/prose-style-zh.md`（12226 B，非逐字节拷贝——上游原文含面向通用写作的条目与 examples，未纳入）。上游 SKILL.md 未内联。

**为什么不放在 `vendor/`**：`vendor/` 的语义是「上游包的只读副本，不入 dist、不被 Skill 引用」，而这份扫描器**必须随包发布并在运行时执行**，所以它进包；本表只承担溯源职责。

## 上游协议要点（v1.0.9 起，2026-09-11；v1.0.12-20260921 补记）

- **时间轴是竖向列表，不是「带编码的图」**：每个节点 = 时间 + 卡片，节点**等大等形**（固定 6px 灰圆点）、`legend` 渲染器对 `type: timeline` 直接返回空数组 ⇒ **`weight`（节点大小）/ `weightLegend` / `legend`（含 `shape`）/ `group`（颜色与形状）都没有任何视觉效果**。上游 schema 仍允许这些字段（写进去不报错），但**允许 ≠ 渲染生效**；要表达成熟度或分类只能写进节点文字与报告正文。本仓库对此加了双层门禁（见 `references/timeline-diagram.md` 构建规则第 8 条）。
- **标题/副标题字宽上限（v1.0.12-20260921 起 warning-only）**：`title` ≤ 24 字宽、`subTitle` ≤ 32 字宽（中文字 1、英文词约 2），超限只给 `⚠` 不拦；`dataSource`/`describe` 不要带「数据来源：」「说明：」前缀。
- **模板不再冻结 `width`/`height`**（v1.0.12-20260921 起移除）：窄容器下固定 920px 会横向溢出，请保持响应式。
- **负值（v1.0.10 起）**：`value` 允许负数。bar 恒以 0 为基准双向生长（正值向右/向上、负值向左/向下；**单系列负值柱用紫 `#814487`**，多系列仍走调色板）；line 数值轴含负刻度并补入 0，线色不随正负变化。**v1.0.9 的渲染器在此处静默失败**：bar 值域硬编码 `[0, maxValue]`，全负数据 → 柱长全卡 `3px`、横向刻度算出负像素飞出画布，而 schema 也没有 `.nonnegative()` 兜底（写进去不报错、画出来是废图）。

- 产物顶层是 **envelope**：`{ "id": "chart-visualization-json", "iframe_template": "…", "option": { …图表配置… } }`；`option.type` 才是图表类型。只写 `option` 层的旧格式**已不兼容**（`未包 envelope：…；旧格式（option 层配置）已不再兼容。`）。
- `iframe_template` 必须与上游 `config.js` 的 `IFRAME_TEMPLATE` **全等**（不是「任意绝对路径都放行」）。该值由 `apps/ai-charts-html` **每次 CDN 发布成功后就刷新**，并同步刷新 `templates/*.json`——所以**只能运行期现读**（`templates/{bar,line,timeline}.json` 或 `config.js`），**禁止硬编码**、禁止沿用上一次运行的值。
- 渲染开放面 `RENDERABLE_CHART_TYPES = ["line", "bar", "timeline"]`；Schema 校验覆盖 28 种 `type`，其余类型校验通过也不能 `::visualization` 展示。
- 未知字段被 Zod 默认 strip（不报错）：`option` 内的 `_comment`、envelope 顶层的额外键都**不影响通过**。
- CLI 退出码：通过 `0`、失败 `1`。

## 更新流程

1. 拿到新版 zip（注意：公司 Windows 落盘文件可能被 DLP 透明加密——WSL 下 `head -c 8` 看不到 `PK` 时，改用 Windows Python 读 `C:\...` 再写到 WSL）。
2. 先跑 `unzip -l`（或 Python `zipfile.namelist()`）核对清单，再解压到 `vendor/<skill>/<版本>/`。
3. 在本文件补一行留档（来源路径 + 源包 SHA-256 + 日期 + 内嵌 `iframe_template`）。**同版本号的第二次构建要另起目录** `vendor/<skill>/<版本>-<构建ID日期>/`（平台会原地更新同一版本号，`deps` 看不出来）。
4. 跑一遍 `validate-cli.js templates/*.json` 与「我们自己的 `option` 内层 + 新 envelope」的组合用例，确认没被上游改坏。
5. 与上一版 `diff -r`（排除 `node_modules`），把**影响我们文档的差异**同步进 `references/chart-templates.md` 与系统提示词的 Chart contract 段。
