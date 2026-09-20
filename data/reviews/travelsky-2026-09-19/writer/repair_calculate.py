import json
from pathlib import Path

raw = {
    "2023": {"ocf": 137.427316, "cash_capex": 527.896896},
    "2024": {"ocf": 2525.944923, "cash_capex": 353.479429},
    "2025": {"ocf": 2923.537577, "cash_capex": 842.793057},
    "2026H1": {"ocf": 2435.699116, "cash_capex": 199.718525},
}
for v in raw.values():
    v["ocf_less_cash_capex"] = v["ocf"] - v["cash_capex"]
three_year_diagnostic = sum(raw[y]["ocf_less_cash_capex"] for y in ("2023", "2024", "2025")) / 3
corrected_2025 = raw["2025"]["ocf_less_cash_capex"] - 20.647823 * 0.15

receivables = {
    "2025": {"gross": 6179.475427, "allowance": 1072.562012, "net": 5106.913415},
    "2026H1": {"gross": 5533.024198, "allowance": 1053.369286, "net": 4479.654911},
}

company_subscores = {
    "A": {"A1": 3, "A2": 3, "A3": 2},
    "B": {"B0": 1, "B1": 4, "B2": 2, "B3": 5, "B4": 4},
    "C": {"C1": 5, "C2": 4, "C3_C4": 7},
    "D": {"D1": 3, "D2": 3, "D3": 2, "D5": 2},
    "E": {"E1": 3, "E2": 3, "E3": 2, "E4": 1, "E5": 2, "E5_5": 2},
    "F": {"F1": 4, "F2": 3, "F2_5": 1, "F3": 2},
}
company_total = sum(sum(v.values()) for v in company_subscores.values())
management = {"诚信": 15, "资本配置": 17, "战略": 12, "股东回报": 11, "危机处理": 6, "组织": 6, "表达": 3}
management_total = sum(management.values())

result = {
    "units": "人民币百万元",
    "raw_cash_bridge": raw,
    "three_year_ocf_less_capex_diagnostic": three_year_diagnostic,
    "corrected_2025_before_customer_and_reinvestment_split": corrected_2025,
    "receivables": receivables,
    "receivable_checks": {k: abs(v["gross"] - v["allowance"] - v["net"]) <= 2e-6 for k, v in receivables.items()},
    "company_subscores": company_subscores,
    "candidate_cScore": company_total,
    "management_subscores": management,
    "candidate_mScore": management_total,
    "target_price": None,
    "valuation_certainty": None,
    "mechanical_buy_price": None,
    "watchlistLevel": None,
    "reverse_validation_weight": 0,
    "blocking_reason": "客户结算/保理/自有营运资金经济分类残差与第二独立主模型未闭合",
}

# 显式剩余收益模型：以2026H1归母账面权益为起点，预测ROE、分配和账面滚动。
# 起点账面已经包含累计OCI；预测期不另造OCI，所有未分配利润进入账面。
shares = 2926.209589
fx = 0.86062
start_bv = 25030.046025

def explicit_ri(start_roe, terminal_roe, ke, start_payout, terminal_payout, g_terminal):
    bv = start_bv
    pv_ri = 0.0
    rows = []
    for year in range(1, 6):
        t = (year - 1) / 4
        roe = start_roe + (terminal_roe - start_roe) * t
        payout = start_payout + (terminal_payout - start_payout) * t
        earnings = bv * roe
        residual = (roe - ke) * bv
        pv_ri += residual / ((1 + ke) ** year)
        end_bv = bv + earnings * (1 - payout)
        rows.append({"year": year, "begin_bv": bv, "roe": roe, "payout": payout, "earnings": earnings, "residual_income": residual, "end_bv": end_bv})
        bv = end_bv
    terminal_residual = (terminal_roe - ke) * bv
    terminal_value = terminal_residual * (1 + g_terminal) / (ke - g_terminal)
    equity = start_bv + pv_ri + terminal_value / ((1 + ke) ** 5)
    return {"equity_cny_m": equity, "value_hkd_per_share": equity / shares / fx, "rollforward": rows}

result["explicit_ri"] = {
    "保守": explicit_ri(0.085, 0.08, 0.115, 0.35, 0.55, 0.01),
    "基准": explicit_ri(0.10, 0.095, 0.105, 0.35, 0.50, 0.02),
    "乐观": explicit_ri(0.115, 0.105, 0.098, 0.35, 0.45, 0.025),
}
result["second_model_status"] = "candidate_valid_explicit_RI"
result["blocking_reason"] = "FCFF客户结算/保理/自有营运资金经济分类残差与维护/扩张再投资仍未闭合；RI仅作为已完成的第二模型候选"
Path(__file__).with_name("repair-calculation-output.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
