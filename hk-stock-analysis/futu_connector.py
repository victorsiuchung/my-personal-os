"""富途 OpenAPI 連接模組。

本模組集中封裝富途 API，方便主程式處理錯誤、限流和 mock 測試。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from typing import Any, Iterable

import pandas as pd

from config import FUTU_HOST, FUTU_PORT, RATE_LIMIT

try:
    from futu import (  # type: ignore
        RET_OK,
        AuType,
        KLType,
        Market,
        OpenQuoteContext,
        SecurityType,
        SimpleFilter,
        StockField,
    )
except ImportError:  # 讓沒有安裝 futu-api 時仍可 import 其他模組
    RET_OK = 0
    AuType = KLType = Market = SecurityType = SimpleFilter = StockField = None
    OpenQuoteContext = None


logger = logging.getLogger(__name__)


class FutuAPIError(RuntimeError):
    """富途 API 呼叫失敗。"""


class RateLimiter:
    """簡單 thread-safe 限流器，避免超過富途 API 請求頻率。"""

    def __init__(self, max_per_second: int) -> None:
        self.min_interval = 1.0 / max_per_second
        self._lock = Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_for = self.min_interval - (now - self._last_call)
            if wait_for > 0:
                time.sleep(wait_for)
            self._last_call = time.monotonic()


rate_limiter = RateLimiter(RATE_LIMIT)


def limited_call(func):
    """套用全域限流。"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        rate_limiter.wait()
        return func(*args, **kwargs)

    return wrapper


@dataclass
class FutuConnector:
    """富途行情連接器。"""

    host: str = FUTU_HOST
    port: int = FUTU_PORT

    def __post_init__(self) -> None:
        if OpenQuoteContext is None:
            raise ImportError("請先安裝 futu-api：pip install futu-api")
        self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)

    def close(self) -> None:
        """關閉富途連接。"""
        try:
            self.quote_ctx.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("關閉富途連接時出錯：%s", exc)

    def __enter__(self) -> "FutuConnector":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @limited_call
    def get_realtime_quote(self, symbol: str) -> pd.DataFrame:
        """獲取單隻股票實時報價。"""
        ret, data = self.quote_ctx.get_market_snapshot([symbol])
        return self._ensure_ok(ret, data, f"獲取實時報價失敗：{symbol}")

    @limited_call
    def get_market_snapshot(self, symbols: list[str]) -> pd.DataFrame:
        """批量獲取市場快照。富途官方文件表示每次最多 400 個標的。"""
        if not symbols:
            return pd.DataFrame()
        ret, data = self.quote_ctx.get_market_snapshot(symbols)
        return self._ensure_ok(ret, data, "批量獲取市場快照失敗")

    @limited_call
    def get_kline(self, symbol: str, ktype: Any = None, count: int = 200) -> pd.DataFrame:
        """獲取 K 線數據。

        注意：富途 get_cur_kline 通常需要先 subscribe 對應 K 線類型。
        若你的 OpenD 權限或訂閱不足，這裡會回傳錯誤並由上層跳過該股票。
        """
        if ktype is None:
            ktype = KLType.K_DAY
        ret, data = self.quote_ctx.get_cur_kline(symbol, count, ktype, AuType.QFQ)
        return self._ensure_ok(ret, data, f"獲取 K 線失敗：{symbol}")

    @limited_call
    def get_history_kline(
        self,
        symbol: str,
        start: str,
        end: str,
        ktype: Any = None,
        max_count: int = 1000,
    ) -> pd.DataFrame:
        """獲取歷史 K 線，用於回測。"""
        if ktype is None:
            ktype = KLType.K_DAY
        all_pages = []
        page_req_key = None

        while True:
            ret, data, page_req_key = self.quote_ctx.request_history_kline(
                code=symbol,
                start=start,
                end=end,
                ktype=ktype,
                autype=AuType.QFQ,
                max_count=max_count,
                page_req_key=page_req_key,
            )
            all_pages.append(self._ensure_ok(ret, data, f"獲取歷史 K 線失敗：{symbol}"))
            if page_req_key is None:
                break

        if not all_pages:
            return pd.DataFrame()
        return pd.concat(all_pages, ignore_index=True)

    @limited_call
    def get_all_stock_list(self, market: str = "HK") -> pd.DataFrame:
        """獲取全市場股票列表。

        只取普通股票，避免窩輪、牛熊證等衍生品。
        """
        futu_market = self._market_enum(market)
        ret, data = self.quote_ctx.get_stock_basicinfo(
            futu_market,
            SecurityType.STOCK,
        )
        return self._ensure_ok(ret, data, f"獲取全市場股票列表失敗：{market}")

    @limited_call
    def get_stock_filter(self, begin: int = 0) -> pd.DataFrame:
        """使用富途股票篩選器 API。

        這裡設定基礎條件，快速縮小分析範圍；若富途版本欄位名稱有差異，
        上層會 fallback 至全市場列表 + snapshot 批量過濾。
        """
        if SimpleFilter is None:
            raise FutuAPIError("futu-api 未安裝，無法使用股票篩選器")

        filters = []

        cur_price_filter = SimpleFilter()
        cur_price_filter.stock_field = StockField.CUR_PRICE
        cur_price_filter.filter_min = 1.0
        filters.append(cur_price_filter)

        market_val_filter = SimpleFilter()
        market_val_filter.stock_field = StockField.MARKET_VAL
        market_val_filter.filter_min = 10_0000_0000
        filters.append(market_val_filter)

        ret, data = self.quote_ctx.get_stock_filter(
            market=Market.HK,
            filter_list=filters,
            begin=begin,
        )
        return self._ensure_ok(ret, data, "富途股票篩選器失敗")

    def _market_enum(self, market: str) -> Any:
        if market.upper() == "HK":
            return Market.HK
        raise ValueError(f"暫只支援港股市場：{market}")

    def _ensure_ok(self, ret: int, data: Any, message: str) -> pd.DataFrame:
        if ret == RET_OK:
            return data
        raise FutuAPIError(f"{message}；富途回傳：{data}")


def chunked(items: Iterable[str], size: int) -> Iterable[list[str]]:
    """將列表切成固定大小批次。"""
    batch: list[str] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
