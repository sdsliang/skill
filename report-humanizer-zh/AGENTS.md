# AGENTS.md — report-humanizer-zh

中文报告「去 AI 味」Skill 项目。工作目录 `/home/xupeipeioo1/apps/skill/report-humanizer-zh`；git 根 `/home/xupeipeioo1/apps/skill`（远端 `git@github.com:sdsliang/skill.git`）。

## 硬性规则

1. **不写过程就是本 skill 的第一条**：SKILL.md 第三节（报告交付物不写工作过程与自我解释）优先级高于所有其它条目与扫描器命中。改这个 skill 时不要削弱它。
2. **`scripts/tell-scan.py` 两份 bundle 必须逐字节一致**（`evals/test-tell-scan.py::t_bundle_parity`）。改 zh 版之后必须同步复制到 `../report-humanizer-en/skill/report-humanizer-en/scripts/tell-scan.py`，反之亦然。
3. **不丢事实是底线**：改 fixtures 或 `references/examples.md` 时，改写后不得出现改写前没有的数值，`facts.zh.json` 的锚点必须两稿俱在（含中文 en dash 写法 `0.48–0.80`）。
4. **反「空产物蒙分」**：改写稿必须是有内容的正文（长度 / 句数 / 相似度阈值），断言不允许被清空或复制原文糊过去。
5. **fixture 命中基线是回归契约**：`ai-flavored` ≥10 强、`humanized` 0/0、`keep` 0 强 / 3 弱、`weak-only` 0 强 / 1 弱。放宽某条规则前先想清楚基线为什么变。
6. **发布是写动作**：往 ToolSmith 写 skill（`push-skill`，含新建 family）**必须先问用户拿到明确同意**。本项目本地编辑、`commit`、`push` 按工作区规则（`apps/skill` 项目 commit/push 免确认；merge/rebase/建删分支仍先问）。
7. **不做 AI 检测规避**：本 skill 只处理表达问题，不判断作者身份、不保证通过任何检测器。别把文案改成「检测器友好」的方向。

## 常用命令

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-zh
python3 -B evals/test-tell-scan.py                                   # 机械闸门，期望 22/22 OK
python3 -B skill/report-humanizer-zh/scripts/tell-scan.py <file>      # 扫描单个文件
diff skill/report-humanizer-zh/scripts/tell-scan.py \
     ../report-humanizer-en/skill/report-humanizer-en/scripts/tell-scan.py   # 应为空
toolsmith-publish status                                             # 发布前后回读（未发布时会报无配置条目）
```

## 改动纪律

- 改规则 → 同步更新 `references/patterns-zh.md` 的条目/严重度与 SKILL.md 第八节的家族表。
- 改严重度或规则表 → 先跑闸门看 fixture 基线是否变化，再决定是否需要改 fixture（不要用改 fixture 的方式掩盖规则退化）。
- 测试文件含连字符，`unittest discover` 导入不到，必须直接 `python3 -B evals/test-tell-scan.py` 运行。
- 脚本顶部已设 `sys.dont_write_bytecode = True`，运行后 `skill/**/scripts/` 下不应出现 `__pycache__`（`t_no_bytecode_residue` 会断言）。

Memory 文件：`PROJECT_STATE.md`（当前状态与验证结果）。改完同步更新。
