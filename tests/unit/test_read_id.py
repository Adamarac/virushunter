"""Tests for read identity — invariant I1.

The cases that matter are the ones the legacy code got wrong or relied on
implicitly, not the happy path.
"""

from dataclasses import FrozenInstanceError

import pytest

from virushunter.domain import LINES_PER_RECORD, ReadId, ReadIdError, fasta_ordinal


class TestOrdinalFromLineNumber:
    """The ordinal is integer division. ADR-0011."""

    @pytest.mark.parametrize(
        "line_number,expected",
        [(1, 0), (5, 1), (9, 2), (13, 3), (4001, 1000)],
    )
    def test_header_lines_map_to_consecutive_ordinals(self, line_number, expected):
        assert ReadId.at_line(line_number, "1", "lib").ordinal == expected

    def test_ordinal_is_int_not_float(self):
        # The whole point. Under Python 2 this was an int; a naive port makes it
        # a float and the identifier becomes @s0.25_1_lib.
        ordinal = ReadId.at_line(1, "1", "lib").ordinal
        assert isinstance(ordinal, int)
        assert not isinstance(ordinal, float)

    def test_records_are_four_lines(self):
        assert LINES_PER_RECORD == 4

    def test_line_numbers_are_one_based(self):
        with pytest.raises(ReadIdError, match="one-based"):
            ReadId.at_line(0, "1", "lib")


class TestFormatting:
    def test_renders_the_legacy_format(self):
        assert str(ReadId(0, "1", "lib")) == "@s0_1_lib"

    def test_matches_what_recodeID_emits_for_the_first_read(self):
        assert str(ReadId.at_line(1, "1", "work_S1")) == "@s0_1_work_S1"


class TestParsing:
    def test_round_trips(self):
        original = ReadId(1234, "2", "work_S1")
        assert ReadId.parse(str(original)) == original

    def test_library_may_contain_underscores(self):
        # The pipeline builds the library as <project>_<sample>, so a naive
        # split('_') would lose part of the name.
        parsed = ReadId.parse("@s7_1_work_S1")
        assert parsed.ordinal == 7
        assert parsed.pair == "1"
        assert parsed.library == "work_S1"

    def test_tolerates_surrounding_whitespace(self):
        assert ReadId.parse("  @s3_1_lib\n").ordinal == 3

    @pytest.mark.parametrize(
        "text",
        [
            "@s0.25_1_lib",   # the Python 3 division bug
            "s0_1_lib",       # missing @
            "@s_1_lib",       # no ordinal
            "@s0_1",          # no library
            "",
            ">lib_0",         # the FASTA form, not this one
        ],
    )
    def test_rejects_malformed(self, text):
        with pytest.raises(ReadIdError):
            ReadId.parse(text)


class TestMate:
    def test_flips_one_to_two(self):
        assert ReadId(5, "1", "lib").mate() == ReadId(5, "2", "lib")

    def test_flips_two_to_one(self):
        assert ReadId(5, "2", "lib").mate() == ReadId(5, "1", "lib")

    def test_mate_of_mate_is_self(self):
        original = ReadId(5, "1", "lib")
        assert original.mate().mate() == original

    def test_refuses_to_guess_for_other_pair_labels(self):
        with pytest.raises(ReadIdError, match="cannot infer"):
            ReadId(5, "3", "lib").mate()


class TestValidation:
    def test_rejects_float_ordinal(self):
        # Guards the exact defect ADR-0011 fixed.
        with pytest.raises(ReadIdError, match="division bug"):
            ReadId(0.25, "1", "lib")

    def test_rejects_bool_ordinal(self):
        # bool is a subclass of int; True would otherwise pass as ordinal 1.
        with pytest.raises(ReadIdError):
            ReadId(True, "1", "lib")

    def test_rejects_negative_ordinal(self):
        with pytest.raises(ReadIdError, match="negative"):
            ReadId(-1, "1", "lib")

    def test_rejects_underscore_in_pair(self):
        # Would make the identifier ambiguous to parse.
        with pytest.raises(ReadIdError, match="must not contain"):
            ReadId(0, "1_x", "lib")

    @pytest.mark.parametrize("pair,library", [("", "lib"), ("1", "")])
    def test_rejects_empty_fields(self, pair, library):
        with pytest.raises(ReadIdError):
            ReadId(0, pair, library)

    def test_is_immutable(self):
        with pytest.raises(FrozenInstanceError):
            ReadId(0, "1", "lib").ordinal = 5


class TestFastaSide:
    """fq2faID.py counts the sequence line, recodeID.py the header line.

    Different lines of the same record; the ordinals must still agree. That
    agreement is what the two sources promise each other in their comments.
    """

    @pytest.mark.parametrize("record_index", range(5))
    def test_agrees_with_the_fastq_side(self, record_index):
        header_line = record_index * LINES_PER_RECORD + 1
        sequence_line = record_index * LINES_PER_RECORD + 2
        assert fasta_ordinal(sequence_line) == ReadId.at_line(header_line, "1", "l").ordinal

    def test_ordinal_is_int(self):
        assert isinstance(fasta_ordinal(2), int)
