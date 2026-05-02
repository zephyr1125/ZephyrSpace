"""
Batch A 申万一级行业数据采集：农林牧渔/钢铁/有色金属/煤炭/石油石化
使用 sw_daily 获取价格历史，理杏仁获取PE分位
"""
import os, requests, time, json
import numpy as np
import pandas as pd
import tushare as ts
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv(r'E:\ObsidianVaults\ZephyrSpace\.env')
lx_token = os.getenv('LIXINGER_TOKEN')
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

industries = [
    {'lx': '110000', 'wind': '801010.SI', 'name': '农林牧渔'},
    {'lx': '230000', 'wind': '801040.SI', 'name': '钢铁'},
    {'lx': '240000', 'wind': '801050.SI', 'name': '有色金属'},
    {'lx': '740000', 'wind': '801950.SI', 'name': '煤炭'},
    {'lx': '750000', 'wind': '801960.SI', 'name': '石油石化'},
]

trade_date = '20260430'  # 最近交易日（5月1日为节假日）
start_3y = (datetime(2026, 4, 30) - timedelta(days=365*3)).strftime('%Y%m%d')

results = {}

for ind in industries:
    nm = ind['name']
    lx = ind['lx']
    wind = ind['wind']
    print('\n=== ' + nm + ' (' + lx + ') ===')

    # 1. 理杏仁 PE/股息率分位（用04-30）
    resp = requests.post(
        'https://open.lixinger.com/api/cn/industry/fundamental/sw_2021',
        json={
            'token': lx_token,
            'stockCodes': [lx],
            'metricsList': [
                'pe_ttm.mcw',
                'pe_ttm.y3.mcw.cvpos',
                'pe_ttm.y5.mcw.cvpos',
                'pe_ttm.y3.mcw.q2v',
                'pe_ttm.y3.mcw.q5v',
                'pe_ttm.y3.mcw.q8v',
                'dyr.mcw',
            ],
            'startDate': '2026-04-30T00:00:00+08:00',
            'endDate':   '2026-04-30T00:00:00+08:00',
        }
    )
    lx_json = resp.json()
    print('LX message: ' + lx_json.get('message', 'ok'))
    pe_cur = pe_3y_pos = pe_5y_pos = pe_q2 = pe_q5 = pe_q8 = dy = None
    if lx_json.get('data'):
        d = lx_json['data'][0]
        pe_cur    = d.get('pe_ttm.mcw')
        pe_3y_pos = d.get('pe_ttm.y3.mcw.cvpos')
        pe_5y_pos = d.get('pe_ttm.y5.mcw.cvpos')
        pe_q2     = d.get('pe_ttm.y3.mcw.q2v')
        pe_q5     = d.get('pe_ttm.y3.mcw.q5v')
        pe_q8     = d.get('pe_ttm.y3.mcw.q8v')
        dy        = d.get('dyr.mcw')
        print('  PE_cur=' + str(round(pe_cur,2) if pe_cur else None) +
              ', 3y_pos=' + str(round(pe_3y_pos*100,1) if pe_3y_pos else None) +
              ', 5y_pos=' + str(round(pe_5y_pos*100,1) if pe_5y_pos else None))
        print('  DY=' + str(round(dy*100,2) if dy else None))
        print('  PE_P20=' + str(round(pe_q2,2) if pe_q2 else None) +
              ', PE_P50=' + str(round(pe_q5,2) if pe_q5 else None) +
              ', PE_P80=' + str(round(pe_q8,2) if pe_q8 else None))
    else:
        print('  NO LX DATA')

    # 2. 3年价格历史（使用 sw_daily，ts_code参数过滤）
    df_p = pro.sw_daily(ts_code=wind, start_date=start_3y, end_date=trade_date)
    if df_p is None or len(df_p) == 0:
        print('  NO PRICE DATA')
        continue
    df_p = df_p.sort_values('trade_date').reset_index(drop=True)
    cur_price = float(df_p.iloc[-1]['close'])
    cur_pe    = float(df_p.iloc[-1]['pe']) if 'pe' in df_p.columns else None
    cur_pb    = float(df_p.iloc[-1]['pb']) if 'pb' in df_p.columns else None
    prices = df_p['close'].dropna().values
    p80 = float(np.percentile(prices, 80))
    p50 = float(np.percentile(prices, 50))
    p20 = float(np.percentile(prices, 20))
    print('  Price=' + str(round(cur_price,2)) +
          ', P80=' + str(round(p80,2)) +
          ', P50=' + str(round(p50,2)) +
          ', P20=' + str(round(p20,2)))
    print('  PE(tushare)=' + str(cur_pe) + ', PB=' + str(cur_pb))

    results[lx] = {
        'name': nm, 'wind': wind, 'lx': lx,
        'pe_cur': pe_cur, 'pe_cur_ts': cur_pe,
        'pe_3y_pos': pe_3y_pos, 'pe_5y_pos': pe_5y_pos,
        'pe_q2': pe_q2, 'pe_q5': pe_q5, 'pe_q8': pe_q8,
        'dy': dy, 'pb': cur_pb,
        'price': cur_price, 'p80': p80, 'p50': p50, 'p20': p20,
    }
    time.sleep(1)

print('\n\n=== FINAL RESULTS ===')
print(json.dumps(results, ensure_ascii=False, indent=2))
