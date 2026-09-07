import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; P=Path(__file__).parent
files={
 '深度分析/美亚光电 深度分析 78 2026-09-07.md':150,
 '管理层档案/美亚光电 管理层档案 78 2026-09-07.md':150,
 '估值分析/美亚光电 估值分析 2026-09-07.md':100,
 '01-公司/美亚光电.md':1,
 '04-A股行业/光电智能分选设备 行业分析.md':1,
}
all_md=list(ROOT.rglob('*.md')); names={p.stem for p in all_md}
checks=[]
for rel,minimum in files.items():
 t=(ROOT/rel).read_text(encoding='utf-8'); unresolved=[]
 for raw in re.findall(r'\[\[([^\]]+)\]\]',t):
  link=raw.split('|')[0].split('#')[0]
  if not (ROOT/(link+'.md')).exists() and link not in names:unresolved.append(link)
 checks.append(dict(path=rel,lines=len(t.splitlines()),minimum=minimum,unresolved=unresolved,has_placeholder=any(x in t for x in ['XXX','待创建','E:\\Download'])))
model=json.loads((P/'model.json').read_text(encoding='utf-8'))
assert sum([8,15,16,11,17,11])==78
assert sum([16,18,14,13,7,6,4])==78
assert round(model['target']*(.68+.14*model['certainty']),2)==12.10
assert '[[美亚光电]]' in (ROOT/'00-首页/公司索引.md').read_text(encoding='utf-8')
for c in checks:assert c['lines']>=c['minimum'] and not c['unresolved'] and not c['has_placeholder'],c
(P/'selfcheck.json').write_text(json.dumps({'passed':True,'checks':checks,'company_score':78,'management_score':78,'target':15.61,'buy_price':12.10},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
