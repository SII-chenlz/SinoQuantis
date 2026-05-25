"""AKShare adapter isolated behind stable SinoQuantis methods."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class AKShareClient:
    """Wrapper around AKShare interfaces used as fallback research data."""

    source = "akshare"

    def __init__(self) -> None:
        try:
            import akshare as ak

            self._ak: Any | None = ak
        except Exception as exc:  # pragma: no cover - depends on optional package
            logger.exception("Failed to import AKShare: {}", exc)
            self._ak = None

    @property
    def available(self) -> bool:
        """Return whether AKShare is importable."""
        return self._ak is not None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def stock_basic(self) -> pd.DataFrame:
        """Fetch stock code/name list from AKShare."""
        if self._ak is None:
            return pd.DataFrame()
        try:
            data = self._ak.stock_info_a_code_name()
            if data.empty:
                return data
            data = data.rename(columns={"code": "symbol", "name": "name"})
            data["symbol"] = data["symbol"].astype(str).str.zfill(6)
            data["ts_code"] = data["symbol"].map(symbol_to_ts_code)
            for column in ["area", "industry", "market", "list_date", "delist_date"]:
                data[column] = pd.NA
            return _with_ingest(
                data[
                    [
                        "ts_code",
                        "symbol",
                        "name",
                        "area",
                        "industry",
                        "market",
                        "list_date",
                        "delist_date",
                    ]
                ],
                self.source,
            )
        except Exception as exc:
            logger.exception("AKShare stock_basic failed: {}", exc)
            return pd.DataFrame()

    def daily_bar(self, start: str, end: str, symbol: str) -> pd.DataFrame:
        """Fetch one symbol's daily bars."""
        if self._ak is None:
            return pd.DataFrame()
        try:
            data = self._ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="",
            )
            if data.empty:
                return data
            data = data.rename(
                columns={
                    "日期": "trade_date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "vol",
                    "成交额": "amount",
                    "涨跌额": "change",
                    "涨跌幅": "pct_chg",
                }
            )
            data["symbol"] = str(symbol).zfill(6)
            data["ts_code"] = data["symbol"].map(symbol_to_ts_code)
            data["pre_close"] = data.groupby("ts_code")["close"].shift(1)
            data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce").dt.date
            return _with_ingest(_ensure_columns(data, _daily_columns()), self.source)
        except Exception as exc:
            logger.exception("AKShare daily_bar failed for {}: {}", symbol, exc)
            return pd.DataFrame()

    def financial_indicator(self, symbol: str) -> pd.DataFrame:
        """Fetch one symbol's financial indicators when AKShare exposes them."""
        if self._ak is None:
            return pd.DataFrame()
        try:
            data = self._ak.stock_financial_analysis_indicator(symbol=symbol)
            if data.empty:
                return data
            data = data.rename(
                columns={
                    "日期": "fiscal_period",
                    "摊薄每股收益(元)": "eps",
                    "净资产收益率(%)": "roe",
                    "总资产净利润率(%)": "roa",
                    "销售毛利率(%)": "gross_margin",
                    "销售净利率(%)": "netprofit_margin",
                    "资产负债率(%)": "debt_to_asset",
                    "流动比率": "current_ratio",
                }
            )
            data["ts_code"] = symbol_to_ts_code(str(symbol).zfill(6))
            data["fiscal_period"] = pd.to_datetime(data["fiscal_period"], errors="coerce").dt.date
            data["announcement_date"] = pd.NA
            return _with_ingest(_ensure_columns(data, _financial_columns()), self.source)
        except Exception as exc:
            logger.exception("AKShare financial_indicator failed for {}: {}", symbol, exc)
            return pd.DataFrame()


def symbol_to_ts_code(symbol: str) -> str:
    """Convert six-digit A-share symbol to Tushare-style ts_code."""
    clean = str(symbol).zfill(6)
    suffix = "SH" if clean.startswith(("6", "9")) else "SZ"
    return f"{clean}.{suffix}"


def _with_ingest(data: pd.DataFrame, source: str) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    output["source"] = source
    output["ingest_time"] = datetime.now(timezone.utc)
    return output


def _ensure_columns(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = data.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output[columns]


def _daily_columns() -> list[str]:
    return [
        "ts_code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "change",
        "pct_chg",
        "vol",
        "amount",
    ]


def _financial_columns() -> list[str]:
    return [
        "ts_code",
        "fiscal_period",
        "announcement_date",
        "eps",
        "roe",
        "roa",
        "gross_margin",
        "netprofit_margin",
        "debt_to_asset",
        "current_ratio",
    ]
