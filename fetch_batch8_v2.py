import requests, gzip, json, os
from dotenv import load_dotenv
from datetime import date, timedelta
import tushare as ts
import traceback

load_dotenv()
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
TS_TOKEN = os.getenv("TUSHARE_TOKEN")

def lx_post(path, payload):
    resp = requests.post(
        f"https://open.lixinger.com/api/{path}",
        json={**payload, "token": LX_TOKEN},
        headers={"Accept-Encoding": "gzip"},
        timeout=30
    )
    try:
        return json.loads(gzip.decompress(resp.content))
    except:
        return resp.json()

# 2026-05-01是劳动节，使用2026-04-30
trade_date = "2026-04-30"
print(f"使用交易日: {trade_date}")

codes = ["000423","601083","002215","000999","002284"]
names = {"000423":"东阿阿胶","601083":"锦江航运","002215":"诺普信","000999":"华润三九","002284":"亚太股份"}

# ====== 批量估值（用2026-04-30）======
print("\n=== 1. 估值数据 ===")
val_resp = lx_post("cn/company/fundamental/non_financial", {
    "stockCodes": codes,
    "date": trade_date,
    "metricsList": ["pe_ttm","pe_ttm.y3.cvpos","pe_ttm.y3.q2v","pe_ttm.y3.q5v","pe_ttm.y3.q8v","pb","mc"]
})
val_dict = {}
if val_resp.get("code") == 1:
    for d in val_resp.get("data", []):
        code = d.get("stockCode")
        val_dict[code] = d
        pe = d.get("pe_ttm") or 0
        pos = d.get("pe_ttm.y3.cvpos") or 0
        q2 = d.get("pe_ttm.y3.q2v") or 0
        q5 = d.get("pe_ttm.y3.q5v") or 0
        q8 = d.get("pe_ttm.y3.q8v") or 0
        pb = d.get("pb") or 0
        mc = d.get("mc") or 0
        print(f"{code} {names.get(code,'')}: PE={pe:.2f}, PE分位={pos:.1f}%, P20={q2:.2f}, P50={q5:.2f}, P80={q8:.2f}, PB={pb:.2f}, MC={mc:.2f}亿")
else:
    print("ERROR:", val_resp)

# ====== 逐只股价 ======
print("\n=== 2. 股价数据 ===")
price_dict = {}
for code in codes:
    r = lx_post("cn/company/candlestick", {
        "stockCode": code,
        "startDate": trade_date,
        "endDate": trade_date,
        "metricsList": ["c"]
    })
    if r.get("code") == 1 and r.get("data"):
        price = r["data"][-1].get("c")
        price_dict[code] = price
        print(f"{code} {names.get(code,'')}: {price} 元")
    else:
        print(f"{code} 股价获取失败: {r.get('message','')}")
        price_dict[code] = None

# ====== Tushare 年报数据（增大limit确保覆盖3年）======
print("\n=== 3. Tushare 年报数据（limit=20）===")
pro = ts.pro_api(TS_TOKEN)
ts_data = {}
ts_codes_list = ["000423.SZ","601083.SH","002215.SZ","000999.SZ","002284.SZ"]

for ts_code in ts_codes_list:
    code = ts_code.split(".")[0]
    print(f"\n--- {ts_code} {names.get(code,'')} ---")
    try:
        df = pro.fina_indicator(ts_code=ts_code,
            fields='ts_code,end_date,roe,netprofit_margin,grossprofit_margin', limit=20)
        annual = df[df['end_date'].str.endswith('1231')].head(4)
        
        df_inc = pro.income(ts_code=ts_code,
            fields='ts_code,end_date,n_income_attr_p,total_revenue', limit=20)
        annual_inc = df_inc[df_inc['end_date'].str.endswith('1231')].head(4)
        
        df_cf = pro.cashflow(ts_code=ts_code,
            fields='ts_code,end_date,n_cashflow_act', limit=20)
        annual_cf = df_cf[df_cf['end_date'].str.endswith('1231')].head(4)
        
        rows = []
        for _, row in annual.iterrows():
            yr = row['end_date'][:4]
            roe = row['roe']
            gpm = row['grossprofit_margin']
            npm = row['netprofit_margin']
            
            inc_row = annual_inc[annual_inc['end_date'].str.startswith(yr)]
            net = inc_row['n_income_attr_p'].values[0]/1e8 if len(inc_row) else None
            rev = inc_row['total_revenue'].values[0]/1e8 if len(inc_row) else None
            
            cf_row = annual_cf[annual_cf['end_date'].str.startswith(yr)]
            ocf = cf_row['n_cashflow_act'].values[0]/1e8 if len(cf_row) else None
            
            ocf_ratio = (ocf/net*100) if (ocf is not None and net is not None and net != 0) else None
            
            rows.append({
                "year": yr, "roe": roe, "gpm": gpm, "npm": npm,
                "net": net, "rev": rev, "ocf": ocf, "ocf_ratio": ocf_ratio
            })
            
            parts = [f"年份={yr}"]
            if roe is not None: parts.append(f"ROE={roe:.1f}%")
            if gpm is not None: parts.append(f"毛利率={gpm:.1f}%")
            if npm is not None: parts.append(f"净利率={npm:.1f}%")
            if net is not None: parts.append(f"净利={net:.2f}亿")
            if rev is not None: parts.append(f"营收={rev:.2f}亿")
            if ocf is not None: parts.append(f"OCF={ocf:.2f}亿")
            if ocf_ratio is not None: parts.append(f"OCF/净利={ocf_ratio:.0f}%")
            print("  " + ", ".join(parts))
        
        ts_data[code] = rows
        
    except Exception as e:
        print(f"  ERROR: {e}")
        ts_data[code] = []

# 保存
result = {
    "trade_date": trade_date,
    "val": val_dict,
    "price": price_dict,
    "ts": ts_data
}
with open("batch8_data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("\n数据保存到 batch8_data.json")
