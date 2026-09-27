from decimal import Decimal, getcontext
import json

getcontext().prec = 28

dupont = {
    "2023": ["77521476277.80", "150560330316.45", "254500826096.02", "272699660092.25", "204938081263.86", "223656469294.82"],
    "2024": ["89334728025.90", "174144069958.25", "272699660092.25", "298944579918.70", "223656469294.82", "242011315120.60"],
    "2025": ["85310324833.67", "172054171890.91", "298944579918.70", "303834844021.44", "242011315120.60", "253959253909.07"],
}

out = {"dupont": {}, "capital_boundary": {}}
for year, raw in dupont.items():
    profit, revenue, assets_begin, assets_end, equity_begin, equity_end = map(Decimal, raw)
    avg_assets = (assets_begin + assets_end) / 2
    avg_equity = (equity_begin + equity_end) / 2
    margin = profit / revenue
    turnover = revenue / avg_assets
    multiplier = avg_assets / avg_equity
    roe = margin * turnover * multiplier
    out["dupont"][year] = {
        "inputs_yuan": {"net_profit": str(profit), "revenue": str(revenue), "assets_begin": str(assets_begin), "assets_end": str(assets_end), "equity_begin": str(equity_begin), "equity_end": str(equity_end)},
        "net_margin": str(margin), "asset_turnover": str(turnover), "equity_multiplier": str(multiplier), "roe": str(roe)
    }

# 6400吨系列酒项目：预算34.5416亿元；仅做每吨经营贡献敏感性，不冒充项目IRR。
budget = Decimal("3454160000")
capacity = Decimal("6400")
for contribution_per_ton in (Decimal("50000"), Decimal("75000"), Decimal("100000")):
    annual_contribution = capacity * contribution_per_ton
    out["capital_boundary"][str(contribution_per_ton)] = {
        "annual_operating_contribution_yuan": str(annual_contribution),
        "contribution_on_budget": str(annual_contribution / budget),
        "simple_payback_years": str(budget / annual_contribution)
    }

print(json.dumps(out, ensure_ascii=False, indent=2))
