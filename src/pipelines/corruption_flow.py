from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import main as run_baseline
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Measure corruption impact, then repair from trusted raw lineage."""
    settings = load_settings()
    required = [
        settings.paths.clean_json,
        settings.paths.baseline_metrics,
        settings.paths.eval_testset,
    ]
    if not all(path.exists() for path in required):
        run_baseline()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality = read_json(settings.paths.baseline_quality_report)
    baseline_freshness = read_json(settings.paths.freshness_report)
    clean_df = pd.DataFrame(read_json(settings.paths.clean_json))
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(
        settings.paths.corrupted_clean_json,
        corrupted_df.to_dict(orient="records"),
    )
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.quality_dir / "corrupted_freshness_report.json",
    )

    repaired_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(repaired_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(
        settings.paths.repaired_clean_json,
        repaired_df.to_dict(orient="records"),
    )
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.quality_dir / "repaired_freshness_report.json",
    )
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        baseline_quality,
        corrupted_quality,
        repaired_quality,
        baseline_freshness,
        corrupted_freshness,
        repaired_freshness,
    )
    print("Baseline vs Corrupted vs Repaired")
    for name, metrics in (
        ("Baseline", baseline_metrics),
        ("Corrupted", corrupted_bundle.summary),
        ("Repaired", repaired_bundle.summary),
    ):
        print(
            f"{name:10} hit_rate={metrics['retrieval_hit_rate']:.4f} "
            f"token_f1={metrics['mean_token_f1']:.4f}"
        )
