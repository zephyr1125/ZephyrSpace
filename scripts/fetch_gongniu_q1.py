#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

print("获取公牛集团 (603195) Q1 2026 财报数据...\n")

# 从东方财富获取 Q1 QDATE 是否已发布
print("从东方财富获取 Q1 2026 财报：")
resp = requests.get(
    "https://datacenter-web.eastmoney.com/api/data/v1/get?"
    "reportName=RPT_LICO_FN_CPD&columns=ALL&"
    "filter=(SECURITY_CODE%3D%22603195%22)&"
    "pageNumber=1&pageSize=5",
    headers={"Accept-Encoding": "gzip"}
)
rows = resp.json().get("result", {}).get("data", [])
if rows:
    print(f"返回 {len(rows)} 条记录：\n")
    for i, row in enumerate(rows[:3], 1):
        qdate = row.get("QDATE", "N/A")
        reportdate = row.get("REPORTDATE", "N/A")
        revenue = row.get("TOTAL_OPERATE_INCOME", 0)
        profit = row.get("PARENT_NETPROFIT", 0)
        roe = row.get("WEIGHTAVG_ROE", 0)
        xsmll = row.get("XSMLL", 0)
        isnew = row.get("ISNEW", "")
        
        # 转换为更易读的格式
        revenue_fmt = f"{float(revenue)/1e8:.2f}亿" if revenue else "N/A"
        profit_fmt = f"{float(profit)/1e8:.2f}亿" if profit else "N/A"
        roe_fmt = f"{float(roe):.2f}%" if roe else "N/A"
        xsmll_fmt = f"{float(xsmll):.2f}%" if xsmll else "N/A"
        
        print(f"第 {i} 条：")
        print(f"  QDATE: {qdate} (最新: {isnew})")
        print(f"  报告日期: {reportdate}")
        print(f"  营业总收入: {revenue_fmt}")
        print(f"  归母净利润: {profit_fmt}")
        print(f"  加权ROE: {roe_fmt}")
        print(f"  毛利率: {xsmll_fmt}")
        print()
else:
    print("未获取到数据")
