#!/bin/sh
# Check that workers can still read gzipped FASTQ under Python 3.
#
# Sequencing data arrives compressed -- virus_hunter.py passes .fastq.gz straight
# to these workers -- so this is the normal path, not an edge case.
#
# Under Python 2, gzip.open returned byte strings and byte strings were str, so
# the string work that follows just worked. Under Python 3 the same call returns
# bytes, and the trap is that the obvious modes do not help: 'r', 'rb' and an
# omitted mode all yield bytes. Only 'rt' yields str.
#
# Needs only Python: no BLAST, no bowtie2, no databases.
#
# Usage:  sh tests/test_gzip_input.sh
# Exit:   0 pass, 1 fail, 2 cannot run

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${VH_PY_IMAGE:-python:3.12-slim}

command -v docker >/dev/null 2>&1 || { echo "docker nao encontrado" >&2; exit 2; }

MSYS_NO_PATHCONV=1
MSYS2_ARG_CONV_EXCL='*'
export MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

OUT="$ROOT/.gzip_out.txt"
status=0

# Workers now import virushunter (ADR-0014), so the package has to be on
# PYTHONPATH. Mounted read-only rather than installed: the test then runs
# against the working tree, not against whatever was last pip-installed.
docker run --rm -v "$ROOT/script:/src:ro" -v "$ROOT/src:/pkg:ro" -e PYTHONPATH=/pkg "$IMAGE" /bin/sh -c '
set -eu
cd /tmp

Q="IIIIIIIIIIIIIIIIIIII"
{
  printf "@x1\nACGTACGTACGTACGTACGT\n+\n%s\n" "$Q"
  printf "@x2\nTTTTTTTTTTTTTTTTTTTT\n+\n%s\n" "$Q"
} > in.fq
python -c "
import gzip, shutil
with open(\"in.fq\",\"rb\") as a, gzip.open(\"in.fq.gz\",\"wb\") as b:
    shutil.copyfileobj(a, b)
"

fail=0

run() {
  name=$1; shift
  if ! python "$@" > /dev/null 2>err.txt; then
    echo "FALHA: $name morreu ao ler .gz"
    sed "s/^/    /" err.txt | tail -3
    fail=1
    return 1
  fi
  return 0
}

# fq2fa.py: gz FASTQ -> FASTA
if run "fq2fa.py" /src/fq2fa.py in.fq.gz out.fa 10; then
  n=$(grep -c "^>" out.fa || true)
  if [ "$n" -ne 2 ]; then
    echo "FALHA: fq2fa.py escreveu $n registros, esperado 2"
    fail=1
  fi
  # bytes leaking into text output shows up as a b-prefixed repr
  if grep -q "b." out.fa && grep -qE "^>b.|^b." out.fa; then
    echo "FALHA: fq2fa.py escreveu repr de bytes na saida"
    fail=1
  fi
fi

# fq2faID.py: gz FASTQ -> FASTA with positional identifiers
if run "fq2faID.py" /src/fq2faID.py in.fq.gz lib out2.fa; then
  expected=">lib_0
>lib_1"
  actual=$(grep "^>" out2.fa)
  if [ "$actual" != "$expected" ]; then
    echo "FALHA: identificadores do fq2faID.py inesperados a partir de .gz"
    echo "  obtido : $(echo $actual)"
    fail=1
  fi
fi

# the uncompressed path must keep working too
if run "fq2fa.py (texto)" /src/fq2fa.py in.fq out3.fa 10; then
  if ! cmp -s out.fa out3.fa; then
    echo "FALHA: .gz e texto puro produziram saidas diferentes"
    diff out.fa out3.fa | head -4 | sed "s/^/    /"
    fail=1
  fi
fi

[ "$fail" -eq 0 ] && echo "OK      leitura de .gz preservada: gz e texto puro dao a mesma saida"
exit "$fail"
' > "$OUT" 2>&1 || status=$?

cat "$OUT"
rm -f "$OUT"
exit "$status"
