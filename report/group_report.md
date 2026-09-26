# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 - L3B (VinUni AI20k) |
| Tên nhóm | sieunhandienquang |
| Repository | https://github.com/manhtungai247/K4-L3B-DAY10-sieunhandienquang-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Hồng Thái | 2A202602894 | Trưởng nhóm / Pipeline Integrator | `core/config.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| 2 | Trần Mạnh Tùng | 2A202602879 | Data Foundation & Recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` |
| 3 | Nguyễn Mạnh Cường | 2A202602650 | Observability, Evaluation & Vector Index | `src/observability/quality.py`, `src/evaluation/testset.py`, `src/retrieval/index.py` |

---

## 2. Tóm tắt kết quả

Nhóm đã xây dựng và tích hợp thành công toàn bộ đường ống dữ liệu (Data Pipeline) chuẩn mực cho AI: từ khâu thu thập metadata Crossref, làm sạch dữ liệu, kiểm soát chất lượng qua Great Expectations 1.x đến nạp ChromaDB và đánh giá RAG Agent.

Trong pha Baseline, hệ thống tải và xử lý 24 bài báo học thuật, đạt tuyệt đối **Hit Rate 1.0000** và **Mean Token F1 1.0000**, vượt qua toàn bộ 4 chốt kiểm định chất lượng và Freshness SLA. Khi kích hoạt bộ tiêm lỗi thực nghiệm (Synthetic Corruption) gồm 6 kịch bản, hiện tượng **Silent Failure** xuất hiện rõ rệt: Great Expectations lập tức báo động đỏ `FAIL` (phát hiện 4 bản ghi trùng lặp và 4 tóm tắt rỗng), tỷ lệ bài báo cũ nhảy vọt lên 50% (`stale_ratio = 0.5000`), kéo tụt Retrieval Hit Rate xuống còn **0.6000** và Token F1 còn **0.5741**.

Nhóm đã kích hoạt cơ chế phục hồi tự động an toàn (**Idempotent Repair**) từ snapshot dữ liệu thô ban đầu `data/raw/crossref_records.json`. Quá trình tái cấu trúc dữ liệu và đánh chỉ mục vector mới đã khôi phục hoàn toàn 100% chất lượng phục vụ của AI (Hit Rate 1.0000, Token F1 1.0000), chứng minh năng lực tự phục hồi mà không cần can thiệp thủ công.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API (Offline Snapshot Fallback)
    -> data/raw/ (crossref_response.json, crossref_records.json) [Data Lineage]
    -> Ingestion & Cleaning (Chuẩn hóa XML, tính age_days, ghép text_for_embedding)
    -> Data Observability Gate (GX 1.x Ephemeral Context + Freshness SLA)
    -> Embedding (all-MiniLM-L6-v2) -> ChromaDB Index (papers-baseline)
    -> Evaluation Baseline (10 deterministic benchmark questions) -> data/reports/phase1_report.md
    -> Synthetic Corruption Suite (Tiêm 6 kịch bản lỗi) -> data/results/corruption_log.json
    -> Re-index ChromaDB (papers-corrupted) -> Đo lường Silent Failure
    -> Idempotent Repair (Tái nạp từ raw snapshot) -> ChromaDB (papers-repaired)
    -> Comparison Report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API / Snapshot | Fetch metadata, retry 429/503, fallback snapshot | `data/raw/crossref_response.json`, `crossref_records.json` | Trần Mạnh Tùng |
| Cleaning | Raw `PaperRecord` | Bóc XML/JATS, khử trùng lặp `paper_id`, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Trần Mạnh Tùng |
| Embedding & Index | Clean DataFrame | Vectorize 384-dim (MiniLM), cô lập 3 collections ChromaDB, lưu manifest relative | `data/chroma/`, `data/embeddings/*.json` | Nguyễn Mạnh Cường |
| Observability | Clean / Corrupted DF | Chốt kiểm soát 4 GX expectations + Giám sát Freshness SLA (ngưỡng 180 ngày) | `data/quality/*_quality_report.json`, `freshness_report.json` | Nguyễn Mạnh Cường |
| Evaluation | Clean / Corrupted DF | Sinh test set 10 câu qua 4 dạng bài; tính Hit Rate, Token F1, LLM Judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Nguyễn Mạnh Cường |
| Corruption & Repair | Clean DataFrame | Tiêm 6 dạng lỗi thực nghiệm; thực thi Idempotent Repair từ raw snapshot | `data/results/corruption_log.json`, `papers_clean_repaired.csv` | Tùng & Thái |
| Orchestration | Cấu hình Settings | Điều phối toàn tuyến Phase 1 và Corruption Flow; sinh báo cáo đối chiếu | `data/reports/phase1_report.md`, `corruption_report.md` | Nguyễn Hồng Thái |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `mock` (hoặc `gemini` khi chạy live API) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 bài báo |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày (tỷ lệ cũ tối đa 25%) |
| Collection Names | `papers-baseline`, `papers-corrupted`, `papers-repaired` |

### Lệnh cài đặt

```powershell
$env:UV_PROJECT_ENVIRONMENT="$env:USERPROFILE\venvs\day10"
uv sync --extra dev
```

### Lệnh chạy

1. **Chạy kiểm thử tự động:**
   ```powershell
   uv run python -m pytest -q
   ```
2. **Chạy toàn tuyến Pha 1 (Baseline):**
   ```powershell
   uv run python script/run_phase1.py
   ```
3. **Chạy toàn tuyến Pha 2 (Corruption -> Repair -> Đối chiếu):**
   ```powershell
   uv run python script/run_corruption_flow.py
   ```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Pytest Test Suite | Thành công (12/12 passed) | 2026-09-26 11:20 | `tests/test_observability.py`, `tests/test_ingestion.py` |
| Baseline pipeline | Thành công (Exit code 0) | 2026-09-26 11:22 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công (Exit code 0) | 2026-09-26 11:25 | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API công khai (`https://api.crossref.org/works`) |
| Query/filter | `query=agentic retrieval augmented generation large language model`, `has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-26 (Bảo toàn bản sao thô tại `data/raw/`) |
| Số record nhận được | 24 bài báo |
| Cơ chế retry/backoff | Retry tự động với mã lỗi 429/503; tự động kích hoạt Offline Fallback đọc snapshot mẫu khi mất mạng |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | `str` | Có | Định danh DOI duy nhất của bài báo | Loại bỏ bản ghi nếu rỗng hoặc trùng |
| `title` | `str` | Có | Tiêu đề công trình khoa học | Trim khoảng trắng; cảnh báo nếu độ dài < 8 ký tự |
| `summary` | `str` | Có | Tóm tắt (Abstract) bài báo | Lọc bỏ thẻ JATS XML `<jats:p>`; bắt buộc độ dài >= 20 ký tự |
| `authors_joined` | `str` | Có | Danh sách tác giả ghép chuỗi phẩy | Chuẩn hóa danh sách, thay thế bằng `"Unknown"` nếu rỗng |
| `categories_joined`| `str` | Có | Chuyên mục khoa học gán nhãn | Ghép chuỗi phân tách bởi dấu phẩy |
| `published` | `str` | Có | Ngày công bố theo định dạng ISO | Parse `YYYY-MM-DD`, fallback về ngày hiện tại nếu lỗi |
| `age_days` | `int` | Có | Số ngày tuổi từ ngày công bố đến `run_date` | `age_days = (run_date - published).days` |
| `text_for_embedding`| `str` | Có | Đoạn văn bản hoàn chỉnh 5 thành phần để embed | Ghép tuần tự: Title, Authors, Published, Categories, Summary |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Bóc tách và xóa thẻ `<jats:p>` | Validity / Conformance | 24 | Regex làm sạch văn bản, kiểm tra không còn ký tự HTML/XML |
| Khử trùng lặp khóa chính `paper_id` | Uniqueness | 0 (tập sạch) / 2 (tập lỗi) | `ExpectColumnValuesToBeUnique` |
| Tính toán độ tuổi `age_days` | Timeliness / Currency | 24 | So sánh với `run_date` (UTC) |
| Định dạng 5 thành phần `text_for_embedding` | Completeness | 24 | Kiểm tra chuỗi chứa đủ tiền tố `Title:`, `Authors:`, `Published:` |

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 câu hỏi chuẩn hóa |
| Các `question_type` | Đủ 4 dạng: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID | Trích xuất trực tiếp DOI từ bài báo đại diện |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | `mock` / `gemini-2.5-flash` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (SHA-256 hash cố định) |

**Lý do giữ nguyên Test Set cho 3 trạng thái:** Test set đóng vai trò là "thước đo đối chứng" (Control Benchmark). Nếu thay đổi câu hỏi qua các pha, điểm số biến động sẽ do độ khó của câu hỏi thay vì do chất lượng dữ liệu. Giữ cố định test set giúp cô lập hoàn toàn tác động của sự cố dữ liệu.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/crossref_response.json`, `crossref_records.json` | Có | Đầy đủ 24 bản ghi gốc phục vụ lineage |
| Cleaned dataset | `data/clean/papers_clean.csv`, `papers_clean.json` | Có | Dữ liệu sạch 24 dòng chuẩn schema |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Manifest lưu đường dẫn tương đối `data/chroma` |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi deterministic phủ đủ 4 nhóm |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Điểm số tuyệt đối Hit Rate 1.0, Token F1 1.0 |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Có | GX 1.x `success=True`, Freshness `is_fresh=True` |
| Baseline report | `data/reports/phase1_report.md` | Có | Báo cáo Markdown sinh tự động từ artifacts |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 100% câu hỏi đều truy xuất chính xác tài liệu chứa đáp án trong Top-4 |
| `mean_token_f1` | 1.0000 | Trích xuất chuẩn xác từng từ khóa đáp án từ ngữ cảnh sạch |
| `judge_accuracy` | 1.0000 | LLM Judge đánh giá câu trả lời hoàn toàn chính xác về mặt ngữ nghĩa |
| `mean_judge_score` | 5.0000 | Điểm tuyệt đối 5/5 trên toàn bộ tập benchmark |
| Ragas, nếu có | N/A | Được bỏ qua (mặc định) để tăng tốc độ thực thi bài lab |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `ExpectTableRowCountToBeBetween` | Completeness | [18, 29] dòng | PASS (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` | Completeness | Cột `paper_id` không null | PASS (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` | Uniqueness | Cột `paper_id` là duy nhất | PASS (0 trùng lặp) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` | Validity | Cột `summary` độ dài >= 20 ký tự | PASS (0 dòng rỗng) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Cột `age_days` trong `data/clean/papers_clean.csv` |
| Timestamp mới nhất | Ngày xuất bản bài báo gần nhất (2026) |
| Ngưỡng freshness | 180 ngày (cho phép tối đa 25% bài báo cũ) |
| Trạng thái baseline | **PASS** (`is_fresh = True`) |
| Lý do | Chỉ có 1 bài báo cũ quá 180 ngày (`stale_ratio = 1/24 = 4.17% <= 25%`) |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| `drop_latest_records` | Loại bỏ 4 bài báo mới nhất | 4 | Cảnh báo thiếu hụt dữ liệu mới | Hit rate sụt giảm còn 0.6 | Nạp lại từ `data/raw/` |
| `blank_summary` | Xóa trắng abstract/summary | 2 | `ExpectColumnValueLengthsToBeBetween` FAIL | Token F1 giảm mạnh | Tái tạo lại từ snapshot |
| `inject_noise` | Chèn chuỗi ký tự rác vào text | 2 | Khoảng cách vector embedding bị trôi lệch | Điểm tương đồng giảm | Nạp lại chuỗi gốc |
| `truncate_title` | Cắt ngắn tiêu đề xuống < 8 ký tự | 2 | Lỗi lookup metadata chính xác | LLM trả lời cụt lủn | Tái tạo lại từ snapshot |
| `stale_date` | Lùi ngày xuất bản về năm 2020 | 8 | Freshness SLA FAIL (stale ratio = 50%) | Đánh mất độ tươi mới tri thức | Tính lại ngày gốc |
| `duplicate_rows` | Nhân đôi 2 bài báo | 2 | `ExpectColumnValuesToBeUnique` FAIL | Index trùng lặp vector rác | Khử trùng lặp theo ID |

**Corruption log:** Lưu tại `data/results/corruption_log.json` (ghi nhận đầy đủ thông tin mã bài báo và thuộc tính bị biến đổi).

**Cơ chế Idempotent Repair:** Hệ thống không thực hiện "chắp vá" trên DataFrame bị lỗi mà loại bỏ hoàn toàn tập dữ liệu bẩn, sau đó tải lại từ đầu từ nguồn `data/raw/crossref_records.json` đáng tin cậy. Quá trình này đảm bảo tính Idempotent: chạy bao nhiêu lần cũng cho ra cùng một trạng thái sạch duy nhất.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | -0.4000 | +0.4000 | Giảm mạnh do mất bài báo mới và tiêu đề bị cắt; phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 1.0000 | 0.5741 | 1.0000 | -0.4259 | +0.4259 | Abstract bị xóa/nhiễu làm AI mất từ khóa quan trọng; phục hồi 100% |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | -0.4000 | +0.4000 | Tỷ lệ trả lời đúng giảm sút do thiếu ngữ cảnh |
| `mean_judge_score` | 5.0000 | 3.4000 | 5.0000 | -1.6000 | +1.6000 | Điểm đánh giá sụp đổ từ 5.0 xuống 3.4 thể hiện rõ Silent Failure |
| Quality checks pass/fail | **PASS** | **FAIL** | **PASS** | Báo động đỏ | Phục hồi xanh | Bắt trúng 4 dòng duplicate ID và 4 dòng rỗng summary |
| Freshness status | **PASS** | **FAIL** | **PASS** | Vi phạm SLA | Đạt chuẩn | Stale ratio nhảy từ 4.17% lên 50.00% rồi trở về 4.17% |

### Hai chuỗi nhân quả cốt lõi (Causality chains):
1. **Chuỗi 1 (Corruption Impact):** Tiêm lỗi xóa summary và cắt title ➔ Great Expectations báo `FAIL` và Vector embedding bị sai lệch ➔ Retrieval Hit Rate giảm từ 1.0 xuống 0.6000, kéo theo Token F1 sụt đổ xuống 0.5741 (Silent Failure).
2. **Chuỗi 2 (Repair Recovery):** Kích hoạt Idempotent Repair từ snapshot thô `crossref_records.json` ➔ Dữ liệu sạch được làm mới, Quality Gate và Freshness SLA quay lại trạng thái `PASS` ➔ Vector Index được tạo mới, đưa Hit Rate và Token F1 phục hồi hoàn hảo về mốc 1.0000.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy `uv sync` và import `great_expectations` trên Windows, chương trình báo lỗi giới hạn độ dài đường dẫn `MAX_PATH` (> 260 ký tự) và phát sinh cảnh báo linting `BLE001` (bắt exception trần trong Chroma index).
- **Nguyên nhân gốc:** Thư viện `great-expectations` phiên bản 1.18 có dependency chain lồng nhau quá sâu trong cache Windows; đồng thời khối xóa collection cũ dùng lệnh `try ... except Exception: pass`.
- **Cách xử lý:** 
  1. Pin cố định `great-expectations==1.16.1` trong `pyproject.toml` và chuyển virtual environment về thư mục ngắn: `$env:UV_PROJECT_ENVIRONMENT="$env:USERPROFILE\venvs\day10"`.
  2. Dùng `contextlib.suppress(Exception)` và bổ sung `__all__` đầy đủ trong `src/observability/__init__.py`.
- **Cách xác minh:** Chạy `uvx ruff check` báo `All checks passed!` và `pytest` chạy thông suốt 12/12 test cases.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Tập dữ liệu nhỏ (24 bài báo) | Chưa phản ánh hết tải trọng và sự phân tán của môi trường production lớn | Mở rộng ingest lên 1.000+ bài báo và áp dụng kỹ thuật batch indexing |
| Chế độ đánh giá LLM mock | Chưa đo lường được chi phí độ trễ (latency) và token inference thực tế | Kết nối live Gemini/Groq API kèm cơ chế exponential backoff và rate limiter |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (`report/2A202602650_NguyenManhCuong.md`, `NguyenHongThai_2A202602894.md`, `TranManhTung_2A202602879.md`).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
