import json,sys
from pathlib import Path
import requests,fitz
P=Path(__file__).parent; R=P.parents[2]/'财报'/'美亚光电'
sys.path.insert(0,r'C:\Users\zephy\.agents\skills\lixinger-query\scripts')
from lixinger_client import query
d=query('cn/company/fundamental/non_financial',stockCodes=['002690'],date='2026-09-07',metricsList=['pe_ttm','pb','ps_ttm','mc','dyr','pe_ttm.y3.cvpos','pe_ttm.y3.q2v','pe_ttm.y3.q5v','pe_ttm.y3.q8v'])
(P/'valuation_latest.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
a=json.loads((P/'announcements.json').read_text(encoding='utf-8'))
items=[(x['标题']+' '+x['发布日期'][:10],x['PDF_URL']) for x in a if ('2026' in x['发布日期'] and any(w in x['标题'] for w in ['投资者关系活动','财务预算','完成独立董事'])) or (('2024年年度报告' not in x['标题']) and '2025-03-27' in x['发布日期'] and x['标题']=='关于回购注销部分限制性股票的公告')]
items += [('2021年关注函','https://reportdocs.static.szse.cn/UpFiles/fxklwxhj/LSD002690166225.pdf')]
for name,url in items:
 try:
  res=requests.get(url,timeout=30);res.raise_for_status();pdf=R/('美亚光电'+name+'.pdf');pdf.write_bytes(res.content)
  doc=fitz.open(pdf);txt='# '+name+'\n来源：'+url+'\n提取方式：PyMuPDF，非 MinerU。\n'+'\n'.join('\n## PDF第'+str(i+1)+'页\n'+page.get_text(sort=True) for i,page in enumerate(doc))
  pdf.with_suffix('.md').write_text(txt,encoding='utf-8');print(name,len(doc))
 except Exception as e: print(name,type(e).__name__)
