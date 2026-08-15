# Descobre quais amostras existem na pasta de entrada e prepara a configuracao
# que o Snakefile vai usar.

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from virushunter.config import Config, ConfigError
from virushunter.config import load as load_config

# Dois jeitos de nomear FASTQ que aparecem na pratica: o padrao das maquinas
# Illumina e a forma curta amostra_1.fastq.
_ILLUMINA = re.compile(
    r"^(?P<prefix>.+?)_(?P<sample>[^_]+)_L\d+_R(?P<pair>[12])_\d+\.fastq(?:\.gz)?$"
)
_SIMPLE = re.compile(r"^(?P<sample>.+)_(?P<pair>[12])\.fastq(?:\.gz)?$")


class SampleDiscoveryError(ValueError):
    """Nao foi possivel identificar as amostras a partir dos nomes dos arquivos."""


def parse_fastq_name(name: str) -> tuple[str, str] | None:
    """Tira o nome da amostra e o numero do par do nome do arquivo; None se nao reconhecer."""
    for pattern in (_ILLUMINA, _SIMPLE):
        match = pattern.match(name)
        if match:
            return match.group("sample"), match.group("pair")
    return None


def fastq_files(fastq_dir: str | Path) -> dict[tuple[str, str], str]:
    """Liga cada dupla (amostra, par) ao arquivo correspondente na pasta."""
    directory = Path(fastq_dir)
    if not directory.is_dir():
        raise SampleDiscoveryError(f"diretorio de fastq nao encontrado: {directory}")

    found: dict[tuple[str, str], str] = {}
    unmatched: list[str] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file() or not entry.name.endswith((".fastq", ".fastq.gz")):
            continue
        key = parse_fastq_name(entry.name)
        if key is None:
            unmatched.append(entry.name)
            continue
        if key in found:
            raise SampleDiscoveryError(
                f"dois arquivos para a mesma amostra e par {key}: "
                f"{found[key]} e {entry.name}"
            )
        found[key] = str(entry)

    if not found:
        detail = ""
        if unmatched:
            detail = "\nArquivos encontrados mas nao reconhecidos:\n  " + "\n  ".join(
                unmatched[:10]
            )
        raise SampleDiscoveryError(f"nenhuma amostra reconhecida em {directory}{detail}")
    return found


def discover_samples(fastq_dir: str | Path) -> list[str]:
    """Nomes das amostras, em ordem alfabetica para o resultado ser sempre o mesmo."""
    return sorted({sample for sample, _ in fastq_files(fastq_dir)})


def resolve_config(snakemake_config: dict[str, Any], workflow_dir: str | Path) -> Config:
    """Junta o que veio pela linha de comando do Snakemake com a configuracao padrao."""
    overrides = dict(snakemake_config or {})
    io = {
        "fastq_dir": "fastq",
        # Sem nome definido, usa o nome da pasta de trabalho como prefixo das bibliotecas.
        "library_prefix": Path.cwd().name,
        **overrides.pop("io", {}),
    }
    overrides["io"] = io

    cfg = load_config(overrides=overrides)
    if not cfg.get("io.library_prefix"):
        raise ConfigError("io.library_prefix nao pode ser vazio")
    return cfg
