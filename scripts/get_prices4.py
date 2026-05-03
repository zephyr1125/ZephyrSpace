"""Get latest prices for all 4 companies - newest first ordering"""
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

companies = [('300972','万辰集团'),('002379','宏桥控股'),('300573','兴齐眼药'),('002847','盐津铺子')]
for code, name in companies:
    r = lx_post('cn/company/candlestick', {
        'stockCode': code,
        'startDate': '2026-03-01',
        'endDate': '2026-04-30',
        'adjustmentType': '1',
        'type': 'day'
    })
    if r.get('data'):
        data = r['data']
        # API returns newest-first
        latest = data[0]
        closes = [x.get('close') for x in data if x.get('close') is not None]
        last_close = latest.get('close')
        last_date = str(latest.get('date', ''))[:10]
        if closes:
            print(f"{name} ({code}): 收盘={last_close} 日期={last_date} 近2月高={max(closes):.2f} 低={min(closes):.2f}")
    else:
        print(f"{name} error: {json.dumps(r)[:200]}")
