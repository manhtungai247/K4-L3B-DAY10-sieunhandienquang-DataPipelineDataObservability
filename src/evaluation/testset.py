from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic 10-question benchmark spanning four task types."""
    if len(df) < 10:
        raise ValueError(
            "At least 10 clean documents are required to build the test set."
        )
    selected = df.sort_values(["published", "paper_id"], ascending=[False, True]).head(
        10
    )
    question_types = [
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
    ]
    test_set: list[dict[str, Any]] = []
    for number, ((_, row), question_type) in enumerate(
        zip(selected.iterrows(), question_types, strict=True), 1
    ):
        title = str(row["title"])
        if question_type == "summary":
            question = f"What is the main contribution of '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif question_type == "authors":
            question = f"Who authored '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif question_type == "date":
            question = f"When was '{title}' published?"
            ground_truth = str(row["published"])
        else:
            question = f"What categories are assigned to '{title}'?"
            ground_truth = str(row["categories_joined"])
        test_set.append(
            {
                "id": f"q{number:02d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )
    write_json(output_path, test_set)
    return test_set
