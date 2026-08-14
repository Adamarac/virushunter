#!/bin/sh
# Capture the reference output of the Python 2 generator.
#
# virus_hunter.py does not run the pipeline -- it writes ~40 shell scripts plus
# pipeline_run.sh. Those scripts are the real, complete description of every
# command the pipeline would execute. Capturing them gives us an executable
# specification to hold the migration against, without needing BLAST, bowtie2 or
# any database.
#
# The source is run UNMODIFIED. The only thing the generator needs that we do not
# have is the cluster: serverInfo() shells out to `ssh <node> get_CPU.py <node>`
# to read each node's CPU and RAM. We satisfy that with a fake `ssh` earlier on
# PATH that reports fixed values, so the capture is deterministic. Fixing those
# values also removes the K7 non-determinism (SPAdes memory derived from whichever
# node picked up the job) from the reference.
#
# Usage:  sh tests/reference/capture.sh [outdir]
# Default outdir: tests/reference/expected

set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:-"$ROOT/tests/reference/expected"}
# The frozen reference in expected/ was captured with python:2.7-slim. Once the
# source is migrated the runner must be Python 3, while the reference stays as it
# was -- that comparison is the whole point. Override to re-freeze the reference:
#   VH_PY_IMAGE=python:2.7-slim sh tests/reference/capture.sh
IMAGE=${VH_PY_IMAGE:-python:3.12-slim}

command -v docker >/dev/null 2>&1 || { echo "docker nao encontrado" >&2; exit 2; }

# Git Bash on Windows rewrites arguments that look like absolute POSIX paths
# ("/work" -> "C:/Program Files/Git/work"), which breaks the container paths.
MSYS_NO_PATHCONV=1
MSYS2_ARG_CONV_EXCL='*'
export MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

# Clear the contents rather than the directory itself: on Windows the folder may
# still be held by a previous bind mount or by OneDrive.
mkdir -p "$OUT"
find "$OUT" -mindepth 1 -delete

docker run --rm \
  -v "$ROOT/script:/src:ro" \
  -v "$ROOT/src:/pkg:ro" \
  -v "$ROOT/config:/config:ro" \
  -v "$ROOT/tests/reference/fixture:/fixture:ro" \
  -v "$OUT:/out" \
  -w /work \
  "$IMAGE" /bin/sh -c '
set -eu

# fake ssh: serverInfo() parses "<server> <CPU> <RAM>" from each line
mkdir -p /fake
cat > /fake/ssh <<"EOF"
#!/bin/sh
echo "$1 48 64"
EOF
chmod +x /fake/ssh
PATH="/fake:$PATH"
export PATH

# writable copy of the tree the generator expects
cp -r /fixture/fastq /work/fastq
cp /src/virus_hunter.py /work/

# The generator now reads config/default.yaml through the package (ADR-0015), so
# both have to be reachable, laid out as the loader expects: <root>/config beside
# <root>/src.
mkdir -p /app
cp -r /pkg /app/src
cp -r /config /app/config
PYTHONPATH=/app/src
export PYTHONPATH
pip install --quiet pyyaml 2>/dev/null

# The generator computes wd = "/mnt" + cwd and writes some artefacts through that
# absolute path while writing others relative to cwd. Make both resolve to the
# same directory so nothing is lost.
mkdir -p /mnt
ln -sfn /work /mnt/work

python virus_hunter.py > /out/_stdout.raw 2>/out/_stderr.txt || {
  echo "generator exit=$?" >> /out/_stderr.txt
}

# serverInfo() launches one ssh per node, all appending to server.info in
# parallel, so the order lines land in that file is a race and the SI dict is
# built in a different order every run. SI is only ever read by key, so this
# affects nothing but the diagnostic line that prints it -- drop that line so the
# capture is reproducible. Pre-existing behaviour, not introduced by the migration.
grep -v "^{.bsidna" /out/_stdout.raw > /out/_stdout.txt
rm -f /out/_stdout.raw

# collect every artefact the generator produced, minus the inputs we supplied
cd /work
for f in *.sh *.txt *.conf *.log; do
  [ -e "$f" ] || continue
  cp "$f" /out/ 2>/dev/null || true
done
rm -f /out/samples.txt
[ -d soap_config ] && cp -r soap_config /out/ || true
'

# server.info holds the fake node table; it is an input to the run, not output
rm -f "$OUT/server.info"

echo "referencia capturada em: $OUT"
find "$OUT" -type f | sort | sed 's|^|  |'
