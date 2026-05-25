"""DuckDB helpers for SinoQuantis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from loguru import logger

from sinoquantis.config import get_settings

TABLE_KEYS: dict[str, list[str]] = {
    "stock_basic": ["ts_code"],
    "trade_calendar": ["exchange", "cal_date"],
    "daily_bar": ["ts_code", "trade_date", "source"],
    "adj_factor": ["ts_code", "trade_date", "source"],
    "financial_indicator": ["ts_code", "fiscal_period", "announcement_date", "source"],
    "financial_statement_long": [
        "ts_code",
        "statement_type",
        "fiscal_period",
        "announcement_date",
        "account_code",
        "source",
        "version",
    ],
    "filing_index": ["source_doc_id"],
    "filing_text": ["source_doc_id", "parser_version"],
    "llm_analysis": ["analysis_id"],
    "factor_value": ["ts_code", "trade_date", "factor_name"],
}


def get_db_path() -> Path:
    """Return the configured DuckDB path."""
    settings = get_settings()
    return settings.sinoquantis_db_path


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection, ensuring the parent directory exists."""
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Opening DuckDB database at {}", path)
    return duckdb.connect(str(path))


def init_db(db_path: Path | None = None) -> None:
    """Initialize database schema."""
    schema_path = Path(__file__).parent / "storage" / "schema.sql"
    with connect(db_path) as con:
        con.execute(schema_path.read_text(encoding="utf-8"))
    logger.info("Initialized database schema at {}", db_path or get_db_path())


def table_exists(table_name: str, db_path: Path | None = None) -> bool:
    """Check whether a table exists in the configured DuckDB database."""
    with connect(db_path) as con:
        result = con.execute(
            "select count(*) from information_schema.tables where table_name = ?",
            [table_name],
        ).fetchone()
    return bool(result and result[0] > 0)


def fetch_df(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[Any] | None = None,
) -> pd.DataFrame:
    """Execute SQL and return a pandas DataFrame."""
    return con.execute(sql, params or []).fetchdf()


def upsert_df(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    data: pd.DataFrame,
    key_columns: list[str] | None = None,
) -> int:
    """Delete matching keys then insert rows to keep pipeline writes idempotent."""
    if data.empty:
        return 0
    keys = key_columns or TABLE_KEYS[table_name]
    missing = sorted(set(keys) - set(data.columns))
    if missing:
        raise ValueError(f"{table_name} upsert missing key columns: {', '.join(missing)}")

    temp_name = f"_tmp_{table_name}"
    con.register(temp_name, data)
    conditions = " and ".join(
        f"{table_name}.{column} is not distinct from {temp_name}.{column}" for column in keys
    )
    con.execute(f"delete from {table_name} using {temp_name} where {conditions}")
    con.execute(f"insert into {table_name} by name select * from {temp_name}")
    con.unregister(temp_name)
    return int(len(data))
