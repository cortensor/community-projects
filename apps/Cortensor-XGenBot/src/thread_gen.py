import re
from typing import List, Tuple
from .cortensor_api import request_completion
from . import config


_IRRELEVANT_WORDS = {w.lower() for w in getattr(config, 'IRRELEVANT_WORDS', []) if w}


def _filter_irrelevant_words(text: str) -> str:
    if not text or not _IRRELEVANT_WORDS:
        return text
    tokens = re.split(r"(\s+)", text)
    cleaned: list[str] = []
    for token in tokens:
        if not token:
            continue
        if token.isspace():
            cleaned.append(token)
            continue
        normalized = re.sub(r"[^\w#]", "", token).lower().lstrip('#')
        if normalized and normalized in _IRRELEVANT_WORDS:
            continue
        cleaned.append(token)
    merged = "".join(cleaned)
    merged = re.sub(r"\s{2,}", " ", merged).strip()
    return merged


def _finalize_line(text: str) -> str:
    cleaned = _clean_line(text)
    cleaned = _sanitize_text(cleaned)
    cleaned = _filter_irrelevant_words(cleaned)
    return cleaned


def _length_target(length: str, n_posts: int) -> Tuple[int, str]:
    """Get character target for given length mode.
    
    All values are now configurable via .env:
    - LENGTH_SHORT_CHARS, LENGTH_MEDIUM_CHARS, LENGTH_LONG_CHARS
    - AUTO_LENGTH_THRESHOLDS, AUTO_LENGTH_FALLBACK_CHARS
    """
    length = (length or getattr(config, 'DEFAULT_LENGTH', 'medium')).lower()
    
    if length == 'short':
        return getattr(config, 'LENGTH_SHORT_CHARS', 140), 'short'
    if length == 'long':
        return getattr(config, 'LENGTH_LONG_CHARS', 240), 'long'
    if length == 'auto':
        # Auto scale: more posts -> slightly shorter lines (configurable thresholds)
        thresholds = getattr(config, 'AUTO_LENGTH_THRESHOLDS', [(4, 240), (8, 200), (12, 180)])
        for threshold, chars in thresholds:
            if n_posts <= threshold:
                return chars, 'auto'
        return getattr(config, 'AUTO_LENGTH_FALLBACK_CHARS', 160), 'auto'
    
    # Default: medium
    return getattr(config, 'LENGTH_MEDIUM_CHARS', 200), 'medium'


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
    min_posts = getattr(config, 'MIN_THREAD_POSTS', 2)
    max_posts = getattr(config, 'MAX_THREAD_POSTS', 25)
    default_n = getattr(config, 'DEFAULT_THREAD_N', 6)
    n = max(min_posts, min(max_posts, int(n_posts or default_n)))
    target, _ = _length_target(length, n)
    tone = tone or config.DEFAULT_TONE
    model_identity = getattr(config, 'MODEL_IDENTITY', 'XGenBot AI')
    role_pattern = (config.THREAD_ROLE_PATTERN or '')
    roles: list[str] = []
    if role_pattern:
        roles = [r.strip() for r in role_pattern.split(',') if r.strip()]
    role_section = ''
    if roles:
        role_map = []
        for i in range(n):
            role = roles[(offset + i) % len(roles)]
            role_map.append(f"- Post {i+1}: {role}")
        role_section = "Role focus per post:\n" + "\n".join(role_map)
    guidance_section = ''
    if instructions:
        guidance_section = "Additional guidance:\n" + instructions.strip()

    numbering_clause = "Never prepend ratios like 1/5 or (1)." if config.THREAD_ENUM_FORMAT == 'none' else "Use light, natural sequencing only when it reads organically; avoid '1/5' style counters."
    prompt_parts = [
        f"You are {model_identity} acting as a senior social strategist.",
        "Goal: craft a native X/Twitter thread that feels insightful and concise.",
        "",
        "Thread requirements:",
        f"- Posts: {n}.",
        f"- Tone: {tone}.",
        "- Language: English.",
        f"- Keep each post near {target} characters (hard max {config.TWEET_CHAR_LIMIT}).",
        "- Each line must read as its own post—no combined paragraphs.",
        f"- {numbering_clause}",
        "- Avoid UI/control words (More, Edit, Delete, Final, Submit, Revert, Cancel, Done).",
        "- Never include meta narration such as 'The final output is' or 'Output is ready'.",
        "- No hashtags except optionally inside the final post.",
        "",
        "Topic:",
        topic.strip(),
    ]
    if role_section:
        prompt_parts.extend(["", role_section])
    if guidance_section:
        prompt_parts.extend(["", guidance_section])
    prompt_parts.extend([
        "",
        f"Deliverable:\nReturn exactly {n} separate lines, each representing one post with no extra commentary.",
    ])
    prompt = "\n".join(part for part in prompt_parts if part is not None)
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
    lines = [_finalize_line(l) for l in lines]
    # Append hashtags to final line if provided and room
    if hashtags:
        last = lines[-1]
        suffix = ' ' + hashtags.strip()
        if len(last) + len(suffix) <= config.TWEET_CHAR_LIMIT:
            lines[-1] = _finalize_line((last + suffix).strip())
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
    model_identity = getattr(config, 'MODEL_IDENTITY', 'XGenBot AI')
    prompt_parts = [
        f"You are {model_identity} acting as a senior X/Twitter copywriter.",
        "Task: craft exactly one scroll-stopping tweet for the topic below.",
        "",
        "Tweet requirements:",
        f"- Tone: {tone}.",
        "- Language: English.",
        f"- Aim for ~{target} characters and never exceed {config.TWEET_CHAR_LIMIT} characters.",
        "- Deliver a single cohesive tweet—no quoted blocks or numbered lists.",
        "- Avoid filler, generic hype, or trailing hashtags unless provided separately.",
        "- Do not include UI/control words (More, Edit, Delete, Final, Submit, Revert, Cancel, Done).",
        "- Remove any meta narration such as 'The final output is' or 'Output is ready'.",
        "",
        "Topic:",
        topic.strip(),
        "",
        "Deliverable: Return only the tweet text with no explanations or markup.",
    ]
    prompt = "\n".join(prompt_parts)
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    out = _finalize_line(raw)
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
    out = _finalize_line(out)
    if hashtags:
        if len(out) + 1 + len(hashtags) <= config.TWEET_CHAR_LIMIT:
            out = _finalize_line((out + ' ' + hashtags).strip())
    return out


def generate_reply(context_text: str, tone: str | None, length: str, instructions: str) -> str:
    target, _ = _length_target(length, 1)
    tone = tone or config.DEFAULT_TONE
    model_identity = getattr(config, 'MODEL_IDENTITY', 'XGenBot AI')
    guidance_section = ''
    if instructions:
        guidance_section = "Additional guidance:\n" + instructions.strip()
    prompt_parts = [
        f"You are {model_identity} acting as a thoughtful X/Twitter responder.",
        "Task: write one native reply to the post below.",
        "",
        "Reply requirements:",
        f"- Tone: {tone}.",
        "- Language: English.",
        f"- Aim for ~{target} characters and never exceed {config.TWEET_CHAR_LIMIT} characters.",
        "- No numbering, no greetings, and no closing signatures.",
        "- Avoid UI/control words (More, Edit, Delete, Final, Submit, Revert, Cancel, Done).",
        "- Remove any meta narration or chain-of-thought markers.",
        "",
        "Context:",
        context_text.strip(),
    ]
    if guidance_section:
        prompt_parts.extend(["", guidance_section])
    prompt_parts.extend([
        "",
        "Deliverable: Return only the reply text with no explanations.",
    ])
    prompt = "\n".join(prompt_parts)
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    return _finalize_line(raw)
