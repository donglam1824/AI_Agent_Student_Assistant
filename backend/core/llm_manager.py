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

import re
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import settings
from core.logger import logger


# ── Provider registry ──────────────────────────────────────────────────────────
# Thêm provider mới tại đây, không cần sửa code ở chỗ khác.

def _exception_text(exc: Exception) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(str(current))
        current = current.__cause__ or current.__context__
    return " ".join(parts)


def _is_llm_fallback_error(exc: Exception) -> bool:
    text = _exception_text(exc)
    upper_text = text.upper()
    lower_text = text.lower()
    quota_markers = (
        "429",
        "RESOURCE_EXHAUSTED",
        "QUOTA",
        "RATE_LIMIT",
        "RATE LIMIT",
        "TOO_MANY_REQUESTS",
    )
    if any(marker in upper_text for marker in quota_markers):
        return True
    return (
        "model" in lower_text
        and any(
            marker in lower_text
            for marker in ("not found", "not supported", "not available")
        )
    )


def _extract_retry_delay_seconds(exc: Exception) -> float | None:
    text = _exception_text(exc)
    patterns = (
        r"retryDelay['\"]?\s*[:=]\s*['\"]?([0-9.]+)s",
        r"retry\s+in\s+([0-9.]+)s",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def coerce_message_content(content: Any) -> str:
    """Coerce LangChain message content (which could be string or list) to plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(
                    item.get("text")
                    or item.get("content")
                    or str(item)
                )
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content) if content is not None else ""


class FallbackChatModel:
    """Small proxy that tries the next LLM model on quota/rate-limit errors."""

    _cooldowns: dict[str, float] = {}

    def __init__(self, models: list[tuple[str, Any]]) -> None:
        if not models:
            raise ValueError("FallbackChatModel requires at least one model.")
        self._models = models

    def __repr__(self) -> str:
        names = ", ".join(name for name, _ in self._models)
        return f"FallbackChatModel([{names}])"

    def __getattr__(self, name: str) -> Any:
        return getattr(self._models[0][1], name)

    def _ready_models(self) -> list[tuple[str, Any]]:
        now = time.monotonic()
        ready: list[tuple[str, Any]] = []
        for name, model in self._models:
            cooldown_until = self._cooldowns.get(name, 0)
            if cooldown_until > now:
                continue
            self._cooldowns.pop(name, None)
            ready.append((name, model))

        if ready:
            if ready[0][0] != self._models[0][0]:
                logger.info(
                    "LLM fallback: primary model is cooling down; "
                    f"starting with '{ready[0][0]}'."
                )
            return ready

        logger.warning(
            "LLM fallback: every model is cooling down; retrying primary model."
        )
        return [self._models[0]]

    def _mark_cooldown(self, model_name: str, exc: Exception) -> None:
        delay = _extract_retry_delay_seconds(exc)
        if delay is None:
            delay = max(settings.llm_fallback_cooldown_seconds, 0)
        self._cooldowns[model_name] = time.monotonic() + delay

    def _call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        models = self._ready_models()
        last_error: Exception | None = None
        for index, (model_name, model) in enumerate(models):
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}'.")
                return getattr(model, method_name)(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if _is_llm_fallback_error(exc) and index < len(models) - 1:
                    next_model = models[index + 1][0]
                    self._mark_cooldown(model_name, exc)
                    logger.warning(
                        "LLM fallback: model "
                        f"'{model_name}' failed with quota/rate-limit error; "
                        f"switching to '{next_model}'."
                    )
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("No LLM model was available.")

    async def _acall(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        models = self._ready_models()
        last_error: Exception | None = None
        for index, (model_name, model) in enumerate(models):
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}' async call.")
                return await getattr(model, method_name)(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if _is_llm_fallback_error(exc) and index < len(models) - 1:
                    next_model = models[index + 1][0]
                    self._mark_cooldown(model_name, exc)
                    logger.warning(
                        "LLM fallback: model "
                        f"'{model_name}' async call failed with quota/rate-limit error; "
                        f"switching to '{next_model}'."
                    )
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("No LLM model was available.")

    def _stream_call(self, method_name: str, *args: Any, **kwargs: Any):
        models = self._ready_models()
        for index, (model_name, model) in enumerate(models):
            yielded = False
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}' stream.")
                for chunk in getattr(model, method_name)(*args, **kwargs):
                    yielded = True
                    yield chunk
                return
            except Exception as exc:
                if yielded or not _is_llm_fallback_error(exc) or index >= len(models) - 1:
                    raise
                next_model = models[index + 1][0]
                self._mark_cooldown(model_name, exc)
                logger.warning(
                    "LLM fallback: model "
                    f"'{model_name}' stream failed before output; "
                    f"switching to '{next_model}'."
                )

    async def _astream_call(self, method_name: str, *args: Any, **kwargs: Any):
        models = self._ready_models()
        for index, (model_name, model) in enumerate(models):
            yielded = False
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}' async stream.")
                async for chunk in getattr(model, method_name)(*args, **kwargs):
                    yielded = True
                    yield chunk
                return
            except Exception as exc:
                if yielded or not _is_llm_fallback_error(exc) or index >= len(models) - 1:
                    raise
                next_model = models[index + 1][0]
                self._mark_cooldown(model_name, exc)
                logger.warning(
                    "LLM fallback: model "
                    f"'{model_name}' async stream failed before output; "
                    f"switching to '{next_model}'."
                )

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._call("invoke", *args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        return await self._acall("ainvoke", *args, **kwargs)

    def batch(self, *args: Any, **kwargs: Any) -> Any:
        return self._call("batch", *args, **kwargs)

    async def abatch(self, *args: Any, **kwargs: Any) -> Any:
        return await self._acall("abatch", *args, **kwargs)

    def stream(self, *args: Any, **kwargs: Any):
        yield from self._stream_call("stream", *args, **kwargs)

    async def astream(self, *args: Any, **kwargs: Any):
        async for chunk in self._astream_call("astream", *args, **kwargs):
            yield chunk

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "FallbackChatModel":
        return FallbackChatModel(
            [(name, model.bind_tools(tools, **kwargs)) for name, model in self._models]
        )

    def with_structured_output(
        self,
        schema: Any = None,
        **kwargs: Any,
    ) -> "FallbackChatModel":
        return FallbackChatModel(
            [
                (name, model.with_structured_output(schema, **kwargs))
                for name, model in self._models
            ]
        )


def _build_gemini_model(model_name: str) -> BaseChatModel:
    """Khởi tạo Google Gemini (mặc định: gemini-2.0-flash)."""
    from langchain_google_genai import ChatGoogleGenerativeAI  # lazy import

    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY chưa được cấu hình trong .env. "
            "Thêm dòng: GEMINI_API_KEY=your_api_key"
        )
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.gemini_api_key,
        temperature=0,
        # convert_system_message_to_human=True,  # bỏ comment nếu gặp lỗi system message
    )


def _split_model_names(value: str) -> list[str]:
    names: list[str] = []
    for raw_name in value.split(","):
        name = raw_name.strip()
        if name and name not in names:
            names.append(name)
    return names


def _build_gemini() -> Any:
    """Build Google Gemini with quota-aware model fallbacks."""
    model_names = _split_model_names(
        ",".join((settings.gemini_model, settings.gemini_fallback_models))
    )
    models = [(model_name, _build_gemini_model(model_name)) for model_name in model_names]
    if len(models) == 1:
        return models[0][1]

    logger.info(
        "LLMManager: Gemini fallback chain configured: "
        f"{[model_name for model_name, _ in models]}"
    )
    return FallbackChatModel(models)


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
        self._providers: dict[str, Any] = {}
        # Cho phép override routing từ bên ngoài (tuỳ chỉnh theo dự án)
        self._task_routing: dict[str, str] = task_routing or dict(_DEFAULT_TASK_ROUTING)
        # Provider mặc định đọc từ settings (có thể override qua .env)
        self._default_provider: str = settings.default_llm_provider

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _load_provider(self, name: str) -> Any:
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

    def get(self, task: str = "default") -> Any:
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

    def get_model(self, task: str = "default") -> Any:
        """
        Trả về LLM phù hợp cho tác vụ `task` (alias cho get).
        """
        return self.get(task)

    def get_provider(self, provider_name: str) -> Any:
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
    ) -> Any:
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
