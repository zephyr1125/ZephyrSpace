"""
AI 泡沫监测 — 仪表盘证据预抓取脚本

用途：
  为「AI 泡沫破裂仪表盘」(skills/ai-bubble-watch) 的 8 个指标（2026-06-27 起新增 Y4）批量拉取最近新闻证据，
  输出 JSON 供 AI 逐项打分。脚本只负责"取证据"，不做打分判断（打分由 AI 在 skill 里完成）。

8 个指标（2026-06-27 起新增 Y4）：
  R1 超大厂 capex 指引下修       [低频·季度]
  R2 大模型融资遇冷(OpenAI等)    [高频]
  R3 二手 GPU(H100/A100) 租赁价  [高频]
  R4 数据中心私募信贷/SPV 风险   [高频]
  Y1 NVIDIA 数据中心收入环比     [低频·季度]
  Y2 Neocloud 客户集中度/取消    [高频]
  Y3 循环交易(vendor financing)  [低频·季度]
  Y4 消费电子因AI挤出而提价      [高频] 🆕

用法：
  python scripts/ai_bubble_scan.py                 # 抓今天，写 _ai_bubble_scan/YYYY-MM-DD.json
  python scripts/ai_bubble_scan.py --date 2026-06-27
  python scripts/ai_bubble_scan.py --dry-run       # 只打印查询计划，不调用 Tavily
  python scripts/ai_bubble_scan.py --only R2,R3,R4 # 只抓部分指标（周中快查高频项）
"""

import os
import sys
import json
import argparse
from datetime import datetime, date

# 让 `from scripts.api_tracker import ...` 可导入（脚本以 `python scripts/ai_bubble_scan.py` 运行时，cwd 不在 sys.path）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 指标查询计划 ──────────────────────────────────────────────
# freq: high = 每周都可能有新信号; low = 主要在财报季更新（无新数据则沿用上期）
INDICATORS = [
    {
        "id": "R1", "tier": "red", "freq": "low",
        "label": "超大厂 capex 指引下修",
        "queries": [
            {"q": "Microsoft Amazon Google Meta Oracle capex guidance 2026 AI spending", "topic": "news", "days": 14},
            {"q": "hyperscaler capex cut lower AI data center spending slowdown", "topic": "news", "days": 21},
        ],
    },
    {
        "id": "R2", "tier": "red", "freq": "high",
        "label": "大模型融资遇冷",
        "queries": [
            {"q": "OpenAI funding round valuation 2026 raise", "topic": "news", "days": 14},
            {"q": "Anthropic xAI funding round struggle down round valuation", "topic": "news", "days": 21},
        ],
    },
    {
        "id": "R3", "tier": "red", "freq": "high",
        "label": "二手 GPU 租赁价断崖",
        "queries": [
            {"q": "H100 GPU rental price per hour 2026 drop trend", "topic": "general", "days": 30},
            {"q": "A100 H100 GPU rental price collapse oversupply idle", "topic": "news", "days": 30},
        ],
    },
    {
        "id": "R4", "tier": "red", "freq": "high",
        "label": "数据中心私募信贷/SPV 风险",
        "queries": [
            {"q": "data center private credit spread AI debt distress", "topic": "news", "days": 21},
            {"q": "AI data center bonds ABS downgrade SPV CoreWeave Meta financing", "topic": "news", "days": 21},
        ],
    },
    {
        "id": "Y1", "tier": "yellow", "freq": "low",
        "label": "NVIDIA 数据中心收入环比",
        "queries": [
            {"q": "NVIDIA data center revenue quarter QoQ growth 2026 earnings", "topic": "news", "days": 21},
        ],
    },
    {
        "id": "Y2", "tier": "yellow", "freq": "high",
        "label": "Neocloud 客户集中度/取消",
        "queries": [
            {"q": "CoreWeave customer concentration Microsoft cancel order 2026", "topic": "news", "days": 21},
            {"q": "neocloud Lambda Nebius Crusoe order cancellation financial trouble", "topic": "news", "days": 21},
        ],
    },
    {
        "id": "Y3", "tier": "yellow", "freq": "low",
        "label": "循环交易(vendor financing)占比",
        "queries": [
            {"q": "Nvidia circular financing OpenAI Oracle vendor financing concern", "topic": "news", "days": 21},
            {"q": "AI related party revenue circular deals accounting scrutiny", "topic": "news", "days": 21},
        ],
    },
    {
        "id": "Y4", "tier": "yellow", "freq": "high",
        "label": "消费电子因AI挤出而提价",
        "queries": [
            {"q": "memory chip DRAM HBM price surge consumer electronics Apple Microsoft Xbox iPhone price hike 2026", "topic": "news", "days": 14},
            {"q": "AI memory shortage OEM device price increase margin compression consumer impact", "topic": "news", "days": 21},
        ],
    },
]


def run_query(client, q, topic, days, max_results=5):
    """单条 Tavily 查询，返回精简结果列表；失败时返回带 error 的占位。"""
    from scripts.api_tracker import get_tracker
    try:
        kwargs = {"query": q, "max_results": max_results, "search_depth": "advanced"}
        if topic == "news":
            kwargs["topic"] = "news"
            kwargs["days"] = days
        tracker = get_tracker()
        with tracker.track("tavily", "search", essential=True,
                           context=f"ai-bubble {topic} days={days}"):
            resp = client.search(**kwargs)
        out = []
        for r in resp.get("results", []):
            out.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "published_date": r.get("published_date", ""),
                "content": (r.get("content") or "").strip()[:400],
            })
        return out
    except Exception as e:
        return [{"error": f"{type(e).__name__}: {e}"}]


def main():
    ap = argparse.ArgumentParser(description="AI 泡沫监测仪表盘证据预抓取")
    ap.add_argument("--date", default=date.today().isoformat(), help="扫描日期 YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true", help="只打印查询计划，不调用 Tavily")
    ap.add_argument("--only", default="", help="只抓指定指标，逗号分隔，如 R2,R3,R4")
    ap.add_argument("--max-results", type=int, default=5)
    args = ap.parse_args()

    only = {x.strip().upper() for x in args.only.split(",") if x.strip()}
    indicators = [i for i in INDICATORS if not only or i["id"] in only]

    if args.dry_run:
        print(f"=== 查询计划（{args.date}）{'· 仅 '+args.only if only else ''} ===\n")
        for ind in indicators:
            print(f"[{ind['id']}] {ind['label']}  ({ind['tier']}/{ind['freq']})")
            for qq in ind["queries"]:
                print(f"    - ({qq['topic']}, {qq['days']}d) {qq['q']}")
            print()
        print(f"共 {len(indicators)} 个指标，"
              f"{sum(len(i['queries']) for i in indicators)} 条查询。")
        return

    # 延迟导入，dry-run 不需要依赖
    from dotenv import load_dotenv
    from tavily import TavilyClient
    load_dotenv(r"E:\ObsidianVaults\ZephyrSpace\.env")
    key = os.getenv("TAVILY_KEY")
    if not key:
        print("ERROR: TAVILY_KEY 未在 .env 中设置", file=sys.stderr)
        sys.exit(1)
    client = TavilyClient(api_key=key)

    result = {
        "date": args.date,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "indicators": {},
    }

    n_queries = 0
    for ind in indicators:
        print(f"  抓取 [{ind['id']}] {ind['label']} ...", flush=True)
        blocks = []
        for qq in ind["queries"]:
            res = run_query(client, qq["q"], qq["topic"], qq["days"], args.max_results)
            blocks.append({"query": qq["q"], "topic": qq["topic"],
                           "days": qq["days"], "results": res})
            n_queries += 1
        result["indicators"][ind["id"]] = {
            "label": ind["label"], "tier": ind["tier"],
            "freq": ind["freq"], "queries": blocks,
        }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ai_bubble_scan")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{args.date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n完成：{len(indicators)} 个指标 / {n_queries} 条查询")
    print(f"输出：{out_path}")


if __name__ == "__main__":
    main()
