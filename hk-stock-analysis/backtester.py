"""HSI 成份股一年回測模組。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from config import BASE_DIR, FUTU_HOST, FUTU_PORT, HSI_CONSTITUENTS
from futu_connector import FutuConnector
from stock_analyzer import analyze_stock
from trade_plan import build_trade_plan


BACKTEST_DIR = BASE_DIR / "reports" / "backtests"


@dataclass
class BacktestConfig:
    lookback_days: int = 200
    horizon_short: int = 20
    horizon_long: int = 60
    min_score_to_buy: int = 70
    strong_score: int = 85
    start: str = ""
    end: str = ""


def run_hsi_backtest(connector: FutuConnector, config: BacktestConfig) -> dict[str, Any]:
    """對 HSI 成份股做一年 walk-forward 回測。"""
    end_date = datetime.strptime(config.end, "%Y-%m-%d").date() if config.end else date.today()
    start_date = datetime.strptime(config.start, "%Y-%m-%d").date() if config.start else end_date - timedelta(days=365)
    fetch_start = start_date - timedelta(days=config.lookback_days + 20)

    trades: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for symbol in tqdm(HSI_CONSTITUENTS, desc="HSI 一年回測"):
        try:
            kline = connector.get_history_kline(symbol, fetch_start.isoformat(), end_date.isoformat())
            trades.extend(backtest_one_symbol(symbol, kline, start_date, end_date, config))
        except Exception as exc:  # noqa: BLE001
            failures.append({"code": symbol, "error": str(exc)})

    metrics = summarize_trades(trades, config)
    return {
        "generated_at": datetime.now().isoformat(),
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "config": config.__dict__,
        "metrics": metrics,
        "trades": trades,
        "failures": failures,
    }


def backtest_one_symbol(
    symbol: str,
    kline: pd.DataFrame,
    start_date: date,
    end_date: date,
    config: BacktestConfig,
) -> list[dict[str, Any]]:
    """單一股票 walk-forward 回測。"""
    df = normalize_kline(kline)
    if len(df) < config.lookback_days + config.horizon_long:
        return []

    trades: list[dict[str, Any]] = []
    dates = pd.to_datetime(df["time_key"]).dt.date

    for idx in range(config.lookback_days, len(df) - config.horizon_long):
        current_date = dates.iloc[idx]
        if current_date < start_date or current_date > end_date:
            continue

        window = df.iloc[idx - config.lookback_days : idx + 1].copy()
        analysis = analyze_stock(window)
        score = analysis["score"]
        if score < config.min_score_to_buy:
            continue

        current_price = float(window["close"].iloc[-1])
        plan = build_trade_plan(window, current_price)
        future_short = df.iloc[idx + config.horizon_short]["close"]
        future_long = df.iloc[idx + config.horizon_long]["close"]
        future_path = df.iloc[idx + 1 : idx + config.horizon_long + 1]

        stop_hit = bool((future_path["low"] <= plan["stop_loss"]).any())
        tp1_hit = bool((future_path["high"] >= plan["take_profit_1"]).any())
        tp2_hit = bool((future_path["high"] >= plan["take_profit_2"]).any())

        trades.append(
            {
                "code": symbol,
                "date": current_date.isoformat(),
                "entry": plan["buy_price"],
                "current_price": current_price,
                "stop_loss": plan["stop_loss"],
                "take_profit_1": plan["take_profit_1"],
                "take_profit_2": plan["take_profit_2"],
                "score": score,
                "signal": analysis["signal"],
                "trend": analysis["trend"],
                "rsi_status": analysis["rsi_status"],
                "macd_signal": analysis["macd_signal"],
                "volume_surge": analysis["volume_surge"],
                "return_20d": pct_return(current_price, float(future_short)),
                "return_60d": pct_return(current_price, float(future_long)),
                "stop_hit_60d": stop_hit,
                "tp1_hit_60d": tp1_hit,
                "tp2_hit_60d": tp2_hit,
            }
        )

    return trades


def summarize_trades(trades: list[dict[str, Any]], config: BacktestConfig) -> dict[str, Any]:
    if not trades:
        return {
            "trade_count": 0,
            "win_rate_20d": 0,
            "win_rate_60d": 0,
            "avg_return_20d": 0,
            "avg_return_60d": 0,
            "tp1_hit_rate": 0,
            "tp2_hit_rate": 0,
            "stop_hit_rate": 0,
        }

    df = pd.DataFrame(trades)
    return {
        "trade_count": int(len(df)),
        "strong_trade_count": int((df["score"] >= config.strong_score).sum()),
        "win_rate_20d": round(float((df["return_20d"] > 0).mean() * 100), 2),
        "win_rate_60d": round(float((df["return_60d"] > 0).mean() * 100), 2),
        "avg_return_20d": round(float(df["return_20d"].mean()), 2),
        "avg_return_60d": round(float(df["return_60d"].mean()), 2),
        "median_return_60d": round(float(df["return_60d"].median()), 2),
        "tp1_hit_rate": round(float(df["tp1_hit_60d"].mean() * 100), 2),
        "tp2_hit_rate": round(float(df["tp2_hit_60d"].mean() * 100), 2),
        "stop_hit_rate": round(float(df["stop_hit_60d"].mean() * 100), 2),
        "best_trades": df.sort_values("return_60d", ascending=False).head(10).to_dict("records"),
        "worst_trades": df.sort_values("return_60d", ascending=True).head(10).to_dict("records"),
    }


def write_backtest_report(result: dict[str, Any]) -> Path:
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKTEST_DIR / f"hsi_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    metrics = result["metrics"]

    lines = [
        "# HSI 93 成份股一年技術模型回測報告",
        "",
        f"- 生成時間：{result['generated_at']}",
        f"- 回測區間：{result['period']['start']} 至 {result['period']['end']}",
        f"- 交易訊號數量：{metrics.get('trade_count', 0)}",
        f"- 20 日勝率：{metrics.get('win_rate_20d', 0)}%",
        f"- 60 日勝率：{metrics.get('win_rate_60d', 0)}%",
        f"- 20 日平均回報：{metrics.get('avg_return_20d', 0)}%",
        f"- 60 日平均回報：{metrics.get('avg_return_60d', 0)}%",
        f"- 止賺一階命中率：{metrics.get('tp1_hit_rate', 0)}%",
        f"- 止賺二階命中率：{metrics.get('tp2_hit_rate', 0)}%",
        f"- 止蝕命中率：{metrics.get('stop_hit_rate', 0)}%",
        "",
        "## 初步判斷",
        backtest_judgement(metrics),
        "",
        "## 改善方向",
        "- 加入大市 regime filter：恆指本身在 MA20/MA60 上方才接受買入訊號。",
        "- 加入相對強弱：只買入跑贏 HSI 的成份股。",
        "- 加入 ATR 風險調整倉位，避免高波動股票拖累。",
        "- 加入成交額排名或南向資金/行業強弱作二次排序。",
        "- 參考 TA-Lib / pandas-ta / vectorbt / backtrader 做更嚴謹策略驗證。",
        "",
        "## 風險提示",
        "本回測存在幸存者偏差，因為使用的是現時 HSI 成份股回看過去一年，而不是一年前的成份股清單。結果只作模型研究，不構成投資建議。",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def backtest_judgement(metrics: dict[str, Any]) -> str:
    win60 = metrics.get("win_rate_60d", 0)
    avg60 = metrics.get("avg_return_60d", 0)
    stop = metrics.get("stop_hit_rate", 0)
    if win60 >= 55 and avg60 > 2 and stop < 35:
        return "模型一年回測初步合格，可以進一步做參數優化和 out-of-sample 測試。"
    return "模型未算穩定，建議加入大市 regime、相對強弱、波動率和成交額過濾後再測。"


def normalize_kline(kline: pd.DataFrame) -> pd.DataFrame:
    df = kline.rename(columns={"close_price": "close", "high_price": "high", "low_price": "low", "open_price": "open"}).copy()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["time_key", "open", "high", "low", "close", "volume"])
    return df.sort_values("time_key").reset_index(drop=True)


def pct_return(entry: float, exit_price: float) -> float:
    return round((exit_price - entry) / entry * 100, 2) if entry else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HSI 93 constituents one-year backtest")
    parser.add_argument("--host", default=FUTU_HOST)
    parser.add_argument("--port", default=FUTU_PORT, type=int)
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    parser.add_argument("--json", action="store_true", help="Also write JSON result")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = parse_args()
    config = BacktestConfig(start=args.start, end=args.end)
    try:
        with FutuConnector(host=args.host, port=args.port) as connector:
            result = run_hsi_backtest(connector, config)
        report_path = write_backtest_report(result)
        print(f"Backtest report generated: {report_path}")
        if args.json:
            json_path = report_path.with_suffix(".json")
            json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Backtest JSON generated: {json_path}")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        logging.exception("Backtest failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

