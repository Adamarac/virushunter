"""Acesso aleatorio a FASTA por cabecalho de registro.

Substitui uma copia byte a byte de CacheLines/getSeq presente em seis workers.
Mantem o desenho por intervalos de linha + linecache: esses arquivos chegam a
dezenas de gigabytes e carrega-los em memoria e justamente o que se evita.
"""

from __future__ import annotations

import linecache
from collections.abc import Iterator
from pathlib import Path


class FastaIndexError(KeyError):
    """A header was requested that the index does not hold."""


class FastaIndex:
    """Maps FASTA headers to the line span of their sequence.

    Spans are one-based and inclusive, matching `linecache.getline`.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        self._spans: dict[str, tuple[int, int]] = {}
        self._build()

    def _build(self) -> None:
        header: str | None = None
        start = 0
        lineno = 0

        with open(self._path, encoding="utf-8", errors="replace") as handle:
            for lineno, line in enumerate(handle, start=1):
                # The legacy CacheLines tests `line.strip().startswith('>')`, so a
                # header indented by whitespace still counts as one. Matched here
                # deliberately: six workers have behaved this way for years and
                # tightening it is a behaviour change, not a cleanup.
                if not line.strip().startswith(">"):
                    continue
                if header is not None:
                    self._spans[header] = (start, lineno - 1)
                header = line.strip()[1:]
                start = lineno + 1

        if header is not None:
            self._spans[header] = (start, lineno)

    @property
    def path(self) -> str:
        return self._path

    def __len__(self) -> int:
        return len(self._spans)

    def __contains__(self, header: object) -> bool:
        return header in self._spans

    def __iter__(self) -> Iterator[str]:
        return iter(self._spans)

    def headers(self) -> list[str]:
        return list(self._spans)

    def span(self, header: str) -> tuple[int, int]:
        try:
            return self._spans[header]
        except KeyError:
            raise FastaIndexError(
                f"header not in {self._path}: {header!r}"
            ) from None

    def sequence(self, header: str) -> str:
        """The sequence for `header`, with line breaks removed."""
        start, end = self.span(header)
        return "".join(
            linecache.getline(self._path, i).strip() for i in range(start, end + 1)
        )

    def invalidate(self) -> None:
        """Drop linecache's copy of this file.

        `linecache` caches file contents globally and does not notice a file
        being rewritten. Any long-lived process that reads a FASTA, waits for a
        stage to regenerate it, then reads again would otherwise serve stale
        lines.
        """
        linecache.checkcache(self._path)
