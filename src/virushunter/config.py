# Le o arquivo config/default.yaml, confere se ele esta preenchido corretamente
# e entrega os valores para o resto do pipeline.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_ENV_VAR = "VIRUSHUNTER_CONFIG"

REQUIRED_SECTIONS = ("compute", "params", "steps", "tools", "databases")

# Chave e o tipo que ela precisa ter. Erro de tipo aqui vira falha silenciosa la na frente.
REQUIRED_KEYS: tuple[tuple[str, type], ...] = (
    ("compute.threads", int),
    ("compute.query_splits", int),
    ("params.evalue", str),
    ("params.min_read_length", int),
    ("params.contig_length_pre_cap3", int),
    ("params.contig_length_post_cap3", int),
    ("params.mystery_min_length", int),
    ("params.kmers.abyss", str),
    ("params.kmers.soap", str),
    ("params.kmers.metavelvet", str),
    ("steps.paired_end", bool),
    ("steps.assembly.mode", str),
    ("tools.scripts_dir", str),
    ("databases.virus_protein", str),
)

VALID_ASSEMBLY_MODES = ("no", "denovo", "trinity")
VALID_PHAGE_MODES = ("False", "True", "Both")


class ConfigError(ValueError):
    """Erro na configuracao: falta alguma coisa ou o valor esta no formato errado."""


class Config:
    """Os valores da configuracao, consultados por caminho: cfg["params.evalue"]."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, dotted: str, default: Any = ...) -> Any:
        """Busca um valor descendo pelas secoes separadas por ponto."""
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is not ...:
                    return default
                raise ConfigError(f"chave ausente na configuracao: {dotted}")
            node = node[part]
        return node

    def __getitem__(self, dotted: str) -> Any:
        return self.get(dotted)


def default_config_path() -> Path:
    """Acha o config/default.yaml; a variavel VIRUSHUNTER_CONFIG aponta outro arquivo."""
    override = os.environ.get(CONFIG_ENV_VAR)
    if override:
        return Path(override)

    here = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "config" / "default.yaml",
        here.parent.parent.parent / "config" / "default.yaml",
        here.parent / "config" / "default.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ConfigError(
        "config/default.yaml nao encontrado. Procurado em:\n  "
        + "\n  ".join(str(c) for c in candidates)
        + f"\nDefina {CONFIG_ENV_VAR} para apontar o arquivo."
    )


def merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Junta duas configuracoes: quem esta em cima so muda as chaves que define."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def validate(data: dict[str, Any]) -> None:
    """Confere se a configuracao esta preenchida; nao julga se os valores fazem sentido."""
    missing = [s for s in REQUIRED_SECTIONS if s not in data]
    if missing:
        raise ConfigError(f"secoes ausentes: {', '.join(missing)}")

    cfg = Config(data)
    for dotted, expected in REQUIRED_KEYS:
        value = cfg.get(dotted)
        # Em Python True e um inteiro, entao um bool passaria como int sem esta checagem.
        if expected is int and isinstance(value, bool):
            raise ConfigError(f"{dotted} deve ser int, veio bool: {value!r}")
        if not isinstance(value, expected):
            raise ConfigError(
                f"{dotted} deve ser {expected.__name__}, "
                f"veio {type(value).__name__}: {value!r}"
            )

    mode = cfg.get("steps.assembly.mode")
    if mode not in VALID_ASSEMBLY_MODES:
        raise ConfigError(
            f"steps.assembly.mode invalido: {mode!r}; use um de {VALID_ASSEMBLY_MODES}"
        )

    phage = cfg.get("steps.viral_search.phage", "False")
    if phage not in VALID_PHAGE_MODES:
        raise ConfigError(
            f"steps.viral_search.phage invalido: {phage!r}; use um de {VALID_PHAGE_MODES}"
        )

    for field in ("compute.threads", "compute.query_splits"):
        if cfg.get(field) < 1:
            raise ConfigError(f"{field} deve ser >= 1, veio {cfg.get(field)}")

    # O e-value fica como texto no YAML para preservar a notacao 1e-5, mas precisa ser numero.
    try:
        float(cfg.get("params.evalue"))
    except (TypeError, ValueError):
        raise ConfigError(
            f"params.evalue deve ser numerico, veio {cfg.get('params.evalue')!r}"
        ) from None


def load(overrides: dict[str, Any] | None = None) -> Config:
    """Le a configuracao padrao, aplica o que foi passado por cima e confere o resultado."""
    path = default_config_path()
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ConfigError(f"{path} nao contem um mapeamento YAML")

    if overrides:
        data = merge(data, overrides)

    validate(data)
    return Config(data)
