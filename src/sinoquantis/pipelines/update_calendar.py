"""Update trade_calendar from Tushare."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from sinoquantis.data_sources.tushare_client import TushareClient
from sinoquantis.db import connect, init_db, upsert_df

COLUMNS = ["exchange", "cal_date", "is_open", "pretrade_date", "source", "ingest_time"]


def update_calendar(start: str, end: str, db_path=None) -> int:
    """Update exchange trade calendar."""
    init_db(db_path)
    client = TushareClient()
    if not client.available:
        return 0
    try:
        data = _normalize(client.trade_calendar(start, end))
        if data.empty:
            return 0
        with connect(db_path) as con:
            rows = upsert_df(con, "trade_calendar", data)
        logger.info("Upserted {} trade_calendar rows", rows)
        return rows
    except Exception as exc:
        logger.exception("trade_calendar update failed: {}", exc)
        return 0


def _normalize(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    for column in COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[COLUMNS]
