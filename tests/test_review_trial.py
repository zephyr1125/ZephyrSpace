"""验证冻结校验、匿名来源隔离和缺陷并集统计。"""
import importlib.util
import json
import random
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('trial', Path(__file__).parents[1] / 'scripts/review_trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class TrialTests(unittest.TestCase):
    def test_anonymous_metadata_and_duplicate_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = {}
            for reviewer in ['codex_a', 'codex_b', 'flash']:
                source = root / (reviewer + '.json')
                finding = dict(severity='P1', location='报告L1', claim='单位错误', evidence='原文L2', impact='十倍差', recommendation='更正')
                source.write_text(json.dumps({'model': reviewer, 'result': {'findings': [finding]}}))
                sources[reviewer] = str(source)
            trial.anonymize(sources, root / 'blind', random.Random(1))
            candidates = trial.read(root / 'blind/candidates.json')
            self.assertNotIn('flash', json.dumps(candidates))
            self.assertNotIn('model', json.dumps(candidates))
            mapping = trial.read(root / 'blind/unblinding.json')
            judgments = [dict(id=x['id'], outcome='valid', kind='error', group='D1', severity='P1') for x in candidates]
            result = trial.metrics(candidates, judgments, mapping)
            self.assertEqual(len(result['confirmed_union']), 1)
            self.assertEqual(result['combinations']['codex_pair']['missed'], {})
            extra = [dict(id=candidates[0]['id'], group='D2', severity='P2')]
            expanded = trial.metrics(candidates, judgments, mapping, extra)
            self.assertEqual(len(expanded['confirmed_union']), 2)
            self.assertEqual(sum(x['correction_claims'] for x in expanded['reviewers'].values()), 3)
            with self.assertRaises(ValueError):
                trial.metrics(candidates, judgments, mapping, [dict(id='不存在', group='D2', severity='P2')])
            with self.assertRaises(ValueError):
                trial.metrics(candidates, judgments[:-1], mapping)

    def test_changed_frozen_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'e.md').write_text('原始证据')
            (root / 'm.json').write_text(json.dumps(dict(rules=['e.md'], evidence=['e.md'], drafts=['e.md'])))
            trial.freeze([root / 'm.json'], root / 'freeze.json', root)
            trial.verify(root / 'freeze.json', root)
            (root / 'e.md').write_text('被修改')
            with self.assertRaises(ValueError):
                trial.verify(root / 'freeze.json', root)


if __name__ == '__main__':
    unittest.main()
