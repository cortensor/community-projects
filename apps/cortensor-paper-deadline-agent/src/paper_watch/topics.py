"""Topic matching for ``paper-watch brief --topic``.

Matching is substring-based over the venue's ``field`` / ``full_name`` /
``abbreviation`` (all lower-cased), plus a small curated synonym table so
Chinese topics and English topics both work, e.g. "人工智能" matches the
field "人工智能", and "vision" matches CVPR ("Computer Vision and Pattern
Recognition"). No venue is ever invented: if nothing matches, the caller
says so honestly.
"""

from __future__ import annotations

from .store import Deadline

__all__ = ["match_topic", "TOPIC_SYNONYMS"]

# topic (normalised) -> extra match strings. Keys are matched as substrings
# too, so "人工智能" also matches via the field text itself; the table only
# adds cross-language bridges.
TOPIC_SYNONYMS: dict[str, list[str]] = {
    "人工智能": ["artificial intelligence", "ai"],
    "ai": ["人工智能", "artificial intelligence"],
    "artificial intelligence": ["人工智能", "ai"],
    "机器学习": ["machine learning"],
    "machine learning": ["机器学习"],
    "计算机视觉": ["computer vision", "vision"],
    "vision": ["computer vision", "计算机视觉"],
    "computer vision": ["计算机视觉"],
    "自然语言处理": ["natural language", "nlp", "computational linguistics"],
    "nlp": ["natural language", "自然语言处理"],
    "数据挖掘": ["data mining", "knowledge discovery"],
    "data mining": ["数据挖掘"],
    "数据库": ["database"],
    "database": ["数据库"],
    "计算机网络": ["computer network", "network"],
    "network": ["计算机网络"],
    "安全": ["security", "privacy", "cryptography"],
    "security": ["安全", "网络与信息安全"],
    "体系结构": ["architecture"],
    "architecture": ["体系结构"],
    "软件工程": ["software engineering"],
    "software engineering": ["软件工程"],
    "图形学": ["graphics", "visualization"],
    "graphics": ["图形学", "计算机图形学"],
    "人机交互": ["human-computer interaction", "hci"],
    "hci": ["人机交互"],
    "机器人": ["robotics", "robot"],
    "robotics": ["机器人"],
    "理论": ["theory", "theoretical"],
    "theory": ["理论"],
    "法律": ["law", "legal"],
    "law": ["法律"],
    "生物信息学": ["bioinformatics"],
    "bioinformatics": ["生物信息学"],
    "多媒体": ["multimedia"],
    "multimedia": ["多媒体"],
    "信息检索": ["information retrieval"],
    "information retrieval": ["信息检索"],
    "操作系统": ["operating system"],
    "operating system": ["操作系统"],
    "编译": ["compiler", "programming language"],
}


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def match_topic(topic: str, deadlines: list[Deadline]) -> list[Deadline]:
    """Deadlines whose venue matches the topic, earliest deadline first."""
    needle = _norm(topic)
    if not needle:
        return []
    keys = [needle] + [_norm(s) for s in TOPIC_SYNONYMS.get(needle, [])]
    # Also allow a synonym key to match when the user typed the synonym.
    for key, syns in TOPIC_SYNONYMS.items():
        if _norm(key) == needle:
            keys += [_norm(s) for s in syns]
    hits: list[Deadline] = []
    for d in deadlines:
        hay = _norm(f"{d.field} {d.full_name} {d.abbreviation}")
        if any(k and k in hay for k in keys):
            hits.append(d)
    hits.sort(key=lambda d: (d.deadline_date or "", d.abbreviation))
    return hits
