"""全市場掃描模組。

掃描流程優先順序：
1. 嘗試使用富途股票篩選器 API
2. fallback 至全市場股票列表 + market snapshot 批量過濾
3. 逐隻拉 K 線分析，並支援 checkpoint 續掃
"""

from __future__ import annotations

import logging
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from time import time
from typing import Any

import pandas as pd
from tqdm import tqdm

from config import (
    CACHE_DIR,
    CHECKPOINT_FILE,
    HSI_CONSTITUENTS,
    KLINE_CACHE_SECONDS,
    KLINE_COUNT,
    MARKET,
    MAX_WORKERS,
    MIN_AVG_VOLUME_20D,
    SCAN_RESUME,
    SNAPSHOT_BATCH_SIZE,
)
from futu_connector import FutuAPIError, FutuConnector, chunked
from screener import apply_snapshot_filters, filter_kline_liquidity
from stock_analyzer import analyze_stock
from trade_plan import build_trade_plan


logger = logging.getLogger(__name__)


@dataclass
class KlineCache:
    """5 分鐘 K 線快取，避免同一輪掃描重複請求。"""

    ttl_seconds: int = KLINE_CACHE_SECONDS
    data: dict[str, tuple[float, pd.DataFrame]] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)

    def get(self, symbol: str) -> pd.DataFrame | None:
        with self.lock:
            item = self.data.get(symbol)
            if not item:
                return None
            created_at, df = item
            if time() - created_at > self.ttl_seconds:
                self.data.pop(symbol, None)
                return None
            return df.copy()

    def set(self, symbol: str, df: pd.DataFrame) -> None:
        with self.lock:
            self.data[symbol] = (time(), df.copy())


@dataclass
class StockScanner:
    """港股全市場掃描器。"""

    connector: FutuConnector
    max_workers: int = MAX_WORKERS
    checkpoint_file: Path = CHECKPOINT_FILE
    kline_cache: KlineCache = field(default_factory=KlineCache)

    def scan_market(self) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """執行完整市場掃描。"""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        stock_list = self.load_candidate_stocks()
        total_count = len(stock_list)
        filtered_df = self.apply_fast_filters(stock_list)
        filtered_count = len(filtered_df)

        results = self.scan_candidates(filtered_df)
        stats = {
            "total_count": total_count,
            "filtered_count": filtered_count,
            "analyzed_count": len(results),
        }
        return results, stats

    def scan_hsi(self) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """只掃描恆生指數成份股，適合較快產生高流動性股票推介。"""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        stock_list = pd.DataFrame({"code": HSI_CONSTITUENTS})
        filtered_df = self.apply_fast_filters(stock_list)
        results = self.scan_candidates(filtered_df)
        stats = {
            "total_count": len(stock_list),
            "filtered_count": len(filtered_df),
            "analyzed_count": len(results),
        }
        return results, stats

    def load_candidate_stocks(self) -> pd.DataFrame:
        """載入候選股票，優先使用股票篩選器。"""
        try:
            logger.info("嘗試使用富途股票篩選器 API...")
            filtered = self.connector.get_stock_filter(begin=0)
            if not filtered.empty:
                normalized = normalize_stock_list(filtered)
                logger.info("股票篩選器取得 %s 隻候選股票", len(normalized))
                return normalized
        except Exception as exc:  # noqa: BLE001
            logger.warning("股票篩選器不可用，改用全市場列表：%s", exc)

        logger.info("獲取港股全市場股票列表...")
        all_stocks = self.connector.get_all_stock_list(MARKET)
        normalized = normalize_stock_list(all_stocks)
        logger.info("全市場股票列表共 %s 隻", len(normalized))
        return normalized

    def apply_fast_filters(self, stocks: pd.DataFrame) -> pd.DataFrame:
        """使用 market snapshot 批量快速過濾市值、成交額、股價。"""
        codes = stocks["code"].dropna().astype(str).tolist()
        snapshots: list[pd.DataFrame] = []

        for batch in tqdm(list(chunked(codes, SNAPSHOT_BATCH_SIZE)), desc="批量獲取市場快照"):
            try:
                snap = self.connector.get_market_snapshot(batch)
                snapshots.append(snap)
            except Exception as exc:  # noqa: BLE001
                logger.warning("快照批次失敗，跳過 %s 隻：%s", len(batch), exc)

        if not snapshots:
            logger.warning("無法取得快照，將直接分析候選股票列表")
            return stocks

        snapshot_df = pd.concat(snapshots, ignore_index=True)
        filtered = apply_snapshot_filters(snapshot_df)
        logger.info("快照篩選後剩餘 %s 隻", len(filtered))
        return filtered

    def scan_candidates(self, candidates: pd.DataFrame) -> list[dict[str, Any]]:
        """多線程逐隻分析股票，支援中斷後續掃。"""
        checkpoint = self.load_checkpoint() if SCAN_RESUME else {"done": set(), "results": []}
        done: set[str] = set(checkpoint.get("done", set()))
        results: list[dict[str, Any]] = list(checkpoint.get("results", []))

        candidate_records = [
            row.to_dict()
            for _, row in candidates.iterrows()
            if str(row.get("code")) not in done
        ]

        if done:
            logger.info("偵測到 checkpoint，已完成 %s 隻，待掃描 %s 隻", len(done), len(candidate_records))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.analyze_one, record): record
                for record in candidate_records
            }
            with tqdm(total=len(futures), desc="逐隻技術分析") as progress:
                for future in as_completed(futures):
                    record = futures[future]
                    code = str(record.get("code"))
                    try:
                        item = future.result()
                        if item:
                            results.append(item)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("%s 分析失敗，繼續下一隻：%s", code, exc)
                    finally:
                        done.add(code)
                        self.save_checkpoint(done, results)
                        progress.update(1)

        self.clear_checkpoint()
        return results

    def analyze_one(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """分析單隻股票。"""
        code = str(record.get("code"))
        name = str(record.get("name", ""))
        kline = self.get_cached_kline(code)

        if not filter_kline_liquidity(kline, MIN_AVG_VOLUME_20D):
            return None

        analysis = analyze_stock(kline, snapshot=record)
        trade_plan = build_trade_plan(kline, float(record.get("last_price") or analysis["current_price"]))
        return {
            "code": code,
            "name": name,
            "current_price": float(record.get("last_price") or analysis["current_price"]),
            "score": analysis["score"],
            "signal": analysis["signal"],
            "trend": analysis["trend"],
            "rsi_status": analysis["rsi_status"],
            "macd_signal": analysis["macd_signal"],
            "volume_surge": analysis["volume_surge"],
            "boll_position": analysis["boll_position"],
            "trade_plan": trade_plan,
            "indicators": analysis["indicators"],
            "market_cap": record.get("total_market_val"),
            "turnover": record.get("turnover"),
        }

    def get_cached_kline(self, code: str) -> pd.DataFrame:
        cached = self.kline_cache.get(code)
        if cached is not None:
            return cached
        kline = self.connector.get_kline(code, count=KLINE_COUNT)
        self.kline_cache.set(code, kline)
        return kline

    def load_checkpoint(self) -> dict[str, Any]:
        if not self.checkpoint_file.exists():
            return {"done": set(), "results": []}
        try:
            with self.checkpoint_file.open("rb") as handle:
                return pickle.load(handle)
        except Exception as exc:  # noqa: BLE001
            logger.warning("讀取 checkpoint 失敗，重新開始：%s", exc)
            return {"done": set(), "results": []}

    def save_checkpoint(self, done: set[str], results: list[dict[str, Any]]) -> None:
        payload = {
            "updated_at": datetime.now().isoformat(),
            "done": done,
            "results": results,
        }
        with self.checkpoint_file.open("wb") as handle:
            pickle.dump(payload, handle)

    def clear_checkpoint(self) -> None:
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()


def normalize_stock_list(df: pd.DataFrame) -> pd.DataFrame:
    """整理富途不同 API 回傳欄位。"""
    if df.empty:
        return pd.DataFrame(columns=["code", "name"])
    result = df.copy()

    if "stock_child_type" in result.columns:
        # 避免窩輪、牛熊證等非普通股票；不同版本欄位值可能不同，所以只做保守排除。
        bad_keywords = ["WARRANT", "BULL", "BEAR", "INLINE"]
        result = result[
            ~result["stock_child_type"].astype(str).str.upper().str.contains("|".join(bad_keywords), na=False)
        ]

    result = result.drop_duplicates(subset=["code"])
    result = result[result["code"].astype(str).str.startswith("HK.")]
    return result.reset_index(drop=True)
