"""Ciclo de execução de um agente: instruções + tarefa -> chamadas de ferramenta -> envelope JSON final."""
from __future__ import annotations

import json
import re

from ..envelope import envelope, is_valid_envelope
from ..llm.base import LLMProvider
from .profiles import AgentProfile
from .toolbox import Toolbox


def extract_json(text: str) -> dict | None:
    """Extrai o primeiro objeto JSON da resposta (aceita bloco ```json)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [m.group(1)] if m else []
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
        start = text.find("{", start + 1) if not candidates else -1
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


class AgentRunner:
    def __init__(self, profile: AgentProfile, provider: LLMProvider, toolbox: Toolbox):
        self.profile = profile
        self.provider = provider
        self.toolbox = toolbox
        self.transcript: list[dict] = []

    def run(self, task: str, context: dict | None = None) -> dict:
        p = self.profile
        system = p.system_prompt()
        user = task
        if context:
            user += "\n\nContexto (JSON):\n" + json.dumps(context, ensure_ascii=False, default=str)[:60000]
        messages: list[dict] = [{"role": "user", "content": user}]
        tools = self.toolbox.specs(p.tools) if p.tools else None
        usage = {"input_tokens": 0, "output_tokens": 0, "turns": 0}
        retried_json = False
        for _ in range(p.max_turns):
            resp = self.provider.chat(system, messages, tools, max_tokens=p.max_tokens, temperature=p.temperature)
            usage["turns"] += 1
            for k in ("input_tokens", "output_tokens"):
                usage[k] += int(resp.usage.get(k, 0) or 0)
            messages.append({"role": "assistant", "content": resp.text, "tool_calls": resp.tool_calls})
            if resp.tool_calls:
                for tc in resp.tool_calls:
                    out = self.toolbox.call(tc.name, tc.arguments, p.tools)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out})
                if self.toolbox.attachments and getattr(self.provider, "supports_images", False):
                    parts = [{"type": "text", "text": "Imagens geradas pela inspeção (capturas/páginas):"}] + \
                            [{"type": "image", "path": a} for a in self.toolbox.attachments]
                    messages.append({"role": "user", "content": parts})
                self.toolbox.attachments = []
                continue
            obj = extract_json(resp.text or "")
            if obj is not None:
                if "skill_name" not in obj:
                    obj = envelope(p.skills[0] if p.skills else p.id, "completed", obj)
                if is_valid_envelope(obj):
                    self.transcript = messages
                    self.toolbox.ws.add_usage(p.id, usage)
                    obj.setdefault("_agent", p.id)
                    return obj
            if retried_json:
                break
            retried_json = True
            messages.append({"role": "user", "content": "Responda agora somente com o objeto JSON do envelope comum, sem texto fora dele."})
        self.transcript = messages
        self.toolbox.ws.add_usage(p.id, usage)
        return envelope(p.skills[0] if p.skills else p.id, "failed",
                        {"error": "o agente não devolveu um envelope JSON válido dentro do limite de turnos"})
