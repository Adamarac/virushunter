"""Tests for configuration loading and validation."""

import textwrap

import pytest

from virushunter.config import Config, ConfigError, load


@pytest.fixture
def overlay(tmp_path):
    def write(body):
        path = tmp_path / "over.yaml"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path
    return write


class TestDefaults:
    def test_default_config_loads(self):
        assert isinstance(load(), Config)

    def test_carries_the_values_that_were_hard_coded(self):
        # These are the literals that lived in virus_hunter.py's __main__. If one
        # drifts, the generated scripts change and verify.sh will say so -- this
        # just names the expectation.
        cfg = load()
        assert cfg["compute.threads"] == 48
        assert cfg["compute.query_splits"] == 50
        assert cfg["params.evalue"] == "0.01"
        assert cfg["params.min_read_length"] == 50
        assert cfg["params.contig_length_pre_cap3"] == 300
        assert cfg["params.contig_length_post_cap3"] == 1500
        assert cfg["params.mystery_min_length"] == 1000
        assert cfg["params.kmers.abyss"] == "31"
        assert cfg["steps.assembly.mode"] == "no"
        assert cfg["steps.paired_end"] is False

    def test_evalue_is_a_string(self):
        # Pasted straight into command lines; reformatting it would change the
        # generated scripts (0.01 -> 0.01 is fine, but 1e-2 is not).
        assert isinstance(load()["params.evalue"], str)

    def test_cluster_node_list_matches_the_original(self):
        cfg = load()
        assert len(cfg["cluster.nodes"]) == 20
        assert cfg["cluster.nodes"][0] == "bsidna4"


class TestLookup:
    def test_dotted_paths(self):
        assert load()["params.kmers.soap"] == "31"

    def test_missing_key_raises(self):
        with pytest.raises(ConfigError, match="chave ausente"):
            load()["params.nope"]

    def test_missing_key_with_default_returns_it(self):
        assert load().get("params.nope", "fallback") == "fallback"

    def test_as_dict_is_a_copy(self):
        cfg = load()
        snapshot = cfg.as_dict()
        snapshot["compute"]["threads"] = 999
        assert cfg["compute.threads"] == 48


class TestOverlay:
    def test_overlay_wins(self, overlay):
        cfg = load(overlay("compute:\n  threads: 8\n"))
        assert cfg["compute.threads"] == 8

    def test_overlay_is_partial(self, overlay):
        # Setting one key must not wipe its siblings.
        cfg = load(overlay("compute:\n  threads: 8\n"))
        assert cfg["compute.query_splits"] == 50
        assert cfg["params.evalue"] == "0.01"

    def test_overlay_reaches_nested_keys(self, overlay):
        cfg = load(overlay("params:\n  kmers:\n    abyss: '55'\n"))
        assert cfg["params.kmers.abyss"] == "55"
        assert cfg["params.kmers.soap"] == "31"

    def test_empty_overlay_is_allowed(self, overlay):
        assert load(overlay(""))["compute.threads"] == 48

    def test_overrides_argument(self):
        cfg = load(overrides={"compute": {"threads": 4}})
        assert cfg["compute.threads"] == 4


class TestValidation:
    def test_rejects_unknown_assembly_mode(self, overlay):
        with pytest.raises(ConfigError, match="assembly.mode"):
            load(overlay("steps:\n  assembly:\n    mode: sideways\n"))

    def test_accepts_denovo(self, overlay):
        # The published method's mode -- must stay reachable. ADR-0004.
        assert load(overlay("steps:\n  assembly:\n    mode: denovo\n"))["steps.assembly.mode"] == "denovo"

    def test_rejects_unknown_phage_mode(self, overlay):
        with pytest.raises(ConfigError, match="phage"):
            load(overlay("steps:\n  viral_search:\n    phage: maybe\n"))

    def test_rejects_non_numeric_evalue(self, overlay):
        # K1 was a threshold that was never numeric. Catch it at load time.
        with pytest.raises(ConfigError, match="evalue"):
            load(overlay('params:\n  evalue: "muito baixo"\n'))

    def test_accepts_scientific_notation_evalue(self, overlay):
        assert load(overlay('params:\n  evalue: "1e-10"\n'))["params.evalue"] == "1e-10"

    def test_rejects_wrong_type(self, overlay):
        with pytest.raises(ConfigError, match="threads"):
            load(overlay("compute:\n  threads: muitas\n"))

    def test_rejects_bool_where_int_expected(self, overlay):
        # bool subclasses int; True would otherwise pass as 1 thread.
        with pytest.raises(ConfigError, match="bool"):
            load(overlay("compute:\n  threads: true\n"))

    @pytest.mark.parametrize("value", [0, -1])
    def test_rejects_non_positive_compute(self, overlay, value):
        with pytest.raises(ConfigError, match=">= 1"):
            load(overlay(f"compute:\n  threads: {value}\n"))

    def test_rejects_non_mapping_overlay(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("- isto é uma lista\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="mapeamento"):
            load(path)
