"""
Tavily 搜索工具模块 - 供 PreBuy 分析流程调用

用途：
  - 红旗排查（监管处罚、负面事件、诉讼）
  - 近期重大事件（公告、并购、管理层变动）
  - 公司基础信息补全（无法从 tushare 获取时）

不替代 web_fetch：结构化财务数据（东方财富/stockanalysis URL）仍用 web_fetch。
"""

import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv(r'E:\ObsidianVaults\ZephyrSpace\.env')
_client = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        key = os.getenv('TAVILY_KEY')
        if not key:
            raise EnvironmentError("TAVILY_KEY 未在 .env 中设置")
        _client = TavilyClient(api_key=key)
    return _client


def _fmt(results: list) -> str:
    """将搜索结果格式化为可直接粘贴到 PreBuy 笔记的文本。"""
    if not results:
        return "（无结果）"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r.get('title', '无标题')}**")
        lines.append(f"   {r.get('url', '')}")
        content = (r.get('content') or '').strip()[:300]
        if content:
            lines.append(f"   > {content}")
    return "\n".join(lines)


def search_red_flags(company_name: str, ticker: str = "", max_results: int = 5) -> str:
    """
    搜索公司负面事件：监管处罚、违规、诉讼、高管离职等。

    Args:
        company_name: 公司中文名（如"东方财富"）
        ticker: 股票代码（如"300059.SZ"），可选，用于提高精确度
        max_results: 返回条数，默认 5

    Returns:
        格式化的搜索摘要字符串
    """
    query = f"{company_name} 监管处罚 违规 诉讼 负面 风险"
    if ticker:
        query = f"{ticker} {query}"
    client = _get_client()
    resp = client.search(query, max_results=max_results, search_depth="advanced")
    return _fmt(resp.get('results', []))


def search_recent_news(company_name: str, ticker: str = "", max_results: int = 5) -> str:
    """
    搜索公司近期重大事件：公告、融资、并购、战略调整、管理层变动。

    Args:
        company_name: 公司中文名
        ticker: 股票代码，可选
        max_results: 返回条数，默认 5

    Returns:
        格式化的搜索摘要字符串
    """
    query = f"{company_name} 最新公告 重大事件 融资 并购 管理层"
    if ticker:
        query = f"{ticker} {query}"
    client = _get_client()
    resp = client.search(query, max_results=max_results, search_depth="advanced")
    return _fmt(resp.get('results', []))


def search_company_info(company_name: str, ticker: str = "", max_results: int = 3) -> str:
    """
    搜索公司基础信息：主营业务、市场地位、竞争格局。
    在 tushare 数据不足时用于补充公司页基础信息。

    Args:
        company_name: 公司中文名
        ticker: 股票代码，可选
        max_results: 返回条数，默认 3

    Returns:
        格式化的搜索摘要字符串
    """
    query = f"{company_name} 主营业务 市场地位 竞争格局 行业分析"
    if ticker:
        query = f"{ticker} {query}"
    client = _get_client()
    resp = client.search(query, max_results=max_results, search_depth="basic")
    return _fmt(resp.get('results', []))


def prebuy_web_research(company_name: str, ticker: str = "") -> dict:
    """
    PreBuy 完整网络调研：一次调用返回红旗 + 近期事件 + 公司信息。
    适合在 PreBuy agent 中一次性调用。

    Returns:
        dict with keys: red_flags, recent_news, company_info
    """
    return {
        "red_flags": search_red_flags(company_name, ticker),
        "recent_news": search_recent_news(company_name, ticker),
        "company_info": search_company_info(company_name, ticker),
    }


# ── 命令行快速测试 ──────────────────────────────────────────
if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "东方财富"
    ticker = sys.argv[2] if len(sys.argv) > 2 else ""
    print(f"\n=== PreBuy 网络调研：{name} {ticker} ===\n")
    result = prebuy_web_research(name, ticker)
    for section, content in result.items():
        print(f"\n--- {section} ---")
        print(content)
