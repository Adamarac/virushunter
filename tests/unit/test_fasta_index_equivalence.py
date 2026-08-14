"""Differential test: FastaIndex against the legacy CacheLines/getSeq.

FastaIndex replaces a byte-identical block copied into six workers. Passing its
own tests only shows it is self-consistent; what matters is that it answers the
same as the code it replaces, including where that code is odd.

The legacy implementation is reproduced verbatim below, transliterated from
Python 2 only where the syntax demanded it (print, xrange). It is the oracle.
"""

import linecache

import pytest

from virushunter.io import FastaIndex

# --------------------------------------------------------------------------
# The oracle: script/blast_output_sort.py and five siblings, as they stand.
# --------------------------------------------------------------------------


def legacy_cache_lines(fname):
    cache = {}
    f = open(fname)
    i = 0
    start, end = 0, 0
    header = None
    for line in f:
        i += 1
        if line.strip().startswith(">"):
            end = i - 1
            if header is not None:
                cache[header] = (start, end)
            header = line.strip()[1:]
            start = i + 1
    if header is not None:
        cache[header] = (start, i)
    f.close()
    return cache


def legacy_get_seq(cachename, cache, header):
    seq = []
    start, end = cache[header]
    for i in range(start, end + 1):
        seq.append(linecache.getline(cachename, i).strip())
    return "".join(seq)


# --------------------------------------------------------------------------

CASES = {
    "simple": ">r0\nACGT\n>r1\nTTTT\n",
    "single_record": ">only\nACGT\n",
    "wrapped": ">long\nAAAA\nCCCC\nGGGG\n>short\nTT\n",
    "no_trailing_newline": ">a\nACGT",
    "blank_line_between": ">a\nACGT\n\n>b\nTTTT\n",
    "blank_line_inside": ">a\nACGT\n\nGGGG\n>b\nTT\n",
    "header_with_spaces": ">acc123 species$Human_virus:genus$X\nACGT\n",
    "header_indented": "  >indented\nACGT\n",
    "empty_sequence": ">a\n>b\nTTTT\n",
    "lowercase_sequence": ">a\nacgtacgt\n",
    "windows_line_endings": ">a\r\nACGT\r\n>b\r\nTTTT\r\n",
    "no_header_at_all": "ACGT\nTTTT\n",
    "empty_file": "",
}


@pytest.fixture(params=sorted(CASES), ids=sorted(CASES))
def sample(request, tmp_path):
    path = tmp_path / "sample.fa"
    path.write_text(CASES[request.param], encoding="utf-8", newline="")
    linecache.clearcache()
    return path


def test_same_headers(sample):
    legacy = legacy_cache_lines(str(sample))
    assert set(FastaIndex(sample).headers()) == set(legacy)


def test_same_spans(sample):
    legacy = legacy_cache_lines(str(sample))
    index = FastaIndex(sample)
    for header, span in legacy.items():
        assert index.span(header) == span, f"span divergiu em {header!r}"


def test_same_sequences(sample):
    legacy = legacy_cache_lines(str(sample))
    index = FastaIndex(sample)
    for header in legacy:
        linecache.clearcache()
        expected = legacy_get_seq(str(sample), legacy, header)
        linecache.clearcache()
        assert index.sequence(header) == expected, f"sequencia divergiu em {header!r}"


def test_indented_header_is_still_a_header(tmp_path):
    # Pinned explicitly because it is the one place the legacy code is odd and
    # the obvious rewrite -- line.startswith('>') -- would silently differ.
    path = tmp_path / "x.fa"
    path.write_text("  >indented\nACGT\n", encoding="utf-8")
    assert "indented" in FastaIndex(path)
    assert "indented" in legacy_cache_lines(str(path))
