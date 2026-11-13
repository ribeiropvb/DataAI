"""Adaptador para a API Chat Completions da OpenAI e serviços compatíveis
(Ollama, OpenRouter, Groq, Gemini via endpoint compatível etc.). Pacote ``openai``, opcional."""
from __future__ import annotations

import json

from .base import LLMResponse, ToolCall, ToolSpec, image_b64


class OpenAIProvider:
    name = "openai"
    supports_images = True

    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None, **client_kwargs):
        try:
            import openai
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Instale o pacote opcional: pip install 'dataai[openai]'") from e
        self.model = model
        kw = dict(client_kwargs)
        if api_key:
            kw["api_key"] = api_key
        if base_url:
            kw["base_url"] = base_url
            self.name = "openai_compatible"
        self.client = openai.OpenAI(**kw)

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
                parts.append({"type": "image_url", "image_url": {"url": f"data:{mt};base64,{data}"}})
        return parts

    def _messages(self, system: str, messages: list[dict]) -> list[dict]:
        out = [{"role": "system", "content": system}]
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": self._content(m["content"])})
            elif m["role"] == "assistant":
                msg = {"role": "assistant", "content": m.get("content") or None}
                if m.get("tool_calls"):
                    msg["tool_calls"] = [{"id": tc.id, "type": "function",
                                          "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)}}
                                         for tc in m["tool_calls"]]
                out.append(msg)
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
        return out

    def chat(self, system: str, messages: list[dict], tools: list[ToolSpec] | None = None,
             max_tokens: int = 4096, temperature: float | None = None) -> LLMResponse:
        kwargs = {"model": self.model, "messages": self._messages(system, messages), "max_tokens": max_tokens}
        if tools:
            kwargs["tools"] = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                                 "parameters": t.parameters}} for t in tools]
        if temperature is not None:
            kwargs["temperature"] = temperature
        r = self.client.chat.completions.create(**kwargs)
        ch = r.choices[0]
        calls = []
        for tc in ch.message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            calls.append(ToolCall(tc.id, tc.function.name, args))
        usage = {"input_tokens": getattr(r.usage, "prompt_tokens", 0) if r.usage else 0,
                 "output_tokens": getattr(r.usage, "completion_tokens", 0) if r.usage else 0}
        return LLMResponse(ch.message.content or "", calls, ch.finish_reason or "", usage, r)
