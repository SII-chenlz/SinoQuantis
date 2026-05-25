"""Update adj_factor from Tushare."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from sinoquantis.data_sources.tushare_client import TushareClient
from sinoquantis.db import connect, init_db, upsert_df

COLUMNS = ["ts_code", "trade_date", "adj_factor", "source", "ingest_time"]


def update_adj_factor(start: str, end: str, db_path=None) -> int:
    """Update adjustment factors."""
    init_db(db_path)
    client = TushareClient()
    if not client.available:
        return 0
    try:
        data = _normalize(client.adj_factor(start, end))
        if data.empty:
            return 0
        with connect(db_path) as con:
            rows = upsert_df(con, "adj_factor", data)
        logger.info("Upserted {} adj_factor rows", rows)
        return rows
    except Exception as exc:
        logger.exception("adj_factor update failed: {}", exc)
        return 0


def _normalize(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    for column in COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[COLUMNS]
