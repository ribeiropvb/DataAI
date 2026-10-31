"""Camada de IA independente de provedor.

O resto do código conversa apenas com ``LLMProvider.chat``. Trocar de provedor é configuração:

    Provedores do MVP: Claude (anthropic) e OpenAI. Sem DATAAI_PROVIDER, usa ANTHROPIC_API_KEY ou OPENAI_API_KEY.
    DATAAI_PROVIDER=anthropic | openai | openai_compatible
    DATAAI_MODEL=<id do modelo>
    DATAAI_BASE_URL=<url>       # só para openai_compatible (Ollama, OpenRouter, Gemini etc.)
    DATAAI_API_KEY=<chave>      # ou a variável padrão do provedor (ANTHROPIC_API_KEY, OPENAI_API_KEY)
"""
from .base import LLMProvider, LLMResponse, ToolCall, ToolSpec, get_provider

__all__ = ["LLMProvider", "LLMResponse", "ToolCall", "ToolSpec", "get_provider"]
