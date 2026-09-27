"""核验局部修复不越界、不继承批准、不改变原规则，并阻断空取证计划。"""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import triplet_score_flow as flow
from scripts import triplet_evidence_gate as gate


class ScoreFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        shutil.copyfile(flow.wp.ROOT / "data/watchlist_meta.json", self.root / "data/watchlist_meta.json")
        scores = {}
        for group, rules in zip(("company", "management"), flow.wp.scoring_rules()):
            rows = [{"id": key, "score": cap * 0.6, "rule_ref": "测试规则",
                     "reason": key + "独立测试依据", "evidence_refs": ["F001"]} for key, cap in rules.items()]
            if group == "company":
                next(r for r in rows if r["id"] == "D2").update(original_statement_found=False, strategy_drift=False)
            scores[group] = {"items": rows, "total": sum(r["score"] for r in rows)}
        self.base = {"schema_version": 1, "scores": scores, "bridges": [], "bridges_not_applicable": "测试无桥",
                     "valuation": {"status": "deferred", "reason": "先评分", "currency": "CNY", "models": [],
                                   "target_price": None, "certainty": None, "buy_price": None},
                     "qualification": {"status": "approved"}, "score_state": "approved", "publish_allowed": True}
        self.save("base.json", self.base)
        self.save("facts.json", [{"fact_id": "F001", "value": 1}])
        self.save("decision.json", {"issues": [{"id": "R07", "acceptance": "按原规则核Capex扣分"}], "score_repair_scope": [
            {"group": "company", "item": "E4", "acceptance_ids": ["R07"]}]})
        self.delta = {"base_sha256": flow.delivery.digest((self.root / "base.json").read_bytes()),
                      "decision_sha256": flow.delivery.digest((self.root / "decision.json").read_bytes()),
                      "changes": [{"group": "company", "item": "E4", "acceptance_ids": ["R07"],
                                   "set": {"score": 1.5, "reason": "Capex原规则扣分测试"}}]}

    def save(self, name, value):
        (self.root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def apply(self, delta=None):
        return flow.apply_delta("base.json", "decision.json", delta or self.delta, self.root, ["facts.json"])

    def test_delta_preserves_unaffected_and_invalidates_approval(self):
        result = self.apply()
        updated = result["workpaper"]
        self.assertEqual(flow.wp.read(self.root / "base.json"), self.base)
        for before, after in zip(self.base["scores"]["company"]["items"], updated["scores"]["company"]["items"]):
            if before["id"] != "E4":
                self.assertEqual(before, after)
        self.assertEqual(updated["scores"]["management"], self.base["scores"]["management"])
        self.assertEqual(updated["scores"]["company"]["total"], sum(r["score"] for r in updated["scores"]["company"]["items"]))
        self.assertEqual(updated["qualification"]["status"], "pending_review")
        self.assertFalse(updated["publish_allowed"])
        self.assertEqual(result["check"]["errors"], [])

    def test_reject_stale_outside_scope_duplicate_and_dangling_reference(self):
        for kind in ("hash", "item", "duplicate", "field", "reference", "acceptance"):
            delta = copy.deepcopy(self.delta)
            change = delta["changes"][0]
            if kind == "hash": delta["base_sha256"] = "old"
            if kind == "item": change["item"] = "E3"
            if kind == "duplicate": delta["changes"].append(copy.deepcopy(change))
            if kind == "field": change["set"]["id"] = "E3"
            if kind == "reference": change["set"]["evidence_refs"] = ["MISSING"]
            if kind == "acceptance": change["acceptance_ids"] = ["NEW"]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.apply(delta)

    def test_plan_freeze_coverage_and_empty_template(self):
        plan = flow.plan_template()
        with self.assertRaises(ValueError): flow.validate_plan(plan)
        for row in plan["requirements"]: row["scope"] = "核对" + row["item"] + "原件与反证"
        self.save("plan.json", plan)
        data = {"plan": "plan.json", "plan_sha256": flow.delivery.digest((self.root / "plan.json").read_bytes()),
                "evidence": ["facts.json"], "answers": [{"id": r["id"], "status": "covered", "coverage": "已定位",
                "remaining": "无", "remaining_kind": "none", "supports_scoring": True,
                "evidence_refs": ["F001"]} for r in plan["requirements"]]}
        self.assertFalse(gate.check(data, self.root)["errors"])
        rejected = copy.deepcopy(data)
        rejected["answers"][0].update(status="bounded", remaining_kind="public_not_checked", supports_scoring=False,
                                      remaining="年报公开财务尚未提取", search_scope="只读最新摘要", assessment="影响原项")
        self.assertTrue(gate.check(rejected, self.root)["errors"])
        data["answers"].pop()
        with self.assertRaises(ValueError): gate.check(data, self.root)
        self.save("plan.json", {})
        with self.assertRaisesRegex(ValueError, "版本"): gate.check(data, self.root)

    def test_scope_cannot_invent_acceptance(self):
        ruling = flow.wp.read(self.root / "decision.json")
        ruling["issues"] = []
        self.save("decision.json", ruling)
        self.delta["decision_sha256"] = flow.delivery.digest((self.root / "decision.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "不存在的原验收ID"):
            self.apply()

    def test_f1_original_negative_tiers_do_not_open_other_negative_scores(self):
        self.assertEqual(flow.wp.f1_negative_tiers(), {-1, -2})
        for item, value, allowed in (("F1", -1, True), ("F1", -2, True),
                                     ("F1", -1.5, False), ("F1", -3, False), ("E4", -1, False)):
            sheet = {"items": [{"id": item, "score": value, "rule_ref": "原文档位",
                                "reason": "原文与事实桥", "evidence_refs": ["F001"]}], "total": value}
            with self.subTest(item=item, value=value):
                if allowed:
                    self.assertEqual(flow.wp.score(sheet, {item: 5}, "company"), value)
                else:
                    with self.assertRaises(ValueError):
                        flow.wp.score(sheet, {item: 5}, "company")

    def test_gap_repair_is_bound_to_ruling_and_cannot_change_other_metadata(self):
        ruling = flow.wp.read(self.root / "decision.json")
        ruling["metadata_repair_scope"] = [{"field": "evidence_gaps", "acceptance_ids": ["R07"]}]
        self.save("decision.json", ruling)
        self.delta["decision_sha256"] = flow.delivery.digest((self.root / "decision.json").read_bytes())
        self.delta["changes"] = []
        self.delta["metadata_changes"] = [{"field": "evidence_gaps", "acceptance_ids": ["R07"], "set": []}]
        result = self.apply()
        self.assertEqual(result["workpaper"]["evidence_gaps"], [])
        self.assertEqual(result["workpaper"]["scores"], self.base["scores"])
        self.assertEqual(flow.wp.read(self.root / "base.json"), self.base)
        self.assertFalse(result["workpaper"]["publish_allowed"])
        for field, ids in (("valuation", ["R07"]), ("evidence_gaps", ["invented"])):
            delta = copy.deepcopy(self.delta)
            delta["metadata_changes"][0].update(field=field, acceptance_ids=ids)
            with self.subTest(field=field, ids=ids), self.assertRaises(ValueError):
                self.apply(delta)

    def test_packets_keep_exact_original_and_no_valuation_in_score(self):
        result = flow.packet("score", flow.wp.ROOT)
        for source in flow.CORE + [flow.CHECKS]:
            self.assertIn((flow.wp.ROOT / source).read_bytes().decode("utf-8-sig"), result["text"])
        self.assertNotIn("skills/valuation/SKILL.md", result["inputs"])

    def test_packet_cli_does_not_double_windows_line_endings(self):
        for source in flow.CORE + [flow.CHECKS]:
            path = self.root / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes("原文第一行\r\n原文第二行\r\n".encode("utf-8"))
        result = subprocess.run([sys.executable, "-X", "utf8", str(flow.wp.ROOT / "scripts/triplet_score_flow.py"),
                                 "--root", str(self.root), "packet", "score", "rules.md"], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((self.root / "rules.md").read_bytes(), flow.packet("score", self.root)["text"].encode("utf-8"))

    def test_gate_uses_raw_not_rounded_scores(self):
        sheet = copy.deepcopy(self.base)
        sheet["scores"]["company"]["total"] = 83.5
        sheet["scores"]["management"]["total"] = 75.5
        self.assertEqual(flow.score_gate(sheet, self.root), "B_GROWTH")
        self.assertEqual(flow.wp.score_display(75.5), "76")

    def test_v2_closed_tiers_and_conditional_bonus(self):
        for row in ({"id": "C2", "score": 4}, {"id": "C1", "score": 5},
                    {"id": "C3+C4", "score": 8}, {"id": "F2.5", "score": 1.5, "positive_precedent": False}):
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "显式档位"):
                flow.wp.validate_explicit_tiers([row], version=2)
        flow.wp.validate_explicit_tiers([{"id": "C2", "score": 3},
            {"id": "F2.5", "score": 1.5, "positive_precedent": True}], version=2)
        flow.wp.validate_explicit_tiers([{"id": "F1", "score": 5}, {"id": "F2", "score": 5},
            {"id": "F3", "score": 3}, {"id": "F2.5", "score": 2, "positive_precedent": True}], version=2)

    def test_capex_decline_triggers_same_original_deduction(self):
        row = {"score": 2, "capex_check": {"applicable": True, "current": 3127594916.41,
               "previous": 4678712053.56, "current_period": "2025FY", "previous_period": "2024FY", "unit": "CNY",
               "evidence_refs": ["F001"], "split_complete": False, "score_before_capex_adjustment": 2}}
        with self.assertRaisesRegex(ValueError, "Capex调整"):
            flow.wp.validate_capex(row)
        row["score"] = 1.5
        flow.wp.validate_capex(row)
        row["capex_check"]["split_complete"] = True
        with self.assertRaises(ValueError): flow.wp.validate_capex(row)
        row["score"] = 2
        flow.wp.validate_capex(row)
        row["capex_check"].update(current=70, previous=100, split_complete=False)
        flow.wp.validate_capex(row)


if __name__ == "__main__":
    unittest.main()
