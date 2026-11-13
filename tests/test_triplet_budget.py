"""预算准入、在途余量、未知计量和单次累计的确定性回归。"""
import copy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import threading
import unittest

from scripts import triplet_budget as budget


class BudgetTests(unittest.TestCase):
    def test_initial_sample_wait_retains_unknown_and_stops_on_real_limit(self):
        ticks = [0.0]
        pending = {"status": "stop_required", "reasons": ["terra计量未知：尚无可信用量快照"], "used_known": 10000}
        limit = {"status": "stop_required", "reasons": ["terra达到提前停止线"], "used_known": 90000}
        results = iter([pending, limit])
        result = budget.initial_sample({}, {}, 'terra', 20, observer=lambda *_: next(results),
                                       clock=lambda: ticks[0], sleeper=lambda n: ticks.__setitem__(0, ticks[0]+n))
        self.assertEqual(result['status'], 'stop_required')
        self.assertEqual(result['used_known'], 90000)
        self.assertEqual(ticks[0], 1)

    def test_initial_sample_timeout_never_reports_ready_or_zero_usage(self):
        ticks = [0.0]
        def pending(*_):
            return {"status": "stop_required", "reasons": ["terra计量未知：尚无可信用量快照"],
                    "used_known": 10000, "interrupt_thread_ids": ["child"]}
        result = budget.initial_sample({}, {}, 'terra', 3, observer=pending,
                                       clock=lambda: ticks[0], sleeper=lambda n: ticks.__setitem__(0, ticks[0]+n))
        self.assertEqual(result['status'], 'stop_required')
        self.assertEqual(result['used_known'], 10000)
        self.assertEqual(result['interrupt_thread_ids'], ['child'])
        self.assertEqual(ticks[0], 3)

    def test_initial_sample_arrival_allows_ready_but_other_unknown_does_not_wait(self):
        ticks = [0.0]
        results = iter([{"status": "stop_required", "reasons": ["terra计量未知：尚无可信用量快照"]},
                        {"status": "ready", "reasons": [], "used_known": 20000}])
        result = budget.initial_sample({}, {}, 'terra', 20, observer=lambda *_: next(results),
                                       clock=lambda: ticks[0], sleeper=lambda n: ticks.__setitem__(0, ticks[0]+n))
        self.assertEqual(result['status'], 'ready')
        result = budget.initial_sample({}, {}, 'terra', 20,
                    observer=lambda *_: {"status": "stop_required", "reasons": ["身份不符"]},
                    clock=lambda: ticks[0], sleeper=lambda _: self.fail('不应等待身份错误'))
        self.assertEqual(result['initial_sample_wait_seconds'], 0)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = datetime(2026, 9, 27, 12, 0, 10, tzinfo=timezone.utc)
        self.config = {"schema_version": 1, "root_thread_id": "root", "root_log": str(self.root / "root.jsonl"),
                       "since": "2026-09-27T12:00:01Z", "total_limit": 200000, "coordinator_limit": 40000,
                       "closeout_reserve": 30000, "inflight_reserve": 15000, "max_active": 1, "stale_seconds": 30,
                       "roles": {"terra": 85000, "sol": 85000},
                       "groups": {"A": {"roles": ["terra", "sol"], "limit": 90000}}}
        self.log("root", 10000)
        self.state = {"config_sha256": budget.digest(self.config), "roles": {}}

    def log(self, name, metric, parent=None, last="2026-09-27T12:00:09Z", reset=False):
        source = {"subagent": {"thread_spawn": {"parent_thread_id": parent}}} if parent else "cli"
        rows = [{"timestamp": "2026-09-27T12:00:00Z", "type": "session_meta", "payload": {"id": name, "source": source}}]
        for at, value in [("2026-09-27T12:00:01Z", 100), (last, 100 + metric)]:
            rows.append({"timestamp": at, "type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": value + 5000, "cached_input_tokens": 5000, "output_tokens": 0}}}})
        if reset:
            row = copy.deepcopy(rows[-1]);row["payload"]["info"]["total_token_usage"]["input_tokens"] = 5001;rows.append(row)
        p = self.root / (name + ".jsonl")
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return p

    def running(self, metric=10000):
        budget.reserve(self.config, self.state, "terra", self.now)
        p = self.log("child", metric, "root")
        budget.bind(self.config, self.state, "terra", "child", p)

    def test_parallel_starts_and_mutated_budget_are_rejected(self):
        budget.reserve(self.config, self.state, "terra", self.now)
        with self.assertRaisesRegex(ValueError, "并发"):
            budget.reserve(self.config, self.state, "sol", self.now)
        self.config["total_limit"] *= 2
        with self.assertRaisesRegex(ValueError, "配置已改变"):
            budget.observe(self.config, self.state, self.now)

    def test_inflight_stops_before_role_limit(self):
        self.running(71000)
        result = budget.observe(self.config, self.state, self.now)
        self.assertEqual(result["status"], "stop_required")
        self.assertEqual(result["interrupt_thread_ids"], ["child"])
        self.assertLess(result["rows"]["terra"]["metric"], self.config["roles"]["terra"])

    def test_finished_cost_not_released_and_group_cost_counted(self):
        self.running(50000)
        self.state["roles"]["terra"]["status"] = "finished"
        self.assertEqual(budget.observe(self.config, self.state, self.now)["used_known"], 60000)
        with self.assertRaisesRegex(ValueError, "组合"):
            budget.reserve(self.config, self.state, "sol", self.now)

    def test_unknown_stale_and_reset_are_not_zero(self):
        self.running()
        for kind in ("missing", "stale", "reset"):
            self.log("child", 10000, "root", reset=kind == "reset")
            if kind == "missing": (self.root / "child.jsonl").unlink()
            now = self.now if kind != "stale" else self.now.replace(minute=2)
            with self.subTest(kind=kind):
                result = budget.observe(self.config, self.state, now)
                self.assertEqual(result["status"], "stop_required")
                self.assertEqual(result["interrupt_thread_ids"], ["child"])

    def test_coordinator_limit_blocks_before_any_dispatch(self):
        self.log("root", 26000)
        with self.assertRaisesRegex(ValueError, "coordinator"):
            budget.reserve(self.config, self.state, "terra", self.now)

    def test_total_reservation_and_duplicate_sessions(self):
        self.config["total_limit"] = 100000
        self.state["config_sha256"] = budget.digest(self.config)
        with self.assertRaisesRegex(ValueError, "剩余总预算"):
            budget.reserve(self.config, self.state, "terra", self.now)
        self.config["total_limit"] = 200000
        self.state["config_sha256"] = budget.digest(self.config)
        budget.reserve(self.config, self.state, "terra", self.now)
        with self.assertRaisesRegex(ValueError, "同一会话"):
            budget.bind(self.config, self.state, "terra", "root", self.root / "root.jsonl")

    def test_tail_half_line_and_cached_tokens_do_not_inflate_charge(self):
        with (self.root / "root.jsonl").open("a", encoding="utf-8") as f:
            f.write('{"timestamp":')
        result = budget.observe(self.config, self.state, self.now)
        self.assertEqual(result["used_known"], 10000)
        self.assertEqual(result["status"], "ready")

    def test_resume_keeps_identity_and_spent_tokens(self):
        self.running(20000)
        self.state["roles"]["terra"]["status"] = "finished"
        result = budget.resume(self.config, self.state, "terra", self.now)
        self.assertEqual(result["spent"], 20000)
        self.assertEqual(result["thread_id"], "child")
        self.assertEqual(budget.observe(self.config, self.state, self.now)["used_known"], 30000)
        with self.assertRaisesRegex(ValueError, "同一会话"):
            budget.resume(self.config, self.state, "terra", self.now)

    def test_transfer_preserves_total_and_rejects_spent_or_live_donor(self):
        self.running(20000)
        with self.assertRaisesRegex(ValueError, "全部停止"):
            budget.transfer(self.config, self.state, "terra", "sol", 10000, "测试", self.now)
        self.state["roles"]["terra"]["status"] = "finished"
        budget.transfer(self.config, self.state, "terra", "sol", 30000, "转移闲余额度", self.now)
        limits = budget.role_limits(self.config, self.state)
        self.assertEqual(limits, {"terra": 55000, "sol": 115000})
        self.assertEqual(sum(limits.values()), sum(self.config["roles"].values()))
        self.assertEqual(self.config["total_limit"], 200000)
        with self.assertRaisesRegex(ValueError, "已消耗"):
            budget.transfer(self.config, self.state, "terra", "sol", 40000, "过多", self.now)

    def test_resume_rejects_exhausted_role_and_group(self):
        self.running(71000)
        self.state["roles"]["terra"]["status"] = "finished"
        with self.assertRaisesRegex(ValueError, "剩余额度"):
            budget.resume(self.config, self.state, "terra", self.now)
        self.log("child", 20000, "root")
        self.config["groups"]["A"]["limit"] = 80000
        self.state["config_sha256"] = budget.digest(self.config)
        with self.assertRaisesRegex(ValueError, "组合"):
            budget.resume(self.config, self.state, "terra", self.now)

    def test_resume_grace_is_bounded_and_never_hides_missing_log(self):
        self.running(20000)
        self.state["roles"]["terra"]["status"] = "finished"
        later = self.now + timedelta(seconds=60)
        self.log("root", 10000, last=later.isoformat())
        budget.resume(self.config, self.state, "terra", later)
        self.assertEqual(budget.observe(self.config, self.state, later)["status"], "ready")
        expired = later + timedelta(seconds=31)
        self.log("root", 10000, last=expired.isoformat())
        self.assertEqual(budget.observe(self.config, self.state, expired)["status"], "stop_required")
        (self.root / "child.jsonl").unlink()
        self.assertEqual(budget.observe(self.config, self.state, later)["status"], "stop_required")

    def test_metering_timeout_does_not_raise_token_or_total_limit(self):
        self.running(20000)
        with self.assertRaisesRegex(ValueError, "全部停止"):
            budget.metering_timeout(self.config, self.state, 300, "平台延迟", self.now)
        self.state["roles"]["terra"]["status"] = "finished"
        old = copy.deepcopy(self.config)
        budget.metering_timeout(self.config, self.state, 300, "平台延迟", self.now)
        budget.resume(self.config, self.state, "terra", self.now)
        later = self.now + timedelta(seconds=90)
        self.log("root", 10000, last=later.isoformat())
        self.assertEqual(budget.observe(self.config, self.state, later)["status"], "ready")
        self.log("child", 71000, "root", last=later.isoformat())
        self.assertEqual(budget.observe(self.config, self.state, later)["status"], "stop_required")
        self.assertEqual(self.config, old)
        with self.assertRaisesRegex(ValueError, "300"):
            budget.metering_timeout(self.config, self.state, 301, "不可无限等", later)

    def test_handoff_allocation_retains_prior_spend_and_cannot_evade_group(self):
        self.running(20000)
        self.state["roles"]["terra"]["status"] = "finished"
        with self.assertRaisesRegex(ValueError, "组合"):
            budget.transfer(self.config, self.state, "terra", "repair", 30000, "有界接手", self.now, new_role=True)
        self.config["groups"] = {}
        self.state["config_sha256"] = budget.digest(self.config)
        budget.transfer(self.config, self.state, "terra", "repair", 30000, "有界接手", self.now, new_role=True)
        self.assertEqual(budget.observe(self.config, self.state, self.now)["used_known"], 30000)
        budget.reserve(self.config, self.state, "repair", self.now)
        with self.assertRaisesRegex(ValueError, "同一会话"):
            budget.bind(self.config, self.state, "repair", "child", self.root / "child.jsonl")
        self.assertEqual(sum(budget.role_limits(self.config, self.state).values()), 170000)

    def test_coordinator_transfer_does_not_mint_budget(self):
        self.running(20000)
        self.state["roles"]["terra"]["status"] = "finished"
        self.config["groups"] = {}
        self.state["config_sha256"] = budget.digest(self.config)
        budget.transfer(self.config, self.state, "terra", "coordinator", 20000, "收尾协调", self.now)
        self.log("root", 26000)
        self.assertEqual(budget.observe(self.config, self.state, self.now)["status"], "ready")
        self.assertEqual(sum(budget.role_limits(self.config, self.state).values()) + self.config["coordinator_limit"] + 20000, 210000)
        self.assertEqual(self.config["total_limit"], 200000)

    def test_cli_nonzero_stop_and_no_reinitialization(self):
        self.log("root", 26000)
        config = self.root / "config.json"
        config.write_text(json.dumps(self.config), encoding="utf-8")
        state = self.root / "state.json"
        command = [sys.executable, "-X", "utf8", str(Path(budget.__file__)), str(config), str(state), "init"]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "stop_required")
        again = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(again.returncode, 1)
        self.assertIn("禁止重置", json.loads(again.stdout)["reason"])
        self.assertFalse(Path(str(state) + ".lock").exists())
        compact = subprocess.run(command[:-1] + ["watch", "--seconds", "1", "--compact"],
                                 capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(compact.returncode, 1)
        payload = json.loads(compact.stdout)
        self.assertEqual(payload["status"], "stop_required")
        self.assertIn("metrics", payload)
        self.assertNotIn("rows", payload)

    def test_compact_monitor_preserves_stop_and_unknown_metering(self):
        self.running(71000)
        full = budget.observe(self.config, self.state, self.now)
        compact = budget.compact_observation(full)
        for key in ("status", "at", "used_known", "reasons", "interrupt_thread_ids"):
            self.assertEqual(compact[key], full[key])
        self.assertEqual(compact["metrics"]["terra"], 71000)
        (self.root / "child.jsonl").unlink()
        missing = budget.compact_observation(budget.observe(self.config, self.state, self.now))
        self.assertEqual(missing["status"], "stop_required")
        self.assertTrue(any("计量未知" in reason for reason in missing["reasons"]))
        self.assertEqual(missing["interrupt_thread_ids"], ["child"])

    def test_unstarted_transfer_keeps_total_and_rejects_reserved_donor(self):
        self.config["groups"] = {}
        self.state["config_sha256"] = budget.digest(self.config)
        roles = list(self.config["roles"])
        donor, target = roles[0], roles[1]
        before = sum(budget.role_limits(self.config, self.state).values())
        budget.transfer(self.config, self.state, donor, target, 10000, "调整尚未启动的分配", self.now, unstarted=True)
        self.assertEqual(sum(budget.role_limits(self.config, self.state).values()), before)
        self.assertEqual(self.state["roles"], {})
        self.state["roles"][donor] = {"status": "finished"}
        with self.assertRaisesRegex(ValueError, "从未预留"):
            budget.transfer(self.config, self.state, donor, target, 10000, "不能猜测零消耗", self.now, unstarted=True)

    def test_transfer_can_resolve_only_target_stop_line(self):
        self.running(20000)
        self.state["roles"]["terra"]["status"] = "finished"
        self.config["groups"] = {}
        self.state["config_sha256"] = budget.digest(self.config)
        self.log("root", 26000)
        budget.transfer(self.config, self.state, "terra", "coordinator", 10000, "原额内收尾", self.now)
        self.assertEqual(budget.observe(self.config, self.state, self.now)["status"], "ready")
        self.log("root", 190000)
        with self.assertRaises(ValueError):
            budget.transfer(self.config, self.state, "terra", "coordinator", 10000, "总额不能解除", self.now)

    def test_watch_returns_early_when_live_log_crosses_stop_line(self):
        now = datetime.now(timezone.utc)
        original = (self.root / "root.jsonl").read_text(encoding="utf-8")
        for old, seconds in (("00", 3), ("01", 2), ("09", 1)):
            original = original.replace("2026-09-27T12:00:" + old + "Z", (now - timedelta(seconds=seconds)).isoformat())
        (self.root / "root.jsonl").write_text(original, encoding="utf-8")
        self.config["since"] = (now - timedelta(seconds=1.5)).isoformat()
        self.state["config_sha256"] = budget.digest(self.config)
        config, state = self.root / "config.json", self.root / "state.json"
        config.write_text(json.dumps(self.config), encoding="utf-8")
        state.write_text(json.dumps(self.state), encoding="utf-8")
        def append_usage():
            event = {"timestamp": datetime.now(timezone.utc).isoformat(), "type": "event_msg", "payload": {
                "type": "token_count", "info": {"total_token_usage": {
                    "input_tokens": 31100, "cached_input_tokens": 5000, "output_tokens": 0}}}}
            with (self.root / "root.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event) + "\n")
        timer = threading.Timer(0.3, append_usage)
        timer.start()
        try:
            result = subprocess.run([sys.executable, "-X", "utf8", str(Path(budget.__file__)),
                                     str(config), str(state), "watch", "--seconds", "20"],
                                    capture_output=True, text=True, encoding="utf-8", timeout=6)
        finally:
            timer.join()
        self.assertEqual(result.returncode, 1)
        self.assertIn("coordinator达到提前停止线", json.loads(result.stdout)["reasons"])


if __name__ == "__main__":
    unittest.main()
