import os
import json
import re
from typing import Dict, Set, Optional
from better_profanity import profanity
from .config import CHILD_FILTER_ENABLED, CHILD_FILTER_MODE

# Initialize base profanity list (English) and extend with Indonesian words.
profanity.load_censor_words()
INDO_PROFANITY = [
    "bodoh", "goblok", "tolol", "bangsat", "anjing", "kontol", "memek",
    "jancuk", "bajingan", "kampret", "sialan",
]
for w in INDO_PROFANITY:
    profanity.add_censor_words([w])

# Per-chat custom bad words and compiled regex caches
_CUSTOM_BAD_WORDS: Dict[int, Set[str]] = {}
_CUSTOM_BAD_WORDS_RE: Dict[int, Optional[re.Pattern]] = {}

# Persistence locations
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_CUSTOM_FILE = os.path.join(_DATA_DIR, "custom_words.json")

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"\b(\+?\d{1,3})?[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b")
ADDRESS_HINTS_RE = re.compile(r"\b(street|st\.|road|rd\.|avenue|ave\.|block|blok|rw|rt|postal|zip|kode pos)\b", re.I)

# Base unsafe terms (single words)
UNSAFE_WORDS = [
    "weapon", "gun", "knife", "kill", "suicide", "die", "blood", "bomb",
    "drugs", "alcohol", "cigarette", "vape", "gamble", "casino", "bet",
    "adult", "porn", "sex", "nude", "nsfw", "explicit", "violence", "gore",
    "hate", "racist", "bully", "abuse",
]

# Multi-word or hyphenated unsafe phrases
UNSAFE_PHRASES = [
    r"self[-\s]?harm",
]

# Extra strict blocklist for under-12 (English)
STRICT_KIDS_WORDS = [
    "dating", "boyfriend", "girlfriend", "flirt", "kiss", "hookup",
    "strip", "naked", "breast", "butt", "penis", "vagina", "condom",
    "beer", "vodka", "whiskey",
    "shoot", "stab", "murder", "explode",
]
STRICT_KIDS_PHRASES = [
    r"make\s+out",
]


def _compile_word_boundary(words: Set[str]) -> Optional[re.Pattern]:
    if not words:
        return None
    escaped = [re.escape(w) for w in sorted(words) if w]
    if not escaped:
        return None
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern, re.I)


UNSAFE_WORDS_RE = _compile_word_boundary(set(UNSAFE_WORDS)) if UNSAFE_WORDS else None
STRICT_KIDS_WORDS_RE = _compile_word_boundary(set(STRICT_KIDS_WORDS)) if STRICT_KIDS_WORDS else None
UNSAFE_PHRASES_RE = [re.compile(p, re.I) for p in UNSAFE_PHRASES]
STRICT_KIDS_PHRASES_RE = [re.compile(p, re.I) for p in STRICT_KIDS_PHRASES]


def _ensure_data_dir() -> None:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
    except Exception:
        pass


def load_state() -> None:
    """Load per-chat custom word sets from disk."""
    _ensure_data_dir()
    try:
        if os.path.exists(_CUSTOM_FILE):
            with open(_CUSTOM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            # Convert keys to int and values to sets
            _CUSTOM_BAD_WORDS.clear()
            _CUSTOM_BAD_WORDS_RE.clear()
            for k, words in data.items():
                try:
                    chat_id = int(k)
                except Exception:
                    continue
                word_set = {str(w) for w in (words or []) if str(w).strip()}
                _CUSTOM_BAD_WORDS[chat_id] = word_set
                _CUSTOM_BAD_WORDS_RE[chat_id] = _compile_word_boundary(word_set)
    except Exception:
        # Non-fatal
        pass


def save_state() -> None:
    """Persist per-chat custom words to disk."""
    _ensure_data_dir()
    try:
        serializable = {str(k): sorted(list(v)) for k, v in _CUSTOM_BAD_WORDS.items()}
        with open(_CUSTOM_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _custom_regex(chat_id: int) -> Optional[re.Pattern]:
    rx = _CUSTOM_BAD_WORDS_RE.get(chat_id)
    if rx is None:
        # Build and cache
        words = _CUSTOM_BAD_WORDS.get(chat_id, set())
        rx = _compile_word_boundary(words)
        _CUSTOM_BAD_WORDS_RE[chat_id] = rx
    return rx


def list_custom_words(chat_id: int) -> list[str]:
    return sorted(_CUSTOM_BAD_WORDS.get(chat_id, set()))


def add_bad_word(chat_id: int, word: str) -> bool:
    w = (word or "").strip()
    if not w:
        return False
    words = _CUSTOM_BAD_WORDS.setdefault(chat_id, set())
    if w in words:
        return False
    words.add(w)
    _CUSTOM_BAD_WORDS_RE[chat_id] = _compile_word_boundary(words)
    save_state()
    return True


def remove_bad_word(chat_id: int, word: str) -> bool:
    w = (word or "").strip()
    if not w:
        return False
    words = _CUSTOM_BAD_WORDS.get(chat_id, set())
    if w not in words:
        return False
    words.discard(w)
    _CUSTOM_BAD_WORDS_RE[chat_id] = _compile_word_boundary(words)
    save_state()
    return True


def custom_count(chat_id: int) -> int:
    return len(_CUSTOM_BAD_WORDS.get(chat_id, set()))


def default_filter_summary(chat_id: Optional[int] = None) -> dict:
    """Return counts-only summary of default filtering categories (plus custom for chat)."""
    try:
        base_size = len(getattr(profanity, "CENSOR_WORDSET", set()))
    except Exception:
        base_size = 0
    return {
        "profanity_lexicon_total": base_size,
        "indo_profanity": len(INDO_PROFANITY),
        "unsafe_words": len(UNSAFE_WORDS),
        "unsafe_phrases": len(UNSAFE_PHRASES),
        "strict_kids_words": len(STRICT_KIDS_WORDS),
        "strict_kids_phrases": len(STRICT_KIDS_PHRASES),
        "custom_words": custom_count(chat_id) if chat_id is not None else 0,
    }


def _matches_custom(chat_id: int, text: str) -> bool:
    rx = _custom_regex(chat_id)
    return bool(rx and rx.search(text))


def is_input_unsafe(chat_id: int, text: str) -> bool:
    if not text:
        return False
    if profanity.contains_profanity(text):
        return True
    if _matches_custom(chat_id, text):
        return True
    if EMAIL_RE.search(text) or PHONE_RE.search(text) or ADDRESS_HINTS_RE.search(text):
        return True
    # Unsafe single words
    if UNSAFE_WORDS_RE and UNSAFE_WORDS_RE.search(text):
        return True
    # Unsafe phrases
    for rx in UNSAFE_PHRASES_RE:
        if rx.search(text):
            return True
    if CHILD_FILTER_ENABLED and CHILD_FILTER_MODE == "strict":
        if STRICT_KIDS_WORDS_RE and STRICT_KIDS_WORDS_RE.search(text):
            return True
        for rx in STRICT_KIDS_PHRASES_RE:
            if rx.search(text):
                return True
    return False


def is_output_safe(chat_id: int, text: str) -> bool:
    if not text:
        return True
    if profanity.contains_profanity(text):
        return False
    if _matches_custom(chat_id, text):
        return False
    if UNSAFE_WORDS_RE and UNSAFE_WORDS_RE.search(text):
        return False
    for rx in UNSAFE_PHRASES_RE:
        if rx.search(text):
            return False
    if CHILD_FILTER_ENABLED and CHILD_FILTER_MODE == "strict":
        if STRICT_KIDS_WORDS_RE and STRICT_KIDS_WORDS_RE.search(text):
            return False
        for rx in STRICT_KIDS_PHRASES_RE:
            if rx.search(text):
                return False
    return True


def sanitize_output(text: str) -> str:
    if not text:
        return text
    text = EMAIL_RE.sub("[hidden-email]", text)
    text = PHONE_RE.sub("[hidden-phone]", text)
    return text


def safe_fallback_response() -> str:
    return "Let’s talk about safe and fun topics! How about animals, space, or a riddle?"
