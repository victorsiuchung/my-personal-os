"""股票篩選器。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from config import MIN_DAYS_LISTED, MIN_MARKET_CAP, MIN_PRICE, MIN_TURNOVER


def apply_snapshot_filters(snapshot_df: pd.DataFrame) -> pd.DataFrame:
    """根據市值、成交額、股價、上市時間等條件過濾股票。"""
    if snapshot_df.empty:
        return snapshot_df

    df = snapshot_df.copy()
    df["last_price"] = pd.to_numeric(df.get("last_price"), errors="coerce")
    df["turnover"] = pd.to_numeric(df.get("turnover"), errors="coerce")
    df["total_market_val"] = pd.to_numeric(df.get("total_market_val"), errors="coerce")
    df["days_listed"] = df.get("listing_date", "").apply(days_since_listing)

    mask = (
        (df["last_price"] >= MIN_PRICE)
        & (df["turnover"] >= MIN_TURNOVER)
        & (df["total_market_val"] >= MIN_MARKET_CAP)
        & (df["days_listed"] >= MIN_DAYS_LISTED)
    )

    if "suspension" in df.columns:
        mask &= ~df["suspension"].fillna(False)

    if "equity_valid" in df.columns:
        mask &= df["equity_valid"].fillna(True)

    return df[mask].reset_index(drop=True)


def days_since_listing(value: Any) -> int:
    """計算上市天數；資料缺失時保守回傳 0。"""
    if not value or pd.isna(value):
        return 0
    try:
        listing_date = datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return 0
    return (datetime.now() - listing_date).days


def filter_kline_liquidity(kline: pd.DataFrame, min_avg_volume: float) -> bool:
    """檢查過去 20 日平均成交量。"""
    if kline is None or len(kline) < 20 or "volume" not in kline.columns:
        return False
    avg_volume = pd.to_numeric(kline["volume"], errors="coerce").tail(20).mean()
    return bool(avg_volume >= min_avg_volume)

