#!/bin/sh
# Valida o DAG do Snakemake sem executar ferramenta alguma.
#
# `snakemake -n` resolve wildcards, entradas e saidas; e a unica validacao do
# workflow possivel sem BLAST e bancos (ADR-0009). Confere cardinalidade exata,
# que e o que quebra em silencio ao editar uma regra.
#
# Uso:  sh tests/test_workflow_dag.sh

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
cp /repo/tests/reference/configs/denovo.yaml /work/

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
check report_sample     2
check report_all        1
check merge_table       1
check index_page        1
check polya_raw         2
check polya_clean       2
check plot_histogram    4
check sample_blastdb    2
check publish           1

total=$(awk "\$1 == \"total\" { print \$2 }" dag.txt | head -1)
if [ "$total" != "349" ]; then
  echo "FALHA: total de $total jobs, esperado 349"
  fail=1
fi

# A rota denovo -- montagem ensemble SAVaC -- e a configuracao que o metodo
# publicado exige, e nao entra no DAG padrao. Precisa de validacao propria.
snakemake -n -s workflow/Snakefile --configfile denovo.yaml --cores 1 > dag_denovo.txt 2>&1 || {
  echo "FALHA: snakemake -n com denovo retornou erro"
  tail -15 dag_denovo.txt
  exit 1
}

check_denovo() {
  rule=$1; expected=$2
  actual=$(awk -v r="$rule" "\$1 == r { print \$2 }" dag_denovo.txt | head -1)
  if [ "$actual" != "$expected" ]; then
    echo "FALHA: [denovo] regra $rule tem $actual jobs, esperado $expected"
    fail=1
  fi
}

for r in assemble_soap assemble_metavelvet assemble_abyss partition_reads          combine_abyss_chunks collect_contigs combine_contigs cap3_consensus          assembled_contigs; do
  check_denovo "$r" 2
done

# Sem montagem estas regras nao podem aparecer no DAG padrao.
for r in assemble_soap cap3_consensus; do
  if awk -v r="$r" "\$1 == r { print \$2 }" dag.txt | grep -q .; then
    echo "FALHA: regra $r aparece no DAG padrao, onde nao ha montagem"
    fail=1
  fi
done

[ "$fail" -eq 0 ] && echo "OK      DAG resolve nas duas rotas: padrao $total jobs, denovo com SAVaC"
exit "$fail"
' > "$OUT" 2>&1 || status=$?

cat "$OUT"
rm -f "$OUT"
exit "$status"
