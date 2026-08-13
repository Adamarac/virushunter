"""Tests for FastaIndex — the random-access reader duplicated in six workers."""

import pytest

from virushunter.io import FastaIndex, FastaIndexError


@pytest.fixture
def simple(tmp_path):
    path = tmp_path / "reads.fa"
    path.write_text(
        ">r0\nACGT\n"
        ">r1\nTTTT\n"
        ">r2\nGGGG\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def wrapped(tmp_path):
    """FASTA in the wild wraps sequences across lines."""
    path = tmp_path / "wrapped.fa"
    path.write_text(
        ">long\nAAAA\nCCCC\nGGGG\n"
        ">short\nTT\n",
        encoding="utf-8",
    )
    return path


class TestIndexing:
    def test_finds_every_record(self, simple):
        index = FastaIndex(simple)
        assert len(index) == 3
        assert index.headers() == ["r0", "r1", "r2"]

    def test_membership(self, simple):
        index = FastaIndex(simple)
        assert "r1" in index
        assert "nope" not in index

    def test_iterates_headers(self, simple):
        assert list(FastaIndex(simple)) == ["r0", "r1", "r2"]

    def test_header_excludes_the_marker(self, simple):
        # The legacy code stored the header without '>' and every consumer
        # depends on that, because BLAST reports query names without it.
        assert ">r0" not in FastaIndex(simple)
        assert "r0" in FastaIndex(simple)

    def test_empty_file_yields_empty_index(self, tmp_path):
        path = tmp_path / "empty.fa"
        path.write_text("", encoding="utf-8")
        assert len(FastaIndex(path)) == 0


class TestSequenceRetrieval:
    def test_reads_single_line_sequences(self, simple):
        index = FastaIndex(simple)
        assert index.sequence("r0") == "ACGT"
        assert index.sequence("r2") == "GGGG"

    def test_joins_wrapped_sequences(self, wrapped):
        assert FastaIndex(wrapped).sequence("long") == "AAAACCCCGGGG"

    def test_reads_the_last_record(self, wrapped):
        # Off-by-one country: the final record has no following '>' to close it.
        assert FastaIndex(wrapped).sequence("short") == "TT"

    def test_unknown_header_raises_with_context(self, simple):
        index = FastaIndex(simple)
        with pytest.raises(FastaIndexError, match="header not in"):
            index.sequence("absent")

    def test_error_is_a_keyerror(self, simple):
        # Legacy callers wrap these lookups in `except KeyError`.
        assert issubclass(FastaIndexError, KeyError)


class TestSpans:
    def test_spans_are_one_based_and_inclusive(self, simple):
        # Matches linecache.getline, which the retrieval relies on.
        assert FastaIndex(simple).span("r0") == (2, 2)
        assert FastaIndex(simple).span("r1") == (4, 4)

    def test_span_covers_every_wrapped_line(self, wrapped):
        assert FastaIndex(wrapped).span("long") == (2, 4)


class TestStaleness:
    def test_invalidate_lets_a_rewritten_file_be_reread(self, tmp_path):
        # linecache caches globally and does not notice a rewrite. Pipeline
        # stages regenerate FASTA files in place, so this is a real hazard.
        path = tmp_path / "x.fa"
        path.write_text(">a\nAAAA\n", encoding="utf-8")
        assert FastaIndex(path).sequence("a") == "AAAA"

        path.write_text(">a\nCCCC\n", encoding="utf-8")
        rebuilt = FastaIndex(path)
        rebuilt.invalidate()
        assert rebuilt.sequence("a") == "CCCC"
