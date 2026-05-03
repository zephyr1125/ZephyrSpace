#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tavily网络调研：获取红旗和重大事件"""

import sys
sys.path.insert(0, r"E:\ObsidianVaults\ZephyrSpace\scripts")

from tavily_search import prebuy_web_research
import json

companies = [
    {"name": "中策橡胶", "ticker": "002966.SZ"},
    {"name": "富特科技", "ticker": "688784.SH"},
    {"name": "埃泰克", "ticker": "600697.SH"}
]

results = {}

print("=== Tavily 网络调研 ===\n")

for company in companies:
    name = company["name"]
    ticker = company["ticker"]
    print(f"【{name}】({ticker})")
    
    try:
        result = prebuy_web_research(name, ticker)
        results[name] = result
        
        # 显示调研结果摘要
        if result.get("red_flags"):
            print(f"  🚩 红旗数量：{len(result['red_flags'])}")
            for flag in result["red_flags"][:3]:
                print(f"    - {flag['title'][:60]}")
        else:
            print(f"  ✓ 未发现重大红旗")
        
        if result.get("recent_news"):
            print(f"  📰 重大事件：{len(result['recent_news'])}项")
            for news in result["recent_news"][:2]:
                print(f"    - {news['title'][:60]}")
        else:
            print(f"  ℹ️ 无最近事件")
        
        print()
    except Exception as e:
        print(f"  ✗ 调研失败：{str(e)[:100]}\n")
        continue

# 保存结果
with open("tavily_research_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("✓ 已保存到 tavily_research_result.json")
