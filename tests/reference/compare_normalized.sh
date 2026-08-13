#!/bin/sh
# Compare two generator captures ignoring node assignment and line order.
#
# Python 2 and Python 3 iterate dicts differently, so the migrated generator
# assigns samples to cluster nodes in a different order and emits script lines in
# a different sequence. Neither changes what work gets done. This tool exists to
# prove that: it strips the "ssh <node>" prefix and sorts the lines, so what
# remains is the set of commands each capture would run.
#
# Used to justify re-freezing the reference after the Python 3 migration
# (ADR-0010). Keep it: the same question comes back on any change that touches
# scheduling or iteration order.
#
# Usage:  sh tests/reference/compare_normalized.sh <dirA> <dirB>
# Exit:   0 same work set, 1 differs, 2 bad usage

set -eu

[ $# -eq 2 ] || { echo "uso: $0 <dirA> <dirB>" >&2; exit 2; }
A=$1; B=$2
[ -d "$A" ] && [ -d "$B" ] || { echo "diretorio inexistente" >&2; exit 2; }

norm() {
  sed -E 's/ssh bsidna[0-9]+ ?//g; s/\{ time //; s/^[[:space:]]+//; s/[[:space:]]+$//' "$1" \
    | sort
}

same=0; differ=0; only=0
for f in "$A"/*.sh "$A"/*.txt; do
  [ -e "$f" ] || continue
  b=$(basename "$f")
  case "$b" in _stdout.txt|_stderr.txt) continue ;; esac
  if [ ! -f "$B/$b" ]; then
    echo "  so em A: $b"; only=$((only+1)); continue
  fi
  if diff <(norm "$f") <(norm "$B/$b") >/dev/null 2>&1; then
    same=$((same+1))
  else
    differ=$((differ+1))
    echo "  difere: $b"
    diff <(norm "$f") <(norm "$B/$b") | head -4 | sed 's/^/      /'
  fi
done

echo
echo "  mesmo conjunto de trabalho : $same"
echo "  divergentes                : $differ"
[ "$only" -gt 0 ] && echo "  presentes so em A          : $only"

[ "$differ" -eq 0 ] && [ "$only" -eq 0 ]
