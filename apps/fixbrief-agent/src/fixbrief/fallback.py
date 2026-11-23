"""Deterministic brief builder (no model).

Used for offline tests and as an honest fallback when no model provider
is reachable. Briefs built here are always labeled
``generated_by="deterministic-fallback"`` so they can never be mistaken
for model output.
"""

from __future__ import annotations

from .facts import extract_facts, infer_difficulty
from .glossary import translate_terms
from .models import Difficulty, Language, RepairBrief, SourceRef

_SUMMARY_TEMPLATES = {
    Language.EN: "{device} with symptom '{symptom}'. Brief assembled from {n} source(s) by deterministic extraction.",
    Language.ES: "{device} con el síntoma '{symptom}'. Resumen armado desde {n} fuente(s) por extracción determinista.",
    Language.PT: "{device} com o sintoma '{symptom}'. Resumo montado a partir de {n} fonte(s) por extração determinística.",
    Language.AR: "{device} مع العرض '{symptom}'. تم تجميع الملخص من {n} مصدر بواسطة استخراج حتمي.",
}

_DEFAULT_WARNINGS = {
    Language.EN: [
        "Disconnect the battery before board-level work.",
        "Back up user data before any reset or board replacement.",
        "Opening the device may void the manufacturer warranty.",
    ],
    Language.ES: [
        "Desconecta la batería antes de trabajar en la placa.",
        "Haz una copia de seguridad antes de cualquier restablecimiento o cambio de placa.",
        "Abrir el equipo puede anular la garantía del fabricante.",
    ],
    Language.PT: [
        "Desconecte a bateria antes de trabalhar na placa.",
        "Faça backup dos dados antes de qualquer redefinição ou troca de placa.",
        "Abrir o aparelho pode anular a garantia do fabricante.",
    ],
    Language.AR: [
        "افصل البطارية قبل العمل على اللوحة.",
        "انسخ البيانات احتياطيًا قبل أي إعادة ضبط أو استبدال للوحة.",
        "قد يؤدي فتح الجهاز إلى إلغاء ضمان الشركة المصنعة.",
    ],
}


def build_fallback_brief(
    device: str,
    symptom: str,
    source_texts: list[tuple[SourceRef, str]],
    language: Language = Language.EN,
) -> RepairBrief:
    """Assemble a validated brief from extracted facts only."""
    merged_causes: list[str] = []
    merged_steps: list[str] = []
    merged_tools: list[str] = []
    merged_warnings: list[str] = []
    difficulty = "medium"
    time_hints: list[int] = []

    for _ref, text in source_texts:
        facts = extract_facts(text)
        for item in facts.causes:
            if item not in merged_causes:
                merged_causes.append(item)
        for item in facts.steps:
            if item not in merged_steps:
                merged_steps.append(item)
        for item in facts.tools:
            if item not in merged_tools:
                merged_tools.append(item)
        for item in facts.warnings:
            if item not in merged_warnings:
                merged_warnings.append(item)
        time_hints.extend(facts.time_hints_minutes)
        candidate = infer_difficulty(facts)
        order = ["easy", "medium", "hard", "professional"]
        if order.index(candidate) > order.index(difficulty):
            difficulty = candidate

    if language != Language.EN:
        merged_tools = [
            translate_terms([t], language)[t] for t in merged_tools
        ]

    warnings = merged_warnings or list(_DEFAULT_WARNINGS[language])
    diagnostic = merged_steps[:4]
    repair = merged_steps[4:] or merged_steps[:4]

    return RepairBrief(
        device=device,
        symptom=symptom,
        language=language,
        summary=_SUMMARY_TEMPLATES[language].format(
            device=device, symptom=symptom, n=len(source_texts)
        ),
        likely_causes=merged_causes[:6],
        diagnostic_steps=diagnostic,
        repair_steps=repair,
        tools_needed=merged_tools[:12],
        difficulty=Difficulty(difficulty),
        estimated_time_minutes=(max(time_hints) if time_hints else 30),
        safety_warnings=warnings[:6],
        sources=[ref for ref, _ in source_texts],
        generated_by="deterministic-fallback",
    )
