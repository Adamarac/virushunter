# Acesso a sequencias de um FASTA sem carregar o arquivo inteiro na memoria:
# primeiro monta um indice de onde cada sequencia comeca e termina, depois le
# so as linhas pedidas.

from __future__ import annotations

import linecache


def index_headers(path: str) -> dict[str, tuple[int, int]]:
    """Mapeia cada cabecalho para o intervalo de linhas da sua sequencia."""
    cache: dict[str, tuple[int, int]] = {}
    header: str | None = None
    start = 0
    i = 0
    with open(path) as f:
        for i, line in enumerate(f, start=1):
            # O strip() antes do startswith e proposital: no formato original um
            # cabecalho indentado ainda conta como cabecalho.
            if line.strip().startswith(">"):
                if header is not None:
                    cache[header] = (start, i - 1)
                header = line.strip()[1:]
                start = i + 1
    if header is not None:
        cache[header] = (start, i)
    return cache


def sequence(path: str, cache: dict[str, tuple[int, int]], header: str) -> str:
    """Le do disco a sequencia de um cabecalho, usando o indice."""
    start, end = cache[header]
    return "".join(linecache.getline(path, i).strip() for i in range(start, end + 1))
