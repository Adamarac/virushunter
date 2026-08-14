#!/usr/bin/env python3
"""Imprime o fecho vivo: os .py que virus_hunter.py realmente alcanca.

Referencias em codigo comentado sao ignoradas -- o orquestrador carrega muito
codigo morto que nomeia scripts que ninguem invoca. Calculado sob demanda para
nao divergir do fonte.
"""

import re
import sys
from pathlib import Path

ROOTS = ["virus_hunter.py", "get_CPU.py"]
REF_RE = re.compile(r"\b([A-Za-z0-9_]+\.py)\b")
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z0-9_]+)", re.MULTILINE)


def live_source(path):
    """File contents with whole-line comments removed."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def closure(script_dir):
    available = {p.name for p in script_dir.glob("*.py")}
    reached = set(ROOTS)
    frontier = list(ROOTS)

    while frontier:
        path = script_dir / frontier.pop()
        if not path.is_file():
            continue
        source = live_source(path)

        for ref in REF_RE.findall(source):
            if ref in available and ref not in reached:
                reached.add(ref)
                frontier.append(ref)

        for module in IMPORT_RE.findall(source):
            candidate = module + ".py"
            if candidate in available and candidate not in reached:
                reached.add(candidate)
                frontier.append(candidate)

    return sorted(n for n in reached if (script_dir / n).is_file())


def main(argv):
    root = Path(__file__).resolve().parent.parent
    script_dir = Path(argv[1]) if len(argv) > 1 else root / "script"
    if not script_dir.is_dir():
        print(f"diretorio inexistente: {script_dir}", file=sys.stderr)
        return 2

    names = closure(script_dir)
    if not names:
        print("fecho vazio -- diretorio errado?", file=sys.stderr)
        return 2

    # newline='\n' matters: this file is consumed by a shell `while read` inside a
    # Linux container, and Windows CRLF would leave \r on every filename.
    out = sys.stdout
    out.reconfigure(newline="\n")
    for name in names:
        print(name, file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
