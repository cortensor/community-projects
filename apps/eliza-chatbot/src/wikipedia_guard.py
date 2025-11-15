import logging
import requests
import re
from typing import Optional, List, Dict, Any, Tuple

from . import config

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(getattr(config, "USE_WIKIPEDIA_GUARD", True))


def _detect_lang(query: str) -> str:
    t = (query or "").lower()
    # Very light heuristic: if Indonesian stopwords present, use id
    if any(w in t for w in [
        "siapa", "apa", "kapan", "dimana", "bagaimana", "mengapa",
        "presiden", "perdana menteri", "pm", "raja", "ratu",
        "ri", "indonesia", "ke-", "sekarang", "saat ini", "kini",
    ]):
        return "id"
    return "en"


def _parse_office_query(text: str) -> Optional[Tuple[str, str, str]]:
    """Parse queries like 'Who is the president of X?' or 'Siapa perdana menteri Y saat ini?'

    Returns tuple: (prop, country_text, role_label)
      - prop: 'P35' (head of state) or 'P6' (head of government)
      - country_text: the country name mention (raw)
      - role_label: 'president' | 'prime_minister' | 'monarch'
    """
    t = (text or "").strip()
    tl = t.lower()

    # English patterns
    m = re.search(r"^who\s+is\s+(the\s+)?president\s+of\s+([^?]+)(\s+(now|currently|today))?\??$", tl)
    if m:
        return ("P35", m.group(2).strip(), "president")
    m = re.search(r"^who\s+is\s+(the\s+)?prime\s+minister\s+of\s+([^?]+)(\s+(now|currently|today))?\??$", tl)
    if m:
        return ("P6", m.group(2).strip(), "prime_minister")
    m = re.search(r"^who\s+is\s+(the\s+)?(king|queen|monarch)\s+of\s+([^?]+)\??$", tl)
    if m:
        return ("P35", m.group(3).strip(), "monarch")

    # Indonesian patterns (country may or may not have 'di' preposition)
    m = re.search(r"^siapa\s+presiden\s+(?:di\s+)?([^?]+?)(\s+(sekarang|saat\s+ini|kini))?\??$", tl)
    if m:
        return ("P35", m.group(1).strip(), "president")
    m = re.search(r"^siapa\s+perdana\s+menteri\s+(?:di\s+)?([^?]+?)(\s+(sekarang|saat\s+ini|kini))?\??$", tl)
    if m:
        return ("P6", m.group(1).strip(), "prime_minister")
    m = re.search(r"^(raja|ratu|monarki)\s+(?:di\s+)?([^?]+?)\s+siapa\??$", tl)
    if m:
        return ("P35", m.group(2).strip(), "monarch")

    # Ambiguous Indonesian: assume user's own country if just 'Siapa presiden saat ini?'
    # We'll let model handle if no explicit country; returning None here.
    return None


def _wikidata_office_holder(lang: str, country_qid: str, prop: str) -> Optional[str]:
    """Fetch current officeholder for a country via Wikidata.

    - prop: 'P35' head of state, 'P6' head of government
    """
    try:
        # Step 1: get claims for the given country
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "ids": country_qid,
            "props": "claims",
            "format": "json",
        }
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
        claims = data.get("entities", {}).get(country_qid, {}).get("claims", {})
        arr: List[Dict[str, Any]] = claims.get(prop, [])
        if not arr:
            return None

        def get_start_time(claim: Dict[str, Any]) -> Optional[str]:
            quals = claim.get("qualifiers", {}) or {}
            start = quals.get("P580", [{}])[0].get("datavalue", {}).get("value", {}).get("time")
            return start  # e.g., "+2024-10-20T00:00:00Z"

        # Prefer preferred-ranked claims; else use the one with latest start time
        preferred = [c for c in arr if c.get("rank") == "preferred"]
        candidates = preferred if preferred else arr
        # Sort by start time if available
        def sort_key(c):
            st = get_start_time(c) or ""
            return st
        candidates = sorted(candidates, key=sort_key)
        chosen = candidates[-1]
        person_id = chosen.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
        if not person_id:
            return None

        # Step 2: fetch label for the person
        params2 = {
            "action": "wbgetentities",
            "ids": person_id,
            "props": "labels",
            "format": "json",
        }
        r2 = requests.get(url, params=params2, timeout=8)
        if r2.status_code != 200:
            return None
        data2 = r2.json()
        labels = data2.get("entities", {}).get(person_id, {}).get("labels", {})
        label = (labels.get(lang, {}) or {}).get("value") or (labels.get("en", {}) or {}).get("value")
        if not label:
            return None
        return label
    except Exception as e:
        logger.debug("[WIKI] wikidata failed: %s", e)
        return None


def _wikidata_search_qid(lang: str, query: str) -> Optional[str]:
    """Fallback: search Wikidata for an item ID by label."""
    try:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "language": lang,
            "search": query,
            "type": "item",
            "format": "json",
            "limit": 1,
        }
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
        hits = data.get("search", [])
        if not hits:
            return None
        return hits[0].get("id")
    except Exception as e:
        logger.debug("[WIKI] wikidata search failed: %s", e)
        return None


def _summary_json(lang: str, title: str) -> Optional[Dict[str, Any]]:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
    try:
        r = requests.get(url, timeout=8, headers={"accept": "application/json"})
        if r.status_code != 200:
            logger.debug("[WIKI] summary HTTP %s", r.status_code)
            return None
        return r.json()
    except Exception as e:
        logger.debug("[WIKI] summary failed: %s", e)
        return None


def _country_qid_from_name(lang: str, name: str) -> Optional[str]:
    # Try Wikipedia: search → summary.wikibase_item; else Wikidata search
    title = _search(lang, name)
    if title:
        js = _summary_json(lang, title) or {}
        qid = js.get("wikibase_item")
        if qid:
            return qid
    return _wikidata_search_qid(lang, name)


def _search(lang: str, query: str) -> Optional[str]:
    # Use MediaWiki search API to get best title
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
        "format": "json",
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            logger.debug("[WIKI] search HTTP %s", r.status_code)
            return None
        data = r.json()
        hits = data.get("query", {}).get("search", [])
        if not hits:
            return None
        return hits[0].get("title")
    except Exception as e:
        logger.debug("[WIKI] search failed: %s", e)
        return None


def _summary(lang: str, title: str) -> Optional[str]:
    # Get a concise extract with the REST summary endpoint
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
    try:
        r = requests.get(url, timeout=8, headers={"accept": "application/json"})
        if r.status_code != 200:
            logger.debug("[WIKI] summary HTTP %s", r.status_code)
            return None
        data = r.json()
        text = data.get("extract") or data.get("description")
        if not text:
            return None
        # Keep to one short sentence
        text = str(text).strip()
        text = re.split(r"(?<=[.!?])\s+", text)[0]
        if len(text) > 200:
            text = text[:200].rstrip() + "…"
        return text
    except Exception as e:
        logger.debug("[WIKI] summary failed: %s", e)
        return None


def try_answer(user_text: str) -> Optional[str]:
    if not is_enabled() or not user_text:
        return None
    lang = _detect_lang(user_text)

    # Global handling: current office (president/prime minister/monarch) of any country
    parsed = _parse_office_query(user_text)
    if parsed:
        prop, country_text, role = parsed
        qid = _country_qid_from_name(lang, country_text)
        if qid:
            person = _wikidata_office_holder(lang, qid, prop)
            if person:
                if lang == "id":
                    if role == "prime_minister":
                        return f"Perdana Menteri {country_text.title()} saat ini adalah {person}."
                    if role == "monarch":
                        return f"Monarki {country_text.title()} saat ini adalah {person}."
                    return f"Presiden {country_text.title()} saat ini adalah {person}."
                else:
                    if role == "prime_minister":
                        return f"The current Prime Minister of {country_text.title()} is {person}."
                    if role == "monarch":
                        return f"The current monarch of {country_text.title()} is {person}."
                    return f"The current President of {country_text.title()} is {person}."

    # Generic search → summary fallback
    title = _search(lang, user_text)
    if not title:
        return None
    return _summary(lang, title)
