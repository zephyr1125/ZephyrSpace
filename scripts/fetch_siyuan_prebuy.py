"""
思源电气 PreBuy 数据抓取脚本
"""
import requests, json, os, sys
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('LIXINGER_TOKEN')
BASE = 'https://open.lixinger.com/api'

def lx_post(path, payload):
    r = requests.post(BASE + '/' + path, json=dict(token=TOKEN, **payload),
                      headers={'Accept-Encoding': 'gzip'})
    return r.json()

def eastmoney_financials(code6):
    url = (
        'https://datacenter-web.eastmoney.com/api/data/v1/get'
        '?reportName=RPT_LICO_FN_CPD&columns=ALL'
        f'&filter=(SECURITY_CODE%3D%22{code6}%22)'
        '&pageNumber=1&pageSize=6'
    )
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    return r.json()

# === 1. Price ===
trade_date = '2026-04-30'
r = lx_post('cn/company/candlestick', {
    'stockCode': '002028',
    'startDate': trade_date,
    'endDate': trade_date,
    'type': 'lxr_fc_rights'
})
price_data = r.get('data', [])
if price_data:
    close = price_data[0]['close']
    print(f"[价格] {trade_date} 收盘价: {close} 元")
else:
    print("[价格] 无数据")

# === 2. Fundamental ===
r2 = lx_post('cn/company/fundamental/non_financial', {
    'stockCodes': ['002028'],
    'date': trade_date,
    'metricsList': ['pe_ttm', 'pb', 'mc', 'dyr',
                    'pe_ttm.y3.cvpos', 'pe_ttm.y3.q2v', 'pe_ttm.y3.q5v', 'pe_ttm.y3.q8v']
})
fund = r2.get('data', [{}])[0]
mc_yi = round(fund.get('mc', 0) / 1e8, 1)
print(f"[估值] PE TTM: {fund.get('pe_ttm'):.2f}x, PB: {fund.get('pb'):.2f}x, 市值: {mc_yi}亿")
print(f"[股息率] {fund.get('dyr', 0)*100:.2f}%")
print(f"[PE分位] 3年历史分位: {fund.get('pe_ttm.y3.cvpos', 0)*100:.1f}%")
print(f"[PE分位] Q2(中位数): {fund.get('pe_ttm.y3.q2v'):.1f}x, Q5: {fund.get('pe_ttm.y3.q5v'):.1f}x, Q8: {fund.get('pe_ttm.y3.q8v'):.1f}x")

# === 3. Eastmoney Financials ===
em = eastmoney_financials('002028')
rows = em.get('result', {}).get('data', [])
print(f"\n[东方财富] 共 {len(rows)} 期财报")
for row in rows:
    rd = (row.get('REPORT_DATE') or '')[:10]
    qdate = row.get('QDATE', '')
    rev = row.get('TOTAL_OPERATE_INCOME')
    netprofit = row.get('PARENT_NETPROFIT')
    deduct = row.get('DEDUCT_PARENT_NETPROFIT')
    ocf = row.get('JYXJL')
    roe = row.get('WEIGHTAVG_ROE')
    rev_yoy = row.get('TOTAL_OPERATE_INCOME_YOY')
    np_yoy = row.get('PARENT_NETPROFIT_YOY')
    goodwill = row.get('GOODWILL')
    
    def yi(v):
        if v is None: return 'N/A'
        return f"{float(v)/1e8:.2f}亿"
    def pct(v):
        if v is None: return 'N/A'
        return f"{float(v)*100:.1f}%"
    
    print(f"\n  {rd} ({qdate}):")
    print(f"    营收={yi(rev)}, 同比={pct(rev_yoy)}")
    print(f"    归母净利={yi(netprofit)}, 同比={pct(np_yoy)}")
    print(f"    扣非归母净利={yi(deduct)}")
    print(f"    OCF={yi(ocf)}")
    print(f"    加权ROE={roe}%")
    print(f"    商誉={yi(goodwill)}")
    if netprofit and ocf:
        ratio = float(ocf) / float(netprofit)
        print(f"    OCF/净利={ratio:.1%}")
