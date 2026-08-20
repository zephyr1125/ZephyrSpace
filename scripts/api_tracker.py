"""
API 用量追踪模块 — 轻量级、零依赖、静默 fallback
====================================================
每次分析（深度分析/管理层档案/估值分析/周度监控等）启动一个 run，
自动记录各 API 的调用次数、成功率、端点分布。

数据存储在 data/api_usage/YYYY-MM/ 目录下，每个 run 一个 JSON 文件。
月度聚合由 api_usage_report.py 完成。

用法：
    from scripts.api_tracker import get_tracker

    tracker = get_tracker()
    tracker.start_run("deep-analysis", "600519.SH", company_name="贵州茅台")

    # 方式1：上下文管理器（推荐）
    with tracker.track("tavily", "search", essential=True):
        results = client.search(query)

    # 方式2：手动 record_call + record_result
    tracker.record_call("lixinger", "fundamental/non_financial")
    resp = requests.post(...)
    tracker.record_result("lixinger", "fundamental/non_financial", success=True)

    tracker.finish_run()

设计原则：
    - 无 run 时 get_tracker() 返回 NoOpTracker，所有操作静默忽略
    - 所有追踪代码失败时静默 fallback，永不中断主流程
    - JSONL 追加写入，每个 run 一个文件，自然隔离
"""

import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

# ── 项目根目录 ──────────────────────────────────────────────
_VAULT_ROOT = Path(__file__).parent.parent
_USAGE_DIR = _VAULT_ROOT / "data" / "api_usage"


# ══════════════════════════════════════════════════════════════
# Eval Trace 转发器（dispatcher 层埋点）
# 设置环境变量 EVAL_TRACE_PATH=<jsonl 路径> 后，所有 instrumented API
# （cninfo / lixinger / wisburg / tavily）调用都会追加写入 eval trace 记录。
# 未设置时完全无副作用（NoOp）。
# ══════════════════════════════════════════════════════════════

_EVAL_TRACE_ENV = "EVAL_TRACE_PATH"

# cninfo 端点 ID -> 语义方法名（供 workflow grader 的 required-action 匹配）
_CNINFO_ENDPOINT_ALIASES = {
    "p_sysapi1133": "company_profile",
    "p_stock2205": "investment_ratings",
    "p_sysapi1139": "dividends",
    "p_stock2215": "share_changes",
    "p_stock2218": "executive_trades",
    "p_stock2219": "share_freeze",
    "p_stock2220": "share_pledge",
    "p_stock2248": "company_penalties",
    "p_stock2246": "company_lawsuits",
}


def _eval_trace_path() -> Optional[str]:
    return os.environ.get(_EVAL_TRACE_ENV) or None


def _semantic_tool_name(api: str, endpoint: str) -> str:
    if api == "cninfo":
        return "cninfo." + _CNINFO_ENDPOINT_ALIASES.get(endpoint, endpoint)
    return f"{api}.{endpoint}"


def _eval_trace_append(record: dict):
    path = _eval_trace_path()
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _record_eval_call(api: str, endpoint: str, context: str = ""):
    if not _eval_trace_path():
        return
    _eval_trace_append({
        "event": "call",
        "tool_name": _semantic_tool_name(api, endpoint),
        "arguments": {"api": api, "endpoint": endpoint, "context": context},
        "timestamp": _now_iso(),
    })


def _record_eval_result(api: str, endpoint: str, success: bool,
                        duration_ms: float = 0, error: str = ""):
    if not _eval_trace_path():
        return
    _eval_trace_append({
        "event": "result",
        "tool_name": _semantic_tool_name(api, endpoint),
        "result_status": "ok" if success else "error",
        "duration_ms": round(duration_ms, 1),
        "error": error[:200] if error else "",
        "timestamp": _now_iso(),
    })


@contextmanager
def _eval_track(api: str, endpoint: str, context: str = ""):
    """上下文管理器：同时写 eval trace（call + result）。无 EVAL_TRACE_PATH 时无副作用。"""
    _record_eval_call(api, endpoint, context)
    t0 = time.perf_counter()
    success, error = True, ""
    try:
        yield
    except Exception as e:
        success, error = False, str(e)
        raise
    finally:
        elapsed = (time.perf_counter() - t0) * 1000
        _record_eval_result(api, endpoint, success, elapsed, error)


def _ensure_dir(path: Path):
    """确保目录存在，失败静默"""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# No-Op Tracker（无 active run 时的静默 fallback）
# ══════════════════════════════════════════════════════════════

class NoOpTracker:
    """所有方法都是空操作，任何情况下不抛异常（eval trace 转发除外）。"""

    def start_run(self, *args, **kwargs):
        return self

    def finish_run(self, *args, **kwargs):
        return self

    def record_call(self, api, endpoint, *, essential=True, context=""):
        _record_eval_call(api, endpoint, context)
        return self

    def record_result(self, api, endpoint, *, success=True, duration_ms=0, call_id=-1):
        _record_eval_result(api, endpoint, success, duration_ms)
        return self

    def track(self, api, endpoint, *, essential=True, context=""):
        return _eval_track(api, endpoint, context)

    def session_stats(self):
        return {}


class _NoOpContext:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ══════════════════════════════════════════════════════════════
# 正式 Tracker
# ══════════════════════════════════════════════════════════════

class ApiTracker:
    """单次分析 run 的 API 用量追踪器"""

    def __init__(self):
        self._run_id: str = ""
        self._analysis_type: str = ""
        self._target: str = ""
        self._company_name: str = ""
        self._started_at: str = ""
        self._calls: dict = {}  # {api_name: {endpoint: [call_records]}}
        self._active: bool = False

    # ── Run 生命周期 ──────────────────────────────────────

    def start_run(
        self,
        analysis_type: str,
        target: str = "",
        *,
        company_name: str = "",
        metadata: Optional[dict] = None,
    ):
        """
        开始一次分析 run。

        Args:
            analysis_type: 分析类型 slug，如 "deep-analysis", "management-archive",
                          "valuation", "weekly-monitor", "ai-bubble-watch"
            target: 分析目标，通常是股票代码（如 "600519.SH"）或主题名
            company_name: 公司中文简称
            metadata: 额外元数据
        """
        self._run_id = f"{analysis_type}-{target or 'unknown'}-{uuid.uuid4().hex[:8]}"
        self._analysis_type = analysis_type
        self._target = target
        self._company_name = company_name
        self._metadata = metadata or {}
        self._started_at = _now_iso()
        self._calls = {}
        self._active = True

    def finish_run(self):
        """结束 run，写入 JSON 文件到 data/api_usage/YYYY-MM/"""
        global _active_tracker
        if not self._active:
            return
        self._active = False  # 防止重复写入
        # 清除全局引用
        if _active_tracker is self:
            _active_tracker = None

        finished_at = _now_iso()
        month = self._started_at[:7]  # "2026-08"

        # 构建 API 用量摘要
        api_summary = {}
        for api_name, endpoints in self._calls.items():
            all_calls = []
            for endpoint, records in endpoints.items():
                all_calls.extend(records)

            essential = sum(1 for c in all_calls if c.get("essential"))
            success = sum(1 for c in all_calls if c.get("success"))
            failure = len(all_calls) - success
            duration_ms = sum(c.get("duration_ms", 0) for c in all_calls)

            api_summary[api_name] = {
                "total_calls": len(all_calls),
                "total_success": success,
                "total_failure": failure,
                "total_duration_ms": round(duration_ms, 1),
                "essential_calls": essential,
                "endpoints": {
                    ep: {
                        "count": len(recs),
                        "success": sum(1 for r in recs if r.get("success")),
                    }
                    for ep, recs in endpoints.items()
                },
            }

        run_log = {
            "run_id": self._run_id,
            "analysis_type": self._analysis_type,
            "target": self._target,
            "company_name": self._company_name,
            "started_at": self._started_at,
            "finished_at": finished_at,
            "metadata": self._metadata,
            "api_summary": api_summary,
        }

        # 写入文件
        try:
            out_dir = _USAGE_DIR / month
            _ensure_dir(out_dir)
            filename = f"{self._started_at[:10]}_{self._analysis_type}_{self._target}_{uuid.uuid4().hex[:6]}.json"
            filepath = out_dir / filename
            filepath.write_text(
                json.dumps(run_log, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass  # 写入失败不抛异常

    # ── 记录方法 ──────────────────────────────────────────

    def record_call(self, api: str, endpoint: str, *, essential: bool = True, context: str = ""):
        """
        记录一次 API 调用的开始。通常在请求前调用。
        返回值是一个 call_id，用于后续 record_result 关联。
        """
        _record_eval_call(api, endpoint, context)
        if not self._active:
            return -1

        call_id = len(self._calls.get(api, {}).get(endpoint, []))
        record = {
            "timestamp": _now_iso(),
            "essential": essential,
            "context": context,
            "success": None,  # 待 fill
            "duration_ms": 0,
        }

        self._calls.setdefault(api, {}).setdefault(endpoint, []).append(record)
        return call_id

    def record_result(
        self,
        api: str,
        endpoint: str,
        *,
        success: bool = True,
        duration_ms: float = 0,
        call_id: int = -1,
    ):
        """记录一次 API 调用的结果。通常在请求后调用。"""
        _record_eval_result(api, endpoint, success, duration_ms, error="" if success else "call failed")
        if not self._active:
            return

        try:
            records = self._calls.get(api, {}).get(endpoint, [])
            if not records:
                return
            # 找到最近一条 success=None 的记录
            for rec in reversed(records):
                if rec["success"] is None:
                    rec["success"] = success
                    rec["duration_ms"] = round(duration_ms, 1)
                    return
        except Exception:
            pass

    @contextmanager
    def track(self, api: str, endpoint: str, *, essential: bool = True, context: str = ""):
        """
        上下文管理器：自动记录调用前后。

        Usage:
            with tracker.track("tavily", "search", essential=True):
                results = client.search(query)
        """
        call_id = self.record_call(api, endpoint, essential=essential, context=context)
        t0 = time.perf_counter()
        try:
            yield
            success = True
        except Exception:
            success = False
            raise
        finally:
            elapsed = (time.perf_counter() - t0) * 1000
            self.record_result(api, endpoint, success=success, duration_ms=elapsed, call_id=call_id)

    # ── 查询方法 ──────────────────────────────────────────

    def session_stats(self) -> dict:
        """返回当前 run 的简要统计"""
        if not self._active:
            return {}
        stats = {}
        for api_name, endpoints in self._calls.items():
            total = sum(len(recs) for recs in endpoints.values())
            success = sum(
                1 for recs in endpoints.values() for r in recs if r.get("success")
            )
            stats[api_name] = {"total": total, "success": success}
        return stats


# ══════════════════════════════════════════════════════════════
# 全局单例
# ══════════════════════════════════════════════════════════════

_noop = NoOpTracker()
_active_tracker: Optional[ApiTracker] = None


def get_tracker() -> ApiTracker | NoOpTracker:
    """返回当前活跃的 tracker，或 NoOpTracker（静默 fallback）"""
    return _active_tracker if _active_tracker is not None else _noop


def start_run(analysis_type: str, target: str = "", **kwargs):
    """便捷函数：创建并启动一个新的 tracker run"""
    global _active_tracker
    _active_tracker = ApiTracker()
    _active_tracker.start_run(analysis_type, target, **kwargs)
    return _active_tracker


def finish_run():
    """便捷函数：结束当前 tracker run"""
    global _active_tracker
    if _active_tracker is not None:
        _active_tracker.finish_run()
        _active_tracker = None


# ── 工具函数 ──────────────────────────────────────────────

def _now_iso() -> str:
    """返回 ISO 格式当前时间（+08:00 时区）"""
    from datetime import datetime, timezone, timedelta

    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


# ══════════════════════════════════════════════════════════════
# 自测
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    # Windows GBK workaround
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

    print("=== API Tracker Self-Test ===\n")

    # Test 1: NoOp mode (no active run)
    t = get_tracker()
    assert isinstance(t, NoOpTracker), "Should return NoOp when no run"
    with t.track("test", "endpoint"):
        pass  # should not error
    print("[PASS] Test 1: NoOp silent mode")

    # Test 2: Active run + track context manager
    t2 = start_run("test-analysis", "000001.SZ", company_name="TestCo")
    with t2.track("tavily", "search", essential=True, context="test search"):
        pass
    stats = t2.session_stats()
    assert stats["tavily"]["total"] == 1
    assert stats["tavily"]["success"] == 1
    print(f"[PASS] Test 2: session stats = {stats}")

    # Test 3: record_call + record_result manual mode
    t2.record_call("wisburg", "reports", essential=True)
    t2.record_result("wisburg", "reports", success=True, duration_ms=123.4)
    t2.record_call("wisburg", "reports", essential=False, context="extra query")
    t2.record_result("wisburg", "reports", success=False, duration_ms=500)

    stats2 = t2.session_stats()
    assert stats2["wisburg"]["total"] == 2
    assert stats2["wisburg"]["success"] == 1
    print(f"[PASS] Test 3: wisburg stats = {stats2['wisburg']}")

    # Test 4: finish_run writes file
    t2.finish_run()
    files = sorted(Path(_USAGE_DIR).rglob("*.json"))
    latest = files[-1] if files else None
    if latest:
        data = json.loads(latest.read_text(encoding="utf-8"))
        assert data["analysis_type"] == "test-analysis"
        assert data["target"] == "000001.SZ"
        assert "tavily" in data["api_summary"]
        assert "wisburg" in data["api_summary"]
        print(f"[PASS] Test 4: file written to {latest}")
        print(f"   tavily: {data['api_summary']['tavily']}")
        print(f"   wisburg: {data['api_summary']['wisburg']}")
        # Clean up test file
        latest.unlink()
    else:
        print("[WARN] Test 4: no output file found")

    # Test 5: After finish_run, back to NoOp
    t3 = get_tracker()
    assert isinstance(t3, NoOpTracker), "Should return NoOp after finish_run"
    print("[PASS] Test 5: back to NoOp after finish_run")

    # Test 6: Exception in track context should still record failure
    t4 = start_run("test-analysis", "error-test")
    try:
        with t4.track("bad-api", "fail-endpoint"):
            raise ValueError("simulated error")
    except ValueError:
        pass
    stats4 = t4.session_stats()
    assert stats4["bad-api"]["success"] == 0, "Failed call should record success=0"
    t4.finish_run()
    # Clean up test file
    files2 = sorted(Path(_USAGE_DIR).rglob("*.json"))
    if files2:
        for f in files2:
            if "error-test" in f.name:
                f.unlink()
    print(f"[PASS] Test 6: exception tracking, stats = {stats4}")

    print("\n[DONE] All tests passed")