"""Tests for sample discovery and workflow configuration resolution."""

import pytest

from virushunter.config import ConfigError
from virushunter.workflow import (
    SampleDiscoveryError,
    discover_samples,
    parse_fastq_name,
    resolve_config,
)


class TestParseFastqName:
    @pytest.mark.parametrize(
        "name,sample,pair",
        [
            ("A_S1_L001_R1_001.fastq.gz", "S1", "1"),
            ("A_S1_L001_R2_001.fastq.gz", "S1", "2"),
            ("B_S2_L001_R1_001.fastq", "S2", "1"),
            # Prefixes with underscores must not shift the sample field.
            ("Proj_2024_S12_L001_R1_001.fastq.gz", "S12", "1"),
        ],
    )
    def test_illumina_names(self, name, sample, pair):
        assert parse_fastq_name(name) == (sample, pair)

    @pytest.mark.parametrize(
        "name,sample,pair",
        [("mysample_1.fastq", "mysample", "1"), ("x_2.fastq.gz", "x", "2")],
    )
    def test_simple_names(self, name, sample, pair):
        assert parse_fastq_name(name) == (sample, pair)

    @pytest.mark.parametrize(
        "name",
        [
            "notes.txt",
            "sample.fastq",        # no pair
            "sample_3.fastq",      # pair must be 1 or 2
            "README.md",
            "samples.txt",         # the legacy manifest, not a read file
        ],
    )
    def test_rejects_non_fastq(self, name):
        # The legacy code split positionally and would produce a garbage sample
        # name here rather than admitting it did not understand the file.
        assert parse_fastq_name(name) is None


class TestDiscoverSamples:
    @pytest.fixture
    def fastq_dir(self, tmp_path):
        d = tmp_path / "fastq"
        d.mkdir()
        for name in [
            "A_S1_L001_R1_001.fastq.gz",
            "A_S1_L001_R2_001.fastq.gz",
            "B_S2_L001_R1_001.fastq.gz",
            "B_S2_L001_R2_001.fastq.gz",
        ]:
            (d / name).write_text("", encoding="utf-8")
        return d

    def test_finds_both_samples(self, fastq_dir):
        assert discover_samples(fastq_dir) == ["S1", "S2"]

    def test_pairs_collapse_to_one_sample(self, fastq_dir):
        # Two files per sample must not produce two samples.
        assert len(discover_samples(fastq_dir)) == 2

    def test_result_is_sorted(self, tmp_path):
        d = tmp_path / "fastq"
        d.mkdir()
        for s in ["S9", "S1", "S3"]:
            (d / f"x_{s}_L001_R1_001.fastq.gz").write_text("", encoding="utf-8")
        # Deterministic order matters: iteration order used to decide node
        # assignment and aggregation argument order.
        assert discover_samples(d) == ["S1", "S3", "S9"]

    def test_ignores_unrelated_files(self, fastq_dir):
        (fastq_dir / "samples.txt").write_text("", encoding="utf-8")
        (fastq_dir / "notes.md").write_text("", encoding="utf-8")
        assert discover_samples(fastq_dir) == ["S1", "S2"]

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(SampleDiscoveryError, match="nao encontrado"):
            discover_samples(tmp_path / "absent")

    def test_empty_directory_raises(self, tmp_path):
        d = tmp_path / "fastq"
        d.mkdir()
        with pytest.raises(SampleDiscoveryError, match="nenhuma amostra"):
            discover_samples(d)

    def test_unrecognised_names_are_reported(self, tmp_path):
        # Failing silently here is how a run ends up analysing nothing.
        d = tmp_path / "fastq"
        d.mkdir()
        (d / "weird-name.fastq").write_text("", encoding="utf-8")
        with pytest.raises(SampleDiscoveryError, match="weird-name.fastq"):
            discover_samples(d)


class TestResolveConfig:
    def test_defaults_come_through(self, tmp_path):
        cfg = resolve_config({}, tmp_path)
        assert cfg["compute.threads"] == 48
        assert cfg["params.evalue"] == "0.01"

    def test_io_defaults_are_supplied(self, tmp_path):
        cfg = resolve_config({}, tmp_path)
        assert cfg["io.fastq_dir"] == "fastq"
        assert cfg["io.library_prefix"]

    def test_snakemake_config_overrides(self, tmp_path):
        cfg = resolve_config({"compute": {"threads": 4}}, tmp_path)
        assert cfg["compute.threads"] == 4
        assert cfg["compute.query_splits"] == 50

    def test_io_can_be_overridden(self, tmp_path):
        cfg = resolve_config({"io": {"fastq_dir": "reads"}}, tmp_path)
        assert cfg["io.fastq_dir"] == "reads"
        assert cfg["io.library_prefix"]  # still defaulted

    def test_validation_still_applies(self, tmp_path):
        # The workflow must not accept what the generator would reject.
        with pytest.raises(ConfigError, match="assembly.mode"):
            resolve_config({"steps": {"assembly": {"mode": "sideways"}}}, tmp_path)

    def test_rejects_empty_library_prefix(self, tmp_path):
        with pytest.raises(ConfigError, match="library_prefix"):
            resolve_config({"io": {"library_prefix": ""}}, tmp_path)
