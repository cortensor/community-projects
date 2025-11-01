import re
from typing import List, Tuple
from .cortensor_api import request_completion
from . import config


def _length_target(length: str, n_posts: int) -> Tuple[int, str]:
    length = (length or 'medium').lower()
    if length == 'short':
        return 140, 'short'
    if length == 'long':
        return 240, 'long'
    if length == 'auto':
        # Auto scale: more posts -> slightly shorter lines
        if n_posts <= 4:
            return 240, 'auto'
        if n_posts <= 8:
            return 200, 'auto'
        if n_posts <= 12:
            return 180, 'auto'
        return 160, 'auto'
    return 200, 'medium'


def _clean_line(s: str) -> str:
    # Strip numbering like "1)" or "1." at start
    s = s.strip()
    s = re.sub(r"^\s*\d+\s*[\.)-]\s*", "", s)
    s = s.replace('\u200b', '').strip()
    from . import config
    return s[: config.TWEET_CHAR_LIMIT]


def _sanitize_text(s: str) -> str:
    """Post-process raw model output to remove LLM meta prefixes, repetition, and quote clutter.

    Steps:
    - Drop leading 'The final answer is:' (case-insensitive) patterns.
    - Remove duplicated consecutive identical sentences.
    - Collapse excessive quotes / whitespace.
    - Ensure we stay within configured char limit.
    """
    if not s:
        return s
    # Remove chain-of-thought residue phrases & meta output markers
    s = re.sub(r"(?is)\bthe\s+final\s+answer\s+is\s*[:\-]*\s*['\"“”‘’]?", "", s)
    s = re.sub(r"(?is)\bthe\s+final\s+output\s+is\s*[:\-]*", "", s)
    s = re.sub(r"(?is)\bthe\s+output\s+is\s+ready\b.*", "", s)
    s = re.sub(r"(?is)\bfinal\s+output\s*:?", "", s)
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # Remove UI/control artifact sequences (e.g., '- More - (if applicable) - Edit - Delete ...')
    s = re.sub(r"(?is)(?:\s*[-–—]\s*(?:more|less|edit|delete|note|cancel|final|submit|revert|done|yes|no)\s*(?:[-–—]\s*\(if applicable\))?)+", " ", s)
    # Remove leftover '(if applicable)' markers
    s = re.sub(r"(?is)\(if\s+applicable\)", "", s)
    # Collapse excessive quotes blocks
    s = re.sub(r"([\"'“”‘’])\1+", r"\1", s)
    # Split into sentence-like chunks and deduplicate while preserving order
    parts = re.split(r"(?<=[.!?])\s+", s)
    seen = set()
    ordered = []
    for p in parts:
        kp = p.strip()
        if not kp:
            continue
        # compare lowercase to catch case variants
        lk = kp.lower()
        if lk in seen:
            continue
        seen.add(lk)
        ordered.append(kp)
    s = " ".join(ordered).strip()
    # Strip wrapping stray quotes
    s = s.strip("'\"“”‘’")
    # Final whitespace collapse
    s = re.sub(r"\s+", " ", s).strip()
    # Enforce char limit again
    s = s[: config.TWEET_CHAR_LIMIT]
    return s

def _strip_think(text: str) -> str:
    """Remove any chain-of-thought markers like <think>...</think> and anything before a closing </think>.

    Rules:
    - Remove paired <think> ... </think> blocks.
    - If a stray </think> exists (even without <think>), drop everything before the last </think>.
    - If a stray <think> remains without closing, drop everything from <think> onward.
    """
    if not text:
        return ''
    # Normalize for tag search
    low = text.lower()
    # Remove paired blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    # After removal, handle stray closing tag
    low2 = text.lower()
    last_close = low2.rfind("</think>")
    if last_close != -1:
        text = text[last_close + len("</think>"):]
    # Handle stray opening tag
    low3 = text.lower()
    first_open = low3.find("<think>")
    if first_open != -1:
        text = text[:first_open]
    return text.strip()


def _extract_text(out) -> str:
    if isinstance(out, dict) and out.get('choices'):
        choice = out['choices'][0]
        text = choice.get('text') or choice.get('message', {}).get('content') or ''
        return text or ''
    return ''


def generate_thread(topic: str, n_posts: int, tone: str | None, hashtags: str, instructions: str, length: str, offset: int = 0) -> List[str]:
    n = max(2, min(25, int(n_posts or 6)))
    target, _ = _length_target(length, n)
    tone = tone or config.DEFAULT_TONE
    extra = (f"\nGuidance: {instructions.strip()}" if instructions else '')
    role_pattern = (config.THREAD_ROLE_PATTERN or '')
    roles: list[str] = []
    if role_pattern:
        roles = [r.strip() for r in role_pattern.split(',') if r.strip()]
    role_lines = ''
    if roles:
        role_map = []
        for i in range(n):
            role = roles[(offset + i) % len(roles)]
            role_map.append(f"Post {i+1}: {role}")
        role_lines = "Roles:\n" + "\n".join(role_map) + "\n"

    numbering_clause = "No explicit numbering like 1/5." if config.THREAD_ENUM_FORMAT == 'none' else "Number each line implicitly only if needed for clarity."
    prompt = (
        "Create a social thread for X/Twitter.\n"
        "- Language: English.\n"
        "- Number of posts: {n}.\n"
        "- Tone: {tone}.\n"
        f"- {numbering_clause}\n"
        "- Each line is a separate post.\n"
        f"- Keep each line around {{target}} characters, max {config.TWEET_CHAR_LIMIT}.\n"
        "- No hashtags except possibly at the end of the last line.\n"
        "- Do NOT include UI words like More, Less, Edit, Delete, Note, Cancel, Final, Submit, Revert, Done, Yes, No.\n"
        "- Do NOT include phrases like 'The final output is', 'Output is ready', or any meta commentary.\n"
        + (role_lines if role_lines else "")
        + "Topic: {topic}{extra}\n"
        + "Return exactly {n} lines."
    ).format(n=n, tone=tone, target=target, topic=topic.strip(), extra=extra)
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    # Split raw output into non-empty lines
    candidate_lines = [l for l in re.split(r"\r?\n", raw) if l.strip()]
    # Heuristic: remove standalone counter-only lines (just 1/5) but keep content lines even if they start with '1/5 '
    lines: list[str] = []
    for l in candidate_lines:
        if re.match(r"^\s*\d+\s*/\s*\d+\s*$", l):
            continue
        lines.append(l)
    # Fix count if model returns more/less
    if len(lines) < n:
        lines += [''] * (n - len(lines))
    lines = lines[:n]
    lines = [_sanitize_text(_clean_line(l)) for l in lines]
    # Append hashtags to final line if provided and room
    if hashtags:
        last = lines[-1]
        suffix = ' ' + hashtags.strip()
        if len(last) + len(suffix) <= config.TWEET_CHAR_LIMIT:
            lines[-1] = _sanitize_text((last + suffix).strip())
    return lines


def format_thread_preview(posts: List[str]) -> List[str]:
    """Format thread lines with optional enumeration or splitting.

    Returns a list of message chunks (one or more) respecting THREAD_SPLIT_SEND.
    If THREAD_ENUM_FORMAT == 'ofx', we prepend '<i/N>' to each line (not counting toward trimming logic here).
    """
    enum_fmt = config.THREAD_ENUM_FORMAT
    out_lines: List[str] = []
    total = len(posts)
    for idx, p in enumerate(posts, start=1):
        base = p
        prefix = ""
        if enum_fmt == 'ofx':
            prefix = f"<{idx}/{total}> "
        elif enum_fmt == 'fraction':
            prefix = f"{idx}/{total} "
        if prefix:
            limit = getattr(config, 'TWEET_CHAR_LIMIT', 280)
            # Ensure we don't exceed limit due to prefix
            trimmed_body = base[: max(0, limit - len(prefix))]
            base = prefix + trimmed_body
        out_lines.append(base)
    if not config.THREAD_SPLIT_SEND:
        # Single message path: join with double newlines
        return ["\n\n".join(out_lines)]
    # Split send path: each line is its own message
    return out_lines


def generate_tweet(topic: str, tone: str | None, length: str, hashtags: str) -> str:
    target, _ = _length_target(length, 1)
    tone = tone or config.DEFAULT_TONE
    prompt = (
        "Create one high-quality X/Twitter post (single tweet).\n"
        "- Language: English.\n"
        "- Tone: {tone}.\n"
        f"- Keep around {{target}} characters (hard max {config.TWEET_CHAR_LIMIT}).\n"
        "- Output EXACTLY one tweet.\n"
        "- Do NOT wrap the tweet in quotes.\n"
        "- Do NOT output multiple sentences separated by standalone quotes.\n"
        "- Avoid generic hype or filler.\n"
        "- Do NOT include UI/control words (More, Edit, Delete, Final, Submit, Revert, Cancel, Done).\n"
        "- No meta phrases like 'The final output is' or 'Output is ready'.\n"
        "Topic: {topic}\n"
        "Return only the tweet text with no explanations."
    ).format(tone=tone, target=target, topic=topic.strip())
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    out = _sanitize_text(_clean_line(raw))
    # If model still dumps multiple quoted sentences, keep first 2 concise sentences.
    sentences = re.split(r"(?<=[.!?])\s+", out)
    if len(sentences) > 2:
        combined = sentences[0].strip()
        # include second only if short enough
        if len(combined) < config.TWEET_CHAR_LIMIT // 2:
            second = sentences[1].strip()
            if second and len(combined) + 1 + len(second) <= config.TWEET_CHAR_LIMIT:
                combined = f"{combined} {second}"
        out = combined
    if hashtags:
        if len(out) + 1 + len(hashtags) <= config.TWEET_CHAR_LIMIT:
            out = _sanitize_text((out + ' ' + hashtags).strip())
    return out


def generate_reply(context_text: str, tone: str | None, length: str, instructions: str) -> str:
    target, _ = _length_target(length, 1)
    tone = tone or config.DEFAULT_TONE
    extra = (f"\nGuidance: {instructions.strip()}" if instructions else '')
    prompt = (
        "Write a reply to the following X/Twitter post.\n"
        "- Language: English.\n"
        "- Tone: {tone}.\n"
        f"- Keep around {{target}} characters, max {config.TWEET_CHAR_LIMIT}.\n"
        "- No numbering.\n"
        "- Avoid UI/control words (More, Edit, Delete, Final, Submit, Revert, Cancel, Done).\n"
        "- No meta phrases like 'The final output is' or 'Output is ready'.\n"
        "Context:\n{ctx}{extra}\n"
        "Return only the reply text."
    ).format(tone=tone, target=target, ctx=context_text.strip(), extra=extra)
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    return _sanitize_text(_clean_line(raw))
