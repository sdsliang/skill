#!/usr/bin/env python3
"""Re-score fixed archived runs offline; R14 is a different input and gets focused evidence checks.

Writes only compact scores under revision-evidence/, never copies historical run artifacts.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import check

HERE = Path(__file__).resolve().parent
RUNS = Path.home()/'.local/state/toolsmith-runs'
RUN_NAMES = {'R14': '20260918-092000-resume-r14-l3-recollect',
             'R17': '20260918-095553-r17-sign-convention',
             'R18': '20260918-110804-r18-abstract-size',
             'B': '20260914-174145-b2-refusal'}


def r14_context(path):
    """Project record links from actual archived execute returns, not generated citations."""
    records = {}
    def walk(obj):
        if isinstance(obj, dict):
            if obj.get('part_kind') == 'tool-return' and obj.get('tool_name') == 'execute':
                text = str(obj.get('content') or '')
                for part in re.split(r'(?=ESID 24_)', text):
                    esid = re.match(r'ESID (24_\d+_\d+(?:_\d+)?)\b', part)
                    link = re.search(r'clinical_result_full_article_link\s*=\s*(https://\S+)', part)
                    if esid and link:
                        records[esid[1]] = {'clinical_result_extra_esid': esid[1],
                                           'clinical_result_full_article_link': link[1]}
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    walk(json.loads((path/'debug-history.json').read_text()))
    esids = list(dict.fromkeys(re.findall(r'24_\d+_\d+(?:_\d+)?', (path/'prompt.txt').read_text())))
    if not esids or any(e not in records for e in esids):
        raise ValueError('R14 source links cannot be reconstructed from archived record returns')
    return {'check': {'esids': esids}, 'fixture': {'response': {'result': {'data': list(records.values())}}}}


def main():
    out = HERE/'revision-evidence'; out.mkdir(exist_ok=True)
    summary, lines, failures = {}, [], []
    for label, name in RUN_NAMES.items():
        path = RUNS/name
        proc = subprocess.run([sys.executable, str(HERE/'check.py'), '--run', str(path),
            '--scenario', 'b' if label == 'B' else 'a', '--json', str(out/f'{label}-revised.json')],
            capture_output=True, text=True)
        if proc.returncode not in (0, 3):
            raise RuntimeError(proc.stderr or proc.stdout)
        score = json.loads((out/f'{label}-revised.json').read_text())
        entry = json.loads((out/f'{label}-entry.json').read_text())
        summary[label] = {'evaluator_revision': check.EVALUATOR_REVISION,
            'run': name, 'entry_score': f"{entry['facts_ok']}/{entry['facts_total']}",
            'revised_score': f"{score['facts_ok']}/{score['facts_total']}",
            'failures': [i['id'] for i in score['items'] if not i['ok'] and i['severity'] == 'fail']}
        if label == 'R14':
            summary[label]['applicability'] = 'NOT scenario A; overall score is diagnostic only, not a quality baseline'
            ctx = r14_context(path)
            sv = check.load_surfaces(str(path))
            focused = {}
            for fn, spec in [(check.op_cite_link_is_deepest, {}),
                             (check.op_fulltext_cite_has_body, {'link_field': 'clinical_result_full_article_link'})]:
                focused[fn.__name__] = dict(zip(['ok', 'detail'], fn(sv, spec, ctx)))
            # Verify both physical R14 routes, without copying or altering the archived originals.
            import fulltext
            bodies, _ = fulltext.evidence(sv['artifacts_dir'])
            focused['bodies'] = [{'name': b['name'], 'valid': b['valid'],
                                  'pmid': sorted(b['pmid']), 'pmcid': sorted(b['pmcid'])} for b in bodies]
            focused['source_context'] = ctx
            summary[label]['focused_fulltext'] = focused
            if (not all(focused[key]['ok'] for key in
                        ('op_cite_link_is_deepest', 'op_fulltext_cite_has_body'))
                    or len(bodies) != 2 or not all(b['valid'] and b['pmid'] == {'39054491'}
                        and b['pmcid'] == {'PMC11270764'} for b in bodies)):
                failures.append('R14 paired JATS/plaintext source proof failed')
        elif proc.returncode != 0:
            failures.append(f'{label} baseline no longer clean')
        line = f'{label} {summary[label]}'
        lines.append(line)
        print(line)
    (out/'rescore-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    lines.append('RESCORE: ' + ('FAIL ' + '; '.join(failures) if failures else 'PASS'))
    print(lines[-1])
    (out/'rescore.txt').write_text('\n'.join(lines)+'\n')
    inputs = [*HERE.glob('*.py'), *HERE.glob('*.facts.json'), *HERE.glob('*.md'),
              *HERE.glob('records/*.json'), *out.glob('*.json'), *out.glob('*.txt')]
    hashes = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(inputs) if p.name != 'sha256.json'}
    (out/'sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
