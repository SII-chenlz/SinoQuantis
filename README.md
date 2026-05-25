# SinoQuantis

**SinoQuantis** is an A-share quantitative research platform with LLM-enhanced fundamental analysis.

This project is designed for research and backtesting only. It does **not** connect to live brokers, place real orders, or provide investment advice.

## Goals

SinoQuantis aims to provide:

- A-share market data ingestion
- Financial statement and announcement indexing
- Point-in-time financial data handling
- LLM-based filing and announcement structuring via DeepSeek API
- Factor generation
- Daily-frequency research backtesting
- Future compatibility with Qlib-style research workflows

## Design Principles

1. Data layer is self-controlled.
2. All financial and announcement data must be point-in-time.
3. No look-ahead bias.
4. T-day signal can only trade from T+1.
5. LLM is used only for text structuring and risk extraction, not trading decisions.
6. No live trading in phase one.
7. API keys are read only from environment variables.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then set:

```env
TUSHARE_TOKEN=
DEEPSEEK_API_KEY=
```

## Basic Commands

```bash
python -m sinoquantis.cli doctor
python -m sinoquantis.cli init-db
```

## Roadmap

- Task 1: project skeleton
- Task 2: DuckDB schema and storage helpers
- Task 3: Tushare and AKShare data adapters
- Task 4: filing index and DeepSeek analysis module
- Task 5: factor generation
- Task 6: daily backtest engine
- Task 7: Qlib export
- Task 8: research report generation

## Disclaimer

This project is for research and education only. It does not constitute investment advice.
