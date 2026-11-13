"""Envelope comum de saída das skills (skills/README.md)."""
from __future__ import annotations

from typing import Any

STATUSES = ("completed", "needs_clarification", "blocked", "failed")


def warning(code: str, message: str, evidence_refs: list[str] | None = None) -> dict:
    return {"code": code, "message": message, "evidence_refs": evidence_refs or []}


def question(question_id: str, text: str, why: str, options: list[str] | None = None,
             default: str | None = None) -> dict:
    return {
        "question_id": question_id,
        "question": text,
        "why_it_matters": why,
        "options": options or [],
        "default_if_unanswered": default,
    }


def envelope(skill_name: str, status: str = "completed", result: Any = None,
             warnings: list | None = None, questions: list | None = None,
             evidence_refs: list | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status inválido: {status}")
    questions = questions or []
    if questions and status == "completed":
        status = "needs_clarification"
    return {
        "skill_name": skill_name,
        "status": status,
        "result": result if result is not None else {},
        "warnings": warnings or [],
        "questions": questions,
        "evidence_refs": evidence_refs or [],
    }


def is_valid_envelope(obj: Any) -> bool:
    keys = {"skill_name", "status", "result", "warnings", "questions", "evidence_refs"}
    return isinstance(obj, dict) and keys <= set(obj) and obj["status"] in STATUSES
