import re
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Optional

from . import config


def _lang(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["siapa", "apa", "kapan", "tanggal", "hari", "sekarang", "saat ini", "presiden", "namaku", "nama saya"]):
        return "id"
    return "en"


def _now_dt() -> datetime:
    tzname = getattr(config, "TIMEZONE", "Asia/Jakarta")
    try:
        tz = ZoneInfo(tzname)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


MONTHS_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}


def _fmt_date(d: date, lang: str) -> str:
    if lang == "id":
        return f"{d.day} {MONTHS_ID[d.month]} {d.year}"
    return d.isoformat()


def _is_today_query(t: str) -> bool:
    t = t.lower().strip()
    pats = [
        r"^tanggal\s+berapa\s+sekarang\??$",
        r"^hari\s+ini\s+tanggal\s+berapa\??$",
        r"^what'?s\s+the\s+date\s+today\??$",
        r"^what\s+is\s+the\s+date\s+today\??$",
    ]
    return any(re.search(p, t) for p in pats)


def try_answer(user_text: str) -> Optional[str]:
    if not user_text:
        return None
    lang = _lang(user_text)
    now = _now_dt()

    # Today/date queries
    if _is_today_query(user_text):
        d = now.date()
        if lang == "id":
            return f"Hari ini tanggal {_fmt_date(d, 'id')}."  # short and clear
        return f"Today is {_fmt_date(d, 'en')}."

    return None
