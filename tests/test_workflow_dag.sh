#!/bin/sh
# Validate the Snakemake DAG without running any bioinformatics tool.
#
# `snakemake -n` resolves the whole dependency graph -- every wildcard, every
# input/output match, every expand() -- and reports what it would run. It needs
# no BLAST, no bowtie2 and no databases, which is the only reason this is
# testable at all (ADR-0009).
#
# What it catches: a rule whose input no other rule produces, a wildcard that
# does not match, a fan-out with the wrong cardinality. What it does not catch:
# whether a command is scientifically correct. For that the reference capture in
# tests/reference/ is the specification.
#
# Slow: installs Snakemake into a throwaway container each run.
#
# Usage:  sh tests/test_workflow_dag.sh
# Exit:   0 DAG resolves with the expected job counts, 1 mismatch, 2 cannot run

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${VH_PY_IMAGE:-python:3.12-slim}

command -v docker >/dev/null 2>&1 || { echo "docker nao encontrado" >&2; exit 2; }

MSYS_NO_PATHCONV=1
MSYS2_ARG_CONV_EXCL='*'
export MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

OUT="$ROOT/.dag_out.txt"
status=0

docker run --rm -v "$ROOT:/repo:ro" "$IMAGE" /bin/sh -c '
set -eu
pip install --quiet snakemake pyyaml >/dev/null 2>&1

mkdir -p /work/fastq && cd /work
cp -r /repo/src /work/src
cp -r /repo/config /work/config
cp -r /repo/workflow /work/workflow

# The fixture is the same one the reference capture uses: two samples, paired
# files, Illumina naming. Compressed here because the workflow expects .gz.
for f in /repo/tests/reference/fixture/fastq/*.fastq; do
  gzip -c "$f" > "/work/fastq/$(basename "$f").gz"
done

snakemake -n -s workflow/Snakefile --cores 1 > dag.txt 2>&1 || {
  echo "FALHA: snakemake -n retornou erro"
  tail -20 dag.txt
  exit 1
}

fail=0
check() {
  rule=$1; expected=$2
  actual=$(awk -v r="$rule" "\$1 == r { print \$2 }" dag.txt | head -1)
  if [ "$actual" != "$expected" ]; then
    echo "FALHA: regra $rule tem $actual jobs, esperado $expected"
    fail=1
  fi
}

# Two samples, 50 query splits. The fan-out cardinality is the thing most likely
# to break silently when a rule is edited.
check host_align        2
check dedup             2
check recode_ids        2
check blast_virus       100
check parse_virus_hits  100
check filter_against_nr 100
check merge_filtered    2
check merge_all_samples 1

total=$(awk "\$1 == \"total\" { print \$2 }" dag.txt | head -1)
if [ "$total" != "326" ]; then
  echo "FALHA: total de $total jobs, esperado 326"
  fail=1
fi

[ "$fail" -eq 0 ] && echo "OK      DAG resolve: $total jobs em 17 regras, 2 amostras x 50 fatias"
exit "$fail"
' > "$OUT" 2>&1 || status=$?

cat "$OUT"
rm -f "$OUT"
exit "$status"
