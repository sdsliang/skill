# PROJECT_STATE — report-humanizer-zh

最后更新：2026-10-09（新会话先读本文件 + `AGENTS.md`）

## 一句话状态

中文报告「去 AI 味」Skill **内容与机械闸门已完成并通过**（20/20）；**尚未发布到 ToolSmith**（等用户授权 + TS 侧建 family）。英文姊妹项目 `../report-humanizer-en` 同步完成（20/20）。

## 交付物

| 文件 | 说明 |
|---|---|
| `skill/report-humanizer-zh/SKILL.md` | 九节结构：一 优先级 / 二 报告文体与读者 / **三 硬性禁项：不写工作过程与自我解释** / 四 数据与依据 / 五 术语与命名（药名三步） / 六 工作流程 / 七 交付前核对 / 八 机械自查 / 九 何时不要改。三种模式：嵌入写作 / 改写草稿 / 审阅 |
| `skill/report-humanizer-zh/references/patterns-zh.md` | A1–A10 结构级、B1–B10 措辞级、C1–C7 中文特有、D1–D3 草稿残留；每条〔强〕/〔弱〕+ 报告场景前后对照；末节说明与扫描器编号的关系 |
| `skill/report-humanizer-zh/references/naming-bilingual.md` | 药名流程：常识优先 → 宿主成对字段 → 字典工具（`report-query-drug` / `pharmcube-mcp-drugBaseLiteCN` / Linking API `drug`）→ 方向性回退（**英→中保留英文原名；中→英用拼音**）；其它实体与格式统一 |
| `skill/report-humanizer-zh/references/examples.md` | 3 组整段前后对照（结论段 / 疗效段 / 安全性段）+「应当保留」边界；每例标出必须逐字保留的锚点 |
| `skill/report-humanizer-zh/scripts/tell-scan.py` | 零依赖双语扫描器，21,351 B，与英文版**逐字节一致** |
| `evals/test-tell-scan.py` | 机械闸门 22 项（18 项基础 + 2 项 examples 自洽性 + 2 项误报回归） |
| `evals/fixtures/` | `ai-flavored.zh.md` / `humanized.zh.md` / `keep.zh.md` / `weak-only.zh.md` / `facts.zh.json` |

## 验证结果（本地，可复现）

```
python3 -B evals/test-tell-scan.py  ->  report-humanizer-zh machine gate: 22/22 OK
```

- zh fixture 基线：`ai-flavored` 14 强 / 2 弱；`humanized` 0/0；`keep` 0 强 / 3 弱（`W-AS-WITH`、`W-PASSIVE`、`W-VERBNOUN`）；`weak-only` 0 强 / 1 弱（`S-INFL-04`）。
- `references/examples.md` 自洽：例 2 改写后补回承载判据的中位值、例 3 把 `12%` 与 `1–2 级` 写进改写前，消除「改写后出现改写前没有的数值」。
- 未跑 TS 真跑（未发布）。发布后需要按工作区规则做一次真实 `toolsmith-publish run` 并记 R 编号。

## 关键决策

1. **两个独立 skill（zh / en），不是同一个 skill 的双语模式**：各自 bundle 自包含，`tell-scan.py` 复制两份并断言逐字节一致。
2. **扫描器一个文件双语**（`--lang auto|zh|en` + `_detect_lang`），避免两份规则实现漂移。
3. **「不写工作过程/自我解释」立为最高优先级规则**（强于清单与扫描命中），例外仅限会改变读者采信或行动的口径说明。
4. **去学术腔**：面向分析报告，允许正式度、名词化、被动与限定语；不把严谨表述口语化。
5. **药名回退方向**：英→中保留英文原名（不音译、不造译名）；中→英用拼音；永不编造。
6. **扫描器定位为助手**：命中不等于必须改；weak 需 `--weak` 才影响退出码；禁止用「命中数下降」代替事实核对。
7. **扫描器两处误报已在真实报告上修正**：`S-PROC-01` 要求有主语或「了」（裸「统计/筛选」不再单命中）；表格行不参与行级命中与文档级计数（表内加粗是正常排版）。真实 R38 报告从 4 强 + 75 处粗体密度降到 0 强。
8. **严重度与扫描器对齐**：清单里 `AI 高频词` 标〔弱〕（一段内两三处才动手），与 `W-AIWORD` 的 weak 一致。

## 待办 / 待用户确认

- [ ] **是否发布到 ToolSmith**：需要 (a) 用户授权；(b) 用户在 TS 侧建 skill family；(c) `~/.config/toolsmith/projects.json` 增加本项目条目（`owned: true`）；(d) `toolsmith-publish push-skill` + `status` 回读。
- [ ] 项目 / skill / 目录命名是否沿用 `report-humanizer-zh`（用户可能想改中文名，如「报告去 AI 味（中文）」）。
- [ ] 发布后补一次真跑（`toolsmith-publish run`）并记台账。

## Git

首次纳入版本控制：commit `4e88724`（分支 `v0.15-remove-html`，已推送 `origin`）。
