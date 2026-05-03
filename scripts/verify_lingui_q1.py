#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

# 从东方财富获取羚锐完整季度历史数据
url = (
    "https://datacenter-web.eastmoney.com/api/data/v1/get"
    "?reportName=RPT_LICO_FN_CPD&columns=ALL"
    "&filter=(SECURITY_CODE%3D%22002296%22)"
    "&pageNumber=1&pageSize=20&sortColumns=REPORTDATE&sortTypes=-1"
)

try:
    resp = requests.get(url, headers={"Accept-Encoding": "gzip"}, timeout=10)
    data = resp.json()
    rows = data.get("result", {}).get("data", [])
    
    print(f"共获取 {len(rows)} 条季度财报记录\n")
    print("QDATE | 报告日期 | 营业收入 | 归母净利 | 收入同比% | 利润同比% | 毛利率% | 加权ROE% | 经营CFO")
    print("-" * 110)
    
    for i, row in enumerate(rows[:16]):  # 前16条(约4年)
        qdate = row.get("QDATE", "—")
        rdate = row.get("REPORTDATE", "—")
        income = row.get("TOTAL_OPERATE_INCOME", 0) or 0
        profit = row.get("PARENT_NETPROFIT", 0) or 0
        income_yoy = row.get("YSTZ", 0) or 0  # 收入同比%
        profit_yoy = row.get("SJLTZ", 0) or 0  # 净利同比%
        margin = row.get("XSMLL", 0) or 0  # 毛利率
        roe = row.get("WEIGHTAVG_ROE", 0) or 0
        cfo = row.get("JYXJL", 0) or 0  # 经营现金流
        
        print(f"{qdate:8} | {str(rdate)[:10]:10} | {income:7.2f}亿 | {profit:6.2f}亿 | {income_yoy:+6.1f}% | {profit_yoy:+7.1f}% | {margin:6.1f}% | {roe:6.2f}% | {cfo:6.2f}亿")
        
    print("\n分析：")
    print("=" * 110)
    
    # 提取历年 Q1 数据
    q1_data = [row for row in rows if row.get("QDATE", "").endswith("Q1")]
    if q1_data:
        print("\n历年 Q1 对比（从最新到最旧）：")
        print("QDATE | 营收 | 净利 | 毛利率 | 收入YoY | 利润YoY | ROE")
        print("-" * 70)
        for q1 in q1_data[:5]:  # 最近5个Q1
            qdate = q1.get("QDATE", "")
            income = q1.get("TOTAL_OPERATE_INCOME", 0) or 0
            profit = q1.get("PARENT_NETPROFIT", 0) or 0
            margin = q1.get("XSMLL", 0) or 0
            yoy_inc = q1.get("YSTZ", 0) or 0
            yoy_profit = q1.get("SJLTZ", 0) or 0
            roe = q1.get("WEIGHTAVG_ROE", 0) or 0
            print(f"{qdate:8} | {income:6.2f}亿 | {profit:5.2f}亿 | {margin:6.1f}% | {yoy_inc:+7.1f}% | {yoy_profit:+7.1f}% | {roe:6.2f}%")
        
        # 判断季节性
        print("\n季节性分析：")
        if len(q1_data) >= 2:
            latest_q1_profit = (q1_data[0].get("PARENT_NETPROFIT") or 0)
            prev_q1_profit = (q1_data[1].get("PARENT_NETPROFIT") or 0)
            print(f"  • 最近Q1（2026Q1）净利: {latest_q1_profit:.2f}亿")
            print(f"  • 上年Q1（2025Q1）净利: {prev_q1_profit:.2f}亿")
            
            # 同比增速
            yoy = ((latest_q1_profit - prev_q1_profit) / prev_q1_profit * 100) if prev_q1_profit else 0
            print(f"  • 同比增速: {yoy:+.1f}%")
            
            # 与全年对比
            latest_fy = next((r for r in rows if r.get("QDATE") == "2025"), None)
            if latest_fy:
                fy_profit = latest_fy.get("PARENT_NETPROFIT") or 0
                q1_pct = (latest_q1_profit / fy_profit * 100) if fy_profit else 0
                print(f"  • 2026Q1占2025全年利润: {q1_pct:.1f}%")
                print(f"  • 2025全年利润: {fy_profit:.2f}亿 (Q1占比低说明Q1是淡季)")
        
except Exception as e:
    print(f"❌ 获取失败: {e}")
