#!/usr/bin/env python3
"""Exige modo texto em todo `gzip.open` do fecho vivo.

Em Python 3, 'r', 'rb' e modo omitido devolvem bytes; so 'rt' devolve str. Todo
dado comprimido aqui e texto (FASTQ, FASTA, SAM). Ver ADR-0012.
"""

import re
import subprocess
import sys
from pathlib import Path

CALL_RE = re.compile(r"gzip\.(\w+)\s*\(([^)]*)\)")
MODE_RE = re.compile(r"['\"]([rwax]\+?[tb]?)['\"]")


def strip_comment(line):
    return re.sub(r"#.*$", "", line)


def check(path):
    findings = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8", errors="replace")
                                 .splitlines(), start=1):
        code = strip_comment(raw)
        for match in CALL_RE.finditer(code):
            func, args = match.group(1), match.group(2)

            if func != "open":
                findings.append((lineno, raw.strip(),
                                 f"gzip.{func} nao existe"))
                continue

            mode = MODE_RE.search(args)
            if mode is None:
                findings.append((lineno, raw.strip(),
                                 "modo omitido -- gzip devolve bytes por padrao"))
            elif not mode.group(1).endswith("t"):
                m = mode.group(1)
                findings.append((lineno, raw.strip(),
                                 "modo '{}' devolve bytes; use '{}t' (todo dado "
                                 "comprimido aqui e texto)".format(m, m.rstrip("b"))))
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
            for lineno, text, why in findings:
                print(f"        linha {lineno}: {text}")
                print(f"        {why}")

    if not checked:
        print("ERRO: nenhum arquivo verificado", file=sys.stderr)
        return 2

    if not failed:
        print(f"OK      {checked} arquivos -- todo gzip.open usa modo texto")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
