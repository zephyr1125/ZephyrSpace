"""阻止漏项、假闭合和无依据的未知进入作者交接。"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import triplet_evidence_gate as gate


class EvidenceGateTests(unittest.TestCase):
    def test_missing_open_and_bounded_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "facts.json").write_text(json.dumps({"facts": [{"fact_id": "F1", "value": 1}]}), encoding="utf-8")
            data = {"evidence": ["facts.json"],
                    "requirements": [{"id": "R1", "scope": "三个完整年度执行对照", "decisive": True}],
                    "answers": [{"id": "R1", "status": "covered", "coverage": "三个年度逐年匹配",
                                 "remaining": "无", "evidence_refs": ["F1"]}]}
            self.assertFalse(gate.check(data, root)["errors"])
            (root / "coverage.json").write_text(json.dumps(data), encoding="utf-8")
            cli = subprocess.run([sys.executable, "-X", "utf8", str(gate.delivery.wp.ROOT / "scripts/triplet_evidence_gate.py"),
                                  str(root / "coverage.json"), "--root", str(root)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(cli.returncode, 0, cli.stderr + cli.stdout)
            self.assertEqual(json.loads(cli.stdout)["status"], "coverage_ready_for_human_check")
            missing = copy.deepcopy(data)
            missing["answers"] = []
            with self.assertRaisesRegex(ValueError, "逐一覆盖"):
                gate.check(missing, root)
            answer = data["answers"][0]
            answer.update(status="open", remaining="仅完成两年", assessment="影响D2")
            self.assertTrue(gate.check(data, root)["errors"])
            answer.update(status="bounded", assessment="缺未披露动机，已删除依赖褒贬")
            self.assertTrue(gate.check(data, root)["errors"])
            answer["search_scope"] = "2023至2025年报及任免公告已查"
            self.assertFalse(gate.check(data, root)["errors"])
            answer["evidence_refs"] = ["不存在"]
            self.assertTrue(gate.check(data, root)["errors"])


if __name__ == "__main__":
    unittest.main()
