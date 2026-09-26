from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into normalized paper records."""

    def text(value: object) -> str:
        raw = "" if value is None else str(value)
        without_tags = re.sub(r"<[^>]+>", " ", raw)
        return normalize_whitespace(without_tags)

    def date_parts(value: object) -> str:
        if not isinstance(value, dict):
            return ""
        parts = value.get("date-parts")
        if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
            return ""
        numbers = parts[0]
        if not numbers:
            return ""
        try:
            year = int(numbers[0])
            month = int(numbers[1]) if len(numbers) > 1 else 1
            day = int(numbers[2]) if len(numbers) > 2 else 1
            return date(year, month, day).isoformat()
        except (TypeError, ValueError):
            return ""

    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []
    seen: set[str] = set()

    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        paper_id = text(item.get("DOI") or item.get("URL")).lower()
        titles = item.get("title", [])
        title = text(titles[0] if isinstance(titles, list) and titles else titles)
        summary = text(item.get("abstract"))
        if not paper_id or paper_id in seen or not title or not summary:
            continue

        authors: list[str] = []
        for author in item.get("author", []) or []:
            if not isinstance(author, dict):
                continue
            name = normalize_whitespace(
                " ".join(
                    filter(
                        None, [text(author.get("given")), text(author.get("family"))]
                    )
                )
            )
            if name and name not in authors:
                authors.append(name)

        categories = [text(value) for value in item.get("subject", []) or []]
        categories = list(dict.fromkeys(value for value in categories if value))
        published = date_parts(item.get("published") or item.get("published-print"))
        created = item.get("created", {})
        updated = (
            text(created.get("date-time"))[:10] if isinstance(created, dict) else ""
        )
        updated = updated or published
        abs_url = text(item.get("URL")) or f"https://doi.org/{paper_id}"
        links = item.get("link", []) or []
        pdf_url = next(
            (
                text(link.get("URL"))
                for link in links
                if isinstance(link, dict)
                and "pdf" in str(link.get("content-type", "")).lower()
            ),
            abs_url,
        )
        if not published:
            continue

        seen.add(paper_id)
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "Uncategorized",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data with retry and fall back to the bundled snapshot."""
    payload: dict | None = None
    if not settings.refresh_source and settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
            "select": "DOI,title,abstract,author,subject,published,created,URL,link",
        }
        headers = {"User-Agent": "AI20K-Day10-Lab/1.0 (educational project)"}
        for attempt in range(4):
            try:
                response = requests.get(
                    "https://api.crossref.org/works",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(
                        f"Crossref returned {response.status_code}"
                    )
                response.raise_for_status()
                payload = response.json()
                write_json(settings.paths.raw_api_response, payload)
                break
            except (requests.RequestException, ValueError):
                if attempt < 3:
                    time.sleep(2**attempt)

    if payload is None:
        if not settings.paths.raw_api_response.exists():
            raise RuntimeError("Crossref unavailable and no local snapshot was found.")
        payload = read_json(settings.paths.raw_api_response)

    records = parse_crossref_payload(payload)
    if not records and settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)
    if not records:
        raise ValueError("Crossref payload did not contain valid paper records.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the normalized raw-record snapshot."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of records in {path}")
    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            PaperRecord(
                paper_id=str(item.get("paper_id", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
                authors=[str(value) for value in item.get("authors", [])],
                categories=[str(value) for value in item.get("categories", [])],
                primary_category=str(item.get("primary_category", "Uncategorized")),
                published=str(item.get("published", "")),
                updated=str(item.get("updated", "")),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records
