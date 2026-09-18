# Evaluator revision 2026-09-18-r2

This is an explicitly authorized evaluator revision and **new baseline**, not a skill-quality improvement. Only `evals/fact-check/**` is owned by this task. No TS/network calls, Git writes, runtime/skill edits, or ground-truth record changes were made. Worktree already contained partial evaluator changes when this task started; those were completed rather than discarded.

## Independent-review follow-up (r2, completed offline)

Three remaining trust-boundary holes are closed within this same r2 baseline:

- `history.py` restricts query evidence to direct `parts` of durable model `response` messages. The target comes from `run.json.turn_id`, or a unique archived turn; legacy model messages are mapped through UI `metadata.pydantic_ai.timestamp`. Only an unambiguous single-user-prompt archive can use the older no-ID fallback. Multiple possible turns, conflicting mappings, unscoped messages, nested tool-return counterfeits and foreign-turn calls cannot supply query attempts. Current `esids` and historical `extra_esids` arrays both work; repeated call IDs are deduplicated and contradictory arguments fail closed.
- Plaintext header IDs are stored as **claims**, with empty proven identity until independently corroborated. The exact `PMC99999999 PMID:12345678\nMethods\n` plus 200-character counterfeit fails alone. JATS corroboration requires matching source IDs **and body text**; independent archived metadata/fetch mappings must match the claimed PMCID and any claimed PMID without competing mappings. Fetch receipts use the same bounded target-turn model reader. R14's real paired plaintext/JATS remains valid.
- Chart label and description identity dimensions are checked for conflicting known drug, dose/frequency, trial and time tokens. A correct complete tooltip cannot conceal a wrong displayed label. Legal partial labels and identity split across carriers remain accepted, including real R17/R18.

Permanent additions: M39–M41 wrong displayed drug/dose/time with a correct tooltip; M42 self-claimed plaintext PMID; MB12 foreign-turn calls; MB13 nested counterfeit calls; MB14 ambiguous target turn; NB01 current `esids` schema remains entirely clean. Regression tests additionally cover legacy timestamp mapping, conflicting mappings, malformed arguments, matching/wrong archived fetch metadata and mismatched JATS body text.

`rescore_revision.py` now fails if any applicable baseline or either R14 source-proof route regresses, stamps summaries with r2, writes its evidence log, and refreshes hashes for code, checklists, unchanged records, docs and evidence. Original `*-entry.json` snapshots are preserved.

## Exact baseline accounting

The previously published/reviewer baseline was A **41 fail + 1 warn**, B **12 fail + 1 warn**. The reviewer demonstrated that R17 retained 41/41 for swapped labels, a single sign flip, a broken replacement line chart and unsigned wrong ownership. That original scorer was not reconstructed with Git in this no-Git task.

At entry, the worktree already had two additional A items (structure and observation identity), giving **43 fail + 1 warn**, but its label/description regexes falsely rejected legitimate R17/R18 layouts. `revision-evidence/*-entry.json` captures the exact pre-edit scores. The completed revision still has **43 fail + 1 warn** for A and **12 fail + 1 warn** for B.

| Archived run | Previously recorded baseline | Actual entry scorer | Completed r2 scorer |
|---|---:|---:|---:|
| R17, scenario A | 41/41, warn 1/1 | 42/43, warn 1/1 | **43/43, warn 1/1** |
| R18, scenario A | 41/41, warn 1/1 | 42/43, warn 1/1 | **43/43, warn 1/1** |
| B, R6 refusal | 12/12, warn 1/1 | 12/12, warn 1/1 | **12/12, warn 1/1** |
| R14 recollected archive, forcibly scored as A | Not an A run | 28/43, warn 0/1 | **26/43, warn 0/1 — NOT APPLICABLE as quality score** |

R14 uses `24_1_39054491_1` / `24_1_42477684_1`, whereas A uses `24_1_30561610` / `24_1_36342163`. The lower forced-A score is honest: P6/P9 now reject mapping R14's article to A's frozen records. Do not interpret that total as an R14 regression or change A's records to make it green. With R14's own source links projected from the archived `execute` record-return text (not from generated citations), **both focused full-text assertions pass**. Both real carriers, `PMC11270764_fulltext_jats.xml` and `PMC11270764_plain.txt`, identify PMID 39054491 / PMC11270764. The parenthesized original/database blind-design divergence also remains accepted.

## Behavior fixed

- Every emitted chart is structurally inspected, including invalid JSON, null/ill-shaped rows, alternate allowed bar filenames, and illegal line/timeline filenames. Present-but-malformed is never treated as optional absence.
- Chart facts bind drug, dose/frequency, trial, endpoint, time and value per observation. Identity can be split across label/description; the common endpoint can be in title/axis/source. Reordered rows and `endpoint-bar-7.json` remain legal. Label/value swaps, dose/time mismatch and each individual sign flip fail. Positive magnitudes require explicit reduction wording in the corresponding cited report observation. Description signs must also agree when a point estimate is present.
- A-S9 and A-S10 now delegate to observation matching; their former magnitude-bag and positional/global-sign paths are removed. They retain legacy checklist IDs and overlap A-S9b: **43 items are not 43 statistically independent signals**.
- Attribution includes signed and unsigned numeric tokens with decimal boundaries. `依洛尤单抗降低 70.5%{{ref_1}}。` fails; embedded larger numbers do not spuriously match 70.5.
- Paired divergence is parsed as one adjacent source/database claim across a semicolon. It requires actual values and a citation, accepts closing parentheses before the marker, and cannot borrow another valid pair elsewhere in the paragraph to excuse an incomplete claim.
- Full-text proof requires substantive body content and source identity. JATS uses `front/article-meta` IDs and a nonempty `body`; IDs in a reference list, a URL/header alone, metadata-only XML, a JSON abstract or an empty filename cannot prove full text. Attribution uses the frozen record's PMID/PMCID, not generated filename/citation agreement. Plaintext can use corroborating JATS or independently archived structured PMID/PMCID mapping responses (source JSON or archived `web_fetch` return). A matching PMCID with the wrong source PMID fails. Missing evidence fails explicitly.
- Missing mutation baselines fail the gate. Scorer errors cannot reuse stale score output. Empty forbidden B files count as files; citation values must be strings, and report markers must match citation keys. B query evidence counts distinct target-turn durable model calls with the esid in `esids` or historical `extra_esids`, rather than repeated esid prose or nested payloads. The verbatim-copy check now includes the exact 60-character boundary and every offset. Malformed shapes are item failures rather than scorer crashes.

## Regression results, separate from real-run scores

`revision-evidence/mutations.txt`: **63 controls OK, zero BAD, GATE PASS**. This includes 42 A failure mutations, 14 B failure mutations and 7 must-remain-clean controls. A flips **43/43** fail items; B flips **12/12**. The must-remain-clean controls require the entire run to pass, not just one selected assertion.

Reviewer-specific permanent controls:

| Case | Control | Result |
|---|---|---|
| Swapped chart labels | M29; M35 after renaming chart | FAIL as required |
| Only one chart value changes sign | M30 | FAIL as required |
| Replacement endpoint-line chart | M31 | FAIL as required |
| Unsigned number cited to wrong owner | M32 | FAIL as required |
| Empty PMC filename plus matching URL | M33 | FAIL as required |
| Unmapped/nonmatching article body | M34 / M36 | FAIL as required |
| Invalid JSON chart | M37 | FAIL as required |
| Valid pair followed by incomplete divergence | M38 | FAIL as required |
| Legitimate paired numeric divergence | N29 | Entire run PASS |
| Reordered and renamed valid bar chart | N30 | Entire run PASS |
| Both baseline paths missing | HarnessTests | Nonzero / GATE FAIL as required |

`revision-evidence/regressions.txt`: **27 unittest cases pass**, including subcases for empty/metadata-only/wrong-source/bibliography IDs, real-shape plaintext/JATS derivatives, independent mappings, unsigned boundaries, paired claims, chart ordering, malformed shapes, exact copy threshold, empty B artifacts, unknown citation markers and query-call deduplication. Synthetic article bodies discuss wooden blocks and explicitly say they are tests; they are not invented clinical evidence or replacement ground truth.

Reproduce offline:

```bash
python3 -W ignore::ResourceWarning -m unittest discover -s evals/fact-check -p 'test_*.py' -v
python3 evals/fact-check/mutations.py
python3 evals/fact-check/rescore_revision.py
```

`rescore_revision.py` only reads the named historical runs and writes compact scores in `revision-evidence/`. No historical run is copied into the repository. `revision-evidence/sha256.json` identifies the evaluator, scenario lists, tests and unchanged record fixtures used for this baseline.

## Evidence limits

These are deterministic checks on archived evidence, not proof that a source was authentic or that every narrative sentence is scientifically correct. Full-text byte/source identity does not prove every reported number came from that body. A standalone plaintext file cannot establish its own PMID/PMCID identity, even with an explicit matching PMID header; R14's actual paired plaintext/JATS route remains valid. Full-text body thresholds reject empty shells but cannot establish completeness. Natural-language attribution and divergence parsing remain bounded patterns, not a general semantic verifier. Tests and score totals must not be presented as stronger evidence than those limits.

Git and Docker status: no Git writes or Docker actions were performed; no deployment artifacts changed. Project-wide memory/docs are intentionally untouched under this task's exclusive-directory boundary; this file is the handoff record for the evaluator revision.
