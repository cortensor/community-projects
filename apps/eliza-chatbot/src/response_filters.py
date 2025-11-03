import re
from typing import Optional, List


def _is_greeting(text: str) -> bool:
    t = text.strip().lower()
    # Common greetings (EN + ID)
    greetings = [
        "hi", "hello", "hey", "morning", "good morning", "gm",
        "selamat pagi", "pagi", "siang", "selamat siang",
        "sore", "selamat sore", "malam", "selamat malam",
        "halo", "hai"
    ]
    return any(t == g or t.startswith(g + " ") for g in greetings)


def _short_greeting_reply(user_text: str) -> str:
    # Mirror user language (very simple heuristic)
    t = user_text.strip().lower()
    if any(w in t for w in ["selamat", "pagi", "siang", "sore", "malam", "halo", "hai"]):
        if "pagi" in t:
            return "Pagi."  # to the point
        if "siang" in t:
            return "Siang."
        if "sore" in t:
            return "Sore."
        if "malam" in t:
            return "Malam."
        if "halo" in t or "hai" in t:
            return "Halo."
        return "Halo."
    # Default EN
    if "morning" in t or t == "gm":
        return "Morning."
    return "Hi."


def _strip_transcript_blocks(text: str) -> str:
    # If the model returns a whole transcript with repeated "User:"/"Assistant:",
    # try to keep only the last Assistant answer.
    pattern = re.compile(r"(?:^|\n)Assistant:\s*(.*?)(?=\nUser:|\Z)", re.S)
    matches = list(pattern.finditer(text))
    if matches:
        return matches[-1].group(1).strip()
    # Remove leading generic preface lines like "I can help you..."
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if lines and re.search(r"i can help you|how can i help|what can i help", lines[0], re.I):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _strip_meta_scaffolding(text: str) -> str:
    # Remove analysis scaffolding like 'Step 1:', '### Step 2', 'The final answer is:'
    patterns = [
        r"^###\s*Step\s*\d+.*$",
        r"^Step\s*\d+\s*:\s*.*$",
        r"^The final answer is:.*$",
        r"^Output for the .* question:.*$",
    ]
    out_lines = []
    for ln in text.splitlines():
        skip = False
        for pat in patterns:
            if re.match(pat, ln.strip(), re.IGNORECASE):
                skip = True
                break
        if not skip:
            out_lines.append(ln)
    return "\n".join(out_lines)


def _user_wants_code(user_text: str) -> bool:
    # Heuristics for code intent: keywords, languages, function-like tokens, or explicit request
    code_terms = r"code|kode|example|contoh|snippet|sample|implement|implementasi|how\s+to|cara|buat|membuat"
    langs = r"python|py\b|solidity|javascript|typescript|java|c\+\+|c#|golang|go\b|rust|php|ruby|kotlin|swift"
    tech = r"smart\s*contract|api|regex|dict\(|list\(|map\(|filter\("
    if re.search(fr"\b({code_terms}|{langs}|{tech})\b", user_text, re.I):
        return True
    # Explicit inline code markers in the question
    if "`" in user_text or "```" in user_text:
        return True
    return False


def _strip_unasked_code_blocks(text: str, user_text: str) -> str:
    # Drop large code blocks unless the user likely wants code examples
    if _user_wants_code(user_text):
        return text
    # Remove fenced code blocks wholesale
    text = re.sub(r"```[\s\S]*?```", "", text).strip()
    return text


def _balance_code_fences(text: str) -> str:
    # Ensure triple backticks are balanced to avoid broken rendering
    openings = len(re.findall(r"```", text))
    # If odd number of fences, append a closing fence
    if openings % 2 == 1:
        text = text.rstrip() + "\n```"
    return text


def _enforce_brevity(text: str, max_sentences: int = 2, max_chars: int = 220) -> str:
    # Keep it to-the-point unless the user asked for more details.
    # Sentence split (simple heuristic)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    brief = " ".join(sentences[:max_sentences]).strip()
    if len(brief) > max_chars:
        brief = brief[:max_chars].rstrip() + "…"
    return brief


def _user_wants_detail(user_text: str) -> bool:
    # Heuristics: user asks for "explain", "why", "how", "detail", "jelaskan", "lebih detail"
    return bool(re.search(r"\b(why|how|explain|details?|jelaskan|mengapa|bagaimana|lebih detail)\b", user_text, re.I))


def _extract_requested_count(user_text: str) -> Optional[int]:
    """Extract a small integer N requested by the user (e.g., '3 headline', 'tiga berita').
    Caps N to 10 for safety.
    """
    t = (user_text or "").lower()
    # Direct digits near list intents
    m = re.search(r"\b(\d{1,2})\b\s*(headline|item|poin|berita|daftar|list)?", t)
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 10:
                return n
        except Exception:
            pass
    # Indonesian number words
    words = {
        "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
        "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10,
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    for w, v in words.items():
        if re.search(fr"\b{re.escape(w)}\b\s*(headline|item|poin|berita|daftar|list)?", t):
            return v
    return None


def _split_list_items(text: str) -> List[str]:
    """Split text into list items if it looks like a numbered/bulleted list.
    Supports patterns like:
      1. foo\n2) bar\n- baz\n• qux
    Returns items with their content (without the bullet/number).
    """
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    items: List[str] = []
    buf: List[str] = []
    pat_item = re.compile(r"^\s*(?:\d{1,2}[\.)]|[-•])\s+")
    for ln in lines:
        if pat_item.match(ln):
            # flush previous
            if buf:
                items.append(" ".join(buf).strip())
                buf = []
            # start new, remove marker
            content = pat_item.sub("", ln).strip()
            buf.append(content)
        else:
            # continuation of current item
            if buf:
                buf.append(ln.strip())
            else:
                # no marker yet; treat as a paragraph item if nothing collected
                buf.append(ln.strip())
    if buf:
        items.append(" ".join(buf).strip())
    return items


def _first_sentence(s: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", s.strip())
    return parts[0].strip()


def post_process_response(user_text: str, model_text: str, *, brief_default: bool = True) -> str:
    """
    Post-process model output to:
    - Remove multi-turn transcripts and boilerplate
    - Keep answers short and to the point by default
    - Avoid unsolicited code blocks unless requested

    Note: This does not guarantee factual correctness (no external verifier),
    but it reduces rambling and off-topic content.
    """
    user_text = (user_text or "").strip()
    text = (model_text or "").strip()

    if not text:
        return text

    # If multiple <final> blocks exist, select the one most relevant to the user_text
    def _tokenize(s: str) -> set[str]:
        s = s.lower()
        # Remove non-letters/numbers except spaces and backticks
        s = re.sub(r"[^a-z0-9_\-\s]", " ", s)
        toks = [t for t in s.split() if len(t) >= 3]
        stop = {
            # EN stopwords (small set)
            "the","and","for","are","you","your","with","that","this","have","has","from","into","about","into","what","which","when","where","why","how","like","more","most","some","such","only","also","just","can","could","should","would","will","want","need",
            # ID stopwords (small set)
            "yang","dan","untuk","dengan","pada","dari","itu","ini","apa","mengapa","bagaimana","lebih","akan","sudah","bisa","ingin","butuh","saya","kamu","anda","nya","ya","tidak","nggak","ga","gak","atau","karena","jadi"
        }
        return {t for t in toks if t not in stop}

    def _score_block(block: str, user_toks: set[str], wants_code: bool) -> tuple[int, int, int]:
        # Higher is better: overlap tokens; then prefer/no-prefer code depending on intent; then shorter length
        block_toks = _tokenize(block)
        overlap = len(block_toks & user_toks)
        has_code = 1 if '```' in block else 0
        code_pref = has_code if wants_code else (1 - has_code)  # prefer code if wants_code else prefer no-code
        length_penalty = -len(block)  # shorter is better
        return (overlap, code_pref, length_penalty)

    finals = re.findall(r"<final>([\s\S]*?)</final>", text, flags=re.IGNORECASE)
    if finals:
        # Prefer a single final block; if multiple, choose the one with most lines/items
        # to avoid picking truncated variants. Then normalize numbering on newlines.
        best_blk = max(finals, key=lambda b: len(b.strip().splitlines()))
        # Normalize to newline-numbered list if block contains inline ' 2. ' etc.
        inline_items = re.findall(r"\b(\d+)\.\s+", best_blk)
        if inline_items and "\n" not in best_blk:
            # Split on numbered markers and rebuild
            parts = re.split(r"\b\d+\.\s+", best_blk)
            rebuilt_items = [p.strip() for p in parts if p.strip()]
            best_blk = "\n".join(f"{i+1}. {rebuilt_items[i]}" for i in range(len(rebuilt_items)))
        text = best_blk.strip()

    # If greeting, keep it ultra-short
    if _is_greeting(user_text):
        return _short_greeting_reply(user_text)

    # Trim transcripts and boilerplate
    text = _strip_transcript_blocks(text)
    text = _strip_meta_scaffolding(text)

    # Remove generic CTA endings (EN/ID variants)
    text = re.sub(r"\s*(Would you like to know more|Do you want to know more|Would you like more details)[^\n]*\?\s*$", "", text, flags=re.I)
    text = re.sub(r"\s*(Apakah Anda ingin|Mau penjelasan lebih|Ingin tahu lebih lanjut)[^\n]*\?\s*$", "", text, flags=re.I)

    # Drop unasked code blocks
    wants_code = _user_wants_code(user_text)
    text = _strip_unasked_code_blocks(text, user_text)

    # Balance code fences if any remain
    if '```' in text:
        text = _balance_code_fences(text)

    # Enforce brevity unless user explicitly asked for details
    if brief_default and not _user_wants_detail(user_text):
        requested_n = _extract_requested_count(user_text) or 0
        if requested_n > 0:
            # Try to preserve an N-item list with 1 sentence per item.
            items = _split_list_items(text)
            if items:
                kept = []
                for it in items[:requested_n]:
                    kept.append(_first_sentence(it))
                # Rebuild as a newline-numbered list
                text = "\n".join(f"{i+1}. {kept[i]}" for i in range(len(kept)))
            else:
                # Fall back to global brevity if not a list
                text = _enforce_brevity(text)
        else:
            # If a list exists but user didn't specify N, keep small lists (2–5 items) intact (1 sentence each)
            items = _split_list_items(text)
            if items and 2 <= len(items) <= 5:
                kept = [_first_sentence(it) for it in items]
                text = "\n".join(f"{i+1}. {kept[i]}" for i in range(len(kept)))
            else:
                # If code is present or requested, do not trim code; optionally compress narration
                if '```' in text or wants_code:
                    parts = text.split('```')
                    preface = parts[0]
                    preface_brief = _enforce_brevity(preface)
                    rebuilt = preface_brief
                    if len(parts) >= 3:
                        code_lang = parts[1].split('\n', 1)[0]
                        code_body = parts[1][len(code_lang):]
                        code_block = f"```{code_lang}{code_body}```"
                        rebuilt = (preface_brief.strip() + "\n\n" + code_block).strip()
                    text = rebuilt
                else:
                    text = _enforce_brevity(text)

    # Final tidy
    return text.strip()
