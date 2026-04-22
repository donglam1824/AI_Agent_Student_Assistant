#  Copy vào powershell
#  Chạy lại khi thêm scope mới - XÓA FILE token.json cũ
import os, sys

sys.path.insert(0, r"l:\AI_Agent_Student_Assistant")
from config.settings import settings
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/keep",
    "https://www.googleapis.com/auth/gmail.modify",
]
# Tắt chế độ local server, bắt buộc xuất ra URL để lấy mã bằng tay
flow = InstalledAppFlow.from_client_secrets_file(
    settings.google_credentials_path, SCOPES
)
# Bắt buộc hiện OAuth code trên màn hình Google
flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
auth_url, _ = flow.authorization_url(prompt="consent")
print("\n1. HÃY COPY ĐƯỜNG LINK NÀY DÁN VÀO TRÌNH DUYỆT (EDGE):")
print(auth_url)
code = input(
    "\n2. SAU KHI CHO PHÉP, GOOGLE SẼ HIỆN MỘT MÃ CODE NỀN TRẮNG. COPY CÁI MÃ MÀU VÀNG Ở GÓC, RỒI CHO VÀO ĐÂY: "
).strip()
flow.fetch_token(code=code)
creds = flow.credentials
with open(settings.google_token_path, "w") as f:
    f.write(creds.to_json())
print("\n✅ Auth successful! Token saved to:", settings.google_token_path)
