"""財經消息監察模組。

免費 Bloomberg/Reuters 網頁不等於付費即時新聞 API；本模組採用保守做法：
1. 保留可信來源入口；
2. 嘗試讀取公開 RSS / 網頁標題；
3. 用關鍵字做簡單消息分數，供推薦排序參考。
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Any


NEWS_SOURCES = [
    {
        "name": "Bloomberg Markets",
        "url": "https://www.bloomberg.com/markets",
        "rss": "https://feeds.bloomberg.com/markets/news.rss",
        "credibility": "high",
    },
    {
        "name": "Reuters Markets",
        "url": "https://www.reuters.com/markets/",
        "rss": "",
        "credibility": "high",
    },
    {
        "name": "HKEX RSS",
        "url": "https://www.hkex.com.hk/services/rss-feeds?sc_lang=zh-hk",
        "rss": "https://www.hkex.com.hk/Services/RSS-Feeds/News-Releases?sc_lang=zh-HK",
        "credibility": "official",
    },
    {
        "name": "HKEXnews",
        "url": "https://www.hkexnews.hk/index.htm",
        "rss": "",
        "credibility": "official",
    },
    {
        "name": "AAStocks Latest News",
        "url": "https://www.aastocks.com/en/stocks/news/aafn/latest-news",
        "rss": "",
        "credibility": "market",
    },
]

POSITIVE_KEYWORDS = ["升", "增長", "盈利", "回購", "突破", "上調", "批准", "beat", "profit", "buyback", "upgrade"]
NEGATIVE_KEYWORDS = ["跌", "虧損", "減持", "調低", "停牌", "訴訟", "miss", "loss", "downgrade", "probe"]


@dataclass
class NewsItem:
    source: str
    title: str
    url: str
    published_at: str = ""


def fetch_market_news(limit: int = 20) -> list[dict[str, Any]]:
    """讀取公開財經消息標題。失敗時回傳來源入口。"""
    items: list[NewsItem] = []

    for source in NEWS_SOURCES:
        try:
            if source.get("rss"):
                items.extend(fetch_rss(source["name"], source["rss"], limit=5))
            else:
                items.extend(fetch_page_titles(source["name"], source["url"], limit=3))
        except Exception:  # noqa: BLE001
            items.append(
                NewsItem(
                    source=source["name"],
                    title=f"{source['name']} source available, live headline fetch failed",
                    url=source["url"],
                    published_at=datetime.now().isoformat(),
                )
            )

    return [item.__dict__ for item in items[:limit]]


def fetch_rss(source_name: str, url: str, limit: int = 5) -> list[NewsItem]:
    request = urllib.request.Request(url, headers={"User-Agent": "hk-stock-analysis/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        root = ET.fromstring(response.read())
    result: list[NewsItem] = []
    for item in root.findall(".//item")[:limit]:
        title = text_or_empty(item.find("title"))
        link = text_or_empty(item.find("link")) or url
        pub_date = text_or_empty(item.find("pubDate"))
        if title:
            result.append(NewsItem(source=source_name, title=title, url=link, published_at=pub_date))
    return result


def fetch_page_titles(source_name: str, url: str, limit: int = 3) -> list[NewsItem]:
    request = urllib.request.Request(url, headers={"User-Agent": "hk-stock-analysis/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        html = response.read().decode("utf-8", errors="ignore")
    titles = re.findall(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    cleaned = [clean_html(title) for title in titles if clean_html(title)]
    return [
        NewsItem(source=source_name, title=title, url=url, published_at=datetime.now().isoformat())
        for title in cleaned[:limit]
    ]


def score_news_for_stock(stock_name: str, news_items: list[dict[str, Any]]) -> dict[str, Any]:
    """用簡單關鍵字估算消息對個股推薦的加減分。"""
    matched = []
    score = 0
    keywords = stock_name_keywords(stock_name)

    for item in news_items:
        title = item.get("title", "")
        if keywords and not any(keyword.lower() in title.lower() for keyword in keywords):
            continue
        delta = 0
        if any(word.lower() in title.lower() for word in POSITIVE_KEYWORDS):
            delta += 5
        if any(word.lower() in title.lower() for word in NEGATIVE_KEYWORDS):
            delta -= 6
        if delta:
            score += delta
            matched.append(item)

    return {
        "news_score": max(-15, min(15, score)),
        "matched_news": matched[:5],
    }


def stock_name_keywords(name: str) -> list[str]:
    short = re.sub(r"[-－].*$", "", name).strip()
    return [short] if len(short) >= 2 else []


def text_or_empty(node: ET.Element | None) -> str:
    return "" if node is None or node.text is None else node.text.strip()


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    return " ".join(value.split())

