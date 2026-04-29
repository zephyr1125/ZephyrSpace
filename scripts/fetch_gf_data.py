import tushare as ts, os, time, pandas as pd
from dotenv import load_dotenv
load_dotenv('E:/ObsidianVaults/ZephyrSpace/.env')
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()
code = '000776.SZ'

db = pro.daily_basic(ts_code=code, trade_date='20260428',
    fields='ts_code,close,pe_ttm,pb,total_mv,dv_ttm,turnover_rate')
print('行情:', db.to_string())

hist = pro.daily(ts_code=code, start_date='20250201', end_date='20260428',
    fields='trade_date,open,high,low,close,vol,pct_chg')
print('近期行情(最近10日):')
print(hist.tail(10).to_string())
print('60日最高:', hist['high'].max(), '60日最低:', hist['low'].min())

fi = pro.fina_indicator(ts_code=code,
    fields='ts_code,end_date,roe,netprofit_yoy,or_yoy,ocf_to_netprofit,grossprofit_margin', limit=8)
print('财务指标:', fi.to_string())

inc = pro.income(ts_code=code,
    fields='ts_code,end_date,total_revenue,n_income_attr_p', limit=8)
print('利润表:', inc.to_string())

from datetime import datetime
today = datetime.today().strftime('%Y%m%d')
for et, et_name in {'1':'一季报','2':'半年报','3':'三季报','4':'年报'}.items():
    df = pro.disclosure_date(ts_code=code, end_type=et)
    time.sleep(0.12)
    if df is not None and len(df):
        future = df[df['pre_date'] >= today]
        not_out = future[future['actual_date'].isna() | (future['actual_date'] == '')]
        rows = not_out if len(not_out) > 0 else future
        if len(rows) > 0:
            row = rows.sort_values('pre_date').iloc[0]
            print(f'下一财报: {row["pre_date"]} {et_name}')
            break

pb_hist = pro.daily_basic(ts_code=code, start_date='20210101', end_date='20260428', fields='trade_date,pb')
pb_hist['month'] = pb_hist['trade_date'].str[:6]
monthly = pb_hist.groupby('month').last()
pb_now = float(db['pb'].iloc[0])
pct = sum(1 for x in monthly['pb'] if x < pb_now) / len(monthly['pb']) * 100
print(f'PB={pb_now:.2f}, 近5年分位: {pct:.1f}%')
print(f'PB历史范围: min={monthly["pb"].min():.2f}, max={monthly["pb"].max():.2f}, median={monthly["pb"].median():.2f}')
