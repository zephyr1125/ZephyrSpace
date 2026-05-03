#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\zephy\.agents\skills\lixinger-query\scripts')
from lixinger_client import query
from datetime import date
import json

# 4家公司代码（纯数字，不带后缀）
codes = ['000975', '688281', '600181', '600415']
code_names = {
    '000975': '山金国际',
    '688281': '思特威-W',
    '600181': '佐力药业',
    '600415': '小商品城'
}

result = {}

# 1. 查询当前市值和基本面
print('=== 1. 当前市值与基本面 ===')
try:
    res = query(
        'cn/company/fundamental/non_financial',
        stockCodes=codes,
        date='2026-04-30',
        metricsList=['mc', 'pe_ttm', 'pb', 'ps_ttm', 'dyr', 'cp', 'roe']
    )
    for item in res.get('data', []):
        code = item.get('stockCode')
        mc = item.get('mc')  # 市值（亿元）
        pe = item.get('pe_ttm')
        roe = item.get('roe')
        cp = item.get('cp')
        dyr = item.get('dyr')
        result[code] = {
            'name': code_names.get(code, code),
            'market_cap': mc,
            'price': cp,
            'pe_ttm': pe,
            'roe': roe,
            'dyr': dyr
        }
        print(f"{code_names.get(code, code)} ({code}): 市值={mc}亿 现价={cp} PE={pe} ROE={roe}% 股息率={dyr}%")
except Exception as e:
    print(f'查询基本面失败: {e}')
    import traceback
    traceback.print_exc()

# 2. 查询最近3年年报毛利率
print('\n=== 2. 近3年毛利率 ===')
for code in codes:
    result[code]['gross_margins'] = {}
    for year_end in ['2023-12-31', '2024-12-31', '2025-12-31']:
        try:
            res = query(
                'cn/company/fs/non_financial',
                stockCodes=[code],
                startDate=year_end,
                endDate=year_end,
                metricsList=['q.ps.toi.t', 'q.ps.cogs.t']
            )
            if res.get('data'):
                item = res['data'][0]
                toi = item.get('q', {}).get('ps', {}).get('toi', {}).get('t')
                cogs = item.get('q', {}).get('ps', {}).get('cogs', {}).get('t')
                if toi and cogs:
                    margin = (toi - cogs) / toi * 100
                    year = year_end[:4]
                    result[code]['gross_margins'][year] = round(margin, 1)
                    print(f"  {code_names.get(code)} {year}: {margin:.1f}%")
        except Exception as e:
            print(f"  查询{code} {year_end}失败: {e}")

# 3. 查询分红信息
print('\n=== 3. 分红信息 ===')
for code in codes:
    try:
        res = query(
            'cn/company/dividend',
            stockCode=code,
            startDate='2023-01-01',
            endDate='2026-12-31',
            limit=20
        )
        dividends = res.get('data', [])
        print(f"{code_names.get(code)} ({code}): 近3年{len(dividends)}次分红")
        if dividends:
            result[code]['dividends'] = []
            for d in dividends[:5]:  # 保留最近5条
                result[code]['dividends'].append({
                    'date': d.get('dividendDate'),
                    'amount': d.get('cashDividend')
                })
                print(f"  {d.get('dividendDate')}: 现金股利={d.get('cashDividend')}")
    except Exception as e:
        print(f"  查询{code}分红失败: {e}")

# 保存结果
with open('batch7_moat_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('\n数据已保存到 batch7_moat_data.json')
