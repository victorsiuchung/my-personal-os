"""交易計劃計算模組。

根據 K 線技術位估算買入價、止蝕價、第一/第二止賺價。
這些價位只作風險管理參考，不構成投資建議。
"""

from __future__ import annotations

import pandas as pd


def build_trade_plan(kline: pd.DataFrame, current_price: float) -> dict[str, float]:
    """用近期支撐/波幅估算交易計劃。"""
    df = kline.copy()
    df = df.rename(
        columns={
            "close_price": "close",
            "high_price": "high",
            "low_price": "low",
        }
    )

    close = pd.to_numeric(df["close"], errors="coerce")
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")

    ma20 = close.rolling(20).mean().iloc[-1]
    support20 = low.tail(20).min()
    resistance20 = high.tail(20).max()
    atr14 = calc_atr(high, low, close, 14).iloc[-1]

    buy_price = float(current_price)
    stop_loss = min(float(ma20) * 0.985, float(support20) * 0.985)
    risk = max(buy_price - stop_loss, buy_price * 0.03, float(atr14))

    take_profit_1 = max(buy_price + risk * 1.5, float(resistance20))
    take_profit_2 = buy_price + risk * 2.5

    return {
        "buy_price": round(buy_price, 3),
        "stop_loss": round(max(stop_loss, 0.01), 3),
        "take_profit_1": round(take_profit_1, 3),
        "take_profit_2": round(take_profit_2, 3),
        "risk_percent": round((buy_price - stop_loss) / buy_price * 100, 2) if buy_price > 0 else 0,
        "reward_1_percent": round((take_profit_1 - buy_price) / buy_price * 100, 2) if buy_price > 0 else 0,
        "reward_2_percent": round((take_profit_2 - buy_price) / buy_price * 100, 2) if buy_price > 0 else 0,
    }


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """計算 ATR。"""
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(period).mean()

