# Runner gate — `verify-run-chain.py`

Offline (zero network, zero platform writes) regression gate for the `toolsmith-publish run` client.

It walks every recorded run under `~/.local/state/toolsmith-runs/` and asserts that the tool chain
rebuilt from the **durable** persisted messages (`/debug/history`) equals the **v1 SSE chain**, plus
exactly the schema-rejected attempts the SSE tap hides.

```
python3 evals/runner-gate/verify-run-chain.py     # exit 0 = all comparable runs agree
```

`TOOLSMITH_PUBLISH` (default `~/.local/bin/toolsmith-publish`) and `TOOLSMITH_RUNS`
(default `~/.local/state/toolsmith-runs`) override the paths.

## Why it exists (ledger O9)

v1's `parse_stream()` does not know the `tool-input-error` event, so run `20260914-174222-a2-2valid`
was recorded as *"40 calls, 0 tool errors"* while the model had actually attempted **41** calls: the
41st sent `execute` with `command` instead of `shell_command`, the tool schema rejected it
(`Field required: shell_command`), and the framework re-prompted and the call was re-issued with a
new id. The durable path sees that by construction; this gate proves the two views agree once the
rejected attempt is accounted for.

## Skips (printed, not failures)

- **v2 runs** — the tap is deliberately a stub (the POST is abandoned right after `data-turn-start`),
  so there is no SSE chain to compare against; the durable path *is* the chain.
- **`--resume` runs** — no tap is written at all, because nothing was POSTed.

Skips still print `history_attempts=…`, so a change in the extracted chain stays visible.

## What counts as "hidden from the tap" (runner O32)

The SSE tap cannot see a call that produced no tool-return. There are **two** reasons for that, and
this gate treats both as hidden: `args-refused` (the tool refused the arguments — shape, name or
value — and the framework re-prompted) and `fetch-failed` (an external retrieval failed with 4xx/5xx
or an unreachable host). Before O32 the second kind was mislabelled `schema-rejected` **and** hidden
from the `errors` list, so the FAIL-level `no tool errors` assertion stayed green while a fetch had
actually failed (R15/R16/R17/R18 each 500'd on
`…/europepmc/webservices/rest/PMC6933872/fullTextXML`). The gate therefore folds
`rejected + fetch_failures` into the comparison set.

## Receipt scope regression (2026-09-18)

`python3 evals/runner-gate/test-runner.py` runs 30 offline tests, including synthetic
`cmd_run --resume` cases: an expired foreign-turn receipt with a pointer-free target passes
without fetching the foreign path; a final target pointer missed by polling fails; a collected
target pointer passes only with matching on-disk bytes and manifest hash.

The collector requires the target `turn_id` and filters top-level UI message `turn_id` values.
Local R18/R19/R20 `/messages` archives confirm a list of messages with top-level `turn_id` and
`parts`; an explicit `messages` envelope is also supported. Foreign and unscoped poll pointers
remain in the receipt diagnostics. Final scoped model/UI/message pointers alone define required
coverage. Unknown final UI shapes and ambiguous multi-turn ownership fail closed; unlabelled
final messages are inferred only when independent evidence identifies a single target turn.

This fix first backed up the runner to
`~/.local/state/toolsmith-publish/toolsmith-publish.v10.bak`. The cumulative snapshot still uses
**original v9**, SHA-256 `7fdfe082bb3758fa4f4577ca5efe1e8a0c7437cf3c14993ae52e4feef398f9dd`:

```bash
python3 evals/runner-gate/snapshot-runner.py \
  --baseline ~/.local/state/toolsmith-publish/toolsmith-publish.v9.bak
```

Validation: runner/test `py_compile` passed; 30 tests passed; chain gate passed with 5 comparable
runs (36 histories, 31 skipped); applying `runner-patches/review-hardening.patch` to original v9
reproduced the installed runner byte for byte and matched all snapshot hashes. No network or
Git writes were performed. Changes are confined to the runner and this gate directory, plus
the required numbered backup; no Docker action applies.

## Not covered by the chain comparison: the receipt layer

`tool_results/**` (params JSONL, fetched page bodies) is deleted at persist and filtered from the
artifact archive, so this gate — which only compares the *tool chain* — would stay green while the
returned data is lost. That layer is archived by the runner's `ReceiptArchiver` during the run and
asserted per-run (`tool_results receipts archived`); see the R19/R20 entries in
`docs/toolsmith-verification-log.md` and `docs/evidence/receipt-layer-2026-09-18.txt`.
