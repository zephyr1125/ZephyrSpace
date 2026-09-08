import sys,json,pathlib,concurrent.futures,requests
sys.stdout.reconfigure(encoding='utf-8');sys.path.insert(0,r'C:\Users\zephy\.agents\skills\lixinger-query\scripts')
from lixinger_client import query
root=pathlib.Path('data/research/688334/2026-09-07')
jobs={
'price':('cn/company/candlestick',dict(stockCode='688334',startDate='2026-05-01',endDate='2026-09-07',type='ex_rights')),
'valuation':('cn/company/fundamental/non_financial',dict(stockCodes=['688334','300215','300012'],date='2026-09-07',metricsList=['pe_ttm','pb','ps_ttm','mc','dyr','pe_ttm.y3.cvpos'])),
'fs':('cn/company/fs/non_financial',dict(stockCodes=['688334'],startDate='2021-12-31',endDate='2026-06-30',metricsList=['y.ps.toi.t','y.ps.npatoshopc.t','y.cfs.ncffoa.t','q.bs.ta.t','q.bs.tl.t'])),
'dividend':('cn/company/dividend',dict(stockCode='688334',startDate='2023-01-01',endDate='2026-09-07'))}
def go(item):
 k,(api,p)=item
 try:
  v=query(api,**p);(root/f'{k}.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');return k,str(v)[:1800]
 except Exception as e:return k,str(e)[:500]
print(list(concurrent.futures.ThreadPoolExecutor(4).map(go,jobs.items())))
try:
 r=requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get',params={'reportName':'RPT_LICO_FN_CPD','columns':'ALL','filter':'(SECURITY_CODE="688334")','pageSize':20,'sortColumns':'REPORTDATE','sortTypes':-1},timeout=30).json();(root/'eastmoney.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print('eastmoney',str(r)[:2500])
except Exception as e: print(type(e).__name__)
