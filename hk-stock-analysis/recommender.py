"""推薦排序模組。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def rank_recommendations(results: list[dict[str, Any]], top_n: int = 20) -> list[dict[str, Any]]:
    """根據技術評分排序，回傳 Top N。"""
    return sorted(results, key=lambda item: item.get("score", 0), reverse=True)[:top_n]


def categorize_recommendations(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """按評分分類。"""
    categories = {
        "強烈買入": [],
        "買入": [],
        "關注": [],
        "迴避": [],
    }

    for item in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
        score = item.get("score", 0)
        if score > 85:
            categories["強烈買入"].append(item)
        elif score >= 70:
            categories["買入"].append(item)
        elif score >= 55:
            categories["關注"].append(item)
        elif score < 40:
            categories["迴避"].append(item)

    return categories


def best_by_industry(results: list[dict[str, Any]], industry_keywords: dict[str, list[str]]) -> dict[str, dict[str, Any]]:
    """根據名稱關鍵字估算各行業最佳股票。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in results:
        name = item.get("name", "")
        for industry, keywords in industry_keywords.items():
            if any(keyword in name for keyword in keywords):
                grouped[industry].append(item)

    best: dict[str, dict[str, Any]] = {}
    for industry, items in grouped.items():
        best[industry] = max(items, key=lambda x: x.get("score", 0))
    return best

