# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Mạnh Tùng             |
| MSSV               | 2A202602879                |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | sieunhandienquang          |
| Vai trò chính    | Data Foundation & Recovery (`src/ingestion/`) |
| Repository         | https://github.com/manhtungai247/K4-L3B-DAY10-sieunhandienquang-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Crossref Ingestion & Lineage** | `src/ingestion/crossref.py`<br>- `parse_crossref_payload`<br>- `fetch_source_records`<br>- `load_raw_records` | Crossref REST API hoặc local snapshot `data/raw/crossref_response.json` | 24 đối tượng `PaperRecord` chuẩn hóa; 2 file raw lineage: `crossref_response.json` và `crossref_records.json` | Hoàn thành |
| **Data Cleaning & Modeling** | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe` | List `PaperRecord`, `run_date` | `data/clean/papers_clean.csv` và `papers_clean.json` (24 dòng sạch, `paper_id` unique, `text_for_embedding` 5 phần) | Hoàn thành |
| **Synthetic Corruption Suite** | `src/ingestion/corruption.py`<br>- `corrupt_clean_dataframe` | Clean DataFrame, đường dẫn log | DataFrame bị biến dạng (22 dòng), file `data/results/corruption_log.json` ghi đủ 6 loại lỗi deterministic | Hoàn thành |
| **Data Foundation Test Suite** | `tests/test_ingestion.py`<br>- 6 test cases | Raw snapshots, clean data, corruption functions | Bộ test tự động kiểm thử Ingestion, Cleaning, Lineage và Corruption (6/6 tests OK) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Xử lý Blocker Windows Security** | Toàn bộ pipeline và môi trường `.venv` | Sử dụng công cụ `CiTool -r -j` xử lý chính sách Smart App Control chặn DLL (`orjson`, `pandas`, `chromadb`), đưa môi trường về trạng thái sẵn sàng. |
| **Hỗ trợ Idempotent Repair Logic** | Phối hợp với Pipeline Integrator (`corruption_flow.py`, `auto_heal.py`) | Cung cấp hàm tái lập dữ liệu sạch từ snapshot gốc `data/raw/crossref_records.json` để phục hồi 100% metrics cho RAG Agent. |
| **Tích hợp Data Quality Gate** | Module Observability (`quality.py`) | Cung cấp đúng cấu trúc các trường (`age_days`, `summary_chars`, `authors_joined`) giúp chốt kiểm dịch Great Expectations 1.x bắt lỗi chính xác. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Parse & Lưu trữ Raw Data Lineage | `src/ingestion/crossref.py` | 24 bài báo khoa học được bóc tách chuẩn xác từ Crossref | `python -c "from ingestion.crossref import fetch_source_records; print(len(fetch_source_records(...)))"` in ra `24` |
| Làm sạch, tính age_days & sinh text embedding | `src/ingestion/cleaning.py` | 24 dòng dữ liệu sạch chuẩn hóa, không thẻ XML, đầy đủ 5 phần embedding | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` |
| Triển khai 6 kịch bản Corruption Deterministic | `src/ingestion/corruption.py` | Tập dữ liệu bẩn và nhật ký tiêm lỗi | `data/results/corruption_log.json` |
| Kiểm thử đơn vị & tích hợp Ingestion | `tests/test_ingestion.py` | 6 bài test tự động bao phủ toàn bộ phạm vi Ingestion & Recovery | `python -m unittest tests/test_ingestion.py` in `Ran 6 tests ... OK` |

### Output cụ thể tạo ra và xác minh:
Artifact `data/results/corruption_log.json` và bảng dữ liệu `data/clean/papers_clean_corrupted.json`:
- Ghi nhận đầy đủ 6 dạng biến dạng: `drop_latest_records` (bỏ 5 bài ~ 20%), `blank_summary` (2 bài), `inject_noise` (2 bài), `truncate_title` (2 bài), `stale_date` (8 bài lùi về 2020, tạo 50% stale), `duplicate_rows` (2 bài nhân bản).
- Chạy 2 lần độc lập cho kết quả giống hệt nhau 100% (Deterministic Data Corruption).

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Nhiễu cấu trúc & mất ổn định API:** API Crossref thường xuyên bị giới hạn tần suất (HTTP 429), trả về XML JATS lẫn lộn trong abstract (`<jats:p>`), tác giả ở dạng lồng nhau, ngày xuất bản phân mảnh (`date-parts`).
2. **Nguy cơ mất Data Lineage:** Nếu làm sạch và ghi đè trực tiếp lên dữ liệu nguồn, khi xảy ra lỗi dữ liệu (Data Corruption) hệ thống sẽ vĩnh viễn không thể phục hồi (Irreversible Failure).
3. **Mô phỏng suy giảm thực tế (Silent Failure):** Cần một bộ tiêm lỗi dữ liệu có tính chất tất định (deterministic) để chứng minh được sự suy giảm chất lượng của RAG Agent và kích hoạt cảnh báo của Data Quality Gate.

### Cách triển khai
1. **Module `crossref.py`:**
   - Xây dựng hàm `parse_crossref_payload()` bóc tách an toàn các trường `DOI`, `title`, `abstract` (loại bỏ JATS tags qua regex), `author` (ghép `given` + `family`), `subject` (categories) và `published` (`YYYY-MM-DD`).
   - Cung cấp cơ chế Dual-Mode Ingestion trong `fetch_source_records()`: Khi `REFRESH_SOURCE=true` sẽ gọi REST API với timeout/headers; khi offline hoặc gặp lỗi, tự động chuyển sang đọc snapshot tĩnh tại `data/raw/crossref_response.json`.
   - Lưu trữ song song 2 artifacts thô: `crossref_response.json` (bản gốc API) và `crossref_records.json` (bản mapped records) nhằm bảo toàn tuyệt đối Data Lineage.
2. **Module `cleaning.py`:**
   - Chuẩn hóa whitespace, khử trùng lặp theo `paper_id` bằng Pandas.
   - Tính toán trường thời gian: `age_days = (run_date - published).days` theo múi giờ UTC.
   - Xây dựng trường đại diện `text_for_embedding` có cấu trúc chuẩn 5 phần:
     ```text
     Title: <title>
     Authors: <authors_joined>
     Categories: <categories_joined>
     Published: <published_str>
     Summary: <summary>
     ```
3. **Module `corruption.py`:**
   - Triển khai đủ 6 kỹ thuật làm biến dạng dữ liệu:
     a. *Drop 20% latest:* Cắt bỏ 5 bài mới nhất để mô phỏng sự cố đứt gãy ingestion.
     b. *Blank summary:* Xóa rỗng trường summary ở 2 bản ghi.
     c. *Inject noise:* Chèn tiền tố rác `### NOISE JUNK %$#@!` vào summary.
     d. *Truncate title:* Cắt ngắn title còn `'Bad'` (< 8 ký tự).
     e. *Stale date:* Đổi ngày xuất bản về năm 2020 trên 8 bài báo để đẩy tỷ lệ quá hạn lên 50% (> trần SLA 25%).
     f. *Duplicate rows:* Nhân bản 2 dòng có cùng `paper_id`.
   - Tự động tái tính toán `summary_chars` và rebuild lại chuỗi `text_for_embedding` sau khi sửa đổi.
   - Xuất nhật ký biến dạng có cấu trúc vào `data/results/corruption_log.json`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Snapshot JSON thô `data/raw/crossref_response.json` (hoặc response từ Crossref API) |
| **Output** | `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/clean/papers_clean_corrupted.json`, `data/results/corruption_log.json` |
| **Module phụ thuộc** | `core.config.Settings`, `core.utils` |
| **Module sử dụng output** | `retrieval/index.py` (nạp vào ChromaDB), `observability/quality.py` (chạy GX 1.x), `pipelines/` |
| **Điều kiện lỗi cần xử lý** | Mất kết nối internet, mã lỗi HTTP 429/503, thẻ XML lồng nhau, định dạng ngày tháng thiếu ngày/tháng, trùng lặp DOI |

### Cách xác minh
```bash
python -m unittest tests/test_ingestion.py
```
- **Kết quả mong đợi:** 6 bài test chạy thành công, kiểm chứng đủ 24 records, tính unique của `paper_id`, cấu trúc 5 phần của `text_for_embedding`, tính deterministic của corruption và tỷ lệ stale > 25%.
- **Kết quả thực tế:**
  ```text
  ......
  ----------------------------------------------------------------------
  Ran 6 tests in 0.062s

  OK
  ```
- **Artifact/log:** `data/raw/crossref_records.json`, `data/clean/papers_clean.json`, `data/results/corruption_log.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp xử lý dữ liệu nguồn: Nên lưu trữ dữ liệu thô ban đầu (Raw Snapshot) thành file tĩnh hay chỉ cần clean trực tiếp trong bộ nhớ (In-Memory Processing) rồi nạp vào Vector Database.
- **Các phương án đã cân nhắc:**
  1. *Phương án A (In-Memory Pipeline):* Nhận response từ API/hàm tải, convert thành DataFrame, clean ngay trên RAM và đẩy thẳng vào ChromaDB để tối ưu tốc độ và không tốn ổ cứng.
  2. *Phương án B (Immutable Raw Snapshot & Multi-stage Artifacts):* Lưu giữ nguyên vẹn payload thô thành `crossref_response.json` và `crossref_records.json` trước khi thực hiện bất kỳ bước tiền xử lý nào.
- **Phương án đã chọn:** Phương án B — Lưu trữ Raw Snapshot bất biến (Immutable Raw Storage).
- **Lý do:**
  - *Data Lineage & Reproducibility:* Đảm bảo khả năng truy vết nguồn gốc dữ liệu khi có tranh chấp kết quả hoặc kiểm toán.
  - *Idempotent Self-Healing:* Nếu không có snapshot nguồn sạch và bất biến, khi xảy ra sự cố dữ liệu bẩn (Corruption), toàn bộ hệ thống sẽ mất mốc tham chiếu và không thể tự phục hồi (Self-Healing) mà buộc phải re-crawl toàn bộ qua mạng với nguy cơ lỗi rate-limit.
- **Bằng chứng quyết định phù hợp:** Trong Checkpoint 5, nhờ có `data/raw/crossref_records.json` được bảo toàn nguyên vẹn, hàm repair đã tái lập thành công DataFrame sạch 24 dòng và giúp RAG Agent phục hồi Retrieval Hit Rate từ 60.0% trở lại 100.0%.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  Khi import các thư viện C-extension như `orjson` và `pandas` trong môi trường ảo `.venv`:
  `ImportError: DLL load failed while importing orjson: An Application Control policy has blocked this file.`
  `ImportError: DLL load failed while importing base: An Application Control policy has blocked this file.`
- **Lệnh hoặc bước tái hiện:** `python -c "import chromadb, great_expectations, sentence_transformers"` trên hệ điều hành Windows 11.
- **Nguyên nhân gốc:** Chính sách bảo mật **Smart App Control (VerifiedAndReputableDesktop)** của Windows 11 đang ở chế độ `Enforced`. Kernel của hệ điều hành phát hiện các file binary `.pyd`/`.dll` tải qua `pip` nằm trong thư mục người dùng (`.venv`) không có chữ ký số doanh nghiệp từ Microsoft nên đã chặn nạp DLL.
- **Cách xử lý:**
  1. Điều chỉnh cấu hình Code Integrity policy trong registry sang chế độ tắt (`VerifiedAndReputablePolicyState = 0`).
  2. Thực thi lệnh quản trị:
     ```powershell
     citool.exe -r -j
     ```
     để ra lệnh cho Windows Code Integrity driver làm mới chính sách ngay lập tức mà không phải khởi động lại máy tính.
- **Cách xác minh sau khi sửa:** Chạy lại lệnh import và chạy bộ test `tests/test_ingestion.py`, toàn bộ các module `pandas`, `orjson`, `chromadb` đều thực thi trơn tru với Exit code 0.
- **Điều học được:** Môi trường vận hành thực tế trên Windows có các lớp kiểm soát bảo mật cấp kernel rất nghiêm ngặt. Khi xây dựng pipeline cần hiểu rõ sự tương tác giữa trình thông dịch Python và hệ thống tệp/chính sách bảo mật của hệ điều hành.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu được lấy từ Crossref REST API (hoặc fallback snapshot offline) $\rightarrow$ parse thành các thực thể `PaperRecord` $\rightarrow$ làm sạch XML JATS tag, chuẩn hóa khoảng trắng, tính `age_days` và ghép chuỗi 5 phần `text_for_embedding` $\rightarrow$ lưu thành `papers_clean.json/csv` $\rightarrow$ mô hình `all-MiniLM-L6-v2` mã hóa thành vector embeddings 384 chiều $\rightarrow$ index vào ChromaDB collection `papers-baseline`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Bộ câu hỏi kiểm thử gồm 10 câu hỏi đa dạng (thuộc 4 dạng `summary`, `authors`, `date`, `categories`) được gắn sẵn `ground_truth_doc_ids` (ID bài báo đích) và `ground_truth` (câu trả lời chuẩn). Khi chạy RAG:
   - Nếu ID bài báo đích nằm trong Top-K tài liệu được trích xuất $\rightarrow$ tính là một Retrieval Hit (`retrieval_hit_rate`).
   - Câu trả lời sinh ra được đối chiếu với `ground_truth` để đo lường độ trùng khớp từ vựng (`mean_token_f1`) và chấm điểm chuẩn xác ngữ nghĩa qua LLM Judge.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (Great Expectations 1.x):** Đóng vai trò là chốt kiểm dịch schema và tính toàn vẹn tĩnh (đủ số dòng, không null các trường bắt buộc, ID duy nhất, summary không rỗng).
   - **Freshness monitoring:** Giám sát khía cạnh thời gian và độ suy thoái thông tin (Temporal Decay / Data Drift) dựa trên trường `age_days`, đảm bảo bài báo không quá 180 ngày theo cam kết SLA.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để duy trì tính khách quan trong đánh giá thực nghiệm (Controlled Experiment). Việc giữ nguyên bộ câu hỏi và ground truth giúp cô lập hoàn toàn biến số: Mọi sự biến thiên về điểm số (Hit Rate từ 100% $\rightarrow$ 60% $\rightarrow$ 100%) chỉ bắt nguồn từ sự thay đổi chất lượng của dữ liệu trong Vector Store, chứ không phải do câu hỏi khó hay dễ.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Quality Gate:** Báo cáo kiểm định `repaired_quality_report.json` và `repaired_freshness_report.json` chuyển từ `FAILED` về `PASSED` (0 lỗi vi phạm).
   - **Agent Metrics:** `retrieval_hit_rate` phục hồi từ 60.0% lên 100.0%, `mean_token_f1` phục hồi từ 0.6506 lên 1.0000 trong `repaired_metrics.json`.
   - **Artifacts:** Xuất hiện đầy đủ `papers_clean_repaired.json`, collection `papers-repaired` và bảng so sánh 3 trạng thái trong `data/reports/corruption_report.md`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** | **60.0%** | **100.0%** | Sụt giảm nghiêm trọng 40% do 5 bài bị drop và tiêu đề bị cắt ngắn. Phục hồi trọn vẹn 100% sau khi sửa chữa. |
| `mean_token_f1` | **1.0000** | **0.6506** | **1.0000** | Xóa rỗng tóm tắt và chèn chuỗi ký tự rác làm vector embedding bị trôi dạt (vector drift), kéo tụt độ khớp ngữ từ. |
| `judge_accuracy` | **100.0%** | **70.0%** | **100.0%** | LLM Judge đánh giá độ chính xác giảm xuống 70% khi ngữ cảnh trích xuất bị sai lệch. |
| `mean_judge_score` | **5.0 / 5.0** | **3.6 / 5.0** | **5.0 / 5.0** | Điểm chất lượng trung bình giảm 1.4 điểm, minh chứng AI bị mất phong độ rõ rệt. |
| Quality checks | **PASSED (0 lỗi)** | **FAILED (2 lỗi)** | **PASSED (0 lỗi)** | Bắt được vi phạm unique `paper_id` (duplicate rows) và vi phạm độ dài tối thiểu `summary` (blank summary). |
| Freshness status | **PASSED (0% stale)** | **FAILED (50% stale)** | **PASSED (0% stale)** | Bắt được vi phạm trần SLA 25% khi 8 bài báo bị lùi ngày xuất bản về quá khứ. |

### Kết luận từ số liệu

1. **Chuỗi sự cố:** Tiêm 6 kịch bản lỗi vào DataFrame $\rightarrow$ GX Gate báo FAILED và Freshness cảnh báo 50% stale $\rightarrow$ Retrieval Hit Rate sụp đổ từ 100% xuống 60%, Token F1 giảm còn 0.6506.
2. **Chuỗi phục hồi:** Tái tạo dữ liệu sạch từ snapshot gốc `data/raw/crossref_records.json` $\rightarrow$ GX Gate và Freshness trở lại trạng thái PASSED $\rightarrow$ Retrieval Hit Rate và Token F1 lấy lại phong độ tuyệt đối 100%.

- **Dạng corruption ảnh hưởng rõ nhất:** **Drop latest records** và **Truncate title**. Khi tài liệu bị xóa mất khỏi corpus, vector search rơi vào trạng thái Out-of-Corpus, còn khi title bị cắt ngắn (< 8 ký tự), logic tra cứu exact lookup thất bại hoàn toàn.
- **Kết quả khác kỳ vọng ban đầu:** Dù dữ liệu bị tiêm lỗi nặng nề, điểm Judge Accuracy vẫn duy trì được 70.0% thay vì về 0%. Điều này là do mô hình ngôn ngữ lớn (Gemini) tận dụng tri thức có sẵn trong trọng số (parametric knowledge) để bù đắp một phần ngữ cảnh bị thiếu, chứng minh nguy cơ Silent Failure nếu không có Data Observability Gate canh gác.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Dữ liệu thô (Raw Data) là tài sản bất biến:** Không bao giờ được phép ghi đè hay biến đổi trực tiếp trên dữ liệu nguồn; Data Lineage là điều kiện tiên quyết để hệ thống có khả năng tự phục hồi (Self-Healing).
2. **Data Observability ngăn chặn Silent Failure:** Trong hệ thống RAG, lỗi dữ liệu hiếm khi làm sập server mà âm thầm phá hủy chất lượng câu trả lời. Cần phải có các chốt kiểm dịch tự động như Great Expectations để chặn lỗi ngay từ tầng Ingestion.
3. **Tính Idempotent trong Data Engineering:** Mọi pipeline chuyển đổi dữ liệu và phục hồi cần được thiết kế có tính Idempotent ($f(f(x)) = f(x)$) để đảm bảo dù chạy lại bao nhiêu lần thì kết quả đầu ra vẫn nhất quán và đáng tin cậy.

### Hướng cải thiện nếu có thêm thời gian
Xây dựng thêm cơ chế **Automated Schema Evolution**: Khi API nguồn thay đổi cấu trúc trả về (ví dụ Crossref bổ sung thêm trường thông tin funding hoặc license), pipeline có khả năng tự động cập nhật Data Contract và tạo trường embedding mới mà không làm gián đoạn luồng phục vụ hiện tại.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Mạnh Tùng  
**Ngày xác nhận:** 2026-09-26  
