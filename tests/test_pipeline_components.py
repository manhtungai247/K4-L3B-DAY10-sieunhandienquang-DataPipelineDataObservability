from __future__ import annotations

import json
from datetime import UTC, datetime

from core.config import load_settings
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import parse_crossref_payload


def _clean_dataframe():
    settings = load_settings()
    payload = json.loads(settings.paths.raw_api_response.read_text(encoding="utf-8"))
    records = parse_crossref_payload(payload)
    return build_clean_dataframe(records, datetime(2026, 9, 26, tzinfo=UTC))


def test_snapshot_parses_and_cleans_24_unique_records() -> None:
    dataframe = _clean_dataframe()
    assert len(dataframe) == 24
    assert dataframe["paper_id"].is_unique
    assert dataframe["text_for_embedding"].str.contains("Title:").all()
    assert dataframe["text_for_embedding"].str.contains("Published:").all()


def test_test_set_has_ten_questions_across_four_types(tmp_path) -> None:
    test_set = build_test_set(_clean_dataframe(), tmp_path / "test_set.json")
    assert len(test_set) == 10
    assert {item["question_type"] for item in test_set} == {
        "summary",
        "authors",
        "date",
        "categories",
    }
    assert all(item["ground_truth_doc_ids"] for item in test_set)


def test_corruption_is_deterministic_and_logs_six_types(tmp_path) -> None:
    clean = _clean_dataframe()
    first = corrupt_clean_dataframe(clean, tmp_path / "first.json")
    second = corrupt_clean_dataframe(clean, tmp_path / "second.json")
    assert first.to_dict(orient="records") == second.to_dict(orient="records")
    payload = json.loads((tmp_path / "first.json").read_text(encoding="utf-8"))
    assert len(payload["corruptions"]) == 6
    assert not first["paper_id"].is_unique
    assert (first["summary"] == "").any()
    assert (first["age_days"] > 180).mean() > 0.25
