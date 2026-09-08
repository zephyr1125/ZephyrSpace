"""核验两家公司修复稿完整性、历史保护、内部链接及机械公式。"""
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def run():
    errors=[]
    primary_manifest=BASE/'evidence/final-primary-hashes.json'
    if primary_manifest.exists():
        for entry in read(primary_manifest):
            p=ROOT/entry['file']
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:errors.append('终审原件变化：'+entry['file'])
    frozen_count=0
    manifests=list((BASE/'frozen').glob('*/manifest.json'))+list((BASE/'revised-frozen').rglob('manifest.json'))
    for manifest in manifests:
        for entry in read(manifest):
            p=ROOT/entry['frozen']
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:errors.append('冻结初稿变化：'+entry['frozen'])
            frozen_count+=1
    for rel,sha in read(BASE/'historical-hashes.json').items():
        p=ROOT/rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:errors.append('历史报告变化：'+rel)
    delivery=read(BASE/'writer/delivery.json')
    reports=[]
    files=[p for folder in ['01-公司','02-主题','03-国家地区','00-首页','深度分析','管理层档案','估值分析','财报'] for p in (ROOT/folder).rglob('*') if p.is_file()]
    names={p.name for p in files}; stems={p.stem for p in files}
    # 整合前允许链接到同批待落库报告；整合后另行核验发布副本与审核字节一致。
    for c in delivery['companies']:
        for rel in c['report_paths'].values():
            p=Path(rel);names.add(p.name);stems.add(p.stem);stems.add(p.parent.name+'/'+p.stem)
    for c in delivery['companies']:
        if abs(round(c['target_price']*(.68+.14*c['valuation_certainty']),2)-c['buy_price'])>.001:errors.append(c['name']+'买价不符')
        # 固定子项上限防止总分能相加、底层却越界或缺项。
        calc=ROOT/c['calculation_script']
        score_input=calc.with_name(calc.name.replace('-recalculate.py','-revision-inputs.json'))
        score_data=read(score_input)['scores']
        maxima={'A':[3,3,4],'B':[2,4,3,6,5],'C':[6,5,9],'D':[4,5,3,3],'E':[6,5,4,3,2],'F':[6,6,3]}
        company_total=0
        for dimension,limits in maxima.items():
            values=score_data['company'].get(dimension)
            if not isinstance(values,list) or len(values)!=len(limits):
                errors.append(c['name']+dimension+'缺固定子项评分');continue
            if any(not 0<=v<=limit for v,limit in zip(values,limits)):errors.append(c['name']+dimension+'子项越界')
            company_total+=sum(values)
        mgmt=score_data['management']
        mgmt_names=['诚信与透明度','资本配置能力','战略稳定性','对股东友好度','危机处理能力','组织与人才能力','表达清晰度与认知质量']
        mgmt_values=[mgmt.get(name,-1) for name in mgmt_names] if isinstance(mgmt,dict) else mgmt
        mgmt_limits=[20,25,15,15,10,10,5]
        if len(mgmt_values)!=7 or any(not 0<=v<=limit for v,limit in zip(mgmt_values,mgmt_limits)):errors.append(c['name']+'管理层量表越界或缺项')
        if company_total!=c['cScore'] or sum(mgmt_values)!=c['mScore']:errors.append(c['name']+'底层评分与交付总分不符')
        for kind,minimum,score in [('company',150,c['cScore']),('management',150,c['mScore']),('valuation',100,None)]:
            p=ROOT/c['report_paths'][kind]
            if not p.exists():errors.append('缺报告：'+str(p));continue
            text=p.read_text(encoding='utf-8-sig');lines=text.splitlines()
            if len(lines)<minimum:errors.append('篇幅不足：'+str(p))
            if '2026-09-08' not in p.stem:errors.append('文件名日期不符：'+str(p))
            if score is not None and f' {score} ' not in p.stem:errors.append('文件名评分不符：'+str(p))
            for i,line in enumerate(lines):
                if i and re.fullmatch(r'\s*\|[\s|:\-]+\|\s*',line) and line.count('|')!=lines[i-1].count('|'):errors.append(f'表头列数不符：{p.name}:{i+1}')
            for match in re.finditer(r'\[\[([^\]]+)\]\]',text):
                link=match.group(1).split('|')[0].split('#')[0]
                if link and not ((ROOT/link).exists() or (ROOT/(link+'.md')).exists() or link in names or link in stems):errors.append(f'未解析链接：{p.name} → {link}')
            reports.append({'file':str(p.relative_to(ROOT)),'lines':len(lines),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        page=ROOT/c['company_page_source']
        if not page.exists():errors.append('缺公司页：'+str(page))
        else:
            for match in re.finditer(r'\[\[([^\]]+)\]\]',page.read_text(encoding='utf-8-sig')):
                link=match.group(1).split('|')[0].split('#')[0]
                if link and not ((ROOT/link).exists() or (ROOT/(link+'.md')).exists() or link in names or link in stems):errors.append(f'未解析链接：{page.name} → {link}')
    result={'checks_version':2,'errors':errors,'reports':reports,'report_count':len(reports),'frozen_files_checked':frozen_count}
    print(json.dumps(result,ensure_ascii=False,indent=2));return bool(errors)
if __name__=='__main__':raise SystemExit(run())
