"""Carga e validacao da configuracao do pipeline."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Configuracao incompleta ou com formato errado."""


CONFIG_ENV_VAR = "VIRUSHUNTER_CONFIG"

CONFIG_OVERLAY_ENV_VAR = "VIRUSHUNTER_CONFIG_OVERLAY"


def default_config_path() -> Path:
    """Localiza config/default.yaml; a variavel de ambiente sobrepoe a busca."""
    from os import environ

    override = environ.get(CONFIG_ENV_VAR)
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

REQUIRED_SECTIONS = ("compute", "params", "steps", "tools", "databases")

REQUIRED_KEYS: tuple[tuple[str, type | tuple[type, ...]], ...] = (
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


class Config:
    """Visao somente-leitura sobre a configuracao ja mesclada."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, dotted: str, default: Any = ...) -> Any:
        """Busca por caminho pontuado, ex.: params.kmers.abyss."""
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

    def as_dict(self) -> dict[str, Any]:
        """Copia profunda, para que ninguem altere a configuracao carregada."""
        return copy.deepcopy(self._data)

    def __repr__(self) -> str:
        return f"Config(sections={sorted(self._data)})"


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """A sobreposicao vence, mas so nas chaves que ela define."""
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate(data: dict[str, Any]) -> None:
    """Confere forma -- chaves, tipos e modos validos -- nao merito cientifico."""
    missing = [s for s in REQUIRED_SECTIONS if s not in data]
    if missing:
        raise ConfigError(f"secoes ausentes: {', '.join(missing)}")

    view = Config(data)
    for dotted, expected in REQUIRED_KEYS:
        value = view.get(dotted)
        if expected is int and isinstance(value, bool):
            raise ConfigError(f"{dotted} deve ser int, veio bool: {value!r}")
        if not isinstance(value, expected):
            name = getattr(expected, "__name__", str(expected))
            raise ConfigError(
                f"{dotted} deve ser {name}, veio {type(value).__name__}: {value!r}"
            )

    mode = view.get("steps.assembly.mode")
    if mode not in VALID_ASSEMBLY_MODES:
        raise ConfigError(
            f"steps.assembly.mode invalido: {mode!r}; use um de {VALID_ASSEMBLY_MODES}"
        )

    phage = view.get("steps.viral_search.phage", "False")
    if phage not in VALID_PHAGE_MODES:
        raise ConfigError(
            f"steps.viral_search.phage invalido: {phage!r}; use um de {VALID_PHAGE_MODES}"
        )

    for field in ("compute.threads", "compute.query_splits"):
        if view.get(field) < 1:
            raise ConfigError(f"{field} deve ser >= 1, veio {view.get(field)}")
    try:
        float(view.get("params.evalue"))
    except (TypeError, ValueError):
        raise ConfigError(
            f"params.evalue deve ser numerico, veio {view.get('params.evalue')!r}"
        ) from None


def load(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
    """Carrega o padrao, opcionalmente sobreposto por outro arquivo parcial."""
    default_path = default_config_path()
    with open(default_path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ConfigError(f"{default_path} nao contem um mapeamento YAML")

    if path is not None:
        with open(path, encoding="utf-8") as handle:
            overlay = yaml.safe_load(handle)
        if overlay is None:
            overlay = {}
        if not isinstance(overlay, dict):
            raise ConfigError(f"{path} nao contem um mapeamento YAML")
        data = _deep_merge(data, overlay)

    from os import environ

    overlay_path = environ.get(CONFIG_OVERLAY_ENV_VAR)
    if overlay_path:
        with open(overlay_path, encoding="utf-8") as handle:
            env_overlay = yaml.safe_load(handle) or {}
        if not isinstance(env_overlay, dict):
            raise ConfigError(f"{overlay_path} nao contem um mapeamento YAML")
        data = _deep_merge(data, env_overlay)

    if overrides:
        data = _deep_merge(data, overrides)

    _validate(data)
    return Config(data)
