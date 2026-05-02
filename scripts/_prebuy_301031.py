"""Data gathering script for 中熔电气 301031 PreBuy analysis."""
import requests, gzip, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

LX_TOKEN = os.getenv('LIXINGER_TOKEN')
LX_BASE = 'https://open.lixinger.com/api'
HEADERS_LX = {'Accept-Encoding': 'gzip', 'Content-Type': 'application/json'}

def lx_post(path, payload):
    resp = requests.post(f'{LX_BASE}/{path}', 
                         data=json.dumps({**payload, 'token': LX_TOKEN}),
                         headers=HEADERS_LX)
    try:
        raw = gzip.decompress(resp.content)
    except Exception:
        raw = resp.content
    return json.loads(raw)

def em_get(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://data.eastmoney.com/'
    }
    resp = requests.get(url, headers=headers, timeout=20)
    return resp.json()

trade_date = '2026-04-30'
STOCK = '301031'

# ===== Eastmoney Financial Data =====
print('=== 东方财富 财务数据（RPT_LICO_FN_CPD）===')
em_url = (
    'https://datacenter-web.eastmoney.com/api/data/v1/get'
    '?reportName=RPT_LICO_FN_CPD&columns=ALL'
    '&filter=(SECURITY_CODE%3D%22301031%22)'
    '&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=REPORT_DATE'
)
em_data = em_get(em_url)
print(f"EM raw keys: {list(em_data.keys()) if isinstance(em_data, dict) else type(em_data)}")
result_obj = em_data.get('result') if isinstance(em_data, dict) else None
records = (result_obj or {}).get('data', []) if result_obj else []

annual_records = [r for r in records if r.get('QDATE', '').endswith('Q4')]
print(f"年报记录数: {len(annual_records)}")
for r in annual_records[:4]:
    qdate = r.get('QDATE', '')
    toi = r.get('TOTAL_OPERATE_INCOME')
    toi_yoy = r.get('TOTAL_OPERATE_INCOME_YOY')
    np = r.get('PARENT_NETPROFIT')
    np_yoy = r.get('PARENT_NETPROFIT_YOY')
    roe = r.get('WEIGHTAVG_ROE')
    ocf = r.get('JYXJL')
    deduct = r.get('DEDUCT_PARENT_NETPROFIT')
    eps = r.get('BASIC_EPS')
    print(f"  [{qdate}] 营收={toi} 同比={toi_yoy}%  净利={np} 同比={np_yoy}%  扣非净利={deduct}  ROE={roe}%  OCF={ocf}  EPS={eps}")

print()
print("=== 全字段（最新年报）===")
if annual_records:
    r = annual_records[0]
    for k, v in sorted(r.items()):
        if v is not None and v != '' and v != 0:
            print(f"  {k}: {v}")

# ===== Lixinger Fundamental =====
print()
print('=== 理杏仁 估值数据 ===')
fund = lx_post('cn/company/fundamental/non_financial', {
    'stockCodes': [STOCK],
    'date': trade_date,
    'metricsList': ['pe_ttm', 'pb', 'mc', 'dyr',
                    'pe_ttm.y3.cvpos', 'pe_ttm.y3.q2v', 'pe_ttm.y3.q5v', 'pe_ttm.y3.q8v']
})
print(json.dumps(fund, ensure_ascii=False, indent=2))

# ===== Try also quarterly data for latest quarter =====
print()
print('=== 东方财富 最近季报（含Q1）===')
quarterly = [r for r in records if not r.get('QDATE', '').endswith('Q4')]
for r in quarterly[:2]:
    qdate = r.get('QDATE', '')
    toi = r.get('TOTAL_OPERATE_INCOME')
    toi_yoy = r.get('TOTAL_OPERATE_INCOME_YOY')
    np = r.get('PARENT_NETPROFIT')
    np_yoy = r.get('PARENT_NETPROFIT_YOY')
    roe = r.get('WEIGHTAVG_ROE')
    ocf = r.get('JYXJL')
    print(f"  [{qdate}] 营收={toi} 同比={toi_yoy}%  净利={np} 同比={np_yoy}%  ROE={roe}%  OCF={ocf}")
