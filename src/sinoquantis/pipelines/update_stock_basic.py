"""Update stock_basic from Tushare with AKShare fallback."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from sinoquantis.data_sources.akshare_client import AKShareClient
from sinoquantis.data_sources.tushare_client import TushareClient
from sinoquantis.db import connect, init_db, upsert_df

STOCK_BASIC_COLUMNS = [
    "ts_code",
    "symbol",
    "name",
    "area",
    "industry",
    "market",
    "list_date",
    "delist_date",
    "source",
    "ingest_time",
]


def update_stock_basic(db_path=None) -> int:
    """Update stock_basic, skipping failed sources without aborting the pipeline."""
    init_db(db_path)
    total = 0
    with connect(db_path) as con:
        for client in (TushareClient(), AKShareClient()):
            if not client.available:
                continue
            try:
                data = _normalize(client.stock_basic())
                if data.empty:
                    continue
                total += upsert_df(con, "stock_basic", data)
                logger.info("Upserted {} stock_basic rows from {}", len(data), client.source)
                if client.source == "tushare":
                    break
            except Exception as exc:
                logger.exception("{} stock_basic update failed: {}", client.source, exc)
    return total


def _normalize(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    for column in STOCK_BASIC_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[STOCK_BASIC_COLUMNS]
