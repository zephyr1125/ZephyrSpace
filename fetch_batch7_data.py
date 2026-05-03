#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime

# 4家公司基本信息
companies = {
    '000975': {'name': '山金国际', 'code_full': '000975.SZ'},
    '688281': {'name': '思特威-W', 'code_full': '688281.SH'},
    '600181': {'name': '佐力药业', 'code_full': '600181.SH'},
    '600415': {'name': '小商品城', 'code_full': '600415.SH'}
}

result = {}

# 东方财富财报查询接口
def fetch_eastmoney_financials(code):
    """从东方财富获取财务数据"""
    try:
        # 获取最新财报期
        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE%3D%22{code}%22)&pageNumber=1&pageSize=5"
        resp = requests.get(url, timeout=10)
        resp.encoding = 'utf-8'
        data = resp.json()
        
        if data.get('result', {}).get('data'):
            items = data['result']['data']
            code_num = code.split('.')[0]
            print(f"\n【{companies[code_num]['name']}】({code})")
            
            # 收集市值、毛利率等信息
            financials = {}
            for item in items[:4]:  # 最近4期（3年+最新）
                period = item.get('QDATE', '')
                market_cap = item.get('MKTCAP')  # 总市值（亿元）
                close_price = item.get('PRICE')  # 收盘价
                
                # 毛利率 = (营收 - 成本) / 营收
                revenue = item.get('REVENUE')
                cost = item.get('OPERATINGCOST')
                
                if revenue and cost:
                    gross_margin = (float(revenue) - float(cost)) / float(revenue) * 100
                else:
                    gross_margin = None
                
                # 其他指标
                net_profit = item.get('NETPROFIT')
                roe = item.get('ROE')
                pe = item.get('PE')
                pb = item.get('PB')
                
                if period and market_cap:
                    financials[period] = {
                        'market_cap': float(market_cap),
                        'close_price': float(close_price) if close_price else None,
                        'gross_margin': gross_margin,
                        'net_profit': float(net_profit) if net_profit else None,
                        'roe': float(roe) if roe and roe != '0.00' else None,
                        'pe': float(pe) if pe and pe != '0.00' else None,
                        'pb': float(pb) if pb and pb != '0.00' else None,
                        'revenue': float(revenue) if revenue else None
                    }
                    
                    if close_price:
                        print(f"  {period}: 市值={market_cap}亿 现价={float(close_price):.2f} 毛利率={gross_margin:.1f}% ROE={roe}%")
                    else:
                        print(f"  {period}: 市值={market_cap}亿 毛利率={gross_margin:.1f}% ROE={roe}%")
            
            result[code_num] = {
                'name': companies[code_num]['name'],
                'code_full': code,
                'financials': financials
            }
            return True
        else:
            print(f"  未找到财务数据")
            return False
            
    except Exception as e:
        print(f"  查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# 查询所有公司
print("=" * 60)
print("从东方财富获取4家公司财务数据")
print("=" * 60)
for code_num, info in companies.items():
    fetch_eastmoney_financials(info['code_full'])

# 保存数据
with open('batch7_moat_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    
print('\n✓ 数据已保存到 batch7_moat_data.json')
