from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def _parse_date(date_str: str) -> datetime:
    try:
        clean_date_str = str(date_str).strip()[:10]
        dt = datetime.strptime(clean_date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=UTC)
    except Exception:
        return datetime(2026, 1, 1, tzinfo=UTC)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a validated pandas DataFrame ready for embedding and indexing."""
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)

    cleaned_rows: list[dict[str, Any]] = []

    for record in records:
        paper_id = normalize_whitespace(record.paper_id)
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)

        if not paper_id or not title:
            continue

        authors = [normalize_whitespace(a) for a in record.authors if a]
        authors_joined = compact_join(authors, sep=", ")

        categories = [normalize_whitespace(c) for c in record.categories if c]
        categories_joined = compact_join(categories, sep=", ")

        pub_dt = _parse_date(record.published)
        published_str = pub_dt.strftime("%Y-%m-%d")
        updated_dt = _parse_date(record.updated or record.published)
        updated_str = updated_dt.strftime("%Y-%m-%d")

        age_days = max(0, (run_date.date() - pub_dt.date()).days)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {published_str}\n"
            f"Summary: {summary}"
        )

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category or (categories[0] if categories else "General"),
                "published": published_str,
                "updated": updated_str,
                "age_days": age_days,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)
    if df.empty:
        return df

    # Khử trùng lặp theo paper_id và lọc row xấu
    df = df.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
