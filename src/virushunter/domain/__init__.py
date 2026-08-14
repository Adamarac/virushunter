"""Domain types: the concepts the pipeline reasons about."""

from virushunter.domain.read_id import LINES_PER_RECORD, ReadId, ReadIdError, fasta_ordinal

__all__ = ["LINES_PER_RECORD", "ReadId", "ReadIdError", "fasta_ordinal"]
