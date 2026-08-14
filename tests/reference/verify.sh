#!/bin/sh
# Compara a saida atual do gerador com a referencia congelada.
#
# _stderr.txt fica fora da comparacao: carrega ruido do ambiente que varia entre
# execucoes. A contagem de artefatos e conferida porque uma captura vazia ja
# passou por "identica" uma vez.
#
# Uso:  sh tests/reference/verify.sh    Exit: 0 identico, 1 divergiu, 2 nao rodou

set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
EXPECTED="$ROOT/tests/reference/expected"
ACTUAL="$ROOT/.ref_verify"

[ -d "$EXPECTED" ] || { echo "referencia ausente: $EXPECTED" >&2; exit 2; }

sh "$ROOT/tests/reference/capture.sh" "$ACTUAL" >/dev/null || {
  echo "captura falhou" >&2; exit 2; }

rm -f "$EXPECTED/_stderr.txt" "$ACTUAL/_stderr.txt" 2>/dev/null || true

# A capture that produced nothing must not read as "identical". This happened
# once: a quoting error made capture.sh emit zero artefacts, and diffing two
# empty directories reported success.
n_exp=$(find "$EXPECTED" -type f | wc -l)
n_act=$(find "$ACTUAL" -type f | wc -l)
if [ "$n_act" -lt 2 ] || [ "$n_exp" -lt 2 ]; then
  echo "FALHOU  captura vazia ou quase vazia (esperado=$n_exp atual=$n_act)" >&2
  echo "        a captura provavelmente nao rodou; ver .ref_verify/_stderr.txt" >&2
  exit 2
fi

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
