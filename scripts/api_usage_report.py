"""
API 用量聚合与续约报告脚本
===============================
从 data/api_usage/YYYY-MM/*.json 读取每次分析的 run 日志，
按月/季/年聚合，输出 API 利用率统计和续约建议。

用法：
    python scripts/api_usage_report.py                     # 本月汇总
    python scripts/api_usage_report.py --month 2026-08     # 指定月
    python scripts/api_usage_report.py --months 6          # 最近6个月趋势
    python scripts/api_usage_report.py --yearly            # 年度续约报告
    python scripts/api_usage_report.py --renewal           # 续约推荐表（Markdown）
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# ── 配置 ──────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).parent.parent
USAGE_DIR = VAULT_ROOT / "data" / "api_usage"
TZ = timezone(timedelta(hours=8))

# API 定价信息（用于续约决策）
API_PRICING = {
    "wisburg":  {"name": "智堡 Wisburg", "annual_fee": "¥2,000", "paid": True},
    "lixinger": {"name": "理杏仁 Lixinger", "annual_fee": "¥1,800", "paid": True},
    "tavily":   {"name": "Tavily", "annual_fee": "免费(1000次/月) + $0.008/次超额", "paid": False},
    "cninfo":   {"name": "CNINFO 深证信", "annual_fee": "免费", "paid": False},
    "tushare":  {"name": "Tushare", "annual_fee": "免费 tier", "paid": False},
}

# 分析类型中文名
ANALYSIS_TYPES_CN = {
    "deep-analysis": "深度分析",
    "management-archive": "管理层档案",
    "valuation": "估值分析",
    "weekly-monitor": "周度监控",
    "ai-bubble-watch": "AI泡沫仪表盘",
    "portfolio-weekly": "持仓周报",
    "forecast-monitor": "财报预告监控",
    "us-quality-mispricing": "美股错杀筛选",
    "hk-quality-mispricing": "港股错杀筛选",
}


# ── 核心逻辑 ──────────────────────────────────────────────

def load_runs(months: list[str]) -> list[dict]:
    """加载指定月份的所有 run 日志"""
    runs = []
    for month in months:
        month_dir = USAGE_DIR / month
        if not month_dir.is_dir():
            continue
        for f in sorted(month_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                runs.append(data)
            except Exception:
                pass
    return runs


def aggregate_runs(runs: list[dict]) -> dict:
    """聚合多个 run 的 API 用量"""
    api_totals = defaultdict(lambda: {
        "total_calls": 0, "total_success": 0, "total_failure": 0,
        "total_duration_minutes": 0.0, "essential_calls": 0,
        "runs_used": 0, "by_type": defaultdict(lambda: {"calls": 0, "runs": 0}),
        "endpoints": defaultdict(int),
    })

    seen_types = set()

    for run in runs:
        atype = run.get("analysis_type", "unknown")
        seen_types.add(atype)

        for api_name, summary in run.get("api_summary", {}).items():
            t = api_totals[api_name]
            t["total_calls"] += summary.get("total_calls", 0)
            t["total_success"] += summary.get("total_success", 0)
            t["total_failure"] += summary.get("total_failure", 0)
            t["total_duration_minutes"] += summary.get("total_duration_ms", 0) / 60000
            t["essential_calls"] += summary.get("essential_calls", 0)
            t["runs_used"] += 1
            t["by_type"][atype]["calls"] += summary.get("total_calls", 0)
            t["by_type"][atype]["runs"] += 1

            for ep, ep_data in summary.get("endpoints", {}).items():
                t["endpoints"][ep] += ep_data.get("count", 0)

    return {
        "total_runs": len(runs),
        "analysis_types": sorted(seen_types),
        "api_summary": dict(api_totals),
    }


def print_monthly_report(month: str, runs: list[dict]):
    """打印月度汇总"""
    aggr = aggregate_runs(runs)

    print(f"\n{'='*60}")
    print(f"  API 用量月度报告 — {month}")
    print(f"{'='*60}")
    print(f"  分析次数: {aggr['total_runs']}")
    print(f"  分析类型: {', '.join(ANALYSIS_TYPES_CN.get(t, t) for t in aggr['analysis_types'])}")

    for api_name, info in API_PRICING.items():
        t = aggr["api_summary"].get(api_name)
        if not t:
            continue
        print(f"\n  {info['name']} ({info['annual_fee']})")
        print(f"    调用: {t['total_calls']} 次 | 成功: {t['total_success']} | 失败: {t['total_failure']}")
        if t["total_calls"] > 0:
            print(f"    成功率: {t['total_success']/t['total_calls']*100:.1f}%")
        print(f"    参与分析: {t['runs_used']}/{aggr['total_runs']} 次")
        if t["endpoints"]:
            top_eps = sorted(t["endpoints"].items(), key=lambda x: -x[1])[:5]
            print(f"    Top端点: {', '.join(f'{ep}({cnt})' for ep, cnt in top_eps)}")

    print(f"\n{'='*60}\n")


def print_renewal_report(runs: list[dict]):
    """打印年度续约推荐报告"""
    aggr = aggregate_runs(runs)

    print(f"\n{'='*60}")
    print(f"  API 续约评估报告")
    print(f"  覆盖 {len(runs)} 次分析")
    print(f"{'='*60}")

    for api_name, info in API_PRICING.items():
        if not info["paid"]:
            continue  # 续约报告只关注付费 API

        t = aggr["api_summary"].get(api_name)
        if not t:
            print(f"\n  {info['name']} — 无使用记录 → ❌ 不续约")
            continue

        calls = t["total_calls"]
        runs_used = t["runs_used"]
        success_rate = t["total_success"] / calls * 100 if calls > 0 else 0

        # 分析类型覆盖
        type_coverage = ", ".join(
            f"{ANALYSIS_TYPES_CN.get(typ, typ)}({d['calls']}次)"
            for typ, d in sorted(t["by_type"].items(), key=lambda x: -x[1]["calls"])
        )

        # 续约建议
        if calls == 0:
            rec = "❌ 不续约"
            reason = "全年无调用"
        elif api_name == "wisburg":
            if runs_used >= len(runs) * 0.5:
                rec = "✅ 续约"
                reason = f"核心依赖，参与{runs_used}/{len(runs)}次分析，卖方研报+电话会纪要不可替代"
            else:
                rec = "⚠️ 评估"
                reason = f"使用频率中等({runs_used}/{len(runs)}次)，需判断是否可降级"
        elif api_name == "lixinger":
            if runs_used >= len(runs) * 0.3:
                rec = "✅ 续约"
                reason = f"CNINFO互补({runs_used}/{len(runs)}次)，增减持/K线/监管独有功能不可替代"
            else:
                rec = "⚠️ 评估"
                reason = f"使用频率偏低({runs_used}/{len(runs)}次)，CNINFO可覆盖多少需评估"

        print(f"\n  ┌─ {info['name']} ({info['annual_fee']})")
        print(f"  ├─ 调用: {calls} 次 | 成功率: {success_rate:.1f}%")
        print(f"  ├─ 覆盖: {type_coverage}")
        print(f"  ├─ 续约建议: {rec}")
        print(f"  └─ 理由: {reason}")

    # 免费 API 小结
    print(f"\n  ── 免费/低成本 API ──")
    for api_name, info in API_PRICING.items():
        if info["paid"]:
            continue
        t = aggr["api_summary"].get(api_name)
        if not t:
            print(f"  {info['name']}: 无使用记录")
            continue
        print(f"  {info['name']}: {t['total_calls']}次调用 / {t['runs_used']}次分析")

    print(f"\n{'='*60}\n")


def list_available_months() -> list[str]:
    """列出所有有数据的月份"""
    if not USAGE_DIR.is_dir():
        return []
    months = []
    for d in sorted(USAGE_DIR.iterdir()):
        if d.is_dir() and len(d.name) == 7 and d.name[4] == "-":
            # 检查是否有 JSON 文件
            if list(d.glob("*.json")):
                months.append(d.name)
    return months


# ══════════════════════════════════════════════════════════════
# 命令行入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    # Windows GBK workaround
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

    ap = argparse.ArgumentParser(description="API 用量聚合与续约报告")
    ap.add_argument("--month", default="", help="指定月份 YYYY-MM（默认本月）")
    ap.add_argument("--months", type=int, default=0, help="最近N个月")
    ap.add_argument("--yearly", action="store_true", help="年度续约报告")
    ap.add_argument("--renewal", action="store_true", help="续约推荐表")
    args = ap.parse_args()

    # 确定要分析的时间范围
    available = list_available_months()

    if not available:
        print("暂无 API 用量数据。")
        print(f"数据目录: {USAGE_DIR}")
        print("运行一次分析后，run 日志会自动写入该目录。")
        sys.exit(0)

    if args.month:
        months = [args.month]
    elif args.months:
        months = available[-args.months:]
    elif args.yearly or args.renewal:
        months = available  # 全部可用月份
    else:
        # 默认：本月
        this_month = datetime.now(TZ).strftime("%Y-%m")
        months = [this_month] if this_month in available else [available[-1]]

    # 去重排序
    months = sorted(set(months))

    runs = load_runs(months)
    if not runs:
        print(f"指定月份无数据: {', '.join(months)}")
        sys.exit(0)

    if args.renewal or args.yearly:
        print_renewal_report(runs)
    else:
        print_monthly_report(months[0] if len(months) == 1 else f"{months[0]} ~ {months[-1]}", runs)
