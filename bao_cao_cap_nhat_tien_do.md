# BÁO CÁO TIẾN ĐỘ THỰC HIỆN ĐỀ TÀI (Cập nhật: 16/05/2026)

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

## Kế hoạch thực hiện 1–2 tuần tới

**Tuần tiếp theo: Kiểm thử tích hợp và Tối ưu hóa**
- Kiểm thử tương tác chéo giữa các agents (ví dụ: Email Agent nhận deadline qua email → Calendar Agent tạo sự kiện lịch tương ứng).
- Tối ưu prompt engineering cho các agent để cải thiện chất lượng phản hồi.
- Triển khai hệ thống nhắc nhở deadline chủ động (Email Agent phát hiện deadline → gửi thông báo cho sinh viên).
- Kiểm tra và cải thiện tốc độ truy vấn RAG khi lượng tài liệu lớn.

**Tuần sau: Hoàn thiện giao diện và Viết báo cáo**
- Hoàn thiện UI/UX các trang Dashboard, bổ sung responsive design cho mobile.
- Viết tài liệu kỹ thuật mô tả kiến trúc hệ thống, luồng hoạt động Multi-Agent.
- Chuẩn bị slide thuyết trình và demo sản phẩm.
- Hoàn chỉnh báo cáo đồ án tốt nghiệp.
