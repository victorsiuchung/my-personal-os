"""本機 Dashboard API Server。

用途：
- 由 Futu OpenD 取得實時數據；
- 輸出推薦 JSON 給 GitHub Pages dashboard；
- 避免在公開 HTML 中暴露任何 token 或直接依賴遠端服務。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from config import FUTU_HOST, FUTU_PORT, TOP_N
from futu_connector import FutuConnector
from news_monitor import fetch_market_news, score_news_for_stock
from recommender import rank_recommendations
from stock_scanner import StockScanner


logger = logging.getLogger(__name__)


class DashboardHandler(BaseHTTPRequestHandler):
    connector: FutuConnector | None = None
    cached_payloads: dict[str, dict] = {}

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.write_json({"ok": True})
            return
        if parsed.path == "/api/news":
            self.write_json({"items": fetch_market_news(limit=20)})
            return
        if parsed.path == "/api/recommendations":
            query = parse_qs(parsed.query)
            refresh = query.get("refresh", ["0"])[0] == "1"
            scope = query.get("scope", ["market"])[0]
            self.write_json(self.get_recommendations(refresh=refresh, scope=scope))
            return
        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def get_recommendations(self, refresh: bool = False, scope: str = "market") -> dict:
        if scope in self.cached_payloads and not refresh:
            return self.cached_payloads[scope]
        if self.connector is None:
            raise RuntimeError("Futu connector is not initialized")

        scanner = StockScanner(self.connector)
        if scope == "hsi":
            results, stats = scanner.scan_hsi()
            source = "Futu OpenD realtime HSI constituent scan"
        else:
            results, stats = scanner.scan_market()
            source = "Futu OpenD realtime full market scan"
        news_items = fetch_market_news(limit=30)

        enriched = []
        for item in results:
            news_impact = score_news_for_stock(item.get("name", ""), news_items)
            item = dict(item)
            item["base_score"] = item.get("score", 0)
            item["news_score"] = news_impact["news_score"]
            item["score"] = max(0, min(100, item["base_score"] + item["news_score"]))
            item["matched_news"] = news_impact["matched_news"]
            enriched.append(item)

        top = rank_recommendations(enriched, TOP_N)
        payload = {
            "source": source,
            "stats": stats,
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "news": news_items,
            "recommendations": top,
        }
        self.cached_payloads[scope] = payload
        return payload

    def write_json(self, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt: str, *args) -> None:
        logger.info(fmt, *args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HK Stock Dashboard API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--futu-host", default=FUTU_HOST)
    parser.add_argument("--futu-port", default=FUTU_PORT, type=int)
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = parse_args()
    try:
        DashboardHandler.connector = FutuConnector(host=args.futu_host, port=args.futu_port)
        server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
        print(f"Dashboard API running at http://{args.host}:{args.port}")
        server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        logger.exception("Dashboard API failed: %s", exc)
        return 1
    finally:
        if DashboardHandler.connector:
            DashboardHandler.connector.close()


if __name__ == "__main__":
    sys.exit(main())
