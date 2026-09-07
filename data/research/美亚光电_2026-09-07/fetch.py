import sys, json, concurrent.futures
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,r'C:\Users\zephy\.agents\skills\lixinger-query\scripts')
from lixinger_client import query
from scripts.cninfo_api import CninfoClient
OUT=Path(__file__).parent
def save(name,fn):
    try:
        v=fn()
        if hasattr(v,'to_dict'): v=v.to_dict('records')
        (OUT/(name+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        print(name,'完成',len(v) if hasattr(v,'__len__') else '',flush=True)
    except Exception as e: print(name,type(e).__name__,str(e)[:180],flush=True)
c=CninfoClient()
# 签名运行时必须在主线程先初始化，避免并发初始化崩溃。
_ = c.mcode
jobs={
 'announcements':lambda:c.list_announcements('002690',category='',start_date='2023-01-01',end_date='2026-09-07',max_pages=12,page_size=30),
 'valuation':lambda:query('cn/company/fundamental/non_financial',stockCodes=['002690'],date='2026-09-04',metricsList=['pe_ttm','pb','ps_ttm','mc','dyr','pe_ttm.y3.cvpos','pe_ttm.y3.q2v','pe_ttm.y3.q5v','pe_ttm.y3.q8v']),
 'bars':lambda:query('cn/company/candlestick',stockCode='002690',startDate='2026-06-01',endDate='2026-09-07',type='non_restore'),
 'financial':lambda:query('cn/company/fs/non_financial',stockCodes=['002690'],startDate='2021-12-31',endDate='2026-06-30',metricsList=['y.ps.toi.t','y.ps.np.t','y.bs.ta.t','y.bs.tl.t','y.cfs.ncffoa.t','q.ps.toi.t','q.ps.np.t','q.cfs.ncffoa.t']),
 'eastmoney':lambda:requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get',params={'reportName':'RPT_LICO_FN_CPD','columns':'ALL','filter':'(SECURITY_CODE="002690")','pageNumber':1,'pageSize':24,'sortColumns':'REPORTDATE','sortTypes':'-1'},timeout=35).json(),
}
for name,method in [('profile','company_profile'),('trades','executive_trades'),('holders','top10_holders'),('dividends','dividends'),('share_changes','share_changes'),('penalties','company_penalties'),('lawsuits','company_lawsuits'),('pledge','share_pledge'),('freeze','share_freeze'),('irm','irm_qa'),('ratings','investment_ratings')]:
    jobs[name]=lambda method=method:getattr(c,method)('002690')
for endpoint in ['measures','inquiry','dividend','senior-executive-shares-change','major-shareholders-shares-change']:
    jobs['lx_'+endpoint]=lambda endpoint=endpoint:query('cn/company/'+endpoint,stockCode='002690',startDate='2021-01-01',endDate='2026-09-07')
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    list(ex.map(lambda p:save(*p),jobs.items()))
from scripts.tavily_search import _get_client
save('tavily_governance',lambda:_get_client().search('美亚光电 002690 减持 大宗 增持 处罚 诉讼 郭廷超 2026年9月',max_results=8,search_depth='advanced'))
save('tavily_industry',lambda:_get_client().search('美亚光电 色选机 CBCT 2026 竞争 药监 质量 环保 处罚',max_results=6,search_depth='advanced'))
from scripts.wisburg_api import WisburgClient
try:
    w=WisburgClient()
    save('wisburg_calls',lambda:w.search_earnings_calls('美亚光电',first=5))
    save('wisburg_reports',lambda:w.search_company_reports('美亚光电',first=5))
except Exception as e: print('智堡',type(e).__name__)
