"""Database tests."""

from pathlib import Path

from sinoquantis.db import init_db, table_exists


def test_init_db_creates_expected_tables(tmp_path: Path) -> None:
    """init_db should create all core tables."""
    db_path = tmp_path / "quant.duckdb"
    init_db(db_path)

    expected_tables = [
        "stock_basic",
        "trade_calendar",
        "daily_bar",
        "adj_factor",
        "financial_indicator",
        "financial_statement_long",
        "filing_index",
        "filing_text",
        "llm_analysis",
        "factor_value",
        "backtest_result",
    ]

    for table in expected_tables:
        assert table_exists(table, db_path)
