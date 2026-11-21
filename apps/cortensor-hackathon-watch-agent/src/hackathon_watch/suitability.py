"""Suitability: Allen's screen, deterministic first, model second.

Allen's profile (from the 2026-11-16 tracker baseline):
- free-only (no entry fee);
- online-first (on-site finals are a minus, not an automatic reject);
- non-student adults (student-only events are out);
- direction: LLM / Agent / AI applications / legal AI;
- resident in Singapore / US.

The deterministic rule screen runs on the list-page text only (name +
notes). It never invents facts the page did not show: when the page
gives no usable signal either way, the answer is ``unsure`` and the
model (if enabled) gets one short classification call per entry. A
model verdict is always labelled preliminary and needs human
confirmation before anyone registers.
"""

from __future__ import annotations

import re

from .models import HackathonEntry, SuitabilityVerdict

STUDENT_ONLY_PATTERNS = [
    r"student[s]?[- ]only", r"students only", r"仅限学生", r"仅限在校生",
    r"仅限.*高校学生", r"面向.*在校学生", r"for students only",
    r"undergraduate[s]? only", r"仅限本科生",
]

FEE_PATTERNS = [
    r"entry fee", r"registration fee", r"报名费", r"参赛费",
    r"ticket[s]?\s*\$[1-9]", r"报名费\s*[¥$]\s*[1-9]",
]

DIRECTION_PATTERNS = [
    r"\bllm\b", r"agent", r"agentic", r"\bai\b", r"人工智能",
    r"大模型", r"智能体", r"legal", r"法律", r"law",
    r"machine learning", r"机器学习", r"genai", r"generative ai",
    r"chatbot", r"copilot", r"rag\b", r"nlp\b",
]

ONLINE_SIGNALS = [r"online", r"线上", r"virtual", r"remote", r"hybrid", r"混合"]
ONSITE_ONLY_SIGNALS = [r"on-site only", r"线下", r"in-person only", r"现场"]


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def rule_screen(entry: HackathonEntry) -> SuitabilityVerdict:
    """Deterministic pre-screen on list-page text only."""
    text = f"{entry.name} {entry.notes or ''}"
    if _any_match(STUDENT_ONLY_PATTERNS, text):
        return SuitabilityVerdict(
            label="not-suitable",
            reason="List text says student-only; Allen is a non-student adult.")
    if _any_match(FEE_PATTERNS, text):
        return SuitabilityVerdict(
            label="not-suitable",
            reason="List text mentions an entry/registration fee; free-only rule.")
    if _any_match(DIRECTION_PATTERNS, text):
        return SuitabilityVerdict(
            label="preliminary",
            reason="Name/notes match LLM/Agent/AI/legal-AI direction; "
                   "fee, eligibility and format still need official-page confirmation.")
    return SuitabilityVerdict(
        label="unsure",
        reason="List page gives no direction signal; needs a model read or "
               "an official-page check before calling it suitable.")


def build_classify_messages(entry: HackathonEntry) -> list[dict[str, str]]:
    """Short prompt: one entry, one JSON verdict. ~120 prompt words."""
    return [
        {"role": "system",
         "content": ("You judge whether a hackathon fits one person. Reply with "
                     "JSON only: {\"label\": \"preliminary\"|\"unsure\"|\"not-suitable\", "
                     "\"reason\": \"one short sentence\"}. Rules: free-only (any fee -> "
                     "not-suitable); student-only -> not-suitable; direction must be "
                     "LLM/Agent/AI applications/legal AI; online or hybrid preferred; "
                     "resident Singapore/US. If the text gives no usable signal, say unsure.")},
        {"role": "user",
         "content": (f"Name: {entry.name}\nURL: {entry.url}\n"
                     f"Source: {entry.source}\nNotes: {entry.notes or '-'}\n"
                     f"Deadline: {entry.deadline or 'unknown'}; "
                     f"Prize: {entry.prize or 'unknown'}")},
    ]


def verdict_tool_schema() -> list[dict]:
    """Function tool so the model can answer by tool call instead of text."""
    return [{
        "type": "function",
        "function": {
            "name": "give_verdict",
            "description": "Return the preliminary suitability verdict.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string",
                              "enum": ["preliminary", "unsure", "not-suitable"]},
                    "reason": {"type": "string"},
                },
                "required": ["label", "reason"],
            },
        },
    }]
