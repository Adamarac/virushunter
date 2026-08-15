"""Descoberta de amostras e resolucao de configuracao para o Snakefile."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from virushunter.config import Config, ConfigError
from virushunter.config import load as load_config

_ILLUMINA = re.compile(
    r"^(?P<prefix>.+?)_(?P<sample>[^_]+)_L\d+_R(?P<pair>[12])_\d+\.fastq(?:\.gz)?$"
)

_SIMPLE = re.compile(r"^(?P<sample>.+)_(?P<pair>[12])\.fastq(?:\.gz)?$")


class SampleDiscoveryError(ValueError):
    """Nenhuma amostra encontrada, ou nome de arquivo nao reconhecido."""


def parse_fastq_name(name: str) -> tuple[str, str] | None:
    """Devolve (amostra, par) do nome do FASTQ, ou None se nao for reconhecido."""
    for pattern in (_ILLUMINA, _SIMPLE):
        match = pattern.match(name)
        if match:
            return match.group("sample"), match.group("pair")
    return None


def discover_samples(fastq_dir: str | Path) -> list[str]:
    """Nomes de amostra encontrados no diretorio, ordenados para ser deterministico."""
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
    """Mapeia (amostra, par) para o arquivo real; o nome da amostra nao o determina."""
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
    """Mescla a config do Snakemake sobre o padrao, usando o mesmo validador."""
    overrides = dict(snakemake_config or {})
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
