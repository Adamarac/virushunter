#!/bin/sh
# Start every worker in the live closure under Python 3 and check how it fails.
#
# The reference harness (tests/reference/) covers the generator only. The ~45
# worker scripts have no behavioural coverage, so this is the cheapest check that
# still says something real: run each one with no arguments and look at the
# exception.
#
# A worker that reaches its argument handling and dies on IndexError has imported
# cleanly, resolved its names and executed its module-level code under Python 3.
# A NameError, AttributeError, SyntaxError or ImportError instead means an
# unmigrated API is still in a path that runs -- exactly what a syntax-only
# migration can miss.
#
# It does NOT check that a worker produces correct output. It cannot: that needs
# BLAST, bowtie2 and the databases (ADR-0009).
#
# Runs inside a container against a throwaway working directory, because several
# workers do file I/O at module level and some of the wider codebase shells out.
#
# Usage:  sh tests/smoke_workers.sh
# Exit:   0 all clean, 1 suspicious files found, 2 cannot run

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${VH_PY_IMAGE:-python:3.12-slim}
CLOSURE="$ROOT/.closure_clean.txt"

command -v docker >/dev/null 2>&1 || { echo "docker nao encontrado" >&2; exit 2; }

# Recompute the live closure: which .py files virus_hunter.py reaches, following
# references in live code only. Kept out of version control so it cannot go stale
# against the source.
#
# Done before disabling MSYS path conversion: this call goes to the host Python,
# which on Windows needs the converted path, while docker below needs the raw one.
python "$ROOT/tests/live_closure.py" > "$CLOSURE"

# Git Bash on Windows rewrites arguments that look like absolute POSIX paths,
# which breaks the container-side paths passed to docker.
MSYS_NO_PATHCONV=1
MSYS2_ARG_CONV_EXCL='*'
export MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

# The container's exit status is the result. It must not be swallowed by the
# pipeline that filters pip's warnings -- a run that reports SUSPEITO and then
# exits 0 would pass in CI. Output goes to a file first, status is saved, and only
# then is the output filtered.
OUTFILE="$ROOT/.smoke_out.txt"
status=0
docker run --rm \
  -v "$ROOT/script:/src:ro" \
  -v "$ROOT/src:/pkg:ro" \
  -v "$ROOT/config:/config:ro" \
  -v "$CLOSURE:/closure.txt:ro" \
  -e PYTHONPATH=/pkg \
  "$IMAGE" /bin/sh -c '
# Mirrors the runtime dependencies declared in pyproject.toml.
pip install --quiet biopython pyyaml 2>/dev/null

# virus_hunter.py calls serverInfo(), which shells out to ssh. Same stand-in as
# tests/reference/capture.sh, so reaching it counts as starting cleanly rather
# than as a failure.
mkdir -p /fake
printf "#!/bin/sh\necho \\"\\$1 48 64\\"\\n" > /fake/ssh
chmod +x /fake/ssh
PATH="/fake:$PATH"
export PATH

mkdir -p /tmp/sandbox && cd /tmp/sandbox
susp=0; okc=0
while read b; do
  [ -f "/src/$b" ] || continue
  err=$(python "/src/$b" 2>&1 >/dev/null | tail -1)
  # Allowlist, not blocklist. Listing the suspicious exceptions instead let any
  # new failure mode pass as expected -- a missing config file raised
  # ConfigError, which is a ValueError, and the check reported everything clean.
  # Only the ways a worker is *supposed* to fail without arguments count as fine.
  case "$err" in
    # No arguments were given, and the worker said so. IndexError is the common
    # shape; "not enough values to unpack" is the same thing where the script
    # unpacks sys.argv in one go.
    ""|*IndexError*|*SystemExit*|*usage*|*Usage*|*"not enough values to unpack"*)
      okc=$((okc+1)) ;;
    # Artefacts of this sandbox, not of the code. A few workers derive an output
    # path from sys.argv[0] and so try to write next to the script, which is
    # mounted read-only on purpose.
    *"Read-only file system"*)
      okc=$((okc+1)) ;;
    *)
      echo "  SUSPEITO  $b :: $err"; susp=$((susp+1)) ;;
  esac
done < /closure.txt
echo
echo "  iniciam limpo (falha so em argumento) : $okc"
echo "  SUSPEITOS (API nao migrada)           : $susp"
[ "$okc" -gt 0 ] || { echo "  nenhum arquivo verificado"; exit 2; }
[ "$susp" -eq 0 ] || exit 1
' > "$OUTFILE" 2>&1 || status=$?

grep -v "^WARNING" "$OUTFILE" || true
rm -f "$OUTFILE"
exit "$status"
