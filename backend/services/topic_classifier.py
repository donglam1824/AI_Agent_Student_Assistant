"""
backend/services/topic_classifier.py
------------------------------------
Dịch vụ phân tích và phân loại chủ đề của tài liệu bằng Gemini.
"""

from typing import List, Dict, Any, Optional
import json
from pydantic import BaseModel, Field
from core.llm_manager import llm_manager
from core.logger import logger

class TopicClassificationResult(BaseModel):
    topic: str = Field(description="Chủ đề chính cụ thể của tài liệu (ví dụ: 'Đại số tuyến tính', 'Cơ sở dữ liệu', 'Lập trình Python', 'Kinh tế vĩ mô', 'Văn học Việt Nam'). Dùng tiếng Việt chính xác.")
    category: str = Field(description="Danh mục tổng quát phù hợp nhất với chủ đề. Chọn một danh mục tổng quan (ví dụ: 'Toán', 'Công nghệ thông tin', 'Kinh tế', 'Văn học', 'Ngôn ngữ', 'Khoa học tự nhiên', 'Khác').")
    tags: List[str] = Field(description="2-3 tags/từ khóa chi tiết liên quan đến tài liệu (ví dụ: ['ma trận', 'định thức'], ['sql', 'postgres'], ['thơ ca', 'văn học hiện đại']).")
    confidence: float = Field(description="Mức độ tự tin của việc phân loại từ 0.0 đến 1.0.")

class TopicClassifier:
    @staticmethod
    def classify(text_sample: str) -> Dict[str, Any]:
        """
        Phân loại chủ đề dựa trên một phần nội dung văn bản của tài liệu.
        """
        if not text_sample or not text_sample.strip():
            return {
                "topic": "Tài liệu trống",
                "category": "Khác",
                "tags": [],
                "confidence": 0.0
            }

        # Lấy nội dung ngắn gọn để tránh quá tải token
        sample = text_sample[:2500]
        
        try:
            llm = llm_manager.get_model(task="rag")
            # Sử dụng structured output
            structured_llm = llm.with_structured_output(TopicClassificationResult)
            
            prompt = f"""
            Hãy phân tích đoạn văn bản mẫu của tài liệu dưới đây và thực hiện phân loại chủ đề cho sinh viên Việt Nam:
            - Xác định chủ đề cụ thể (topic) của tài liệu.
            - Phân vào một danh mục lớn (category) phù hợp.
            - Trích xuất 2-3 tags từ khóa chi tiết.
            - Đánh giá mức độ tự tin (confidence) từ 0.0 đến 1.0.

            Đoạn văn bản mẫu:
            {sample}
            """
            
            result: TopicClassificationResult = structured_llm.invoke(prompt)
            
            return {
                "topic": result.topic,
                "category": result.category,
                "tags": result.tags,
                "confidence": result.confidence
            }
        except Exception as e:
            logger.error(f"TopicClassifier error: {e}. Falling back to default values.")
            # Fallback values
            return {
                "topic": "Chưa xác định",
                "category": "Khác",
                "tags": [],
                "confidence": 0.0
            }
