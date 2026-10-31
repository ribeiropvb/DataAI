"""Tipos comuns e fábrica de provedores."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON Schema do objeto de argumentos


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = ""
    usage: dict = field(default_factory=dict)  # {"input_tokens": int, "output_tokens": int}
    raw: Any = None


class LLMProvider(Protocol):
    """Mensagens internas (formato neutro):

    - ``{"role": "user", "content": str | [{"type": "text", "text": ...}, {"type": "image", "path": ...}]}``
    - ``{"role": "assistant", "content": str, "tool_calls": [ToolCall, ...]}``
    - ``{"role": "tool", "tool_call_id": str, "name": str, "content": str}``
    """

    name: str
    model: str
    supports_images: bool

    def chat(self, system: str, messages: list[dict], tools: list[ToolSpec] | None = None,
             max_tokens: int = 4096, temperature: float | None = None) -> LLMResponse: ...


class ProviderConfigError(RuntimeError):
    pass


DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-5"}


def detect_provider() -> str | None:
    """Provedor pela configuração: DATAAI_PROVIDER ou, sem ela, pela chave existente (Claude tem prioridade)."""
    name = (os.environ.get("DATAAI_PROVIDER") or "").strip().lower()
    if name:
        return name
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def get_provider(name: str | None = None, model: str | None = None, **kwargs) -> LLMProvider:
    name = (name or detect_provider() or "").strip().lower()
    if not name:
        raise ProviderConfigError("Provedor de IA não configurado. Defina ANTHROPIC_API_KEY (Claude) ou OPENAI_API_KEY "
                                  "(OpenAI), ou DATAAI_PROVIDER, ou rode com --no-llm.")
    model = model or os.environ.get("DATAAI_MODEL") or DEFAULT_MODELS.get(name)
    if not model:
        raise ProviderConfigError("Defina DATAAI_MODEL com o identificador do modelo escolhido.")
    api_key = kwargs.pop("api_key", None) or os.environ.get("DATAAI_API_KEY")
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(model, api_key=api_key, **kwargs)
    if name in ("openai", "openai_compatible"):
        from .openai_provider import OpenAIProvider
        base_url = kwargs.pop("base_url", None) or os.environ.get("DATAAI_BASE_URL")
        if name == "openai_compatible" and not base_url:
            raise ProviderConfigError("openai_compatible exige DATAAI_BASE_URL.")
        return OpenAIProvider(model, api_key=api_key, base_url=base_url, **kwargs)
    raise ProviderConfigError(f"Provedor desconhecido: {name}. Use anthropic, openai ou openai_compatible.")


def image_b64(path: str) -> tuple[str, str]:
    import base64
    import mimetypes
    mt = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return mt, base64.b64encode(f.read()).decode()
