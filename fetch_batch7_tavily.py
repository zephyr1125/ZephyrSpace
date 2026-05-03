#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\ObsidianVaults\ZephyrSpace\scripts')

from tavily_search import search_red_flags, prebuy_web_research
import json

companies = [
    {'code': '000975.SZ', 'name': '山金国际', 'industry': '黄金采选'},
    {'code': '688281.SH', 'name': '思特威-W', 'industry': '图像芯片'},
    {'code': '600181.SH', 'name': '佐力药业', 'industry': '中成药'},
    {'code': '600415.SH', 'name': '小商品城', 'industry': '商业贸易'}
]

result = {}

print("=" * 70)
print("使用 Tavily 搜索4家公司信息")
print("=" * 70)

for company in companies:
    print(f"\n【{company['name']}】({company['code']})")
    print(f"行业: {company['industry']}")
    print("-" * 50)
    
    try:
        # 调用 Tavily 搜索
        research = prebuy_web_research(company['name'], company['code'])
        
        result[company['code']] = {
            'name': company['name'],
            'industry': company['industry'],
            'red_flags': research.get('red_flags', []),
            'recent_news': research.get('recent_news', []),
            'company_info': research.get('company_info', '')
        }
        
        # 输出结果
        print("🚩 主要红旗:")
        if research.get('red_flags'):
            for flag in research['red_flags'][:3]:
                print(f"  • {flag}")
        else:
            print("  (未发现重大红旗)")
        
        print("\n📰 近期重要新闻:")
        if research.get('recent_news'):
            for news in research['recent_news'][:3]:
                print(f"  • {news}")
        else:
            print("  (无特别重要新闻)")
        
        print("\n📊 公司背景:")
        if research.get('company_info'):
            info_text = research['company_info'][:200]
            print(f"  {info_text}...")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        result[company['code']] = {
            'name': company['name'],
            'industry': company['industry'],
            'error': str(e)
        }

# 保存结果
with open('batch7_tavily_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print('\n✓ 数据已保存到 batch7_tavily_data.json')
