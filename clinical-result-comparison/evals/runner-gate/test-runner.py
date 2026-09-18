#!/usr/bin/env python3
"""Permanent offline v2 runner tests. No credentials, network, or historical writes.

Run: python3 evals/runner-gate/test-runner.py
TOOLSMITH_PUBLISH overrides the executable under test.
"""
from contextlib import redirect_stdout
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

TOOL = os.path.expanduser(os.environ.get('TOOLSMITH_PUBLISH', '~/.local/bin/toolsmith-publish'))
loader = importlib.machinery.SourceFileLoader('runner_test_subject', TOOL)
ts = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(ts)
POINTER = '/workspace/tool_results/query/data.jsonl'


def call(cid, name, args=None):
    return {'part_kind': 'tool-call', 'tool_call_id': cid, 'tool_name': name,
            'args': json.dumps(args or {})}


def ret(cid, name, content='ok', outcome='success'):
    return {'part_kind': 'tool-return', 'tool_call_id': cid, 'tool_name': name,
            'content': content, 'outcome': outcome}


def retry(cid, reason, name='query'):
    return {'part_kind': 'retry-prompt', 'tool_call_id': cid,
            'tool_name': name, 'content': reason}


def history(parts, turn='t'):
    # Actual v2 shape: model messages have no turn_id; UI messages do.
    return {'raw_model_messages': [{'parts': parts, 'instructions': 'SYSTEM\nplatform tail'}],
            'raw_ui_messages': [{'turn_id': turn, 'parts': []}]}


def archive(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for name, value in files.items():
            z.writestr(name, value)
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


class FakeClient:
    def __init__(self, messages=None, failures=0):
        self.messages = messages if messages is not None else [{'turn_id': 't', 'parts': [
            {'type': 'tool-query', 'state': 'output-available', 'output': POINTER}]}]
        self.failures = failures
        self.downloads = 0

    def json_call(self, *args, **kwargs):
        return 200, self.messages

    def download(self, *args, **kwargs):
        self.downloads += 1
        if self.downloads <= self.failures:
            raise SystemExit('HTTP 404')
        return b'{"value":42}\n'


class OfflineCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.net = patch.object(socket, 'create_connection', side_effect=AssertionError('NETWORK FORBIDDEN'))
        self.net.start()
        self.addCleanup(self.net.stop)


class ReceiptTests(OfflineCase):
    def test_traversal_and_encoded_paths_rejected(self):
        for pointer in ['/workspace/tool_results/../run.json',
                        '/workspace/tool_results/query/../../run.json',
                        '/workspace/tool_results/%2e%2e/run.json',
                        '/workspace/tool_results/query/a.json/../../run.json']:
            with self.subTest(pointer=pointer):
                self.assertIn(pointer, ts.receipt_diagnostics({'text': pointer}))
                with self.assertRaises(ValueError):
                    ts.receipt_destination(str(self.root), pointer)
        client = FakeClient([{'turn_id': 't', 'parts': [
            {'part_kind': 'tool-return', 'content': '/workspace/tool_results/../run.json'}]}])
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        collector.poll()
        result = collector.summary()
        self.assertEqual(client.downloads, 0)
        self.assertEqual(result['failed'], 1)
        self.assertFalse((self.root / 'run.json').exists())

    def test_directory_mentions_are_not_receipts(self):
        self.assertEqual(ts.receipt_diagnostics('/workspace/tool_results/query/'), [])
        self.assertEqual(ts.receipt_diagnostics('File: ' + POINTER + '.'), [POINTER])

    def test_glob_directory_queries_are_not_receipt_candidates(self):
        for pattern in ('*.jsonl', 'call_?.jsonl', 'call_[0-9].jsonl',
                        'call_[!ab].jsonl', 'call.json[ln]', '[ab]/data.jsonl',
                        'call_*.jsonl/../../run.json'):
            for tool in ('query', 'query-*', 'query[12]'):
                pointer = f'/workspace/tool_results/{tool}/{pattern}'
                command = f'for f in {pointer}; do wc -c "$f"; done'
                with self.subTest(pointer=pointer):
                    self.assertEqual(ts.receipt_pointers(
                        history([call('e', 'execute', {'shell_command': command})])), [])
        # Brackets surrounding a prose link are delimiters, not part of its path.
        self.assertEqual(ts.receipt_diagnostics(f'[{POINTER}](source)'), [POINTER])

    def test_glob_query_does_not_hide_missing_concrete_return(self):
        glob = '/workspace/tool_results/query/*.jsonl'
        command = f'ls -la /workspace/tool_results/query/; for f in {glob}; do echo "$f"; done'
        messages = [{'turn_id': 't', 'parts': [{'type': 'tool-execute',
                     'input': {'shell_command': command}}]}]
        client = FakeClient(messages)
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        collector.poll()
        query = call('e', 'execute', {'shell_command': command})
        query_history = history([query])
        self.assertEqual(client.downloads, 0)
        rec = collector.summary()
        self.assertEqual(rec['pointers'], [])
        self.assertEqual(ts.receipt_check({'receipts': rec},
                         query_history, str(self.root))[0], 'PASS')
        # Match the live shape: a query tool returns the actual pointer; execute
        # later queries the directory and prints that same concrete path.
        final = history([ret('q', 'query', POINTER), query,
                         ret('e', 'execute', f'== {POINTER} (13 bytes)')])
        self.assertEqual(ts.receipt_pointers(final), [POINTER])
        self.assertEqual(ts.receipt_check({'receipts': rec},
                         final, str(self.root))[0], 'FAIL')
        messages[0]['parts'][0]['output'] = POINTER
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, 1)
        self.assertEqual(rec['pointers'], [POINTER])
        self.assertEqual(ts.receipt_check({'receipts': rec},
                         final, str(self.root))[0], 'PASS')

    def test_non_glob_unsafe_concrete_paths_still_fail_with_glob(self):
        glob = '/workspace/tool_results/query/*.jsonl'
        for pointer in ('/workspace/tool_results/query/../../run.json',
                        '/workspace/tool_results/query/%2A.jsonl',
                        '/workspace/tool_results/query/%3F.jsonl',
                        '/workspace/tool_results/query/%5Bab%5D.jsonl',
                        '/workspace/tool_results/query/$file.jsonl',
                        POINTER + '\\'):
            with self.subTest(pointer=pointer):
                content = f'{glob} {pointer}'
                self.assertEqual(ts.receipt_diagnostics(content), [pointer])
                with self.assertRaises(ValueError):
                    ts.receipt_relpath(pointer)
                client = FakeClient([{'turn_id': 't', 'parts': [
                    {'part_kind': 'tool-return', 'content': content}]}])
                collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
                collector.poll()
                self.assertEqual(client.downloads, 0)
                self.assertEqual(collector.summary()['failed'], 1)
                self.assertEqual(ts.receipt_check({'receipts': collector.summary()},
                                 history([ret('q', 'query', content)]), str(self.root))[0], 'FAIL')

    def test_nested_escaped_json_is_decoded_before_pointer_scan(self):
        for pointer in (POINTER, '/workspace/tool_results/web_fetch/call_39ea4afacc51.md'):
            command = f'python - <<\'PY\'\np="{pointer}"\nprint(open(p).read())\nPY'
            nested = json.dumps({'shell_command': command})
            for value in (nested, json.dumps(nested), json.dumps([{'args': nested}])):
                with self.subTest(pointer=pointer, value=value):
                    payload = {'parts': [{'part_kind': 'tool-call', 'args': value}]}
                    self.assertEqual(ts.receipt_diagnostics(payload), [pointer])
                    self.assertEqual(ts.receipt_diagnostics([payload, {'output': pointer + '.'}]),
                                     [pointer])

    def test_unsafe_suffixes_remain_candidates_and_are_rejected(self):
        traversal = '/workspace/tool_results/query/../../run.json'
        escaped_suffix = POINTER + '\\'
        nested = json.dumps({'shell_command': f'cat "{traversal}" "{escaped_suffix}"'})
        for value in (nested, json.dumps(nested), nested[:-1], escaped_suffix,
                      json.dumps({'path': escaped_suffix}),
                      json.dumps({'path': POINTER + '%5c'})):
            with self.subTest(value=value):
                found = ts.receipt_diagnostics({'parts': [{'args': value}]})
                self.assertTrue(found)
                self.assertNotIn(POINTER, found)
                for pointer in found:
                    with self.assertRaises(ValueError):
                        ts.receipt_destination(str(self.root), pointer)
                client = FakeClient([{'turn_id': 't', 'parts': [
                    {'part_kind': 'tool-return', 'content': value}]}])
                collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
                collector.poll()
                rec = collector.summary()
                self.assertEqual(client.downloads, 0)
                self.assertEqual(rec['failed'], len(found))
                self.assertEqual(ts.receipt_check({'receipts': rec},
                                 history([ret('q', 'query', value)]), str(self.root))[0], 'FAIL')
        self.assertEqual(ts.receipt_diagnostics({'path': escaped_suffix}), [escaped_suffix])
        self.assertIn(traversal, ts.receipt_diagnostics({'args': nested}))

    def test_model_abbreviation_is_diagnostic_and_not_downloaded(self):
        abbreviated = '/workspace/tool_results/.../call_8451c932d3ac.jsonl'
        precise = '/workspace/tool_results/query/call_8451c932d3ac.jsonl'
        h = history([call('e', 'execute', {'shell_command': f'cat {abbreviated}'}),
                     {'part_kind': 'thinking', 'content': f'look at {abbreviated}'},
                     ret('q', 'query', precise)])
        self.assertEqual(ts.receipt_pointers(h), [precise])
        self.assertIn(abbreviated, ts.receipt_diagnostics(h))
        self.assertNotIn(abbreviated, ts.receipt_pointers(h))

        # Actual R25 UI shape: the abbreviation lives in reasoning prose; the
        # precise params pointer is a tool output. Only the latter is fetched.
        messages = [{'turn_id': 't', 'parts': [
            {'type': 'reasoning', 'text': f'read {abbreviated}'},
            {'type': 'tool-query', 'state': 'output-available', 'output': precise},
            {'type': 'tool-execute', 'state': 'output-available',
             'input': {'shell_command': f'cat {abbreviated}'}, 'output': 'done'}]}]
        client = FakeClient(messages)
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, 1)
        self.assertEqual(rec['pointers'], [precise])
        self.assertEqual(rec['diagnostic_pointers'], [abbreviated, precise])
        self.assertEqual(ts.receipt_check({'receipts': rec}, h, str(self.root))[0], 'PASS')

    def test_real_returned_missing_pointer_fails(self):
        messages = [{'turn_id': 't', 'parts': [
            {'type': 'tool-query', 'state': 'output-available', 'output': POINTER}]}]
        client = FakeClient(messages, failures=100)
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        for _ in range(collector.MAX_ATTEMPTS + 1):
            collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, collector.MAX_ATTEMPTS)
        self.assertEqual((rec['pointers'], rec['failed']), ([POINTER], 1))
        self.assertEqual(ts.receipt_check({'receipts': rec},
                         history([ret('q', 'query', POINTER)]), str(self.root))[0], 'FAIL')

    def test_authoritative_abbreviation_fails_closed_without_normalization(self):
        abbreviated = '/workspace/tool_results/.../call_8451c932d3ac.jsonl'
        h = history([ret('q', 'query', abbreviated)])
        self.assertEqual(ts.receipt_pointers(h), [abbreviated])
        with self.assertRaises(ValueError):
            ts.receipt_relpath(abbreviated)
        rec = {'pointers': [abbreviated], 'fetched': 1, 'failed': 0,
               'files': {abbreviated: {'bytes': 1, 'sha256': '0' * 64}}}
        self.assertEqual(ts.receipt_check({'receipts': rec}, h, str(self.root))[0], 'FAIL')

    def test_symlink_escape_rejected(self):
        (self.root / 'tool_results').symlink_to(self.root)
        with self.assertRaises(ValueError):
            ts.receipt_destination(str(self.root), POINTER)

    def test_transient_failure_retries_and_hash_verifies(self):
        client = FakeClient(failures=1)
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        collector.poll()
        collector.poll()
        collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, 2)
        self.assertEqual((rec['fetched'], rec['failed']), (1, 0))
        h = history([ret('q', 'query', POINTER)])
        self.assertEqual(ts.receipt_check({'receipts': rec}, h, str(self.root))[0], 'PASS')
        (self.root / 'tool_results/query/data.jsonl').write_bytes(b'tampered')
        self.assertEqual(ts.receipt_check({'receipts': rec}, h, str(self.root))[0], 'FAIL')

    def test_retries_are_bounded_and_failure_remains_visible(self):
        client = FakeClient(failures=100)
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        for _ in range(8):
            collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, collector.MAX_ATTEMPTS)
        self.assertEqual(rec['failed'], 1)

    def test_empty_polls_do_not_override_final_pointers(self):
        rec = {'pointers': [], 'fetched': 0, 'failed': 0, 'polls': 100}
        h = history([ret('q', 'query', POINTER)])
        self.assertEqual(ts.receipt_check({'receipts': rec}, h, str(self.root))[0], 'FAIL')
        self.assertEqual(ts.receipt_check({'receipts': rec})[0], 'FAIL')
        self.assertEqual(ts.receipt_check({'receipts': rec}, history([]), str(self.root))[0], 'PASS')

    def test_aggregate_counts_without_files_cannot_pass(self):
        rec = {'pointers': [POINTER], 'fetched': 1, 'failed': 0}
        self.assertEqual(ts.receipt_check({'receipts': rec}, history([ret('q', 'query', POINTER)]),
                                          str(self.root))[0], 'FAIL')

    def test_foreign_expired_pointer_does_not_fail_pointer_free_target(self):
        client = FakeClient([{'turn_id': 'old', 'parts': [{'type': 'tool-query',
                             'state': 'output-available', 'output': POINTER}]},
                             {'turn_id': 't', 'parts': [{'type': 'text', 'text': 'Done'}]}],
                            failures=100)
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, 0)
        self.assertEqual(rec['pointers'], [])
        self.assertEqual(rec['foreign_pointers'], [POINTER])
        scoped, error = ts.scope_history({'history': {
            'raw_model_messages': [{'turn_id': 'old', 'parts': [ret('old', 'query', POINTER)]},
                                   {'turn_id': 't', 'parts': [{'part_kind': 'text', 'content': 'Done'}]}],
            'raw_ui_messages': client.messages}, 'messages': client.messages}, 't')
        self.assertEqual(error, '')
        self.assertEqual(ts.receipt_check({'receipts': rec}, scoped, str(self.root))[0], 'PASS')
        # Old collectors put foreign paths into pointers; final evidence still wins.
        rec['pointers'] = [POINTER]
        check = ts.receipt_check({'receipts': rec}, scoped, str(self.root))
        self.assertEqual(check[0], 'PASS')
        self.assertIn('1 poll-only diagnostic', check[2])

    def test_unknown_poll_scope_is_diagnostic_but_final_own_pointer_still_required(self):
        for payload in [[{'parts': [{'type': 'text', 'text': POINTER}]}],
                        {'unknown_envelope': [{'turn_id': 't', 'text': POINTER}]}]:
            with self.subTest(payload=payload):
                client = FakeClient(payload)
                collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
                collector.poll()
                rec = collector.summary()
                self.assertEqual(client.downloads, 0)
                self.assertEqual(rec['uncertain_pointers'], [POINTER])
                self.assertEqual(ts.receipt_check({'receipts': rec}, history([]), str(self.root))[0], 'PASS')
                self.assertEqual(ts.receipt_check({'receipts': rec},
                                 history([ret('q', 'query', POINTER)]), str(self.root))[0], 'FAIL')

    def test_target_ui_envelope_pointer_collected_and_reconciled(self):
        client = FakeClient({'messages': [{'turn_id': 'old', 'text': '/workspace/tool_results/query/old.json'},
                                         {'turn_id': 't', 'parts': [{'type': 'tool-query',
                                          'state': 'output-available', 'output': POINTER}]}]})
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), turn_id='t')
        collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, 1)
        self.assertEqual(rec['pointers'], [POINTER])
        scoped, error = ts.scope_history({'history': {
            'raw_model_messages': [{'turn_id': 't', 'parts': [{'part_kind': 'text', 'content': 'Done'}]}],
            'raw_ui_messages': []}, 'messages': client.messages}, 't')
        self.assertEqual(error, '')
        self.assertIn(POINTER, ts.receipt_pointers(scoped))
        self.assertEqual(ts.receipt_check({'receipts': rec}, scoped, str(self.root))[0], 'PASS')
        rec['files'] = {}
        self.assertEqual(ts.receipt_check({'receipts': rec}, scoped, str(self.root))[0], 'FAIL')

    def test_final_ambiguous_or_unsupported_ui_scope_fails_closed(self):
        h = {'raw_model_messages': [{'turn_id': 't', 'parts': [ret('q', 'query')]}],
             'raw_ui_messages': [{'turn_id': 'old', 'parts': []}]}
        for messages in [[{'text': POINTER}], {'unknown_envelope': [{'text': POINTER}]}, [None]]:
            with self.subTest(messages=messages):
                scoped, error = ts.scope_history({'history': h, 'messages': messages}, 't')
                self.assertTrue(error)
                self.assertEqual(ts.receipt_check({'receipts': {'pointers': []}},
                                                 scoped, str(self.root))[0], 'FAIL')

    def test_missing_collector_target_never_borrows_thread_id(self):
        client = FakeClient()
        collector = ts.ReceiptArchiver(client, 't', str(self.root))
        collector.poll()
        rec = collector.summary()
        self.assertEqual(client.downloads, 0)
        self.assertEqual(rec['uncertain_pointers'], [POINTER])

    def test_stop_waits_for_worker_before_closing_log(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        client = FakeClient()
        original = client.download

        def slow(*args, **kwargs):
            entered.set()
            release.wait(3)
            return original(*args, **kwargs)

        client.download = slow
        collector = ts.ReceiptArchiver(client, 'thread', str(self.root), tick=.01, turn_id='t')
        collector.start()
        self.assertTrue(entered.wait(1))
        result = {}

        def finish():
            result.update(collector.summary())
            finished.set()

        stopper = threading.Thread(target=finish)
        stopper.start()
        try:
            self.assertFalse(finished.wait(.05))
            self.assertFalse(collector._log.closed)
        finally:
            release.set()
            stopper.join(3)
        self.assertTrue(finished.is_set())
        self.assertFalse(collector._thread.is_alive())
        self.assertTrue(collector._log.closed)
        self.assertEqual(result['fetched'], 1)


class ChainTests(OfflineCase):
    def test_returned_is_actual_returns_only(self):
        parts = [call('a', 'query'), ret('a', 'query'), call('b', 'query'),
                 call('c', 'query'), retry('c', 'RuntimeError: Field required'),
                 call('d', 'query'), retry('d', 'Failed to fetch: HTTP 500'),
                 call('e', 'query'), retry('e', '1 validation error for call[query]\nx\n Field required')]
        st = ts.tool_chain_from_history(history(parts))
        self.assertEqual((st['attempts'], st['returned']), (5, 1))
        self.assertEqual(len(st['unmatched']), 1)
        self.assertEqual(len(st['errors']), 1)
        self.assertEqual(len(st['rejected']), 1)
        self.assertEqual(len(st['fetch_failures']), 1)

    def test_retry_classifier_uses_original_structure(self):
        self.assertEqual(ts.retry_kind([{'type': 'missing', 'loc': ['x'], 'msg': 'Field required'}]), 'rejected')
        self.assertEqual(ts.retry_kind('RuntimeError: Field required'), 'errors')
        self.assertEqual(ts.retry_kind('RuntimeError: 1 validation error for call[query]'), 'errors')
        self.assertEqual(ts.retry_kind([{'msg': 'Field required'}]), 'errors')
        self.assertEqual(ts.retry_kind([]), 'errors')
        self.assertEqual(ts.retry_kind('Failed to fetch: HTTP 500'), 'fetch_failures')

    def test_orphans_duplicates_conflicts_fail(self):
        cases = [[ret('missing', 'query')],
                 [call('a', 'query'), call('a', 'query')],
                 [call('a', 'query'), ret('a', 'different')],
                 [call('a', 'query'), ret('a', 'query'), retry('a', 'Unknown tool name x')],
                 [retry('missing', 'Unknown tool name x')],
                 [call('a', 'query'), retry('a', 'RuntimeError: failure'),
                  retry('a', 'Unknown tool name x')]]
        for parts in cases:
            with self.subTest(parts=parts):
                self.assertTrue(ts.tool_chain_from_history(history(parts))['errors'])


class ContractTests(OfflineCase):
    def setUp(self):
        super().setUp()
        skill = self.root / 'skill/demo'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('Skill body\n')
        (skill / 'support.txt').write_text('a' * 1024)
        (self.root / 'sys.md').write_text('SYSTEM\n')
        self.a = SimpleNamespace(repo=str(self.root), sys=str(self.root / 'sys.md'),
                                 skill_name='demo', tool='query', expect=None, out=str(self.root))
        self.body = '<skill name="demo">\nSkill body\n</skill>\n- /workspace/skills/demo/support.txt (1.0 KB)'
        self.parts = [call('s', 'load_skill', {'name': 'demo'}), ret('s', 'load_skill', self.body),
                      call('p', 'present_artifact', {'path': '/workspace/output/report.md'}),
                      ret('p', 'present_artifact')]
        self.run = {'turn_id': 't', 'kind': 'completed', 'outcome': 'succeeded',
                    'receipts': {'pointers': [], 'fetched': 0, 'failed': 0}}
        self.files = {'output/report.md': '# Report\nA measured result {{ref_1}}\n',
                      'output/citations.json': json.dumps({'ref_1': {'title': 'Study', 'link': 'https://example.org',
                                                                  'paper_release_time_str': '2026-01-01'}})}

    def checks(self, h=None):
        z = archive(self.files)
        self.addCleanup(z.close)
        b = {'history': h or history(self.parts), 'zip': z,
             'timing': {'turns': [{'turn_id': 't'}]}}
        return ts.check_run(self.a, self.run, b, ts.tool_chain_from_history(b['history']))

    def failures(self, h=None):
        return [name for level, name, _ in self.checks(h) if level == 'FAIL']

    def test_positive_v2_contract(self):
        self.assertEqual(self.failures(), [])

    def test_empty_report_and_citations_fail(self):
        self.files.update({'output/report.md': ' \n', 'output/citations.json': '{}'})
        failures = self.failures()
        self.assertIn('report contains nonempty content', failures)
        self.assertIn('citations contains nonempty source entries', failures)

    def test_missing_or_partial_or_duplicate_manifest_fails(self):
        for body in [self.body.split('</skill>')[0] + '</skill>',
                     self.body.replace('support.txt', 'wrong.txt'),
                     self.body + '\n- /workspace/skills/demo/support.txt (1.0 KB)']:
            with self.subTest(body=body):
                self.parts[1]['content'] = body
                self.assertTrue(any('manifest' in name for name in self.failures()))

    def test_unreturned_call_is_failure(self):
        self.parts.insert(2, call('lost', 'query'))
        self.assertIn('every tool call either returned or was re-prompted (nothing lost)', self.failures())

    def test_presentation_requires_target_and_success(self):
        for args, outcome in [({'path': '/workspace/output/wrong.md'}, 'success'),
                              ({'path': '/workspace/output/report.md'}, 'error')]:
            with self.subTest(args=args, outcome=outcome):
                self.parts[-2]['args'] = json.dumps(args)
                self.parts[-1]['outcome'] = outcome
                self.assertTrue(any('final successful call' in name for name in self.failures()))
        self.parts.pop()
        self.assertTrue(any('final successful call' in name for name in self.failures()))

    def test_chart_targets_not_just_tag_counts(self):
        chart = {'id': ts.ENVELOPE_ID, 'iframe_template': '/release/chart.html', 'option': {'type': 'bar'}}
        self.files['visualizations/endpoint-bar-1.json'] = json.dumps(chart)
        self.files['output/report.md'] += '\n::visualization[Plot]{path="/workspace/visualizations/endpoint-bar-1.json"}'
        self.assertEqual(self.failures(), [])
        self.files['output/report.md'] = self.files['output/report.md'].replace('endpoint-bar-1.json', 'wrong.json')
        self.assertTrue(any('targets' in name for name in self.failures()))

    def test_malformed_json_is_failed_assertion(self):
        for value in ['{', '[]', '{"ref_1":{"title":7,"link":"","paper_release_time_str":9}}']:
            with self.subTest(value=value):
                self.files['output/citations.json'] = value
                self.assertTrue(self.failures())

    def test_unscopable_multiturn_fails_explicitly(self):
        h = history(self.parts)
        h['raw_ui_messages'].append({'turn_id': 'old', 'parts': []})
        self.assertIn('durable evidence belongs to the target turn', self.failures(h))
        _, error = ts.scope_history({'history': h}, 't')
        self.assertIn('unscopable multi-turn', error)

    def test_scoped_multiturn_does_not_borrow_prior_skill_or_prompt(self):
        h = history(self.parts)
        h['raw_model_messages'][0]['turn_id'] = 'old'
        h['raw_model_messages'].append({'turn_id': 't', 'parts': [call('q', 'query'), ret('q', 'query')]})
        h['raw_ui_messages'].append({'turn_id': 'old', 'parts': []})
        failures = self.failures(h)
        self.assertIn('deployed system prompt == local', failures)
        self.assertIn('deployed skill == local tree', failures)
        self.assertTrue(any('final successful call' in name for name in failures))
        scoped, error = ts.scope_history({'history': h}, 't')
        self.assertEqual(error, '')
        self.assertEqual(ts.tool_chain_from_history(scoped)['attempts'], 1)

    def test_scoped_multiturn_positive(self):
        h = history(self.parts)
        h['raw_model_messages'][0]['turn_id'] = 't'
        h['raw_model_messages'].insert(0, {'turn_id': 'old', 'instructions': 'OLD',
                                          'parts': [call('x', 'query')]})
        h['raw_ui_messages'].append({'turn_id': 'old', 'parts': []})
        self.assertEqual(self.failures(h), [])

    def test_v2_cli_collects_durable_history_and_fails_unseen_receipts(self):
        for missing_receipt in (False, True):
            with self.subTest(missing_receipt=missing_receipt):
                out = self.root / ('missing' if missing_receipt else 'positive')
                out.mkdir()
                a = SimpleNamespace(**vars(self.a))
                for key, value in dict(prompt='Compare results', prompt_file=None, resume=None,
                                       turn_id='t', cfg={}, model=None, timeout=5, poll_interval=5,
                                       grace=1, web=False, tag='synthetic', out=str(out), project_id='p',
                                       reasoning_effort=None, no_assert=False, dry_run=False).items():
                    setattr(a, key, value)
                parts = list(self.parts)
                if missing_receipt:
                    parts = parts[:2] + [call('q', 'query'), ret('q', 'query', POINTER)] + parts[2:]
                messages = [{'turn_id': 't', 'parts': [{'type': 'text', 'text': 'Done'}]}]
                timing = {'turns': [{'turn_id': 't', 'started_at': '2026-01-01T00:00:00',
                                     'completed_at': '2026-01-01T00:00:01'}]}
                z = archive(self.files)
                self.addCleanup(z.close)
                b = {'history': history(parts), 'messages': messages, 'timing': timing, 'zip': z}
                client = FakeClient(messages)

                def response(method, path, **kwargs):
                    if path.endswith('/info'):
                        return 200, {'status': 'idle'}
                    if path.endswith('/timing'):
                        return 200, timing
                    if path.endswith('/messages'):
                        return 200, messages
                    raise AssertionError(path)

                client.json_call = response
                with patch.object(ts, 'assert_owned_project'), \
                     patch.object(ts, 'create_thread', return_value='thread'), \
                     patch.object(ts, 'post_turn', return_value={'tap_status': 'turn-start (detached)'}), \
                     patch.object(ts, 'thread_bundle', return_value=b), redirect_stdout(io.StringIO()):
                    code = ts.cmd_run(client, a)
                self.assertEqual(code, 3 if missing_receipt else 0)
                saved = json.loads((out / 'run.json').read_text())
                self.assertEqual(saved['turn_id'], 't')
                self.assertEqual(saved['receipts']['final_missing'], [POINTER] if missing_receipt else [])
                if missing_receipt:
                    self.assertIn('tool_results receipts archived', saved['fails'])

    def test_resumed_turn_receipts_ignore_expired_foreign_but_require_own(self):
        for scenario in ('foreign-only', 'own-missed', 'own-collected'):
            with self.subTest(scenario=scenario):
                out = self.root / scenario
                out.mkdir()
                a = SimpleNamespace(**vars(self.a))
                for key, value in dict(prompt=None, prompt_file=None, resume='thread',
                                       turn_id='t', cfg={}, model=None, timeout=5, poll_interval=5,
                                       grace=1, web=False, tag='synthetic', out=str(out), project_id='p',
                                       reasoning_effort=None, no_assert=False, dry_run=False).items():
                    setattr(a, key, value)
                own = scenario != 'foreign-only'
                parts = list(self.parts)
                if own:
                    parts = parts[:2] + [call('q', 'query'), ret('q', 'query', POINTER)] + parts[2:]
                foreign = '/workspace/tool_results/query/expired.jsonl'
                messages = [{'turn_id': 'old', 'parts': [{'type': 'text', 'text': foreign}]},
                            {'turn_id': 't', 'parts': [{'type': 'text', 'text': 'Done'}]}]
                if scenario == 'own-collected':
                    messages[-1]['parts'].append({'type': 'tool-query', 'state': 'output-available',
                                                 'output': POINTER})
                h = history(parts)
                h['raw_model_messages'][0]['turn_id'] = 't'
                h['raw_model_messages'].insert(0, {'turn_id': 'old', 'parts': [ret('old', 'query', foreign)]})
                h['raw_ui_messages'] = messages
                timing = {'turns': [{'turn_id': 't', 'started_at': '2026-01-01T00:00:00',
                                     'completed_at': '2026-01-01T00:00:01'}]}
                z = archive(self.files)
                self.addCleanup(z.close)
                b = {'history': h, 'messages': messages, 'timing': timing, 'zip': z}
                client = FakeClient(messages)
                original_download = client.download

                def download(path, **kwargs):
                    if 'expired.jsonl' in path:
                        raise AssertionError('foreign receipt must never be downloaded')
                    return original_download(path, **kwargs)

                def response(method, path, **kwargs):
                    if path.endswith('/info'):
                        return 200, {'status': 'idle'}
                    if path.endswith('/timing'):
                        return 200, timing
                    if path.endswith('/messages'):
                        return 200, messages
                    raise AssertionError(path)

                client.download, client.json_call = download, response
                with patch.object(ts, 'assert_owned_project'), \
                     patch.object(ts, 'RUNS', str(self.root / 'no-prior-runs')), \
                     patch.object(ts, 'thread_bundle', return_value=b), \
                     patch.object(ts.ReceiptArchiver, 'start', lambda collector: collector.poll()), \
                     redirect_stdout(io.StringIO()):
                    code = ts.cmd_run(client, a)
                self.assertEqual(code, 3 if scenario == 'own-missed' else 0)
                saved = json.loads((out / 'run.json').read_text())
                self.assertEqual(saved['receipts']['turn_id'], 't')
                self.assertEqual(saved['receipts']['foreign_pointers'], [foreign])
                self.assertEqual(saved['receipts']['final_pointers'], [POINTER] if own else [])
                self.assertEqual(saved['receipts']['final_missing'], [POINTER] if scenario == 'own-missed' else [])
                self.assertEqual(client.downloads, 1 if scenario == 'own-collected' else 0)

    def test_refusal_cannot_borrow_prior_params_call(self):
        self.a.expect = 'refusal'
        self.files = {}
        self.parts = self.parts[:2] + [{'part_kind': 'text', 'content': 'Insufficient records.'}]
        h = history(self.parts)
        h['raw_model_messages'][0]['turn_id'] = 't'
        h['raw_model_messages'].insert(0, {'turn_id': 'old', 'parts': [call('q', 'query'), ret('q', 'query')]})
        h['raw_ui_messages'].append({'turn_id': 'old', 'parts': []})
        self.assertIn('refusal contract: the selection was actually queried', self.failures(h))
        self.parts.extend([call('current', 'query'), ret('current', 'query')])
        self.assertEqual(self.failures(), [])


class GateTests(OfflineCase):
    def test_no_comparable_samples_is_not_pass(self):
        gate = str(Path(__file__).with_name('verify-run-chain.py'))
        env = dict(os.environ, TOOLSMITH_RUNS=str(self.root), TOOLSMITH_PUBLISH=TOOL)
        result = subprocess.run([sys.executable, gate], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('NO SAMPLES', result.stdout)
        run = self.root / '20260101-v2'
        run.mkdir()
        (run / 'debug-history.json').write_text(json.dumps(history([])))
        (run / 'stream.tap').write_text('data: {"type":"data-turn-start"}\n')
        result = subprocess.run([sys.executable, gate], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('0 comparable', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
