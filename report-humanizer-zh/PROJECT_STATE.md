# PROJECT_STATE — report-humanizer-zh

最后更新：2026-10-10（新会话先读本文件 + `AGENTS.md`）

## 一句话状态

中文报告「去 AI 味」Skill **已发布并在 ToolSmith 原地更新**（平台 `1.0.0` / `skill_id d7fed181277045dd9f28989b9cb4acb5`，部署 == 工作树 == dist）；仓库打包版本 **`v0.1.1`**，机械闸门 **25/25 OK**。英文姊妹项目 `../report-humanizer-en` 同步完成（20/20）。

## 交付物

| 文件 | 说明 |
|---|---|
| `skill/report-humanizer-zh/SKILL.md` | 九节结构：一 优先级 / 二 报告文体与读者 / **三 硬性禁项：不写工作过程与自我解释** / 四 数据与依据 / 五 术语与命名（药名三步） / 六 工作流程 / 七 交付前核对 / 八 机械自查 / 九 何时不要改。三种模式：嵌入写作 / 改写草稿 / 审阅 |
| `skill/report-humanizer-zh/references/patterns-zh.md` | A1–A10 结构级、B1–B10 措辞级、**C1–C8 中文特有**（C8 = 数字记号混用）、D1–D3 草稿残留；每条〔强〕/〔弱〕+ 报告场景前后对照；末节说明与扫描器编号的关系 |
| `skill/report-humanizer-zh/references/naming-bilingual.md` | 药名流程：常识优先 → 宿主成对字段 → 字典工具（`report-query-drug` / `pharmcube-mcp-drugBaseLiteCN` / Linking API `drug`）→ 方向性回退（**英→中保留英文原名；中→英用拼音**）；其它实体与格式统一 |
| `skill/report-humanizer-zh/references/examples.md` | 3 组整段前后对照（结论段 / 疗效段 / 安全性段）+「应当保留」边界；每例标出必须逐字保留的锚点 |
| `skill/report-humanizer-zh/scripts/tell-scan.py` | 零依赖双语扫描器，22,558 B，与英文版**逐字节一致**（含 `_mixed_notation` → `W-FMT-MIXED`） |
| `evals/test-tell-scan.py` | 机械闸门 25 项（18 项基础 + 2 项 examples 自洽性 + 2 项误报回归 + 1 项打包一致性 + **2 项 `W-FMT-MIXED` 正反例**） |
| `tools/pack-dist.py` | 确定性打包器 → `dist/report-humanizer-zh-v0.1.1.zip`（28,406 B / 5 entries / sha256 `7264e94eabdf…`），**TS 创建 skill 上传用的附件** |
| `evals/fixtures/` | `ai-flavored.zh.md` / `humanized.zh.md` / `keep.zh.md` / `weak-only.zh.md` / `facts.zh.json` |

## 验证结果（本地，可复现）

```
python3 -B evals/test-tell-scan.py  ->  report-humanizer-zh machine gate: 25/25 OK
```

- zh fixture 基线：`ai-flavored` 14 强 / 2 弱；`humanized` 0/0；`keep` 0 强 / 3 弱（`W-AS-WITH`、`W-PASSIVE`、`W-VERBNOUN`）；`weak-only` 0 强 / 1 弱（`S-INFL-04`）。
- `references/examples.md` 自洽：例 2 改写后补回承载判据的中位值、例 3 把 `12%` 与 `1–2 级` 写进改写前，消除「改写后出现改写前没有的数值」。
- **未跑 TS 真跑**（本项目无 project_id / prompt，`run` 起不来）。效果验证改在 `clinical_result_xp` 项目上以「真对比任务 + 挂本 skill」形态做：**R39 A/B 同日对照**（挂 humanizer vs 不挂）——正文去空白字符 5,112 → 3,868（**−24%**）、平均句长 67.3 → 53.7（−20%）、逗号 139 → 84（**−40%**）、12-gram 重复率 0.0624 → 0.0447（−28%），引用标记 4/4、事实面一条不少；扫描器在实验组报告上命中 `W-BOLD-COUNT` + `W-FMT-MIXED`、对照组只命中 `W-BOLD-COUNT`。结果与缺陷记录在 `clinical-result-comparison/docs/toolsmith-verification-log.md` 的 R39。

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

- [x] **TS 侧创建**（2026-10-10：用户上传 `dist/report-humanizer-zh-v0.1.0.zip` 建好 skill，family `407d8fb6…`，平台 v1.0.0）
- [x] **重打包并原地更新**（2026-10-10：`v0.1.1` → `../tools/push-skill-inplace.py`，平台版本号仍 `1.0.0`、`is_current=True`、部署 == dist）
- [x] **真实效果取证**（2026-10-10：`clinical_result_xp` 上的 R39 A/B 同日对照，见上「验证结果」）
- [ ] 项目 / skill / 目录命名是否沿用 `report-humanizer-zh`（用户可能想改中文名，如「报告去 AI 味（中文）」）。
- [ ] **`W-BOLD-COUNT` 阈值**：实验组与对照组真产物各命中一次，但两份稿子的加粗都是表头/标签式加粗，不是强调滥用。需要更多报告样本才能判断是否该按 prose 行加权——记为「待样本」，本轮不改规则。
- [ ] **上游新鲜度**：本 skill 引用了 `report-query-drug` 等平台工具的 schema；平台工具升版后要重跑 `deps` / 重读 schema（本项目目前只能人工核对，skill 包内没有 deps 清单）。

### Phase B 本轮改动（v0.1.1，2026-10-10）

1. **排版统一规则**：新增 `C8`（数字记号混用）+ `B7` 加强（连接号统一），扫描器按**文档级弱命中** `W-FMT-MIXED`（阈值 1，只统计正文行、表格行不计）报出；边界是**只统一符号形态与空格，数值与位数一字不动**，表格 / 引文 / citation 标记 / 代码 / 路径 / URL / ID 按宿主契约。
2. **过程口吻边界**：宿主契约**要求**写的声明照写，但写成**材料属性**（「本批材料均为摘要级」可以）而不是**运行环境**（「本次运行无外网、链路未能发起」删）。
3. SKILL.md / patterns-zh.md 四处镜像改动；回归 +2 → 闸门 **25/25**；重打 `v0.1.1`；TS 原地更新（脚本 `../tools/push-skill-inplace.py`，五道护栏）。

## 线上发布记录（ToolSmith）

| 项 | 值 |
|---|---|
| skill 名 | `report-humanizer-zh` |
| skill family | `407d8fb6ad5045dda22586448c4e5df0` |
| 当前版本 | 平台 v1.0.0 / skill_id `d7fed181277045dd9f28989b9cb4acb5`（2026-10-10 首建，同日**原地更新**到 v0.1.1 内容；版本号标签不变） |
| 仓库版本 | **v0.1.1**（`dist/report-humanizer-zh-v0.1.1.zip`，28,406 B / 5 entries / sha256 `7264e94eabdf…`） |
| 部署校验 | `python3 -B ../tools/verify-skill-upload.py --repo .` → `deployed == worktree and == dist: True`（5/5 逐字节一致） |
| 配置 | `~/.config/toolsmith/projects.json` 已有本项目条目（`owned: true`，skill-only 无 prompt） |
| 备注 | 平台上没有对应 prompt family；`toolsmith-publish status` 因「prompt-first」用不了，本项目的部署校验走上面那个脚本 |

 > 包名 `v0.1.x` 是仓库自己的版本号，平台版本序列是平台自己的（1.0.x），不要硬套。

## Git

首次纳入版本控制：commit `4e88724`（分支 `v0.15-remove-html`，已推送 `origin`）。
