#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PreBuy 数据收集脚本 - 基于用户初始数据补充财务细节
"""

import sys
sys.path.insert(0, r"C:\Users\zephy\.agents\skills\lixinger-query\scripts")

from lixinger_client import query
import json

# 用户提供的初始数据作为基础
companies_initial = {
    "中策橡胶": {
        "code": "002966",
        "ticker": "002966.SZ",
        "roe": 0.196,
        "pe": 8.8,
        "pe_percentile": 2.3,
        "market_cap_billion": 428,
        "remark": "轮胎"
    },
    "富特科技": {
        "code": "688784",
        "ticker": "688784.SH",
        "roe": 0.193,
        "pe": 25.5,
        "pe_percentile": 0.0,
        "market_cap_billion": 79,
        "remark": "汽车零部件"
    },
    "埃泰克": {
        "code": "600697",
        "ticker": "600697.SH",
        "roe": 0.183,
        "pe": 38.4,
        "pe_percentile": 20.0,
        "market_cap_billion": 89,
        "remark": "汽车零部件"
    }
}

results = {}

# 初始化结果字典
for name, info in companies_initial.items():
    results[name] = info.copy()

print("=== 基础数据已加载 ===")
print(f"✓ 已加载 {len(companies_initial)} 家公司初始数据")


# 第2b步：获取PE/PB历史分位 (当前日期)
print("\n=== 获取PE/PB历史分位 ===")
try:
    codes = [c["code"] for c in companies_initial.values()]
    val_resp = query(
        "cn/company/fundamental/non_financial",
        stockCodes=codes,
        date="2026-05-02",
        metricsList=["pe_ttm", "pb", "dyr", "mc"]
    )
    
    if val_resp["code"] == 1:
        for item in val_resp.get("data", []):
            code = item["stockCode"]
            # 匹配公司名
            for name, info in companies_initial.items():
                if info["code"] == code:
                    results[name]["估值详情"] = {
                        "PE_TTM": item.get("pe_ttm"),
                        "PB": item.get("pb"),
                        "股息率": item.get("dyr"),
                        "市值亿": item.get("mc")
                    }
                    break
        print(f"✓ 估值数据获取成功：{len(val_resp.get('data', []))}只公司")
    else:
        print(f"  API返回code={val_resp.get('code')}")
except Exception as e:
    print(f"✗ 估值数据获取失败：{e}")

# 第2c步：获取当前价格 (2026-05-02)
# candlestick 是 [S] 类型，必须逐只调用，需要 type 参数
print("\n=== 获取当前价格 ===")
for name, info in companies_initial.items():
    code = info["code"]
    try:
        price_resp = query(
            "cn/company/candlestick",
            stockCode=code,
            startDate="2026-05-02",
            endDate="2026-05-02",
            type="normal"  # 必须指定复权类型
        )
        
        if price_resp["code"] == 1 and price_resp.get("data"):
            latest = price_resp["data"][0]
            results[name]["价格数据"] = {
                "收盘价": latest.get("close"),
                "开盘价": latest.get("open"),
                "成交量": latest.get("volume"),
                "日期": latest.get("date")
            }
            print(f"  ✓ {name} 价格数据获取成功")
    except Exception as e:
        print(f"  ✗ {name} 价格数据获取失败：{str(e)[:60]}")
        continue

# 输出JSON格式结果
print("\n=== 数据收集完成 ===")
print(json.dumps(results, indent=2, ensure_ascii=False))

# 保存为文件便于后续处理
with open("prebuy_data_collected.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n✓ 已保存到 prebuy_data_collected.json")
