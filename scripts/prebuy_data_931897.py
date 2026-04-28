"""拉取931897候选11家公司完整财务数据"""
import tushare as ts, os, time, json
from dotenv import load_dotenv

load_dotenv(r"E:\ObsidianVaults\ZephyrSpace\.env")
ts.set_token(os.getenv("TUSHARE_TOKEN"))
pro = ts.pro_api()

TRADE_DATE = "20260427"

candidates = [
    ("600023.SH", "浙能电力"),
    ("600098.SH", "广州发展"),
    ("600642.SH", "申能股份"),
    ("600795.SH", "国电电力"),
    ("600027.SH", "华电国际"),
    ("600863.SH", "内蒙华电"),
    ("600011.SH", "华能国际"),
    ("600483.SH", "福能股份"),
    ("000690.SZ", "宝新能源"),
    ("600900.SH", "长江电力"),
    ("600886.SH", "国投电力"),
]

result = {}
for code, name in candidates:
    print(f"处理 {name}({code})...")
    data = {"code": code, "name": name}
    
    # daily_basic：价格/PE/PB/市值/DY
    r = pro.daily_basic(ts_code=code, trade_date=TRADE_DATE,
                        fields="ts_code,close,pe_ttm,pb,total_mv,dv_ttm,turnover_rate")
    if len(r):
        row = r.iloc[0]
        data.update({
            "close": row.get("close"), "pe_ttm": round(row.get("pe_ttm") or 0, 2),
            "pb": round(row.get("pb") or 0, 2),
            "total_mv_yi": round((row.get("total_mv") or 0)/10000, 1),
            "dv_ttm": round(row.get("dv_ttm") or 0, 2),
            "turnover_rate": round(row.get("turnover_rate") or 0, 2),
        })
    time.sleep(0.12)
    
    # 60日高低
    hist = pro.daily(ts_code=code, fields="ts_code,trade_date,high,low,close,vol", limit=60)
    if len(hist):
        data["high_60"] = round(hist["high"].max(), 2)
        data["low_60"] = round(hist["low"].min(), 2)
        curr = data.get("close") or hist["close"].iloc[0]
        data["pct_from_high"] = round((curr - data["high_60"]) / data["high_60"] * 100, 1)
    time.sleep(0.12)
    
    # fina_indicator：ROE/营收/净利/现金流（年报优先）
    fi = pro.fina_indicator(ts_code=code,
        fields="ts_code,end_date,roe,or_yoy,netprofit_yoy,dt_netprofit_yoy,ocfps,eps",
        limit=6)
    if len(fi):
        annual = fi[fi["end_date"].str.endswith("1231")]
        row = annual.iloc[0] if len(annual) else fi.iloc[0]
        data.update({
            "roe": round(row.get("roe") or 0, 2),
            "or_yoy": round(row.get("or_yoy") or 0, 1),
            "netprofit_yoy": round(row.get("netprofit_yoy") or 0, 1),
            "dt_netprofit_yoy": round(row.get("dt_netprofit_yoy") or 0, 1),
            "fina_end_date": row.get("end_date"),
            "ocfps": row.get("ocfps"),
            "eps": row.get("eps"),
        })
    time.sleep(0.12)
    
    # income：营收/净利（最近年报）
    inc = pro.income(ts_code=code, fields="ts_code,end_date,total_revenue,n_income_attr_p", limit=4)
    if len(inc):
        ann_inc = inc[inc["end_date"].str.endswith("1231")]
        if len(ann_inc):
            row = ann_inc.iloc[0]
            data["revenue_yi"] = round((row.get("total_revenue") or 0)/1e8, 2)
            data["net_profit_yi"] = round((row.get("n_income_attr_p") or 0)/1e8, 2)
    time.sleep(0.12)
    
    # cashflow：OCF
    cf = pro.cashflow(ts_code=code, fields="ts_code,end_date,n_cashflow_act", limit=4)
    if len(cf):
        ann_cf = cf[cf["end_date"].str.endswith("1231")]
        if len(ann_cf):
            row = ann_cf.iloc[0]
            ocf = (row.get("n_cashflow_act") or 0)/1e8
            data["ocf_yi"] = round(ocf, 2)
            np = data.get("net_profit_yi") or 0
            data["ocf_ratio"] = round(ocf/np, 2) if np and np > 0 else None
    time.sleep(0.12)
    
    # 商誉
    bs = pro.balancesheet(ts_code=code, fields="ts_code,end_date,goodwill,total_hldr_eqy_exc_min_int", limit=4)
    if len(bs):
        ann_bs = bs[bs["end_date"].str.endswith("1231")]
        if len(ann_bs):
            row = ann_bs.iloc[0]
            gw = (row.get("goodwill") or 0)/1e8
            eq = (row.get("total_hldr_eqy_exc_min_int") or 0)/1e8
            data["goodwill_yi"] = round(gw, 2)
            data["equity_yi"] = round(eq, 2)
            data["gw_ratio"] = round(gw/eq*100, 1) if eq > 0 else 0
    time.sleep(0.12)
    
    # 下一财报日
    from datetime import datetime
    today = datetime.today().strftime("%Y%m%d")
    end_types = {"1": "一季报", "2": "半年报", "3": "三季报", "4": "年报"}
    candidates_earn = []
    for et, et_name in end_types.items():
        df_d = pro.disclosure_date(ts_code=code, end_type=et)
        time.sleep(0.12)
        if df_d is None or len(df_d) == 0:
            continue
        future = df_d[df_d["pre_date"] >= today]
        not_out = future[future["actual_date"].isna() | (future["actual_date"] == "")]
        rows = not_out if len(not_out) > 0 else future
        if len(rows):
            row = rows.sort_values("pre_date").iloc[0]
            candidates_earn.append({"pre_date": row["pre_date"], "type": et_name})
    if candidates_earn:
        candidates_earn.sort(key=lambda x: x["pre_date"])
        best = candidates_earn[0]
        data["next_earnings_date"] = f"{best['pre_date'][:4]}-{best['pre_date'][4:6]}-{best['pre_date'][6:]}"
        data["next_earnings_type"] = best["type"]
    else:
        data["next_earnings_date"] = "2026-08-31（估算）"
        data["next_earnings_type"] = "半年报"
    
    result[code] = data
    print(f"  close={data.get('close')} pe={data.get('pe_ttm')} dv={data.get('dv_ttm')}% roe={data.get('roe')}% next={data.get('next_earnings_date')}")

with open(r"E:\ObsidianVaults\ZephyrSpace\data\prebuy_931897_data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\n保存完成: data/prebuy_931897_data.json")
