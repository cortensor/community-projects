"""Multilingual phone-repair glossary (EN / ES / PT / AR).

Starter glossary of common repair terms used to localize briefs and to
give the model exact terminology instead of letting it improvise
translations. Arabic entries use Modern Standard Arabic technical terms.
"""

from __future__ import annotations

from .models import Language

# term_en -> {lang: translation}
GLOSSARY: dict[str, dict[Language, str]] = {
    "charging port": {
        Language.EN: "charging port",
        Language.ES: "puerto de carga",
        Language.PT: "porta de carregamento",
        Language.AR: "منفذ الشحن",
    },
    "charger": {
        Language.EN: "charger",
        Language.ES: "cargador",
        Language.PT: "carregador",
        Language.AR: "شاحن",
    },
    "cable": {
        Language.EN: "cable",
        Language.ES: "cable",
        Language.PT: "cabo",
        Language.AR: "كابل",
    },
    "battery": {
        Language.EN: "battery",
        Language.ES: "batería",
        Language.PT: "bateria",
        Language.AR: "بطارية",
    },
    "screen": {
        Language.EN: "screen",
        Language.ES: "pantalla",
        Language.PT: "tela",
        Language.AR: "شاشة",
    },
    "touch screen": {
        Language.EN: "touch screen",
        Language.ES: "pantalla táctil",
        Language.PT: "tela sensível ao toque",
        Language.AR: "شاشة لمس",
    },
    "motherboard": {
        Language.EN: "motherboard",
        Language.ES: "placa base",
        Language.PT: "placa-mãe",
        Language.AR: "اللوحة الأم",
    },
    "connector": {
        Language.EN: "connector",
        Language.ES: "conector",
        Language.PT: "conector",
        Language.AR: "موصّل",
    },
    "screwdriver": {
        Language.EN: "screwdriver",
        Language.ES: "destornillador",
        Language.PT: "chave de fenda",
        Language.AR: "مفك",
    },
    "tweezers": {
        Language.EN: "tweezers",
        Language.ES: "pinzas",
        Language.PT: "pinça",
        Language.AR: "ملقط",
    },
    "heat gun": {
        Language.EN: "heat gun",
        Language.ES: "pistola de calor",
        Language.PT: "soprador térmico",
        Language.AR: "مسدس حراري",
    },
    "suction cup": {
        Language.EN: "suction cup",
        Language.ES: "ventosa",
        Language.PT: "ventosa",
        Language.AR: "كوب شفط",
    },
    "spudger": {
        Language.EN: "spudger",
        Language.ES: "espátula de apertura",
        Language.PT: "espátula de abertura",
        Language.AR: "أداة فتح بلاستيكية",
    },
    "multimeter": {
        Language.EN: "multimeter",
        Language.ES: "multímetro",
        Language.PT: "multímetro",
        Language.AR: "مقياس متعدد",
    },
    "soldering iron": {
        Language.EN: "soldering iron",
        Language.ES: "soldador",
        Language.PT: "ferro de solda",
        Language.AR: "كاوية لحام",
    },
    "not charging": {
        Language.EN: "not charging",
        Language.ES: "no carga",
        Language.PT: "não carrega",
        Language.AR: "لا يشحن",
    },
    "black screen": {
        Language.EN: "black screen",
        Language.ES: "pantalla negra",
        Language.PT: "tela preta",
        Language.AR: "شاشة سوداء",
    },
    "boot loop": {
        Language.EN: "boot loop",
        Language.ES: "bucle de arranque",
        Language.PT: "loop de inicialização",
        Language.AR: "حلقة إعادة تشغيل",
    },
    "water damage": {
        Language.EN: "water damage",
        Language.ES: "daño por agua",
        Language.PT: "danos por água",
        Language.AR: "أضرار المياه",
    },
    "overheating": {
        Language.EN: "overheating",
        Language.ES: "sobrecalentamiento",
        Language.PT: "superaquecimento",
        Language.AR: "ارتفاع درجة الحرارة",
    },
    "battery drain": {
        Language.EN: "battery drain",
        Language.ES: "descarga rápida de batería",
        Language.PT: "drenagem da bateria",
        Language.AR: "استنزاف البطارية",
    },
    "no signal": {
        Language.EN: "no signal",
        Language.ES: "sin señal",
        Language.PT: "sem sinal",
        Language.AR: "لا توجد إشارة",
    },
    "force restart": {
        Language.EN: "force restart",
        Language.ES: "reinicio forzado",
        Language.PT: "reinicialização forçada",
        Language.AR: "إعادة تشغيل قسرية",
    },
    "factory reset": {
        Language.EN: "factory reset",
        Language.ES: "restablecimiento de fábrica",
        Language.PT: "redefinição de fábrica",
        Language.AR: "إعادة ضبط المصنع",
    },
    "backup": {
        Language.EN: "backup",
        Language.ES: "copia de seguridad",
        Language.PT: "backup",
        Language.AR: "نسخة احتياطية",
    },
    "warranty": {
        Language.EN: "warranty",
        Language.ES: "garantía",
        Language.PT: "garantia",
        Language.AR: "ضمان",
    },
    "safety warning": {
        Language.EN: "safety warning",
        Language.ES: "advertencia de seguridad",
        Language.PT: "aviso de segurança",
        Language.AR: "تحذير سلامة",
    },
    "swollen battery": {
        Language.EN: "swollen battery",
        Language.ES: "batería hinchada",
        Language.PT: "bateria inchada",
        Language.AR: "بطارية منتفخة",
    },
    "adhesive": {
        Language.EN: "adhesive",
        Language.ES: "adhesivo",
        Language.PT: "adesivo",
        Language.AR: "مادة لاصقة",
    },
    "gasket": {
        Language.EN: "gasket",
        Language.ES: "junta",
        Language.PT: "junta",
        Language.AR: "حشية",
    },
}


def lookup(term: str, lang: Language) -> str | None:
    """Return the glossary translation for ``term`` or ``None``."""
    entry = GLOSSARY.get(term.strip().lower())
    if entry is None:
        return None
    return entry.get(lang)


def translate_terms(terms: list[str], lang: Language) -> dict[str, str]:
    """Translate every known term; unknown terms pass through unchanged."""
    out: dict[str, str] = {}
    for term in terms:
        out[term] = lookup(term, lang) or term
    return out


def known_terms() -> list[str]:
    return sorted(GLOSSARY.keys())
