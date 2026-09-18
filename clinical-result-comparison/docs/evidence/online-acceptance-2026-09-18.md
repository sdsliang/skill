# Online acceptance - 2026-09-18

## Deployment

- Prompt family `91febc286412479a8b6d569fa3b8025e`: in-place update, platform v1.6, local SHA `2ff672b5aa9b`.
- Skill family `9fe0035bdd324b998436c6cb9c2de212`: in-place update, platform v1.0.7, 19/19 files identical, dist SHA `4d20d48faeee`.
- `toolsmith-publish status`: in sync.
- Live dependency gate was checked before publish: params schema `esids`, no pending upstream changes.

## Runs

- R21 refusal: report/citations absent and selection queried. Initial runner receipt assertion failed because escaped JSON produced a trailing backslash candidate; preserved as historical failure.
- R22 standard A: report/citations present, deployed prompt/skill match, 43/43 r2 facts. One external Europe PMC HTTP 500 was visibly declared. Manual review found no chart despite the local fixed scenario table's one-chart expectation, and the report omitted the source-vs-record blinding discrepancy (`double-blind` vs stored `three-blind`). Do not call this full acceptance.
- R23 PMC/full-text: PMC11270764 JATS was retrieved (99,951 bytes; parsed body 43,186 chars), independently identified by PMID/PMCID, and full-text citations were grounded. Manual review found the report incorrectly said no time series existed although it listed C1D1 to C2D1 values; one drug-discontinuation interpretation also overstates a table footnote.
- R24/R25 refusal retries: runner exposed receipt parsing defects (glob and model-authored ellipsis). They are retained as failed historical runs, not rewritten.
- R26 final refusal: output contract, selection query, deployed bytes, and receipt archive all PASS; one real receipt was fetched and hash-verified. The offline B scorer has a false positive on the phrase `ID 是否有效` in a user-facing recheck suggestion (11/12), so this is not represented as B 12/12.

## Runner follow-up

The local runner now extracts required receipt pointers only from typed `tool-return/tool-result` content. Model prose, reasoning, and execute globs are diagnostic-only; concrete unsafe paths returned by a tool still fail closed. Backups v11-v13 and cumulative patch metadata are outside the repo. Offline runner tests: 38 PASS; historical chain gate: 5 comparable PASS; original-v9 patch reproduction: byte-identical. Receipt replay R21-R24: 8 real files, size and SHA-256 verified; R26 live receipt check PASS.

## Acceptance conclusion

Deployment and runtime contract checks passed. Content acceptance is **incomplete**: R22 and R23 require prompt/skill follow-up before claiming the standard A/full-text acceptance is green. No rollback was performed and no TS asset was republished after the in-place update.
