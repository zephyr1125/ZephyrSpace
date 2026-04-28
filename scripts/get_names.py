import tushare as ts, os, time
from dotenv import load_dotenv
load_dotenv()
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

codes = ['300274.SZ','605117.SH','300750.SZ','300827.SZ','001301.SZ',
         '002850.SZ','002150.SZ','300953.SZ','002518.SZ','300450.SZ','603659.SH']
print("=== 公司名称 ===")
for c in codes:
    r = pro.stock_basic(ts_code=c, fields='ts_code,name,industry')
    if len(r):
        row = r.iloc[0]
        name = row['name']
        ind = row['industry']
        print(f"{c}  {name}  {ind}")
    time.sleep(0.1)

print()
print("=== 603659.SH 市值补查 ===")
r2 = pro.daily_basic(ts_code='603659.SH', fields='ts_code,trade_date,pe_ttm,total_mv,pb')
print(r2.head(3).to_string())
