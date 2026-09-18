#!/usr/bin/env python3
"""Offline gate for `toolsmith-publish run` (zero network, zero platform writes).

For every recorded run under `~/.local/state/toolsmith-runs/`, the tool chain rebuilt from the
*durable* persisted messages (`/debug/history`) must equal the v1 SSE chain, plus exactly the
schema-rejected attempts that the SSE tap hides.

Why this exists (ledger O9): v1's `parse_stream()` does not know `tool-input-error`, so one run
recorded "40 calls, 0 tool errors" while the model had actually attempted 41 calls (the 41st sent
`execute` with `command` instead of `shell_command`, was rejected by the tool schema, and was
retried). The durable path sees it by construction; this gate proves the two views agree once the
rejected attempt is accounted for.

Skips (printed, not failures):
  * v2 runs — the tap is deliberately a stub (the POST is abandoned right after `data-turn-start`),
    so there is no SSE chain to compare against; the durable path *is* the chain.
  * `--resume` runs — no `stream.tap` was written at all (nothing was POSTed).

Usage:  python3 evals/runner-gate/verify-run-chain.py
Exit:   0 all comparable runs agree; 1 any mismatch (prints which check failed and why).
"""
import collections
import glob
import importlib.machinery
import importlib.util
import json
import os
import sys

TOOL = os.path.expanduser(os.environ.get("TOOLSMITH_PUBLISH", "~/.local/bin/toolsmith-publish"))
RUNS = os.path.expanduser(os.environ.get("TOOLSMITH_RUNS", "~/.local/state/toolsmith-runs"))

ldr = importlib.machinery.SourceFileLoader("ts", TOOL)
ts = importlib.util.module_from_spec(importlib.util.spec_from_loader("ts", ldr))
ldr.exec_module(ts)

bad = 0
seen = 0
for d in sorted(glob.glob(os.path.join(RUNS, "2026*"))):
    hist = os.path.join(d, "debug-history.json")
    if not os.path.exists(hist):
        print(f"{os.path.basename(d):28s} SKIP (no debug-history.json)")
        continue
    seen += 1
    tap = next((os.path.join(d, n) for n in ("stream.sse", "stream.tap")
                if os.path.exists(os.path.join(d, n))), None)
    n = ts.tool_chain_from_history(json.load(open(hist, encoding="utf-8")))
    if tap is None:
        print(f"{os.path.basename(d):28s} SKIP (--resume run: nothing was POSTed, so no tap)"
              f"  history_attempts={n['attempts']}")
        continue
    o = ts.parse_stream(tap)
    if not o["calls"]:
        # v2 run: the tap is a stub by design (POST is abandoned after data-turn-start),
        # so there is no SSE chain to compare against — the durable path IS the chain.
        print(f"{os.path.basename(d):28s} SKIP (v2 run: tap carries no tool events)"
              f"  history_attempts={n['attempts']}")
        continue
    # (O32) the attempts the tap cannot see are BOTH the argument-refused calls and the
    # external fetch failures the framework re-prompted (i.e. `retries` in the raw history).
    rej = {r["tool_call_id"] for r in n["rejected"] + n["fetch_failures"]}
    # dropping the rejected attempts from the new chain must reproduce the old one exactly
    keep = [c for c in n["calls"] if c[0] not in rej]
    same = [(a[1], a[2]) for a in o["calls"]] == [(b[1], b[2]) for b in keep]
    nids, oids = {c[0] for c in n["calls"]}, {c[0] for c in o["calls"]}
    checks = {
        "chain == tap + rejected": same,
        "extra ids == rejected": nids - oids == rej,
        "no double count": len(n["calls"]) == len(o["calls"]) + len(rej),
        "no unreturned call": not n["unmatched"] and all(c[0] in o["outputs"] for c in o["calls"]),
        "errors == tap tool-output-error": len(n["errors"]) == len(o["errors"]),
    }
    ok = all(checks.values())
    bad += 0 if ok else 1
    print(f"{os.path.basename(d):28s} attempts={n['attempts']} returned={len(n['calls']) - len(rej)} "
          f"rejected={len(rej)} errors={len(n['errors'])} tap={o['events'].get('tool-input-start')} calls "
          f"-> {'OK' if ok else 'MISMATCH ' + str([k for k, v in checks.items() if not v])}")
    print("    " + " ".join(f"{k}x{v}" for k, v in collections.Counter(c[1] for c in n["calls"]).most_common()))
    for r in n["rejected"] + n["fetch_failures"]:
        print(f"    hidden from v1: {r['tool_name']} "
              f"{json.dumps(r['args'], ensure_ascii=False)[:80]} -> "
              f"{json.dumps(r['reason'], ensure_ascii=False)[:160]}")

if not seen:
    print("no run directories found; nothing to compare")
print("\nGATE:", "PASS — durable chain == v1 SSE chain (+ the schema-rejected attempts the tap hides)"
      if not bad else f"FAIL ({bad})")
sys.exit(1 if bad else 0)
