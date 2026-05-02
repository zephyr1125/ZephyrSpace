import os
import tushare as ts
from dotenv import load_dotenv
load_dotenv()
pro = ts.pro_api(os.getenv("TUSHARE_TOKEN"))

for ts_code in ["300181.SZ", "002155.SZ", "603092.SH", "002602.SZ"]:
    print(f"--- {ts_code} ---")
    df = pro.income(
        ts_code=ts_code,
        fields="ts_code,end_date,n_income_attr_p,total_revenue",
        limit=20
    )
    annual = df[df["end_date"].str.endswith("1231")].head(4)
    for _, r in annual.iterrows():
        np_val = r.get("n_income_attr_p")
        rev_val = r.get("total_revenue")
        if np_val and rev_val:
            print(f"  {r['end_date']}: 净利润={np_val/1e8:.3f}亿, 营收={rev_val/1e8:.3f}亿")
        else:
            print(f"  {r['end_date']}: no data")
    print()
