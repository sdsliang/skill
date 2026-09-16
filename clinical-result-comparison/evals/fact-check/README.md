# `evals/fact-check/` — 必含事实清单与离线打分器

给 `clinical-result-comparison` 补上 autoresearch 范式里唯一缺失的东西：**一个能自动判分的真值标量**。
`docs/autoresearch-iteration-plan.md` §9 定了两层指标，其中成本层（`calls` / `wall_s` / `tokens`）由
`toolsmith-publish run` 直接产出，而质量层原本只有「布尔门」（跑没跑完、有没有产物）。本目录把质量层
从布尔门升级为 `facts_ok / facts_total` 标量：**一份清单写明「这次 run 必须说出哪些事实」，`check.py`
对 run 产物逐条判定**，于是「改动是让它更好还是更坏」第一次有了可比数字。

## 文件

| 路径 | 作用 |
| --- | --- |
| `records/scenario-a.records.json` | 场景 A 的 ground truth：`POST /api/tools/debug` 对 2 个有效 esid 的真实返回（5 行 / `actual_result_count=5`） |
| `records/scenario-b.records.json` | 场景 B：1 个有效 + 1 个不可用 esid 的真实返回（3 行 / `actual=3`） |
| `scenario-a.facts.json` | 场景 A 清单：**30 条 fail 级 + 1 条 warn 级** |
| `scenario-b.facts.json` | 场景 B 清单：**12 条 fail 级 + 1 条 warn 级** |
| `check.py` | 离线打分器（纯标准库，不联网、不调用平台） |
| `mutations.py` | 负向对照 harness：证明每条清单项都能翻 FAIL |

## 用法

```bash
# 对一份已跑完的 run 目录判分（run 目录由 `toolsmith-publish run` 落在
# ~/.local/state/toolsmith-runs/<时间戳>-<tag>/）
python3 check.py --run ~/.local/state/toolsmith-runs/20260916-104943-v2-poll --scenario a
python3 check.py --run ~/.local/state/toolsmith-runs/20260914-174145-b2-refusal --scenario b

python3 check.py --run <dir> --scenario a -v          # 逐条打印
python3 check.py --run <dir> --scenario a --json out.json

# 证明清单本身有牙（需要上面两个 run 目录仍在；可用 MUT_RUN_A / MUT_RUN_B 覆盖）
python3 mutations.py
```

退出码：`0` = 全部 fail 级条目 PASS；`3` = 有 fail 级条目 FAIL；`4` = 输入不可用（run 目录/清单读不到）。
`warn` 级条目只报告、不影响退出码。

打分输出最后一行是标量：

```
SCORE scenario=a facts 30/30 warn 1/1 -> PASS
```

## 清单条目的写法

`scenario-*.facts.json` 的 `items[]`，每条必须有 `id`、`kind`、`severity`（`fail` 默认 / `warn`）、`evidence`。

| `kind` | 字段 | 语义 |
| --- | --- | --- |
| `present` | `surface`, `patterns[]`, `anchors[]?`, `min_count?` | 图案必须出现在该 surface 上；给了 `anchors` 时只认「锚点所在块」内的命中 |
| `absent` | `surface`, `patterns[]` | 图案不得出现（用于「不许把 5 行返回写成 5 条结果」「不许把 `+3.6%` 写成 `−3.6%`」这类反向事实） |
| `attribution` | `surface`, `pairs[{token, owner}]` | 有引注的句/单元格里，token 必须归属其 owner ref |
| `line` | `surface`, `line_regex`, `patterns[]` | 同一行（如 H1 标题）必须同时命中全部图案 |
| `shape` | `op`, 参数 | 结构化断言，见下表 |

`surface` 取值：`report`（`artifacts/output/report.md`）、`citations`、`charts`（`artifacts/visualizations/*.json`）、
`answer`（对话答复文本）、`transcript`（整段轨迹）、`any`（report + answer）。

`shape` 的 op：`artifact_present` / `artifact_absent`、`glob_count`、`citations_keys_exact`、
`citations_entry_key_set`、`citations_matches_record`（对 ground truth record 逐字比，日期按 `YYYY-MM-DD`）、
`citations_distinct`、`chart_envelope`（`id` / `iframe_template` 形状 / `option.type` / `group` / `stack` /
`data_len` / `label` 非空 / `title` 非空）、`chart_values`。

### 锚点归因（`anchors` + `attribution`）

`{{ref_n}}` 把 report 切成**块**（一行、表格行各为一块），块内再切成**单元**：散文按 `。；` 切句
（**只在括号/方括号深度 0 处切**——`（A{{ref_2}}；B{{ref_1}}）` 是一个单元，不然括号内的对比句会被拆开后失去对方的引注，
造成假归因失败），表格行按 `|` 切单元格（单元格没有标记时继承该行的标记）。规则是「**单元里出现的 token，其 owner ref
必须在该单元的引注里**」。落到句/单元格粒度是必须的：像「试验 A＝NCT02729025（依洛尤单抗）{{ref_1}}；
试验 B＝OCEAN(a)-DOSE（NCT04270760）（奥帕司兰）{{ref_2}}」这种一行两试验的写法，按整行判会让
「把 B 的药名写成 A 的药」这类错配逃过检查（`mutations.py` 的 M06 是负向对照，M15 补的是**表格单元格内**的同一类错配）。

无引注的单元不参与归因——这是刻意的，因为标题（H1）天然没有 `{{ref_n}}`；标题的正确性用 `A-T1` 单独断言。

## 反 gaming 约束（硬性）

1. **先有 record，后有清单。** 清单必须自 `POST /api/tools/debug` 返回的真实 record 撰写，**不得**先看
   某次 run 的 report 再回填。否则等于拿产物自证产物，就是 autoresearch issue #599 那类作弊。
   本目录的撰写顺序是：`records/*.json` → 清单 → 再拿 R8 产物判分。
2. **不得回改清单迁就产物。** 判出 FAIL 只能三角分诊：真缺陷 / 清单笔误，二者都要在台账留痕。
3. **`warn` 级不计分。** 记录里读不出来的推断（如剂量↔降幅映射要靠 arms 顺序 + `arm_count` 推）不算事实。

## 已知缺口

- **`iframe_template` 无法离线校验**。envelope 里这个 URL 每次发布都变，且旧构建会被平台删掉；离线只能断言
  形状（`^https://\S+$`），无法断言它与部署端 `config.js` 全等。当前只有在线 `run` 的第 4 条断言覆盖这一层。
- **场景 B 的完整判定只对 v2 run 成立**。v1（SSE）run 目录没有 `messages.json`、`artifacts.zip` 也只有几十字节，
  `check.py` 只能从 `debug-history.json` 兜底重建 `answer` 与 `transcript`（会打一条 `[WARN] surfaces rebuilt`）。
  兜底能覆盖 B 的全部 12 条 fail 级条目（R6 实测 12/12 PASS），但 `transcript` 是重建的，不是原生产物。
- **清单只覆盖 2 个场景（A/B）**，还没有覆盖跨试验 18 esid（场景 C）与同试验多证据状态（场景 D）。
- **`facts_ok/facts_total` 是清单覆盖率，不是事实完备率**：报告可以在全部条目 PASS 的同时漏掉清单没写的事。
  清单的覆盖面靠「对着 record 逐字段过一遍」手工保证。

## 负向对照（清单有牙的证明）

`mutations.py` 把真实 run 目录复制到临时目录、施加定向变异，要求 **① 判分退出码变 3、② 该变异期望的条目
出现在 FAIL 列表、③ 所有变异合起来覆盖清单里每一条 fail 级条目**。

变异手段分两类：`sub()`（按**正则**替换，带替换次数上限断言——上限防的是「字符串里的 `|` 被当成空分支交替、
一次改掉几千处」的静默灾难）与 `sub_lit()`（`re.escape` + `count=1`，用于含 `|` / `{}` 的**字面**锚点）。
当前结果：

```
arm a: flipped 30/30   (15 个变异：改主终点数值、翻转安慰剂符号、抹掉试验登记号、篡改时点、
                        把 ref_1 指向不存在的引用、把标题里的药名写成另一个、
                        在表格单元格里把 B 的药名写成 A 的（M15）、把 2 条写成 5 条、
                        改 citation 标题、让两个 ref 指向同一条记录、改图表数值、多出一张时间轴图、
                        删掉 report、破坏 envelope、删掉 ref_2)
arm b: flipped 12/12   (11 个变异：写出 report/citations、写出图表、改口说「已生成报告」、
                        改掉不可用 esid 名、改掉有效 esid 名、删掉「未返回记录」表述、
                        删掉「不足以构成」表述、删掉请用户核对的表述、给死 esid 编造结论、
                        否认「什么都没写」、抹掉有效记录的药品名)
GATE: PASS
```

基线（未变异）两份清单都必须全 PASS——否则说明清单本身写错了。

**两份独立样本的基线**：R8（`20260916-104943-v2-poll`）与 R9（`20260916-112352-p8-kill`，同一场景 A、
客户端被 `kill -9` 后 `--resume` 补齐）都用 `scenario=a` 跑到 **30/30 PASS**。两个不同 run 同一场景都给满分，
说明清单没有绑定单次运行的措辞（同时也说明它测不出“两轮之间的微小质量差”——那是后来场景 C/D 与人工抽检的事）。
