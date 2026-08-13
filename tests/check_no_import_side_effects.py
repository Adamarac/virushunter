#!/usr/bin/env python3
"""Guard against side effects at module level.

The pipeline is written in Python 2, which is not installed on most machines
today, so this check is deliberately lexical: it reads the source as text and
never imports or parses it. That is the point -- importing the file is the very
thing we are trying to keep safe.

What it enforces: no statement at column 0 may invoke a call. A module that only
defines functions and binds literals can be imported for inspection or testing
without reaching the network or the filesystem.

Scope: this applies to modules that get imported. Most workers in script/ are
standalone programs that are only ever executed, and doing their work at module
level is unremarkable for those -- running this check against them reports
findings that are not defects. The targets that matter are the orchestrator and
anything imported from it.

Limitation: it does not follow imports, so it checks each file on its own. A
clean file that imports a dirty one still pays that file's side effects. Pass
every module you care about, not just the entry point.

Background: virus_hunter.py used to run `SI=serverInfo()` at module level, which
opened SSH connections to twenty nodes on import. firstpage.py imports that
module, so the final reporting step of every run inherited the behaviour, and no
part of the codebase could be imported or tested off-cluster.
See docs/decisions/0006-no-import-side-effects.md.

Usage:  python3 tests/check_no_import_side_effects.py [file ...]
Exit:   0 clean, 1 side effect found, 2 bad usage
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
