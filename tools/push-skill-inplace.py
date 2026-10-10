#!/usr/bin/env python3
"""Publish a skill-only project to ToolSmith **in place** (current version, no new label).

`toolsmith-publish push-skill` cannot serve a repo that ships a skill but no system prompt:
its ownership guard and `status` both read a prompt family first (`GET /api/prompts/None` →
404). This helper does the skill half with the same client, the same ownership guard and the
same platform endpoint the runner uses for an in-place update:

    POST /api/skills/update_skill_file   multipart {skill_id, skill_name, file=<dist zip>}

Semantics: the current platform version's files are replaced and its internal `commit_id`
advances — the version label and `skill_id` stay the same, no history entry is created. The
whole bundle zip is required; a partial zip would drop the files it omits.

    python3 -B tools/push-skill-inplace.py --repo . --check     # plan only, writes nothing
    python3 -B tools/push-skill-inplace.py --repo .             # in-place update + re-verify

Guards, in order (any failure aborts before a byte is written):
  1. `tools/pack-dist.py --check` — the dist zip must equal a fresh build of `skill/<name>/`
  2. `zip_skill_name(dist)` — the bundle's `SKILL.md` name must equal the configured skill name
  3. projects.json entry for this repo must be `"owned": true`
  4. `/api/auth/me` + the current version's `owner_user_id` must be the caller
  5. after upload: re-download the deployed bundle and compare it member-by-member with dist

Exit codes: 0 updated and verified / 3 uploaded but the deployed bundle differs / 2 usage,
guard or transport failure.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True

RUNNER = os.environ.get("TOOLSMITH_RUNNER", os.path.expanduser("~/.local/bin/toolsmith-publish"))
CONFIG = os.path.expanduser("~/.config/toolsmith/projects.json")


def load_runner():
    loader = SourceFileLoader("tsrunner", RUNNER)
    spec = importlib.util.spec_from_loader("tsrunner", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def newest_dist(repo: str) -> str | None:
    d = os.path.join(repo, "dist")
    if not os.path.isdir(d):
        return None
    cands = [f for f in os.listdir(d) if f.endswith(".zip")]
    if not cands:
        return None

    def key(name: str):
        tail = name.rsplit("-v", 1)[-1].removesuffix(".zip")
        try:
            return tuple(int(x) for x in tail.split("."))
        except ValueError:
            return (-1,)

    return os.path.join(d, max(cands, key=key))


def members(zip_bytes: bytes) -> tuple[dict[str, bytes], str]:
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = z.namelist()
    roots = {n.split("/")[0] for n in names if "/" in n}
    root = (list(roots)[0] + "/") if len(roots) == 1 else ""
    return ({n[len(root):] if root and n.startswith(root) else n: z.read(n) for n in names}, root)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="project directory (config key)")
    ap.add_argument("--dist", help="bundle zip (default: newest dist/<name>-v*.zip)")
    ap.add_argument("--family", help="skill family id (default: projects.json)")
    ap.add_argument("--name", help="skill name (default: projects.json)")
    ap.add_argument("--check", action="store_true", help="print the plan, write nothing")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    cfg = {}
    if os.path.isfile(CONFIG):
        with open(CONFIG, encoding="utf-8") as fh:
            cfg = json.load(fh).get(repo, {})
    family = args.family or cfg.get("skill_family")
    name = args.name or cfg.get("skill_name") or os.path.basename(repo)
    if not family:
        print(f"no skill_family for {repo}: pass --family or add a projects.json entry",
              file=sys.stderr)
        return 2
    if not cfg.get("owned"):
        print(f"guard: projects.json entry for {repo} is not marked \"owned\": true — refusing "
              f"to write (write-permission guardrail)", file=sys.stderr)
        return 2

    ts = load_runner()

    # 1. the attachment must be the current bundle, not a stale zip on disk
    pack = Path(repo) / "tools" / "pack-dist.py"
    if pack.is_file():
        out = subprocess.run([sys.executable, "-B", str(pack), "--check"],
                             capture_output=True, text=True)
        print(f"pack   {out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ''}")
        if out.returncode != 0:
            print("guard: pack-dist.py --check failed — repack before publishing:\n"
                  + (out.stdout + out.stderr).strip(), file=sys.stderr)
            return 2

    dist = args.dist or newest_dist(repo)
    if not dist or not os.path.isfile(dist):
        print(f"no bundle zip found under {repo}/dist", file=sys.stderr)
        return 2

    # 2. bundle identity must match the configured skill name
    zip_name, zip_desc = ts.zip_skill_name(dist)
    if zip_name.lower() != name.lower():
        print(f"guard: zip SKILL.md name {zip_name!r} != configured skill_name {name!r}",
              file=sys.stderr)
        return 2
    with open(dist, "rb") as fh:
        blob = fh.read()

    # 3/4. ownership on both sides
    client = ts.Client(os.environ.get("TS_BASE") or ts.env_from_secrets("TS_BASE"),
                       os.environ.get("TS_TOKEN") or ts.env_from_secrets("TS_TOKEN"))
    who = ts.me(client)
    status, lst = client.json_call("POST", "/api/skills/list",
                                   {"family_id": family, "only_latest": False})
    if status >= 300:
        print(f"POST /api/skills/list -> HTTP {status}", file=sys.stderr)
        return 2
    items = lst.get("items", lst if isinstance(lst, list) else [])
    cur = next((i for i in items if i.get("is_current")), None)
    if cur is None:
        print(f"family {family}: no current skill version", file=sys.stderr)
        return 2
    if cur.get("owner_user_id") and cur["owner_user_id"] != who.get("user_id"):
        print(f"guard: family {family} is owned by {cur.get('owner_user_id')!r}, not "
              f"{who.get('user_id')!r} — refusing to write", file=sys.stderr)
        return 2

    print(f"repo   {repo}")
    print(f"skill  {name}  family={family}")
    print(f"as     {who.get('username')} (user_id={who.get('user_id')})")
    print(f"cur    v{cur.get('version')} skill_id={cur.get('id')} "
          f"commit_id={cur.get('commit_id')} updated_at={cur.get('updated_at')}")
    print(f"dist   {os.path.basename(dist)} bytes={len(blob)} sha={ts.sha(blob)[:12]} "
          f"name={zip_name!r}")
    deployed_before, _ = members(client.download(f"/api/skills/{cur['id']}/download"))
    changed = sorted(rel for rel, b in members(blob)[0].items()
                     if deployed_before.get(rel) != b)
    print(f"diff   members that will change: {changed or 'none'}")

    if args.check:
        print("\n--check: nothing written.")
        return 0
    if not changed:
        print("\nnothing to update (deployed bundle already matches dist).")
        return 0

    # 5. in-place update, then re-download and compare
    print("\nPOST /api/skills/update_skill_file (in-place, current version)")
    status, resp = client.upload("/api/skills/update_skill_file",
                                 {"skill_id": cur.get("id"), "skill_name": name}, dist)
    print(f"       -> HTTP {status} skill_id={resp.get('id')} version={resp.get('version')} "
          f"commit_id={resp.get('commit_id')} files={len(resp.get('files') or [])} "
          f"is_current={resp.get('is_current')}")
    if status >= 300:
        print(f"in-place skill update failed: {json.dumps(resp, ensure_ascii=False)[:400]}",
              file=sys.stderr)
        return 2

    after, _ = members(client.download(f"/api/skills/{cur['id']}/download"))
    local, _ = members(blob)
    drift = sorted(set(after) ^ set(local)) + sorted(
        rel for rel in set(after) & set(local) if after[rel] != local[rel])
    print(f"verify entries={len(after)} drift-vs-dist={drift or 'none'} "
          f"owner={resp.get('owner')!r}")
    ok = not drift and resp.get("owner_user_id", who.get("user_id")) == who.get("user_id")
    print(f"\n-> deployed == dist: {ok}")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
