#!/bin/sh
# Re-capture the generator output and compare it against the committed reference.
#
# This is the strongest behavioural check available for the migration. The
# generator's entire job is to emit the shell scripts that describe every command
# the pipeline runs; if the migrated code emits byte-identical scripts, behaviour
# was preserved. It needs no BLAST, no bowtie2 and no databases -- only Docker.
#
# _stderr.txt is excluded from the comparison: it carries environment noise (a
# "find: write error" from the host filesystem, a harmless `rm` complaint) that
# varies between runs while every generated artefact stays identical.
#
# Usage:  sh tests/reference/verify.sh
# Exit:   0 identical, 1 drift, 2 cannot run

set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
EXPECTED="$ROOT/tests/reference/expected"
ACTUAL="$ROOT/.ref_verify"

[ -d "$EXPECTED" ] || { echo "referencia ausente: $EXPECTED" >&2; exit 2; }

sh "$ROOT/tests/reference/capture.sh" "$ACTUAL" >/dev/null || {
  echo "captura falhou" >&2; exit 2; }

rm -f "$EXPECTED/_stderr.txt" "$ACTUAL/_stderr.txt" 2>/dev/null || true

if diff -r "$EXPECTED" "$ACTUAL" > "$ROOT/.ref_diff.txt" 2>&1; then
  n=$(find "$EXPECTED" -type f | wc -l)
  echo "OK      saida do gerador identica a referencia ($n artefatos)"
  rm -rf "$ACTUAL" "$ROOT/.ref_diff.txt"
  exit 0
else
  echo "FALHOU  a saida do gerador divergiu da referencia"
  echo
  echo "  artefatos divergentes:"
  grep -E '^(diff|Only in)' "$ROOT/.ref_diff.txt" \
    | sed -E 's|.*/([^/"]+)"? .*|    \1|; s|^Only in .*: |    ausente/extra: |' \
    | sort -u
  echo
  echo "  primeiras diferencas:"
  grep -vE '^(diff|Only in)' "$ROOT/.ref_diff.txt" | head -12 | sed 's|^|    |'
  echo
  echo "  diff completo: .ref_diff.txt      saida atual: .ref_verify/"
  exit 1
fi
