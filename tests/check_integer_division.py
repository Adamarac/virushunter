#!/usr/bin/env python3
"""Find divisions by an integer literal that were integer division under Python 2.

In Python 2 `7/4` is 1. In Python 3 it is 1.75. The operator did not change
spelling, so a migration that only fixes syntax leaves every one of these
silently returning a different value.

This codebase cannot absorb that. Read identity is the read's position in the
file (invariant I1): recodeID.py computes `lineno = i/4` and emits
`@s<lineno>_<pair>_<library>`. Under Python 3 that becomes `@s1.0_1_lib`, and
every downstream consumer -- pair lookup, virus grouping, linecache retrieval --
silently fails to match. fq2faID.py builds the FASTA side of the same identifier
and has to agree with it exactly.

The rule enforced: in the live closure, a division involving an integer literal
must say what it means -- `//` for integer division, or `float()` on an operand
for real division. A bare `/` is rejected.

Deliberately strict. Being explicit costs one character and removes a whole class
of defect that produces plausible wrong output rather than an error.

Usage:  python3 tests/check_integer_division.py [file ...]
        with no arguments, checks the live closure
Exit:   0 clean, 1 finding, 2 bad usage
"""

import re
import subprocess
import sys
from pathlib import Path

# X / 3   or   3 / X   -- an integer literal on either side
DIV_RE = re.compile(r"(?<![/\w.])(\w+|\))\s*/\s*(\d+)(?![\d.])|(?<![/\w.])(\d+)\s*/\s*(\w+)")


def strip_noise(line):
    line = re.sub(r"#.*$", "", line)
    line = re.sub(r"'[^']*'|\"[^\"]*\"", "''", line)
    return line


def check(path):
    findings = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8", errors="replace")
                                 .splitlines(), start=1):
        code = strip_noise(raw)
        if "/" not in code:
            continue
        # already explicit
        if "//" in code or "float(" in code:
            continue
        if DIV_RE.search(code):
            findings.append((lineno, raw.strip()))
    return findings


def live_closure(root):
    out = subprocess.run(
        [sys.executable, str(root / "tests" / "live_closure.py")],
        capture_output=True, text=True,
    )
    return [n for n in out.stdout.split() if n]


def main(argv):
    root = Path(__file__).resolve().parent.parent

    if len(argv) > 1:
        targets = [Path(a) if Path(a).is_absolute() else root / a for a in argv[1:]]
    else:
        names = live_closure(root)
        if not names:
            print("ERRO: nao foi possivel calcular o fecho vivo", file=sys.stderr)
            return 2
        targets = [root / "script" / n for n in names]

    failed = False
    checked = 0
    for path in targets:
        if not path.is_file():
            print(f"ERRO: arquivo nao encontrado: {path}", file=sys.stderr)
            return 2
        checked += 1
        findings = check(path)
        if findings:
            failed = True
            print(f"FALHOU  {path.name}")
            for lineno, text in findings:
                print(f"        linha {lineno}: {text}")
                print("        divisao por literal inteiro sem '//' nem float()")

    if not checked:
        print("ERRO: nenhum arquivo verificado", file=sys.stderr)
        return 2

    if not failed:
        print(f"OK      {checked} arquivos -- nenhuma divisao ambigua")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
