from hackathon_watch.memory import WatchMemory


def test_record_and_known(tmp_state):
    mem = WatchMemory(tmp_state / "memory.json")
    assert len(mem) == 0
    mem.record("url:https://example.test/a", "Hack A", "https://example.test/a",
               source="devfolio", first_seen="2026-11-17T00:00:00+00:00")
    assert mem.known("url:https://example.test/a")
    assert not mem.known("url:https://example.test/b")
    assert len(mem) == 1


def test_record_is_idempotent_and_persists(tmp_state):
    path = tmp_state / "memory.json"
    mem = WatchMemory(path)
    mem.record("url:https://example.test/a", "Hack A", "https://example.test/a")
    mem.record("url:https://example.test/a", "Hack A renamed",
               "https://example.test/a")
    assert len(mem) == 1
    mem2 = WatchMemory(path)
    assert len(mem2) == 1
    assert mem2.get("url:https://example.test/a").name == "Hack A renamed"


def test_mark_reminded(tmp_state):
    mem = WatchMemory(tmp_state / "memory.json")
    mem.record("k1", "Hack A", "https://example.test/a")
    assert mem.get("k1").reminded is False
    mem.mark_reminded("k1")
    assert mem.get("k1").reminded is True


def test_export_import_json_round_trip(tmp_state):
    mem = WatchMemory(tmp_state / "memory.json")
    mem.record("url:https://example.test/a", "Hack A", "https://example.test/a",
               verdict="preliminary")
    exported = mem.export_json(tmp_state / "export.json")
    mem2 = WatchMemory(tmp_state / "memory2.json")
    assert mem2.import_json(exported) == 1
    assert mem2.get("url:https://example.test/a").verdict == "preliminary"


def test_export_import_bundle_round_trip(tmp_state):
    mem = WatchMemory(tmp_state / "memory.json")
    mem.record("url:https://example.test/a", "Hack A", "https://example.test/a",
               source="devfolio", verdict="unsure")
    bundle_path = mem.export_bundle(tmp_state / "bundle.json")
    mem2 = WatchMemory(tmp_state / "memory2.json")
    assert mem2.import_bundle_file(bundle_path) == 1
    entry = mem2.get("url:https://example.test/a")
    assert entry is not None and entry.name == "Hack A"
    assert entry.verdict == "unsure"


def test_corrupt_memory_file_loads_empty(tmp_state):
    path = tmp_state / "memory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    mem = WatchMemory(path)
    assert len(mem) == 0
