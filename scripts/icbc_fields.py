"""获取工商银行东方财富全部字段"""
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

url = (
    'https://datacenter-web.eastmoney.com/api/data/v1/get'
    '?reportName=RPT_LICO_FN_CPD&columns=ALL'
    '&filter=(SECURITY_CODE%3D%22601398%22)'
    '&pageNumber=1&pageSize=2&sortColumns=REPORTDATE&sortTypes=-1'
)
resp = requests.get(url, headers={'Accept-Encoding': 'gzip', 'User-Agent': 'Mozilla/5.0'})
result = resp.json().get('result') or {}
rows = result.get('data') or []
if not rows:
    print('No data')
    print(resp.text[:500])
else:
    row = rows[0]
    print(f'QDATE={row.get("QDATE")}')
    print('全部非空字段:')
    for k, v in row.items():
        if v is not None:
            print(f'  {k}: {v}')
