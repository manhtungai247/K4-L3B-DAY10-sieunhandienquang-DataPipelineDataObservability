from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd
from great_expectations import expectations as gxe

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(
    df: pd.DataFrame, settings: Settings, report_name: str
) -> dict[str, Any]:
    """Run the required Great Expectations 1.x suite and freshness gate."""
    required_columns = {"paper_id", "title", "summary", "age_days"}
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"Missing columns for quality checks: {missing}")

    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    asset = source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_definition = asset.add_batch_definition_whole_dataframe(
        f"papers_batch_{report_name}"
    )
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
    expectations = [
        gxe.ExpectTableRowCountToBeBetween(
            min_value=max(1, int(settings.max_results * 0.75)),
            max_value=settings.max_results + 5,
        ),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20),
    ]
    results = [batch.validate(expectation) for expectation in expectations]
    checks = [
        {
            "expectation": type(expectation).__name__,
            "success": bool(result.success),
            "result": dict(result.result or {}),
        }
        for expectation, result in zip(expectations, results, strict=True)
    ]
    stale_rows = int(
        (
            pd.to_numeric(df["age_days"], errors="coerce")
            > settings.freshness_threshold_days
        ).sum()
    )
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    freshness_success = stale_ratio <= 0.25
    payload = {
        "report_name": report_name,
        "success": all(check["success"] for check in checks) and freshness_success,
        "gx_success": all(check["success"] for check in checks),
        "checks": checks,
        "freshness": {
            "threshold_days": settings.freshness_threshold_days,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": stale_ratio,
            "success": freshness_success,
        },
    }
    write_json(
        settings.paths.quality_dir / f"{report_name}_quality_report.json", payload
    )
    return payload


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path
) -> dict[str, Any]:
    """Summarize publication recency against the configured freshness SLA."""
    published = pd.to_datetime(df["published"], errors="coerce").dropna()
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    payload = {
        "latest_published": published.max().date().isoformat()
        if not published.empty
        else None,
        "oldest_published": published.min().date().isoformat()
        if not published.empty
        else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "allowed_stale_ratio": 0.25,
        "is_fresh": stale_ratio <= 0.25,
    }
    write_json(report_path, payload)
    return payload
