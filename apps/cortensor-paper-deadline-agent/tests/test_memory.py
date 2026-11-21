"""Memory: mark-once dedup, export/import round-trip."""

import json

from paper_watch.memory import RemindedMemory


def test_mark_dedups(tmp_path):
    mem = RemindedMemory(tmp_path / "reminded.json")
    assert len(mem) == 0
    assert mem.mark(["CVPR|2026-11-27|full", "FAKE|2026-12-01|abstract"]) == 2
    assert mem.mark(["CVPR|2026-11-27|full"]) == 0  # already reminded
    assert "CVPR|2026-11-27|full" in mem
    assert len(mem) == 2


def test_persists_across_instances(tmp_path):
    path = tmp_path / "reminded.json"
    RemindedMemory(path).mark(["A|2026-12-01|full"])
    assert "A|2026-12-01|full" in RemindedMemory(path)


def test_export_import_round_trip(tmp_path):
    src = RemindedMemory(tmp_path / "a.json")
    src.mark(["A|2026-12-01|full", "B|2026-12-02|full"])
    exported = tmp_path / "export.json"
    src.export_to(exported)
    assert json.loads(exported.read_text())["reminded"].keys() == {
        "A|2026-12-01|full", "B|2026-12-02|full",
    }
    dst = RemindedMemory(tmp_path / "b.json")
    assert dst.import_from(exported) == 2
    assert dst.import_from(exported) == 0  # merge is idempotent
    assert len(dst) == 2


def test_corrupt_file_loads_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert len(RemindedMemory(path)) == 0
