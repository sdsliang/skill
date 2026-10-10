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
│   └── scripts/tell-scan.py            # dependency-free bilingual scanner, 21,351 B (byte-identical to the Chinese twin)
├── tools/pack-dist.py                  # deterministic packer: dist/report-humanizer-en-v0.1.0.zip (the upload attachment)
└── evals/
    ├── test-tell-scan.py               # 23-check machine gate (run directly, never via unittest discover)
    └── fixtures/                       # ai-flavored / humanized / keep / weak-only + facts.json
```

## Local gate

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-en
python3 -B evals/test-tell-scan.py     # expect: report-humanizer-en machine gate: 23/23 OK
```

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
python3 -B tools/pack-dist.py            # builds dist/report-humanizer-en-v0.1.0.zip
python3 -B tools/pack-dist.py --check    # expect IDENTICAL
```

- 5 members (`SKILL.md` + `references/*.md` + `scripts/*.py`) under the `report-humanizer-en/` prefix, which matches the `name:` in `SKILL.md` (the platform checks this).
- Deterministic: fixed timestamp, Unix creator, 0644, deflate level 6 — unchanged worktree, unchanged bytes, which is what `toolsmith-publish status` compares against.
- `evals/test-tell-scan.py::t_dist_zip_is_current` gates "dist equals worktree", so the bundle cannot change without repacking.
- When uploading from a Windows browser, use the UNC path:

```
\\wsl.localhost\Ubuntu-22.04\home\xupeipeioo1\apps\skill\report-humanizer-en\dist\report-humanizer-en-v0.1.0.zip
```

> Do not copy the zip to `C:\...` and upload from there: the corporate DLP driver can transparently encrypt Windows-side writes, and the platform would receive a broken archive. Read it straight from WSL over UNC.

## Versioning and publishing

- **Not published to ToolSmith.** Publishing requires: (1) the user to create the skill family on the platform; (2) a `~/.config/toolsmith/projects.json` entry for this project (key = `/home/xupeipeioo1/apps/skill/report-humanizer-en`, `owned: true`); (3) explicit user authorisation before `toolsmith-publish push-skill`.
- This project ships a **skill bundle only, with no system prompt**, so `publish` (prompt + skill) does not apply.
- `scripts/tell-scan.py` **must stay byte-identical** to `../report-humanizer-zh/skill/report-humanizer-zh/scripts/tell-scan.py` (asserted by `t_bundle_parity`); edit one, copy the other.

Memory: `AGENTS.md`, `PROJECT_STATE.md`. Git root = `/home/xupeipeioo1/apps/skill` (`git@github.com:sdsliang/skill.git`).
