"""港股全市場股票分析系統主程式。"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from config import FUTU_HOST, FUTU_PORT, MAX_WORKERS, REPORT_DIR
from futu_connector import FutuConnector
from report_generator import generate_report
from stock_scanner import StockScanner


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="港股全市場股票分析系統")
    parser.add_argument("--host", default=FUTU_HOST, help="Futu OpenD host")
    parser.add_argument("--port", default=FUTU_PORT, type=int, help="Futu OpenD port")
    parser.add_argument("--workers", default=MAX_WORKERS, type=int, help="多線程數量")
    parser.add_argument("--verbose", action="store_true", help="輸出詳細 log")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with FutuConnector(host=args.host, port=args.port) as connector:
            logger.info("已連接 Futu OpenD：%s:%s", args.host, args.port)
            scanner = StockScanner(connector=connector, max_workers=args.workers)
            results, stats = scanner.scan_market()
            report_path = generate_report(
                results,
                total_count=stats["total_count"],
                filtered_count=stats["filtered_count"],
            )
            logger.info("報告已生成：%s", report_path)
            print(f"報告已生成：{Path(report_path).resolve()}")
            return 0
    except KeyboardInterrupt:
        logger.warning("使用者中斷。已掃描進度會保存到 checkpoint，下次可續掃。")
        return 130
    except Exception as exc:  # noqa: BLE001
        logger.exception("執行失敗：%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

