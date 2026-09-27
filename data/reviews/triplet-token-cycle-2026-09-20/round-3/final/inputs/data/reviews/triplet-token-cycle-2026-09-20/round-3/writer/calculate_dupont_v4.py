"""按年报合并资产与归母权益口径重算归母杜邦近似分解。"""
import json
from pathlib import Path

# 单位：亿元；资产为合并资产总计，权益与利润为归属于上市公司股东口径。
rows = [
    (2019, 854.2957346725, 412.0647101443, 1830.4237204250, 1360.1034987511),
    (2020, 949.1538091672, 466.9728542981, 2133.9581052746, 1613.2273508756),
    (2021, 1061.9015484376, 524.6014437816, 2551.6819515990, 1895.3936879729),
    (2022, 1240.9984377199, 627.1644373827, 2543.6480499525, 1975.0667239600),
    (2023, 1476.9360499414, 747.3407155075, 2726.9966009225, 2156.6857160743),
    (2024, 1708.9915227634, 862.2814642162, 2989.4457991870, 2331.0598439947),
]
out = []
for prev, cur in zip(rows, rows[1:]):
    year, revenue, profit, assets, equity = cur
    avg_assets = (prev[3] + assets) / 2
    avg_equity = (prev[4] + equity) / 2
    out.append({"year": year, "revenue": revenue, "attributable_profit": profit,
                "total_assets": assets, "attributable_equity": equity,
                "attributable_net_margin_pct": round(profit / revenue * 100, 4),
                "asset_turnover": round(revenue / avg_assets, 6),
                "equity_multiplier": round(avg_assets / avg_equity, 6),
                "implied_attributable_roe_pct": round(profit / avg_equity * 100, 4)})
Path(__file__).with_name("dupont-v4-result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
