"""核验本批历史保护、缺陷映射、报告完整性、公式与链接；不修改研究文件。"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from review_trial import verify


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def run():
    errors = []
    for relative, expected in read(BASE / 'historical-hashes.json').items():
        path = ROOT / relative
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append('历史报告发生变化：' + relative)
    verify(ROOT / 'data/reviews/batch1-2026-09-08/freeze.json')
    expected = read(BASE / 'expected-defects.json')
    all_files = [p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts]
    names = {p.name for p in all_files}
    stems = {p.stem for p in all_files if p.suffix == '.md'}
    reports = []
    for ticker, groups in expected.items():
        path = BASE / ticker / 'repair-summary.json'
        if not path.exists():
            errors.append('缺修复清单：' + ticker)
            continue
        summary = read(path)
        paths = summary.get('new_paths') or summary.get('new_reports') or summary.get('new')
        if isinstance(paths, dict):
            paths = [paths[k] for k in ('company', 'management', 'valuation')]
        if not paths or len(paths) != 3:
            errors.append('三件套路径不完整：' + ticker)
            continue
        for reviewer in ('a', 'b'):
            final_path = BASE / ticker / f'review-{reviewer}-final.json'
            if not final_path.exists():
                errors.append('缺最终复核：' + str(final_path))
                continue
            final = read(final_path)
            if final.get('pass') is not True:
                errors.append('最终复核未通过：' + str(final_path))
            closure = {r.get('group', r.get('id')) for r in final.get('coverage', []) if r.get('status') == 'closed'}
            if closure != set(groups):
                errors.append('最终复核缺陷未闭环：' + str(final_path))
            hashes = final.get('file_sha256', {})
            normalized = {k.replace('\\', '/'): v for k, v in hashes.items()}
            required = paths + [summary['company_page']]
            for relative in required:
                relative = relative.replace('\\', '/')
                reviewed = ROOT / relative
                if not reviewed.exists() or normalized.get(relative) != hashlib.sha256(reviewed.read_bytes()).hexdigest():
                    errors.append(f'最终复核哈希未覆盖当前文件：{reviewer} {relative}')
        covered = {r.get('group', r.get('id')) for r in summary['repairs']}
        if covered != set(groups):
            errors.append(f'{ticker}缺陷映射差异：{covered ^ set(groups)}')
        target, certainty = summary['target_price'], summary['valuation_certainty']
        if abs(round(target * (.68 + .14 * certainty), 2) - summary['buy_price']) > .001:
            errors.append('机械买价不一致：' + ticker)
        for index, relative in enumerate(paths):
            p = ROOT / relative
            if not p.exists():
                errors.append('新版文件不存在：' + relative)
                continue
            text = p.read_text(encoding='utf-8-sig')
            lines = text.splitlines()
            if len(lines) < [150, 150, 100][index]:
                errors.append('篇幅不合格：' + relative)
            if '2026-09-08' not in p.stem:
                errors.append('新版日期不符：' + relative)
            if index < 2 and f" {summary[['cScore', 'mScore'][index]]} " not in p.stem:
                errors.append('文件名评分不符：' + relative)
            if not re.search(r'\[\[01-公司/' + re.escape(summary['company']), text):
                errors.append('缺公司页链接：' + relative)
            for i, line in enumerate(lines):
                if i and re.fullmatch(r'\s*\|[\s|:\-]+\|\s*', line):
                    if line.count('|') != lines[i - 1].count('|'):
                        errors.append(f'表头列数不符：{relative}:{i + 1}')
            for match in re.finditer(r'\[\[([^\]]+)\]\]', text):
                link = match.group(1).split('|')[0].split('#')[0]
                if not link:
                    continue
                resolved = (ROOT / link).exists() or (ROOT / (link + '.md')).exists()
                resolved |= (p.parent / link).exists() or (p.parent / (link + '.md')).exists()
                resolved |= link in names or link in stems
                if not resolved:
                    errors.append(f'未解析链接：{relative} -> {link}')
            reports.append({'file': relative, 'lines': len(lines)})
    result = {'errors': errors, 'reports': reports, 'report_count': len(reports)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(run())
