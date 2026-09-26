from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Inject 6 synthetic data corruptions into a clean DataFrame and log operations."""
    out_log = Path(output_log_path) if isinstance(output_log_path, str) else output_log_path
    corrupted = df.copy()
    logs: list[dict[str, Any]] = []

    # 1. Drop latest records (20% of dataset)
    drop_count = max(1, int(len(corrupted) * 0.20))
    dropped_papers = corrupted.iloc[:drop_count][["paper_id", "title"]].to_dict(orient="records")
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)
    logs.append(
        {
            "corruption_type": "drop_latest_records",
            "count": drop_count,
            "description": f"Dropped {drop_count} newest records to simulate missing ingestion events.",
            "affected_papers": dropped_papers,
        }
    )

    # 2. Blank summary on selected rows
    blank_indices = [0, 1] if len(corrupted) >= 2 else [0]
    blanked_papers: list[dict[str, Any]] = []
    for idx in blank_indices:
        p_id = corrupted.loc[idx, "paper_id"]
        corrupted.loc[idx, "summary"] = ""
        blanked_papers.append({"index": idx, "paper_id": p_id})
    logs.append(
        {
            "corruption_type": "blank_summary",
            "count": len(blank_indices),
            "description": "Erased abstract/summary to empty string (violates summary length expectation).",
            "affected_papers": blanked_papers,
        }
    )

    # 3. Inject noise into summary
    noise_indices = [2, 3] if len(corrupted) >= 4 else []
    noise_papers: list[dict[str, Any]] = []
    for idx in noise_indices:
        p_id = corrupted.loc[idx, "paper_id"]
        corrupted.loc[idx, "summary"] = f"### NOISE JUNK %$#@! {corrupted.loc[idx, 'summary']}"
        noise_papers.append({"index": idx, "paper_id": p_id})
    logs.append(
        {
            "corruption_type": "inject_noise",
            "count": len(noise_indices),
            "description": "Injected gibberish noise prefix to degrade embedding semantic matching.",
            "affected_papers": noise_papers,
        }
    )

    # 4. Truncate title (< 8 characters)
    trunc_indices = [4, 5] if len(corrupted) >= 6 else []
    trunc_papers: list[dict[str, Any]] = []
    for idx in trunc_indices:
        p_id = corrupted.loc[idx, "paper_id"]
        corrupted.loc[idx, "title"] = "Bad"
        trunc_papers.append({"index": idx, "paper_id": p_id})
    logs.append(
        {
            "corruption_type": "truncate_title",
            "count": len(trunc_indices),
            "description": "Truncated paper title to 'Bad' (< 8 chars) breaking title lookup and metadata.",
            "affected_papers": trunc_papers,
        }
    )

    # 5. Stale date (make published dates very old to violate Freshness SLA)
    stale_count = max(6, int(len(corrupted) * 0.40))
    stale_papers: list[dict[str, Any]] = []
    for idx in range(min(stale_count, len(corrupted))):
        p_id = corrupted.loc[idx, "paper_id"]
        corrupted.loc[idx, "published"] = "2020-01-01"
        corrupted.loc[idx, "age_days"] = 2450
        stale_papers.append({"index": idx, "paper_id": p_id})
    logs.append(
        {
            "corruption_type": "stale_date",
            "count": stale_count,
            "description": f"Rewound publication date to 2020 on {stale_count} papers (> 25% Freshness SLA threshold).",
            "affected_papers": stale_papers,
        }
    )

    # 6. Duplicate rows (violates paper_id uniqueness)
    dup_rows = corrupted.iloc[[0, 1]].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    logs.append(
        {
            "corruption_type": "duplicate_rows",
            "count": len(dup_rows),
            "description": "Duplicated rows with identical paper_id (violates unique paper_id expectation).",
            "affected_papers": dup_rows[["paper_id", "title"]].to_dict(orient="records"),
        }
    )

    # 7. Rebuild helper columns and text_for_embedding
    corrupted["summary_chars"] = corrupted["summary"].apply(len)
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Published: {row['published']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )

    write_json(out_log, logs)
    return corrupted
