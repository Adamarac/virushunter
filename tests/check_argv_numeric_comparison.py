#!/usr/bin/env python3
"""Find command-line arguments compared as numbers but never converted.

sys.argv values are always strings. Under Python 2, comparing a number with a
string does not raise -- the language falls back to an artificial ordering in
which every numeric value sorts before every string. So

    threshold = sys.argv[5]          # '0.01', a string
    if float(hsp.expect) < threshold:  # always True

silently accepts everything. The comparison looks like a filter, reads like a
filter in review, and filters nothing. Under Python 3 the same code raises
TypeError, which is why this survived unnoticed for years.

This check is lexical and never imports its target, so it runs under Python 3
against Python 2 sources. It reports a name bound directly from sys.argv, with
no int()/float() conversion, that later appears in an ordering comparison
(< > <= >=) in the same file. Equality comparisons are ignored: comparing a
string argument with == is normal and correct.

Known finding: E_VALUE_THRESH in blast_filter_NR.py and diamond_filter_NR.py.
This is issue K1 in docs/known-issues.md. The check is expected to FAIL until
that is fixed -- see docs/decisions/0007-inert-evalue-threshold.md.

Usage:  python3 tests/check_argv_numeric_comparison.py [file ...]
Exit:   0 clean, 1 finding, 2 bad usage
"""

import re
import sys
from pathlib import Path

DEFAULT_TARGETS = ["script/blast_filter_NR.py", "script/diamond_filter_NR.py"]

# NAME = sys.argv[...]  with no surrounding conversion call.
ASSIGN_RE = re.compile(
    r"^[ \t]*([A-Za-z_]\w*)[ \t]*=[ \t]*sys\.argv\[", re.MULTILINE
)
CONVERTED_RE = re.compile(r"=[ \t]*(?:int|float|long|Decimal)[ \t]*\([ \t]*sys\.argv\[")


def blank_triple_quoted(text):
    """Blank out triple-quoted regions, preserving line numbering.

    These files embed HTML in triple-quoted strings, and markup such as
    `<input type="text">` otherwise reads as an ordering comparison against a
    variable named `input`.
    """
    out = []
    i, n = 0, len(text)
    delim = None
    while i < n:
        if delim is None:
            if text.startswith(("'''", '"""'), i):
                delim = text[i:i + 3]
                out.append("   ")
                i += 3
                continue
            out.append(text[i])
        else:
            if text.startswith(delim, i):
                out.append("   ")
                delim = None
                i += 3
                continue
            out.append("\n" if text[i] == "\n" else " ")
        i += 1
    return "".join(out)


def strip_noise(line):
    """Remove comments and single-line string literals."""
    line = re.sub(r"#.*$", "", line)
    line = re.sub(r"'[^']*'|\"[^\"]*\"", "''", line)
    return line


def converted_elsewhere(text, name):
    """True if the file converts `name` anywhere, e.g. `int(illumina)`.

    trim_quality.py binds `illumina` straight from sys.argv but passes
    `int(illumina)` at the call site, so the comparison inside the callee runs
    on an int. That is correct code and must not be reported.
    """
    return re.search(
        r"\b(?:int|float|long|Decimal)[ \t]*\([ \t]*\b%s\b" % re.escape(name), text
    ) is not None


def unconverted_argv_names(text):
    names = set()
    for line in text.splitlines():
        code = strip_noise(line)
        if CONVERTED_RE.search(code):
            continue
        m = ASSIGN_RE.match(code)
        if m:
            names.add(m.group(1))
    return names


def ordering_comparisons(text, name):
    """Yield (lineno, text) where `name` takes part in an ordering comparison."""
    pattern = re.compile(
        r"(?:\b%s\b[ \t]*(?:<=|>=|<|>))|(?:(?:<=|>=|<|>)[ \t]*\b%s\b)"
        % (re.escape(name), re.escape(name))
    )
    for lineno, line in enumerate(text.splitlines(), start=1):
        code = strip_noise(line)
        if code.lstrip().startswith("#"):
            continue
        if pattern.search(code):
            yield lineno, line.strip()


def check(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = blank_triple_quoted(raw)
    raw_lines = raw.splitlines()

    findings = []
    for name in sorted(unconverted_argv_names(text)):
        if converted_elsewhere(text, name):
            continue
        for lineno, _ in ordering_comparisons(text, name):
            findings.append((name, lineno, raw_lines[lineno - 1].strip()))
    return findings


def main(argv):
    targets = argv[1:] or DEFAULT_TARGETS
    root = Path(__file__).resolve().parent.parent

    failed = False
    for name in targets:
        path = root / name if not Path(name).is_absolute() else Path(name)
        if not path.is_file():
            print("ERRO: arquivo nao encontrado: %s" % path, file=sys.stderr)
            return 2

        findings = check(path)
        if findings:
            failed = True
            print("FALHOU  %s" % name)
            for var, lineno, line in findings:
                print("        linha %d: %s" % (lineno, line))
                print("        '%s' vem de sys.argv (string) e nunca e convertido;" % var)
                print("        sob Python 2 esta comparacao e sempre verdadeira")
        else:
            print("OK      %s -- nenhum argumento comparado sem conversao" % name)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
