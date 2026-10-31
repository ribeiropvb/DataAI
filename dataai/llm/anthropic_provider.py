"""Adaptador para a API Messages da Anthropic (pacote ``anthropic``, opcional)."""
from __future__ import annotations

import json

from .base import LLMResponse, ToolCall, ToolSpec, image_b64


class AnthropicProvider:
    name = "anthropic"
    supports_images = True

    def __init__(self, model: str, api_key: str | None = None, **client_kwargs):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Instale o pacote opcional: pip install 'dataai[anthropic]'") from e
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key, **client_kwargs) if api_key else anthropic.Anthropic(**client_kwargs)

    @staticmethod
    def _content(content):
        if isinstance(content, str):
            return content
        parts = []
        for p in content:
            if p["type"] == "text":
                parts.append({"type": "text", "text": p["text"]})
            elif p["type"] == "image":
                mt, data = image_b64(p["path"])
                parts.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}})
        return parts

    def _messages(self, messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": self._content(m["content"])})
            elif m["role"] == "assistant":
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list) \
                        and all(b.get("type") == "tool_result" for b in out[-1]["content"]):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        return out

    def chat(self, system: str, messages: list[dict], tools: list[ToolSpec] | None = None,
             max_tokens: int = 4096, temperature: float | None = None) -> LLMResponse:
        kwargs = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": self._messages(messages)}
        if tools:
            kwargs["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]
        if temperature is not None:
            kwargs["temperature"] = temperature
        r = self.client.messages.create(**kwargs)
        text = "".join(b.text for b in r.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, b.input if isinstance(b.input, dict) else json.loads(b.input))
                 for b in r.content if b.type == "tool_use"]
        usage = {"input_tokens": getattr(r.usage, "input_tokens", 0), "output_tokens": getattr(r.usage, "output_tokens", 0)}
        return LLMResponse(text, calls, r.stop_reason or "", usage, r)
