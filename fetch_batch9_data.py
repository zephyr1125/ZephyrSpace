"""Batch 9 data fetch: 紫金矿业, 中熔电气, 惠泰医疗, 羚锐制药"""
import requests, gzip, json, os
import tushare as ts
from dotenv import load_dotenv
from datetime import date, timedelta
load_dotenv()

LX_TOKEN = os.getenv('LIXINGER_TOKEN')
TS_TOKEN = os.getenv('TUSHARE_TOKEN')

def lx_post(path, payload):
    resp = requests.post(
        f'https://open.lixinger.com/api/{path}',
        json={**payload, 'token': LX_TOKEN},
        headers={'Accept-Encoding': 'gzip'},
        timeout=30
    )
    try:
        return json.loads(gzip.decompress(resp.content))
    except:
        return resp.json()

# ===== 1. 股价 =====
print("=" * 60)
print("[1] 股价")

# LX for 601899, 688617, 600285
codes_lx = ['601899', '688617', '600285']
prices = {}
for code in codes_lx:
    r = lx_post('cn/company/candlestick', {
        'stockCode': code,
        'startDate': '2026-04-20',
        'endDate': '2026-04-30',
        'granularity': '1d',
        'adjustmentType': 'none',
        'type': 'a'
    })
    data = r.get('data', [])
    if data:
        last = data[0]  # newest first
        price = last.get('close', last.get('c'))
        dt = last.get('date', last.get('t', ''))
        prices[code] = price
        print(f"  {code}: {price} ({str(dt)[:10]})")
    else:
        prices[code] = None
        print(f"  {code}: 无数据 - {r.get('message','')}")

# Tushare for 873527 (北交所)
pro = ts.pro_api(TS_TOKEN)
for start in ['20260430','20260429','20260428','20260425','20260424']:
    df = pro.daily(ts_code='873527.BJ', start_date=start, end_date='20260430')
    if df is not None and not df.empty:
        row = df.iloc[0]
        prices['873527'] = float(row['close'])
        print(f"  873527: {row['close']} ({row['trade_date']})")
        break
else:
    prices['873527'] = None
    print("  873527: 无法获取价格")

# ===== 2. 估值分位 (仅主板+科创板) =====
print("\n[2] 估值分位 (LX)")
fund_dict = {}
r2 = lx_post('cn/company/fundamental/non_financial', {
    'stockCodes': codes_lx,
    'date': '2026-04-30',
    'metricsList': ['pe_ttm','pe_ttm.y3.cvpos','pe_ttm.y3.q2v','pe_ttm.y3.q5v','pe_ttm.y3.q8v','pb','mc']
})
if r2.get('data'):
    for d in r2['data']:
        fund_dict[d['stockCode']] = d
        mc_yi = (d.get('mc') or 0) / 1e8
        cvpos = (d.get('pe_ttm.y3.cvpos') or 0) * 100
        print(f"  {d['stockCode']}: PE={d.get('pe_ttm','N/A')}, PB={d.get('pb','N/A')}, "
              f"MC={mc_yi:.1f}亿, PE_3y分位={cvpos:.1f}%, "
              f"P20={d.get('pe_ttm.y3.q2v','N/A')}, P50={d.get('pe_ttm.y3.q5v','N/A')}, "
              f"P80={d.get('pe_ttm.y3.q8v','N/A')}")
else:
    print(f"  Error: {r2}")

# 873527 估值用 Tushare daily_basic
print("\n[2b] 873527 估值 (Tushare daily_basic)")
for start in ['20260430','20260429','20260428','20260425','20260424','20260423','20260422']:
    df_b = pro.daily_basic(ts_code='873527.BJ', start_date=start, end_date='20260430',
                           fields='ts_code,trade_date,pe_ttm,pb,total_mv,circ_mv')
    if df_b is not None and not df_b.empty:
        row = df_b.iloc[0]
        mc_yuan = float(row['total_mv']) * 1e4 if row['total_mv'] else None  # 万元->元
        fund_dict['873527'] = {
            'pe_ttm': float(row['pe_ttm']) if row['pe_ttm'] and str(row['pe_ttm']) not in ['nan','None'] else None,
            'pb': float(row['pb']) if row['pb'] and str(row['pb']) not in ['nan','None'] else None,
            'mc': mc_yuan
        }
        mc_yi = float(row['total_mv']) / 1e4 if row['total_mv'] else 0
        print(f"  873527: PE={row['pe_ttm']}, PB={row['pb']}, MC={mc_yi:.1f}亿 ({row['trade_date']})")
        break
else:
    print("  873527: 无法获取估值数据")

# ===== 3. 财务指标 (Tushare fina_indicator) =====
print("\n[3] 财务指标 (fina_indicator)")
ts_codes_all = ['601899.SH', '873527.BJ', '688617.SH', '600285.SH']
names = {'601899': '紫金矿业', '873527': '中熔电气', '688617': '惠泰医疗', '600285': '羚锐制药'}
fina_dict = {}
for tsc in ts_codes_all:
    code = tsc.split('.')[0]
    print(f"\n  {tsc} ({names.get(code,'')}):")
    try:
        df = pro.fina_indicator(ts_code=tsc,
            fields='ts_code,end_date,roe,netprofit_margin,grossprofit_margin',
            limit=10)
        annual = df[df['end_date'].str.endswith('1231')].head(3)
        fina_dict[code] = annual.to_dict('records')
        for _, row in annual.iterrows():
            print(f"    {row['end_date']}: ROE={row.get('roe','N/A')}, 毛利率={row.get('grossprofit_margin','N/A')}, 净利率={row.get('netprofit_margin','N/A')}")
    except Exception as e:
        print(f"    Error: {e}")
        fina_dict[code] = []

# ===== 4. 现金流 + 净利润 + 营收 =====
print("\n[4] 现金流 + 净利润 + 营收")
cf_dict = {}
for tsc in ts_codes_all:
    code = tsc.split('.')[0]
    print(f"\n  {tsc}:")
    try:
        df_cf = pro.cashflow(ts_code=tsc, fields='ts_code,end_date,n_cashflow_act', limit=10)
        df_income = pro.income(ts_code=tsc, fields='ts_code,end_date,n_income_attr_p,total_revenue', limit=10)
        annual_cf = df_cf[df_cf['end_date'].str.endswith('1231')].head(3)
        annual_income = df_income[df_income['end_date'].str.endswith('1231')].head(3)
        rows = []
        for _, row in annual_cf.iterrows():
            year = row['end_date'][:4]
            ocf = float(row['n_cashflow_act']) / 1e8 if row['n_cashflow_act'] and str(row['n_cashflow_act']) not in ['nan','None'] else None
            inc_rows = annual_income[annual_income['end_date'].str.startswith(year)]
            if not inc_rows.empty:
                net_raw = inc_rows.iloc[0]['n_income_attr_p']
                rev_raw = inc_rows.iloc[0]['total_revenue']
                net = float(net_raw) / 1e8 if net_raw and str(net_raw) not in ['nan','None'] else None
                rev = float(rev_raw) / 1e8 if rev_raw and str(rev_raw) not in ['nan','None'] else None
            else:
                net = None
                rev = None
            ratio = ocf / net if (ocf is not None and net is not None and net != 0) else None
            rows.append({'year': row['end_date'], 'ocf': ocf, 'net': net, 'rev': rev, 'ratio': ratio})
            ocf_s = f"{ocf:.2f}" if ocf is not None else "N/A"
            net_s = f"{net:.2f}" if net is not None else "N/A"
            rev_s = f"{rev:.2f}" if rev is not None else "N/A"
            ratio_s = f"{ratio:.2f}" if ratio is not None else "N/A"
            print(f"    {row['end_date']}: OCF={ocf_s}亿, 净利={net_s}亿, 营收={rev_s}亿, OCF/净利={ratio_s}")
        cf_dict[code] = rows
    except Exception as e:
        print(f"    Error: {e}")
        cf_dict[code] = []

# ===== Save =====
result = {'prices': prices, 'fund': fund_dict, 'fina': fina_dict, 'cf': cf_dict}
with open('batch9_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\n\n数据已保存到 batch9_data.json")
