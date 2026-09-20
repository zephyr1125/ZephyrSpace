"""验证三件套检查能阻断已知漏项、错误计算和冻结文件覆盖。"""
import copy
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("workpaper", Path(__file__).parents[1] / "scripts/triplet_workpaper.py")
workpaper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workpaper)


def fixture():
    company, management = workpaper.scoring_rules()
    scores = {}
    for label, rules in (("company", company), ("management", management)):
        rows = [{"id": key, "score": cap * 0.6, "rule_ref": "规则原文", "reason": key + "测试用假设，不是研究结论",
                 "evidence_refs": ["原件测试定位"]} for key, cap in rules.items()]
        if label == "company":
            next(r for r in rows if r["id"] == "D2").update(original_statement_found=False, strategy_drift=False)
        scores[label] = {"items": rows, "total": sum(row["score"] for row in rows)}
    models = []
    for model_id, formula, inputs, x, y, xs, ys in (
        ("PE", "eps * pe", {"eps": 0.3, "pe": 10}, "eps", "pe", [0.2, 0.3, 0.4], [8, 10, 12]),
        ("DDM", "d0 * (1 + g) / (ke - g) / fx", {"d0": 0.154, "g": 0.025, "ke": 0.11, "fx": 0.86062},
         "ke", "g", [0.10, 0.11, 0.12], [0.01, 0.025, 0.04]),
    ):
        metadata = {key: {"unit": "测试单位", "date": "2026-09-19", "kind": "assumption", "evidence_refs": ["测试"]} for key in inputs}
        scenarios = {name: {"inputs": dict(inputs), "input_meta": copy.deepcopy(metadata),
                            "value": workpaper.expression(formula, inputs)} for name in workpaper.SCENARIOS}
        models.append({"id": model_id, "formula": formula, "weight": 0.5, "basis": "测试独立依据",
                       "shared_assumptions": ["盈利"], "output_currency": "HKD", "output_unit": "per_share",
                       "scenarios": scenarios, "sensitivity": {"x": x, "y": y, "x_values": xs, "y_values": ys,
                       "values": [[workpaper.expression(formula, {**inputs, x: xv, y: yv}) for xv in xs] for yv in ys]}})
    target = sum(model["scenarios"]["base"]["value"] * model["weight"] for model in models)
    return {"schema_version": 1, "scores": scores, "bridges": [], "bridges_not_applicable": "测试不含权益桥",
            "valuation": {"currency": "HKD", "models": models, "weighted": {name: target for name in workpaper.SCENARIOS},
                          "target_price": target, "certainty": 0.6, "certainty_reason": "测试",
                          "buy_price": target * 0.764,
                          "reverse": {"weight": 0, "variable": "pe", "implied_value": 10, "formula": "eps * pe",
                                      "inputs": {"eps": 0.3, "pe": 10}, "market_price": 3, "assumptions": "固定EPS", "evidence_refs": ["测试"]}}}


class WorkpaperTests(unittest.TestCase):
    def test_integer_totals_use_half_up_without_changing_raw_gate_scores(self):
        data = fixture()
        data["score_display"] = "integer_half_up"
        company, management = workpaper.scoring_rules()
        for name, rules in (("company", company), ("management", management)):
            for row in data["scores"][name]["items"]:
                row["score"] = rules[row["id"]] * 0.695
                if row["id"] == "D2":
                    row["original_statement_found"] = True
            data["scores"][name]["total"] = 69.5
        original = copy.deepcopy(data)
        result = workpaper.check(data, reports=False)
        self.assertEqual(result["errors"], [])
        self.assertLess(result["computed"]["cScore"], 70)
        self.assertLess(result["computed"]["mScore"], 70)
        text = workpaper.render(data)
        self.assertIn("<!-- triplet:cScore -->70<!-- /triplet:cScore -->", text)
        self.assertIn("<!-- triplet:combinedScore -->139<!-- /triplet:combinedScore -->", text)
        self.assertEqual(data, original)
        self.assertEqual(workpaper.score_display(76.5), "77")
        self.assertEqual(workpaper.score_display(76.49), "76")

    def test_integer_report_validation_and_legacy_compatibility(self):
        data = fixture()
        self.assertIn("<!-- triplet:cScore -->60.000000<!-- /triplet:cScore -->", workpaper.render(data))
        data["score_display"] = "integer_half_up"
        with tempfile.TemporaryDirectory() as directory:
            text = workpaper.render(data) + "\n" * 160
            data["reports"] = {}
            for kind in ("deep", "management", "valuation"):
                data["reports"][kind] = kind + ".md"
                Path(directory, kind + ".md").write_text(text, encoding="utf-8")
            self.assertEqual(workpaper.check(data, Path(directory))["errors"], [])
            Path(directory, "deep.md").write_text(text.replace(
                "<!-- triplet:cScore -->60<!--", "<!-- triplet:cScore -->61<!--"), encoding="utf-8")
            self.assertTrue(any("cScore" in e for e in workpaper.check(data, Path(directory))["errors"]))
        data["score_display"] = "unsupported"
        self.assertTrue(workpaper.check(data, reports=False)["errors"])

    def test_combined_display_adds_raw_scores_before_rounding(self):
        result = {"cScore": 74.4, "mScore": 74.4, "target_price": 1,
                  "certainty": 0.5, "buy_price": 0.75, "currency": "USD"}
        data = {"score_display": "integer_half_up"}
        values = workpaper.snapshot_values(data, result)
        self.assertEqual(workpaper.snapshot_text(data, "combinedScore", values["combinedScore"]), "149")
        self.assertEqual(workpaper.snapshot_text(data, "certainty", 0.5), "0.500000")

    def test_valid_and_historical_ddm_center(self):
        data = fixture()
        result = workpaper.check(data, reports=False)
        self.assertEqual(result["errors"], [])
        self.assertAlmostEqual(result["computed"]["models"]["DDM"][1][1][1], 2.1578150909, places=9)
        self.assertIn("<!-- triplet:buy_price -->", workpaper.render(data))

    def test_known_missing_matrix_and_bad_cell_are_blocked(self):
        for mutation in (lambda m: m.pop("sensitivity"),
                         lambda m: m["sensitivity"]["values"][0].pop(),
                         lambda m: m["sensitivity"]["values"][1].__setitem__(1, 999),
                         lambda m: m["sensitivity"].__setitem__("y", "ke")):
            with self.subTest(mutation=mutation):
                data = fixture()
                mutation(data["valuation"]["models"][1])
                self.assertTrue(workpaper.check(data, reports=False)["errors"])

    def test_score_missing_and_conditional_cap(self):
        data = fixture()
        data["scores"]["company"]["items"].pop()
        self.assertTrue(workpaper.check(data, reports=False)["errors"])
        data = fixture()
        d2 = next(r for r in data["scores"]["company"]["items"] if r["id"] == "D2")
        d2["score"] = 5
        data["scores"]["company"]["total"] += 2
        self.assertTrue(any("D2" in error for error in workpaper.check(data, reports=False)["errors"]))

    def test_weights_currency_metadata_and_buy_price(self):
        for mutation in (lambda v: v["models"][0].__setitem__("weight", 0.6),
                         lambda v: v["reverse"].__setitem__("weight", 0.1),
                         lambda v: v.__setitem__("buy_price", v["target_price"]),
                         lambda v: v["models"][0].__setitem__("output_currency", "CNY"),
                         lambda v: v["models"][0]["scenarios"]["base"]["input_meta"].pop("eps")):
            with self.subTest(mutation=mutation):
                data = fixture()
                mutation(data["valuation"])
                self.assertTrue(workpaper.check(data, reports=False)["errors"])

    def test_duplicate_assets_and_unclosed_acceptance(self):
        data = fixture()
        data["bridges"] = [{"id": "equity", "start": 10, "result": 14, "unit": "HKD", "date": "2026-09-19",
                            "scope": "归母", "items": [{"economic_id": "cash", "signed_value": 2, "evidence_refs": ["测试"]}] * 2}]
        self.assertTrue(any("重复" in error for error in workpaper.check(data, reports=False)["errors"]))
        data = fixture()
        data["repair"] = {"issues": [{"id": "C03", "severity": "P1", "acceptance_ids": ["formula", "matrix"]}],
                          "closures": [{"id": "C03", "locations": ["估值报告"], "score_valuation_impact": "不变，有计算依据",
                                        "checks": [{"id": "formula", "passed": True, "evidence": "计算结果"}]}]}
        self.assertTrue(workpaper.check(data, reports=False, repair=True)["errors"])

    def test_report_markers_detect_stale_values(self):
        with tempfile.TemporaryDirectory() as directory:
            data = fixture()
            text = workpaper.render(data) + "\n" * 160
            data["reports"] = {}
            for kind in ("deep", "management", "valuation"):
                filename = kind + ".md"
                data["reports"][kind] = filename
                Path(directory, filename).write_text(text, encoding="utf-8")
            self.assertEqual(workpaper.check(data, Path(directory))["errors"], [])
            path = Path(directory, "deep.md")
            path.write_text(text.replace("<!-- triplet:cScore -->60.000000", "<!-- triplet:cScore -->61.000000"), encoding="utf-8")
            self.assertTrue(workpaper.check(data, Path(directory))["errors"])

    def test_expressions_cannot_execute_code_or_accept_nan(self):
        for formula, inputs in (("__import__('os').getcwd()", {}), ("x[0]", {"x": [1]}),
                                ("x + 1", {"x": float("nan")}), ("10 ** 10000", {}), ("True", {})):
            with self.subTest(formula=formula), self.assertRaises((ValueError, TypeError)):
                workpaper.expression(formula, inputs)

    def test_matrix_in_workpaper_but_missing_from_report_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            data = fixture()
            text = workpaper.render(data) + "\n" * 160
            data["reports"] = {}
            for kind in ("deep", "management", "valuation"):
                data["reports"][kind] = kind + ".md"
                content = re.sub(r"<!-- triplet:table:model-DDM -->.*?<!-- /triplet:table:model-DDM -->", "", text, flags=re.S) if kind == "valuation" else text
                Path(directory, kind + ".md").write_text(content, encoding="utf-8")
            self.assertTrue(any("model-DDM" in error for error in workpaper.check(data, Path(directory))["errors"]))

    def test_no_overwrite_or_outside_root(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "frozen.md")
            workpaper.save_new(path, "冻结")
            with self.assertRaises(FileExistsError):
                workpaper.save_new(path, "替换")
            self.assertEqual(path.read_text(encoding="utf-8"), "冻结")
            with self.assertRaises(ValueError):
                workpaper.local(Path(directory), "../outside.md")

    def test_repair_package_derived_without_changing_judgment(self):
        data = {"issues": [{"id": "C03", "candidate_ids": ["C001"], "severity": "P1", "decision": "valid",
                            "reason": "缺双变量矩阵", "evidence_refs": ["估值原件"], "action": "补矩阵",
                            "score_valuation_impact": "不改基准价", "acceptance": [{"id": "matrix", "condition": "核对9格"}]}],
                "parameters": {"target_price": None, "reason": "待修复"}}
        original = copy.deepcopy(data)
        output = workpaper.repair_package(data)
        self.assertIn("matrix：核对9格", output)
        self.assertEqual(data, original)

    def test_migration_reconstructs_current_original_rules(self):
        result = workpaper.verify_migration(workpaper.ROOT / "docs/three-report-rule-migration.json")
        self.assertEqual(result["modules"], 3)

    def test_nike_repeated_placeholder_regression_is_blocked(self):
        data = fixture()
        for row in data["scores"]["company"]["items"]:
            row["reason"] = "见最终修订报告评分桥；事实、规则与限制按V5统一。"
        self.assertTrue(any("相同理由" in error for error in workpaper.check(data, reports=False)["errors"]))

    def test_unchanged_scores_must_survive_repair(self):
        previous = fixture()
        data = copy.deepcopy(previous)
        data["repair"] = {"issues": [], "closures": [], "score_changes": []}
        self.assertEqual(workpaper.check(data, reports=False, repair=True, previous=previous)["errors"], [])
        data["scores"]["company"]["items"][0]["evidence_refs"] = ["只见最终报告"]
        self.assertTrue(any("未映射" in e for e in workpaper.check(data, reports=False, repair=True, previous=previous)["errors"]))
        self.assertTrue(any("--previous" in e for e in workpaper.check(data, reports=False, repair=True)["errors"]))

    def test_report_rewrite_outside_declared_repair_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = fixture()
            previous["reports"] = {}
            content = workpaper.render(previous) + "\n## 已核实治理\n保留董事与任期证据。\n" + "\n" * 160
            for kind in ("deep", "management", "valuation"):
                previous["reports"][kind] = kind + "-old.md"
                (root / (kind + "-old.md")).write_text(content, encoding="utf-8")
            data = copy.deepcopy(previous)
            data["repair"] = {"issues": [], "closures": [], "score_changes": [], "report_changes": []}
            for kind in data["reports"]:
                data["reports"][kind] = kind + "-new.md"
                (root / (kind + "-new.md")).write_text(content, encoding="utf-8")
            self.assertEqual(workpaper.check(data, root, repair=True, previous=previous)["errors"], [])
            (root / "management-new.md").write_text(content.replace("保留董事与任期证据。", "略。"), encoding="utf-8")
            self.assertTrue(any("未声明重写" in e for e in workpaper.check(data, root, repair=True, previous=previous)["errors"]))


if __name__ == "__main__":
    unittest.main()
