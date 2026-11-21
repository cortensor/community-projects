"""Baseline parsing: read Allen's tracker files as the known set.

Formats (all 2026-11-16, Asia/Shanghai):

- ``open-list-20261116.md`` — numbered lines
  ``N. <Name> - <detail> ... 链接：<URL>`` (100 open entries).
- ``full-recheck-20261116.md`` — numbered lines in the "new 19" section
  ``N. <Name>（...）— <detail> ... 链接 <URL>`` or ``链接 to_verify``.
- ``full-recheck-20261116-verified.md`` — headings
  ``### N. <Name> — <detail>`` followed by ``- 链接：<URL>`` lines.

Entries whose link is ``to_verify`` have no usable URL and are keyed by
name only. Many open-list rows share one aggregator URL
(``aicpt-memo.cn``); entries sharing a URL are deduped by name instead,
so distinct events on one aggregator page are not collapsed into one.

Parsing is deliberately tolerant: a line that does not match is
skipped and counted, never guessed into an entry.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import HackathonEntry
from .normalize import entry_key, normalize_name, normalize_url

_LINK_RE = re.compile(r"https?://[^\s)>\]（(]+")
_NUMBERED_RE = re.compile(r"^\s*[A-Z]?\d+[.、]\s+(.+)$")
_HEADING_RE = re.compile(r"^###\s*\d+[.、]?\s+(.+)$")
_LINK_LINE_RE = re.compile(r"^\s*-\s*链接[:：]\s*(.*)$")

_DETAIL_MARKERS = ("已在", "新增", "面向", "主办", "承办", "截止", "链接",
                   "备注", "任务", "活动", "奖金", "总奖", "报名")


def _clean_url(raw: str) -> str:
    return raw.rstrip(").,;]。")


def _name_from_body(body: str) -> str:
    # Em-dash first (full-recheck style: name — detail).
    head = body.split("—", 1)[0] if "—" in body else body
    # Then accumulate " - " segments until a detail segment starts: a
    # segment is detail when it contains a Chinese full stop or starts
    # with a detail marker. This keeps names like
    # "Google - The Gemma 4 Developer Agent Competition" whole while
    # still cutting "Name - 华为云与小红书联合主办。截止 ..." at the dash.
    parts = re.split(r"\s+[-–]\s+", head)
    kept: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if kept and ("。" in part or part.startswith(_DETAIL_MARKERS)):
            break
        kept.append(part)
    name = " - ".join(kept) if kept else head.strip()
    # Strip a trailing parenthetical qualifier, e.g. "Name（Kaggle）".
    name = re.split(r"[（(]", name, maxsplit=1)[0]
    return re.sub(r"\s+", " ", name).strip()


def _entry_from_numbered(line: str, source: str) -> HackathonEntry | None:
    m = _NUMBERED_RE.match(line)
    if not m:
        return None
    body = m.group(1).strip()
    name = _name_from_body(body)
    if not name or len(name) < 3:
        return None
    urls = [_clean_url(u) for u in _LINK_RE.findall(body)]
    return HackathonEntry(name=name, url=urls[0] if urls else "",
                          source=source, notes="baseline 2026-11-16")


def parse_baseline_text(text: str, source: str = "baseline") -> list[HackathonEntry]:
    entries: list[HackathonEntry] = []
    pending: HackathonEntry | None = None
    for line in text.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            if pending is not None:
                entries.append(pending)
            name = _name_from_body(heading.group(1).strip())
            pending = (HackathonEntry(name=name, url="", source=source,
                                      notes="baseline 2026-11-16")
                       if name and len(name) >= 3 else None)
            continue
        link_line = _LINK_LINE_RE.match(line)
        if link_line and pending is not None:
            urls = [_clean_url(u) for u in _LINK_RE.findall(link_line.group(1))]
            if urls:
                pending.url = urls[0]
            entries.append(pending)
            pending = None
            continue
        if pending is not None and line.strip() == "":
            continue
        numbered = _entry_from_numbered(line, source)
        if numbered is not None:
            entries.append(numbered)
    if pending is not None:
        entries.append(pending)
    return entries


def dedupe_key(entry: HackathonEntry, seen_urls: dict[str, str]) -> str:
    """One dedupe key per entry, shared by load_baseline and memory seeding.

    Normalised URL first; when several entries share one URL (aggregator
    pages), fall back to the normalised name so distinct events survive.
    """
    norm_url = normalize_url(entry.url) if entry.url else ""
    if norm_url and norm_url in seen_urls:
        key = "name:" + normalize_name(entry.name)
    else:
        key = entry_key(entry.url, entry.name)
    if norm_url:
        seen_urls[norm_url] = key
    return key


def load_baseline(baseline_dir: str | Path) -> tuple[list[HackathonEntry], dict]:
    """Load + dedupe all baseline files in a directory.

    Returns (entries, stats). Dedupe: normalised URL first; when several
    entries share one URL, fall back to the normalised name so distinct
    events on one aggregator page survive.
    """
    directory = Path(baseline_dir)
    files = sorted(p for p in directory.glob("*.md"))
    entries: list[HackathonEntry] = []
    stats: dict[str, int] = {"files": len(files), "parsed": 0, "skipped_lines": 0}
    seen_keys: set[str] = set()
    seen_urls: dict[str, str] = {}
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        parsed = parse_baseline_text(text)
        stats["parsed"] += len(parsed)
        for entry in parsed:
            key = dedupe_key(entry, seen_urls)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            entries.append(entry)
    stats["deduped"] = len(entries)
    return entries, stats


def baseline_names(entries: list[HackathonEntry]) -> set[str]:
    return {normalize_name(e.name) for e in entries}
