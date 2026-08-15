"""Identidade de leitura: a posicao no arquivo, nao o cabecalho do sequenciador (I1)."""

from __future__ import annotations

import re
from dataclasses import dataclass

LINES_PER_RECORD = 4

_PATTERN = re.compile(r"^@s(?P<ordinal>\d+)_(?P<pair>[^_]+)_(?P<library>.+)$")


class ReadIdError(ValueError):
    """Identificador de leitura invalido ou impossivel de interpretar."""


@dataclass(frozen=True)
class ReadId:
    """Identidade imutavel de uma leitura: ordinal, par e biblioteca."""

    ordinal: int
    pair: str
    library: str

    def __post_init__(self) -> None:
        """Rejeita ordinal fracionario, sintoma da divisao real do Python 3."""
        if not isinstance(self.ordinal, int) or isinstance(self.ordinal, bool):
            raise ReadIdError(
                f"ordinal deve ser int, veio {self.ordinal!r} "
                f"({type(self.ordinal).__name__})"
            )
        if self.ordinal < 0:
            raise ReadIdError(f"ordinal nao pode ser negativo, veio {self.ordinal}")
        if not self.pair:
            raise ReadIdError("par nao pode ser vazio")
        if "_" in self.pair:
            raise ReadIdError(f"par nao pode conter '_', veio {self.pair!r}")
        if not self.library:
            raise ReadIdError("biblioteca nao pode ser vazia")

    @classmethod
    def at_line(cls, line_number: int, pair: str, library: str) -> ReadId:
        """Identidade da leitura cujo cabecalho esta na linha dada, contada a partir de 1."""
        if line_number < 1:
            raise ReadIdError(f"linha e contada a partir de 1, veio {line_number}")
        return cls(line_number // LINES_PER_RECORD, pair, library)

    @classmethod
    def parse(cls, text: str) -> ReadId:
        """Interpreta @s<ordinal>_<par>_<biblioteca>; a biblioteca pode conter '_'."""
        match = _PATTERN.match(text.strip())
        if match is None:
            raise ReadIdError(f"nao e um identificador de leitura: {text!r}")
        return cls(
            ordinal=int(match.group("ordinal")),
            pair=match.group("pair"),
            library=match.group("library"),
        )

    def mate(self, of_pair: str | None = None) -> ReadId:
        """A outra leitura do par; sem argumento alterna entre 1 e 2."""
        if of_pair is None:
            if self.pair == "1":
                of_pair = "2"
            elif self.pair == "2":
                of_pair = "1"
            else:
                raise ReadIdError(
                    f"nao da para inferir o par de {self.pair!r}; passe explicitamente"
                )
        return ReadId(self.ordinal, of_pair, self.library)

    def __str__(self) -> str:
        """Formato emitido por recodeID.py e blast_trim.py."""
        return f"@s{self.ordinal}_{self.pair}_{self.library}"


def fasta_ordinal(line_number: int) -> int:
    """Ordinal do lado FASTA, contado da linha de sequencia; concorda com ReadId."""
    if line_number < 1:
        raise ReadIdError(f"linha e contada a partir de 1, veio {line_number}")
    return line_number // LINES_PER_RECORD
