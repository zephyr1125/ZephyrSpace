#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""拉取 CNINFO 全市场业绩预告（按日期，不限单只股票）。

用法:
    python scripts/fetch_daily_forecasts.py                 # 默认今天
    python scripts/fetch_daily_forecasts.py 2026-07-03      # 指定单日
    python scripts/fetch_daily_forecasts.py 2026-07-01 2026-07-03   # 区间
    python scripts/fetch_daily_forecasts.py 2026-07-03 --json out.json

原理: CNINFO hisAnnouncement/query 接口，stock 留空即全市场，
      category=category_yjygjxz_szsh 为业绩预告，plate=sz;sh;bj 覆盖深沪京。
"""
import sys
import json
import time
import argparse
import datetime as dt

import requests

ENDPOINT = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CATEGORY_FORECAST = "category_yjygjxz_szsh"


def fetch_forecasts(start, end, plate="sz;sh;bj", page_size=30, sleep=0.3):
    """返回全市场业绩预告列表 [{code, name, title, url, time}]。"""
    out = []
    page = 1
    while True:
        r = requests.post(
            ENDPOINT,
            data={
                "pageNum": str(page), "pageSize": str(page_size),
                "column": "szse", "tabName": "fulltext",
                "plate": plate, "stock": "", "searchkey": "",
                "secid": "", "category": CATEGORY_FORECAST,
                "trade": "", "seDate": f"{start}~{end}",
                "sortName": "time", "sortType": "desc", "isHLtitle": "true",
            },
            headers={
                "Accept": "application/json",
                "Referer": "http://www.cninfo.com.cn/",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=30,
        )
        d = r.json()
        anns = d.get("announcements") or []
        if not anns:
            break
        for a in anns:
            # announcementTime 是 UTC 毫秒，+8h 转北京时间
            ts = a.get("announcementTime", 0) / 1000
            beijing = dt.datetime.utcfromtimestamp(ts) + dt.timedelta(hours=8)
            out.append({
                "code": a.get("secCode", ""),
                "name": a.get("secName", ""),
                "title": a.get("announcementTitle", "").replace("<em>", "").replace("</em>", ""),
                "url": f"https://static.cninfo.com.cn/{a.get('adjunctUrl', '')}",
                "time": beijing.strftime("%Y-%m-%d %H:%M"),
            })
        if not d.get("hasMore"):
            break
        page += 1
        time.sleep(sleep)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("start", nargs="?", default=None, help="起始日期 YYYY-MM-DD (默认今天)")
    p.add_argument("end", nargs="?", default=None, help="结束日期 YYYY-MM-DD (默认=start)")
    p.add_argument("--json", dest="json_out", default=None, help="额外写出 JSON 文件")
    args = p.parse_args()

    today = dt.date.today().isoformat()
    start = args.start or today
    end = args.end or start

    res = fetch_forecasts(start, end)

    # UTF-8 输出，避免 Windows GBK 控制台乱码
    out = sys.stdout
    try:
        out.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"[{start} ~ {end}] 全市场业绩预告 {len(res)} 条\n", file=out)
    for a in res:
        print(f"{a['code']}  {a['name']:<8}  {a['time']}  {a['title']}", file=out)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"start": start, "end": end, "count": len(res), "items": res},
                      f, ensure_ascii=False, indent=2)
        print(f"\n[写出] {args.json_out}", file=out)


if __name__ == "__main__":
    main()
