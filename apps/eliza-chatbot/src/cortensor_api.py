# src/cortensor_api.py
import os
import re
import time
import random
import requests
import logging
from . import config
from .response_filters import post_process_response
from .wikipedia_guard import try_answer as wiki_try_answer
from .news_guard import try_answer as news_try_answer
from .local_guard import try_answer as local_try_answer

logger = logging.getLogger(__name__)

# --- Runtime tunables (with env fallbacks) ---
_MAX_RETRIES = int(os.getenv("CORTENSOR_MAX_RETRIES", "2"))  # Total attempts = 1 + _MAX_RETRIES
_RETRY_BACKOFF_BASE = float(os.getenv("CORTENSOR_RETRY_BACKOFF_BASE", "1.6"))  # exponential base
_RETRY_JITTER = float(os.getenv("CORTENSOR_RETRY_JITTER", "0.25"))  # fraction of backoff added/subtracted
_REQUEST_TIMEOUT = float(os.getenv("CORTENSOR_REQUEST_TIMEOUT", "180"))  # per-attempt timeout (seconds) now 3 minutes default
_MAX_TOKENS = int(os.getenv("CORTENSOR_MAX_TOKENS", "2400"))  # max tokens for completion output (default 2400)


class CortensorAPIError(Exception):
    """Base exception for Cortensor API errors."""


class CortensorNetworkError(CortensorAPIError):
    """Raised when the Cortensor API is unreachable after retries."""


class CortensorResponseError(CortensorAPIError):
    """Raised for non-success HTTP responses after retries are exhausted."""


def _extract_token_usage(data: dict) -> dict | None:
    """Best-effort extraction of token usage from various possible response shapes.

    Returns a dict with keys: prompt, completion, total (when available), else None.
    """
    try:
        # Common OpenAI-like shape
        if isinstance(data.get('usage'), dict):
            u = data['usage']
            return {
                'prompt': u.get('prompt_tokens'),
                'completion': u.get('completion_tokens'),
                'total': u.get('total_tokens'),
            }
        # Some APIs nest in meta or result
        meta = data.get('meta') or data.get('metadata')
        if isinstance(meta, dict):
            u = meta.get('usage') or meta.get('token_usage')
            if isinstance(u, dict):
                return {
                    'prompt': u.get('prompt') or u.get('prompt_tokens'),
                    'completion': u.get('completion') or u.get('completion_tokens'),
                    'total': u.get('total') or u.get('total_tokens'),
                }
        result = data.get('result') or data.get('data')
        if isinstance(result, dict) and isinstance(result.get('usage'), dict):
            u = result['usage']
            return {
                'prompt': u.get('prompt') or u.get('prompt_tokens'),
                'completion': u.get('completion') or u.get('completion_tokens'),
                'total': u.get('total') or u.get('total_tokens'),
            }
    except Exception:
        logger.debug("Token usage extraction failed", exc_info=True)
    return None

ELIZA_PERSONA = f"""
You are Eliza, a concise, friendly AI assistant for Telegram.

Guidelines:
1. Never reveal or include internal chain-of-thought, analysis notes, or any <think> / </think> tags in the final answer.
2. Default language is {config.DEFAULT_LANGUAGE}. If the user explicitly writes in another language, respond in that language.
    - Keep all code blocks, identifiers, API names, technical terms, and terminal outputs in English.
3. First turn only: greet once and offer help. Later turns: do not repeat greetings unless explicitly asked.
4. Use Telegram MarkdownV2 safely:
    - Use *bold* sparingly for emphasis.
    - Use bullet lists with "- " prefix.
    - Escape special characters as required by MarkdownV2.
5. For code examples:
    - Use fenced code blocks with a language tag, e.g. ```python.
    - Provide minimal, correct, directly runnable examples.
    - Do not mix multiple languages in a single code fence.
6. Do not fabricate environment setup or capabilities; be clear about limitations when relevant.
7. Avoid repeating the same sentence at both the start and the end.
8. If the user asks for differences/comparisons, produce a clean, structured list.

System rules:
{config.SYSTEM_PROMPT}
"""


def _default_client_reference() -> str:
    """Return a safe fallback client reference when none is provided."""
    template = getattr(config, "CORTENSOR_CLIENT_REFERENCE_TEMPLATE", "chat-eliza-user")
    if "(ID)" in template:
        return template.replace("(ID)", "anon")
    if "{id}" in template:
        try:
            return template.format(id="anon")
        except Exception:
            pass
    return template

def sanitize_for_telegram(text: str) -> str:
    """Enhanced sanitizer for Telegram MarkdownV2.
    Escapes special characters ONLY outside fenced code blocks.

    NOTE: Fixed logic bug where a for..else appended the *last* code block twice.
    """
    # Strategy:
    # 1) Split by fenced code blocks ```...``` and keep them intact.
    # 2) For non-code parts, further split by inline code `...` and keep them intact.
    # 3) In remaining text, preserve simple *bold* markers while escaping other specials.
    # 4) Avoid escaping '.' to keep ordered lists clean.

    def escape_outside_bold(s: str) -> str:
        # Protect simple *bold* spans first
        BOPEN = "\uE000"
        BCLOSE = "\uE001"
        def _protect_bold(m):
            inner = m.group(1)
            return f"{BOPEN}{inner}{BCLOSE}"
        protected = re.sub(r"\*([^*\n]+)\*", _protect_bold, s)
        # Escape Telegram MarkdownV2 specials (conservative set), excluding '.' and '*'
        specials = r"_[]()~`>#+-=|{}!\\"
        for ch in specials:
            protected = protected.replace(ch, f"\\{ch}")
        # Restore bold markers
        protected = protected.replace(BOPEN, "*").replace(BCLOSE, "*")
        return protected

    def escape_segment(seg: str) -> str:
        # Split around inline code `...` and escape only outside
        parts2 = re.split(r"(`[^`]*`)", seg)
        out2 = []
        for j, p2 in enumerate(parts2):
            if j % 2 == 0:
                out2.append(escape_outside_bold(p2))
            else:
                out2.append(p2)  # keep inline code intact
        return "".join(out2)

    parts = re.split(r"(```.*?```)", text, flags=re.DOTALL)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(escape_segment(part))
        else:
            out.append(part)  # keep fenced code intact
    return "".join(out)

def sanitize_for_html(text: str) -> str:
    """Convert a subset of Markdown to Telegram-safe HTML and escape HTML where needed.

    Handles:
    - Fenced code blocks ```lang\n...``` or ```...``` -> <pre><code>...</code></pre>
    - Inline code `...` -> <code>...</code>
    - Bold **...** and *...* -> <b>...</b>
    - Links [text](url) -> <a href="url">text</a>
    - Escapes HTML in all other text safely.
    """
    def html_escape(s: str) -> str:
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;"))

    # Split by fenced code blocks first; keep captured content separate
    parts = re.split(r"```([\s\S]*?)```", text)
    html_out = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            # This is inside a code fence; remove optional language tag on first line
            content = part
            if "\n" in content:
                first, rest = content.split("\n", 1)
                lang = first.strip()
                if lang and " " not in lang and len(lang) <= 32:
                    code = rest
                else:
                    code = content
            else:
                code = content
            html_out.append(f"<pre><code>{html_escape(code)}</code></pre>")
            continue

        # Non-code segment: convert markdown-ish to HTML using placeholders
        segment = part
        repls: list[tuple[str, str]] = []

        # Replace links with placeholders
        def _link_sub(m):
            txt = html_escape(m.group(1))
            href = html_escape(m.group(2))
            token = f"\uE100{len(repls)}\uE101"
            repls.append((token, f"<a href=\"{href}\">{txt}</a>"))
            return token
        segment = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link_sub, segment)

        # Replace inline code with placeholders (escape content now)
        def _icode_sub(m):
            code_txt = html_escape(m.group(1))
            token = f"\uE102{len(repls)}\uE103"
            repls.append((token, f"<code>{code_txt}</code>"))
            return token
        segment = re.sub(r"`([^`\n]+)`", _icode_sub, segment)

        # Replace bold (**...**) first then (*...*) with placeholders; escape inner
        def _bold2_sub(m):
            inner = html_escape(m.group(1))
            token = f"\uE104{len(repls)}\uE105"
            repls.append((token, f"<b>{inner}</b>"))
            return token
        segment = re.sub(r"\*\*([^*]+)\*\*", _bold2_sub, segment)

        def _bold1_sub(m):
            inner = html_escape(m.group(1))
            token = f"\uE106{len(repls)}\uE107"
            repls.append((token, f"<b>{inner}</b>"))
            return token
        segment = re.sub(r"\*([^*]+)\*", _bold1_sub, segment)

        # Escape remaining text
        segment = html_escape(segment)
        # Restore placeholders
        for tok, html_val in repls:
            segment = segment.replace(tok, html_val)

        html_out.append(segment)

    return "".join(html_out)


def strip_think_blocks(text: str) -> str:
    """Remove internal reasoning blocks <think>...</think> or orphan closing tags.

    Rules:
    - Remove every complete <think> ... </think> segment (case-insensitive).
    - If there's an orphan </think> without an opening <think>, keep everything BEFORE it and drop the tag + trailing content.
    - Case-insensitive handling.
    """
    lowered = text.lower()
    if '<think>' in lowered and '</think>' in lowered:
        import re as _re
        new_text = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
        if new_text != text:
            logger.debug("<think> block(s) stripped.")
        text = new_text
    # Orphan '</think>' without '<think>' -> treat everything after as noisy / duplicated tail.
    # Keep content before the orphan closing tag.
    if '<think>' not in lowered and '</think>' in lowered:
        closing_idx = lowered.rfind('</think>')
        kept = text[:closing_idx]
        if kept != text:
            logger.debug("Orphan </think> encountered: trimming tail after closing tag.")
            text = kept
    return text.strip()


def remove_special_markers(text: str) -> str:
    """Remove known special/end markers occasionally emitted by some models."""
    patterns = [
        r"<\|endoftext\|>",
        r"<\|end_of_sentence\|>",
        r"<\|eot_id\|>",
        r"<\|begin_of_text\|>",
        r"<\|start_header_id\|>",
        r"<\|end_header_id\|>",
        r"<\|.*?_stop\|>",
        r"<\|.*?_start\|>",
        r"<｜end▁of▁sentence｜>",
    ]
    import re as _re
    for pat in patterns:
        text = _re.sub(pat, "", text)
    return text.strip()


def extract_last_assistant_segment(text: str) -> str | None:
    """Extract the last 'Assistant:' segment if present, up to the next role marker or end.

    Returns the extracted content or None if no 'Assistant:' tag is found.
    """
    import re as _re
    pattern = _re.compile(r"(?im)^assistant:\s*(.*)$", _re.DOTALL)
    # We need to segment by role markers explicitly
    # Find all role markers and boundaries
    markers = list(_re.finditer(r"(?im)^(user|human|assistant|system):", text))
    if not markers:
        return None
    last_assistant_idx = None
    for i, m in enumerate(markers):
        if m.group(1).lower() == "assistant":
            last_assistant_idx = i
    if last_assistant_idx is None:
        return None
    start = markers[last_assistant_idx].end()
    # End at next marker or end of text
    end = len(text)
    if last_assistant_idx + 1 < len(markers):
        end = markers[last_assistant_idx + 1].start()
    segment = text[start:end].strip()
    return segment if segment else None


def remove_meta_evaluation_lines(text: str) -> str:
    """Remove typical meta-evaluation lines (judge/compliance chatter) that shouldn't reach users."""
    meta_patterns = [
        r"assistant's response is compliant",
        r"adheres to the strict output rules",
        r"strict output rules",
        r"in your response, do not",
        r"the task is to determine whether",
        r"therefore, the answer is",
        r"thus, the response",
        r"this complies with",
        r"compliant with the rules",
    ]
    import re as _re
    lines = text.splitlines()
    filtered = []
    for ln in lines:
        if any(_re.search(pat, ln, flags=_re.IGNORECASE) for pat in meta_patterns):
            continue
        filtered.append(ln)
    return "\n".join(filtered).strip()


_GREETING_PATTERNS = [
    r"^hello[!.]*$",
    r"^hi[!.]*$",
    r"^hey[!.]*$",
    r"^good\s+morning[!.]*$",
    r"^good\s+afternoon[!.]*$",
    r"^good\s+evening[!.]*$",
        r"^how can i assist (you )?today[?!.]*$",
        r"^how can i help (you )?today[?!.]*$",
]

# Add a few common Indonesian greetings to improve cross-language handling
_GREETING_PATTERNS.extend([
    r"^halo[!.]*$",
    r"^hai[!.]*$",
    r"^selamat\s+pagi[!.]*$",
    r"^selamat\s+siang[!.]*$",
    r"^selamat\s+sore[!.]*$",
    r"^selamat\s+malam[!.]*$",
])

def remove_redundant_greetings(text: str, is_first_turn: bool) -> str:
    """Remove redundant greetings.

    Behaviour:
    - Non-first turn: strip all standalone greeting lines.
    - First turn: keep only the first greeting if multiple appear.
    - If the exact same greeting appears at both start and end, drop the trailing duplicate.
    """
    lines = [l.strip() for l in text.splitlines()]
    if not lines:
        return text
    import re as _re

    def is_greeting(line: str) -> bool:
        lower = line.lower()
        for pat in _GREETING_PATTERNS:
            if _re.fullmatch(pat, lower):
                return True
        return False

    removed = 0
    if is_first_turn:
        # Keep first greeting, remove subsequent identical plain greetings at top cluster.
        seen_greeting = False
        new_lines = []
        for ln in lines:
            if is_greeting(ln):
                if not seen_greeting:
                    new_lines.append(ln)
                    seen_greeting = True
                else:
                    removed += 1
            else:
                new_lines.append(ln)
        lines = new_lines
    else:
        # Remove all pure greeting lines.
        new_lines = []
        for ln in lines:
            if is_greeting(ln):
                removed += 1
                continue
            new_lines.append(ln)
        lines = new_lines

    # Remove trailing duplicate of the first line if identical and greeting-like
    if len(lines) >= 2 and lines[0] == lines[-1] and lines[0]:
        if lines[0].lower() == lines[-1].lower() and removed == 0:
            # Only count as removal if it's actually greeting or clearly redundant
            if any(pat for pat in _GREETING_PATTERNS if re.fullmatch(pat, lines[0].lower())):
                lines = lines[:-1]
                removed += 1

    if removed:
        logger.info("[CLEAN_GREETING] removed_lines=%d", removed)
    return "\n".join([l for l in lines if l])


def remove_extraneous_headers(text: str) -> str:
    """Remove irrelevant headers like 'Web3 SDK Response:' (and variants)."""
    patterns = [r"^\*?\s*web3 sdk response:?\s*$"]
    import re as _re
    new_lines = []
    removed = 0
    for ln in text.splitlines():
        if any(_re.match(pat, ln.strip().lower()) for pat in patterns):
            removed += 1
            continue
        new_lines.append(ln)
    if removed:
        logger.info("[CLEAN_HEADER] removed_lines=%d", removed)
    return "\n".join(new_lines)


def deduplicate_repeated_sections(text: str) -> str:
    """Detect & remove large duplicate sections (e.g., repeated identical code blocks or repeated opening paragraph).

    Lightweight approach:
    - If two identical code blocks appear consecutively, drop the second.
    - If the first paragraph (<=200 chars) is repeated verbatim at the end, remove the trailing repetition.
    """
    import re as _re
    original = text

    # Hapus blok kode identik berturut
    pattern = r"(```[a-zA-Z0-9_]*\n[\s\S]*?```)(\s+)(```[a-zA-Z0-9_]*\n[\s\S]*?``` )"
    # Manual scanning untuk kesederhanaan
    code_blocks = _re.findall(r"```[a-zA-Z0-9_]*\n[\s\S]*?```", text)
    if len(code_blocks) >= 2:
        seen = set()
        new_blocks = []
        last = None
        for blk in code_blocks:
            if blk == last:
                logger.info("[DEDUP] Removed consecutive duplicate code block")
                continue
            new_blocks.append(blk)
            last = blk
        # Rebuild roughly if any removal occurred (only valid if duplicates existed)
        if len(new_blocks) != len(code_blocks):
            # naive replace all code blocks sequentially
            idx = 0
            def repl(match):
                nonlocal idx
                val = new_blocks[idx] if idx < len(new_blocks) else ''
                idx += 1
                return val
            text = _re.sub(r"```[a-zA-Z0-9_]*\n[\s\S]*?```", repl, text)

    # Paragraf pertama diulang di akhir
    first_para = text.strip().split('\n\n')[0]
    if 0 < len(first_para) <= 200:
        occurrences = text.count(first_para)
        if occurrences > 1 and text.rstrip().endswith(first_para):
            text = text.rstrip()[: -len(first_para)].rstrip()
            logger.info("[DEDUP] Removed repeated trailing paragraph")

    if text != original:
        logger.info("[DEDUP] total_chars_diff=%d", len(original) - len(text))
    return text

def _should_retry(status_code: int) -> bool:
    """Return True if the given HTTP status should be retried."""
    return status_code in {408, 429, 500, 502, 503, 504, 522, 524}


def _http_post_with_retries(api_endpoint: str, headers: dict, payload: dict, progress_cb=None):
    """Perform POST with retries on network errors and retryable HTTP statuses.

    Returns the successful `requests.Response` or raises `CortensorNetworkError` / `CortensorResponseError`.
    """
    attempt = 0
    last_exception = None
    total_attempts = _MAX_RETRIES + 1
    while True:
        attempt += 1
        started = time.monotonic()
        try:
            resp = requests.post(api_endpoint, headers=headers, json=payload, timeout=_REQUEST_TIMEOUT)
            elapsed = time.monotonic() - started
            logger.info("[HTTP] attempt=%d status=%s elapsed=%.2fs", attempt, getattr(resp, 'status_code', '?'), elapsed)

            # Success
            if 200 <= resp.status_code < 300:
                return resp

            # Retryable status?
            if attempt <= total_attempts and _should_retry(resp.status_code):
                backoff = (_RETRY_BACKOFF_BASE ** (attempt - 1))
                jitter = backoff * random.uniform(-_RETRY_JITTER, _RETRY_JITTER)
                sleep_for = max(0.1, backoff + jitter)
                logger.warning("[RETRY] attempt=%d status=%s sleeping=%.2fs", attempt, resp.status_code, sleep_for)
                if progress_cb:
                    try:
                        progress_cb({
                            'event': 'retry',
                            'kind': 'http',
                            'attempt': attempt,
                            'next_attempt': attempt + 1,
                            'total_attempts': total_attempts,
                            'reason': f'status {resp.status_code}',
                            'sleep': sleep_for
                        })
                    except Exception:
                        logger.debug("progress_cb failed (http)", exc_info=True)
                time.sleep(sleep_for)
                continue

            # Non-retryable failure
            try:
                preview = resp.text[:400]
            except Exception:
                preview = '<unavailable>'
            raise CortensorResponseError(f"HTTP {resp.status_code}: {preview}")

        except requests.RequestException as exc:  # network / timeout
            last_exception = exc
            logger.error("[NET_ERR] attempt=%d error=%s", attempt, exc.__class__.__name__, exc_info=True)
            if attempt <= total_attempts:
                backoff = (_RETRY_BACKOFF_BASE ** (attempt - 1))
                jitter = backoff * random.uniform(-_RETRY_JITTER, _RETRY_JITTER)
                sleep_for = max(0.25, backoff + jitter)
                logger.info("[NET_RETRY] attempt=%d sleeping=%.2fs", attempt, sleep_for)
                if progress_cb:
                    try:
                        progress_cb({
                            'event': 'retry',
                            'kind': 'network',
                            'attempt': attempt,
                            'next_attempt': attempt + 1,
                            'total_attempts': total_attempts,
                            'reason': exc.__class__.__name__,
                            'sleep': sleep_for
                        })
                    except Exception:
                        logger.debug("progress_cb failed (network)", exc_info=True)
                time.sleep(sleep_for)
                continue
            raise CortensorNetworkError(f"Network unreachable after {attempt} attempts: {exc}") from exc


def get_completion(history: list, new_prompt: str, progress_cb=None, *, session_id: int | None = None, client_reference: str | None = None) -> str:
    """Send prompt to Cortensor and return sanitized answer.

    Logging provides:
    - Session used
    - Prompt size & preview
    - HTTP status & latency
    - Raw answer preview
    """
    api_endpoint = config.CORTENSOR_API_URL
    headers = {"Authorization": f"Bearer {config.CORTENSOR_API_KEY}", "Content-Type": "application/json"}

    # Resolve session_id (prefer per-user override, else env)
    if session_id is None:
        try:
            session_id = int(config.CORTENSOR_SESSION_ID)
        except Exception:
            session_id = 9
            logger.warning(
                "Invalid or non-integer CORTENSOR_SESSION_ID. Falling back to 9.")

    # Build prompt: Llama 3.1 chat template (preferred) or legacy
    if getattr(config, "USE_LLAMA_CHAT_TEMPLATE", True):
        # Llama 3.1 chat format per docs:
        # <|begin_of_text|><|start_header_id|>system<|end_header_id|>
        # ...system content...
        # <|eot_id|><|start_header_id|>user<|end_header_id|>
        # ...user content...
        # <|eot_id|><|start_header_id|>assistant<|end_header_id|>
        parts = ["<|begin_of_text|>"]
        sys_lines = [ELIZA_PERSONA.strip()]
        if getattr(config, "INCLUDE_CURRENT_DATE", False):
            try:
                from datetime import datetime
                sys_lines.append(f"Current date: {datetime.utcnow().date().isoformat()}")
            except Exception:
                pass
        system_block = "\n".join(sys_lines)
        parts.append("<|start_header_id|>system<|end_header_id|>\n" + system_block + "\n<|eot_id|>")
        # History alternating user/assistant
        for i, message in enumerate(history):
            if i % 2 == 0:  # user
                parts.append("<|start_header_id|>user<|end_header_id|>\n" + str(message) + "\n<|eot_id|>")
            else:  # assistant
                parts.append("<|start_header_id|>assistant<|end_header_id|>\n" + str(message) + "\n<|eot_id|>")
        # New prompt from user, then open assistant header for generation
        parts.append("<|start_header_id|>user<|end_header_id|>\n" + str(new_prompt) + "\n<|eot_id|>")
        parts.append("<|start_header_id|>assistant<|end_header_id|>\n")
        full_prompt = "".join(parts)
        # Ensure a default stop at <|eot_id|> if not provided
        if not getattr(config, "CO_STOP", None):
            payload_stop = ["<|eot_id|>"]
        else:
            try:
                payload_stop = [s for s in str(getattr(config, "CO_STOP")).split(",") if s]
            except Exception:
                payload_stop = str(getattr(config, "CO_STOP"))
    else:
        full_prompt_parts = [ELIZA_PERSONA.strip()]
        if getattr(config, "INCLUDE_CURRENT_DATE", False):
            try:
                from datetime import datetime
                full_prompt_parts.append(f"Current date: {datetime.utcnow().date().isoformat()}")
            except Exception:
                pass
        for i, message in enumerate(history):
            if i % 2 == 0:
                full_prompt_parts.append(f"User: {message}")
            else:
                full_prompt_parts.append(f"Assistant: {message}")
        full_prompt_parts.append(f"User: {new_prompt}")
        full_prompt_parts.append("Assistant:")
        full_prompt = "\n".join(full_prompt_parts)

    resolved_client_reference = client_reference or _default_client_reference()

    payload = {
        "session_id": session_id,
        "prompt": full_prompt,
        "prompt_type": 1,
        "stream": False,
        "timeout": 180,
        # Allow longer outputs when needed; configurable via CORTENSOR_MAX_TOKENS
        "max_tokens": _MAX_TOKENS,
        # Disambiguate requests on the backend so responses are not mixed across users.
        "client_reference": resolved_client_reference,
    }
    # Decoding parameters (tunable for Llama)
    payload.update({
        "temperature": float(getattr(config, "CO_TEMPERATURE", 0.3)),
        "top_p": float(getattr(config, "CO_TOP_P", 0.9)),
        "top_k": int(getattr(config, "CO_TOP_K", 40)),
        "n": int(getattr(config, "CO_N", 1)),
        "presence_penalty": float(getattr(config, "CO_PRESENCE_PENALTY", 0.0)),
        "frequency_penalty": float(getattr(config, "CO_FREQUENCY_PENALTY", 0.0)),
    })
    # Optional stop sequences (comma-separated)
    # Stop sequences: prefer chat template stop if used
    stop_val = getattr(config, "CO_STOP", None)
    if getattr(config, "USE_LLAMA_CHAT_TEMPLATE", True):
        if stop_val:
            try:
                payload["stop"] = [s for s in str(stop_val).split(",") if s]
            except Exception:
                payload["stop"] = str(stop_val)
        else:
            payload["stop"] = ["<|eot_id|>"]
    else:
        if stop_val:
            try:
                payload["stop"] = [s for s in str(stop_val).split(",") if s]
            except Exception:
                payload["stop"] = str(stop_val)

    # --- LOG: before submission ---
    prompt_preview = (full_prompt[:220] + '…') if len(full_prompt) > 230 else full_prompt
    logger.info(
        "[SUBMIT] session=%s turns=%d prompt_chars=%d preview=%r",
        session_id,
        len(history) // 2,
        len(full_prompt),
        prompt_preview,
    )
    logger.debug(
        "[PAYLOAD] session_id=%s prompt_type=%s timeout=%s stream=%s max_tokens=%s", 
        payload.get('session_id'), payload.get('prompt_type'), payload.get('timeout'), payload.get('stream'), payload.get('max_tokens')
    )

    # Primary request with retries
    response = _http_post_with_retries(api_endpoint, headers, payload, progress_cb=progress_cb)
    response_data = response.json()

    # Log token usage if provided by the backend
    usage = _extract_token_usage(response_data)
    if usage:
        logger.info("[USAGE] prompt=%s completion=%s total=%s", usage.get('prompt'), usage.get('completion'), usage.get('total'))

    if 'choices' in response_data and response_data['choices']:
        raw_answer = response_data['choices'][0].get('text', '')

    # --- LOG: raw answer summary ---
        raw_preview = (raw_answer[:200] + '…') if len(raw_answer) > 210 else raw_answer
        logger.info(
            "[RAW_ANSWER] chars=%d preview=%r",
            len(raw_answer),
            raw_preview,
        )

        # If model uses <final>...</final>, extract it; else cut off at role markers.
        # Keep all <final> blocks; selection is done later in post_process_response
        # Paranoid guard: if there's a closing </final> without content after, we keep original.

        # Cut off if the model starts prompting the user again.
        stop_markers = ["\nUser:", "\nassistant:", "\nAssistant:"]
        for marker in stop_markers:
            if marker in raw_answer:
                raw_answer = raw_answer.split(marker)[0]
                logger.debug(f"Answer truncated at marker {marker!r}.")

    # Remove internal reasoning blocks (<think>)
        before_strip_len = len(raw_answer)
        raw_answer = strip_think_blocks(raw_answer)
        if len(raw_answer) != before_strip_len:
            logger.info("[STRIP_THINK] removed_chars=%d", before_strip_len - len(raw_answer))

        clean_answer = raw_answer.replace('</s>', '').strip()

        # Remove known special end markers and meta-evaluation/judge artifacts
        extracted = extract_last_assistant_segment(clean_answer)
        if extracted:
            clean_answer = extracted
        clean_answer = remove_special_markers(clean_answer)
        clean_answer = remove_meta_evaluation_lines(clean_answer)

    # Post-processing filters before Markdown escaping
        clean_answer = remove_extraneous_headers(clean_answer)
        clean_answer = remove_redundant_greetings(
            clean_answer,
            is_first_turn=(len(history) == 0)
        )
        clean_answer = deduplicate_repeated_sections(clean_answer)

        # Facts guard strategy: News (if enabled) -> Wikipedia (if enabled) -> Local (date/time) -> model
        chosen_answer = news_try_answer(new_prompt) or wiki_try_answer(new_prompt) or local_try_answer(new_prompt) or clean_answer

        # Apply final brevity/transcript filter before Telegram sanitization
        if getattr(config, "FLEX_OUTPUT", False):
            # In flexible mode, keep model style more naturally; still strip transcripts/reasoning safely.
            safe_brief = post_process_response(
                user_text=new_prompt,
                model_text=chosen_answer,
                brief_default=False,
            )
        else:
            safe_brief = post_process_response(
                user_text=new_prompt,
                model_text=chosen_answer,
                brief_default=config.BRIEF_BY_DEFAULT,
            )

        # Prefer HTML formatting for Telegram rendering
        sanitized = sanitize_for_html(safe_brief)

        logger.info("[DONE] final_answer_chars=%d", len(sanitized))
        return sanitized

    logger.error("Invalid response structure: keys=%s", list(response_data.keys()))
    raise CortensorResponseError("Invalid response structure from API.")
