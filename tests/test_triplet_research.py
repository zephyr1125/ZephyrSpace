"""回放联合首审、版本隔离、批准依赖和已知数值故障，不冒充模型质量测试。"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import triplet_research as research
from scripts import triplet_score_flow as flow
from test_triplet_delivery import sample, write


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = sample(self.root)
        for path in research.RULES + ["data/watchlist_meta.json"]:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(research.wp.ROOT / path, target)
        self.data = research.wp.read(self.root / "workpaper.json")
        self.data.update(research_profile=research.PROFILE, numeric_fact_ids=["TEST-FACT-001"], numeric_calculations=[])
        for model in self.data["valuation"]["models"]:
            model.update(economic_basis="测试原件对应经营推导，非真实研究", evidence_refs=["TEST-FACT-001"])
            for scenario in model["scenarios"].values():
                for meta in scenario["input_meta"].values():
                    meta["evidence_refs"] = ["TEST-FACT-001"]
        self.data["valuation"]["reverse"]["evidence_refs"] = ["TEST-FACT-001"]
        self.fact = {"fact_id": "TEST-FACT-001", "entity": "测试公司", "metric": "capacity", "value": 86.354,
                     "unit": "%", "currency": "none", "period_start": "2025-01-01", "period_end": "2025-12-31",
                     "as_of": "2026-09-21", "consolidation": "consolidated", "actual_or_plan": "actual",
                     "source_ref": "SOURCE-001", "locator": "原件表1"}
        self.save_fact()
        write(self.root, "workpaper.json", self.data)

    def save_fact(self):
        write(self.root, "evidence.json", {"facts": [self.fact], "sources": [
            {"source_id": "SOURCE-001", "url": "https://example.com/report"}]})

    def test_draft_saves_unknown_and_withdrawn_states_without_approval(self):
        data = research.workpaper_template("测试公司", "TEST", "CNY", "2026-09-28")
        data["evidence_gaps"] = [{"status": s} for s in ("not_obtained", "not_derivable")]
        for model, status in zip(data["valuation"]["models"], ("not_applicable", "withdrawn")):
            model.update(status=status, weight=0)
        write(self.root, "draft-input.json", data)
        receipt = research.save_draft("draft-input.json", self.root, "draft")
        self.assertEqual(receipt["status"], "draft_saved_not_reviewed")
        self.assertFalse(receipt["research_approved"])
        self.assertEqual(research.wp.read(self.root / "draft/workpaper.json"), data)
        self.assertTrue(research.check(data, self.root, ["evidence.json"])["errors"])
        with self.assertRaisesRegex(ValueError, "禁止覆盖"):
            research.save_draft("draft-input.json", self.root, "draft")

    def test_draft_cannot_claim_full_approval(self):
        data = research.workpaper_template("测试公司", "TEST", "CNY", "2026-09-28")
        data["research_state"] = "approved"
        write(self.root, "approved.json", data)
        with self.assertRaisesRegex(ValueError, "批准"):
            research.save_draft("approved.json", self.root, "draft")
        self.assertFalse((self.root / "draft").exists())

    def test_template_has_original_items_but_cannot_pass_as_research(self):
        data = research.workpaper_template("测试公司", "TEST", "CNY", "2026-09-27")
        for group, limits in zip(("company", "management"), research.wp.scoring_rules()):
            self.assertEqual([r["id"] for r in data["scores"][group]["items"]], list(limits))
            self.assertTrue(all(r["score"] is None for r in data["scores"][group]["items"]))
        self.assertFalse(data["publish_allowed"])
        self.assertTrue(research.check(data, self.root, ["evidence.json"])["errors"])
        with self.assertRaises(ValueError):
            research.workpaper_template("测试", "TEST", "CNY", "不是日期")

    def test_recompute_repairs_arithmetic_without_changing_judgment(self):
        self.data["numeric_calculations"] = [
            {"id": "SECOND", "formula": "v*2", "input_fact_ids": {"v": "FIRST"}, "result": 0,
             "unit": "%", "basis": "测试派生依赖", "same_basis": []},
            {"id": "FIRST", "formula": "v+1", "input_fact_ids": {"v": "TEST-FACT-001"}, "result": 0,
             "unit": "%", "basis": "测试加法", "same_basis": []}]
        for model in self.data["valuation"]["models"]:
            model["scenarios"]["base"]["value"] = 0
            model["sensitivity"]["values"] = []
        self.data["valuation"]["weighted"] = {}
        self.data["valuation"]["buy_price"] = 0
        before = copy.deepcopy(self.data)
        result, changes = research.recompute(self.data, self.root, ["evidence.json"])
        self.assertEqual(self.data, before)
        self.assertEqual(result["scores"], before["scores"])
        self.assertEqual(result["valuation"]["reverse"], before["valuation"]["reverse"])
        self.assertEqual([row["id"] for row in result["numeric_calculations"]], ["FIRST", "SECOND"])
        self.assertAlmostEqual(result["numeric_calculations"][1]["result"], (86.354 + 1) * 2)
        for old, new in zip(before["valuation"]["models"], result["valuation"]["models"]):
            self.assertEqual(old["formula"], new["formula"])
            for scenario in research.wp.SCENARIOS:
                self.assertEqual(old["scenarios"][scenario]["inputs"], new["scenarios"][scenario]["inputs"])
                self.assertEqual(old["scenarios"][scenario]["input_meta"], new["scenarios"][scenario]["input_meta"])
        self.assertTrue(changes)
        self.assertFalse(research.check(result, self.root, ["evidence.json"])["errors"])
        again, differences = research.recompute(result, self.root, ["evidence.json"])
        self.assertEqual(again, result)
        self.assertEqual(differences, [])

    def test_recompute_refuses_dependency_errors_and_input_conflicts(self):
        calculation = {"id": "FIRST", "formula": "v+1", "input_fact_ids": {"v": "TEST-FACT-001"},
                       "result": 0, "unit": "%", "basis": "测试", "same_basis": []}
        self.data["numeric_calculations"] = [calculation]
        for invalid in ("FIRST", "MISSING"):
            calculation["input_fact_ids"]["v"] = invalid
            with self.assertRaisesRegex(ValueError, "成环或引用未声明"):
                research.recompute(self.data, self.root, ["evidence.json"])
        calculation["input_fact_ids"]["v"] = "TEST-FACT-001"
        self.data["numeric_calculations"].append(copy.deepcopy(calculation))
        with self.assertRaisesRegex(ValueError, "ID重复"):
            research.recompute(self.data, self.root, ["evidence.json"])
        self.data["numeric_calculations"].pop()
        scenario = self.data["valuation"]["models"][0]["scenarios"]["base"]
        variable = next(iter(scenario["inputs"]))
        scenario["input_meta"][variable]["calculation_id"] = "FIRST"
        with self.assertRaisesRegex(ValueError, "模型输入绑定"):
            research.recompute(self.data, self.root, ["evidence.json"])

    def test_recompute_keeps_unresolved_economics_and_rejects_approval(self):
        self.data["valuation"]["models"][0]["economic_basis"] = ""
        write(self.root, "pending.json", self.data)
        write(self.root, "paths.json", ["evidence.json"])
        receipt = research.prepare_calculations("pending.json", "paths.json", self.root, "computed")
        self.assertEqual(receipt["status"], "failed")
        self.assertFalse(receipt["research_approved"])
        self.assertEqual(receipt["output_sha256"], research.delivery.digest((self.root / "computed/workpaper.json").read_bytes()))
        self.assertIn("evidence.json", receipt["input_sha256"])
        with self.assertRaisesRegex(ValueError, "禁止覆盖"):
            research.prepare_calculations("pending.json", "paths.json", self.root, "computed")
        self.data["research_state"] = "approved"
        with self.assertRaisesRegex(ValueError, "获批底稿"):
            research.recompute(self.data, self.root, ["evidence.json"])

    def test_recompute_does_not_override_unit_constraints(self):
        other = dict(self.fact, fact_id="OTHER", unit="CNY", value=2)
        evidence = research.wp.read(self.root / "evidence.json")
        evidence["facts"].append(other)
        write(self.root, "evidence.json", evidence)
        self.data["numeric_fact_ids"].append("OTHER")
        self.data["numeric_calculations"] = [{"id": "BAD", "formula": "a+b",
            "input_fact_ids": {"a": "TEST-FACT-001", "b": "OTHER"}, "result": 0,
            "unit": "%", "basis": "故意混单位", "same_basis": ["unit"]}]
        with self.assertRaisesRegex(ValueError, "混用unit"):
            research.recompute(self.data, self.root, ["evidence.json"])

    def driver_fixture(self):
        model = self.data["valuation"]["models"][0]
        scenario = model["scenarios"]["base"]
        parameter = next(iter(scenario["inputs"]))
        value = scenario["inputs"][parameter]
        evidence = research.wp.read(self.root / "evidence.json")
        evidence["facts"] += [
            {"fact_id": "BASE", "metric": "base", "value": (value - 1) / 1.1, "unit": "USD/share"},
            {"fact_id": "ORGANIC", "metric": "same_store_growth", "value": .1, "unit": "decimal"},
            {"fact_id": "CAPACITY", "metric": "net_openings", "value": 1, "unit": "store"}]
        write(self.root, "evidence.json", evidence)
        self.data["numeric_calculations"] = [{"id": "DRIVER", "formula": "base*(1+organic)+capacity",
            "input_fact_ids": {"base": "BASE", "organic": "ORGANIC", "capacity": "CAPACITY"},
            "result": value, "unit": "USD/share"}]
        scenario["input_meta"][parameter].update(calculation_id="DRIVER", unit="USD/share")
        return {"issues": [{"id": "A2"}], "mechanical_requirements": [
            {"id": "A2-driver", "acceptance_id": "A2", "model_id": model["id"], "scenarios": ["base"],
             "input": parameter, "required_metrics": ["same_store_growth", "net_openings"]}]}

    def test_acceptance_requires_actual_driver_dependency(self):
        ruling = self.driver_fixture()
        self.assertFalse(research.check_acceptance(self.data, ruling, self.root, ["evidence.json"])["errors"])
        calc = self.data["numeric_calculations"][0]
        calc["input_fact_ids"].pop("capacity")
        calc["formula"] = "base*(1+organic)+1"
        result = research.check_acceptance(self.data, ruling, self.root, ["evidence.json"])
        self.assertIn("缺经营驱动", result["errors"][0])

    def test_unused_driver_or_unbound_model_does_not_count(self):
        ruling = self.driver_fixture()
        calc = self.data["numeric_calculations"][0]
        calc["formula"] = "base*(1+organic)+1"
        self.assertIn("未参与公式", research.check_acceptance(self.data, ruling, self.root, ["evidence.json"])["errors"][0])
        calc["formula"] = "base*(1+organic)+capacity"
        scenario = self.data["valuation"]["models"][0]["scenarios"]["base"]
        scenario["inputs"][ruling["mechanical_requirements"][0]["input"]] += 1
        self.assertIn("驱动桥与模型输入", research.check_acceptance(self.data, ruling, self.root, ["evidence.json"])["errors"][0])

    def test_driver_bound_to_unused_model_input_cannot_pass(self):
        ruling = self.driver_fixture()
        model = self.data["valuation"]["models"][0]
        parameter = ruling["mechanical_requirements"][0]["input"]
        replacement = "independent_" + parameter
        for scenario in model["scenarios"].values():
            scenario["inputs"][replacement] = scenario["inputs"][parameter]
            scenario["input_meta"][replacement] = copy.deepcopy(scenario["input_meta"][parameter])
            scenario["input_meta"][replacement].pop("calculation_id", None)
        model["formula"] = model["formula"].replace(parameter, replacement)
        for axis in ("x", "y"):
            if model["sensitivity"][axis] == parameter:
                model["sensitivity"][axis] = replacement
        research.wp.calculate_model(model)
        result = research.check_acceptance(self.data, ruling, self.root, ["evidence.json"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("未参与估值公式", result["errors"][0])

    def test_empty_or_unrelated_acceptance_cannot_pass(self):
        ruling = self.driver_fixture()
        ruling["mechanical_requirements"][0]["acceptance_id"] = "NEW-ISSUE"
        self.assertTrue(research.check_acceptance(self.data, ruling, self.root, ["evidence.json"])["errors"])
        self.assertTrue(research.check_acceptance(self.data, {}, self.root, ["evidence.json"])["errors"])

    def test_legacy_script_descriptor_is_not_a_calculation_graph(self):
        ruling = self.driver_fixture()
        self.data["numeric_calculations"] = {"path": "calculations.py", "result": "calculations.json"}
        result = research.check_acceptance(self.data, ruling, self.root, ["evidence.json"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("计算记录数组", result["errors"][0])
        self.assertEqual(result["checks"], [])
        for malformed in [["CALC"], [{}], [{"id": 12}]]:
            self.data["numeric_calculations"] = malformed
            with self.assertRaisesRegex(ValueError, "计算记录"):
                research.wp.calculation_records(self.data)

    def test_driver_graph_round_trip_through_freeze_packet_and_reports(self):
        from scripts import triplet_review_packet as packet
        driver = self.driver_fixture()
        evidence = research.wp.read(self.root / "evidence.json")
        for row in evidence["facts"][1:]:
            for key, value in self.fact.items():
                row.setdefault(key, value)
            self.data["numeric_fact_ids"].append(row["fact_id"])
        write(self.root, "evidence.json", evidence)
        self.data["numeric_calculations"][0].update(basis="合成接口测试，不是公司经济模型", same_basis=[])
        self.data["valuation"]["models"][0]["evidence_refs"] = ["DRIVER"]
        write(self.root, "workpaper.json", self.data)
        ruling = self.ruling()
        ruling["mechanical_requirements"] = driver["mechanical_requirements"]
        ruling["mechanical_requirements"][0]["acceptance_id"] = "V03-basis"
        write(self.root, "decision.json", ruling)
        research.freeze({"workpaper": "workpaper.json", "decision": "decision.json", "evidence": ["evidence.json"]},
                        self.root, "versions/driver")
        packed = packet.build(self.data, self.root, ["evidence.json"])
        self.assertTrue({"DRIVER", "ORGANIC", "CAPACITY"} <= packed["evidence"].keys())
        for path in self.bundle["templates"].values():
            with (self.root / path).open("a", encoding="utf-8") as stream:
                stream.write("\n测试数值：{{number:DRIVER}}。\n")
        bundle = {**self.bundle, "workpaper": "versions/driver/workpaper.json", "decision": "versions/driver/decision.json"}
        research.delivery.build(bundle, self.root, self.root / "build")
        research.delivery.verify(self.root / "build/manifest.json", self.root)
        self.assertFalse(research.wp.read(self.root / "versions/driver/decision.json").get("publish_allowed", False))
        # 拿掉驱动绑定后不能再次冻结；旧版本仍能复验。
        parameter = driver["mechanical_requirements"][0]["input"]
        self.data["valuation"]["models"][0]["scenarios"]["base"]["input_meta"][parameter].pop("calculation_id")
        write(self.root, "workpaper.json", self.data)
        with self.assertRaisesRegex(ValueError, "裁决验收"):
            research.freeze({"workpaper": "workpaper.json", "decision": "decision.json", "evidence": ["evidence.json"]},
                            self.root, "versions/broken")
        research.delivery.verify(self.root / "build/manifest.json", self.root)

    def test_numeric_dependency_chain_is_checked_without_duplicate_ledger(self):
        self.data["numeric_calculations"] = [
            {"id": "DERIVED-1", "formula": "x*2", "input_fact_ids": {"x": "TEST-FACT-001"},
             "result": 172.708, "unit": "%", "basis": "合成测试", "same_basis": []},
            {"id": "DERIVED-2", "formula": "x-y", "input_fact_ids": {"x": "DERIVED-1", "y": "TEST-FACT-001"},
             "result": 86.354, "unit": "%", "basis": "合成测试", "same_basis": ["unit", "currency", "period_end"]}]
        index = research.delivery.evidence_index(self.root, ["evidence.json"])
        research.numeric_check(self.data, index)
        self.data["numeric_calculations"][0]["input_fact_ids"] = {"x": "DERIVED-2"}
        with self.assertRaisesRegex(ValueError, "未声明关键数值"):
            research.numeric_check(self.data, index)

    def test_joint_preflight_rejects_deferred_and_unsupported_model(self):
        self.assertFalse(research.check(self.data, self.root, ["evidence.json"])["errors"])
        data = copy.deepcopy(self.data)
        data["valuation"].update(status="deferred", reason="尚未分析", models=[], target_price=None, certainty=None, buy_price=None)
        self.assertTrue(research.check(data, self.root, ["evidence.json"])["errors"])
        data = copy.deepcopy(self.data)
        data["valuation"]["models"][0].pop("economic_basis")
        self.assertTrue(research.check(data, self.root, ["evidence.json"])["errors"])

    def ruling(self):
        first = research.delivery.digest((self.root / "workpaper.json").read_bytes())
        for path in ("review-a.json", "review-b.json"):
            write(self.root, path, {"workpaper_sha256": first, "coverage": {"score": True, "valuation": True},
                                   "input_sha256": {p: research.delivery.digest((self.root / p).read_bytes())
                                                    for p in ["evidence.json", *research.RULES]}})
        return {"decision": "defer", "research_state": "pending", "score_state": "approved", "issues": [
            {"id": "V03", "lane": "research", "status": "open", "reason": "经济依据不足",
             "acceptance": [{"id": "V03-basis"}]}], "basis": "测试联合首审",
            "review_refs": ["review-a.json", "review-b.json"],
            "research_cycle": {"mode": "joint", "first_review_refs": ["review-a.json", "review-b.json"],
                               "first_workpaper_sha256": first, "repairs_used": 0},
            "valuation_repair_scope": [{"field": "models", "model_ids": ["PE"], "acceptance_ids": ["V03-basis"]}]}

    def test_score_only_review_cannot_spend_joint_repair(self):
        ruling = self.ruling()
        self.assertEqual(research.validate_cycle(ruling, self.root)["repairs_used"], 0)
        row = research.wp.read(self.root / "review-b.json")
        row["coverage"]["valuation"] = False
        write(self.root, "review-b.json", row)
        with self.assertRaisesRegex(ValueError, "同时首审"):
            research.validate_cycle(ruling, self.root)

    def test_repair_budget_and_scope_are_enforced(self):
        ruling = self.ruling()
        ruling["research_cycle"]["repairs_used"] = 2
        with self.assertRaisesRegex(ValueError, "耗尽"):
            research.validate_cycle(ruling, self.root)
        ruling["research_cycle"]["repairs_used"] = 1
        with self.assertRaisesRegex(ValueError, "例外"):
            research.validate_cycle(ruling, self.root)

    def test_valuation_delta_preserves_score_but_not_full_approval(self):
        ruling = self.ruling()
        ruling["approval_projections"] = {"score": research.projection(self.data, self.root, ["evidence.json"], "score")}
        write(self.root, "decision.json", ruling)
        models = copy.deepcopy(self.data["valuation"]["models"])
        models[0]["economic_basis"] = "补充经营经济推导与同口径比较"
        delta = {"base_sha256": research.delivery.digest((self.root / "workpaper.json").read_bytes()),
                 "decision_sha256": research.delivery.digest((self.root / "decision.json").read_bytes()),
                 "changes": [], "valuation_changes": [{"field": "models", "set": models, "acceptance_ids": ["V03-basis"]}]}
        result = flow.apply_delta("workpaper.json", "decision.json", delta, self.root, ["evidence.json"])
        self.assertEqual(result["workpaper"]["scores"], self.data["scores"])
        self.assertEqual(result["workpaper"]["score_state"], "approved")
        self.assertFalse(result["workpaper"]["publish_allowed"])
        self.assertEqual(result["workpaper"]["research_cycle"]["repairs_used"], 1)
        write(self.root, "repaired.json", result["workpaper"])
        stale_delta = copy.deepcopy(delta)
        stale_delta["base_sha256"] = research.delivery.digest((self.root / "repaired.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "不得重置"):
            flow.apply_delta("repaired.json", "decision.json", stale_delta, self.root, ["evidence.json"])
        models[1]["economic_basis"] = "未经授权修改另一模型"
        with self.assertRaisesRegex(ValueError, "未授权模型"):
            flow.apply_delta("workpaper.json", "decision.json", delta, self.root, ["evidence.json"])
        models[1] = copy.deepcopy(self.data["valuation"]["models"][1])
        delta["valuation_changes"][0]["field"] = "publish_allowed"
        with self.assertRaises(ValueError):
            flow.apply_delta("workpaper.json", "decision.json", delta, self.root, ["evidence.json"])

    def test_shared_fact_and_rule_change_invalidate_projections(self):
        before = {s: research.projection(self.data, self.root, ["evidence.json"], s) for s in ("score", "valuation")}
        data = copy.deepcopy(self.data)
        data["valuation"]["certainty_reason"] = "改变估值判断"
        self.assertEqual(before["score"], research.projection(data, self.root, ["evidence.json"], "score"))
        self.assertNotEqual(before["valuation"], research.projection(data, self.root, ["evidence.json"], "valuation"))
        self.fact["value"] = 54
        self.save_fact()
        for scope in before:
            self.assertNotEqual(before[scope], research.projection(self.data, self.root, ["evidence.json"], scope))

    def test_current_pointer_does_not_break_old_manifest(self):
        write(self.root, "decision.json", self.ruling())
        config = {"workpaper": "workpaper.json", "decision": "decision.json", "evidence": ["evidence.json"]}
        research.freeze(config, self.root, "versions/v1")
        bundle = {**self.bundle, "workpaper": "versions/v1/workpaper.json", "decision": "versions/v1/decision.json"}
        research.delivery.build(bundle, self.root, self.root / "build")
        research.freeze({**config, "previous_decision": "versions/v1/decision.json"}, self.root, "versions/v2")
        research.delivery.verify(self.root / "build/manifest.json", self.root)
        with self.assertRaises(ValueError):
            research.freeze(config, self.root, "versions/v1")
        write(self.root, "versions/v1/workpaper.json", {})
        with self.assertRaises(ValueError):
            research.delivery.verify(self.root / "build/manifest.json", self.root)

    def test_freeze_cannot_resign_old_approval_for_new_evidence(self):
        ruling = self.ruling()
        ruling["approval_projections"] = {"score": research.projection(self.data, self.root, ["evidence.json"], "score")}
        write(self.root, "decision.json", ruling)
        config = {"workpaper": "workpaper.json", "decision": "decision.json", "evidence": ["evidence.json"]}
        research.freeze(config, self.root, "versions/v1")
        self.fact["value"] = 54
        self.save_fact()
        with self.assertRaisesRegex(ValueError, "旧批准依赖"):
            research.freeze(config, self.root, "versions/v2")
        with self.assertRaisesRegex(ValueError, "旧裁决依赖"):
            research.freeze({**config, "decision": "versions/v1/decision.json"}, self.root, "versions/v3")
        ruling.pop("approval_projections")
        write(self.root, "decision.json", ruling)
        with self.assertRaisesRegex(ValueError, "审核未绑定"):
            research.freeze(config, self.root, "versions/v4")

    def test_numeric_recompute_and_dividend_year(self):
        data = copy.deepcopy(self.data)
        data["numeric_calculations"] = [{"id": "utilization", "input_fact_ids": {"u": "TEST-FACT-001"},
            "formula": "u", "result": 54, "unit": "%", "basis": "原件利用率", "same_basis": ["unit"]}]
        self.assertTrue(research.check(data, self.root, ["evidence.json"])["errors"])
        data["numeric_calculations"][0]["result"] = 86.354
        self.assertFalse(research.check(data, self.root, ["evidence.json"])["errors"])

        self.fact.update(metric="dividend", profit_attribution_year=2024, declaration_date="2025-03-01",
                         payment_date="2025-06-01", payment_status="paid")
        self.save_fact()
        calc = data["numeric_calculations"][0]
        calc.update(dividend_basis="profit_attribution_year", years=[2025])
        self.assertTrue(research.check(data, self.root, ["evidence.json"])["errors"])
        calc["dividend_basis"] = "payment_year"
        self.assertFalse(research.check(data, self.root, ["evidence.json"])["errors"])

    def test_actual_input_cannot_change_scale_silently(self):
        data = copy.deepcopy(self.data)
        model = data["valuation"]["models"][0]
        meta = model["scenarios"]["base"]["input_meta"]["eps"]
        meta.update(kind="actual", numeric_fact_id="TEST-FACT-001", unit="%")
        self.assertTrue(any("实际模型输入" in e for e in research.check(data, self.root, ["evidence.json"])["errors"]))
        meta["unit"] = "万元"
        self.assertTrue(any("单位" in e for e in research.check(data, self.root, ["evidence.json"])["errors"]))


if __name__ == "__main__":
    unittest.main()
