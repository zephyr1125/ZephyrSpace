"""
重算 watchlist_index.json 中所有指数的 price_bands。

新定义（与当前价格无关）：
  bands[0] = 3年历史收盘价 P80（历史偏贵区上沿，不追高）
  bands[1] = 3年历史收盘价 P50（历史中位，合理估值）
  bands[2] = 3年历史收盘价 P20（历史偏低区，积极买入）

历史本身隐含了行业惯常估值水位，无需按行业手动调参。
"""
import json
import time
import os
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
import tushare as ts

ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

# ── 日期范围：今天往前 3 年 ──────────────────────────────────────
today = datetime.today()
start_3y = (today - timedelta(days=365 * 3)).strftime('%Y%m%d')
end_date  = today.strftime('%Y%m%d')


def fetch_3y_prices(index_code: str):
    """
    拉取指数 3 年日收盘价。
    tushare index_daily 的 ts_code 后缀：
      .CSI  中证/国证主题指数
      .SH   上交所
      .SZ   深交所
    H30xxx 系列在 tushare 中用 .CSI 后缀。
    """
    # 将存储里的代码转换成 tushare 格式（去掉 .CSI 改为对应后缀）
    base = index_code.rsplit('.', 1)[0]
    suffix = index_code.rsplit('.', 1)[1] if '.' in index_code else ''

    candidates = []
    if suffix == 'CSI':
        # 尝试顺序：.CSI → .SH → .SZ
        candidates = [f'{base}.CSI', f'{base}.SH', f'{base}.SZ']
    elif suffix in ('SH', 'SZ'):
        candidates = [index_code]
    else:
        candidates = [index_code]

    for ts_code in candidates:
        try:
            df = pro.index_daily(
                ts_code=ts_code,
                start_date=start_3y,
                end_date=end_date,
                fields='trade_date,close'
            )
            if df is not None and len(df) >= 30:
                return df['close'].dropna().values, ts_code
        except Exception:
            pass
        time.sleep(0.1)

    return None, None


def calc_bands(prices):
    """返回 [P80, P50, P20]，取整。"""
    p80 = int(round(np.percentile(prices, 80)))
    p50 = int(round(np.percentile(prices, 50)))
    p20 = int(round(np.percentile(prices, 20)))
    return [p80, p50, p20]


def main():
    with open('data/watchlist_index.json', encoding='utf-8') as f:
        data = json.load(f)

    updated, failed = [], []

    for entry in data['indices']:
        code = entry['index_code']
        name = entry.get('name', '')
        old_bands = entry.get('price_bands', [])

        prices, ts_code_used = fetch_3y_prices(code)
        if prices is None or len(prices) < 30:
            print(f'  ❌ 无数据  {code} {name}')
            failed.append(code)
            continue

        new_bands = calc_bands(prices)
        entry['price_bands'] = new_bands

        # 更新 valuation_anchor 说明
        entry['valuation_anchor'] = (
            f'3年历史价格分位锚点（{start_3y[:4]}-{end_date[:4]}）：'
            f'P80={new_bands[0]}（偏贵区上沿，不追高），'
            f'P50={new_bands[1]}（历史中位，合理区），'
            f'P20={new_bands[2]}（历史偏低区，积极买入）。'
            f'数据来源 tushare {ts_code_used}，共 {len(prices)} 个交易日。'
        )
        entry['last_updated'] = today.strftime('%Y-%m-%d')

        print(
            f'  ✅ {code:20s} {name[:16]:16s} '
            f'旧:{old_bands} → 新:{new_bands} '
            f'当前:{entry.get("current_index_price")}'
        )
        updated.append(code)
        time.sleep(0.12)

    with open('data/watchlist_index.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'\n完成：更新 {len(updated)} 只，失败 {len(failed)} 只')
    if failed:
        print('失败列表：', failed)


if __name__ == '__main__':
    main()
