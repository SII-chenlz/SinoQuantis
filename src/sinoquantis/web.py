"""Lightweight web console for SinoQuantis operations."""

from __future__ import annotations

import html
import platform
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import duckdb
from loguru import logger

from sinoquantis.config import get_settings
from sinoquantis.db import connect, init_db, table_exists
from sinoquantis.pipelines.update_adj_factor import update_adj_factor
from sinoquantis.pipelines.update_calendar import update_calendar
from sinoquantis.pipelines.update_daily_bar import update_daily_bar
from sinoquantis.pipelines.update_filings import update_filings
from sinoquantis.pipelines.update_financials import update_financials
from sinoquantis.pipelines.update_stock_basic import update_stock_basic

TABLES = [
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


@dataclass(frozen=True)
class ActionResult:
    """Result shown after a web operation."""

    ok: bool
    title: str
    message: str


def get_table_counts() -> list[dict[str, Any]]:
    """Return row counts for known tables, tolerating an uninitialized database."""
    settings = get_settings()
    if not settings.sinoquantis_db_path.exists():
        return [{"table": table, "exists": False, "rows": None} for table in TABLES]

    counts: list[dict[str, Any]] = []
    with connect(settings.sinoquantis_db_path) as con:
        for table in TABLES:
            exists = table_exists(table, settings.sinoquantis_db_path)
            rows = None
            if exists:
                rows = con.execute(f"select count(*) from {table}").fetchone()[0]
            counts.append({"table": table, "exists": exists, "rows": rows})
    return counts


def run_action(form: dict[str, str]) -> ActionResult:
    """Run a web-submitted operation and return a displayable result."""
    action = form.get("action", "")
    try:
        if action == "init-db":
            init_db()
            return ActionResult(True, "数据库初始化完成", "已创建或确认所有核心表。")
        if action == "update-stock-basic":
            rows = update_stock_basic()
            return ActionResult(True, "股票基础信息更新完成", f"写入/更新 {rows} 行。")
        if action == "update-calendar":
            rows = update_calendar(_required(form, "start"), _required(form, "end"))
            return ActionResult(True, "交易日历更新完成", f"写入/更新 {rows} 行。")
        if action == "update-daily":
            rows = update_daily_bar(_required(form, "start"), _required(form, "end"))
            return ActionResult(True, "日线行情更新完成", f"写入/更新 {rows} 行。")
        if action == "update-adj-factor":
            rows = update_adj_factor(_required(form, "start"), _required(form, "end"))
            return ActionResult(True, "复权因子更新完成", f"写入/更新 {rows} 行。")
        if action == "update-financials":
            rows = update_financials(_required(form, "start"), _required(form, "end"))
            return ActionResult(True, "财务指标更新完成", f"写入/更新 {rows} 行。")
        if action == "update-filings":
            rows = update_filings(_required(form, "start"), _required(form, "end"))
            return ActionResult(True, "公告索引更新完成", f"写入/更新 {rows} 行。")
        return ActionResult(False, "未知操作", f"未识别的 action: {action}")
    except Exception as exc:  # pragma: no cover - defensive web boundary
        logger.exception("Web action failed: {}", exc)
        return ActionResult(False, "操作失败", str(exc))


def render_dashboard(result: ActionResult | None = None) -> str:
    """Render the complete web dashboard HTML."""
    settings = get_settings()
    counts = get_table_counts()
    token_state = "已配置" if settings.tushare_token else "未配置"
    deepseek_state = "已配置" if settings.deepseek_api_key else "未配置"
    result_html = ""
    if result:
        klass = "notice ok" if result.ok else "notice error"
        result_html = f"""
        <section class=\"{klass}\">
          <strong>{_e(result.title)}</strong>
          <span>{_e(result.message)}</span>
        </section>
        """

    table_rows = "".join(
        f"""
        <tr>
          <td>{_e(row['table'])}</td>
          <td>{'是' if row['exists'] else '否'}</td>
          <td>{'-' if row['rows'] is None else row['rows']}</td>
        </tr>
        """
        for row in counts
    )
    status_items = [
        ("Python", platform.python_version()),
        ("DuckDB", duckdb.__version__),
        ("数据目录", settings.sinoquantis_data_dir.resolve()),
        ("数据库", settings.sinoquantis_db_path),
        ("TUSHARE_TOKEN", token_state),
        ("DEEPSEEK_API_KEY", deepseek_state),
    ]
    status_rows = "".join(
        (
            f'<div class="status-item"><strong>{_e(label)}</strong>'
            f'<span>{_e(value)}</span></div>'
        )
        for label, value in status_items
    )

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>SinoQuantis Web Console</title>
  <style>
    :root {{
      --bg: #f5f7fa;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #64748b;
      --border: #d9e1ea;
      --accent: #0f766e;
      --accent-soft: #dff7f4;
      --danger: #b42318;
      --danger-soft: #fee4e2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background: var(--bg);
    }}
    header {{
      padding: 24px 32px;
      background: #0f172a;
      color: white;
      border-bottom: 4px solid var(--accent);
    }}
    header h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    header p {{ margin: 0; color: #cbd5e1; }}
    main {{ width: min(1180px, calc(100vw - 32px)); margin: 24px auto 48px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    .panel h2 {{ margin: 0 0 14px; font-size: 18px; }}
    .status-list {{ display: grid; gap: 8px; }}
    .status-item {{ display: flex; justify-content: space-between; gap: 16px; }}
    .status-item span:last-child {{ color: var(--muted); text-align: right; }}
    .notice {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
      padding: 12px 14px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    .notice.ok {{ background: var(--accent-soft); border-color: #99e6dc; }}
    .notice.error {{ background: var(--danger-soft); border-color: #fecdca; color: var(--danger); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid var(--border); text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; }}
    form {{ display: grid; gap: 10px; }}
    label {{ font-size: 13px; color: var(--muted); }}
    input {{
      width: 100%;
      height: 38px;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0 10px;
      font: inherit;
      background: white;
    }}
    button {{
      height: 38px;
      border: 0;
      border-radius: 6px;
      padding: 0 14px;
      font: inherit;
      color: white;
      background: var(--accent);
      cursor: pointer;
    }}
    button.secondary {{ color: var(--text); background: #e2e8f0; }}
    .actions {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .inline {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .full {{ grid-column: 1 / -1; }}
    footer {{ margin-top: 18px; color: var(--muted); font-size: 13px; }}
    @media (max-width: 860px) {{
      .grid, .actions, .inline {{ grid-template-columns: 1fr; }}
      header {{ padding: 20px 16px; }}
      main {{ width: calc(100vw - 20px); margin-top: 12px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>SinoQuantis Web Console</h1>
    <p>A 股量化研究操作台。当前只做研究数据更新和本地数据库管理，不接入实盘交易。</p>
  </header>
  <main>
    {result_html}
    <section class=\"grid\">
      <div class=\"panel\">
        <h2>环境状态</h2>
        <div class=\"status-list\">{status_rows}</div>
      </div>
      <div class=\"panel\">
        <h2>快捷操作</h2>
        <form method=\"post\" action=\"/action\">
          <input type=\"hidden\" name=\"action\" value=\"init-db\">
          <button type=\"submit\">初始化数据库</button>
        </form>
        <form method=\"post\" action=\"/action\" style=\"margin-top: 10px;\">
          <input type=\"hidden\" name=\"action\" value=\"update-stock-basic\">
          <button class=\"secondary\" type=\"submit\">更新股票基础信息</button>
        </form>
      </div>
    </section>

    <section class=\"panel\" style=\"margin-top: 16px;\">
      <h2>数据更新</h2>
      <div class=\"actions\">
        {_date_form('update-calendar', '交易日历', '20100101', '20261231')}
        {_date_form('update-daily', '日线行情', '20200101', '20260524')}
        {_date_form('update-adj-factor', '复权因子', '20200101', '20260524')}
        {_date_form('update-financials', '财务指标', '20180101', '20260524')}
        {_date_form('update-filings', '公告索引', '20240101', '20260524', full=True)}
      </div>
    </section>

    <section class=\"panel\" style=\"margin-top: 16px;\">
      <h2>数据库表</h2>
      <table>
        <thead><tr><th>表名</th><th>已创建</th><th>行数</th></tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </section>
    <footer>提示：大范围更新行情和公告可能耗时较长；建议先用较小日期区间试跑。</footer>
  </main>
</body>
</html>"""


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the blocking web console server."""
    server = ThreadingHTTPServer((host, port), SinoQuantisRequestHandler)
    logger.info("SinoQuantis web console started at http://{}:{}", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - interactive server shutdown
        logger.info("Stopping SinoQuantis web console")
    finally:
        server.server_close()


class SinoQuantisRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the lightweight web console."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/", "/index.html"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_html(render_dashboard())

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/action":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        parsed = urllib.parse.parse_qs(raw_body)
        form = {key: values[-1] for key, values in parsed.items() if values}
        result = run_action(form)
        self._send_html(render_dashboard(result))

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug("web: " + fmt, *args)

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _required(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"缺少必填参数: {key}")
    return value


def _date_form(
    action: str,
    title: str,
    default_start: str,
    default_end: str,
    full: bool = False,
) -> str:
    klass = "panel full" if full else "panel"
    return f"""
    <form class=\"{klass}\" method=\"post\" action=\"/action\">
      <h2>{_e(title)}</h2>
      <input type=\"hidden\" name=\"action\" value=\"{_e(action)}\">
      <div class=\"inline\">
        <div>
          <label>开始日期</label>
          <input name=\"start\" value=\"{_e(default_start)}\" inputmode=\"numeric\" required>
        </div>
        <div>
          <label>结束日期</label>
          <input name=\"end\" value=\"{_e(default_end)}\" inputmode=\"numeric\" required>
        </div>
      </div>
      <button type=\"submit\">开始更新</button>
    </form>
    """


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)
