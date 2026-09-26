# Corruption and Idempotent Repair Report

## Three-state comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.6000 | 1.0000 |
| Mean token F1 | 1.0000 | 0.5741 | 1.0000 |
| Judge accuracy | 1.0000 | 0.6000 | 1.0000 |
| Mean judge score | 5.0000 | 3.4000 | 5.0000 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |

## Observed impact

- Corruption changed retrieval hit rate by **-0.4000** relative to baseline.
- Rebuilding from the trusted raw snapshot recovered **+0.4000**
  hit-rate points.
- Corrupted quality checks failed because the suite injects missing summaries,
  duplicate IDs,
  truncated titles, stale dates, noisy text, and dropped records.
- Repair is idempotent: it discards the corrupted dataframe and rebuilds the
  canonical clean
  dataset from `data/raw/crossref_records.json`, then recreates the vector index.

## Freshness evidence

- Baseline stale ratio: 0.0417
- Corrupted stale ratio: 0.5000
- Repaired stale ratio: 0.0417

All values in this report are generated from pipeline artifacts.
