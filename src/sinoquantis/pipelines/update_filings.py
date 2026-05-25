"""Update filing_index from announcement sources."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from sinoquantis.data_sources.cninfo_client import CninfoClient
from sinoquantis.db import connect, init_db, upsert_df

COLUMNS = [
    "source_doc_id",
    "ts_code",
    "company_name",
    "title",
    "filing_type",
    "report_period",
    "announcement_date",
    "url",
    "local_path",
    "source",
    "ingest_time",
    "file_hash",
]


def update_filings(start: str, end: str, db_path=None, page_size: int = 30) -> int:
    """Update first-stage filing index rows without parsing PDFs."""
    init_db(db_path)
    client = CninfoClient()
    total = 0
    page = 1
    with connect(db_path) as con:
        while True:
            try:
                data = _normalize(client.query_filings(start, end, page=page, page_size=page_size))
            except Exception as exc:
                logger.exception("filing_index update failed on page {}: {}", page, exc)
                break
            if data.empty:
                break
            total += upsert_df(con, "filing_index", data)
            logger.info("Upserted {} filing_index rows from page {}", len(data), page)
            if len(data) < page_size:
                break
            page += 1
    return total


def _normalize(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    output = data.copy()
    for column in COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[COLUMNS]
