#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open("01-公司/羚锐制药.md", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the PreBuy conclusion with escaped quotes
content = content.replace(
    '**结论：维持 growth，但更接近"稳健型 growth"。核心吸引力不是高速成长，而是高毛利、较强现金流和当前不贵的估值。**',
    '**结论：维持 growth，但更接近"稳健型 growth"。Q1 2026 利润同比下滑反映高基数和季节性，但毛利率仍维持67%+高位，价格成本结构未变。核心吸引力不是高速成长，而是高毛利、较强现金流和当前不贵的估值。**'
)

# Update line 27
content = content.replace(
    "1. `2025年` ROE `23.47%`，毛利率 `80.03%`，净利率 `19.79%`，盈利质量非常好。",
    "1. `2025年` ROE `23.47%`，毛利率 `80.03%`，净利率 `19.79%`，盈利质量非常好；Q1 2026毛利率67.96%，仍维持高位。"
)

with open("01-公司/羚锐制药.md", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 羚锐制药 PreBuy 结论已更新")
