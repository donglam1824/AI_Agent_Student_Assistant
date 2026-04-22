# 🎓 AI Student Assistant

Trợ lý AI thông minh cho sinh viên, xây dựng theo kiến trúc **multi-agent** với [LangGraph](https://github.com/langchain-ai/langgraph) + Microsoft 365.

## Cấu trúc dự án

```
├── agents/         # LangGraph agents (CalendarAgent, ...)
├── tools/          # LangChain tools (1 file = 1 action)
├── services/       # Wrappers giao tiếp API bên ngoài
├── models/         # Pydantic schemas
├── config/         # Settings & environment
├── core/           # Shared infra (auth, logger)
└── main.py         # Entry point CLI
```

## Modules

| Module    | Status | Mô tả                                      |
|-----------|--------|--------------------------------------------|
| Calendar  | ✅ Done | Xem / tạo / sửa / xóa sự kiện lịch        |
| Notes     | 🔜     | Ghi chú thông minh + RAG                  |
| Email     | 🔜     | Đọc & soạn email tự động                  |
| Reminder  | 🔜     | Nhắc nhở theo lịch                         |

## Cài đặt & Chạy ứng dụng

Dự án bao gồm 2 phần chính: **Backend** (FastAPI) và **Frontend** (Next.js).

### 1. Chạy Backend (FastAPI)

```bash
cd backend

# 1. Tạo virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Cấu hình môi trường
copy .env.example .env
# Mở .env và điền các API key cần thiết (OPENAI_API_KEY, GEMINI_API_KEY, v.v.)

# 4. Chạy server
uvicorn main:app --reload --port 8000
# Backend sẽ chạy tại: http://localhost:8000
# Hoặc chạy CLI mode: python main.py
```

### 2. Chạy Frontend (Next.js)

```bash
cd frontend

# 1. Cài đặt dependencies
npm install

# 2. Cấu hình môi trường (nếu cần)
# Mặc định file .env.local đã có NEXT_PUBLIC_API_URL=http://localhost:8000

# 3. Chạy dev server
npm run dev
# Frontend sẽ mở tại: http://localhost:3000
```

## Chạy nhanh (Mock mode)

Mặc định `MOCK_GRAPH=True` → không cần Azure credentials, dùng dữ liệu giả để test agent.

```
🧑‍🎓 Bạn: Tôi có lịch gì trong tuần này?
🤖 Trợ lý: 📅 Lịch 7 ngày tới (3 sự kiện): ...
```

## Thêm module mới

1. Tạo `agents/<module>/` với `state.py`, `nodes.py`, `agent.py`
2. Tạo `tools/<module>/` với các tool cần thiết
3. Tạo `services/<module>_service.py`
4. Import agent mới vào `main.py`