import json
from pathlib import Path

RUN = Path(__file__).resolve().parent

# 金额单位：人民币百万元；每股价值最终换算为港元。
revenue = {2023: 6983.846861, 2024: 8823.023321, 2025: 8765.840000}
net_profit = {2023: 1447.875971, 2024: 2128.563558, 2025: 2405.903695}
assets_end = {2022: 25237.623431, 2023: 27500.129431, 2024: 29694.645613, 2025: 33190.595227}
equity_end = {2022: 19742.230000, 2023: 21018.594000, 2024: 22896.985700, 2025: 24625.227568}

dupont = {}
for year in (2023, 2024, 2025):
    avg_assets = (assets_end[year - 1] + assets_end[year]) / 2
    avg_equity = (equity_end[year - 1] + equity_end[year]) / 2
    margin = net_profit[year] / revenue[year]
    turnover = revenue[year] / avg_assets
    leverage = avg_assets / avg_equity
    roe = net_profit[year] / avg_equity
    dupont[str(year)] = {
        "net_margin": margin,
        "asset_turnover": turnover,
        "equity_multiplier": leverage,
        "roe_identity": margin * turnover * leverage,
        "roe_direct": roe,
        "avg_assets": avg_assets,
        "avg_equity": avg_equity,
    }

customer = {
    2023: {"reserve": 1189.599, "settlement_ar": 962.165, "factoring_ar": 848.460, "epay_ap": 1165.956, "settlement_ap": 343.393},
    2024: {"reserve": 1449.124, "settlement_ar": 1118.645, "factoring_ar": 839.886, "epay_ap": 1436.509, "settlement_ap": 379.995},
    2025: {"reserve": 1528.546, "settlement_ar": 1413.903, "factoring_ar": 1323.740, "epay_ap": 1519.907, "settlement_ap": 516.939},
    2026: {"reserve": 1979.880, "settlement_ar": 1642.021, "factoring_ar": 1518.042, "epay_ap": 1975.473, "settlement_ap": 700.112},
}
for values in customer.values():
    values["client_net_liability_proxy"] = values["reserve"] + values["epay_ap"] + values["settlement_ap"] - values["settlement_ar"]

ocf = {2023: 137.427316, 2024: 2525.944923, 2025: 2923.537577}
cash_capex = {2023: 527.896896, 2024: 353.479429, 2025: 842.793057}
fcff_diagnostic = {}
for year in (2024, 2025):
    client_delta = customer[year]["client_net_liability_proxy"] - customer[year - 1]["client_net_liability_proxy"]
    fcff_diagnostic[str(year)] = {
        "ocf_less_cash_capex": ocf[year] - cash_capex[year],
        "client_net_liability_change": client_delta,
        "after_visible_client_proxy": ocf[year] - cash_capex[year] - client_delta,
        "factoring_ar_change": customer[year]["factoring_ar"] - customer[year - 1]["factoring_ar"],
    }

shares = 2926.209589
cny_hkd = 1.09
b0 = 25030.046025
stub_days = 80

def ri_value(roe_start, roe_end, ke, payout_start, payout_end, g):
    bv = b0
    pv_ri = 0.0
    rows = []
    for t in range(1, 6):
        roe = roe_start + (roe_end - roe_start) * (t - 1) / 4
        payout = payout_start + (payout_end - payout_start) * (t - 1) / 4
        earnings = roe * bv
        ri = (roe - ke) * bv
        end_bv = bv + earnings * (1 - payout)
        pv_ri += ri / ((1 + ke) ** t)
        rows.append({"year": t, "begin_bv": bv, "roe": roe, "payout": payout, "earnings": earnings, "ri": ri, "end_bv": end_bv})
        bv = end_bv
    ri6 = (roe_end - ke) * bv
    terminal_payout = 1 - g / roe_end
    terminal_value = ri6 / (ke - g)
    value_cny = b0 + pv_ri + terminal_value / ((1 + ke) ** 5)
    value_hkd_0630 = value_cny / shares * cny_hkd
    # 仅作时点敏感性：假设80天内价值按Ke累积；不冒充实际利润。
    value_hkd_0918 = value_hkd_0630 * ((1 + ke) ** (stub_days / 365))
    return {
        "value_cny_m": value_cny,
        "value_hkd_0630": value_hkd_0630,
        "value_hkd_0918_stub": value_hkd_0918,
        "terminal_payout": terminal_payout,
        "ri6": ri6,
        "rows": rows,
    }

ri_scenarios = {
    "conservative": ri_value(0.085, 0.080, 0.115, 0.35, 0.55, 0.010),
    "base": ri_value(0.100, 0.095, 0.105, 0.35, 0.50, 0.020),
    "optimistic": ri_value(0.115, 0.105, 0.098, 0.35, 0.45, 0.025),
}

ri_sensitivity = {}
for roe in (0.085, 0.095, 0.105):
    ri_sensitivity[f"roe_{roe:.3f}"] = {}
    for ke in (0.095, 0.105, 0.115):
        g = min(0.02, roe * 0.25)
        result = ri_value(roe, roe, ke, 0.50, 1 - g / roe, g)
        ri_sensitivity[f"roe_{roe:.3f}"][f"ke_{ke:.3f}"] = result["value_hkd_0918_stub"]

company_subscores = {
    "A": {"A1": 3, "A2": 3, "A3": 2},
    "B": {"B0": 1, "B1": 4, "B2": 2, "B3": 5, "B4": 4},
    "C": {"C1": 5, "C2": 4, "C3_C4": 7},
    "D": {"D1": 3, "D2": 3, "D3": 2, "D5": 2},
    "E": {"E1": 2, "E2": 3, "E3": 2, "E4": 1.5, "E5": 1, "E5_5": 2},
    "F": {"F1": 4, "F2": 3, "F2_5": 1, "F3": 2},
}
dimension_totals = {key: sum(values.values()) for key, values in company_subscores.items()}
candidate_company_raw = sum(dimension_totals.values())
candidate_company_rounded = round(candidate_company_raw)

management_subscores = {"诚信": 15, "资本配置": 17, "战略": 12, "股东回报": 11, "危机能力": 6, "组织": 6, "表达": 3}
candidate_management = sum(management_subscores.values())

output = {
    "status": "research_incomplete_pending_final_recheck",
    "repair_round": 2,
    "exception_round": 1,
    "dupont": dupont,
    "customer_capital_bridge": customer,
    "fcff_diagnostic": fcff_diagnostic,
    "maintenance_capex_range_cny_m": [800, 1200],
    "normalized_fcff_range_cny_m": [1400, 1900],
    "normalized_fcff_range_status": "bounded_diagnostic_not_formal_dcf_input",
    "ri_scenarios": ri_scenarios,
    "ri_sensitivity": ri_sensitivity,
    "company_subscores": company_subscores,
    "dimension_totals": dimension_totals,
    "candidate_company_score_raw": candidate_company_raw,
    "candidate_company_score_rounded": candidate_company_rounded,
    "candidate_management_score": candidate_management,
    "formal_parameters": {"cScore": None, "mScore": None, "target_price": None, "valuation_certainty": None, "mechanical_buy_price": None, "watchlistLevel": None},
    "reverse_validation_weight": 0,
    "remaining_p1_author_view": ["C04", "C05"],
}

(RUN / "repair2-calculation-output.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(output, ensure_ascii=False, indent=2))
