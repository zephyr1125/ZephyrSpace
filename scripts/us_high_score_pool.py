"""美股「未收录高分企业」候选池构建 —— 不看价格，纯企业质量 + 覆盖率标签.

与 cn/hk_high_score_pool 同构；美股数据层与港股一致（Tiger + yfinance），但：
  - 宇宙：Tiger 选股器 Market.US，仅设流通市值 ≥ USD 30B（实测 ~531 家），无价格/PE 门槛
  - Yahoo 直接用 ticker（无 5/4 位代码转换）
  - 覆盖：watchlist .US + 低分登记 .US 硬排；公司页/旧研究打标用「index 美股节 ticker ∪ 文件名 ticker」集合
  - 管理层红旗：无批量源 → 池内 `RunB核` 占位，Run B 逐家 Web/Tavily 核
  - 共享 hk_high_score_pool 的财务拉取与质量打分（fetch_hk_quality/quality_score，含高周转薄利豁免）

Usage:
    python scripts/us_high_score_pool.py
    python scripts/us_high_score_pool.py --min-cap 50
    python scripts/us_high_score_pool.py --min-score 50
    python scripts/us_high_score_pool.py --codes MAR,TJX,ORLY   # 指定 ticker(测试)
    python scripts/us_high_score_pool.py --limit 60
    python scripts/us_high_score_pool.py --no-cache

Output:
    data/screens/美股高分候选池.json
    data/screens/美股高分候选池_YYYY-MM-DD.csv
    data/cache/us_high_score_fs_cache.json        # yfinance 指标缓存
"""

from __future__ import annotations

import csv
import json
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

from scripts.hk_high_score_pool import fetch_hk_quality, quality_score  # noqa: E402
from scripts.us_mispricing_screen import _tiger_client, number  # noqa: E402

MIN_MCAP_B = 30        # 最低流通市值 USD B（实测 ≥30B → ~531 家）
MIN_SCORE = 60          # 质量分入池下限（≥70 Ⅰ候选 / 60-70 Ⅱ候选）
FS_WORKERS = 5
FS_CACHE_FILE = "us_high_score_fs_cache.json"

FIN_SECTOR = {"financial services", "insurance", "banks", "asset management", "capital markets",
              "diversified financial services", "mortgage finance", "credit services",
              "insurance—life", "insurance—property & casualty", "insurance—diversified",
              "banks—diversified", "banks—regional", "banks—money center", "investment banking & brokerage"}
INDEX_PATH = ROOT / "00-首页" / "公司索引.md"
REGISTRY_PATH = ROOT / "00-首页" / "低分公司登记.md"
WL_FILES = ["data/watchlist_strategic.json", "data/watchlist_core.json",
            "data/watchlist_growth.json", "data/watchlist_out_of_scope.json"]
COMPANY_DIR = ROOT / "01-公司"
DEEP_DIR = ROOT / "深度分析"
MGMT_DIR = ROOT / "管理层档案"

_TICKER = re.compile(r"\(([A-Z][A-Z0-9.\-]{0,4})\)")
_PURE = re.compile(r"[A-Z][A-Z0-9]{0,4}")

# ── 覆盖率（label-only）：index 美股节 ticker + 三个目录文件名 ticker ──

def _dir_tokens(d):
    """目录文件名 → 候选 ticker token 集合（(XXXX) 括号 token 或 纯大写文件名）。"""
    toks = set()
    if not d.exists():
        return toks
    for p in d.iterdir():
        base = p.name[:-3] if p.name.endswith(".md") else p.name
        m = _TICKER.search(base)
        if m:
            toks.add(m.group(1))
        elif _PURE.fullmatch(base) and len(base) <= 6:
            toks.add(base)
    return toks


def _us_tokens():
    page_tokens = _dir_tokens(COMPANY_DIR)
    deep_tokens = _dir_tokens(DEEP_DIR)
    mgmt_tokens = _dir_tokens(MGMT_DIR)
    # index 美股节括号 ticker（对应有页）
    if INDEX_PATH.exists():
        text = INDEX_PATH.read_text(encoding="utf-8")
        m = re.search(r"^## 美股\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if m:
            for tok in _TICKER.findall(m.group(1)):
                page_tokens.add(tok)
    return page_tokens, deep_tokens, mgmt_tokens


_PAGE_TOKENS = _DEEP_TOKENS = _MGMT_TOKENS = None


def _load_tokens():
    global _PAGE_TOKENS, _DEEP_TOKENS, _MGMT_TOKENS
    if _PAGE_TOKENS is None:
        _PAGE_TOKENS, _DEEP_TOKENS, _MGMT_TOKENS = _us_tokens()
    return _PAGE_TOKENS, _DEEP_TOKENS, _MGMT_TOKENS


def coverage_label(symbol):
    """宽松口径：symbol 命中 index/文件 token 才打标签；否则全新。"""
    pt, dt, mt = _load_tokens()
    labels = []
    if symbol in pt:
        labels.append("公司页")
    if symbol in dt:
        labels.append("深度分析")
    if symbol in mt:
        labels.append("管理层档案")
    return labels or ["全新"]


def watchlist_us():
    """watchlist 四份 JSON 里 .US → bare ticker 集合。"""
    out = set()
    for rel in WL_FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for e in data.get("entries", []):
                c = str(e.get("code", ""))
                if c.endswith(".US"):
                    out.add(c[:-3])
        except Exception as exc:
            print(f"  ⚠ {rel} 读取失败: {exc}")
    return out


def low_registry_us():
    """低分公司登记.md 中 TICKER.US 形式代码。"""
    if not REGISTRY_PATH.exists():
        return set()
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9.\-]{0,4})\.US", text))


def _is_financial(sector, name):
    s = (sector or "").lower()
    n = (name or "").upper()
    if s in FIN_SECTOR or "bank" in s or "insurance" in s or "asset management" in s:
        return True
    if "-REIT" in n or ".REIT" in n or " REIT " in n or n.endswith(" REIT"):
        return True
    return False


def tiger_universe_us(min_cap_b=MIN_MCAP_B):
    """遍历 Market.US 全部页，仅设流通市值下限；对偶发限流做重试+节流。"""
    from tigeropen.common.consts import Market
    from tigeropen.common.consts.filter_fields import StockField
    from tigeropen.quote.domain.filter import StockFilter

    client = _tiger_client()
    filters = [StockFilter(StockField.FloatMarketVal, filter_min=min_cap_b * 1_000_000_000,
                           is_no_filter=False)]
    out, cursor = [], None
    while True:
        res = None
        for _ in range(6):
            try:
                res = client.market_scanner(market=Market.US, filters=filters, cursor_id=cursor,
                                            page_size=200)
                break
            except Exception:
                time.sleep(1.5)
        if res is None:
            print("  ⚠ Tiger 分页失败，中断遍历。")
            break
        for item in res.items:
            fd = item.field_data
            out.append({
                "代码": str(item.symbol),
                "流通市值_亿美元": round(number(fd.get(StockField.FloatMarketVal)) / 100_000_000, 1),
            })
        cursor = res.cursor_id
        if not cursor:
            break
        time.sleep(0.15)
    return out


def main():
    parser = ArgumentParser(description="美股未收录高分企业候选池构建")
    parser.add_argument("--min-cap", type=float, default=MIN_MCAP_B, help="流通市值下限 USD B")
    parser.add_argument("--min-score", type=float, default=MIN_SCORE, help="质量分入池下限")
    parser.add_argument("--codes", default="", help="只对指定 ticker(逗号)跑财务(测试)")
    parser.add_argument("--limit", type=int, default=0, help="只对前 N 家跑财务(测试)")
    parser.add_argument("--no-cache", action="store_true", help="忽略缓存强制重拉")
    args = parser.parse_args()

    out_dir = ROOT / "data" / "screens"
    out_dir.mkdir(parents=True, exist_ok=True)
    pool_path = out_dir / "美股高分候选池.json"
    csv_path = out_dir / f"美股高分候选池_{date.today().isoformat()}.csv"

    print("=" * 62)
    print(f" 美股未收录高分企业候选池  (min-cap=${args.min_cap}B, min-score={args.min_score})")
    print("=" * 62)

    universe = tiger_universe_us(args.min_cap)
    print(f"[Tiger] 流通市值≥USD {args.min_cap}B → {len(universe)} 家")

    wl = watchlist_us()
    low = low_registry_us()
    targets = [u for u in universe if u["代码"] not in wl and u["代码"] not in low]
    print(f"[排除集] watchlist .US {len(wl)} + 低分登记 .US {len(low)}；硬排后 {len(targets)} 家")

    if args.codes:
        wanted = {c.upper().strip() for c in args.codes.split(",") if c.strip()}
        targets = [t for t in targets if t["代码"] in wanted]
        print(f"[codes] 指定 {len(targets)} 家（其余在 watchlist/低分登记）")
    elif args.limit > 0:
        targets = targets[:args.limit]
        print(f"[limit] 前 {args.limit} 家")

    cache_dir = ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / FS_CACHE_FILE
    cache = {}
    if cache_path.exists() and not args.no_cache:
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    to_fetch = [t for t in targets if t["代码"] not in cache or args.no_cache]
    print(f"[yfinance缓存] 命中 {len(targets) - len(to_fetch)}，需拉 {len(to_fetch)}")
    fetched = {}
    done = 0
    total = len(to_fetch)
    with ThreadPoolExecutor(max_workers=FS_WORKERS) as ex:
        futs = {ex.submit(fetch_hk_quality, t["代码"]): t for t in to_fetch}
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                fetched[t["代码"]] = fut.result()
            except Exception as exc:
                fetched[t["代码"]] = {"_ok": False, "名称": "", "行业": "", "_err": str(exc)[:120]}
            done += 1
            if done % 25 == 0:
                print(f"  … yfinance {done}/{total}")
    cache.update(fetched)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for v in fetched.values() if v.get("_ok"))
    fin = sum(1 for v in fetched.values() if v.get("_financial"))
    print(f"[yfinance] 本次 {ok} 可用 / {fin} 金融剔除 / {total - ok - fin} 数据不足")

    today = date.today().isoformat()
    old_by_code = {}
    if pool_path.exists():
        try:
            for r in json.loads(pool_path.read_text(encoding="utf-8")):
                if isinstance(r, dict) and r.get("代码"):
                    old_by_code[r["代码"]] = r
        except Exception:
            pass

    pool_rows, dropped = [], 0
    for t in targets:
        e = cache.get(t["代码"]) or {}
        if not e.get("_ok"):
            if e.get("_financial"):
                continue          # 金融/REIT 静默剔除
            dropped += 1
            continue
        score, flags = quality_score(e)
        if score < args.min_score:
            dropped += 1
            continue
        sym = t["代码"]
        cov = coverage_label(sym)
        tier = "Ⅰ候选" if score >= 70 else "Ⅱ候选"
        row = {
            "代码": f"{sym}.US", "Tiger代码": sym, "板块": "",
            "简称": e.get("名称") or sym, "行业": e.get("行业", ""),
            "池内档位": tier, "质量分": score,
            "覆盖": "/".join(cov) if cov != ["全新"] else "全新",
            "管理层红旗": "RunB核",
            "流通市值_亿美元": t["流通市值_亿美元"],
            "review_status": (old_by_code.get(f"{sym}.US") or {}).get("review_status", "pending"),
            "reviewed_date": (old_by_code.get(f"{sym}.US") or {}).get("reviewed_date", ""),
            "notes": (old_by_code.get(f"{sym}.US") or {}).get("notes", ""),
            "进入池日期": (old_by_code.get(f"{sym}.US") or {}).get("进入池日期", today),
            **{k: v for k, v in e.items() if not k.startswith("_")},
            "量化警示": "；".join(flags) or "无",
        }
        pool_rows.append(row)

    pool_rows.sort(key=lambda r: -r["质量分"])
    pool_path.write_text(json.dumps(pool_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[JSON] {pool_path} ({len(pool_rows)} 只)")

    csv_cols = ["代码", "简称", "行业", "池内档位", "质量分", "5Y ROE均值_%", "5Y ROE最低_%",
                "营收5年CAGR_%", "净利润3年CAGR_%", "毛利率均值_%", "净利率均值_%",
                "FCF转化率", "FCF正年数占比_%", "OCF负年数", "资产负债率_%",
                "流通市值_亿美元", "管理层红旗", "覆盖", "量化警示", "review_status", "reviewed_date"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(pool_rows)
    print(f"[CSV] {csv_path}")

    tier1 = [r for r in pool_rows if r["池内档位"] == "Ⅰ候选"]
    tier2 = [r for r in pool_rows if r["池内档位"] == "Ⅱ候选"]
    print(f"\n[池分布] Ⅰ候选={len(tier1)}  Ⅱ候选={len(tier2)}  (低分/数据不足 {dropped})")
    print("\n[Ⅰ候选 top20 - 供分批 AI 复核]:")
    for r in tier1[:20]:
        print(f"  {r['质量分']:5.1f}  {r['代码']:<11s} {str(r['简称'])[:22]:<23s} "
              f"{str(r.get('行业'))[:14]:<15s} ROE={r.get('5Y ROE均值_%')}%  [{r['覆盖']}]")


if __name__ == "__main__":
    main()
