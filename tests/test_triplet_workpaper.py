"""验证三件套检查能阻断已知漏项、错误计算和冻结文件覆盖。"""
import copy
import importlib.util
import json
import re
import subprocess
import sys
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


def report_body(kind):
    """结构测试的分离正文；不同条目避免依赖空行或重复占位通过检查。"""
    topics = {"deep": ("业务", "渠道", "产品", "客户", "成本", "竞争"),
              "management": ("治理", "董事", "任期", "激励", "配置", "回报"),
              "valuation": ("假设", "折现", "情景", "敏感性", "现金流", "交叉验证")}[kind]
    axes = ("历史", "当前", "预期", "反证", "约束")
    evidence = ("年报", "公告", "计算", "访谈", "行业")
    return "\n" + "\n".join("## " + topic + "\n" + "\n".join(
        f"{kind}的{topic}在{axis}条件下，根据{source}定位核验该维度的依据及适用限制。"
        for axis in axes for source in evidence) for topic in topics) + "\n"


class WorkpaperTests(unittest.TestCase):
    def test_unresolved_scoring_evidence_blocks_writing(self):
        adjudication = {"issues": [{"id": "A01", "severity": "P1", "decision": "valid",
                                    "acceptance": [{"id": "capital"}]}]}
        preparation = {"items": [{"id": "capital", "kind": "evidence", "status": "open",
                                  "resolution": "五年回购净效果未核实，暂给中档分", "evidence_refs": ["年报"]}]}
        self.assertEqual(workpaper.repair_readiness(preparation, adjudication)["status"], "failed")
        preparation["items"][0].update(status="resolved", resolution="已列原始回购额、均价、净股数和SBC抵消桥")
        self.assertEqual(workpaper.repair_readiness(preparation, adjudication)["status"], "ready_for_repair_writing")
        preparation["items"] = []
        self.assertEqual(workpaper.repair_readiness(preparation, adjudication)["status"], "failed")

    def test_stale_known_text_cannot_survive_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root, previous = Path(directory), fixture()
            self.make_reports(root, previous, "-old")
            data = copy.deepcopy(previous)
            self.make_reports(root, data, "-new")
            data["repair"] = {"issues": [], "closures": [], "score_changes": [], "report_changes": []}
            preparation = {"items": [], "replacements": [{"report": "valuation", "old": "取得CFO 8-K正文",
                                                          "new": "已核CFO 8-K正文"}]}
            result = workpaper.handoff(data, root, "repair", previous, {"issues": []}, preparation)
            self.assertTrue(any("新文未落实" in e for e in result["errors"]))
            path = root / data["reports"]["valuation"]
            original = path.read_text(encoding="utf-8")
            data["repair"]["issues"] = [{"id": "text", "severity": "P2"}]
            data["repair"]["report_changes"] = [{"report": "valuation", "section": "交接状态",
                                                 "issue_id": "text", "reason": "修正已取得公告的状态"}]
            path.write_text(original + "## 交接状态\n取得CFO 8-K正文\n已核CFO 8-K正文\n", encoding="utf-8")
            self.assertTrue(any("旧文未清除" in e for e in workpaper.handoff(
                data, root, "repair", previous, {"issues": []}, preparation)["errors"]))
            path.write_text(original + "## 交接状态\n已核CFO 8-K正文\n", encoding="utf-8")
            self.assertEqual(workpaper.handoff(data, root, "repair", previous, {"issues": []}, preparation)["errors"], [])

    def make_reports(self, root, data, suffix=""):
        data["reports"] = {kind: kind + suffix + ".md" for kind in ("deep", "management", "valuation")}
        tables = workpaper.render(data)
        for kind, name in data["reports"].items():
            (root / name).write_text(tables + report_body(kind), encoding="utf-8")

    def test_nike_v3_same_summary_and_numbered_padding_are_blocked(self):
        # 保留真实失败机制，避免测试依赖本地被忽略的耐克草稿。
        with tempfile.TemporaryDirectory() as directory:
            root, data = Path(directory), fixture()
            self.make_reports(root, data)
            text = "# NIKE v3定向修复稿\n## 事实与口径\n品牌和渠道经营基础仍在，收入利润现金流修复尚需验证。\n"
            text += "\n".join(f"- 修复核对记录{i}：本段不引入新事实；以v2增量、底稿和上述唯一结论为准。" for i in range(1, 116))
            for kind, name in data["reports"].items():
                (root / name).write_text(f"> 文档类型：{kind}。\n" + text + workpaper.render(data), encoding="utf-8")
            result = workpaper.check(data, root)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("编号占位" in e for e in result["errors"]))
            self.assertTrue(any("同文" in e for e in result["errors"]))

    def test_shared_tables_allowed_but_distinct_body_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root, data = Path(directory), fixture()
            self.make_reports(root, data)
            self.assertEqual(workpaper.check(data, root)["errors"], [])
            for name in data["reports"].values():
                (root / name).write_text(workpaper.render(data) + "\n" * 160, encoding="utf-8")
            self.assertTrue(any("缺独立分析正文" in e for e in workpaper.check(data, root)["errors"]))

    def test_repair_cannot_use_plain_check_or_initial_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root, data = Path(directory), fixture()
            self.make_reports(root, data)
            data["repair"] = {"issues": [], "closures": [], "score_changes": [], "report_changes": []}
            self.assertTrue(any("不得跳过" in e for e in workpaper.check(data, root)["errors"]))
            self.assertEqual(workpaper.handoff(data, root)["status"], "failed")
            # 表格渲染仍可用，但不具备送审资格。
            self.assertIn("triplet:cScore", workpaper.render(data))

    def test_handoff_locks_acceptance_and_previous_and_report_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, previous = Path(directory), fixture()
            self.make_reports(root, previous, "-old")
            data = copy.deepcopy(previous)
            self.make_reports(root, data, "-new")
            data["repair"] = {"issues": [], "closures": [], "score_changes": [], "report_changes": []}
            adjudication = {"issues": []}
            preparation = {"items": []}
            result = workpaper.handoff(data, root, "repair", previous, adjudication, preparation)
            self.assertEqual(result["status"], "ready_for_independent_review")
            self.assertTrue(result["scope"]["repair"])
            self.assertEqual(len(result["report_sha256"]), 3)
            self.assertEqual(workpaper.handoff(data, root, "repair")["status"], "failed")
            adjudication["issues"] = [{"id": "A01", "severity": "P1", "decision": "valid", "acceptance": [{"id": "A01-body"}]}]
            preparation["items"] = [{"id": "A01-body", "kind": "text", "status": "resolved", "resolution": "正文已独立核对", "evidence_refs": ["原件位置"]}]
            result = workpaper.handoff(data, root, "repair", previous, adjudication, preparation)
            self.assertTrue(any("锁定裁决不一致" in e for e in result["errors"]))
            data["repair"]["issues"] = [{"id": "A01", "severity": "P1", "acceptance_ids": ["A01-body"]}]
            data["repair"]["closures"] = [{"id": "A01", "locations": ["三稿各自正文"],
                                          "score_valuation_impact": "经核查不变", "checks": [
                                              {"id": "A01-body", "passed": True, "evidence": "独立内容位置"}]}]
            self.assertEqual(workpaper.handoff(data, root, "repair", previous, adjudication, preparation)["errors"], [])
            data["repair"]["issues"][0]["severity"] = "P2"
            self.assertTrue(any("锁定裁决不一致" in e for e in workpaper.handoff(data, root, "repair", previous, adjudication, preparation)["errors"]))

    def test_declared_mass_deletion_cannot_pass_as_directed_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root, previous = Path(directory), fixture()
            self.make_reports(root, previous, "-old")
            data = copy.deepcopy(previous)
            self.make_reports(root, data, "-new")
            data["repair"] = {"issues": [{"id": "A01", "severity": "P1", "acceptance_ids": ["body"]}],
                              "closures": [{"id": "A01", "locations": ["deep"], "score_valuation_impact": "不变",
                                            "checks": [{"id": "body", "passed": True, "evidence": "作者声明"}]}],
                              "score_changes": [], "report_changes": []}
            text = workpaper.render(data) + "\n## 摘要\n业务收入增长，渠道和竞争情况需要分别核对。\n" + "\n" * 160
            (root / data["reports"]["deep"]).write_text(text, encoding="utf-8")
            for section in workpaper.report_sections(report_body("deep")):
                if section != "__preamble__":
                    data["repair"]["report_changes"].append({"report": "deep", "section": section, "issue_id": "A01", "reason": "压缩", "replacement_section": "摘要"})
            result = workpaper.check(data, root, repair=True, previous=previous)
            self.assertTrue(any("大面积丢失" in e for e in result["errors"]))

    def test_illegal_score_item_can_be_removed_only_with_declared_issue(self):
        previous, data = fixture(), fixture()
        previous["scores"]["company"]["items"].append({"id": "F4", "score": 2})
        previous["scores"]["company"]["total"] += 2
        data["repair"] = {"issues": [{"id": "A01", "severity": "P2"}], "closures": [],
                          "score_changes": [{"key": "company/F4", "issue_id": "A01", "reason": "删除非法项", "evidence_refs": ["唯一评分规则"]}]}
        self.assertEqual(workpaper.check(data, reports=False, repair=True, previous=previous)["errors"], [])
        data["repair"]["score_changes"] = []
        self.assertTrue(any("未映射" in e for e in workpaper.check(data, reports=False, repair=True, previous=previous)["errors"]))

    def test_handoff_cli_exits_nonzero_without_repair_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root, data = Path(directory), fixture()
            self.make_reports(root, data)
            path = root / "workpaper.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, "-X", "utf8", str(workpaper.ROOT / "scripts/triplet_workpaper.py"),
                                     "handoff", str(path), "--root", str(root), "--stage", "repair"],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 1)
            self.assertIn("--adjudication", result.stdout)
            result = subprocess.run([sys.executable, "-X", "utf8", str(workpaper.ROOT / "scripts/triplet_workpaper.py"),
                                     "handoff", str(path), "--root", str(root), "--stage", "initial"],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ready_for_independent_review")
            self.assertEqual(len(payload["report_sha256"]), 3)
            self.assertIn("workpaper", payload["input_sha256"])

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
                Path(directory, kind + ".md").write_text(text + report_body(kind), encoding="utf-8")
            self.assertEqual(workpaper.check(data, Path(directory))["errors"], [])
            Path(directory, "deep.md").write_text(text.replace(
                "<!-- triplet:cScore -->60<!--", "<!-- triplet:cScore -->61<!--") + report_body("deep"), encoding="utf-8")
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

    def test_quality_gate_stop_keeps_price_fields_null(self):
        data = fixture()
        data["valuation"] = {"status": "stopped_quality_gate_after_full_research", "currency": "USD",
                             "models": [], "target_price": None, "certainty": None, "buy_price": None,
                             "reason": "原始评分可信否决全部入池档位"}
        result = workpaper.check(data, reports=False)
        self.assertEqual(result["errors"], [])
        self.assertIsNone(result["computed"]["target_price"])
        self.assertIn("<!-- triplet:target_price -->null<!--", workpaper.render(data))
        data["valuation"]["target_price"] = 1
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
                Path(directory, filename).write_text(text + report_body(kind), encoding="utf-8")
            self.assertEqual(workpaper.check(data, Path(directory))["errors"], [])
            path = Path(directory, "deep.md")
            path.write_text(text.replace("<!-- triplet:cScore -->60.000000", "<!-- triplet:cScore -->61.000000") + report_body("deep"), encoding="utf-8")
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
                Path(directory, kind + ".md").write_text(content + report_body(kind), encoding="utf-8")
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

    def test_repair_package_accepts_adjudicator_original_finding(self):
        data = {"issues": [{"id": "A09", "candidate_ids": [], "severity": "P1", "decision": "valid",
                            "reason": "裁决回看原件发现口径错误", "evidence_refs": ["年报原件"], "action": "纠正口径",
                            "score_valuation_impact": "重算受影响分项", "acceptance": [{"id": "A09-fact", "condition": "核对原值"}]}],
                "parameters": {"target_price": None}}
        output = workpaper.repair_package(data)
        self.assertIn("候选：裁决原件新增", output)
        self.assertIn("A09-fact：核对原值", output)

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
                (root / (kind + "-old.md")).write_text(content + report_body(kind), encoding="utf-8")
            data = copy.deepcopy(previous)
            data["repair"] = {"issues": [], "closures": [], "score_changes": [], "report_changes": []}
            for kind in data["reports"]:
                data["reports"][kind] = kind + "-new.md"
                (root / (kind + "-new.md")).write_text(content + report_body(kind), encoding="utf-8")
            self.assertEqual(workpaper.check(data, root, repair=True, previous=previous)["errors"], [])
            (root / "management-new.md").write_text(content.replace("保留董事与任期证据。", "略。") + report_body("management"), encoding="utf-8")
            self.assertTrue(any("未声明重写" in e for e in workpaper.check(data, root, repair=True, previous=previous)["errors"]))


if __name__ == "__main__":
    unittest.main()
