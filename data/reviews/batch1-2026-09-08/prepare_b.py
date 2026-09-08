from pathlib import Path
import json, hashlib, re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('data/reviews/batch1-2026-09-08')

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def prepare(code, name, date, scores, ranges, replacements):
    out = ROOT / BASE / code
    out.mkdir(parents=True, exist_ok=True)
    logs = []
    drafts = []
    originals = []
    for folder, suffix, score in zip(['深度分析', '管理层档案', '估值分析'], ['company', 'management', 'valuation'], scores):
        source = Path(folder) / f'{name} {folder}{" " + str(score) if score else ""} {date}.md'
        raw = (ROOT/source).read_text(encoding='utf-8')
        lines = raw.splitlines()
        kept = []
        tail = False
        for n, line in enumerate(lines, 1):
            old = line
            if line.startswith('## 与 2026-07-12 版差异'):
                tail = True
            if tail or line.startswith(('更新说明:', '复核调整:', '复核日期:')):
                line = None
            else:
                for before, after in replacements:
                    line = line.replace(before, after)
            if old != line:
                logs.append({'source': source.as_posix(), 'source_line': n, 'before': old, 'after': line, 'reason': '移除历史修订轨迹、旧评分比较或此前复核归因；保留当期事实与推导'})
            if line is not None:
                kept.append(line)
        result = '\n'.join(kept)+'\n'
        target = BASE/code/f'draft-{suffix}.md'
        (ROOT/target).write_text(result, encoding='utf-8')
        drafts.append(target.as_posix())
        originals.append({'path':source.as_posix(),'sha256':sha(raw),'draft_sha256':sha(result),'original_lines':len(lines),'draft_lines':len(kept)})
    source = Path('财报')/name/f'{name}2026半年度报告.md'
    raw = (ROOT/source).read_text(encoding='utf-8')
    lines = raw.splitlines()
    gaps = ['本地财报目录仅发现2026半年度报告转换稿；data/research文本及文件名检索未发现本公司独立原始资料。三年完整年度经营及历史治理材料、截止日行情与历史估值序列的独立原始证据缺失；不以三件套初稿补充事实。半年报内比较期间可用于有限周期对照。']
    evidence = f'# {name} 原始证据节选\n\n证据截止日：{date}。以下仅逐行复制本地财报转换稿，L 为原文件一基行号，未更正转换文本或补写事实。\n\n材料缺口：{gaps[0]}\n'
    for start,end in ranges:
        evidence += f'\n## 来源：{source.as_posix()}，原文 L{start}–L{end}\n\n'
        evidence += '\n'.join(f'L{i}: {lines[i-1]}' for i in range(start,end+1))+'\n'
    ep = BASE/code/'evidence.md'
    (ROOT/ep).write_text(evidence, encoding='utf-8')
    manifest = {'id':f'batch1-{code}','company':name,'cutoff':date,'rules':[(BASE/'rules.md').as_posix()],'evidence':[ep.as_posix()],'drafts':drafts}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    chars = len(evidence)+sum(len((ROOT/p).read_text(encoding='utf-8')) for p in drafts)
    prep = {'company':name,'cutoff':date,'role':'仅材料准备，未进行复核或纠错','draft_sources':originals,'draft_edits':logs,'evidence_sources':[{'path':source.as_posix(),'sha256':sha(raw),'ranges':ranges}],'evidence_sha256':sha(evidence),'material_gaps':gaps,'characters_evidence_and_drafts':chars,'search_scope':['财报/'+name,'data/research（文件名与文本内公司名/股票代码）'],'api_called':False}
    (out/'preparation.json').write_text(json.dumps(prep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(name,chars,'chars',len(logs),'edits',out)

if __name__ == '__main__':
    import sys
    if sys.argv[1] == '688111':
        prepare('688111','金山办公','2026-08-22',[82,81,None],[(1,1042),(2400,2424),(3008,3251),(3460,3596),(3900,4362)], [
            ('（非此前误判2.5万股）',''),('（非此前误判的2.5万股，利益绑定修正）',''),
            ('（重大修正）',''),('（修正）',''),('497.9万股修正','497.9万股'),
            ('> ⚠️ **重大修正**：此前档案误判"章庆元持股仅2.5万股（约570万市值）"，实际','> '),
            ('——此前档案误判为"2.5万股"，利益绑定判断需彻底修正。','。'),
            ('，非此前判断的"弱"',''),('，修正此前误判',''),
            ('，此前"CEO持股极少"的判断基于错误数据（2.5万股），需彻底修正',''),
            ('，治理质量优于此前判断',''),
            ('（终审指出）',''),
            ('，较上期0.60下调0.05',''),
            ('。不低于0.50，因主营业务可预测性显著强于此前0.50档案例（亚朵/中信特钢）。','。'),
        ])
    else:
        prepare('600036','招商银行','2026-08-28',[84,82,None],[(1,1307),(1499,1913),(1982,2177)], [
            ('，较 2026-07-12 版（82）上调 2 分',''),
            ('与上次持平：',''),('与上次持平，',''),('较上次 +1：',''),
            ('从 5 下调：',''),('，从 2 下调',''),('，从 3 下调',''),
            ('监管罚单记录较此前掌握更完整','监管罚单记录'),('监管记录较此前掌握更完整','监管记录'),
            ('内部重平衡：E1 因 ROAE 长期下行 -1、E5.5 因半年报本无 KAM +1、E5 因零售资产质量恶化维持 1','E1 因 ROAE 长期下行、E5.5 因半年报本无 KAM、E5 因零售资产质量恶化'),
            ('> ⚠️ **本轮新增（2026-08-28 更新）**：通过 Tavily（T0 限额 1 次）发现此前档案遗漏的','> 通过 Tavily 获取的'),
            ('历史修复记录：2026-07-12 版曾复核维持 81 分；本轮因半年报数据 + 新增监管记录 + 换届落地重新评估为 82 分。',''),
            ('方法论修正（删除逆向 DCF 正式权重）后 target 不变，是稳健性检验通过。',''),
        ])
