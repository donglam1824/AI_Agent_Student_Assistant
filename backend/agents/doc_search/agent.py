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
from tools.doc_search.import_from_drive import list_drive_documents, guide_drive_import

SYSTEM_PROMPT = """Ban la tro ly tim kiem tai lieu thong minh cho sinh vien.
Ban co the upload tai lieu moi, tim kiem thong tin trong cac tai lieu da luu (RAG),
va huong dan nguoi dung import tai lieu tu Google Drive.

Huong dan quan trong:
- Luon tra loi bang tieng Viet.
- Khi nguoi dung muon upload file, hay dung `upload_document` voi duong dan file cung cap.
- Khi nguoi dung hoi ve kien thuc hoac noi dung tai lieu, hay dung `search_documents`.
  + Toi uu cau truy van (query) trich xuat thanh tu khoa ngu nghia gon nhat co the.
  + Neu nguoi dung nhac ten tai lieu cu the, hay goi `list_documents` truoc de xem ten file chinh xac.
- Co the dung `list_documents` de tra loi: Toi dang co tai lieu nao?
- Khi nguoi dung nhac den Google Drive, tai lieu tren Drive, Google Docs/Sheets/Slides:
  + Goi `list_drive_documents` de xem cac tai lieu Drive da import vao he thong.
  + Neu chua co hoac ho muon import them, goi `guide_drive_import` de huong dan cu the.
- Sau khi tim duoc du lieu qua cac doan trich (context), hay tong hop va tra loi truc tiep,
  dac biet chu y trich nguon (vi du: [1] Tu: giai_tich_co_ban.txt).
- Neu ket qua tim kiem khong thay doan van nao co nghia, hay thanh that tra loi la he thong
  khong tim thay thong tin, thay vi bia dat.
- Thoi gian hien tai: {current_time}
"""

DOC_SEARCH_TOOLS = [upload_document, search_documents, list_documents, list_drive_documents, guide_drive_import]


class DocSearchAgent:
    """LangGraph-based Document Search Agent."""

    def __init__(self, user_id: str | None = None) -> None:
        self._user_id = user_id
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

        config = {"configurable": {"user_id": self._user_id}} if self._user_id else None
        logger.info(f"DocSearchAgent.run - user={self._user_id}, query={user_message!r}")
        final_state = self._graph.invoke(initial_state, config=config)
        return final_state["messages"][-1].content
