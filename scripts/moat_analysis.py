#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
第四轮筛选：护城河强度评估
"""
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    """调用理杏仁 API"""
    try:
        resp = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN}, timeout=10)
        result = resp.json()
        if result.get("code") != 0:
            print(f"❌ API 错误 ({path}): {result.get('msg')}")
            return {"data": []}
        return result
    except Exception as e:
        print(f"❌ 请求失败 ({path}): {e}")
        return {"data": []}

def last_trading_day(days_back=1):
    """计算最近交易日（跳过周末）"""
    d = datetime.now()
    for _ in range(days_back):
        d -= timedelta(days=1)
        while d.weekday() >= 5:  # 5=周六 6=周日
            d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")

# ========== 第1步：拉取市值和毛利率数据 ==========
codes = ["300972", "002267", "002850", "002847"]
company_names = {
    "300972": "万辰集团",
    "002267": "东鹏饮料",
    "002850": "兴齐眼药",
    "002847": "盐津铺子"
}

print("=" * 60)
print("📊 第1步：拉取市值和毛利率数据")
print("=" * 60)

# 获取当前市值
trade_date = last_trading_day()
print(f"\n📅 数据基准日期：{trade_date}")

print("\n📈 获取市值数据...")
market_cap_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": trade_date,
    "metricsList": ["mc"]
})

market_cap_data = {}
for d in market_cap_resp.get("data", []):
    code = d.get("stockCode")
    mc = d.get("mc")
    if code and mc is not None:
        market_cap_data[code] = mc

print("\n💰 市值汇总：")
for code in codes:
    mc = market_cap_data.get(code)
    name = company_names[code]
    if mc is None:
        status = "❓"
        mc_str = "N/A"
    else:
        status = "✓" if mc >= 50 else "✗"
        mc_str = f"{mc:.1f}"
    print(f"  {name:12} ({code}): {mc_str:>7}亿元 {status}")

# 获取毛利率（最近3年）
print("\n📊 获取毛利率数据...")
gross_margin_data = {}
for year_end in ["2023-12-31", "2024-12-31", "2025-12-31"]:  # 2025年报可能未发
    fs_resp = lx_post("cn/company/fs/non_financial", {
        "stockCodes": codes,
        "date": year_end,
        "metricsList": ["a.ps.gp.margin"]
    })
    # 以年份为键存储
    year = year_end.split("-")[0]
    gross_margin_data[year] = {}
    for d in fs_resp.get("data", []):
        code = d.get("stockCode")
        margin = d.get("a.ps.gp.margin")  # 可能是 None
        if code:
            gross_margin_data[year][code] = margin

print("\n毛利率趋势（%）：")
print(f"{'公司':12} | 2023年 | 2024年 | 2025年 | 趋势")
print("-" * 50)
for code in codes:
    name = company_names[code]
    y2023 = gross_margin_data.get("2023", {}).get(code, "N/A")
    y2024 = gross_margin_data.get("2024", {}).get(code, "N/A")
    y2025 = gross_margin_data.get("2025", {}).get(code, "N/A")
    
    # 判断趋势
    trend = "?"
    if isinstance(y2023, (int, float)) and isinstance(y2024, (int, float)):
        if y2024 > y2023:
            trend = "↑ 上升"
        elif y2024 < y2023:
            trend = "↓ 下降"
        else:
            trend = "→ 稳定"
    
    print(f"{name:12} | {str(y2023):>6} | {str(y2024):>6} | {str(y2025):>6} | {trend}")

# ========== 保存原始数据以供后续分析 ==========
analysis_data = {
    "codes": codes,
    "company_names": company_names,
    "trade_date": trade_date,
    "market_cap": market_cap_data,
    "gross_margin": gross_margin_data
}

import json
with open("scripts/moat_raw_data.json", "w", encoding="utf-8") as f:
    json.dump(analysis_data, f, ensure_ascii=False, indent=2)

print("\n✅ 数据已保存到 moat_raw_data.json")
print("\n➡️  下一步：从东方财富获取补充财报验证...")
