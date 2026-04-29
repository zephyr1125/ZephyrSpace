import tushare as ts, os, time, json
from dotenv import load_dotenv
import pandas as pd

load_dotenv(r'E:\ObsidianVaults\ZephyrSpace\.env')
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

codes = ['000651.SZ', '000682.SZ']

for code in codes:
    print(f"\n===== {code} =====")
    time.sleep(0.12)
    
    # 1. 财务指标 (取8期)
    df_fi = pro.fina_indicator(ts_code=code, 
        fields='ts_code,end_date,roe,or_yoy,netprofit_yoy,grossprofit_margin,ocf_to_profit,debt_to_assets,eps', limit=8)
    print("--- fina_indicator (8期) ---")
    print(df_fi[['end_date','roe','or_yoy','netprofit_yoy','grossprofit_margin','ocf_to_profit','debt_to_assets','eps']].to_string())
    time.sleep(0.12)
    
    # 2. 营收净利趋势
    df_inc = pro.income(ts_code=code, start_date='20250101', end_date='20260331',
        fields='ts_code,end_date,revenue,n_income_attr_p')
    print("\n--- income ---")
    print(df_inc.to_string())
    time.sleep(0.12)
    
    # 3. 今日估值
    df_db = pro.daily_basic(ts_code=code, trade_date='20260429',
        fields='ts_code,pe_ttm,pb,total_mv,dv_ttm,turnover_rate')
    print("\n--- daily_basic 20260429 ---")
    print(df_db.to_string())
    time.sleep(0.12)
    
    # 4. 近60日行情
    df_price = pro.daily(ts_code=code, start_date='20260210', end_date='20260429',
        fields='ts_code,trade_date,close,pct_chg,vol')
    print("\n--- daily (近60日) ---")
    print(df_price.head(5).to_string())
    latest_close = df_price.iloc[0]['close'] if len(df_price)>0 else 'N/A'
    min_60 = df_price['close'].min() if len(df_price)>0 else 'N/A'
    max_60 = df_price['close'].max() if len(df_price)>0 else 'N/A'
    print(f"... ({len(df_price)} rows total, latest={latest_close}, 60日区间=[{min_60}, {max_60}])")
    time.sleep(0.12)
    
    # 5. 历史PE/PB (5年月末)
    df_hist = pro.daily_basic(ts_code=code, start_date='20210101', end_date='20260429',
        fields='ts_code,trade_date,pb,pe_ttm')
    df_hist['ym'] = df_hist['trade_date'].str[:6]
    df_month = df_hist.groupby('ym').last().reset_index()
    pe_vals = df_month['pe_ttm'].dropna()
    pb_vals = df_month['pb'].dropna()
    cur_pe = df_db['pe_ttm'].values[0] if len(df_db)>0 else None
    cur_pb = df_db['pb'].values[0] if len(df_db)>0 else None
    if len(pe_vals)>0 and cur_pe:
        pe_pct = (pe_vals < cur_pe).sum() / len(pe_vals) * 100
        print(f"\n--- PE历史分位 ---")
        print(f"当前PE={cur_pe:.2f}x, 5年月末: min={pe_vals.min():.2f}, max={pe_vals.max():.2f}, median={pe_vals.median():.2f}, 分位={pe_pct:.1f}%")
    if len(pb_vals)>0 and cur_pb:
        pb_pct = (pb_vals < cur_pb).sum() / len(pb_vals) * 100
        print(f"当前PB={cur_pb:.2f}x, 5年月末: min={pb_vals.min():.2f}, max={pb_vals.max():.2f}, median={pb_vals.median():.2f}, 分位={pb_pct:.1f}%")
    time.sleep(0.12)
    
    # 6. 现金流
    df_cf = pro.cashflow(ts_code=code, start_date='20240101', end_date='20260331',
        fields='ts_code,end_date,n_cashflow_act')
    print("\n--- cashflow ---")
    print(df_cf.to_string())
    time.sleep(0.12)
    
    # 7. 股权质押
    df_pledge = pro.pledge_stat(ts_code=code, fields='ts_code,end_date,pledge_ratio')
    print("\n--- pledge_stat ---")
    print(df_pledge.head(3).to_string())
    time.sleep(0.12)
    
    # 8. 下一财报日(半年报)
    df_disc = pro.disclosure_date(ts_code=code, end_type='2')
    print("\n--- disclosure_date (半年报) ---")
    print(df_disc.head(3).to_string())
    time.sleep(0.12)

print("\n===== ALL DONE =====")
