#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\zephy\.agents\skills\lixinger-query\scripts')
from lixinger_client import query
import json
from datetime import datetime

companies = {
    '000975': '山金国际',
    '688281': '思特威-W',
    '600181': '佐力药业',
    '600415': '小商品城'
}

result = {}

print("=" * 70)
print("使用理杏仁API查询4家公司财务数据")
print("=" * 70)

# 第一步：查询市值、PE、PB、ROE、股息率
print("\n【第一步】查询当前基本面...")
try:
    res = query(
        'cn/company/fundamental/non_financial',
        stockCodes=list(companies.keys()),
        date='2026-04-30',
        metricsList=['mc', 'pe_ttm', 'pb', 'dyr']
    )
    
    for item in res.get('data', []):
        code = item.get('stockCode')
        if code in companies:
            result[code] = {
                'name': companies[code],
                'market_cap': item.get('mc'),
                'pe_ttm': item.get('pe_ttm'),
                'pb': item.get('pb'),
                'dyr': item.get('dyr')
            }
            print(f"  {companies[code]}: 市值={item.get('mc')}亿 PE={item.get('pe_ttm')} PB={item.get('pb')} DYR={item.get('dyr')}%")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 第二步：查询财报数据（毛利率）- 分别查不同年份
print("\n【第二步】查询毛利率数据...")

# 分别查2023、2024、2025年报
for year_end in ['2025-12-31', '2024-12-31', '2023-12-31']:
    print(f"  查询 {year_end[:4]} 年报...")
    try:
        res = query(
            'cn/company/fs/non_financial',
            stockCodes=list(companies.keys()),
            date=year_end,
            metricsList=['q.ps.toi.t', 'q.ps.cogs.t']
        )
        
        for item in res.get('data', []):
            code = item.get('stockCode')
            if code in companies:
                if code not in result:
                    result[code] = {'name': companies[code]}
                if 'gross_margins' not in result[code]:
                    result[code]['gross_margins'] = {}
                
                toi = item.get('q', {}).get('ps', {}).get('toi', {}).get('t')
                cogs = item.get('q', {}).get('ps', {}).get('cogs', {}).get('t')
                
                if toi and cogs and float(toi) > 0:
                    margin = (float(toi) - float(cogs)) / float(toi) * 100
                    year = year_end[:4]
                    result[code]['gross_margins'][year] = round(margin, 1)
                    print(f"    {companies[code]} {year}: {margin:.1f}%")
    except Exception as e:
        print(f"    ❌ 失败: {e}")

# 第三步：查询分红数据
print("\n【第三步】查询分红历史...")
for code in companies.keys():
    try:
        res = query(
            'cn/company/dividend',
            stockCode=code,
            startDate='2023-01-01',
            endDate='2026-12-31'
        )
        
        dividends = res.get('data', [])
        if code not in result:
            result[code] = {'name': companies[code]}
        result[code]['dividend_count'] = len(dividends)
        result[code]['recent_dividends'] = []
        
        for div in dividends[:5]:
            result[code]['recent_dividends'].append({
                'date': div.get('dividendDate'),
                'amount': div.get('cashDividend')
            })
        
        if dividends:
            print(f"  {companies[code]}: {len(dividends)}次分红 (最近: {dividends[0].get('dividendDate')} ¥{dividends[0].get('cashDividend')})")
        else:
            print(f"  {companies[code]}: 无分红记录")
    except Exception as e:
        print(f"  {companies[code]}: 查询失败 - {e}")

# 保存结果
with open('batch7_lixinger_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print('\n✓ 数据已保存到 batch7_lixinger_data.json')
print("\nJSON数据内容:")
print(json.dumps(result, ensure_ascii=False, indent=2))
