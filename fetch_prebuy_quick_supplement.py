#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充财报和价格数据 - 使用 tushare
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
TS_TOKEN = os.getenv("TUSHARE_TOKEN")
if not TS_TOKEN:
    print("ERROR: TUSHARE_TOKEN not found in .env")
    exit(1)

API_URL = "https://api.tushare.pro"

def ts_api_call(api_name, params):
    """调用 tushare API"""
    data = {
        "api_name": api_name,
        "token": TS_TOKEN,
        "params": params,
        "fields": ""
    }
    r = requests.post(API_URL, json=data)
    return r.json()

# 4个公司的代码
companies_ts = [
    {"name": "伊利股份", "code": "600887", "ts_code": "600887.SH"},
    {"name": "海天味业", "code": "603288", "ts_code": "603288.SH"},
    {"name": "大博医疗", "code": "002901", "ts_code": "002901.SZ"},
    {"name": "东方电子", "code": "000682", "ts_code": "000682.SZ"},
]

# 读取已有数据
with open("fetch_prebuy_quick_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("补充财报和价格数据")
print("=" * 80)

# 补充价格和财务数据
for company in companies_ts:
    code = company["code"]
    ts_code = company["ts_code"]
    name = company["name"]
    
    print(f"\n【{name}】{ts_code}")
    
    # 获取日线数据（最新价格）
    try:
        daily_resp = ts_api_call("daily", {"ts_code": ts_code, "start_date": "20250101", "end_date": "20251231"})
        if daily_resp.get("data") and daily_resp["data"].get("items"):
            latest_price = daily_resp["data"]["items"][0][3]  # 收盘价
            data[code]["price"] = latest_price
            print(f"  当前价: ¥{latest_price:.2f}")
        else:
            print(f"  当前价: 拉取失败")
    except Exception as e:
        print(f"  当前价: 错误 - {e}")
    
    # 获取财务指标（fina_indicator）
    try:
        fina_resp = ts_api_call("fina_indicator", {"ts_code": ts_code, "start_date": "20240101", "end_date": "20241231"})
        if fina_resp.get("data") and fina_resp["data"].get("items"):
            items = fina_resp["data"]["items"]
            # items 格式: [字段值列表]，需要找到对应的字段
            # 字段在 fina_resp["data"]["fields"] 中
            fields = fina_resp["data"].get("fields", [])
            
            if items:
                row = items[0]  # 最新一期
                data_dict = dict(zip(fields, row)) if fields else {}
                
                if "roe" in data_dict:
                    data[code]["roe"] = data_dict["roe"]
                    print(f"  ROE(TTM): {data_dict['roe']:.2f}%" if data_dict.get("roe") else "  ROE(TTM): N/A")
        else:
            print(f"  财务指标: 拉取失败")
    except Exception as e:
        print(f"  财务指标: 错误 - {e}")
    
    # 获取业绩快报（fina_audit）
    try:
        audit_resp = ts_api_call("fina_audit", {"ts_code": ts_code})
        if audit_resp.get("data") and audit_resp["data"].get("items"):
            items = audit_resp["data"]["items"]
            fields = audit_resp["data"].get("fields", [])
            
            if items:
                row = items[0]
                data_dict = dict(zip(fields, row)) if fields else {}
                # 从 audit 中提取净利润等
                print(f"  业绩快报: 已获取")
        else:
            print(f"  业绩快报: 无数据")
    except Exception as e:
        print(f"  业绩快报: 错误 - {e}")

# 保存补充后的数据
with open("fetch_prebuy_quick_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 补充数据已保存")
