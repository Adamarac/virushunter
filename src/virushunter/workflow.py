"""Helpers the Snakefile needs: sample discovery and configuration resolution.

Kept out of the Snakefile so they can be unit-tested. Snakemake files are hard to
test directly, and sample discovery is exactly the kind of thing that fails
quietly -- the legacy version derived a sample name by positional splitting and
would mis-group anything not matching the sequencer's naming convention.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from virushunter.config import Config, ConfigError
from virushunter.config import load as load_config

#: Illumina-style names, e.g. A_S1_L001_R1_001.fastq.gz -> sample S1, pair 1.
_ILLUMINA = re.compile(
    r"^(?P<prefix>.+?)_(?P<sample>[^_]+)_L\d+_R(?P<pair>[12])_\d+\.fastq(?:\.gz)?$"
)

#: Fallback: <sample>_<pair>.fastq[.gz]
_SIMPLE = re.compile(r"^(?P<sample>.+)_(?P<pair>[12])\.fastq(?:\.gz)?$")


class SampleDiscoveryError(ValueError):
    """No samples were found, or a filename could not be interpreted."""


def parse_fastq_name(name: str) -> tuple[str, str] | None:
    """Return (sample, pair) for a FASTQ filename, or None if it is not one.

    The legacy readSeeds2() did this positionally --
    `line.split('.')[0].split('_')[1]` -- which silently mis-grouped any name not
    matching the sequencer's convention, and had no way to say so. Here the
    patterns are explicit and a non-match is visible.
    """
    for pattern in (_ILLUMINA, _SIMPLE):
        match = pattern.match(name)
        if match:
            return match.group("sample"), match.group("pair")
    return None


def discover_samples(fastq_dir: str | Path) -> list[str]:
    """Sample names found in `fastq_dir`, sorted.

    Sorted rather than in filesystem order: iteration order used to decide which
    node ran which sample and the order of aggregation arguments, and under
    Python 2 it came from dict hashing. Determinism here is deliberate.
    """
    directory = Path(fastq_dir)
    if not directory.is_dir():
        raise SampleDiscoveryError(f"diretorio de fastq nao encontrado: {directory}")

    samples: set[str] = set()
    unmatched: list[str] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        if not entry.name.endswith((".fastq", ".fastq.gz")):
            continue
        parsed = parse_fastq_name(entry.name)
        if parsed is None:
            unmatched.append(entry.name)
        else:
            samples.add(parsed[0])

    if not samples:
        detail = ""
        if unmatched:
            detail = "\nArquivos encontrados mas nao reconhecidos:\n  " + "\n  ".join(
                unmatched[:10]
            )
        raise SampleDiscoveryError(
            f"nenhuma amostra reconhecida em {directory}{detail}"
        )

    return sorted(samples)


def fastq_files(fastq_dir: str | Path) -> dict[tuple[str, str], str]:
    """Map (sample, pair) to the actual filename on disk.

    Rules cannot name their inputs by pattern here: a sample called S1 lives in a
    file called A_S1_L001_R1_001.fastq.gz, and the parts around the sample name
    are not derivable from it. So the mapping is built once from what is really
    there.
    """
    directory = Path(fastq_dir)
    if not directory.is_dir():
        raise SampleDiscoveryError(f"diretorio de fastq nao encontrado: {directory}")

    found: dict[tuple[str, str], str] = {}
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        parsed = parse_fastq_name(entry.name)
        if parsed is None:
            continue
        key = parsed
        if key in found:
            raise SampleDiscoveryError(
                f"dois arquivos para a mesma amostra e par {key}: "
                f"{found[key]} e {entry.name}"
            )
        found[key] = str(entry)
    return found


def resolve_config(snakemake_config: dict[str, Any], workflow_dir: str | Path) -> Config:
    """Merge Snakemake's --config/--configfile over config/default.yaml.

    Snakemake hands the workflow a plain dict. Routing it through the same loader
    means the workflow and the legacy generator validate identically, instead of
    the workflow silently accepting a value the generator would have rejected.
    """
    overrides = dict(snakemake_config or {})

    # Defaults for keys the generator never needed, because it derived them from
    # the working directory instead.
    io_defaults = {
        "fastq_dir": "fastq",
        "library_prefix": Path.cwd().name,
    }
    io = {**io_defaults, **overrides.pop("io", {})}

    cfg = load_config(overrides=overrides)
    data = cfg.as_dict()
    data["io"] = io

    resolved = Config(data)
    if not resolved.get("io.library_prefix"):
        raise ConfigError("io.library_prefix nao pode ser vazio")
    return resolved
