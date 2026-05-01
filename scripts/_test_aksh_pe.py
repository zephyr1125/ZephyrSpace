import akshare as ak
import pandas as pd

# 单个测试，避免循环慢
df = ak.stock_zh_index_value_csindex(symbol='399986')
print(f'399986: rows={len(df)}, cols={df.columns.tolist()}')
if len(df):
    print('first row:')
    print(df.iloc[0])
    print('last row:')
    print(df.iloc[-1])
    if '日期' in df.columns:
        print('date range:', df['日期'].min(), '~', df['日期'].max())

