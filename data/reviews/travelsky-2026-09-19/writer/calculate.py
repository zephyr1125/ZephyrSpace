import json
from pathlib import Path

OUT = Path(__file__).with_name("calculation-output.json")

shares = 2_926.209589  # 百万股
fx = 0.86062  # 1港元对应人民币
price_hkd = 8.75

# 2025年报现金流桥，单位均为人民币百万元。
net_profit = 2405.903695
noncash_and_other = 2923.537577 - net_profit
reported_ocf = 2923.537577
cash_capex = 842.793057
after_tax_interest = 20.647823 * (1 - 0.15)
fcff_2025 = reported_ocf - cash_capex + after_tax_interest
fcff_2024 = 2525.944923 - 353.479429 + 4.030876 * (1 - 0.15)
normalized_fcff = (fcff_2024 + fcff_2025) / 2

cash = 10017.949086
customer_provisions = 1528.545849
interest_debt = 1288.402135 + 471.506280 + 301.884278
conservative_net_cash = cash - customer_provisions - interest_debt

def dcf(start, growth, wacc, terminal_g, years=5):
    pv = 0.0
    f = start
    for year in range(1, years + 1):
        f *= 1 + growth
        pv += f / ((1 + wacc) ** year)
    terminal = f * (1 + terminal_g) / (wacc - terminal_g)
    enterprise = pv + terminal / ((1 + wacc) ** years)
    equity = enterprise + conservative_net_cash
    return equity / shares / fx

dcf_scenarios = {
    "保守": dcf(normalized_fcff * 0.90, 0.01, 0.105, 0.01),
    "基准": dcf(normalized_fcff, 0.04, 0.095, 0.02),
    "乐观": dcf(normalized_fcff * 1.05, 0.07, 0.088, 0.025),
}

bvps_cny = 25030.046025 / shares

def pb_roe_value(roe, ke, growth):
    pb = (roe - growth) / (ke - growth)
    return bvps_cny * pb / fx

ri_scenarios = {
    "保守": pb_roe_value(0.085, 0.115, 0.015),
    "基准": pb_roe_value(0.10, 0.105, 0.02),
    "乐观": pb_roe_value(0.115, 0.098, 0.025),
}

weights = {"DCF": 0.60, "RI": 0.40}
combined = {k: dcf_scenarios[k] * weights["DCF"] + ri_scenarios[k] * weights["RI"] for k in dcf_scenarios}
target = combined["基准"]
certainty = 0.64
buy_price = target * (0.68 + 0.14 * certainty)

dcf_sensitivity = {}
for wacc in (0.085, 0.095, 0.105):
    dcf_sensitivity[f"WACC {wacc:.1%}"] = {f"g {g:.1%}": dcf(normalized_fcff, 0.04, wacc, g) for g in (0.01, 0.02, 0.03)}

ri_sensitivity = {}
for roe in (0.085, 0.10, 0.115):
    ri_sensitivity[f"ROE {roe:.1%}"] = {f"Ke {ke:.1%}": pb_roe_value(roe, ke, 0.02) for ke in (0.095, 0.105, 0.115)}

# 零权重反向验证：固定基准DCF其他参数，二分求解当前股价对应的五年FCFF增速。
lo, hi = -0.20, 0.20
for _ in range(100):
    mid = (lo + hi) / 2
    value = dcf(normalized_fcff, mid, 0.095, 0.02)
    if value < price_hkd:
        lo = mid
    else:
        hi = mid
implied_growth = (lo + hi) / 2

result = {
    "units": "除每股价格外，金额为人民币百万元；每股价格为港元",
    "cash_flow_bridge": {
        "2025净利润": net_profit,
        "2025净利润至OCF净调整": noncash_and_other,
        "2025报表OCF": reported_ocf,
        "2025购建长期资产现金支出": cash_capex,
        "2025税后利息重计": after_tax_interest,
        "2025_FCFF": fcff_2025,
        "2024_FCFF": fcff_2024,
        "两年标准化FCFF": normalized_fcff,
    },
    "net_cash_bridge": {
        "现金及现金等价物": cash,
        "减客户备付金": customer_provisions,
        "减有息借款及租赁负债": interest_debt,
        "保守净现金": conservative_net_cash,
    },
    "dcf_scenarios_hkd": dcf_scenarios,
    "ri_scenarios_hkd": ri_scenarios,
    "weights": weights,
    "combined_scenarios_hkd": combined,
    "target_price_hkd": target,
    "valuation_certainty": certainty,
    "mechanical_buy_price_hkd": buy_price,
    "dcf_sensitivity_hkd": dcf_sensitivity,
    "ri_sensitivity_hkd": ri_sensitivity,
    "reverse_dcf_implied_5y_growth": implied_growth,
    "market_price_hkd": price_hkd,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
