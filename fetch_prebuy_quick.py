#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速 PreBuy 数据拉取脚本 - 4 家 A 股公司
使用固定日期（2025-12-31）
"""
import requests
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
if not LX_TOKEN:
    print("ERROR: LIXINGER_TOKEN not found in .env")
    exit(1)

LX_BASE = "https://open.lixinger.com/api"

def lx_post(path, payload):
    """调用理杏仁 API"""
    resp = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN})
    data = resp.json()
    if data.get("msg"):
        print(f"  API返回: {data.get('msg')}")
    return data

# 目标公司
companies = [
    {"name": "伊利股份", "code": "600887", "shr": "SH"},
    {"name": "海天味业", "code": "603288", "shr": "SH"},
    {"name": "大博医疗", "code": "002901", "shr": "SZ"},
    {"name": "东方电子", "code": "000682", "shr": "SZ"},
]

# 使用固定日期（2025年底数据）
trade_date = "2025-12-31"
last_annual_end = "2024-12-31"

print(f"交易日期: {trade_date}")
print(f"财报期末: {last_annual_end}")
print()

# 拉取价格（逐只，因为需要分开输出）
price_data = {}
for company in companies:
    code = company["code"]
    result = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "endDate": trade_date,
        "count": 1
    })
    if result.get("data"):
        price_data[code] = result["data"][0]
        print(f"✓ {company['name']} 获取价格")
    else:
        print(f"✗ {company['name']} 价格拉取失败: {result.get('msg', '未知错误')}")

print()

# 批量拉取估值
codes = [c["code"] for c in companies]
print("拉取估值指标...")
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": trade_date,
    "metricsList": ["pe_ttm", "pb", "mc", "dyr"]
})
val_dict = {d["stockCode"]: d for d in val_resp.get("data", [])}
print(f"✓ 估值数据: {len(val_dict)}/{len(codes)} 家")

# 批量拉取财报
print("拉取财报指标...")
fs_resp = lx_post("cn/company/fs/non_financial", {
    "stockCodes": codes,
    "date": last_annual_end,
    "metricsList": ["a.pr.roe.t", "a.ps.toi.t", "a.ps.ni.t", "a.ps.ni.exclud.t", "a.cf.operating.t"]
})
fs_dict = {d["stockCode"]: d for d in fs_resp.get("data", [])}
print(f"✓ 财报数据: {len(fs_dict)}/{len(codes)} 家")

print()
print("=" * 80)
print("数据汇总")
print("=" * 80)

result_data = {}
for company in companies:
    code = company["code"]
    name = company["name"]
    
    price_info = price_data.get(code, {})
    val_info = val_dict.get(code, {})
    fs_info = fs_dict.get(code, {})
    
    result_data[code] = {
        "name": name,
        "code": code,
        "shr": company["shr"],
        "trade_date": trade_date,
        "price": price_info.get("closePrice"),
        "pe_ttm": val_info.get("pe_ttm"),
        "pb": val_info.get("pb"),
        "mc": val_info.get("mc"),  # 亿元
        "dyr": val_info.get("dyr"),  # 股息率 %
        "roe": fs_info.get("a.pr.roe.t"),
        "revenue": fs_info.get("a.ps.toi.t"),  # 营收
        "net_income": fs_info.get("a.ps.ni.t"),  # 归母净利
        "net_income_exclud": fs_info.get("a.ps.ni.exclud.t"),  # 扣非净利
        "ocf": fs_info.get("a.cf.operating.t"),  # 经营现金流
    }
    
    print(f"\n【{name}】{code}.{company['shr']}")
    if price_info.get('closePrice'):
        print(f"  当前价: ¥{price_info.get('closePrice'):.2f}")
    else:
        print(f"  当前价: N/A")
    
    if val_info.get('pe_ttm'):
        print(f"  PE(TTM): {val_info.get('pe_ttm'):.1f}x")
    if val_info.get('pb'):
        print(f"  PB: {val_info.get('pb'):.2f}x")
    if val_info.get('mc'):
        print(f"  市值: ¥{val_info.get('mc'):.0f}亿")
    if val_info.get('dyr') is not None:
        print(f"  股息率DY(TTM): {val_info.get('dyr'):.2f}%")
    
    if fs_info.get('a.pr.roe.t') is not None:
        print(f"  ROE({last_annual_end[:4]}年): {fs_info.get('a.pr.roe.t'):.2f}%")
    if fs_info.get('a.ps.ni.t') is not None:
        print(f"  归母净利({last_annual_end[:4]}年): ¥{fs_info.get('a.ps.ni.t'):.2f}亿")

# 输出 JSON 供后续使用
with open("fetch_prebuy_quick_data.json", "w", encoding="utf-8") as f:
    json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 数据已保存至 fetch_prebuy_quick_data.json")

print()
