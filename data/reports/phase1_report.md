# Phase 1 — Baseline Data Pipeline

## Source and lineage

- Source: Crossref REST API
- Raw records: 24
- Clean records: 24
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

## Evaluation

| Metric | Value |
| --- | ---: |
| Samples | 10 |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 1.0000 |
| Judge accuracy | 1.0000 |
| Mean judge score | 5.0000 |

## Data observability

- Great Expectations suite: **PASS**
- Overall quality gate: **PASS**
- Freshness SLA: **PASS**
- Stale rows: 1/24
- Freshness threshold: 180 days

This report is generated from the pipeline artifacts; values are not entered manually.
