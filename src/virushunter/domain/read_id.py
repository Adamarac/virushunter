"""Identidade de leitura: a posicao no arquivo, nao o cabecalho do sequenciador.

Consequencias, detalhadas em docs/invariants.md (I1): nenhuma etapa anterior a
recodificacao pode remover registros -- por isso os filtros mascaram --, e o
ordinal e divisao inteira (ADR-0011).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: FASTQ records are four lines: header, sequence, separator, quality.
LINES_PER_RECORD = 4

_PATTERN = re.compile(r"^@s(?P<ordinal>\d+)_(?P<pair>[^_]+)_(?P<library>.+)$")


class ReadIdError(ValueError):
    """A read identifier could not be parsed or built."""


@dataclass(frozen=True)
class ReadId:
    """The identity of a single read.

    Immutable on purpose: an identity that can be edited in place is an identity
    that can be edited by accident.
    """

    ordinal: int
    pair: str
    library: str

    def __post_init__(self) -> None:
        if not isinstance(self.ordinal, int) or isinstance(self.ordinal, bool):
            raise ReadIdError(
                f"ordinal must be an int, got {self.ordinal!r} "
                f"({type(self.ordinal).__name__}) -- a float here is the "
                "Python 3 division bug"
            )
        if self.ordinal < 0:
            raise ReadIdError(f"ordinal must not be negative, got {self.ordinal}")
        if not self.pair:
            raise ReadIdError("pair must not be empty")
        if "_" in self.pair:
            raise ReadIdError(f"pair must not contain '_', got {self.pair!r}")
        if not self.library:
            raise ReadIdError("library must not be empty")

    @classmethod
    def at_line(cls, line_number: int, pair: str, library: str) -> ReadId:
        """Build the identity of the read whose header is at `line_number`.

        Line numbers are one-based, matching how the scripts count while reading.
        Integer division is used deliberately -- see ADR-0011.
        """
        if line_number < 1:
            raise ReadIdError(f"line_number is one-based, got {line_number}")
        return cls(line_number // LINES_PER_RECORD, pair, library)

    @classmethod
    def parse(cls, text: str) -> ReadId:
        """Parse `@s<ordinal>_<pair>_<library>`.

        The library name may itself contain underscores -- the pipeline builds it
        as `<project>_<sample>`, e.g. `work_S1` -- so only the first two fields
        are split off.
        """
        match = _PATTERN.match(text.strip())
        if match is None:
            raise ReadIdError(f"not a read identifier: {text!r}")
        return cls(
            ordinal=int(match.group("ordinal")),
            pair=match.group("pair"),
            library=match.group("library"),
        )

    def mate(self, of_pair: str | None = None) -> ReadId:
        """The other read of the pair.

        With no argument this flips 1 <-> 2, which is what the reporting stage
        does when it looks up a hit's partner.
        """
        if of_pair is None:
            if self.pair == "1":
                of_pair = "2"
            elif self.pair == "2":
                of_pair = "1"
            else:
                raise ReadIdError(
                    f"cannot infer the mate of pair {self.pair!r}; pass one explicitly"
                )
        return ReadId(self.ordinal, of_pair, self.library)

    def __str__(self) -> str:
        return f"@s{self.ordinal}_{self.pair}_{self.library}"


def fasta_ordinal(line_number: int) -> int:
    """Ordinal for the FASTA side, as `fq2faID.py` computes it.

    fq2faID.py emits `><fileID>_<ordinal>` from the *sequence* line rather than
    the header line, so it counts a different line of the same record. Both land
    on the same ordinal, which is exactly what the two must agree on.
    """
    if line_number < 1:
        raise ReadIdError(f"line_number is one-based, got {line_number}")
    return line_number // LINES_PER_RECORD
