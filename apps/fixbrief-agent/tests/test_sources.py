"""Offline tests for source loading helpers (no network)."""

import os

from fixbrief.config import normalize_no_proxy
from fixbrief.sources import html_to_text, list_samples, load_sample


def test_html_to_text_strips_scripts_and_tags():
    html = (
        "<html><head><title>x</title><style>body{}</style></head>"
        "<body><script>alert(1)</script><h1>Repair</h1>"
        "<p>Check the <b>charging port</b> first.</p></body></html>"
    )
    text = html_to_text(html)
    assert "alert(1)" not in text
    assert "charging port" in text
    assert "<" not in text


def test_load_sample_rejects_traversal():
    import pytest

    with pytest.raises((FileNotFoundError, ValueError)):
        load_sample("../pyproject.toml")


def test_list_samples_nonempty():
    assert len(list_samples()) >= 3


def test_normalize_no_proxy_strips_bracketed_ipv6(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1,::1,[::1],[fd00::1]")
    monkeypatch.setenv("no_proxy", "[::1],example.com")
    normalize_no_proxy()
    assert os.environ["NO_PROXY"] == "localhost,127.0.0.1,::1"
    assert os.environ["no_proxy"] == "example.com"
    # Idempotent.
    normalize_no_proxy()
    assert os.environ["NO_PROXY"] == "localhost,127.0.0.1,::1"
