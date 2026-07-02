#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""财报预告监控引擎：CNINFO 清单 → 理杏仁补数据 → JSON 增量存储 → 渲染 MD。

数据链:
  1) CNINFO hisAnnouncement/query 全市场按日期区间拉「业绩预告」清单
  2) 理杏仁 fundamental/non_financial 批量补估值（PE/PB/PS/市值/股息率）
  3) 理杏仁 fs/non_financial 逐只补最近季度营收/净利润 → 算同比
  4) 理杏仁 company/industries 逐只补申万2021二级行业分类
  5) 合并进 data/forecast_scan/<label>.json（按 code 去重，保留最新一次）
  6) 渲染 02-主题/财报预告/<label>.md（个股列表 + 行业聚合表）

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
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(VAULT, "data", "forecast_scan")
DOC_DIR = os.path.join(VAULT, "02-主题", "财报预告")

# ================= CNINFO =================
CNINFO_ENDPOINT = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CATEGORY_FORECAST = "category_yjygjxz_szsh"


def cninfo_forecasts(start, end, plate="sz;sh;bj", page_size=30, sleep=0.3):
    out, page = [], 1
    while True:
        r = requests.post(
            CNINFO_ENDPOINT,
            data={
                "pageNum": str(page), "pageSize": str(page_size),
                "column": "szse", "tabName": "fulltext", "plate": plate,
                "stock": "", "searchkey": "", "secid": "",
                "category": CATEGORY_FORECAST, "trade": "",
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
    lines.append(f"> 数据源：CNINFO 公告清单 + 理杏仁估值/财务/申万行业")
    lines.append(f"> 累计收录：**{n}** 家公司")
    if store.get("scan_log"):
        last = store["scan_log"][-1]
        lines.append(f"> 最近扫描：{last['ran_at']}（区间 {last['start']}~{last['end']}，新增 {last['added']} / 更新 {last['updated']}）")
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

    # ---- 个股列表 ----
    lines.append("## 个股预告列表\n")
    lines.append("| 公告日 | 代码 | 简称 | 方向 | 申万二级 | PE_ttm | PB | 市值 | 营收同比 | 净利同比 |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r.get('date','-')} | {r['code']} | {r.get('name','-')} | {r.get('direction','-')} | "
            f"{r.get('sw_l2') or '-'} | {fmt_num(r.get('pe_ttm'))} | {fmt_num(r.get('pb'),2)} | "
            f"{fmt_yi(r.get('mc'))} | {fmt_pct(r.get('toi_yoy'))} | {fmt_pct(r.get('np_yoy'))} |")
    lines.append("")

    # ---- 说明 ----
    lines.append("---\n")
    lines.append("**口径说明**：")
    lines.append("- 「方向」来自公告标题正则（预增/预减/扭亏等），标题未写方向则标「未标明」，可参考净利同比推断。")
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
    print(f"[3/4] 理杏仁逐只补财务+行业（{len(codes)} 只）...")
    for idx, it in enumerate(items, 1):
        c = it["code"]
        is_new = c not in existing
        y = lx_fs_yoy(c, args.end) or {}
        sw_l2, sw_l1 = lx_sw_level2(c)
        f = fund.get(c, {})
        rec = {
            "code": c, "name": it["name"], "date": it["date"],
            "direction": guess_direction(it["title"]), "title": it["title"],
            "url": it["url"], "sw_l2": sw_l2, "sw_l1": sw_l1,
            "pe_ttm": f.get("pe_ttm"), "pb": f.get("pb"),
            "ps_ttm": f.get("ps_ttm"), "mc": f.get("mc"), "dyr": f.get("dyr"),
            "latest_period": y.get("period"),
            "toi": y.get("toi"), "toi_yoy": y.get("toi_yoy"),
            "np": y.get("np"), "np_yoy": y.get("np_yoy"),
        }
        existing[c] = rec
        added += 1 if is_new else 0
        updated += 0 if is_new else 1
        if idx % 20 == 0:
            print(f"      ... {idx}/{len(codes)}")
        time.sleep(0.15)

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


if __name__ == "__main__":
    main()
