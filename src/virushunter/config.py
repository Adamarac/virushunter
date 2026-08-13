"""Loading and validation of the pipeline configuration.

Every parameter used to live as a literal inside the `__main__` block of
`script/virus_hunter.py`, so running an analysis with a different threshold meant
editing the source. That is issue K9, and it is why no run's parameters could be
versioned alongside its results.

This module reads them from YAML instead. `config/default.yaml` holds exactly the
values that were hard-coded, so extraction changes nothing on its own -- proven
by tests/reference/verify.sh, which compares the generated scripts byte for byte.

Validation is deliberately shallow: required keys must exist and have the right
shape. It does not check that a threshold is scientifically sensible, because
nothing here knows what sensible means -- that judgement belongs to whoever sets
the value, and pretending otherwise would just hide it behind a schema.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """The configuration is missing something, or something is the wrong shape."""


#: Environment variable that overrides discovery entirely.
CONFIG_ENV_VAR = "VIRUSHUNTER_CONFIG"


def default_config_path() -> Path:
    """Locate config/default.yaml.

    Deriving it from `__file__` alone only works while the package is used from a
    source checkout: once installed, the module sits in site-packages and the
    config does not live three directories above it. So the search is explicit,
    and an environment variable wins over all of it.
    """
    from os import environ

    override = environ.get(CONFIG_ENV_VAR)
    if override:
        return Path(override)

    here = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "config" / "default.yaml",           # run from the project root
        here.parent.parent.parent / "config" / "default.yaml",  # src/ checkout
        here.parent / "config" / "default.yaml",          # packaged alongside the module
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ConfigError(
        "config/default.yaml nao encontrado. Procurado em:\n  "
        + "\n  ".join(str(c) for c in candidates)
        + f"\nDefina {CONFIG_ENV_VAR} para apontar o arquivo."
    )

#: Sections every configuration must carry.
REQUIRED_SECTIONS = ("compute", "params", "steps", "tools", "databases")

#: (path, type) pairs checked after merging. Kept small on purpose: these are the
#: values whose absence or wrong type would fail late and confusingly, deep inside
#: a generated shell script.
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
    """Read-only view over the merged configuration."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, dotted: str, default: Any = ...) -> Any:
        """Fetch by dotted path, e.g. `params.kmers.abyss`."""
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
        """A deep copy, so callers cannot mutate the loaded configuration."""
        return copy.deepcopy(self._data)

    def __repr__(self) -> str:
        return f"Config(sections={sorted(self._data)})"


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Overlay wins, but only for the keys it actually sets."""
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate(data: dict[str, Any]) -> None:
    missing = [s for s in REQUIRED_SECTIONS if s not in data]
    if missing:
        raise ConfigError(f"secoes ausentes: {', '.join(missing)}")

    view = Config(data)
    for dotted, expected in REQUIRED_KEYS:
        value = view.get(dotted)
        # bool is a subclass of int; an int field must not silently accept True.
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

    # The e-value is a string because it is pasted straight into command lines,
    # and reformatting it would change the generated scripts. It still has to be
    # a number -- K1 was exactly a threshold that was never numeric.
    try:
        float(view.get("params.evalue"))
    except (TypeError, ValueError):
        raise ConfigError(
            f"params.evalue deve ser numerico, veio {view.get('params.evalue')!r}"
        ) from None


def load(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
    """Load `config/default.yaml`, optionally overlaid with another file.

    The overlay only needs the keys it changes; everything else falls back to the
    default, so a run-specific file stays short and readable.
    """
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

    if overrides:
        data = _deep_merge(data, overrides)

    _validate(data)
    return Config(data)
