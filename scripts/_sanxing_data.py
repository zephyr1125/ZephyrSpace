"""
三星电气(601567) PreBuy 数据采集脚本
"""
import requests, gzip, json, os, sys
from dotenv import load_dotenv

load_dotenv()
LX_TOKEN = os.getenv('LIXINGER_TOKEN')
LX_BASE = 'https://open.lixinger.com/api'
HEADERS = {'Accept-Encoding': 'gzip', 'Content-Type': 'application/json'}

def lx_post(path, payload):
    resp = requests.post(f'{LX_BASE}/{path}', headers=HEADERS,
                         json={**payload, 'token': LX_TOKEN})
    try:
        data = gzip.decompress(resp.content)
        return json.loads(data)
    except Exception:
        return resp.json()

def em_get(report_name, columns, filter_str, page_size=10):
    url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
    params = {
        'reportName': report_name,
        'columns': columns,
        'pageNumber': '1',
        'pageSize': str(page_size),
        'sortColumns': 'REPORTDATE',
        'sortTypes': '-1',
        'filter': filter_str
    }
    resp = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    result = resp.json()
    if result is None:
        return []
    return (result.get('result') or {}).get('data', [])

TRADE_DATE = '2026-04-30'
CODE = '601567'

# ===== 1. 理杏仁：当前价格 =====
print("=" * 60)
print("1. 当前价格（理杏仁 candlestick）")
candle = lx_post('cn/company/candlestick', {
    'stockCode': CODE,
    'startDate': '2026-04-28',
    'endDate': TRADE_DATE,
    'type': 'lxr_fc_rights'
})
price_data = candle.get('data', [])
if price_data:
    latest = price_data[-1]
    print(f"  日期: {latest['date'][:10]}")
    print(f"  收盘价: {latest['close']}")
    print(f"  涨跌幅: {latest['change']:.2%}")

# ===== 2. 理杏仁：基本面估值 =====
print("\n2. 基本面估值（理杏仁 fundamental）")
fund = lx_post('cn/company/fundamental/non_financial', {
    'stockCodes': [CODE],
    'date': TRADE_DATE,
    'metricsList': ['pe_ttm', 'pb', 'mc', 'dyr',
                    'pe_ttm.y3.cvpos', 'pe_ttm.y3.q2v', 'pe_ttm.y3.q5v', 'pe_ttm.y3.q8v']
})
fdata = fund.get('data', [{}])[0] if fund.get('data') else {}
print(f"  PE TTM: {fdata.get('pe_ttm', 'N/A'):.2f}")
print(f"  PB: {fdata.get('pb', 'N/A'):.4f}")
print(f"  总市值: {fdata.get('mc', 0)/1e8:.2f}亿元")
print(f"  股息率(DYR): {fdata.get('dyr', 0)*100:.2f}%")
print(f"  PE 3年分位: {fdata.get('pe_ttm.y3.cvpos', 'N/A'):.4f}")
print(f"  PE 3年 20%分位 (便宜): {fdata.get('pe_ttm.y3.q2v', 'N/A'):.2f}x")
print(f"  PE 3年 50%分位 (中位): {fdata.get('pe_ttm.y3.q5v', 'N/A'):.2f}x")
print(f"  PE 3年 80%分位 (偏贵): {fdata.get('pe_ttm.y3.q8v', 'N/A'):.2f}x")

# ===== 3. 东方财富：年报综合数据 =====
print("\n3. 年报综合数据（东方财富 RPT_LICO_FN_CPD）")
cols = 'SECUCODE,QDATE,REPORTDATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,KCFJCXSYJLR,WEIGHTAVG_ROE,YSTZ,SJLTZ,XSMLL,MGJYXJJE,BPS,ASSIGNDSCRPT,DEDUCT_BASIC_EPS,BASIC_EPS,ZCFZL'
rows = em_get('RPT_LICO_FN_CPD', cols, f'(SECURITY_CODE="{CODE}")', page_size=10)
annual = [r for r in rows if str(r.get('QDATE', '')).endswith('Q4')]
for r in annual[:4]:
    qdate = r.get('QDATE', '')
    rev = r.get('TOTAL_OPERATE_INCOME')
    np_ = r.get('PARENT_NETPROFIT')
    deduct = r.get('KCFJCXSYJLR')
    roe = r.get('WEIGHTAVG_ROE')
    rev_yoy = r.get('YSTZ')
    np_yoy = r.get('SJLTZ')
    gpm = r.get('XSMLL')
    ocf_ps = r.get('MGJYXJJE')
    bps = r.get('BPS')
    divid = r.get('ASSIGNDSCRPT')
    deduct_eps = r.get('DEDUCT_BASIC_EPS')
    lev = r.get('ZCFZL')
    print(f"\n  [{qdate}]")
    print(f"    营收: {rev/1e8:.2f}亿" if rev else "    营收: N/A")
    print(f"    归母净利润: {np_/1e8:.2f}亿" if np_ else "    归母净利润: N/A")
    print(f"    扣非净利润: {deduct/1e8:.2f}亿" if deduct else "    扣非净利润: N/A")
    print(f"    加权ROE: {roe}%")
    print(f"    营收同比: {rev_yoy}%")
    print(f"    净利同比: {np_yoy}%")
    print(f"    毛利率: {gpm}%")
    print(f"    每股经营现金流: {ocf_ps}")
    print(f"    每股净资产: {bps}")
    print(f"    资产负债率: {lev}%")
    print(f"    分红方案: {divid}")
    print(f"    扣非EPS: {deduct_eps}")

# ===== 4. 东方财富：现金流量表 =====
print("\n4. 现金流量表（东方财富 RPT_DMSK_FN_CASHFLOW）")
cf_cols = 'SECUCODE,REPORT_DATE,NETCASH_OPERATE,NETCASH_INVEST,NETCASH_FINANCE,CCE_ADD,SALES_SERVICES'
cf_rows = em_get('RPT_DMSK_FN_CASHFLOW', cf_cols, f'(SECURITY_CODE="{CODE}")', page_size=20)
annual_cf = [r for r in cf_rows if str(r.get('REPORT_DATE', '')).endswith('12-31 00:00:00')][:4]
for r in annual_cf:
    rdate = str(r.get('REPORT_DATE', ''))[:10]
    ocf = r.get('NETCASH_OPERATE')
    print(f"  {rdate}: 经营现金流={ocf/1e8:.2f}亿" if ocf else f"  {rdate}: 经营现金流=N/A")

# ===== 5. 东方财富：资产负债表（获取负债率）=====
print("\n5. 资产负债表（东方财富 RPT_DMSK_FN_BALANCE）")
bs_cols = 'SECUCODE,REPORT_DATE,TOTAL_ASSETS,TOTAL_LIABILITIES,TOTAL_EQUITY_ATSOPC'
bs_rows = em_get('RPT_DMSK_FN_BALANCE', bs_cols, f'(SECURITY_CODE="{CODE}")', page_size=20)
annual_bs = [r for r in bs_rows if str(r.get('REPORT_DATE', '')).endswith('12-31 00:00:00')][:4]
for r in annual_bs:
    rdate = str(r.get('REPORT_DATE', ''))[:10]
    ta = r.get('TOTAL_ASSETS')
    tl = r.get('TOTAL_LIABILITIES')
    eq = r.get('TOTAL_EQUITY_ATSOPC')
    if ta and tl:
        print(f"  {rdate}: 总资产={ta/1e8:.1f}亿, 总负债={tl/1e8:.1f}亿, 净资产={eq/1e8:.1f}亿, 负债率={tl/ta*100:.1f}%")
    else:
        print(f"  {rdate}: data unavailable")

print("\n完成")
