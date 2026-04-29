import tushare as ts, os, time, pandas as pd
from dotenv import load_dotenv
load_dotenv('E:/ObsidianVaults/ZephyrSpace/.env')
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()
code = '601881.SH'

db = pro.daily_basic(ts_code=code, trade_date='20260428',
    fields='ts_code,close,pe_ttm,pb,total_mv,dv_ttm,turnover_rate')
print('=== 行情基本面 ===')
print(db.to_string())

time.sleep(0.15)
hist = pro.daily(ts_code=code, start_date='20250201', end_date='20260428',
    fields='trade_date,open,high,low,close,vol,pct_chg')
print('\n=== 近10日行情 ===')
print(hist.tail(10).to_string())
print('\n=== 近60日高低点 ===')
hist60 = hist.tail(60)
print(f"60日最高: {hist60['high'].max():.2f}, 60日最低: {hist60['low'].min():.2f}")
print(f"近60日均价: {hist60['close'].mean():.2f}")

time.sleep(0.15)
fi = pro.fina_indicator(ts_code=code,
    fields='ts_code,end_date,roe,netprofit_yoy,or_yoy,ocf_to_netprofit,grossprofit_margin', limit=8)
print('\n=== 财务指标 ===')
print(fi.to_string())

time.sleep(0.15)
inc = pro.income(ts_code=code,
    fields='ts_code,end_date,total_revenue,n_income_attr_p', limit=8)
print('\n=== 利润表 ===')
print(inc.to_string())

time.sleep(0.15)
# 资产负债表 - 券商关键指标
bs = pro.balancesheet(ts_code=code,
    fields='ts_code,end_date,total_assets,total_equity', limit=4)
print('\n=== 资产负债表 ===')
print(bs.to_string())

time.sleep(0.15)
# 分红数据
div = pro.dividend(ts_code=code, fields='ts_code,end_date,cash_div_tax,record_date,pay_date', limit=8)
print('\n=== 分红历史 ===')
print(div.to_string())

time.sleep(0.15)
# PB历史分位
pb_hist = pro.daily_basic(ts_code=code, start_date='20210101', end_date='20260428', fields='trade_date,pb,pe_ttm')
pb_hist['month'] = pb_hist['trade_date'].str[:6]
monthly = pb_hist.groupby('month').last()
pb_now = float(db['pb'].iloc[0])
pe_now = float(db['pe_ttm'].iloc[0])
pb_pct = sum(1 for x in monthly['pb'] if x < pb_now) / len(monthly['pb']) * 100
pe_pct = sum(1 for x in monthly['pe_ttm'] if x < pe_now) / len(monthly['pe_ttm']) * 100
print(f'\n=== PB/PE历史分位（近5年月末）===')
print(f'PB={pb_now:.2f}, 近5年分位: {pb_pct:.1f}%')
print(f'PE={pe_now:.1f}, 近5年分位: {pe_pct:.1f}%')
print(f'PB月度样本数: {len(monthly)}')
print(f'PB历史区间: [{monthly["pb"].min():.2f}, {monthly["pb"].max():.2f}]')
print(f'PE历史区间: [{monthly["pe_ttm"].min():.1f}, {monthly["pe_ttm"].max():.1f}]')

time.sleep(0.15)
# 下一财报预告日期
from datetime import datetime
today = datetime.today().strftime('%Y%m%d')
for et, et_name in {'1':'一季报','2':'半年报','3':'三季报','4':'年报'}.items():
    try:
        df = pro.disclosure_date(ts_code=code, end_type=et)
        time.sleep(0.12)
        if df is not None and len(df):
            future = df[df['pre_date'] >= today]
            not_out = future[future['actual_date'].isna() | (future['actual_date'] == '')]
            rows = not_out if len(not_out) > 0 else future
            if len(rows) > 0:
                row = rows.sort_values('pre_date').iloc[0]
                print(f'\n下一财报预告: {row["pre_date"]} {et_name}')
                break
    except Exception as e:
        print(f'disclosure_date error: {e}')
        break

print('\n=== 完成 ===')
