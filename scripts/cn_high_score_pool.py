"""A股「未收录高分企业」候选池构建 —— 不看价格，纯企业质量 + 管理层红旗 + 覆盖率标签.

定位：cn-quality-mispricing-screen（错杀筛选）的价格/估值/跌幅导向相反，本脚本只按「企业质量能否支撑
B_GROWTH/A_CORE 级（深分≥70/76 + 管档≥70/76）」粗排全 A 股中尚未被知识库深度覆盖的公司。
产出是一个**持久候选池**（大列表=数据资产），由 skill 层每次对池头 N 家分批复核消化，避免一次性大输出。

流水线：
  Step 1  全集+门：CNINFO 全A → 剔除 ST/退市/亏损(pe_ttm≤0)/流通市值过小 → 剔除 watchlist + 低分公司登记
  Step 2  逐只 fs（10 年窗口）→ 「企业质量分 0-100」= 成长25 + 盈利25(10Y ROE均值/最低) + 现金流25
          + 资本15 + 股本与股东回报10 − 异常惩罚；非标审计(近端)直接剔除
  Step 3  管理层红旗层：理杏仁 hot/ple(质押) / hot/mssc(大股东) / hot/esc(高管) / hot/df(分红融资) 批量打标
  Step 4  覆盖率标签（宽松口径：只打标不排除）：有公司页 / 有深度分析 / 有管理层档案
  Step 5  落池：A股高分候选池.json（含 review_status，供 skill 分批复核写回）+ 当日 CSV 快照

Usage:
    python scripts/cn_high_score_pool.py                     # 今天
    python scripts/cn_high_score_pool.py --date 2026-09-05
    python scripts/cn_high_score_pool.py --limit 50          # 冒烟
    python scripts/cn_high_score_pool.py --min-cap 80        # 市值下限(流通,亿)调大→池更小
    python scripts/cn_high_score_pool.py --min-score 50      # 校准期把阈值放低看分布
    python scripts/cn_high_score_pool.py --skip-hot          # 跳过管理层红旗批量(调试)

Output:
    data/screens/A股高分候选池.json                       （状态源，跨调用持久）
    data/screens/A股高分候选池_YYYY-MM-DD.csv              （可读快照）

复用（勿重造）：
    cn_mispricing_screen: cninfo_universe / lixinger_fundamental / resolve_trade_date /
                          number / clamp / linear / _cagr / cn_to_ts / board_of / FUNDAMENTAL_METRICS
    forecast_monitor:     load_watchlist_a_share_codes
Scope 说明：
    fs/non_financial 不覆盖银行/券商/保险 → 金融股本版自动无数据，不入池（与错杀 skill 一致）。
"""

from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import sys
import time
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from scripts.cn_mispricing_screen import (  # noqa: E402
    FUNDAMENTAL_METRICS,
    _cagr,
    board_of,
    clamp,
    cn_to_ts,
    cninfo_universe,
    linear,
    lixinger_fundamental,
    number,
    resolve_trade_date,
)
from scripts.lixinger_api import get_client  # noqa: E402

# ── 参数（初值，首跑校准后回填） ───────────────────────
MIN_CMCAP_YI = 50        # 最低流通市值 CNY 亿（流动性/可研究性门槛，非估值）
MIN_SCORE = 60           # 最低质量分入池（Ⅱ候选下限；≥70 为 Ⅰ候选）
FS_YEARS = 10            # 逐只拉多年年报窗口（支撑 10Y ROE 均值/最低）
FS_WORKERS = 3           # 理杏仁 fs 并发（保守值，偶发限流）
PLEDGE_RED_RATIO = 0.10  # 质押占总股本 >10% → WATCH 红旗
SELL_RED_RATIO = -0.005  # 大股东/高管近1年净减持股本比例 < -0.5% → WATCH 红旗

# 基本面上下文列（仅展示，不参与质量分）
FUNDAMENTAL_METRICS = FUNDAMENTAL_METRICS

FS_CACHE_FILE = "cn_high_score_fs_cache.json"   # fs 原始指标缓存（data/cache/ 下），重打分/调阈值免重复拉取

# 逐只 fs 指标：参考 cn_mispricing_screen.FS_METRICS，去掉了估值类，扩 10 年 + 分红率
FS_METRICS = [
    "y.ps.toi.t", "y.ps.np.t", "y.ps.ebit.t", "y.ps.ieife.t", "y.ps.da.t", "y.ps.d_np_r.t",
    "y.cfs.ncffoa.t",
    "y.bs.ar.t", "y.bs.i.t", "y.bs.tsc.t",
    "y.m.roe.t", "y.m.roa.t", "y.m.gp_m.t", "y.m.np_s_r.t",
    "y.m.tl_ta_r.t", "y.m.fcf.t",
]

AUDIT_OK = {"unqualified_opinion"}
GLOB_COVER = [
    ("公司页", "01-公司"),
    ("深度分析", "深度分析"),
    ("管理层档案", "管理层档案"),
]

# ── 数值工具 ─────────────────────────────────────────────

# 低分登记表里 6 位 A股代码（裸或带 .SH/.SZ/.BJ）
re_digits = re.compile(r"(?<!\d)(\d{6})(?:\.(?:SH|SZ|BJ))?")

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


def _series(recs, tbl, fld):
    """从 fs 记录（新→旧）提取某 y.* 指标序列。"""
    out = []
    for rec in recs:
        try:
            v = rec["y"][tbl][fld]["t"]
            out.append(_nan(v))
        except (KeyError, TypeError):
            out.append(float("nan"))
    return out


def _latest(recs, tbl, fld):
    s = _series(recs, tbl, fld)
    for v in s:
        if math.isfinite(v):
            return v
    return float("nan")


def _by_year(recs):
    """按会计年度去重（restatement 可能同一年多条），返回新→旧年记录。"""
    best = {}
    for rec in sorted(recs, key=lambda r: str(r.get("date", "")), reverse=True):
        y = str(rec.get("date", ""))[:4]
        if y and y not in best:
            best[y] = rec
    return [best[k] for k in sorted(best, reverse=True)]


# ── 排除集：watchlist + 低分公司登记 ────────────────────

def _load_low_registry():
    """解析 00-首页/低分公司登记.md 里出现的全部 6 位 A股代码（格式混杂：裸/带后缀）。

    宽松口径只作为硬排除之一；只挑 6 位连续数字，港股(01099)与年份(2026)天然不受影响。
    """
    path = ROOT / "00-首页" / "低分公司登记.md"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    codes = set()
    for m in re_digits.finditer(text):
        codes.add(m.group(1))
    return codes


def _watchlist_exclude():
    """返回 {6位A股代码}：strategic/core/growth(复用 forecast_monitor) + out_of_scope 的 .SH/.SZ。"""
    out = set()
    try:
        from scripts.forecast_monitor import load_watchlist_a_share_codes
        out.update(load_watchlist_a_share_codes().keys())
    except Exception as exc:
        print(f"  ⚠ load_watchlist_a_share_codes 失败: {exc}")
    wl_path = ROOT / "data" / "watchlist_out_of_scope.json"
    if wl_path.exists():
        try:
            data = json.loads(wl_path.read_text(encoding="utf-8"))
            for e in data.get("entries", []):
                code = str(e.get("code", ""))
                if code.endswith((".SH", ".SZ")):
                    out.add(code.split(".")[0])
        except Exception as exc:
            print(f"  ⚠ out_of_scope 读取失败: {exc}")
    return out


# ── Step 1c 覆盖标签（宽松口径，只打标不排除） ─────────

def _coverage_labels(zwjc):
    """用 zwjc 简称 glob 顶层研究目录，返回标签 list。"""
    if not zwjc:
        return []
    found = []
    for label, rel in GLOB_COVER:
        if glob.glob(str(ROOT / rel / f"{zwjc}*.md")):
            found.append(label)
    return found


# ── Step 2: 逐只 fs 10 年 + 质量指标 ───────────────────

def fetch_quality_fs(code, screen_date):
    """逐只拉 10 年年报，返回质量分所需指标 dict + 审计意见；数据不足返回 None。"""
    lx = get_client()
    start = (datetime.fromisoformat(screen_date) - timedelta(days=365 * FS_YEARS)).strftime("%Y-%m-%d")
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
            time.sleep(1.0 + attempt * 1.0)
    if not isinstance(r, list) or not r:
        return None

    recs = _by_year(r)
    if len(recs) < 3:
        return None

    # 审计（近端非标即剔除，repo 红线）
    audits = []
    for rec in recs[:3]:
        a = str(rec.get("auditOpinionType", "") or "")
        if a:
            audits.append(a)
    latest_audit = str(recs[0].get("auditOpinionType", "") or "")
    audit_red = bool(latest_audit) and latest_audit not in AUDIT_OK

    revs = _series(recs, "ps", "toi")
    nps = _series(recs, "ps", "np")
    ncfs = _series(recs, "cfs", "ncffoa")
    ars = _series(recs, "bs", "ar")
    invs = _series(recs, "bs", "i")
    tscs = _series(recs, "bs", "tsc")
    roes = _series(recs, "m", "roe")
    gps = _series(recs, "m", "gp_m")
    nprs = _series(recs, "m", "np_s_r")
    fcf = _series(recs, "m", "fcf")
    dnp = _series(recs, "ps", "d_np_r")

    toi0, np0 = revs[0], nps[0]
    ebit0 = _latest(recs, "ps", "ebit")
    ie0 = _latest(recs, "ps", "ieife")
    roa = _latest(recs, "m", "roa")
    debt = _latest(recs, "m", "tl_ta_r")

    if not math.isfinite(ebit0) and not math.isfinite(np0):
        return None  # 财务数据过少

    # 5/3 年 CAGR（净利可能为负 → _cagr 会丢）
    rev5 = _cagr(revs, 5)
    rev3 = _cagr(revs, 3)
    np5 = _cagr(nps, 5)
    np3 = _cagr(nps, 3)
    ocf3 = _cagr(ncfs, 3)
    ar3 = _cagr(ars, 3)
    inv3 = _cagr(invs, 3)
    share3 = _cagr(tscs, 3)

    # 盈利持续质量
    roe10_mean = 100 * _nmean(roes)
    roe10_min = 100 * _nmin(roes)
    gross_mean = 100 * _nmean(gps)
    npm_mean = 100 * _nmean(nprs)

    # FCF：近5年累计 + 正年数占比 + 转化率
    fcf5 = fcf[:5]
    fcf5_fin = [v for v in fcf5 if math.isfinite(v)]
    fcf5sum = sum(fcf5_fin) if fcf5_fin else float("nan")
    np5_fin = [v for v in nps[:5] if math.isfinite(v)]
    np5sum = sum(np5_fin) if np5_fin else 0.0
    fcf5_conv = (fcf5sum / np5sum) if (math.isfinite(fcf5sum) and np5sum > 0) else float("nan")
    pos = [v for v in fcf5_fin if v >= 0]
    fcf_pos_ratio = (len(pos) / len(fcf5_fin)) if fcf5_fin else float("nan")

    # OCF 负年数（全窗口）
    ocf_neg_years = sum(1 for v in ncfs if math.isfinite(v) and v < 0)

    # 股东回报：近5年分红率均值(0-100%)
    dnp5 = [v for v in dnp[:5] if math.isfinite(v)]
    payout_mean5 = 100 * _nmean(dnp5) if dnp5 else float("nan")

    # 最新年度同比（增速异常用，年报 yoy 代理季报）
    def _yoy(arr):
        if len(arr) >= 2 and math.isfinite(arr[0]) and math.isfinite(arr[1]) and arr[1]:
            return (arr[0] - arr[1]) / abs(arr[1])
        return float("nan")
    qrev = 100 * _yoy(revs)
    qni = 100 * _yoy(nps)

    # 资本结构（最新）
    debt_equity = (debt / (1 - debt)) if (math.isfinite(debt) and debt < 1) else float("nan")
    interest_cov = 100.0 if (math.isfinite(ebit0) and (not math.isfinite(ie0) or ie0 == 0)) else (
        abs(ebit0 / ie0) if (math.isfinite(ebit0) and math.isfinite(ie0) and ie0 != 0) else float("nan"))

    return {
        "recs_count": len(recs),
        "审计意见": latest_audit or "none",
        "审计红旗": audit_red,
        "营收5年CAGR_%": (100 * rev5) if math.isfinite(rev5) else "",
        "营收3年CAGR_%": (100 * rev3) if math.isfinite(rev3) else "",
        "净利润5年CAGR_%": (100 * np5) if math.isfinite(np5) else "",
        "净利润3年CAGR_%": (100 * np3) if math.isfinite(np3) else "",
        "经营现金流3年CAGR_%": (100 * ocf3) if math.isfinite(ocf3) else "",
        "应收账款3年CAGR_%": (100 * ar3) if math.isfinite(ar3) else "",
        "存货3年CAGR_%": (100 * inv3) if math.isfinite(inv3) else "",
        "10Y ROE均值_%": round(roe10_mean, 2),
        "10Y ROE最低_%": round(roe10_min, 2) if math.isfinite(roe10_min) else "",
        "最新ROE_%": (100 * roe_l if math.isfinite(roe_l := _latest(recs, "m", "roe")) else ""),
        "毛利率10Y均值_%": round(gross_mean, 2) if math.isfinite(gross_mean) else "",
        "净利率10Y均值_%": round(npm_mean, 2) if math.isfinite(npm_mean) else "",
        "资产负债率_%": (100 * debt) if math.isfinite(debt) else "",
        "ROA_%": (100 * roa) if math.isfinite(roa) else "",
        "利息保障倍数": round(interest_cov, 2) if math.isfinite(interest_cov) else "",
        "长期债务权益比": round(debt_equity, 4) if math.isfinite(debt_equity) else "",
        "5Y累计FCF": round(fcf5sum, 0) if math.isfinite(fcf5sum) else "",
        "FCF5Y转化率": round(fcf5_conv, 3) if math.isfinite(fcf5_conv) else "",
        "FCF正年数占比_%": round(100 * fcf_pos_ratio, 0) if math.isfinite(fcf_pos_ratio) else "",
        "OCF负年数": ocf_neg_years,
        "分红率5Y均值_%": round(payout_mean5, 1) if math.isfinite(payout_mean5) else "",
        "股数3年CAGR_%": (100 * share3) if math.isfinite(share3) else "",
        "最新年度营收同比_%": round(qrev, 2) if math.isfinite(qrev) else "",
        "最新年度净利同比_%": round(qni, 2) if math.isfinite(qni) else "",
        # 原始数组（评分用）
        "_roe10": roe10_mean, "_roe10min": roe10_min, "_gross": gross_mean, "_npm": npm_mean,
        "_fcf5sum": fcf5sum, "_fcf5conv": fcf5_conv, "_fcfpos": fcf_pos_ratio,
        "_ocfneg": ocf_neg_years, "_dnp5": payout_mean5, "_share3": share3,
        "_rev5": rev5, "_rev3": rev3, "_np5": np5, "_np3": np3, "_ocf3": ocf3,
        "_ar3": ar3, "_qrev": qrev, "_qni": qni, "_debt": debt, "_debt_eq": debt_equity,
        "_roa": roa, "_intcov": interest_cov,
    }


# ── 企业质量分（无估值维度） ────────────────────────────

def quality_score(extra):
    """成长25 + 盈利25 + 现金流25 + 资本15 + 股本与股东回报10 − 惩罚。

    单位约定：`extra` 里 CAGR/ROE/毛利/净利率等已存成百分数(_roe10等) 或小数(_rev5等)。
    缺失值保持 NaN → linear()/线性段返回中性 35，避免把"历史不足"误罚成 0。
    """
    rev5c = extra["_rev5"] * 100     # 分数 → 百分点；nan 保留
    rev3c = extra["_rev3"] * 100
    np5c = extra["_np5"] * 100
    np3c = extra["_np3"] * 100
    ocf3c = extra["_ocf3"] * 100
    ar3c = extra["_ar3"] * 100
    share3p = extra["_share3"] * 100

    roe10 = extra["_roe10"]          # 已是 %
    roe10min = extra["_roe10min"]
    gross = extra["_gross"]
    npm = extra["_npm"]
    fcf5conv = extra["_fcf5conv"]    # 小数
    fcfpos = extra["_fcfpos"]        # 小数
    ocfneg = extra["_ocfneg"]
    dnp5 = extra["_dnp5"]            # %
    debt = extra["_debt"]            # 小数(负债率)；缺失按中性 65%
    if not math.isfinite(debt):
        debt = 0.65
    roa = extra["_roa"]              # %
    intcov = extra["_intcov"]        # 倍数；缺失中性 100
    if not math.isfinite(intcov):
        intcov = 100.0
    debt_eq = extra["_debt_eq"]      # 小数
    if not math.isfinite(debt_eq):
        debt_eq = 1.5
    qrev = extra["_qrev"]            # %
    qni = extra["_qni"]

    # 增长 25（CAGR 均为百分点；跨期一致性与参考错杀脚本同构）
    # ⚠️ 任何一侧 NaN 必须回落中性 35，绝不允许 NaN 泄漏进总和（否则 clamp(NaN)→100 假满分）
    consistency = (100 - min(abs(rev5c - rev3c) * 4, 100)
                   if math.isfinite(rev5c) and math.isfinite(rev3c) else 35)
    profit_cons = (100 - min(abs(np5c - np3c) * 2.5, 100)
                   if math.isfinite(np5c) and math.isfinite(np3c) else 35)
    growth = (
        0.35 * linear(rev5c, 3, 15)
        + 0.25 * linear(rev3c, 2, 14)
        + 0.20 * consistency
        + 0.20 * profit_cons
    )

    # 盈利质量 25：10Y ROE 均值 + 最差年 ROE（可持续性）+ 毛利率地板
    profit = (
        0.55 * linear(roe10, 10, 20)
        + 0.25 * linear(roe10min, 0, 12)
        + 0.20 * linear(gross, 15, 60)
    )

    # 现金流 25：OCF 趋势 + 5Y FCF 转化/正年数 + 应收剪刀差 + 净利率
    ar_gap = (rev3c - ar3c) if math.isfinite(ar3c) else float("nan")
    cash = (
        0.15 * linear(ocf3c, 0, 15)
        + 0.20 * linear(fcf5conv, 0.5, 1.3)
        + 0.20 * linear(fcfpos * 100, 50, 100)
        + 0.15 * clamp(100 - ocfneg * 25, 0, 100)
        + 0.15 * linear(ar_gap, -8, 4)
        + 0.15 * linear(npm, 5, 20)
    )

    # 资本结构 15（debt 已为 65 中性；1.5-debt_eq 同参考）
    capital = (
        0.40 * linear(roa, 4, 14)
        + 0.25 * linear(65 - debt * 100, 0, 45)
        + 0.20 * linear(intcov, 2, 12)
        + 0.15 * linear(1.5 - debt_eq, 0, 1.5)
    )

    # 股本与股东回报 10：股本纪律(少稀释) + 分红率(正信号，权重低不惩罚低分红好公司)
    shareholder = 0.50 * linear(2 - share3p, 0, 2) + 0.50 * linear(dnp5, 15, 50)

    penalty = 0.0
    flags = []
    if (math.isfinite(qrev) and qrev > 60) or (math.isfinite(qni) and qni > 80):
        penalty += 12; flags.append("最新年增速异常")
    if math.isfinite(np5c) and math.isfinite(rev5c) and np5c - rev5c > 20:
        penalty += 7; flags.append("利润增速显著快于营收")
    if roe10 > 40:
        penalty += 6; flags.append("10Y ROE均值>40%")
    if math.isfinite(ar3c) and ar_gap < -8:
        penalty += 8; flags.append("应收增速>营收")
    if ocf3c < -5:
        penalty += 8; flags.append("OCF3Y萎缩>5%")
    if math.isfinite(extra["_fcf5sum"]) and extra["_fcf5sum"] < 0:
        penalty += 8; flags.append("5Y累计FCF为负")
    if share3p > 2:
        penalty += 6; flags.append("股本膨胀>2%")
    if ocfneg >= 3:
        penalty += 8; flags.append("OCF负年数≥3")

    total = round(clamp(0.25 * growth + 0.25 * profit + 0.25 * cash + 0.15 * capital + 0.10 * shareholder - penalty, 0, 100), 1)
    return total, flags


# ── Step 3: 管理层红旗批量（理杏仁 hot/*，≤100/次） ─────

def fetch_hot_redflags(codes):
    """批量拉质押/大股东/高管/分红融资汇总，返回 {code: {flags:[], 字段}}。"""
    if not codes:
        return {}
    lx = get_client()
    out = {}
    for ep, label in [("cn/company/hot/ple", "质押"),
                      ("cn/company/hot/mssc", "大股东增减持"),
                      ("cn/company/hot/esc", "高管增减持"),
                      ("cn/company/hot/df", "分红融资")]:
        chunk = 100
        for i in range(0, len(codes), chunk):
            batch = codes[i:i + chunk]
            try:
                rows = lx.post(ep, {"stockCodes": batch})
            except Exception as exc:
                print(f"  ⚠ hot/{ep} 批次@{i} 失败: {exc}")
                continue
            if not isinstance(rows, list):
                continue
            for item in rows:
                code = item.get("stockCode")
                if not code:
                    continue
                rec = out.setdefault(code, {})
                rec["_hot_" + label] = item
            time.sleep(0.05)
    return out


def _flag_from_hot(rec):
    """从 hot 汇总生成 WATCH 红旗文案（仅明确信号，缺数据不惩罚）。"""
    flags = []
    ple = rec.get("_hot_质押") or {}
    ps_sc_r = number(ple.get("ps_sc_r"))  # 质押占总股本比例
    if math.isfinite(ps_sc_r) and ps_sc_r > PLEDGE_RED_RATIO:
        flags.append(f"质押占总股本{100 * ps_sc_r:.0f}%>10%")

    for label, key in [("大股东增减持", "mssc_cap_rc_y1"), ("高管增减持", "esc_cap_rc_y1")]:
        row = rec.get("_hot_" + label) or {}
        v = number(row.get(key))
        if math.isfinite(v) and v < SELL_RED_RATIO:
            flags.append(f"{label}近1年净减{100 * -v:.1f}%")
    return flags


# ── 主流程 ───────────────────────────────────────────────

def main():
    parser = ArgumentParser(description="A股未收录高分企业候选池构建")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--min-cap", type=float, default=MIN_CMCAP_YI, help="流通市值下限(亿)")
    parser.add_argument("--min-score", type=float, default=MIN_SCORE, help="质量分入池下限")
    parser.add_argument("--limit", type=int, default=0, help="仅对市值 top N 只做 fs（测试用）")
    parser.add_argument("--codes", default="", help="只对指定代码(逗号分隔6位)做 fs，跳过市值排序（测试用）")
    parser.add_argument("--skip-hot", action="store_true", help="跳过管理层红旗批量")
    parser.add_argument("--no-cache", action="store_true", help="忽略 fs 缓存强制重拉")
    args = parser.parse_args()

    screen_date = args.date
    out_dir = ROOT / "data" / "screens"
    out_dir.mkdir(parents=True, exist_ok=True)
    pool_path = out_dir / "A股高分候选池.json"
    csv_path = out_dir / f"A股高分候选池_{screen_date}.csv"

    print("=" * 62)
    print(f" A股未收录高分企业候选池 — {screen_date}  (min-cap={args.min_cap}亿, min-score={args.min_score})")
    print("=" * 62)

    trade_date = resolve_trade_date(screen_date)
    if trade_date != screen_date:
        print(f"[交易日] {screen_date} 非交易日 → {trade_date}")

    # ── Step 1a: 全集 + 排除 ──
    universe = cninfo_universe()
    print(f"[CNINFO] 全A股 {len(universe)} 只")
    if not universe:
        print("❌ CNINFO 无结果，终止。")
        return

    wl_exclude = _watchlist_exclude()
    low_exclude = _load_low_registry()
    print(f"[排除集] watchlist {len(wl_exclude)} 只 + 低分登记 {len(low_exclude)} 只")

    # ── Step 1b: 批量 fundamental（市值/PE 门槛，非估值） ──
    codes = [u["code"] for u in universe]
    name_map = {u["code"]: u["name"] for u in universe}
    fund = lixinger_fundamental(codes, trade_date)
    print(f"[理杏仁] fundamental 覆盖 {len(fund)}/{len(codes)}")

    candidates = []
    for u in universe:
        code = u["code"]
        zwjc = u["name"]
        if not zwjc:
            continue
        if "ST" in zwjc.upper() or "退" in zwjc:
            continue
        if code in wl_exclude or code in low_exclude:
            continue
        item = fund.get(code)
        if not item:
            continue
        cmc = number(item.get("cmc"))
        pe = number(item.get("pe_ttm"))
        cmc_yi = cmc / 1e8
        if not math.isfinite(pe) or pe <= 0:      # 盈利门槛（非估值）
            continue
        if not math.isfinite(cmc) or cmc_yi < args.min_cap:
            continue
        candidates.append({
            "代码": code, "TS代码": cn_to_ts(code), "板块": board_of(code), "简称": zwjc,
            "流通市值_亿": round(cmc_yi, 1),
            "总市值_亿": round(number(item.get("mc")) / 1e8, 1),
            "PE_TTM": pe,
            "股息率_%": round(100 * number(item.get("dyr")), 2),
            "PB": number(item.get("pb")),
        })
    print(f"[门槛] 排除ST/亏损/市值<{args.min_cap}亿 + watchlist/低分 → {len(candidates)} 只")

    if args.codes:
        wanted = {c for c in args.codes.split(",") if c.strip()}
        scored_targets = [c for c in candidates if c["代码"] in wanted]
        print(f"[codes] 仅对指定 {len(scored_targets)} 只（{args.codes}）做财务评分")
    else:
        scored_targets = candidates if args.limit <= 0 else sorted(
            candidates, key=lambda c: c["总市值_亿"], reverse=True)[:args.limit]
        if args.limit > 0:
            print(f"[limit] 仅对市值 top {len(scored_targets)} 只做财务评分")

    # ── Step 2: 逐只 fs 10 年 + 质量分（带缓存，重跑免拉取） ──
    cache_dir = ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / FS_CACHE_FILE
    fs_cache = {}
    if cache_path.exists() and not args.no_cache:
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("trade_date") == trade_date:
                fs_cache = data.get("entries", {})
        except Exception:
            pass

    to_fetch = [c for c in scored_targets if c["代码"] not in fs_cache or args.no_cache]
    print(f"[fs缓存] 命中 {len(scored_targets) - len(to_fetch)}/{len(scored_targets)}，需拉取 {len(to_fetch)}")
    fetched = {}
    done = 0
    total = len(to_fetch)
    with ThreadPoolExecutor(max_workers=FS_WORKERS) as ex:
        futs = {ex.submit(fetch_quality_fs, c["代码"], screen_date): c for c in to_fetch}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                fetched[c["代码"]] = fut.result()
            except Exception:
                fetched[c["代码"]] = None
            done += 1
            if done % 50 == 0:
                print(f"  … 财务评分 {done}/{total}")
    got = sum(1 for v in fetched.values() if v)
    print(f"[理杏仁 fs] 本次拉取 {got}/{total} 只（其余=数据不足/非金融）")

    # 合并缓存：缓存 None 也保留（数据不足无需反复拉）
    fs_cache.update({k: v for k, v in fetched.items() if v is not None})
    cache_path.write_text(json.dumps(
        {"trade_date": trade_date, "entries": fs_cache}, ensure_ascii=False), encoding="utf-8")
    results = {k: fs_cache.get(k) for k in [c["代码"] for c in scored_targets]}

    pool_rows = []
    audit_excluded = 0
    below = 0
    for c in candidates:
        extra = results.get(c["代码"])
        if not extra:
            continue
        if extra.get("审计红旗"):
            audit_excluded += 1
            continue
        score, flags = quality_score(extra)
        if score < args.min_score:
            below += 1
            continue
        tier = "Ⅰ候选" if score >= 70 else "Ⅱ候选"
        row = {**c, **{k: v for k, v in extra.items() if not k.startswith("_")}}
        row.update({
            "质量分": score, "池内档位": tier, "量化警示": "；".join(flags) or "无",
            "覆盖": "/".join(_coverage_labels(c["简称"])) or "全新",
        })
        pool_rows.append((score, row))

    pool_rows.sort(key=lambda x: x[0], reverse=True)
    print(f"[质量分档] 入池 {len(pool_rows)}（Ⅰ≥70 / Ⅱ≥60），审计红旗剔除 {audit_excluded}，低于{args.min_score}分 {below}")

    ordered_codes = [r[1]["代码"] for r in pool_rows]
    hot = fetch_hot_redflags(ordered_codes) if (ordered_codes and not args.skip_hot) else {}
    for _, row in pool_rows:
        code = row["代码"]
        rec = hot.get(code)
        flags = _flag_from_hot(rec) if rec else []
        row["管理层红旗"] = "；".join(flags) or "无"
        # 展示用分红融资信息（不参与红旗判定，避免误伤年轻/低分红好公司）
        df = (rec or {}).get("_hot_分红融资") or {}
        dfr = number(df.get("dfr_fs"))
        row["分红融资比"] = round(dfr, 2) if math.isfinite(dfr) else ""
    if not args.skip_hot:
        n_watch = sum(1 for _, r in pool_rows if r["管理层红旗"] != "无")
        print(f"[管理层红旗] 批量打标完成，{n_watch} 只带 WATCH 红旗")

    # ── 合并旧池 review 状态（刷新不丢消化进度） ──
    old_by_code = {}
    if pool_path.exists():
        try:
            for r in json.loads(pool_path.read_text(encoding="utf-8")):
                if isinstance(r, dict) and r.get("代码"):
                    old_by_code[r["代码"]] = r
        except Exception:
            pass
    today = date.today().isoformat()
    for _, row in pool_rows:
        old = old_by_code.get(row["代码"])
        row["review_status"] = (old or {}).get("review_status", "pending") if old else "pending"
        row["reviewed_date"] = (old or {}).get("reviewed_date", "") if old else ""
        row["notes"] = (old or {}).get("notes", "") if old else ""
        row["进入池日期"] = (old or {}).get("进入池日期", today) if old else today

    # ── 落 JSON + CSV ──
    pool_rows_sorted = [r for _, r in pool_rows]
    pool_path.write_text(json.dumps(pool_rows_sorted, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[JSON] {pool_path} ({len(pool_rows_sorted)} 只)")

    csv_cols = [
        "代码", "TS代码", "板块", "简称", "池内档位", "质量分", "10Y ROE均值_%", "10Y ROE最低_%",
        "营收5年CAGR_%", "净利润5年CAGR_%", "毛利率10Y均值_%", "净利率10Y均值_%",
        "FCF5Y转化率", "FCF正年数占比_%", "OCF负年数", "分红率5Y均值_%", "资产负债率_%",
        "流通市值_亿", "总市值_亿", "PE_TTM", "股息率_%", "审计意见", "管理层红旗", "分红融资比",
        "覆盖", "量化警示", "review_status", "reviewed_date",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols, extrasaction="ignore")
        w.writeheader()
        for row in pool_rows_sorted:
            w.writerow(row)
    print(f"[CSV] {csv_path}")

    # ── 终端摘要 ──
    tier1 = [r for r in pool_rows_sorted if r["池内档位"] == "Ⅰ候选"]
    tier2 = [r for r in pool_rows_sorted if r["池内档位"] == "Ⅱ候选"]
    print(f"\n[池分布] Ⅰ候选={len(tier1)}  Ⅱ候选={len(tier2)}")
    print(f"\n[Ⅰ候选 top20 - 未复核质量最高，供分批 AI 复核]:")
    for r in tier1[:20]:
        flag = r["管理层红旗"]
        cov = r["覆盖"]
        print(f"  {r['质量分']:5.1f}  {r['代码']} {r['简称']:<10s} ROE10={r.get('10Y ROE均值_%')}%  "
              f"{flag if flag != '无' else ''}  [{cov}]")


if __name__ == "__main__":
    main()
