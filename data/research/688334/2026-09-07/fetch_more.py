import requests,pathlib,fitz,json,concurrent.futures,sys
sys.stdout.reconfigure(encoding='utf-8')
r=pathlib.Path('财报/西高院'); jobs={'2026年半年度报告':'https://stockmc.xueqiu.com/202608/688334_20260820_NHEF.pdf','2026募投延期公告':'https://stockmc.xueqiu.com/202606/688334_20260630_BV15.pdf','2026职工董事变更':'https://stockmc.xueqiu.com/202608/688334_20260807_GOAV.pdf'}
def go(item):
 n,u=item
 try:
  z=requests.get(u,timeout=40);d=fitz.open(stream=z.content,filetype='pdf');t='\n\n'.join(f'## 原文第{i+1}页\n'+p.get_text(sort=True) for i,p in enumerate(d));assert len(t)>500
  (r/f'西高院{n}.pdf').write_bytes(z.content);(r/f'西高院{n}.md').write_text(f'# 西高院{n}\n来源：{u}\n提取：PyMuPDF，非MinerU；表格以PDF为准。\n'+t,encoding='utf-8');return n,len(d)
 except Exception as e:return n,str(e)
print(list(concurrent.futures.ThreadPoolExecutor(3).map(go,jobs.items())))
from scripts.tavily_search import _get_client
v=_get_client().search('西高院 688334 减持 增持 处罚 诉讼 管理层变更 2026年9月',max_results=8,search_depth='advanced')
pathlib.Path('data/research/688334/2026-09-07/tavily.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');print([(x['title'],x['url'],x['content'][:600]) for x in v.get('results',[])])
