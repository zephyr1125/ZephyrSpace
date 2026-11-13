"""Offline synthetic tests; never invoke the real project selector or queue."""
import copy
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).with_name('earnings_discovery.py')
if not source.exists():
    source = Path(__file__).resolve().parents[1] / 'scripts/earnings_discovery.py'
spec = importlib.util.spec_from_file_location('priority_test_source', source)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

base_spec = importlib.util.spec_from_file_location('discovery_fixtures', Path(__file__).with_name('test_earnings_discovery.py'))
base = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(base)


class PriorityTests(unittest.TestCase):
    def setUp(self):
        self.entries = [dict(id=c+'|Q3', code=c, discovered_at=str(i))
                        for i, c in enumerate(['A.US', 'B.US', 'C.US', 'D.US', 'E.US'])]

    def test_priority_only_reorders_eligible_and_preserves_fallback(self):
        order = ['EXCLUDED.US|Q3', 'C.US|Q3', 'C.US|Q3', 'A.US|Q3']
        self.assertEqual([e['code'] for e in m.prioritize_candidates(self.entries, order)],
                         ['C.US', 'A.US', 'B.US', 'D.US', 'E.US'])

    def test_three_tiers_overlap_stability_missing_and_no_mutation(self):
        before = copy.deepcopy(self.entries)
        result = m.preview_three_tier_order(
            self.entries, ['B.US', 'B.US'], ['A.US|Q3', 'B.US|Q3'],
            {'A.US': (1, 1), 'C.US': (80.5, 80), 'D.US': (81, 79.5)})
        self.assertEqual(result['priority_order'], ['B.US|Q3', 'A.US|Q3', 'C.US|Q3', 'D.US|Q3', 'E.US|Q3'])
        self.assertEqual(result['groups']['missing_scores'], ['E.US|Q3'])
        self.assertFalse(result['holdings_complete'])
        self.assertEqual(self.entries, before)

    def test_invalid_scores_last_and_duplicate_candidate_rejected(self):
        scores = {'A.US': (True, 90), 'B.US': (float('nan'), 80), 'C.US': (None, 80),
                  'D.US': (80, 80), 'E.US': (81, 80)}
        result = m.preview_three_tier_order(self.entries, [], [], scores, holdings_complete=True)
        self.assertEqual(result['priority_order'], ['E.US|Q3', 'D.US|Q3', 'A.US|Q3', 'B.US|Q3', 'C.US|Q3'])
        self.assertTrue(result['holdings_complete'])
        with self.assertRaises(ValueError):
            m.preview_three_tier_order(self.entries + self.entries[:1], [], [], scores)


class SelectorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = base.DiscoveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_synthetic_selector_priority_keeps_quota_lock_and_completion_gates(self):
        f = self.fixture
        f.d.record([f.observation(c, True) for c in f.codes], f.q)
        queue = base.m.read(f.d.queue_path)
        picked = next(e for e in queue['entries'] if e.get('code') == 'AAA.US')
        queue['user_priority_order'] = ['historical', picked['id']]
        base.m.atomic_json(f.d.queue_path, queue)
        self.assertEqual(f.d.select(f.q)['candidate']['id'], picked['id'])
        low = copy.deepcopy(f.q)
        low['rateLimits']['primary']['usedPercent'] = 80
        with self.assertRaises(ValueError):
            f.d.select(low)
        lock = f.root / 'data/reviews/earnings-update-active.lock.json'
        base.m.atomic_json(lock, {'synthetic_test': True})
        self.assertIsNone(f.d.select(f.q)['candidate'])
        lock.unlink()
        picked['status'] = 'completed'
        base.m.atomic_json(f.d.queue_path, queue)
        self.assertNotEqual(f.d.select(f.q)['candidate']['id'], picked['id'])


if __name__ == '__main__':
    unittest.main()
