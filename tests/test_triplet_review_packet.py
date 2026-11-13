"""审核包回归：防止压缩丢规则、丢来源和把缺证伪装成批准。"""
import copy
import tempfile
import unittest
from pathlib import Path

from scripts import triplet_review_packet as packet
from test_triplet_delivery import sample, write


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        sample(self.root)
        self.data = packet.wp.read(self.root / "workpaper.json")
        def normalize(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "evidence_refs":
                        value[key] = ["TEST-REF"]
                    else:
                        normalize(child)
            elif isinstance(value, list):
                for child in value:
                    normalize(child)
        normalize(self.data)
        self.data["valuation"]["models"][0]["evidence_refs"] = ["FACT-1"]
        self.records = {"facts": [{"fact_id": "FACT-1", "source_ids": ["SOURCE-1"], "statement": "测试事实"}],
                        "sources": [{"source_id": "SOURCE-1", "url": "https://example.com/original"}]}
        # 样例含与本试验无关的引用，将其显式注册，避免掩盖依赖遗漏。
        for key in packet.references({"valuation": self.data["valuation"], "bridges": self.data.get("bridges", [])}):
            if key != "FACT-1":
                self.records["facts"].append({"fact_id": key, "statement": "样例引用"})
        write(self.root, "evidence.json", self.records)

    def build(self):
        return packet.build(self.data, self.root, ["evidence.json"])

    def test_preserves_models_and_formula_without_claiming_approval(self):
        before = copy.deepcopy(self.data)
        result = self.build()
        self.assertEqual(result["research"]["valuation"], before["valuation"])
        self.assertEqual(result["rules"]["buy_price_formula"], packet.wp.BUY_PRICE_FORMULA)
        self.assertIn("SOURCE-1", result["evidence"])
        self.assertIn("discount_rate", result["review_questions"])
        self.assertEqual(self.data, before)
        self.assertNotIn("approved", result)

    def test_missing_transitive_source_blocks_dispatch(self):
        self.records["sources"] = []
        write(self.root, "evidence.json", self.records)
        with self.assertRaisesRegex(ValueError, "SOURCE-1"):
            self.build()

    def test_incorrect_buy_price_blocks_dispatch(self):
        self.data["valuation"]["buy_price"] += 1
        with self.assertRaisesRegex(ValueError, "机械买入价"):
            self.build()

    def test_placeholder_formula_and_ambiguous_metadata_block_dispatch(self):
        model = self.data["valuation"]["models"][0]
        original = model["formula"]
        model["formula"] = "see_calculations"
        with self.assertRaises((ValueError, KeyError)):
            self.build()
        model["formula"] = original
        meta = next(iter(model["scenarios"]["base"]["input_meta"].values()))
        meta["kind"] = "assumption or forecast"
        with self.assertRaisesRegex(ValueError, "输入缺单位"):
            self.build()

    def test_references_support_calculation_map_and_cycles(self):
        self.records["facts"][0]["input_fact_ids"] = {"x": "FACT-2"}
        self.records["facts"].append({"fact_id": "FACT-2", "evidence_refs": ["FACT-1"]})
        write(self.root, "evidence.json", self.records)
        self.assertIn("FACT-2", self.build()["evidence"])

    def test_packet_retains_model_calculation_dependency(self):
        meta = next(iter(self.data["valuation"]["models"][0]["scenarios"]["base"]["input_meta"].values()))
        meta["calculation_id"] = "DERIVED"
        self.data["numeric_calculations"] = [{"id": "DERIVED", "formula": "x", "input_fact_ids": {"x": "FACT-1"}, "result": 1, "unit": "USD"}]
        result = self.build()
        self.assertIn("DERIVED", result["evidence"])
        self.assertIn("SOURCE-1", result["evidence"])


if __name__ == "__main__":
    unittest.main()
