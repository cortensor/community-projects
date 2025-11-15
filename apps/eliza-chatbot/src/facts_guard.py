import re
from typing import Optional


_ORDINAL_ID = {
    "pertama": 1,
    "kedua": 2,
    "ketiga": 3,
    "keempat": 4,
    "kelima": 5,
    "keenam": 6,
    "ketujuh": 7,
    "kedelapan": 8,
    "kesembilan": 9,
    "kesepuluh": 10,
}

_PRESIDENTS = {
    1: "Sukarno",
    2: "Suharto",
    3: "B. J. Habibie",
    4: "Abdurrahman Wahid",
    5: "Megawati Sukarnoputri",
    6: "Susilo Bambang Yudhoyono",
    7: "Joko Widodo",
    8: "Prabowo Subianto",
}


def _extract_index(text: str) -> Optional[int]:
    t = text.lower()
    # Digit forms: "ke-3", "ke 3", "ketiga" handled below
    m = re.search(r"presiden\s+(ri|indonesia)\s+ke[-\s]?(\d+)", t)
    if m:
        try:
            return int(m.group(2))
        except Exception:
            return None
    # Word ordinals
    for word, idx in _ORDINAL_ID.items():
        if re.search(rf"presiden\s+(ri|indonesia).*\b{word}\b", t):
            return idx
    return None


def try_answer(user_text: str) -> Optional[str]:
    """
    Return a short, definitive answer if the user asks about the ordinal number
    of the President of Indonesia (RI). Otherwise, return None.
    """
    if not user_text:
        return None
    idx = _extract_index(user_text)
    if idx is None:
        return None
    name = _PRESIDENTS.get(idx)
    if not name:
        return None
    # Keep it short and to the point
    return f"Presiden RI ke-{idx} adalah {name}."
