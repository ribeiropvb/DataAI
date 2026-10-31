"""Copia as skills do DataAI para a pasta de skills de um harness.

    python scripts/install_skills.py              # .claude/skills deste repositório (Claude Code no projeto)
    python scripts/install_skills.py --global     # ~/.claude/skills (todas as pastas)
    python scripts/install_skills.py --dest PASTA # outra pasta (outro harness)

As skills chamam as ferramentas por `python -m dataai ferramenta ...`, então o pacote precisa estar
instalado (`pip install -e .`) no Python que o harness usa.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--global", dest="glob", action="store_true", help="instala em ~/.claude/skills")
    g.add_argument("--dest", default=None, help="pasta de destino")
    args = ap.parse_args()
    dest = Path(args.dest) if args.dest else (Path.home() / ".claude" / "skills" if args.glob else ROOT / ".claude" / "skills")
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for skill in sorted((ROOT / "skills").iterdir()):
        if (skill / "SKILL.md").exists():
            target = dest / skill.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(skill, target)
            n += 1
    print(f"{n} skills instaladas em {dest}")
    try:
        import dataai  # noqa: F401
    except ImportError:
        print("Aviso: o pacote dataai não está instalado neste Python. Rode: pip install -e .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
