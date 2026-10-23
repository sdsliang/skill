# 复核协议（模型逐条判读）

这一步是 skill 的价值所在：**机器能筛出 467 条，只有人能说清哪 30 条值得看。**

## 1. 批次设计（决定性约束）

| 参数 | 值 | 原因 |
|---|---|---|
| 每批条数 | **15** | 单条压缩摘要约 2.5 KB（Results 不再截断）+ 元数据，15 条约 37 KB，**低于工具单文件读取上限（~50 KB）** |
| 分片粒度 | 每片 15 条，独立 JSON 文件 | 一片一文件，避免一次读 300 KB 的行 |
| 索引方式 | **显式顺序 `i`（1..N）** | 不要用 esid 直接下标；池内顺序与批次顺序不一定一致，之前用 esid 索引导致整批错位 |

分片文件结构：

```json
{"items": [{
  "i": 1,
  "bucket": "early",
  "abstract_id": "5RO",
  "presentation": "Rapid Oral",
  "trial": "ABBV-706 ph1",
  "indication": ["小细胞肺癌"],
  "phase": "Phase I",
  "evaluation": "积极",
  "n": 124,
  "randomized": "否",
  "trial_control": null,
  "key_evidence": "是",
  "primary_endpoint": ["ORR"],
  "refractory": ["TOP1i-ADC 耐药", "既往 ≥2 线"],
  "table_only": false,
  "condensed": "#### Background ... #### Results ... #### Conclusion ...",
  "summary": "..."
}]}
```

`condensed` 的压缩比例：

- Background：前 320 字符（够拿到药名 + 靶点 + 设计）
- **Results：全文，不截断**（这是 v0.2 最重要的一条）
- Conclusion：前 280 字符
- `summary`（`clinical_result_summary`）作为**独立字段**并列给出，不要拼进 `condensed`

### 1.1 为什么 Results 不能截断

v0.1 把 Results 截到 760 字符，实测代价：

- ESMO 2026 摘要 Results 段中位数 **956 字符**，最长 2094 —— **52%（338/646）的摘要把关键数字印在 760 之后**；
- 低分条目里有 260 条 Results > 760，其中 **117 条（45%）在截断点之后还有带百分比的疗效数字**，只有 4 条是真的「数字只在未展示的表里」；
- 直接导致两名内部专家推荐被误判为 weak：HS-20122 的 `52.5%` 在 Results 偏移 919，CM518D1 的 `33.3%` 在偏移 851。

整篇摘要才 ~2 KB，截断没有收益，只有损失。**宁可多读，不要丢数字。**

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
| `reason` | ≤40 字，中文，写"为什么"，不写"是什么"；人群难度档必须写进去 |
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
| `keep` | 数字明确：ORR ≥ 40%（后线/耐药 ≥ 25%）/ HR ≤ 0.75 / OS 绝对获益 ≥ 3 月 / 明确阴性结论；且能引出具体数字 |
| `weak` | 有疗效数字但样本 < 20、单臂极小样本、关键数字落在未给出的 table 里；或 ORR 在一般人群 25–40% 且无其它支撑 |
| `drop` | 只有安全性 / PK / 生物标志物 / HRQoL；或只说"将继续评估"而无结果 |

注意：

- **ORR 门槛按人群难度分档，不是一把尺**：一线/未治疗 ≥40%，后线（≥2 线）或明确耐药人群 ≥25%。降档的**前提是 `reason` 里写明人群**（几线、既往用过什么），只降门槛不写人群 = 放宽标准。
- **“数字明确”不等于“值得推荐”**。keep 只是"可以进入定榜候选"，定榜还要看适应症难度、机制新颖度、是否首次公布、**报告形式**。
- `weak` 不是"差"，是"凭这篇摘要判不了"。
- 明确阴性（如 ORR 0%、OS HR 1.48）也是 keep —— 失败桶要的就是这种。
- **口头报告不等于数据更好**，但口头报告 + 强数字是双重信号；只有口头没数字不能 keep。

## 5. 合并与校验（必做，不做就会静默错位）

合并全部批次后：

1. **条数校验**：判定条数 == 池子条数（ESMO 2026 v0.2：532）。
2. **i 覆盖校验**：`set(i) == set(range(1, N+1))`，缺一个就重跑对应批次。
3. **evidence 逐字校验**：把 `evidence` 与 `condensed` 都做空白归一 + 小写后做子串匹配。
   - 命中率参考：ESMO 2026 首轮 400/467 = 86%；v0.2（532 条 / 36 批）**532/532 = 100%**，`reason` 超 40 字的 0 条。
   - 首轮命中率低于 95%  практически всегда 是分片时 `condensed` 与判定时读到的不一致（截断、字段名写错、改用了 `summary`），先查这个再查模型。
   - **未命中的 evidence 不得进入交付物**，改用机器信号或标「待核实」。未命中通常来自表格排版被转写、跨行拼接。
4. **bucket 合法性校验**：`bucket` 只接受 `early|pivotal|failed`；出现 `keep|weak|drop` 说明模型把 verdict 写进了 bucket，回退到机器分桶。

## 6. 任务拆分与模型选择

- 532 条 / 15 = 36 片 → 分 6–7 个子任务，每个 5–6 片。
- 首选稳定可用的模型；实测 `gpt-5.6-terra` 在 6/6 子任务上稳定，grok 系列易 idle timeout，部分 key 对 5.5/5.4 返回 403。
- 子任务提示词必须自带全部规则（不要让它去读 SKILL.md，子任务上下文很贵）。
- **分片文件里必须自带正文**。ESMO 2026 首轮踩过：池子条目只有 `abstract_text`，`condensed` 字段是复核批次阶段才拼出来的；直接拿 pool.json 切片 → 6/6 子任务收到 `condensed = null` → 4 个子任务拒绝判定、2 个改用 `summary` 凑数（keep 率从 24% 掉到 3%）。**切片要基于 `review.jsonl` 的 batch item**（含 `background` / `results` / `summary`），落盘前断言 `all(it['condensed'] for it in items)`。
- **单文件体积 ≤ 40 KB**。36 片实测 max 40,804 B / avg 35,964 B —— 再大就顶到 `read` 的 50 KB 上限。

## 7. 定榜（第二步收敛）

从 keep 池到 30 条，按顺序：

1. **压同质**：同一病种同一机制最多留 2 条（ESMO 2026 早期桶里 SCLC 的 DLL3/SEZ6/B7-H3 ADC 有 5 条 keep，只留最强的 3 条）。
2. **标注数据类型**：首次公布 > 更新 > 亚组/二次分析。更新类进榜的**理由必须是"数据更成熟后结论更硬"**，不能写成"新药"。
3. **标出报告形式**：每条写「口头 / 快速口头 / 壁报 / 电子壁报」。同分时口头优先。
4. **补全药物信息**：`trial_abbreviation` 常看不出药名（如 `PERSEE`、`CA017-078`），必须从摘要 Background 段取药名 + 靶点；会议库已直接给出 `drug` / `target` / `moa` 字段，优先用它。
5. **跑同资产历史对照**：`scripts/history_for.py --pool pool.json` 拉每个药历次会议的数据，进榜条目必须看一遍。ESMO 2026 实证：SYS6043 从 ASCO 2026 到 ESMO 2026 从 64.0% 降到 45.7%（样本 502 → 137），9MW2821 从 ESMO 2023 的 38.5% 一路降到 30.0% —— 这种趋势单次会议快照看不出来。
6. **写候补**：每桶列 2–4 条"差一位"，方便读者知道边界在哪。
7. **不足 10 条就写不足**，不要用 weak 凑数。

**定榜排序不能只靠机器 sort。** 池子按 `(presentation_rank, -n)` 排，那是**为读的次序**，不是推荐次序。ESMO 2026 实测：7 条专家选择在机器序里排名为 2 / 19 / 27 / 72 / 101（另有 2 条判 weak 未入 keep），两条壁报 `1029P`、`2567P` 因 n 小被压到 72 和 101 名 —— 壁报档里 n 大的平庸研究一定压过 n 小的耐药人群研究。所以定榜由人（或复核模型读完全部 keep 后）排序，脚本只负责按给定顺序渲染（`scripts/make_watchlist.py` 就是只渲染、不排序）。

**定榜要交付三件**：`judgements.csv`（全量判定，机器桶与复核桶并排）· `watchlist.csv` / `watchlist.md`（定榜）· `history.md`（同资产历次读数）。
