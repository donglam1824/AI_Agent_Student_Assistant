"""
backend/agents/email/tools/analyze_priority.py
----------------------------------------------
Tool phân tích mức độ ưu tiên của email học thuật.
"""
from typing import Literal
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class AnalyzePriorityInput(BaseModel):
    subject: str = Field(description="Tiêu đề email")
    sender: str = Field(description="Người gửi email")
    body: str = Field(description="Nội dung email cần phân tích")

@tool("analyze_priority", args_schema=AnalyzePriorityInput)
def analyze_priority(subject: str, sender: str, body: str) -> str:
    """
    Phân tích nội dung email và đánh giá mức độ ưu tiên:
    - urgent: Khẩn cấp (có deadline rất gần, yêu cầu làm ngay)
    - important: Quan trọng (thông báo thi, lịch học, thông tin từ trường)
    - follow_up: Cần theo dõi/trả lời (có câu hỏi, yêu cầu phản hồi)
    - info: Chỉ là thông tin thông thường
    
    Lưu ý: Tool này hiện tại sẽ phân tích bằng logic rule-based kết hợp keyword, 
    để tích hợp hoàn chỉnh với Agent, bản thân Agent sẽ dùng LLM suy luận, 
    nhưng gọi tool này để chuẩn hoá kết quả.
    """
    text = (subject + " " + body).lower()
    
    if "deadline" in text or "khẩn" in text or "urgent" in text or "gấp" in text or "asap" in text:
        return "urgent"
    
    if "thi" in text or "lịch học" in text or "điểm" in text or "quan trọng" in text or "bắt buộc" in text:
        return "important"
        
    if "trả lời" in text or "phản hồi" in text or "xác nhận" in text or "?" in text:
        return "follow_up"
        
    return "info"
