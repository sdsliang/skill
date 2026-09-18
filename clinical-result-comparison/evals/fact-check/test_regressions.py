#!/usr/bin/env python3
"""Permanent evaluator regressions. Synthetic bodies concern wooden blocks, not medicine."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import check as ck
import fulltext
import mutations as mut

HERE = Path(__file__).resolve().parent
ITEMS = {i['id']: i for i in json.loads((HERE/'scenario-a.facts.json').read_text())['items']}


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.art = Path(self.tmp.name)
        (self.art/'sources').mkdir()
        self.ctx = {'check': {'esids': ['test']}, 'fixture': {'response': {'result': {'data': [
            {'clinical_result_extra_esid': 'test',
             'clinical_result_full_article_link': 'https://pubmed.ncbi.nlm.nih.gov/12345678'}]}}}}
        self.sv = {'artifacts_dir': str(self.art), 'citations': {'ref_1': {
            'link': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC99999999/'}}}

    def put(self, text, name='PMC99999999_fulltext.xml'):
        (self.art/'sources'/name).write_text(text)

    def proven(self):
        return ck.op_fulltext_cite_has_body(self.sv, ITEMS['A-P9-fulltext-cite-has-body'], self.ctx)[0]

    def test_jats_valid_and_wrong_source(self):
        self.put(mut.ft_body('12345678', 'PMC99999999'))
        self.assertTrue(self.proven())
        self.put(mut.ft_body('87654321', 'PMC99999999'))
        self.assertFalse(self.proven())

    def test_empty_and_metadata_only(self):
        for body in ['', 'PMC99999999', '<article><front><article-meta><article-id pub-id-type="pmcid">PMC99999999</article-id><article-id pub-id-type="pmid">12345678</article-id></article-meta></front><body/></article>']:
            with self.subTest(body=body):
                self.put(body)
                self.assertFalse(self.proven())

    def test_reference_list_pmid_does_not_identify_article(self):
        body = mut.ft_body('87654321', 'PMC99999999').replace('</article>', '<back><ref-list><article-id pub-id-type="pmid">12345678</article-id></ref-list></back></article>')
        self.put(body)
        self.assertFalse(self.proven())

    def test_plaintext_needs_independent_mapping(self):
        body = 'PMC99999999\nMethods\n' + ('Wooden blocks are sorted by color and shape in this synthetic test. ' * 8) + '\nResults\nInventory completed.'
        self.put(body, 'PMC99999999_plain.txt')
        self.assertFalse(self.proven())
        self.put(json.dumps({'resultList': {'result': [{'source': 'MED', 'id': '12345678', 'pmcid': 'PMC99999999'}]}}), 'mapping.json')
        self.assertTrue(self.proven())

    def test_plaintext_header_cannot_self_corroborate(self):
        self.put('PMC99999999 PMID:12345678\nMethods\n' + 'x' * 200, 'PMC99999999_plain.txt')
        self.assertFalse(self.proven())
        body = fulltext.inspect(self.art/'sources/PMC99999999_plain.txt')
        self.assertEqual(body['pmid'], set())
        self.assertEqual(body['claimed_pmid'], {'12345678'})
        # A different mapping cannot corroborate this claimed source pair.
        self.put(json.dumps({'pmid': '87654321', 'pmcid': 'PMC99999999'}), 'mapping.json')
        self.assertFalse(self.proven())
        self.put(json.dumps({'pmid': '12345678', 'pmcid': 'PMC99999999'}), 'mapping.json')
        self.assertTrue(self.proven())

    def test_plaintext_fetch_corroboration_is_scoped_and_matches_source(self):
        self.put('PMC99999999 PMID:12345678\nMethods\n' + 'x' * 200, 'PMC99999999_plain.txt')
        self.sv['run_dir'] = str(self.art)
        (self.art/'run.json').write_text(json.dumps({'turn_id': 'target'}))
        receipt = {'part_kind': 'tool-return', 'tool_name': 'web_fetch',
                   'content': {'pmid': '12345678', 'pmcid': 'PMC99999999'}}
        def archive(part, turn='target'):
            (self.art/'debug-history.json').write_text(json.dumps({'raw_model_messages': [
                {'kind': 'request', 'turn_id': turn, 'parts': [part]}]}))
        archive(receipt)
        self.assertTrue(self.proven())
        archive(receipt, 'foreign')
        self.assertFalse(self.proven())
        archive({'part_kind': 'tool-return', 'tool_name': 'execute', 'content': receipt})
        self.assertFalse(self.proven())
        archive({**receipt, 'content': {'pmid': '87654321', 'pmcid': 'PMC99999999'}})
        self.assertFalse(self.proven())

    def test_plaintext_wrong_jats_content_stays_unmapped(self):
        self.put(mut.ft_body('12345678', 'PMC99999999'))
        self.put('PMC99999999 PMID:12345678\nMethods\n' + 'x' * 200, 'PMC99999999_plain.txt')
        _, bad = fulltext.attributed(self.sv, self.ctx)
        self.assertIn('PMC99999999_plain.txt', bad)

    def test_plaintext_derivative_with_jats(self):
        source = mut.ft_body('12345678', 'PMC99999999').replace('separately.', 'separately. ' * 20)
        self.put(source)
        import xml.etree.ElementTree as ET
        self.put(' '.join(ET.fromstring(source).itertext()), 'PMC99999999_plain.txt')
        byref, bad = fulltext.attributed(self.sv, self.ctx)
        self.assertEqual(bad, [])
        self.assertEqual(len(byref['ref_1']), 2)

    def test_abstract_json_is_not_body(self):
        self.put(json.dumps({'source': 'MED', 'id': '12345678', 'pmcid': 'PMC99999999', 'abstractText': 'Results: wooden blocks.'}), 'PMC99999999.json')
        self.assertFalse(self.proven())

    def test_wrong_deep_link(self):
        self.put(mut.ft_body('12345678', 'PMC88888888'))
        self.assertFalse(ck.op_cite_link_is_deepest(self.sv, {}, self.ctx)[0])


class TextTests(unittest.TestCase):
    def test_divergence(self):
        spec = ITEMS['A-P2-divergence-shows-both']
        for text, expected in [
            ('原文 36.0；库内记录 18.5{{ref_1}}。', True),
            ('原文 double-blinded；库内记录 开放{{ref_1}}。', True),
            ('（原文 double-blinded；库内记录 开放）{{ref_1}}。', True),
            ('原文；库内记录{{ref_1}}。', False),
            ('原文 36.0；库内记录 18.5。', False),
            ('原文 36.0；库内记录 18.5{{ref_1}}。库内记录 90。', False),
            ('原文 36.0；库内记录 18.5{{ref_1}}；库内记录 90{{ref_1}}。', False)]:
            with self.subTest(text=text):
                self.assertEqual(ck.eval_sent_if(spec, {'report': text})[0], expected)

    def test_unsigned_owner_and_numeric_boundaries(self):
        spec = ITEMS['A-ATTR-misattribution']
        for val, expected in [('70.5', False), ('+70.5', False), ('−70.5', False),
                              ('170.5', True), ('70.50', True), ('170.50', True)]:
            with self.subTest(value=val):
                self.assertEqual(ck.eval_attribution(spec, {'report': f'依洛尤单抗降低 {val}%{{{{ref_1}}}}。'})[0], expected)

    def test_verbatim_exact_threshold_and_unsampled_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'sources'; p.mkdir()
            fragment = ''.join(chr(0x4e00+i) for i in range(60))
            for prefix in ['', 'abc']:
                (p/'source.txt').write_text(prefix+fragment)
                self.assertFalse(ck.op_no_verbatim_copy({'artifacts_dir': tmp, 'report': fragment}, {'min_run': 60})[0])

    def test_empty_forbidden_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'output'; p.mkdir()
            for name in ['report.md', 'citations.json']:
                (p/name).write_text('')
            self.assertFalse(ck.op_artifact_absent({'_art': tmp}, {'files': ['output/report.md', 'output/citations.json']})[0])

    def test_unknown_citation_marker(self):
        self.assertFalse(ck.op_citations_keys_exact({'citations': {'ref_1': {}},
            'report': 'fact{{ref_1}}; bogus{{ref_9}}'}, {'keys': ['ref_1']})[0])

    def test_citation_null_not_nonempty_string(self):
        self.assertFalse(ck.op_citations_entry_key_set({'citations': {'ref_1': {'title': None}}}, {'refs': ['ref_1'], 'keys': ['title']})[0])


class ChartTests(unittest.TestCase):
    def setUp(self):
        # Nonclinical independent identity example: red/blue blocks, count at two times.
        self.spec = {'pattern': 'endpoint-bar-*.json', 'optional_when_absent': True,
            'observations': [
                {'identity_patterns': ['red', 'one', 'day 1'], 'report_identity_patterns': ['red', 'one'], 'endpoint_regex': 'count', 'owner': 'ref_1', 'value': -2},
                {'identity_patterns': ['blue', 'two', 'day 2'], 'report_identity_patterns': ['blue', 'two'], 'endpoint_regex': 'count', 'owner': 'ref_2', 'value': -4}]}
        self.chart = {'id': 'chart-visualization-json', 'iframe_template': 'https://example.invalid/chart',
                      'option': {'type': 'bar', 'title': 'count', 'data': [
                          {'label': 'red one day 1', 'description': 'count', 'value': -2},
                          {'label': 'blue two day 2', 'description': 'count', 'value': -4}]}}
        self.sv = {'charts': {'endpoint-bar-7.json': self.chart},
                   'report': 'red one count -2{{ref_1}}。\n\nblue two count -4{{ref_2}}。'}

    def check(self):
        return ck.op_chart_observations(self.sv, self.spec)[0]

    def test_order_independent(self):
        self.assertTrue(self.check())
        self.chart['option']['data'].reverse()
        self.assertTrue(self.check())

    def test_value_label_sign_time_endpoint_mutations(self):
        original = copy.deepcopy(self.chart['option']['data'])
        for key, value in [('value', 2), ('value', -4), ('label', 'blue two day 2'), ('label', 'red one day 2'), ('value', float('nan')), ('value', True)]:
            with self.subTest(key=key, value=value):
                self.chart['option']['data'] = copy.deepcopy(original)
                self.chart['option']['data'][0][key] = value
                self.assertFalse(self.check())

    def test_correct_description_cannot_hide_wrong_label(self):
        row = self.chart['option']['data'][0]
        row['description'] = 'red one day 1 count'
        for label in ['blue', 'two', 'day 2', 'red blue', 'red one day 2']:
            with self.subTest(label=label):
                row['label'] = label
                self.assertFalse(self.check())
        row['label'] = 'red'
        self.assertTrue(self.check())  # remaining identity is legally in description
        row['description'] += ' blue'
        self.assertFalse(self.check())

    def test_unsigned_equivalent(self):
        for row in self.chart['option']['data']:
            row['value'] = abs(row['value'])
        self.sv['report'] = 'red one count 降低 2{{ref_1}}。\n\nblue two count 降低 4{{ref_2}}。'
        self.assertTrue(self.check())

    def test_every_chart_including_unknown_names(self):
        spec = ITEMS['A-S2a-chart-structure']
        for name, chart in [('endpoint-line-4.json', {'option': {'type': 'line'}}), ('evidence-timeline.json', None), ('endpoint-bar-5.json', {**self.chart, 'option': {'data': [None]}})]:
            with self.subTest(name=name):
                self.sv['charts'] = {name: chart}
                self.assertFalse(ck.op_charts_structural(self.sv, spec)[0])

    def test_malformed_json_preserved_as_failed_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'artifacts/visualizations'; p.mkdir(parents=True)
            (p/'endpoint-bar-9.json').write_text('{broken')
            sv = ck.load_surfaces(tmp)
            self.assertIn('endpoint-bar-9.json', sv['charts'])
            self.assertFalse(ck.op_charts_structural(sv, ITEMS['A-S2a-chart-structure'])[0])
            self.assertFalse(ck.op_chart_observations(sv, self.spec)[0])


class HarnessTests(unittest.TestCase):
    def test_query_attempts_are_not_transcript_mentions(self):
        spec = {'tool': 'query', 'esid': 'dead-id', 'min_count': 2}
        with tempfile.TemporaryDirectory() as tmp:
            sv = {'run_dir': tmp, 'transcript': 'dead-id dead-id'}
            self.assertFalse(ck.op_query_attempts(sv, spec)[0])
            call = {'part_kind': 'tool-call', 'tool_name': 'query',
                    'tool_call_id': 'one', 'args': {'extra_esids': ['dead-id']}}
            path = Path(tmp)/'debug-history.json'
            def archive(parts):
                return {'raw_model_messages': [
                    {'kind': 'request', 'parts': [{'part_kind': 'user-prompt', 'content': 'query'}]},
                    {'kind': 'response', 'parts': parts}]}
            path.write_text(json.dumps(archive([call, call])))
            self.assertFalse(ck.op_query_attempts(sv, spec)[0])
            path.write_text(json.dumps(archive([call, {**call, 'tool_call_id': 'two'}])))
            self.assertTrue(ck.op_query_attempts(sv, spec)[0])

    def test_query_current_legacy_and_counterfeit_scope(self):
        spec = {'tool': 'query', 'esid': 'dead-id', 'min_count': 2}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sv = {'run_dir': tmp}
            calls = [{'part_kind': 'tool-call', 'tool_name': 'query', 'tool_call_id': str(i),
                      'args': {key: ['dead-id']}} for i, key in enumerate(['esids', 'extra_esids'])]
            response = {'kind': 'response', 'turn_id': 'target', 'parts': calls}
            root.joinpath('run.json').write_text(json.dumps({'turn_id': 'target'}))
            def check(messages):
                root.joinpath('debug-history.json').write_text(json.dumps({'raw_model_messages': messages}))
                return ck.op_query_attempts(sv, spec)[0]
            self.assertTrue(check([response]))
            self.assertFalse(check([{**response, 'turn_id': 'foreign'}]))
            self.assertFalse(check([{**response, 'parts': [calls[0]]},
                                    {**response, 'turn_id': 'foreign', 'parts': [calls[1]]}]))
            self.assertFalse(check([{'kind': 'request', 'turn_id': 'target', 'parts': [
                {'part_kind': 'tool-return', 'content': calls}]}]))
            self.assertFalse(check([{**response, 'parts': [], 'payload': calls}]))
            self.assertFalse(check([{**response, 'turn_id': None}]))
            root.joinpath('run.json').unlink()
            self.assertFalse(check([response, {**response, 'turn_id': 'foreign'}]))

    def test_query_ambiguous_legacy_and_argument_shapes(self):
        spec = {'tool': 'query', 'esid': 'dead-id', 'min_count': 1}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            call = {'part_kind': 'tool-call', 'tool_name': 'query', 'tool_call_id': 'one'}
            prompt = {'kind': 'request', 'parts': [{'part_kind': 'user-prompt', 'content': 'query'}]}
            def check(args, extra_prompt=False):
                messages = [prompt, {'kind': 'response', 'parts': [{**call, 'args': args}]}]
                if extra_prompt:
                    messages.append(prompt)
                root.joinpath('debug-history.json').write_text(json.dumps({'raw_model_messages': messages}))
                return ck.op_query_attempts({'run_dir': tmp}, spec)[0]
            self.assertTrue(check(json.dumps({'esids': ['dead-id']})))
            self.assertFalse(check({'esids': 'dead-id'}))
            self.assertFalse(check({'esids': ['dead-id-extra']}))
            self.assertFalse(check({'esids': ['other'], 'extra_esids': ['dead-id']}))
            self.assertFalse(check({'esids': ['dead-id']}, extra_prompt=True))

    def test_query_legacy_ui_timestamp_maps_target_turn(self):
        spec = {'tool': 'query', 'esid': 'dead-id', 'min_count': 2}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath('run.json').write_text(json.dumps({'turn_id': 'target'}))
            call = {'part_kind': 'tool-call', 'tool_name': 'query',
                    'tool_call_id': 'one', 'args': {'esids': ['dead-id']}}
            history = {'raw_model_messages': [
                {'kind': 'response', 'timestamp': 't1', 'parts': [call]},
                {'kind': 'response', 'timestamp': 't2', 'parts': [{**call, 'tool_call_id': 'two'}]}],
                'raw_ui_messages': [
                    {'turn_id': turn, 'metadata': {'pydantic_ai': {'timestamp': timestamp}}}
                    for turn, timestamp in [('target', 't1'), ('foreign', 't2')]]}
            def check():
                root.joinpath('debug-history.json').write_text(json.dumps(history))
                return ck.op_query_attempts({'run_dir': tmp}, spec)[0]
            self.assertFalse(check())
            history['raw_ui_messages'][1]['turn_id'] = 'target'
            self.assertTrue(check())
            history['raw_ui_messages'].append({'turn_id': 'foreign',
                'metadata': {'pydantic_ai': {'timestamp': 't1'}}})
            self.assertFalse(check())


    def test_missing_both_baselines_cannot_pass(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, 'MUT_RUN_A': tmp+'/missing-a', 'MUT_RUN_B': tmp+'/missing-b', 'MUT_WORK': tmp+'/work'}
            p = subprocess.run([sys.executable, str(HERE/'mutations.py')], env=env, capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('GATE: FAIL', p.stdout)
            self.assertNotIn('GATE: PASS', p.stdout)


if __name__ == '__main__':
    unittest.main()
