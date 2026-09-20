"""验证交付装配、引用解析、区间分数与局部补丁，不代替投资判断测试。"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import triplet_delivery as delivery
from test_triplet_workpaper import fixture, report_body


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), encoding="utf-8")


def sample(root):
    data = fixture()
    for sheet in data["scores"].values():
        for row in sheet["items"]:
            row["evidence_refs"] = ["TEST-FACT-001"]
    write(root, "workpaper.json", data)
    write(root, "evidence.json", {"facts": [{"fact_id": "TEST-FACT-001", "source_id": "SOURCE-001", "raw_value": "公开任职安排"}]})
    write(root, "decision.json", {"decision": "defer", "research_state": "pending", "basis": "测试研究判断待独立复核",
                                   "review_refs": [], "issues": []})
    bundle = {"schema_version": 1, "workpaper": "workpaper.json", "decision": "decision.json",
              "evidence": ["evidence.json"], "id_prefixes": ["TEST-"],
              "facts": {"cfo": {"text": "已核公开任职安排，个人动机未披露。", "refs": ["TEST-FACT-001"],
                                  "retired": ["尚未取得高管公告"]}},
              "templates": {kind: kind + ".md" for kind in delivery.KINDS}}
    for kind, path in bundle["templates"].items():
        table = "{{table:company}}" if kind == "deep" else "{{table:management}}" if kind == "management" else "{{table:model-PE}}\n{{table:model-DDM}}\n{{table:weighted}}"
        write(root, path, "{{decision}}\n{{fact:cfo}}\n" + table + report_body(kind))
    return bundle


class DeliveryTests(unittest.TestCase):
    def test_explicit_tiers_reject_plausible_but_unlisted_intermediate_scores(self):
        for key, value in (("A3", 3), ("D1", 3), ("F2", 4)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key + "违反"):
                delivery.wp.validate_explicit_tiers([{"id": key, "score": value}])
        delivery.wp.validate_explicit_tiers([{"id": "A3", "score": 4}, {"id": "D1", "score": 2},
                                            {"id": "F2", "score": 0.5}])
        data = fixture()
        data["score_rule_validation"] = "explicit_tiers_v1"
        for item in data["scores"]["company"]["items"]:
            if item["id"] in ("A3", "F2"):
                item["score"] = {"A3": 2, "F2": 3}[item["id"]]
        row = next(row for row in data["scores"]["company"]["items"] if row["id"] == "D1")
        row["score"] = 3
        data["scores"]["company"]["total"] = sum(item["score"] for item in data["scores"]["company"]["items"])
        self.assertTrue(any("D1违反" in error for error in delivery.wp.check(data, reports=False)["errors"]))

    def test_approved_score_is_not_approved_full_research(self):
        ledger = {"decision": "defer", "research_state": "approved", "score_state": "approved",
                  "research_status": "execution_incomplete", "basis": "仅评分通过", "issues": [],
                  "review_refs": ["a.json", "b.json"]}
        with self.assertRaisesRegex(ValueError, "完整研究"):
            delivery.validate_decision(ledger)
        ledger["research_state"] = "pending"
        delivery.validate_decision(ledger)

    def test_score_phase_cli_does_not_require_reports_or_claim_to_check_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = fixture()
            data.pop("reports", None)
            write(root, "workpaper.json", data)
            result = subprocess.run([sys.executable, "-X", "utf8", str(delivery.wp.ROOT / "scripts/triplet_workpaper.py"),
                                     "check", str(root / "workpaper.json"), "--no-reports"],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(json.loads(result.stdout)["scope"]["reports"])

    def test_deferred_valuation_preserves_scores_without_quality_rejection(self):
        for interval in (False, True):
            with self.subTest(interval=interval), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = sample(root)
                data = delivery.wp.read(root / "workpaper.json")
                if interval:
                    sheet = data["scores"]["management"]
                    row = sheet["items"][-1]
                    old = row["score"]
                    row.update(score=None, bounds=[0, 5], bounds_reason="测试决定性事实仍有两种可能")
                    sheet.update(bounds=[sheet["total"] - old, sheet["total"] - old + 5], total=None)
                data["valuation"] = {"status": "deferred", "currency": "HKD", "models": [],
                                     "target_price": None, "certainty": None, "buy_price": None,
                                     "reason": "决定性估值输入待核，不能发布价格"}
                ledger = delivery.wp.read(root / "decision.json")
                ledger["score_bounds"] = delivery.score_ranges(data)
                write(root, "decision.json", ledger)
                write(root, "workpaper.json", data)
                if not interval:
                    rendered = delivery.wp.render(data)
                    self.assertNotIn("triplet:table:weighted", rendered)
                    self.assertIn("null", rendered)
                write(root, "valuation.md", "{{decision}}\n{{fact:cfo}}\n" + report_body("valuation"))
                texts, manifest = delivery.assemble(bundle, root)
                self.assertEqual(manifest["score_bounds"], ledger["score_bounds"])
                self.assertFalse(manifest["publish_allowed"])
                self.assertIn("正式估值暂缓", texts["valuation"])
                self.assertNotIn("候选方案为停止正式定价", texts["valuation"])
                ledger["decision"] = "eligible"
                write(root, "decision.json", ledger)
                with self.assertRaises(ValueError):
                    delivery.assemble(bundle, root)
                ledger["decision"] = "defer"
                ledger["quality_stop_approved"] = True
                write(root, "decision.json", ledger)
                with self.assertRaisesRegex(ValueError, "质量否决"):
                    delivery.assemble(bundle, root)
                ledger.pop("quality_stop_approved")
                write(root, "decision.json", ledger)
                data["valuation"]["target_price"] = 10
                write(root, "workpaper.json", data)
                with self.assertRaisesRegex(ValueError, "null"):
                    delivery.assemble(bundle, root)

    def test_publication_guard_catches_real_nike_residuals_not_real_unknowns(self):
        bad = ["类型: 深度分析草稿", "# NIKE 管理层档案（例外修复稿）",
               "本稿尚待主任务 `handoff --stage repair` 与双路定向复查，不代表通过或可入库。",
               "本稿尚待主任务交接检查与双路定向复查，不代表最终评级。",
               "质量停止判断已获批准；交付装配仍待定向验收。", "机械校验端点: 66",
               "机械表使用下端点66/56/122以闭合算术", "机械校验采用锁定外包络下端点0"]
        for line in bad:
            with self.subTest(line=line):
                self.assertTrue(delivery.publication_errors({"deep": line}))
        self.assertEqual(delivery.publication_errors({"deep": "仍待未披露的人才保留率、个人动机及未来经营修复。"}), [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            bundle["publication_ready"] = True
            with (root / "deep.md").open("a", encoding="utf-8") as stream:
                stream.write("\n" + bad[2])
            with self.assertRaisesRegex(ValueError, "发布流程"):
                delivery.build(bundle, root, "out")
            self.assertFalse((root / "out").exists())

    def release_fixture(self, root):
        bundle = sample(root)
        ledger = delivery.wp.read(root / "decision.json")
        ledger.update(research_state="approved", score_bounds=delivery.score_ranges(delivery.wp.read(root / "workpaper.json")),
                      review_refs=["data/first-review.json", "data/second-review.json"])
        for ref in ledger["review_refs"]:
            write(root, ref, {"status": "pass"})
        write(root, "decision.json", ledger)
        manifest = delivery.build(bundle, root, "build")
        write(root, "data/review.json", {"status": "pass", "scope": "测试独立验收"})
        auth = {"publish_allowed": True, "delivery_state": "approved", "issues": [],
                "decision": manifest["decision"], "research_state": manifest["research_state"],
                "score_bounds": manifest["score_bounds"],
                "approved_manifest_sha256": delivery.digest((root / "build/manifest.json").read_bytes()),
                "approved_report_sha256": manifest["reports"], "release_review_refs": ["data/review.json"]}
        write(root, "authorization.json", auth)
        reports = {}
        for name in manifest["reports"]:
            reports[name] = "published/" + name
            (root / "published").mkdir(exist_ok=True)
            (root / reports[name]).write_bytes((root / "build" / name).read_bytes())
        return {"manifest": "build/manifest.json", "authorization": "authorization.json", "reports": reports}

    def test_release_archive_is_portable_and_detects_changes(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self.release_fixture(root)
            self.assertEqual(delivery.archive_release(config, root, "final/release-v1")["status"], "release_verified")
            receipt = root / "final/release-v1/release.json"
            saved = delivery.wp.read(receipt)
            self.assertIn("data/review.json", saved["files"])
            shutil.rmtree(root / "build")
            (root / "data/review.json").unlink()
            (root / "workpaper.json").unlink()
            self.assertEqual(delivery.verify_release(receipt, root)["reports"], 3)
            snapshot = receipt.parent / saved["files"]["data/review.json"]["archive"]
            old_bytes = snapshot.read_bytes()
            snapshot.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, "归档依据哈希不符"):
                delivery.verify_release(receipt, root)
            snapshot.write_bytes(old_bytes)
            write(root, "published/deep.md", "错误版本")
            with self.assertRaisesRegex(ValueError, "正式报告已变化"):
                delivery.verify_release(receipt, root)

    def test_release_rejects_wrong_version_and_missing_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self.release_fixture(root)
            auth = delivery.wp.read(root / "authorization.json")
            good = copy.deepcopy(auth)
            auth["issues"] = [{"status": "closed", "acceptance": [{"status": "open"}]}]
            write(root, "authorization.json", auth)
            with self.assertRaisesRegex(ValueError, "未通过验收条件"):
                delivery.archive_release(config, root, "final/v1")
            auth = copy.deepcopy(good)
            auth["approved_manifest_sha256"] = "旧版哈希"
            write(root, "authorization.json", auth)
            with self.assertRaisesRegex(ValueError, "manifest不一致"):
                delivery.archive_release(config, root, "final/v1")
            self.assertFalse((root / "final/v1").exists())
            write(root, "authorization.json", good)
            (root / "data/review.json").unlink()
            with self.assertRaises(OSError):
                delivery.archive_release(config, root, "final/v1")
            self.assertFalse((root / "final/v1").exists())

    def test_release_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self.release_fixture(root)
            write(root, "release-config.json", config)
            cli = [sys.executable, "-X", "utf8", str(delivery.wp.ROOT / "scripts/triplet_delivery.py")]
            result = subprocess.run(cli + ["archive-release", str(root / "release-config.json"), "--root", str(root),
                                           "--output", "final/v1"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "release_verified")
            write(root, "published/deep.md", "错误版本")
            result = subprocess.run(cli + ["verify-release", str(root / "final/v1/release.json"), "--root", str(root)],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 1)
            self.assertIn("正式报告已变化", result.stdout)

    def test_release_detects_git_ignored_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            config = self.release_fixture(root)
            delivery.archive_release(config, root, "final/v1")
            write(root, ".gitignore", "final/v1/inputs/\n")
            with self.assertRaisesRegex(ValueError, "Git忽略"):
                delivery.verify_release(root / "final/v1/release.json", root)

    def test_build_is_deterministic_and_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            first = delivery.build(bundle, root, "out-a")
            second = delivery.build(bundle, root, "out-b")
            self.assertEqual(first, second)
            self.assertFalse(first["publish_allowed"])
            self.assertEqual(delivery.verify(root / "out-a/manifest.json", root)["status"], "version_verified")
            with self.assertRaisesRegex(ValueError, "全新"):
                delivery.build(bundle, root, "out-a")
            write(root, "out-a/deep.md", "未经核验的改稿")
            with self.assertRaisesRegex(ValueError, "手改"):
                delivery.verify(root / "out-a/manifest.json", root)

    def test_nike_wrong_ids_and_shortened_ids_are_rejected(self):
        index = {"NKE-BND-CAL-001": {}, "NKE-BND-ORG-001": {}, "NKE-BND-ORG-002": {}, "NKE-BND-ORG-003": {}}
        errors, _ = delivery.scan_references({"report": "[NKE-CAL-BND-001；NKE-BND-CAP-004；NKE-BND-ORG-001/002/003/004]"}, index, ["NKE-BND-", "NKE-CAL-BND-"])
        self.assertTrue(any("NKE-CAL-BND-001" in e for e in errors))
        self.assertTrue(any("NKE-BND-CAP-004" in e for e in errors))
        self.assertTrue(any("压缩" in e for e in errors))

    def test_registry_does_not_register_source_reference_as_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample(root)
            index = delivery.evidence_index(root, ["evidence.json"])
            self.assertNotIn("SOURCE-001", index)
            with self.assertRaisesRegex(ValueError, "重复"):
                delivery.evidence_index(root, ["evidence.json", "evidence.json"])

    def test_unknown_reference_prevents_any_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            data = delivery.wp.read(root / "workpaper.json")
            data["scores"]["company"]["items"][0]["evidence_refs"] = ["TEST-NOT-EXIST"]
            write(root, "workpaper.json", data)
            with self.assertRaisesRegex(ValueError, "未注册|不存在"):
                delivery.build(bundle, root, "out")
            self.assertFalse((root / "out").exists())
            data["scores"]["company"]["items"][0]["evidence_refs"] = ["TEST-FACT-001"]
            write(root, "workpaper.json", data)
            self.assertEqual(delivery.build(bundle, root, "out")["status"], "assembled_for_review")

    def test_unknown_tokens_and_output_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            with self.assertRaisesRegex(ValueError, "根目录"):
                delivery.build(bundle, root, "../outside-vault")
            with (root / "deep.md").open("a", encoding="utf-8") as stream:
                stream.write("\n{{unknown:field}}\n")
            with self.assertRaisesRegex(ValueError, "未解析"):
                delivery.build(bundle, root, "out")
            self.assertFalse((root / "out").exists())

    def test_registry_change_invalidates_frozen_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            delivery.build(bundle, root, "out")
            write(root, "evidence.json", {"facts": []})
            with self.assertRaisesRegex(ValueError, "源文件已变化"):
                delivery.verify(root / "out/manifest.json", root)

    def test_shared_fact_changes_all_reports_and_retired_text_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            bundle["facts"]["cfo"]["text"] = "已核五年高管时间线，动机和保留率仍未知。"
            texts, _ = delivery.assemble(bundle, root)
            self.assertTrue(all(bundle["facts"]["cfo"]["text"] in text for text in texts.values()))
            with (root / "valuation.md").open("a", encoding="utf-8") as stream:
                stream.write("\n尚未取得高管公告\n")
            with self.assertRaisesRegex(ValueError, "过期事实"):
                delivery.assemble(bundle, root)

    def test_interval_totals_never_become_point_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            data = delivery.wp.read(root / "workpaper.json")
            row = data["scores"]["management"]["items"][-1]
            old = row["score"]
            row.update(score=None, bounds=[0, 5], bounds_reason="未排除规则全域，非实际零分")
            sheet = data["scores"]["management"]
            sheet["bounds"] = [sheet["total"] - old, sheet["total"] - old + 5]
            sheet["total"] = None
            data["valuation"] = {"status": "stopped_quality_gate_after_full_research", "currency": "HKD", "models": [],
                                 "target_price": None, "certainty": None, "buy_price": None, "reason": "测试有据边界否决"}
            bounds = delivery.score_ranges(data)
            ledger = delivery.wp.read(root / "decision.json")
            ledger.update(decision="reject", bounds_approved=True, quality_stop_approved=True, score_bounds=bounds)
            write(root, "decision.json", ledger)
            write(root, "workpaper.json", data)
            write(root, "valuation.md", "{{decision}}\n{{fact:cfo}}\n" + report_body("valuation"))
            texts, manifest = delivery.assemble(bundle, root)
            self.assertEqual(manifest["score_bounds"], bounds)
            self.assertIn("57–62", texts["management"])
            self.assertNotIn("管理层：57；", texts["management"])
            ledger.pop("bounds_approved")
            ledger.pop("quality_stop_approved")
            write(root, "decision.json", ledger)
            candidate, candidate_manifest = delivery.assemble(bundle, root)
            self.assertIn("候选方案为停止正式定价", candidate["valuation"])
            self.assertFalse(candidate_manifest["publish_allowed"])
            with self.assertRaisesRegex(ValueError, "研究及发布批准"):
                delivery.require_release_approval({"publish_allowed": True, "delivery_state": "approved",
                                                  "research_state": "pending", "issues": [], "release_review_refs": ["x"]})
            ledger.update(research_state="approved", review_refs=["first.json", "second.json"])
            write(root, "first.json", {})
            write(root, "second.json", {})
            write(root, "decision.json", ledger)
            with self.assertRaisesRegex(ValueError, "区间批准"):
                delivery.assemble(bundle, root)
            ledger.update(research_state="pending")
            write(root, "decision.json", ledger)
            bundle["publication_ready"] = True
            original_text = (root / "management.md").read_text(encoding="utf-8")
            write(root, "management.md", original_text + "\n" + row["id"] + "为0分。\n")
            with self.assertRaisesRegex(ValueError, "表述为点值"):
                delivery.assemble(bundle, root)
            write(root, "management.md", original_text)
            data["bridges"] = [{"id": "shares", "start": 1532, "result": 1503, "unit": "百万股", "date": "FY2024",
                               "scope": "总普通股", "items": [
                                   {"economic_id": "options", "signed_value": 7, "evidence_refs": ["TEST-FACT-001"]},
                                   {"economic_id": "repurchase", "signed_value": -41, "evidence_refs": ["TEST-FACT-001"]},
                                   {"economic_id": "employee", "signed_value": 5, "evidence_refs": ["TEST-FACT-001"]}]}]
            write(root, "workpaper.json", data)
            self.assertEqual(delivery.assemble(bundle, root)[1]["score_bounds"], bounds)
            data["bridges"][0]["result"] = 1504
            write(root, "workpaper.json", data)
            with self.assertRaisesRegex(ValueError, "桥接"):
                delivery.assemble(bundle, root)
            data["bridges"] = []
            sheet["total"] = 57
            write(root, "workpaper.json", data)
            with self.assertRaisesRegex(ValueError, "端点"):
                delivery.assemble(bundle, root)

    def test_delivery_issue_does_not_revoke_research_but_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            ledger = delivery.wp.read(root / "decision.json")
            write(root, "review-facts.json", {"fixture": "独立事实复核测试"})
            write(root, "review-reasoning.json", {"fixture": "独立推理复核测试"})
            ledger.update(research_state="approved", decision="reject", review_refs=["review-facts.json", "review-reasoning.json"],
                          score_bounds=delivery.score_ranges(delivery.wp.read(root / "workpaper.json")),
                          issues=[{"id": "D01", "lane": "delivery", "status": "open", "reason": "引用显示有误",
                                   "acceptance": "核对正确来源", "classified_by": "adjudicator", "no_decision_impact": True}])
            write(root, "decision.json", ledger)
            _, manifest = delivery.assemble(bundle, root)
            self.assertEqual(manifest["research_state"], "approved")
            self.assertFalse(manifest["publish_allowed"])
            ledger["issues"][0]["lane"] = "research"
            write(root, "decision.json", ledger)
            with self.assertRaisesRegex(ValueError, "未关闭研究"):
                delivery.assemble(bundle, root)

    def test_patch_is_exact_review_scoped_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            ledger = delivery.wp.read(root / "decision.json")
            ledger["issues"] = [{"id": "D01", "lane": "delivery", "status": "open", "reason": "措辞修正",
                                 "acceptance": "仅一处措辞", "classified_by": "adjudicator", "no_decision_impact": True}]
            write(root, "decision.json", ledger)
            raw = (root / "deep.md").read_bytes()
            plan = {"edits": [{"path": "deep.md", "before_sha256": delivery.digest(raw), "old": "## 业务", "new": "## 商业模式",
                               "count": 1, "issue_id": "D01"}]}
            result = delivery.patch_templates(bundle, plan, root, "patch")
            self.assertEqual((root / "deep.md").read_bytes(), raw)
            self.assertIn("## 商业模式", (root / result["mapping"]["deep.md"]).read_text(encoding="utf-8"))
            plan["edits"][0]["count"] = 2
            with self.assertRaisesRegex(ValueError, "次数"):
                delivery.patch_templates(bundle, plan, root, "bad")
            self.assertFalse((root / "bad").exists())
            plan["edits"][0]["path"] = "workpaper.json"
            with self.assertRaisesRegex(ValueError, "仅允许"):
                delivery.patch_templates(bundle, plan, root, "bad")

    def test_delivery_downgrade_requires_adjudication(self):
        ledger = {"decision": "defer", "research_state": "pending", "basis": "未知待核", "review_refs": [],
                  "issues": [{"id": "D01", "lane": "delivery", "status": "open", "reason": "引用错误",
                              "acceptance": "核真实来源"}]}
        with self.assertRaisesRegex(ValueError, "裁决"):
            delivery.validate_decision(ledger)

    def test_cli_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = sample(root)
            write(root, "bundle.json", bundle)
            result = subprocess.run([sys.executable, "-X", "utf8", str(delivery.wp.ROOT / "scripts/triplet_delivery.py"),
                                     "build", str(root / "bundle.json"), "--root", str(root), "--output", "out"],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "assembled_for_review")


if __name__ == "__main__":
    unittest.main()
