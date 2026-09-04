#!/bin/sh
# Captura a saida do gerador antigo, para validar a migracao de uma rota contra o
# comportamento original. Exige Docker.
#
# O virus_hunter.py foi removido da arvore (ADR-0020) e vem do historico:
#   git show 6961916^:script/virus_hunter.py > /tmp/legacy/virus_hunter.py
#
# Uso: PKG=<raiz>/src sh tests/capture-reference.sh <dir-legado> <config.yaml> <fixture> <saida>
#
# Validado: a recaptura da rota padrao sai identica, byte a byte, aos 56 arquivos
# da referencia congelada que existia em tests/reference/expected/ (git 6961916^).
set -eu
ROOT=$(cd "$(dirname "$0")/../../../../../../.." 2>/dev/null && pwd) || true
LEGACY="$1"; CONFIG="$2"; FIXTURE="$3"; OUT="$4"
IMAGE=${VH_PY_IMAGE:-python:3.12-slim}
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
mkdir -p "$OUT"; find "$OUT" -mindepth 1 -delete 2>/dev/null || true
docker run --rm \
  -v "$LEGACY:/src:ro" -v "$PKG:/pkg:ro" -v "$CONFIG:/cfg.yaml:ro" \
  -v "$FIXTURE:/fixture:ro" -v "$OUT:/out" -w /work "$IMAGE" /bin/sh -c '
set -eu
mkdir -p /fake
printf "#!/bin/sh\necho \"\$1 48 64\"\n" > /fake/ssh
chmod +x /fake/ssh
PATH="/fake:$PATH"; export PATH
cp -r /fixture/fastq /work/fastq
cp /src/*.py /work/
mkdir -p /app/config
cp -r /pkg /app/src
cp /cfg.yaml /app/config/default.yaml
PYTHONPATH=/app/src; export PYTHONPATH
VIRUSHUNTER_CONFIG=/app/config/default.yaml; export VIRUSHUNTER_CONFIG
pip install --quiet pyyaml 2>/dev/null
mkdir -p /mnt && ln -sfn /work /mnt/work
python virus_hunter.py > /out/_stdout.raw 2>/out/_stderr.txt || echo "gerador saiu $?" >> /out/_stderr.txt
grep -v "^{.bsidna" /out/_stdout.raw > /out/_stdout.txt || true
rm -f /out/_stdout.raw
cd /work
for f in *.sh *.txt *.conf *.log; do [ -e "$f" ] && cp "$f" /out/ 2>/dev/null || true; done
rm -f /out/samples.txt /out/server.info
for d in soap_config contig_*; do [ -d "$d" ] && cp -r "$d" /out/ || true; done
'
echo "  artefatos: $(find "$OUT" -type f | wc -l)"
