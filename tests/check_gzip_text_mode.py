#!/usr/bin/env python3
"""Require gzip streams to declare text mode explicitly.

Under Python 2, gzip.open returned byte strings, and byte strings were str, so
every line could be stripped, split, compared against literals and concatenated
into output without a thought.

Under Python 3 that is no longer true, and the trap is that the obvious modes do
not help: 'r', 'rb' and no mode at all all yield bytes. Only 'rt' yields str.

    gzip.open(f)          -> bytes
    gzip.open(f, 'r')     -> bytes
    gzip.open(f, 'rb')    -> bytes
    gzip.open(f, 'rt')    -> str

The workers here read FASTQ from .gz and immediately do string work on it:
line.strip(), comparisons with '>' or '@', concatenation into text output files.
With bytes that raises TypeError -- loud, unlike the division change, but a hard
blocker all the same.

The rule enforced: every gzip.open in the live closure uses a text mode ('rt',
'wt', 'at'). Every compressed stream this pipeline touches is a text format --
FASTQ, FASTA, SAM -- and every consumer does string work on it, so binary is
never what is wanted here. A genuinely binary use would need this rule revisited
rather than silently exempted.

Note that 'rb' is not an acceptable answer either: it is explicit, but it is
explicitly the wrong thing, and it reads as intentional to a reviewer.

Usage:  python3 tests/check_gzip_text_mode.py [file ...]
        with no arguments, checks the live closure
Exit:   0 clean, 1 finding, 2 bad usage
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
                                 "gzip.%s nao existe" % func))
                continue

            mode = MODE_RE.search(args)
            if mode is None:
                findings.append((lineno, raw.strip(),
                                 "modo omitido -- gzip devolve bytes por padrao"))
            elif not mode.group(1).endswith("t"):
                m = mode.group(1)
                findings.append((lineno, raw.strip(),
                                 "modo '%s' devolve bytes; use '%st' (todo dado "
                                 "comprimido aqui e texto)" % (m, m.rstrip("b"))))
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
            print("ERRO: arquivo nao encontrado: %s" % path, file=sys.stderr)
            return 2
        checked += 1
        findings = check(path)
        if findings:
            failed = True
            print("FALHOU  %s" % path.name)
            for lineno, text, why in findings:
                print("        linha %d: %s" % (lineno, text))
                print("        %s" % why)

    if not checked:
        print("ERRO: nenhum arquivo verificado", file=sys.stderr)
        return 2

    if not failed:
        print("OK      %d arquivos -- todo gzip.open usa modo texto" % checked)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
