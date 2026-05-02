"""
Batch A 申万一级行业 - 加权ROE + 成分股集中度采集
使用 index_member(is_new=Y) + daily_basic(市值) + fina_indicator(ROE)
"""
import os, time, json
import pandas as pd
import numpy as np
import tushare as ts
from dotenv import load_dotenv

load_dotenv(r'E:\ObsidianVaults\ZephyrSpace\.env')
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

TRADE_DATE = '20260430'

industries = [
    {'lx': '110000', 'wind': '801010.SI', 'name': '农林牧渔'},
    {'lx': '230000', 'wind': '801040.SI', 'name': '钢铁'},
    {'lx': '240000', 'wind': '801050.SI', 'name': '有色金属'},
    {'lx': '740000', 'wind': '801950.SI', 'name': '煤炭'},
    {'lx': '750000', 'wind': '801960.SI', 'name': '石油石化'},
]

results = {}

for ind in industries:
    nm = ind['name']
    wind = ind['wind']
    print('\n=== ' + nm + ' ===')

    # 1. 获取当前成分股
    df_m = pro.index_member(index_code=wind)
    current = df_m[df_m['is_new'] == 'Y']['con_code'].tolist()
    print('  Current members:', len(current))

    # 2. 获取市值 (daily_basic)
    mv_rows = []
    for code in current[:50]:  # 取前50只用于估算
        try:
            r = pro.daily_basic(ts_code=code, trade_date=TRADE_DATE, fields='ts_code,total_mv')
            if r is not None and len(r) > 0:
                mv_rows.append({'ts_code': code, 'total_mv': float(r.iloc[0]['total_mv'])})
        except:
            pass
        time.sleep(0.06)

    df_mv = pd.DataFrame(mv_rows)
    if len(df_mv) == 0:
        print('  NO MV DATA')
        continue

    total_mv_sum = df_mv['total_mv'].sum()
    df_mv['weight'] = df_mv['total_mv'] / total_mv_sum * 100
    df_mv = df_mv.sort_values('weight', ascending=False).reset_index(drop=True)

    cr5 = df_mv.head(5)['weight'].sum()
    cr10 = df_mv.head(10)['weight'].sum()
    top20 = df_mv.head(20)

    print('  CR5=' + str(round(cr5, 1)) + '%, CR10=' + str(round(cr10, 1)) + '%')
    print('  Top5: ' + str(df_mv.head(5)['ts_code'].tolist()))

    # 3. 加权ROE
    roe_sum = 0.0
    weight_sum = 0.0
    for _, row in top20.iterrows():
        try:
            r2 = pro.fina_indicator(ts_code=row['ts_code'], fields='ts_code,end_date,roe', limit=5)
            if r2 is not None and len(r2) > 0:
                annual = r2[r2['end_date'].str.endswith('1231')]
                rec = annual.iloc[0] if len(annual) > 0 else r2.iloc[0]
                roe_val = rec['roe']
                if roe_val is not None and not pd.isna(roe_val) and float(roe_val) > 0:
                    roe_sum += float(roe_val) * float(row['weight'])
                    weight_sum += float(row['weight'])
        except:
            pass
        time.sleep(0.06)

    weighted_roe = roe_sum / weight_sum if weight_sum > 0 else None
    print('  Weighted ROE (top20)=' + str(round(weighted_roe, 1) if weighted_roe else 'N/A') + '%')

    results[ind['lx']] = {
        'name': nm,
        'member_count': len(current),
        'cr5': round(cr5, 1),
        'cr10': round(cr10, 1),
        'weighted_roe': round(weighted_roe, 1) if weighted_roe else None,
        'top5': df_mv.head(5)[['ts_code', 'weight']].to_dict('records'),
    }

print('\n\n=== FINAL RESULTS ===')
print(json.dumps(results, ensure_ascii=False, indent=2))
