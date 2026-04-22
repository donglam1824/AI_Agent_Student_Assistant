# BÁO CÁO TIẾN ĐỘ THỰC HIỆN ĐỀ TÀI (Cập nhật: 27/03/2026)

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

## Kết quả đã đạt được (Từ 13/03/2026 đến nay)

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

## Kế hoạch thực hiện 1–2 tuần tới

**Tuần 3: Xây dựng chuyên môn cho Note Agent (Trợ lý Ghi chú và RAG)**
- Thiết kế luồng hoạt động nội bộ của Note Agent.
- Tìm hiểu và triển khai kỹ thuật Retrieval-Augmented Generation (RAG).
- Chuẩn bị pipeline phân mảnh văn bản, tích hợp Vector Database (cSDL Vector cục bộ hoặc dịch vụ cloud) để tìm kiếm theo ngữ nghĩa. 
- Viết các Tools hỗ trợ cho Note Agent tra cứu kiến thức sách, slide tham khảo, tạo hoặc sửa đổi ghi chú.

**Tuần 4: Kết nối luồng Email và Thiết kế Giao diện UI**
- Hoàn tất API kết nối hộp thư/email (dùng Microsoft Graph API hoặc Gmail API) cho Email Agent.
- Lập trình các công cụ giúp đọc thư, tóm tắt thư mới, tự động soạn thảo mail trả lời, gửi thông báo hạn nộp bài cho sinh viên.
- (Tùy chọn/Nâng cao) Thử nghiệm đóng gói dưới dạng giao diện người dùng (Streamlit hoặc Web App cơ bản) thay thế cho công cụ dòng lệnh (CLI) để trình diễn ứng dụng trực quan hơn.
- Kiểm thử tích hợp sự tương tác chéo giữa các agents (ví dụ: Email Agent nhận deadline qua email xong yêu cầu Calendar Agent lập sẵn một sự kiện lịch).
