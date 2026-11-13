"""全池发现机制测试；全部证据为临时测试数据，不作真实覆盖证明。"""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

here = Path(__file__).resolve()
source = here.parent / "earnings_discovery.py"
if not source.exists():
    source = here.parents[1] / "scripts/earnings_discovery.py"
spec = importlib.util.spec_from_file_location("earnings_discovery", source)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 10, 11, 10, tzinfo=timezone.utc)
        self.d = m.Discovery(self.root, self.now)
        self.codes = ["600000.SH", "00001.HK", "AAA.US"]
        for file, code in zip(m.POOL_FILES, self.codes):
            m.atomic_json(self.root / "data" / file, {"entries": [{"name": code, "code": code, "lastEarningsIncorporated": "2026Q1"}]})
        self.old_entry = {"id": "historical", "code": "OLD.US", "status": "completed", "notes": "保留原记录"}
        m.atomic_json(self.d.queue_path, {"entries": [self.old_entry], "policy": {"queue_before_full_scan": True}, "scan": {"official_disclosure_scan_complete": False}})
        self.q = {"source": "official account/rateLimits/read ordinary user", "checked_at": self.now.isoformat(), "ordinaryUsageAllowed": True,
                  "rateLimits": {"limitId": "codex", "primary": {"usedPercent": 0, "windowDurationMins": 10080}}}

    def observation(self, code, new=False):
        host = {"CN": "cninfo.com.cn", "HK": "hkexnews.hk", "US": "sec.gov"}[m.market(code)]
        url = "https://" + host + "/test?company=" + code
        p = self.d.directory / "evidence" / self.d.day / (code + ".txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("合成测试证据 " + code, encoding="utf-8")
        return {"code": code, "status": "verified_new_report" if new else "verified_no_update", "checked_at": self.now.isoformat(),
                "method": "official_document_read", "comparison_basis": "测试期次比较",
                "latest_report": {"period": "2026Q2" if new else "2026Q1", "period_end": "2026-06-30" if new else "2026-03-31", "disclosure_date": "2026-08-01", "official_url": url},
                "official_sources": [{"company_code": code, "url": url, "authority": "exchange" if host != "sec.gov" else "regulator", "locator": "测试发行人和全目录", "evidence_path": str(p.relative_to(self.root)), "sha256": m.digest(p)}]}

    def failed(self, code):
        return {"code": code, "status": "failed", "checked_at": self.now.isoformat(), "failure": "官方请求失败（测试）"}

    def test_cn_report_titles_do_not_skip_short_quarter_names(self):
        for title, expected in [
            ("2026年三季度报告", ("2026Q3", "2026-09-30")),
            ("2026年第三季度报告", ("2026Q3", "2026-09-30")),
            ("法拉电子2026年三季度报告", ("2026Q3", "2026-09-30")),
            ("2026年一季度报告", ("2026Q1", "2026-03-31")),
            ("2026年第一季度报告", ("2026Q1", "2026-03-31")),
            ("2026年半年度报告", ("2026H1", "2026-06-30")),
            ("2025年年度报告", ("2025FY", "2025-12-31")),
            ("2026年三季度报告摘要", None),
            ("2026年第三季度报告（英文版）", None),
        ]:
            with self.subTest(title=title):
                self.assertEqual(m.parse_cn_report_title(title), expected)
        with self.assertRaises(ValueError):
            m.parse_cn_report_title("2026年第四季度报告")

    def test_plan_ignores_queue_and_completed_day(self):
        q = m.read(self.d.queue_path)
        q["entries"].append({"id": "pending", "status": "pending", "code": "AAA.US"})
        q["last_completed_beijing_day"] = self.d.day
        m.atomic_json(self.d.queue_path, q)
        p = self.d.plan(self.q)
        self.assertEqual({x["code"] for x in p["checks_required"]}, set(self.codes))
        self.assertFalse(p["coverage"]["complete"])
        self.assertTrue(all(x["checked_at"] is None and x["last_verified_at"] is None for x in p["checks_required"]))
        self.assertFalse(m.read(self.d.queue_path)["policy"]["queue_before_full_scan"])

    def test_success_all_markets_and_preserve_history(self):
        self.d.plan(self.q)
        result = self.d.record([self.observation(c) for c in self.codes], self.q)
        self.assertTrue(result["coverage"]["complete"])
        self.assertEqual(result["coverage"]["verified"], 3)
        self.assertEqual(m.read(self.d.queue_path)["entries"], [self.old_entry])
        self.assertEqual(m.read(self.d.queue_path)["scan"], {"official_disclosure_scan_complete": False})

    def test_failures_unchecked_and_resume(self):
        self.d.plan(self.q)
        r = self.d.record([self.observation(self.codes[0]), self.failed(self.codes[1])], self.q)
        self.assertFalse(r["coverage"]["complete"])
        self.assertEqual(r["coverage"]["by_market"]["HK"]["failed"], 1)
        self.assertIn(self.codes[1], r["coverage"]["failure_reasons"])
        self.assertEqual(r["coverage"]["unchecked"], [self.codes[2]])
        self.assertEqual(len(self.d.plan(self.q)["checks_required"]), 2)
        self.assertIsNone(self.d.select(self.q)["candidate"])

    def test_next_day_full_pool_legitimate_anchor(self):
        self.d.record([self.observation(c) for c in self.codes], self.q)
        d = m.Discovery(self.root, self.now + timedelta(days=1))
        quota = copy.deepcopy(self.q); quota["checked_at"] = d.now.isoformat()
        p = d.plan(quota)
        self.assertEqual(len(p["checks_required"]), 3)
        self.assertEqual(p["coverage"]["verified"], 0)
        self.assertTrue(all(x["last_verified_at"] == self.now.isoformat() and x["checked_at"] is None for x in p["checks_required"]))

    def test_pool_change_and_none_exclusion(self):
        self.d.record([self.observation(c) for c in self.codes], self.q)
        m.atomic_json(self.root / "data/watchlist_out_of_scope.json", {"entries": [{"code": "NONE.US", "name": "NONE"}]})
        p = self.root / "data/watchlist_growth.json"
        m.atomic_json(p, {"entries": [{"code": "BBB.US", "name": "new"}]})
        c = self.d.status()["coverage"]
        self.assertEqual(c["total"], 3)
        self.assertEqual(c["unchecked"], ["BBB.US"])
        self.assertFalse(c["complete"])

    def test_invalid_success_evidence_atomic(self):
        self.d.plan(self.q)
        before = m.digest(self.d.path)
        for field in ["missing", "wronghash", "wrongissuer", "wronghost", "outside", "future", "credential"]:
            a = self.observation(self.codes[1]); s = a["official_sources"][0]
            if field == "missing": a["official_sources"] = []
            if field == "wronghash": s["sha256"] = "0"
            if field == "wrongissuer": s["company_code"] = "AAA.US"
            if field == "wronghost": s["url"] = "https://example.com/report"
            if field == "outside": s["evidence_path"] = "../auth.json"
            if field == "future": a["checked_at"] = (self.now + timedelta(days=1)).isoformat()
            if field == "credential": s["url"] += "&api_key=test"
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.d.record([self.observation(self.codes[0]), a], self.q)
            self.assertEqual(m.digest(self.d.path), before)

    def test_enqueue_dedup_and_recovery(self):
        a = self.observation(self.codes[2], True)
        original = self.d.enqueue
        self.d.enqueue = lambda data: (_ for _ in ()).throw(RuntimeError("模拟保存台账后中断"))
        with self.assertRaises(RuntimeError): self.d.record([a], self.q)
        self.d.enqueue = original
        self.d.plan(self.q)
        self.d.record([a], self.q)
        entries = m.read(self.d.queue_path)["entries"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0], self.old_entry)
        self.assertEqual(entries[1]["status"], "pending")

    def test_select_serially_without_daily_count_cap(self):
        self.d.record([self.observation(c, True) for c in self.codes], self.q)
        s = self.d.select(self.q)
        self.assertIsInstance(s["candidate"], dict)
        q = m.read(self.d.queue_path)
        first = next(e for e in q["entries"] if e["id"] == s["candidate"]["id"])
        first.update(status="completed", completed_beijing_date=self.d.day)
        q["last_completed_beijing_day"] = self.d.day
        m.atomic_json(self.d.queue_path, q)
        second = self.d.select(self.q)["candidate"]
        self.assertIsNotNone(second)
        self.assertNotEqual(first["id"], second["id"])
        next(e for e in q["entries"] if e["id"] == second["id"]).update(
            status="completed", completed_at=self.now.isoformat())
        m.atomic_json(self.d.queue_path, q)
        third = self.d.select(self.q)["candidate"]
        self.assertIsNotNone(third)
        next(e for e in q["entries"] if e["id"] == third["id"]).update(
            status="completed", completed_beijing_date=self.d.day)
        m.atomic_json(self.d.queue_path, q)
        self.assertIsNone(self.d.select(self.q)["candidate"])
        self.assertTrue(self.d.plan(self.q)["coverage"]["complete"])
        self.assertIsNone(q["policy"]["max_company_updates_per_run"])
        self.assertIsNone(q["policy"]["max_company_updates_per_beijing_day"])
        self.assertEqual(q["policy"]["weekly_remaining_must_exceed_percent"], 20)

    def test_failed_checks_warning_not_completion(self):
        self.d.record([self.observation(self.codes[0], True), self.failed(self.codes[1]), self.failed(self.codes[2])], self.q)
        s = self.d.select(self.q)
        self.assertTrue(s["coverage_warning"])
        self.assertIsNotNone(s["candidate"])

    def test_incremental_needs_true_anchor(self):
        a = self.observation(self.codes[0]); a["method"] = "official_incremental_check"; a["since"] = self.now.isoformat()
        with self.assertRaises(ValueError): self.d.record([a], self.q)
        self.d.record([self.observation(self.codes[0])], self.q)
        self.d.record([a], self.q)

    def test_quota_strict_and_fresh(self):
        for change in ["twenty", "below_twenty", "stale", "wrongwindow", "wrongsource", "denied"]:
            q = copy.deepcopy(self.q)
            if change == "twenty": q["rateLimits"]["primary"]["usedPercent"] = 80
            if change == "below_twenty": q["rateLimits"]["primary"]["usedPercent"] = 81
            if change == "stale": q["checked_at"] = (self.now-timedelta(hours=2)).isoformat()
            if change == "wrongwindow": q["rateLimits"]["primary"]["windowDurationMins"] = 300
            if change == "wrongsource": q["source"] = "inferred"
            if change == "denied": q["ordinaryUsageAllowed"] = False
            with self.subTest(change=change), self.assertRaises(ValueError): self.d.plan(q)
        q = copy.deepcopy(self.q); q["rateLimits"]["primary"]["usedPercent"] = 79
        self.d.plan(q)

    def test_locks_block_overlap(self):
        with m.run_lock(self.root):
            with self.assertRaises(RuntimeError): self.d.plan(self.q)
        m.atomic_json(self.root / "data/reviews/earnings-update-active.lock.json", {"test": True})
        with self.assertRaises(RuntimeError): self.d.plan(self.q)

    def test_updated_baseline_prevents_stale_selection(self):
        self.d.record([self.observation(c, True) for c in self.codes], self.q)
        for f in m.POOL_FILES:
            p = self.root / "data" / f; v = m.read(p); v["entries"][0]["lastEarningsIncorporated"] = "2026Q2"; m.atomic_json(p, v)
        self.assertIsNone(self.d.select(self.q)["candidate"])

    def test_full_189_company_day_without_rotation(self):
        codes = [f"{600000+i}.SH" for i in range(69)] + [f"{i+1:05}.HK" for i in range(33)] + [f"TEST{i}.US" for i in range(87)]
        for f, group in zip(m.POOL_FILES, [codes[:2], codes[2:96], codes[96:]]):
            m.atomic_json(self.root / "data" / f, {"entries": [{"name": c, "code": c, "lastEarningsIncorporated": "2026Q1"} for c in group]})
        p = self.d.plan(self.q)
        self.assertEqual(len(p["checks_required"]), 189)
        self.assertEqual([p["coverage"]["by_market"][k]["total"] for k in ["CN", "HK", "US"]], [69, 33, 87])
        r = self.d.record([self.observation(c) for c in codes], self.q)
        self.assertTrue(r["coverage"]["complete"])
        tomorrow = m.Discovery(self.root, self.now + timedelta(days=1))
        q = copy.deepcopy(self.q); q["checked_at"] = tomorrow.now.isoformat()
        self.assertEqual(len(tomorrow.plan(q)["checks_required"]), 189)


if __name__ == "__main__":
    unittest.main()
