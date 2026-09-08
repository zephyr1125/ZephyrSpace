import requests, pathlib, concurrent.futures, fitz, json, sys
sys.stdout.reconfigure(encoding='utf-8')
root=pathlib.Path('财报/西高院')
jobs={'2025年年度报告':'https://stockmc.xueqiu.com/202604/688334_20260411_HWCQ.pdf','2026年半年度报告':'https://stockmc.xueqiu.com/202608/688334_20260820_NHEF.pdf','2026募投延期公告':'https://stockmc.xueqiu.com/202606/688334_20260630_BV15.pdf','2026职工董事变更':'https://stockmc.xueqiu.com/202608/688334_20260807_GOAV.pdf'}
def go(item):
 name,url=item
 try:
  r=requests.get(url,timeout=45);r.raise_for_status(); doc=fitz.open(stream=r.content,filetype='pdf')
  assert sum(len(p.get_text()) for p in doc)>500, '下载结果非有效公告正文'
  (root/f'西高院{name}.pdf').write_bytes(r.content)
  text='\n\n'.join(f'## 原文第{i+1}页\n'+p.get_text(sort=True) for i,p in enumerate(doc))
  (root/f'西高院{name}.md').write_text(f'# 西高院{name}\n\n来源：{url}\n\n提取方式：PyMuPDF文本提取，非MinerU。表格以PDF为准。\n\n'+text,encoding='utf-8')
  return name,len(doc),len(text)
 except Exception as e:return name,str(e)
print(list(concurrent.futures.ThreadPoolExecutor(4).map(go,jobs.items())))
pathlib.Path('data/research/688334/2026-09-07/sources.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
