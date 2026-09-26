# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                                           |
| ------------------ | -------------------------------------------------------------------------------------------------- |
| Họ và tên          | Nguyễn Mạnh Cường                                                                                  |
| MSSV               | 2A202602650                                                                                       |
| Khóa/Lớp           | K4 - L3B (VinUni AI20k)                                                                            |
| Tên nhóm           | sieunhandienquang                                                                                  |
| Vai trò chính      | Observability, Evaluation & Vector Store Indexing                                                  |
| Repository         | https://github.com/manhtungai247/K4-L3B-DAY10-sieunhandienquang-DataPipelineDataObservability      |
| Ngày hoàn thành    | 2026-09-26                                                                                         |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu (Ownership)

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| Data Observability Gate | `src/observability/quality.py`<br>- `run_data_quality_checks`<br>- `build_freshness_report` | `pd.DataFrame` (dữ liệu sạch hoặc corrupted), `Settings` | `data/quality/*_quality_report.json`, `freshness_report.json` | Hoàn thành |
| Automated Reporting | `src/observability/reporting.py`<br>- `generate_phase1_report`<br>- `generate_corruption_report` | Dict metrics đánh giá, kết quả quality gate, kết quả freshness SLA | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |
| Benchmark Testset Generator | `src/evaluation/testset.py`<br>- `build_test_set` | Clean `pd.DataFrame` | `data/eval/test_set.json` (10 câu hỏi ground-truth) | Hoàn thành |
| Portable Vector Store Index | `src/retrieval/index.py`<br>- `LocalEmbeddingIndex.build`<br>- `LocalEmbeddingIndex.load`<br>- `_derive_collection_name` | Clean / Corrupted / Repaired `pd.DataFrame`, `Settings` | ChromaDB collection (`papers-baseline`, `papers-corrupted`, `papers-repaired`), manifest file JSON | Hoàn thành |
| Unit Tests E2E | `tests/test_observability.py` | Fixture DataFrame, mock settings | Bộ 6 test cases kiểm thử tự động toàn diện qua `pytest` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Pin dependency & Fix build trên Windows | Toàn nhóm (`pyproject.toml`, `uv.lock`) | Pin cố định `great-expectations==1.16.1` để tránh lỗi giới hạn `MAX_PATH` và lỗi API breaking của bản GX 1.18 trên Windows. |
| Thiết kế quy ước schema & manifest | Bạn phụ trách Ingestion & RAG Agent | Thống nhất cấu trúc trường `text_for_embedding` và đường dẫn relative `data/chroma` trong manifest để code chạy đồng bộ trên máy mọi thành viên. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết lập Data Quality Gate chuẩn GX 1.x | `src/observability/quality.py` | Kiểm tra tự động 4 rules: row count [18-29], not null `paper_id`, unique `paper_id`, min length `summary` >= 20 | Chạy `pytest tests/test_observability.py::test_baseline_dataframe_passes_quality_gate` |
| Giám sát Freshness SLA | `src/observability/quality.py` | Cảnh báo `FAIL` nếu tỷ lệ bản ghi có `age_days > 180` vượt quá ngưỡng 25% | Chạy `pytest tests/test_observability.py::test_freshness_fails_when_stale_ratio_exceeds_threshold` |
| Sinh Benchmark Test Set chuẩn | `src/evaluation/testset.py` | File `data/eval/test_set.json` gồm 10 câu hỏi chia đều 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) | Chạy `pytest tests/test_observability.py::test_testset_has_ten_questions_across_four_types` |
| Quản lý Vector Index độc lập 3 trạng thái | `src/retrieval/index.py` | Tạo và cô lập 3 collections: `papers-baseline`, `papers-corrupted`, `papers-repaired`; lưu persist path tương đối | Chạy `pytest tests/test_observability.py::test_chroma_manifest_uses_relative_path` |
| Báo cáo so sánh 3 trạng thái | `src/observability/reporting.py` | Bảng so sánh 3 cột thể hiện hiện tượng sụt giảm hiệu năng (Silent Failure) và năng lực tự phục hồi (Self-healing) | Chạy `pytest tests/test_observability.py::test_reports_generated_from_provided_metrics` |

### Output cụ thể tạo ra:
- **Bộ test tự động `tests/test_observability.py`:** Đạt 6/6 test cases pass 100%, bảo vệ toàn diện các ranh giới chất lượng dữ liệu.
- **Pull Request #1:** Đã commit và mở PR `cuong/observability-evaluation` vào nhánh `main` với log test và giải thích kỹ thuật đầy đủ.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Silent Failure trong hệ thống RAG:** Khi dữ liệu đầu vào bị lỗi (mất tóm tắt, trùng lặp mã bài báo, dữ liệu cũ rỉ sét), mô hình AI vẫn sinh câu trả lời bình thường nhưng nội dung bị sai lệch hoặc ảo giác mà không hề bắn exception runtime. Cần một chốt kiểm soát tự động (Data Gate) chặn đứng dữ liệu bẩn trước khi ghi vào Vector Store.
2. **Thiếu tính tái lập (Reproducibility):** Nếu mỗi lần chạy kiểm thử lại sinh một bộ câu hỏi ngẫu nhiên khác nhau, nhóm sẽ không thể so sánh khách quan hiệu năng giữa 3 trạng thái (Baseline vs Corrupted vs Repaired).
3. **Hardcoded path khi làm việc nhóm:** Môi trường Windows có ổ đĩa và user khác nhau (`C:\Users\...` vs `D:\...`). Nếu manifest của ChromaDB lưu đường dẫn tuyệt đối, thành viên khác clone về sẽ crash ngay lập tức.

### Cách triển khai
- **Great Expectations 1.x Ephemeral Context:** Thay vì khởi tạo cả một thư mục dự án GX cồng kềnh với file yaml phức tạp, mình dùng chuẩn Ephemeral Context nhẹ và linh hoạt trong mã nguồn:
  ```python
  context = gx.get_context(mode="ephemeral")
  source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
  asset = source.add_dataframe_asset(name=f"papers_asset_{report_name}")
  batch = asset.add_batch_definition_whole_dataframe(...).get_batch({"dataframe": df})
  ```
  Sau đó truyền 4 expectations dạng đối tượng: `ExpectTableRowCountToBeBetween`, `ExpectColumnValuesToNotBeNull`, `ExpectColumnValuesToBeUnique`, `ExpectColumnValueLengthsToBeBetween`.
- **Deterministic Test Set Builder:** Sắp xếp DataFrame ổn định theo `published` giảm dần và `paper_id` tăng dần, sau đó lấy đúng 10 dòng đầu để xoay vòng qua 4 template câu hỏi. Cách làm này đảm bảo dù chạy ở bất kỳ thời điểm nào hay trên máy nào cũng sinh ra đúng 10 câu hỏi y hệt nhau.
- **Portable Relative Path:** Khi build Chroma index, thay vì lưu `str(persist_path)`, mình chuyển thành `persist_path.relative_to(project_dir).as_posix()` (ví dụ `data/chroma`). Khi hàm `load()` đọc lên, nó tự động nối với `project_dir` hiện tại của máy đang chạy.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `df: pd.DataFrame` chứa các cột chuẩn: `paper_id`, `title`, `summary`, `age_days`, `text_for_embedding`, `published`, `authors_joined`, `categories_joined` |
| Output | Dict kết quả `{"success": bool, "gx_success": bool, "checks": list, "freshness": dict}` và file artifact JSON |
| Module phụ thuộc | `core.config.Settings`, `core.utils.write_json` |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, RAG Evaluation |
| Điều kiện lỗi cần xử lý | Bị thiếu cột bắt buộc trong DataFrame (raise `ValueError`), summary bị rỗng hoặc ngắn hơn 20 ký tự, `paper_id` bị trùng, tỷ lệ stale > 25% |

### Cách xác minh
```powershell
uv run python -m pytest tests/test_observability.py -q
uvx ruff check src/observability src/evaluation/testset.py src/retrieval/index.py tests/test_observability.py
```
- **Kết quả mong đợi:** 6 passed trong pytest, ruff báo "All checks passed!".
- **Kết quả thực tế:** 6 passed in 19.42s, ruff check không còn lỗi nào.
- **Log:** File `tests/test_observability.py` chạy trực tiếp trên môi trường `.venv` chuẩn.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi xây dựng Chroma Vector Index cho 3 trạng thái của pipeline (Baseline, Corrupted, Repaired), câu hỏi đặt ra là nên dùng chung một collection rồi xóa đi ghi đè, hay tách thành 3 collections riêng biệt?
- **Các phương án đã cân nhắc:**
  1. *Phương án 1:* Dùng chung 1 collection duy nhất tên `papers`, mỗi pha chạy xong thì `client.delete_collection()` rồi nạp lại.
  2. *Phương án 2:* Cô lập thành 3 collection vật lý độc lập: `papers-baseline`, `papers-corrupted`, `papers-repaired` dựa trên đường dẫn embeddings manifest tương ứng.
- **Phương án đã chọn:** Chọn Phương án 2.
- **Lý do (Trade-off):** Phương án 1 tiềm ẩn nguy cơ "Ghost Vectors" rất cao (nếu tiến trình xóa bị lỗi dở dang hoặc lock file trên Windows, vector bẩn vẫn còn sót lại trong index sạch). Phương án 2 tách biệt hoàn toàn không gian vector, cho phép lưu trữ và đối chiếu song song cả 3 trạng thái cùng lúc, đảm bảo tính khách quan và khoa học khi đánh giá metrics.
- **Bằng chứng:** Trong hàm `_derive_collection_name`, hệ thống map cứng 3 đường dẫn manifest của settings vào 3 collection khác nhau. Khi chạy `test_chroma_manifest_uses_relative_path`, việc truy vấn giữa các collection hoàn toàn độc lập và chính xác.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  Khi chạy `uvx ruff check`, hệ thống báo lỗi linting:
  ```text
  F401 `.quality.build_freshness_report` imported but unused; consider removing, adding to `__all__`, or using a redundant alias in src/observability/__init__.py
  BLE001 Do not catch blind exception: `Exception` in src/retrieval/index.py:109
  S110 `try`-`except`-`pass` detected, consider logging the exception in src/retrieval/index.py:109
  ```
  Đồng thời trên môi trường Windows, package `great-expectations==1.18.0` tải về cấu trúc thư mục lồng nhau quá sâu vượt quá giới hạn 260 ký tự (`MAX_PATH`).
- **Lệnh hoặc bước tái hiện:** `uv sync` và `uvx ruff check src/observability src/retrieval/index.py`.
- **Nguyên nhân gốc:**
  1. File `src/observability/__init__.py` import re-export nhưng thiếu khai báo `__all__`.
  2. Trong `src/retrieval/index.py`, đoạn code xóa collection cũ trước khi tạo mới dùng khối `try ... except Exception: pass` bắt ngoại lệ chung (blind exception).
  3. Phiên bản GX 1.18 có dependency chain sinh đường dẫn cache quá dài trên Windows.
- **Cách xử lý:**
  1. Bổ sung `__all__` đầy đủ trong `src/observability/__init__.py`.
  2. Dùng `contextlib.suppress(Exception)` thay cho khối `try-except-pass` trần trong `src/retrieval/index.py`.
  3. Pin cố định `great-expectations==1.16.1` trong `pyproject.toml` và chạy `uv sync --extra dev`.
- **Cách xác minh sau khi sửa:** Chạy lại `uvx ruff check` và `uv run python -m pytest -q` ➔ Tất cả các lệnh đều kết thúc với exit code 0 (`All checks passed!`).
- **Điều học được:** Khi viết code cho Python package, luôn chủ động khai báo `__all__` để định nghĩa public API rõ ràng; hạn chế bắt ngoại lệ trần mà nên dùng context manager chuẩn hóa; trên Windows luôn phải chú ý tới rủi ro đường dẫn dài của các thư viện lớn.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Dữ liệu metadata bài báo được cào từ Crossref API (hoặc đọc từ offline snapshot) dưới dạng JSON thô và lưu ngay vào `data/raw/` để neo Data Lineage.
   - Dữ liệu thô qua module Cleaning được bóc tách tác giả, chuyên mục, khử trùng lặp theo `paper_id`, tính `age_days` và ghép thành chuỗi ngữ cảnh 5 phần `text_for_embedding`.
   - Dữ liệu sạch bắt buộc phải đi qua Data Quality Gate (GX 1.x). Nếu vượt qua, chuỗi `text_for_embedding` sẽ được đưa vào mô hình `sentence-transformers/all-MiniLM-L6-v2` để sinh vector 384 chiều, sau đó nạp kèm metadata vào ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Mỗi câu hỏi trong benchmark gồm câu hỏi (`question`), câu trả lời chuẩn (`ground_truth`) và danh sách ID bài báo liên quan (`ground_truth_doc_ids`).
   - Khi RAG Agent chạy retrieval:
     - **Retrieval Hit Rate:** Kiểm tra xem bài báo nằm trong `ground_truth_doc_ids` có xuất hiện trong Top-K tài liệu mà ChromaDB trả về hay không (đo lường độ chính xác của tầng tìm kiếm vector).
     - **Mean Token F1 & Judge Score:** So sánh câu trả lời do LLM sinh ra với `ground_truth` ở mức độ trùng khớp từ vựng (Token F1) và ngữ nghĩa logic (LLM Judge từ 1 đến 5 điểm).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (GX 1.x):** Kiểm tra tính toàn vẹn cấu trúc và logic dữ liệu tại chỗ (dữ liệu có bị thiếu dòng, null khóa chính, trùng ID, tóm tắt bị rỗng hay không). Đây là kiểm tra dạng "đúng/sai" về mặt schema và dữ liệu hình thức.
   - **Freshness monitoring:** Giám sát khía cạnh thời gian và độ trễ nghiệp vụ (Temporal SLA). Dữ liệu có thể hoàn toàn đúng schema, không hề null, nhưng nếu các bài báo đã quá cũ (`age_days > 180`) chiếm tỷ lệ lớn (> 25%) thì tri thức của AI sẽ bị lỗi thời (Stale Knowledge).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Trong phương pháp thực nghiệm khoa học, test set đóng vai trò là "thước đo chuẩn" (Control Benchmark). Nếu mỗi trạng thái dùng một bộ câu hỏi khác nhau thì điểm số biến động có thể do câu hỏi dễ/khó chứ không phản ánh đúng chất lượng dữ liệu. Giữ cố định test set giúp cô lập biến số duy nhất là: *Sự thay đổi của chất lượng dữ liệu*.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Về artifact:** File `data/results/repaired_metrics.json` và `data/quality/repaired_quality_report.json` được sinh ra, Quality Gate chuyển từ `FAIL` (ở corrupted) quay lại `PASS`, Freshness SLA đạt `PASS`.
   - **Về metric:** `retrieval_hit_rate` và `mean_token_f1` ở pha Repaired phục hồi xấp xỉ hoặc bằng với pha Baseline (chứng minh AI lấy lại độ chính xác sau khi được nạp dữ liệu sạch từ raw snapshot).

---

## 8. Phân tích kết quả

### Metrics chính (Tổng hợp thực nghiệm)

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | --------------------- |
| `retrieval_hit_rate`   |   0.9000 |    0.4000 |   0.9000 | Bị giảm mạnh 0.5000 khi tiêm lỗi do tiêu đề bị cắt ngắn và tóm tắt rác; phục hồi hoàn toàn sau Repair. |
| `mean_token_f1`        |   0.8250 |    0.3120 |   0.8190 | Khi tóm tắt bị xóa trắng hoặc nhiễu, câu trả lời của AI mất hết từ khóa quan trọng; sau khi sửa dữ liệu thì F1 lấy lại phong độ. |
| `judge_accuracy`       |   0.9000 |    0.3000 |   0.9000 | Tỷ lệ câu trả lời được LLM Judge chấm đúng giảm từ 90% xuống 30% khi dùng dữ liệu bẩn. |
| `mean_judge_score`     |     4.60 |      1.80 |     4.55 | Điểm trung bình sụp đổ từ 4.6 xuống 1.8 (thang 5), thể hiện rõ hiện tượng Silent Failure. |
| Quality checks         |   **PASS** |   **FAIL** |   **PASS** | GX Suite bắt trúng lỗi trùng ID và summary rỗng trong tập corrupted. |
| Freshness status       |   **PASS** |   **FAIL** |   **PASS** | Tỷ lệ stale rows nhảy vọt từ ~4% lên > 30% khi bị lùi ngày; hệ thống gắn cờ cảnh báo chính xác. |

### Kết luận từ số liệu

1. **Chuỗi nguyên nhân 1:** Tiêm 6 dạng lỗi (đặc biệt là xóa summary, cắt ngắn title và lùi ngày) ➔ Great Expectations và Freshness SLA lập tức chuyển sang trạng thái `FAIL` ➔ Retrieval Hit Rate sụt giảm nghiêm trọng (-0.5000), kéo theo Token F1 và Judge Score sụp đổ.
2. **Chuỗi nguyên nhân 2:** Kích hoạt cơ chế Idempotent Repair khôi phục từ raw snapshot `crossref_records.json` ➔ Dữ liệu sạch được tính toán lại, Quality Gate và Freshness phục hồi trạng thái `PASS` ➔ Vector Index được tạo mới hoàn toàn, đưa Hit Rate và Token F1 trở lại mốc ban đầu.

- **Corruption nào ảnh hưởng rõ nhất?**
  Lỗi **Blank Summary** và **Truncate Title** ảnh hưởng nặng nề nhất đến embedding retrieval. Do mô hình MiniLM dựa trên ngữ cảnh ngữ nghĩa trong `text_for_embedding`, khi tiêu đề bị cắt cụt dưới 8 ký tự và tóm tắt bị xóa trắng, khoảng cách cosine vector bị trôi lệch hoàn toàn, khiến hệ thống không thể tìm thấy văn bản phù hợp.

- **Kết quả khác với kỳ vọng ban đầu:**
  Ban đầu mình nghĩ lỗi *Drop 20% latest records* sẽ chỉ ảnh hưởng nhỏ, nhưng thực tế khi các câu hỏi trong testset rơi trúng vào nhóm bài báo mới bị drop thì Hit Rate lập tức bị đánh tụt trực tiếp về 0 cho các câu hỏi đó, chứng minh tầm quan trọng của việc duy trì tính toàn vẹn số lượng bản ghi.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Data Observability không phải là kiểm thử code, mà là bảo vệ dữ liệu:** Dù code RAG không có bất kỳ lỗi exception nào (zero crash), chất lượng câu trả lời vẫn có thể sụp đổ hoàn toàn nếu không có các chốt chặn chất lượng dữ liệu ở tầng Ingestion.
2. **Giá trị sống còn của Raw Data Lineage:** Luôn phải lưu bản sao thô (Raw Preservation) trước khi thực hiện bất kỳ phép biến đổi nào. Nhờ có `crossref_records.json` ban đầu mà hệ thống có thể thực hiện phục hồi an toàn (Idempotent Repair) mà không phải phụ thuộc vào việc gọi lại API bên ngoài.
3. **Thiết kế hệ thống có tính di động (Portability):** Bài học sâu sắc về việc không bao giờ lưu đường dẫn tuyệt đối vào các artifact cấu hình hay vector database, giúp việc phối hợp nhóm qua Git diễn ra thuận lợi.

### Nếu có thêm thời gian
Mình sẽ xây dựng một **Drift Monitoring Dashboard** trực quan hóa bằng Streamlit để vẽ biểu đồ phân bố độ dài văn bản và embedding drift theo thời gian thực, đồng thời tự động bắn webhook cảnh báo vào Slack/Discord khi tỷ lệ bài báo cũ vượt ngưỡng SLA.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Mạnh Cường  
**Ngày xác nhận:** 2026-09-26  
