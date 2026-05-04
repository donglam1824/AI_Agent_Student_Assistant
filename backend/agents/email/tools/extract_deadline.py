"""
backend/agents/email/tools/extract_deadline.py
----------------------------------------------
Tool trích xuất thông tin deadline từ nội dung email học thuật.
"""
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class ExtractDeadlineInput(BaseModel):
    text: str = Field(description="Nội dung cần trích xuất thông tin deadline (thường là nội dung email)")

class DeadlineInfo(BaseModel):
    has_deadline: bool = Field(description="Email có đề cập đến deadline/hạn chót hay không")
    task_name: Optional[str] = Field(None, description="Tên công việc cần làm, ví dụ: 'Nộp báo cáo', 'Đăng ký môn học'")
    deadline_date: Optional[str] = Field(None, description="Ngày hạn chót (định dạng YYYY-MM-DD)")
    deadline_time: Optional[str] = Field(None, description="Giờ hạn chót (định dạng HH:MM), nếu có")

@tool("extract_deadline", args_schema=ExtractDeadlineInput)
def extract_deadline(text: str) -> str:
    """
    Trích xuất thông tin deadline từ văn bản email.
    Sử dụng tool này khi cần phân tích một email xem nó có deadline không và deadline là khi nào.
    Trả về một chuỗi JSON chứa thông tin chi tiết.
    """
    from core.llm_manager import llm_manager
    import json
    
    # Sử dụng LLM với pydantic structured output
    llm = llm_manager.get_model(task="extract_deadline")
    structured_llm = llm.with_structured_output(DeadlineInfo)
    
    prompt = f"""
    Trích xuất thông tin deadline từ đoạn văn bản email dưới đây.
    Hãy chú ý đến ngày, giờ, và công việc cụ thể.
    
    Email:
    {text}
    """
    
    result: DeadlineInfo = structured_llm.invoke(prompt)
    
    return json.dumps({
        "has_deadline": result.has_deadline,
        "task_name": result.task_name,
        "deadline_date": result.deadline_date,
        "deadline_time": result.deadline_time
    }, ensure_ascii=False)
