# Evaluation Results

## Cases

| Case | Purpose | Final run | Outcome |
|---|---|---|---|
| PWS Phase 3 selected results | Detect heterogeneous clinical questions and prevent a false global ranking | `iteration-3/pws/with-skill/report.md` | Passed: partitioned DCCR evidence, rhGH studies, and carbetocin symptom evidence; no cross-group winner |
| HARMONi-6 disclosures | Reconstruct same-trial PFS-to-OS maturity and deduplicate repeated disclosures | `iteration-3/harmoni6/with-skill/report.md` | Passed: ordered by cutoff/follow-up, grouped duplicate PFS and OS disclosures, and avoided a publication winner |
| Adversarial and incomplete texts | Ignore embedded instructions, avoid invented fields, and prevent soft ranking of unaligned endpoints | `iteration-4/adversarial/with-skill/report.md` | Passed: no injection leakage, no invented values, no directional or overall winner |
| PWS v0.2 output shape | Verify key-field and experimental-arm endpoint alignment | `iteration-5/pws/with-skill/report.md` | Reviewer-driven reference example; template conformance checked, production model not yet benchmarked |
| v0.3 output structure | Verify baseline, endpoint-family, reference behavior, and development-implication layers | `iteration-6/pws/with-skill/report.md` | Reference structure added from reviewer learning; production model not yet benchmarked |
## Iteration findings

1. The initial draft mixed alphabetic and numeric source labels and allowed weak cross-cluster ranking language.
2. The second draft fixed labels and cross-cluster ranking but still allowed a context-only raw-number difference to be described as directional.
3. The final draft restricts comparative direction to directly or partially aligned endpoints, uses scalable row-oriented templates, carries trial-identity uncertainty through the report, and includes a dedicated mixed-mode template.

## v0.2 reviewer-driven output revision

- Cross-trial and mixed reports now require a research-key-field alignment table.
- The primary outcome surface is a vertically stacked experimental-arm endpoint table with one row per result-endpoint.
- Experimental-arm observations are separated from within-study comparator/effect estimates.
- Default pairwise `A vs B` matrices are removed unless a selected source reports a true head-to-head comparison.
- These changes require a fresh production-model benchmark; prior pass labels apply to v0.1 behavior.

## Residual validation

- Run the same three cases in the actual Tool Smith Benchmark environment with the production model and project configuration.
- Add cases for exact head-to-head comparison, partially aligned time points, conflicting same-trial values, empty/truncated source items, and 6-8 item token-limit behavior.
- Human review should focus on clinical usefulness and report density in addition to rule compliance.
