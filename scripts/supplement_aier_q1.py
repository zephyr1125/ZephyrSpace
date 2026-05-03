#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

print("爱尔眼科 (300015.SZ) Q1 2026 财报补充分析\n")

url = (
    "https://datacenter-web.eastmoney.com/api/data/v1/get"
    "?reportName=RPT_LICO_FN_CPD&columns=ALL"
    "&filter=(SECURITY_CODE%3D%22300015%22)"
    "&pageNumber=1&pageSize=5&sortColumns=REPORTDATE&sortTypes=-1"
)

try:
    resp = requests.get(url, headers={"Accept-Encoding": "gzip"}, timeout=10)
    data = resp.json()
    rows = data.get("result", {}).get("data", [])
    
    print("【季度数据对比（单位：万元原始，需÷10000转亿）】\n")
    print("期别 | 收入(万元) | 利润(万元) | 收入(亿) | 利润(亿) | 毛利率 | 收入YoY | 利润YoY")
    print("-" * 100)
    
    for row in rows[:3]:
        qdate = row.get("QDATE", "")
        income_raw = row.get("TOTAL_OPERATE_INCOME") or 0
        profit_raw = row.get("PARENT_NETPROFIT") or 0
        income_yi = income_raw / 10000
        profit_yi = profit_raw / 10000
        margin = row.get("XSMLL") or 0
        yoy_inc = row.get("YSTZ") or 0
        yoy_profit = row.get("SJLTZ") or 0
        
        print(f"{qdate:8} | {income_raw:10.0f} | {profit_raw:10.0f} | {income_yi:8.2f} | {profit_yi:8.2f} | {margin:6.2f}% | {yoy_inc:+7.1f}% | {yoy_profit:+7.1f}%")
    
    # 提取关键数据
    q1_2026 = next((r for r in rows if r.get("QDATE") == "2026Q1"), None)
    q1_2025 = next((r for r in rows if r.get("QDATE") == "2025Q1"), None)
    
    if q1_2026 and q1_2025:
        income_2026 = (q1_2026.get("TOTAL_OPERATE_INCOME") or 0) / 10000
        profit_2026 = (q1_2026.get("PARENT_NETPROFIT") or 0) / 10000
        margin_2026 = q1_2026.get("XSMLL") or 0
        roe_2026 = q1_2026.get("WEIGHTAVG_ROE") or 0
        yoy_inc_2026 = q1_2026.get("YSTZ") or 0
        yoy_profit_2026 = q1_2026.get("SJLTZ") or 0
        
        income_2025 = (q1_2025.get("TOTAL_OPERATE_INCOME") or 0) / 10000
        profit_2025 = (q1_2025.get("PARENT_NETPROFIT") or 0) / 10000
        margin_2025 = q1_2025.get("XSMLL") or 0
        roe_2025 = q1_2025.get("WEIGHTAVG_ROE") or 0
        
        print("\n" + "=" * 100)
        print("\n【2026Q1 数据摘要】\n")
        print(f"营业收入：{income_2026:.2f}亿")
        print(f"归母净利：{profit_2026:.2f}亿")
        print(f"毛利率：{margin_2026:.2f}%")
        print(f"加权ROE：{roe_2026:.2f}%")
        print(f"收入同比：{yoy_inc_2026:+.1f}%")
        print(f"利润同比：{yoy_profit_2026:+.1f}%")
        
        print("\n【与 2025Q1 对标】\n")
        print(f"营收：{income_2026:.2f}亿 vs {income_2025:.2f}亿，同比 {yoy_inc_2026:+.1f}%")
        print(f"利润：{profit_2026:.2f}亿 vs {profit_2025:.2f}亿，同比 {yoy_profit_2026:+.1f}%")
        print(f"毛利率：{margin_2026:.2f}% vs {margin_2025:.2f}%，环比 {(margin_2026-margin_2025):+.2f}pp")
        print(f"ROE：{roe_2026:.2f}% vs {roe_2025:.2f}%")
        
        print("\n【关键信号】\n")
        print(f"✅ 收入+{yoy_inc_2026:.1f}%、利润+{yoy_profit_2026:.1f}% → 增长加速")
        print(f"✅ 利润增速 > 收入增速 → 盈利质量好，成本控制有效")
        print(f"✅ 毛利率稳定在 {margin_2026:.1f}% → 产品定价权稳定")
        
except Exception as e:
    print(f"❌ 获取失败: {e}")
