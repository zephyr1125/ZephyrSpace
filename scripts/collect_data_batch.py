"""一次性拉取4家公司的理杏仁+Tushare数据，输出JSON供后续分析用"""
import requests, gzip, json, os, sys
from dotenv import load_dotenv
from datetime import date, timedelta
import tushare as ts

load_dotenv()
LX_TOKEN = os.getenv('LIXINGER_TOKEN')
LX_BASE = 'https://open.lixinger.com/api'

def lx_post(path, payload):
    resp = requests.post(
        f'{LX_BASE}/{path}',
        json={**payload, 'token': LX_TOKEN},
        headers={'Accept-Encoding': 'gzip'}
    )
    try:
        if resp.headers.get('Content-Encoding') == 'gzip':
            return json.loads(gzip.decompress(resp.content))
    except Exception:
        pass
    return resp.json()

def last_trade_day():
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()

trade_date = last_trade_day()
last_annual_end = f"{date.today().year - 1}-12-31"

print(f"Trade date: {trade_date}")
print(f"Last annual end: {last_annual_end}")

COMPANIES = [
    ("万辰集团", "300972", "300972.SZ"),
    ("宏桥控股", "002379", "002379.SZ"),
    ("兴齐眼药", "300573", "300573.SZ"),
    ("盐津铺子", "002847", "002847.SZ"),
]

results = {}

for name, pure_code, ts_code in COMPANIES:
    print(f"\n{'='*50}")
    print(f"=== {name} ({pure_code}) ===")
    r = {"name": name, "pure_code": pure_code, "ts_code": ts_code}

    # 1. 估值 + PE历史分位
    val_resp = lx_post("cn/company/fundamental/non_financial", {
        "stockCodes": [pure_code],
        "date": trade_date,
        "metricsList": ["pe_ttm", "pb", "mc", "pe_ttm.y3.cvpos",
                        "pe_ttm.y3.q2v", "pe_ttm.y3.q5v", "pe_ttm.y3.q8v"]
    })
    val_data = val_resp.get("data", [{}])[0] if val_resp.get("data") else {}
    r["pe_ttm"] = val_data.get("pe_ttm")
    r["pb"] = val_data.get("pb")
    r["mc"] = val_data.get("mc")
    r["pe_3yr_pos"] = val_data.get("pe_ttm.y3.cvpos")
    r["pe_p20"] = val_data.get("pe_ttm.y3.q2v")
    r["pe_p50"] = val_data.get("pe_ttm.y3.q5v")
    r["pe_p80"] = val_data.get("pe_ttm.y3.q8v")
    print(f"  PE: {r['pe_ttm']}, PB: {r['pb']}, MC: {r['mc']}亿")
    print(f"  PE 3yr分位: {r['pe_3yr_pos']}, P20: {r['pe_p20']}, P50: {r['pe_p50']}, P80: {r['pe_p80']}")

    # 2. 近期股价（K线）
    candle_resp = lx_post("cn/company/candlestick", {
        "stockCode": pure_code,
        "startDate": (date.today() - timedelta(days=90)).isoformat(),
        "endDate": trade_date,
        "adjustmentType": "1"
    })
    candle_data = candle_resp.get("data", [])
    if candle_data:
        last_bar = candle_data[-1]
        r["last_price"] = last_bar.get("c")
        r["price_date"] = last_bar.get("d", "")[:10]
        prices = [x["c"] for x in candle_data if x.get("c")]
        r["price_90d_high"] = max(prices)
        r["price_90d_low"] = min(prices)
        print(f"  最新价: {r['last_price']} ({r['price_date']})")
        print(f"  近90日高/低: {r['price_90d_high']:.2f} / {r['price_90d_low']:.2f}")
    else:
        print(f"  candle error: {candle_resp}")

    # 3. 分红历史
    div_resp = lx_post("cn/company/dividend", {
        "stockCode": pure_code,
        "startDate": "2022-01-01",
        "endDate": trade_date,
    })
    divs = div_resp.get("data", [])
    r["dividends"] = divs[:5]
    print(f"  分红记录数: {len(divs)}")
    for dv in divs[:3]:
        print(f"    {dv.get('date','')[:10]} 每股派息: {dv.get('dividend')}")

    # 4. 股权质押
    pledge_resp = lx_post("cn/company/pledge", {
        "stockCode": pure_code,
        "startDate": "2023-01-01",
        "endDate": trade_date,
    })
    all_pledges = pledge_resp.get("data", [])
    active = [p for p in all_pledges if not p.get("pledgeDischargeDate")]
    r["pledge_active_count"] = len(active)
    r["pledge_active"] = active[:5]
    print(f"  活跃质押: {len(active)}条")

    # 5. 高管增减持
    exec_resp = lx_post("cn/company/senior-executive-shares-change", {
        "stockCode": pure_code,
        "startDate": "2024-07-01",
        "endDate": trade_date,
    })
    changes = exec_resp.get("data", [])
    r["exec_changes"] = changes[:10]
    buys = [x for x in changes if x.get("changeType") == "increase"]
    sells = [x for x in changes if x.get("changeType") == "decrease"]
    r["exec_buy_count"] = len(buys)
    r["exec_sell_count"] = len(sells)
    print(f"  高管增减持 (近~1年): 增{len(buys)} 减{len(sells)}")

    results[name] = r

# Tushare 数据
print("\n=== Tushare财务数据 ===")
pro = ts.pro_api(os.getenv("TUSHARE_TOKEN"))

for name, pure_code, ts_code in COMPANIES:
    print(f"\n--- {name} ---")
    r = results[name]

    # 财务指标
    try:
        fi = pro.fina_indicator(
            ts_code=ts_code,
            fields="ts_code,end_date,roe,roa,grossprofit_margin,netprofit_margin,ocf_to_profit,debt_to_assets,current_ratio",
            limit=10
        )
        annual_fi = fi[fi["end_date"].str.endswith("1231")].head(3)
        r["fina_indicator"] = annual_fi.to_dict("records")
        print(f"  财务指标: {annual_fi[['end_date','roe','roa','grossprofit_margin','netprofit_margin','ocf_to_profit']].to_string()}")
    except Exception as e:
        print(f"  fina_indicator error: {e}")

    # 利润表
    try:
        income = pro.income(
            ts_code=ts_code,
            fields="ts_code,end_date,total_revenue,n_income_attr_p,ebit",
            limit=8
        )
        annual_inc = income[income["end_date"].str.endswith("1231")].head(3)
        r["income"] = annual_inc.to_dict("records")
        print(f"  利润表: {annual_inc[['end_date','total_revenue','n_income_attr_p']].to_string()}")
    except Exception as e:
        print(f"  income error: {e}")

    # 现金流
    try:
        cf = pro.cashflow(
            ts_code=ts_code,
            fields="ts_code,end_date,n_cashflow_act,n_cashflow_inv_act,free_cashflow",
            limit=6
        )
        annual_cf = cf[cf["end_date"].str.endswith("1231")].head(3)
        r["cashflow"] = annual_cf.to_dict("records")
        print(f"  现金流: {annual_cf[['end_date','n_cashflow_act','free_cashflow']].to_string()}")
    except Exception as e:
        print(f"  cashflow error: {e}")

    # 资产负债表
    try:
        bs = pro.balancesheet(
            ts_code=ts_code,
            fields="ts_code,end_date,total_assets,total_liab,money_cap,st_borr,lt_borr,goodwill",
            limit=6
        )
        annual_bs = bs[bs["end_date"].str.endswith("1231")].head(3)
        r["balance"] = annual_bs.to_dict("records")
        print(f"  资产负债: {annual_bs[['end_date','total_assets','total_liab','goodwill']].to_string()}")
    except Exception as e:
        print(f"  balancesheet error: {e}")

print("\n=== 所有数据收集完成，输出JSON ===")
print(json.dumps(results, ensure_ascii=False, default=str, indent=2))
