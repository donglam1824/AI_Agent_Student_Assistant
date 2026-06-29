
## Bước 1 – Đăng ký ứng dụng trên Google Cloud Console

### 1.1. Tạo Project trên Google Cloud

1. Truy cập **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Đăng nhập bằng tài khoản Google.
3. Nhấn nút **"Select a project"** (góc trên bên trái) → **"NEW PROJECT"**.
4. Đặt tên project (ví dụ: `StudentAIAssistant`) → nhấn **"CREATE"**.
5. Đợi vài giây, sau đó chọn project vừa tạo.

### 1.2. Bật các Google APIs cần thiết

Vào **[APIs & Services → Library](https://console.cloud.google.com/apis/library)** và bật lần lượt các API sau:

| API                        | Tìm kiếm với từ khóa    | Dùng cho           |
|----------------------------|--------------------------|--------------------|
| Google Calendar API        | `Calendar API`           | Quản lý lịch       |
| Gmail API                  | `Gmail API`              | Đọc/gửi email     |
| Google Tasks API           | `Tasks API`              | Ghi chú (Tasks)    |
| Google Drive API           | `Drive API`              | Tìm tài liệu (RAG)|

**Cách bật:**
- Nhấn vào tên API → nhấn nút **"ENABLE"**.
- Lặp lại cho tất cả 4 API trên.

### 1.3. Cấu hình OAuth Consent Screen

1. Vào **[APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)**.
2. Chọn **"External"** → **"CREATE"**.
3. Điền thông tin:
   - **App name:** `ORCA Student Assistant` (hoặc tên tùy ý)
   - **User support email:** chọn email của bạn
   - **Developer contact email:** nhập email của bạn
4. Nhấn **"SAVE AND CONTINUE"**.
5. Ở trang **Scopes**, nhấn **"ADD OR REMOVE SCOPES"** và thêm các scope sau:

   ```
   openid
   https://www.googleapis.com/auth/userinfo.email
   https://www.googleapis.com/auth/userinfo.profile
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/tasks
   https://www.googleapis.com/auth/drive.readonly
   ```

6. Nhấn **"UPDATE"** → **"SAVE AND CONTINUE"**.
7. Ở trang **Test users**, nhấn **"ADD USERS"** → nhập email Google mà bạn sẽ dùng để đăng nhập thử → **"SAVE AND CONTINUE"**.

8. Nhấn **"BACK TO DASHBOARD"**.

### 1.4. Tạo OAuth 2.0 Client ID

1. Vào **[APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)**.
2. Nhấn **"+ CREATE CREDENTIALS"** → chọn **"OAuth client ID"**.
3. Chọn **Application type:** `Web application`.
4. Đặt tên: `ORCA Web Client`.
5. Cấu hình các URI:
   - **Authorized JavaScript origins:** thêm `http://localhost:3000`
   - **Authorized redirect URIs:** thêm `http://localhost:3000`
6. Nhấn **"CREATE"**.
7. **Ghi lại** 2 giá trị quan trọng:
   - **Client ID** (dạng: `xxxx.apps.googleusercontent.com`)
   - **Client Secret** (dạng: `GOCSPX-xxxx`)
---

## Bước 2 – Lấy API Key cho Gemini AI

1. Truy cập **[Google AI Studio](https://aistudio.google.com/apikey)**.
2. Đăng nhập bằng tài khoản Google.
3. Nhấn **"Create API Key"** → chọn project vừa tạo ở Bước 1 (hoặc tạo project mới).
4. **Copy API Key** và lưu lại.

## Bước 3 – Cài đặt Backend (Python + FastAPI)

### 3.1. Giải nén mã nguồn

Giải nén file `.zip` ra một thư mục, ví dụ: `D:\ORCA\` hoặc `C:\Projects\AI_Agent_Student_Assistant\`.

### 3.2. Mở Terminal

Mở **PowerShell** hoặc **Command Prompt**, di chuyển đến thư mục backend:

```powershell
cd D:\ORCA\AI_Agent_Student_Assistant\backend
```

### 3.3. Tạo Virtual Environment

```powershell
python -m venv venv
```

### 3.4. Kích hoạt Virtual Environment

**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
.\venv\Scripts\activate.bat
```

### 3.5. Cài đặt thư viện Python

```powershell
pip install -r requirements.txt
```

### 3.6. Tạo file cấu hình `.env`

Tạo file `.env` trong thư mục `backend/` với nội dung sau:

```env
# ═══ LLM ═══
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=<paste_gemini_api_key_ở_bước_2>

# ═══ Google OAuth2 (Web Application Flow) ═══
GOOGLE_CLIENT_ID=<paste_client_id_ở_bước_1.4>
GOOGLE_CLIENT_SECRET=<paste_client_secret_ở_bước_1.4>
GOOGLE_REDIRECT_URI=http://localhost:3000
GOOGLE_CALENDAR_ID=primary

# ═══ Token Encryption Key ═══
# Chạy lệnh bên dưới để sinh key, rồi paste vào đây:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=<paste_key_vừa_sinh>

# ═══ Providers ═══
CALENDAR_PROVIDER=google
EMAIL_PROVIDER=google
NOTE_PROVIDER=google
MOCK_GRAPH=False

# ═══ JWT ═══
JWT_SECRET_KEY=thay_bang_chuoi_bat_ky_kho_doan
JWT_ALGORITHM=HS256

# ═══ Database ═══
DATABASE_URL=sqlite:///./orca.db

# ═══ Embeddings / Vector RAG ═══
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_BATCH_SIZE=32
```

### 3.7. Sinh Token Encryption Key

Chạy lệnh sau trong terminal (đã kích hoạt venv):

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy kết quả (chuỗi dạng `abc...xyz=`) và paste vào `TOKEN_ENCRYPTION_KEY` trong file `.env`.

---

## Bước 4 – Cài đặt Frontend (Next.js)

### 4.1. Mở Terminal mới

Mở một cửa sổ terminal mới, di chuyển đến thư mục frontend:

```powershell
cd D:\ORCA\AI_Agent_Student_Assistant\frontend
```

### 4.2. Cài đặt thư viện Node.js

```powershell
npm install
```

Quá trình cài đặt mất khoảng **1–3 phút**.

### 4.3. Cấu hình file `.env.local`

Tạo (hoặc chỉnh sửa) file `.env.local` trong thư mục `frontend/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<paste_client_id_ở_bước_1.4>
```

> `NEXT_PUBLIC_GOOGLE_CLIENT_ID` **phải trùng** với `GOOGLE_CLIENT_ID` ở backend.

---

## Bước 5 – Chạy ứng dụng

### 5.1. Chạy Backend (Terminal 1)

```powershell
cd D:\ORCA\AI_Agent_Student_Assistant\backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

Khi thấy dòng `Uvicorn running on http://127.0.0.1:8000` là backend đã sẵn sàng.

- **API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Endpoint:** [http://localhost:8000](http://localhost:8000)

### 5.2. Chạy Frontend (Terminal 2)

```powershell
cd D:\ORCA\AI_Agent_Student_Assistant\frontend
npm run dev
```

Khi thấy `Ready on http://localhost:3000` là frontend đã sẵn sàng.

- **Giao diện web:** Mở trình duyệt tại [http://localhost:3000](http://localhost:3000)

---

## Bước 6 – Đăng nhập và sử dụng

1. Mở trình duyệt, truy cập **[http://localhost:3000](http://localhost:3000)**.
2. Nhấn nút **"Đăng nhập bằng Google"**.
3. Chọn tài khoản Google đã thêm vào **Test users** ở Bước 1.3.
4. Cấp quyền cho ứng dụng (Calendar, Gmail, Tasks, Drive).
---