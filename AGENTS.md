# SinoQuantis Agent Instructions

You are working on **SinoQuantis**, an A-share quantitative research platform with LLM-enhanced fundamental analysis.

## Hard Rules

1. Do not implement live trading in phase one.
2. Do not provide investment advice.
3. Do not output buy/sell/target-price recommendations.
4. All financial statement and announcement data must be point-in-time.
5. No look-ahead bias.
6. API keys must only be read from environment variables.
7. All external API calls must include error handling, retry logic, and logging.
8. After each meaningful change, run tests.
9. Prefer maintainable, typed, testable code.
10. Do not place multiple large unrelated functions in one file.

## Architecture

- Data layer: self-controlled.
- Research layer: compatible with Qlib-style workflows later.
- Backtesting layer: lightweight first, inspired by RQAlpha/Backtrader design.
- Execution layer: only reserve vn.py adapter interfaces later; do not implement now.
- LLM layer: DeepSeek API for text structuring, risk extraction, and evidence collection only.

## Safety and Research Constraints

The LLM output should never directly become an order. It should produce structured fields such as sentiment score, risk score, quality score, uncertainty score, and evidence. These outputs must be validated through backtesting before being used as factors.
