# R57 — per-ref fact-row sharding (①) + facts field subtraction (②) — 2026-10-12

**Verdict: FAIL as an improvement — ① was never exercised (0 `task` calls in 3/3 runs), ② was**
**adopted 100 % but is below the measurement floor. Wall and `output_tokens` medians both came out**
**slightly worse, inside the ±20–40 % same-input variance.**

Two hypotheses were on the table after R55/R56:

* **① per-ref fact-row sharding.** R56 established that subagents *do* run concurrently (model
  generation) while the sandbox `execute` lane is a single platform-wide channel; R56-b measured
  1.38–1.69× on a pure-generation payload. The lever R55-3 named (45 facts × 15 fields hand-written,
  ≈1/3 of a run's reasoning) is exactly what sharding would parallelise.
* **② facts field subtraction.** Measured over three R55 runs, `source_file` was 13 % of
  `facts.json` and `version+population+assessment+timepoint` another 11 %. `build_ledger.py` already
  derives `source_file` from `ref` and defaults the other four, so the only change needed is
  permission to omit them.

The *motivation* for the round was another finding: `SKILL.md` told the model to run
`build_ledger.py --scaffold` once and edit the rows it emits — and **the model never did**
(0/33 ids reused, `value`+`endpoint` matched 0/51 final rows, the last ref missing) while paying one
`execute` call plus a full read of the 33-row file. So ② also **deleted that instruction**.

## Changes (all local, then published in place)

| Surface | Change |
|---|---|
| `scripts/merge_ref_facts.py` (new) | deterministic merge of `work/facts.ref_*.json` → `work/facts.json`; checks the split (unknown ref, duplicate fact `id` / record `ref` across shards, empty shard, uncovered-ref `WARN`); exit 3 + nothing written on findings |
| `evals/scripts/test-merge-ref-facts.py` (new) | 16 tests, incl. "merged file compiles through `build_ledger.py` and gets the derived `source_file`" |
| `references/input-and-extraction.md` | + shard recipe (≥3 refs, one message, explicit `timeout_seconds`) + "write only what the scripts cannot derive" |
| `references/input-contract.md` | Status / Chunking / Constraints rewritten on measured numbers; new *Delegating the fact rows* section; new *Measured boundaries of the `task` tool* table |
| `SKILL.md` | item 9 (scripts), `:41` delegation section rewritten as concurrent fact-row sharding, `facts[]` field contract now omission-permitted |
| `references/toolbox.md` | new `## 3. merge_ref_facts.py`; `## 2a.` scaffold section demoted to "still exists, the workflow does not use it" with the measured adoption numbers (code + 9 tests kept); 5 other scaffold references removed |
| `system-prompts/…-v0.16.md` | workflow step 1 delegation pointer; `## Subagent delegation` trigger/chunking/`Serial expectation` → *Fact rows, one subagent per ref* + *Concurrency and the one lane*; `facts[]` contract |
| `tools/pack-dist.py` | `EXPECTED` 26 → 27, docstring |

Local gates: `test-skill-scripts.py` 62 · `test-check-report.py` 25 · `test-build-ledger-scaffold.py` 9 ·
`test-merge-ref-facts.py` 16 · `test-render-facts.py` 28 · `test_regressions.py` 35 ·
`test-runner.py` 41 · `test_pack_dist.py` 5 · `test_replay_run.py` 14 · node 8+8 ·
`mutations.py` arm a 44/44, arm b 12/12 — all green.

## Publication (in place, 2026-10-12)

`toolsmith-publish deps` → `DEPS: unchanged since the recorded baseline`.
`toolsmith-publish publish`:

* prompt **v1.8, 79,218 B, sha `f293fb45f39e`** (`== local`; previous 76,477 B / `c4bb1a7b3ee1`)
* skill **v1.0.9**, dist `multi-clinical-result-comparison-v0.16.zip` **161,148 B / 27 entries / sha `a4a6f9de9d1b`**,
  `HTTP 200`, `files=0` (in-place), read-back `entries=27 identical=27 differing=0`
* `status`: **in sync — deployed matches the worktree**
* commit `b200eb6`

## Runs

Fixed input `/tmp/prompt-r53-4.txt` (4 esids → **4 refs → crosses the ≥3-ref shard threshold**),
model `DeepSeek Flash`, web off.

### First batch died mid-flight (platform incident, not the change)

`20261012-182425-r57-shard-{1,2,3}` (threads `3f21ca05…`, `526a8410…`, `e72ec310…`) all froze at
~264 s: `status=idle`, steps stuck (12 / 24 / 9), **no `/timing` `completed_at` row**, two
`GET /api/threads/…/messages → Connection refused` gaps each. Every thread was waiting on an
`execute` result, and **`task` calls were still 0 in all three**, so the change was not in play.
`run --resume <thread>` re-attached without re-POSTing but the steps never advanced again → the
turns really were dead. Discarded and re-run (tag `r57b-*`). Ticket: Obsidian
`TS并发turn同时卡死-idle无timing-row-resume也救不回.md`.

### Second batch — measured

| run | wall (polled / server) | out_tokens | reasoning | steps | `task` | facts rows | facts.json |
|---|---:|---:|---:|---:|---:|---:|---:|
| `20261012-183501-r57b-shard-1` | 465.5 / 448.1 s | 81,344 | 63,194 | 24 | **0** | 56 | 17,444 B |
| `20261012-183501-r57b-shard-2` | 384.9 s | 60,599 | 44,529 | 20 | **0** | 55 | 20,458 B |
| `20261012-183501-r57b-shard-3` | 445.9 s | 78,248 | 62,868 | 23 | **0** | 48 | 15,846 B |

Quality: **21 PASS / 1 FAIL in each**, the single FAIL being the known platform-side
`tool_results receipts archived` assertion. 4 `records[]` and a complete appendix/chart in each run.

## Verdict ① — not exercised

`tool-task` count = **0 / 0 / 0**. Only one run (shard-1) even considered it, and its reasoning
shows **our own document set talked it out of it** (16 fragments weighing the trade-off):

> "4 esids, and 3+ refs → fact rows delegation is suggested… The guidance says 'when 3 or more refs
> are selected you should delegate the fact rows one subagent per ref'. But also **'Prefer
> straight-through scripting before delegating'** … it's a **should, not a must** ('never
> mandatory' per skill) … **4 subagent round-trips (which also share the single execute lane)** …
> doing it myself is cheaper and more accurate. **The benefit is context bounding — but my context
> already holds the sources.**"

Three things follow, and they are the real R57 finding:

1. The `## Subagent delegation` section contains a **competing rule** ("Try straight-through
   scripting before delegating… decide in one line and move on") that the model applied to the
   fact rows even though it is written about the *pull*.
2. The new rule is phrased as permission ("is a real speed-up", "needs 3 or more refs"), while the
   old text still says delegation is "never a reason to shrink the source set / never mandatory".
   A permission loses to a cost.
3. **The "one lane" bullet I added this round was read as a price**, not as information.

So the instruction produced **reasoning churn and zero behaviour change** — the same failure mode as
the scaffold instruction it was meant to replace. The honest conclusion is *not* "ask harder": at
4 refs of abstract-sized sources the model's judgement may well be right (facts are ~10 % of turn
output; splitting that cannot beat 10 %).

## Verdict ② — adopted, and measurable in the artefact, not in the totals

`source_file` omitted **159/159 rows** (56/56, 55/55, 48/48); the four defaulted fields omitted on
22–49 rows each, per run. Serialised row cost:

| | rows | B/row (as written) | B/row (had the omitted fields been written) | saved |
|---|---:|---:|---:|---:|
| R55 baseline sub-1/2/3 | 36 / 51 / 55 | 478 / 482 / 475 | — | 0 % |
| R57 shard-1/2/3 | 56 / 55 / 48 | 313 / 337 / 299 | 423 / 445 / 400 | **25.9 / 24.2 / 25.2 %** |

The facts block shrank **~25 %** (≈4–7 KB ≈ 1.5–2.5 K output tokens of a 60–81 K turn) — exactly the
~3 % the pre-registered arithmetic predicted, i.e. below the noise floor by construction.

The instruction deletion worked too: **`--scaffold` invoked 3/3 times before, 0/3 times now**, and
the candidate-file read (`work/facts.candidates.json`) disappeared.

## Metrics vs baseline

Baseline = the 8 runs on this exact prompt with content = current minus R57 (R53-doc-4/4b/4c, R54-base-1/2,
R55-sub-1/2/3). The tightest baseline is the immediately preceding three (R55-sub).

| metric | baseline (n=8) | tight baseline (n=3) | R57 (n=3) | Δ (n=8) | Δ (tight) |
|---|---:|---:|---:|---:|---:|
| wall median | 413.8 s | 405.4 s | **445.9 s** | **+7.8 %** | **+10.0 %** |
| wall mean | 401.5 s | 405.4 s | 432.1 s | +7.6 % | +6.6 % |
| out_tokens median | 70,983 | 70,187 | **78,248** | **+10.2 %** | **+11.5 %** |
| out_tokens mean | 68,599 | 68,592 | 73,397 | +7.0 % | +7.0 % |
| reasoning median | 50,851 | 51,147 | 62,868 | +23.6 % | +23.0 % |
| steps | 17–22 | 20–22 | 20–24 | — | — |

Guardrail was out_tokens **< +10 %** (threshold 78,081 on the n=8 baseline) → **missed by 167 tokens**
on the median, i.e. a coin flip, not a signal. Wall-clock target (an improvement) → **not met**;
the delta is well inside the ±20–40 % same-input spread we documented in R55.

Tool composition moved in the direction the field subtraction predicted only for `read_file`
(10–12 → 7–10) while `execute` rose (13–14 → 17–21) — consistent with "the facts block got smaller
but the run did more scripted passes", not with a cheaper pipeline.

## What this round actually settles

* **① remains untested.** No wall-clock claim can be made for or against sharding: the model does not
  delegate at 4 refs, and its stated reason (`context already holds the sources`, facts are a small
  block) is consistent with the arithmetic.
* **② is confirmed as a real but small subtraction** (25 % of the facts block) and, more usefully,
  **removed a step the model was paying for and not using** (scaffold: 3/3 → 0/3).
* **Adding a permission does not beat an existing cost sentence.** Any further attempt at ① has to
  *delete* the competing "prefer straight-through scripting" text first, or it will fail the same way.
* The measurement floor is unchanged: **n=3 medians cannot resolve <20 %**, so ② could never have
  been scored on tokens; only ① (wall) was worth testing, and it did not run.

## Next round (proposal, needs approval)

R58 should be a **subtraction**, not a re-phrasing: drop the fact-row delegation recipe (SKILL.md,
`references/input-contract.md`, system-prompt workflow step 1 + *Fact rows* bullet) and keep what the
round did establish — `merge_ref_facts.py` (working, 16 tests), the measured `task` boundaries table,
and the concurrent-not-serial correction. If ① is ever retried, the condition should be
source-class-based (`registration-class` payloads, ≥6 refs) and the competing sentence must go first.
