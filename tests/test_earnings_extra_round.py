"""Synthetic quota/registry tests. No actual Codex RPC or production root."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).with_name('earnings_discovery.py')
if not source.exists():
    source = Path(__file__).resolve().parents[1] / 'scripts/earnings_discovery.py'
spec = importlib.util.spec_from_file_location('extra_round_test_source', source)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ExtraRoundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 11, 4, 3, 9, 44, tzinfo=timezone.utc)
        self.reset = int((self.now + timedelta(hours=4)).timestamp())
        self.q = {'source': 'official account/rateLimits/read ordinary user',
                  'checked_at': self.now.isoformat(), 'ordinaryUsageAllowed': True,
                  'rateLimits': {'limitId': 'codex', 'primary': {
                      'usedPercent': 81, 'windowDurationMins': 10080, 'resetsAt': self.reset},
                      'secondary': None, 'spendControlReached': False}}

    def test_normal_19_20_rejected_above_20_allowed_without_reset(self):
        for used in [81, 80]:
            self.q['rateLimits']['primary']['usedPercent'] = used
            with self.subTest(used=used), self.assertRaises(ValueError):
                m.quota_gate(self.q, self.now)
        self.q['rateLimits']['primary']['usedPercent'] = 79
        del self.q['rateLimits']['primary']['resetsAt']
        self.assertEqual(m.quota_gate(self.q, self.now)['remaining_percent'], 21)

    def test_extra_19_permitted_registered_resumed_and_no_default_bypass(self):
        record = m.start_extra_round(self.root, self.q, self.now)
        d = m.Discovery(self.root, self.now, quota_mode='pre-reset-extra', extra_run_id=record['run_id'])
        self.assertEqual(d.check_quota(self.q)['remaining_percent'], 19)
        self.assertTrue(m.extra_registry_path(self.root).exists())
        with self.assertRaises(ValueError):
            m.Discovery(self.root, self.now).check_quota(self.q)
        with self.assertRaises(ValueError):
            m.Discovery(self.root, self.now, quota_mode='pre-reset-extra').check_quota(self.q)
        with self.assertRaises(ValueError):
            m.Discovery(self.root, self.now, extra_run_id=record['run_id']).check_quota(self.q)

    def test_start_too_early_exact_reset_and_late_rejected_without_claim(self):
        for when in [self.now - timedelta(seconds=1), self.now + timedelta(hours=4),
                     self.now + timedelta(hours=4, seconds=1)]:
            q = copy.deepcopy(self.q); q['checked_at'] = when.isoformat()
            with self.subTest(when=when), self.assertRaises(ValueError):
                m.start_extra_round(self.root, q, when)
            self.assertFalse(m.extra_registry_path(self.root).exists())

    def test_duplicate_claim_cannot_restart_even_after_close(self):
        record = m.start_extra_round(self.root, self.q, self.now)
        with self.assertRaises(ValueError):
            m.start_extra_round(self.root, self.q, self.now)
        m.finish_extra_round(self.root, record['run_id'], self.now, 'blocked')
        with self.assertRaises(ValueError):
            m.start_extra_round(self.root, self.q, self.now)
        with self.assertRaises(ValueError):
            m.Discovery(self.root, self.now, quota_mode='pre-reset-extra', extra_run_id=record['run_id']).check_quota(self.q)

    def test_read_failure_stale_provider_denial_exhaustion_bad_reset_rejected(self):
        with self.assertRaises(ValueError): m.start_extra_round(self.root, None, self.now)
        for change in ['source', 'missing_time', 'stale', 'future', 'ordinary_denied', 'spend',
                       'service_limit', 'zero', 'reset_missing', 'reset_boolean', 'window',
                       'used_nan', 'used_boolean', 'prewindow_snapshot']:
            q = copy.deepcopy(self.q)
            if change == 'source': q['source'] = 'failed_read'
            if change == 'missing_time': del q['checked_at']
            if change == 'stale': q['checked_at'] = (self.now - timedelta(hours=2)).isoformat()
            if change == 'future': q['checked_at'] = (self.now + timedelta(seconds=1)).isoformat()
            if change == 'ordinary_denied': q['ordinaryUsageAllowed'] = False
            if change == 'spend': q['rateLimits']['spendControlReached'] = True
            if change == 'service_limit': q['rateLimits']['rateLimitReachedType'] = 'weekly'
            if change == 'zero': q['rateLimits']['primary']['usedPercent'] = 100
            if change == 'reset_missing': del q['rateLimits']['primary']['resetsAt']
            if change == 'reset_boolean': q['rateLimits']['primary']['resetsAt'] = True
            if change == 'window': q['rateLimits']['primary']['windowDurationMins'] = 300
            if change == 'used_nan': q['rateLimits']['primary']['usedPercent'] = float('nan')
            if change == 'used_boolean': q['rateLimits']['primary']['usedPercent'] = True
            if change == 'prewindow_snapshot': q['checked_at'] = (self.now - timedelta(seconds=1)).isoformat()
            with self.subTest(change=change), self.assertRaises((ValueError, KeyError)):
                m.start_extra_round(self.root, q, self.now)
            self.assertFalse(m.extra_registry_path(self.root).exists())

    def test_reset_ends_exception_new_week_normal_threshold_and_new_claim(self):
        record = m.start_extra_round(self.root, self.q, self.now)
        after = self.now + timedelta(hours=4)
        q = copy.deepcopy(self.q); q['checked_at'] = after.isoformat()
        q['rateLimits']['primary'].update(usedPercent=0, resetsAt=self.reset + 604800)
        d = m.Discovery(self.root, after, quota_mode='pre-reset-extra', extra_run_id=record['run_id'])
        with self.assertRaises(ValueError): d.check_quota(q)
        self.assertEqual(m.Discovery(self.root, after).check_quota(q)['remaining_percent'], 100)
        q['rateLimits']['primary']['usedPercent'] = 81
        with self.assertRaises(ValueError): m.Discovery(self.root, after).check_quota(q)
        # The old claim remains; a different official week gets its own one-time claim.
        next_start = self.now + timedelta(days=7); q['checked_at'] = next_start.isoformat()
        next_record = m.start_extra_round(self.root, q, next_start)
        self.assertNotEqual(record['cycle_id'], next_record['cycle_id'])
        self.assertNotEqual(record['run_id'], next_record['run_id'])

    def test_cycle_changed_inside_window_cannot_reuse_old_run(self):
        record = m.start_extra_round(self.root, self.q, self.now)
        q = copy.deepcopy(self.q); q['rateLimits']['primary']['resetsAt'] -= 1
        with self.assertRaises(ValueError):
            m.Discovery(self.root, self.now, quota_mode='pre-reset-extra', extra_run_id=record['run_id']).check_quota(q)

    def test_closeout_after_exhaustion_or_reset_does_not_need_quota(self):
        record = m.start_extra_round(self.root, self.q, self.now)
        after = self.now + timedelta(hours=5)
        result = m.finish_extra_round(self.root, record['run_id'], after, 'quota_exhausted')
        self.assertEqual(result['state'], 'closed')
        self.assertEqual(result['stop_reason'], 'quota_exhausted')

    def test_existing_company_slot_prevents_claim(self):
        slot = self.root / 'data/reviews/earnings-research-slots/AAA.US.lock.json'
        m.atomic_json(slot, {'synthetic': True})
        with self.assertRaises(RuntimeError): m.start_extra_round(self.root, self.q, self.now)
        self.assertFalse(m.extra_registry_path(self.root).exists())

    def test_short_window_exhaustion_not_exempt_and_week_can_be_secondary(self):
        q = copy.deepcopy(self.q)
        q['rateLimits']['secondary'] = {'usedPercent': 100, 'windowDurationMins': 300}
        with self.assertRaises(ValueError): m.start_extra_round(self.root, q, self.now)
        q['rateLimits']['secondary']['usedPercent'] = 10
        q['rateLimits']['primary'], q['rateLimits']['secondary'] = q['rateLimits']['secondary'], q['rateLimits']['primary']
        record = m.start_extra_round(self.root, q, self.now)
        self.assertEqual(record['resets_at'], self.reset)

    def test_extra_discovery_uses_registered_gate_and_preserves_queue_policy(self):
        fixture_spec = importlib.util.spec_from_file_location('extra_fixture', Path(__file__).with_name('test_earnings_discovery.py'))
        fixture_module = importlib.util.module_from_spec(fixture_spec)
        fixture_spec.loader.exec_module(fixture_module)
        f = fixture_module.DiscoveryTests(); f.setUp(); self.addCleanup(f.doCleanups)
        q = copy.deepcopy(f.q)
        q['rateLimits']['primary'].update(usedPercent=81, resetsAt=int((f.now + timedelta(hours=2)).timestamp()))
        run = m.start_extra_round(f.root, q, f.now)
        d = m.Discovery(f.root, f.now, quota_mode='pre-reset-extra', extra_run_id=run['run_id'])
        self.assertEqual(d.plan(q)['coverage']['total'], 3)
        self.assertIsNone(d.select(q)['candidate'])  # Actual discovery remains mandatory.
        d.record([f.observation(c, True) for c in f.codes], q)
        self.assertIsNotNone(d.select(q)['candidate'])
        queue = m.read(d.queue_path)
        self.assertEqual(queue['policy']['weekly_remaining_must_exceed_percent'], 20)
        with self.assertRaises(ValueError): m.Discovery(f.root, f.now).select(q)


if __name__ == '__main__':
    unittest.main()
