"""Unit tests for deterministic repository security, docs, and wiring scanners."""

from __future__ import annotations

from pathlib import Path

from cortensor_release_gate.scanners import (
    scan_cortensor_wiring,
    scan_repository_docs,
    scan_repository_security,
)


def _create_compliant_repo(root: Path) -> None:
    (root / "PROJECTS.yml").write_text(
        "- name: sample-app\n  category: apps\n  owner: '@alice'\n  status: active\n  version: v0.1.0\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Sample App\nBuilt with OpenMinion 0.1 SDK.\n",
        encoding="utf-8",
    )
    (root / "STATUS.md").write_text("# Status\nActive.\n", encoding="utf-8")
    (root / "RELEASE.md").write_text("# Release\n## v0.1.0\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\ndependencies = ["openminion==0.1.23"]\n',
        encoding="utf-8",
    )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "BUILDING_BLOCKS_TESTED.md").write_text("# Tested\n", encoding="utf-8")
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "app.py").write_text(
        'import openminion\nENDPOINT = "https://api.cortensor.app/v1"\n',
        encoding="utf-8",
    )
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "test_app.py").write_text("def test_ok(): assert True\n", encoding="utf-8")


def test_compliant_repo_passes_all_scanners(tmp_path: Path) -> None:
    _create_compliant_repo(tmp_path)
    sec = scan_repository_security(tmp_path)
    docs = scan_repository_docs(tmp_path)
    wiring = scan_cortensor_wiring(tmp_path)

    assert sec.passed is True
    assert sec.findings == []
    assert docs.passed is True
    assert docs.missing_files == []
    assert wiring.uses_openminion is True
    assert wiring.openminion_pin == "==0.1.23"
    assert wiring.has_tests is True
    assert wiring.cortensor_endpoints_detected == ["https://api.cortensor.app/v1"]
    assert wiring.findings == []


def test_security_scanner_flags_dotenv_and_pem_key(tmp_path: Path) -> None:
    _create_compliant_repo(tmp_path)
    (tmp_path / ".env").write_text("CORTENSOR_API_KEY=demo\n", encoding="utf-8")
    (tmp_path / "src" / "leak.py").write_text(
        'PEM = "-----BEGIN ' + 'PRIVATE KEY-----"\n',
        encoding="utf-8",
    )

    sec = scan_repository_security(tmp_path)
    ids = {f.check_id for f in sec.findings}
    assert sec.passed is False
    assert "SEC-DOTENV-FILE" in ids
    assert "SEC-PEM-KEY" in ids


def test_docs_scanner_flags_missing_files_and_bad_yaml(tmp_path: Path) -> None:
    (tmp_path / "PROJECTS.yml").write_text("name: [unclosed\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Plain Readme\n", encoding="utf-8")

    docs = scan_repository_docs(tmp_path)
    ids = {f.check_id for f in docs.findings}
    assert docs.passed is False
    assert "STATUS.md" in docs.missing_files
    assert "DOC-PROJECTS-YAML" in ids
    assert "DOC-README-OPENMINION" in ids
    assert "DOC-HACKATHON5-NOTES" in ids


def test_wiring_scanner_flags_missing_openminion_and_tests(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "plain.py").write_text("print('hello')\n", encoding="utf-8")

    wiring = scan_cortensor_wiring(tmp_path)
    ids = {f.check_id for f in wiring.findings}
    assert wiring.uses_openminion is False
    assert wiring.has_tests is False
    assert "WIRE-NO-OPENMINION" in ids
    assert "WIRE-UNPINNED-OPENMINION" in ids
    assert "WIRE-NO-TESTS" in ids


def test_cli_module_entrypoint_help() -> None:
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    res = subprocess.run(
        [sys.executable, "-m", "cortensor_release_gate.cli", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    assert "audit" in res.stdout
    assert "probe" in res.stdout
