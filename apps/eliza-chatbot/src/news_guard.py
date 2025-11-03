import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from . import config

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(getattr(config, "USE_NEWS_GUARD", False) and getattr(config, "NEWSAPI_KEY", None))


CONTINENT_HINTS = {
    # continent: list of country codes or query hints
    "americas": ["us", "ca", "br", "mx"],
    "europe": ["gb", "de", "fr", "it", "es"],
    "asia": ["jp", "cn", "in", "id", "sg"],
    "africa": ["za", "ng", "eg", "ke"],
    "oceania": ["au", "nz"],
    "middle east": ["sa", "ae", "il", "tr"],
}


def _lang(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["sebutkan", "headline", "berita", "sumber", "benua", "ringkas", "waktu", "kejadian"]):
        return "id"
    return "en"


def _requested_count(text: str) -> int:
    import re
    m = re.search(r"\b(\d{1,2})\b", (text or "").lower())
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 10:
                return n
        except Exception:
            pass
    return 3


def _since_24h_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()


def _parse_timeframe(user_text: str) -> str:
    t = (user_text or "").lower()
    if any(w in t for w in ["≤24", "24 jam", "24 hours", "last 24 hours", "24h"]):
        return "24h"
    if any(w in t for w in ["minggu lalu", "last week", "previous week"]):
        return "last_week"
    return "24h"


def _week_range_utc_now() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    # Previous week Monday 00:00 to Sunday 23:59:59
    # Find current week Monday
    weekday = now.weekday()  # Monday=0
    this_monday = now - timedelta(days=weekday)
    prev_monday = this_monday - timedelta(days=7)
    prev_sunday = this_monday - timedelta(seconds=1)
    return prev_monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(), prev_sunday.isoformat()


def _news_search(query: str, *, lang: str = "en", country: Optional[str] = None, page_size: int = 5, timeframe: str = "24h") -> List[dict]:
    url = "https://newsapi.org/v2/everything"
    headers = {"X-Api-Key": config.NEWSAPI_KEY}
    if timeframe == "last_week":
        frm, to = _week_range_utc_now()
    else:
        frm, to = _since_24h_iso(), None
    params = {
        "q": query,
        "from": frm,
        **({"to": to} if to else {}),
        "language": lang,
        "sortBy": "publishedAt",
        "pageSize": page_size,
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=12)
        if r.status_code != 200:
            logger.debug("[NEWS] HTTP %s %s", r.status_code, r.text[:200])
            return []
        data = r.json()
        return data.get("articles", []) or []
    except Exception as e:
        logger.debug("[NEWS] request failed: %s", e)
        return []


def _pick_per_continent(n: int) -> List[Tuple[str, Optional[str]]]:
    # Return (continent_label, country_code_hint) pairs up to n distinct continents
    order = ["americas", "europe", "asia", "africa", "oceania", "middle east"]
    res: List[Tuple[str, Optional[str]]] = []
    for cont in order:
        if len(res) >= n:
            break
        codes = CONTINENT_HINTS.get(cont, [])
        code = codes[0] if codes else None
        res.append((cont, code))
    return res


def _fmt_item(lang: str, region_label: str, art: dict) -> Optional[str]:
    title = (art or {}).get("title") or ""
    src = ((art or {}).get("source") or {}).get("name") or ""
    published_at = (art or {}).get("publishedAt") or ""
    if not title:
        return None
    # Escape inline for MarkdownV2 inside emphasis spans (bold title)
    def _mdv2_inline_escape(s: str) -> str:
        # Escape characters that could break emphasis: *, _, `
        return (
            s.replace("\\", "\\\\")
             .replace("*", r"\*")
             .replace("_", r"\_")
             .replace("`", r"\`")
        )
    # Parse time
    dt = None
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except Exception:
        pass
    ts = dt.strftime("%d %b %Y %H:%M UTC") if dt else ""
    safe_title = _mdv2_inline_escape(title)
    if lang == "id":
        prefix = region_label.capitalize()
        return f"{prefix}: *{safe_title}*: — {ts} (Sumber: {src})".strip()
    else:
        prefix = region_label.capitalize()
        return f"{prefix}: *{safe_title}*: — {ts} (Source: {src})".strip()


def try_answer(user_text: str) -> Optional[str]:
    if not is_enabled() or not user_text:
        return None
    lang = _lang(user_text)
    n = _requested_count(user_text)
    timeframe = _parse_timeframe(user_text)

    # Build continent queries; use simple keywords ensuring variety
    regions = _pick_per_continent(max(n, 3))
    items: List[str] = []
    used_titles = set()

    for (label, _code) in regions:
        # Use the label as a query hint; NewsAPI doesn't filter by continent, so we bias via keywords
        q = {
            "americas": "(US OR Canada OR Mexico OR Brazil)",
            "europe": "(Europe OR Germany OR France OR UK OR Italy OR Spain)",
            "asia": "(Asia OR Japan OR China OR India OR Indonesia OR Singapore)",
            "africa": "(Africa OR Nigeria OR South Africa OR Kenya OR Egypt)",
            "oceania": "(Oceania OR Australia OR New Zealand)",
            "middle east": "(Middle East OR Saudi Arabia OR UAE OR Israel OR Turkey)",
        }.get(label, label)
        arts = _news_search(q, lang=("id" if lang == "id" else "en"), page_size=5, timeframe=timeframe)
        for art in arts:
            title = art.get("title") or ""
            if not title or title in used_titles:
                continue
            line = _fmt_item(lang, label, art)
            if line:
                items.append(line)
                used_titles.add(title)
                break  # one per region
        if len(items) >= n:
            break

    if len(items) >= 1:
        # Return as newline-separated numbered list
        return "\n".join(f"{i+1}. {items[i]}" for i in range(min(n, len(items))))
    return None
