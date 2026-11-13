"""刷新美股质量价值研究候选；缺失条件不会被视为通过。"""
from __future__ import annotations

import csv
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from argparse import ArgumentParser

import yfinance as yf
from tigeropen.common.consts import Market
from tigeropen.common.consts.filter_fields import StockField
from tigeropen.quote.domain.filter import StockFilter
from us_mispricing_screen import _tiger_client, number, linear, ROOT


def write_csv(path, rows):
    if not rows:
        path.write_text('代码\n', encoding='utf-8-sig')
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def value(frame, names, column=0):
    for name in names:
        if name in frame.index and len(frame.columns) > column:
            return number(frame.loc[name].iloc[column])
    return float('nan')


def ratio(a, b):
    return a / b if math.isfinite(a) and math.isfinite(b) and b > 0 else float('nan')


def cagr(frame, names):
    # 按真实报告日期计算可得周期，不冒充五年增长率。
    if len(frame.columns) < 2:
        return float('nan'), 0
    valid = [n for n in range(len(frame.columns)) if math.isfinite(value(frame, names, n))]
    if len(valid) < 2:
        return float('nan'), 0
    frame = frame.iloc[:, valid]
    n = len(frame.columns) - 1
    years = (frame.columns[0] - frame.columns[n]).days / 365.25
    a, b = value(frame, names), value(frame, names, n)
    return ((a / b) ** (1 / years) - 1) * 100 if a > 0 and b > 0 and years > 0 else float('nan'), round(years, 2)


def supplement(row):
    t = yf.Ticker(row['代码'])
    i = t.info or {}
    row.update({'公司名': i.get('longName', ''), '行业': i.get('industry', ''), '板块': i.get('sector', ''),
                '币种': i.get('currency', ''), '财报币种': i.get('financialCurrency', ''), '证券类型': i.get('quoteType', ''),
                'Yahoo价格': i.get('currentPrice', ''), 'Yahoo市值': i.get('marketCap', ''),
                'Yahoo52周高点': i.get('fiftyTwoWeekHigh', ''), 'Yahoo_PE': i.get('trailingPE', ''),
                '行情时间戳': i.get('regularMarketTime', '')})
    industry = row['行业'].lower()
    if row['证券类型'] != 'EQUITY' or row['币种'] != 'USD' or not row['公司名']:
        row['分组'] = '隔离：证券身份或币种未核实'
        return row
    if row['板块'] == 'Financial Services' or any(s in industry for s in ['reit', 'mortgage', 'business development']):
        row['分组'] = '排除：金融/REIT/BDC'
        return row
    if row['板块'] == 'Energy' or any(s in industry for s in ['mining', 'coal', 'fertilizer', 'agricultural inputs', 'aluminum', 'steel', 'copper', 'gold', 'silver']):
        row['分组'] = '资源独立池'
    elif any(s in industry for s in ['marine shipping']):
        row['分组'] = '航运独立池'
    else:
        row['分组'] = '普通经营公司'
    income, cash, balance = t.income_stmt, t.cashflow, t.balance_sheet
    revenue = value(income, ['Total Revenue'])
    ni = value(income, ['Net Income', 'Net Income Common Stockholders'])
    assets = value(balance, ['Total Assets'])
    equity = value(balance, ['Stockholders Equity', 'Common Stock Equity'])
    old_equity = value(balance, ['Stockholders Equity', 'Common Stock Equity'], 1)
    ocf = value(cash, ['Operating Cash Flow'])
    capex = value(cash, ['Capital Expenditure'])
    fcf = ocf - abs(capex) if math.isfinite(ocf) and math.isfinite(capex) else float('nan')
    rev_cagr, years = cagr(income, ['Total Revenue'])
    ni_cagr, _ = cagr(income, ['Net Income', 'Net Income Common Stockholders'])
    row.update({'年报期': str(income.columns[0].date()) if len(income.columns) else '',
                '资产负债表期': str(balance.columns[0].date()) if len(balance.columns) else '',
                '现金流报表期': str(cash.columns[0].date()) if len(cash.columns) else '',
                '可得增长年数': years, '营收可得周期CAGR_%': rev_cagr, '净利可得周期CAGR_%': ni_cagr,
                '毛利率_%': 100 * ratio(value(income, ['Gross Profit']), revenue),
                '营业利润率_%': 100 * ratio(value(income, ['Operating Income']), revenue),
                'ROE_%': 100 * ratio(ni, (equity + old_equity) / 2),
                '资产负债率_%': 100 * ratio(value(balance, ['Total Liabilities Net Minority Interest']), assets),
                'OCF': ocf, 'Capex': capex, 'FCF': fcf, 'FCF净利比': ratio(fcf, ni)})
    q = t.quarterly_income_stmt
    row['最新季度期'] = str(q.columns[0].date()) if len(q.columns) else ''
    # 只接受同季同比，不能把相邻季度当作同比。
    prior = next((n for n in range(1, len(q.columns)) if 350 <= (q.columns[0] - q.columns[n]).days <= 380), None) if len(q.columns) else None
    for label, names in [('季度营收同比_%', ['Total Revenue']), ('季度净利同比_%', ['Net Income', 'Net Income Common Stockholders'])]:
        row[label] = (ratio(value(q, names), value(q, names, prior)) - 1) * 100 if prior is not None else float('nan')
    missing = ['五年营收及净利CAGR（可得周期不足五年）'] if years < 4.9 else []
    tests = {'毛利率_%': (25, None), '营业利润率_%': (10, None), 'ROE_%': (12, None),
             '资产负债率_%': (None, 65), 'OCF': (0, None), 'FCF': (0, None),
             '营收可得周期CAGR_%': (5, None), '净利可得周期CAGR_%': (5, None),
             '季度营收同比_%': (0, None), '季度净利同比_%': (0, None)}
    failed = []
    for key, (low, high) in tests.items():
        v = row[key]
        if not math.isfinite(v):
            missing.append(key)
        elif (low is not None and (v < low or (key in ['OCF', 'FCF'] and v <= 0))) or (high is not None and v > high):
            failed.append(key)
    flags = []
    if row['ROE_%'] > 40:
        flags.append('高ROE：回购/权益基数待核实')
    if row['季度净利同比_%'] > 80:
        flags.append('净利同比异常：低基数/非经常项待核实')
    if row['FCF净利比'] < .7:
        flags.append('现金转化偏弱')
    price_gap = abs(ratio(number(row['Yahoo价格']), row['最新价']) - 1)
    high_gap = abs(ratio(number(row['Yahoo52周高点']), row['52周高点']) - 1)
    if price_gap > .1 or high_gap > .1:
        flags.append('跨源价格/高点差异超过10%')
        row['分组'] = '隔离：跨源价格或拆股差异'
    row['未通过条件'] = '；'.join(failed)
    row['missing_evidence'] = '；'.join(missing + ['最新10-Q/业绩稿原件', '治理与下跌原因', '正常化利润及SBC'])
    row['量化警示'] = '；'.join(flags)
    row['筛选状态'] = '未通过' if failed else '待补证候选'
    growth = .5 * linear(rev_cagr, 3, 15) + .5 * linear(ni_cagr, 3, 20)
    profit = .4 * linear(row['营业利润率_%'], 10, 30) + .3 * linear(row['毛利率_%'], 20, 65) + .3 * linear(row['ROE_%'], 12, 30)
    capital = .6 * linear(row['FCF净利比'], .5, 1.3) + .4 * linear(65 - row['资产负债率_%'], 0, 45)
    valuation = .6 * linear(30 - row['PE_TTM'], 0, 20) + .4 * linear(row['距52周高点跌幅_%'], 15, 45)
    confidence = max(0, 100 - 15 * len(missing) - 10 * len(flags) - 20)
    row['二筛总分'] = round(max(0, .25 * growth + .25 * profit + .2 * capital + .2 * valuation + .1 * confidence - 3 * len(flags)), 1)
    row['研究排序说明'] = '排序分，非公司质量分；五年增长未验证，可得周期仅作代理'
    return row


def main():
    p = ArgumentParser()
    p.add_argument('--date', required=True)
    p.add_argument('--repair-cache', action='store_true', help='复核已有候选的增长口径，不重新扫描市场')
    args = p.parse_args()
    out = ROOT / 'data' / 'screens'
    out.mkdir(exist_ok=True)
    if args.repair_cache:
        path = out / f'美股质量错杀初筛_{args.date}.csv'
        with path.open(encoding='utf-8-sig', newline='') as f:
            cached = list(csv.DictReader(f))
        targets = [r for r in cached if r.get('筛选状态') == '待补证候选']
        for row in targets:
            for key in ['最新价', 'PE_TTM', '52周高点', '距52周高点跌幅_%']:
                row[key] = number(row[key])
        replacements = {}
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(supplement, dict(r)): r for r in targets}
            for future in as_completed(futures):
                base = futures[future]
                try:
                    replacements[base['代码']] = future.result()
                except Exception:
                    replacements[base['代码']] = {**base, '分组': '隔离：缓存复核失败'}
        completed = [replacements.get(r['代码'], r) for r in cached]
        # 统一修复初轮分类，不依赖候选是否获得财务数据。
        for row in completed:
            if 'agricultural inputs' in row.get('行业', '').lower():
                row['分组'] = '资源独立池'
        write_csv(path, completed)
        candidates = [r for r in completed if r.get('分组') == '普通经营公司' and r.get('筛选状态') == '待补证候选']
        candidates.sort(key=lambda r: number(r.get('二筛总分'), 0), reverse=True)
        for n, row in enumerate(candidates, 1):
            row['二筛排名'] = n
        write_csv(out / f'美股质量错杀二筛排序_{args.date}.csv', candidates)
        write_csv(out / f'美股质量错杀异常与独立池_{args.date}.csv', [r for r in completed if r not in candidates])
        print(f'已复核 {len(targets)}；普通候选 {len(candidates)}')
        for row in candidates:
            print(row['代码'], row['二筛总分'], row['已在Watchlist'], row['missing_evidence'])
        return
    client = _tiger_client()
    specs = [(StockField.CurPrice, 5, None), (StockField.FloatMarketVal, 2e9, None),
             (StockField.PeTTM, 8, 30), (StockField.Week52High, 5, None)]
    filters = [StockFilter(f, filter_min=a, filter_max=b, is_no_filter=False) for f, a, b in specs]
    raw, cursor = [], None
    while True:
        r = client.market_scanner(market=Market.US, filters=filters, cursor_id=cursor, page_size=200)
        for item in r.items:
            d = item.field_data
            raw.append({'代码': item.symbol, **{f.name: number(d.get(f)) for f, _, _ in specs}})
        cursor = r.cursor_id
        if not cursor:
            break
    write_csv(out / f'美股Tiger原始_{args.date}.csv', raw)
    watched = set()
    for name in ['watchlist_core.json', 'watchlist_growth.json']:
        data = json.loads((ROOT / 'data' / name).read_text(encoding='utf-8-sig'))
        entries = data if isinstance(data, list) else data.get('entries', [])
        watched.update(e.get('code', '').removesuffix('.US') for e in entries if e.get('code', '').endswith('.US'))
    rows = []
    for d in raw:
        drawdown = 100 * (1 - ratio(d['CurPrice'], d['Week52High']))
        if 15 <= drawdown <= 45:
            rows.append({'代码': d['代码'], '最新价': d['CurPrice'], '流通市值_亿美元': d['FloatMarketVal'] / 1e8,
                         'PE_TTM': d['PeTTM'], '52周高点': d['Week52High'], '距52周高点跌幅_%': round(drawdown, 2),
                         '数据日期': args.date, '已在Watchlist': '是' if d['代码'] in watched else '否'})
    print(f'Tiger原始 {len(raw)}；回撤15%—45% {len(rows)}', flush=True)
    completed = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(supplement, dict(r)): r for r in rows}
        for future in as_completed(futures):
            base = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = {**base, '分组': '隔离：补数失败', 'missing_evidence': type(e).__name__}
            completed.append(result)
            if len(completed) % 20 == 0:
                write_csv(out / f'美股质量错杀初筛_{args.date}.csv', completed)
                print(f'已补数 {len(completed)}/{len(rows)}', flush=True)
    write_csv(out / f'美股质量错杀初筛_{args.date}.csv', sorted(completed, key=lambda x: x['代码']))
    candidates = [r for r in completed if r.get('分组') == '普通经营公司' and r.get('筛选状态') == '待补证候选']
    candidates.sort(key=lambda x: x.get('二筛总分', 0), reverse=True)
    for n, r in enumerate(candidates, 1):
        r['二筛排名'] = n
    write_csv(out / f'美股质量错杀二筛排序_{args.date}.csv', candidates)
    write_csv(out / f'美股质量错杀异常与独立池_{args.date}.csv', [r for r in completed if r not in candidates])
    print(f'候选 {len(candidates)}；新候选 {sum(r["已在Watchlist"] == "否" for r in candidates)}', flush=True)
    for r in candidates[:20]:
        print(r['代码'], r['二筛总分'], r['最新价'], r['PE_TTM'], r['距52周高点跌幅_%'], r['已在Watchlist'], flush=True)


if __name__ == '__main__':
    main()
