"""Tushare Pro adapter for A-share research data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from sinoquantis.config import get_settings


class TushareClient:
    """Small Tushare Pro wrapper with graceful missing-token behavior."""

    source = "tushare"

    def __init__(self, token: str | None = None) -> None:
        self.token = token or get_settings().tushare_token
        self._pro: Any | None = None
        if not self.token:
            logger.warning("TUSHARE_TOKEN is missing; skipping Tushare data source.")
            return
        try:
            import tushare as ts

            ts.set_token(self.token)
            self._pro = ts.pro_api()
        except Exception as exc:  # pragma: no cover - depends on optional package
            logger.exception("Failed to initialize Tushare client: {}", exc)

    @property
    def available(self) -> bool:
        """Return whether Tushare can be called."""
        return self._pro is not None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _call(self, api_name: str, **kwargs: Any) -> pd.DataFrame:
        if self._pro is None:
            return pd.DataFrame()
        return getattr(self._pro, api_name)(**kwargs)

    def stock_basic(self) -> pd.DataFrame:
        """Fetch listed and delisted stock basic records."""
        frames: list[pd.DataFrame] = []
        for status in ("L", "D"):
            try:
                frame = self._call(
                    "stock_basic",
                    exchange="",
                    list_status=status,
                    fields="ts_code,symbol,name,area,industry,market,list_date,delist_date",
                )
                if not frame.empty:
                    frames.append(frame)
            except Exception as exc:
                logger.exception("Tushare stock_basic({}) failed: {}", status, exc)
        data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return _with_ingest(_date_columns(data, ["list_date", "delist_date"]), self.source)

    def trade_calendar(self, start: str, end: str, exchange: str = "SSE") -> pd.DataFrame:
        """Fetch exchange trade calendar."""
        try:
            data = self._call("trade_cal", exchange=exchange, start_date=start, end_date=end)
            if data.empty:
                return data
            data["is_open"] = data["is_open"].astype(bool)
            return _with_ingest(_date_columns(data, ["cal_date", "pretrade_date"]), self.source)
        except Exception as exc:
            logger.exception("Tushare trade_calendar failed: {}", exc)
            return pd.DataFrame()

    def daily_bar(self, start: str, end: str, ts_code: str | None = None) -> pd.DataFrame:
        """Fetch daily OHLCV bars."""
        try:
            data = self._call("daily", ts_code=ts_code or "", start_date=start, end_date=end)
            return _with_ingest(_date_columns(data, ["trade_date"]), self.source)
        except Exception as exc:
            logger.exception("Tushare daily_bar failed for {}: {}", ts_code or "all", exc)
            return pd.DataFrame()

    def adj_factor(self, start: str, end: str, ts_code: str | None = None) -> pd.DataFrame:
        """Fetch adjustment factors."""
        try:
            data = self._call("adj_factor", ts_code=ts_code or "", start_date=start, end_date=end)
            return _with_ingest(_date_columns(data, ["trade_date"]), self.source)
        except Exception as exc:
            logger.exception("Tushare adj_factor failed for {}: {}", ts_code or "all", exc)
            return pd.DataFrame()

    def financial_indicator(self, start: str, end: str, ts_code: str | None = None) -> pd.DataFrame:
        """Fetch financial indicators with disclosure dates preserved."""
        try:
            data = self._call(
                "fina_indicator",
                ts_code=ts_code or "",
                start_date=start,
                end_date=end,
            )
            if data.empty:
                return data
            data = data.rename(
                columns={
                    "ann_date": "announcement_date",
                    "end_date": "fiscal_period",
                    "grossprofit_margin": "gross_margin",
                    "debt_to_assets": "debt_to_asset",
                }
            )
            data = _ensure_columns(
                data,
                [
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
                ],
            )
            data = _date_columns(data, ["fiscal_period", "announcement_date"])
            return _with_ingest(data, self.source)
        except Exception as exc:
            logger.exception("Tushare financial_indicator failed for {}: {}", ts_code or "all", exc)
            return pd.DataFrame()


def _with_ingest(data: pd.DataFrame, source: str) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    output["source"] = source
    output["ingest_time"] = datetime.now(timezone.utc)
    return output


def _date_columns(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    for column in columns:
        if column in output.columns:
            output[column] = pd.to_datetime(
                output[column],
                format="%Y%m%d",
                errors="coerce",
            ).dt.date
    return output


def _ensure_columns(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = data.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output[columns]
