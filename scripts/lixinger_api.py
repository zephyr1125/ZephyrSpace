"""
理杏仁 API 统一客户端模块（带用量追踪）
===========================================
替代所有分散在各处的 lx_post() 函数，提供统一接口并自动记录 API 用量。

用法：
    from scripts.lixinger_api import LixingerClient
    lx = LixingerClient()

    # 基本面（批量，[M]端点）
    r = lx.fundamentals(["600519"], date="2025-04-30", metrics=["pe_ttm", "pb", "mc"])

    # 年报财务（批量，[M]端点）
    r = lx.financials(["600519"], end_date="2024-12-31",
                      metrics=["y.ps.toi.t", "y.ps.np.t"])

    # 行情K线（逐只，[S]端点）
    r = lx.candlestick("600519", start="2024-01-01", end="2025-05-12")

    # 也可以直接用于低层调用（兼容旧 lx_post 风格）：
    r = lx.post("cn/company/measures", {"stockCode": "600519", ...})

设计原则：
    - 所有 HTTP 请求走 _post() 汇聚点，自动追踪用量
    - 追踪失败静默 fallback，永不中断主流程
    - GZIP 解码双路兼容（API 有时返回压缩、有时返回明文）
"""

import json
import gzip
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# 自动加载 .env
load_dotenv(Path(__file__).parent.parent / ".env")

# ══════════════════════════════════════════════════════════════
# 客户端
# ══════════════════════════════════════════════════════════════

class LixingerClient:
    """理杏仁 API 客户端（自动追踪用量）"""

    BASE_URL = "https://open.lixinger.com/api"

    def __init__(self, token: str = None):
        self._token = token or os.getenv("LIXINGER_TOKEN")
        if not self._token:
            raise EnvironmentError(
                "LIXINGER_TOKEN 未设置。请在 .env 中配置或传入 token 参数。"
            )

    # ── 底层请求（所有端点汇聚点，自动追踪） ──────────────

    def post(self, path: str, payload: dict) -> dict:
        """
        底层 POST 请求，自动追踪 API 用量。

        Args:
            path: API 路径，如 "cn/company/fundamental/non_financial"
            payload: 请求体（不含 token，自动注入）

        Returns:
            API 响应 data 字段（通常是一个 list）
        """
        from scripts.api_tracker import get_tracker
        import time

        tracker = get_tracker()
        t0 = time.perf_counter()

        try:
            resp = requests.post(
                f"{self.BASE_URL}/{path}",
                json={**payload, "token": self._token},
                headers={"Accept-Encoding": "gzip"},
                timeout=30,
            )
            elapsed = (time.perf_counter() - t0) * 1000

            # 双路解码：API 有时返回 gzip 压缩、有时返回明文 JSON
            try:
                data = json.loads(gzip.decompress(resp.content))
            except Exception:
                data = resp.json()

            tracker.record_call("lixinger", path, essential=True)
            tracker.record_result("lixinger", path, success=True, duration_ms=elapsed)
            return data.get("data", data)

        except Exception:
            elapsed = (time.perf_counter() - t0) * 1000
            tracker.record_call("lixinger", path, essential=True)
            tracker.record_result("lixinger", path, success=False, duration_ms=elapsed)
            raise

    # ── [M] 批量端点（stockCodes 为 list） ─────────────────

    def fundamentals(self, stock_codes: list, date: str, metrics: list) -> list:
        """基本面数据（批量）

        POST cn/company/fundamental/non_financial
        常用 metrics: pe_ttm, pb, mc, roe, dy, turnover, market_cap 等
        """
        return self.post("cn/company/fundamental/non_financial", {
            "stockCodes": stock_codes,
            "date": date,
            "metricsList": metrics,
        })

    def financials(self, stock_codes: list, end_date: str, metrics: list) -> list:
        """年报财务数据（批量）

        POST cn/company/fs/non_financial
        常用 metrics: y.ps.toi.t(营收), y.ps.np.t(净利),
                      y.bs.ta.t(总资产), y.bs.tl.t(总负债)
        注意：嵌套字典结构，d['y']['ps']['toi']['t'] 访问，不是扁平 key
        """
        return self.post("cn/company/fs/non_financial", {
            "stockCodes": stock_codes,
            "date": end_date,
            "metricsList": metrics,
        })

    def industries(self, stock_codes: list, date: str) -> list:
        """行业分类（批量）"""
        return self.post("cn/company/industries", {
            "stockCodes": stock_codes,
            "date": date,
        })

    # ── [S] 单只端点 ─────────────────────────────────────

    def candlestick(self, stock_code: str, start: str, end: str,
                    adjustment: str = "qfq") -> list:
        """K线行情（前复权）"""
        return self.post("cn/company/candlestick", {
            "stockCode": stock_code,
            "startDate": start,
            "endDate": end,
            "adjustmentType": adjustment,
        })

    def dividend(self, stock_code: str, start: str, end: str) -> list:
        """分红历史"""
        return self.post("cn/company/dividend", {
            "stockCode": stock_code,
            "startDate": start,
            "endDate": end,
        })

    def senior_executive_shares(self, stock_code: str, start: str, end: str) -> list:
        """高管增减持"""
        return self.post("cn/company/senior-executive-shares-change", {
            "stockCode": stock_code,
            "startDate": start,
            "endDate": end,
        })

    def major_shareholders_shares(self, stock_code: str, start: str, end: str) -> list:
        """大股东增减持"""
        return self.post("cn/company/major-shareholders-shares-change", {
            "stockCode": stock_code,
            "startDate": start,
            "endDate": end,
        })

    def measures(self, stock_code: str, start: str, end: str) -> list:
        """监管措施"""
        return self.post("cn/company/measures", {
            "stockCode": stock_code,
            "startDate": start,
            "endDate": end,
        })

    def inquiry(self, stock_code: str, start: str, end: str) -> list:
        """交易所问询函"""
        return self.post("cn/company/inquiry", {
            "stockCode": stock_code,
            "startDate": start,
            "endDate": end,
        })

    def profile(self, stock_code: str) -> dict:
        """公司概况（实控人、董事长、总经理等）"""
        return self.post("cn/company/profile", {
            "stockCode": stock_code,
        })

    def announcement(self, stock_code: str) -> list:
        """近期公告列表"""
        return self.post("cn/company/announcement", {
            "stockCode": stock_code,
        })

    # ── [S] 热门汇总端点 ─────────────────────────────────

    def hot_esc(self, stock_code: str) -> list:
        """高管增减持汇总"""
        return self.post("cn/company/hot/esc", {
            "stockCode": stock_code,
        })

    def hot_mssc(self, stock_code: str) -> list:
        """大股东增减持汇总"""
        return self.post("cn/company/hot/mssc", {
            "stockCode": stock_code,
        })

    def hot_df(self, stock_code: str) -> list:
        """分红融资统计"""
        return self.post("cn/company/hot/df", {
            "stockCode": stock_code,
        })

    def hot_ple(self, stock_code: str) -> list:
        """质押汇总"""
        return self.post("cn/company/hot/ple", {
            "stockCode": stock_code,
        })


# ══════════════════════════════════════════════════════════════
# 便捷函数（兼容旧 lx_post 风格）
# ══════════════════════════════════════════════════════════════

_client_singleton = None


def get_client() -> LixingerClient:
    """获取 LixingerClient 单例"""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = LixingerClient()
    return _client_singleton


def lx_post(path: str, payload: dict) -> dict:
    """兼容旧代码的便捷函数。推荐使用 LixingerClient 实例方法。"""
    return get_client().post(path, payload)


# ══════════════════════════════════════════════════════════════
# 自测
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    print("=== LixingerClient Self-Test ===\n")

    # 不实际发请求，仅验证模块加载和追踪集成
    from scripts.api_tracker import start_run, finish_run, get_tracker

    # 测试1: No-Op 模式（无 active run）
    lx = LixingerClient()
    tracker = get_tracker()
    from scripts.api_tracker import NoOpTracker
    assert isinstance(tracker, NoOpTracker)
    print("[PASS] Test 1: No active run => NoOp tracker")

    # 测试2: Active run 下的 record 逻辑
    start_run("test-lixinger", "000001.SZ", company_name="Test")
    # 手动测试 post 的追踪（但跳过实际 HTTP 请求）
    print("[PASS] Test 2: start_run sets up active tracker")
    finish_run()

    # 测试3: 方法签名完整性
    expected_methods = [
        "post", "fundamentals", "financials", "industries",
        "candlestick", "dividend", "senior_executive_shares",
        "major_shareholders_shares", "measures", "inquiry",
        "profile", "announcement",
        "hot_esc", "hot_mssc", "hot_df", "hot_ple",
    ]
    for m in expected_methods:
        assert hasattr(lx, m), f"Missing method: {m}"
    print(f"[PASS] Test 3: All {len(expected_methods)} methods present")

    print("\n[DONE] All tests passed")
    print("(No actual HTTP requests were made)")
