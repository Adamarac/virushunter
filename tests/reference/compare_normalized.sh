#!/bin/sh
# Compara duas capturas ignorando atribuicao de no e ordem de linha.
#
# Existe para provar que a mudanca de ordem de iteracao entre Python 2 e 3 nao
# altera o conjunto de trabalho. Ver ADR-0010.
#
# Uso:  sh tests/reference/compare_normalized.sh <dirA> <dirB>

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
