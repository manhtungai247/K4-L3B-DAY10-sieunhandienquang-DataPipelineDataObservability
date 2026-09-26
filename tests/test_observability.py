from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from core.config import load_settings
from evaluation.testset import build_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


@pytest.fixture
def sample_clean_df() -> pd.DataFrame:
    settings = load_settings()
    raw_path = settings.paths.raw_records_json
    records = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = []
    for r in records:
        authors_joined = ", ".join(r["authors"])
        categories_joined = ", ".join(r["categories"])
        text = (
            f"Title: {r['title']}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {r['published']}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {r['summary']}"
        )
        rows.append(
            {
                "paper_id": r["paper_id"],
                "title": r["title"],
                "summary": r["summary"],
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "published": r["published"],
                "age_days": 30,
                "text_for_embedding": text,
                "abs_url": r.get("abs_url", ""),
                "pdf_url": r.get("pdf_url", ""),
            }
        )
    return pd.DataFrame(rows)


def test_testset_has_ten_questions_across_four_types(
    sample_clean_df: pd.DataFrame, tmp_path: Path
) -> None:
    output_path = tmp_path / "test_set.json"
    test_set = build_test_set(sample_clean_df, output_path)

    assert len(test_set) == 10
    question_types = {item["question_type"] for item in test_set}
    assert question_types == {"summary", "authors", "date", "categories"}

    for item in test_set:
        assert item["id"]
        assert item["question"]
        assert item["ground_truth"]
        assert len(item["ground_truth_doc_ids"]) == 1

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(saved) == 10


def test_baseline_dataframe_passes_quality_gate(
    sample_clean_df: pd.DataFrame,
) -> None:
    settings = load_settings()
    result = run_data_quality_checks(sample_clean_df, settings, "test_baseline")

    assert result["success"] is True
    assert result["gx_success"] is True
    assert result["freshness"]["success"] is True
    assert (
        settings.paths.quality_dir / "test_baseline_quality_report.json"
    ).exists()


def test_duplicate_or_blank_summary_fails_quality_gate(
    sample_clean_df: pd.DataFrame,
) -> None:
    settings = load_settings()

    # Case 1: duplicate paper_id
    dup_df = sample_clean_df.copy()
    dup_df.loc[1, "paper_id"] = dup_df.loc[0, "paper_id"]
    dup_result = run_data_quality_checks(dup_df, settings, "test_duplicate")
    assert dup_result["success"] is False
    assert dup_result["gx_success"] is False

    # Case 2: blank summary
    blank_df = sample_clean_df.copy()
    blank_df.loc[0, "summary"] = ""
    blank_result = run_data_quality_checks(blank_df, settings, "test_blank")
    assert blank_result["success"] is False
    assert blank_result["gx_success"] is False


def test_freshness_fails_when_stale_ratio_exceeds_threshold(
    sample_clean_df: pd.DataFrame, tmp_path: Path
) -> None:
    settings = load_settings()
    stale_df = sample_clean_df.copy()

    # Set > 25% of records to exceed 180 days (stale)
    stale_count = int(len(stale_df) * 0.35)
    stale_df.loc[:stale_count, "age_days"] = 250

    result = run_data_quality_checks(stale_df, settings, "test_stale")
    assert result["freshness"]["stale_ratio"] > 0.25
    assert result["freshness"]["success"] is False
    assert result["success"] is False

    report = build_freshness_report(
        stale_df, settings, tmp_path / "freshness_report.json"
    )
    assert report["is_fresh"] is False
    assert report["stale_ratio"] > 0.25


def test_chroma_manifest_uses_relative_path(
    sample_clean_df: pd.DataFrame, tmp_path: Path
) -> None:
    settings = load_settings()

    # Verify collection name isolation
    assert (
        LocalEmbeddingIndex._derive_collection_name(
            settings, settings.paths.embeddings_json
        )
        == settings.baseline_collection_name
    )
    assert (
        LocalEmbeddingIndex._derive_collection_name(
            settings, settings.paths.corrupted_embeddings_json
        )
        == settings.corrupted_collection_name
    )
    assert (
        LocalEmbeddingIndex._derive_collection_name(
            settings, settings.paths.repaired_embeddings_json
        )
        == settings.repaired_collection_name
    )

    # Build index to a temporary manifest path
    manifest_path = tmp_path / "papers_embeddings_test.json"
    LocalEmbeddingIndex.build(
        sample_clean_df.head(5), settings, embeddings_output_path=manifest_path
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert not Path(manifest["persist_path"]).is_absolute()
    assert manifest["persist_path"] == "data/chroma"
    assert "C:" not in manifest["persist_path"]
    assert "D:" not in manifest["persist_path"]

    # Verify loading works across environments using relative persist_path
    loaded_index = LocalEmbeddingIndex.load(
        settings, embeddings_path=manifest_path
    )
    assert loaded_index.collection_name == manifest["collection_name"]
    assert len(loaded_index.documents) == 5


def test_reports_generated_from_provided_metrics(tmp_path: Path) -> None:
    phase1_path = tmp_path / "phase1_report.md"
    generate_phase1_report(
        report_path=phase1_path,
        source_summary={
            "source": "Crossref",
            "raw_records": 24,
            "clean_records": 24,
            "embedding_model": "all-MiniLM-L6-v2",
        },
        metrics={
            "samples": 10,
            "retrieval_hit_rate": 0.8888,
            "mean_token_f1": 0.7777,
            "judge_accuracy": 0.9000,
            "mean_judge_score": 4.5,
        },
        quality={"gx_success": True, "success": True},
        freshness={
            "is_fresh": True,
            "stale_rows": 1,
            "total_rows": 24,
            "threshold_days": 180,
        },
    )
    phase1_text = phase1_path.read_text(encoding="utf-8")
    assert "0.8888" in phase1_text
    assert "0.7777" in phase1_text
    assert "**PASS**" in phase1_text

    corruption_path = tmp_path / "corruption_report.md"
    generate_corruption_report(
        report_path=corruption_path,
        baseline_metrics={"retrieval_hit_rate": 0.9000, "mean_token_f1": 0.8000},
        corrupted_metrics={"retrieval_hit_rate": 0.4000, "mean_token_f1": 0.3500},
        repaired_metrics={"retrieval_hit_rate": 0.9000, "mean_token_f1": 0.8000},
        baseline_quality={"success": True},
        corrupted_quality={"success": False},
        repaired_quality={"success": True},
        baseline_freshness={"is_fresh": True, "stale_ratio": 0.04},
        corrupted_freshness={"is_fresh": False, "stale_ratio": 0.33},
        repaired_freshness={"is_fresh": True, "stale_ratio": 0.04},
    )
    corruption_text = corruption_path.read_text(encoding="utf-8")
    assert "0.9000" in corruption_text
    assert "0.4000" in corruption_text
    assert "| Quality gate | PASS | FAIL | PASS |" in corruption_text
    assert "| Freshness SLA | PASS | FAIL | PASS |" in corruption_text
