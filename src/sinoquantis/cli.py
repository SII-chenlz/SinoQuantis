"""Command-line interface for SinoQuantis."""

from __future__ import annotations

import platform
from pathlib import Path

import duckdb
import typer
from dotenv import load_dotenv
from loguru import logger

from sinoquantis.config import get_settings
from sinoquantis.db import init_db
from sinoquantis.pipelines.update_adj_factor import update_adj_factor as update_adj_factor_pipeline
from sinoquantis.pipelines.update_calendar import update_calendar as update_calendar_pipeline
from sinoquantis.pipelines.update_daily_bar import update_daily_bar as update_daily_bar_pipeline
from sinoquantis.pipelines.update_filings import update_filings as update_filings_pipeline
from sinoquantis.pipelines.update_financials import update_financials as update_financials_pipeline
from sinoquantis.pipelines.update_stock_basic import (
    update_stock_basic as update_stock_basic_pipeline,
)

load_dotenv()

app = typer.Typer(help="SinoQuantis A-share quantitative research platform.")
DB_PATH_OPTION = typer.Option(None, "--db-path", help="Optional DuckDB path.")


@app.command("doctor")
def doctor() -> None:
    """Check local environment and configuration."""
    settings = get_settings()
    data_dir = settings.sinoquantis_data_dir

    typer.echo("SinoQuantis doctor")
    typer.echo(f"Python: {platform.python_version()}")
    typer.echo(f"DuckDB: {duckdb.__version__}")
    typer.echo(f"Data dir: {data_dir.resolve()}")
    typer.echo(f"DB path: {settings.sinoquantis_db_path}")

    if settings.tushare_token:
        typer.echo("TUSHARE_TOKEN: found")
    else:
        typer.echo("TUSHARE_TOKEN: missing")

    if settings.deepseek_api_key:
        typer.echo("DEEPSEEK_API_KEY: found")
    else:
        typer.echo("DEEPSEEK_API_KEY: missing")

    for subdir in ["raw", "filings", "reports"]:
        path = data_dir / subdir
        if not path.exists():
            logger.warning("Creating missing data directory: {}", path)
            path.mkdir(parents=True, exist_ok=True)

    typer.echo("Doctor check complete.")


@app.command("init-db")
def init_db_command(
    db_path: Path | None = DB_PATH_OPTION,
) -> None:
    """Initialize DuckDB schema."""
    init_db(db_path)
    typer.echo("Database initialized.")


@app.command("update-stock-basic")
def update_stock_basic() -> None:
    """Update A-share stock basic information."""
    rows = update_stock_basic_pipeline()
    typer.echo(f"Updated stock_basic rows: {rows}")


@app.command("update-calendar")
def update_calendar(start: str = typer.Option(...), end: str = typer.Option(...)) -> None:
    """Update A-share trading calendar."""
    rows = update_calendar_pipeline(start, end)
    typer.echo(f"Updated trade_calendar rows: {rows}")


@app.command("update-daily")
def update_daily(start: str = typer.Option(...), end: str = typer.Option(...)) -> None:
    """Update A-share daily bars."""
    rows = update_daily_bar_pipeline(start, end)
    typer.echo(f"Updated daily_bar rows: {rows}")


@app.command("update-adj-factor")
def update_adj_factor(start: str = typer.Option(...), end: str = typer.Option(...)) -> None:
    """Update A-share adjustment factors."""
    rows = update_adj_factor_pipeline(start, end)
    typer.echo(f"Updated adj_factor rows: {rows}")


@app.command("update-financials")
def update_financials(start: str = typer.Option(...), end: str = typer.Option(...)) -> None:
    """Update A-share financial indicators."""
    rows = update_financials_pipeline(start, end)
    typer.echo(f"Updated financial_indicator rows: {rows}")


@app.command("update-filings")
def update_filings(start: str = typer.Option(...), end: str = typer.Option(...)) -> None:
    """Update A-share filing announcement index."""
    rows = update_filings_pipeline(start, end)
    typer.echo(f"Updated filing_index rows: {rows}")


if __name__ == "__main__":
    app()
