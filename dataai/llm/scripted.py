"""Provedor roteirizado para testes: devolve respostas prontas, sem rede."""
from __future__ import annotations

from typing import Callable

from .base import LLMResponse, ToolSpec


class ScriptedProvider:
    name = "scripted"
    model = "scripted"
    supports_images = False

    def __init__(self, responses: list[LLMResponse] | Callable[[str, list[dict], list[ToolSpec] | None], LLMResponse]):
        self._responses = responses
        self.calls: list[dict] = []

    def chat(self, system, messages, tools=None, max_tokens=4096, temperature=None) -> LLMResponse:
        self.calls.append({"system": system, "messages": list(messages), "tools": [t.name for t in tools or []]})
        if callable(self._responses):
            return self._responses(system, messages, tools)
        if not self._responses:
            raise RuntimeError("ScriptedProvider sem respostas restantes")
        return self._responses.pop(0)
