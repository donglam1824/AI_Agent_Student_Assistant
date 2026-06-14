# BÁO CÁO TIẾN ĐỘ THỰC HIỆN ĐỀ TÀI (Cập nhật: 03/06/2026)

## Mô tả đề tài
**Tên đề tài:** Hệ thống Multi-Agent AI hỗ trợ quản lý tri thức và trợ lý học tập cá nhân cho sinh viên

**Mô tả đề tài:**
Trong quá trình học tập tại đại học, sinh viên thường phải tiếp nhận và quản lý nhiều nguồn thông tin khác nhau như tài liệu bài giảng, email từ giảng viên, thông báo từ nhà trường, cũng như các ghi chú cá nhân. Các thông tin này thường nằm rải rác trên nhiều nền tảng khác nhau như email, hệ thống quản lý học tập, hoặc các dịch vụ lưu trữ tài liệu, gây khó khăn cho sinh viên trong việc theo dõi thông tin quan trọng và quản lý hoạt động học tập.

Đề tài hướng tới xây dựng một hệ thống AI Multi-Agent đóng vai trò như một trợ lý học tập cá nhân cho sinh viên, hỗ trợ quản lý tri thức học tập và theo dõi các hoạt động học tập trong môi trường số.

Hệ thống sẽ tích hợp với các hệ sinh thái phổ biến (như Microsoft 365, Google Workspace) để truy cập và đồng bộ các dịch vụ Email, Calendar (Lịch), Notes (Ghi chú) và Tasks (Nhiệm vụ).

**Các chức năng chính của hệ thống bao gồm:**
- Xây dựng Router thông minh ứng dụng mô hình ngôn ngữ lớn (LLM) để phân tích yêu cầu bằng ngôn ngữ tự nhiên và điều phối tác vụ.
- Quản lý lịch trình, lịch học với độ tự chủ cao nhờ Calendar Agent (truy vấn, thêm lịch, dời lịch, hủy).
- Theo dõi các thông báo quan trọng từ email hoặc hệ thống học tập và nhắc nhở sinh viên về các deadline quan trọng (Email Agent/Reminder).
- Hỗ trợ tạo, tổ chức ghi chú học tập, tìm kiếm và truy xuất thông tin từ các tài liệu học tập với kỹ thuật RAG (Note Agent).
- Hệ thống được xây dựng dựa trên kiến trúc tiên tiến Multi-Agent bằng LangGraph, trong đó các agent chuyên biệt phối hợp với nhau để làm việc hoàn toàn tự động.

## Kết quả đã đạt được (Từ 13/03/2026 đến 14/04/2026)

Thay vì chỉ khảo sát, nhóm/cá nhân đã **hoàn thành đáng kể việc phát triển mã nguồn cốt lõi (Core System)**:

1. **Thiết lập Core Multi-Agent và LLM Manager:**
   - Xây dựng thành công bộ khung chuẩn với kiến trúc Module hóa (`agents/`, `tools/`, `services/`, `core/`).
   - Xây dựng bộ quản lý LLM linh hoạt cho phép thay đổi / mở rộng các nhà cung cấp như OpenAI, Google (Gemini) dễ dàng.

2. **Hoàn thiện Bộ Định Tuyến Ý Định (Intent Router):**
   - Đã tạo ra file chạy chính (Entry Point) hỗ trợ CLI (Command Line Interface), nhận diện chính xác yêu cầu nhắn gửi của người dùng thuộc loại nào (Calendar, Note, Email, Unknown) và kích hoạt trực tiếp đúng Agent tương ứng.

3. **Hoàn thành Calendar Module (Trợ lý Lịch học):**
   - Đã được định nghĩa xong các State, Tools, và graph theo chuẩn LangGraph.
   - Hoàn chỉnh việc tích hợp thực tế với **Google Calendar API** (đã xây dựng Module xác thực OAuth2, client-secret, token).
   - Agent lịch đã có thể tự động trả lời người dùng, đọc danh sách sự kiện (`list_events`), tạo lịch hẹn (`create_event`), cập nhật (`update_event`) và xóa sự kiện (`delete_event`).

4. **Khởi tạo hệ thống cho các Agent mới:**
   - Hoàn thành thiết kế lớp cấu trúc (Scaffolding pattern) cho Note Agent và Email Agent, học theo kiến trúc StateGraph vòng lặp suy luận (Reason - Tools) từ Calendar. Đảm bảo toàn bộ hệ thống thống nhất một cách hoạt động đồng bộ.

## Kết quả đã đạt được (Từ 14/04/2026 đến 16/05/2026)

Trong giai đoạn này, hệ thống đã được **mở rộng toàn diện từ CLI sang Web Application đầy đủ**, triển khai nhiều Agent mới, tích hợp đa nền tảng, và xây dựng hệ thống RAG hoàn chỉnh:

### 1. Xây dựng Giao diện Web Application (Frontend + Backend API)

- **Backend API (FastAPI):** Chuyển đổi toàn bộ hệ thống từ CLI sang kiến trúc API RESTful sử dụng FastAPI (`main.py`), hỗ trợ CORS cho frontend Next.js, tổ chức API theo phiên bản (`/api/v1/`).
- **Frontend (Next.js + TypeScript):** Xây dựng giao diện web hoàn chỉnh với kiến trúc App Router, bao gồm:
  - **Trang Chat chính** (`ChatWindow`, `ChatInput`, `ChatMessage`, `AgentBadge`): Giao diện trò chuyện tương tác với AI, hiển thị phản hồi từ các Agent khác nhau kèm badge nhận diện.
  - **Trang Quản lý Tài liệu** (`DocumentList`, `DropZone`, `DriveBrowser`): Upload tài liệu thủ công bằng kéo-thả (drag & drop), duyệt và import file từ Google Drive.
  - **Panel Email** (`EmailPanel`, `EmailNotificationBadge`, `EmailToast`): Hiển thị email mới, thông báo push khi có email học thuật quan trọng.
  - **Trang Cài đặt** (`settings/page.tsx`): Quản lý kết nối tài khoản Google và Microsoft, cấu hình tùy chọn người dùng.
  - **Layout Dashboard** (`layout.tsx`, `Sidebar`): Thanh điều hướng bên trái với menu truy cập nhanh đến Chat, Calendar, Email, Notes, Docs và Settings.

### 2. Hệ thống Xác thực và Quản lý Người dùng

- **Google OAuth2 Login:** Triển khai luồng đăng nhập Google OAuth2 code flow hoàn chỉnh. Frontend gửi `authorization_code`, backend trao đổi lấy `access_token` + `refresh_token`, lưu mã hóa vào DB, rồi phát hành JWT nội bộ cho ứng dụng.
- **Microsoft OAuth2 Connection:** Xây dựng luồng kết nối tài khoản Microsoft 365 bổ sung (`/auth/microsoft/url`, `/auth/microsoft`), cho phép người dùng liên kết tài khoản Microsoft sau khi đã đăng nhập bằng Google. Sử dụng MSAL (Microsoft Authentication Library) để quản lý token.
- **Quản lý Token bảo mật:** Tất cả access_token và refresh_token (Google, Microsoft) được mã hóa trước khi lưu vào SQLite (`core/crypto.py`). Hệ thống tự động refresh token khi hết hạn.
- **Database Layer (SQLAlchemy + SQLite):** Xây dựng lớp cơ sở dữ liệu với ORM SQLAlchemy, bao gồm mô hình `User` lưu trữ thông tin người dùng, token Google, token Microsoft, email Microsoft liên kết. CRUD operations đầy đủ qua `db/crud.py`.
- **API kết nối tài khoản:** Endpoint `/auth/connections` cho phép frontend kiểm tra trạng thái kết nối Google/Microsoft, `/auth/microsoft` (DELETE) để ngắt kết nối Microsoft.

### 3. Hoàn thành Email Agent (Đa hộp thư Gmail + Outlook)

- **Email Agent (LangGraph ReAct):** Xây dựng `EmailAgent` hoàn chỉnh với kiến trúc StateGraph vòng lặp Reason-Tools, hỗ trợ 6 công cụ (tools): `list_emails`, `send_email`, `reply_email`, `analyze_priority`, `extract_deadline`, `create_reminder`.
- **Multi-Email Service:** Triển khai `MultiEmailService` tổng hợp cả Gmail (`GoogleEmailService`) và Outlook (`GraphEmailService`) vào cùng một giao diện thống nhất. Agent tự động nhận diện nguồn email qua prefix `gmail:<id>` hoặc `outlook:<id>`.
- **Google Gmail Service:** Tích hợp Gmail API cho phép đọc, gửi và trả lời email. Xử lý MIME message (base64 decode), parse header (Subject, From, Date).
- **Microsoft Outlook Service (Graph API):** Tích hợp Microsoft Graph API cho Outlook mail (`/me/messages`, `/me/sendMail`), hỗ trợ đọc, gửi email qua tài khoản Microsoft 365.
- **Hệ thống quét email định kỳ:** Xây dựng `EmailScheduler` sử dụng APScheduler với 4 phiên quét/ngày (7:30, 12:00, 17:00, 21:00). Tự động lọc email học thuật theo domain giảng viên/nhà trường, phân tích và lưu trữ kết quả.
- **Email Analyzer:** Module `email_analyzer.py` phân tích email học thuật, trích xuất deadline, phân loại mức độ ưu tiên để cảnh báo sinh viên.

### 4. Hoàn thành Note Agent (Trợ lý Ghi chú qua Google Tasks)

- **Note Agent (LangGraph ReAct):** Xây dựng `NoteAgent` với 2 công cụ: `list_notes` (xem danh sách ghi chú) và `create_note` (tạo ghi chú mới).
- **Google Tasks Integration:** Ghi chú được lưu trữ trên Google Tasks (danh sách "ORCA Notes"), tận dụng tài khoản Google đã xác thực của người dùng. Dịch vụ `google_note_service.py` xử lý tạo/lấy danh sách tasks qua Google Tasks API.
- **Agent tự động đặt tiêu đề:** Nếu người dùng không đề cập tiêu đề, agent tự động sinh tiêu đề rõ ràng (ví dụ: "Ghi chú môn Toán – 22/04") dựa trên nội dung.

### 5. Xây dựng Document Search Agent và Hệ thống RAG

- **DocSearch Agent (LangGraph ReAct):** Agent chuyên biệt cho tìm kiếm tài liệu, hỗ trợ 5 công cụ: `upload_document`, `search_documents`, `list_documents`, `list_drive_documents`, `guide_drive_import`.
- **Pipeline RAG hoàn chỉnh:**
  - **Document Loader** (`rag/document_loader.py`): Hỗ trợ 3 nguồn (file trên disk, text thuần từ Google Drive export, binary PDF/DOCX từ Drive). Sử dụng `RecursiveCharacterTextSplitter` với separators ngữ nghĩa (chunk_size=1000, overlap=200).
  - **Vector Store** (`rag/vector_store.py`): Sử dụng ChromaDB làm cơ sở dữ liệu vector cục bộ, lưu tại `data/chroma_db/`. Hỗ trợ thêm, xóa, tìm kiếm theo relevance score kèm filter metadata.
  - **Embeddings** (`rag/embeddings.py`): Sử dụng mô hình embedding để chuyển đổi văn bản thành vector.
  - **Retriever** (`rag/retriever.py`): Truy xuất top-k chunks liên quan nhất với ngưỡng score 0.3, hỗ trợ lọc theo tên tài liệu và user_id.
- **DocSearch Service** (`services/doc_search_service.py`): Lớp điều phối quản lý toàn bộ quá trình upload/import/sync/search. Metadata tài liệu được lưu trong SQLite riêng (`data/documents.db`), hỗ trợ 3 nguồn: manual upload, Google Drive, OneDrive.

### 6. Tích hợp Google Drive cho RAG

- **Google Drive Service** (`services/google_drive_service.py`): Kết nối Google Drive API v3, hỗ trợ:
  - Liệt kê thư mục và file (`list_folders`, `list_files`).
  - Export Google Docs/Sheets/Slides sang text/csv.
  - Download file thông thường (PDF, DOCX, TXT).
  - Lấy metadata file (name, modifiedTime, size).
- **Import và Sync từ Drive:** Người dùng có thể chọn file từ Drive và import vào hệ thống RAG. Hỗ trợ re-sync tự động kiểm tra `modifiedTime` để chỉ cập nhật khi file thay đổi.
- **Frontend DriveBrowser:** Component `DriveBrowser.tsx` cho phép người dùng duyệt thư mục Drive, chọn file và import trực tiếp vào cơ sở tri thức.

### 7. Tích hợp Microsoft Teams Agent

- **Teams Agent (LangGraph ReAct):** Agent hỗ trợ sinh viên theo dõi lớp học trên Microsoft Teams, bao gồm 5 công cụ: `list_teams`, `list_team_channels`, `list_education_classes`, `list_team_messages`, `list_class_assignments`.
- **Teams Service (Graph API):** `GraphTeamsService` tích hợp Microsoft Graph REST API:
  - Liệt kê Teams, kênh (channels), lớp Education.
  - Đọc tin nhắn mới trên kênh (thông báo giảng viên).
  - Xem danh sách bài tập, deadline.
- **Mock Teams Service:** Dịch vụ mock để phát triển/demo khi chưa có tài khoản Microsoft thực.

### 8. Tích hợp OneDrive cho RAG

- **OneDrive Service** (`services/onedrive_service.py`): Tương tự Google Drive, hỗ trợ liệt kê file, download nội dung từ OneDrive qua Microsoft Graph API.
- **DocSearch Service mở rộng:** Hỗ trợ `import_from_onedrive` và `sync_onedrive_document` với cùng logic metadata và chunk management như Google Drive.

### 9. Nâng cấp Intent Router

- **Router mở rộng:** Bộ định tuyến ý định (Intent Router) đã được mở rộng từ 3 loại (Calendar, Note, Email) lên 5 loại: `calendar`, `note`, `email`, `docsearch`, `unknown`. Hỗ trợ phân loại câu hỏi liên quan đến tìm kiếm tài liệu, hỏi đáp kiến thức.
- **Lazy-loading agents:** Các agent nặng (Email, DocSearch) được khởi tạo theo kiểu lazy-load để tối ưu thời gian khởi động.

## Kết quả đã đạt được (Từ 16/05/2026 đến 01/06/2026)

Trong giai đoạn này, hệ thống tiếp tục được **hoàn thiện theo hướng ổn định hóa trải nghiệm sử dụng thực tế**, đặc biệt ở các phần phân loại tài liệu, quản lý tri thức RAG, định tuyến hội thoại và xử lý email học thuật:

### 1. Hoàn thiện phân loại tài liệu học tập và giao diện tổng quan chủ đề

- **Topic Classifier:** Xây dựng dịch vụ `TopicClassifier` sử dụng LLM để tự động phân tích nội dung tài liệu, xác định `topic`, `category`, `tags` và độ tin cậy khi upload/import tài liệu.
- **Metadata tài liệu mở rộng:** Bổ sung lưu trữ `topic`, `category`, `tags` vào database và metadata chunk trong vector store, giúp tài liệu không chỉ được tìm kiếm theo nội dung mà còn được tổ chức theo chủ đề học tập.
- **API quản lý chủ đề:** Bổ sung endpoint `/documents/topics` để tổng hợp số lượng tài liệu theo danh mục và endpoint cập nhật thủ công topic/category/tags cho từng tài liệu.
- **Frontend Topic Overview:** Xây dựng component `TopicOverview` hiển thị tổng quan phân loại học tập bằng biểu đồ donut, category cards và bộ lọc theo danh mục. Danh sách tài liệu hỗ trợ hiển thị badge chủ đề/danh mục và chỉnh sửa metadata trực tiếp.

### 2. Hoàn thiện tích hợp OneDrive và đồng bộ tài liệu đa nguồn

- **OneDrive Service:** Hoàn thiện dịch vụ đọc file OneDrive thông qua Microsoft Graph API, hỗ trợ liệt kê thư mục, liệt kê file và tải nội dung file về hệ thống RAG.
- **API OneDrive:** Bổ sung các endpoint `/documents/onedrive/folders`, `/documents/onedrive/files`, `/documents/onedrive/import` và `/documents/onedrive/sync/{file_id}` để thao tác tài liệu OneDrive tương tự Google Drive.
- **Frontend Docs mở rộng:** Trang quản lý tài liệu có thêm tab OneDrive, tái sử dụng `DriveBrowser` để người dùng có thể duyệt, chọn và import tài liệu từ Microsoft 365.
- **Cơ chế re-sync:** Cả Google Drive và OneDrive đều hỗ trợ kiểm tra `modifiedTime`/metadata để tránh xử lý lại tài liệu khi file chưa thay đổi.

### 3. Nâng cấp chất lượng RAG bằng Markdown hóa PDF và Knowledge Wiki

- **PDF to Markdown bằng marker-pdf:** Nâng cấp `DocumentLoader` để ưu tiên chuyển PDF sang Markdown bằng `marker-pdf`, giữ tốt hơn cấu trúc tiêu đề, đoạn, bảng biểu và ngữ cảnh học tập. Khi môi trường không hỗ trợ marker, hệ thống tự fallback về `pypdf`.
- **Markdown cache:** Bổ sung cache Markdown theo user và hash nội dung file tại `data/markdown_cache/`, giúp tránh chuyển đổi lại PDF nhiều lần và cải thiện tốc độ xử lý tài liệu.
- **Markdown Knowledge Wiki:** Xây dựng `WikiService` tạo cơ sở tri thức dạng Markdown theo từng user tại `data/wiki/`, gồm `manifest.json`, `index.md`, file tóm tắt theo danh mục và file Markdown riêng cho từng tài liệu.
- **Contextualized chunks:** Trước khi đưa chunk vào vector store, hệ thống bổ sung ngữ cảnh gồm tên tài liệu, danh mục, chủ đề, tags và tóm tắt tài liệu. Việc này giúp kết quả truy xuất RAG có thêm ngữ cảnh và giảm rủi ro trả lời rời rạc khi chunk quá ngắn.
- **Đồng bộ khi xóa tài liệu:** Khi người dùng xóa tài liệu, hệ thống xóa cả vector tương ứng và bản ghi trong Markdown wiki để tránh dữ liệu cũ còn tồn tại trong kho tri thức.

### 4. Nâng cấp Email Agent theo hướng "Smart Academic Email"

- **Bộ lọc email học thuật dùng chung:** Xây dựng `academic_filter.py` với cơ chế phân loại nhiều tầng: domain trường đại học, subdomain LMS/học vụ, keyword trong sender và keyword trong subject/body.
- **Lọc email học thuật mặc định:** Tool `list_emails` mặc định chỉ trả về email học thuật (`academic_only=True`), đồng thời vẫn hỗ trợ xem tất cả email khi người dùng yêu cầu.
- **Tool quét và tóm tắt email:** Bổ sung `scan_and_summarize_emails` để quét Gmail/Outlook, lọc email học thuật, phân nhóm theo mức độ ưu tiên (`urgent`, `important`, `follow_up`, `info`) và trình bày kết quả có cấu trúc.
- **Tool đọc chi tiết email:** Bổ sung `read_email_detail` để lấy nội dung đầy đủ một email cụ thể, tóm tắt bằng LLM, trích xuất deadline và gợi ý hành động như tạo nhắc lịch hoặc soạn phản hồi.
- **Email Agent prompt mới:** Cập nhật prompt hệ thống để ưu tiên luồng quét email học thuật, không hiển thị danh sách email thô, chủ động đề xuất tạo reminder khi phát hiện deadline và đề xuất soạn phản hồi khi email cần trả lời.
- **Scheduler dùng bộ lọc chung:** `EmailScheduler` được điều chỉnh để dùng cùng module `academic_filter`, giúp logic lọc email học thuật thống nhất giữa quét định kỳ và chat.

### 5. Cải thiện Intent Router và trải nghiệm chat

- **Nhận diện ý định bằng keyword:** Bổ sung lớp nhận diện nhanh dựa trên keyword trước khi gọi LLM, giúp các yêu cầu phổ biến về lịch, ghi chú, email, tài liệu và Teams được định tuyến nhanh hơn.
- **Chuẩn hóa tiếng Việt không dấu:** Router hỗ trợ normalize nội dung người dùng để nhận diện cả câu có dấu và không dấu, giảm lỗi khi sinh viên nhập nhanh.
- **Hỗ trợ Teams trong router:** Intent Router mở rộng thêm `teams`, đồng bộ với Teams Agent đã xây dựng trước đó.
- **Parse kết quả LLM an toàn hơn:** Bổ sung cơ chế chuẩn hóa output từ LLM để chỉ nhận một trong các intent hợp lệ, hạn chế lỗi khi mô hình trả lời dài hoặc sai định dạng.

### 6. Dọn dẹp dữ liệu phát sinh và ổn định mã nguồn

- **Loại bỏ binary phát sinh khỏi repository:** Dọn các file database/cache như ChromaDB binary và SQLite WAL/SHM khỏi Git để giảm rủi ro commit nhầm dữ liệu runtime.
- **Cập nhật dependency xử lý tài liệu:** Bổ sung `marker-pdf` và cấu hình liên quan để phục vụ pipeline chuyển đổi PDF sang Markdown.
- **Cải thiện giao diện phụ trợ:** Tinh chỉnh giao diện email panel, badge agent và các thông báo OAuth Microsoft bằng tiếng Việt để trải nghiệm đồng nhất hơn.

## Kết quả đã đạt được (Từ 01/06/2026 đến 03/06/2026)

Trong giai đoạn này, hệ thống tập trung **tối ưu chất lượng truy xuất tri thức RAG**, đặc biệt với các câu hỏi tiếng Việt ngắn, câu hỏi khái niệm và trường hợp semantic search thuần chưa trả về đúng đoạn tài liệu liên quan.

### 1. Nâng cấp Retriever thành Hybrid Retriever

- **Kết hợp semantic search và lexical rerank:** `Retriever` được nâng cấp từ truy xuất thuần vector sang cơ chế hybrid. Hệ thống vẫn dùng Chroma semantic search làm bước đầu, sau đó bổ sung lượt tìm kiếm lexical cục bộ trên cùng phạm vi dữ liệu đã lọc để tăng khả năng bắt đúng từ khóa, cụm từ và metadata.
- **Cải thiện truy vấn tiếng Việt:** Bổ sung chuẩn hóa Unicode, bỏ dấu tiếng Việt, tách token và loại stopword để xử lý tốt hơn các câu hỏi nhập nhanh, không dấu hoặc chỉ chứa một vài khái niệm chính.
- **Rerank theo nhiều tín hiệu:** Kết quả được chấm lại bằng tổ hợp điểm semantic, điểm lexical và metadata boost dựa trên `source`, `topic`, `category`, `tags`, `context_summary`. Cách này giúp ưu tiên đoạn tài liệu khớp cả nội dung lẫn ngữ cảnh học tập.
- **Fallback an toàn khi điểm thấp:** Khi không có chunk vượt ngưỡng đầy đủ nhưng vẫn có kết quả tương đối liên quan, retriever có thể trả về chunk tốt nhất để giảm tình trạng "không tìm thấy tài liệu" trong các truy vấn hợp lệ nhưng embedding cho điểm thấp.

### 2. Làm giàu nội dung trước khi index vào Vector Store

- **Module enrichment mới:** Bổ sung `rag/enrichment.py` với hàm `prepare_chunks_for_index`, dùng để đưa `context_prefix` vào nội dung được embedding trước khi lưu vào ChromaDB.
- **Giữ nguyên nội dung gốc cho câu trả lời:** Nội dung chunk ban đầu được lưu vào metadata `raw_content`, còn `page_content` được làm giàu để phục vụ truy xuất. Khi format context cho LLM, hệ thống ưu tiên dùng `raw_content` để tránh lặp lại phần prefix và giữ câu trả lời tự nhiên.
- **Áp dụng đồng bộ cho nhiều luồng nhập liệu:** Enrichment được gọi trong các luồng upload tài liệu thủ công, xử lý background document API, import Google Drive và import OneDrive, giúp chất lượng index nhất quán giữa các nguồn tài liệu.

### 3. Mở rộng Vector Store phục vụ tìm kiếm cục bộ

- **Bổ sung truy xuất danh sách chunks:** `VectorStore` có thêm `get_documents(filter, limit)` để lấy các chunk đã lưu trong ChromaDB theo phạm vi user/document, phục vụ lexical reranking mà không cần tạo thêm cơ sở dữ liệu phụ.
- **Giữ metadata `_chroma_id`:** Khi đọc chunk từ ChromaDB, hệ thống gắn lại id nội bộ vào metadata để tránh trùng lặp ứng viên khi kết hợp kết quả semantic và lexical.
- **Ổn định log/warning:** Các cảnh báo relevance score ngoài khoảng chuẩn từ Chroma/LangChain được lọc để log vận hành gọn hơn trong quá trình truy vấn.

### 4. Điều chỉnh DocSearch Service cho chất lượng truy vấn thực tế

- **Tăng số kết quả truy xuất:** `DocSearchService` chuyển sang dùng `Retriever(k=8, score_threshold=0.2)` để lấy thêm ngữ cảnh cho LLM và giảm rủi ro loại nhầm đoạn liên quan trong tài liệu tiếng Việt.
- **Nhất quán metadata cho OneDrive:** Luồng sync/import OneDrive được bổ sung tính toán `content_hash`, hỗ trợ kiểm tra thay đổi nội dung và đồng bộ lại tài liệu chính xác hơn.
- **Chuẩn bị script kiểm tra nội bộ:** Tạo các script scratch để kiểm tra database, log và truy vấn RAG trong quá trình debug/tối ưu. Các script này phục vụ phát triển nội bộ, chưa được đưa vào luồng sản phẩm chính.

## Kế hoạch thực hiện 1–2 tuần tới (Sau 03/06/2026)

**Tuần tiếp theo: Kiểm thử tích hợp và Tối ưu hóa**
- Kiểm thử end-to-end các luồng chính: đăng nhập Google, kết nối Microsoft, chat với từng agent, upload/import tài liệu, tìm kiếm RAG, quét email học thuật và đọc chi tiết email.
- Kiểm thử tương tác chéo giữa các agents, đặc biệt luồng Email Agent phát hiện deadline → Calendar Agent tạo sự kiện/nhắc lịch tương ứng.
- Đo hiệu năng pipeline RAG với tài liệu lớn, kiểm tra thời gian chuyển PDF sang Markdown, tốc độ embedding, tốc độ truy vấn ChromaDB và chi phí của bước lexical rerank cục bộ.
- Kiểm thử chất lượng hybrid retrieval bằng bộ câu hỏi tiếng Việt có dấu/không dấu, câu hỏi khái niệm ngắn và câu hỏi theo chủ đề/danh mục tài liệu.
- Rà soát lỗi biên của bộ lọc email học thuật, bổ sung domain/keyword phổ biến và giảm false positive/false negative.

**Tuần sau: Hoàn thiện giao diện và Viết báo cáo**
- Hoàn thiện UI/UX cho Dashboard, Docs, Email và Settings; kiểm tra responsive design trên mobile/tablet.
- Viết tài liệu kỹ thuật mô tả kiến trúc Multi-Agent, luồng xác thực OAuth, pipeline RAG, Knowledge Wiki và luồng xử lý email học thuật.
- Chuẩn bị dữ liệu demo gồm tài liệu mẫu, email mẫu, lịch học/deadline và kịch bản trình diễn các agent phối hợp.
- Hoàn chỉnh báo cáo đồ án tốt nghiệp, slide thuyết trình và checklist triển khai/demo.
