#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""当日业绩预告扫描 + 关键数据补全（CNINFO 清单 → 理杏仁数据）。

链路:
  1) CNINFO hisAnnouncement/query 全市场按日拉「业绩预告」→ 得到 code 清单
  2) 理杏仁 fundamental/non_financial 批量补估值（PE/PB/PS/市值/股息率）
  3) 理杏仁 fs/non_financial 批量补最近季度营收/净利润 → 算同比
  4) 从标题正则出预告方向（预增/预减/扭亏/首亏/续亏/略增…）

用法:
    python scripts/scan_daily_forecasts.py                 # 今天
    python scripts/scan_daily_forecasts.py 2026-07-03      # 指定单日
    python scripts/scan_daily_forecasts.py 2026-07-01 2026-07-03 --json out.json
"""
import sys
import io
import re
import json
import time
import argparse
import datetime as dt
import gzip

import requests
from dotenv import load_dotenv
import os

load_dotenv()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ---------- CNINFO：全市场当日业绩预告清单 ----------
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
    # 去重（补充说明公告等同一天可能重复）
    seen, uniq = set(), []
    for a in out:
        if a["code"] in seen:
            continue
        seen.add(a["code"])
        uniq.append(a)
    return uniq


# ---------- 从标题正则预告方向 ----------
DIRECTION_PATTERNS = [
    ("扭亏", "扭亏"), ("首亏", "首次亏损/首亏"), ("续亏", "续亏"),
    ("预增", "预增"), ("略增", "略增"), ("续盈", "续盈"),
    ("预减", "预减"), ("略减", "略减"), ("预盈", "预盈"),
]


def guess_direction(title):
    for kw, label in DIRECTION_PATTERNS:
        if kw in title:
            return label
    if "补充" in title:
        return "（补充说明）"
    return "未标明（需看正文）"


# ---------- 理杏仁 ----------
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
    """批量估值。理杏仁 date 必须是已收盘交易日，公告日/非交易日会返回空，
    故从 date 往前逐日回退至拿到数据（最多回退 7 天覆盖周末+节假日）。
    批量上限 100，分批。"""
    res = {}
    for i in range(0, len(codes), 100):
        batch = codes[i:i + 100]
        d0 = dt.date.fromisoformat(date)
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


def lx_recent_fs(codes, start, end):
    """批量最近季度营收/净利润 → 用于算同比（取同期两年对比）。
    注意：fs/non_financial 每次只接受 1 只股票，须逐只查询。"""
    res = {}
    for c in codes:
        r = lx_post("cn/company/fs/non_financial", {
            "stockCodes": [c], "startDate": start, "endDate": end,
            "metricsList": ["q.ps.toi.t", "q.ps.np.t"],
        })
        data = r.get("data") or []
        if data:
            res[c] = data
        time.sleep(0.15)
    return res


def yoy_from_fs(records):
    """从财务记录里找最近一期，与去年同季比营收/净利润同比。"""
    if not records:
        return None
    recs = sorted(records, key=lambda x: x["date"], reverse=True)
    latest = recs[0]
    lm = latest["date"][5:10]  # MM-DD
    ly = latest["date"][:4]
    prev = next((r for r in recs if r["date"][5:10] == lm and r["date"][:4] == str(int(ly) - 1)), None)
    def val(rec, path):
        cur = rec.get("q", {})
        for k in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur if isinstance(cur, (int, float)) else None
    out = {"period": latest["date"][:10]}
    toi_now, np_now = val(latest, ["ps", "toi", "t"]), val(latest, ["ps", "np", "t"])
    out["toi"], out["np"] = toi_now, np_now
    if prev:
        toi_prev, np_prev = val(prev, ["ps", "toi", "t"]), val(prev, ["ps", "np", "t"])
        if toi_prev:
            out["toi_yoy"] = (toi_now - toi_prev) / abs(toi_prev)
        if np_prev:
            out["np_yoy"] = (np_now - np_prev) / abs(np_prev)
    return out


def fmt_yi(v):
    return f"{v/1e8:.1f}亿" if isinstance(v, (int, float)) else "-"


def fmt_pct(v):
    return f"{v*100:+.1f}%" if isinstance(v, (int, float)) else "-"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("start", nargs="?", default=None)
    p.add_argument("end", nargs="?", default=None)
    p.add_argument("--json", dest="json_out", default=None)
    args = p.parse_args()

    today = dt.date.today().isoformat()
    start = args.start or today
    end = args.end or start

    print(f"[1/3] CNINFO 拉取 {start}~{end} 全市场业绩预告清单 ...")
    items = cninfo_forecasts(start, end)
    codes = [x["code"] for x in items]
    print(f"      → {len(codes)} 家公司\n")
    if not codes:
        print("无业绩预告。")
        return

    print("[2/3] 理杏仁批量补估值 ...")
    fund = lx_fundamentals(codes, end)

    print("[3/3] 理杏仁批量补财务 + 算同比 ...\n")
    fs_start = (dt.date.fromisoformat(end) - dt.timedelta(days=800)).isoformat()
    fs = lx_recent_fs(codes, fs_start, end)

    rows = []
    for it in items:
        c = it["code"]
        f = fund.get(c, {})
        y = yoy_from_fs(fs.get(c))
        rows.append({
            "code": c, "name": it["name"], "date": it["date"],
            "direction": guess_direction(it["title"]),
            "title": it["title"], "url": it["url"],
            "pe_ttm": f.get("pe_ttm"), "pb": f.get("pb"),
            "mc": f.get("mc"), "dyr": f.get("dyr"),
            "latest_period": (y or {}).get("period"),
            "toi": (y or {}).get("toi"), "toi_yoy": (y or {}).get("toi_yoy"),
            "np": (y or {}).get("np"), "np_yoy": (y or {}).get("np_yoy"),
        })

    # 打印表
    print(f"{'代码':<7}{'简称':<9}{'方向':<12}{'PE_ttm':>8}{'市值':>9}{'最近营收同比':>11}{'净利同比':>10}")
    print("-" * 78)
    for r in rows:
        pe = f"{r['pe_ttm']:.1f}" if isinstance(r["pe_ttm"], (int, float)) else "-"
        print(f"{r['code']:<7}{r['name']:<9}{r['direction']:<12}{pe:>8}"
              f"{fmt_yi(r['mc']):>9}{fmt_pct(r['toi_yoy']):>11}{fmt_pct(r['np_yoy']):>10}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fp:
            json.dump({"start": start, "end": end, "count": len(rows), "items": rows},
                      fp, ensure_ascii=False, indent=2)
        print(f"\n[写出] {args.json_out}")


if __name__ == "__main__":
    main()
