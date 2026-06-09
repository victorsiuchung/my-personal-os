"""Markdown 報告生成器。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from config import INDUSTRY_KEYWORDS, REPORT_DIR, TOP_N
from recommender import best_by_industry, categorize_recommendations, rank_recommendations


def generate_report(
    results: list[dict[str, Any]],
    total_count: int,
    filtered_count: int,
    output_dir: Path = REPORT_DIR,
) -> Path:
    """生成 Markdown 報告並保存。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    report_path = output_dir / f"hk_stock_report_{now.strftime('%Y%m%d_%H%M%S')}.md"

    top_items = rank_recommendations(results, TOP_N)
    categories = categorize_recommendations(results)
    industry_best = best_by_industry(results, INDUSTRY_KEYWORDS)

    content = []
    content.append("# 港股全市場技術分析報告\n")
    content.append("## 一、執行摘要\n")
    content.append(f"- 分析時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")
    content.append(f"- 全市場股票總數：{total_count}")
    content.append(f"- 篩選後符合條件數量：{filtered_count}")
    content.append(f"- 成功完成技術分析數量：{len(results)}")
    content.append(f"- 市場情緒總覽：{market_sentiment(results)}\n")

    content.append("## 二、Top 10 強烈推薦列表\n")
    content.append(table_for_items(top_items[:10]))

    content.append("\n## 三、分類推薦\n")
    content.append(section_for_category("🔥 強烈買入（評分 > 85）", categories["強烈買入"]))
    content.append(section_for_category("✅ 買入（70-85 分）", categories["買入"]))
    content.append(section_for_category("👀 關注（55-70 分）", categories["關注"]))

    content.append("\n## 四、各行業最佳推薦\n")
    if industry_best:
        content.append("| 行業 | 代碼 | 名稱 | 現價 | 技術評分 | 信號 |")
        content.append("| :--- | :--- | :--- | ---: | ---: | :--- |")
        for industry, item in industry_best.items():
            content.append(
                f"| {industry} | {item['code']} | {item['name']} | "
                f"{item['current_price']:.2f} | {item['score']} | {item['signal']} |"
            )
    else:
        content.append("- 暫無足夠資料歸類。")

    content.append("\n## 五、技術面信號掃描結果\n")
    content.append(signal_list("MACD 金叉股", results, lambda x: x.get("macd_signal") == "金叉"))
    content.append(signal_list("RSI 超賣反彈機會股", results, lambda x: x.get("rsi_status") == "超賣"))
    content.append(signal_list("成交量異動股", results, lambda x: x.get("volume_surge") is True))
    content.append(signal_list("突破布林帶上軌股", results, lambda x: x.get("boll_position") == "上軌"))

    content.append("\n## 六、風險提示\n")
    content.append(
        "- 本報告只基於技術指標與富途行情數據作量化掃描，不構成投資建議。\n"
        "- 港股波動高，細價股、低流動性股票及消息股風險較大。\n"
        "- 技術信號可能失效，入市前應自行檢查基本面、公告、成交深度與市場環境。\n"
        "- 若富途 API 數據延遲、權限不足或個別股票資料缺失，結果可能不完整。"
    )

    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def market_sentiment(results: list[dict[str, Any]]) -> str:
    if not results:
        return "資料不足"
    avg_score = sum(item.get("score", 0) for item in results) / len(results)
    strong_count = sum(1 for item in results if item.get("score", 0) > 85)
    buy_count = sum(1 for item in results if 70 <= item.get("score", 0) <= 85)
    if avg_score >= 70 or strong_count >= 10:
        return f"偏強（平均分 {avg_score:.1f}，強烈買入 {strong_count}，買入 {buy_count}）"
    if avg_score >= 55:
        return f"中性偏強（平均分 {avg_score:.1f}）"
    return f"偏弱（平均分 {avg_score:.1f}）"


def table_for_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- 暫無符合條件股票。\n"
    lines = [
        "| 排名 | 代碼 | 名稱 | 現價 | 買入價 | 止蝕 | 止賺一 | 止賺二 | 技術評分 | 趨勢 | RSI | 信號 |",
        "| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- | :--- | :--- |",
    ]
    for idx, item in enumerate(items, 1):
        plan = item.get("trade_plan", {})
        lines.append(
            f"| {idx} | {item['code']} | {item['name']} | {item['current_price']:.2f} | "
            f"{fmt(plan.get('buy_price'))} | {fmt(plan.get('stop_loss'))} | "
            f"{fmt(plan.get('take_profit_1'))} | {fmt(plan.get('take_profit_2'))} | "
            f"{item['score']} | {item['trend']} | {item['rsi_status']} | {item['signal']} |"
        )
    return "\n".join(lines) + "\n"


def fmt(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"


def section_for_category(title: str, items: list[dict[str, Any]]) -> str:
    lines = [f"\n### {title}"]
    lines.append(table_for_items(items[:20]))
    return "\n".join(lines)


def signal_list(title: str, results: list[dict[str, Any]], predicate) -> str:
    matched = [item for item in results if predicate(item)]
    lines = [f"\n### {title}"]
    if not matched:
        lines.append("- 暫無。")
        return "\n".join(lines)
    for item in sorted(matched, key=lambda x: x.get("score", 0), reverse=True)[:30]:
        lines.append(f"- {item['code']} {item['name']}：評分 {item['score']}，信號 {item['signal']}")
    return "\n".join(lines)
