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

### `chart-visualization-json/1.0.10`（上游最新；**部署端尚未升级**）

| 项 | 值 |
| --- | --- |
| 来源 | 前端提供的 `C:\Users\YYMF\Downloads\chart-visualization-json-v1.0.10.zip`（明文 zip，`PK\x03\x04`，未走 DLP 透明加密） |
| 源包 SHA-256 | `57c36b0f4c9a409b483eb245c807afd87a1fbce4692ed9d13156e84d9323a4b7` |
| 收到日期 | 2026-09-11 |
| 包内文件数 | 47（不含 `node_modules/`，与 1.0.9 同集，无新增文件） |
| 内嵌 `config.js` 的 `IFRAME_TEMPLATE` | `https://vcdn.pharmcube.com/ai-charts-html/test/20260911-134013/iframe-template.json` |
| 与 Tool Smith 部署端是否一致 | **否**——2026-09-11 用户决定暂不升级部署端，部署端仍是 1.0.9 / `20260910-153117` |

#### 1.0.9 → 1.0.10 差异（2026-09-11 实测，共 6 个文件）

| 文件 | 变化 |
| --- | --- |
| `config.js` | `IFRAME_TEMPLATE` 指向新发布 `…/20260911-134013/…` |
| `templates/{bar,line,timeline,visualization}.json` | 仅 envelope 的 `iframe_template` 值同步为同一发布 ID |
| `references/chart-types.md` | **仅 +1 行**：`**负值（line / bar）**：value 允许为负数。bar 恒以 0 为基准双向生长（正值向右/向上、负值向左/向下，单系列负值柱用紫色区分）；line 数值轴含负刻度并补入 0，但线色不随正负变化。` |
| `SKILL.md` / `schemas/*` / `scripts/validate.js` | **逐字节未变** |

即：**协议零变更**，`schemas/data.js` 仍是 `value: z.number()`（没加 `.nonnegative()`）→ 上游选的是「支持负值」而非「fail-loud」。

**渲染器确实修了（源码级 + 实测双证）**，新 bundle `static/index-DocPC1fd.js`：bar 值域 `Si({min:0, max:maxValue||0})` → `vi({min: Math.min(0, n.minValue||0), max: Math.max(0, n.maxValue||0)})`；柱长 `max(plotW*(v/domainMax), 3)` + 固定起点 `padL` → 零轴 `k(0)` + `max(|k(v)−k(0)|, 3)`；横向刻度/网格 `padL + plotW*tick/(domainMax||1)` → 按 `[domainMin, domainMax]` 归一化；新增单系列负值柱紫色判定；line 侧 `max: i<0 ? Math.max(s,0) : s`。实测同一份全负 bar 数据：旧版 5 根柱全 `3px`（起点同一处），新版 `566.8/818.8/852.8/865/881.6 px`、右端全部 `x+w=1320`（0 轴）、`8.72 px per unit` 五根一致、fill 全 `#814487` 紫。回归：正值分组柱逐像素一致，负值折线正常（仅因「补入 0」整体压缩）。

### `chart-visualization-json/1.0.9`（部署端当前等价物）

| 项 | 值 |
| --- | --- |
| 来源 | 前端提供的 `C:\Users\YYMF\Downloads\chart-visualization-json-v1.0.9.zip`（明文 zip，未走 DLP 透明加密） |
| 源包 SHA-256 | `572fbe553978696e3f915b6a13ea9a7ebe31f4be6d00987c057c8daf75e20438` |
| 收到日期 | 2026-09-11 |
| 包内文件数 | 47（不含 `node_modules/`） |
| 内嵌 `config.js` 的 `IFRAME_TEMPLATE` | `https://vcdn.pharmcube.com/ai-charts-html/test/20260910-153117/iframe-template.json` |
| 与 Tool Smith 部署端是否一致 | 是（截至 2026-09-11；用户暂不升级部署端） |

本地跑校验器（把 `<版本>` 换成实际版本，注意 `iframe_template` 需与该版本 `config.js` 一致）：

```bash
cd vendor/chart-visualization-json/<版本>
node scripts/validate-cli.js templates/bar.json          # 应输出「校验通过: chart-visualization-json（option.type=bar）」
```

若 `node_modules/` 缺失（例如别人 clone 后另装）：`npm install zod --no-save`（上游 `package.json` **未声明** `zod` 依赖，这是已知缺口）。

## 上游协议要点（v1.0.9 起，2026-09-11）

- **负值（v1.0.10 起）**：`value` 允许负数。bar 恒以 0 为基准双向生长（正值向右/向上、负值向左/向下；**单系列负值柱用紫 `#814487`**，多系列仍走调色板）；line 数值轴含负刻度并补入 0，线色不随正负变化。**v1.0.9 的渲染器在此处静默失败**：bar 值域硬编码 `[0, maxValue]`，全负数据 → 柱长全卡 `3px`、横向刻度算出负像素飞出画布，而 schema 也没有 `.nonnegative()` 兜底（写进去不报错、画出来是废图）。

- 产物顶层是 **envelope**：`{ "id": "chart-visualization-json", "iframe_template": "…", "option": { …图表配置… } }`；`option.type` 才是图表类型。只写 `option` 层的旧格式**已不兼容**（`未包 envelope：…；旧格式（option 层配置）已不再兼容。`）。
- `iframe_template` 必须与上游 `config.js` 的 `IFRAME_TEMPLATE` **全等**（不是「任意绝对路径都放行」）。该值由 `apps/ai-charts-html` **每次 CDN 发布成功后就刷新**，并同步刷新 `templates/*.json`——所以**只能运行期现读**（`templates/{bar,line,timeline}.json` 或 `config.js`），**禁止硬编码**、禁止沿用上一次运行的值。
- 渲染开放面 `RENDERABLE_CHART_TYPES = ["line", "bar", "timeline"]`；Schema 校验覆盖 28 种 `type`，其余类型校验通过也不能 `::visualization` 展示。
- 未知字段被 Zod 默认 strip（不报错）：`option` 内的 `_comment`、envelope 顶层的额外键都**不影响通过**。
- CLI 退出码：通过 `0`、失败 `1`。

## 更新流程

1. 拿到新版 zip（注意：公司 Windows 落盘文件可能被 DLP 透明加密——WSL 下 `head -c 8` 看不到 `PK` 时，改用 Windows Python 读 `C:\...` 再写到 WSL）。
2. 先跑 `unzip -l`（或 Python `zipfile.namelist()`）核对清单，再解压到 `vendor/<skill>/<版本>/`。
3. 在本文件补一行留档（来源路径 + 源包 SHA-256 + 日期 + 内嵌 `iframe_template`）。
4. 跑一遍 `validate-cli.js templates/*.json` 与「我们自己的 `option` 内层 + 新 envelope」的组合用例，确认没被上游改坏。
5. 与上一版 `diff -r`（排除 `node_modules`），把**影响我们文档的差异**同步进 `references/chart-templates.md` 与系统提示词的 Chart contract 段。
