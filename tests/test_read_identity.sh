#!/bin/sh
# Check invariant I1 end to end: a read's identity is its position in the file.
#
# Three scripts build that identity and must agree on the ordinal:
#
#   recodeID.py    @s<n>_<pair>_<library>   "consistent with fq2faID.py"
#   fq2faID.py     ><fileID>_<n>            "consistent with blast_trim.py"
#   blast_trim.py  @s<n>_<pair>_<library>   "consistent with fq2faID.py"
#
# The ordinal is i/4 over the line counter. Under Python 2 that is integer
# division; under Python 3 it is real division, so without the fix these emit
# @s0.0_1_lib and >lib_0.0. Nothing raises. The pipeline runs to completion and
# silently stops matching reads to their pairs.
#
# First behavioural test of a worker in this repository. Needs only Python -- no
# BLAST, no bowtie2, no databases.
#
# Usage:  sh tests/test_read_identity.sh
# Exit:   0 pass, 1 fail, 2 cannot run

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${VH_PY_IMAGE:-python:3.12-slim}

command -v docker >/dev/null 2>&1 || { echo "docker nao encontrado" >&2; exit 2; }

MSYS_NO_PATHCONV=1
MSYS2_ARG_CONV_EXCL='*'
export MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

OUT="$ROOT/.identity_out.txt"
status=0

# Workers now import virushunter (ADR-0014), so the package has to be on
# PYTHONPATH. Mounted read-only rather than installed: the test then runs
# against the working tree, not against whatever was last pip-installed.
docker run --rm -v "$ROOT/script:/src:ro" -v "$ROOT/src:/pkg:ro" -e PYTHONPATH=/pkg "$IMAGE" /bin/sh -c '
set -eu
cd /tmp

# Three 20 bp reads. fq2faID.py skips sequences under 10 bp, so a toy 4 bp read
# would yield an empty FASTA and the test would prove nothing.
Q="IIIIIIIIIIIIIIIIIIII"
{
  printf "@x1\nACGTACGTACGTACGTACGT\n+\n%s\n" "$Q"
  printf "@x2\nTTTTTTTTTTTTTTTTTTTT\n+\n%s\n" "$Q"
  printf "@x3\nGGGGGGGGGGGGGGGGGGGG\n+\n%s\n" "$Q"
} > in.fq
: > empty.tab

python /src/recodeID.py   in.fq out.fq lib 1            > /dev/null
python /src/fq2faID.py    in.fq lib   out.fa            > /dev/null
python /src/blast_trim.py in.fq empty.tab out.trim lib 1 > /dev/null

echo "--- recodeID.py ---";   grep "^@s" out.fq
echo "--- fq2faID.py ---";    grep "^>"  out.fa
echo "--- blast_trim.py ---"; grep "^@s" out.trim.tmp

fail=0

expected="@s0_1_lib
@s1_1_lib
@s2_1_lib"
if [ "$(grep "^@s" out.fq)" != "$expected" ]; then
  echo "FALHA: identificadores do recodeID.py inesperados"
  fail=1
fi

# a fractional ordinal is the exact symptom of the Python 3 division change
for pair in "out.fq:@s" "out.trim.tmp:@s" "out.fa:>lib_"; do
  file=${pair%%:*}; prefix=${pair#*:}
  if grep -qE "^${prefix}[0-9]+\.[0-9]" "$file"; then
    echo "FALHA: $file tem ordinal fracionario (divisao real)"
    fail=1
  fi
done

ord_fq=$(grep "^@s" out.fq       | sed -E "s/^@s([0-9]+)_.*/\1/" | tr "\n" " ")
ord_fa=$(grep "^>"  out.fa       | sed -E "s/^>lib_([0-9]+).*/\1/" | tr "\n" " ")
ord_bt=$(grep "^@s" out.trim.tmp | sed -E "s/^@s([0-9]+)_.*/\1/" | tr "\n" " ")
if [ "$ord_fq" != "$ord_fa" ] || [ "$ord_fq" != "$ord_bt" ]; then
  echo "FALHA: ordinais divergem entre os geradores de identidade"
  echo "  recodeID  : $ord_fq"
  echo "  fq2faID   : $ord_fa"
  echo "  blast_trim: $ord_bt"
  fail=1
fi

[ "$fail" -eq 0 ] && echo "OK      invariante I1: ordinais inteiros e concordantes nos 3 geradores"
exit "$fail"
' > "$OUT" 2>&1 || status=$?

cat "$OUT"
rm -f "$OUT"
exit "$status"
