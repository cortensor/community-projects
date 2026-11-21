"""Repo memory: record / lookup / label counts / MemoryBundle round-trip."""

from issue_triage.memory import RepoMemory
from issue_triage.models import TriageDecision


def _decision(repo="openminion/openminion", number=1, component="area:brain",
              issue_type="bug", labels=("bug",), status="decided"):
    return TriageDecision(
        repo=repo, issue_number=number, issue_type=issue_type,
        severity="high", component=component, labels=list(labels),
        route="ready-to-fix", confidence=0.8, status=status,
    )


def test_record_and_load(tmp_path):
    mem = RepoMemory(tmp_path)
    mem.record(_decision(number=778))
    loaded = mem.load("openminion/openminion")
    assert len(loaded) == 1
    assert loaded[0].issue_number == 778


def test_record_same_issue_replaces(tmp_path):
    mem = RepoMemory(tmp_path)
    mem.record(_decision(number=1, component="area:brain"))
    mem.record(_decision(number=1, component="area:runtime"))
    loaded = mem.load("openminion/openminion")
    assert len(loaded) == 1
    assert loaded[0].component == "area:runtime"


def test_lookup_prefers_same_component(tmp_path):
    mem = RepoMemory(tmp_path)
    mem.record(_decision(number=1, component="area:brain"))
    mem.record(_decision(number=2, component="area:runtime"))
    found = mem.lookup("openminion/openminion", component="area:runtime")
    assert [d.issue_number for d in found] == [2]


def test_lookup_decided_before_proposed(tmp_path):
    mem = RepoMemory(tmp_path)
    mem.record(_decision(number=1, component="area:brain", status="proposed"))
    mem.record(_decision(number=2, component="area:brain", status="decided"))
    found = mem.lookup("openminion/openminion", component="area:brain")
    assert [d.issue_number for d in found] == [2]


def test_mark_decided(tmp_path):
    mem = RepoMemory(tmp_path)
    mem.record(_decision(number=5, status="proposed"))
    mem.mark_decided("openminion/openminion", 5)
    assert mem.load("openminion/openminion")[0].status == "decided"


def test_label_counts(tmp_path):
    mem = RepoMemory(tmp_path)
    mem.record(_decision(number=1, labels=["bug", "area:brain"]))
    mem.record(_decision(number=2, labels=["bug"]))
    assert mem.label_counts("openminion/openminion") == {"bug": 2, "area:brain": 1}


def test_missing_repo_loads_empty(tmp_path):
    assert RepoMemory(tmp_path).load("nobody/nothing") == []


def test_bundle_export_import_round_trip(tmp_path):
    mem = RepoMemory(tmp_path)
    mem.record(_decision(number=778))
    bundle_path = tmp_path / "bundle.json"
    info = mem.export_bundle("openminion/openminion", bundle_path)
    assert info["item_count"] == 1
    assert bundle_path.is_file()

    mem2 = RepoMemory(tmp_path / "other")
    added = mem2.import_bundle_file(bundle_path, "openminion/openminion")
    assert added == 1
    assert mem2.load("openminion/openminion")[0].issue_number == 778
    # re-import is idempotent
    assert mem2.import_bundle_file(bundle_path, "openminion/openminion") == 0
