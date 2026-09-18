#!/usr/bin/env python3
"""Capture a reproducible runner delta, never a full executable or credentials."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--runner', type=Path, default=Path.home() / '.local/bin/toolsmith-publish')
args = parser.parse_args()
before, after = args.baseline.read_bytes(), args.runner.read_bytes()
patch = ''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),
                                     after.decode().splitlines(keepends=True),
                                     fromfile='a/toolsmith-publish', tofile='b/toolsmith-publish'))
if not patch:
    parser.error('no changes to snapshot')
# Only changed source hunks are retained. Inspect them before sharing the patch.
out = Path(__file__).resolve().parent / 'runner-patches'
out.mkdir(exist_ok=True)
(out / 'review-hardening.patch').write_text(patch, encoding='utf-8')
(out / 'review-hardening.json').write_text(json.dumps({
    'baseline_backup': args.baseline.name,
    'baseline_sha256': hashlib.sha256(before).hexdigest(),
    'runner_sha256': hashlib.sha256(after).hexdigest(),
    'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
    'apply': 'patch toolsmith-publish < review-hardening.patch',
}, indent=2) + '\n', encoding='utf-8')
print(f'Wrote {out}/review-hardening.patch and .json')
