"""
财新开放数据 API 工具模块
=========================

已验证端点 (3个):
  GET /api/open/news/list      数据新闻列表（分页，按时间倒序）
  GET /api/open/companies/hot  近期热门报道企业（20条）
  GET /api/open/persons/hot    近期热门报道人物（20条）

鉴权: uid 必须放在 HTTP Header，不能用 Query String（文档有误）。

局限: 当前不支持按公司名/股票代码/关键词搜索，仅限全量拉取。
      待财新开放搜索接口后可扩展。

用法:
    from scripts.caixin_api import CaixinClient
    client = CaixinClient()

    news = client.news_list(page_num=1, page_size=20)
    companies = client.hot_companies()
    persons = client.hot_persons()
"""

import json
import os
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URL = "https://cxdata.caixin.com/api/open"


def _load_dotenv() -> None:
    """从项目根目录 .env 加载环境变量（不覆盖已有值）。"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key not in os.environ:
            os.environ[key] = value


_load_dotenv()


class CaixinClient:
    """财新开放数据 API 客户端。"""

    def __init__(self, uid: str | None = None):
        self.uid = uid or os.getenv("CAIXIN_UID")
        if not self.uid:
            raise EnvironmentError("CAIXIN_UID 未在 .env 中设置")

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{BASE_URL}{path}"
        if params:
            qs = urllib.parse.urlencode(params)
            url = f"{url}?{qs}"
        req = urllib.request.Request(url, headers={"uid": self.uid})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    # ── 新闻 ────────────────────────────────────────────

    def news_list(self, page_num: int = 1, page_size: int = 20) -> dict:
        """获取数据新闻列表，按发布时间倒序。

        Args:
            page_num: 页码，从 1 开始。
            page_size: 每页条数，最大 100。
        """
        if page_size > 100:
            page_size = 100
        return self._get("/news/list", {"pageNum": page_num, "pageSize": page_size})

    def news_list_all_pages(self, page_size: int = 100, max_pages: int | None = None) -> list[dict]:
        """遍历所有分页，返回全部新闻条目（合并后的 list）。

        Warning: 总数据量超过 11 万条，全量拉取耗时较长，谨慎使用。
        """
        all_items: list[dict] = []
        page = 1
        while True:
            result = self.news_list(page_num=page, page_size=page_size)
            data = result.get("data", {})
            items = data.get("list", [])
            all_items.extend(items)
            if not data.get("next") or (max_pages and page >= max_pages):
                break
            page += 1
        return all_items

    # ── 企业 ────────────────────────────────────────────

    def hot_companies(self) -> list[dict]:
        """获取近期在财新报道中频繁出现的核心企业列表（默认 20 条）。"""
        result = self._get("/companies/hot")
        return result.get("data", [])

    # ── 人物 ────────────────────────────────────────────

    def hot_persons(self) -> list[dict]:
        """获取近期在财新报道中频繁出现的核心人物列表（默认 20 条）。"""
        result = self._get("/persons/hot")
        return result.get("data", [])


# ── 便捷函数 ────────────────────────────────────────────

_client: CaixinClient | None = None


def _get_client() -> CaixinClient:
    global _client
    if _client is None:
        _client = CaixinClient()
    return _client


def news_list(page_num: int = 1, page_size: int = 20) -> dict:
    return _get_client().news_list(page_num, page_size)


def hot_companies() -> list[dict]:
    return _get_client().hot_companies()


def hot_persons() -> list[dict]:
    return _get_client().hot_persons()
