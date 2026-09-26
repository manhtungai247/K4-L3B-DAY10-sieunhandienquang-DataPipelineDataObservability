# Báo cáo nhóm — Day 10 Data Pipeline & Data Observability

## 1. Thông tin

| Mục | Nội dung |
| --- | --- |
| Lớp | K4-L3B |
| Nhóm | sieunhandienquang |
| Repository | `manhtungai247/K4-L3B-DAY10-sieunhandienquang-DataPipelineDataObservability` |
| Ngày hoàn thành | 2026-09-26 |

Thành viên: Nguyễn Hồng Thái (2A202602894), Trần Mạnh Tùng (2A202602879),
Nguyễn Mạnh Cường (2A202602650). Phân công chi tiết nằm trong `docs/TEAM.md`.

## 2. Kiến trúc và kết quả

```text
Crossref snapshot/API → raw records → cleaning → GX + freshness gate
→ MiniLM embeddings → ChromaDB → evaluation
→ six corruptions → re-evaluation → repair from trusted raw → comparison
```

Pipeline parse và làm sạch 24 bài báo, tạo test set cố định gồm 10 câu thuộc bốn
nhóm summary, authors, date và categories. Ba collection ChromaDB tách biệt dữ liệu
baseline, corrupted và repaired để tránh lẫn trạng thái.

| Metric/signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.5000 | 1.0000 |
| Mean token F1 | 1.0000 | 0.5788 | 1.0000 |
| Judge accuracy | 1.0000 | 0.7000 | 1.0000 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |
| Stale ratio | 0.0417 | 0.3333 | 0.0417 |

Sáu lỗi được tiêm gồm mất 20% bản ghi mới, summary rỗng, noise, title bị cắt,
ngày xuất bản cũ và bản ghi trùng. Việc mất các tài liệu mới làm hit rate giảm 0.5;
summary lỗi làm token F1 giảm còn 0.5788. Repair không sửa trực tiếp dataframe lỗi mà
dựng lại từ `data/raw/crossref_records.json`, vì vậy có tính idempotent và khôi phục
toàn bộ metric cùng quality/freshness signals.

## 3. Tái hiện

```powershell
$env:UV_PROJECT_ENVIRONMENT="$env:USERPROFILE\venvs\day10"
uv sync --extra dev
uv run python -m pytest -q
uv run python script\run_phase1.py
uv run python script\run_corruption_flow.py
```

Trên Windows, virtual environment dùng đường dẫn ngắn để tránh `MAX_PATH` khi import
Great Expectations. Model embedding là `sentence-transformers/all-MiniLM-L6-v2`,
`top_k=4`, freshness threshold 180 ngày và stale-ratio limit 25%.

## 4. Artifacts

- Raw lineage: `data/raw/`
- Clean/corrupted/repaired datasets: `data/clean/`
- Test set và metrics: `data/eval/`, `data/results/`
- GX/freshness evidence: `data/quality/`
- Báo cáo sinh tự động: `data/reports/`

Giới hạn: tập dữ liệu chỉ có 24 bản ghi và test set 10 câu; kết quả chứng minh luồng
observability/repair nhưng chưa đại diện cho tải production lớn hoặc concept drift dài hạn.
