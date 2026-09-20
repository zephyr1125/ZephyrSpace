"""仅串行迁移本次已验收的安踏记录，保持其他条目内容和文件排版。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
CODE = '02020.HK'


def load_file(path):
    raw = path.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    return text, json.loads(text), bom


def entry_spans(text):
    start = text.index('[', text.index('"entries"')) + 1
    decoder = json.JSONDecoder()
    spans = []
    pos = start
    while True:
        while text[pos].isspace() or text[pos] == ',':
            pos += 1
        if text[pos] == ']':
            return spans, pos
        value, end = decoder.raw_decode(text, pos)
        spans.append((pos, end, value))
        pos = end


def main():
    acceptance = json.loads((RUN / 'acceptance.json').read_text(encoding='utf-8-sig'))
    assert acceptance['dual_targeted_review_passed'] is True
    assert acceptance['company_and_index_completed'] is True
    params = json.loads((RUN / 'final-parameters.json').read_text(encoding='utf-8-sig'))
    assert params['watchlistLevel'] == 'B_GROWTH'
    core_path = ROOT / 'data/watchlist_core.json'
    growth_path = ROOT / 'data/watchlist_growth.json'
    core_text, core, core_bom = load_file(core_path)
    growth_text, growth, growth_bom = load_file(growth_path)
    matches = [e for e in core['entries'] if e['code'] == CODE]
    assert len(matches) == 1 and not any(e['code'] == CODE for e in growth['entries'])
    entry = dict(matches[0])
    entry.update(cScore=params['cScore'], mScore=params['mScore'],
                 target_price=params['target_price'], valuation_certainty=params['valuation_certainty'],
                 watchlistLevel='B_GROWTH', strategicCoreType=None,
                 next_earnings_date=None, next_earnings_type=None,
                 lastEarningsIncorporated='2026H1',
                 lastFundamentalReviewDate='2026-09-14', lastRedFlagReviewDate='2026-09-14',
                 dv_ttm=None)
    # 股息率未在本轮重建可靠TTM桥，清空旧值，不把旧时点3.3%冒充当前值。
    spans, _ = entry_spans(core_text)
    idx = next(i for i, (_, _, e) in enumerate(spans) if e['code'] == CODE)
    start, end, _ = spans[idx]
    if idx + 1 < len(spans):
        next_start = spans[idx + 1][0]
        core_new = core_text[:start] + core_text[next_start:]
    else:
        previous_end = spans[idx - 1][1]
        core_new = core_text[:previous_end] + core_text[end:]
    growth_spans, _ = entry_spans(growth_text)
    last_end = growth_spans[-1][1]
    newline = '\r\n' if '\r\n' in growth_text else '\n'
    encoded = json.dumps(entry, ensure_ascii=False, indent=2)
    encoded = newline.join('    ' + line for line in encoded.splitlines())
    growth_new = growth_text[:last_end] + ',' + newline + encoded + growth_text[last_end:]
    new_core, new_growth = json.loads(core_new), json.loads(growth_new)
    assert new_core['entries'] == [e for e in core['entries'] if e['code'] != CODE]
    assert new_growth['entries'] == growth['entries'] + [entry]
    assert {k: v for k, v in core.items() if k != 'entries'} == {k: v for k, v in new_core.items() if k != 'entries'}
    assert {k: v for k, v in growth.items() if k != 'entries'} == {k: v for k, v in new_growth.items() if k != 'entries'}
    # 写前再检查磁盘快照，避免覆盖其他任务在期间写入的改动。
    assert load_file(core_path)[0] == core_text and load_file(growth_path)[0] == growth_text
    (RUN / 'watchlist-before.json').write_text(json.dumps({'core_entry': matches[0], 'growth_entry': None}, ensure_ascii=False, indent=2), encoding='utf-8')
    core_path.write_bytes((b'\xef\xbb\xbf' if core_bom else b'') + core_new.encode('utf-8'))
    growth_path.write_bytes((b'\xef\xbb\xbf' if growth_bom else b'') + growth_new.encode('utf-8'))
    (RUN / 'watchlist-reviewed-row.json').write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding='utf-8')
    print('安踏已从core迁移至growth；其他条目及顶层元数据保持原值。')


if __name__ == '__main__':
    main()
