# -*- coding: utf-8 -*-
import os, sys, time

with open('.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

import tushare as ts
ts.set_token(os.environ.get('TUSHARE_TOKEN', ''))
pro = ts.pro_api()

codes = [
    '000791.SZ','600642.SH','688123.SH','600887.SH','600550.SH','688676.SH',
    '300953.SZ','002518.SZ','600863.SH','600483.SH','000690.SZ','002979.SZ',
    '002236.SZ','688698.SH','603416.SH','688169.SH','603203.SH','300428.SZ',
    '601609.SH','603993.SH','688041.SH','002747.SZ','603629.SH',
    '000938.SZ','600580.SH','600098.SH','002249.SZ','603009.SH',
    '002074.SZ','600795.SH','000600.SZ','600027.SH','601567.SH','001301.SZ',
    '002150.SZ','603659.SH','600011.SH','301219.SZ','603369.SH',
    '002056.SZ','688008.SH','300857.SZ','002311.SZ','603210.SH'
]

# name lookup
name_map = {}
try:
    basic = pro.stock_basic(fields='ts_code,name')
    for _, row in basic.iterrows():
        name_map[row['ts_code']] = row['name']
except:
    pass

print(f"{'code':<12} {'name':<8} {'end_date':<12} {'flag':<5} {'ROE%':<7} {'NP同比%':<10} {'Rev同比%'}")
print('-'*70)
stale = []
for code in sorted(codes):
    try:
        r = pro.fina_indicator(
            ts_code=code,
            fields='ts_code,end_date,roe,netprofit_yoy,or_yoy',
            limit=2
        )
        if len(r):
            d = r.iloc[0]
            ed = str(d['end_date'])
            flag = 'Q1ok' if ed == '20260331' else 'STALE'
            if flag == 'STALE':
                stale.append(code)
            roe  = f"{float(d['roe']):.1f}"           if d['roe']              else 'N/A'
            npy  = f"{float(d['netprofit_yoy']):.1f}" if d['netprofit_yoy']    else 'N/A'
            revy = f"{float(d['or_yoy']):.1f}"        if d['or_yoy']           else 'N/A'
            name = name_map.get(code, '')[:6]
            print(f"{code:<12} {name:<8} {ed:<12} {flag:<5} {roe:<7} {npy:<10} {revy:<10}")
        time.sleep(0.12)
    except Exception as e:
        print(f"{code:<12} ERR: {e}")

print()
print(f"==> STALE (需web补验): {stale}")
