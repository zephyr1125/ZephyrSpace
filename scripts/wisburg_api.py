"""
智堡 (Wisburg) API 工具模块
=============================
提供对智堡研究平台的9个API端点的封装，用于深度分析、周度监控、数据验证。

认证: Bearer Token (WISBURG_KEY in .env)
Base URL: https://api-omen.wisburg.com

端点一览:
  /api/reports        — 投行研报（摩根士丹利/瑞银等）→ 摘要为 markdown
  /api/company-reports — 围绕单一上市公司的企业研究
  /api/earningscalls   — 电话会纪要（含参会人名单、财务指标、Q&A）
  /api/articles        — 专栏文章 → 正文为 HTML
  /api/feed            — 资讯流（快讯级别，content 字段为 markdown）
  /api/market-daily    — AI 市场日报
  /api/archives        — 文献（央行讲话/IMF报告/学术论文）
  /api/am-reports      — 资管机构研究报告（安联/CME等）
  /api/images          — 图片流（信息图 + 详细文字解读）

用法:
    from scripts.wisburg_api import WisburgClient
    client = WisburgClient()

    # 搜索投行研报
    items = client.search_reports("比亚迪", first=5)
    detail = client.get_report_detail(90479)  # 获取摘要全文

    # 搜索电话会纪要
    calls = client.search_earnings_calls("宁德时代")

    # 深度分析一站式拉取
    bundle = client.deep_analysis_bundle("比亚迪")
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# 客户端
# ══════════════════════════════════════════════════════════════

class WisburgClient:
    """智堡 API 客户端"""

    BASE_URL = "https://api-omen.wisburg.com"

    def __init__(self, key: str = None):
        if key is None:
            # 尝试从 .env 读取
            try:
                from dotenv import load_dotenv
                load_dotenv(Path(__file__).parent.parent / ".env")
            except ImportError:
                pass
            key = os.getenv("WISBURG_KEY")
        if not key:
            raise EnvironmentError(
                "WISBURG_KEY 未设置。请在 .env 中配置或传入 key 参数。"
            )
        self._key = key

    def _api(self, path: str) -> dict:
        """底层 GET 请求"""
        url = f"{self.BASE_URL}{path}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self._key}",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("code") != 200:
            raise RuntimeError(f"Wisburg API error {data.get('code')}: {data.get('message')}")
        return data

    def _list(self, endpoint: str, query: str = "", first: int = 20,
              after: str = "", start_time: str = "", end_time: str = "") -> list:
        """通用列表查询 → 返回 items 列表"""
        params = {"first": str(min(first, 100))}
        if query:
            params["query"] = query
        if after:
            params["after"] = after
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        qs = urllib.parse.urlencode(params)
        data = self._api(f"{endpoint}?{qs}")
        return data["data"]["items"]

    def _detail(self, endpoint: str, item_id: int) -> dict:
        """通用详情查询 → 返回 data 对象"""
        data = self._api(f"{endpoint}/{item_id}")
        return data["data"]

    # ── 1. 投行研报 ──────────────────────────────────────

    def search_reports(self, query: str = "", first: int = 20,
                       start_time: str = "", end_time: str = "") -> list:
        """搜索投行研报列表

        Returns: list of {id, title, datetime}
        """
        return self._list("/api/reports", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    def get_report_detail(self, report_id: int) -> dict:
        """获取研报详情

        Returns: {id, title, datetime, summary(markdown), url(or empty)}
        """
        return self._detail("/api/reports", report_id)

    # ── 2. 企业研究 ──────────────────────────────────────

    def search_company_reports(self, query: str = "", first: int = 20,
                               start_time: str = "", end_time: str = "") -> list:
        """搜索企业研究报告列表

        Returns: list of {id, title, datetime}
        """
        return self._list("/api/company-reports", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    def get_company_report_detail(self, report_id: int) -> dict:
        """获取企业研究报告详情

        Returns: {id, title, datetime, summary(markdown), url(or empty)}
        """
        return self._detail("/api/company-reports", report_id)

    # ── 3. 电话会纪要 ────────────────────────────────────

    def search_earnings_calls(self, query: str = "", first: int = 20,
                              start_time: str = "", end_time: str = "") -> list:
        """搜索电话会纪要列表

        Returns: list of {id, title, datetime}
        """
        return self._list("/api/earningscalls", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    def get_earnings_call_detail(self, call_id: int) -> dict:
        """获取电话会纪要详情

        Returns: {id, title, datetime, summary(markdown), url(or empty)}
        """
        return self._detail("/api/earningscalls", call_id)

    # ── 4. 专栏文章 ──────────────────────────────────────

    def search_articles(self, query: str = "", first: int = 20,
                        start_time: str = "", end_time: str = "") -> list:
        """搜索专栏文章列表

        Returns: list of {id, title, datetime, description(or empty)}
        """
        return self._list("/api/articles", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    def get_article_detail(self, article_id: int) -> dict:
        """获取文章详情

        Returns: {id, title, datetime, description, body(HTML)}
        """
        return self._detail("/api/articles", article_id)

    # ── 5. 资讯流 ──────────────────────────────────────

    def search_feed(self, query: str = "", first: int = 20,
                    start_time: str = "", end_time: str = "") -> list:
        """搜索资讯流

        Returns: list of {id, title, datetime, content(markdown)}
        Note: feed 用 content 字段，非 summary
        """
        return self._list("/api/feed", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    # ── 6. AI市场日报 ────────────────────────────────────

    def list_market_daily(self, first: int = 20,
                          start_time: str = "", end_time: str = "") -> list:
        """获取 AI 市场日报列表

        Returns: list of {id, title, datetime}
        """
        return self._list("/api/market-daily", first=first,
                         start_time=start_time, end_time=end_time)

    # ── 7. 文献 ─────────────────────────────────────────

    def search_archives(self, query: str = "", first: int = 20,
                        start_time: str = "", end_time: str = "") -> list:
        """搜索文献列表

        Returns: list of {id, title, datetime}
        """
        return self._list("/api/archives", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    def get_archive_detail(self, archive_id: int) -> dict:
        """获取文献详情

        Returns: {id, title, datetime, summary(markdown), url(or empty)}
        """
        return self._detail("/api/archives", archive_id)

    # ── 8. 资管报告 ──────────────────────────────────────

    def search_am_reports(self, query: str = "", first: int = 20,
                          start_time: str = "", end_time: str = "") -> list:
        """搜索资管机构研究报告列表

        Returns: list of {id, title, datetime}
        """
        return self._list("/api/am-reports", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    def get_am_report_detail(self, report_id: int) -> dict:
        """获取资管报告详情

        Returns: {id, title, datetime, summary(markdown), url(or empty)}
        """
        return self._detail("/api/am-reports", report_id)

    # ── 9. 图片流 ──────────────────────────────────────

    def search_images(self, query: str = "", first: int = 20,
                      start_time: str = "", end_time: str = "") -> list:
        """搜索图片流列表

        Returns: list of {title, datetime, description, cover_url}
        """
        return self._list("/api/images", query=query, first=first,
                         start_time=start_time, end_time=end_time)

    # ── 快捷复合方法 ────────────────────────────────────

    def prebuy_research(self, company_name: str, ticker: str = "",
                        first: int = 5) -> dict:
        """PreBuy 研报调研：一次调用搜遍 reports + company-reports + earnings calls

        Returns: {reports, company_reports, earnings_calls}
        """
        q = ticker if ticker else company_name
        return {
            "reports": self.search_reports(q, first=first),
            "company_reports": self.search_company_reports(q, first=first),
            "earnings_calls": self.search_earnings_calls(q, first=first),
        }

    def market_pulse(self, query: str = "", first: int = 10) -> dict:
        """市场脉搏：一次拉取 feed + market_daily + images

        Returns: {feed, market_daily, images}
        """
        return {
            "feed": self.search_feed(query, first=first),
            "market_daily": self.list_market_daily(first=first),
            "images": self.search_images(query, first=first),
        }

    def weekly_scan_bundle(self, company_name: str, days: int = 7) -> dict:
        """周度监控数据包：feed + reports + earnings calls 近N天

        Args:
            company_name: 公司名称或股票代码
            days: 回溯天数

        Returns: {feed, reports, earnings_calls}
        """
        import datetime
        start = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        q = company_name
        return {
            "feed": self.search_feed(q, first=10, start_time=start),
            "reports": self.search_reports(q, first=10, start_time=start),
            "earnings_calls": self.search_earnings_calls(q, first=5, start_time=start),
            "company_reports": self.search_company_reports(q, first=10, start_time=start),
        }

    def deep_analysis_bundle(self, company_name: str, ticker: str = "") -> dict:
        """深度分析一站式数据包

        拉取与一家公司相关的所有智堡内容，按维度组织：
        - sell_side: 投行研报（可用于交叉验证财务预测、获取卖方视角）
        - company_deep: 企业研究报告（通常比研报更深）
        - mgmt_voice: 电话会纪要（管理层原始表述）
        - news_snippets: 资讯流快讯
        - market_theme: AI 市场日报（宏观/行业主题背景）
        - visual_data: 相关图表（无id字段，key为title+datetime）

        Returns: dict with keys as above
        """
        q = ticker if ticker else company_name
        return {
            "sell_side": self.search_reports(q, first=10),
            "company_deep": self.search_company_reports(q, first=10),
            "mgmt_voice": self.search_earnings_calls(q, first=5),
            "news_snippets": self.search_feed(q, first=10),
            "market_theme": self.list_market_daily(first=5),
            "visual_data": self.search_images(q, first=5),
        }


# ── 命令行快速测试 ──────────────────────────────────────────

if __name__ == "__main__":
    import sys
    client = WisburgClient()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else ""

        if cmd == "search":
            # python scripts/wisburg_api.py search 比亚迪
            items = client.search_reports(arg, first=5)
            for item in items:
                print(f"  [{item['id']}] {item['title']}")
                print(f"      {item['datetime']}")

        elif cmd == "detail":
            # python scripts/wisburg_api.py detail 90479
            d = client.get_report_detail(int(arg))
            print(f"Title: {d['title']}")
            print(f"Time: {d['datetime']}")
            summary = d.get("summary", "")
            print(f"\nSummary ({len(summary)} chars):\n{summary[:1000]}")
            if d.get("url"):
                print(f"\nURL: {d['url']}")

        elif cmd == "calls":
            # python scripts/wisburg_api.py calls 宁德时代
            calls = client.search_earnings_calls(arg, first=5)
            for c in calls:
                print(f"  [{c['id']}] {c['title']}")

        elif cmd == "feed":
            items = client.search_feed(arg, first=5)
            for item in items:
                print(f"  [{item['id']}] {item['title']}")
                print(f"      {item.get('content', '')[:200]}")

        elif cmd == "bundle":
            # python scripts/wisburg_api.py bundle 比亚迪
            b = client.deep_analysis_bundle(arg)
            for section, items in b.items():
                print(f"\n--- {section} ({len(items)} items) ---")
                for item in items[:3]:
                    print(f"  [{item['id']}] {item['title']}")

        elif cmd == "scan":
            # python scripts/wisburg_api.py scan 绿的谐波
            b = client.weekly_scan_bundle(arg)
            for section, items in b.items():
                if items:
                    print(f"\n--- {section} ({len(items)} items) ---")
                    for item in items[:3]:
                        print(f"  [{item['id']}] {item['title']}")
                        c = item.get("content", "")
                        if c:
                            print(f"      {c[:200]}")
        else:
            print(f"Unknown command: {cmd}")
    else:
        # 默认：展示当前最新研报
        print("=== 智堡最新投行研报 ===")
        items = client.search_reports(first=10)
        for item in items:
            print(f"  [{item['id']}] {item['title']}")
            print(f"      {item['datetime']}")

        print("\n=== 最新 AI 市场日报 ===")
        md = client.list_market_daily(first=5)
        for item in md:
            print(f"  [{item['id']}] {item['title']}")

        print("\n=== 最新资讯流 ===")
        feed = client.search_feed(first=5)
        for item in feed:
            print(f"  [{item['id']}] {item['title']}")
