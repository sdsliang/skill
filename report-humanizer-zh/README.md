# report-humanizer-zh —— 中文报告去 AI 味（ToolSmith Skill）

把中文分析报告正文写成「懂业务的同事写给决策者看」的文字：结论先行、只讲事实与依据、术语统一、**不写工作过程与自我解释**。

参考来源：`blader/humanizer`（§1–§5 结构级优先）与 `op7418/Humanizer-zh`（31 条中文问题分类，本 skill 重权为报告场景）。两者均以「AI 写作特征清单」为核心，本 skill 在其上加了两条报告专属约束：**不写过程**（SKILL.md 第三节，最高优先级）与**药名中英写法流程**（`references/naming-bilingual.md`）。

## 目录结构

```
report-humanizer-zh/
├── skill/report-humanizer-zh/          # 发布到 TS 的 bundle（自包含）
│   ├── SKILL.md                        # 九节：优先级 / 报告文体 / 硬性禁项 / 数据 / 术语命名 / 流程 / 交付前核对 / 机械自查 / 何时不要改
│   ├── references/patterns-zh.md       # 30 条问题清单（A 结构级 / B 措辞级 / C 中文特有 / D 草稿残留），每条〔强〕〔弱〕+ 报告场景对照
│   ├── references/naming-bilingual.md  # 实体与药名中英写法：常识优先 → 查字典 → 方向性回退
│   ├── references/examples.md          # 3 组整段前后对照 + 「应当保留」边界
│   └── scripts/tell-scan.py            # 零依赖双语扫描器，21,351 B（与英文版逐字节一致）
└── evals/
    ├── test-tell-scan.py               # 机械闸门 22 项（直接运行，不要用 unittest discover）
    └── fixtures/                       # ai-flavored / humanized / keep / weak-only + facts.json
```

## 本地门禁

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-zh
python3 -B evals/test-tell-scan.py     # 期望：report-humanizer-zh machine gate: 22/22 OK
```

闸门覆盖四件事：扫描器行为（语言判定 / 代码块跳过 / `--allow` / 退出码 / JSON 形状）、fixture 命中形态、**改写不丢事实**（数值不得凭空增加、`facts.zh.json` 的锚点两稿俱在）、**反「空产物蒙分」**（改写稿 ≥200 字符 / ≥3 句 / 含关键事实 / `difflib` 相似度 < 0.9 / AI 味稿必须更长）。另有四项回归：`references/examples.md` 自身（改写后不得出现改写前没有的数值、保留锚点必须两稿俱在）与两处**误报回归**（裸名词「统计/筛选」不得单命中；表格行不参与行级命中与文档级计数）。

fixture 命中基线（回归必须复现）：

| 文件 | 强命中 | 弱命中 |
|---|---|---|
| `ai-flavored.zh.md` | ≥10（实测 14） | — |
| `humanized.zh.md` | 0 | 0 |
| `keep.zh.md` | 0 | 3（`W-AS-WITH`、`W-PASSIVE`、`W-VERBNOUN`） |
| `weak-only.zh.md` | 0 | 1（`S-INFL-04`） |

## 扫描器用法

```bash
python3 -B skill/report-humanizer-zh/scripts/tell-scan.py <file.md> [--lang auto|zh|en]
        [--json] [--weak] [--allow RULE,RULE]
```

退出码：`0` 无强命中 / `3` 有强命中（可当闸门）/ `2` 用法或文件错误。定位是**助手不是判分器**：命中不等于必须改，没命中不等于没问题。

## 版本与发布

- **未发布到 ToolSmith**。发布前需要：(1) 用户在 TS 侧建 skill family；(2) 在 `~/.config/toolsmith/projects.json` 增加本项目条目（键 = `/home/xupeipeioo1/apps/skill/report-humanizer-zh`，`owned: true`）；(3) 用户明确授权后执行 `toolsmith-publish push-skill`。
- 本项目**只有 Skill bundle，没有系统提示词**，因此不走 `publish`（那是 prompt + skill 联合发布）。
- `scripts/tell-scan.py` 与 `../report-humanizer-en/skill/report-humanizer-en/scripts/tell-scan.py` **必须逐字节一致**（`t_bundle_parity` 断言）；改一处必须同步复制另一处。

Memory: `AGENTS.md`、`PROJECT_STATE.md`。Git 根 = `/home/xupeipeioo1/apps/skill`（`git@github.com:sdsliang/skill.git`）。
