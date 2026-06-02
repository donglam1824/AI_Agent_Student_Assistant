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
from core.llm_manager import llm_manager, coerce_message_content
from core.logger import logger

from tools.doc_search.search_documents import search_documents
from tools.doc_search.list_documents import list_documents
from tools.doc_search.import_from_drive import list_drive_documents, guide_drive_import

SYSTEM_PROMPT = """Bạn là trợ lý tìm kiếm tài liệu thông minh dành cho sinh viên đại học Việt Nam.
Bạn giúp sinh viên tìm kiếm thông tin trong tài liệu đã lưu, liệt kê tài liệu,
và hướng dẫn import tài liệu từ Google Drive hoặc OneDrive.

## Quy tắc quan trọng
- Luôn trả lời bằng tiếng Việt, rõ ràng và có cấu trúc.
- KHÔNG BAO GIỜ bịa đặt thông tin. Nếu không tìm thấy, hãy nói thẳng.

## Cách sử dụng tools
1. **Khi sinh viên hỏi kiến thức hoặc nội dung tài liệu** → dùng `search_documents`:
   - Tối ưu câu truy vấn: trích xuất từ khóa ngữ nghĩa ngắn gọn nhất.
   - Ví dụ: "giải thích đạo hàm hàm hợp" → query: "đạo hàm hàm hợp chain rule"
   - Nếu sinh viên nhắc tên tài liệu cụ thể, gọi `list_documents` trước để lấy tên file chính xác.
2. **Khi sinh viên hỏi "tôi có tài liệu nào?"** → dùng `list_documents`.
3. **Khi sinh viên nhắc Google Drive hoặc OneDrive** → dùng `list_drive_documents` để xem
   file đã import, rồi `guide_drive_import` nếu cần hướng dẫn import thêm.

## Cách trả lời sau khi tìm kiếm
- Tổng hợp các đoạn trích tìm được thành câu trả lời mạch lạc.
- Luôn trích nguồn, ví dụ: [1] Từ: giai_tich_co_ban.pdf
- Nếu `search_documents` không trả về kết quả phù hợp, hãy thành thật nói hệ thống
  chưa có tài liệu liên quan và gợi ý sinh viên upload tài liệu qua trang Quản lý Tài liệu.

## Lưu ý
- Việc upload tài liệu được thực hiện qua giao diện web (trang Quản lý Tài liệu), không qua chat.
  Nếu sinh viên muốn upload, hướng dẫn họ vào trang Tài liệu trên sidebar.
- Thời gian hiện tại: {current_time} (UTC)
"""

DOC_SEARCH_TOOLS = [search_documents, list_documents, list_drive_documents, guide_drive_import]


class DocSearchAgent:
    """LangGraph-based Document Search Agent."""

    def __init__(self, user_id: str | None = None) -> None:
        self._user_id = user_id
        self._llm_with_tools = llm_manager.get_with_tools(
            task="rag",
            tools=DOC_SEARCH_TOOLS,
        )
        self._graph = self._build_graph(self._llm_with_tools, DOC_SEARCH_TOOLS)
        logger.info(f"DocSearchAgent initialized – {llm_manager.info()}")

    def _build_graph(self, llm_with_tools, tools) -> StateGraph:
        builder = StateGraph(DocSearchAgentState)
        builder.add_node("reason", make_reason_node(llm_with_tools))
        builder.add_node("tools", ToolNode(tools))
        builder.add_edge(START, "reason")
        builder.add_conditional_edges(
            "reason",
            should_continue,
            {"tools": "tools", "end": END},
        )
        builder.add_edge("tools", "reason")
        return builder.compile()

    def _rewrite_query(self, user_message: str) -> str:
        """Dùng LLM để chuyển câu hỏi tự nhiên thành truy vấn tìm kiếm tối ưu."""
        try:
            llm = llm_manager.get("rag")
            prompt = (
                "Chuyển câu hỏi của sinh viên thành truy vấn tìm kiếm ngữ nghĩa tối ưu "
                "để tìm trong cơ sở dữ liệu tài liệu học tập.\n\n"
                "QUY TẮC:\n"
                "- Trích xuất từ khóa ngữ nghĩa cốt lõi, bỏ từ thừa.\n"
                "- Nếu câu hỏi chung chung (ví dụ: 'tài liệu nói về gì?', 'tóm tắt tài liệu'), "
                "trả về: 'tóm tắt nội dung chính khái niệm định nghĩa mục tiêu chủ đề'\n"
                "- Giữ nguyên thuật ngữ chuyên ngành (cả tiếng Việt và tiếng Anh).\n"
                "- CHỈ trả về chuỗi truy vấn, không giải thích.\n\n"
                f"Câu hỏi: \"{user_message}\"\n"
                "Truy vấn tìm kiếm:"
            )
            response = llm.invoke(prompt)
            rewritten = coerce_message_content(response.content).strip() if hasattr(response, "content") else str(response).strip()
            # Fallback nếu LLM trả về quá ngắn hoặc rỗng
            if len(rewritten) < 3:
                return user_message
            logger.debug(f"Query rewrite: '{user_message}' → '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite failed, using original: {e}")
            return user_message

    def _run_scoped_search(self, user_message: str, source_scope: dict) -> str:
        from services.doc_search_service import get_doc_search_service

        query = self._rewrite_query(user_message)

        context = get_doc_search_service().search(
            query=query,
            user_id=self._user_id,
            source_scope=source_scope,
        )

        if "Không tìm thấy" in context or "KhÃ´ng tÃ¬m tháº¥y" in context:
            return "Mình không tìm thấy nội dung phù hợp trong nguồn tài liệu đã chọn."

        llm = llm_manager.get("rag")
        prompt = (
            "Bạn là trợ lý học tập cho sinh viên đại học. "
            "Người dùng đã giới hạn phạm vi tìm kiếm vào một số tài liệu cụ thể.\n\n"
            "QUY TẮC:\n"
            "- CHỈ trả lời dựa trên context được cung cấp bên dưới. "
            "KHÔNG sử dụng kiến thức ngoài context.\n"
            "- Nếu context không chứa đủ thông tin, nói rõ rằng tài liệu đã chọn "
            "không có nội dung liên quan.\n"
            "- Trích nguồn khi trả lời, ví dụ: [1] Từ: ten_file.pdf\n"
            "- Trả lời bằng tiếng Việt, rõ ràng, có cấu trúc (dùng bullet points, "
            "heading khi phù hợp).\n"
            "- Nếu câu hỏi chung (ví dụ: 'tài liệu nói về gì?'), hãy tóm tắt "
            "các ý chính trong context.\n\n"
            f"Câu hỏi của người dùng: {user_message}\n\n"
            f"Context:\n{context}\n\n"
            "Trả lời:"
        )
        response = llm.invoke(prompt)
        return coerce_message_content(response.content) if hasattr(response, "content") else str(response)

    def run(self, user_message: str, source_scope: dict | None = None) -> str:
        from datetime import datetime, timezone
        if source_scope and source_scope.get("mode") != "all":
            return self._run_scoped_search(user_message, source_scope)

        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        initial_state: DocSearchAgentState = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT.format(current_time=current_time)),
                HumanMessage(content=user_message),
            ],
            "user_request": user_message,
            "action_result": "",
        }

        configurable = {}
        if self._user_id:
            configurable["user_id"] = self._user_id
        if source_scope:
            configurable["source_scope"] = source_scope
        config = {"configurable": configurable} if configurable else None
        logger.info(f"DocSearchAgent.run - user={self._user_id}, query={user_message!r}")
        final_state = self._graph.invoke(initial_state, config=config)
        return final_state["messages"][-1].content
