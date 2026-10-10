# report-humanizer-zh —— 中文报告去 AI 味（ToolSmith Skill）

把中文分析报告正文写成「懂业务的同事写给决策者看」的文字：结论先行、只讲事实与依据、术语统一、**不写工作过程与自我解释**。

参考来源：`blader/humanizer`（§1–§5 结构级优先）与 `op7418/Humanizer-zh`（31 条中文问题分类，本 skill 重权为报告场景）。两者均以「AI 写作特征清单」为核心，本 skill 在其上加了两条报告专属约束：**不写过程**（SKILL.md 第三节，最高优先级）与**药名中英写法流程**（`references/naming-bilingual.md`）。

## 目录结构

```
report-humanizer-zh/
├── skill/report-humanizer-zh/          # 发布到 TS 的 bundle（自包含）
│   ├── SKILL.md                        # 九节：优先级 / 报告文体 / 硬性禁项 / 数据 / 术语命名 / 流程 / 交付前核对 / 机械自查 / 何时不要改
│   ├── references/patterns-zh.md       # 31 条问题清单（A 结构级 / B 措辞级 / C 中文特有 / D 草稿残留），每条〔强〕〔弱〕+ 报告场景对照
│   ├── references/naming-bilingual.md  # 实体与药名中英写法：常识优先 → 查字典 → 方向性回退
│   ├── references/examples.md          # 3 组整段前后对照 + 「应当保留」边界
│   └── scripts/tell-scan.py            # 零依赖双语扫描器，22,558 B（与英文版逐字节一致）
├── tools/pack-dist.py                  # 确定性打包：dist/report-humanizer-zh-v0.1.1.zip（TS 上传附件 / 原地更新）
└── evals/
    ├── test-tell-scan.py               # 机械闸门 25 项（直接运行，不要用 unittest discover）
    └── fixtures/                       # ai-flavored / humanized / keep / weak-only + facts.json
```

## 本地门禁

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-zh
python3 -B evals/test-tell-scan.py     # 期望：report-humanizer-zh machine gate: 25/25 OK
```

闸门覆盖四件事：扫描器行为（语言判定 / 代码块跳过 / `--allow` / 退出码 / JSON 形状）、fixture 命中形态、**改写不丢事实**（数值不得凭空增加、`facts.zh.json` 的锚点两稿俱在）、**反「空产物蒙分」**（改写稿 ≥200 字符 / ≥3 句 / 含关键事实 / `difflib` 相似度 < 0.9 / AI 味稿必须更长）。另有五项回归：`references/examples.md` 自身（改写后不得出现改写前没有的数值、保留锚点必须两稿俱在）与两处**误报回归**（裸名词「统计/筛选」不得单命中；表格行不参与行级命中与文档级计数），以及打包一致性（`dist` 必须等于工作区重打的包）。

**2026-10-10 新增两类规则**（闸门 23 → 25）：①**排版统一**（`C8` 数字记号混用 / `B7` 连接号）——同一数值全文只允许一种形态（`12 个月` 与 `12 个月`、`0.48–0.80` 与 `0.48-0.80` 不得混用），扫描器按**文档级弱命中** `W-FMT-MIXED`（阈值 1，只统计正文行、表格行不计）报出；边界是**只统一符号形态与空格，数值与位数一字不动**，表格 / 引文 / citation 标记 / 代码 / 路径 / URL / ID 按宿主契约。②**过程口吻措辞边界**：宿主契约**要求**写的声明照写，但**写成材料属性**（「本批材料均为摘要级、无全文记录」可以）而不是运行环境（「本次运行无外网、链路未能发起」删）。

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

## 打包与上传（TS 建 skill 用附件）

TS 上创建 skill 需要**上传压缩包附件**，所以包必须能一条命令重打、且与工作区一致：

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-zh
python3 -B tools/pack-dist.py            # 生成 dist/report-humanizer-zh-v0.1.1.zip
python3 -B tools/pack-dist.py --check    # 期望 IDENTICAL
```

- 包内 5 个成员（`SKILL.md` + `references/*.md` + `scripts/*.py`），前缀 `report-humanizer-zh/`，与 `SKILL.md` 的 `name:` 一致（平台按这个校验）。
- 打包确定性：固定时间戳、Unix creator、0644、deflate 6——工作区不变则字节不变，`toolsmith-publish status` 才能拿它对账。
- `evals/test-tell-scan.py::t_dist_zip_is_current` 会把「dist 与工作区是否一致」当闸门，改了 bundle 必须重打包，否则测试红。
- 从 Windows 浏览器上传时用 UNC 路径：

```
\\wsl.localhost\Ubuntu-22.04\home\xupeipeioo1\apps\skill\report-humanizer-zh\dist\report-humanizer-zh-v0.1.1.zip
```

> 不要用「复制到 `C:\...` 再上传」的方式绕过 UNC：公司机器有 DLP 透明加密，Windows 侧落盘可能变成密文，传上去就是坏包。走 UNC 直接读 WSL 明文。

## 版本与发布

**已发布并在 TS 原地更新（2026-10-10）**：平台 `skill_id d7fed181277045dd9f28989b9cb4acb5`、family
`407d8fb6ad5045dda22586448c4e5df0`、平台版本 `1.0.0`（平台自己的序列）——当前线上内容 = 本仓库
`dist/report-humanizer-zh-v0.1.1.zip`（**28,406 B / 5 entries / sha256 `7264e94eabdf…`**）。

- 发布路径：本项目**只有 Skill bundle、没有系统提示词**，所以不走 `publish`（那是 prompt + skill 联合发布），
  走**原地更新**脚本（`POST /api/skills/update_skill_file`，传全量 bundle zip、保 `skill_id` 与版本号）：
  ```bash
  cd /home/xupeipeioo1/apps/skill/report-humanizer-zh
  python3 -B ../tools/push-skill-inplace.py --check    # 五道护栏预检，只读
  python3 -B ../tools/push-skill-inplace.py            # 真上传：dist 一致性 / name 一致 / owned / owner / 回读比对
  python3 -B ../tools/verify-skill-upload.py --repo .  # 只读校验：部署 == 工作树 == dist
  ```
- `--version` 语义：**默认原地更新当前版本（版本号标签不变、内容被替换）**；要留历史版本才另开新版本。
- 打包版本号 `v0.1.x` 是**本仓库自己的版本号**，与平台 skill 版本序列（`1.0.x`）无关，靠内容哈希对齐（`verify-skill-upload.py`）。
- 内容变更即 bump 打包版本并**删掉旧 zip**（本项目 dist 只留当前包；对比结果项目才保留历史包）。
- 版本沿革：`v0.1.0`（首建）→ **`v0.1.1`**（2026-10-10：排版统一规则 + 文档级弱命中 `W-FMT-MIXED` + 过程口吻边界，见 `PROJECT_STATE.md`）。

Memory: `AGENTS.md`、`PROJECT_STATE.md`。Git 根 = `/home/xupeipeioo1/apps/skill`（`git@github.com:sdsliang/skill.git`）。
