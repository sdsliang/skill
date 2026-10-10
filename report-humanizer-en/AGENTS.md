# AGENTS.md — report-humanizer-en

English report de-AI-flavoring Skill. Working directory `/home/xupeipeioo1/apps/skill/report-humanizer-en`; git root `/home/xupeipeioo1/apps/skill` (remote `git@github.com:sdsliang/skill.git`).

## Hard rules

1. **The process-narration ban is the point of this skill**: SKILL.md Section 3 (no process narration or self-explanation in a deliverable) outranks every checklist entry and every scanner hit. Never weaken it while editing.
2. **`scripts/tell-scan.py` must be byte-identical across both bundles** (`evals/test-tell-scan.py::t_bundle_parity`). After editing the English copy, immediately copy it to `../report-humanizer-zh/skill/report-humanizer-zh/scripts/tell-scan.py` and vice versa.
3. **No fact loss is the floor**: when touching fixtures or `references/examples.md`, an AFTER paragraph may not contain numbers absent from BEFORE, and every `facts.en.json` anchor (including `0.48-0.80` with a plain hyphen, unlike the Chinese twin's en dash) must survive in both drafts.
4. **Anti empty-artifact**: the rewrite must be real prose (length / sentence-count / similarity thresholds). Assertions must never be satisfiable by emptying or copying the source.
5. **Fixture baseline is a regression contract**: `ai-flavored` ≥10 strong, `humanized` 0/0, `keep` 0 strong / 2 weak, `weak-only` 0 strong / 1 weak. Understand why a baseline would move before relaxing a rule.
6. **Notation consistency touches symbols and spacing only**: digits, magnitude and units stay untouched; tables / quotations / citation markers / code / paths / URLs / IDs follow the host contract (implementation: `_mixed_notation` and `W-FMT-MIXED` in `tell-scan.py`).
7. **Process voice is bounded by material property vs runtime environment**: statements the host contract requires are written as material properties; runtime environment, retrieval chain, tools and retries are never written.
8. **Publishing is a write action**: writing to ToolSmith (`push-skill`, including creating a family) **requires asking the user and getting explicit consent first**. Local edits, `commit` and `push` follow workspace rules (commit/push in `apps/skill` need no confirmation; merge/rebase/branch creation or deletion still do).
9. **No detector evasion**: this skill handles expression only. It does not judge authorship and does not guarantee passing any detector.

## Commands

```bash
cd /home/xupeipeioo1/apps/skill/report-humanizer-en
python3 -B evals/test-tell-scan.py                                    # gate, expect 25/25 OK
python3 -B skill/report-humanizer-en/scripts/tell-scan.py <file>       # scan one file
diff skill/report-humanizer-en/scripts/tell-scan.py \
     ../report-humanizer-zh/skill/report-humanizer-zh/scripts/tell-scan.py   # must be empty
python3 -B tools/pack-dist.py --check                                 # dist equals the worktree
python3 -B ../tools/verify-skill-upload.py --repo .                 # read-only: live skill == worktree == dist
python3 -B ../tools/push-skill-inplace.py --check                   # read-only pre-flight (five guards); drop --check to really upload (a write action, needs consent)                   # read-only: deployed skill == worktree == dist (status is prompt-first and refuses here)
```

## Packaging discipline

- After touching `skill/report-humanizer-en/**` repack: `python3 -B tools/pack-dist.py` (`--check` must be IDENTICAL). This zip is what ToolSmith takes as the skill attachment.
- `dist/*.zip` is committed (same rule as `clinical-result-comparison`), because the platform reconciles archives, not worktrees.
- Upload over the UNC path (`\\wsl.localhost\Ubuntu-22.04\...`), never by copying to `C:\...`: DLP can transparently encrypt Windows-side writes and the platform would receive ciphertext.

## Editing discipline

- Changing a rule means updating both `references/patterns-en.md` (entry and severity) and the family table in SKILL.md Section 8.
- Changing severities or rule tables: run the gate first, then decide whether the fixtures should change. Never edit fixtures to hide a rule regression.
- The test filename contains a hyphen, so `unittest discover` cannot import it; always run it directly.
- The scanner sets `sys.dont_write_bytecode = True`; after a run there must be no `__pycache__` under `skill/**/scripts/` (`t_no_bytecode_residue` asserts this).

## Status (2026-10-10)

`v0.1.1` is packaged (30,765 B / 5 entries / sha256 `ccd56070090d…`) and **updated in place on ToolSmith** (platform `1.0.0` / `skill_id 8a872f3a75bf474a97bafad3a0a6fde2`, deployed == dist); gate 25/25 OK.

Memory: `PROJECT_STATE.md`. Update it whenever you finish a change.
