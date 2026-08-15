"""Acesso aleatorio a FASTA por cabecalho, sem carregar o arquivo em memoria."""

from __future__ import annotations

import linecache
from collections.abc import Iterator
from pathlib import Path


class FastaIndexError(KeyError):
    """Cabecalho pedido nao existe no indice."""


class FastaIndex:
    """Mapeia cabecalho FASTA para o intervalo de linhas da sua sequencia."""

    def __init__(self, path: str | Path) -> None:
        """Constroi o indice percorrendo o arquivo uma vez."""
        self._path = str(path)
        self._spans: dict[str, tuple[int, int]] = {}
        self._build()

    def _build(self) -> None:
        """Aceita cabecalho indentado, como o CacheLines legado que isto substitui."""
        header: str | None = None
        start = 0
        lineno = 0

        with open(self._path, encoding="utf-8", errors="replace") as handle:
            for lineno, line in enumerate(handle, start=1):
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
        """Caminho do arquivo indexado."""
        return self._path

    def __len__(self) -> int:
        """Numero de registros indexados."""
        return len(self._spans)

    def __contains__(self, header: object) -> bool:
        """Se o cabecalho esta no indice."""
        return header in self._spans

    def __iter__(self) -> Iterator[str]:
        """Percorre os cabecalhos na ordem em que aparecem."""
        return iter(self._spans)

    def headers(self) -> list[str]:
        """Cabecalhos indexados."""
        return list(self._spans)

    def span(self, header: str) -> tuple[int, int]:
        """Intervalo de linhas do registro, contado a partir de 1 e inclusivo."""
        try:
            return self._spans[header]
        except KeyError:
            raise FastaIndexError(
                f"cabecalho ausente em {self._path}: {header!r}"
            ) from None

    def sequence(self, header: str) -> str:
        """Sequencia do registro, com as quebras de linha removidas."""
        start, end = self.span(header)
        return "".join(
            linecache.getline(self._path, i).strip() for i in range(start, end + 1)
        )

    def invalidate(self) -> None:
        """Descarta o cache global do linecache, que nao percebe reescrita do arquivo."""
        linecache.checkcache(self._path)
