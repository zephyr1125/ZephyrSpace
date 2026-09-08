"""只读取康臣返修输入并写出计算结果，不生成研究报告。"""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def ddm(p: dict) -> dict:
    ds = [p["d0"] * (1 + p["stage1_growth"]) ** i for i in range(1, p["years"] + 1)]
    pv1 = sum(x / (1 + p["discount_rate"]) ** i for i, x in enumerate(ds, 1))
    tv = ds[-1] * (1 + p["terminal_growth"]) / (p["discount_rate"] - p["terminal_growth"])
    pv_terminal = tv / (1 + p["discount_rate"]) ** p["years"]
    return {"dividends": ds, "pv_stage1": pv1, "terminal_value": tv, "pv_terminal": pv_terminal, "value": pv1 + pv_terminal}

def normalized_eps(e: dict, tax_rate: float, fx: float) -> tuple[float, float, float]:
    profit = (e["ttm_profit_before_tax"] - e["remove_fvpl_gain_pre_tax"]) * (1 - tax_rate) - e["ttm_nci"]
    eps_cny = profit / e["diluted_share_proxy"]
    return profit, eps_cny, eps_cny * fx

def main() -> None:
    x = json.loads((ROOT / "consun-revision-inputs.json").read_text(encoding="utf-8-sig"))
    e = x["earnings_bridge_rmb"]
    profit, eps_cny, eps_hkd = normalized_eps(e, e["normalization_tax_rate"], e["hkd_per_rmb_assumption"])
    d = {k: ddm(v) for k, v in x["ddm"].items()}
    pe = eps_hkd * x["pe_multiple"]
    target_raw = pe * x["formal_weights"]["normalized_pe"] + d["base"]["value"] * x["formal_weights"]["ddm"]
    target = round(target_raw, 1)
    buy = round(target * (0.68 + 0.14 * x["valuation_certainty"]), 2)
    scenarios = {}
    for key in ("bear", "base", "bull"):
        ps = x["pe_scenarios"][key]
        scenario_eps = eps_hkd if ps["eps_hkd"] is None else ps["eps_hkd"]
        pe_value = scenario_eps * ps["multiple"]
        scenarios[key] = {"eps_hkd": scenario_eps, "pe_value": pe_value, "ddm_value": d[key]["value"], "weighted_value": pe_value * 0.75 + d[key]["value"] * 0.25}
    b = x["cash_bridge_rmb"]
    cash_classified = b["cash_and_equivalents"] + b["bank_time_deposits"] + b["restricted_cash"] + b["wealth_management_products"]
    partial_proxy = cash_classified - b["restricted_cash"] - b["bank_loans"] - b["lease_liabilities"] - b["capital_commitments"] - b["deferred_withholding_tax"]
    cf = x["reported_cash_flow_rmb"]
    company_score = sum(sum(v) if isinstance(v, list) else v for v in x["scores"]["company"].values())
    other = x["ttm_other_income_bridge_rmb"]
    out = {"as_of": x["as_of"], "company": x["company"], "earnings_bridge": {"ttm_profit_before_tax_rmb": e["ttm_profit_before_tax"], "ttm_actual_tax_rmb": e["ttm_income_tax"], "ttm_actual_tax_rate": e["ttm_income_tax"] / e["ttm_profit_before_tax"], "ttm_nci_rmb": e["ttm_nci"], "ttm_fvpl_removed_pretax_rmb": e["remove_fvpl_gain_pre_tax"], "normalized_tax_rate": e["normalization_tax_rate"], "tax_rate_anchor": e["h1_2026_tax_plus_prior_overprovision"] / e["h1_2026_pbt"], "normalized_parent_profit_rmb": profit, "diluted_share_proxy": e["diluted_share_proxy"], "eps_cny_diluted_proxy": eps_cny, "normalized_eps_hkd": eps_hkd, "fx_sensitivity_eps_hkd": {str(fx): normalized_eps(e, e["normalization_tax_rate"], fx)[2] for fx in (1.05, 1.10, 1.15)}, "tax_sensitivity_eps_hkd": {str(rate): normalized_eps(e, rate, e["hkd_per_rmb_assumption"])[2] for rate in (0.12, 0.15, 0.18)}}, "ttm_other_income_bridge_rmb": {**other, "recalculated_total": sum(other.values())}, "pe_value": pe, "ddm": d, "scenarios": scenarios, "formal_weight_sum": sum(x["formal_weights"].values()), "target_price_raw": target_raw, "target_price": target, "valuation_certainty": x["valuation_certainty"], "certainty_factors": x["certainty_factors"], "buy_price": buy, "deep_discount_boundary": round(buy * 0.85, 2), "cash_diagnostic": {"cash_classified_rmb": cash_classified, "partial_group_financial_asset_proxy_rmb": partial_proxy, "proxy_per_share_hkd": partial_proxy * e["hkd_per_rmb_assumption"] / e["basic_current_shares"], "nci_attribution": "unknown", "formal_weight": 0}, "reported_cash_flow": {"fy2024_simplified_fcf": cf["fy2024_ocf"] - cf["fy2024_cash_capex"], "fy2025_simplified_fcf": cf["fy2025_ocf"] - cf["fy2025_cash_capex"], "h1_2026_cash_capex": "unknown", "formal_weight": 0}, "cScore": company_score, "mScore": sum(x["scores"]["management"].values())}
    (ROOT / "consun-revision-calculations.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if __name__ == "__main__": main()
