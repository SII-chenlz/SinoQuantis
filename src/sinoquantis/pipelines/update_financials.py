"""Update financial_indicator while preserving announcement_date."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from sinoquantis.data_sources.akshare_client import AKShareClient
from sinoquantis.data_sources.tushare_client import TushareClient
from sinoquantis.db import connect, fetch_df, init_db, upsert_df

COLUMNS = [
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
    "source",
    "ingest_time",
]


def update_financials(start: str, end: str, db_path=None) -> int:
    """Update financial indicators and drop rows without disclosure dates."""
    init_db(db_path)
    total = 0
    tushare = TushareClient()
    with connect(db_path) as con:
        if tushare.available:
            data = _normalize(_drop_missing_announcement(tushare.financial_indicator(start, end)))
            if not data.empty:
                rows = upsert_df(con, "financial_indicator", data)
                logger.info("Upserted {} financial_indicator rows from Tushare", rows)
                return rows

        akshare = AKShareClient()
        if not akshare.available:
            return total
        symbols = fetch_df(
            con,
            "select symbol from stock_basic where symbol is not null order by symbol",
        )
        for symbol in symbols["symbol"].dropna().astype(str).tolist():
            try:
                data = _normalize(_drop_missing_announcement(akshare.financial_indicator(symbol)))
                if data.empty:
                    continue
                total += upsert_df(con, "financial_indicator", data)
                logger.info("Upserted {} financial_indicator rows for {}", len(data), symbol)
            except Exception as exc:
                logger.exception("financial_indicator update failed for {}: {}", symbol, exc)
    return total


def _drop_missing_announcement(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty or "announcement_date" not in data.columns:
        return pd.DataFrame()
    output = data.dropna(subset=["announcement_date"]).copy()
    dropped = len(data) - len(output)
    if dropped:
        logger.warning("Dropped {} financial rows without announcement_date", dropped)
    return output


def _normalize(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    for column in COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[COLUMNS]
