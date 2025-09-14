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
    return s[:280]

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


def generate_thread(topic: str, n_posts: int, tone: str | None, hashtags: str, instructions: str, length: str) -> List[str]:
    n = max(2, min(25, int(n_posts or 6)))
    target, _ = _length_target(length, n)
    tone = tone or config.DEFAULT_TONE
    extra = (f"\nGuidance: {instructions.strip()}" if instructions else '')
    prompt = (
        "Create a social thread for X/Twitter.\n"
        "- Language: English.\n"
        "- Number of posts: {n}.\n"
        "- Tone: {tone}.\n"
        "- Each line is a separate post, no numbering or bullets.\n"
        "- Keep each line around {target} characters, max 280.\n"
        "- No hashtags except possibly at the end of the last line.\n"
        "Topic: {topic}{extra}\n"
        "Return exactly {n} lines."
    ).format(n=n, tone=tone, target=target, topic=topic.strip(), extra=extra)
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    lines = [l for l in re.split(r"\r?\n", raw) if l.strip()]
    # Fix count if model returns more/less
    if len(lines) < n:
        lines += [''] * (n - len(lines))
    lines = lines[:n]
    lines = [_clean_line(l) for l in lines]
    # Append hashtags to final line if provided and room
    if hashtags:
        last = lines[-1]
        suffix = ' ' + hashtags.strip()
        if len(last) + len(suffix) <= 280:
            lines[-1] = (last + suffix).strip()
    return lines


def generate_tweet(topic: str, tone: str | None, length: str, hashtags: str) -> str:
    target, _ = _length_target(length, 1)
    tone = tone or config.DEFAULT_TONE
    prompt = (
        "Create one social post for X/Twitter.\n"
        "- Language: English.\n"
        "- Tone: {tone}.\n"
        "- Keep around {target} characters, max 280.\n"
        "- No numbering.\n"
        "Topic: {topic}\n"
        "Return only the post text."
    ).format(tone=tone, target=target, topic=topic.strip())
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    out = _clean_line(raw)
    if hashtags:
        if len(out) + 1 + len(hashtags) <= 280:
            out = (out + ' ' + hashtags).strip()
    return out


def generate_reply(context_text: str, tone: str | None, length: str, instructions: str) -> str:
    target, _ = _length_target(length, 1)
    tone = tone or config.DEFAULT_TONE
    extra = (f"\nGuidance: {instructions.strip()}" if instructions else '')
    prompt = (
        "Write a reply to the following X/Twitter post.\n"
        "- Language: English.\n"
        "- Tone: {tone}.\n"
        "- Keep around {target} characters, max 280.\n"
        "- No numbering.\n"
        "Context:\n{ctx}{extra}\n"
        "Return only the reply text."
    ).format(tone=tone, target=target, ctx=context_text.strip(), extra=extra)
    raw = _extract_text(request_completion(prompt, config.MODEL_PROVIDER, config.MODEL_NAME))
    raw = _strip_think(raw)
    return _clean_line(raw)
