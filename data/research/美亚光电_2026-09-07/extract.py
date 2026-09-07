import json,sys,concurrent.futures
from pathlib import Path
import requests,fitz
P=Path(__file__).parent
R=P.parents[2]/'财报'/'美亚光电'
R.mkdir(parents=True,exist_ok=True)
a=json.loads((P/'announcements.json').read_text(encoding='utf-8'))
chosen=[]
for x in a:
    title=x['标题']
    if title in ['2022年年度报告','2023年年度报告','2024年年度报告','2025年年度报告','2026年半年度报告'] or ('2026' in x['发布日期'] and any(w in title for w in ['聘任高级','诉讼','质量回报','权益分派','激励'])) or ('2025' in x['发布日期'] and any(w in title for w in ['高级管理人员辞职','回购注销部分限制性股票的公告'])):
        chosen.append(x)
def fetch(x):
    title=x['标题']; suffix='' if title.endswith('年年度报告') or title.endswith('年半年度报告') else ' '+x['发布日期'][:10]
    pdf=R/('美亚光电'+title+suffix+'.pdf')
    res=requests.get(x['PDF_URL'],timeout=45);res.raise_for_status();pdf.write_bytes(res.content)
    d=fitz.open(pdf)
    txt='# '+title+'\n\n来源：'+x['PDF_URL']+'\n\n提取方式：PyMuPDF 文本提取，非 MinerU；表格需对照原 PDF。\n\n'
    txt+='\n\n'.join('## PDF第'+str(i+1)+'页\n\n'+pg.get_text(sort=True) for i,pg in enumerate(d))
    pdf.with_suffix('.md').write_text(txt,encoding='utf-8')
    print(title,len(d),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(fetch,chosen))
(P/'pdf_sources.json').write_text(json.dumps(chosen,ensure_ascii=False,indent=2),encoding='utf-8')
