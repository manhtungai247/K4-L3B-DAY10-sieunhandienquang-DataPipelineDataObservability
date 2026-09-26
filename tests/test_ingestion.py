from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
import pandas as pd

from core.config import load_settings
from core.utils import read_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records, parse_crossref_payload


class TestDataFoundationAndRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.now = datetime(2026, 9, 26, tzinfo=UTC)
        cls.test_scratch_dir = cls.settings.paths.project_dir / "data" / "quality"
        cls.test_scratch_dir.mkdir(parents=True, exist_ok=True)

    def test_01_snapshot_parse_24_records(self):
        """Verify snapshot offline parses exactly 24 records with valid schema."""
        payload = read_json(self.settings.paths.raw_api_response)
        records = parse_crossref_payload(payload)
        self.assertEqual(len(records), 24, "Snapshot must parse exactly 24 records")
        for r in records:
            self.assertTrue(r.paper_id, "paper_id must not be empty")
            self.assertTrue(r.title, "title must not be empty")
            self.assertTrue(r.summary, "summary must not be empty")
            self.assertNotIn("<jats:", r.summary, "JATS XML tags must be stripped from summary")
            self.assertTrue(r.published, "published date must be formatted")

    def test_02_clean_dataframe_24_unique_rows(self):
        """Verify cleaned dataframe has 24 unique rows and valid age_days."""
        raw_records = load_raw_records(self.settings.paths.raw_records_json)
        df = build_clean_dataframe(raw_records, self.now)
        self.assertEqual(len(df), 24, "Clean dataframe must have 24 rows")
        self.assertEqual(df["paper_id"].nunique(), 24, "All paper_ids must be unique")
        self.assertIn("age_days", df.columns)
        self.assertTrue((df["age_days"] >= 0).all(), "age_days must be non-negative")

    def test_03_text_for_embedding_structure(self):
        """Verify text_for_embedding contains all 5 required parts: Title, Summary, Authors, Categories, Published."""
        raw_records = load_raw_records(self.settings.paths.raw_records_json)
        df = build_clean_dataframe(raw_records, self.now)
        for _, row in df.iterrows():
            text = row["text_for_embedding"]
            self.assertIn("Title:", text)
            self.assertIn("Summary:", text)
            self.assertIn("Authors:", text)
            self.assertIn("Categories:", text)
            self.assertIn("Published:", text)

    def test_04_corruption_deterministic(self):
        """Verify running corruption twice produces identical deterministic results."""
        raw_records = load_raw_records(self.settings.paths.raw_records_json)
        df_clean = build_clean_dataframe(raw_records, self.now)

        log1_path = self.test_scratch_dir / "test_ingestion_log1.json"
        log2_path = self.test_scratch_dir / "test_ingestion_log2.json"

        corrupted_1 = corrupt_clean_dataframe(df_clean, log1_path)
        corrupted_2 = corrupt_clean_dataframe(df_clean, log2_path)

        pd.testing.assert_frame_equal(corrupted_1, corrupted_2)
        self.assertEqual(read_json(log1_path), read_json(log2_path))

    def test_05_corruption_log_records_6_scenarios(self):
        """Verify corruption log captures all 6 error scenarios with affected paper IDs."""
        raw_records = load_raw_records(self.settings.paths.raw_records_json)
        df_clean = build_clean_dataframe(raw_records, self.now)
        log_path = self.test_scratch_dir / "test_ingestion_log.json"

        corrupt_clean_dataframe(df_clean, log_path)
        logs = read_json(log_path)
        self.assertEqual(len(logs), 6, "Must record all 6 corruption scenarios")

        recorded_types = {entry["corruption_type"] for entry in logs}
        expected_types = {
            "drop_latest_records",
            "blank_summary",
            "inject_noise",
            "truncate_title",
            "stale_date",
            "duplicate_rows",
        }
        self.assertEqual(recorded_types, expected_types)

        for entry in logs:
            self.assertIn("affected_papers", entry)
            self.assertGreater(len(entry["affected_papers"]), 0)

    def test_06_corrupted_data_properties(self):
        """Verify corrupted data contains empty summary, duplicate IDs, and stale ratio > 25%."""
        raw_records = load_raw_records(self.settings.paths.raw_records_json)
        df_clean = build_clean_dataframe(raw_records, self.now)
        log_path = self.test_scratch_dir / "test_ingestion_log.json"

        corrupted = corrupt_clean_dataframe(df_clean, log_path)

        # 1. Summary rỗng
        has_blank_summary = (corrupted["summary"] == "").any()
        self.assertTrue(has_blank_summary, "Must have rows with blank summary")

        # 2. Duplicate ID
        has_duplicate_id = corrupted["paper_id"].duplicated().any()
        self.assertTrue(has_duplicate_id, "Must have duplicate paper_id")

        # 3. Stale ratio > 25% (ngưỡng 180 ngày)
        stale_count = (corrupted["age_days"] > 180).sum()
        stale_ratio = stale_count / len(corrupted)
        self.assertGreater(stale_ratio, 0.25, f"Stale ratio {stale_ratio} must exceed 25%")


if __name__ == "__main__":
    unittest.main()
