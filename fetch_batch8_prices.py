import os, json
from dotenv import load_dotenv
import tushare as ts

load_dotenv()
TS_TOKEN = os.getenv("TUSHARE_TOKEN")
pro = ts.pro_api(TS_TOKEN)

ts_codes = ["000423.SZ","601083.SH","002215.SZ","000999.SZ","002284.SZ"]
names = {"000423":"东阿阿胶","601083":"锦江航运","002215":"诺普信","000999":"华润三九","002284":"亚太股份"}

price_dict = {}
print("=== 获取股价（Tushare）===")
# 尝试不同日期
for ts_code in ts_codes:
    code = ts_code.split(".")[0]
    for start_date in ["20260430","20260429","20260428","20260425"]:
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date="20260430")
        if df is not None and not df.empty:
            row = df.iloc[0]
            price = row['close']
            tdate = row['trade_date']
            price_dict[code] = {"price": price, "date": tdate}
            print(f"{ts_code} {names.get(code,'')}: 收盘价={price}元 ({tdate})")
            break
    else:
        print(f"{ts_code}: 无法获取价格")
        price_dict[code] = None

# 加载现有数据，合并更新
with open("batch8_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 更新价格
data["price_ts"] = price_dict

# 修正MC单位（Lixinger mc是元，转亿）
print("\n=== 市值（转换后，亿）===")
for code, d in data["val"].items():
    mc_raw = d.get("mc", 0)
    mc_yi = mc_raw / 1e8
    d["mc_yi"] = mc_yi
    print(f"{code} {names.get(code,'')}: {mc_yi:.2f}亿")

with open("batch8_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\n完成，更新到 batch8_data.json")
