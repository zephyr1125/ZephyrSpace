"""Get latest prices - try different date ranges"""
import requests, gzip, json, os
from dotenv import load_dotenv
load_dotenv()

LX_TOKEN = os.getenv('LIXINGER_TOKEN')
LX_BASE = 'https://open.lixinger.com/api'

def lx_post(path, payload):
    resp = requests.post(f'{LX_BASE}/{path}', 
        json={**payload, 'token': LX_TOKEN},
        headers={'Accept-Encoding': 'gzip'})
    try:
        if resp.headers.get('Content-Encoding') == 'gzip':
            return json.loads(gzip.decompress(resp.content))
    except: pass
    return resp.json()

# Try 300972 with wider range
r = lx_post('cn/company/candlestick', {
    'stockCode': '300972',
    'startDate': '2026-04-01',
    'endDate': '2026-04-30',
    'adjustmentType': '1',
    'type': 'day'
})
print(f"300972 Apr 2026: {json.dumps(r, ensure_ascii=False)[:500]}")

r2 = lx_post('cn/company/candlestick', {
    'stockCode': '300972',
    'startDate': '2025-12-01',
    'endDate': '2026-01-31',
    'adjustmentType': '1',
    'type': 'day'
})
if r2.get('data'):
    last = r2['data'][-1]
    print(f"Last bar Dec-Jan: {json.dumps(last, ensure_ascii=False)[:200]}")
else:
    print(f"Error: {r2}")

# Check fundamental for market cap to infer price
r3 = lx_post('cn/company/fundamental/non_financial', {
    'stockCodes': ['300972','002379','300573','002847'],
    'date': '2026-04-30',
    'metricsList': ['pe_ttm', 'pb', 'mc']
})
print(f"\nFundamental Apr 30: {json.dumps(r3, ensure_ascii=False)[:800]}")
