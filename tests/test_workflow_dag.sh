#!/bin/sh
# Valida o DAG do Snakemake nas quatro configuracoes, sem executar ferramenta.
#
# `snakemake -n` resolve wildcards, entradas e saidas; e a unica validacao do
# workflow possivel sem BLAST e bancos (ADR-0009). Confere cardinalidade exata,
# que e o que quebra em silencio ao editar uma regra.
#
# Roda no host quando o snakemake esta instalado; senao em container.
#
# Uso:  sh tests/test_workflow_dag.sh
# Exit: 0 as quatro rotas resolvem, 1 divergencia, 2 nao rodou

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK="$ROOT/.dagcheck"

if python -c "import snakemake" 2>/dev/null; then
  RUNNER=host
elif command -v docker >/dev/null 2>&1; then
  RUNNER=docker
else
  echo "nem snakemake no host nem docker" >&2
  exit 2
fi

find "$WORK" -mindepth 1 -delete 2>/dev/null || true
mkdir -p "$WORK/fastq"
cp -r "$ROOT/src" "$ROOT/config" "$ROOT/workflow" "$WORK/"
cp "$ROOT"/tests/reference/configs/*.yaml "$WORK/"

# Mesma fixture da captura de referencia: duas amostras, nomes Illumina.
python - "$ROOT" "$WORK" <<'PY'
import gzip, pathlib, shutil, sys
src = pathlib.Path(sys.argv[1]) / "tests" / "reference" / "fixture" / "fastq"
dst = pathlib.Path(sys.argv[2]) / "fastq"
for f in src.glob("*.fastq"):
    with open(f, "rb") as a, gzip.open(dst / (f.name + ".gz"), "wb") as b:
        shutil.copyfileobj(a, b)
PY

run_dag() {
  config=$1; out=$2
  if [ "$RUNNER" = host ]; then
    (cd "$WORK" && python -m snakemake -n -s workflow/Snakefile \
       ${config:+--configfile "$config"} --cores 1) > "$out" 2>&1 || true
  else
    MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run --rm -v "$WORK:/work" \
      -w /work "${VH_PY_IMAGE:-python:3.12-slim}" /bin/sh -c \
      "pip install --quiet snakemake pyyaml >/dev/null 2>&1; \
       snakemake -n -s workflow/Snakefile ${config:+--configfile $config} --cores 1" \
      > "$out" 2>&1 || true
  fi
}

fail=0

count_of() {
  awk -v r="$2" '$1 == r { print $2 }' "$WORK/dag_$1.txt" | head -1
}

expect() {
  actual=$(count_of "$1" "$2")
  if [ "$actual" != "$3" ]; then
    echo "FALHA: [$1] regra $2 tem ${actual:-0} jobs, esperado $3"
    fail=1
  fi
}

expect_absent() {
  if [ -n "$(count_of "$1" "$2")" ]; then
    echo "FALHA: [$1] regra $2 esta no DAG, onde nao deveria"
    fail=1
  fi
}

# Um total errado significa que uma regra deixou de entrar no DAG, ou entrou onde
# nao devia -- e o que quebra em silencio ao editar uma regra.
check_route() {
  name=$1; config=$2; expected_total=$3
  run_dag "$config" "$WORK/dag_$name.txt"

  if grep -qE "Error|Exception" "$WORK/dag_$name.txt"; then
    echo "FALHA: [$name] snakemake -n reportou erro"
    grep -E "Error|Exception" "$WORK/dag_$name.txt" | head -3 | sed 's/^/    /'
    fail=1
    return
  fi

  total=$(count_of "$name" total)
  if [ "$total" != "$expected_total" ]; then
    echo "FALHA: [$name] total de ${total:-nenhum} jobs, esperado $expected_total"
    fail=1
  fi
}

check_route padrao  ""            349
check_route paired  paired.yaml   355
check_route adaptor adaptor.yaml  357
check_route denovo  denovo.yaml   369

if [ "$fail" -eq 0 ]; then
  # Fan-out da rota padrao: 2 amostras, 50 fatias.
  expect padrao blast_virus       100
  expect padrao filter_against_nr 100
  expect padrao report_sample     2
  expect padrao merge_all_samples 1

  # Paired dobra o que roda por par, e so isso.
  expect paired dedup      4
  expect paired recode_ids 4
  expect padrao dedup      2

  # A remocao de adaptador substitui a recodificacao; as duas nunca coexistem.
  expect adaptor trim_quality  2
  expect adaptor find_adaptors 2
  expect_absent adaptor recode_ids
  expect_absent padrao  trim_quality

  # Montagem so na rota denovo.
  expect denovo assemble_soap  2
  expect denovo cap3_consensus 2
  expect_absent padrao assemble_soap
fi

if [ "$fail" -eq 0 ]; then
  echo "OK      DAG resolve nas 4 rotas ($RUNNER): padrao 349, paired 355, adaptor 357, denovo 369"
  find "$WORK" -mindepth 1 -delete 2>/dev/null || true
fi
exit "$fail"
