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

- [ ] **Publish to ToolSmith?** Requires (a) user authorisation, (b) creating the skill family on the platform (**that step uploads an attachment** → use `dist/report-humanizer-en-v0.1.0.zip`, UNC path in the README), (c) a `~/.config/toolsmith/projects.json` entry with `owned: true`, (d) `toolsmith-publish push-skill` followed by a `status` read-back.
- [ ] Confirm the project / skill / directory naming (`report-humanizer-en`).
- [ ] After publishing, run one real `toolsmith-publish run` and record it in the project log.

## Git

First committed as `4e88724` (branch `v0.15-remove-html`, pushed to `origin`).
