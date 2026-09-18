# 固定三组线上回归

用户于 2026-09-18 指定：以后每次 Skill 或系统提示词迭代发布后，固定执行 `evals/fixed-regression-inputs.json` 的全部三组；分别为 4、18、14 条选中结果。它们是独立固定组，不覆盖历史 A/B 评分基线，也不强套 A/B 的事实分数。已有拒绝测试仍用于其独立契约。

## 每轮步骤

1. 发布前核对目标配置、deps、status；获得当次 TS 发布授权，原地更新并回读一致。
2. 保存原始 JSON 输入。按 `docs/test-input-resolution.md` 只读 SQL 解析真实 `_id`，保留请求/返回/映射/缺失项。只转换实际命中项，不猜前后缀，不悄悄缩小范围。
3. 三组分别生成 prompt 文件，保留用户原句和选择顺序，逐个真实 `_id` 替换；使用 `toolsmith-publish run --web --prompt-file <file> --tag r<n>-fixed-<group> --poll-interval 8`。每组独立线程、独立 R 记录。
4. 保留 verification、工具完整回执、报告、引用、图表和成本。运行断言通过仅说明输出契约通过。
5. 人工核查所有选中记录覆盖、同试验/跨试验关系、关键结果与时间/分析集、设计字段与原文的一致性、冲突的双来源披露、未确认项标注，以及正文/表格/图表标签的一致性。论文双盲与登记多角色盲法不自动判抽取错误。
6. 写入台账，区分我方可改项和平台侧现象；任何失败原样保留，重跑另开 R，不改历史结论。

## 首轮发布和输入核验

2026-09-18 原地更新：prompt v1.6（55,885 B，SHA 前缀 `50b870badd16`），skill v1.0.7（skill_id `ad75ec2c44334f389a0394895a47b765`），对应仓库 v0.15；dist SHA `e91f474fa80b450b5b18b72acc93e9dbc12f0a7bab181a0ae77d70da994ef887`。平台回读 prompt 一致、19/19 技能文件一致；上游无变化。

本轮证据目录 `~/.local/state/toolsmith-runs/fixed-regression-20260918/`。32 个不重复输入全部按 `_id OR extra_esid` 命中，全部原输入已等于真实 `_id`，无需替换。SQL 响应 `data` 实际 32 行；`actual_result_count` / `total_result_count` 却为 0，计数使用实际数据，不使用这两个元数据计数字段。

R27/R28/R29 分别为 fixed-1/fixed-2/fixed-3。最终验收见 `docs/toolsmith-verification-log.md`。
