import os, sys
os.chdir(r'E:\ObsidianVaults\ZephyrSpace')
from dotenv import load_dotenv
load_dotenv()
import tushare as ts
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 测试 index_dailybasic 接口
for code in ['000300.SH', '000905.SH', '399006.SZ', '000016.SH']:
    try:
        df = pro.index_dailybasic(ts_code=code, start_date='20260420', end_date='20260430',
                                  fields='ts_code,trade_date,pe,pe_ttm,pb')
        print(f'{code}: rows={len(df) if df is not None else 0}')
        if df is not None and len(df):
            print(df.head(3))
    except Exception as e:
        print(f'{code}: ERROR {e}')
    print('---')
