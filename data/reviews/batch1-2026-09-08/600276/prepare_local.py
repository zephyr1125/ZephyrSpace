from pathlib import Path
import json, hashlib, re
ROOT=Path('E:/ObsidianVaults/ZephyrSpace')
BASE=ROOT/'data/reviews/batch1-2026-09-08'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(ticker,name,date,paths,removes,changes,ranges,gaps):
 out=BASE/ticker; out.mkdir(exist_ok=True)
 prep={'company':name,'cutoff':date,'scope':'仅材料准备；未复核、未纠错；删除历史审核轨迹，保留当期事实和原有判断','draft_sources':[],'redactions':[],'evidence_sources':[],'gaps':gaps}
 drafts=[]
 for key,rel in paths.items():
  p=ROOT/rel; ls=p.read_text(encoding='utf-8-sig').splitlines(); result=[]; mapping=[]
  for i,s in enumerate(ls,1):
   if any(a<=i<=b for a,b in removes.get(key,[])):
    prep['redactions'].append({'draft':key,'source':rel,'source_line':i,'original':s,'replacement':'','reason':'历史评分变化、旧版链接或此前复核轨迹'});continue
   new=changes.get(key,{}).get(i,s)
   if new!=s:prep['redactions'].append({'draft':key,'source':rel,'source_line':i,'original':s,'replacement':new,'reason':'仅去除历史修订措辞，保留当前事实推导'})
   result.append(new);mapping.append({'draft_line':len(result),'source_line':i})
  dst=out/f'draft-{key}.md';dst.write_text('\n'.join(result)+'\n',encoding='utf-8');drafts.append(dst.relative_to(ROOT).as_posix())
  prep['draft_sources'].append({'draft':dst.relative_to(ROOT).as_posix(),'source':rel,'source_sha256':sha(p),'prepared_sha256':sha(dst),'line_mapping':mapping})
 evidence=[f'# {name} 原始证据包\n\n证据截止：{date}。以下为本地归档原文逐行节选；行号指向所列源文件，未按初稿结论改写原文。\n']
 if gaps:evidence.append('## 材料可得性\n'+'\n'.join('- '+s for s in gaps)+'\n')
 for rel,rr in ranges:
  p=ROOT/rel;ls=p.read_text(encoding='utf-8-sig').splitlines();rr=[(a,min(b,len(ls))) for a,b in rr]
  prep['evidence_sources'].append({'path':rel,'sha256':sha(p),'ranges':rr})
  for a,b in rr:
   evidence.append(f'\n## 来源：{rel}，L{a}–L{b}\n')
   evidence.extend(f'L{i}: {ls[i-1]}' for i in range(a,b+1))
 ev=out/'evidence.md';ev.write_text('\n'.join(evidence)+'\n',encoding='utf-8')
 manifest={'id':f'batch1-{ticker}','company':name,'cutoff':date,'rules':['data/reviews/batch1-2026-09-08/rules.md'],'evidence':[ev.relative_to(ROOT).as_posix()],'drafts':drafts}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 prep['total_material_characters']=sum(len((ROOT/p).read_text(encoding='utf-8')) for p in [manifest['evidence'][0],*drafts]);prep['evidence_sha256']=sha(ev)
 (out/'preparation.json').write_text(json.dumps(prep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(name,prep['total_material_characters'])
 return prep

if __name__=='__main__':
 paths={'company':'深度分析/恒瑞医药 深度分析 78 2026-08-29.md','management':'管理层档案/恒瑞医药 管理层档案 78 2026-08-29.md','valuation':'估值分析/恒瑞医药 估值分析 2026-08-29.md'}
 original={k:(ROOT/v).read_text(encoding='utf-8-sig').splitlines() for k,v in paths.items()}
 changes={'company':{23:'> ⚠️ 本报告基于 2026-08-19 发布的 2026 年半年度报告（未经审计）。',296:original['company'][295].replace('（较5月版本从"中性偏正"下调）',''),298:original['company'][297].replace('（终审修正）','').replace('而非1/3','')},'management':{129:original['management'][128].replace('，终审修正',''),133:original['management'][132].replace('~~**现金收益贡献有限**~~（终审删除）：','')},'valuation':{64:'> 真正可依赖的输入是：**①forward earnings；②净现金；③对研发平台长期增长的判断**。故收敛为"经营业务 PE + 部分超额净现金"单一核心锚，其余方法全部降为诊断。',103:original['valuation'][102].replace('**终审撤销正式权重**：','').replace('（初稿 45%+15%=60% 实为同一张"盈利增长估值票"）',''),107:original['valuation'][106].replace('初稿',''),108:original['valuation'][107].replace('25%→0','0%'),112:original['valuation'][111].replace('初稿',''),225:original['valuation'][224].split('较初稿')[0]}}
 ranges=[('财报/恒瑞医药/恒瑞医药2025年度报告.md',[(1,350),(900,1300),(1800,2110),(5190,5250)]),('财报/恒瑞医药/恒瑞医药2024年度报告.md',[(1,160)]),('财报/恒瑞医药/恒瑞医药2023年度报告.md',[(1,160)]),('财报/恒瑞医药/恒瑞医药2026第一季度报告.md',[(1,170)])]
 prepare('600276','恒瑞医药','2026-08-29',paths,{'company':[(19,19),(68,79)],'valuation':[(22,22),(149,149)]},changes,ranges,['未找到本地归档的2026年半年度原始报告；已检索财报/恒瑞医药及data/research的文件名和正文，未找到对应原文或原始数据。最新本地经营原文为2026第一季度报告；初稿涉及2026H1、2026年8月行情、券商预测及近期公告的输入未由初稿反向补作证据。'])

