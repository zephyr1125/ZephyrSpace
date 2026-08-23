"""A股质量错杀筛选 —— CNINFO 全A清单 + 理杏仁基本面粗筛 + tushare 52周高点 + 理杏仁财务评分.

三步流水线：
  Step 1  粗筛：CNINFO 全A清单 → 理杏仁 fundamental 批量(股价/市值/PE) → tushare 52周高点跌幅过滤
  Step 2  排序：理杏仁 fs/non_financial 逐只拉 7 年年报 → 四维量化评分 → A/B/C 分档
  Step 3  精筛：AI 7 条指标手工精筛（由 skill 层执行，本脚本只产出 A/B/C 候选）

Usage:
    python scripts/cn_mispricing_screen.py                    # 今天
    python scripts/cn_mispricing_screen.py --date 2026-08-23
    python scripts/cn_mispricing_screen.py --skip-watchlist   # 排除已在 watchlist 的 A 股
    python scripts/cn_mispricing_screen.py --limit 100        # 仅评分前 100 只（测试用）

Output:
    data/screens/A股质量错杀初筛_YYYY-MM-DD.csv
    data/screens/A股质量错杀二筛排序_YYYY-MM-DD.csv

数据源分工（与港股/美股版对应）：
    全A清单   → CNINFO  szse_stock.json（repo 已有 _load_org_ids 同源）
    股价/市值/PE → 理杏仁 cn/company/fundamental/non_financial（批量）
    52周高点 → tushare daily（逐日全市场 high，取 1 年 max）
    财务评分 → 理杏仁 cn/company/fs/non_financial（逐只 7 年年报，含 m.* 财务指标树）
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lixinger_api import get_client

# ── A股粗筛参数 ──────────────────────────────────────────
# A股流动性优于港股，市值门槛略低；估值中枢高于港股（15-18 vs 12-14）
MIN_PRICE = 5                # 最低股价 CNY
MIN_CMCAP_YI = 50            # 最低流通市值 CNY 亿（≈ 50亿，规避微型股）
PE_MIN, PE_MAX = 6, 30       # PE TTM 范围（A股中枢 15-18，放宽到 30 容纳成长股）
MIN_DRAWDOWN_PCT = 15        # 距 52 周高点至少跌这么多
PE_CENTER = 18               # 估值折价评分锚点（A股中枢）

FUNDAMENTAL_METRICS = ["sp", "mc", "cmc", "pe_ttm", "d_pe_ttm", "pb", "ps_ttm", "dyr"]
FS_METRICS = [
    "y.ps.toi.t", "y.ps.np.t", "y.ps.ebit.t", "y.ps.ieife.t",
    "y.cfs.ncffoa.t",
    "y.bs.ar.t", "y.bs.i.t", "y.bs.tsc.t",
    "y.m.roe.t", "y.m.roa.t", "y.m.gp_m.t", "y.m.np_s_r.t",
    "y.m.tl_ta_r.t", "y.m.fcf.t", "y.m.ncffoa_np_r.t",
]


# ── 工具函数 ─────────────────────────────────────────────

def number(value, default=float("nan")):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def linear(value, bad, good):
    if not math.isfinite(value):
        return 35.0
    if good == bad:
        return 50.0
    return 100.0 * clamp((value - bad) / (good - bad), 0.0, 1.0)


def _cagr(values, years=3):
    """values[0] = 最新，values[n] = n 年前。"""
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return float("nan")
    n = min(years, len(vals) - 1)
    newest, oldest = vals[0], vals[n]
    if newest <= 0 or oldest <= 0:
        return float("nan")
    return (newest / oldest) ** (1 / n) - 1


# ── 代码/板块工具 ────────────────────────────────────────

def cn_to_ts(code: str) -> str:
    """6位代码 → tushare ts_code 格式（带市场后缀）。"""
    if code[0] == "6":
        return code + ".SH"
    if code[0] in ("0", "3"):
        return code + ".SZ"
    return code + ".BJ"  # 北交所（43/83/87/92 开头）


def board_of(code: str) -> str:
    """6位代码 → 板块（沪/深/科/创/北）。"""
    if code.startswith("688"):
        return "科"
    if code.startswith(("300", "301")):
        return "创"
    if code[0] == "6":
        return "沪"
    if code[0] in ("0", "3"):
        return "深"
    return "北"


# ── Step 1a: CNINFO 全A清单 ─────────────────────────────

def cninfo_universe():
    """从 CNINFO szse_stock.json 取全A股（category='A股'），返回 [{code, name}]。

    与 cninfo_api._load_org_ids 同源，覆盖沪深 A 股（约 5300 只）。
    """
    resp = requests.get("http://www.cninfo.com.cn/new/data/szse_stock.json", timeout=30)
    stock_list = resp.json().get("stockList", [])
    out = []
    for it in stock_list:
        if it.get("category") != "A股":
            continue
        code = str(it.get("code", ""))
        if len(code) != 6:
            continue
        out.append({"code": code, "name": it.get("zwjc", "")})
    return out


def resolve_trade_date(screen_date):
    """用 tushare 交易日历把 screen_date 回退到最近交易日（理杏仁周末返回空）。

    周末/节假日时，理杏仁 fundamental 接口对非交易日 date 返回空列表，
    故须先把日期解析为最近交易日再查询。
    """
    import tushare as ts
    load_dotenv(ROOT / ".env")
    pro = ts.pro_api(os.getenv("TUSHARE_TOKEN"))
    d = datetime.fromisoformat(screen_date)
    start = (d - timedelta(days=20)).strftime("%Y%m%d")
    end = d.strftime("%Y%m%d")
    try:
        cal = pro.trade_cal(exchange="SSE", start_date=start, end_date=end, is_open="1")
        if cal.empty:
            return screen_date
        latest = str(cal["cal_date"].max())
        return f"{latest[:4]}-{latest[4:6]}-{latest[6:]}"
    except Exception:
        # 兜底：退到工作日
        dd = d
        while dd.weekday() >= 5:
            dd -= timedelta(days=1)
        return dd.isoformat()


# ── Step 1b: 理杏仁 fundamental 批量粗筛 ─────────────────

def lixinger_fundamental(codes, screen_date, chunk=100):
    """批量拉 A 股 fundamental（sp/mc/cmc/pe_ttm/...），返回 {code: {...}}。"""
    lx = get_client()
    results = {}
    total = len(codes)
    for i in range(0, total, chunk):
        batch = codes[i:i + chunk]
        try:
            r = lx.fundamentals(batch, date=screen_date, metrics=FUNDAMENTAL_METRICS)
            if isinstance(r, list):
                for item in r:
                    code = item.get("stockCode")
                    if code:
                        results[code] = item
        except Exception as exc:
            print(f"  ⚠ fundamental batch @{i} 失败: {exc}")
        if i + chunk < total:
            time.sleep(0.1)
    return results


# ── Step 1c: tushare 52周高点 ───────────────────────────

def tushare_52w_high(screen_date):
    """逐日拉全市场 daily.high，取最近 ~1 年 max 作为 52 周高点，返回 {ts_code: high}。"""
    import tushare as ts
    load_dotenv(ROOT / ".env")
    pro = ts.pro_api(os.getenv("TUSHARE_TOKEN"))

    start = (datetime.fromisoformat(screen_date) - timedelta(days=400)).strftime("%Y%m%d")
    end = screen_date.replace("-", "")
    cal = pro.trade_cal(exchange="SSE", start_date=start, end_date=end, is_open="1")
    dates = sorted(cal["cal_date"].tolist(), reverse=True)[:260]  # ~1 个自然年

    high = {}
    done = 0
    for d in dates:
        try:
            df = pro.daily(trade_date=d, fields="ts_code,high")
            for _, row in df.iterrows():
                h = row["high"]
                c = row["ts_code"]
                high[c] = max(high.get(c, h), h)
        except Exception as exc:
            print(f"  ⚠ daily {d} 失败: {exc}")
        done += 1
        if done % 50 == 0:
            print(f"  … tushare {done}/{len(dates)} 交易日")
        time.sleep(0.12)
    return high


# ── Step 2: 理杏仁 fs 财务评分 ───────────────────────────

def _fs_series(recs, tbl, fld):
    """从 fs 响应 recs（新→旧）提取某指标的数值序列。"""
    vals = []
    for rec in recs:
        try:
            v = rec["y"][tbl][fld]["t"]
            vals.append(v if isinstance(v, (int, float)) else float("nan"))
        except (KeyError, TypeError):
            vals.append(float("nan"))
    return vals


def _fs_latest(recs, tbl, fld):
    """取最新一期的指标值（recs 已按 date 新→旧排序）。"""
    s = _fs_series(recs, tbl, fld)
    for v in s:
        if math.isfinite(v):
            return v
    return float("nan")


def fetch_fs_metrics(code, screen_date):
    """逐只拉 7 年年报，返回 score_row 所需的指标字典；失败/数据不足返回 None。

    带重试：理杏仁单只 fs 接口在并发下偶发限流，最多重试 2 次 + 退避。
    """
    lx = get_client()
    start = (datetime.fromisoformat(screen_date) - timedelta(days=365 * 7)).strftime("%Y-%m-%d")
    payload = {
        "stockCodes": [code],
        "startDate": start,
        "endDate": screen_date,
        "metricsList": FS_METRICS,
    }
    r = None
    for attempt in range(3):
        try:
            r = lx.post("cn/company/fs/non_financial", payload)
        except Exception:
            r = None
        if isinstance(r, list) and r:
            break
        if attempt < 2:
            time.sleep(1.0 + attempt * 1.0)  # 退避 1s / 2s
    if not isinstance(r, list) or not r:
        return None

    recs = sorted(r, key=lambda x: x.get("date", ""), reverse=True)  # 新→旧
    if len(recs) < 2:
        return None

    toi = _fs_series(recs, "ps", "toi")
    np_ = _fs_series(recs, "ps", "np")
    ebit = _fs_series(recs, "ps", "ebit")
    ieife = _fs_series(recs, "ps", "ieife")
    ncffoa = _fs_series(recs, "cfs", "ncffoa")
    ar = _fs_series(recs, "bs", "ar")
    inv = _fs_series(recs, "bs", "i")
    tsc = _fs_series(recs, "bs", "tsc")

    roe = _fs_latest(recs, "m", "roe")
    roa = _fs_latest(recs, "m", "roa")
    gp_m = _fs_latest(recs, "m", "gp_m")
    np_s_r = _fs_latest(recs, "m", "np_s_r")
    tl_ta_r = _fs_latest(recs, "m", "tl_ta_r")
    fcf = _fs_latest(recs, "m", "fcf")

    toi0 = toi[0] if toi and math.isfinite(toi[0]) else float("nan")
    np0 = np_[0] if np_ and math.isfinite(np_[0]) else float("nan")
    ebit0 = ebit[0] if ebit and math.isfinite(ebit[0]) else float("nan")
    ieife0 = ieife[0] if ieife and math.isfinite(ieife[0]) else 0.0

    # 利息保障倍数：EBIT / 利息费用（利息为 0 时给大数）
    if math.isfinite(ebit0) and ieife0 and abs(ieife0) > 0:
        interest_cov = abs(ebit0 / ieife0)
    else:
        interest_cov = 100.0 if math.isfinite(ebit0) else float("nan")

    # FCF / 净利润
    fcf_conv = (fcf / np0) if (math.isfinite(fcf) and math.isfinite(np0) and np0 != 0) else float("nan")

    # 债务权益比（用总负债/总权益近似 = tl_ta_r / (1 - tl_ta_r)）
    debt_equity = (tl_ta_r / (1 - tl_ta_r)) if (math.isfinite(tl_ta_r) and tl_ta_r < 1) else float("nan")

    # 最新年度同比（作为"最新季度同比"的代理，用于增速异常惩罚）
    rev_yoy = ((toi[0] - toi[1]) / abs(toi[1])) if (len(toi) >= 2 and math.isfinite(toi[0]) and math.isfinite(toi[1]) and toi[1]) else float("nan")
    ni_yoy = ((np_[0] - np_[1]) / abs(np_[1])) if (len(np_) >= 2 and math.isfinite(np_[0]) and math.isfinite(np_[1]) and np_[1]) else float("nan")

    return {
        "营收5年CAGR_%": round(100 * _cagr(toi, 5), 2) if toi else "",
        "净利润5年CAGR_%": round(100 * _cagr(np_, 5), 2) if np_ else "",
        "营收3年CAGR_%": round(100 * _cagr(toi, 3), 2) if toi else "",
        "净利润3年CAGR_%": round(100 * _cagr(np_, 3), 2) if np_ else "",
        "经营现金流3年CAGR_%": round(100 * _cagr(ncffoa, 3), 2) if ncffoa else "",
        "应收账款3年CAGR_%": round(100 * _cagr(ar, 3), 2) if ar else "",
        "库存3年CAGR_%": round(100 * _cagr(inv, 3), 2) if inv else "",
        "毛利率_%": round(100 * gp_m, 2) if math.isfinite(gp_m) else "",
        "净利率_%": round(100 * np_s_r, 2) if math.isfinite(np_s_r) else "",
        "ROE_%": round(100 * roe, 2) if math.isfinite(roe) else "",
        "ROA_%": round(100 * roa, 2) if math.isfinite(roa) else "",
        "资产负债率_%": round(100 * tl_ta_r, 2) if math.isfinite(tl_ta_r) else "",
        "长期债务权益比": round(debt_equity, 4) if math.isfinite(debt_equity) else "",
        "利息保障倍数": round(interest_cov, 2) if math.isfinite(interest_cov) else "",
        "FCF净利润转化率": round(fcf_conv, 4) if math.isfinite(fcf_conv) else "",
        "股数3年CAGR_%": round(100 * _cagr(tsc, 3), 2) if tsc else "",
        "最新季度营收同比_%": round(100 * rev_yoy, 2) if math.isfinite(rev_yoy) else "",
        "最新季度净利润同比_%": round(100 * ni_yoy, 2) if math.isfinite(ni_yoy) else "",
        "经营现金流_原始值": ncffoa[0] if ncffoa and math.isfinite(ncffoa[0]) else "",
    }


# ── 量化评分（复用港股版 score_row，仅调 PE 中枢） ────────

def score_row(row, extra):
    """四维评分：增长 + 现金流质量 + 资本质量 + 估值折价 - 异常惩罚。

    A股版调整：估值折价锚点用 PE_CENTER=18（A股中枢，高于港股 14x）。
    NaN 安全：所有 number() 结果先经 _fin 兜底，避免 nan 污染导致 clamp(nan)=100 的假满分。
    """
    def _fin(x, default=0.0):
        return x if math.isfinite(x) else default

    rev5 = number(row.get("营收5年CAGR_%", ""))
    ni5 = number(row.get("净利润5年CAGR_%", ""))
    roe = number(row.get("ROE_%", ""))
    debt_assets = number(row.get("资产负债率_%", ""))
    pe = number(row.get("PE_TTM", ""))
    drawdown = number(row.get("距52周高点跌幅_%", ""))

    rev3 = number(extra.get("营收3年CAGR_%", ""))
    ni3 = number(extra.get("净利润3年CAGR_%", ""))
    cfo3 = number(extra.get("经营现金流3年CAGR_%", ""))
    ar3 = number(extra.get("应收账款3年CAGR_%", ""))
    inv3 = number(extra.get("库存3年CAGR_%", ""))
    gross = number(extra.get("毛利率_%", ""))
    net_margin = number(extra.get("净利率_%", ""))
    roa = number(extra.get("ROA_%", ""))
    debt_equity = number(extra.get("长期债务权益比", ""))
    interest = number(extra.get("利息保障倍数", ""))
    fcf_conv = number(extra.get("FCF净利润转化率", ""))
    share_cagr = number(extra.get("股数3年CAGR_%", ""))

    consistency = 100 - min(abs(_fin(rev5) - _fin(rev3)) * 4, 100) if math.isfinite(rev3) else 35
    profit_consistency = 100 - min(abs(_fin(ni5) - _fin(ni3)) * 2.5, 100) if math.isfinite(ni3) else 35

    growth = (
        0.35 * linear(rev5, 3, 15)
        + 0.25 * linear(rev3, 2, 14)
        + 0.20 * consistency
        + 0.20 * profit_consistency
    )

    ar_gap = (rev3 - ar3) if math.isfinite(ar3) else float("nan")
    inv_gap = (rev3 - inv3) if math.isfinite(inv3) else float("nan")

    cash_quality = (
        0.25 * linear(cfo3, 0, 15)
        + 0.15 * linear(fcf_conv, 0.5, 1.2)
        + 0.20 * linear(ar_gap, -8, 4)
        + 0.10 * linear(inv_gap, -10, 5)
        + 0.20 * linear(net_margin, 5, 20)
        + 0.10 * linear(gross, 20, 60)
    )

    capital_quality = (
        0.35 * linear(roa, 4, 14)
        + 0.20 * linear(65 - _fin(debt_assets, 65), 0, 45)
        + 0.20 * linear(interest, 2, 12)
        + 0.15 * linear(roe, 10, 25)
        + 0.10 * linear(1.5 - _fin(debt_equity, 1.5), 0, 1.5)
    )

    valuation = 0.55 * (100 - abs(_fin(pe, PE_CENTER) - PE_CENTER) / 10 * 100) + 0.45 * linear(drawdown, 15, 40)
    valuation = clamp(valuation, 0, 100)

    penalty = 0.0
    flags = []
    qrev = number(row.get("最新季度营收同比_%", ""))
    qni = number(row.get("最新季度净利润同比_%", ""))
    if math.isfinite(qrev) and qrev > 60 or math.isfinite(qni) and qni > 80:
        penalty += 12; flags.append("增速异常")
    if _fin(ni5) - _fin(rev5) > 20:
        penalty += 7; flags.append("利润增速显著快于营收")
    if _fin(roe) > 40:
        penalty += 6; flags.append("ROE>40%")
    if math.isfinite(ar_gap) and ar_gap < -8:
        penalty += 8; flags.append("应收增速>营收")
    if math.isfinite(cfo3) and cfo3 < 0:
        penalty += 10; flags.append("经营现金流3Y为负")
    if math.isfinite(fcf_conv) and fcf_conv < 0.7:
        penalty += 8; flags.append("FCF/NI<70%")
    if math.isfinite(share_cagr) and share_cagr > 2:
        penalty += 6; flags.append("股数膨胀>2%")
    if not extra:
        penalty += 10; flags.append("财务缺数据")

    total = round(clamp(0.30 * growth + 0.30 * cash_quality + 0.25 * capital_quality + 0.15 * valuation - penalty, 0, 100), 1)
    tier = "A-优先三件套" if total >= 72 and penalty < 12 else "B-保留观察" if total >= 58 else "C-暂缓"

    return total, tier, penalty, "；".join(flags) or "无", extra


# ── Watchlist 加载 ───────────────────────────────────────

def _load_watchlist_cn():
    """从 watchlist JSON 读取已在关注列表中的 A 股代码（去 .SH/.SZ 后缀）。"""
    symbols = set()
    for filename in ("watchlist_core.json", "watchlist_growth.json"):
        path = ROOT / "data" / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for entry in data.get("entries", []):
                code = entry.get("code", "")
                if code.endswith((".SH", ".SZ")):
                    symbols.add(code[:-3])
        except Exception as exc:
            print(f"  ⚠ 读取 {filename} 失败: {exc}")
    return symbols


# ── 主流程 ───────────────────────────────────────────────

def main():
    parser = ArgumentParser(description="A股质量错杀筛选")
    parser.add_argument("--date", default=date.today().isoformat(), help="筛选日期 (YYYY-MM-DD)")
    parser.add_argument("--skip-watchlist", action="store_true", help="排除已在 watchlist 中的 A 股标的")
    parser.add_argument("--limit", type=int, default=0, help="仅对前 N 只候选做财务评分（0=全部，测试用）")
    parser.add_argument("--skip-tushare", action="store_true", help="跳过 52 周高点（测试用，跌幅过滤会失效）")
    args = parser.parse_args()

    screen_date = args.date
    out_dir = ROOT / "data" / "screens"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f" A股质量错杀筛选 — {screen_date}")
    print("=" * 60)

    # 解析最近交易日（理杏仁 fundamental 对周末返回空）
    trade_date = resolve_trade_date(screen_date)
    if trade_date != screen_date:
        print(f"[交易日] {screen_date} 非交易日，回退到 {trade_date}")

    # ── Step 1a: CNINFO 全A清单 ──
    universe = cninfo_universe()
    print(f"[CNINFO] 全A股清单 → {len(universe)} 只")
    if not universe:
        print("❌ CNINFO 无结果，终止。")
        return

    # ── Step 1b: 理杏仁 fundamental 粗筛 ──
    codes = [u["code"] for u in universe]
    name_map = {u["code"]: u["name"] for u in universe}
    fund = lixinger_fundamental(codes, trade_date)
    print(f"[理杏仁] fundamental 覆盖 {len(fund)}/{len(codes)} 只")

    candidates = []
    for u in universe:
        code = u["code"]
        item = fund.get(code)
        if not item:
            continue
        sp = number(item.get("sp"))
        cmc = number(item.get("cmc"))          # 流通市值，单位元
        pe = number(item.get("pe_ttm"))
        cmc_yi = cmc / 1e8                      # 元 → 亿
        if sp < MIN_PRICE or cmc_yi < MIN_CMCAP_YI:
            continue
        if not (PE_MIN <= pe <= PE_MAX):
            continue
        candidates.append({
            "代码": code,
            "TS代码": cn_to_ts(code),
            "板块": board_of(code),
            "简称": name_map.get(code, ""),
            "最新价": sp,
            "流通市值_亿": round(cmc_yi, 2),
            "总市值_亿": round(number(item.get("mc")) / 1e8, 2),
            "PE_TTM": pe,
            "扣非PE": number(item.get("d_pe_ttm")),
            "PB": number(item.get("pb")),
            "PS_TTM": number(item.get("ps_ttm")),
            "股息率_%": round(100 * number(item.get("dyr")), 2),
        })
    print(f"[粗筛] 价格≥{MIN_PRICE} & 流通市值≥{MIN_CMCAP_YI}亿 & PE {PE_MIN}-{PE_MAX} → {len(candidates)} 只")

    # ── Step 1c: tushare 52周高点 + 跌幅过滤 ──
    if args.skip_tushare:
        high52 = {}
        print("[tushare] 已跳过 52 周高点")
    else:
        high52 = tushare_52w_high(screen_date)
        print(f"[tushare] 52周高点覆盖 {len(high52)} 只")

    for c in candidates:
        ts_code = c["TS代码"]
        h = high52.get(ts_code)
        cur = c["最新价"]
        if h and cur and h > 0:
            c["52周高点"] = round(h, 2)
            c["距52周高点跌幅_%"] = round((1 - cur / h) * 100, 2)
        else:
            c["52周高点"] = ""
            c["距52周高点跌幅_%"] = ""

    if not args.skip_tushare:
        before = len(candidates)
        candidates = [c for c in candidates
                      if c["距52周高点跌幅_%"] == "" or number(c["距52周高点跌幅_%"]) >= MIN_DRAWDOWN_PCT]
        print(f"[跌幅过滤] ≥{MIN_DRAWDOWN_PCT}%: {before} → {len(candidates)} 只")

    # watchlist 标记/排除
    watched = _load_watchlist_cn() if args.skip_watchlist else set()
    if watched:
        print(f"[Watchlist] 已加载 {len(watched)} 只 A 股关注标的")
    for c in candidates:
        c["已在Watchlist"] = "是" if c["代码"] in watched else "否"
    if args.skip_watchlist:
        before_wl = len(candidates)
        candidates = [c for c in candidates if c["已在Watchlist"] != "是"]
        print(f"[Watchlist排除] {before_wl} → {len(candidates)} 只")

    if not candidates:
        print("❌ 无候选通过粗筛，终止。")
        return

    # ── 初筛 CSV ──
    step1_path = out_dir / f"A股质量错杀初筛_{screen_date}.csv"
    fieldnames = [
        "代码", "TS代码", "板块", "简称", "最新价", "流通市值_亿", "总市值_亿",
        "PE_TTM", "扣非PE", "PB", "PS_TTM", "股息率_%",
        "52周高点", "距52周高点跌幅_%", "已在Watchlist",
    ]
    with open(step1_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for c in candidates:
            w.writerow(c)
    print(f"[初筛 CSV] {step1_path} ({len(candidates)} 只)")

    # ── Step 2: 理杏仁 fs 财务评分 ──
    scored_targets = candidates if args.limit <= 0 else candidates[:args.limit]
    if args.limit > 0:
        print(f"[limit] 仅对前 {len(scored_targets)} 只做财务评分")

    results = {}
    done = 0
    total = len(scored_targets)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fetch_fs_metrics, c["代码"], screen_date): c for c in scored_targets}
        for future in as_completed(futures):
            c = futures[future]
            try:
                results[c["代码"]] = future.result()
            except Exception:
                results[c["代码"]] = None
            done += 1
            if done % 50 == 0:
                print(f"  … 财务评分 {done}/{total}")
    print(f"[理杏仁 fs] 完成 {sum(1 for v in results.values() if v)}/{total} 只")

    scored = []
    for c in candidates:
        extra = results.get(c["代码"])
        # 把粗筛字段并入 row，供 score_row 读取 PE/跌幅/ROE 等
        row = dict(c)
        if extra:
            row.update(extra)
        total_score, tier, penalty, flags, _ = score_row(row, extra or {})
        scored.append({
            "二筛排名": 0,
            "代码": c["代码"],
            "TS代码": c["TS代码"],
            "板块": c["板块"],
            "简称": c["简称"],
            "二筛总分": total_score,
            "评级档": tier,
            "异常惩罚": penalty,
            "PE_TTM": c["PE_TTM"],
            "扣非PE": c["扣非PE"],
            "距52周高点跌幅_%": c["距52周高点跌幅_%"],
            "营收5年CAGR_%": (extra or {}).get("营收5年CAGR_%", ""),
            "净利润5年CAGR_%": (extra or {}).get("净利润5年CAGR_%", ""),
            "已在Watchlist": c["已在Watchlist"],
            "量化警示": flags,
            **{k: v for k, v in (extra or {}).items()
               if k not in ("营收5年CAGR_%", "净利润5年CAGR_%")},
        })

    scored.sort(key=lambda x: x["二筛总分"], reverse=True)
    for i, item in enumerate(scored, 1):
        item["二筛排名"] = i

    step2_path = out_dir / f"A股质量错杀二筛排序_{screen_date}.csv"
    with open(step2_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=scored[0].keys())
        w.writeheader()
        w.writerows(scored)
    print(f"[二筛 CSV] {step2_path} ({len(scored)} 只)")

    # ── 终端摘要 ──
    tiers = {"A-优先三件套": [], "B-保留观察": [], "C-暂缓": []}
    for s in scored:
        tiers[s["评级档"]].append(s)
    print(f"\n[评级分布] A={len(tiers['A-优先三件套'])} B={len(tiers['B-保留观察'])} C={len(tiers['C-暂缓'])}")
    print("\n[A档 - 优先三件套]:")
    for s in tiers["A-优先三件套"]:
        print(f"  {s['二筛排名']:2d}. {s['代码']} {s['简称']:<8s} {s['二筛总分']:5.1f}分  "
              f"PE={s['PE_TTM']} 跌幅={s['距52周高点跌幅_%']}%  {s['量化警示']}")
    if tiers["B-保留观察"]:
        print(f"\n[B档前10 - 保留观察]:")
        for s in tiers["B-保留观察"][:10]:
            print(f"  {s['二筛排名']:2d}. {s['代码']} {s['简称']:<8s} {s['二筛总分']:5.1f}分  "
                  f"PE={s['PE_TTM']} 跌幅={s['距52周高点跌幅_%']}%")


if __name__ == "__main__":
    main()
