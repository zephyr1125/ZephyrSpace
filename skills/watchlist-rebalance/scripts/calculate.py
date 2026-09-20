"""计算七档价格区间及累计目标缺口，不读取账户或执行交易。"""

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


BASE_CNY = {"B_GROWTH": 10000, "A_CORE": 20000, "S_STRATEGIC": 40000}


def number(value):
    """拒绝空值、布尔值及非有限值，避免把数据异常当零。"""
    if isinstance(value, bool):
        raise ValueError("布尔值不是有效金额或价格")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("请输入有效数值") from exc
    if not result.is_finite():
        raise ValueError("数值必须有限")
    return result


def calculate(price, target, certainty, level, holding_cny):
    """按当前价格重估后的人民币持仓市值计算缺口。"""
    p, t, c, h = map(number, (price, target, certainty, holding_cny))
    if p <= 0 or t <= 0 or not 0 <= c <= 1 or h < 0:
        raise ValueError("价格/目标价须为正数，确定性须为 0—1，持仓市值不得为负")
    if level not in BASE_CNY:
        raise ValueError("仅支持三个有效 Watchlist 等级")
    b = t * (Decimal("0.68") + Decimal("0.14") * c)
    bands = [
        ("高估三档", t * Decimal("1.2"), 0),
        ("高估二档", t * Decimal("1.1"), 0),
        ("高估一档", t, 0),
        ("正常区间", b, 0),
        ("低估一档", b * Decimal("0.9"), 1),
        ("低估二档", b * Decimal("0.8"), 2),
        ("低估三档", Decimal(0), 3),
    ]
    index = next(i for i, (_, minimum, _) in enumerate(bands) if p >= minimum)
    label, lower, grade = bands[index]
    cap = Decimal(BASE_CNY[level] * grade) if grade else None
    return {
        "band": label,
        "buy_price": str(b),
        "lower_inclusive": str(lower),
        "upper_exclusive": str(bands[index - 1][1]) if index else None,
        "target_holding_cny": str(cap) if cap is not None else None,
        "gap_cny": str(max(Decimal(0), cap - h)) if cap is not None else "0",
        "replacement_price_eligible": grade >= 1,
        "sale_price_eligible": index == 0,
        "note": "价格资格不等于买卖建议；须另核持仓、估值有效性与资金来源",
    }


def score(price, target, certainty, company_score, management_score, rules=None):
    """按透明锚点插值，保留质量与价格的独立贡献。"""
    if rules is None:
        rules = json.loads((Path(__file__).resolve().parents[1] / "rules.json").read_text(encoding="utf-8"))
    p, t, c, cs, ms = map(number, (price, target, certainty, company_score, management_score))
    if p <= 0 or t <= 0 or not 0 <= c <= 1 or not 0 <= cs <= 100 or not 0 <= ms <= 100:
        raise ValueError("价格、确定性或质量评分超出合法范围")
    qw, pw, cw, mw = [number(rules[k]) for k in (
        "quality_weight", "price_weight", "company_share_of_quality", "management_share_of_quality"
    )]
    if any(x < 0 or x > 1 for x in (qw, pw, cw, mw)) or qw + pw != 1 or cw + mw != 1:
        raise ValueError("各层权重必须非负且合计为1")
    b = t * (Decimal("0.68") + Decimal("0.14") * c)
    points = []
    for anchor in rules["price_score_anchors"]:
        if anchor["basis"] not in ("target", "buy"):
            raise ValueError("未知价格锚点基准")
        x = (t if anchor["basis"] == "target" else b) * number(anchor["multiple"])
        y = number(anchor["score"])
        if x <= 0 or not 0 <= y <= 100:
            raise ValueError("价格锚点或评分非法")
        points.append((x, y))
    if len(points) < 2 or any(a[0] <= z[0] or a[1] > z[1] for a, z in zip(points, points[1:])):
        raise ValueError("价格锚点必须递减且吸引力评分不减")
    if p >= points[0][0]:
        v = points[0][1]
    elif p <= points[-1][0]:
        v = points[-1][1]
    else:
        hi, lo = next((hi, lo) for hi, lo in zip(points, points[1:]) if lo[0] <= p <= hi[0])
        v = hi[1] + (hi[0] - p) / (hi[0] - lo[0]) * (lo[1] - hi[1])
    q = cs * cw + ms * mw
    return {
        "quality_score": str(q), "price_score": str(v),
        "company_contribution": str(cs * cw * qw),
        "management_contribution": str(ms * mw * qw),
        "price_contribution": str(v * pw), "total_score": str(q * qw + v * pw),
        "weight_status": rules["weight_status"],
        "price_score_status": rules["price_score_status"],
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("price", "target", "certainty", "holding-cny"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--level", choices=BASE_CNY, required=True)
    parser.add_argument("--company-score")
    parser.add_argument("--management-score")
    args = parser.parse_args()
    try:
        result = calculate(args.price, args.target, args.certainty, args.level, args.holding_cny)
        if (args.company_score is None) != (args.management_score is None):
            raise ValueError("统一评分须同时提供公司分和管理层分")
        if args.company_score is not None:
            result["scoring"] = score(args.price, args.target, args.certainty, args.company_score, args.management_score)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
