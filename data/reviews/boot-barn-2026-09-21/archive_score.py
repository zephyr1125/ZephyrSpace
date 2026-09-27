"""归档本轮已批准评分；不将未获批准估值转换为正式研究。"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path('data/reviews/boot-barn-2026-09-21')
OUT = ROOT / RUN / 'final'

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    decision = read(RUN / 'decision.json')
    assert decision['score_state'] == 'approved'
    assert decision['research_state'] != 'approved'
    score = RUN / 'repair-v2/workpaper.json'
    assert digest((ROOT / score).read_bytes()) == '3566ee92416c4738bc164db64ad4f46e1b2778c727d71e63fd025a01afd73516'
    check = read(RUN / 'repair-v2/check.json')
    files = {str(score), str(RUN / 'repair-v2/check.json'), str(RUN / 'repair-v2/receipt.json'),
             str(RUN / 'repair-v2/acceptance.md'), str(RUN / 'delta-repair-v2.json'),
             str(RUN / 'decision.json'), str(RUN / 'decision-closeout.json'),
             str(RUN / 'score-rules.md'), 'deep-prebuy-skill/SKILL.md',
             'management-archive/SKILL.md', 'docs/three-report-closeout.md',
             'data/WATCHLIST_RULES.md', 'data/WATCHLIST_SCHEMA.md'}
    for path, expected in check['inputs'].items():
        assert digest((ROOT / path).read_bytes()) == expected, path
        files.add(path)
    for name in ('review-facts-score.json', 'review-reasoning-score.json',
                 'review-facts-score-recheck.json', 'review-reasoning-score-recheck.json',
                 'review-facts-score-exception.json', 'review-reasoning-score-exception.json',
                 'review-facts-full.json', 'review-reasoning-full.json',
                 'review-facts-delivery-closeout.json', 'delivery-closeout.md',
                 'frozen-integrity-closeout.json'):
        files.add(str(RUN / name))
    # 官方原件已在财报或本轮来源目录保留；记录哈希，不复制同一大文件。
    originals = {}
    def visit(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ('path', 'file', 'local_path') and isinstance(value, str):
                    p = ROOT / value
                    if p.is_file():
                        originals[value] = digest(p.read_bytes())
                elif isinstance(value, (dict, list)):
                    visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    for path in check['inputs']:
        visit(read(path))
    assert not (OUT / 'score-package.json').exists()
    (OUT / 'inputs').mkdir(parents=True, exist_ok=True)
    entries = {}
    for i, path in enumerate(sorted(files)):
        raw = (ROOT / path).read_bytes()
        target = Path('inputs') / f'{i:03d}-{Path(path).name}'
        (OUT / target).write_bytes(raw)
        entries[path] = {'archive': target.as_posix(), 'sha256': digest(raw)}
    packet = {'schema_version': 1, 'company': 'Boot Barn', 'code': 'BOOT.US',
              'cutoff': '2026-09-21', 'score_state': 'approved',
              'company_score': 80, 'management_score': 79, 'combined_score': 159,
              'score_gate_candidate': 'B_GROWTH', 'research_status': 'execution_incomplete',
              'valuation_state': 'not_approved', 'target_price': None,
              'valuation_certainty': None, 'buy_price': None, 'publish_allowed': False,
              'files': entries, 'originals_retained_with_hash': originals,
              'scope': '仅归档已批准评分及其独立验收；不是完整三件套发布验收包，不授权Watchlist回写。'}
    (OUT / 'score-package.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for entry in entries.values():
        assert digest((OUT / entry['archive']).read_bytes()) == entry['sha256']
    print(json.dumps({'status': 'score_package_verified', 'snapshots': len(entries), 'originals': len(originals)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
