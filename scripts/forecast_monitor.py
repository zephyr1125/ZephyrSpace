#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""财报预告监控引擎：CNINFO 清单 → 理杏仁补数据 → JSON 增量存储 → 渲染 MD。

数据链:
  1) CNINFO hisAnnouncement/query 全市场按日期区间拉「业绩预告」清单
  2) 理杏仁 fundamental/non_financial 批量补估值（PE/PB/PS/市值/股息率）
  3) 理杏仁 fs/non_financial 逐只补最近季度营收/净利润 → 算同比
  4) 理杏仁 company/industries 逐只补申万2021二级行业分类
  5) CNINFO hisAnnouncement/query 拉「正式半年报」→ 与 Watchlist 交叉比对
  6) 合并进 data/forecast_scan/<label>.json（按 code 去重，保留最新一次）
  7) 渲染 02-主题/财报预告/<label>.md（行业聚合表 + Watchlist 半年报告警 + 个股预告列表）

用法:
  python scripts/forecast_monitor.py 2026-06-01 2026-07-03
  python scripts/forecast_monitor.py 2026-06-01 2026-07-03 --label 2026Q2财报预告
  # label 缺省时按结束日期所在季度自动生成，如 2026Q2财报预告
"""
import sys
import io
import re
import os
import json
import time
import gzip
import argparse
import datetime as dt

import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.cninfo_api import CninfoClient
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(VAULT, "data", "forecast_scan")
DOC_DIR = os.path.join(VAULT, "02-主题", "财报预告")

# ================= CNINFO =================
CNINFO_ENDPOINT = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CATEGORY_FORECAST = "category_yjygjxz_szsh"
CATEGORY_SEMIANNUAL = "category_bndbg_szsh"

# ================= Watchlist =================
WATCHLIST_FILES = [
    ("S_STRATEGIC", "data/watchlist_strategic.json"),
    ("A_CORE", "data/watchlist_core.json"),
    ("B_GROWTH", "data/watchlist_growth.json"),
]


def cninfo_forecasts(start, end, plate="sz;sh;bj", page_size=30, sleep=0.3,
                     category=None):
    """拉取 CNINFO 公告清单。category 默认 CATEGORY_FORECAST（业绩预告），
    可传入 CATEGORY_SEMIANNUAL 拉取正式半年报。"""
    if category is None:
        category = CATEGORY_FORECAST
    out, page = [], 1
    while True:
        r = requests.post(
            CNINFO_ENDPOINT,
            data={
                "pageNum": str(page), "pageSize": str(page_size),
                "column": "szse", "tabName": "fulltext", "plate": plate,
                "stock": "", "searchkey": "", "secid": "",
                "category": category, "trade": "",
                "seDate": f"{start}~{end}", "sortName": "time",
                "sortType": "desc", "isHLtitle": "true",
            },
            headers={"Accept": "application/json",
                     "Referer": "http://www.cninfo.com.cn/",
                     "User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        d = r.json()
        anns = d.get("announcements") or []
        if not anns:
            break
        for a in anns:
            ts = a.get("announcementTime", 0) / 1000
            beijing = dt.datetime.utcfromtimestamp(ts) + dt.timedelta(hours=8)
            out.append({
                "code": a.get("secCode", ""),
                "name": a.get("secName", ""),
                "title": a.get("announcementTitle", "").replace("<em>", "").replace("</em>", ""),
                "date": beijing.strftime("%Y-%m-%d"),
                "url": f"https://static.cninfo.com.cn/{a.get('adjunctUrl', '')}",
            })
        if not d.get("hasMore"):
            break
        page += 1
        time.sleep(sleep)
    # 同一 code 多条时保留最新公告（补充说明等），并记录条数
    by_code = {}
    for a in sorted(out, key=lambda x: x["date"], reverse=True):
        if a["code"] not in by_code:
            by_code[a["code"]] = a
    return list(by_code.values())


def load_watchlist_a_share_codes():
    """读取三个 watchlist JSON，返回 {bare_6digit_code: {name, tier, code_with_suffix}}。
    仅匹配 A 股（.SH/.SZ 后缀），CNINFO 不覆盖 H 股/美股。"""
    watchlist = {}
    for tier, rel_path in WATCHLIST_FILES:
        full_path = os.path.join(VAULT, rel_path)
        if not os.path.exists(full_path):
            continue
        with open(full_path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("entries", []):
            code = entry.get("code", "")
            if not isinstance(code, str) or not code:
                continue
            if code.endswith(".SH") or code.endswith(".SZ"):
                bare = code.split(".")[0]
                watchlist[bare] = {
                    "name": entry.get("name", ""),
                    "tier": tier,
                    "code_with_suffix": code,
                }
    return watchlist


def cross_reference_watchlist(announcements, watchlist):
    """过滤公告清单，仅保留 watchlist 中的标的，附加 tier 信息。
    按 tier 优先级（S > A > B）+ 日期降序排列。"""
    TIER_ORDER = {"S_STRATEGIC": 0, "A_CORE": 1, "B_GROWTH": 2}
    hits = []
    for a in announcements:
        code = a["code"]
        if code in watchlist:
            wl = watchlist[code]
            hits.append({
                **a,
                "tier": wl["tier"],
                "watchlist_name": wl["name"],
                "code_with_suffix": wl["code_with_suffix"],
            })
    hits.sort(key=lambda x: (TIER_ORDER.get(x["tier"], 9), x["date"]))
    return hits


# ============ 标题方向正则 ============
DIRECTION_PATTERNS = [
    ("扭亏", "扭亏"), ("首亏", "首亏"), ("续亏", "续亏"),
    ("预增", "预增"), ("略增", "略增"), ("续盈", "续盈"),
    ("预减", "预减"), ("略减", "略减"), ("预盈", "预盈"),
]


def guess_direction(title):
    for kw, label in DIRECTION_PATTERNS:
        if kw in title:
            return label
    if "补充" in title:
        return "补充说明"
    return "未标明"


# ================= CNINFO 结构化预告 =================
_cninfo_client = None


def _get_cninfo():
    global _cninfo_client
    if _cninfo_client is None:
        _cninfo_client = CninfoClient()
    return _cninfo_client


def cninfo_structured_forecast(code):
    """从 CNINFO p_stock2238 获取结构化业绩预告数据。失败返回 None。"""
    try:
        df = _get_cninfo().performance_forecast(code, limit=3)
        if df.empty:
            return None
        row = df.iloc[0]
        np_low = row.get("净利润下限(元)")
        np_high = row.get("净利润上限(元)")
        chg_low = row.get("净利润增减幅下限(%)")
        chg_high = row.get("净利润增减幅上限(%)")

        def safe_float(v):
            if v is None:
                return None
            try:
                f = float(v)
                return f if f == f else None  # NaN → None
            except (ValueError, TypeError):
                return None

        return {
            "forecast_type": row.get("业绩类型", None),
            "forecast_content": row.get("业绩预告内容", None),
            "np_forecast_low": safe_float(np_low),
            "np_forecast_high": safe_float(np_high),
            "np_change_low": safe_float(chg_low),
            "np_change_high": safe_float(chg_high),
        }
    except Exception:
        return None


# ================= 理杏仁 =================
LX_TOKEN = os.getenv("LIXINGER_TOKEN")
LX_BASE = "https://open.lixinger.com/api"


def lx_post(path, payload):
    r = requests.post(f"{LX_BASE}/{path}", json={**payload, "token": LX_TOKEN},
                      headers={"Accept-Encoding": "gzip"}, timeout=30)
    try:
        if r.headers.get("Content-Encoding") == "gzip":
            return json.loads(gzip.decompress(r.content))
    except Exception:
        pass
    return r.json()


def lx_fundamentals(codes, date):
    """批量估值。date 须为已收盘交易日，自动回退最多 7 天。批量上限 100。"""
    res = {}
    d0 = dt.date.fromisoformat(date)
    for i in range(0, len(codes), 100):
        batch = codes[i:i + 100]
        for back in range(0, 8):
            probe = (d0 - dt.timedelta(days=back)).isoformat()
            r = lx_post("cn/company/fundamental/non_financial", {
                "stockCodes": batch, "date": probe,
                "metricsList": ["pe_ttm", "pb", "ps_ttm", "mc", "dyr"],
            })
            data = r.get("data") or []
            if data:
                for d in data:
                    res[d["stockCode"]] = d
                break
    return res


def lx_fs_yoy(code, end):
    """单只最近季度营收/净利 + 同比。fs/non_financial 每次只接受 1 只。"""
    start = (dt.date.fromisoformat(end) - dt.timedelta(days=800)).isoformat()
    r = lx_post("cn/company/fs/non_financial", {
        "stockCodes": [code], "startDate": start, "endDate": end,
        "metricsList": ["q.ps.toi.t", "q.ps.np.t"],
    })
    recs = r.get("data") or []
    if not recs:
        return None
    recs = sorted(recs, key=lambda x: x["date"], reverse=True)
    latest = recs[0]
    mmdd, yr = latest["date"][5:10], latest["date"][:4]
    prev = next((x for x in recs if x["date"][5:10] == mmdd and x["date"][:4] == str(int(yr) - 1)), None)

    def val(rec):
        q = rec.get("q", {}).get("ps", {})
        toi = q.get("toi", {}).get("t")
        np_ = q.get("np", {}).get("t")
        return (toi if isinstance(toi, (int, float)) else None,
                np_ if isinstance(np_, (int, float)) else None)

    toi_now, np_now = val(latest)
    out = {"period": latest["date"][:10], "toi": toi_now, "np": np_now,
           "toi_yoy": None, "np_yoy": None}
    if prev:
        toi_prev, np_prev = val(prev)
        if toi_now is not None and toi_prev:
            out["toi_yoy"] = (toi_now - toi_prev) / abs(toi_prev)
        if np_now is not None and np_prev:
            out["np_yoy"] = (np_now - np_prev) / abs(np_prev)
    return out


def lx_sw_level2(code):
    """申万行业分类：返回 (二级名, 一级名)。二级=代码 XXYY00 且 YY!=00。"""
    r = lx_post("cn/company/industries", {"stockCode": code})
    sw = [d for d in (r.get("data") or []) if d.get("source") == "sw"]
    l1 = next((d["name"] for d in sw if d["stockCode"].endswith("0000")), None)
    l2 = next((d["name"] for d in sw
               if d["stockCode"].endswith("00") and not d["stockCode"].endswith("0000")), None)
    return l2, l1


# ================= 存储 + 渲染 =================
def default_label(end):
    d = dt.date.fromisoformat(end)
    q = (d.month - 1) // 3 + 1
    return f"{d.year}Q{q}财报预告"


def load_store(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"label": None, "companies": {}, "scan_log": []}


def fmt_yi(v):
    return f"{v/1e8:.1f}亿" if isinstance(v, (int, float)) else "-"


def fmt_pct(v):
    return f"{v*100:+.1f}%" if isinstance(v, (int, float)) else "-"


def fmt_num(v, nd=1):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "-"


def render_md(store, label):
    companies = store["companies"]
    rows = sorted(companies.values(), key=lambda x: (x.get("date", ""), x.get("code", "")), reverse=True)
    n = len(rows)

    lines = []
    lines.append(f"# {label}\n")
    lines.append("> 数据源：CNINFO 结构化预告 + 半年报 Watchlist 交叉比对 + 理杏仁估值/财务/申万行业")
    lines.append(f"> 累计收录：**{n}** 家公司")
    if store.get("scan_log"):
        last = store["scan_log"][-1]
        lines.append(f"> 最近扫描：{last['ran_at']}（区间 {last['start']}~{last['end']}，新增 {last['added']} / 更新 {last['updated']}）")
    sa_count = len(store.get("semiannual_alerts", []))
    if sa_count:
        lines.append(f"> 🔔 Watchlist 半年报已披露：**{sa_count}** 家（需更新三件套）")
    lines.append("")

    # ---- 行业聚合表 ----
    ind = {}
    for r in rows:
        key = r.get("sw_l2") or "未分类"
        g = ind.setdefault(key, {"n": 0, "toi": [], "np": [], "l1": r.get("sw_l1") or ""})
        g["n"] += 1
        if isinstance(r.get("toi_yoy"), (int, float)):
            g["toi"].append(r["toi_yoy"])
        if isinstance(r.get("np_yoy"), (int, float)):
            g["np"].append(r["np_yoy"])

    def avg(a):
        return sum(a) / len(a) if a else None

    lines.append("## 申万二级行业分布\n")
    lines.append("| 申万二级行业 | 一级 | 已发预告数 | 占比 | 平均营收同比 | 平均净利同比 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for key, g in sorted(ind.items(), key=lambda kv: kv[1]["n"], reverse=True):
        share = f"{g['n']/n*100:.1f}%" if n else "-"
        lines.append(f"| {key} | {g['l1']} | {g['n']} | {share} | "
                     f"{fmt_pct(avg(g['toi']))} | {fmt_pct(avg(g['np']))} |")
    lines.append("")

    # ---- Watchlist 半年报告警 ----
    semiannual_alerts = store.get("semiannual_alerts", [])
    if semiannual_alerts:
        lines.append("## ⚠️ Watchlist 公司半年报已披露（需更新三件套）\n")
        lines.append("> 以下 Watchlist 公司在扫描区间内已发布正式半年报，建议安排三件套分析更新。\n")
        lines.append("| 公告日 | 代码 | 简称 | Watchlist 档位 | 公告标题 |")
        lines.append("|---|---|---|---|---|")
        for a in semiannual_alerts:
            lines.append(f"| {a['date']} | {a.get('code_with_suffix', a['code'])} "
                         f"| {a.get('watchlist_name', a.get('name', '-'))} "
                         f"| {a['tier']} | {a['title']} |")
        lines.append("")

    # ---- 个股列表 ----
    lines.append("## 个股预告列表\n")
    lines.append("| 公告日 | 代码 | 简称 | 方向 | 预告净利区间 | 净利增幅 | 申万二级 | PE_ttm | PB | 市值 | 营收同比 | 净利同比 |")
    lines.append("|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        # 净利区间
        lo = r.get("np_forecast_low")
        hi = r.get("np_forecast_high")
        if lo is not None and hi is not None:
            fc_cell = f"{fmt_yi_compact(lo)}~{fmt_yi_compact(hi)}" if lo != hi else fmt_yi_compact(lo)
        else:
            fc_cell = "-"
        # 增幅区间
        cl = r.get("np_change_low")
        ch = r.get("np_change_high")
        if cl is not None and ch is not None:
            chg_cell = f"{cl:+.1f}%~{ch:+.1f}%" if cl != ch else f"{cl:+.1f}%"
        else:
            chg_cell = "-"

        lines.append(
            f"| {r.get('date','-')} | {r['code']} | {r.get('name','-')} | {r.get('direction','-')} | "
            f"{fc_cell} | {chg_cell} | "
            f"{r.get('sw_l2') or '-'} | {fmt_num(r.get('pe_ttm'))} | {fmt_num(r.get('pb'),2)} | "
            f"{fmt_yi(r.get('mc'))} | {fmt_pct(r.get('toi_yoy'))} | {fmt_pct(r.get('np_yoy'))} |")
    lines.append("")

    # ---- 说明 ----
    lines.append("---\n")
    lines.append("**口径说明**：")
    lines.append("- 「方向」优先使用 CNINFO 结构化 API (`p_stock2238`) 的业绩类型；不可用时回退标题正则。")
    lines.append("- 「预告净利区间/净利增幅」来自 CNINFO 结构化预告 API，是公司预测值。")
    lines.append("- 「营收/净利同比」为理杏仁最近一期财报（累计口径）vs 去年同期，是**已实现**同比，非预告预测值。")
    lines.append("- 行业平均同比仅纳入有同比数据的公司。")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("start")
    p.add_argument("end")
    p.add_argument("--label", default=None)
    args = p.parse_args()

    label = args.label or default_label(args.end)
    store_path = os.path.join(STORE_DIR, f"{label}.json")
    doc_path = os.path.join(DOC_DIR, f"{label}.md")
    os.makedirs(STORE_DIR, exist_ok=True)
    os.makedirs(DOC_DIR, exist_ok=True)

    store = load_store(store_path)
    store["label"] = label
    existing = store["companies"]

    print(f"[1/4] CNINFO 拉取 {args.start}~{args.end} 全市场业绩预告 ...")
    items = cninfo_forecasts(args.start, args.end)
    print(f"      → {len(items)} 家公司")

    codes = [x["code"] for x in items]
    print(f"[2/4] 理杏仁批量补估值 ...")
    fund = lx_fundamentals(codes, args.end) if codes else {}

    added = updated = 0
    pre_existing_codes = set(existing.keys())
    print(f"[3/4] 理杏仁逐只补财务+行业+CNINFO结构化预告（{len(codes)} 只）...")
    for idx, it in enumerate(items, 1):
        c = it["code"]
        is_new = c not in existing
        y = lx_fs_yoy(c, args.end) or {}
        sw_l2, sw_l1 = lx_sw_level2(c)
        f = fund.get(c, {})
        # CNINFO 结构化预告（净利润区间+业绩类型，优先于标题正则）
        fc = cninfo_structured_forecast(c)
        rec = {
            "code": c, "name": it["name"], "date": it["date"],
            "direction": (fc.get("forecast_type") if fc and fc.get("forecast_type")
                          else guess_direction(it["title"])),
            "title": it["title"],
            "url": it["url"], "sw_l2": sw_l2, "sw_l1": sw_l1,
            "pe_ttm": f.get("pe_ttm"), "pb": f.get("pb"),
            "ps_ttm": f.get("ps_ttm"), "mc": f.get("mc"), "dyr": f.get("dyr"),
            "latest_period": y.get("period"),
            "toi": y.get("toi"), "toi_yoy": y.get("toi_yoy"),
            "np": y.get("np"), "np_yoy": y.get("np_yoy"),
            # 结构化预告字段
            "forecast_type": fc.get("forecast_type") if fc else None,
            "forecast_content": fc.get("forecast_content") if fc else None,
            "np_forecast_low": fc.get("np_forecast_low") if fc else None,
            "np_forecast_high": fc.get("np_forecast_high") if fc else None,
            "np_change_low": fc.get("np_change_low") if fc else None,
            "np_change_high": fc.get("np_change_high") if fc else None,
        }
        existing[c] = rec
        added += 1 if is_new else 0
        updated += 0 if is_new else 1
        if idx % 20 == 0:
            print(f"      ... {idx}/{len(codes)}")
        time.sleep(0.15)

    # ---- [5/5] 半年报扫描 + Watchlist 交叉比对 ----
    print(f"\n[5/5] CNINFO 拉取 {args.start}~{args.end} 正式半年报 + Watchlist 交叉比对 ...")
    watchlist = load_watchlist_a_share_codes()
    semiannual_all = cninfo_forecasts(args.start, args.end, category=CATEGORY_SEMIANNUAL)
    print(f"      全市场半年报：{len(semiannual_all)} 份")
    semiannual_hits = cross_reference_watchlist(semiannual_all, watchlist)

    # 合并到 store（按 code 去重，新 code 追加，已有 code 更新日期/标题）
    existing_alerts = {a["code"]: a for a in store.get("semiannual_alerts", [])}
    sa_added = 0
    sa_new_codes = set()
    for sa in semiannual_hits:
        c = sa["code"]
        if c not in existing_alerts:
            existing_alerts[c] = {**sa, "first_seen": dt.datetime.utcnow().strftime("%Y-%m-%d")}
            sa_added += 1
            sa_new_codes.add(c)
        else:
            existing_alerts[c].update({k: sa[k] for k in ["date", "title", "url"] if k in sa})
    store["semiannual_alerts"] = sorted(
        existing_alerts.values(),
        key=lambda x: ({"S_STRATEGIC": 0, "A_CORE": 1, "B_GROWTH": 2}.get(x.get("tier", ""), 9),
                       x.get("date", "")),
    )
    print(f"      → 命中 Watchlist：{len(semiannual_hits)} 家（本次新增 {sa_added}，累计 {len(store['semiannual_alerts'])} 家）")
    if semiannual_hits:
        for sa in semiannual_hits:
            tag = "🆕" if sa["code"] in sa_new_codes else "  "
            print(f"         {tag} [{sa['tier']}] {sa.get('code_with_suffix', sa['code'])} "
                  f"{sa.get('watchlist_name', sa.get('name', '-'))}  {sa['date']}")

    store["scan_log"].append({
        "ran_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "start": args.start, "end": args.end,
        "added": added, "updated": updated,
    })

    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

    md = render_md(store, label)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[4/4] 完成：新增 {added} / 更新 {updated}，累计 {len(existing)} 家")
    print(f"      JSON  → {store_path}")
    print(f"      文档  → {doc_path}")

    # ---- 本次新增/更新明细表 ----
    if added or updated:
        batch_codes = [x["code"] for x in items]
        added_codes = [c for c in batch_codes if c not in pre_existing_codes]
        updated_codes = [c for c in batch_codes if c in pre_existing_codes]

        hdr = f"{'代码':<8} {'简称':<10} {'公告日':<12} {'方向':<14} {'申万二级':<10} " \
              f"{'预告净利区间':<28} {'净利增幅':<22} {'PE':>8} {'市值':>8}"

        if added_codes:
            print(f"\n{'─'*80}")
            print(f"📋 新增 {len(added_codes)} 家（{args.start} ~ {args.end}）")
            print(f"{'─'*80}")
            print(hdr)
            print("-" * 130)
            for c in sorted(added_codes, key=lambda c: (existing[c].get("date", ""), c)):
                _print_company_row(existing[c])

        if updated_codes:
            print(f"\n{'─'*80}")
            print(f"🔄 更新 {len(updated_codes)} 家（{args.start} ~ {args.end}）")
            print(f"{'─'*80}")
            print(hdr)
            print("-" * 130)
            for c in sorted(updated_codes, key=lambda c: (existing[c].get("date", ""), c)):
                _print_company_row(existing[c])

    # ---- 半年报 Watchlist 告警 ----
    if store.get("semiannual_alerts"):
        print(f"\n{'═'*80}")
        print(f"🔔 Watchlist 公司半年报已披露 — 以下标的需更新三件套分析（累计 {len(store['semiannual_alerts'])} 家）")
        print(f"{'═'*80}")
        TIER_LABEL = {"S_STRATEGIC": "战略", "A_CORE": "核心", "B_GROWTH": "成长"}
        for a in store["semiannual_alerts"]:
            tier_cn = TIER_LABEL.get(a["tier"], a["tier"])
            print(f"  [{tier_cn}] {a.get('code_with_suffix', a['code']):<12} "
                  f"{a.get('watchlist_name', a.get('name', '-')):<10} "
                  f"{a['date']}  {a['title'][:50]}")

    print()


def _print_company_row(r):
    """格式化打印一条公司预告记录"""
    # 净利区间
    lo = r.get("np_forecast_low")
    hi = r.get("np_forecast_high")
    if lo is not None and hi is not None:
        if lo == hi:
            fc_str = f"{fmt_yi_compact(lo)}"
        else:
            fc_str = f"{fmt_yi_compact(lo)} ~ {fmt_yi_compact(hi)}"
    else:
        fc_str = "-"

    # 增幅区间
    cl = r.get("np_change_low")
    ch = r.get("np_change_high")
    if cl is not None and ch is not None:
        if cl == ch:
            chg_str = f"{cl:+.1f}%"
        else:
            chg_str = f"{cl:+.1f}% ~ {ch:+.1f}%"
    else:
        chg_str = "-"

    pe_str = f"{r.get('pe_ttm', 0):.1f}" if r.get("pe_ttm") else "-"
    mc_str = fmt_yi(r.get("mc")) if r.get("mc") else "-"

    print(f"{r['code']:<8} {r.get('name',''):<10} {r.get('date',''):<12} "
          f"{r.get('direction',''):<14} {r.get('sw_l2') or '-':<10} "
          f"{fc_str:<28} {chg_str:<22} {pe_str:>8} {mc_str:>8}")


def fmt_yi_compact(v):
    """格式化预告净利润（输入为万元）为易读单位。"""
    if v is None:
        return "-"
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 10000:
        return f"{sign}{v/10000:.2f}亿"
    else:
        return f"{sign}{v:.0f}万"


if __name__ == "__main__":
    main()
