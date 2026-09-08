"""重算两家公司评分、估值、机械买入价及关键财务桥。

本脚本只读取 inputs.json 并写入 calculations.json；不生成或修改研究报告。
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def two_stage_ddm(d0: float, growth: float, terminal_growth: float, discount: float, years: int) -> dict:
    dividends = [d0 * (1 + growth) ** year for year in range(1, years + 1)]
    pv_stage1 = sum(dividend / (1 + discount) ** year for year, dividend in enumerate(dividends, 1))
    terminal = dividends[-1] * (1 + terminal_growth) / (discount - terminal_growth)
    pv_terminal = terminal / (1 + discount) ** years
    return {
        "dividends": dividends,
        "pv_stage1": pv_stage1,
        "terminal_value_at_year_n": terminal,
        "pv_terminal": pv_terminal,
        "value": pv_stage1 + pv_terminal,
    }


def gordon_ddm(d1: float, terminal_growth: float, discount: float) -> float:
    return d1 / (discount - terminal_growth)


def reverse_growth(price: float, eps0: float, years: int, discount: float, terminal_pe: float, payout: float) -> float:
    def present_value(growth: float) -> float:
        earnings = [eps0 * (1 + growth) ** year for year in range(1, years + 1)]
        distributions = sum(payout * eps / (1 + discount) ** year for year, eps in enumerate(earnings, 1))
        terminal = earnings[-1] * terminal_pe / (1 + discount) ** years
        return distributions + terminal

    low, high = -0.20, 0.50
    for _ in range(200):
        mid = (low + high) / 2
        if present_value(mid) < price:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def score_total(values: list[float]) -> float:
    return sum(values)


def main() -> None:
    inputs = json.loads((ROOT / "inputs.json").read_text(encoding="utf-8"))
    consun = inputs["companies"]["康臣药业"]
    huaming = inputs["companies"]["华明装备"]

    consun_pe = consun["normalized_eps"] * consun["pe_multiple"]
    consun_ddm = two_stage_ddm(
        consun["ddm"]["d0"],
        consun["ddm"]["stage1_growth"],
        consun["ddm"]["terminal_growth"],
        consun["ddm"]["discount_rate"],
        consun["ddm"]["years"],
    )
    consun_target_raw = (
        consun_pe * consun["formal_weights"]["normalized_pe"]
        + consun_ddm["value"] * consun["formal_weights"]["ddm"]
    )
    consun_target = round(consun_target_raw, 1)
    consun_buy = round(consun_target * (0.68 + 0.14 * consun["valuation_certainty"]), 2)
    bridge = consun["cash_bridge_rmb"]
    cash_like = sum(
        bridge[key]
        for key in ("cash_and_equivalents", "bank_time_deposits", "restricted_cash", "wealth_management_products")
    )
    pre_buffer_distributable = cash_like - sum(
        bridge[key]
        for key in ("bank_loans", "lease_liabilities", "capital_commitments", "deferred_withholding_tax")
    )

    huaming_pe = huaming["normalized_eps"] * huaming["pe_multiple"]
    huaming_ddm = gordon_ddm(
        huaming["ddm"]["d1"],
        huaming["ddm"]["terminal_growth"],
        huaming["ddm"]["discount_rate"],
    )
    huaming_target_raw = (
        huaming_pe * huaming["formal_weights"]["normalized_pe"]
        + huaming_ddm * huaming["formal_weights"]["ddm"]
    )
    huaming_target = round(huaming_target_raw, 1)
    huaming_buy = round(huaming_target * (0.68 + 0.14 * huaming["valuation_certainty"]), 2)
    debt = huaming["debt_bridge_rmb"]
    bank_debt = debt["short_term_borrowings"] + debt["current_long_term_borrowings"] + debt["long_term_borrowings"]
    lease_debt = debt["current_lease_liabilities"] + debt["noncurrent_lease_liabilities"]
    reverse_g = reverse_growth(
        huaming["current_price"],
        huaming["normalized_eps"],
        huaming["reverse_dcf"]["years"],
        huaming["reverse_dcf"]["discount_rate"],
        huaming["reverse_dcf"]["terminal_pe"],
        huaming["reverse_dcf"]["payout_ratio"],
    )

    output = {
        "as_of": inputs["as_of"],
        "康臣药业": {
            "cScore": score_total(consun["scores"]["company_dimensions"]),
            "mScore": score_total(consun["scores"]["management_dimensions"]),
            "normalized_pe_value": consun_pe,
            "ddm": consun_ddm,
            "formal_weight_sum": sum(consun["formal_weights"].values()),
            "target_price_raw": consun_target_raw,
            "target_price": consun_target,
            "valuation_certainty": consun["valuation_certainty"],
            "buy_price": consun_buy,
            "cash_like_rmb": cash_like,
            "pre_operating_buffer_distributable_proxy_rmb": pre_buffer_distributable,
            "proxy_per_share_hkd": pre_buffer_distributable * bridge["hkd_per_rmb"] / consun["shares_basic"],
            "sotp_formal_weight": 0,
            "fcf_formal_weight": 0,
        },
        "华明装备": {
            "cScore": score_total(huaming["scores"]["company_dimensions"]),
            "mScore": score_total(huaming["scores"]["management_dimensions"]),
            "normalized_pe_value": huaming_pe,
            "ddm_value": huaming_ddm,
            "formal_weight_sum": sum(huaming["formal_weights"].values()),
            "target_price_raw": huaming_target_raw,
            "target_price": huaming_target,
            "valuation_certainty": huaming["valuation_certainty"],
            "buy_price": huaming_buy,
            "bank_debt_rmb": bank_debt,
            "lease_debt_rmb": lease_debt,
            "total_interest_and_lease_debt_rmb": bank_debt + lease_debt,
            "net_debt_using_cash_equivalents_rmb": bank_debt + lease_debt - debt["cash_and_equivalents"],
            "reverse_dcf_implied_growth_with_60pct_payout": reverse_g,
            "fcf_formal_weight": 0,
        },
    }
    (ROOT / "calculations.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
