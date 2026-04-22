"""
agents/doc_search/agent.py
---------------------------
DocSearchAgent – LangGraph ReAct agent cho tìm kiếm tài liệu.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.doc_search.nodes import make_reason_node, should_continue
from agents.doc_search.state import DocSearchAgentState
from core.llm_manager import llm_manager
from core.logger import logger

from tools.doc_search.upload_document import upload_document
from tools.doc_search.search_documents import search_documents
from tools.doc_search.list_documents import list_documents

SYSTEM_PROMPT = """Bạn là trợ lý tìm kiếm tài liệu thông minh cho sinh viên.
Bạn có thể upload tài liệu mới và tìm kiếm thông tin trong các tài liệu đã lưu (RAG).

Hướng dẫn quan trọng:
- Luôn trả lời bằng tiếng Việt.
- Khi người dùng muốn upload file, hãy dùng `upload_document` với đường dẫn file cung cấp.
- Khi người dùng hỏi về kiến thức hoặc nội dung tài liệu, hãy dùng `search_documents`.
  + Tối ưu câu truy vấn (query) trích xuất thành từ khoá ngữ nghĩa gọn gàng nhất có thể.
  + Nếu người dùng nhắc cấu trúc tên tài liệu cụ thể (như: trong file bài giảng Giải tích, file doc1.txt...), hãy gọi `list_documents` để xem danh sách tên file chính xác rồi truyền vào tham số `document_name` để thu hẹp phạm vi tìm kiếm.
- Có thể dùng `list_documents` để trả lời câu hỏi: Tôi đang có tài liệu nào?
- Sau khi tìm được dữ liệu qua các đoạn trích (context), hãy tổng hợp và trả lời trực tiếp câu hỏi người dùng, ĐẶC BIỆT chú ý trích nguồn (ví dụ: "[1] Từ: giai_tich_co_ban.txt").
- Nếu kết quả tìm kiếm không tìm thấy đoạn văn nào có nghĩa, bạn hãy thành thật trả lời là hệ thống không tìm thấy thông tin hoặc đoạn văn với điểm nội dung đủ cao, thay vì bịa đặt.
- Thời gian hiện tại: {current_time}
"""

DOC_SEARCH_TOOLS = [upload_document, search_documents, list_documents]


class DocSearchAgent:
    """LangGraph-based Document Search Agent."""

    def __init__(self) -> None:
        self._llm_with_tools = llm_manager.get_with_tools(
            task="rag",
            tools=DOC_SEARCH_TOOLS,
        )
        self._graph = self._build_graph()
        logger.info(f"DocSearchAgent initialized – {llm_manager.info()}")

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(DocSearchAgentState)
        builder.add_node("reason", make_reason_node(self._llm_with_tools))
        builder.add_node("tools", ToolNode(DOC_SEARCH_TOOLS))
        builder.add_edge(START, "reason")
        builder.add_conditional_edges(
            "reason",
            should_continue,
            {"tools": "tools", "end": END},
        )
        builder.add_edge("tools", "reason")
        return builder.compile()

    def run(self, user_message: str) -> str:
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        initial_state: DocSearchAgentState = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT.format(current_time=current_time)),
                HumanMessage(content=user_message),
            ],
            "user_request": user_message,
            "action_result": "",
        }

        logger.info(f"DocSearchAgent.run – query: {user_message!r}")
        final_state = self._graph.invoke(initial_state)
        return final_state["messages"][-1].content
