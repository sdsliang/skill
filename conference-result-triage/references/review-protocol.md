# 复核协议（模型逐条判读）

这一步是 skill 的价值所在：**机器能筛出 467 条，只有人能说清哪 30 条值得看。**

## 1. 批次设计（决定性约束）

| 参数 | 值 | 原因 |
|---|---|---|
| 每批条数 | **25** | 单条压缩摘要 ~1300 字符 + 元数据 ≈ 1.6 KB/条，25 条 ≈ 39 KB，**低于工具单文件读取上限（~50 KB）** |
| 分片粒度 | 每片 25 条，独立 JSON 文件 | 一片一文件，避免一次读 300 KB 的行 |
| 索引方式 | **显式顺序 `i`（1..N）** | 不要用 esid 直接下标；池内顺序与批次顺序不一定一致，之前用 esid 索引导致整批错位 |

分片文件结构：

```json
{"items": [{
  "i": 1,
  "bucket": "early",
  "trial": "ABBV-706 ph1",
  "indication": ["小细胞肺癌"],
  "phase": "Phase I",
  "evaluation": "积极",
  "n": 124,
  "randomized": "否",
  "trial_control": null,
  "key_evidence": "是",
  "primary_endpoint": ["ORR"],
  "condensed": "#### Background ... #### Results ... #### Conclusion ..."
}]}
```

`condensed` 的压缩比例（**硬约束，不要整篇塞**）：

- Background：前 320 字符（够拿到药名 + 靶点 + 设计）
- Results：前 760 字符（够拿到主要终点数字）
- Conclusion：前 280 字符

## 2. 每条必须输出六个键

```json
{
  "i": 17,
  "bucket": "pivotal",
  "verdict": "keep",
  "reason": "随机对照 PFS 16.1 vs 6.9 月，HR 0.56",
  "evidence": "PFS was significantly improved with pembro-CT vs pembro (16.1 vs 6.9 months; HR 0.56)",
  "key_numbers": ["PFS 16.1 vs 6.9 mo", "HR 0.56", "OS 50.2 vs 29.9 mo"]
}
```

| 键 | 约束 |
|---|---|
| `i` | **原样抄**，一个字都不能改；改了就无法回填 |
| `bucket` | 按证据强度重判（见 §3），可以覆盖机器分桶 |
| `verdict` | 只能 `keep` / `weak` / `drop` |
| `reason` | ≤40 字，中文，写"为什么"，不写"是什么" |
| `evidence` | **逐字**从该条 `condensed` 摘 1 句，≤120 字符，不改写、不拼接、不翻译 |
| `key_numbers` | 该条摘要里出现过的具体数字，不重算 |

## 3. 分桶重判（按证据强度，不按期别数字）

```
if 主要终点未达 / 未显著 / 无效 / 提前终止（did not meet, no significant,
   terminated, HR 跨 1, p 不显著）:            → failed   （失败优先）
elif 随机对照 + 主要终点达成 + 有临床意义:      → pivotal
elif 单臂 / 无对照 / 剂量爬坡 + 有具体疗效数字:  → early
else: 保留机器分桶
```

实测会被这条规则改判的例子：III 期但 OS 未达的 postMONARCH（pivotal → failed）、Phase II 但有随机对照的 COMPANION-002（机器 pivotal，保持）。

## 4. verdict 的判定标准

| verdict | 条件 |
|---|---|
| `keep` | 数字明确：ORR ≥ 40% / HR ≤ 0.75 / OS 绝对获益 ≥ 3 月 / 明确阴性结论；且能引出具体数字 |
| `weak` | 有疗效数字但样本 < 20、单臂极小样本、关键数字落在未给出的 table 里 |
| `drop` | 只有安全性 / PK / 生物标志物 / HRQoL；或只说"将继续评估"而无结果 |

注意：

- **"数字明确"不等于"值得推荐"**。keep 只是"可以进入定榜候选"，定榜还要看适应症难度、机制新颖度、是否首次公布。
- `weak` 不是"差"，是"凭这篇摘要判不了"。
- 明确阴性（如 ORR 0%、OS HR 1.48）也是 keep —— 失败桶要的就是这种。

## 5. 合并与校验（必做，不做就会静默错位）

合并全部批次后：

1. **条数校验**：判定条数 == 池子条数（ESMO 2026：467）。
2. **i 覆盖校验**：`set(i) == set(range(1, N+1))`，缺一个就重跑对应批次。
3. **evidence 逐字校验**：把 `evidence` 与 `condensed` 都做空白归一 + 小写后做子串匹配。
   - 命中率参考：ESMO 2026 首轮 400/467 = 86%。
   - **未命中的 evidence 不得进入交付物**，改用机器信号或标「待核实」。未命中通常来自表格排版被转写、跨行拼接。
4. **bucket 合法性校验**：`bucket` 只接受 `early|pivotal|failed`；出现 `keep|weak|drop` 说明模型把 verdict 写进了 bucket，回退到机器分桶。

## 6. 任务拆分与模型选择

- 467 条 / 25 = 19 片 → 分 5–6 个子任务，每个 2–4 片。
- 首选稳定可用的模型；实测 `gpt-5.6-terra` 在 6/6 子任务上稳定，grok 系列易 idle timeout，部分 key 对 5.5/5.4 返回 403。
- 子任务提示词必须自带全部规则（不要让它去读 SKILL.md，子任务上下文很贵）。

## 7. 定榜（第二步收敛）

从 206 条 keep 到 30 条，按顺序：

1. **压同质**：同一病种同一机制最多留 2 条（ESMO 2026 早期桶里 SCLC 的 DLL3/SEZ6/B7-H3 ADC 有 5 条 keep，只留最强的 3 条）。
2. **标注数据类型**：首次公布 > 更新 > 亚组/二次分析。更新类进榜的**理由必须是"数据更成熟后结论更硬"**，不能写成"新药"。
3. **补全药物信息**：`trial_abbreviation` 常看不出药名（如 `PERSEE`、`CA017-078`），必须从摘要 Background 段取药名 + 靶点。
4. **写候补**：每桶列 2–4 条"差一位"，方便读者知道边界在哪。
5. **不足 10 条就写不足**，不要用 weak 凑数。
