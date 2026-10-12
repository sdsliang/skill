#!/usr/bin/env python3
"""Regression checks for the single runtime execution contract."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / 'skill/multi-clinical-result-comparison'


class WorkflowTests(unittest.TestCase):
    def test_all_instructions_use_review_interface(self):
        for path in [ROOT / 'system-prompts/multi-clinical-result-comparison-v0.16.md',
                     SKILL / 'SKILL.md', SKILL / 'references/toolbox.md']:
            with self.subTest(path=path.name):
                text = path.read_text()
                self.assertIn('--apply-review', text)
                self.assertIn('overwrite=True', text)
                self.assertIn('patch.py', text)
                self.assertIn('additions', text)

    def test_no_retired_timeline_encoding_instruction(self):
        for path in [ROOT / 'system-prompts/multi-clinical-result-comparison-v0.16.md', SKILL / 'SKILL.md']:
            text = path.read_text()
            self.assertNotRegex(text, r'maturity via weight|weightLegend|`weight`')
            self.assertNotIn('never patched', text)
            self.assertNotIn('re-issue the whole file', text)

    def test_quality_boundaries_remain(self):
        for path in [ROOT / 'system-prompts/multi-clinical-result-comparison-v0.16.md', SKILL / 'SKILL.md']:
            text = path.read_text()
            for term in ['R6', 'R7', 'drug_earth_name_cn', 'source quote', 'conclusion', 'present_artifact']:
                self.assertIn(term, text)
        prompt = (ROOT / 'system-prompts/multi-clinical-result-comparison-v0.16.md').read_text()
        self.assertIn('Every ledger fact must reach the appendix', prompt)
        self.assertIn('never hand-write or hand-edit it', prompt)
        self.assertIn('at most one fetch per record', prompt)


if __name__ == '__main__':
    unittest.main(verbosity=2)
