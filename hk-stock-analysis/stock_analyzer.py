"""技術分析模組。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class AnalysisResult:
    code: str
    name: str
    current_price: float
    score: int
    signal: str
    trend: str
    rsi_status: str
    macd_signal: str
    volume_surge: bool
    boll_position: str
    indicators: dict[str, Any]


def analyze_stock(kline: pd.DataFrame, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """計算單隻股票技術指標與評分。"""
    if kline is None or len(kline) < 60:
        raise ValueError("K 線數據不足，至少需要 60 日")

    df = kline.copy()
    df = _normalize_kline_columns(df)

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)

    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    rsi = calc_rsi(close, 14)
    macd_line, signal_line, hist = calc_macd(close)
    boll_mid, boll_upper, boll_lower = calc_bollinger(close)
    avg_volume20 = volume.rolling(20).mean()

    latest_close = float(close.iloc[-1])
    latest_volume = float(volume.iloc[-1])
    latest = {
        "ma5": float(ma5.iloc[-1]),
        "ma10": float(ma10.iloc[-1]),
        "ma20": float(ma20.iloc[-1]),
        "ma60": float(ma60.iloc[-1]),
        "rsi": float(rsi.iloc[-1]),
        "macd": float(macd_line.iloc[-1]),
        "macd_signal_line": float(signal_line.iloc[-1]),
        "macd_hist": float(hist.iloc[-1]),
        "boll_mid": float(boll_mid.iloc[-1]),
        "boll_upper": float(boll_upper.iloc[-1]),
        "boll_lower": float(boll_lower.iloc[-1]),
        "avg_volume20": float(avg_volume20.iloc[-1]),
    }

    trend = judge_trend(latest_close, latest)
    rsi_status = judge_rsi(latest["rsi"])
    macd_signal = judge_macd(hist)
    volume_surge = latest_volume > latest["avg_volume20"] * 1.8 if latest["avg_volume20"] > 0 else False
    boll_position = judge_boll(latest_close, latest)
    score = calc_score(latest_close, latest, trend, rsi_status, macd_signal, volume_surge, boll_position)
    signal = score_to_signal(score)

    return {
        "trend": trend,
        "rsi_status": rsi_status,
        "macd_signal": macd_signal,
        "volume_surge": volume_surge,
        "boll_position": boll_position,
        "score": score,
        "signal": signal,
        "indicators": latest,
        "current_price": latest_close,
        "snapshot": snapshot or {},
    }


def _normalize_kline_columns(df: pd.DataFrame) -> pd.DataFrame:
    """兼容富途 K 線欄位命名。"""
    mapping = {
        "close_price": "close",
        "high_price": "high",
        "low_price": "low",
        "open_price": "open",
    }
    df = df.rename(columns={old: new for old, new in mapping.items() if old in df.columns})
    required = ["close", "high", "low", "volume"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"K 線缺少必要欄位：{missing}")
    return df


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def calc_bollinger(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    return mid, upper, lower


def judge_trend(price: float, latest: dict[str, float]) -> str:
    if price > latest["ma5"] > latest["ma10"] > latest["ma20"] > latest["ma60"]:
        return "上升"
    if price < latest["ma5"] < latest["ma10"] < latest["ma20"] < latest["ma60"]:
        return "下跌"
    return "盤整"


def judge_rsi(rsi: float) -> str:
    if rsi >= 70:
        return "超買"
    if rsi <= 30:
        return "超賣"
    return "中性"


def judge_macd(hist: pd.Series) -> str:
    if len(hist) < 2:
        return "無"
    prev = hist.iloc[-2]
    curr = hist.iloc[-1]
    if prev <= 0 < curr:
        return "金叉"
    if prev >= 0 > curr:
        return "死叉"
    return "無"


def judge_boll(price: float, latest: dict[str, float]) -> str:
    if price >= latest["boll_upper"]:
        return "上軌"
    if price <= latest["boll_lower"]:
        return "下軌"
    return "中軌"


def calc_score(
    price: float,
    latest: dict[str, float],
    trend: str,
    rsi_status: str,
    macd_signal: str,
    volume_surge: bool,
    boll_position: str,
) -> int:
    """按多個技術訊號加權評分。"""
    score = 50

    if trend == "上升":
        score += 22
    elif trend == "下跌":
        score -= 22

    if macd_signal == "金叉":
        score += 15
    elif macd_signal == "死叉":
        score -= 15

    if rsi_status == "超賣":
        score += 8
    elif rsi_status == "超買":
        score -= 8

    if volume_surge and trend == "上升":
        score += 10
    elif volume_surge and trend == "下跌":
        score -= 8

    if boll_position == "上軌" and trend == "上升":
        score += 7
    elif boll_position == "下軌":
        score += 4

    if price > latest["ma20"]:
        score += 5
    else:
        score -= 5

    return int(max(0, min(100, score)))


def score_to_signal(score: int) -> str:
    if score >= 85:
        return "強烈買入"
    if score >= 70:
        return "買入"
    if score >= 55:
        return "中性"
    if score >= 40:
        return "賣出"
    return "強烈賣出"

