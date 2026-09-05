"""港股「未收录高分企业」候选池构建 —— 不看价格，纯企业质量 + 覆盖率标签.

定位与 cn_high_score_pool 同构，但港股数据层完全不同：
  - 宇宙：Tiger 选股器（无 CNINFO），仅按流通市值 ≥ 下限（默认 HKD 200亿），无价格/PE 门槛
  - 财务：yfinance 逐只 ~5 年年报（无审计意见、字段常缺 → 缺失留 NaN 中性）
  - 覆盖：公司索引港股节 code→名称（打标）+ watchlist/低分登记 .HK（硬排）
  - 管理层红旗：港股无 CNINFO/理杏仁批量接口 → 本池只标注「RunB核」，由 skill Run B 逐家 Web/Tavily 核

产物：持久候选池 JSON（review_status 状态源）+ CSV 快照。与 A股版一致由 skill 分批复核消化，避免一次性大输出。

Usage:
    python scripts/hk_high_score_pool.py
    python scripts/hk_high_score_pool.py --min-cap 30          # 市值下限 HKD B
    python scripts/hk_high_score_pool.py --min-score 50        # 校准看分布
    python scripts/hk_high_score_pool.py --codes 01999,09992   # 只对指定 Tiger 5 位码跑(测试)
    python scripts/hk_high_score_pool.py --limit 60            # 对前 60 家(按 Tiger 返回序) 跑
    python scripts/hk_high_score_pool.py --no-cache            # 忽略缓存强制重拉

Output:
    data/screens/港股高分候选池.json
    data/screens/港股高分候选池_YYYY-MM-DD.csv
    data/cache/hk_high_score_fs_cache.json        # yfinance 指标缓存(重打分零重拉)

复用（勿重造，只读 import）：
    scripts/hk_mispricing_screen: _tiger_client / tiger_to_yahoo_hk / number / clamp / linear / _cagr
注：金融(银行/保险/券商)与 REIT 不在服务范围 → 依 yfinance sector 剔除；地产开发商保留（交给资本维度计分）。
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import time
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from scripts.hk_mispricing_screen import (  # noqa: E402
    _cagr,
    _tiger_client,
    clamp,
    linear,
    number,
    tiger_to_yahoo_hk,
)

# ── 参数（初值，首跑校准回填） ───────────────────────
MIN_MCAP_B = 20        # 最低流通市值 HKD B（实测 ≥20B → ~337 家）
MIN_SCORE = 60          # 质量分入池下限（≥70 Ⅰ候选 / 60-70 Ⅱ候选）
FS_WORKERS = 5          # yfinance 并发（与错杀版一致）
FS_CACHE_FILE = "hk_high_score_fs_cache.json"

# 金融 + REIT 剔除（yfinance sector 口径），地产开发商保留
FIN_SECTOR = {"financial services", "insurance", "banks", "asset management", "capital markets",
              "diversified financial services", "mortgage finance", "credit services"}
INDEX_PATH = ROOT / "00-首页" / "公司索引.md"
REGISTRY_PATH = ROOT / "00-首页" / "低分公司登记.md"
WL_FILES = ["data/watchlist_strategic.json", "data/watchlist_core.json",
            "data/watchlist_growth.json", "data/watchlist_out_of_scope.json"]

# ── 数值工具 ─────────────────────────────────────────────

def _nan(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _nmean(vals):
    fs = [v for v in vals if math.isfinite(v)]
    return sum(fs) / len(fs) if fs else float("nan")


def _nmin(vals):
    fs = [v for v in vals if math.isfinite(v)]
    return min(fs) if fs else float("nan")


def _series(frames, names):
    """yfinance 年报 frame → 数值序列（列序=新→旧，与错杀版约定一致）。"""
    for name in names:
        if name in frames.index:
            return [number(v) for v in frames.loc[name].tolist() if math.isfinite(number(v))]
    return []


def _code5(symbol):
    """任一带 .HK/纯数字 → 5 位零填充代码（知识库口径 00700）。"""
    digits = "".join(c for c in str(symbol) if c.isdigit())
    return f"{int(digits):05d}" if digits else ""


# ── 宇宙：Tiger 仅市值门槛 ───────────────────────────────

def tiger_universe(min_cap_b=MIN_MCAP_B):
    """遍历 Tiger 选股器全部页，仅设流通市值下限（无价格/PE/跌幅门槛）。"""
    from tigeropen.common.consts import Market
    from tigeropen.common.consts.filter_fields import StockField
    from tigeropen.quote.domain.filter import StockFilter

    client = _tiger_client()
    filters = [StockFilter(StockField.FloatMarketVal, filter_min=min_cap_b * 1_000_000_000,
                           is_no_filter=False)]
    out, cursor = [], None
    while True:
        res = client.market_scanner(market=Market.HK, filters=filters, cursor_id=cursor, page_size=200)
        for item in res.items:
            fd = item.field_data
            raw = str(item.symbol)
            yahoo = tiger_to_yahoo_hk(raw)
            out.append({
                "代码5": _code5(raw),          # 00700
                "Tiger代码": raw,              # 00700
                "Yahoo代码": yahoo,            # 0700.HK
                "流通市值_亿港元": round(number(fd.get(StockField.FloatMarketVal)) / 100_000_000, 1),
            })
        cursor = res.cursor_id
        if not cursor:
            break
        time.sleep(0.05)
    return out


# ── 覆盖：已研究代码集 + 名称 ──────────────────────────

def _watchlist_hk():
    """watchlist 四份 JSON 里的 .HK → 5 位代码集合。"""
    codes = set()
    for rel in WL_FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for e in data.get("entries", []):
                c = str(e.get("code", ""))
                if c.endswith(".HK"):
                    codes.add(_code5(c))
        except Exception as exc:
            print(f"  ⚠ {rel} 读取失败: {exc}")
    return codes


def _low_registry_hk():
    """低分公司登记.md 中 5 位 .HK 代码。"""
    if not REGISTRY_PATH.exists():
        return set()
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    return {m for m in re.findall(r"(?<!\d)(\d{5})\.HK", text)}


def _index_hk_map():
    """公司索引.md 港股节 → {5位code: 中文简称}。"""
    if not INDEX_PATH.exists():
        return {}
    text = INDEX_PATH.read_text(encoding="utf-8")
    m = re.search(r"^## 港股\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    body = m.group(1) if m else ""
    out = {}
    for line in body.splitlines():
        hit = re.search(r"\[\[(.+?)\]\]（(\d{4,5})）", line)
        if hit:
            out[f"{int(hit.group(2)):05d}"] = hit.group(1).strip()
    return out


def _coverage_labels(code5, name, index_map):
    """宽松口径：只在 index 命中才打标签；未命中 → 全新。"""
    if code5 not in index_map:
        return [], None  # 未建页（不管有没有深度文件——深度文件一般对应已建页）
    zwjc = index_map[code5]
    found = ["公司页"]
    for label, rel in [("深度分析", "深度分析"), ("管理层档案", "管理层档案")]:
        if (ROOT / rel / f"{zwjc}*").glob("*") or any(p.name.startswith(zwjc) for p in (ROOT / rel).glob(f"{zwjc}*")):
            found.append(label)
    return found, zwjc


# ── yfinance 财务 + 行业过滤 ────────────────────────────

def _is_financial(sector, name):
    s = (sector or "").lower()
    n = (name or "").upper()
    if s in FIN_SECTOR or "bank" in s or "insurance" in s:
        return True
    if "-REIT" in n or ".REIT" in n or " REIT " in n or n.endswith(" REIT"):
        return True
    return False


def fetch_hk_quality(yahoo_symbol):
    """yfinance 逐只拉年报 → 质量指标 dict；失败返回 None（含金融/缺数据标记待上层判断）。"""
    import yfinance as yf

    ticker = yf.Ticker(yahoo_symbol)
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    name = info.get("longName") or info.get("shortName") or ""
    sector = info.get("sector", "")

    try:
        income = ticker.get_income_stmt(freq="yearly")
        cash = ticker.get_cash_flow(freq="yearly")
        balance = ticker.get_balance_sheet(freq="yearly")
    except Exception as exc:
        return {"_financial": False, "名称": name, "行业": sector, "_ok": False, "_err": str(exc)[:120]}

    rev = _series(income, ["TotalRevenue", "OperatingRevenue"])
    gross = _series(income, ["GrossProfit"])
    ni = _series(income, ["NetIncome", "NetIncomeCommonStockholders"])
    ebit = _series(income, ["EBIT", "OperatingIncome"])
    ie = _series(income, ["InterestExpense", "InterestExpenseNonOperating"])
    cfo = _series(cash, ["OperatingCashFlow", "TotalCashFromOperatingActivities"])
    fcf = _series(cash, ["FreeCashFlow"])
    ar = _series(balance, ["AccountsReceivable", "NetReceivables"])
    inv = _series(balance, ["Inventory"])
    assets = _series(balance, ["TotalAssets"])
    equity = _series(balance, ["StockholdersEquity", "CommonStockEquity"])
    debt = _series(balance, ["TotalDebt"])

    if not rev or not ni or not equity:
        return {"_financial": _is_financial(sector, name), "名称": name, "行业": sector,
                "_ok": False, "_err": "财报字段不足"}

    # 行业过滤
    if _is_financial(sector, name):
        return {"_financial": True, "名称": name, "行业": sector, "_ok": False, "_err": "金融/REIT 剔除"}

    n = min(len(ni), len(equity))
    roe_year = [_nan(ni[i]) / _nan(equity[i]) for i in range(n) if _nan(equity[i]) != 0]
    roa_year = [_nan(ni[i]) / _nan(assets[i]) for i in range(min(len(ni), len(assets)))
                if _nan(assets[i]) > 0]
    roe_mean = 100 * _nmean(roe_year)
    roe_min = 100 * _nmin(roe_year)
    roa_mean = 100 * _nmean(roa_year)
    gross_mean = 100 * _nmean([_nan(g) / _nan(r) for g, r in zip(gross[:n], rev[:n])
                              if r and _nan(r) > 0 and g])
    npm_mean = 100 * _nmean([_nan(x) / _nan(r) for x, r in zip(ni[:n], rev[:n]) if r and _nan(r) > 0])

    rev3 = 100 * _cagr(rev, 3)
    rev5 = 100 * _cagr(rev, 5)
    ni3 = 100 * _cagr(ni, 3)
    ni5 = 100 * _cagr(ni, 5)
    ocf3 = 100 * _cagr(cfo, 3)
    ar3 = 100 * _cagr(ar, 3)
    inv3 = 100 * _cagr(inv, 3)

    fcf_years = [v for v in fcf if math.isfinite(v)]
    fcf_conv = _nmean([v / x for v, x in zip(fcf[:n], ni[:n])
                       if v and x and _nan(x) > 0 and math.isfinite(v)])
    fcf_pos = sum(1 for v in fcf_years if v >= 0) / len(fcf_years) if fcf_years else float("nan")
    ocf_neg = sum(1 for v in cfo if math.isfinite(v) and v < 0)

    assets0 = assets[0] if assets else float("nan")
    equity0 = equity[0] if equity else float("nan")
    debt0 = debt[0] if debt else float("nan")
    rev0, ni0 = rev[0], ni[0]
    ebit0 = ebit[0] if ebit else float("nan")
    ie0 = ie[0] if ie else float("nan")

    if not math.isfinite(ni0):
        return {"_financial": False, "名称": name, "行业": sector, "_ok": False, "_err": "最新净利缺失"}

    def _yoy(arr):
        if len(arr) >= 2 and arr[0] and arr[1]:
            return (arr[0] - arr[1]) / abs(arr[1])
        return float("nan")
    qrev = 100 * _yoy(rev)
    qni = 100 * _yoy(ni)

    interest_cov = (abs(ebit0 / ie0) if math.isfinite(ebit0) and math.isfinite(ie0) and ie0 != 0
                    else (100.0 if math.isfinite(ebit0) else float("nan")))
    debt_assets = (100 * debt0 / assets0) if (math.isfinite(debt0) and assets0) else float("nan")
    debt_equity = (debt0 / equity0) if (math.isfinite(debt0) and math.isfinite(equity0) and equity0 != 0) else float("nan")
    shares = _series(balance, ["OrdinarySharesNumber", "ShareIssued"])
    share3 = 100 * _cagr(shares, 3)

    return {
        "_ok": True, "_financial": False, "名称": name, "行业": sector,
        "营收5年CAGR_%": round(rev5, 2) if math.isfinite(rev5) else "",
        "营收3年CAGR_%": round(rev3, 2) if math.isfinite(rev3) else "",
        "净利润5年CAGR_%": round(ni5, 2) if math.isfinite(ni5) else "",
        "净利润3年CAGR_%": round(ni3, 2) if math.isfinite(ni3) else "",
        "经营现金流3年CAGR_%": round(ocf3, 2) if math.isfinite(ocf3) else "",
        "应收账款3年CAGR_%": round(ar3, 2) if math.isfinite(ar3) else "",
        "存货3年CAGR_%": round(inv3, 2) if math.isfinite(inv3) else "",
        "毛利率均值_%": round(gross_mean, 1) if math.isfinite(gross_mean) else "",
        "净利率均值_%": round(npm_mean, 1) if math.isfinite(npm_mean) else "",
        "5Y ROE均值_%": round(roe_mean, 1) if math.isfinite(roe_mean) else "",
        "5Y ROE最低_%": round(roe_min, 1) if math.isfinite(roe_min) else "",
        "资产负债率_%": round(debt_assets, 1) if math.isfinite(debt_assets) else "",
        "利息保障倍数": round(interest_cov, 1) if math.isfinite(interest_cov) else "",
        "长期债务权益比": round(debt_equity, 2) if math.isfinite(debt_equity) else "",
        "FCF转化率": round(fcf_conv, 2) if math.isfinite(fcf_conv) else "",
        "FCF正年数占比_%": round(100 * fcf_pos, 0) if math.isfinite(fcf_pos) else "",
        "OCF负年数": ocf_neg,
        "股数3年CAGR_%": round(share3, 2) if math.isfinite(share3) else "",
        "最新年度营收同比_%": round(qrev, 2) if math.isfinite(qrev) else "",
        "最新年度净利同比_%": round(qni, 2) if math.isfinite(qni) else "",
        # 评分用（CAGR 存百分数以与评分函数单位一致）
        "_rev5": rev5 / 100 if math.isfinite(rev5) else float("nan"),
        "_rev3": rev3 / 100 if math.isfinite(rev3) else float("nan"),
        "_ni5": ni5 / 100 if math.isfinite(ni5) else float("nan"),
        "_ni3": ni3 / 100 if math.isfinite(ni3) else float("nan"),
        "_ocf3": ocf3 / 100 if math.isfinite(ocf3) else float("nan"),
        "_ar3": ar3 / 100 if math.isfinite(ar3) else float("nan"),
        "_share3": share3 / 100 if math.isfinite(share3) else float("nan"),
        "_roe_mean": roe_mean, "_roe_min": roe_min,
        "_roa": roa_mean, "_gross": gross_mean, "_npm": npm_mean,
        "_fcf_conv": fcf_conv, "_fcf_pos": fcf_pos, "_ocf_neg": ocf_neg,
        "_debt_assets": debt_assets, "_debt_eq": debt_equity, "_intcov": interest_cov,
        "_qrev": qrev, "_qni": qni, "_fcf5neg": not bool(fcf_years) or (len([v for v in fcf_years if v < 0]) > len(fcf_years) // 2),
    }


# ── 质量分（无估值/无审计） ─────────────────────────────

def quality_score(e):
    """growth20 + profit28 + cash27 + capital20 + 股本纪律5 − 惩罚。NaN→中性35。

    港股无分红史、成熟高 ROE 现金牛多（营收低增但质量极高），故比 A股版更轻成长、
    更重盈利与现金流；成长停滞不再把康师傅这类名字压到 Ⅰ 线以下。
    """
    def _neutral(v, fallback=float("nan")):
        return v if math.isfinite(v) else fallback

    rev5c = e["_rev5"] * 100
    rev3c = e["_rev3"] * 100
    ni5c = e["_ni5"] * 100
    ni3c = e["_ni3"] * 100
    ocf3c = e["_ocf3"] * 100
    ar3c = e["_ar3"] * 100
    share3p = e["_share3"] * 100

    consistency = (100 - min(abs(rev5c - rev3c) * 4, 100)
                   if math.isfinite(rev5c) and math.isfinite(rev3c) else 35)
    profit_cons = (100 - min(abs(ni5c - ni3c) * 2.5, 100)
                   if math.isfinite(ni5c) and math.isfinite(ni3c) else 35)
    growth = (0.35 * linear(rev5c, 3, 15) + 0.25 * linear(rev3c, 2, 14)
              + 0.20 * consistency + 0.20 * profit_cons)

    # 盈利 25：ROE 均值/最差年 + 毛利率地板
    # 高周转薄利豁免（对应错杀 skill 豁免 C）：ROE≥18 且现金转化好且无 OCF 负年 → 薄利不再拖累
    fcf_conv = _neutral(e["_fcf_conv"])
    high_turn = (math.isfinite(e["_roe_mean"]) and e["_roe_mean"] >= 18
                 and (not math.isfinite(fcf_conv) or fcf_conv >= 0.6) and e["_ocf_neg"] == 0)
    gross_sub = linear(e["_gross"], 15, 60)
    npm_sub = linear(e["_npm"], 5, 20)
    if high_turn:
        gross_sub = max(gross_sub, 45)
        npm_sub = max(npm_sub, 45)
    profit = (0.50 * linear(e["_roe_mean"], 10, 20) + 0.25 * linear(e["_roe_min"], 0, 12)
              + 0.25 * gross_sub)

    ar_gap = (rev3c - ar3c) if math.isfinite(ar3c) else float("nan")
    cash = (0.15 * linear(ocf3c, 0, 15)
            + 0.20 * linear(fcf_conv, 0.5, 1.2)
            + 0.20 * linear(_neutral(e["_fcf_pos"]) * 100, 50, 100)
            + 0.15 * clamp(100 - e["_ocf_neg"] * 25, 0, 100)
            + 0.15 * linear(ar_gap, -8, 4)
            + 0.15 * npm_sub)

    debt = _neutral(e["_debt_assets"], 65.0)
    capital = (0.35 * linear(_neutral(e["_roa"]), 4, 14)
               + 0.25 * linear(65 - debt, 0, 45)
               + 0.20 * linear(_neutral(e["_intcov"], 100.0), 2, 12)
               + 0.20 * linear(1.5 - _neutral(e["_debt_eq"], 1.5), 0, 1.5))

    shareholder = linear(2 - share3p, 0, 2)   # 只含股本纪律（无分红史），权重 5%

    penalty = 0.0
    flags = []
    qrev, qni = _neutral(e["_qrev"]), _neutral(e["_qni"])
    if (math.isfinite(qrev) and qrev > 60) or (math.isfinite(qni) and qni > 80):
        penalty += 12; flags.append("最新年增速异常")
    if math.isfinite(ni5c) and math.isfinite(rev5c) and ni5c - rev5c > 20:
        penalty += 7; flags.append("利润增速显著快于营收")
    if e["_roe_mean"] > 40:
        penalty += 6; flags.append("ROE均值>40%")
    if math.isfinite(ar3c) and ar_gap < -8:
        penalty += 8; flags.append("应收增速>营收")
    if ocf3c < -5:
        penalty += 8; flags.append("OCF3Y萎缩>5%")
    if e.get("_fcf5neg"):
        penalty += 8; flags.append("多数年份FCF为负")
    if share3p > 2:
        penalty += 6; flags.append("股本膨胀>2%")
    if e["_ocf_neg"] >= 3:
        penalty += 8; flags.append("OCF负年数≥3")

    total = round(clamp(0.20 * growth + 0.28 * profit + 0.27 * cash + 0.20 * capital
                        + 0.05 * shareholder - penalty, 0, 100), 1)
    return total, flags


# ── 主流程 ───────────────────────────────────────────────

def main():
    parser = ArgumentParser(description="港股未收录高分企业候选池构建")
    parser.add_argument("--min-cap", type=float, default=MIN_MCAP_B, help="流通市值下限 HKD B")
    parser.add_argument("--min-score", type=float, default=MIN_SCORE, help="质量分入池下限")
    parser.add_argument("--codes", default="", help="只对指定 Tiger 5 位码(逗号)跑财务(测试)")
    parser.add_argument("--limit", type=int, default=0, help="只对前 N 家跑财务(测试)")
    parser.add_argument("--no-cache", action="store_true", help="忽略缓存强制重拉")
    args = parser.parse_args()

    out_dir = ROOT / "data" / "screens"
    out_dir.mkdir(parents=True, exist_ok=True)
    pool_path = out_dir / "港股高分候选池.json"
    csv_path = out_dir / f"港股高分候选池_{date.today().isoformat()}.csv"

    print("=" * 62)
    print(f" 港股未收录高分企业候选池  (min-cap={args.min_cap}B, min-score={args.min_score})")
    print("=" * 62)

    # ── 1. 宇宙（Tiger 仅市值门槛） ──
    universe = tiger_universe(args.min_cap)
    print(f"[Tiger] 流通市值≥HKD {args.min_cap}B → {len(universe)} 家")

    wl = _watchlist_hk()
    low = _low_registry_hk()
    index_map = _index_hk_map()
    print(f"[排除集] watchlist .HK {len(wl)} + 低分登记 .HK {len(low)}；"
          f"[公司索引港股节] {len(index_map)} 家")

    targets = [u for u in universe if u["代码5"] not in wl and u["代码5"] not in low]
    print(f"[硬排后] {len(targets)} 家（其余已在 watchlist/低分登记）")

    if args.codes:
        wanted = {_code5(c) for c in args.codes.split(",") if c.strip()}
        targets = [t for t in targets if t["代码5"] in wanted]
        print(f"[codes] 指定 {len(targets)} 家")
    elif args.limit > 0:
        targets = targets[:args.limit]
        print(f"[limit] 前 {args.limit} 家")

    # ── 2. yfinance 财务（带缓存） ──
    cache_dir = ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / FS_CACHE_FILE
    cache = {}
    if cache_path.exists() and not args.no_cache:
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    to_fetch = [t for t in targets if t["Yahoo代码"] not in cache or args.no_cache]
    print(f"[yfinance缓存] 命中 {len(targets) - len(to_fetch)}，需拉 {len(to_fetch)}")
    fetched = {}
    done = 0
    total = len(to_fetch)
    with ThreadPoolExecutor(max_workers=FS_WORKERS) as ex:
        futs = {ex.submit(fetch_hk_quality, t["Yahoo代码"]): t for t in to_fetch}
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                fetched[t["Yahoo代码"]] = fut.result()
            except Exception as exc:
                fetched[t["Yahoo代码"]] = {"_ok": False, "名称": "", "行业": "", "_err": str(exc)[:120]}
            done += 1
            if done % 25 == 0:
                print(f"  … yfinance {done}/{total}")
    cache.update(fetched)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for v in fetched.values() if v.get("_ok"))
    fin = sum(1 for v in fetched.values() if v.get("_financial"))
    print(f"[yfinance] 本次 {ok} 可用 / {fin} 金融剔除 / {total - ok - fin} 数据不足")

    # ── 3/4/5. 行业过滤已在 fetch 内；覆盖标签 + 打分 ──
    today = date.today().isoformat()
    old_by_code = {}
    if pool_path.exists():
        try:
            for r in json.loads(pool_path.read_text(encoding="utf-8")):
                if isinstance(r, dict) and r.get("代码"):
                    old_by_code[r["代码"]] = r
        except Exception:
            pass

    pool_rows, audit_excluded, dropped = [], 0, 0
    for t in targets:
        e = cache.get(t["Yahoo代码"]) or {}
        if not e.get("_ok"):
            if e.get("_financial"):
                continue          # 金融/REIT 静默剔除
            dropped += 1
            continue
        score, flags = quality_score(e)
        if score < args.min_score:
            dropped += 1
            continue
        code5 = t["代码5"]
        labels, zwjc = _coverage_labels(code5, e.get("名称"), index_map)
        name = zwjc or e.get("名称") or code5
        tier = "Ⅰ候选" if score >= 70 else "Ⅱ候选"
        row = {
            "代码": f"{code5}.HK", "Tiger代码": t["Tiger代码"], "Yahoo代码": t["Yahoo代码"],
            "板块": "港", "简称": name, "行业": e.get("行业", ""),
            "池内档位": tier, "质量分": score,
            "覆盖": "/".join(labels) if labels else "全新",
            "管理层红旗": "RunB核",   # 港股无批量红旗 → Run B 逐家 Web 核
            "流通市值_亿港元": t["流通市值_亿港元"],
            "review_status": (old_by_code.get(f"{code5}.HK") or {}).get("review_status", "pending"),
            "reviewed_date": (old_by_code.get(f"{code5}.HK") or {}).get("reviewed_date", ""),
            "notes": (old_by_code.get(f"{code5}.HK") or {}).get("notes", ""),
            "进入池日期": (old_by_code.get(f"{code5}.HK") or {}).get("进入池日期", today),
            **{k: v for k, v in e.items() if not k.startswith("_")},
            "量化警示": "；".join(flags) or "无",
        }
        pool_rows.append(row)

    pool_rows.sort(key=lambda r: -r["质量分"])
    pool_path.write_text(json.dumps(pool_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[JSON] {pool_path} ({len(pool_rows)} 只)")

    csv_cols = ["代码", "简称", "行业", "池内档位", "质量分", "5Y ROE均值_%", "5Y ROE最低_%",
                "营收5年CAGR_%", "净利润5年CAGR_%", "毛利率均值_%", "净利率均值_%",
                "FCF转化率", "FCF正年数占比_%", "OCF负年数", "资产负债率_%",
                "流通市值_亿港元", "管理层红旗", "覆盖", "量化警示", "review_status", "reviewed_date"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(pool_rows)
    print(f"[CSV] {csv_path}")

    tier1 = [r for r in pool_rows if r["池内档位"] == "Ⅰ候选"]
    tier2 = [r for r in pool_rows if r["池内档位"] == "Ⅱ候选"]
    print(f"\n[池分布] Ⅰ候选={len(tier1)}  Ⅱ候选={len(tier2)}  (数据不足/低分 {dropped})")
    print("\n[Ⅰ候选 top20 - 供分批 AI 复核]:")
    for r in tier1[:20]:
        print(f"  {r['质量分']:5.1f}  {r['代码']} {r['简称'][:14]:<15s} "
              f"{r.get('行业','')[:12]:<13s} ROE={r.get('5Y ROE均值_%')}%  [{r['覆盖']}]")


if __name__ == "__main__":
    main()
