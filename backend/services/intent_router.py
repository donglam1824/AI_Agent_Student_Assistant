import re
import unicodedata
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from cachetools import LRUCache
import threading

from core.llm_manager import llm_manager
from core.logger import logger

class IntentResult(BaseModel):
    intent: Literal["calendar", "note", "email", "docsearch", "teams", "unknown"] = Field(
        description="Phân loại yêu cầu của người dùng vào một trong các nhóm này."
    )
    confidence: float = Field(
        description="Mức độ tự tin của việc phân loại từ 0.0 đến 1.0.",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Giải thích ngắn gọn (1-2 câu) lý do chọn intent này."
    )

class IntentRouter:
    """LLM-first semantic intent router with keyword boosting."""

    def __init__(self, cache_maxsize: int = 256):
        self._cache = LRUCache(maxsize=cache_maxsize)
        self._lock = threading.Lock()
        
        # Keyword lists for boosting
        self.exclude_phrases = (
            "lịch sử", "lich su",
            "lịch sự", "lich su",
            "lịch lãm", "lich lam",
            "lịch thiệp", "lich thiep",
        )
        self.calendar_keywords = (
            "lịch", "lich", "calendar", "thời khóa biểu", "thoi khoa bieu",
            "lịch học", "lich hoc", "cuộc họp", "cuoc hop", "sự kiện",
            "su kien", "hẹn", "hen", "deadline",
        )
        self.note_keywords = (
            "ghi chú", "ghi chu", "note", "lưu lại", "luu lai", "lưu ghi chú",
            "luu ghi chu", "tạo ghi chú", "tao ghi chu", "xem ghi chú",
            "xem ghi chu", "liệt kê ghi chú", "liet ke ghi chu",
        )
        self.email_keywords = (
            "email", "gmail", "hộp thư", "hop thu", "soạn thư", "soan thu",
            "gửi mail", "gui mail", "gửi email", "gui email", "trả lời mail",
            "tra loi mail", "thư phản hồi", "thu phan hoi",
        )
        self.teams_keywords = (
            "microsoft teams", "teams", "lớp teams", "lop teams",
            "kênh teams", "kenh teams", "tin nhắn lớp", "tin nhan lop",
            "bài tập teams", "bai tap teams",
        )
        self.docsearch_keywords = (
            "tài liệu", "tai lieu", "tệp", "tep", "file", "pdf", "docx", "pptx", "txt",
            "upload", "tải lên", "tai len", "đã tải", "da tai", "slide", "powerpoint",
            "giáo trình", "giao trinh", "trong tài liệu", "trong tai lieu",
            "trong file", "trong pdf",
            "tóm tắt chương", "tom tat chuong", "tóm tắt bài", "tom tat bai",
            "tóm tắt môn", "tom tat mon", "giải thích chương", "giai thich chuong",
            "nội dung chương", "noi dung chuong", "ôn tập chương", "on tap chuong",
        )

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text.lower())
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    def _contains_any(self, text: str, keywords: tuple[str, ...]) -> bool:
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text):
                return True
        return False

    def _get_keyword_signals(self, text: str) -> List[str]:
        text_lower = text.lower()
        normalized = self._normalize_text(text)

        for phrase in self.exclude_phrases:
            text_lower = text_lower.replace(phrase, " ")
            normalized = normalized.replace(phrase, " ")

        matched = []
        if self._contains_any(text_lower, self.note_keywords) or self._contains_any(normalized, self.note_keywords):
            matched.append("note")
        if self._contains_any(text_lower, self.email_keywords) or self._contains_any(normalized, self.email_keywords):
            matched.append("email")
        if self._contains_any(text_lower, self.teams_keywords) or self._contains_any(normalized, self.teams_keywords):
            matched.append("teams")
        if self._contains_any(text_lower, self.docsearch_keywords) or self._contains_any(normalized, self.docsearch_keywords):
            matched.append("docsearch")
        if self._contains_any(text_lower, self.calendar_keywords) or self._contains_any(normalized, self.calendar_keywords):
            matched.append("calendar")
            
        return matched

    def classify(self, text: str) -> IntentResult:
        cache_key = self._normalize_text(text).strip()
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        try:
            llm = llm_manager.get_model(task="default")
            structured_llm = llm.with_structured_output(IntentResult)
            
            prompt = f"""Bạn là bộ định tuyến cực kỳ chính xác cho trợ lý sinh viên đại học.
Phân loại câu hỏi của sinh viên vào ĐÚNG 1 nhóm:

1. 'calendar': Xem/tạo/sửa/xóa lịch, thời khóa biểu, cuộc họp, sự kiện, deadline.
2. 'note': Tạo, lưu, xem, liệt kê, quản lý ghi chú cá nhân.
3. 'email': Soạn thư, gửi email, kiểm tra hòm thư, xử lý thư phản hồi.
4. 'docsearch': Hỏi kiến thức, tóm tắt bài học, tìm kiếm nội dung tài liệu, hỏi đáp về chương/môn/slide, hoặc quản lý tài liệu (upload, liệt kê file). Câu hỏi học thuật chung (ví dụ: 'đạo hàm là gì', 'giải thích OOP') cũng thuộc nhóm này.
5. 'teams': Microsoft Teams – lớp học, kênh, tin nhắn, bài tập trên Teams.

Nếu câu hỏi mang tính trò chuyện xã giao hoặc hoàn toàn không liên quan, trả về 'unknown'.

Vài ví dụ dễ nhầm lẫn:
- "Ghi chú lại lịch họp ngày mai": Hành động chính là GHI CHÚ -> intent: 'note'
- "Trong email có nói về deadline nộp bài": Đối tượng chính là EMAIL -> intent: 'email'
- "Định lý pytago là gì": Hỏi kiến thức -> intent: 'docsearch'

Câu hỏi: "{text}"
"""
            
            result: IntentResult = structured_llm.invoke(prompt)
        except Exception as e:
            logger.error(f"LLM Classification error: {e}. Falling back to keywords.")
            result = IntentResult(intent="unknown", confidence=0.0, reasoning="LLM error fallback")

        # Keyword Boosting Logic
        keyword_signals = self._get_keyword_signals(text)
        
        if result.confidence >= 0.8:
            # LLM is very confident, trust it
            pass
        elif 0.5 <= result.confidence < 0.8:
            # LLM is somewhat confident, boost if keyword matches
            if result.intent in keyword_signals:
                result.confidence = 0.85
                result.reasoning += f" [Boosted by keyword: {result.intent}]"
        else:
            # LLM is not confident, rely heavily on keywords if there's a clear signal
            if len(keyword_signals) == 1:
                result.intent = keyword_signals[0] # type: ignore
                result.confidence = 0.9
                result.reasoning = f"Fallback to clear keyword signal: {keyword_signals[0]}"

        with self._lock:
            self._cache[cache_key] = result
            
        return result
