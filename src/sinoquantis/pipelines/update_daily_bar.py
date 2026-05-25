"""Update daily_bar with Tushare first and AKShare symbol batching fallback."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from sinoquantis.data_sources.akshare_client import AKShareClient
from sinoquantis.data_sources.tushare_client import TushareClient
from sinoquantis.db import connect, fetch_df, init_db, upsert_df

COLUMNS = [
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
    "source",
    "ingest_time",
]


def update_daily_bar(start: str, end: str, db_path=None) -> int:
    """Update daily bars. AKShare fallback batches by symbol from stock_basic."""
    init_db(db_path)
    total = 0
    tushare = TushareClient()
    with connect(db_path) as con:
        if tushare.available:
            data = _normalize(tushare.daily_bar(start, end))
            if not data.empty:
                rows = upsert_df(con, "daily_bar", data)
                logger.info("Upserted {} daily_bar rows from Tushare", rows)
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
                data = _normalize(akshare.daily_bar(start, end, symbol))
                if data.empty:
                    continue
                total += upsert_df(con, "daily_bar", data)
                logger.info("Upserted {} daily_bar rows for {}", len(data), symbol)
            except Exception as exc:
                logger.exception("daily_bar update failed for {}: {}", symbol, exc)
    return total


def _normalize(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    for column in COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[COLUMNS]
