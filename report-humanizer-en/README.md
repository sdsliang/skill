# report-humanizer-en — English report de-AI-flavoring (ToolSmith Skill)

Rewrite English analytical report prose so it reads like a colleague wrote it for a decision maker: conclusion first, facts and evidence only, consistent terminology, **no process narration or self-explanation**.

Sources: `blader/humanizer` (structural-first §1–§5) and `op7418/Humanizer-zh` (31-item Chinese pattern taxonomy, reweighted here for reports). Both are AI-writing-tell catalogues; this skill adds two report-specific constraints on top: **no process narration** (SKILL.md Section 3, highest priority) and **bilingual entity/drug naming** (`references/naming-bilingual.md`).

## Layout

```
report-humanizer-en/
├── skill/report-humanizer-en/          # self-contained bundle published to ToolSmith
│   ├── SKILL.md                        # 10 sections: priority / report voice / hard ban / data / naming / workflow / checklist / scanner / when not to act / worked example
│   ├── references/patterns-en.md       # 26 entries (A structural / B wording and rhythm / C inflation / D formatting / E leftovers / F wrong reader / G report-specific) with [strong]/[weak] marks
│   ├── references/naming-bilingual.md  # English/Chinese naming: common knowledge → dictionary → directional fallback
│   ├── references/examples.md          # 3 full-paragraph before/after pairs + "should be kept" boundaries
│   └── scripts/tell-scan.py            # dependency-free bilingual scanner, 22,558 B (byte-identical to the Chinese twin)
├── tools/pack-dist.py                  # deterministic packer: dist/report-humanizer-en-v0.1.1.zip (the upload attachment / in-place update)
└── evals/
    ├── test-tell-scan.py               # 25-check machine gate (run directly, never via unittest discover)
    └── fixtures/                       # ai-flavored / humanized / keep / weak-only + facts.json
```

## Local gate

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-en
python3 -B evals/test-tell-scan.py     # expect: report-humanizer-en machine gate: 25/25 OK
```

**Added 2026-10-10 (gate 23 → 25)**: ① **notation consistency** (new `D18` mixed notation plus a strengthened `B7` connector rule) — one value must keep a single form throughout (`0.48-0.80` and `0.48–0.80` must not mix), reported as the **document-level weak** hit `W-FMT-MIXED` (threshold 1, prose lines only — table rows never counted); the boundary is **symbol form and spacing only, never digits or magnitude**, and tables / quotations / citation markers / code / paths / URLs / IDs follow the host contract. ② **Process-voice boundary**: statements the host contract *requires* are still written, but as **material properties** ("all sources are abstract-level only") rather than **runtime environment** ("no network in this run, the chain never started").

The gate covers scanner behaviour (language detection, fenced-block skipping, `--allow`, exit codes, JSON shape), fixture outcome shape, **no fact loss** (the rewrite may not invent numbers; every `facts.en.json` anchor must survive in both drafts), and **anti empty-artifact** (rewrite ≥200 chars, ≥3 sentences, key facts present, `difflib` ratio < 0.9, AI draft longer than the rewrite). Two further checks validate `references/examples.md` itself: the AFTER paragraph may not contain numbers absent from BEFORE, and every "must survive verbatim" anchor must appear in both. One more gates packaging (dist must equal a fresh build). Two more are false-positive regressions found by scanning a real report: a bare noun such as a statistics term must not fire as process narration on its own, and table rows must be excluded from both line scanning and document-level counting.

Fixture baseline (must reproduce on regression):

| File | Strong | Weak |
|---|---|---|
| `ai-flavored.en.md` | ≥10 (measured 16) | ≥8 (measured 12) |
| `humanized.en.md` | 0 | 0 |
| `keep.en.md` | 0 | 2 (`W-ING-RIDER`, `W-NOMINAL`) |
| `weak-only.en.md` | 0 | 1 (`S-INFL-04`) |

## Scanner

```bash
python3 -B skill/report-humanizer-en/scripts/tell-scan.py <file.md> [--lang auto|zh|en]
        [--json] [--weak] [--allow RULE,RULE]
```

Exit codes: `0` no strong hits / `3` strong hits present (usable as a gate) / `2` usage or file error. It is an **assistant, not a judge**: a hit is not an order to edit, and no hit is not proof of quality.

## Packaging and upload (the attachment ToolSmith asks for)

Creating the skill on ToolSmith requires **uploading a bundle zip**, so the archive has to be one command away and always equal to the worktree:

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-en
python3 -B tools/pack-dist.py            # builds dist/report-humanizer-en-v0.1.1.zip
python3 -B tools/pack-dist.py --check    # expect IDENTICAL
```

- 5 members (`SKILL.md` + `references/*.md` + `scripts/*.py`) under the `report-humanizer-en/` prefix, which matches the `name:` in `SKILL.md` (the platform checks this).
- Deterministic: fixed timestamp, Unix creator, 0644, deflate level 6 — unchanged worktree, unchanged bytes, which is what `toolsmith-publish status` compares against.
- `evals/test-tell-scan.py::t_dist_zip_is_current` gates "dist equals worktree", so the bundle cannot change without repacking.
- When uploading from a Windows browser, use the UNC path:

```
\\wsl.localhost\Ubuntu-22.04\home\xupeipeioo1\apps\skill\report-humanizer-en\dist\report-humanizer-en-v0.1.1.zip
```

> Do not copy the zip to `C:\...` and upload from there: the corporate DLP driver can transparently encrypt Windows-side writes, and the platform would receive a broken archive. Read it straight from WSL over UNC.

## Versioning and publishing

**Published and updated in place on ToolSmith (2026-10-10)**: platform `skill_id 8a872f3a75bf474a97bafad3a0a6fde2`,
family `5d3eb1c8c1cd43a4a6148e07afbe008f`, platform version `1.0.0` (the platform's own sequence) — the live content equals
this repo's `dist/report-humanizer-en-v0.1.1.zip` (**30,765 B / 5 entries / sha256 `ccd56070090d…`**).

- This project ships a **skill bundle only, with no system prompt**, so `publish` (prompt + skill) does not apply; updates go
  through the **in-place** path (`POST /api/skills/update_skill_file`, full bundle zip, keeping `skill_id` and the version label):
  ```bash
  cd /home/xupeipeioo1/apps/skill/report-humanizer-en
  python3 -B ../tools/push-skill-inplace.py --check    # five read-only guards
  python3 -B ../tools/push-skill-inplace.py            # real upload: dist match / name match / owned / owner / read-back
  python3 -B ../tools/verify-skill-upload.py --repo .  # read-only: deployed == worktree == dist
  ```
- The `v0.1.x` in the filename is **this repo's own version**, unrelated to the platform sequence (`1.0.x`); the two are
  reconciled by content hash.
- The bundle changed, so the packaging version was bumped and the old zip deleted (this project's `dist/` keeps only the
  current package).
- Version history: `v0.1.0` (initial) → **`v0.1.1`** (2026-10-10: notation-consistency rule, document-level weak
  `W-FMT-MIXED` hit, and the process-voice boundary — see `PROJECT_STATE.md`).

Memory: `AGENTS.md`, `PROJECT_STATE.md`. Git root = `/home/xupeipeioo1/apps/skill` (`git@github.com:sdsliang/skill.git`).
