"""Deterministic fact extraction from repair source text.

Pure-Python heuristics — no model involved. The same extractor feeds the
offline fallback brief and the OpenMinion tools, so both paths are
grounded in identical facts.

Two passes:
1. Section-aware pass for Markdown sources (bundled samples): numbered
   items are steps; bullets under Causes/Tools/Warnings headings go to
   their own buckets. Headings never leak into facts.
2. Sentence-pattern pass for unstructured text (live web pages):
   cause/warning signal patterns over cleaned sentences.
"""

from __future__ import annotations

import re

from .models import RepairFacts

_CAUSE_PATTERNS = [
    re.compile(r"\b(cause[sd]?|caused by|due to|because of)\b", re.IGNORECASE),
    re.compile(r"\b(faulty|damaged|worn|corroded|loose|swollen|dead)\b", re.IGNORECASE),
]
_NUMBERED_PATTERN = re.compile(r"^\s*\d+[.)]\s+(.+)$")
_BULLET_PATTERN = re.compile(r"^\s*[-*•]\s+(.+)$")
_HEADING_PATTERN = re.compile(r"^\s*#{1,6}\s+(.+)$")
_WARNING_PATTERNS = [
    re.compile(r"\b(warning|caution|danger|careful|never|do not|avoid)\b", re.IGNORECASE),
]
_TOOL_KEYWORDS = [
    "screwdriver", "tweezers", "heat gun", "suction cup", "spudger",
    "multimeter", "soldering iron", "pry tool", "opening pick",
    "isopropyl alcohol", "compressed air", "replacement battery",
    "replacement screen", "charging board", "adhesive", "gasket",
]
_DEVICE_PATTERNS = [
    re.compile(r"\b(Samsung|iPhone|Redmi|Xiaomi|Tecno|Infinix|Motorola|Pixel)\b[^\n.,;]{0,40}", re.IGNORECASE),
]
_SYMPTOM_KEYWORDS = [
    "not charging", "black screen", "boot loop", "water damage",
    "overheating", "battery drain", "no signal", "won't turn on",
    "touch not working", "restarting",
]
_DIFFICULTY_SIGNALS = [
    (re.compile(r"\b(solder|microsolder|board.level|reball)\b", re.IGNORECASE), "board-level work"),
    (re.compile(r"\b(open|disassembl|remove the (back|screen|battery))\b", re.IGNORECASE), "device must be opened"),
    (re.compile(r"\b(software|settings|restart|reset)\b", re.IGNORECASE), "software-level fix possible"),
]
_TIME_PATTERN = re.compile(r"(\d{1,3})\s*(?:-|–|to)?\s*(\d{1,3})?\s*minutes?", re.IGNORECASE)


def _clean(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip(" -*•\t")


def _section_bucket(heading: str) -> str | None:
    lowered = heading.lower()
    if "cause" in lowered:
        return "causes"
    if "tool" in lowered or "part" in lowered:
        return "tools"
    if "warn" in lowered or "safety" in lowered:
        return "warnings"
    if any(k in lowered for k in ("procedure", "diagnos", "repair", "step", "fix")):
        return "steps"
    return None


def _sentences(text: str) -> list[str]:
    cleaned_lines = []
    for line in text.splitlines():
        if _HEADING_PATTERN.match(line):
            continue
        cleaned_lines.append(line)
    joined = "\n".join(cleaned_lines)
    parts = re.split(r"(?<=[.!?])\s+|\n+", joined)
    out = []
    for part in parts:
        sentence = _clean(part)
        if len(sentence) > 12:
            out.append(sentence)
    return out


def extract_facts(text: str) -> RepairFacts:
    """Extract structured repair facts from plain text."""
    facts = RepairFacts(char_count=len(text))
    lowered = text.lower()

    for pattern in _DEVICE_PATTERNS:
        for match in pattern.finditer(text):
            hint = _clean(match.group(0))
            if hint and hint not in facts.device_hints:
                facts.device_hints.append(hint)

    for keyword in _SYMPTOM_KEYWORDS:
        if keyword in lowered and keyword not in facts.symptom_hints:
            facts.symptom_hints.append(keyword)

    for keyword in _TOOL_KEYWORDS:
        if keyword in lowered and keyword not in facts.tools:
            facts.tools.append(keyword)

    # Pass 1: section-aware line parsing.
    section: str | None = None
    for line in text.splitlines():
        heading_match = _HEADING_PATTERN.match(line)
        if heading_match:
            section = _section_bucket(heading_match.group(1))
            continue
        numbered = _NUMBERED_PATTERN.match(line)
        if numbered:
            step = _clean(numbered.group(1))
            if step and step not in facts.steps:
                facts.steps.append(step)
            continue
        bullet = _BULLET_PATTERN.match(line)
        if bullet and section is not None:
            item = _clean(bullet.group(1))
            bucket = getattr(facts, section)
            if item and item not in bucket:
                bucket.append(item)

    # Pass 2: sentence patterns (fills gaps for unstructured sources).
    for sentence in _sentences(text):
        if any(p.search(sentence) for p in _CAUSE_PATTERNS):
            if sentence not in facts.causes:
                facts.causes.append(sentence)
        if any(p.search(sentence) for p in _WARNING_PATTERNS):
            if sentence not in facts.warnings:
                facts.warnings.append(sentence)

    for pattern, label in _DIFFICULTY_SIGNALS:
        if pattern.search(text) and label not in facts.difficulty_signals:
            facts.difficulty_signals.append(label)

    for match in _TIME_PATTERN.finditer(text):
        try:
            minutes = int(match.group(2) or match.group(1))
        except (TypeError, ValueError):
            continue
        if 1 <= minutes <= 480 and minutes not in facts.time_hints_minutes:
            facts.time_hints_minutes.append(minutes)

    # Dedupe tools case-insensitively (keyword scan + section bullets).
    seen_tools: set[str] = set()
    deduped_tools: list[str] = []
    for tool_name in facts.tools:
        key = tool_name.lower()
        if key not in seen_tools:
            seen_tools.add(key)
            deduped_tools.append(tool_name)
    facts.tools = deduped_tools

    # Keep outputs bounded and deterministic.
    facts.causes = facts.causes[:8]
    facts.steps = facts.steps[:20]
    facts.tools = facts.tools[:16]
    facts.warnings = facts.warnings[:8]
    facts.device_hints = facts.device_hints[:5]
    return facts


def infer_difficulty(facts: RepairFacts) -> str:
    """Map difficulty signals to a brief difficulty label."""
    signals = set(facts.difficulty_signals)
    if "board-level work" in signals:
        return "professional"
    if "device must be opened" in signals:
        return "hard" if len(facts.steps) > 8 else "medium"
    if "software-level fix possible" in signals:
        return "easy"
    return "medium"
