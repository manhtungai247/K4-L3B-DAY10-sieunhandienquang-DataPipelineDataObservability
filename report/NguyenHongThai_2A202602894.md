# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hồng Thái |
| MSSV | 2A202602894 |
| Khóa/Lớp | K4 - L3B (VinUni AI20k) |
| Tên nhóm | sieunhandienquang |
| Vai trò chính | Trưởng nhóm, Pipeline Integrator & Orchestrator |
| Repository | https://github.com/manhtungai247/K4-L3B-DAY10-sieunhandienquang-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Pipeline Settings & Paths** | `src/core/config.py`<br>- `load_settings`<br>- `require_llm_credentials` | File `.env`, biến môi trường hệ thống | Đối tượng `Settings` chứa toàn bộ đường dẫn artifacts và cấu hình | Hoàn thành |
| **Baseline Orchestration (Pha 1)** | `src/pipelines/phase1.py`<br>`script/run_phase1.py` | Settings, Ingestion data, Chroma index | Pipeline chạy end-to-end; sinh `baseline_metrics.json` và `phase1_report.md` | Hoàn thành |
| **Corruption & Self-Healing Flow (Pha 2)** | `src/pipelines/corruption_flow.py`<br>`script/run_corruption_flow.py` | Baseline metrics, corrupted data, raw snapshot | Luồng tiêm lỗi, đo suy giảm, phục hồi an toàn và sinh `corruption_report.md` | Hoàn thành |
| **Integration & Verification** | Toàn bộ dự án | Mã nguồn và tests của cả nhóm | 12/12 unit tests passed, bảng đối chiếu 3 trạng thái hoàn chỉnh | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Khắc phục lỗi Windows MAX_PATH** | Toàn nhóm (Cường, Tùng) | Hướng dẫn cấu hình đường dẫn ngắn `$env:UV_PROJECT_ENVIRONMENT="$env:USERPROFILE\venvs\day10"` để tránh crash import Great Expectations trên Windows. |
| **Rà soát Data Contract đa tầng** | Data Foundation (`src/ingestion/`) & Observability (`src/observability/`) | Thống nhất cấu trúc 5 phần của `text_for_embedding` và schema dataframe giữa tầng clean và tầng ChromaDB. |
| **Quản lý Git Teamwork & Review PR** | Toàn bộ thành viên | Phối hợp review và merge PR #1 (Cường), PR #2 (Tùng) vào branch tích hợp để kiểm thử toàn tuyến. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Tích hợp toàn tuyến Baseline Phase 1 | `src/pipelines/phase1.py` | Chuỗi 6 bước Ingest ➔ Clean ➔ Index ➔ Eval ➔ Quality Gate chạy thông suốt | `uv run python script/run_phase1.py` chạy exit code 0 |
| Tích hợp luồng Corruption ➔ Repair | `src/pipelines/corruption_flow.py` | Cơ chế Idempotent Repair tái nạp từ snapshot phục hồi 100% metrics | `uv run python script/run_corruption_flow.py` chạy exit code 0 |
| Xây dựng báo cáo so sánh tự động | `src/observability/reporting.py` | Hai báo cáo Markdown `phase1_report.md` và `corruption_report.md` | Kiểm tra file sinh ra trong `data/reports/` khớp số liệu JSON |
| Xác minh tích hợp hệ thống | `tests/test_observability.py`, `tests/test_ingestion.py` | Bộ 12 test cases kiểm thử tự động của cả nhóm | `uv run python -m pytest -q` đạt 12 passed in 19s |

### Output cụ thể tạo ra:
Bảng đối chiếu 3 trạng thái in ra console và file `data/reports/corruption_report.md` thể hiện rõ nét sự suy giảm và phục hồi:
- **Baseline:** Hit rate `1.0000`, Token F1 `1.0000`, Quality `PASS`, Freshness `PASS` (`stale_ratio = 0.0417`).
- **Corrupted:** Hit rate `0.6000`, Token F1 `0.5741`, Quality `FAIL`, Freshness `FAIL` (`stale_ratio = 0.5000`).
- **Repaired:** Hit rate `1.0000`, Token F1 `1.0000`, Quality `PASS`, Freshness `PASS` (`stale_ratio = 0.0417`).

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Thiếu cơ chế điều phối liên tục (Orchestration):** Các module Ingestion, Cleaning, ChromaDB, Great Expectations và Evaluation được phát triển độc lập bởi các thành viên; nếu không có contract chặt chẽ và luồng điều phối tập trung, hệ thống sẽ bị lỗi truyền tham số hoặc không đảm bảo thứ tự thực thi.
2. **Nguy cơ lỗi phụ thuộc trạng thái (State Leakage):** Khi chuyển từ dữ liệu sạch sang dữ liệu bẩn rồi sang phục hồi, nếu không làm sạch cache hoặc phân lập collection, các vector lỗi sẽ làm bẩn kết quả phục hồi.
3. **Hiện tượng Silent Failure:** Cần đo lường chính xác tác động của dữ liệu bẩn lên AI và chứng minh việc sửa chữa giải quyết tận gốc nguyên nhân chứ không phải chỉ "vá" kết quả hiển thị.

### Cách triển khai
- **Thiết kế Pipeline khép kín trong `phase1.py`:**
  Xâu chuỗi tuần tự: `fetch_source_records` ➔ `build_clean_dataframe` ➔ `LocalEmbeddingIndex.build` (tạo collection `papers-baseline`) ➔ `build_test_set` ➔ `evaluate_corpus` ➔ `run_data_quality_checks` và `build_freshness_report` ➔ `generate_phase1_report`.
- **Cơ chế Idempotent Repair trong `corruption_flow.py`:**
  Khi dữ liệu bị tiêm 6 loại lỗi ở pha corrupted, hàm `repair_from_raw_snapshot()` không sửa chữa chắp vá trên DataFrame lỗi mà:
  1. Đọc lại snapshot sạch ban đầu từ `data/raw/crossref_records.json`.
  2. Tái tạo DataFrame sạch canonical qua `build_clean_dataframe`.
  3. Ghi đè vào `data/clean/papers_clean_repaired.csv` và `json`.
  4. Đánh chỉ mục mới hoàn toàn vào collection `papers-repaired`.
  5. Đánh giá lại trên cùng test set để đối chiếu khách quan.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | `Settings` cấu hình hệ thống, data snapshot `data/raw/`, ground-truth benchmark `data/eval/test_set.json` |
| Output | `data/results/*_metrics.json`, `data/quality/*_quality_report.json`, `data/reports/*.md` |
| Module phụ thuộc | `ingestion`, `retrieval`, `observability`, `evaluation` |
| Module sử dụng output | Giám khảo nghiệm thu, hệ thống RAG Serving, báo cáo nhóm |
| Điều kiện lỗi cần xử lý | Mất kết nối API Crossref (fallback snapshot), lỗi lock SQLite ChromaDB, crash đường dẫn Windows |

### Cách xác minh
```powershell
uv run python -m pytest -q
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```
- **Kết quả mong đợi:** Toàn bộ test và 2 scripts thực thi với exit code 0, sinh đầy đủ các file artifacts trong `data/`.
- **Kết quả thực tế:** Pipeline chạy mượt mà, in bảng so sánh 3 cột rõ ràng ra terminal.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp phục hồi dữ liệu trong `corruption_flow.py`: Nên viết các hàm "nghịch đảo" (Inverse Operations) để tìm và xóa từng dòng lỗi, hay tái tạo lại toàn bộ từ raw snapshot?
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (Targeted Patching):* Dựa vào `corruption_log.json`, viết code để đảo ngược 6 lỗi: xóa dòng duplicate, bỏ noise prefix, re-fetch title bị cắt ngắn,...
  2. *Phương án 2 (Immutable Reconstruction / Idempotent Repair):* Hủy bỏ hoàn toàn tập dữ liệu lỗi trong bộ nhớ, đọc lại từ file nguồn bất biến `data/raw/crossref_records.json` và chạy lại luồng cleaning chuẩn.
- **Phương án đã chọn:** Phương án 2 — Idempotent Reconstruction.
- **Lý do (Trade-off):** Phương án 1 cực kỳ dễ sinh bug khi gặp các lỗi phức tạp (như mất mát bản ghi không rõ ID hoặc lỗi cascading) và vi phạm tính Idempotent. Phương án 2 đơn giản, tuyệt đối tin cậy, đảm bảo trạng thái sau phục hồi luôn đồng nhất với baseline 100% dù chạy bao nhiêu lần đi nữa.
- **Bằng chứng:** Sau khi chạy repair theo phương án 2, toàn bộ chỉ số Hit Rate và Token F1 quay trở lại đúng mốc `1.0000`, Quality checks và Freshness SLA đều quay lại `PASS`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  Khi chạy `uv sync` và gọi lệnh kiểm tra `import great_expectations`, Python bắn lỗi `ModuleNotFoundError: No module named 'great_expectations.expectations.core'` dù thư viện đã tải về.
- **Lệnh hoặc bước tái hiện:** `python -c "import great_expectations"` trên Windows 11 với đường dẫn thư mục dài.
- **Nguyên nhân gốc:**
  Trên Windows, hệ thống file có giới hạn độ dài đường dẫn mặc định là 260 ký tự (`MAX_PATH`). Package `great-expectations` phiên bản 1.18 có cấu trúc thư mục lồng nhau quá sâu trong thư mục ảo `.venv`, khiến đường dẫn file vượt quá 260 ký tự và Windows không thể nạp module.
- **Cách xử lý:**
  1. Pin cố định phiên bản ổn định `great-expectations==1.16.1` trong `pyproject.toml`.
  2. Thiết lập biến môi trường để di chuyển virtual environment ra thư mục ngắn ngoài profile người dùng:
     ```powershell
     $env:UV_PROJECT_ENVIRONMENT="$env:USERPROFILE\venvs\day10"
     uv sync --extra dev
     ```
- **Cách xác minh sau khi sửa:** Chạy lại lệnh import và toàn bộ test suite, không còn bất kỳ lỗi import nào phát sinh.
- **Điều học được:** Trên môi trường Windows, lập trình viên pipeline luôn phải tính đến hạn chế đường dẫn `MAX_PATH` và phân cấp thư mục khi làm việc với các framework lớn.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô tải từ Crossref REST API qua mạng (hoặc từ local fallback snapshot) được cất giữ nguyên bản tại `data/raw/`. Qua bước cleaning, dữ liệu được lọc thẻ XML, tính `age_days` và ghép chuỗi `text_for_embedding`. Dữ liệu sạch vượt qua chốt kiểm định Great Expectations 1.x sẽ được mô hình `all-MiniLM-L6-v2` mã hóa thành vector 384 chiều và nạp vào ChromaDB collection kèm metadata.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Mỗi câu hỏi trong bộ benchmark có sẵn đáp án chuẩn (`ground_truth`) và ID tài liệu đích (`ground_truth_doc_ids`). Khi Agent nhận câu hỏi:
   - `retrieval_hit_rate` kiểm tra xem tài liệu đích có nằm trong Top-4 kết quả vector search hay không.
   - `mean_token_f1` và LLM Judge đánh giá mức độ trùng khớp từ vựng và tính đúng đắn ngữ nghĩa của câu trả lời do AI tạo ra so với đáp án chuẩn.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks (GX 1.x) kiểm tra tính toàn vẹn cấu trúc tĩnh của dữ liệu (số dòng, không null, ID không trùng, độ dài tóm tắt).
   - Freshness monitoring theo dõi độ trễ nghiệp vụ theo thời gian (Temporal Decay) dựa vào cột `age_days`, nhằm đảm bảo tri thức nạp vào AI không bị lỗi thời (Stale).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì tính khách quan của phép thử nghiệm có đối chứng (Controlled Experiment). Cố định test set giúp cô lập biến số duy nhất là chất lượng của dữ liệu trong Vector Store, loại trừ hoàn toàn việc điểm số thay đổi do câu hỏi dễ hay khó.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Về artifact: Xuất hiện đầy đủ `papers_clean_repaired.json`, collection `papers-repaired`, file `repaired_metrics.json` và `repaired_quality_report.json`.
   - Về metric: Quality Gate và Freshness SLA chuyển từ `FAIL` về `PASS`, Hit Rate và Token F1 lấy lại mức tuyệt đối 1.0000.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | ---: | ---: | ---: | :--- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Giảm mạnh 40% do 4 bài mới bị drop và 2 tiêu đề bị cắt cụt; phục hồi 100% sau repair |
| `mean_token_f1` | 1.0000 | 0.5741 | 1.0000 | Tóm tắt bị xóa trắng và chèn noise làm câu trả lời của AI mất hết từ khóa trọng tâm |
| `judge_accuracy` | 1.0000 | 0.7000 | 1.0000 | Điểm chính xác giảm còn 70% khi ngữ cảnh bị sai lệch |
| `mean_judge_score` | 5.0000 | 3.4000 | 5.0000 | Điểm trung bình giảm từ 5.0 xuống 3.4 thể hiện rõ nét Silent Failure |
| Quality checks | **PASS** | **FAIL** | **PASS** | Bắt được 4 dòng trùng lặp ID và 4 dòng tóm tắt rỗng |
| Freshness status | **PASS** | **FAIL** | **PASS** | Cảnh báo vi phạm khi tỷ lệ bài báo cũ vọt lên 50% (> trần SLA 25%) |

### Kết luận từ số liệu

1. **Chuỗi 1:** Tiêm 6 dạng lỗi ➔ Great Expectations và Freshness SLA báo động `FAIL` ➔ Retrieval Hit Rate sụt giảm nghiêm trọng (-0.4000), kéo theo Token F1 sụp đổ còn 0.5741 (Silent Failure).
2. **Chuỗi 2:** Kích hoạt Idempotent Repair tái tạo từ raw snapshot ➔ Toàn bộ chốt kiểm định phục hồi trạng thái `PASS` ➔ Hit Rate và Token F1 lấy lại mốc 1.0000.

- **Dạng lỗi ảnh hưởng rõ nhất:** Việc làm mất 20% bài báo mới (`drop_latest_records`) và xóa trắng tóm tắt (`blank_summary`) gây thiệt hại nặng nề nhất cho retrieval vì làm vector search hoàn toàn trôi lệch ra ngoài không gian ngữ nghĩa cần tìm.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Giá trị bất biến của Raw Lineage:** Không bao giờ ghi đè trực tiếp lên dữ liệu nguồn; raw snapshot là mỏ neo duy nhất để hệ thống có thể tự phục hồi (Self-Healing).
2. **Data Observability là tuyến phòng thủ số 1:** Ngăn chặn hiện tượng Silent Failure trước khi dữ liệu độc hại xâm nhập vào Vector Database và tầng phục vụ LLM.
3. **Thiết kế Pipeline có tính Idempotent:** Đảm bảo hệ thống có thể chạy lại bất kỳ lúc nào mà không gây ra tác dụng phụ hay rò rỉ trạng thái.

### Hướng cải thiện nếu có thêm thời gian
Tích hợp một **Automated Rollback Circuit Breaker**: Nếu chốt kiểm định Great Expectations phát hiện tỷ lệ lỗi vượt quá 10%, pipeline sẽ tự động chặn không cho nạp vector mới và tự động kích hoạt luồng rollback về snapshot ổn định gần nhất mà không cần con người can thiệp.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hồng Thái  
**Ngày xác nhận:** 2026-09-26  
