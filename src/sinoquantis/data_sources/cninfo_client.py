"""Cninfo announcement index adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class CninfoClient:
    """Fetch filing index rows from Cninfo and reserve PDF download support."""

    source = "cninfo"
    query_url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    static_base_url = "http://static.cninfo.com.cn"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 SinoQuantis research client",
                "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch",
            }
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def query_filings(
        self,
        start: str,
        end: str,
        stock: str | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> pd.DataFrame:
        """Query filing index rows for a date window."""
        payload = {
            "pageNum": page,
            "pageSize": page_size,
            "column": "szse",
            "tabName": "fulltext",
            "plate": "",
            "stock": stock or "",
            "searchkey": "",
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": f"{_dash_date(start)}~{_dash_date(end)}",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        try:
            response = self.session.post(self.query_url, data=payload, timeout=self.timeout)
            response.raise_for_status()
            rows = response.json().get("announcements") or []
            return self.normalize(rows)
        except Exception as exc:
            logger.exception("Cninfo filing query failed: {}", exc)
            return pd.DataFrame()

    def normalize(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        """Normalize raw Cninfo announcement rows to filing_index schema."""
        records: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for row in rows:
            sec_code = str(row.get("secCode") or "").zfill(6)
            adjunct_url = row.get("adjunctUrl") or ""
            url = f"{self.static_base_url}/{adjunct_url}" if adjunct_url else None
            announcement_date = _announcement_date(row.get("announcementTime"))
            title = _clean_title(str(row.get("announcementTitle") or ""))
            source_doc_id = filing_source_doc_id(sec_code, title, announcement_date, url)
            records.append(
                {
                    "source_doc_id": source_doc_id,
                    "ts_code": symbol_to_ts_code(sec_code) if sec_code.strip("0") else None,
                    "company_name": row.get("secName"),
                    "title": title,
                    "filing_type": row.get("category"),
                    "report_period": _parse_date(row.get("reportPeriod")),
                    "announcement_date": announcement_date,
                    "url": url,
                    "local_path": None,
                    "source": self.source,
                    "ingest_time": now,
                    "file_hash": None,
                }
            )
        return pd.DataFrame(records)

    def download_pdf(self, url: str, output_path: Path) -> Path | None:
        """Download a filing PDF. The first pipeline only stores URLs and does not call this."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            return output_path
        except Exception as exc:
            logger.exception("Cninfo PDF download failed for {}: {}", url, exc)
            return None


def filing_source_doc_id(
    sec_code: str,
    title: str,
    announcement_date,
    url: str | None,
) -> str:
    """Build a stable filing document id from source fields."""
    raw = f"cninfo|{sec_code}|{announcement_date}|{title}|{url or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def symbol_to_ts_code(symbol: str) -> str:
    """Convert six-digit A-share code to ts_code."""
    clean = str(symbol).zfill(6)
    suffix = "SH" if clean.startswith(("6", "9")) else "SZ"
    return f"{clean}.{suffix}"


def _dash_date(value: str) -> str:
    text = str(value).replace("-", "")
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


def _announcement_date(value: Any):
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000).date()
    except Exception:
        return _parse_date(value)


def _parse_date(value: Any):
    if value in (None, ""):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _clean_title(title: str) -> str:
    return title.replace("<em>", "").replace("</em>", "").strip()
