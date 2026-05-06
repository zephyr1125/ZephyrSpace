"""从东方财富获取工商银行财务数据"""
import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8')

url = (
    'https://datacenter-web.eastmoney.com/api/data/v1/get'
    '?reportName=RPT_LICO_FN_CPD&columns=ALL'
    '&filter=(SECURITY_CODE%3D%22601398%22)'
    '&pageNumber=1&pageSize=8&sortColumns=REPORTDATE&sortTypes=-1'
)
resp = requests.get(url, headers={'Accept-Encoding': 'gzip', 'User-Agent': 'Mozilla/5.0'})
rows = resp.json().get('result', {}).get('data', [])
print(f'共获取{len(rows)}条记录')
print()
for row in rows:
    qdate = row.get('QDATE', '')
    rdate = row.get('REPORTDATE', '')
    isnew = row.get('ISNEW', '')
    rev = row.get('TOTAL_OPERATE_INCOME')
    np_ = row.get('PARENT_NETPROFIT')
    rev_yoy = row.get('YSTZ')
    np_yoy = row.get('SJLTZ')
    roe = row.get('WEIGHTAVG_ROE')
    margin = row.get('XSMLL')
    ocf = row.get('JYXJL')
    print(f'QDATE={qdate}  REPORTDATE={rdate[:10] if rdate else ""}  ISNEW={isnew}')
    print(f'  营业收入={rev}  归母净利={np_}')
    print(f'  营收同比={rev_yoy}%  净利同比={np_yoy}%')
    print(f'  ROE(加权)={roe}%  净利率={margin}%  经营现金流={ocf}')
    print()
