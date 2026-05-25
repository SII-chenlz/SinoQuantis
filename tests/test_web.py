"""Web console tests."""

from __future__ import annotations

from pathlib import Path

from sinoquantis.db import table_exists
from sinoquantis.web import render_dashboard, run_action


def test_render_dashboard_contains_core_controls() -> None:
    html = render_dashboard()

    assert "SinoQuantis Web Console" in html
    assert "update-stock-basic" in html
    assert "update-filings" in html


def test_run_init_db_action(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "quant.duckdb"
    monkeypatch.setenv("SINOQUANTIS_DB_PATH", str(db_path))

    result = run_action({"action": "init-db"})

    assert result.ok
    assert table_exists("stock_basic", db_path)
