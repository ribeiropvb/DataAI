"""Execução dos agentes: perfil (agents/*.yaml) + skills (skills/*/SKILL.md) + ferramentas."""
from .profiles import AgentProfile, load_profiles
from .runner import AgentRunner

__all__ = ["AgentProfile", "load_profiles", "AgentRunner"]
