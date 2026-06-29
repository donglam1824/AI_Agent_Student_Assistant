"""
Quản lý và định tuyến LLM client (Gemini, OpenAI, Ollama...) theo từng loại task.
Hỗ trợ lazy load và tự động fallback.
"""

from __future__ import annotations

import re
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import settings
from core.logger import logger


# Đăng ký các provider mới tại đây

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
    """Ép kiểu nội dung tin nhắn LangChain (chuỗi/danh sách) thành chuỗi thường"""
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
    """Proxy tự động chuyển sang model dự phòng khi lỗi quota/rate-limit"""

    _cooldowns: dict[str, float] = {}

    def __init__(
        self,
        model_factories: list[tuple[str, Callable[[], Any]]],
        bound_tools: list[tuple[list[Any], dict[str, Any]]] | None = None,
        structured_output: tuple[Any, dict[str, Any]] | None = None,
    ) -> None:
        if not model_factories:
            raise ValueError("FallbackChatModel requires at least one model factory.")
        self._model_factories = model_factories
        self._bound_tools = bound_tools or []
        self._structured_output = structured_output
        self._instances: dict[str, Any] = {}

    def __repr__(self) -> str:
        names = ", ".join(name for name, _ in self._model_factories)
        return f"FallbackChatModel([{names}])"

    def _get_model_instance(self, name: str, factory: Callable[[], Any]) -> Any:
        if name not in self._instances:
            model = factory() if callable(factory) else factory
            for tools, kwargs in self._bound_tools:
                model = model.bind_tools(tools, **kwargs)
            if self._structured_output:
                schema, kwargs = self._structured_output
                model = model.with_structured_output(schema, **kwargs)
            self._instances[name] = model
        return self._instances[name]

    def __getattr__(self, name: str) -> Any:
        primary_name, primary_factory = self._model_factories[0]
        primary_instance = self._get_model_instance(primary_name, primary_factory)
        return getattr(primary_instance, name)

    def _ready_models(self) -> list[tuple[str, Callable[[], Any]]]:
        now = time.monotonic()
        ready: list[tuple[str, Callable[[], Any]]] = []
        for name, factory in self._model_factories:
            cooldown_until = self._cooldowns.get(name, 0)
            if cooldown_until > now:
                continue
            self._cooldowns.pop(name, None)
            ready.append((name, factory))

        if ready:
            if ready[0][0] != self._model_factories[0][0]:
                logger.info(
                    "LLM fallback: primary model is cooling down; "
                    f"starting with '{ready[0][0]}'."
                )
            return ready

        logger.warning(
            "LLM fallback: every model is cooling down; retrying primary model."
        )
        return [self._model_factories[0]]

    def _mark_cooldown(self, model_name: str, exc: Exception) -> None:
        delay = _extract_retry_delay_seconds(exc)
        if delay is None:
            delay = max(settings.llm_fallback_cooldown_seconds, 0)
        self._cooldowns[model_name] = time.monotonic() + delay

    def _call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        models = self._ready_models()
        last_error: Exception | None = None
        for index, (model_name, factory) in enumerate(models):
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}'.")
                model = self._get_model_instance(model_name, factory)
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
        for index, (model_name, factory) in enumerate(models):
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}' async call.")
                model = self._get_model_instance(model_name, factory)
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
        for index, (model_name, factory) in enumerate(models):
            yielded = False
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}' stream.")
                model = self._get_model_instance(model_name, factory)
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
        for index, (model_name, factory) in enumerate(models):
            yielded = False
            try:
                if index > 0:
                    logger.info(f"LLM fallback: trying '{model_name}' async stream.")
                model = self._get_model_instance(model_name, factory)
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
        new_bound = self._bound_tools.copy()
        new_bound.append((tools, kwargs))
        return FallbackChatModel(
            self._model_factories,
            bound_tools=new_bound,
            structured_output=self._structured_output,
        )

    def with_structured_output(
        self,
        schema: Any = None,
        **kwargs: Any,
    ) -> "FallbackChatModel":
        return FallbackChatModel(
            self._model_factories,
            bound_tools=self._bound_tools,
            structured_output=(schema, kwargs),
        )


def _build_gemini_model(model_name: str) -> BaseChatModel:
    """Khởi tạo model Gemini"""
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
        max_retries=0, # Tắt retry để kích hoạt fallback ngay
    )


def _split_model_names(value: str) -> list[str]:
    names: list[str] = []
    for raw_name in value.split(","):
        name = raw_name.strip()
        if name and name not in names:
            names.append(name)
    return names


def _build_gemini() -> Any:
    """Khởi tạo Gemini kèm cơ chế fallback"""
    model_names = _split_model_names(
        ",".join((settings.gemini_model, settings.gemini_fallback_models))
    )
    factories = [(model_name, lambda n=model_name: _build_gemini_model(n)) for model_name in model_names]

    if len(factories) > 1:
        logger.info(
            "LLMManager: Gemini fallback chain configured: "
            f"{model_names}"
        )
    # Luôn bọc trong FallbackChatModel để tận dụng cơ chế lazy loading
    return FallbackChatModel(factories)


def _build_openai() -> Any:
    """Khởi tạo model OpenAI"""
    def _factory():
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
            max_retries=0, # Tắt retry để báo lỗi nhanh (fail-fast)
        )
    return FallbackChatModel([(settings.openai_model, _factory)])


def _build_ollama() -> Any:
    """Khởi tạo Ollama chạy local"""
    def _factory():
        from langchain_ollama import ChatOllama  # lazy import

        return ChatOllama(model="llama3", temperature=0)
    return FallbackChatModel([("llama3", _factory)])
_PROVIDER_FACTORIES = {
    "gemini": _build_gemini,
    "openai": _build_openai,
    "ollama": _build_ollama,
}


# Cấu hình routing task mặc định
_DEFAULT_TASK_ROUTING: dict[str, str] = {
    "calendar": "gemini",
    "rag": "gemini",
    "email": "gemini",
    "notes": "gemini",
    "reminder": "gemini",
    "reasoning": "openai", # Lý luận phức tạp dùng OpenAI
    "default": "gemini",
}


# ── LLMManager ────────────────────────────────────────────────────────────────

class LLMManager:
    """Quản lý vòng đời và routing các LLM client"""

    def __init__(
        self,
        task_routing: dict[str, str] | None = None,
    ) -> None:
        self._providers: dict[str, Any] = {}
        self._task_routing: dict[str, str] = task_routing or dict(_DEFAULT_TASK_ROUTING)
        self._default_provider: str = settings.default_llm_provider

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _load_provider(self, name: str) -> Any:
        """Khởi tạo lazy và cache provider"""
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
        """Tìm provider theo task (fallback về default)"""
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
        """Lấy LLM đã được bind kèm tools"""
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
        # Reset để trigger lazy-init sau (tránh lỗi API key nếu init ngay)

    def info(self) -> dict[str, Any]:
        """Trả về trạng thái hiện tại – dùng cho debug/logging."""
        return {
            "default_provider": self._default_provider,
            "task_routing": self._task_routing,
            "loaded_providers": list(self._providers.keys()),
        }


# Singleton instance
llm_manager = LLMManager()
