# -*- coding: utf-8 -*-
"""从商业航天垂直媒体抓取新闻，并按公司与宏观主题归类。"""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCE_CONFIG_PATH = ROOT_DIR / "data" / "sources" / "industry_sources.json"
RULES_PATH = ROOT_DIR / "data" / "classification" / "news_rules.json"
CACHE_DIR = ROOT_DIR / "data" / "cache"
TRANSLATION_CACHE_PATH = CACHE_DIR / "translations" / "news_translations.json"
ARTICLE_CACHE_PATH = CACHE_DIR / "articles" / "article_summaries.json"
DEFAULT_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
MAX_ITEMS_PER_COMPANY = 5
MAX_MACRO_ITEMS = 8
MAX_KEY_EVENTS = 8
TRANSLATION_TIMEOUT = 6
ARTICLE_TIMEOUT = 12


@dataclass
class NewsItem:
    title: str
    url: str
    published_at: str | None
    summary: str | None
    source_name: str
    source_role: str


def make_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"})
    return session


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_whitespace(text: str) -> str:
    unescaped = html.unescape(text)
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()


def normalize_title_for_dedupe(title: str) -> str:
    lowered = title.lower()
    lowered = re.sub(r"\s+", " ", lowered)
    lowered = re.sub(r"[^\w一-鿿 ]+", "", lowered)
    return lowered.strip()


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[一-鿿]", text))


def should_translate(text: str | None) -> bool:
    if not text:
        return False
    normalized = normalize_whitespace(text)
    if not normalized or contains_cjk(normalized):
        return False
    letter_count = len(re.findall(r"[A-Za-z]", normalized))
    return letter_count >= 3


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for parser in (
        lambda text: datetime.fromisoformat(text.replace("Z", "+00:00")),
        lambda text: email.utils.parsedate_to_datetime(text),
        lambda text: datetime.strptime(text, "%Y-%m-%d"),
    ):
        try:
            parsed = parser(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def sort_key(item: NewsItem) -> tuple[int, str]:
    parsed = parse_datetime(item.published_at)
    if parsed is None:
        return (0, item.title)
    return (int(parsed.timestamp()), item.title)


def clean_summary_text(summary: str | None) -> str | None:
    if not summary:
        return None
    cleaned = normalize_whitespace(summary)
    cleaned = re.sub(r"The post .*? appeared first on .*?\.?$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Read more\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = normalize_whitespace(cleaned)
    return cleaned or None


def shorten_summary(summary: str | None) -> str | None:
    if not summary:
        return None
    return clean_summary_text(summary)


def load_translation_cache() -> dict[str, str]:
    if not TRANSLATION_CACHE_PATH.exists():
        return {}
    with TRANSLATION_CACHE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict):
        return {str(key): str(value) for key, value in data.items()}
    return {}


def save_translation_cache(cache: dict[str, str]) -> None:
    TRANSLATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRANSLATION_CACHE_PATH.open("w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)


def load_article_cache() -> dict[str, str]:
    if not ARTICLE_CACHE_PATH.exists():
        return {}
    with ARTICLE_CACHE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict):
        return {str(key): str(value) for key, value in data.items()}
    return {}


def save_article_cache(cache: dict[str, str]) -> None:
    ARTICLE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ARTICLE_CACHE_PATH.open("w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)


def make_translation_key(text: str) -> str:
    return hashlib.sha256(normalize_whitespace(text).encode("utf-8")).hexdigest()


def translate_with_google(session: requests.Session, normalized: str) -> str | None:
    response = session.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": normalized,
        },
        timeout=TRANSLATION_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        return None

    translated_parts: list[str] = []
    for part in payload[0]:
        if isinstance(part, list) and part and isinstance(part[0], str):
            translated_parts.append(part[0])
    translated = normalize_whitespace("".join(translated_parts))
    return translated or None


def translate_with_mymemory(session: requests.Session, normalized: str) -> str | None:
    response = session.get(
        "https://api.mymemory.translated.net/get",
        params={"q": normalized, "langpair": "en|zh-CN"},
        timeout=TRANSLATION_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    translated = payload.get("responseData", {}).get("translatedText")
    if not isinstance(translated, str):
        return None
    translated = normalize_whitespace(translated)
    return translated or None


def translate_text(session: requests.Session, text: str, cache: dict[str, str]) -> str | None:
    normalized = normalize_whitespace(text)
    if not should_translate(normalized):
        return None

    cache_key = make_translation_key(normalized)
    cached = cache.get(cache_key)
    if cached:
        return cached

    for translator in (translate_with_mymemory, translate_with_google):
        try:
            translated = translator(session, normalized)
        except Exception:
            translated = None
        if translated:
            cache[cache_key] = translated
            return translated
    return None


def fetch_rss_items(session: requests.Session, config: dict[str, Any]) -> list[NewsItem]:
    timeout = config.get("timeout", DEFAULT_TIMEOUT)
    response = session.get(config["source_url"], timeout=timeout)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items: list[NewsItem] = []
    for node in root.findall('.//item'):
        title = normalize_whitespace(node.findtext('title', default=''))
        link = normalize_whitespace(node.findtext('link', default=''))
        summary = clean_summary_text(node.findtext('description', default=''))
        published_at = normalize_whitespace(node.findtext('pubDate', default='') or node.findtext('published', default=''))
        if not title or not link:
            continue
        items.append(NewsItem(
            title=title,
            url=link,
            published_at=published_at or None,
            summary=summary or None,
            source_name=config['source_name'],
            source_role=config['source_role'],
        ))
    return items


def fetch_all_news() -> list[NewsItem]:
    configs = load_json(SOURCE_CONFIG_PATH)
    session = make_session()
    collected: list[NewsItem] = []
    for config in configs:
        if not config.get('enabled', True):
            continue
        try:
            collected.extend(fetch_rss_items(session, config))
        except Exception:
            continue
    unique: dict[str, NewsItem] = {}
    for item in collected:
        key = normalize_title_for_dedupe(item.title)
        if key not in unique:
            unique[key] = item
    items = list(unique.values())
    items.sort(key=sort_key, reverse=True)
    return items


def should_enrich_summary(summary: str | None) -> bool:
    if not summary:
        return True
    normalized = clean_summary_text(summary)
    if not normalized:
        return True
    return normalized.endswith('...') or normalized.endswith('…')


def extract_article_summary(page_html: str) -> str | None:
    patterns = [
        r"<meta[^>]+property=['\"]og:description['\"][^>]+content=['\"]([^'\"]+)",
        r"<meta[^>]+name=['\"]description['\"][^>]+content=['\"]([^'\"]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.IGNORECASE)
        if not match:
            continue
        summary = clean_summary_text(match.group(1))
        if summary and not summary.endswith('...') and not summary.endswith('…'):
            return summary
    return None


def enrich_summary(session: requests.Session, item: NewsItem, cache: dict[str, str]) -> str | None:
    summary = clean_summary_text(item.summary)
    if not should_enrich_summary(summary):
        return summary

    cached = cache.get(item.url)
    if cached:
        return cached

    try:
        response = session.get(item.url, timeout=ARTICLE_TIMEOUT)
        response.raise_for_status()
        enriched = extract_article_summary(response.text)
    except Exception:
        enriched = None

    if enriched:
        cache[item.url] = enriched
        return enriched
    return summary


def get_bilingual_fields(
    session: requests.Session,
    item: NewsItem,
    translation_cache: dict[str, str],
    article_cache: dict[str, str],
) -> dict[str, str | None]:
    display_summary = enrich_summary(session, item, article_cache)
    return {
        "translated_title": translate_text(session, item.title, translation_cache),
        "summary": display_summary,
        "translated_summary": translate_text(session, display_summary or "", translation_cache),
    }


def classify_items(items: list[NewsItem], rules: dict[str, Any]) -> dict[str, Any]:
    company_buckets: dict[str, list[NewsItem]] = {company['name']: [] for company in rules['companies']}
    macro_items: list[NewsItem] = []
    used_keys: set[str] = set()

    for item in items:
        haystack = f"{item.title} {item.summary or ''}".lower()
        matched_company = False
        for company in rules['companies']:
            if any(keyword.lower() in haystack for keyword in company['keywords']):
                company_buckets[company['name']].append(item)
                matched_company = True
        if matched_company:
            used_keys.add(normalize_title_for_dedupe(item.title))
            continue
        if any(keyword.lower() in haystack for keyword in rules['macro_keywords']):
            macro_items.append(item)

    trimmed_companies = {
        company['name']: bucket[:MAX_ITEMS_PER_COMPANY]
        for company, bucket in zip(rules['companies'], [company_buckets[c['name']] for c in rules['companies']])
    }
    macro_items = macro_items[:MAX_MACRO_ITEMS]

    key_events: list[NewsItem] = []
    for item in items:
        if len(key_events) >= MAX_KEY_EVENTS:
            break
        key = normalize_title_for_dedupe(item.title)
        if key in used_keys or item in macro_items:
            key_events.append(item)
    topic_candidates = []
    for topic in rules['topic_mappings']:
        topic_candidates.append(topic['note_path'])

    return {
        'company_buckets': trimmed_companies,
        'macro_items': macro_items,
        'key_events': key_events,
        'topic_candidates': topic_candidates,
    }


def render_news_item(
    item: NewsItem,
    session: requests.Session,
    translation_cache: dict[str, str],
    article_cache: dict[str, str],
    include_source: bool = False,
    macro_mode: bool = False,
) -> list[str]:
    bilingual = get_bilingual_fields(session, item, translation_cache, article_cache)
    if macro_mode:
        bullet = f'- [{item.title}]({item.url})（{item.published_at or item.source_name}，{item.source_name}）'
    else:
        bullet = f'- [{item.title}]({item.url})'
        if item.published_at:
            bullet += f'（{item.published_at}）'
    lines = [bullet]

    if bilingual["translated_title"]:
        lines.append(f'  ↳ {bilingual["translated_title"]}')

    if bilingual["summary"]:
        lines.append(f'  {bilingual["summary"]}')

    if bilingual["translated_summary"]:
        lines.append(f'  ↳ {bilingual["translated_summary"]}')

    if include_source:
        lines.append(f'  来源：{item.source_name}')

    return lines


def build_report_content(date: str, items: list[NewsItem], rules: dict[str, Any]) -> str:
    classified = classify_items(items, rules)
    company_lookup = {company['name']: company['note_path'] for company in rules['companies']}
    translation_session = make_session()
    translation_cache = load_translation_cache()
    article_cache = load_article_cache()

    lines = [
        '---',
        '类型: 日报',
        f'日期: {date}',
        f'最后更新日期: {date}',
        '来源状态: 行业新闻池自动抓取',
        '---',
        '',
        f'# {date} 商业航天日报',
        '',
        '## 今日重点事件',
        '',
    ]
    if classified['key_events']:
        for item in classified['key_events']:
            lines.extend(render_news_item(item, translation_session, translation_cache, article_cache))
    else:
        lines.append('- 今日未抓取到有效重点事件。')

    lines.extend(['', '## 宏观与产业动态', ''])
    if classified['macro_items']:
        for item in classified['macro_items']:
            lines.extend(render_news_item(item, translation_session, translation_cache, article_cache, macro_mode=True))
    else:
        lines.append('- 暂无单独保留的宏观产业新闻。')

    lines.extend(['', '## 公司动态', ''])
    for company in rules['companies']:
        name = company['name']
        note_path = company_lookup[name].removesuffix('.md')
        lines.extend([f'### [[{note_path}]]', ''])
        bucket = classified['company_buckets'].get(name, [])
        if bucket:
            for item in bucket:
                lines.extend(render_news_item(item, translation_session, translation_cache, article_cache, include_source=True))
        else:
            lines.append('- 今日新闻池中未匹配到该公司相关新闻。')
        lines.append('')

    lines.extend(['## 值得补充到主题页', ''])
    for topic in classified['topic_candidates']:
        lines.append(f'- [[{topic.removesuffix(".md")}]]')

    lines.extend(['', '## 参考来源', ''])
    seen = set()
    for item in items:
        key = (item.source_name, item.source_role)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f'- {item.source_name}（{item.source_role}）')
    save_translation_cache(translation_cache)
    save_article_cache(article_cache)
    return '\n'.join(lines)


def save_cache(date: str, items: list[NewsItem]) -> Path:
    cache_dir = CACHE_DIR / 'industry_news'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f'{date}.json'
    with cache_path.open('w', encoding='utf-8') as file:
        json.dump([asdict(item) for item in items], file, ensure_ascii=False, indent=2)
    return cache_path


def main() -> int:
    parser = argparse.ArgumentParser(description='抓取商业航天行业新闻')
    parser.add_argument('--date', required=True)
    parser.add_argument('--output-format', choices=['json', 'markdown'], default='json')
    args = parser.parse_args()

    items = fetch_all_news()
    save_cache(args.date, items)
    rules = load_json(RULES_PATH)

    if args.output_format == 'markdown':
        print(build_report_content(args.date, items, rules))
    else:
        json.dump([asdict(item) for item in items], sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
