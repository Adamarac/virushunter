#!/usr/bin/env python3
"""Rejeita efeito colateral em nivel de modulo.

Verificacao lexica: nunca importa o alvo, que e justamente o que se quer manter
seguro. Vale para modulos importados; workers autonomos fazem trabalho em nivel
de modulo por natureza. Ver ADR-0006.
"""

import re
import sys
from pathlib import Path

DEFAULT_TARGETS = ["script/virus_hunter.py"]

# Calls that reach outside the process. Checked in addition to any function
# the file defines itself.
DANGEROUS = [
    r"os\.system\s*\(",
    r"subprocess\.\w+\s*\(",
    r"\bopen\s*\(",
    r"os\.mkdir\s*\(",
    r"os\.remove\s*\(",
    r"os\.popen\s*\(",
]

DEF_RE = re.compile(r"^def\s+(\w+)\s*\(", re.MULTILINE)


def top_level_statements(lines):
    """Yield (lineno, text) for statements starting at column 0.

    Skips continuation lines -- both backslash continuations and lines inside
    an unclosed bracket -- so multi-line literals such as the `servers=[...]`
    list are treated as a single statement.
    """
    depth = 0
    continued = False
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        starts_statement = (
            depth == 0
            and not continued
            and line[:1] not in ("", " ", "\t", "#")
        )
        if starts_statement:
            yield i, line

        code = re.sub(r"#.*$", "", line)
        code = re.sub(r"'[^']*'|\"[^\"]*\"", "", code)
        depth += code.count("(") + code.count("[") + code.count("{")
        depth -= code.count(")") + code.count("]") + code.count("}")
        depth = max(depth, 0)
        continued = code.rstrip().endswith("\\")


def check(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    defined = set(DEF_RE.findall("".join(lines)))
    patterns = list(DANGEROUS) + [rf"\b{re.escape(n)}\s*\(" for n in sorted(defined)]

    findings = []
    for lineno, text in top_level_statements(lines):
        if text.startswith(("def ", "class ", "import ", "from ")):
            continue
        if text.startswith("if __name__"):
            continue
        for pat in patterns:
            if re.search(pat, text):
                findings.append((lineno, text.strip(), pat))
                break
    return findings


def main(argv):
    targets = argv[1:] or DEFAULT_TARGETS
    root = Path(__file__).resolve().parent.parent

    failed = False
    for name in targets:
        path = root / name if not Path(name).is_absolute() else Path(name)
        if not path.is_file():
            print(f"ERRO: arquivo nao encontrado: {path}", file=sys.stderr)
            return 2

        findings = check(path)
        if findings:
            failed = True
            print(f"FALHOU  {name}")
            for lineno, text, pat in findings:
                print(f"        linha {lineno}: {text}")
                print(f"        efeito colateral em nivel de modulo (padrao: {pat})")
        else:
            print(f"OK      {name} -- nenhum efeito colateral em nivel de modulo")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
