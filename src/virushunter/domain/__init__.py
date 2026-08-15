"""Tipos de dominio: os conceitos sobre os quais o pipeline raciocina."""

from virushunter.domain.read_id import LINES_PER_RECORD, ReadId, ReadIdError, fasta_ordinal

__all__ = ["LINES_PER_RECORD", "ReadId", "ReadIdError", "fasta_ordinal"]
