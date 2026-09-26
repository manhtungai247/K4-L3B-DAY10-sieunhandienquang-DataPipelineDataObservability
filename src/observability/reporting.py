from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric(metrics: dict[str, Any], name: str) -> str:
    value = metrics.get(name)
    return f"{float(value):.4f}" if isinstance(value, (int, float)) else "n/a"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the reproducible baseline summary from generated artifacts."""
    content = f"""# Phase 1 — Baseline Data Pipeline

## Source and lineage

- Source: {source_summary.get("source", "Crossref")}
- Raw records: {source_summary.get("raw_records", 0)}
- Clean records: {source_summary.get("clean_records", 0)}
- Embedding model: `{source_summary.get("embedding_model", "n/a")}`

## Evaluation

| Metric | Value |
| --- | ---: |
| Samples | {metrics.get("samples", 0)} |
| Retrieval hit rate | {_metric(metrics, "retrieval_hit_rate")} |
| Mean token F1 | {_metric(metrics, "mean_token_f1")} |
| Judge accuracy | {_metric(metrics, "judge_accuracy")} |
| Mean judge score | {_metric(metrics, "mean_judge_score")} |

## Data observability

- Great Expectations suite: **{"PASS" if quality.get("gx_success") else "FAIL"}**
- Overall quality gate: **{"PASS" if quality.get("success") else "FAIL"}**
- Freshness SLA: **{"PASS" if freshness.get("is_fresh") else "FAIL"}**
- Stale rows: {freshness.get("stale_rows", 0)}/{freshness.get("total_rows", 0)}
- Freshness threshold: {freshness.get("threshold_days", "n/a")} days

This report is generated from the pipeline artifacts; values are not entered manually.
"""
    write_text(report_path, content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    baseline_quality: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    baseline_freshness: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the three-state corruption and repair comparison."""
    rows = [
        ("Retrieval hit rate", "retrieval_hit_rate"),
        ("Mean token F1", "mean_token_f1"),
        ("Judge accuracy", "judge_accuracy"),
        ("Mean judge score", "mean_judge_score"),
    ]
    metric_rows = "\n".join(
        f"| {label} | {_metric(baseline_metrics, key)} | "
        f"{_metric(corrupted_metrics, key)} | {_metric(repaired_metrics, key)} |"
        for label, key in rows
    )
    hit_drop = float(baseline_metrics.get("retrieval_hit_rate", 0)) - float(
        corrupted_metrics.get("retrieval_hit_rate", 0)
    )
    hit_recovery = float(repaired_metrics.get("retrieval_hit_rate", 0)) - float(
        corrupted_metrics.get("retrieval_hit_rate", 0)
    )
    quality_row = (
        f"| Quality gate | {'PASS' if baseline_quality.get('success') else 'FAIL'} | "
        f"{'PASS' if corrupted_quality.get('success') else 'FAIL'} | "
        f"{'PASS' if repaired_quality.get('success') else 'FAIL'} |"
    )
    baseline_fresh_status = "PASS" if baseline_freshness.get("is_fresh") else "FAIL"
    corrupted_fresh_status = (
        "PASS" if corrupted_freshness.get("is_fresh") else "FAIL"
    )
    repaired_fresh_status = "PASS" if repaired_freshness.get("is_fresh") else "FAIL"
    freshness_row = (
        f"| Freshness SLA | {baseline_fresh_status} | {corrupted_fresh_status} | "
        f"{repaired_fresh_status} |"
    )
    content = f"""# Corruption and Idempotent Repair Report

## Three-state comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
{metric_rows}
{quality_row}
{freshness_row}

## Observed impact

- Corruption changed retrieval hit rate by **{-hit_drop:+.4f}** relative to baseline.
- Rebuilding from the trusted raw snapshot recovered **{hit_recovery:+.4f}**
  hit-rate points.
- Corrupted quality checks failed because the suite injects missing summaries,
  duplicate IDs,
  truncated titles, stale dates, noisy text, and dropped records.
- Repair is idempotent: it discards the corrupted dataframe and rebuilds the
  canonical clean
  dataset from `data/raw/crossref_records.json`, then recreates the vector index.

## Freshness evidence

- Baseline stale ratio: {float(baseline_freshness.get("stale_ratio", 0)):.4f}
- Corrupted stale ratio: {float(corrupted_freshness.get("stale_ratio", 0)):.4f}
- Repaired stale ratio: {float(repaired_freshness.get("stale_ratio", 0)):.4f}

All values in this report are generated from pipeline artifacts.
"""
    write_text(report_path, content)
