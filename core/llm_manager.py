"""
core/llm_manager.py
--------------------
LLMManager – Quản lý và định tuyến các LLM provider theo loại tác vụ.

Mục tiêu:
  - Một điểm duy nhất để lấy LLM instance trong toàn bộ hệ thống.
  - Hỗ trợ nhiều provider: Gemini, OpenAI, Ollama, ...
  - Cho phép route từng tác vụ (calendar, rag, email, ...) sang LLM tốt nhất.
  - Lazy init: provider chỉ được khởi tạo khi lần đầu dùng đến.

Cách dùng:
    from core.llm_manager import llm_manager

    llm = llm_manager.get("calendar")           # lấy LLM cho tác vụ lịch
    llm_with_tools = llm_manager.get_with_tools("calendar", tools)
    llm = llm_manager.get_provider("openai")    # lấy trực tiếp theo tên provider
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import settings
from core.logger import logger


# ── Provider registry ──────────────────────────────────────────────────────────
# Thêm provider mới tại đây, không cần sửa code ở chỗ khác.

def _build_gemini() -> BaseChatModel:
    """Khởi tạo Google Gemini (mặc định: gemini-2.0-flash)."""
    from langchain_google_genai import ChatGoogleGenerativeAI  # lazy import

    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY chưa được cấu hình trong .env. "
            "Thêm dòng: GEMINI_API_KEY=your_api_key"
        )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0,
        # convert_system_message_to_human=True,  # bỏ comment nếu gặp lỗi system message
    )


def _build_openai() -> BaseChatModel:
    """Khởi tạo OpenAI GPT (fallback hoặc tác vụ đặc thù)."""
    from langchain_openai import ChatOpenAI  # lazy import

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY chưa được cấu hình trong .env. "
            "Thêm dòng: OPENAI_API_KEY=your_api_key"
        )
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


def _build_ollama() -> BaseChatModel:
    """Khởi tạo Ollama (chạy local, miễn phí hoàn toàn)."""
    from langchain_ollama import ChatOllama  # lazy import – cần pip install langchain-ollama

    return ChatOllama(model="llama3", temperature=0)


# Map tên provider → hàm factory
_PROVIDER_FACTORIES: dict[str, Any] = {
    "gemini": _build_gemini,
    "openai": _build_openai,
    "ollama": _build_ollama,
}


# ── Task → Provider routing ────────────────────────────────────────────────────
# Điều chỉnh bảng này khi bạn tìm được LLM tốt hơn cho từng tác vụ.
# Key "default" là fallback khi không tìm thấy task trong bảng.

_DEFAULT_TASK_ROUTING: dict[str, str] = {
    # Tác vụ lịch – cần gọi tool chính xác → Gemini Flash đủ tốt và nhanh
    "calendar": "gemini",
    # RAG / tìm kiếm tài liệu – context window lớn → Gemini
    "rag": "gemini",
    # Gửi/phân loại email – viết văn bản → Gemini
    "email": "gemini",
    # Ghi chú – yêu cầu thấp → Gemini
    "notes": "gemini",
    # Nhắc nhở – đơn giản → Gemini
    "reminder": "gemini",
    # Tác vụ yêu cầu reasoning phức tạp → chuyển OpenAI khi cần
    "reasoning": "openai",
    # Fallback cho mọi task không có trong bảng
    "default": "gemini",
}


# ── LLMManager ────────────────────────────────────────────────────────────────

class LLMManager:
    """
    Quản lý vòng đời và routing các LLM provider.

    Attributes:
        _providers: Cache {provider_name -> instance} – lazy init.
        _task_routing: Bảng ánh xạ {task_name -> provider_name}.
    """

    def __init__(
        self,
        task_routing: dict[str, str] | None = None,
    ) -> None:
        self._providers: dict[str, BaseChatModel] = {}
        # Cho phép override routing từ bên ngoài (tuỳ chỉnh theo dự án)
        self._task_routing: dict[str, str] = task_routing or dict(_DEFAULT_TASK_ROUTING)
        # Provider mặc định đọc từ settings (có thể override qua .env)
        self._default_provider: str = settings.default_llm_provider

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _load_provider(self, name: str) -> BaseChatModel:
        """Lazy-init một provider theo tên, cache lại để tái sử dụng."""
        if name not in self._providers:
            factory = _PROVIDER_FACTORIES.get(name)
            if factory is None:
                raise ValueError(
                    f"Provider '{name}' không được hỗ trợ. "
                    f"Danh sách hỗ trợ: {list(_PROVIDER_FACTORIES.keys())}"
                )
            logger.info(f"LLMManager: khởi tạo provider '{name}'.")
            self._providers[name] = factory()
        return self._providers[name]

    def _resolve_provider(self, task: str) -> str:
        """Tra bảng routing, fallback về default nếu không tìm thấy."""
        provider = self._task_routing.get(task) or self._task_routing.get("default")
        if provider is None:
            provider = self._default_provider
        return provider

    # ── Public API ─────────────────────────────────────────────────────────────

    def get(self, task: str = "default") -> BaseChatModel:
        """
        Trả về LLM phù hợp cho tác vụ `task`.

        Args:
            task: Tên tác vụ – "calendar", "rag", "email", "notes", ...

        Returns:
            BaseChatModel đã sẵn sàng dùng.
        """
        provider_name = self._resolve_provider(task)
        logger.debug(f"LLMManager.get(task={task!r}) → provider={provider_name!r}")
        return self._load_provider(provider_name)

    def get_provider(self, provider_name: str) -> BaseChatModel:
        """
        Lấy trực tiếp LLM theo tên provider (bỏ qua routing).

        Args:
            provider_name: "gemini" | "openai" | "ollama"
        """
        return self._load_provider(provider_name)

    def get_with_tools(
        self,
        task: str,
        tools: list[Any],
    ) -> BaseChatModel:
        """
        Trả về LLM đã bind tools – tiện dùng trong agent init.

        Args:
            task: Tên tác vụ.
            tools: Danh sách LangChain tools.

        Returns:
            LLM đã `.bind_tools(tools)`.
        """
        llm = self.get(task)
        return llm.bind_tools(tools)

    def set_routing(self, task: str, provider_name: str) -> None:
        """
        Cập nhật routing lúc runtime (dùng trong test hoặc config động).

        Args:
            task: Tên tác vụ cần override.
            provider_name: Provider mới.
        """
        if provider_name not in _PROVIDER_FACTORIES:
            raise ValueError(
                f"Provider '{provider_name}' không hợp lệ. "
                f"Chọn: {list(_PROVIDER_FACTORIES.keys())}"
            )
        logger.info(f"LLMManager: routing '{task}' → '{provider_name}'")
        self._task_routing[task] = provider_name
        # Nếu provider mới chưa init, reset để trigger lazy-init lần sau
        # (không force init ngay để tránh lỗi khi chưa có API key)

    def info(self) -> dict[str, Any]:
        """Trả về trạng thái hiện tại – dùng cho debug/logging."""
        return {
            "default_provider": self._default_provider,
            "task_routing": self._task_routing,
            "loaded_providers": list(self._providers.keys()),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────
# Import dòng này ở mọi nơi cần dùng LLM:
#   from core.llm_manager import llm_manager
llm_manager = LLMManager()
