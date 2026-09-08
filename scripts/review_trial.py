"""冻结配对试验材料、匿名化意见；揭盲后统计已裁决缺陷覆盖。"""
import argparse
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    if path.exists():
        raise ValueError(f'不覆盖试验留档：{path.name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def freeze(manifests, output, root=ROOT):
    files = {}
    for manifest in manifests:
        config = read(manifest)
        paths = [str(Path(manifest).resolve().relative_to(root.resolve()))]
        paths += [p for role in ('rules', 'evidence', 'drafts') for p in config[role]]
        for relative in paths:
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError('材料超出工作区')
            files[path.relative_to(root.resolve()).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(output, {'files': files})


def verify(path, root=ROOT):
    for relative, expected in read(path)['files'].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f'冻结材料发生变化：{relative}')


def anonymize(sources, output, rng=None):
    # 仅保留判断本身，不传作者、运行目录、模型、用量与输出文件名。
    rows = []
    for reviewer, path in sources.items():
        data = read(path)
        result = data.get('result', data)
        for index, finding in enumerate(result['findings']):
            rows.append((reviewer, index, {k: finding[k] for k in
                         ('severity', 'location', 'claim', 'evidence', 'impact', 'recommendation')}))
    (rng or random.SystemRandom()).shuffle(rows)
    candidates, mapping = [], {}
    for index, (reviewer, original_index, finding) in enumerate(rows, 1):
        item_id = f'C{index:03}'
        candidates.append({'id': item_id, **finding})
        mapping[item_id] = {'reviewer': reviewer, 'original_index': original_index}
    output = Path(output)
    write(output / 'candidates.json', candidates)
    write(output / 'unblinding.json', mapping)


def metrics(candidates, judgments, mapping, supplemental=()):
    ids = {x['id'] for x in candidates}
    judged_ids = [x['id'] for x in judgments]
    if len(set(judged_ids)) != len(judged_ids) or set(judged_ids) != ids or set(mapping) != ids:
        raise ValueError('裁决或来源映射遗漏、重复或含未知条目')
    reviewers = ['codex_a', 'codex_b', 'flash']
    result = {r: {'proposed': 0, 'outcomes': {}, 'defects': [],
                  'correction_claims': 0, 'fully_valid_corrections': 0,
                  'invalid_corrections': 0} for r in reviewers}
    groups = {}
    for item in judgments:
        outcome = item['outcome']
        if outcome not in ('valid', 'partial', 'invalid', 'insufficient', 'non_defect'):
            raise ValueError('未知裁决类型')
        reviewer = mapping[item['id']]['reviewer']
        row = result[reviewer]
        row['proposed'] += 1
        row['outcomes'][outcome] = row['outcomes'].get(outcome, 0) + 1
        if item.get('is_correction', item['kind'] == 'error'):
            row['correction_claims'] += 1
            if outcome == 'valid' and item['kind'] == 'error':
                row['fully_valid_corrections'] += 1
            if outcome == 'invalid':
                row['invalid_corrections'] += 1
        if outcome in ('valid', 'partial') and item['kind'] == 'error':
            group, severity = item['group'], item['severity']
            if not group or severity not in ('P0', 'P1', 'P2'):
                raise ValueError('成立缺陷缺少分组或有效级别')
            if group in groups and groups[group]['severity'] != severity:
                raise ValueError('同组缺陷级别不一致')
            groups.setdefault(group, {'severity': severity, 'reviewers': []})
            groups[group]['reviewers'].append(reviewer)
            row['defects'].append(group)
    # 复合候选可覆盖多个缺陷，但提出条数及纠错成立率仍仅计一次。
    by_id = {x['id']: x for x in judgments}
    for item in supplemental:
        original = by_id.get(item['id'])
        if not original or original['outcome'] not in ('valid', 'partial') or original['kind'] != 'error':
            raise ValueError('附加分组必须来自成立纠错')
        group, severity = item['group'], item['severity']
        if not group or severity not in ('P0', 'P1', 'P2'):
            raise ValueError('附加分组缺少有效组或级别')
        if group in groups and groups[group]['severity'] != severity:
            raise ValueError('附加分组级别不一致')
        reviewer = mapping[item['id']]['reviewer']
        groups.setdefault(group, {'severity': severity, 'reviewers': []})
        groups[group]['reviewers'].append(reviewer)
        result[reviewer]['defects'].append(group)
    for row in result.values():
        row['defects'] = sorted(set(row['defects']))
        row['strict_valid_rate'] = (row['fully_valid_corrections'] / row['correction_claims']
                                    if row['correction_claims'] else None)
    combinations = {}
    for label, members in [('codex_pair', ['codex_a', 'codex_b']),
                           ('a_flash', ['codex_a', 'flash']), ('b_flash', ['codex_b', 'flash'])]:
        found = {g for g, value in groups.items() if set(value['reviewers']) & set(members)}
        combinations[label] = {'found': sorted(found),
                               'missed': {g: v['severity'] for g, v in groups.items() if g not in found}}
    return {'reviewers': result, 'confirmed_union': groups, 'combinations': combinations,
            'note': '缺陷集合仅为已提议并核实的并集，部分成立只计被认可的错误部分，不代表穷尽真值。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('freeze'); p.add_argument('output'); p.add_argument('manifests', nargs='+')
    p = sub.add_parser('verify'); p.add_argument('freeze_file')
    p = sub.add_parser('anonymize'); p.add_argument('sources'); p.add_argument('output')
    p = sub.add_parser('metrics'); p.add_argument('directory')
    args = parser.parse_args()
    if args.command == 'freeze':
        freeze(args.manifests, args.output)
    elif args.command == 'verify':
        verify(args.freeze_file)
    elif args.command == 'anonymize':
        anonymize(read(args.sources), args.output)
    else:
        path = Path(args.directory)
        suffix = '-final' if (path / 'candidates-final.json').exists() else ''
        extra = path / 'supplemental-groups.json'
        write(path / 'metrics.json', metrics(read(path / f'candidates{suffix}.json'),
              read(path / f'judgments{suffix}.json'), read(path / 'unblinding.json'),
              read(extra) if extra.exists() else []))
    print('完成：' + args.command)


if __name__ == '__main__':
    main()
