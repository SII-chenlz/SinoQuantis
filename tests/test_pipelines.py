"""Pipeline tests with mocked external data sources."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from sinoquantis.db import connect, fetch_df, init_db, upsert_df
from sinoquantis.pipelines import (
    update_calendar,
    update_daily_bar,
    update_financials,
    update_stock_basic,
)


class MockTushareMissing:
    source = "tushare"
    available = False


class MockStockAKShare:
    source = "akshare"
    available = True

    def stock_basic(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "平安银行",
                    "area": None,
                    "industry": None,
                    "market": None,
                    "list_date": None,
                    "delist_date": None,
                    "source": "akshare",
                    "ingest_time": datetime.now(timezone.utc),
                }
            ]
        )


def test_update_stock_basic_uses_akshare_when_tushare_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(update_stock_basic, "TushareClient", MockTushareMissing)
    monkeypatch.setattr(update_stock_basic, "AKShareClient", MockStockAKShare)

    db_path = tmp_path / "quant.duckdb"
    rows = update_stock_basic.update_stock_basic(db_path)
    rows_again = update_stock_basic.update_stock_basic(db_path)

    with connect(db_path) as con:
        stored = fetch_df(con, "select * from stock_basic")

    assert rows == 1
    assert rows_again == 1
    assert len(stored) == 1
    assert stored.loc[0, "ts_code"] == "000001.SZ"


class MockCalendarTushare:
    source = "tushare"
    available = True

    def trade_calendar(self, start: str, end: str) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "exchange": "SSE",
                    "cal_date": date(2020, 1, 2),
                    "is_open": True,
                    "pretrade_date": date(2019, 12, 31),
                    "source": "tushare",
                    "ingest_time": datetime.now(timezone.utc),
                }
            ]
        )


def test_update_calendar_upserts_mocked_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(update_calendar, "TushareClient", MockCalendarTushare)
    db_path = tmp_path / "quant.duckdb"

    assert update_calendar.update_calendar("20200101", "20200131", db_path) == 1
    assert update_calendar.update_calendar("20200101", "20200131", db_path) == 1

    with connect(db_path) as con:
        stored = fetch_df(con, "select * from trade_calendar")
    assert len(stored) == 1


class MockDailyTushareMissing:
    source = "tushare"
    available = False


class MockDailyAKShare:
    source = "akshare"
    available = True

    def daily_bar(self, start: str, end: str, symbol: str) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": date(2020, 1, 2),
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.5,
                    "close": 10.5,
                    "pre_close": 10.0,
                    "change": 0.5,
                    "pct_chg": 5.0,
                    "vol": 1000.0,
                    "amount": 10000.0,
                    "source": "akshare",
                    "ingest_time": datetime.now(timezone.utc),
                }
            ]
        )


def test_update_daily_akshare_batches_by_stock_basic(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(update_daily_bar, "TushareClient", MockDailyTushareMissing)
    monkeypatch.setattr(update_daily_bar, "AKShareClient", MockDailyAKShare)
    db_path = tmp_path / "quant.duckdb"
    init_db(db_path)
    with connect(db_path) as con:
        upsert_df(
            con,
            "stock_basic",
            pd.DataFrame(
                [
                    {
                        "ts_code": "000001.SZ",
                        "symbol": "000001",
                        "name": "平安银行",
                        "area": None,
                        "industry": None,
                        "market": None,
                        "list_date": None,
                        "delist_date": None,
                        "source": "test",
                        "ingest_time": datetime.now(timezone.utc),
                    }
                ]
            ),
        )

    assert update_daily_bar.update_daily_bar("20200101", "20200131", db_path) == 1
    with connect(db_path) as con:
        stored = fetch_df(con, "select * from daily_bar")
    assert len(stored) == 1


class MockFinancialTushare:
    source = "tushare"
    available = True

    def financial_indicator(self, start: str, end: str) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "fiscal_period": date(2019, 12, 31),
                    "announcement_date": date(2020, 3, 30),
                    "eps": 1.0,
                    "roe": 10.0,
                    "roa": 1.2,
                    "gross_margin": 30.0,
                    "netprofit_margin": 20.0,
                    "debt_to_asset": 60.0,
                    "current_ratio": 1.5,
                    "source": "tushare",
                    "ingest_time": datetime.now(timezone.utc),
                },
                {
                    "ts_code": "000002.SZ",
                    "fiscal_period": date(2019, 12, 31),
                    "announcement_date": pd.NA,
                    "eps": 2.0,
                    "source": "tushare",
                    "ingest_time": datetime.now(timezone.utc),
                },
            ]
        )


def test_update_financials_drops_rows_without_announcement_date(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(update_financials, "TushareClient", MockFinancialTushare)
    db_path = tmp_path / "quant.duckdb"

    assert update_financials.update_financials("20180101", "20200101", db_path) == 1
    with connect(db_path) as con:
        stored = fetch_df(con, "select * from financial_indicator")
    assert len(stored) == 1
    assert stored.loc[0, "ts_code"] == "000001.SZ"
