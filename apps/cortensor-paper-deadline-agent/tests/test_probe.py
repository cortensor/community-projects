"""Probe structure + deterministic probes (no model calls)."""

from conftest import TODAY
from paper_watch.probe import PROBE_NAMES, render_probes_doc, run_probes


def test_probe_names_cover_only_used_blocks():
    assert len(PROBE_NAMES) == 10
    assert "verification_honesty" in PROBE_NAMES
    # No verdict/validation blocks: this agent does not judge or score.
    assert not any("verdict" in n or "consensus" in n for n in PROBE_NAMES)


def test_skip_model_probes_run_offline(data_dir):
    results = run_probes(skip_model=True, data_dir=data_dir, today=TODAY)
    names = [r.name for r in results]
    assert names == [
        "runtime_isolation",
        "memory_bundle_portability",
        "error_and_timeout_contracts",
        "verification_honesty",
    ]
    by_name = {r.name: r for r in results}
    assert by_name["verification_honesty"].status == "pass"
    assert by_name["memory_bundle_portability"].status == "pass"
    assert by_name["runtime_isolation"].status == "pass"
    assert by_name["error_and_timeout_contracts"].status == "pass"


def test_probes_doc_lists_every_probe(data_dir):
    results = run_probes(skip_model=True, data_dir=data_dir, today=TODAY)
    from paper_watch.config import resolve_preset

    doc = render_probes_doc(results, resolve_preset())
    for name in PROBE_NAMES:
        assert name in doc
    assert "verification_honesty" in doc
    assert "$0" in doc
