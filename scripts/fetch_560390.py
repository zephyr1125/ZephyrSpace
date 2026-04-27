"""
Step 1: 获取电网设备ETF(560390)全量成分股
"""
import tushare as ts, os, time, pandas as pd
from dotenv import load_dotenv
load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

print("=" * 60)
print("方法1：搜索电网相关指数")
print("=" * 60)
for mkt in ['CSI', 'SW', 'SSE', 'SZSE']:
    try:
        r = pro.index_basic(market=mkt)
        if r is not None and 'name' in r.columns:
            hits = r[r['name'].str.contains('电网', na=False)]
            if not hits.empty:
                print(f"[{mkt}]")
                print(hits[['ts_code','name']].to_string())
    except Exception as e:
        print(f"[{mkt}] error: {e}")

print("\n" + "=" * 60)
print("方法2：fund_portfolio 直接尝试ETF代码")
print("=" * 60)
best_stocks = None
for code in ['560390.OF', '560390.SZ', '560390.SH']:
    try:
        h = pro.fund_portfolio(ts_code=code, fields='ts_code,ann_date,end_date,symbol,mkv,amount,stk_mkv_ratio')
        if h is not None and len(h) > 0:
            print(f"\nfund_portfolio {code}: {len(h)} rows, latest end_date={h['end_date'].max()}")
            latest = h['end_date'].max()
            stocks = h[h['end_date']==latest].copy()
            print(f"最新期({latest}) 成分股: {len(stocks)} 只")
            print(stocks[['symbol','stk_mkv_ratio']].sort_values('stk_mkv_ratio', ascending=False).to_string())
            best_stocks = stocks
        else:
            print(f"fund_portfolio {code}: 无数据")
    except Exception as e:
        print(f"fund_portfolio {code}: {e}")

print("\n" + "=" * 60)
print("方法3：index_weight 尝试不同指数代码")
print("=" * 60)
for index_code in ['930680.CSI', '930688.CSI', '930723.CSI', '399396.SZ', '000318.SH', '930966.CSI', '930964.CSI']:
    try:
        df = pro.index_weight(index_code=index_code)
        if df is not None and len(df) > 0:
            latest = df['trade_date'].max()
            stocks = df[df['trade_date']==latest]
            print(f"\n{index_code}: {len(stocks)} 只成分股 (latest: {latest})")
            print(stocks[['con_code','weight']].sort_values('weight', ascending=False).head(10).to_string())
        else:
            print(f"{index_code}: 无数据")
    except Exception as e:
        print(f"{index_code}: {e}")

print("\n" + "=" * 60)
print("方法4：搜索560390相关ETF基础信息")
print("=" * 60)
try:
    f = pro.fund_basic(ts_code='560390.OF')
    if f is not None and len(f):
        print(f.to_string())
except Exception as e:
    print(f"fund_basic 560390.OF: {e}")

try:
    f = pro.fund_basic(market='E', status='L')
    if f is not None and len(f):
        hits = f[f['name'].str.contains('电网', na=False)]
        if not hits.empty:
            print("\n含'电网'的ETF：")
            print(hits[['ts_code','name','benchmark']].to_string())
except Exception as e:
    print(f"fund_basic search: {e}")
