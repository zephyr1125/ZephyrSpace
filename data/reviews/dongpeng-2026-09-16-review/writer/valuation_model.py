"""东鹏饮料估值自检脚本。

本脚本只读取同目录 JSON 输入并输出机械计算结果；事实、预测和待补值由输入文件明确区分。
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def dcf_value(scenario: dict, common: dict) -> dict:
    """按 FCFF/WACC 口径计算每股权益价值。"""
    revenue = common["base_revenue_cny_bn"]
    fcffs = []
    revenues = []
    for growth, margin in zip(scenario["revenue_growth"], scenario["fcff_margin"], strict=True):
        revenue *= 1 + growth
        revenues.append(revenue)
        fcffs.append(revenue * margin)

    wacc = scenario["wacc"]
    terminal_growth = scenario["terminal_growth"]
    terminal_value = fcffs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_explicit = sum(fcff / ((1 + wacc) ** year) for year, fcff in enumerate(fcffs, start=1))
    pv_terminal = terminal_value / ((1 + wacc) ** len(fcffs))
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value + common["adjusted_net_financial_assets_cny_bn"]
    cny_per_share = equity_value * 1e9 / common["total_ordinary_shares"]
    hkd_per_share = cny_per_share * common["cny_to_hkd"]
    return {
        "revenue_cny_bn": revenues,
        "fcff_cny_bn": fcffs,
        "pv_explicit_cny_bn": pv_explicit,
        "pv_terminal_cny_bn": pv_terminal,
        "enterprise_value_cny_bn": enterprise_value,
        "equity_value_cny_bn": equity_value,
        "cny_per_share": cny_per_share,
        "hkd_per_share": hkd_per_share,
    }


def pe_value(scenario: dict, common: dict) -> dict:
    """按归母净利、总普通股数与可比 PE 计算每股价值。"""
    eps_cny = scenario["net_profit_cny_bn"] * 1e9 / common["total_ordinary_shares"]
    cny_per_share = eps_cny * scenario["pe_multiple"]
    return {
        "eps_cny": eps_cny,
        "pe_multiple": scenario["pe_multiple"],
        "cny_per_share": cny_per_share,
        "hkd_per_share": cny_per_share * common["cny_to_hkd"],
    }


def reverse_pe(price_hkd: float | None, common: dict, pe_multiple: float) -> dict | None:
    """零权重反推：给定市场价与 PE，求隐含归母净利。"""
    if price_hkd is None:
        return None
    price_cny = price_hkd / common["cny_to_hkd"]
    implied_eps_cny = price_cny / pe_multiple
    implied_profit_cny_bn = implied_eps_cny * common["total_ordinary_shares"] / 1e9
    return {
        "price_hkd": price_hkd,
        "fixed_pe_multiple": pe_multiple,
        "implied_eps_cny": implied_eps_cny,
        "implied_net_profit_cny_bn": implied_profit_cny_bn,
    }


def dcf_sensitivity(base_scenario: dict, common: dict) -> dict:
    """固定基准收入与FCFF路径，仅改变WACC和永续增长率。"""
    matrix = {}
    for wacc in (0.09, 0.095, 0.10, 0.105):
        row = {}
        for terminal_growth in (0.025, 0.03, 0.035):
            scenario = dict(base_scenario)
            scenario["wacc"] = wacc
            scenario["terminal_growth"] = terminal_growth
            row[f"g_{terminal_growth:.3f}"] = dcf_value(scenario, common)["hkd_per_share"]
        matrix[f"wacc_{wacc:.3f}"] = row
    return matrix


def main() -> None:
    inputs = json.loads((ROOT / "valuation-input-v1.json").read_text(encoding="utf-8"))
    common = inputs["common"]
    results = {
        "evidence_version": inputs["evidence_version"],
        "status": inputs["status"],
        "dcf": {},
        "comparable_pe": {},
    }
    for name, scenario in inputs["dcf_scenarios"].items():
        results["dcf"][name] = dcf_value(scenario, common)
    for name, scenario in inputs["pe_scenarios"].items():
        results["comparable_pe"][name] = pe_value(scenario, common)

    weights = inputs["model_weights"]
    results["weighted_value_hkd"] = {
        name: results["dcf"][name]["hkd_per_share"] * weights["dcf"]
        + results["comparable_pe"][name]["hkd_per_share"] * weights["comparable_pe"]
        for name in ("bear", "base", "bull")
    }
    results["dcf_sensitivity_base_cashflows_hkd"] = dcf_sensitivity(
        inputs["dcf_scenarios"]["base"], common
    )
    base_value = results["weighted_value_hkd"]["base"]
    certainty = inputs["valuation_certainty_placeholder"]
    results["mechanical_buy_price_hkd"] = base_value * (0.68 + 0.14 * certainty)
    results["reverse_validation_weight"] = 0
    results["reverse_pe"] = reverse_pe(
        common["market_price_hkd"], common, inputs["reverse_validation"]["fixed_pe_multiple"]
    )
    results["blocking_gaps"] = inputs["blocking_gaps"]

    output_path = ROOT / "valuation-output-v1.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
