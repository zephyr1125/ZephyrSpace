import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "huaming-revision-inputs.json"
OUTPUT = ROOT / "huaming-revision-calculations.json"


def ddm_two_stage(d0, growth, years, terminal_growth, cost_of_equity):
    """按同一两阶段股利模型计算显性期和终值。"""
    pv_dividends = sum(
        d0 * (1 + growth) ** year / (1 + cost_of_equity) ** year
        for year in range(1, years + 1)
    )
    dividend_year_n = d0 * (1 + growth) ** years
    terminal_value = dividend_year_n * (1 + terminal_growth) / (
        cost_of_equity - terminal_growth
    )
    return pv_dividends + terminal_value / (1 + cost_of_equity) ** years


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    earnings = data["earnings_bridge"]
    shares = data["shares"]["current_total"]
    cash = data["cash_flow_bridge"]
    valuation = data["valuation"]

    ttm_attributable = (
        earnings["fy2025_attributable"]
        - earnings["h1_2025_attributable"]
        + earnings["h1_2026_attributable"]
    )
    normalized_eps = ttm_attributable / shares
    h1_tax_rate = earnings["h1_2026_tax"] / earnings["h1_2026_pbt"]
    h1_payout = data["dividends"]["h1_2026_proposed_dps"] / (
        earnings["h1_2026_attributable"] / shares
    )
    fy2025_payout = data["dividends"]["fy2025_total_dps"] / (
        earnings["fy2025_attributable"] / shares
    )

    ttm_ocf = cash["fy2025_ocf"] - cash["h1_2025_ocf"] + cash["h1_2026_ocf"]
    ttm_cash_capex = (
        cash["fy2025_cash_capex"]
        - cash["h1_2025_cash_capex"]
        + cash["h1_2026_cash_capex"]
    )
    ttm_reported_fcf = ttm_ocf - ttm_cash_capex
    fcf_per_share = ttm_reported_fcf / shares

    financing = cash["h1_2026_other_financing_payments"]
    financing_total = sum(financing.values())
    lease_related = (
        financing["financing_lease_payment"]
        + financing["lease_principal_and_interest"]
    )

    pe_value = normalized_eps * valuation["pe"]["multiple"]
    ddm_value = ddm_two_stage(**{
        "d0": valuation["ddm"]["d0"],
        "growth": valuation["ddm"]["stage1_growth"],
        "years": valuation["ddm"]["years"],
        "terminal_growth": valuation["ddm"]["terminal_growth"],
        "cost_of_equity": valuation["ddm"]["cost_of_equity"],
    })
    fcf_value = fcf_per_share / valuation["fcf_yield"]["required_yield"]
    raw_target = (
        pe_value * valuation["pe"]["weight"]
        + ddm_value * valuation["ddm"]["weight"]
        + fcf_value * valuation["fcf_yield"]["weight"]
    )
    target = round(raw_target, 1)
    certainty = valuation["certainty"]
    buy_price = round(target * (0.68 + 0.14 * certainty), 2)

    c = data["scores"]["company"]
    company_score = sum(c["A"]) + sum(c["B"]) + c["C"] + c["D"] + sum(c["E"]) + sum(c["F"])
    management_score = sum(data["scores"]["management"])

    scenarios = {}
    scenario_inputs = {
        "bear": {"eps": 0.74, "pe": 17.0, "d0": 0.42, "g": 0.01, "gt": 0.01, "ke": 0.115, "fcf_ps": 0.62, "yield": 0.06},
        "base": {"eps": normalized_eps, "pe": 20.0, "d0": 0.50, "g": 0.04, "gt": 0.025, "ke": 0.10, "fcf_ps": fcf_per_share, "yield": 0.052},
        "bull": {"eps": 0.90, "pe": 23.0, "d0": 0.56, "g": 0.06, "gt": 0.03, "ke": 0.09, "fcf_ps": 0.84, "yield": 0.045},
    }
    for name, s in scenario_inputs.items():
        pe = s["eps"] * s["pe"]
        ddm = ddm_two_stage(s["d0"], s["g"], 5, s["gt"], s["ke"])
        fcf = s["fcf_ps"] / s["yield"]
        scenarios[name] = {
            "inputs": s,
            "pe_value": pe,
            "ddm_value": ddm,
            "fcf_value": fcf,
            "weighted_value": pe * 0.70 + ddm * 0.15 + fcf * 0.15,
        }

    h_share = {}
    for issue_ratio in (0.05, 0.10, 0.15):
        new_shares = shares * issue_ratio
        for price_ratio in (0.8, 1.0, 1.2):
            issue_price = raw_target * price_ratio
            post_value = (raw_target * shares + issue_price * new_shares) / (shares + new_shares)
            h_share[f"issue_{issue_ratio:.0%}_price_{price_ratio:.0%}"] = post_value

    result = {
        "ttm_attributable": ttm_attributable,
        "normalized_eps": normalized_eps,
        "h1_effective_tax_rate": h1_tax_rate,
        "fy2025_payout_ratio": fy2025_payout,
        "h1_2026_proposed_payout_ratio": h1_payout,
        "ttm_ocf": ttm_ocf,
        "ttm_cash_capex": ttm_cash_capex,
        "ttm_reported_fcf": ttm_reported_fcf,
        "fcf_per_share": fcf_per_share,
        "other_financing_payments_total": financing_total,
        "lease_related_financing_payments": lease_related,
        "valuation": {
            "pe_value": pe_value,
            "ddm_value": ddm_value,
            "fcf_value": fcf_value,
            "raw_target": raw_target,
            "target_price": target,
            "valuation_certainty": certainty,
            "buy_price": buy_price,
        },
        "scenarios": scenarios,
        "h_share_sensitivity": h_share,
        "scores": {
            "company": company_score,
            "management": management_score,
            "combined": company_score + management_score,
        },
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
