# Báo cáo cá nhân — Nguyễn Hồng Thái

| Mục | Nội dung |
| --- | --- |
| MSSV | 2A202602894 |
| Lớp | K4-L3B |
| Nhóm | sieunhandienquang |
| Vai trò | Trưởng nhóm, Pipeline Integrator |
| Ngày | 2026-09-26 |

## Phạm vi

Tích hợp hai entrypoint `phase1.py` và `corruption_flow.py`; kiểm tra contract giữa
ingestion, cleaning, ChromaDB, evaluation và observability; xác minh artifact ba trạng
thái. Output chính là pipeline chạy end-to-end và báo cáo so sánh tự sinh.

## Quyết định kỹ thuật

Repair luôn dựng lại canonical dataframe từ raw snapshot thay vì đảo ngược từng lỗi.
Cách này đơn giản hơn, tái lập được và idempotent: chạy repair nhiều lần vẫn tạo cùng
24 record và metric. Baseline, corrupted và repaired dùng chung test set nên mức suy
giảm không bị nhiễu bởi thay đổi câu hỏi.

Quality checks kiểm tra tính hợp lệ của từng batch (row count, null, unique, độ dài),
trong khi freshness theo dõi tuổi dữ liệu và tỷ lệ stale. Corruption làm quality gate
thất bại và tăng stale ratio từ 0.0417 lên 0.3333; repair đưa cả hai về baseline.

## Sự cố đã xử lý

Great Expectations báo thiếu module dù file đã cài. Đường dẫn module dài đúng 260 ký tự,
chạm giới hạn `MAX_PATH` của Windows. Giải pháp là đặt môi trường uv tại
`%USERPROFILE%\venvs\day10` và pin Great Expectations 1.16.1. Import và GX suite sau đó
chạy thành công.

## Kết quả xác minh

| Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.5000 | 1.0000 |
| Mean token F1 | 1.0000 | 0.5788 | 1.0000 |
| Judge accuracy | 1.0000 | 0.7000 | 1.0000 |
| Quality | PASS | FAIL | PASS |
| Freshness | PASS | FAIL | PASS |

Lệnh kiểm tra:

```powershell
uv run python -m pytest -q
uv run python script\run_phase1.py
uv run python script\run_corruption_flow.py
```

Điều học được chính: raw lineage là điều kiện để self-healing đáng tin cậy; quality gate
phải chạy trước serving; và retrieval metric có thể giảm mạnh dù pipeline vẫn chạy không lỗi.
