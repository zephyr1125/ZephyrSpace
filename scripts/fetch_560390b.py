import tushare as ts, os, time
from dotenv import load_dotenv
load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# 获取560390.SH所有历史持仓
h = pro.fund_portfolio(ts_code='560390.SH')
print(f'全部持仓记录: {len(h)} rows')
dates = sorted(h['end_date'].unique())
print(f'end_dates: {dates}')
for ed in dates:
    period = h[h['end_date']==ed]
    print(f'\n{ed}: {len(period)} 只')
    print(period[['symbol','stk_mkv_ratio']].sort_values('stk_mkv_ratio', ascending=False).to_string())

print('\n\n申万电网设备成分股')
try:
    r = pro.index_member(index_code='801738.SI')
    print(f'rows: {len(r) if r is not None else 0}')
    if r is not None and len(r):
        print(r.to_string())
except Exception as e:
    print(f'error: {e}')

# 尝试931994.CSI (中证电网设备主题)
print('\n\n中证电网设备主题(931994.CSI)成分股')
try:
    r2 = pro.index_weight(index_code='931994.CSI')
    if r2 is not None and len(r2):
        latest = r2['trade_date'].max()
        stocks = r2[r2['trade_date']==latest]
        print(f'成分股数量: {len(stocks)} (latest: {latest})')
        print(stocks[['con_code','weight']].sort_values('weight', ascending=False).to_string())
    else:
        print('无数据')
except Exception as e:
    print(f'error: {e}')
