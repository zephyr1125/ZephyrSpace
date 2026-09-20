"""验证边界、金额缺口与统一比较的关键行为。"""

import ast
from decimal import Decimal
from pathlib import Path
import unittest

from calculate import calculate, score


class RebalanceRulesTests(unittest.TestCase):
    def test_boundary_ownership(self):
        cases = {120: "高估三档", 110: "高估二档", 100: "高估一档", 75: "正常区间",
                 67.5: "低估一档", 60: "低估二档", 59.99: "低估三档"}
        for price, expected in cases.items():
            with self.subTest(price=price):
                self.assertEqual(calculate(price, 100, 0.5, "A_CORE", 0)["band"], expected)

    def test_cumulative_target_deducts_existing_market_value(self):
        for level, target in (("B_GROWTH", 30000), ("A_CORE", 60000), ("S_STRATEGIC", 120000)):
            result = calculate(59, 100, 0.5, level, 25000)
            self.assertEqual(Decimal(result["gap_cny"]), target - 25000)
        self.assertEqual(calculate(74, 100, 0.5, "A_CORE", 25000)["gap_cny"], "0")
        self.assertIsNone(calculate(120, 100, 0.5, "A_CORE", 25000)["target_holding_cny"])

    def test_tier_one_can_replace_and_quality_can_beat_deeper_discount(self):
        self.assertTrue(calculate(74, 100, 0.5, "A_CORE", 0)["replacement_price_eligible"])
        high_quality = score(74, 100, 0.5, 95, 95)
        deeper = score(61, 100, 0.5, 65, 65)
        self.assertEqual(Decimal(high_quality["total_score"]), Decimal("73.5"))
        self.assertGreater(Decimal(high_quality["total_score"]), Decimal(deeper["total_score"]))

    def test_price_score_is_continuous_and_monotone(self):
        previous = Decimal(-1)
        for price in range(150, 0, -1):
            current = Decimal(score(price, 100, 0.5, 80, 80)["price_score"])
            self.assertGreaterEqual(current, previous)
            self.assertTrue(0 <= current <= 100)
            previous = current
        before = Decimal(score("67.500001", 100, 0.5, 80, 80)["price_score"])
        after = Decimal(score("67.499999", 100, 0.5, 80, 80)["price_score"])
        self.assertLess(after - before, Decimal("0.00001"))

    def test_invalid_inputs_are_not_zero_or_percentage_converted(self):
        for bad in (None, "nan", "inf", True, 0, -1):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                calculate(bad, 100, 0.5, "A_CORE", 0)
        with self.assertRaises(ValueError):
            calculate(50, 100, 50, "A_CORE", 0)
        with self.assertRaises(ValueError):
            score(50, 100, 0.5, None, 80)

    def test_matches_finance_away_from_floating_point_boundary_noise(self):
        # 只执行纯函数，避免导入 Finance 服务导致账户或网络副作用。
        path = Path("E:/Work/Python/Finance/api/services/stock_watchlist.py")
        if not path.exists():
            self.skipTest("Finance 源码不可用")
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        nodes = [n for n in tree.body if
                 isinstance(n, ast.FunctionDef) and n.name in ("_calculate_price_bands", "_determine_current_band") or
                 isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_BAND_DEFINITIONS" for t in n.targets)]
        scope = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
        for certainty in (0, 0.5, 1):
            _, bands = scope["_calculate_price_bands"](100, certainty)
            for price in (10, 51.23, 63.21, 71.23, 88.88, 101.23, 111.23, 121.23):
                expected = scope["_determine_current_band"](price, bands)["label"]
                self.assertEqual(calculate(price, 100, certainty, "A_CORE", 0)["band"], expected)


if __name__ == "__main__":
    unittest.main()
