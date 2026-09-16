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
