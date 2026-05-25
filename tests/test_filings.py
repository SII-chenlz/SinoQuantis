"""Filing index tests with mocked Cninfo client."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from sinoquantis.data_sources.cninfo_client import CninfoClient
from sinoquantis.db import connect, fetch_df
from sinoquantis.pipelines import update_filings


class MockCninfoClient:
    source = "cninfo"

    def query_filings(
        self,
        start: str,
        end: str,
        page: int = 1,
        page_size: int = 30,
    ) -> pd.DataFrame:
        if page > 1:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {
                    "source_doc_id": "doc-1",
                    "ts_code": "000001.SZ",
                    "company_name": "平安银行",
                    "title": "2025年年度报告",
                    "filing_type": "年度报告",
                    "report_period": date(2025, 12, 31),
                    "announcement_date": date(2026, 3, 30),
                    "url": "http://static.cninfo.com.cn/test.pdf",
                    "local_path": None,
                    "source": "cninfo",
                    "ingest_time": datetime.now(timezone.utc),
                    "file_hash": None,
                }
            ]
        )


def test_update_filings_upserts_mocked_rows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(update_filings, "CninfoClient", MockCninfoClient)
    db_path = tmp_path / "quant.duckdb"

    assert update_filings.update_filings("20240101", "20260524", db_path) == 1
    assert update_filings.update_filings("20240101", "20260524", db_path) == 1

    with connect(db_path) as con:
        stored = fetch_df(con, "select * from filing_index")
    assert len(stored) == 1
    assert stored.loc[0, "source_doc_id"] == "doc-1"


def test_cninfo_normalize_builds_stable_doc_id_and_cleans_title() -> None:
    client = CninfoClient()
    data = client.normalize(
        [
            {
                "secCode": "000001",
                "secName": "平安银行",
                "announcementTitle": "<em>年度报告</em>",
                "category": "年度报告",
                "announcementTime": 1774800000000,
                "adjunctUrl": "finalpage/test.pdf",
            }
        ]
    )

    assert len(data) == 1
    assert data.loc[0, "title"] == "年度报告"
    assert data.loc[0, "ts_code"] == "000001.SZ"
    assert data.loc[0, "source_doc_id"]
