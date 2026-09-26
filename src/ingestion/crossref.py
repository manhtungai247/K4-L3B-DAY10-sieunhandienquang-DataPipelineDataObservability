from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_jats_xml(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def _format_date_parts(date_parts: list[Any]) -> str:
    if not date_parts or not isinstance(date_parts, list):
        return "2026-01-01"
    first = date_parts[0]
    if isinstance(first, list):
        year = first[0] if len(first) > 0 else 2026
        month = first[1] if len(first) > 1 else 1
        day = first[2] if len(first) > 2 else 1
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return "2026-01-01"


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref API payload to a list of PaperRecord objects."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = item.get("DOI") or item.get("id") or ""
        if not paper_id:
            continue

        raw_title = item.get("title", [""])
        title = raw_title[0] if isinstance(raw_title, list) and raw_title else str(raw_title)
        title = normalize_whitespace(title)

        raw_abstract = item.get("abstract", "")
        summary = _clean_jats_xml(raw_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)

        categories = item.get("subject", [])
        if not isinstance(categories, list):
            categories = [str(categories)] if categories else []
        primary_category = categories[0] if categories else "Computer Science"

        published = ""
        if "published" in item and "date-parts" in item["published"]:
            published = _format_date_parts(item["published"]["date-parts"])
        elif "published-online" in item and "date-parts" in item["published-online"]:
            published = _format_date_parts(item["published-online"]["date-parts"])
        elif "created" in item and "date-time" in item["created"]:
            published = str(item["created"]["date-time"])[:10]
        else:
            published = "2026-01-01"

        updated = published
        url = item.get("URL") or f"https://doi.org/{paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=f"Crossref record {paper_id}",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API, saving raw response and records.
    
    Falls back to local snapshot if network is unavailable, refresh_source is False,
    or API returns errors.
    """
    records: list[PaperRecord] = []

    if settings.refresh_source:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "DataObservabilityLab/1.0 (mailto:student@lab.edu)"}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                payload = response.json()
                write_json(settings.paths.raw_api_response, payload)
                records = parse_crossref_payload(payload)
                if records:
                    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
                    return records
        except Exception:
            # Fall back to offline snapshot
            pass

    # Fallback: Load from existing raw_records_json if available
    if settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)
        if records:
            return records

    # Fallback: Load from raw_api_response snapshot
    if settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)
        records = parse_crossref_payload(payload)
        if records:
            write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
            return records

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map into a list of PaperRecord objects."""
    data = read_json(path)
    if isinstance(data, dict) and "message" in data:
        return parse_crossref_payload(data)
    if isinstance(data, list):
        return [PaperRecord(**item) for item in data]
    return []
