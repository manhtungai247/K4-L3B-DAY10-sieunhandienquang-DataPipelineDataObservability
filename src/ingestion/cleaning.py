from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(
    records: list[PaperRecord], run_date: datetime
) -> pd.DataFrame:
    """Normalize raw records into the canonical pre-embedding dataframe."""
    rows: list[dict] = []
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")

    for record in records:
        title = normalize_whitespace(re.sub(r"<[^>]+>", " ", record.title))
        summary = normalize_whitespace(re.sub(r"<[^>]+>", " ", record.summary))
        paper_id = normalize_whitespace(record.paper_id).lower()
        authors = list(
            dict.fromkeys(
                normalize_whitespace(value) for value in record.authors if value.strip()
            )
        )
        categories = list(
            dict.fromkeys(
                normalize_whitespace(value)
                for value in record.categories
                if value.strip()
            )
        )
        published = pd.to_datetime(record.published, utc=True, errors="coerce")
        updated = pd.to_datetime(record.updated, utc=True, errors="coerce")
        if not paper_id or not title or not summary or pd.isna(published):
            continue
        published_text = published.date().isoformat()
        updated_text = (
            updated.date().isoformat() if not pd.isna(updated) else published_text
        )
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        age_days = max(0, (run_timestamp.date() - published.date()).days)
        text_for_embedding = "\n".join(
            [
                f"Title: {title}",
                f"Summary: {summary}",
                f"Authors: {authors_joined}",
                f"Categories: {categories_joined}",
                f"Published: {published_text}",
            ]
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(record.primary_category)
                or (categories[0] if categories else "Uncategorized"),
                "published": published_text,
                "updated": updated_text,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        raise ValueError("No valid records remained after cleaning.")
    dataframe = pd.DataFrame(rows)
    dataframe = dataframe.drop_duplicates(subset=["paper_id"], keep="first")
    return dataframe.sort_values(
        by=["published", "paper_id"], ascending=[False, True]
    ).reset_index(drop=True)
