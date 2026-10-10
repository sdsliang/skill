# PROJECT_STATE — report-humanizer-en

Last updated: 2026-10-10 (read this file plus `AGENTS.md` first in a new session)

## One-line status

English report de-AI-flavoring Skill: **published and updated in place on ToolSmith** (platform `1.0.0` / `skill_id 8a872f3a75bf474a97bafad3a0a6fde2`, deployed == worktree == dist); repo packaging version **`v0.1.1`**, machine gate **25/25 OK**. The Chinese twin `../report-humanizer-zh` is in the same state.

## Deliverables

| File | Notes |
|---|---|
| `skill/report-humanizer-en/SKILL.md` | Ten sections: 1 priority / 2 report voice and reader / **3 hard ban: no process narration or self-explanation** / 4 data and provenance / 5 terminology and naming / 6 workflow / 7 pre-delivery checklist / 8 mechanical self-check / 9 when not to act / 10 worked example. Three modes: embedded writing, rewriting, review |
| `skill/report-humanizer-en/references/patterns-en.md` | 26 entries: A structural, B wording and rhythm, C inflation/certainty/sales language, D formatting, E leftovers, F wrong reader, G report-specific, each marked [strong] or [weak] with before/after pairs; closes with how the `S-*`/`W-*` scanner ids relate to these entries |
| `skill/report-humanizer-en/references/naming-bilingual.md` | Naming flow: common knowledge → host-returned paired fields → one dictionary lookup (`report-query-drug` / `pharmcube-mcp-drugBaseLiteCN` / Linking API `drug`) → directional fallback (**English → Chinese keeps the English name; Chinese → English uses pinyin**); other entities and format consistency |
| `skill/report-humanizer-en/references/examples.md` | 3 full-paragraph before/after pairs (pipeline status / trial readout / safety and market access) + "should be kept" boundaries, each with verbatim anchors |
| `skill/report-humanizer-en/scripts/tell-scan.py` | Dependency-free bilingual scanner, 22,558 B (includes `_mixed_notation` → `W-FMT-MIXED`), **byte-identical** to the Chinese copy |
| `evals/test-tell-scan.py` | 25-check machine gate (18 base + 2 examples self-containment + 2 false-positive regressions + 1 packaging + **2 `W-FMT-MIXED` positive/negative cases**) |
| `tools/pack-dist.py` | Deterministic packer → `dist/report-humanizer-en-v0.1.1.zip` (30,765 B / 5 entries / sha256 `ccd56070090d…`), **the attachment ToolSmith takes when creating the skill** |
| `evals/fixtures/` | `ai-flavored.en.md` / `humanized.en.md` / `keep.en.md` / `weak-only.en.md` / `facts.en.json` |

## Verification (local, reproducible)

```
python3 -B evals/test-tell-scan.py  ->  report-humanizer-en machine gate: 25/25 OK
```

- Fixture baseline: `ai-flavored` 16 strong / 12 weak across 19 rules; `humanized` 0/0; `keep` 0 strong / 2 weak (`W-ING-RIDER`, `W-NOMINAL`); `weak-only` 0 strong / 1 weak (`S-INFL-04`).
- Example 2's "must survive verbatim" anchor was `planned Phase 3 study`, which was not literally present in BEFORE; narrowed to `planned Phase 3`. The new anchor check also tolerates sentence-initial capitalisation only.
- **No ToolSmith run of this repo has been made** (it has no project_id and no prompt, so `run` cannot start). Effectiveness was instead measured on the `clinical_result_xp` project as "a real comparison task with this skill attached": **R39 same-day A/B** (attached vs not attached) — prose characters (whitespace removed) 5,112 → 3,868 (**−24%**), mean sentence length 67.3 → 53.7 (−20%), commas `，` 139 → 84 (**−40%**), 12-gram repetition 0.0624 → 0.0447 (−28%), citation markers 4/4 and no fact lost. The scanner flagged `W-BOLD-COUNT` + `W-FMT-MIXED` on the treated report and only `W-BOLD-COUNT` on the control. Details and defects live in `clinical-result-comparison/docs/toolsmith-verification-log.md` under R39.

## Key decisions

1. **Two independent skills (zh / en), not one bilingual skill**: each bundle is self-contained, so `tell-scan.py` is duplicated and asserted byte-identical.
2. **One bilingual scanner file** (`--lang auto|zh|en` plus `_detect_lang`) so the two implementations cannot drift.
3. **Process narration ban sits above everything else** (above the checklist and above any scanner hit); the only exceptions are calibration statements that change how a reader trusts or acts on a result.
4. **Report register, not academic or chat register**: formal voice, nominalization, passive and qualifiers stay; do not make rigorous prose chatty.
5. **Directional naming fallback**: English → Chinese keeps the English name (no transliteration, no invented Chinese name); Chinese → English uses pinyin; never invent.
6. **The scanner is an assistant, not a judge**: only [strong] hits justify an edit, `--weak` is opt-in for gating, and a falling hit count never substitutes for fact checking.
7. **Two scanner false positives were fixed against a real report**: `S-PROC-01` now needs an actor or a completed form (a bare "statistics" style noun no longer fires), and table rows are excluded from both line scanning and document-level counting (bold inside tables is normal). The real R38 report went from 4 strong hits plus a 75-span bold-density signal to 0 strong hits.
8. **Severity alignment with the scanner**: pattern B1 (overused AI words) is [weak] in both the catalogue and `W-AIWORD`, with a note that a cluster of such words in one paragraph already justifies an edit.

## Open items

- [x] **Created on ToolSmith** (2026-10-10: the user uploaded `dist/report-humanizer-en-v0.1.0.zip`, family `5d3eb1c8…`, platform v1.0.0).
- [x] **Repackaged and updated in place** (2026-10-10: `v0.1.1` via `../tools/push-skill-inplace.py`; the platform version label stays `1.0.0`, `is_current=True`, deployed == dist).
- [x] **Effectiveness evidence** (2026-10-10: R39 same-day A/B on `clinical_result_xp`, see above).
- [ ] Confirm the project / skill / directory naming (`report-humanizer-en`).
- [ ] **`W-BOLD-COUNT` threshold**: both real reports (treated and control) hit it once, yet their bold spans are table-header/label bold rather than emphasis abuse. More report samples are needed before deciding whether to weight it by prose lines — logged as "awaiting samples", rule unchanged this round.
- [ ] **Upstream freshness**: this skill references platform tool schemas such as `report-query-drug`; when a platform tool changes version, re-read the schema (there is no dependency manifest inside the bundle, so this is manual today).

### This round's changes (v0.1.1, 2026-10-10)

1. **Notation consistency**: new `D18` (mixed notation) plus a strengthened `B7` connector rule, reported as the **document-level weak** `W-FMT-MIXED` (threshold 1, prose lines only — table rows never counted). Boundary: **symbol form and spacing only, never digits or magnitude**; tables / quotations / citation markers / code / paths / URLs / IDs follow the host contract.
2. **Process-voice boundary**: a statement the host contract *requires* is still written, but as a **material property** ("all sources are abstract-level only") rather than **runtime environment** ("no network in this run, the chain never started").
3. Mirrored edits in `SKILL.md` and `patterns-en.md`; regressions +2 → gate **25/25**; repacked as `v0.1.1`; updated in place on ToolSmith (five guards in `../tools/push-skill-inplace.py`).

## Deployment record (ToolSmith)

| item | value |
|---|---|
| skill name | `report-humanizer-en` |
| skill family | `5d3eb1c8c1cd43a4a6148e07afbe008f` |
| current version | platform v1.0.0 / skill_id `8a872f3a75bf474a97bafad3a0a6fde2` (created 2026-10-10T10:00:32, then **updated in place** the same day to the v0.1.1 content; the label is unchanged) |
| repo version | **v0.1.1** (`dist/report-humanizer-en-v0.1.1.zip`, 30,765 B / 5 entries / sha256 `ccd56070090d…`) |
| deployment check | `python3 -B ../tools/verify-skill-upload.py --repo .` → `deployed == worktree and == dist: True` (5/5 byte-identical) |
| config | entry present in `~/.config/toolsmith/projects.json` (`owned: true`, skill-only, no prompt) |
| note | there is no matching prompt family; `toolsmith-publish status` is prompt-first and refuses here, so this repo's deployment check is the script above |

> The `v0.1.x` in the filename is this repo's own version; the platform keeps its own sequence (1.0.x). Do not conflate them.

## Git

First committed as `4e88724` (branch `v0.15-remove-html`, pushed to `origin`).
