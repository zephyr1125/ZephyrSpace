#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

print("获取爱尔眼科 (300015.SZ) Q1 2026 财报数据...\n")

# 爱尔眼科代码：300015
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
    
    print(f"从东方财富获取 Q1 2026 财报：")
    print(f"返回 {len(rows)} 条记录：\n")
    
    for i, row in enumerate(rows, 1):
        qdate = row.get("QDATE", "—")
        isnew = row.get("ISNEW", 0)
        rdate = row.get("REPORTDATE", "—")
        income = (row.get("TOTAL_OPERATE_INCOME") or 0) / 10000  # 万元 -> 亿元
        profit = (row.get("PARENT_NETPROFIT") or 0) / 10000
        yoy_inc = (row.get("YSTZ") or 0)
        yoy_profit = (row.get("SJLTZ") or 0)
        roe = (row.get("WEIGHTAVG_ROE") or 0)
        margin = (row.get("XSMLL") or 0)
        
        marker = " (🔴 最新)" if isnew == 1 else ""
        print(f"第 {i} 条：")
        print(f"  QDATE: {qdate} (最新: {isnew}){marker}")
        print(f"  报告日期: {rdate}")
        print(f"  营业总收入: {income:.2f}亿")
        print(f"  归母净利润: {profit:.2f}亿")
        print(f"  加权ROE: {roe:.2f}%")
        print(f"  毛利率: {margin:.2f}%")
        print(f"  收入YoY: {yoy_inc:+.1f}%")
        print(f"  利润YoY: {yoy_profit:+.1f}%\n")
        
    # 特别提取 2026Q1 数据
    q1_2026 = next((r for r in rows if r.get("QDATE") == "2026Q1"), None)
    if q1_2026:
        print("=" * 70)
        print("【2026Q1 提取结果】")
        print(f"营业总收入: {(q1_2026.get('TOTAL_OPERATE_INCOME') or 0) / 10000:.2f}亿")
        print(f"归母净利润: {(q1_2026.get('PARENT_NETPROFIT') or 0) / 10000:.2f}亿")
        print(f"加权ROE: {q1_2026.get('WEIGHTAVG_ROE') or 0:.2f}%")
        print(f"毛利率: {q1_2026.get('XSMLL') or 0:.2f}%")
        print(f"收入同比: {q1_2026.get('YSTZ') or 0:+.1f}%")
        print(f"利润同比: {q1_2026.get('SJLTZ') or 0:+.1f}%")
    else:
        print("⚠️ 未找到 2026Q1 数据，可能尚未发布")
        
except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()
