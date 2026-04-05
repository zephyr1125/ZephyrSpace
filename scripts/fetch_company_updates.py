# -*- coding: utf-8 -*-
"""抓取商业航天关注公司的增量动态，并标准化输出。"""

from __future__ import annotations

import argparse
import email.utils
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_CONFIG_PATH = ROOT_DIR / "data" / "sources" / "company_sources.json"
CACHE_DIR = ROOT_DIR / "data" / "cache"
DEFAULT_TIMEOUT = 8
USER_AGENT = "ZephyrSpaceResearchHub/0.1 (+https://obsidian.local)"
TOPIC_PAGES = [
    "02-主题/商业发射",
    "02-主题/低轨卫星互联网",
    "02-主题/卫星通信",
]
REVIEW_SIGNAL_KEYWORDS = [
    "launch",
    "mission",
    "satellite",
    "order",
    "contract",
    "agreement",
    "partnership",
    "funding",
    "financing",
    "ipo",
    "regulatory",
    "approval",
    "获批",
    "签约",
    "合作",
    "融资",
    "订单",
    "发射",
    "试验",
    "试车",
]


@dataclass
class UpdateItem:
    """统一的动态条目结构。"""

    company: str
    note_path: str
    title: str
    url: str
    published_at: str | None
    source_name: str
    source_role: str
    summary: str | None = None


def make_session() -> requests.Session:
    """创建统一的 HTTP 会话。"""
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def load_source_configs() -> list[dict[str, Any]]:
    """读取数据源配置。"""
    with SOURCE_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_whitespace(text: str) -> str:
    """压缩多余空白，保留可读性。"""
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_datetime(value: str | None) -> datetime | None:
    """尽量把不同格式的时间统一成 datetime。"""
    if not value:
        return None

    value = value.strip()
    for parser in (
        lambda text: datetime.fromisoformat(text.replace("Z", "+00:00")),
        lambda text: email.utils.parsedate_to_datetime(text),
        lambda text: datetime.strptime(text, "%Y-%m-%d"),
        lambda text: datetime.strptime(text, "%Y/%m/%d"),
    ):
        try:
            parsed = parser(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def sort_key_for_item(item: UpdateItem) -> tuple[int, str]:
    """为动态排序，优先按时间倒序，再按标题稳定排序。"""
    parsed = parse_datetime(item.published_at)
    if parsed is None:
        return (0, item.title)
    return (int(parsed.timestamp()), item.title)


def fetch_rss_updates(session: requests.Session, config: dict[str, Any]) -> list[UpdateItem]:
    """抓取 RSS/Atom 数据源。"""
    response = session.get(config["source_url"], timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items: list[UpdateItem] = []
    keywords = [keyword.lower() for keyword in config.get("keywords", [])]

    for node in root.findall(".//item"):
        title = normalize_whitespace(node.findtext("title", default=""))
        link = normalize_whitespace(node.findtext("link", default=""))
        summary = normalize_whitespace(node.findtext("description", default=""))
        published_at = normalize_whitespace(
            node.findtext("pubDate", default="") or node.findtext("published", default="")
        )
        haystack = f"{title} {summary}".lower()
        if keywords and not any(keyword in haystack for keyword in keywords):
            continue
        if not title or not link:
            continue

        items.append(
            UpdateItem(
                company=config["company"],
                note_path=config["note_path"],
                title=title,
                url=link,
                published_at=published_at or None,
                source_name=config["source_name"],
                source_role=config["source_role"],
                summary=summary or None,
            )
        )
    return items


def fetch_landspace_updates(session: requests.Session, config: dict[str, Any]) -> list[UpdateItem]:
    """抓取蓝箭航天新闻中心。"""
    response = session.get(config["source_url"], timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    html_text = response.text

    pattern = re.compile(
        r'<a[^>]+href="(?P<href>[^"]*news-detail[^"]*)"[^>]*>(?P<body>.*?)</a>',
        re.S,
    )
    items: list[UpdateItem] = []
    seen: set[str] = set()

    for match in pattern.finditer(html_text):
        href = match.group("href")
        body = normalize_whitespace(re.sub(r"<.*?>", " ", match.group("body")))
        if not body or body.lower() == "learn more":
            continue
        title_match = re.match(r"(?P<date>\d{4}-\d{2}-\d{2}|\d{2}\s+\d{2}月\s+\d{4})\s+(?P<title>.+)", body)
        if title_match:
            published_at = title_match.group("date")
            title = title_match.group("title")
        else:
            published_at = None
            title = body

        absolute_url = urljoin(config["source_url"], href)
        dedupe_key = f"{title}|{absolute_url}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        items.append(
            UpdateItem(
                company=config["company"],
                note_path=config["note_path"],
                title=title,
                url=absolute_url,
                published_at=published_at,
                source_name=config["source_name"],
                source_role=config["source_role"],
            )
        )
    return items


def fetch_ll2_updates(session: requests.Session, config: dict[str, Any]) -> list[UpdateItem]:
    """抓取 Launch Library 2 的发射事件。"""
    response = session.get(config["source_url"], timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = response.json()

    items: list[UpdateItem] = []
    for node in payload.get("results", []):
        title = normalize_whitespace(node.get("name", ""))
        status = (node.get("status") or {}).get("name")
        mission = node.get("mission") or {}
        if isinstance(mission, dict):
            subtitle = normalize_whitespace(mission.get("description") or mission.get("name") or "")
        else:
            subtitle = normalize_whitespace(str(mission))
        summary_parts = [part for part in [status, subtitle] if part]
        summary = " | ".join(summary_parts) if summary_parts else None
        if not title:
            continue

        items.append(
            UpdateItem(
                company=config["company"],
                note_path=config["note_path"],
                title=title,
                url=node.get("url") or config["source_url"],
                published_at=node.get("net"),
                source_name=config["source_name"],
                source_role=config["source_role"],
                summary=summary,
            )
        )
    return items


def fetch_updates_for_source(session: requests.Session, config: dict[str, Any]) -> dict[str, Any]:
    """抓取单个来源，并返回标准化结果。"""
    if not config.get("enabled", True) or config.get("source_type") == "disabled":
        return {
            "company": config["company"],
            "note_path": config["note_path"],
            "source_name": config["source_name"],
            "source_role": config.get("source_role", "待接入"),
            "source_url": config.get("source_url", ""),
            "status": "disabled",
            "items": [],
            "reason": config.get("reason", "数据源已禁用。"),
        }

    fetchers = {
        "rss": fetch_rss_updates,
        "rss_keyword": fetch_rss_updates,
        "landspace_html": fetch_landspace_updates,
        "ll2_launches": fetch_ll2_updates,
    }

    fetcher = fetchers.get(config["source_type"])
    if fetcher is None:
        return {
            "company": config["company"],
            "note_path": config["note_path"],
            "source_name": config["source_name"],
            "source_role": config.get("source_role", "未知"),
            "source_url": config.get("source_url", ""),
            "status": "error",
            "items": [],
            "reason": f"暂不支持的数据源类型：{config['source_type']}",
        }

    try:
        items = fetcher(session, config)
        items.sort(key=sort_key_for_item, reverse=True)
        items = items[:3]
        return {
            "company": config["company"],
            "note_path": config["note_path"],
            "source_name": config["source_name"],
            "source_role": config.get("source_role", "未知"),
            "source_url": config.get("source_url", ""),
            "status": "ok",
            "items": [asdict(item) for item in items],
        }
    except Exception as error:
        return {
            "company": config["company"],
            "note_path": config["note_path"],
            "source_name": config["source_name"],
            "source_role": config.get("source_role", "未知"),
            "source_url": config.get("source_url", ""),
            "status": "error",
            "items": [],
            "reason": str(error),
        }


def fetch_all_updates() -> list[dict[str, Any]]:
    """抓取所有已配置公司来源。"""
    session = make_session()
    results = []
    for config in load_source_configs():
        results.append(fetch_updates_for_source(session, config))
    return results


def build_review_signals(results: list[dict[str, Any]]) -> list[UpdateItem]:
    """从标题中提取值得复查的信号。"""
    items: list[UpdateItem] = []
    for result in results:
        for raw_item in result.get("items", []):
            title = raw_item["title"].lower()
            if any(keyword in title for keyword in REVIEW_SIGNAL_KEYWORDS):
                items.append(UpdateItem(**raw_item))
    items.sort(key=sort_key_for_item, reverse=True)
    return items[:6]


def build_report_content(date: str, results: list[dict[str, Any]]) -> str:
    """根据抓取结果生成日报内容。"""
    all_items = [
        UpdateItem(**raw_item)
        for result in results
        for raw_item in result.get("items", [])
    ]
    all_items.sort(key=sort_key_for_item, reverse=True)
    top_items = all_items[:5]
    review_signals = build_review_signals(results)

    lines = [
        "---",
        "类型: 日报",
        f"日期: {date}",
        f"最后更新日期: {date}",
        "来源状态: 自动抓取",
        "---",
        "",
        f"# {date} 商业航天日报",
        "",
        "## 今日重点事件",
        "",
    ]

    if top_items:
        for item in top_items:
            lines.append(
                f"- [[{item.note_path.removesuffix('.md')}]]: "
                f"[{item.title}]({item.url})"
                + (f"（{item.published_at}，{item.source_name}）" if item.published_at else f"（{item.source_name}）")
            )
    else:
        lines.append("- 今日未抓取到可用事件，需人工复查数据源。")

    lines.extend(["", "## 公司动态", ""])

    for result in results:
        company_link = result["note_path"].removesuffix(".md")
        lines.extend([f"### [[{company_link}]]", ""])
        status = result["status"]
        items = result.get("items", [])

        if status == "ok" and items:
            for raw_item in items:
                item = UpdateItem(**raw_item)
                bullet = f"- [{item.title}]({item.url})"
                if item.published_at:
                    bullet += f"（{item.published_at}）"
                if item.summary:
                    bullet += f"：{item.summary}"
                bullet += f"；来源：{item.source_name}"
                lines.append(bullet)
        elif status == "disabled":
            lines.append(f"- 暂未接入自动抓取：{result.get('reason', '待补充。')}")
        else:
            lines.append(f"- 抓取失败：{result.get('reason', '未知错误')}")
        lines.append("")

    lines.extend(["## 值得复查的信号", ""])
    if review_signals:
        for item in review_signals:
            lines.append(
                f"- [[{item.note_path.removesuffix('.md')}]]: "
                f"[{item.title}]({item.url})"
                + (f"（{item.published_at}）" if item.published_at else "")
            )
    else:
        lines.append("- 暂无自动识别出的重点信号，建议人工浏览公司动态。")

    lines.extend(["", "## 候选补充页面", ""])
    for topic in TOPIC_PAGES:
        lines.append(f"- [[{topic}]]")

    lines.extend(["", "## 参考来源", ""])
    seen_sources: set[tuple[str, str]] = set()
    for result in results:
        source_key = (result["source_name"], result["source_url"])
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        if result["source_url"]:
            lines.append(f"- [{result['source_name']}]({result['source_url']})（{result['source_role']}）")
        else:
            lines.append(f"- {result['source_name']}（{result['source_role']}）")

    return "\n".join(lines)


def save_cache(date: str, results: list[dict[str, Any]]) -> Path:
    """把抓取结果写入本地缓存，方便后续调试和比对。"""
    cache_dir = CACHE_DIR / "company_updates"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{date}.json"
    with cache_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    return cache_path


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取商业航天公司动态")
    parser.add_argument("--date", required=True)
    parser.add_argument("--output-format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    results = fetch_all_updates()
    save_cache(args.date, results)

    if args.output_format == "markdown":
        print(build_report_content(args.date, results))
    else:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

