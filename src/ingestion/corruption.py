from __future__ import annotations

from datetime import timedelta

import pandas as pd

from core.utils import write_json


def _rebuild_embedding_text(df: pd.DataFrame) -> None:
    df["authors_joined"] = df["authors"].apply(
        lambda values: ", ".join(values) if isinstance(values, list) else str(values)
    )
    df["categories_joined"] = df["categories"].apply(
        lambda values: ", ".join(values) if isinstance(values, list) else str(values)
    )
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: "\n".join(
            [
                f"Title: {row['title']}",
                f"Summary: {row['summary']}",
                f"Authors: {row['authors_joined']}",
                f"Categories: {row['categories_joined']}",
                f"Published: {row['published']}",
            ]
        ),
        axis=1,
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six deterministic corruptions and record their lineage."""
    if len(df) < 12:
        raise ValueError("At least 12 rows are required for the corruption suite.")

    corrupted = (
        df.copy(deep=True)
        .sort_values("published", ascending=False)
        .reset_index(drop=True)
    )
    drop_count = max(1, round(len(corrupted) * 0.20))
    dropped_ids = corrupted.iloc[:drop_count]["paper_id"].astype(str).tolist()
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)

    groups = {
        "blank_summary": list(range(min(3, len(corrupted)))),
        "inject_noise": list(range(3, min(6, len(corrupted)))),
        "truncate_title": list(range(6, min(9, len(corrupted)))),
        "stale_date": list(range(9, min(15, len(corrupted)))),
    }
    logs: list[dict] = [
        {
            "corruption_type": "drop_latest_records",
            "affected_count": len(dropped_ids),
            "paper_ids": dropped_ids,
            "parameters": {"fraction": 0.20},
        }
    ]

    blank_ids = corrupted.loc[groups["blank_summary"], "paper_id"].astype(str).tolist()
    corrupted.loc[groups["blank_summary"], "summary"] = ""
    logs.append(
        {
            "corruption_type": "blank_summary",
            "affected_count": len(blank_ids),
            "paper_ids": blank_ids,
        }
    )

    noise_ids = corrupted.loc[groups["inject_noise"], "paper_id"].astype(str).tolist()
    corrupted.loc[groups["inject_noise"], "summary"] = corrupted.loc[
        groups["inject_noise"], "summary"
    ].apply(lambda value: f"@@@ CORRUPTED ### {str(value)[::-1]} !!!")
    logs.append(
        {
            "corruption_type": "inject_noise",
            "affected_count": len(noise_ids),
            "paper_ids": noise_ids,
        }
    )

    title_ids = corrupted.loc[groups["truncate_title"], "paper_id"].astype(str).tolist()
    corrupted.loc[groups["truncate_title"], "title"] = (
        corrupted.loc[groups["truncate_title"], "title"].astype(str).str.slice(0, 5)
    )
    logs.append(
        {
            "corruption_type": "truncate_title",
            "affected_count": len(title_ids),
            "paper_ids": title_ids,
            "parameters": {"max_characters": 5},
        }
    )

    stale_ids = corrupted.loc[groups["stale_date"], "paper_id"].astype(str).tolist()
    for index in groups["stale_date"]:
        published = pd.to_datetime(corrupted.at[index, "published"], errors="coerce")
        if pd.notna(published):
            corrupted.at[index, "published"] = (
                (published - timedelta(days=730)).date().isoformat()
            )
            corrupted.at[index, "age_days"] = int(corrupted.at[index, "age_days"]) + 730
    logs.append(
        {
            "corruption_type": "stale_date",
            "affected_count": len(stale_ids),
            "paper_ids": stale_ids,
            "parameters": {"days_shifted": 730},
        }
    )

    duplicate_source = corrupted.iloc[:2].copy(deep=True)
    duplicate_ids = duplicate_source["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicate_source], ignore_index=True)
    logs.append(
        {
            "corruption_type": "duplicate_rows",
            "affected_count": len(duplicate_ids),
            "paper_ids": duplicate_ids,
        }
    )

    _rebuild_embedding_text(corrupted)
    write_json(
        output_log_path,
        {
            "input_rows": len(df),
            "output_rows": len(corrupted),
            "corruptions": logs,
        },
    )
    return corrupted.reset_index(drop=True)
