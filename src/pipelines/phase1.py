from __future__ import annotations

from dataclasses import asdict

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Run raw ingestion, cleaning, indexing, evaluation and observability."""
    settings = load_settings()
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    if not records:
        raise RuntimeError("No raw records are available for the baseline pipeline.")

    clean_df = build_clean_dataframe(records, now_utc())
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(
        clean_df, settings, settings.paths.embeddings_json
    )
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(
        clean_df, settings, settings.paths.freshness_report
    )
    generate_phase1_report(
        settings.paths.baseline_report,
        {
            "source": settings.source_api,
            "raw_records": len(records),
            "clean_records": len(clean_df),
            "embedding_model": settings.embedding_model,
        },
        evaluation.summary,
        quality,
        freshness,
    )

    demo_answers = []
    for item in test_set[:3]:
        result = answer_question(item["question"], settings, index)
        demo_answers.append(asdict(result))
    write_json(settings.paths.demo_answers, demo_answers)
    print(
        "Baseline complete: "
        f"{len(clean_df)} documents, {len(test_set)} questions, "
        f"hit_rate={evaluation.summary['retrieval_hit_rate']:.4f}, "
        f"quality={'PASS' if quality['success'] else 'FAIL'}"
    )
