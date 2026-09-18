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

`python3 evals/runner-gate/test-runner.py` runs 38 offline tests, including synthetic
`cmd_run --resume` cases: an expired foreign-turn receipt with a pointer-free target passes
without fetching the foreign path; a final target pointer missed by polling fails; a collected
target pointer passes only with matching on-disk bytes and manifest hash.

The collector requires the target `turn_id` and filters top-level UI message `turn_id` values.
Local R18/R19/R20 `/messages` archives confirm a list of messages with top-level `turn_id` and
`parts`; an explicit `messages` envelope is also supported. Foreign and unscoped poll pointers
remain in the receipt diagnostics. Final scoped model/UI/message pointers alone define required
coverage. Unknown final UI shapes and ambiguous multi-turn ownership fail closed; unlabelled
final messages are inferred only when independent evidence identifies a single target turn.

The earlier scope fix was backed up to `toolsmith-publish.v10.bak`; this R21-R23 parsing fix
first backed up the runner to `~/.local/state/toolsmith-publish/toolsmith-publish.v11.bak`.
The receipt parser now decodes
JSON-serialized message fields before scanning them, so escaped closing quotes cannot become
receipt path suffixes; malformed or unsafe candidates still go through `receipt_relpath` and
fail closed.

The R25 provenance fix first backed up the installed runner to
`~/.local/state/toolsmith-publish/toolsmith-publish.v14.bak` (SHA-256
`8dfdfb91e8402ac16c6adcb43cde58566da7df8bdfbdd62c6fdb3cc12860c7d`).
The R24 follow-up was backed up at
`~/.local/state/toolsmith-publish/toolsmith-publish.v12.bak` (SHA-256
`a8fd28a35a37b8536b7e68d1628e5a610a32fda99b985d3ef1315702ace0207c`). R24's
`raw_model_messages[7].parts[1].args` contains an `execute` directory query with
`/workspace/tool_results/pharmcube-query-clinical-result-with-params/*.jsonl`.
The actual params return and subsequent execute output name only
`call_1ab8c7345fde.jsonl`, already archived at 30,732 bytes; the glob caused the second,
phantom requirement. The parser now ignores wildcard expressions (`*`, `?`, bracket classes)
and keeps bracket classes together so `call.json[ln]` cannot become `call.json`.
Directory queries therefore trigger no receipt download, while missing concrete
pointers still fail. Only those wildcard expressions are excluded: unsupported concrete
paths (including traversal, percent encoding, variables and backslashes) still fail validation.

Tool returns provide concrete file evidence in R24. The R25 review exposed the remaining
provenance bug: `raw_model_messages` and UI messages contain model reasoning, tool-call
arguments, tool outputs, and general prose in different shapes. The model wrote
`/workspace/tool_results/.../call_8451c932d3ac.jsonl` in reasoning and execute input prose,
while the precise params receipt appeared in a tool output. The parser now treats explicit
`part_kind`/`type` objects as provenance boundaries: only model `tool-return`/`tool-result`
content and typed UI `tool-*.output` are authoritative receipt evidence. Other mentions are
retained under `diagnostic_pointers` and never create download requirements. A concrete unsafe
path in a real return still reaches `receipt_relpath` and fails closed; no ellipsis stripping
or blanket candidate removal is used.

Tests cover glob queries in serialized model arguments and UI inputs, concrete execute outputs,
missing-then-archived receipts, prose link brackets, unsafe concrete paths beside globs, real
returned missing receipts, real returned unsafe paths, abbreviated model paths, and the actual
R25 UI shape. The current suite has 38 tests. The new R25 regression passes against the fixed
runner and fails against the pre-provenance v13 backup when replaying the actual R25 history.
The R25 precise receipt is required; the abbreviated path remains diagnostic only.

The cumulative snapshot still uses **original v9**, SHA-256 `7fdfe082bb3758fa4f4577ca5efe1e8a0c7437cf3c14993ae52e4feef398f9dd`:

```bash
python3 evals/runner-gate/snapshot-runner.py \
  --baseline ~/.local/state/toolsmith-publish/toolsmith-publish.v9.bak
```

Validation: runner/test/snapshot `py_compile` passed; 38 tests passed; chain gate passed with
5 comparable runs (41 histories, 36 skipped). Applying `runner-patches/review-hardening.patch`
to original v9 reproduced the installed runner byte for byte; baseline, runner and patch hashes
all matched. The separate current-local `check_run` replay of R21/R22/R23/R24/R25 is
`docs/evidence/r21-r25-receipt-recheck.json`: all five replayed with exit 0 and zero FAIL/WARN;
required receipt counts are 1/3/3/1/1. R25's abbreviated model mention is recorded as diagnostic
only, while the precise params receipt is archived and hash-verified. The earlier R21-R24
receipt evidence remains unchanged. This is not an overall run or quality PASS. Original
historical files remain unchanged. No live run, publish, network, Git write, prompt, skill,
scorer, state or ledger change was performed; no Docker action applies.

## Not covered by the chain comparison: the receipt layer

`tool_results/**` (params JSONL, fetched page bodies) is deleted at persist and filtered from the
artifact archive, so this gate — which only compares the *tool chain* — would stay green while the
returned data is lost. That layer is archived by the runner's `ReceiptArchiver` during the run and
asserted per-run (`tool_results receipts archived`); see the R19/R20 entries in
`docs/toolsmith-verification-log.md` and `docs/evidence/receipt-layer-2026-09-18.txt`.
