# -*- coding: utf-8 -*-
"""Publish REGN: company index + watchlist core entry."""
import json, io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 1) company index
p = "00-首页/公司索引.md"
t = open(p, encoding="utf-8").read()
t = t.replace("> 共 **644** 个公司页（更新于 2026-09-11）。",
              "> 共 **645** 个公司页（更新于 2026-09-24）。")
anchor = "## 美股\n\n"
assert anchor in t
assert "[[Regeneron(REGN)]]" not in t
t = t.replace(anchor, anchor + "- [[Regeneron(REGN)]]\n", 1)
open(p, "w", encoding="utf-8").write(t)
print("index: added Regeneron(REGN), count -> 645, date -> 2026-09-24")

# 2) watchlist core
wp = "data/watchlist_core.json"
d = json.load(open(wp, encoding="utf-8"))
entry = {
    "name": "Regeneron",
    "code": "REGN.US",
    "board": "纳",
    "cScore": 81,
    "mScore": 80,
    "target_price": 834.25,
    "valuation_certainty": 0.51,
    "dv_ttm": 0.47,
    "next_earnings_date": None,
    "next_earnings_type": None,
    "lastEarningsIncorporated": "2026Q2",
    "cycle_is_cyclical": False,
    "cycle_position": None,
    "watchlistLevel": "A_CORE",
    "trackingStatus": "WATCHING",
    "strategicCoreType": None,
    "lastFundamentalReviewDate": "2026-09-24",
    "lastRedFlagReviewDate": "2026-09-24",
}
assert all(e["code"] != "REGN.US" for e in d["entries"]), "REGN already present"
d["entries"].append(entry)
d["updated_at"] = "2026-09-24"
json.dump(d, open(wp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("watchlist_core: entries ->", len(d["entries"]))
print(json.dumps(entry, ensure_ascii=False, indent=1))
