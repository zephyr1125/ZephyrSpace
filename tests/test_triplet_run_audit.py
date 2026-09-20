"""防止累计用量重复求和、跨任务计入或日志回退后给出伪精确总量。"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("audit", Path(__file__).parents[1] / "scripts/triplet_run_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def write_log(self, root, name, parent=None, values=(100, 150, 150)):
        source = {"subagent": {"thread_spawn": {"parent_thread_id": parent, "agent_role": "writer"}}} if parent else "vscode"
        lines = [{"timestamp": "2026-09-19T00:00:00Z", "type": "session_meta", "payload": {"id": name, "source": source}}]
        for i, value in enumerate(values):
            usage = {"input_tokens": value, "cached_input_tokens": value - 10, "cache_write_input_tokens": 0,
                     "output_tokens": 5, "reasoning_output_tokens": 2, "total_tokens": value + 5}
            lines.append({"timestamp": f"2026-09-19T00:00:0{i + 1}Z", "type": "event_msg",
                          "payload": {"type": "token_count", "info": {"total_token_usage": usage}}})
        path = root / (name + ".jsonl")
        path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
        return path

    def test_last_counter_once_and_descendants_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_log(root, "root")
            self.write_log(root, "child", "root")
            self.write_log(root, "grandchild", "child")
            self.write_log(root, "unrelated")
            result = audit.audit(root, "root")
            self.assertEqual(len(result["sessions"]), 3)
            self.assertEqual(result["totals"]["input_tokens"], 450)
            self.assertEqual(result["totals"]["total_tokens"], 465)
            self.assertEqual(result["totals"]["uncached_input_tokens"], 30)

    def test_counter_reset_does_not_silently_undercount(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_log(Path(directory), "root", values=(100, 150, 20))
            result = audit.summarize(path)
            self.assertEqual(len(result["counter_decreases"]), 1)
            self.assertIsNone(result["usage"]["total_tokens"])

    def test_cutoff_excludes_later_followup(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_log(Path(directory), "root")
            result = audit.audit(directory, "root", audit.datetime.fromisoformat("2026-09-19T00:00:01+00:00"))
            self.assertEqual(result["totals"]["input_tokens"], 100)


if __name__ == "__main__":
    unittest.main()
