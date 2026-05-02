import os
import tushare as ts
from dotenv import load_dotenv
load_dotenv()
pro = ts.pro_api(os.getenv("TUSHARE_TOKEN"))

for ts_code in ["300181.SZ", "002155.SZ"]:
    print(f"--- {ts_code} OCF ---")
    df = pro.cashflow(ts_code=ts_code, fields="ts_code,end_date,n_cashflow_act", limit=20)
    annual = df[df["end_date"].str.endswith("1231")].drop_duplicates("end_date").head(4)
    for _, r in annual.iterrows():
        val = r.get("n_cashflow_act")
        if val:
            print(f"  {r['end_date']}: OCF={val/1e8:.3f}亿")
        else:
            print(f"  {r['end_date']}: no data")
    print()
