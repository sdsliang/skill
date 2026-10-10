#!/usr/bin/env python3
"""Read-only: does the ToolSmith-deployed skill bundle equal this repo?

`toolsmith-publish status` is prompt-first, so it refuses a repo that ships a skill but no
system prompt (the two report-humanizer projects are exactly that). This helper does the
skill half only, and it never writes anything on the platform:

    python3 -B tools/verify-skill-upload.py --repo ../report-humanizer-zh
    python3 -B tools/verify-skill-upload.py --repo ../report-humanizer-zh --show-files

What it proves
  1. which skill version the platform serves (`skill_id`, `version`, `updated_at`, owner)
  2. every member of the deployed zip is byte-identical to `skill/<name>/<rel>` locally
  3. the deployed member set equals the local `dist/*.zip` member set, and each member's
     sha matches the local archive — i.e. the uploaded attachment is the archive we built
  4. no local file is missing from the deployment

Exit codes: 0 in sync / 3 drift (details printed) / 2 usage or transport error.

The ToolSmith client is reused from the installed runner (no credentials or base URL are
duplicated here, and nothing is written back).
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
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
    ap.add_argument("--family", help="skill family id (default: projects.json)")
    ap.add_argument("--name", help="skill name (default: projects.json)")
    ap.add_argument("--show-files", action="store_true", help="list every member")
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

    ts = load_runner()
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

    print(f"repo   {repo}")
    print(f"skill  {name}  family={family}")
    print(f"as     {who.get('username')} (user_id={who.get('user_id')})")
    print(f"cur    v{cur.get('version')} skill_id={cur.get('id')} "
          f"commit_id={cur.get('commit_id')} updated_at={cur.get('updated_at')}")
    print(f"       owner={cur.get('owner')!r} owner_user_id={cur.get('owner_user_id')} "
          f"message={cur.get('message')!r} versions_in_family={len(items)}")

    deployed_bytes = client.download(f"/api/skills/{cur['id']}/download")
    deployed, root = members(deployed_bytes)
    local_root = os.path.join(repo, "skill", name)

    same, diffs, absent = [], [], []
    for rel, blob in sorted(deployed.items()):
        path = os.path.join(local_root, rel)
        if not os.path.isfile(path):
            absent.append(rel)
        elif ts.sha(blob) != ts.sha(open(path, "rb").read()):
            diffs.append(rel)
        else:
            same.append(rel)

    dist = newest_dist(repo)
    dist_members: dict[str, bytes] = {}
    dist_note = "no dist/*.zip"
    if dist:
        with open(dist, "rb") as fh:
            dist_members, _ = members(fh.read())
        dist_note = (f"{os.path.basename(dist)} entries={len(dist_members)} "
                     f"bytes={os.path.getsize(dist)} "
                     f"sha={ts.sha(open(dist, 'rb').read())[:12]}")

    set_drift = sorted(set(dist_members) ^ set(deployed))
    content_drift = sorted(rel for rel in set(dist_members) & set(deployed)
                           if dist_members[rel] != deployed[rel])

    print(f"\nzip    entries={len(deployed)} identical-to-worktree={len(same)} "
          f"differing={len(diffs)} missing-locally={len(absent)} root={root or '(none)'}")
    print(f"dist   {dist_note}")
    print(f"       member-set drift vs dist: {set_drift or 'none'}")
    print(f"       content drift vs dist:    {content_drift or 'none'}")
    if args.show_files or diffs or absent or set_drift or content_drift:
        for rel in sorted(deployed):
            tag = ("DIFF " if rel in diffs else "NO-LOCAL " if rel in absent else "ok   ")
            print(f"         {tag}{rel}")

    ok = not (diffs or absent or set_drift or content_drift)
    print(f"\n-> deployed == worktree and == dist: {ok}")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
