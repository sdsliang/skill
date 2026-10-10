# PROJECT_STATE — report-humanizer-en

Last updated: 2026-10-09 (read this file plus `AGENTS.md` first in a new session)

## One-line status

English report de-AI-flavoring Skill: **content and machine gate complete and green** (20/20); **not yet published to ToolSmith** (needs user authorisation and a platform-side skill family). The Chinese twin `../report-humanizer-zh` is in the same state.

## Deliverables

| File | Notes |
|---|---|
| `skill/report-humanizer-en/SKILL.md` | Ten sections: 1 priority / 2 report voice and reader / **3 hard ban: no process narration or self-explanation** / 4 data and provenance / 5 terminology and naming / 6 workflow / 7 pre-delivery checklist / 8 mechanical self-check / 9 when not to act / 10 worked example. Three modes: embedded writing, rewriting, review |
| `skill/report-humanizer-en/references/patterns-en.md` | 26 entries: A structural, B wording and rhythm, C inflation/certainty/sales language, D formatting, E leftovers, F wrong reader, G report-specific, each marked [strong] or [weak] with before/after pairs; closes with how the `S-*`/`W-*` scanner ids relate to these entries |
| `skill/report-humanizer-en/references/naming-bilingual.md` | Naming flow: common knowledge → host-returned paired fields → one dictionary lookup (`report-query-drug` / `pharmcube-mcp-drugBaseLiteCN` / Linking API `drug`) → directional fallback (**English → Chinese keeps the English name; Chinese → English uses pinyin**); other entities and format consistency |
| `skill/report-humanizer-en/references/examples.md` | 3 full-paragraph before/after pairs (pipeline status / trial readout / safety and market access) + "should be kept" boundaries, each with verbatim anchors |
| `skill/report-humanizer-en/scripts/tell-scan.py` | Dependency-free bilingual scanner, 21,351 B, **byte-identical** to the Chinese copy |
| `evals/test-tell-scan.py` | 23-check machine gate (18 base + 2 examples self-containment + 2 false-positive regressions + 1 packaging) |
| `tools/pack-dist.py` | Deterministic packer → `dist/report-humanizer-en-v0.1.0.zip` (29,002 B / 5 entries / sha `2f1e5b515f16`), **the attachment ToolSmith takes when creating the skill** |
| `evals/fixtures/` | `ai-flavored.en.md` / `humanized.en.md` / `keep.en.md` / `weak-only.en.md` / `facts.en.json` |

## Verification (local, reproducible)

```
python3 -B evals/test-tell-scan.py  ->  report-humanizer-en machine gate: 23/23 OK
```

- Fixture baseline: `ai-flavored` 16 strong / 12 weak across 19 rules; `humanized` 0/0; `keep` 0 strong / 2 weak (`W-ING-RIDER`, `W-NOMINAL`); `weak-only` 0 strong / 1 weak (`S-INFL-04`).
- Example 2's "must survive verbatim" anchor was `planned Phase 3 study`, which was not literally present in BEFORE; narrowed to `planned Phase 3`. The new anchor check also tolerates sentence-initial capitalisation only.
- No ToolSmith run has been performed yet (not published). A real `toolsmith-publish run` with an R-number log entry is required after publishing.

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

- [x] **Created on ToolSmith**: the user uploaded `dist/report-humanizer-en-v0.1.0.zip` on 2026-10-10 (family `5d3eb1c8…`, platform v1.0.0); the deployed bundle was verified byte-for-byte against the worktree and the dist zip.
- [ ] **How to ship later updates**: either (a) re-upload a fresh zip in the ToolSmith UI (`python3 -B tools/pack-dist.py`, then pick the file over the UNC path from the README), or (b) patch the runner so `push-skill` accepts a skill-only project (today `assert_owned_targets` insists on reading a prompt family and dies). The runner is ours to change, but that needs a backup, `py_compile`, the zero-network gate and an O-entry in the ledger, plus the user's go-ahead.
- [ ] Confirm the project / skill / directory naming (`report-humanizer-en`).
- [ ] This skill has **never been run on ToolSmith**: `toolsmith-publish run` needs a project_id and a prompt, and this repo has neither. Real-run verification would first require attaching it to a platform project.

## Deployment record (ToolSmith)

| item | value |
|---|---|
| skill name | `report-humanizer-en` |
| skill family | `5d3eb1c8c1cd43a4a6148e07afbe008f` |
| current version | platform v1.0.0 / skill_id `8a872f3a75bf474a97bafad3a0a6fde2` (uploaded 2026-10-10T10:00:32) |
| repo version | v0.1.0 (`dist/report-humanizer-en-v0.1.0.zip`, 29,002 B / 5 entries / sha `2f1e5b515f16`) |
| deployment check | `python3 -B ../tools/verify-skill-upload.py --repo .` → `deployed == worktree and == dist: True` (5/5 byte-identical) |
| config | entry present in `~/.config/toolsmith/projects.json` (`owned: true`, skill-only, no prompt) |
| note | there is no matching prompt family; `toolsmith-publish status` is prompt-first and refuses here, so this repo's deployment check is the script above |

> The `v0.1.0` in the filename is this repo's own version; the platform keeps its own sequence (1.0.x). Do not conflate them.

## Git

First committed as `4e88724` (branch `v0.15-remove-html`, pushed to `origin`).
